"""
Purpose: Command-line interface entry points for ToonShorts video pipeline.
Inputs: CLI arguments for story topic, style preset, brief, and plugin overrides.
Outputs: Executed pipeline runs and exit status codes.
Depends on: argparse, brief, core.config, core.library, core.pipeline, inventory, logging, pathlib, plugins, sys
Used by: __main__
Config keys: None
Tests: tests/smoke/test_smoke_pipeline.py
"""

import argparse
import json
import logging
from pathlib import Path
import sys

# Support running directly via python src/toonshorts/cli.py
if __name__ == "__main__" and not __package__:
    src_path = str(Path(__file__).resolve().parent.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

from toonshorts.core import config
from toonshorts.core.pipeline import run_pipeline, run_pipeline_from_brief, load_style_preset
from toonshorts.core.library import clean_temp_builds
from toonshorts import plugins
from toonshorts.inventory import format_inventory_display, get_inventory
from toonshorts.brief import load_brief

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("toonshorts.cli")


def make_command(args: argparse.Namespace) -> int:
    """Executes video generation through the modular pipeline runner or validated brief."""
    workers = getattr(args, "workers", None)
    if workers is not None and (workers < 1 or workers > 4):
        sys.stderr.write(f"Error: Invalid worker count: {workers}. Worker count must be between 1 and 4.\n")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None
    overwrite = getattr(args, "overwrite", False)

    # Brief mode execution
    if getattr(args, "brief", None):
        try:
            brief = load_brief(args.brief)
            result = run_pipeline_from_brief(
                brief_source=brief,
                output_dir=output_dir,
                stills_only=getattr(args, "stills_only", False),
                auto_confirm=args.yes,
                mock=args.mock,
                keep_temp=args.keep_temp,
                fast=getattr(args, "fast", False),
                workers=workers,
                overwrite=overwrite,
            )
            if getattr(args, "stills_only", False):
                print("\n=======================================================")
                print(f"  KEY SCENE STILLS READY FOR APPROVAL:")
                for st in result.get("stills", []):
                    print(f"   - {st}")
                print(f"  Scene file: {result.get('scene_file')}")
                print("=======================================================\n")
                return 0

            final_video = result.get("video")
            if final_video:
                print("\n=======================================================")
                print(f"  SUCCESS! Video created at: {final_video}")
                print(f"  Self-contained folder: {final_video.parent}")
                print("=======================================================\n")
                return 0
            return 0
        except Exception as e:
            logger.exception("Brief pipeline failed with error: %s", e)
            sys.stderr.write(f"\nPipeline Error: {e}\n")
            return 1

    topic = (args.topic or "").strip()
    if not topic:
        sys.stderr.write("Error: --topic or --brief is required.\n")
        return 1

    if not args.style:
        sys.stderr.write("Error: --style is required when not using --brief.\n")
        return 1

    # Support both --voice-engine and deprecated --voice
    voice_choice = args.voice_engine or args.voice

    try:
        final_video = run_pipeline(
            topic=topic,
            style_name=args.style,
            llm_name=args.llm,
            voice_name=voice_choice,
            renderer_name=args.renderer,
            motion_name=args.motion,
            output_dir=output_dir,
            auto_confirm=args.yes,
            keep_temp=args.keep_temp,
            mock=args.mock,
            allow_noncommercial=args.allow_noncommercial,
            fast=getattr(args, "fast", False),
            workers=workers,
            overwrite=overwrite,
        )
        if final_video:
            print("\n=======================================================")
            print(f"  SUCCESS! Video created at: {final_video}")
            print(f"  Self-contained folder: {final_video.parent}")
            print("=======================================================\n")
            return 0
        return 0
    except Exception as e:
        logger.exception("Pipeline failed with error: %s", e)
        sys.stderr.write(f"\nPipeline Error: {e}\n")
        return 1


def clean_tmp_command(args: argparse.Namespace) -> int:
    """Deletes lingering temporary build folders from videos/."""
    deleted = clean_temp_builds()
    if deleted:
        print(f"Cleaned {len(deleted)} temporary build folder(s):")
        for d in deleted:
            print(f" - {d.name}")
    else:
        print("No temporary build folders found.")
    return 0


def inventory_command(args: argparse.Namespace) -> int:
    """Prints installed asset and plugin inventory."""
    if getattr(args, "json", False):
        print(json.dumps(get_inventory(), indent=2))
    else:
        print(format_inventory_display())
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="toonshorts",
        description="ToonShorts: Automated comedy animation shorts generator."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    make_parser = subparsers.add_parser("make", help="Create a finished vertical animation video")
    make_parser.add_argument("--style", default=None, help="Art style (stickman, crayon, paper_cutout, pixel_art, chalkboard, whiteboard)")
    make_parser.add_argument("--topic", default=None, help="Story topic or comedy premise")
    make_parser.add_argument("--brief", default=None, help="Path or name of brief JSON file to build")
    make_parser.add_argument("--stills-only", action="store_true", help="Render key scene stills for approval first")
    make_parser.add_argument("--yes", "-y", action="store_true", help="Skip cost confirmation prompt")
    make_parser.add_argument("--mock", action="store_true", help="Run with offline mock generator for testing")
    make_parser.add_argument(
        "--fast",
        action="store_true",
        default=False,
        help="Fast draft mode: half resolution (540x960), 15 fps, roughness 0, blur off",
    )
    make_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of parallel render workers (1-4, default: 2)",
    )
    make_parser.add_argument("--llm", default=None, help="LLM plugin to use (gemini, fake)")
    make_parser.add_argument(
        "--voice-engine",
        dest="voice_engine",
        choices=["gemini", "gemini_tts", "piper", "sapi", "windows_sapi", "fake"],
        default=None,
        help="Voice engine plugin to use (gemini, piper, sapi)",
    )
    make_parser.add_argument("--voice", default=None, help=argparse.SUPPRESS)
    make_parser.add_argument(
        "--allow-noncommercial",
        action="store_true",
        help="Allow voices marked as non-commercial or unverified in voices.json",
    )
    make_parser.add_argument("--renderer", default=None, help="Renderer plugin to use (animejs, cairo, pillow, gemini, fake)")
    make_parser.add_argument("--motion", default=None, help="Motion plugin to use (ffmpeg, static)")
    make_parser.add_argument("--output-dir", default=None, help="Custom output directory")
    make_parser.add_argument("--overwrite", action="store_true", default=False, help="Overwrite existing video directory if it already exists")
    make_parser.add_argument("--keep-temp", action="store_true", help="Retain intermediate render assets")

    clean_parser = subparsers.add_parser("clean-tmp", help="Remove lingering temporary build directories (.tmp-*) from videos/")

    inv_parser = subparsers.add_parser("inventory", help="Inspect installed characters, styles, voices, and animations")
    inv_parser.add_argument("--json", action="store_true", help="Output inventory as structured JSON")

    args = parser.parse_args()
    if args.command == "make":
        sys.exit(make_command(args))
    elif args.command == "clean-tmp":
        sys.exit(clean_tmp_command(args))
    elif args.command == "inventory":
        sys.exit(inventory_command(args))


if __name__ == "__main__":
    main()
