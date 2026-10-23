"""
Purpose: Unit tests for purposeful camera shot planner, config validation, and mathematical purity.
Inputs: Scene durations, cue timings, camera configurations, and seek points.
Outputs: Verified boundary clamping, minimum hold enforcement, cue lead-in, and timeline saving.
Depends on: pytest, toonshorts.core.camera
Used by: tests
Config keys: None
Tests: tests/unit/test_camera_shot_planner.py
"""

import math
from pathlib import Path
import pytest

from toonshorts.core.camera import (
    ALLOWED_EASING,
    DEFAULT_CAMERA_CONFIG,
    ease_in_out_cubic,
    format_camera_timeline,
    load_camera_config_for_style,
    plan_scene_camera_shots,
    save_camera_timelines,
    validate_camera_config,
)


def test_camera_config_validation_success():
    """Valid config with all allowed keys and valid ranges passes cleanly."""
    valid_cfg = {
        "mode": "purposeful_only",
        "continuous_drift": False,
        "transition_duration_ms": 350,
        "easing": "easeInOutCubic",
        "lead_ms": 130,
        "min_hold_ms": 1000,
        "target_move_interval_s": [3, 6],
    }
    validated = validate_camera_config(valid_cfg)
    assert validated["mode"] == "purposeful_only"
    assert validated["continuous_drift"] is False
    assert validated["transition_duration_ms"] == 350
    assert validated["easing"] == "easeInOutCubic"
    assert validated["lead_ms"] == 130
    assert validated["min_hold_ms"] == 1000
    assert validated["target_move_interval_s"] == [3.0, 6.0]


def test_camera_config_validation_transition_duration_bounds():
    """transition_duration_ms must be between 150 and 800 ms."""
    # Too short
    with pytest.raises(ValueError, match="transition_duration_ms"):
        validate_camera_config({"transition_duration_ms": 149})

    # Too long
    with pytest.raises(ValueError, match="transition_duration_ms"):
        validate_camera_config({"transition_duration_ms": 801})

    # Boundaries pass
    assert validate_camera_config({"transition_duration_ms": 150})["transition_duration_ms"] == 150
    assert validate_camera_config({"transition_duration_ms": 800})["transition_duration_ms"] == 800


