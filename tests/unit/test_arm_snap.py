"""
Purpose: Unit tests for arm snap to visual targets, boundary clamping, and fallbacks.
Inputs: Target bounding box and shoulder joint screen coordinates.
Outputs: Snapped angle within [-75.0, -35.0] or fallback to -55.0.
Depends on: math, pytest
Used by: tests
Config keys: None
Tests: tests/unit/test_arm_snap.py
"""

import math
import pytest


def compute_arm_snap_angle(
    target_rect: dict | None,
    shoulder_screen: tuple[float, float],
    stage_w: int = 1080,
    stage_h: int = 1920,
    default_angle: float = -55.0,
    enabled: bool = True,
) -> float:
    """Python mirror of computeArmSnapAngle in gestures_fk.js."""
    if not enabled:
        return default_angle
    if not target_rect:
        return default_angle

    width = target_rect.get("width", 0.0)
    height = target_rect.get("height", 0.0)
    if width <= 0.0 or height <= 0.0:
        return default_angle

    left = target_rect.get("left", 0.0)
    top = target_rect.get("top", 0.0)
    right = target_rect.get("right", left + width)
    bottom = target_rect.get("bottom", top + height)

    if right < 0 or bottom < 0 or left > stage_w or top > stage_h:
        return default_angle

    tgt_x = left + width / 2.0
    tgt_y = top + height / 2.0

    sh_x, sh_y = shoulder_screen
    dx = tgt_x - sh_x
    dy = tgt_y - sh_y

    theta_deg = math.atan2(dy, abs(dx)) * (180.0 / math.pi)
    return max(-75.0, min(-35.0, theta_deg))


def test_arm_snap_fallback_missing_target():
    """Missing or None target falls back to default angle (-55.0)."""
    assert compute_arm_snap_angle(None, (210.0, 1130.0)) == -55.0


def test_arm_snap_fallback_zero_size():
    """Target with zero width or zero height falls back to default angle (-55.0)."""
    rect_zero_w = {"left": 200, "top": 300, "width": 0, "height": 100}
    rect_zero_h = {"left": 200, "top": 300, "width": 100, "height": 0}
    assert compute_arm_snap_angle(rect_zero_w, (210.0, 1130.0)) == -55.0
    assert compute_arm_snap_angle(rect_zero_h, (210.0, 1130.0)) == -55.0


def test_arm_snap_fallback_off_stage():
    """Target outside 1080x1920 stage boundaries falls back to default angle (-55.0)."""
    rect_off_left = {"left": -300, "top": 300, "width": 100, "height": 100, "right": -200, "bottom": 400}
    rect_off_top = {"left": 200, "top": -300, "width": 100, "height": 100, "right": 300, "bottom": -200}
    rect_off_right = {"left": 1200, "top": 300, "width": 100, "height": 100, "right": 1300, "bottom": 400}
    rect_off_bottom = {"left": 200, "top": 2100, "width": 100, "height": 100, "right": 300, "bottom": 2200}

    assert compute_arm_snap_angle(rect_off_left, (210.0, 1130.0)) == -55.0
    assert compute_arm_snap_angle(rect_off_top, (210.0, 1130.0)) == -55.0
    assert compute_arm_snap_angle(rect_off_right, (210.0, 1130.0)) == -55.0
    assert compute_arm_snap_angle(rect_off_bottom, (210.0, 1130.0)) == -55.0


def test_arm_snap_clamping_ranges():
    """Upper bound clamps to -75.0 (extreme high) and lower bound clamps to -35.0 (extreme low)."""
    # Target positioned far above
    rect_high = {"left": 210, "top": 0, "width": 10, "height": 10}
    ang_high = compute_arm_snap_angle(rect_high, (210.0, 1130.0))
    assert ang_high == -75.0

    # Target positioned level with shoulder
    rect_low = {"left": 600, "top": 1130, "width": 50, "height": 50}
    ang_low = compute_arm_snap_angle(rect_low, (210.0, 1130.0))
    assert ang_low == -35.0


def test_arm_snap_valid_target_elevation():
    """Valid target inside board area produces accurate, unclipped angle."""
    rect = {"left": 300, "top": 500, "width": 200, "height": 100}  # center: (400, 550)
    sh = (200.0, 1100.0)  # dx = 200, dy = -550 -> atan2(-550, 200) = -70.016 deg
    ang = compute_arm_snap_angle(rect, sh)
    assert -75.0 <= ang <= -35.0
    assert round(ang, 2) == -70.02


def test_arm_snap_config_disabled():
    """When enabled=False, always returns default fallback angle."""
    rect = {"left": 300, "top": 500, "width": 200, "height": 100}
    assert compute_arm_snap_angle(rect, (200.0, 1100.0), enabled=False) == -55.0
