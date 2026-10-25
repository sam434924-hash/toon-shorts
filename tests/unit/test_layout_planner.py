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


def test_plan_scene_layout_rules():
    """Verifies automatic planner rules: 1 main=hero/title-card, 2=split, 3 seq=chain, list=stack."""
    from toonshorts.core.layout_planner import plan_scene_layout

    # 1 main visual in standard scene -> hero
    sc_hero = {
        "scene_number": 2,
        "dialogue_line": "This is the single core concept to remember.",
        "action": "points to single main concept",
        "visuals": [{"id": "single_vis", "trigger_word": "concept"}],
    }
    p_hero = plan_scene_layout(sc_hero, scene_duration=4.0)
    assert p_hero["template"] == "hero"
    assert p_hero["hero"] == "single_vis"
    assert "hero" in p_hero["slots"]

    # 1 main visual in scene 1 or title scene -> title-card
    sc_title = {
        "scene_number": 1,
        "dialogue_line": "Welcome to our cybersecurity guide.",
        "action": "shows title heading and icon",
        "visuals": [{"id": "title_elem", "trigger_word": "guide"}],
    }
    p_title = plan_scene_layout(sc_title, scene_duration=4.0)
    assert p_title["template"] == "title-card"
    assert "card" in p_title["slots"]

    # 2 visuals that compare -> split
    sc_split = {
        "scene_number": 3,
        "dialogue_line": "Compare strong passwords versus weak passwords.",
        "action": "comparing strong vs weak",
        "visuals": [
            {"id": "vis_strong", "trigger_word": "strong"},
            {"id": "vis_weak", "trigger_word": "weak"},
        ],
    }
    p_split = plan_scene_layout(sc_split, scene_duration=4.0)
    assert p_split["template"] == "split"
    assert p_split["slots"]["left"] == "vis_strong"
    assert p_split["slots"]["right"] == "vis_weak"

    # 3 in sequence -> chain
    sc_chain = {
        "scene_number": 4,
        "dialogue_line": "First shop, then reuse, then bank access.",
        "action": "explaining sequence of steps in attack chain",
        "visuals": [
            {"id": "step1", "trigger_word": "shop"},
            {"id": "step2", "trigger_word": "reuse"},
            {"id": "step3", "trigger_word": "bank"},
        ],
    }
    p_chain = plan_scene_layout(sc_chain, scene_duration=5.0)
    assert p_chain["template"] == "chain"
    assert p_chain["slots"]["step_1"] == "step1"
    assert p_chain["slots"]["step_2"] == "step2"
    assert p_chain["slots"]["step_3"] == "step3"

    # List -> stack
    sc_stack = {
        "scene_number": 5,
        "dialogue_line": "Here are the top three password rules to follow.",
        "action": "listing three rules in a stack",
        "visuals": [
            {"id": "rule1", "trigger_word": "first"},
            {"id": "rule2", "trigger_word": "second"},
            {"id": "rule3", "trigger_word": "third"},
        ],
    }
    p_stack = plan_scene_layout(sc_stack, scene_duration=5.0)
    assert p_stack["template"] == "stack"
    assert p_stack["slots"]["top"] == "rule1"
    assert p_stack["slots"]["mid"] == "rule2"
    assert p_stack["slots"]["bottom"] == "rule3"


