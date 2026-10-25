"""
Purpose: Unit tests for acting planner, validation rules, and check-acting CLI.
Inputs: Sample screenplay scenes, word timings, and layout blocks.
Outputs: Assertion results for beats, accents, gestures, listener reactions, and validation.
Depends on: pytest, json, pathlib, toonshorts.core.acting
Used by: tests
Config keys: None
Tests: self
"""

import json
from pathlib import Path
import pytest
from toonshorts.core.acting import (
    ALLOWED_GESTURES,
    plan_acting_plan,
    save_acting_plan,
    load_acting_plan,
    check_acting,
)


def test_acting_plan_generation():
    """Verify acting plan generates cast, beats, accents, and listener reactions for scenes."""
    scenes = [
        {
            "scene_number": 1,
            "speaker": "Speaker A",
            "dialogue_line": "Did you know that hackers can bypass your password in seconds?",
            "duration": 3.8,
            "word_timings": [
                {"word": "did", "start_time": 0.1, "end_time": 0.3},
                {"word": "hackers", "start_time": 0.5, "end_time": 1.1},
                {"word": "bypass", "start_time": 1.2, "end_time": 1.6},
                {"word": "password", "start_time": 1.7, "end_time": 2.3},
            ],
            "layout": {
                "template": "hero",
                "elements": [{"id": "el1", "slot_id": "slot-hero"}],
            },
        },
        {
            "scene_number": 2,
            "speaker": "Speaker B",
            "dialogue_line": "Wait really?! How does credential stuffing actually work?",
            "duration": 3.6,
            "word_timings": [
                {"word": "wait", "start_time": 0.1, "end_time": 0.4},
                {"word": "really", "start_time": 0.5, "end_time": 1.0},
                {"word": "stuffing", "start_time": 1.5, "end_time": 2.2},
            ],
        },
    ]

    plan = plan_acting_plan(scenes)
    assert "cast" in plan
    assert plan["cast"]["left"] == "boy_b"
    assert plan["cast"]["right"] == "girl_a"
    assert len(plan["scenes"]) == 2

    sc1 = plan["scenes"][0]
    assert sc1["speaker"] == "A"
    assert sc1["listener"] == "B"
    assert len(sc1["beats"]) == 1

    beat1 = sc1["beats"][0]
    assert beat1["tactic"] in ("hook", "explain", "warn", "punchline", "ask")
    assert beat1["energy"] in ("low", "medium", "high")
    assert beat1["gesture"]["name"] in ALLOWED_GESTURES
    # Lead frames: gesture starts earlier than stressed word
    assert beat1["gesture"]["start_ms"] <= beat1["gesture"]["peak_ms"]
    assert beat1["listener_reaction"] is not None
    assert beat1["listener_reaction"]["type"] in ("nod", "head_tilt", "amused", "skeptical", "blink", "attentive")


def test_no_back_to_back_repeating_gestures():
    """Verify that a speaker never receives the identical gesture back-to-back across multiple lines."""
    scenes = [
        {"scene_number": 1, "speaker": "A", "dialogue_line": "First line of explanation."},
        {"scene_number": 2, "speaker": "A", "dialogue_line": "Second line of explanation."},
        {"scene_number": 3, "speaker": "A", "dialogue_line": "Third line of explanation."},
    ]
    plan = plan_acting_plan(scenes, seed=123)
    gestures = [sc["beats"][0]["gesture"]["name"] for sc in plan["scenes"]]
    for i in range(1, len(gestures)):
        assert gestures[i] != gestures[i - 1], f"Gesture {gestures[i]} repeated at index {i}"


def test_save_load_acting_plan(tmp_path: Path):
    """Verify acting plan serialization and deserialization."""
    scenes = [
        {"scene_number": 1, "speaker": "A", "dialogue_line": "Check this out!"},
    ]
    plan = plan_acting_plan(scenes)
    out_file = tmp_path / "acting_plan.json"
    save_acting_plan(plan, out_file)
    assert out_file.is_file()

    loaded = load_acting_plan(out_file)
    assert loaded["cast"] == plan["cast"]
    assert len(loaded["scenes"]) == 1
    assert loaded["scenes"][0]["beats"][0]["tactic"] == plan["scenes"][0]["beats"][0]["tactic"]


def test_check_acting_tool(tmp_path: Path):
    """Verify check_acting returns PASS on valid plan and FAIL on rule violations."""
    scenes = [
        {
            "scene_number": 1,
            "speaker": "Speaker A",
            "dialogue_line": "How hackers break in.",
            "duration": 4.0,
            "word_timings": [{"word": "hackers", "start_time": 0.5, "end_time": 1.2}],
            "layout": {"template": "hero", "elements": [{"slot_id": "slot-hero"}]},
        },
        {
            "scene_number": 2,
            "speaker": "Speaker B",
            "dialogue_line": "They test stolen password combos across every popular service.",
            "duration": 4.0,
            "word_timings": [{"word": "password", "start_time": 0.5, "end_time": 1.2}],
        },
    ]
    plan = plan_acting_plan(scenes)
    save_acting_plan(plan, tmp_path / "acting_plan.json")

    report = check_acting(tmp_path)
    assert report["status"] == "PASS"
    assert report["scenes_count"] == 2
    assert len(report["errors"]) == 0

    # Invalidate plan with unknown gesture
    plan["scenes"][0]["beats"][0]["gesture"]["name"] = "cartwheel"
    save_acting_plan(plan, tmp_path / "acting_plan.json")

    report_bad = check_acting(tmp_path)
    assert report_bad["status"] == "FAIL"
    assert any("cartwheel" in e for e in report_bad["errors"])
