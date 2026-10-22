"""Unit tests for Scene format v2 data models and directing validator rules."""

from pathlib import Path
import json
import pytest
from pydantic import ValidationError

from toonshorts.core.models import (
    Character,
    PlanValidationError,
    Scene,
    ScriptPlan,
    Shot,
    Visual,
)
from toonshorts.core.validator import (
    adapt_plan_v1_to_v2,
    estimate_scene_duration,
    validate_plan,
    validate_shots,
)


def make_valid_v1_dict():
    return {
        "title": "V1 Test Plan",
        "art_style": "whiteboard",
        "emotional_arc": "Setup and humorous punchline",
        "characters": [
            {"name": "Alice", "visual_description": "Friendly presenter"},
            {"name": "Bob", "visual_description": "Curious coder"}
        ],
        "scenes": [
            {"scene_number": 1, "speaker": "Alice", "dialogue_line": "Hello world welcome to the tech demo.", "action": "Intro", "pose": "idle"},
            {"scene_number": 2, "speaker": "Bob", "dialogue_line": "Thank you Alice glad to be here today.", "action": "Response", "pose": "idle"},
            {"scene_number": 3, "speaker": "Alice", "dialogue_line": "Let us explain how things work under the hood.", "action": "Explain", "pose": "idle"},
            {"scene_number": 4, "speaker": "Bob", "dialogue_line": "This is so simple and crystal clear!", "action": "Outro", "pose": "laughing", "is_punchline": True}
        ]
    }


def test_v1_plan_loads_unchanged():
    v1_dict = make_valid_v1_dict()
    # Ensure without version key, it defaults to version 1 and layout cards
    plan = validate_plan(v1_dict)
    assert plan.version == 1
    assert len(plan.scenes) == 4
    for sc in plan.scenes:
        assert sc.layout == "cards"
        assert sc.shots is None
        assert sc.visuals is None


def test_v1_fixture_file_loads_unchanged():
    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "what_is_an_api_plan.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    plan = validate_plan(data)
    assert plan.version == 1
    assert plan.title == "What_is_an_API"
    assert len(plan.scenes) == 6


def test_validator_unknown_fields_rejected():
    v1_dict = make_valid_v1_dict()
    v1_dict["unexpected_global_field"] = "malicious_or_junk"
    with pytest.raises(PlanValidationError):
        validate_plan(v1_dict)

    v1_dict_sc = make_valid_v1_dict()
    v1_dict_sc["scenes"][0]["unknown_scene_field"] = 123
    with pytest.raises(PlanValidationError):
        validate_plan(v1_dict_sc)


def test_shot_zoom_limit():
    shots = [
        Shot(start=0.5, end=3.0, type="close_up", target="Alice", zoom=1.40, ease_in=0.5, ease_out=0.5)
    ]
    errs, _ = validate_shots(shots, ["Alice"], scene_number=1, scene_length=5.0)
    assert any("zoom (1.40) must be <= 1.35" in e for e in errs)


def test_shot_ease_times_limits():
    # ease_in too low
    shots1 = [
        Shot(start=0.5, end=3.0, type="close_up", target="Alice", zoom=1.2, ease_in=0.3, ease_out=0.5)
    ]
    errs1, _ = validate_shots(shots1, ["Alice"], scene_number=1, scene_length=5.0)
    assert any("ease_in (0.30s) must be between 0.4 and 0.6 s" in e for e in errs1)

    # ease_out too high
    shots2 = [
        Shot(start=0.5, end=3.0, type="close_up", target="Alice", zoom=1.2, ease_in=0.5, ease_out=0.7)
    ]
    errs2, _ = validate_shots(shots2, ["Alice"], scene_number=1, scene_length=5.0)
    assert any("ease_out (0.70s) must be between 0.4 and 0.6 s" in e for e in errs2)


def test_shot_minimum_hold_limit():
    # Total duration 2.0s, ease_in 0.5, ease_out 0.5 -> hold = 1.0s (< 1.2s minimum)
    shots = [
        Shot(start=0.5, end=2.5, type="close_up", target="Alice", zoom=1.2, ease_in=0.5, ease_out=0.5)
    ]
    errs, _ = validate_shots(shots, ["Alice"], scene_number=1, scene_length=5.0)
    assert any("minimum hold must be at least 1.2 s" in e for e in errs)

    # Sufficient hold: 0.5s + 1.2s + 0.5s = 2.2s -> start 0.5, end 2.8 (hold = 1.3s >= 1.2s)
    shots_valid = [
        Shot(start=0.5, end=2.8, type="close_up", target="Alice", zoom=1.2, ease_in=0.5, ease_out=0.5)
    ]
    errs_valid, _ = validate_shots(shots_valid, ["Alice"], scene_number=1, scene_length=5.0)
    assert len(errs_valid) == 0


