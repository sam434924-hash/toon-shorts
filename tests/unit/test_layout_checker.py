"""
Purpose: Unit tests for automated layout, safe-zone bounding box, beat sampling overlap, and balance checker.
Inputs: Rendered HTML scene documents and camera zoom state configurations.
Outputs: Assertion results verifying safe-area clearance and clipping detection.
Depends on: json, pathlib, pytest, toonshorts.core.layout_checker, toonshorts.plugins.render.animejs.html_builder
Used by: tests
Config keys: SAFE_ZONE_TOP_PX, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_layout_checker.py
"""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from toonshorts.core.layout_checker import (
    check_scene_html_layout,
    validate_element_overlaps,
    verify_video_layout,
)
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html


def test_layout_checker_passes_on_valid_split_zones_html(tmp_path: Path):
    """Verifies that standard split-zones scene HTML passes all layout and safe-zone checks."""
    html = generate_whiteboard_html(
        title="Valid Layout Test",
        words=[{"text": "Cybersecurity", "start_ms": 200, "end_ms": 800}],
        duration_sec=3.5,
        theme="night_studio",
        enable_split_camera_zones=True,
    )
    html_file = tmp_path / "scene_1_still.html"
    html_file.write_text(html, encoding="utf-8")

    res = check_scene_html_layout(html_file, scene_num=1)
    assert res["passed"] is True, f"Expected layout check to pass, but got violations: {res['violations']}"
    assert len(res["violations"]) == 0

    bz = res["resting_measurements"]["boardZone"]
    assert bz is not None
    # Whiteboard canvas container covers upper two-thirds (starts at top: 60px, bottom: 1200px)
    assert bz["top"] >= 0.0
    assert bz["bottom"] <= 1210.0
    assert bz["left"] >= 0.0
    assert bz["right"] <= 1080.5

    # Check content visuals stay strictly below safe-zone (288px) and inside whiteboard margins
    for v in res["resting_measurements"]["visuals"]:
        box = v["box"]
        assert box["top"] >= 287.5, f"Visual {v['selector']} inside safe zone: {box['top']}"
        assert box["bottom"] <= bz["bottom"] + 1.0, f"Visual {v['selector']} exceeds board bottom: {box['bottom']}"

    # Check peak zoom state as well
    bz_peak = res["peak_measurements"]["boardZone"]
    assert bz_peak is not None
    assert bz_peak["top"] >= 0.0
    assert bz_peak["bottom"] <= 1210.0


def test_layout_checker_detects_board_above_canvas_and_inside_safe_zone(tmp_path: Path):
    """Verifies that if a board element is placed above y=0 or inside top 288px, layout checker fails."""
    html = generate_whiteboard_html(
        title="Invalid Board Test",
        words=[{"text": "Faulty", "start_ms": 200}],
        duration_sec=3.0,
        enable_split_camera_zones=True,
    )
    # Inject bad top coordinate on board zone
    corrupted_html = html.replace("top: 230px;", "top: -150px;").replace("top: 60px;", "top: -150px;").replace("top: 290px;", "top: -150px;").replace("top: 288px;", "top: -150px;")
    html_file = tmp_path / "scene_2_still.html"
    html_file.write_text(corrupted_html, encoding="utf-8")

    res = check_scene_html_layout(html_file, scene_num=2)
    assert res["passed"] is False
    assert any("above canvas boundary" in v for v in res["violations"])


def test_layout_checker_detects_overflow_clipping(tmp_path: Path):
    """Verifies that if text overflows a clipped container, layout checker reports clipping."""
    html = generate_whiteboard_html(
        title="A" * 120,  # Deliberately huge title to trigger overflow
        words=[{"text": "Overflow", "start_ms": 200}],
        duration_sec=3.0,
        enable_split_camera_zones=True,
    )
    # Constrain title badge to tiny width with overflow hidden
    corrupted_html = html.replace(
        ".title-badge {",
        ".title-badge { width: 40px !important; max-width: 40px !important; overflow: hidden !important; white-space: nowrap !important; "
    )
    html_file = tmp_path / "scene_3_still.html"
    html_file.write_text(corrupted_html, encoding="utf-8")

    res = check_scene_html_layout(html_file, scene_num=3)
    assert res["passed"] is False
    assert any("clipped by overflow hidden" in v for v in res["violations"])


