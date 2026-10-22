"""Smoke test running the entire end-to-end pipeline with fake plugins in under 30s."""

import time
from pathlib import Path
import pytest
from toonshorts.core.pipeline import run_pipeline


@pytest.mark.slow
def test_full_pipeline_smoke(tmp_path):
    """Executes the entire ToonShorts pipeline without network or API calls."""
    start_time = time.time()

    out_dir = tmp_path / "smoke_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    video_path = run_pipeline(
        topic="The Semicolon Mystery",
        style_name="stickman",
        llm_name="fake",
        voice_name="fake",
        renderer_name="fake",
        motion_name="static",
        output_dir=out_dir,
        auto_confirm=True,
        keep_temp=False,
        mock=True,
    )

    elapsed = time.time() - start_time

    assert video_path is not None, "Pipeline did not return an output video path"
    assert Path(video_path).is_file(), f"Output video file does not exist: {video_path}"
    assert Path(video_path).stat().st_size > 0, "Output video file is 0 bytes"
    assert elapsed < 30.0, f"Smoke test took {elapsed:.2f}s, exceeding 30 second threshold"
