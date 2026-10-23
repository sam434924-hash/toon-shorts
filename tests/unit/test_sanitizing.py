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


def test_sanitize_filename_windows_reserved_names():
    """Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9) must be blocked case-insensitively."""
    reserved = [
        "con", "CON", "Con",
        "prn", "PRN", "aux", "AUX",
        "nul", "NUL",
        "com1", "COM5", "com9",
        "lpt1", "LPT4", "lpt9",
    ]
    for name in reserved:
        safe = sanitize_filename(name)
        assert safe == "toon_short", f"Expected default fallback for reserved name '{name}', got '{safe}'"


def test_sanitize_filename_windows_reserved_names_with_extension():
    """Windows reserved names followed by an extension must also be blocked."""
    cases = [
        "con.txt", "CON.mp4", "nul.mp4", "NUL.json",
        "aux.wav", "prn.pdf", "com1.png", "lpt9.dat",
    ]
    for case in cases:
        safe = sanitize_filename(case)
        assert safe == "toon_short", f"Expected default fallback for reserved name '{case}', got '{safe}'"


def test_sanitize_filename_trailing_dots_and_spaces():
    """Trailing dots and spaces must be stripped."""
    assert sanitize_filename("my_video...   ") == "my_video"
    assert sanitize_filename("sample..") == "sample"
    assert sanitize_filename("title   ") == "title"
    assert sanitize_filename("...   ") == "toon_short"


def test_sanitize_filename_path_separators_and_traversal():
    """Path separators and '..' traversals must be stripped."""
    assert sanitize_filename("../../../etc/passwd") == "etcpasswd"
    assert sanitize_filename(r"..\\..\\windows\\system32") == "windowssystem32"
    assert sanitize_filename("folder/subfolder/file") == "foldersubfolderfile"


def test_sanitize_filename_control_characters():
    """Control characters (\\x00-\\x1f, \\x7f-\\x9f) must be removed."""
    dirty = "my\x00video\x08test\x1bfile\x7f"
    clean = sanitize_filename(dirty)
    assert clean == "myvideotestfile"


def test_sanitize_filename_cap_length_100():
    """Length must be capped at 100 characters by default, and trailing dots stripped."""
    long_title = "a" * 120
    safe = sanitize_filename(long_title)
    assert len(safe) == 100

    long_with_dots = ("b" * 98) + "...."
    safe_dots = sanitize_filename(long_with_dots)
    assert len(safe_dots) <= 100
    assert not safe_dots.endswith(".")

