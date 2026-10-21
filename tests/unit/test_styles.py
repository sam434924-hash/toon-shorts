"""Tests for style preset configuration loading and schema validation."""

import pytest
from toonshorts.cli import load_style_preset
from toonshorts import config


def test_load_all_presets():
    expected_styles = ["stickman", "crayon", "paper_cutout", "pixel_art", "chalkboard"]
    for style in expected_styles:
        preset = load_style_preset(style)
        assert preset["name"] == style
        assert "image_prompt_prefix" in preset
        assert "color_palette" in preset
        assert "caption" in preset
        assert "pacing" in preset
        assert "avoid" in preset
        assert isinstance(preset["avoid"], list)
        assert len(preset["avoid"]) > 0


def test_missing_style_preset_error():
    with pytest.raises(FileNotFoundError):
        load_style_preset("non_existent_retro_synthwave")
