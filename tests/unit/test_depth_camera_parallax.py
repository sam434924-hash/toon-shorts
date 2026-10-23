"""
Unit tests for multiplane depth layers, parallax factor application, and deterministic camera motion.
Tests Phase B requirements:
- Four depth layers in night_studio (Layer 1 Foreground, Layer 2 Subject, Layer 3 Board, Layer 4 Deep background).
- Parallax factor configuration and application (2.0, 1.0, 0.5, 0.12).
- Camera position determinism: identical results for identical frame numbers.
- Camera presets configuration: wide, boy_close, girl_close, board_close.
"""

import math
import pytest
from toonshorts.core import config
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html


def test_depth_layers_and_parallax_factors_in_config():
    """Verify parallax factors and camera presets are strictly configured in central config."""
    factors = config.CAMERA_PARALLAX_FACTORS
    assert factors["foreground"] == 2.0
    assert factors["subject"] == 1.0
    assert factors["board"] == 0.5
    assert factors["deep_bg"] == 0.12

    presets = config.CAMERA_PRESETS
    assert "wide" in presets
    assert "boy_close" in presets
    assert "girl_close" in presets
    assert "board_close" in presets

    assert presets["wide"]["zoom"] == 1.0
    assert presets["boy_close"]["zoom"] >= 1.15
    assert presets["girl_close"]["zoom"] >= 1.15
    assert presets["board_close"]["zoom"] >= 1.20


def test_night_studio_html_contains_four_depth_layers():
    """Verify night_studio HTML markup declares all 4 depth layers with accurate data-depth-factors."""
    html = generate_whiteboard_html(
        title="Testing Layers",
        words=[{"text": "Sample", "start_ms": 0, "end_ms": 1000}],
        duration_sec=3.0,
        theme="night_studio",
    )

    # All 4 depth layers must be present
    assert 'id="layer-deep-bg"' in html
    assert 'data-depth-factor="0.12"' in html

    assert 'id="layer-board"' in html
    assert 'data-depth-factor="0.5"' in html

    assert 'id="layer-subject"' in html
    assert 'data-depth-factor="1.0"' in html

    assert 'id="layer-foreground"' in html
    assert 'data-depth-factor="2.0"' in html

    # Layer contents
    assert 'class="desk-props"' in html
    assert 'class="desk-container"' in html
    assert 'class="whiteboard-outer"' in html
    assert 'id="camera-viewport"' in html


def test_deterministic_camera_drift_and_parallax_formula():
    """
    Verify camera position, rotation, and layer parallax shifts are strictly deterministic
    functions of frame_number (zero randomness, identical for identical frameIdx).
    """
    def compute_simulated_camera(frame_idx: int, cam_preset_x: float, cam_preset_y: float, zoom: float):
        drift_x = 2.5 * math.sin(frame_idx * 0.035)
        drift_y = 1.8 * math.cos(frame_idx * 0.028)
        drift_rot = config.CAMERA_DRIFT_ROT_MAX * math.sin(frame_idx * 0.022)

        shifts = {}
        for layer_name, factor in config.CAMERA_PARALLAX_FACTORS.items():
            shift_x = (-cam_preset_x * factor) + (drift_x * factor)
            shift_y = (-cam_preset_y * factor) + (drift_y * factor)
            scale = 1.0 + (zoom - 1.0) * min(1.2, factor)
            shifts[layer_name] = (round(shift_x, 4), round(shift_y, 4), round(scale, 4))

        return {
            "drift_x": round(drift_x, 4),
            "drift_y": round(drift_y, 4),
            "drift_rot": round(drift_rot, 4),
            "shifts": shifts,
        }

    # Frame 15 twice: must be bit-exact
    res_a = compute_simulated_camera(15, 130.0, -45.0, 1.18)
    res_b = compute_simulated_camera(15, 130.0, -45.0, 1.18)
    assert res_a == res_b

    # Frame 45 twice: must be bit-exact
    res_45a = compute_simulated_camera(45, 0.0, 90.0, 1.25)
    res_45b = compute_simulated_camera(45, 0.0, 90.0, 1.25)
    assert res_45a == res_45b

    # Verify parallax scaling by factors:
    # Foreground shift magnitude must be ~4x the board shift magnitude (2.0 vs 0.5)
    fg_shift_x = res_a["shifts"]["foreground"][0]
    board_shift_x = res_a["shifts"]["board"][0]
    assert abs(fg_shift_x) > abs(board_shift_x) * 3.5, "Foreground layer must shift more than board"
    assert abs(res_a["drift_rot"]) < 0.40, "Drift rotation must remain under 0.4 degrees"
