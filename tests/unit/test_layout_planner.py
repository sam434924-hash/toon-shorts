"""
Unit tests for the board visual layout planning system:
1. Verifies 5 layout templates in data (hero, split, chain, stack, title-card).
2. Verifies all slots are strictly inside board zone (y: 288..808, x: 60..960) with valid padding and min_gap.
3. Verifies validation of scene layout blocks (max 3 elements, one hero per beat, valid slots).
4. Verifies lifecycle: slot reuse allowed when previous element exits, fails if undeclared collision.
5. Verifies declared overlap rules: allowed only as badge/label on card corner with layer order.
6. Verifies horizontal visual balance calculation (> 70% warning threshold).
"""

import pytest
from toonshorts.core.layout_planner import (
    DEFAULT_LAYOUT_TEMPLATES,
    BOARD_ZONE_BOTTOM,
    BOARD_ZONE_LEFT,
    BOARD_ZONE_RIGHT,
    BOARD_ZONE_TOP,
    compute_board_visual_balance,
    load_layout_templates,
    validate_layout_template_definition,
    validate_scene_layout,
)


def test_default_layout_templates_exist():
    """Confirms all 5 required layout templates are defined in data."""
    required = {"hero", "split", "chain", "stack", "title-card"}
    templates = load_layout_templates()
    assert required.issubset(set(templates.keys())), f"Missing templates: {required - set(templates.keys())}"


def test_all_template_slots_inside_board_zone():
    """All template slots must be strictly inside board zone (y: 288..808, x: 60..960) and satisfy min_gap."""
    templates = load_layout_templates()
    for name, tmpl in templates.items():
        errors = validate_layout_template_definition(name, tmpl)
        assert not errors, f"Template '{name}' failed validation: {errors}"
        assert tmpl["padding"] > 0
        assert tmpl["min_gap"] >= 16

        for s_name, box in tmpl["slots"].items():
            assert box["y"] >= BOARD_ZONE_TOP, f"{name}.{s_name} y={box['y']} < {BOARD_ZONE_TOP}"
            assert box["y"] + box["height"] <= BOARD_ZONE_BOTTOM, f"{name}.{s_name} bottom > {BOARD_ZONE_BOTTOM}"
            assert box["x"] >= BOARD_ZONE_LEFT, f"{name}.{s_name} x={box['x']} < {BOARD_ZONE_LEFT}"
            assert box["x"] + box["width"] <= BOARD_ZONE_RIGHT, f"{name}.{s_name} right > {BOARD_ZONE_RIGHT}"


def test_validate_scene_layout_valid():
    """Valid layout block with split template and single hero passes cleanly."""
    layout = {
        "template": "split",
        "hero": "padlock_hero",
        "elements": [
            {
                "id": "padlock_hero",
                "slot": "left",
                "is_hero": True,
                "enter_time": 0.5,
                "exit_time": 4.5,
            },
            {
                "id": "side_card",
                "slot": "right",
                "is_hero": False,
                "enter_time": 1.0,
                "exit_time": 4.5,
            },
        ],
    }
    errs = validate_scene_layout(layout, scene_duration=5.0, scene_number=1)
    assert not errs, f"Unexpected validation errors: {errs}"


def test_validate_scene_layout_max_three_elements():
    """Fails if more than 3 elements are visible on screen simultaneously."""
    layout = {
        "template": "stack",
        "hero": "el1",
        "elements": [
            {"id": "el1", "slot": "top", "is_hero": True, "enter_time": 0.0, "exit_time": 4.0},
            {"id": "el2", "slot": "mid", "is_hero": False, "enter_time": 0.5, "exit_time": 4.0},
            {"id": "el3", "slot": "bottom", "is_hero": False, "enter_time": 1.0, "exit_time": 4.0},
            {"id": "el4", "slot": "top", "is_hero": False, "enter_time": 1.5, "exit_time": 4.0},
        ],
    }
    errs = validate_scene_layout(layout, scene_duration=5.0, scene_number=1)
    assert any("More than 3 elements on screen at once" in e for e in errs)


