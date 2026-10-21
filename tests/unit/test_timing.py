"""Tests for scene timing and word boundary calculations."""

from toonshorts.voice import compute_fallback_word_timings, WordTiming


def test_proportional_word_timings():
    text = "Wait, what did you just do?"
    duration = 2.0
    timings = compute_fallback_word_timings(text, duration)

    assert len(timings) == 6
    assert timings[0].word == "Wait,"
    assert timings[-1].word == "do?"
    
    # Timing should start at 0.0 and end at or close to total duration
    assert timings[0].start_time == 0.0
    assert abs(timings[-1].end_time - duration) <= 0.05

    # Check ascending order
    for i in range(len(timings) - 1):
        assert timings[i].start_time <= timings[i].end_time
        assert timings[i].end_time <= timings[i+1].start_time


def test_empty_text_timing():
    timings = compute_fallback_word_timings("", 2.0)
    assert timings == []
