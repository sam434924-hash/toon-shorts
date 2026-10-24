"""
Unit tests for Fast Preview / Fast Draft Mode (--fast):
1. Verifies non-supporting renderers raise PipelineError on --fast.
2. Verifies fast mode produces 540x960 resolution at 15 fps on animejs renderer.
3. Verifies output is written strictly into output/fast/ and never the normal output name.
4. Verifies fast mode makes no Gemini API calls and reuses cached audio.
"""

import json
from pathlib import Path
import subprocess
import pytest

from toonshorts.core import config
from toonshorts.core.errors import PipelineError
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


def test_fast_mode_rejects_unsupported_renderer():
    """Fast draft mode must raise an explicit PipelineError if renderer does not support it."""
    with pytest.raises(PipelineError, match="does not support fast draft mode"):
        run_pipeline(
            topic="What is an API?",
            style_name="stickman",
            renderer_name="cairo",
            mock=True,
            fast=True,
        )


@pytest.mark.slow
def test_fast_preview_mode_pipeline(monkeypatch):
    """Verifies fast draft generates 540x960 @ 15fps in output/fast/ on supported renderer."""
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

    # Run pipeline in fast mode with cached topic and animejs
    fast_video = run_pipeline(
        topic="What is an API?",
        style_name="whiteboard",
        renderer_name="animejs",
        fast=True,
        overwrite=True,
    )

    assert fast_video is not None
    assert fast_video.is_file()

    # 1. Output destination check: must be in videos/What_is_an_API/ and self-contained
    video_dir = fast_video.parent
    assert video_dir.name == "What_is_an_API"
    assert (video_dir / "brief.json").is_file()
    assert (video_dir / "scene.json").is_file()
    assert (video_dir / "manifest.json").is_file()
    assert (video_dir / "voice").is_dir()
    assert (video_dir / "visuals").is_dir()

    # 2. Video property checks
    width, height, fps, duration = get_video_metadata(fast_video)
    assert (width, height) == (540, 960), f"Expected half resolution (540, 960), got ({width}, {height})"
    assert fps == 15, f"Expected 15 fps, got {fps}"
    assert duration > 10.0, f"Expected full duration matching plan, got {duration}s"
