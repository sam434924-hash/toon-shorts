"""
Purpose: Unit tests for board object schema, caps, slot overlap resolution, and security.
Inputs: Board object payloads, text strings, timing anchors, and visual items.
Outputs: Assertion results verifying strict validation, sanitization, and deterministic seeking.
Depends on: pytest, playwright, toonshorts.core.board_objects, toonshorts.core.config
Used by: tests
Config keys: ENABLE_BOARD_OBJECTS
Tests: self
"""

import json
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

from toonshorts.core import config
from toonshorts.core.board_objects import (
    ALLOWED_TYPES,
    BOARD_SLOTS,
    MAX_DIAGRAM_NODES,
    MAX_OBJECTS_PER_SCENE,
    MAX_TEXT_LENGTH,
    MIN_FONT_SIZE_PX,
    compute_auto_font_size,
    convert_visuals_to_board_objects,
    derive_object_seed,
    parse_anchor_time_ms,
    resolve_board_objects_for_scene,
    sanitize_board_text,
    validate_board_object_schema,
)
from toonshorts.core.models import Visual, WordTiming
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html


def test_board_object_allowed_types():
    assert "text_pop" in ALLOWED_TYPES
    assert "text_typewriter" in ALLOWED_TYPES
    assert "highlight_word" in ALLOWED_TYPES
    assert "svg_draw" in ALLOWED_TYPES
    assert "diagram_flow" in ALLOWED_TYPES
    assert "icon_pop" in ALLOWED_TYPES
    assert len(ALLOWED_TYPES) == 6


def test_sanitize_board_text_strips_speaker_labels():
    raw1 = "Boy: Hello world!"
    assert sanitize_board_text(raw1) == "Hello world!"

    raw2 = "Girl: Welcome to the studio"
    assert sanitize_board_text(raw2) == "Welcome to the studio"

    raw3 = "Host: Zack: Double label"
    assert "Double label" in sanitize_board_text(raw3)


def test_sanitize_board_text_caps_length_and_ellipsizes():
    short_text = "Short text"
    assert sanitize_board_text(short_text) == "Short text"

    long_text = "A" * 120
    sanitized = sanitize_board_text(long_text)
    assert len(sanitized) <= MAX_TEXT_LENGTH
    assert sanitized.endswith("...")
    assert len(sanitized) == MAX_TEXT_LENGTH


def test_sanitize_board_text_strips_html_tags():
    xss = "<script>alert('xss')</script>Normal Text"
    sanitized = sanitize_board_text(xss)
    assert "<script>" not in sanitized
    assert "</script>" not in sanitized
    assert "Normal Text" in sanitized


def test_compute_auto_font_size():
    assert compute_auto_font_size(10) >= 40
    assert compute_auto_font_size(25) >= 36
    assert compute_auto_font_size(45) >= 32
    assert compute_auto_font_size(80) == MIN_FONT_SIZE_PX
    assert compute_auto_font_size(200) == MIN_FONT_SIZE_PX


def test_derive_object_seed_is_deterministic():
    s1 = derive_object_seed(1, "obj-alpha")
    s2 = derive_object_seed(1, "obj-alpha")
    s3 = derive_object_seed(2, "obj-alpha")
    s4 = derive_object_seed(1, "obj-beta")

    assert s1 == s2
    assert s1 != s3
    assert s1 != s4


def test_parse_anchor_time_ms():
    wts = [
        {"word": "Welcome", "start_time": 0.5},
        {"word": "to", "start_time": 1.2},
        {"word": "Python", "start_time": 2.4},
    ]

    # Word index anchor
    assert parse_anchor_time_ms(0, wts) == 500
    assert parse_anchor_time_ms(2, wts) == 2400

    # Float seconds anchor
    assert parse_anchor_time_ms(1.5, wts) == 1500

    # Trigger word string anchor
    assert parse_anchor_time_ms("Python", wts) == 2400
    assert parse_anchor_time_ms("welcome", wts) == 500


def test_validate_board_object_schema_unknown_type_skipped():
    invalid_obj = {
        "id": "bad-1",
        "type": "unknown_future_plugin",
        "anchor": 1000,
        "data": {"text": "foo"},
    }
    res = validate_board_object_schema(invalid_obj, scene_number=1, total_duration_ms=5000)
    assert res is None


def test_validate_board_object_schema_diagram_nodes_capped():
    diag_obj = {
        "id": "diag-1",
        "type": "diagram_flow",
        "anchor": 500,
        "data": {
            "nodes": [f"Node {i}" for i in range(12)],
            "arrows": ["->"] * 10,
        },
    }
    res = validate_board_object_schema(diag_obj, scene_number=1, total_duration_ms=6000)
    assert res is not None
    assert len(res["data"]["nodes"]) == MAX_DIAGRAM_NODES


def test_resolve_board_objects_caps_objects_per_scene():
    raw_objs = [
        {"id": f"obj-{i}", "type": "text_pop", "anchor": i * 500, "data": {"text": f"Point {i}"}}
        for i in range(15)
    ]
    resolved = resolve_board_objects_for_scene(
        raw_objs,
        scene_number=1,
        duration_sec=6.0,
    )
    assert len(resolved) <= MAX_OBJECTS_PER_SCENE


