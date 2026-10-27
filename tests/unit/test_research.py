"""
Purpose: Unit tests for safe web-research step verifying HTTPS enforcement, domain allowlist,
         20KB byte cap, 5-page run limit, and untrusted notes formatting.
Inputs: Target URLs, custom allowlist configs, mock HTTP responses.
Outputs: Pytest assertions validating strict security sandboxing.
Depends on: pytest, unittest.mock, toonshorts.core.research
Used by: Test suite
Config keys: None
Tests: tests/unit/test_research.py
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from toonshorts.core.research import (
    MAX_BYTES_PER_PAGE,
    extract_plain_text,
    fetch_page_text,
    load_allowlist,
    safe_web_research,
)


def test_rejects_non_https():
    """Non-HTTPS URLs (http://, file://, ftp://) must be strictly rejected."""
    allowed = ["en.wikipedia.org"]
    ok, err, _ = fetch_page_text("http://en.wikipedia.org/wiki/AI", allowed)
    assert not ok
    assert "Only HTTPS is allowed" in err

    ok_file, err_file, _ = fetch_page_text("file:///etc/passwd", allowed)
    assert not ok_file
    assert "Only HTTPS is allowed" in err_file


def test_rejects_disallowed_domains():
    """Domains not listed in research_allowlist.json must be strictly rejected."""
    allowed = ["en.wikipedia.org", "anthropic.com"]
    ok, err, host = fetch_page_text("https://malicious-site.com/exploit", allowed)
    assert not ok
    assert "not in approved allowlist" in err
    assert host == "malicious-site.com"


def test_max_bytes_per_page_capping():
    """Content exceeding 20KB is capped at exactly 20480 bytes."""
    allowed = ["docs.python.org"]
    huge_html = "<html><body>" + ("A" * 30000) + "</body></html>"

    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.read.side_effect = lambda limit: huge_html[:limit].encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok, text, _ = fetch_page_text("https://docs.python.org/3/", allowed, max_bytes=MAX_BYTES_PER_PAGE)
        assert ok
        assert len(text.encode("utf-8")) <= MAX_BYTES_PER_PAGE


def test_extract_plain_text_strips_scripts_and_tags():
    """HTML tags, javascript, and CSS must be completely stripped from output text."""
    raw = """
    <html>
      <head><script>alert('xss');</script><style>body { color: red; }</style></head>
      <body>
        <h1>Title Header</h1>
        <p>This is safe plain text.</p>
      </body>
    </html>
    """
    clean = extract_plain_text(raw)
    assert "alert" not in clean
    assert "color: red" not in clean
    assert "Title Header" in clean
    assert "This is safe plain text." in clean


def test_safe_web_research_max_five_pages_and_notes(tmp_path):
    """Enforces maximum 5 pages per run and generates UNTRUSTED DATA notes file."""
    urls = [
        "https://en.wikipedia.org/wiki/AI_agent",
        "https://anthropic.com/research",
        "https://ai.google.dev/gemini",
        "https://docs.python.org/3/library/json.html",
        "https://en.wikipedia.org/wiki/Prompt_engineering",
        "https://en.wikipedia.org/wiki/Sixth_URL_Exceeded",
    ]

    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.read.return_value = b"<html><body><p>AI agent definition and architecture.</p></body></html>"
    mock_resp.__enter__.return_value = mock_resp

    notes_file = tmp_path / "notes.md"

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = safe_web_research(urls, output_notes_path=notes_file)

        assert len(result["entries"]) == 5  # 6th was capped
        assert notes_file.is_file()
        content = notes_file.read_text(encoding="utf-8")
        assert "UNTRUSTED DATA" in content
        assert "## Sources Log" in content
        assert "AI agent definition" in content
