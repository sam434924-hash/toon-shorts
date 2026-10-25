"""
Purpose: Comprehensive unit tests for camera shot language, Appendix A implementation, visibility validation, and check-camera CLI.
Inputs: Synthetic scenes, camera shot presets, and camera plan files.
Outputs: Assertion results for presets, parallax, transitions, zoom cap, visibility checks, and validation.
Depends on: pytest, json, pathlib, toonshorts.core.camera_shots, toonshorts.core.camera, toonshorts.core.config
Used by: tests
Config keys: CAMERA_CHARACTER_MAX_ZOOM, CAMERA_SNAP_MAX_ZOOM, CAMERA_BOARD_MAX_ZOOM
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
    verify_camera_plan_visibility,
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
    """Verify hard cuts (0s), snap-zooms (6-8 frames), and creep pushes respect zoom cap 1.35 / 1.45."""
    # 0s Hard cut with HOLD motion
    shot_cut = shot_from_preset("CAM_01_WIDE_2SHOT", start_sec=0.0, end_sec=2.5, speaker="BOTH", motion="HOLD", entry="CUT")
    assert shot_cut.entry == "CUT"
    assert shot_cut.motion == "HOLD"
    assert shot_cut.zoom_start == 1.0
    assert shot_cut.zoom_end == 1.0

    # Snap-zoom (punchline snap, <= 1.5s reaction beat)
    shot_snap = shot_from_preset("CAM_04_CU_SPEAKER_B", start_sec=2.5, end_sec=3.8, speaker="B", motion="SNAP_ZOOM", entry="CUT")
    assert shot_snap.motion == "SNAP_ZOOM"
    assert shot_snap.zoom_end <= 1.45

    # Creep in motion
    shot_creep = shot_from_preset("CAM_02_MED_BOARD", start_sec=3.8, end_sec=6.5, speaker="A", motion="CREEP_IN", entry="CUT")
    assert shot_creep.motion == "CREEP_IN"
    assert shot_creep.zoom_end <= 1.35
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
    """Verify timeline validator flags shots exceeding max duration or zoom cap 1.35."""
    shots_too_long = [
        shot_from_preset("CAM_01_WIDE_2SHOT", start_sec=0.0, end_sec=8.5, speaker="BOTH", motion="HOLD"),  # >8.0s error
    ]
    probs = timeline_problems(shots_too_long, total_sec=8.5, max_zoom=1.35)
    assert any("longer than" in p for p in probs)

    shots_zoom_bad = [
        CameraShot(
            start_sec=0.0,
            end_sec=2.0,
            speaker="A",
            preset="CAM_01_WIDE_2SHOT",
            zoom_start=1.0,
            zoom_end=1.8,  # >1.35 error
            center_start=(0.5, 0.5),
            center_end=(0.5, 0.5),
            motion="CREEP_IN",
            entry="CUT",
            eye_target="PARTNER",
        )
    ]
    probs_zoom = timeline_problems(shots_zoom_bad, total_sec=2.0, max_zoom=1.35)
    assert any("outside 1.0..1.35" in p for p in probs_zoom)


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
        assert s.zoom_start <= 1.45
        assert s.zoom_end <= 1.45

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
        shot_from_preset("CAM_04_CU_SPEAKER_B", start_sec=2.5, end_sec=3.8, speaker="B", motion="HOLD"),
    ]
    save_camera_plan(shots, tmp_path / "camera_plan.json")

    report = check_camera(tmp_path)
    assert report["status"] == "PASS"
    assert report["shots_count"] == 2
    assert report["peak_zoom"] <= 1.35
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
            zoom_end=2.5,  # Exceeds 1.35
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
    assert any("exceeds cap" in e or "zoom_cap_exceeded" in e for e in report_bad["errors"])


def test_visibility_check_passing_plan():
    """Verify visibility check passes when board >= 70% visible, speaker in frame, CU <= 1.5s."""
    scenes = [
        {
            "scene_number": 1,
            "speaker": "Speaker A",
            "duration": 3.8,
            "visuals": [{"id": "v1"}],
        },
        {
            "scene_number": 2,
            "speaker": "Speaker B",
            "duration": 4.0,
            "visuals": [{"id": "v2"}],
        },
    ]
    shots = [
        # Scene 1: Med board (0..3.8s) keeps board >= 70% visible and Character A inside
        shot_from_preset("CAM_02_MED_BOARD", start_sec=0.0, end_sec=3.8, speaker="A", motion="HOLD"),
        # Scene 2: Main shot Med board (3.8..6.5s)
        shot_from_preset("CAM_02_MED_BOARD", start_sec=3.8, end_sec=6.5, speaker="B", motion="HOLD"),
        # Scene 2: Short reaction CU (6.5..7.8s, duration 1.3s <= 1.5s)
        shot_from_preset("CAM_04_CU_SPEAKER_B", start_sec=6.5, end_sec=7.8, speaker="B", motion="SNAP_ZOOM"),
    ]
    errs = verify_camera_plan_visibility(shots, scenes=scenes)
    assert errs == [], f"Expected passing plan, got errors: {errs}"


def test_visibility_check_failing_cropped_board():
    """Verify visibility check flags board visibility < 70% in scenes using board."""
    scenes = [
        {
            "scene_number": 1,
            "speaker": "Speaker A",
            "duration": 4.0,
            "visuals": [{"id": "v1"}],
        }
    ]
    # Center shifted far right (0.90, 0.50) with zoom 1.35 crops the board below 70%
    bad_shot = CameraShot(
        start_sec=0.0,
        end_sec=4.0,
        speaker="A",
        preset="CAM_01_WIDE_2SHOT",
        zoom_start=1.35,
        zoom_end=1.35,
        center_start=(0.90, 0.50),
        center_end=(0.90, 0.50),
        motion="HOLD",
        entry="CUT",
        eye_target="BOARD",
    )
    errs = verify_camera_plan_visibility([bad_shot], scenes=scenes)
    assert any("board_visibility_under_70" in e for e in errs)
    assert any("Scene 1" in e for e in errs)


def test_visibility_check_failing_cropped_speaker():
    """Verify visibility check flags speaking character cropped by visible rectangle."""
    scenes = [
        {
            "scene_number": 1,
            "speaker": "Speaker B",  # Speaker B is at X: 570..840
            "duration": 3.0,
            "visuals": [],
        }
    ]
    # Camera centered far to the left (0.15, 0.50) at zoom 1.35 crops Speaker B
    bad_shot = CameraShot(
        start_sec=0.0,
        end_sec=3.0,
        speaker="B",
        preset="CAM_02_MED_BOARD",
        zoom_start=1.35,
        zoom_end=1.35,
        center_start=(0.15, 0.50),
        center_end=(0.15, 0.50),
        motion="HOLD",
        entry="CUT",
        eye_target="PARTNER",
    )
    errs = verify_camera_plan_visibility([bad_shot], scenes=scenes)
    assert any("speaking_character_cropped" in e for e in errs)
    assert any("Scene 1" in e for e in errs)


def test_visibility_check_failing_long_closeup():
    """Verify visibility check flags close-up shot with duration > 1.5s."""
    scenes = [
        {
            "scene_number": 1,
            "speaker": "Speaker B",
            "duration": 4.0,
            "visuals": [],
        }
    ]
    # CU shot lasting 2.2s (> 1.5s)
    bad_shot = shot_from_preset("CAM_04_CU_SPEAKER_B", start_sec=0.0, end_sec=2.2, speaker="B", motion="HOLD")
    errs = verify_camera_plan_visibility([bad_shot], scenes=scenes)
    assert any("closeup_duration_exceeded" in e for e in errs)
    assert any("Scene 1" in e for e in errs)


def test_visibility_check_speaker_name_formats():
    """Verify normalize_speaker handles 'Speaker A', 'girl_a', 'Speaker B', 'boy_b', and 'REACTION'."""
    scenes = [
        {"scene_number": 1, "speaker": "girl_a", "duration": 3.0, "visuals": []},
        {"scene_number": 2, "speaker": "boy_b", "duration": 3.0, "visuals": []},
    ]
    shots = [
        shot_from_preset("CAM_02_MED_BOARD", start_sec=0.0, end_sec=3.0, speaker="Speaker A", motion="HOLD"),
        shot_from_preset("CAM_02_MED_BOARD", start_sec=3.0, end_sec=6.0, speaker="Speaker B", motion="HOLD"),
    ]
    errs = verify_camera_plan_visibility(shots, scenes=scenes)
    assert errs == [], f"Expected clean pass for named speakers, got: {errs}"


def test_visibility_check_every_frame_motion_catches_violation():
    """Verify that camera visibility verifies every frame, catching mid-shot boundary excursions."""
    scenes = [
        {"scene_number": 1, "speaker": "Speaker A", "duration": 3.0, "visuals": [{"id": "v1"}]},
    ]
    # Center shifts from 0.48 (valid board) to 0.95 (cropped board) over the shot
    moving_shot = CameraShot(
        start_sec=0.0,
        end_sec=3.0,
        speaker="A",
        preset="CAM_01_WIDE_2SHOT",
        zoom_start=1.20,
        zoom_end=1.20,
        center_start=(0.48, 0.46),  # valid board at start
        center_end=(0.95, 0.46),    # crops board before end
        motion="CREEP_IN",
        entry="CUT",
        eye_target="BOARD",
    )
    errs = verify_camera_plan_visibility([moving_shot], scenes=scenes)
    assert any("board_visibility_under_70" in e for e in errs)
    assert any("Scene 1" in e for e in errs)


def test_visibility_check_single_reaction_exemption():
    """Verify that only a single short reaction shot is exempt from 70% board visibility per scene."""
    scenes = [
        {"scene_number": 1, "speaker": "A", "duration": 5.0, "visuals": [{"id": "v1"}]},
    ]
    # Two reaction shots in the same scene, both cropping board below 70%
    shot1 = CameraShot(
        start_sec=0.0, end_sec=2.0, speaker="A", preset="CAM_02_MED_BOARD",
        zoom_start=1.18, zoom_end=1.18, center_start=(0.48, 0.46), center_end=(0.48, 0.46),
    )
    # First reaction shot (exempt)
    rx1 = CameraShot(
        start_sec=2.0, end_sec=3.2, speaker="B", preset="CAM_06_ECU_REACTION",
        zoom_start=1.40, zoom_end=1.40, center_start=(0.90, 0.48), center_end=(0.90, 0.48),
        motion="SNAP_ZOOM",
    )
    # Second reaction shot (should FAIL because only one exemption allowed per scene)
    rx2 = CameraShot(
        start_sec=3.2, end_sec=4.5, speaker="B", preset="CAM_06_ECU_REACTION",
        zoom_start=1.40, zoom_end=1.40, center_start=(0.90, 0.48), center_end=(0.90, 0.48),
        motion="SNAP_ZOOM",
    )
    errs = verify_camera_plan_visibility([shot1, rx1, rx2], scenes=scenes)
    assert len([e for e in errs if "board_visibility_under_70" in e]) == 1
    assert any("time 3.20s" in e for e in errs)

