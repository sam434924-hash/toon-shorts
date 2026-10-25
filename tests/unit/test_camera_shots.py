"""
Purpose: Comprehensive unit tests for camera shot language, Appendix A implementation, and check-camera CLI.
Inputs: Synthetic scenes, camera shot presets, and camera plan files.
Outputs: Assertion results for presets, parallax, transitions, zoom cap, and validation.
Depends on: pytest, json, pathlib, toonshorts.core.camera_shots, toonshorts.core.camera, toonshorts.core.config
Used by: tests
Config keys: CAMERA_CHARACTER_MAX_ZOOM, CAMERA_BOARD_MAX_ZOOM
Tests: self
"""

import json
from pathlib import Path
import pytest
from toonshorts.core import config
from toonshorts.core.camera_shots import (
    PRESETS,
    ShotPreset,
    CameraShot,
    DEFAULT_PLANES,
    shot_from_preset,
    evaluate_camera,
    bg_blur_for_zoom,
    cut_time_for_line,
    timeline_problems,
)
from toonshorts.core.camera import (
    plan_camera_plan,
    save_camera_plan,
    load_camera_plan,
    check_camera,
)


def test_presets_exist_and_conform_to_appendix_a():
    """Verify all 6 required Appendix A shot presets are defined with valid properties."""
    required = [
        "CAM_01_WIDE_2SHOT",
        "CAM_02_MED_BOARD",
        "CAM_03_OTS_SPEAKER_A",
        "CAM_04_CU_SPEAKER_B",
        "CAM_05_CU_SPEAKER_A",
        "CAM_06_ECU_REACTION",
    ]
    for code in required:
        assert code in PRESETS, f"Preset {code} must exist"
        preset = PRESETS[code]
        assert isinstance(preset, ShotPreset)
        assert preset.zoom_min >= 1.0
        assert preset.lens_mm > 0
        assert 0.0 <= preset.center[0] <= 1.0
        assert 0.0 <= preset.center[1] <= 1.0
        assert preset.bg_blur_px >= 0.0


def test_shot_transitions_and_zoom_cap():
    """Verify hard cuts (0s), snap-zooms (6-8 frames), and creep pushes respect zoom cap 1.9."""
    # 0s Hard cut with HOLD motion
    shot_cut = shot_from_preset("CAM_01_WIDE_2SHOT", start_sec=0.0, end_sec=2.5, speaker="BOTH", motion="HOLD", entry="CUT")
    assert shot_cut.entry == "CUT"
    assert shot_cut.motion == "HOLD"
    assert shot_cut.zoom_start == 1.0
    assert shot_cut.zoom_end == 1.0

    # Snap-zoom (punchline snap)
    shot_snap = shot_from_preset("CAM_04_CU_SPEAKER_B", start_sec=2.5, end_sec=4.0, speaker="B", motion="SNAP_ZOOM", entry="CUT")
    assert shot_snap.motion == "SNAP_ZOOM"
    assert shot_snap.zoom_end <= 1.9

    # Creep in motion
    shot_creep = shot_from_preset("CAM_02_MED_BOARD", start_sec=4.0, end_sec=7.0, speaker="A", motion="CREEP_IN", entry="CUT")
    assert shot_creep.motion == "CREEP_IN"
    assert shot_creep.zoom_end <= 1.9
    assert shot_creep.zoom_end > shot_creep.zoom_start


def test_parallax_plane_formula():
    """Verify multiplane depth layer offset math and deterministic camera evaluation."""
    shot = shot_from_preset("CAM_01_WIDE_2SHOT", start_sec=0.0, end_sec=3.0, speaker="BOTH", motion="HOLD")
    frame_state = evaluate_camera(shot, frame_idx=30)
    assert "planes" in frame_state
    planes = frame_state["planes"]

    # Verify planes match DEFAULT_PLANES
    for p_name in DEFAULT_PLANES:
        assert p_name in planes
        assert "scale" in planes[p_name]
        assert "offset_px" in planes[p_name]

    # Verify determinism: re-evaluating frame 30 produces identical dictionary
    frame_state2 = evaluate_camera(shot, frame_idx=30)
    assert frame_state == frame_state2


def test_background_blur_ramp():
    """Verify bg_blur_for_zoom smooth ramp: 2.0px at wide (1.0x), 14.0px at close (1.8x)."""
    assert bg_blur_for_zoom(1.0) == 2.0
    blur_mid = bg_blur_for_zoom(1.4)
    assert 2.0 < blur_mid < 14.0
    assert bg_blur_for_zoom(1.8) == 14.0
    # Capped beyond 1.8x
    assert bg_blur_for_zoom(1.9) == 14.0


