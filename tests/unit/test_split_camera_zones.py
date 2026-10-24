"""
Purpose: Unit tests for split camera zones, bounding box containment, and safe zones.
Inputs: Scene manifests, speaker geometries, gestures, and camera configs.
Outputs: Assertion results for containment, independence, safe zone clearance.
Depends on: json, pytest, toonshorts.core.camera, toonshorts.core.config, toonshorts.plugins.render.animejs.layout
Used by: tests
Config keys: ENABLE_SPLIT_CAMERA_ZONES, SAFE_ZONE_BOTTOM_PX, SAFE_ZONE_RIGHT_BOUNDARY_PX, SAFE_ZONE_TOP_PX
Tests: tests/unit/test_split_camera_zones.py
"""

import json
from pathlib import Path
import pytest

from toonshorts.core import config
from toonshorts.core.camera import plan_split_camera_shots
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html
from toonshorts.plugins.render.animejs.layout import (
    adjust_stage_anchors_inward,
    compute_character_camera_framing,
    compute_speaker_bounding_box,
    verify_no_safe_zone_overlap,
    verify_speaker_in_character_zone,
)


def test_split_zone_geometry_and_safe_zones():
    """Verify that all split zones strictly clear YouTube Shorts safe zones."""
    board_zone = config.SPLIT_BOARD_ZONE
    char_zone = config.SPLIT_CHARACTER_ZONE
    sub_zone = config.SPLIT_SUBTITLE_ZONE

    top_limit = config.SAFE_ZONE_TOP_PX  # 288 px
    bottom_limit = config.SAFE_ZONE_BOTTOM_PX  # 1440 px
    right_limit = config.SAFE_ZONE_RIGHT_BOUNDARY_PX  # 960 px

    for name, zone in [("board", board_zone), ("character", char_zone), ("subtitle", sub_zone)]:
        left = zone["left"]
        right = zone["left"] + zone["width"]
        top = zone["top"]
        bottom = zone["top"] + zone["height"]

        assert top >= top_limit, f"{name} zone top ({top}) encroaches top safe zone ({top_limit})"
        assert bottom <= bottom_limit, f"{name} zone bottom ({bottom}) encroaches bottom safe zone ({bottom_limit})"
        assert right <= right_limit, f"{name} zone right ({right}) encroaches right safe zone ({right_limit})"
        assert left >= 0, f"{name} zone left ({left}) is out of frame"