def test_brand_new_script_with_no_layout_gets_valid_plan():
    """Verifies a brand new script with no layout gets a valid plan via the planner and passes validation."""
    from toonshorts.core.layout_planner import plan_script_layouts
    from toonshorts.core.validator import validate_plan
    from toonshorts.core.models import PlanValidationError

    raw_script = {
        "version": 2,
        "title": "Fresh Script Without Layout",
        "art_style": "night_studio",
        "emotional_arc": "suspenseful",
        "characters": [
            {"name": "Alice", "visual_description": "Friendly presenter"},
            {"name": "Bob", "visual_description": "Tech expert character"}
        ],
        "scenes": [
            {
                "scene_number": 1,
                "speaker": "Alice",
                "dialogue_line": "Do you know how movie hackers really smash keyboards?",
                "action": "questioning title myth",
                "pose": "idle",
                "layout": None,
                "visuals": [{"id": "vis1", "type": "custom", "trigger_word": "hackers"}],
                "cast": ["Alice", "Bob"]
            },
            {
                "scene_number": 2,
                "speaker": "Bob",
                "dialogue_line": "They test stolen credentials across multiple services.",
                "action": "explaining steps in attack chain",
                "pose": "idle",
                "layout": None,
                "visuals": [
                    {"id": "step_a", "type": "custom", "trigger_word": "test"},
                    {"id": "step_b", "type": "custom", "trigger_word": "stolen"},
                    {"id": "step_c", "type": "custom", "trigger_word": "services"}
                ],
                "cast": ["Alice", "Bob"]
            },
            {
                "scene_number": 3,
                "speaker": "Alice",
                "dialogue_line": "So a leak in one service breaches another service.",
                "action": "comparing forum leak vs email breach",
                "pose": "idle",
                "layout": None,
                "visuals": [
                    {"id": "leak_a", "type": "custom", "trigger_word": "leak"},
                    {"id": "leak_b", "type": "custom", "trigger_word": "breaches"}
                ],
                "cast": ["Alice", "Bob"]
            },
            {
                "scene_number": 4,
                "speaker": "Bob",
                "dialogue_line": "Always use unique passwords and turn on 2FA today!",
                "action": "punchline reminder",
                "pose": "laughing",
                "is_punchline": True,
                "layout": None,
                "visuals": [{"id": "shield_hero", "type": "custom", "trigger_word": "2FA"}],
                "cast": ["Alice", "Bob"]
            }
        ]
    }

    # Brand new script directly into validate_plan fails because scenes have no layout
    with pytest.raises(PlanValidationError, match="missing required layout block"):
        validate_plan(raw_script)

    # Planner automatically creates valid layouts
    planned = plan_script_layouts(raw_script)
    assert planned["scenes"][0]["layout"]["template"] == "title-card"
    assert planned["scenes"][1]["layout"]["template"] == "chain"
    assert planned["scenes"][2]["layout"]["template"] == "split"
    assert planned["scenes"][3]["layout"]["template"] == "hero"

    # Now passes validation
    validated_plan = validate_plan(planned)
    assert validated_plan is not None


def test_script_with_overlapping_slots_is_rejected():
    """Verifies that a script with overlapping slots is rejected by validation."""
    from toonshorts.core.validator import validate_plan
    from toonshorts.core.models import PlanValidationError

    bad_script = {
        "version": 2,
        "title": "Conflicting Slot Script",
        "art_style": "night_studio",
        "emotional_arc": "suspenseful",
        "characters": [
            {"name": "Alice", "visual_description": "Friendly presenter"},
            {"name": "Bob", "visual_description": "Tech expert character"}
        ],
        "scenes": [
            {
                "scene_number": 1,
                "speaker": "Alice",
                "dialogue_line": "This layout has two elements colliding in the same slot.",
                "action": "explaining",
                "pose": "idle",
                "cast": ["Alice", "Bob"],
                "layout": {
                    "template": "hero",
                    "hero": "elem1",
                    "slots": {"hero": "elem1"},
                    "elements": [
                        {"id": "elem1", "slot": "hero", "is_hero": True, "enter_time": 0.5, "exit_time": 4.0},
                        {"id": "elem2", "slot": "hero", "is_hero": False, "enter_time": 1.0, "exit_time": 4.5},
                    ]
                }
            },
            {
                "scene_number": 2,
                "speaker": "Bob",
                "dialogue_line": "This is second scene.",
                "action": "explaining",
                "pose": "idle",
                "cast": ["Alice", "Bob"],
                "layout": {"template": "hero", "hero": "e2", "slots": {"hero": "e2"}, "elements": [{"id": "e2", "slot": "hero", "enter_time": 0.0, "exit_time": 3.0}]}
            },
            {
                "scene_number": 3,
                "speaker": "Alice",
                "dialogue_line": "This is third scene.",
                "action": "explaining",
                "pose": "idle",
                "cast": ["Alice", "Bob"],
                "layout": {"template": "hero", "hero": "e3", "slots": {"hero": "e3"}, "elements": [{"id": "e3", "slot": "hero", "enter_time": 0.0, "exit_time": 3.0}]}
            },
            {
                "scene_number": 4,
                "speaker": "Bob",
                "dialogue_line": "This is fourth scene.",
                "action": "punchline",
                "pose": "laughing",
                "is_punchline": True,
                "cast": ["Alice", "Bob"],
                "layout": {"template": "hero", "hero": "e4", "slots": {"hero": "e4"}, "elements": [{"id": "e4", "slot": "hero", "enter_time": 0.0, "exit_time": 3.0}]}
            }
        ]
    }
    with pytest.raises(PlanValidationError, match="collision without lifecycle exit"):
        validate_plan(bad_script)
