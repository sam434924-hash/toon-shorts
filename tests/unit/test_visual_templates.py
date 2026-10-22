"""Unit tests for Visual Templates allowlist, parameter limits, XSS prevention, and stage layout overflow."""

import pytest

from toonshorts.core.models import PlanValidationError, Visual
from toonshorts.core.validator import validate_plan
from toonshorts.core.visuals import (
    ALLOWED_PALETTES,
    ALLOWED_VISUAL_TYPES,
    check_stage_layout_overflow,
    sanitize_text,
    validate_visual_item,
)


def make_valid_stage_plan():
    return {
        "version": 2,
        "title": "Visual Test Plan",
        "art_style": "whiteboard",
        "emotional_arc": "Testing template limits",
        "characters": [
            {"name": "Alice", "visual_description": "Presenter"},
            {"name": "Bob", "visual_description": "Assistant"}
        ],
        "scenes": [
            {
                "scene_number": 1,
                "speaker": "Alice",
                "dialogue_line": "This is scene one with flow visual.",
                "action": "Present",
                "pose": "idle",
                "layout": "stage",
                "visuals": [
                    {
                        "type": "flow",
                        "trigger_word": "flow",
                        "params": {"nodes": ["Client", "API", "Server"], "color": "blue"}
                    }
                ]
            },
            {"scene_number": 2, "speaker": "Bob", "dialogue_line": "Scene two reply.", "action": "Act", "pose": "idle"},
            {"scene_number": 3, "speaker": "Alice", "dialogue_line": "Scene three line.", "action": "Act", "pose": "idle"},
            {"scene_number": 4, "speaker": "Bob", "dialogue_line": "Scene four line.", "action": "Act", "pose": "idle"}
        ]
    }


def test_allowed_visual_types():
    assert "flow" in ALLOWED_VISUAL_TYPES
    assert "request_response" in ALLOWED_VISUAL_TYPES
    assert "typed_code" in ALLOWED_VISUAL_TYPES
    assert "step_ladder" in ALLOWED_VISUAL_TYPES
    assert "check_cross" in ALLOWED_VISUAL_TYPES
    assert "counter" in ALLOWED_VISUAL_TYPES

    # Unknown type
    errs = validate_visual_item("3d_cube", "trigger", {}, scene_number=1, visual_index=0)
    assert any("unknown visual type '3d_cube'" in e for e in errs)


def test_flow_validation():
    # Valid
    assert not validate_visual_item("flow", "word", {"nodes": ["A", "B", "C"]}, 1, 0)

    # Too few nodes (< 2)
    errs1 = validate_visual_item("flow", "word", {"nodes": ["OnlyOne"]}, 1, 0)
    assert any("must have between 2 and 4 nodes" in e for e in errs1)

    # Too many nodes (> 4)
    errs2 = validate_visual_item("flow", "word", {"nodes": ["A", "B", "C", "D", "E"]}, 1, 0)
    assert any("must have between 2 and 4 nodes" in e for e in errs2)

    # Node label too long (> 14 chars)
    errs3 = validate_visual_item("flow", "word", {"nodes": ["Short", "ThisLabelIsWayTooLongForBoard"]}, 1, 0)
    assert any("exceeds maximum 14 characters" in e for e in errs3)

    # Unknown param
    errs4 = validate_visual_item("flow", "word", {"nodes": ["A", "B"], "unknown_prop": 123}, 1, 0)
    assert any("unknown param 'unknown_prop'" in e for e in errs4)


def test_request_response_validation():
    # Valid
    assert not validate_visual_item(
        "request_response",
        "word",
        {"client_label": "Browser", "server_label": "Cloud", "request_label": "GET /data", "response_label": "200 OK"},
        1,
        0,
    )

    # Label too long
    errs = validate_visual_item("request_response", "word", {"client_label": "VeryLongClientLabelExceeds14"}, 1, 0)
    assert any("exceeds maximum 14 characters" in e for e in errs)

    # Unknown param
    errs2 = validate_visual_item("request_response", "word", {"css_style": "display: flex"}, 1, 0)
    assert any("unknown param 'css_style'" in e for e in errs2)


def test_typed_code_validation():
    # Valid
    assert not validate_visual_item(
        "typed_code",
        "word",
        {"lines": ["def get_user():", "    return {'id': 1}"], "language": "python"},
        1,
        0,
    )

    # Line too long (> 40 chars)
    long_line = "x = " + "a" * 45
    errs = validate_visual_item("typed_code", "word", {"lines": [long_line]}, 1, 0)
    assert any("exceeds maximum 40 characters" in e for e in errs)

    # Too many lines (> 6)
    errs2 = validate_visual_item("typed_code", "word", {"lines": [f"line {i}" for i in range(7)]}, 1, 0)
    assert any("must have between 1 and 6 lines" in e for e in errs2)


def test_step_ladder_validation():
    # Valid
    assert not validate_visual_item("step_ladder", "word", {"steps": ["Step 1", "Step 2", "Step 3"]}, 1, 0)

    # Invalid count
    errs = validate_visual_item("step_ladder", "word", {"steps": ["SingleStep"]}, 1, 0)
    assert any("must have between 2 and 4 steps" in e for e in errs)

    # Label too long
    errs2 = validate_visual_item("step_ladder", "word", {"steps": ["OK", "StepNameIsWayTooLong12345"]}, 1, 0)
    assert any("exceeds maximum 14 characters" in e for e in errs2)