def test_speaker_bounding_box_inside_character_zone_all_scenes():
    """For every scene and every speaker, verify bounding box is inside character zone and safe zones."""
    brief_path = Path("videos/octopus_facts_v2/scene.json")
    assert brief_path.exists(), "videos/octopus_facts_v2/scene.json must exist"

    with open(brief_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data.get("scenes", [])
    assert len(scenes) > 0, "No scenes found in brief"

    # Test both speakers (boy_b anchored left, girl_a anchored right) across all scenes and gestures
    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        gesture = scene.get("gesture", "idle")
        speaker = scene.get("speaker", "boy_b")

        # Test both left and right speaker slots
        for slot in ["left", "right"]:
            framing = compute_character_camera_framing(
                speaker_slot=slot,
                gesture=gesture,
                requested_zoom=1.35,
            )

            # 1. Assert zoom does not exceed 1.35
            assert framing["zoom"] <= 1.35, f"Scene {scene_num} {slot} zoom exceeded 1.35x"
            assert framing["zoom"] >= 1.0, f"Scene {scene_num} {slot} zoom is below 1.0x"

            # 2. Assert transformed bounding box is inside the character zone
            is_inside_zone = verify_speaker_in_character_zone(framing["transformed_bbox"])
            assert is_inside_zone, (
                f"Scene {scene_num} speaker {slot} (gesture: {gesture}) bounding box "
                f"{framing['transformed_bbox']} is outside character zone"
            )

            # 3. Assert screen bounding box stays clear of safe zones
            clear_of_safe_zones = verify_no_safe_zone_overlap(framing["screen_bbox"])
            assert clear_of_safe_zones, (
                f"Scene {scene_num} speaker {slot} screen bbox {framing['screen_bbox']} "
                f"overlaps YouTube Shorts safe zones"
            )


def test_speaker_gestures_bounding_box_fit():
    """Test all supported gestures for both speakers ensuring containment."""
    gestures = ["idle", "explain", "point", "open_hand", "nod", "head_tilt", "lean_speaker", "thumbs_up"]

    for slot in ["left", "right"]:
        for gesture in gestures:
            framing = compute_character_camera_framing(
                speaker_slot=slot,
                gesture=gesture,
                requested_zoom=1.35,
            )
            assert framing["zoom"] <= 1.35
            assert verify_speaker_in_character_zone(framing["transformed_bbox"])
            assert verify_no_safe_zone_overlap(framing["screen_bbox"])


def test_independent_camera_shots_board_and_character():
    """Assert board zoom does not move characters and character zoom does not move board."""
    word_timings = [
        {"word": "Hello", "start_time": 0.5, "end_time": 1.0},
        {"word": "World", "start_time": 1.2, "end_time": 2.2},
    ]
    visuals = [
        {"id": "card_1", "start_time": 2.5, "duration_ms": 1500},
    ]

    split_shots = plan_split_camera_shots(
        duration_sec=6.0,
        word_timings=word_timings,
        visuals=visuals,
        speaker_id="boy_b",
        speaker_slot="left",
    )

    assert "character" in split_shots
    assert "board" in split_shots

    char_shots = split_shots["character"]
    board_shots = split_shots["board"]

    # Character shots only target speaker or wide
    for s in char_shots:
        assert "board" not in s["to_target"]
        assert "board" not in s["from_target"]

    # Board shots only target board or wide
    for s in board_shots:
        assert "speaker" not in s["to_target"]
        assert "speaker" not in s["from_target"]

    # Minimum hold is at least 1.2s (1200ms)
    for s in char_shots:
        if s["from_target"] != "wide" and s["to_target"] == "wide":
            # Return move after hold
            prev = next(p for p in char_shots if p["to_target"] == s["from_target"])
            hold_duration = s["t_start"] - prev["t_end"]
            assert hold_duration >= 1200, f"Character hold duration {hold_duration}ms is less than 1.2s"


def test_zoom_clamping_and_inward_anchor_adjustment():
    """Verify zoom is clamped to max 1.35x and inward anchor adjustment when needed."""
    # Test zoom clamping
    framing = compute_character_camera_framing("left", requested_zoom=2.0)
    assert framing["zoom"] <= 1.35

    # Test inward adjustment function
    anchors = config.SPLIT_STAGE_ANCHORS
    adjusted = adjust_stage_anchors_inward("left", anchors, shift_px=25.0)
    assert adjusted["left"]["left"] == anchors["left"]["left"] + 25.0
    assert adjusted["left"]["width"] == anchors["left"]["width"] - 25.0

    adjusted_right = adjust_stage_anchors_inward("right", anchors, shift_px=25.0)
    assert adjusted_right["right"]["left"] == anchors["right"]["left"] - 25.0
    assert adjusted_right["right"]["width"] == anchors["right"]["width"] - 25.0


def test_flag_off_preserves_bit_exact_structure():
    """When ENABLE_SPLIT_CAMERA_ZONES is False, generated HTML uses Phase 4 layer markup."""
    html_off = generate_whiteboard_html(
        title="Test Flag Off",
        words=[{"text": "Test", "start_ms": 0, "end_ms": 1000}],
        duration_sec=3.0,
        enable_split_camera_zones=False,
    )

    assert '<body class="split-zones-active"' not in html_off
    assert 'class="split-zones-active"' not in html_off
    assert 'id="layer-deep-bg"' in html_off
    assert 'id="layer-board"' in html_off
    assert 'id="layer-subject"' in html_off
    assert 'id="layer-foreground"' in html_off
    assert 'id="zone-board"' not in html_off
    assert 'id="zone-character"' not in html_off


def test_flag_on_generates_split_zones_markup():
    """When ENABLE_SPLIT_CAMERA_ZONES is True, generated HTML uses independent zone markup."""
    html_on = generate_whiteboard_html(
        title="Test Flag On",
        words=[{"text": "Test", "start_ms": 0, "end_ms": 1000}],
        duration_sec=3.0,
        enable_split_camera_zones=True,
    )

    assert "split-zones-active" in html_on
    assert 'id="zone-board"' in html_on
    assert 'id="zone-character"' in html_on
    assert 'id="zone-subtitles"' in html_on
    assert 'id="board-camera-content"' in html_on
    assert 'id="character-camera-content"' in html_on