def test_camera_config_validation_unknown_keys_rejected():
    """Unknown keys in camera config must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Unknown camera config keys rejected"):
        validate_camera_config({"unknown_key": "bad_value", "random_flag": 123})


def test_camera_config_validation_continuous_drift_must_be_false():
    """continuous_drift must be False for now."""
    with pytest.raises(ValueError, match="continuous_drift must be False"):
        validate_camera_config({"continuous_drift": True})


def test_camera_config_validation_easing_allow_list():
    """Easing must come from fixed allow-list."""
    for easing in ALLOWED_EASING:
        cfg = validate_camera_config({"easing": easing})
        assert cfg["easing"] == easing

    with pytest.raises(ValueError, match="rejected"):
        validate_camera_config({"easing": "elasticEaseOut"})


def test_style_json_camera_configs_are_valid():
    """Both whiteboard.json and night_studio.json must have valid camera configs."""
    wb_cfg = load_camera_config_for_style("whiteboard")
    assert wb_cfg is not None
    assert wb_cfg["mode"] == "purposeful_only"
    assert wb_cfg["continuous_drift"] is False
    assert wb_cfg["transition_duration_ms"] == 350

    ns_cfg = load_camera_config_for_style("night_studio")
    assert ns_cfg is not None
    assert ns_cfg["mode"] == "purposeful_only"
    assert ns_cfg["continuous_drift"] is False
    assert ns_cfg["transition_duration_ms"] == 350


def test_ease_in_out_cubic_monotonic_and_no_overshoot():
    """easeInOutCubic must start at 0.0, end at 1.0, and never overshoot."""
    assert ease_in_out_cubic(0.0) == 0.0
    assert ease_in_out_cubic(1.0) == 1.0
    assert ease_in_out_cubic(0.5) == 0.5

    samples = [ease_in_out_cubic(i / 1000.0) for i in range(1001)]
    assert min(samples) == 0.0
    assert max(samples) == 1.0
    # Strictly monotonically non-decreasing
    for i in range(len(samples) - 1):
        assert samples[i] <= samples[i + 1]


def test_scene_with_no_cues_stays_on_wide_locked():
    """Scenes with no speech and no visuals stay on wide, locked (zero shots returned)."""
    shots = plan_scene_camera_shots(duration_sec=4.0, word_timings=[], visuals=[])
    assert shots == []

    timeline = format_camera_timeline(shots, duration_sec=4.0, scene_number=1)
    assert "LOCKED on 'wide'" in timeline
    assert "0 camera moves" in timeline


def test_shot_planner_lead_time_rule():
    """Shot move starts lead_ms before the cue."""
    lead_ms = 130
    trans_dur = 350
    cue_time_ms = 1000
    wts = [{"word": "hello", "start_time": cue_time_ms / 1000.0, "end_time": (cue_time_ms + 400) / 1000.0}]

    shots = plan_scene_camera_shots(
        duration_sec=4.0,
        word_timings=wts,
        visuals=[],
        speaker_id="boy_b",
        speaker_slot="left",
    )
    assert len(shots) >= 1
    first_shot = shots[0]
    assert first_shot["from_target"] == "wide"
    assert first_shot["to_target"] == "speaker_boy_b"
    assert first_shot["t_start"] == cue_time_ms - lead_ms  # 870ms
    assert first_shot["t_end"] == (cue_time_ms - lead_ms) + trans_dur  # 1220ms


def test_shot_planner_skips_moves_too_close_for_min_hold():
    """If two cues are too close to satisfy min_hold_ms, the second move is skipped."""
    min_hold = 1000
    trans_dur = 350
    lead_ms = 130

    # First cue at 1000ms -> move ends at 870 + 350 = 1220ms. Must hold until 2220ms.
    # Second cue at 1500ms -> desired move start at 1370ms < 2220ms. MUST BE SKIPPED.
    wts = [{"word": "first", "start_time": 1.0, "end_time": 1.3}]
    vis = [{"id": "vis1", "start_ms": 1500, "duration_ms": 600}]

    shots = plan_scene_camera_shots(
        duration_sec=5.0,
        word_timings=wts,
        visuals=vis,
        speaker_id="presenter",
    )
    # The visual move at 1500ms should be skipped because min_hold is violated
    assert len(shots) == 1
    assert shots[0]["to_target"] == "speaker_presenter"


def test_shot_planner_clamping_to_scene_bounds():
    """Moves cannot start before t=0 or extend past total scene duration."""
    wts = [{"word": "immediate", "start_time": 0.05, "end_time": 0.3}]
    shots = plan_scene_camera_shots(duration_sec=2.0, word_timings=wts, speaker_id="boy_b")

    assert len(shots) >= 1
    # Move start clamped to >= 0
    assert shots[0]["t_start"] >= 0
    # Move end clamped to <= 2000ms
    for s in shots:
        assert s["t_start"] >= 0
        assert s["t_end"] <= 2000


def test_camera_timeline_formatting_and_save(tmp_path: Path):
    """Timeline formatting produces clear human-readable output and saves to baseline/phase4b/."""
    shots = [
        {"t_start": 870, "t_end": 1220, "from_target": "wide", "to_target": "speaker_boy_b"},
        {"t_start": 2370, "t_end": 2720, "from_target": "speaker_boy_b", "to_target": "board_close"},
    ]
    txt = format_camera_timeline(shots, duration_sec=4.8, scene_number=1)
    assert "Scene 1 Camera Shot Timeline" in txt
    assert "LOCKED on 'wide'" in txt
    assert "MOVE: 'wide' -> 'speaker_boy_b'" in txt
    assert "MOVE: 'speaker_boy_b' -> 'board_close'" in txt
    assert "Summary: 2 moves" in txt

    summary_file = save_camera_timelines({1: txt}, output_dir=tmp_path)
    assert summary_file.is_file()
    assert "Phase 4B" in summary_file.read_text(encoding="utf-8")
    assert (tmp_path / "scene_1_camera_timeline.txt").is_file()


def test_browser_camera_engine_pure_function_of_time(tmp_path: Path):
    """
    Verifies that camera_engine.js in Playwright is a 100% pure function of time:
    Seeking order does not matter (backward seek matches forward seek bit-for-bit),
    continuous drift is zero in purposeful mode, and transforms stay within stage bounds.
    """
    from playwright.sync_api import sync_playwright
    from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html

    wts = [{"word": "three", "start_time": 1.0, "end_time": 1.4}]
    vis = [{"dom_id": "test_vis", "start_ms": 2500, "duration_ms": 800}]
    html = generate_whiteboard_html(
        title="Purity Test",
        words=[{"text": "three", "start_ms": 1000}],
        duration_sec=4.0,
        word_timings=wts,
        visuals=vis,
        theme="night_studio",
    )
    test_html_file = tmp_path / "test_purity.html"
    test_html_file.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(test_html_file.resolve().as_uri())

        # Forward seek: t=2000, then t=500
        state_2000_a = page.evaluate("computeCameraState(2000, 60)")
        state_500 = page.evaluate("computeCameraState(500, 15)")
        # Backward seek to t=2000: must be bit-for-bit identical!
        state_2000_b = page.evaluate("computeCameraState(2000, 60)")

        assert state_2000_a["camX"] == state_2000_b["camX"]
        assert state_2000_a["camY"] == state_2000_b["camY"]
        assert state_2000_a["camZoom"] == state_2000_b["camZoom"]
        assert state_2000_a["focus"] == state_2000_b["focus"]
        assert state_2000_a["driftX"] == 0.0
        assert state_2000_a["driftY"] == 0.0
        assert state_2000_a["driftRot"] == 0.0

        # Assert camera stays safely bounded inside stage
        assert -150.0 <= state_2000_a["camX"] <= 150.0
        assert -100.0 <= state_2000_a["camY"] <= 120.0
        assert 1.0 <= state_2000_a["camZoom"] <= 1.35
        browser.close()
