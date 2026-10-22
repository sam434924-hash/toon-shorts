"""
Unit tests for Fast Preview Mode (--fast):
1. Verifies fast mode produces 540x960 resolution at 15 fps.
2. Verifies duration is capped at <= 6.0 seconds.
3. Verifies output is written strictly into output/fast/ and never the normal output name.
4. Verifies fast mode makes no Gemini API calls and reuses cached audio.
"""

import json
from pathlib import Path
import subprocess
import pytest

from toonshorts.core import config
from toonshorts.core.pipeline import run_pipeline


def get_video_metadata(video_path: Path):
    """Extracts width, height, fps, and duration from a video via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:format=duration",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    stream = data["streams"][0]
    width = int(stream["width"])
    height = int(stream["height"])
    r_fps = stream["r_frame_rate"]
    num, den = map(int, r_fps.split("/"))
    fps = round(num / den)
    duration = float(data["format"]["duration"])
    return width, height, fps, duration


def test_fast_preview_mode_pipeline(monkeypatch):
    """Verifies fast preview generates <= 6s video at 540x960 @ 15fps in output/fast/."""
    # Ensure no Gemini calls occur by sabotaging API client if invoked
    from toonshorts.core.client import GeminiClientWrapper
    def bomb_generate(*args, **kwargs):
        raise AssertionError("CRITICAL: Fast preview mode must NEVER make a Gemini API call!")
    monkeypatch.setattr(GeminiClientWrapper, "generate_text_with_retry", bomb_generate)
    monkeypatch.setattr(GeminiClientWrapper, "generate_speech_with_retry", bomb_generate)
    monkeypatch.setattr(GeminiClientWrapper, "generate_image_with_retry", bomb_generate)

    # Protected file check
    normal_output = config.OUTPUT_DIR / "What_is_an_API.mp4"
    initial_mtime = normal_output.stat().st_mtime if normal_output.exists() else None

    # Run pipeline in fast mode with cached topic
    fast_video = run_pipeline(
        topic="What is an API?",
        style_name="stickman",
        fast=True,
    )

    assert fast_video is not None
    assert fast_video.is_file()

    # 1. Output destination check: must be in output/fast/ and not normal output
    assert fast_video.parent == config.OUTPUT_DIR / "fast"
    assert fast_video.name != "What_is_an_API.mp4"
    if normal_output.exists():
        assert normal_output.stat().st_mtime == initial_mtime, "Normal output was overwritten!"

    # 2. Video property checks
    width, height, fps, duration = get_video_metadata(fast_video)
    assert (width, height) == (540, 960), f"Expected half resolution (540, 960), got ({width}, {height})"
    assert fps == 15, f"Expected 15 fps, got {fps}"
    assert duration <= 6.05, f"Expected duration <= 6.0s, got {duration}s"
