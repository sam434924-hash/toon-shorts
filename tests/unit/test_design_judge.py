"""
Purpose: Unit tests for DesignJudge verifying checks that FAIL on bad fixtures:
         - Truncated card text fixture (FAILS text fit / overflow)
         - Truncated caption fixture (FAILS caption ".." truncation)
         - Short board with empty bottom fixture (FAILS empty space > 120px)
         - Amber-filled card fixture (FAILS amber card fill > 10% and accent share)
         - Text-box-only scene fixture (FAILS hero coverage < 40%)
         - Rainbow cards fixture (FAILS palette conformance / max 3 hues)
         - Tiny text fixture (FAILS min text height)
         - Cramped board fixture (FAILS board fill / whitespace)
         - Tiny character fixture (FAILS character-to-board height ratio)
         - Good/fixed scene fixture (PASSES all checks)
Inputs: Synthetic still images, HTML files, and scene metadata fixtures.
Outputs: Assertion validations for design judge rule enforcement.
Depends on: pytest, PIL, numpy, toonshorts.core.design_judge
Used by: Test suite
Config keys: None
Tests: tests/unit/test_design_judge.py
"""

from pathlib import Path
import pytest
import numpy as np
from PIL import Image, ImageDraw
from toonshorts.core.design_judge import DesignJudge, hex_to_rgb


@pytest.fixture
def base_canvas():
    """Generates a standard 1080x1920 still frame with deep purple wall and whiteboard."""
    img = Image.new("RGB", (1080, 1920), color=hex_to_rgb("#3D1F7A"))
    draw = ImageDraw.Draw(img)
    # Whiteboard outer: x: 60..1020, y: 230..1030 (h=800)
    draw.rectangle([60, 230, 1020, 1030], fill=hex_to_rgb("#3D1F7A"))
    # Inner canvas: x: 76..1004, y: 246..1014
    draw.rectangle([76, 246, 1004, 1014], fill=hex_to_rgb("#F7F4FF"))
    # Character area: x: 60..460, y: 1040..1530 (h=490)
    draw.rectangle([80, 1050, 440, 1530], fill=hex_to_rgb("#6D3FD0"))
    # Caption bubble: x: 500..1020, y: 1100..1480
    draw.rectangle([500, 1100, 1020, 1480], fill=hex_to_rgb("#1B1240"))
    # Floor line at y=1530
    draw.line([0, 1530, 1080, 1530], fill=hex_to_rgb("#3D1F7A"), width=6)
    return img


def test_fixture_truncated_card_text_fails(tmp_path, base_canvas):
    """Fixture with narrow 2-column card overflowing text must FAIL text fit check."""
    still_file = tmp_path / "truncated_card.png"
    base_canvas.save(still_file)

    scene_data = {
        "board_objects": [
            {
                "id": "bo_overflow",
                "type": "custom",
                "data": {
                    "label": "Passive Chat Card",
                    "svg": '<svg viewBox="0 0 860 410"><rect width="380" height="350"/><text font-size="64">PASSIVE CHAT EXTENDED WORKFLOW</text></svg>',
                },
            }
        ]
    }

    judge = DesignJudge()
    result = judge.judge_still(still_file, scene_data=scene_data)

    assert result.passed is False
    assert not result.checks["text_fit"].passed
    assert any("overflows" in iss or "all-caps" in iss for iss in result.issues)


def test_fixture_truncated_caption_fails(tmp_path, base_canvas):
    """Fixture with caption truncated by '..' or line-clamp must FAIL text fit check."""
    still_file = tmp_path / "truncated_caption.png"
    base_canvas.save(still_file)

    scene_data = {
        "dialogue_line": "Imagine asking an ..",
        "board_objects": [
            {
                "id": "bo_hero",
                "is_hero": True,
                "data": {"width": 800, "height": 380},
            }
        ],
    }

    html_file = tmp_path / "scene_1_still.html"
    html_file.write_text('<div id="speech-bubble-text" style="-webkit-line-clamp: 2;">Imagine asking an ..</div>', encoding="utf-8")

    judge = DesignJudge()
    result = judge.judge_still(still_file, scene_data=scene_data, html_path=html_file)

    assert result.passed is False
    assert not result.checks["text_fit"].passed
    assert any("ellipsis" in iss or "truncated" in iss for iss in result.issues)


def test_fixture_short_board_empty_bottom_fails(tmp_path):
    """Fixture with short board and empty space > 120px at bottom of safe area must FAIL empty space."""
    img = Image.new("RGB", (1080, 1920), color=hex_to_rgb("#3D1F7A"))
    draw = ImageDraw.Draw(img)
    # Short board y: 230..750 (h=520)
    draw.rectangle([60, 230, 1020, 750], fill=hex_to_rgb("#F7F4FF"))
    # Small character y: 750..1150
    draw.rectangle([80, 750, 440, 1150], fill=hex_to_rgb("#6D3FD0"))
    # Empty space from y=1150 to y=1535 (385px empty safe area!)

    still_file = tmp_path / "empty_bottom.png"
    img.save(still_file)

    judge = DesignJudge()
    result = judge.judge_still(still_file)

    assert result.passed is False
    assert not result.checks["empty_space"].passed
    assert any("Empty horizontal strip" in iss for iss in result.issues)