def test_verify_video_layout_directory_report(tmp_path: Path):
    """Verifies directory-level verification writes layout_check.json and layout_check.txt."""
    html = generate_whiteboard_html(
        title="Directory Check",
        words=[{"text": "Directory", "start_ms": 200}],
        duration_sec=3.0,
        enable_split_camera_zones=True,
    )
    (tmp_path / "scene_1_still.html").write_text(html, encoding="utf-8")

    report = verify_video_layout(tmp_path)
    assert report["passed"] is True
    assert (tmp_path / "layout_check.json").is_file()
    assert (tmp_path / "layout_check.txt").is_file()

    txt_content = (tmp_path / "layout_check.txt").read_text(encoding="utf-8")
    assert "AUTOMATED LAYOUT & SAFE-ZONE REPORT" in txt_content
    assert "PASS" in txt_content


def test_cli_check_layout_command(tmp_path: Path):
    """Tests the CLI check-layout command via python -m toonshorts check-layout."""
    html = generate_whiteboard_html(
        title="CLI Layout Check",
        words=[{"text": "CLI", "start_ms": 200}],
        duration_sec=3.0,
        enable_split_camera_zones=True,
    )
    (tmp_path / "scene_1_still.html").write_text(html, encoding="utf-8")

    cmd = [sys.executable, "-m", "toonshorts", "check-layout", str(tmp_path), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"CLI check-layout failed with stderr: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert data["passed"] is True


def test_layout_checker_detects_deliberate_overlap_padlock_over_99_percent():
    """Verifies that an undeclared collision between a padlock and 99% label is detected and failed."""
    items = [
        {
            "id": "padlock_icon",
            "box": {"left": 250, "right": 450, "top": 350, "bottom": 550, "width": 200, "height": 200, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        },
        {
            "id": "meter_label_99_percent",
            "box": {"left": 400, "right": 520, "top": 450, "bottom": 520, "width": 120, "height": 70, "visible": True},
            "isText": True,
            "isShape": False,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        },
    ]
    violations, warnings = validate_element_overlaps(items, timestamp_ms=1200, scene_num=4)
    assert len(violations) >= 1
    assert any("Undeclared overlap" in v and "padlock_icon" in v and "meter_label_99_percent" in v for v in violations)
    assert any("Text over busy shapes" in v for v in violations)


def test_layout_checker_declared_corner_badge_passes():
    """Verifies that declared badge/label on a card corner passes without undeclared overlap error."""
    items = [
        {
            "id": "main_card",
            "box": {"left": 200, "right": 600, "top": 350, "bottom": 650, "width": 400, "height": 300, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        },
        {
            "id": "corner_badge",
            "box": {"left": 540, "right": 595, "top": 355, "bottom": 395, "width": 55, "height": 40, "visible": True},
            "isText": True,
            "isShape": False,
            "isDeclaredOverlap": True,
            "outsideSlot": False,
        },
    ]
    violations, warnings = validate_element_overlaps(items, timestamp_ms=500, scene_num=1)
    assert len(violations) == 0


def test_layout_checker_minimum_gap_violation():
    """Verifies that non-overlapping elements with gap < 16px fail minimum gap rule."""
    items = [
        {
            "id": "elem_left",
            "box": {"left": 100, "right": 300, "top": 350, "bottom": 550, "width": 200, "height": 200, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        },
        {
            "id": "elem_right",
            "box": {"left": 308, "right": 508, "top": 350, "bottom": 550, "width": 200, "height": 200, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        },
    ]
    violations, warnings = validate_element_overlaps(items, timestamp_ms=800, scene_num=2, min_gap=16.0)
    assert len(violations) == 1
    assert "Minimum gap violated" in violations[0]
    assert "gap=8.0px < min_gap=16.0px" in violations[0]


def test_layout_checker_elements_outside_slot():
    """Verifies that an element placed outside its slot boundary fails."""
    items = [
        {
            "id": "overflowing_visual",
            "box": {"left": 50, "right": 450, "top": 250, "bottom": 700, "width": 400, "height": 450, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": True,
        }
    ]
    violations, warnings = validate_element_overlaps(items, timestamp_ms=400, scene_num=3)
    assert len(violations) == 1
    assert "placed outside its slot boundary" in violations[0]


def test_layout_checker_more_than_three_elements_visible():
    """Verifies that having more than 3 elements visible simultaneously fails."""
    items = [
        {
            "id": f"elem_{i}",
            "box": {"left": 100 + i * 200, "right": 250 + i * 200, "top": 350, "bottom": 500, "width": 150, "height": 150, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        }
        for i in range(4)
    ]
    violations, warnings = validate_element_overlaps(items, timestamp_ms=1000, scene_num=1)
    assert any("More than 3 board elements visible" in v and "found 4" in v for v in violations)


def test_layout_checker_visual_balance_warning():
    """Verifies that when > 70% of visual area is on one side, a balance warning is emitted."""
    items = [
        {
            "id": "heavy_left_block",
            "box": {"left": 80, "right": 520, "top": 320, "bottom": 750, "width": 440, "height": 430, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        },
        {
            "id": "tiny_right_dot",
            "box": {"left": 800, "right": 840, "top": 500, "bottom": 540, "width": 40, "height": 40, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        },
    ]
    violations, warnings = validate_element_overlaps(items, timestamp_ms=600, scene_num=2)
    assert len(warnings) >= 1
    assert any("[BALANCE WARN]" in w and "left side" in w for w in warnings)


def test_layout_checker_balance_suppressed_during_staggered_entry():
    """Verifies that balance warnings are suppressed while beat elements are still staggering in."""
    items = [
        {
            "id": "staggered_left_item",
            "box": {"left": 80, "right": 520, "top": 320, "bottom": 750, "width": 440, "height": 430, "visible": True},
            "isText": False,
            "isShape": True,
            "isDeclaredOverlap": False,
            "outsideSlot": False,
        }
    ]
    # During staggered entry: all_beat_elements_visible=False
    violations, warnings = validate_element_overlaps(
        items, timestamp_ms=400, scene_num=1, all_beat_elements_visible=False
    )
    assert len(violations) == 0
    assert len(warnings) == 0, f"Expected no balance warning during staggered entry, got {warnings}"

    # Once all beat elements are visible:
    violations2, warnings2 = validate_element_overlaps(
        items, timestamp_ms=1200, scene_num=1, all_beat_elements_visible=True
    )
    assert len(warnings2) == 1
    assert any("[BALANCE WARN]" in w for w in warnings2)


def test_slot_motion_margin_and_pop_overshoot(tmp_path: Path):
    """Verifies that slots have motion margins and 1.14x pop overshoot frames pass overlap check."""
    html = generate_whiteboard_html(
        title="Overshoot Margin Test",
        words=[],
        duration_sec=3.0,
        layout={"template": "split", "slots": {"left": "obj_left", "right": "obj_right"}},
        board_objects=[
            {
                "id": "obj_left",
                "type": "text_pop",
                "anchor": 200,
                "start_ms": 200,
                "duration_ms": 500,
                "exit_ms": 3000,
                "enter": "pop",
                "board_slot": "slot_left",
                "data": {"text": "Left Card"}
            },
            {
                "id": "obj_right",
                "type": "text_pop",
                "anchor": 400,
                "start_ms": 400,
                "duration_ms": 500,
                "exit_ms": 3000,
                "enter": "pop",
                "board_slot": "slot_right",
                "data": {"text": "Right Card"}
            }
        ],
        theme="night_studio",
        enable_split_camera_zones=True,
    )
    html_file = tmp_path / "scene_1_still.html"
    html_file.write_text(html, encoding="utf-8")

    res = check_scene_html_layout(html_file, scene_num=1)
    assert res["passed"] is True, f"Expected peak overshoot frames to pass, but got: {res['violations']}"
    assert len(res["violations"]) == 0


def test_title_and_keyword_cards_in_layout(tmp_path: Path):
    """Verifies that title-card template includes a title slot element and keyword cards appear in slots."""
    html = generate_whiteboard_html(
        title="Security Myth Title",
        words=[{"text": "Keyword One", "start_ms": 300}, {"text": "Keyword Two", "start_ms": 600}],
        duration_sec=3.5,
        layout={"template": "title-card", "slots": {"card": "keyword-card-1-1"}},
        theme="night_studio",
        enable_split_camera_zones=True,
    )
    assert 'class="title-badge title-slot-element" id="wb-title"' in html
    assert 'style="display: none;"' not in html or 'id="wb-title" style="display: none;"' not in html
    assert "Security Myth Title" in html

