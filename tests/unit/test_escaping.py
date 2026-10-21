"""Tests for ASS subtitle escaping and security."""

from toonshorts.subtitles import escape_ass_text, format_ass_time


def test_escape_braces():
    malicious = "Hello {\\b1\\c&H0000FF&}World{}"
    escaped = escape_ass_text(malicious)
    assert "{" not in escaped
    assert "}" not in escaped
    assert "｛" in escaped
    assert "｝" in escaped


def test_escape_backslashes():
    text_with_slashes = r"Line 1\NLine 2\hIndent\c&HFFFFFF&"
    escaped = escape_ass_text(text_with_slashes)
    assert "\\" not in escaped
    assert "/" in escaped


def test_escape_percent_signs():
    text_with_percent = "100% genuine comedy %s %d"
    escaped = escape_ass_text(text_with_percent)
    assert "%" not in escaped
    assert "％" in escaped


def test_format_ass_time():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(5.42) == "0:00:05.42"
    assert format_ass_time(65.12) == "0:01:05.12"
    assert format_ass_time(3665.5) == "1:01:05.50"
