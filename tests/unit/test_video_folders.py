"""
Purpose: Unit tests for self-contained video folder architecture, name sanitizer, exists-guard, and clean failure.
Inputs: Video names, temporary directory fixtures, mock pipeline options.
Outputs: Pytest assertions verifying folder layout, safety checks, and library reuse.
Depends on: pathlib, pytest, toonshorts.core.library, toonshorts.core.models, toonshorts.core.pipeline
Used by: Test suite
Config keys: None
Tests: tests/unit/test_video_folders.py
"""

from pathlib import Path
import pytest
import shutil
import uuid

from toonshorts.core.models import (
    sanitize_video_name,
    resolve_video_dir,
    VideoManifest,
)
from toonshorts.core.library import (
    compute_library_key,
    get_or_create_sfx,
    copy_library_asset,
    clean_temp_builds,
)
from toonshorts.core.pipeline import run_pipeline, run_pipeline_from_brief
from toonshorts.brief import VideoBrief


def test_name_sanitizer_valid_and_cleaning():
    """Verify video name sanitizer enforces alphanumeric, dash, and underscore characters."""
    assert sanitize_video_name("octopus_facts_v2") == "octopus_facts_v2"
    assert sanitize_video_name("My Great Video!") == "My_Great_Video"
    assert sanitize_video_name("hello---world___test") == "hello-world_test"
    assert sanitize_video_name("clean-name-123") == "clean-name-123"


def test_name_sanitizer_length_cap():
    """Verify video name sanitizer enforces length limit (max 64 chars)."""
    long_name = "a" * 100
    cleaned = sanitize_video_name(long_name, max_length=64)
    assert len(cleaned) <= 64
    assert cleaned == "a" * 64


def test_name_sanitizer_rejects_empty_and_reserved():
    """Verify video name sanitizer rejects empty strings and Windows reserved names."""
    with pytest.raises(ValueError, match="empty"):
        sanitize_video_name("   ")

    with pytest.raises(ValueError, match="empty"):
        sanitize_video_name("!@#$%^&*()")

    for res in ["CON", "prn", "aux", "nul", "com1", "lpt9"]:
        with pytest.raises(ValueError, match="reserved"):
            sanitize_video_name(res)


def test_name_sanitizer_path_traversal_resolution(tmp_path):
    """Verify resolve_video_dir blocks any names resolving outside the base videos directory."""
    base_dir = tmp_path / "videos"
    base_dir.mkdir()

    # Normal resolution
    safe_dir = resolve_video_dir("my_clip", base_dir=base_dir)
    assert safe_dir == base_dir / "my_clip"
    assert safe_dir.parent == base_dir

    # Traversal attempts sanitized to safe names within base_dir
    sanitized = resolve_video_dir("../../etc/passwd", base_dir=base_dir)
    assert sanitized.parent == base_dir
    assert ".." not in sanitized.name


def test_exists_guard_stops_and_overwrite_allows(tmp_path):
    """Verify pipeline stops if videos/<name> already exists, and only proceeds with overwrite=True."""
    base_dir = tmp_path / "videos"
    base_dir.mkdir()
    existing_dir = base_dir / "existing_video"
    existing_dir.mkdir()
    (existing_dir / "scene.json").write_text('{"old": true}', encoding="utf-8")

    # Should raise FileExistsError without overwrite
    with pytest.raises(FileExistsError, match="already exists"):
        run_pipeline(
            topic="existing_video",
            style_name="stickman",
            output_dir=base_dir,
            mock=True,
            auto_confirm=True,
            overwrite=False,
        )

    # With overwrite=True, pipeline proceeds
    result = run_pipeline(
        topic="existing_video",
        style_name="stickman",
        output_dir=base_dir,
        mock=True,
        auto_confirm=True,
        overwrite=True,
    )
    assert result is not None
    assert result.is_file()
    # Ensure old scene.json was NOT silently loaded or retained
    new_scene = (existing_dir / "scene.json").read_text(encoding="utf-8")
    assert '"old": true' not in new_scene


def test_failed_run_preserves_tmp_dir_and_run_log(tmp_path, monkeypatch):
    """Verify failed run leaves .tmp-<name>-<id> directory intact with run.log."""
    base_dir = tmp_path / "videos"
    base_dir.mkdir()

    # Sabotage voice generation to simulate failure mid-pipeline
    from toonshorts.plugins.voice.fake import FakeVoicePlugin
    def failing_generate(*args, **kwargs):
        raise RuntimeError("Simulated mid-pipeline crash!")
    monkeypatch.setattr(FakeVoicePlugin, "generate_all_voices", failing_generate)

    with pytest.raises(RuntimeError, match="Simulated mid-pipeline crash"):
        run_pipeline(
            topic="failing_video",
            style_name="stickman",
            output_dir=base_dir,
            mock=True,
            auto_confirm=True,
        )

    # Destination videos/failing_video must NOT exist
    assert not (base_dir / "failing_video").exists()

    # Temporary build folder must be preserved
    tmp_folders = list(base_dir.glob(".tmp-failing_video-*"))
    assert len(tmp_folders) == 1
    preserved = tmp_folders[0]
    assert preserved.is_dir()
    assert (preserved / "run.log").is_file()
    assert (preserved / "brief.json").is_file()
    assert (preserved / "scene.json").is_file()


def test_clean_temp_builds_utility(tmp_path):
    """Verify clean_temp_builds cleans lingering .tmp-* folders and leaves final folders alone."""
    base_dir = tmp_path / "videos"
    base_dir.mkdir()

    (base_dir / ".tmp-vid1-abc12345").mkdir()
    (base_dir / ".tmp-vid2-def67890").mkdir()
    (base_dir / "finished_video").mkdir()

    cleaned = clean_temp_builds(videos_dir=base_dir)
    assert len(cleaned) == 2
    assert not (base_dir / ".tmp-vid1-abc12345").exists()
    assert not (base_dir / ".tmp-vid2-def67890").exists()
    assert (base_dir / "finished_video").is_dir()


def test_library_reuse_and_copy(tmp_path):
    """Verify library caches assets on miss, reuses on hit, and plain-copies into video folder."""
    dest_file = tmp_path / "dest" / "sfx.wav"
    calls = 0

    def make_sfx(p: Path):
        nonlocal calls
        calls += 1
        p.write_bytes(b"RIFFdummydata")

    unique_sfx_name = f"test_boing_{uuid.uuid4().hex}"
    # Miss: renders and saves to library
    path1, is_hit1 = get_or_create_sfx(unique_sfx_name, make_sfx)
    try:
        assert not is_hit1
        assert calls == 1
        assert path1.is_file()

        # Hit: reuses from library without recalling maker
        path2, is_hit2 = get_or_create_sfx(unique_sfx_name, make_sfx)
        assert is_hit2
        assert calls == 1
        assert path1 == path2

        # Plain copy into video destination
        copied = copy_library_asset(path1, dest_file)
        assert copied.is_file()
        assert copied == dest_file
        assert not copied.is_symlink()
    finally:
        if path1.exists():
            path1.unlink()