def test_resolve_board_objects_slot_overlap_resolution():
    # Two overlapping objects in the same slot
    raw_objs = [
        {
            "id": "obj-1",
            "type": "text_pop",
            "anchor": 1000,
            "exit_time": 4000,
            "board_slot": "slot_mid",
            "data": {"text": "First"},
        },
        {
            "id": "obj-2",
            "type": "text_pop",
            "anchor": 1500,
            "exit_time": 4500,
            "board_slot": "slot_mid",
            "data": {"text": "Second"},
        },
    ]
    resolved = resolve_board_objects_for_scene(
        raw_objs,
        scene_number=1,
        duration_sec=6.0,
    )
    assert len(resolved) == 2
    # Second object should have been reassigned to a different slot to prevent visual overlap
    assert resolved[0]["board_slot"] != resolved[1]["board_slot"]


def test_convert_visuals_to_board_objects():
    visuals = [
        Visual(type="kinetic_words", trigger_word="API", params={"text": "Boy: What is an API?", "highlight_term": "API"}),
        Visual(type="flow", trigger_word="flow", params={"nodes": ["Client", "Server"]}),
        Visual(type="hearts_pop", trigger_word="love", params={"count": 3}),
    ]
    wts = [
        WordTiming(word="What", start_time=0.2, end_time=0.5),
        WordTiming(word="API", start_time=1.0, end_time=1.4),
        WordTiming(word="flow", start_time=2.5, end_time=3.0),
        WordTiming(word="love", start_time=4.0, end_time=4.5),
    ]

    bo = convert_visuals_to_board_objects(
        visuals,
        scene_number=1,
        duration_sec=6.0,
        word_timings=wts,
    )
    assert len(bo) == 3
    # kinetic_words with highlight_term becomes highlight_word
    assert bo[0]["type"] == "highlight_word"
    assert "Boy:" not in bo[0]["data"]["text"]
    # flow becomes diagram_flow
    assert bo[1]["type"] == "diagram_flow"
    # hearts_pop becomes icon_pop
    assert bo[2]["type"] == "icon_pop"


def test_board_objects_browser_render_and_seek_purity(tmp_path):
    board_objs = [
        {
            "id": "bo-test-1",
            "type": "text_pop",
            "anchor": 500,
            "exit_time": 3000,
            "board_slot": "slot_top",
            "data": {"text": "Headline Text"},
        },
        {
            "id": "bo-test-2",
            "type": "text_typewriter",
            "anchor": 1000,
            "exit_time": 4000,
            "board_slot": "slot_mid",
            "data": {"text": "def calculate():\n    return 42"},
        },
        {
            "id": "bo-test-3",
            "type": "diagram_flow",
            "anchor": 1500,
            "exit_time": 4500,
            "board_slot": "slot_bottom",
            "data": {"nodes": ["Client", "Gateway", "DB"], "arrows": ["req", "query"]},
        },
    ]

    html_code = generate_whiteboard_html(
        title="Board Objects Test",
        words=[{"text": "Headline", "start_ms": 500, "duration_ms": 400}],
        duration_sec=5.0,
        scene_number=1,
        board_objects=board_objs,
    )

    test_file = tmp_path / "board_test.html"
    test_file.write_text(html_code, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(test_file.resolve().as_uri())

        # Test at t=200ms: before all board objects
        page.evaluate("window.seekTo(200)")
        res_200 = page.evaluate("""() => {
            const el1 = document.getElementById('bo-test-1');
            const el2 = document.getElementById('bo-test-2');
            return {
                op1: el1 ? window.getComputedStyle(el1).opacity : null,
                op2: el2 ? window.getComputedStyle(el2).opacity : null,
            };
        }""")
        assert res_200["op1"] == "0"
        assert res_200["op2"] == "0"

        # Test at t=1200ms: bo-test-1 is visible, bo-test-2 is typing
        page.evaluate("window.seekTo(1200)")
        res_1200 = page.evaluate("""() => {
            const el1 = document.getElementById('bo-test-1');
            const el2 = document.getElementById('bo-test-2');
            const body2 = document.getElementById('bo-test-2-body');
            return {
                op1: parseFloat(window.getComputedStyle(el1).opacity),
                txt1: el1.textContent,
                op2: parseFloat(window.getComputedStyle(el2).opacity),
                txt2: body2 ? body2.textContent : '',
            };
        }""")
        assert res_1200["op1"] > 0.5
        assert "Headline Text" in res_1200["txt1"]
        assert res_1200["op2"] > 0.1
        assert len(res_1200["txt2"]) > 0

        # Purity check: seek forward then backward yields exact same DOM state
        page.evaluate("window.seekTo(3500)")
        page.evaluate("window.seekTo(1200)")
        res_1200_again = page.evaluate("""() => {
            const el1 = document.getElementById('bo-test-1');
            const body2 = document.getElementById('bo-test-2-body');
            return {
                op1: parseFloat(window.getComputedStyle(el1).opacity),
                txt2: body2 ? body2.textContent : '',
            };
        }""")
        assert res_1200_again["op1"] == res_1200["op1"]
        assert res_1200_again["txt2"] == res_1200["txt2"]

        browser.close()