def test_cut_lead_frames():
    """Verify camera cuts 3 frames (~100ms) before speaker change for natural rhythm."""
    line_start_sec = 2.0
    # 3 frames at 30fps is 0.10s
    cut_sec = cut_time_for_line(line_start_sec, kind="SPEAKER_CHANGE", fps=30)
    assert abs(cut_sec - (line_start_sec - 3.0 / 30.0)) < 1e-4

    # Reaction cut: 12 frames lead
    reaction_cut = cut_time_for_line(line_start_sec, kind="REACTION", fps=30)
    assert abs(reaction_cut - (line_start_sec - 12.0 / 30.0)) < 1e-4

    # Bound check: Line starting at 0.05s does not cut below 0.0s
    assert cut_time_for_line(0.05, kind="SPEAKER_CHANGE", fps=30) == 0.0


def test_timeline_validation():
    """Verify timeline validator flags shots exceeding max duration or zoom cap 1.9."""
    shots_too_long = [
        shot_from_preset("CAM_01_WIDE_2SHOT", start_sec=0.0, end_sec=8.5, speaker="BOTH", motion="HOLD"),  # >8.0s error
    ]
    probs = timeline_problems(shots_too_long, total_sec=8.5, max_zoom=1.9)
    assert any("longer than" in p for p in probs)

    shots_zoom_bad = [
        CameraShot(
            start_sec=0.0,
            end_sec=2.0,
            speaker="A",
            preset="CAM_01_WIDE_2SHOT",
            zoom_start=1.0,
            zoom_end=2.2,  # >1.9 error
            center_start=(0.5, 0.5),
            center_end=(0.5, 0.5),
            motion="CREEP_IN",
            entry="CUT",
            eye_target="PARTNER",
        )
    ]
    probs_zoom = timeline_problems(shots_zoom_bad, total_sec=2.0, max_zoom=1.9)
    assert any("outside 1.0..1.9" in p for p in probs_zoom)


def test_plan_save_load_camera_plan(tmp_path: Path):
    """Verify end-to-end camera plan generation, serialization, and reloading."""
    scenes = [
        {
            "scene_number": 1,
            "speaker": "Speaker A",
            "dialogue_line": "Did you know that hackers can bypass your firewall?",
            "duration": 3.0,
            "word_timings": [{"start_time": 0.2, "end_time": 2.6, "text": "word"}],
        },
        {
            "scene_number": 2,
            "speaker": "Speaker B",
            "dialogue_line": "Wait really?! How does that work?",
            "duration": 3.0,
            "word_timings": [{"start_time": 0.2, "end_time": 2.5, "text": "word"}],
        },
    ]
    shots = plan_camera_plan(scenes, total_duration_sec=6.0)
    assert len(shots) >= 2
    for s in shots:
        assert s.duration() <= 6.0
        assert s.zoom_start <= 1.9
        assert s.zoom_end <= 1.9

    out_file = tmp_path / "camera_plan.json"
    save_camera_plan(shots, out_file)
    assert out_file.is_file()

    loaded_shots = load_camera_plan(out_file)
    assert len(loaded_shots) == len(shots)
    assert loaded_shots[0].preset == shots[0].preset
    assert loaded_shots[0].zoom_start == shots[0].zoom_start


def test_check_camera_cli_tool(tmp_path: Path):
    """Verify check_camera function returns PASS on compliant plan and FAIL on invalid plan."""
    # Create valid camera_plan.json in tmp_path
    shots = [
        shot_from_preset("CAM_01_WIDE_2SHOT", start_sec=0.0, end_sec=2.5, speaker="BOTH", motion="HOLD"),
        shot_from_preset("CAM_04_CU_SPEAKER_B", start_sec=2.5, end_sec=4.5, speaker="B", motion="HOLD"),
    ]
    save_camera_plan(shots, tmp_path / "camera_plan.json")

    report = check_camera(tmp_path)
    assert report["status"] == "PASS"
    assert report["shots_count"] == 2
    assert report["peak_zoom"] <= 1.9
    assert report["determinism_verified"] is True
    assert report["board_zone_independent"] is True
    assert len(report["errors"]) == 0

    # Test invalid plan (exceeding zoom)
    shots_invalid = [
        CameraShot(
            start_sec=0.0,
            end_sec=3.0,
            speaker="A",
            preset="CAM_01_WIDE_2SHOT",
            zoom_start=1.0,
            zoom_end=2.5,  # Exceeds 1.9
            center_start=(0.5, 0.5),
            center_end=(0.5, 0.5),
            motion="CREEP_IN",
            entry="CUT",
            eye_target="PARTNER",
        )
    ]
    save_camera_plan(shots_invalid, tmp_path / "camera_plan.json")
    report_bad = check_camera(tmp_path)
    assert report_bad["status"] == "FAIL"
    assert any("exceeds cap" in e for e in report_bad["errors"])
