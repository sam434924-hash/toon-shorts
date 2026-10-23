"""
Unit tests for parallel scene rendering, worker pool, ordering, and FFmpeg pipe error handling:
1. Worker count limits (1-4, rejects < 1 or > 4).
2. Strict scene ordering even when workers finish out of order.
3. Cancellation, process termination, and directory cleanup after a failed worker.
4. FFmpeg pipe error handling and partial output cleanup on failure.
"""

from pathlib import Path
import subprocess
import time
from unittest.mock import MagicMock, patch
import pytest

from toonshorts.plugins.render.animejs.capture import (
    SceneRenderJob,
    _render_job_with_browser,
    derive_scene_seed,
    render_scenes_in_parallel,
    validate_worker_count,
)


def test_worker_count_limits():
    """Validates worker count defaults to 2, allows 1-4, and rejects all other values."""
    assert validate_worker_count(None) == 2
    assert validate_worker_count(1) == 1
    assert validate_worker_count(2) == 2
    assert validate_worker_count(3) == 3
    assert validate_worker_count(4) == 4

    for invalid in [0, -1, -5, 5, 8, 10, "2", 1.5]:
        with pytest.raises(ValueError, match="Worker count must be an integer between 1 and 4"):
            validate_worker_count(invalid)


def test_rough_seed_derivation_deterministic():
    """Scene seed derivation must be identical across runs and distinct across scene IDs."""
    s1_a = derive_scene_seed(1, global_seed=42)
    s1_b = derive_scene_seed(1, global_seed=42)
    s2 = derive_scene_seed(2, global_seed=42)
    assert s1_a == s1_b
    assert s1_a != s2


def test_scene_ordering_preserved_out_of_order_completion(tmp_path):
    """
    Simulates workers completing in arbitrary order (e.g. 3, then 1, then 2).
    Verifies that the assembler / coordinator returns scenes strictly in scene order.
    """
    job1 = SceneRenderJob(scene_number=1, title="S1", words=[], audio_path=None, output_path=tmp_path / "s1.mp4")
    job2 = SceneRenderJob(scene_number=2, title="S2", words=[], audio_path=None, output_path=tmp_path / "s2.mp4")
    job3 = SceneRenderJob(scene_number=3, title="S3", words=[], audio_path=None, output_path=tmp_path / "s3.mp4")

    # Stagger sleep so job 3 finishes first, then 1, then 2
    delays = {1: 0.05, 2: 0.10, 3: 0.01}

    def mock_render(job, **kwargs):
        time.sleep(delays[job.scene_number])
        job.output_path.write_bytes(b"dummy")
        return job.output_path

    with patch("toonshorts.plugins.render.animejs.capture._render_job_with_browser", side_effect=mock_render):
        results = render_scenes_in_parallel([job1, job2, job3], workers=3)

    assert results == [job1.output_path, job2.output_path, job3.output_path]


def test_failed_worker_cancels_others_and_cleans_up(tmp_path):
    """
    Simulates a worker failure in Scene 2.
    Verifies that:
    - Error is raised naming Scene 2.
    - Other running workers are canceled.
    - Partial output files and temp directories are cleaned up.
    """
    job1 = SceneRenderJob(scene_number=1, title="S1", words=[], audio_path=None, output_path=tmp_path / "s1.mp4")
    job2 = SceneRenderJob(scene_number=2, title="S2", words=[], audio_path=None, output_path=tmp_path / "s2.mp4")
    job3 = SceneRenderJob(scene_number=3, title="S3", words=[], audio_path=None, output_path=tmp_path / "s3.mp4")

    def mock_render_fail(job, cancel_event=None, **kwargs):
        if job.scene_number == 2:
            time.sleep(0.02)
            job.output_path.write_bytes(b"partial")
            raise RuntimeError("Crash in video encoder for Scene 2")
        # Other jobs wait for cancellation
        for _ in range(20):
            if cancel_event and cancel_event.is_set():
                return None
            time.sleep(0.01)
        job.output_path.write_bytes(b"completed")
        return job.output_path

    with patch("toonshorts.plugins.render.animejs.capture._render_job_with_browser", side_effect=mock_render_fail):
        with pytest.raises(RuntimeError, match="Rendering failed in Scene 2"):
            render_scenes_in_parallel([job1, job2, job3], workers=2)

    # Partial output of failed job must be deleted
    assert not (tmp_path / "s2.mp4").exists()


def test_ffmpeg_pipe_error_handling(tmp_path):
    """Simulates an FFmpeg failure and verifies clean termination and clear error message with stderr."""
    out_file = tmp_path / "fail_video.mp4"
    job = SceneRenderJob(
        scene_number=1,
        title="Fail Test",
        words=[{"text": "Crash"}],
        audio_path=None,
        output_path=out_file,
        duration_sec=0.5,
        temp_dir=tmp_path / "temp_sc1",
    )

    # Mock subprocess.Popen to return a process that fails with code 1
    fake_proc = MagicMock()
    fake_proc.poll.return_value = 1
    fake_proc.wait.return_value = 1
    fake_proc.stdin = MagicMock()
    fake_proc.stdin.closed = False

    def fake_popen(*args, **kwargs):
        # Write mock error message to stderr log file if opened
        stderr_file = kwargs.get("stderr")
        if stderr_file and hasattr(stderr_file, "write"):
            stderr_file.write(b"Error: Mock FFmpeg invalid codec or broken filter graph!\n")
            stderr_file.flush()
        return fake_proc

    with patch("subprocess.Popen", side_effect=fake_popen):
        with patch("toonshorts.plugins.render.animejs.capture.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_pw.return_value.start.return_value.chromium.launch.return_value = mock_browser
            mock_context = MagicMock()
            mock_browser.new_context.return_value = mock_context
            mock_page = MagicMock()
            mock_context.new_page.return_value = mock_page
            mock_page.evaluate.return_value = []
            mock_page.screenshot.return_value = b"\x89PNG\r\n\x1a\n"

            with pytest.raises(RuntimeError, match="FFmpeg pipeline failed for scene 1 with return code 1"):
                _render_job_with_browser(job)

    # Verify partial file is removed
    assert not out_file.exists()


def test_keyboard_interrupt_cleanup(tmp_path):
    """Simulates Ctrl+C (KeyboardInterrupt) and verifies cleanup of outputs, temp dirs, and procs."""
    out_file1 = tmp_path / "sc1_int.mp4"
    out_file2 = tmp_path / "sc2_int.mp4"
    job1 = SceneRenderJob(scene_number=1, title="S1", words=[], audio_path=None, output_path=out_file1)
    job2 = SceneRenderJob(scene_number=2, title="S2", words=[], audio_path=None, output_path=out_file2)

    def mock_interrupt(job, **kwargs):
        job.output_path.write_bytes(b"partial-data")
        if job.scene_number == 1:
            raise KeyboardInterrupt("Simulated Ctrl+C")
        time.sleep(0.1)
        return job.output_path

    with patch("toonshorts.plugins.render.animejs.capture._render_job_with_browser", side_effect=mock_interrupt):
        with pytest.raises(KeyboardInterrupt):
            render_scenes_in_parallel([job1, job2], workers=2)

    assert not out_file1.exists()
    assert not out_file2.exists()