def test_check_cross_validation():
    # Valid check and cross
    assert not validate_visual_item("check_cross", "word", {"icon": "check", "label": "Valid"}, 1, 0)
    assert not validate_visual_item("check_cross", "word", {"icon": "cross", "label": "Failed"}, 1, 0)

    # Invalid icon
    errs = validate_visual_item("check_cross", "word", {"icon": "question_mark", "label": "Unknown"}, 1, 0)
    assert any("icon must be 'check' or 'cross'" in e for e in errs)

    # Label too long
    errs2 = validate_visual_item("check_cross", "word", {"icon": "check", "label": "SuperLongLabelOver14"}, 1, 0)
    assert any("exceeds maximum 14 characters" in e for e in errs2)


def test_counter_validation():
    # Valid
    assert not validate_visual_item("counter", "word", {"from_val": 0, "to_val": 100, "label": "Req/sec"}, 1, 0)

    # Number out of bounds
    errs = validate_visual_item("counter", "word", {"from_val": -2000000, "to_val": 10}, 1, 0)
    assert any("from_val must be a number between -1000000 and 1000000" in e for e in errs)

    # Suffix too long
    errs2 = validate_visual_item("counter", "word", {"from_val": 0, "to_val": 10, "suffix": "way_too_long"}, 1, 0)
    assert any("suffix 'way_too_long' exceeds maximum 6 characters" in e for e in errs2)


def test_named_palette_only():
    # Allowed palette
    assert not validate_visual_item("flow", "word", {"nodes": ["A", "B"], "color": "purple"}, 1, 0)

    # Free CSS / arbitrary hex / unknown color rejected
    errs = validate_visual_item("flow", "word", {"nodes": ["A", "B"], "color": "#ff0000"}, 1, 0)
    assert any("not in allowed palette" in e for e in errs)


def test_xss_and_script_injection_rejected():
    # Injection in params rejected
    errs1 = validate_visual_item(
        "flow",
        "word",
        {"nodes": ["Safe", "<script>alert('xss')</script>"]},
        1,
        0,
    )
    assert any("forbidden script, HTML, or SVG" in e for e in errs1)

    errs2 = validate_visual_item(
        "check_cross",
        "word",
        {"icon": "check", "label": "img onerror=1"},
        1,
        0,
    )
    assert any("forbidden script, HTML, or SVG" in e for e in errs2)

    # Sanitizer escapes special characters
    raw = '<script>alert("test") & \'quote\'</script>'
    escaped = sanitize_text(raw)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&quot;" in escaped


def test_stage_layout_overflow_rejected():
    # 3 large visuals stacked exceed safe board height (385px)
    # request_response (150) + request_response (150) + step_ladder 4 steps (164) = 464px + 32px gap = 496px > 385px
    overflow_visuals = [
        {"type": "request_response", "params": {"client_label": "C1", "server_label": "S1"}},
        {"type": "request_response", "params": {"client_label": "C2", "server_label": "S2"}},
        {"type": "step_ladder", "params": {"steps": ["Step 1", "Step 2", "Step 3", "Step 4"]}},
    ]
    errs = check_stage_layout_overflow(overflow_visuals, scene_number=1)
    assert any("visuals overflow board safe area" in e for e in errs)

    # Fitting visuals: 1 flow (110) + 1 request_response (150) = 260px + 16px gap = 276px <= 385px
    fit_visuals = [
        {"type": "flow", "params": {"nodes": ["Client", "API", "Server"]}},
        {"type": "request_response", "params": {"client_label": "Client", "server_label": "Server"}},
    ]
    assert not check_stage_layout_overflow(fit_visuals, scene_number=1)


def test_stage_layout_plan_validation():
    plan_dict = make_valid_stage_plan()
    # Add overflow visuals to scene 1
    plan_dict["scenes"][0]["visuals"] = [
        {"type": "request_response", "trigger_word": "this", "params": {"client_label": "C1", "server_label": "S1"}},
        {"type": "request_response", "trigger_word": "scene", "params": {"client_label": "C2", "server_label": "S2"}},
        {"type": "step_ladder", "trigger_word": "one", "params": {"steps": ["Step 1", "Step 2", "Step 3", "Step 4"]}},
    ]
    with pytest.raises(PlanValidationError, match="visuals overflow board safe area"):
        validate_plan(plan_dict)


def test_resolve_visual_timings_matched_and_fallback(caplog):
    import logging
    from toonshorts.core.models import Visual, WordTiming
    from toonshorts.plugins.render.animejs.visual_renderer import resolve_visual_timings

    word_timings = [
        WordTiming(word="Imagine", start_time=0.45, end_time=0.85),
        WordTiming(word="you", start_time=0.90, end_time=1.10),
        WordTiming(word="call", start_time=1.20, end_time=1.45),
        WordTiming(word="the", start_time=1.50, end_time=1.60),
        WordTiming(word="api", start_time=1.65, end_time=2.10),
    ]

    visuals = [
        Visual(type="flow", trigger_word="api", params={"nodes": ["A", "B"]}),
        Visual(type="counter", trigger_word="nonexistentword", params={"from_val": 0, "to_val": 10}),
    ]

    with caplog.at_level(logging.WARNING):
        resolved = resolve_visual_timings(visuals, word_timings, duration_sec=5.0, scene_number=2)

    # First visual matched "api" at 1.65s -> 1650ms
    assert resolved[0]["start_ms"] == 1650
    assert resolved[0]["trigger_word"] == "api"

    # Second visual missed -> logged warning and even spacing
    assert any("Trigger word 'nonexistentword' not found in word timings" in record.message for record in caplog.records)
    assert resolved[1]["start_ms"] > 1650
