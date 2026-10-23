"""Unit tests for graphics plugins and inventory registration."""

import pytest
from toonshorts.inventory import get_installed_board_animations
from toonshorts.plugins.graphics import (
    list_graphics_plugins,
    get_graphics_plugin,
    KineticWordsPlugin,
    DrawSVGPlugin,
    OctopusVectorPlugin,
    HeartsPopPlugin,
    BlueBloodDropPlugin,
)


def test_graphics_plugins_discovery_and_inventory():
    """Verify graphics plugins are registered in inventory automatically."""
    plugins = list_graphics_plugins()
    assert "kinetic_words" in plugins
    assert "draw_svg" in plugins
    assert "octopus_vector" in plugins
    assert "hearts_pop" in plugins
    assert "blue_blood_drop" in plugins

    board_anims = get_installed_board_animations()
    assert "graphics_plugins" in board_anims
    for p in ["kinetic_words", "draw_svg", "octopus_vector", "hearts_pop", "blue_blood_drop"]:
        assert p in board_anims["graphics_plugins"]


def test_kinetic_words_render():
    """Verify kinetic words markup and highlight term."""
    out = KineticWordsPlugin.render(
        element_id="test-kw",
        text="True Blue Blood",
        highlight_term="Blue",
        highlight_color="#38bdf8",
        start_ms=500,
    )
    assert "test-kw" in out["html"]
    assert "color: #38bdf8" in out["html"]
    assert out["descriptor"]["start_ms"] == 500


def test_draw_svg_render():
    """Verify draw_svg generates stroke-dashoffset styles."""
    out = DrawSVGPlugin.render(
        element_id="test-draw",
        svg_paths=["M 0,0 L 100,100"],
        stroke_color="#38bdf8",
        start_ms=200,
    )
    assert "draw-path" in out["html"]
    assert "stroke-dashoffset" in out["css"]
    assert out["descriptor"]["path_count"] == 1


def test_octopus_vector_render():
    """Verify vector octopus produces head, 8 arms, and optional numbered badges."""
    out = OctopusVectorPlugin.render(
        element_id="test-octo",
        start_ms=300,
        show_numbers=True,
    )
    assert "arm-num-badge" in out["html"]
    assert out["descriptor"]["arm_count"] == 8
    assert out["descriptor"]["show_numbers"] is True


def test_hearts_pop_render():
    """Verify hearts pop generates 3 bouncy hearts."""
    out = HeartsPopPlugin.render(
        element_id="test-hearts",
        count=3,
        color="#ef4444",
        labels=["Systemic", "Gill 1", "Gill 2"],
    )
    assert "heart-item" in out["html"]
    assert out["descriptor"]["count"] == 3
    assert "Gill 1" in out["html"]


def test_blue_blood_drop_render():
    """Verify blue blood drop renders gradient and label."""
    out = BlueBloodDropPlugin.render(
        element_id="test-drop",
        label="Copper Hemocyanin",
    )
    assert "blue-drop-container" in out["html"]
    assert "Copper Hemocyanin" in out["html"]
