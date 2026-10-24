"""
Purpose: Unit tests for automated layout and safe-zone bounding box checker.
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

from toonshorts.core.layout_checker import check_scene_html_layout, verify_video_layout
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
    # Must sit below top 15% (288 px)
    assert bz["top"] >= 287.5
    assert bz["bottom"] <= 810.0
    assert bz["left"] >= 0.0
    assert bz["right"] <= 1080.5

    # Check peak zoom state as well
    bz_peak = res["peak_measurements"]["boardZone"]
    assert bz_peak is not None
    assert bz_peak["top"] >= 287.5
    assert bz_peak["bottom"] <= 810.0


def test_layout_checker_detects_board_above_canvas_and_inside_safe_zone(tmp_path: Path):
    """Verifies that if a board element is placed above y=0 or inside top 288px, layout checker fails."""
    html = generate_whiteboard_html(
        title="Invalid Board Test",
        words=[{"text": "Faulty", "start_ms": 200}],
        duration_sec=3.0,
        enable_split_camera_zones=True,
    )
    # Inject bad top coordinate on board zone
    corrupted_html = html.replace("top: 288px;", "top: -150px;")
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
