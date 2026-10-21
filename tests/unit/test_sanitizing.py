"""Tests for filename sanitization against OS traversal and invalid characters."""

from toonshorts.models import sanitize_filename


def test_sanitize_filename_illegal_chars():
    title = 'Why Did the Chicken Cross the Road? : "An Epic Tale" <Part 1> /\\ | *'
    safe = sanitize_filename(title)
    for bad_char in '<>:"/\\|?*':
        assert bad_char not in safe
    assert "Chicken" in safe


def test_sanitize_filename_spaces_and_length():
    title = "A " * 50
    safe = sanitize_filename(title, max_length=20)
    assert len(safe) <= 20
    assert " " not in safe


def test_sanitize_filename_empty_fallback():
    title = '???:::***///\\\\'
    safe = sanitize_filename(title)
    assert safe == "toon_short"
