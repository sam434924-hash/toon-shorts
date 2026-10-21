"""
Purpose: Compatibility re-export of ASS subtitle utilities.
Inputs: Text and subtitle timing data.
Outputs: Escaped subtitle text and timestamp formatting.
Depends on: core.subtitles
Used by: None
Config keys: None
Tests: tests/unit/test_escaping.py
"""

from .core.subtitles import escape_ass_text, format_ass_time, generate_ass_subtitles

__all__ = ["escape_ass_text", "format_ass_time", "generate_ass_subtitles"]