def test_shot_at_most_one_zoom_per_5_seconds():
    # Two zoom shots within 3 seconds
    shots = [
        Shot(start=0.5, end=2.8, type="close_up", target="Alice", zoom=1.2, ease_in=0.5, ease_out=0.5),
        Shot(start=3.5, end=5.8, type="close_up", target="Alice", zoom=1.2, ease_in=0.5, ease_out=0.5),
    ]
    errs, _ = validate_shots(shots, ["Alice"], scene_number=1, scene_length=8.0)
    assert any("at most one zoom per 5 s" in e for e in errs)


def test_shot_target_must_exist_in_cast():
    shots = [
        Shot(start=0.5, end=2.8, type="close_up", target="Charlie", zoom=1.2, ease_in=0.5, ease_out=0.5)
    ]
    errs, _ = validate_shots(shots, ["Alice", "Bob"], scene_number=1, scene_length=5.0)
    assert any("target 'Charlie' must exist in scene cast" in e for e in errs)


def test_shot_no_overlapping_shots():
    # Shot 1 ends at 3.0, Shot 2 starts at 2.5
    shots = [
        Shot(start=0.5, end=3.0, type="wide", target=None, zoom=1.0, ease_in=0.5, ease_out=0.5),
        Shot(start=2.5, end=4.5, type="wide", target=None, zoom=1.0, ease_in=0.5, ease_out=0.5),
    ]
    errs, _ = validate_shots(shots, ["Alice"], scene_number=1, scene_length=5.0)
    assert any("overlapping shots" in e for e in errs)


def test_shots_inside_scene_length():
    # Scene length is 4.0s, shot ends at 5.5s
    shots = [
        Shot(start=1.0, end=5.5, type="wide", target=None, zoom=1.0, ease_in=0.5, ease_out=0.5)
    ]
    errs, _ = validate_shots(shots, ["Alice"], scene_number=1, scene_length=4.0)
    assert any("must be inside scene length" in e for e in errs)


def test_layout_validation():
    plan_dict = make_valid_v1_dict()
    plan_dict["version"] = 2
    plan_dict["scenes"][0]["layout"] = "invalid_layout_mode"
    with pytest.raises((PlanValidationError, ValidationError)):
        validate_plan(plan_dict)

    # Valid layouts 'cards' and 'stage'
    plan_dict["scenes"][0]["layout"] = "stage"
    plan_dict["scenes"][1]["layout"] = "cards"
    plan = validate_plan(plan_dict)
    assert plan.scenes[0].layout == "stage"
    assert plan.scenes[1].layout == "cards"


def test_cast_speaker_and_180_degree_rule():
    plan_dict = make_valid_v1_dict()
    plan_dict["version"] = 2

    # Speaker not in cast
    plan_dict["scenes"][0]["cast"] = ["Bob"]
    plan_dict["scenes"][0]["speaker"] = "Alice"
    with pytest.raises(PlanValidationError, match="must exist in scene cast"):
        validate_plan(plan_dict)

    # Cast exceeds 2 characters
    plan_dict["scenes"][0]["cast"] = ["Alice", "Bob", "Charlie"]
    with pytest.raises(PlanValidationError, match="exceeds maximum of 2"):
        validate_plan(plan_dict)

    # 180-degree rule: Character A left, Character B right must not swap
    plan_dict["scenes"][0]["cast"] = ["Alice", "Bob"]
    plan_dict["scenes"][0]["speaker"] = "Alice"
    plan_dict["scenes"][1]["cast"] = ["Bob", "Alice"]  # Swapped!
    plan_dict["scenes"][1]["speaker"] = "Bob"
    with pytest.raises(PlanValidationError, match="180-degree rule violation"):
        validate_plan(plan_dict)


def test_visuals_max_count():
    plan_dict = make_valid_v1_dict()
    plan_dict["version"] = 2
    plan_dict["scenes"][0]["visuals"] = [
        {"type": "flow", "trigger_word": "hello", "params": {}},
        {"type": "flow", "trigger_word": "world", "params": {}},
        {"type": "flow", "trigger_word": "welcome", "params": {}},
        {"type": "flow", "trigger_word": "demo", "params": {}},  # 4 visuals!
    ]
    with pytest.raises(PlanValidationError, match="at most 3 visuals allowed"):
        validate_plan(plan_dict)
