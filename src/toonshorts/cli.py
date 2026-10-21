"""
Purpose: Command-line interface entry points for ToonShorts video pipeline.
Inputs: CLI arguments for story topic, style preset, and plugin overrides.
Outputs: Executed pipeline runs and exit status codes.
Depends on: argparse, core.config, core.pipeline, logging, pathlib, plugins, sys
Used by: __main__
Config keys: None
Tests: tests/smoke/test_smoke_pipeline.py
"""

import argparse
import sys
import logging
from pathlib import Path

# Support running directly via python src/toonshorts/cli.py
if __name__ == "__main__" and not __package__:
    src_path = str(Path(__file__).resolve().parent.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

from toonshorts.core import config
from toonshorts.core.pipeline import run_pipeline, load_style_preset
from toonshorts import plugins

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("toonshorts.cli")


def make_command(args: argparse.Namespace) -> int:
    """Executes video generation through the modular pipeline runner."""
    topic = args.topic.strip()
    if not topic:
        sys.stderr.write("Error: --topic cannot be empty.\n")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        final_video = run_pipeline(
            topic=topic,
            style_name=args.style,
            llm_name=args.llm,
            voice_name=args.voice,
            renderer_name=args.renderer,
            motion_name=args.motion,
            output_dir=output_dir,
            auto_confirm=args.yes,
            keep_temp=args.keep_temp,
            mock=args.mock,
        )
        if final_video:
            print("\n=======================================================")
            print(f"  SUCCESS! Video created at: {final_video}")
            print("=======================================================\n")
            return 0
        return 0
    except Exception as e:
        logger.exception("Pipeline failed with error: %s", e)
        sys.stderr.write(f"\nPipeline Error: {e}\n")
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="toonshorts",
        description="ToonShorts: Automated comedy animation shorts generator."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    make_parser = subparsers.add_parser("make", help="Create a finished vertical animation video")
    make_parser.add_argument("--style", required=True, help="Art style (stickman, crayon, paper_cutout, pixel_art, chalkboard)")
    make_parser.add_argument("--topic", required=True, help="Story topic or comedy premise")
    make_parser.add_argument("--yes", "-y", action="store_true", help="Skip cost confirmation prompt")
    make_parser.add_argument("--mock", action="store_true", help="Run with offline mock generator for testing")
    make_parser.add_argument("--llm", default=None, help="LLM plugin to use (gemini, fake)")
    make_parser.add_argument("--voice", default=None, help="Voice plugin to use (edge_tts, synthetic, fake)")
    make_parser.add_argument("--renderer", default=None, help="Renderer plugin to use (pillow, gemini, fake)")
    make_parser.add_argument("--motion", default=None, help="Motion plugin to use (ffmpeg, static)")
    make_parser.add_argument("--output-dir", default=None, help="Custom output directory")
    make_parser.add_argument("--keep-temp", action="store_true", help="Retain intermediate render assets")

    args = parser.parse_args()
    if args.command == "make":
        sys.exit(make_command(args))


if __name__ == "__main__":
    main()