def test_validate_scene_layout_one_hero_per_beat():
    """Fails if multiple hero elements are active at the same time."""
    layout = {
        "template": "split",
        "elements": [
            {"id": "hero1", "slot": "left", "is_hero": True, "enter_time": 0.0, "exit_time": 3.0},
            {"id": "hero2", "slot": "right", "is_hero": True, "enter_time": 1.5, "exit_time": 4.0},
        ],
    }
    errs = validate_scene_layout(layout, scene_duration=5.0, scene_number=1)
    assert any("Multiple hero elements visible at once" in e for e in errs)


def test_lifecycle_slot_reuse_allowed_when_sequenced():
    """Slot reuse is permitted when previous element exits before or as new element enters."""
    layout = {
        "template": "hero",
        "elements": [
            {"id": "first_visual", "slot": "hero", "is_hero": True, "enter_time": 0.0, "exit_time": 2.0},
            {"id": "second_visual", "slot": "hero", "is_hero": True, "enter_time": 2.0, "exit_time": 4.5},
        ],
    }
    errs = validate_scene_layout(layout, scene_duration=5.0, scene_number=1)
    assert not errs, f"Sequential slot reuse should pass without error, got: {errs}"


def test_lifecycle_slot_collision_fails():
    """Fails if two undeclared elements occupy the same slot simultaneously."""
    layout = {
        "template": "hero",
        "elements": [
            {"id": "el1", "slot": "hero", "is_hero": True, "enter_time": 0.5, "exit_time": 3.5},
            {"id": "el2", "slot": "hero", "is_hero": False, "enter_time": 2.0, "exit_time": 4.5},
        ],
    }
    errs = validate_scene_layout(layout, scene_duration=5.0, scene_number=1)
    assert any("collision without lifecycle exit" in e for e in errs)


def test_declared_overlap_corner_badge_passes():
    """Declared overlap as a corner badge with layer order is permitted."""
    layout = {
        "template": "hero",
        "hero": "card_visual",
        "elements": [
            {"id": "card_visual", "slot": "hero", "is_hero": True, "enter_time": 0.5, "exit_time": 4.5},
            {
                "id": "corner_badge",
                "slot": "hero",
                "is_hero": False,
                "enter_time": 1.0,
                "exit_time": 4.5,
                "overlap": {
                    "role": "badge",
                    "corner": "top_right",
                    "layer_order": 2,
                },
            },
        ],
    }
    errs = validate_scene_layout(layout, scene_duration=5.0, scene_number=1)
    assert not errs, f"Declared corner badge should pass, got: {errs}"


def test_declared_overlap_forbidden_role_fails():
    """Fails if declared overlap uses an unapproved role or lacks layer order."""
    layout = {
        "template": "hero",
        "elements": [
            {"id": "card", "slot": "hero", "enter_time": 0.5, "exit_time": 4.5},
            {
                "id": "other_full_shape",
                "slot": "hero",
                "enter_time": 1.0,
                "exit_time": 4.5,
                "overlap": {
                    "role": "full_diagram",  # forbidden
                    "corner": "top_right",
                    "layer_order": 2,
                },
            },
        ],
    }
    errs = validate_scene_layout(layout, scene_duration=5.0, scene_number=1)
    assert any("forbidden" in e for e in errs)


def test_balance_check():
    """Visual balance computes left/right ratios and detects imbalance over 70%."""
    # Balanced side by side
    boxes_balanced = [
        {"x": 100, "y": 300, "width": 300, "height": 300},
        {"x": 680, "y": 300, "width": 300, "height": 300},
    ]
    l_ratio, r_ratio, is_bal = compute_board_visual_balance(boxes_balanced)
    assert is_bal
    assert abs(l_ratio - 0.5) < 0.05

    # Heavy on left side (80% left, 20% right)
    boxes_imbalanced = [
        {"x": 100, "y": 300, "width": 400, "height": 400},  # area = 160,000
        {"x": 700, "y": 300, "width": 200, "height": 100},  # area = 20,000
    ]
    l_ratio, r_ratio, is_bal = compute_board_visual_balance(boxes_imbalanced)
    assert not is_bal
    assert l_ratio > 0.70
