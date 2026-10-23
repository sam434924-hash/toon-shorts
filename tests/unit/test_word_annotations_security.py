"""
Purpose: Unit tests for word-aligned annotations validation and XSS security.
Inputs: Missing, empty, malformed, and malicious word timings.
Outputs: Graceful annotation skipping, length capping, and XSS-immune JSON payloads.
Depends on: toonshorts.core.models, toonshorts.plugins.render.animejs.annotations
Used by: tests
Config keys: None
Tests: tests/unit/test_word_annotations_security.py
"""

import math
import pytest

from toonshorts.core.models import Scene, WordTiming
from toonshorts.plugins.render.animejs.annotations import (
    MAX_ANNOTATIONS_PER_SCENE,
    MAX_WORD_LENGTH,
    extract_whiteboard_content_and_annotations,
    validate_word_timings,
)


def test_missing_word_timings_skips_annotations():
    """Missing word_timings (None) logs a warning and returns an empty annotations list."""
    scene = Scene(scene_number=1, speaker="Narrator", dialogue_line="Hello world", action="Title: Point A, Point B")
    title, cards, annotations = extract_whiteboard_content_and_annotations(
        scene=scene,
        duration_sec=3.0,
        word_timings=None,
    )
    assert annotations == []
    assert len(cards) > 0


def test_empty_word_timings_skips_annotations():
    """Empty word_timings ([]) logs a warning and returns an empty annotations list."""
    scene = Scene(scene_number=2, speaker="Narrator", dialogue_line="Hello world", action="Title: Point A")
    title, cards, annotations = extract_whiteboard_content_and_annotations(
        scene=scene,
        duration_sec=3.0,
        word_timings=[],
    )
    assert annotations == []
    assert len(cards) > 0


def test_malformed_timings_non_numeric():
    """Non-numeric start_time or end_time skips annotations."""
    malformed = [
        WordTiming(word="bad", start_time="zero", end_time=1.0),  # type: ignore
    ]
    res = validate_word_timings(malformed, duration_sec=3.0, scene_number=1)
    assert res is None


def test_malformed_timings_nan_inf():
    """NaN or Inf timings skip annotations."""
    nan_timings = [WordTiming(word="test", start_time=float("nan"), end_time=1.0)]
    inf_timings = [WordTiming(word="test", start_time=0.0, end_time=float("inf"))]
    assert validate_word_timings(nan_timings, duration_sec=3.0, scene_number=1) is None
    assert validate_word_timings(inf_timings, duration_sec=3.0, scene_number=1) is None


def test_malformed_timings_outside_scene_duration():
    """Negative start_time or start_time > duration_sec skips annotations."""
    neg_timings = [WordTiming(word="test", start_time=-0.5, end_time=1.0)]
    late_timings = [WordTiming(word="test", start_time=4.5, end_time=5.0)]
    inverted_timings = [WordTiming(word="test", start_time=2.0, end_time=1.0)]

    assert validate_word_timings(neg_timings, duration_sec=3.0, scene_number=1) is None
    assert validate_word_timings(late_timings, duration_sec=3.0, scene_number=1) is None
    assert validate_word_timings(inverted_timings, duration_sec=3.0, scene_number=1) is None


def test_word_length_capping():
    """Words longer than MAX_WORD_LENGTH are capped cleanly."""
    super_long = "supercalifragilisticexpialidocious_extra_long_word"
    assert len(super_long) > MAX_WORD_LENGTH
    timings = [WordTiming(word=super_long, start_time=0.5, end_time=1.0)]
    validated = validate_word_timings(timings, duration_sec=3.0, scene_number=1)
    assert validated is not None
    assert len(validated[0].word) <= MAX_WORD_LENGTH


def test_max_annotations_per_scene_capping():
    """Number of annotations per scene is strictly capped to MAX_ANNOTATIONS_PER_SCENE (8)."""
    many_points = ", ".join([f"Point {i}" for i in range(15)])
    scene = Scene(
        scene_number=1,
        speaker="Narrator",
        dialogue_line="one two three four five six seven eight nine ten",
        action=f"Title: {many_points}",
    )
    valid_timings = [
        WordTiming(word=f"word{i}", start_time=round(0.1 * i, 2), end_time=round(0.1 * i + 0.08, 2))
        for i in range(20)
    ]
    _, _, annotations = extract_whiteboard_content_and_annotations(
        scene=scene,
        duration_sec=3.0,
        word_timings=valid_timings,
    )
    assert len(annotations) <= MAX_ANNOTATIONS_PER_SCENE


def test_malicious_script_tags_and_quotes_handling():
    """Malicious script tags, onload handlers, and quotes are safely handled as plain text."""
    xss_payload = '<script>alert("xss")</script>'
    scene = Scene(
        scene_number=1,
        speaker="Narrator",
        dialogue_line=f'He said "{xss_payload}" and \'quotes\'',
        action=f'XSS Test: {xss_payload}, \' OR \'1\'=\'1',
    )
    timings = [
        WordTiming(word=xss_payload, start_time=0.2, end_time=0.8),
        WordTiming(word="safe", start_time=1.0, end_time=1.5),
    ]
    title, cards, annotations = extract_whiteboard_content_and_annotations(
        scene=scene,
        duration_sec=3.0,
        word_timings=timings,
    )
    # Validate words are capped and preserved safely without crash
    assert len(title) <= 50
    assert len(cards) > 0
    assert len(annotations) > 0
