"""
Purpose: Command-line interface entry points for ToonShorts video pipeline.
Inputs: CLI arguments for story topic, style preset, brief, and plugin overrides.
Outputs: Executed pipeline runs and exit status codes.
Depends on: argparse, brief, core.acting, core.camera, core.config, core.images, core.layout_checker, core.library, core.pipeline, core.visual_checker, inventory, logging, pathlib, plugins, sys
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
                renderer_name=args.renderer,
                output_dir=output_dir,
                stills_only=getattr(args, "stills_only", False),
                auto_confirm=args.yes,
                mock=args.mock,
                keep_temp=args.keep_temp,
                fast=getattr(args, "fast", False),
                workers=workers,
                overwrite=overwrite,
                scene_source=getattr(args, "scene", None),
                allow_fallback=getattr(args, "allow_fallback", False),
                allow_low_score=getattr(args, "allow_low_score", False),
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
            allow_fallback=getattr(args, "allow_fallback", False),
            allow_low_score=getattr(args, "allow_low_score", False),
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




def check_camera_command(args: argparse.Namespace) -> int:
    """Verifies camera plan shot list, determinism, zoom limits, and clearance."""
    from toonshorts.core.camera import check_camera
    try:
        report = check_camera(args.video_name)
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2))
        else:
            status = report.get("status", "FAIL")
            print(f"Camera check {status} for {report.get('video')}")
            print(f"Shots: {report.get('shots_count')}, Duration: {report.get('total_duration_sec', 0):.2f}s, Peak Zoom: {report.get('peak_zoom', 0):.2f}")
            if report.get("errors"):
                for err in report["errors"]:
                    print(f"  - ERROR: {err}")
        return 0 if report.get("status") == "PASS" else 1
    except Exception as e:
        sys.stderr.write(f"Camera check error: {e}\n")
        return 1



def check_acting_command(args: argparse.Namespace) -> int:
    """Verifies acting plan, beat coverage, gesture vocabulary, and listener reactions."""
    from toonshorts.core.acting import check_acting
    try:
        report = check_acting(args.video_name)
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2))
        else:
            status = report.get("status", "FAIL")
            print(f"Acting check {status} for {report.get('video')}")
            print(f"Scenes: {report.get('scenes_count')}, Cast: {report.get('cast')}")
            if report.get("errors"):
                for err in report["errors"]:
                    print(f"  - ERROR: {err}")
        return 0 if report.get("status") == "PASS" else 1
    except Exception as e:
        sys.stderr.write(f"Acting check error: {e}\n")
        return 1

def check_visuals_command(args: argparse.Namespace) -> int:
    """Inspects scene stills against quality checklist, contrast ratios, and writes visual_review.md."""
    from toonshorts.core.visual_checker import perform_visual_check
    video_input = args.video_name
    video_path = Path(video_input)
    if not video_path.is_dir():
        cand = config.VIDEOS_DIR / video_input
        if cand.is_dir():
            video_path = cand
        else:
            sys.stderr.write(f"Error: Video directory not found at '{video_input}' or '{cand}'.\n")
            return 1
    try:
        report = perform_visual_check(video_path)
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2))
        else:
            txt_report = (video_path / "visual_review.md").read_text(encoding="utf-8")
            print(txt_report)
        return 0 if report.get("passed", False) else 1
    except Exception as e:
        sys.stderr.write(f"Visual check error: {e}\n")
        return 1


def check_layout_command(args: argparse.Namespace) -> int:
    """Verifies scene stills layout, bounding boxes, and safe zones using Playwright."""
    from toonshorts.core.layout_checker import verify_video_layout
    video_input = args.video_name
    video_path = Path(video_input)
    if not video_path.is_dir():
        cand = config.VIDEOS_DIR / video_input
        if cand.is_dir():
            video_path = cand
        else:
            sys.stderr.write(f"Error: Video directory not found at '{video_input}' or '{cand}'.\n")
            return 1
    try:
        report = verify_video_layout(video_path)
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2))
        else:
            txt_report = (video_path / "layout_check.txt").read_text(encoding="utf-8")
            print(txt_report)
        return 0 if report.get("passed", False) else 1
    except Exception as e:
        sys.stderr.write(f"Layout check error: {e}\n")
        return 1


def register_image_command(args: argparse.Namespace) -> int:
    """Takes an image file and registers it into library/elements/images/."""
    try:
        from toonshorts.core.images import register_image
        lib_path = register_image(
            file_path=args.file,
            prompt=args.prompt,
            style=args.style,
            theme=args.theme,
            source=args.source,
        )
        print(str(lib_path))
        return 0
    except Exception as e:
        sys.stderr.write(f"Error registering image: {e}\n")
        return 1


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
    make_parser.add_argument("--scene", default=None, help="Explicit scene plan JSON file to build")
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
    make_parser.add_argument("--allow-fallback", action="store_true", default=False, help="Allow fallback to proportional word timing and even spacing if Whisper alignment fails")
    make_parser.add_argument("--allow-low-score", action="store_true", default=False, help="Continue full video generation even if critic review score is below 7.0 after repair")
    make_parser.add_argument("--keep-temp", action="store_true", help="Retain intermediate render assets")

    clean_parser = subparsers.add_parser("clean-tmp", help="Remove lingering temporary build directories (.tmp-*) from videos/")

    inv_parser = subparsers.add_parser("inventory", help="Inspect installed characters, styles, voices, and animations")
    inv_parser.add_argument("--json", action="store_true", help="Output inventory as structured JSON")

    check_layout_parser = subparsers.add_parser("check-layout", help="Verify scene stills layout, bounding boxes, and safe zones")
    check_layout_parser.add_argument("video_name", help="Name of video folder inside videos/ or path to directory")
    check_layout_parser.add_argument("--json", action="store_true", help="Output check results as structured JSON")

    check_cam_parser = subparsers.add_parser("check-camera", help="Verify camera plan shot list, pacing, determinism, and zoom limits")
    check_cam_parser.add_argument("video_name", help="Name of video folder inside videos/ or path to directory")
    check_cam_parser.add_argument("--json", action="store_true", help="Output review as structured JSON")

    check_acting_parser = subparsers.add_parser("check-acting", help="Verify acting plan, beats, accents, gestures, and listener reactions")
    check_acting_parser.add_argument("video_name", help="Name of video folder inside videos/ or path to directory")
    check_acting_parser.add_argument("--json", action="store_true", help="Output review as structured JSON")

    check_visuals_parser = subparsers.add_parser("check-visuals", help="Inspect scene stills against quality checklist and contrast ratios")
    check_visuals_parser.add_argument("video_name", help="Name of video folder inside videos/ or path to directory")
    check_visuals_parser.add_argument("--json", action="store_true", help="Output review as structured JSON")

    reg_img_parser = subparsers.add_parser(
        "register-image",
        help="Validate, strip metadata, and register an image into library/elements/images/",
    )
    reg_img_parser.add_argument("file", help="Path to image file to register")
    reg_img_parser.add_argument("--prompt", required=True, help="Prompt used to generate the image")
    reg_img_parser.add_argument("--theme", default=None, help="Theme tags (e.g. night_studio, security)")
    reg_img_parser.add_argument("--style", default="default", help="Art style of the image")
    reg_img_parser.add_argument("--source", default="generated", help="Source of image (default: generated)")

    args = parser.parse_args()
    if args.command == "make":
        sys.exit(make_command(args))
    elif args.command == "clean-tmp":
        sys.exit(clean_tmp_command(args))
    elif args.command == "inventory":
        sys.exit(inventory_command(args))
    elif args.command == "check-layout":
        sys.exit(check_layout_command(args))
    elif args.command == "check-camera":
        sys.exit(check_camera_command(args))
    elif args.command == "check-acting":
        sys.exit(check_acting_command(args))
    elif args.command == "check-visuals":
        sys.exit(check_visuals_command(args))
    elif args.command == "register-image":
        sys.exit(register_image_command(args))


if __name__ == "__main__":
    main()