def test_fixture_amber_filled_card_fails(tmp_path, base_canvas):
    """Fixture where amber fills whole card (> 10% of board) must FAIL accent share."""
    still_file = tmp_path / "amber_card.png"
    base_canvas.save(still_file)

    scene_data = {
        "board_objects": [
            {
                "id": "bo_amber_card",
                "data": {
                    "label": "Full Amber Card",
                    "svg": '<svg viewBox="0 0 860 410"><rect width="840" height="350" fill="#FFC233"/></svg>',
                },
            }
        ]
    }

    judge = DesignJudge()
    result = judge.judge_still(still_file, scene_data=scene_data)

    assert result.passed is False
    assert not result.checks["accent_share"].passed
    assert any("Amber accent used as full card fill" in iss for iss in result.issues)


def test_fixture_textbox_only_scene_fails(tmp_path, base_canvas):
    """Fixture with grid of text boxes and no hero covering >= 40% of board must FAIL hero present."""
    still_file = tmp_path / "textbox_only.png"
    base_canvas.save(still_file)

    scene_data = {
        "board_objects": [
            {
                "id": "bo_tb1",
                "is_hero": False,
                "data": {"width": 300, "height": 100, "svg": '<svg viewBox="0 0 300 100"></svg>'},
            },
            {
                "id": "bo_tb2",
                "is_hero": False,
                "data": {"width": 300, "height": 100, "svg": '<svg viewBox="0 0 300 100"></svg>'},
            },
        ]
    }

    judge = DesignJudge()
    result = judge.judge_still(still_file, scene_data=scene_data)

    assert result.passed is False
    assert not result.checks["hero_present"].passed
    assert any("no dominant hero visual" in iss or "covers only" in iss for iss in result.issues)


def test_fixture_rainbow_cards_fails(tmp_path, base_canvas):
    """Fixture with 6 rainbow colored cards must FAIL palette conformance."""
    img = base_canvas
    draw = ImageDraw.Draw(img)
    colors = ["#22C55E", "#06B6D4", "#EC4899", "#F97316", "#A855F7", "#EAB308"]
    for i, col in enumerate(colors):
        y = 260 + i * 110
        draw.rectangle([100, y, 980, y + 90], fill=hex_to_rgb(col))

    still_file = tmp_path / "rainbow_cards.png"
    img.save(still_file)

    judge = DesignJudge()
    result = judge.judge_still(still_file)

    assert result.passed is False
    assert not result.checks["palette_conformance"].passed
    assert any("Off-palette" in iss or "distinct hues" in iss for iss in result.issues)


def test_fixture_tiny_text_fails(tmp_path, base_canvas):
    """Fixture with font-size < 48px must FAIL min text height check."""
    still_file = tmp_path / "tiny_text.png"
    base_canvas.save(still_file)

    scene_data = {
        "board_objects": [
            {
                "id": "bo_tiny",
                "data": {
                    "label": "Tiny text card",
                    "svg": '<svg><text font-size="24">Tiny text</text></svg>',
                },
            }
        ]
    }

    judge = DesignJudge()
    result = judge.judge_still(still_file, scene_data=scene_data)

    assert result.passed is False
    assert not result.checks["min_text_height"].passed
    assert any("font size 24px" in iss for iss in result.issues)


def test_fixture_cramped_board_fails(tmp_path, base_canvas):
    """Fixture where cards cover 92% of board (whitespace < 20%) must FAIL board fill ratio."""
    img = base_canvas
    draw = ImageDraw.Draw(img)
    draw.rectangle([80, 250, 1000, 1010], fill=hex_to_rgb("#3D1F7A"))

    still_file = tmp_path / "cramped_board.png"
    img.save(still_file)

    judge = DesignJudge()
    result = judge.judge_still(still_file)

    assert result.passed is False
    assert not result.checks["board_fill"].passed
    assert any("whitespace" in iss or "over-crowded" in iss for iss in result.issues)


def test_fixture_tiny_character_fails(tmp_path, base_canvas):
    """Fixture with character height 200px vs 800px board (25% < 55%) must FAIL character proportions."""
    still_file = tmp_path / "tiny_char.png"
    base_canvas.save(still_file)

    scene_data = {
        "character_bounds": {
            "height": 200.0,
            "bottom": 1500.0,
        }
    }

    judge = DesignJudge()
    result = judge.judge_still(still_file, scene_data=scene_data)

    assert result.passed is False
    assert not result.checks["character_proportions"].passed
    assert any("minimum is 55%" in iss for iss in result.issues)


def test_fixture_good_scene_passes(tmp_path, base_canvas):
    """Fixture conforming to all design rules must PASS."""
    img = base_canvas
    draw = ImageDraw.Draw(img)
    # Hero card (deep purple) covering ~50% of content
    draw.rectangle([100, 260, 980, 680], fill=hex_to_rgb("#3D1F7A"))
    # Accent highlight badge (amber, ~8% of board)
    draw.rectangle([140, 300, 480, 420], fill=hex_to_rgb("#FFB800"))
    # Supporting teal badge (meaning: verified)
    draw.rectangle([520, 300, 860, 420], fill=hex_to_rgb("#17B8A6"))

    still_file = tmp_path / "good_scene.png"
    img.save(still_file)

    scene_data = {
        "scene_number": 1,
        "dialogue_line": "Imagine asking an AI to plan your day.",
        "character_bounds": {
            "height": 480.0,
            "bottom": 1530.0,
        },
        "board_objects": [
            {
                "id": "bo_hero",
                "is_hero": True,
                "data": {
                    "label": "Hero Card",
                    "width": 840,
                    "height": 420,
                    "svg": '<svg viewBox="0 0 840 420"><rect width="840" height="420" fill="#3D1F7A"/><text font-size="64">Card Title</text><text font-size="48">Details</text></svg>',
                },
            }
        ],
    }

    judge = DesignJudge()
    result = judge.judge_still(still_file, scene_data=scene_data)

    assert result.passed is True
    assert len(result.issues) == 0
