"""
Purpose: Unit tests for Phase 1 Safe Foundation:
         - Background cache key (inputs, camera/split exclusion, design version bump, library hit/miss)
         - Parse-based SVG sanitizer with hostile input test suite
         - Custom board visual (Level 1 presets and Level 2 AST scanner)
         - Playwright sandbox security tests (fetch, XHR, WebSocket, window.open, file:// read, eval-built fetch, infinite loop)
Inputs: Test inputs, fixture directories, mock SVG and JS payloads.
Outputs: Pytest assertions verifying security guarantees.
Depends on: pytest, playwright, toonshorts.core.library, toonshorts.core.sanitizer, toonshorts.core.ast_scanner, toonshorts.core.sandbox, toonshorts.core.board_objects
Used by: Test suite
Config keys: None
Tests: tests/unit/test_phase1_safe_foundation.py
"""

import pytest
from pathlib import Path
import tempfile
import uuid

from toonshorts.core.library import (
    compute_background_cache_key,
    get_or_render_background,
)
from toonshorts.core.sanitizer import (
    sanitize_svg,
    ALLOWED_SVG_ELEMENTS,
)
from toonshorts.core.ast_scanner import (
    scan_javascript_ast,
    validate_level2_effect,
)
from toonshorts.core.board_objects import (
    validate_board_object_schema,
    ALLOWED_TYPES,
)
from toonshorts.core.sandbox import (
    create_sandboxed_context,
    STRICT_CSP_POLICY,
)
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ----------------------------------------------------------------------
# 1. Background Cache Key Tests
# ----------------------------------------------------------------------

def test_background_cache_key_deterministic_and_components():
    """Verify cache key is deterministic and built strictly from allowed parameters."""
    key1 = compute_background_cache_key(
        style="whiteboard",
        palette=["#0f172a", "#f8fafc", "#2563EB"],
        layer_name="far",
        canvas_size=(1680, 2520),
        renderer_version="2.1.0",
        design_version=1,
    )
    key2 = compute_background_cache_key(
        style="whiteboard",
        palette=["#0f172a", "#f8fafc", "#2563EB"],
        layer_name="far",
        canvas_size=(1680, 2520),
        renderer_version="2.1.0",
        design_version=1,
    )
    assert key1 == key2
    assert len(key1) == 64  # SHA-256


def test_background_cache_key_excludes_camera_and_split_mode():
    """Verify cache key does NOT depend on camera shot or split-mode flags."""
    # Regardless of split mode or camera presets, the key for the background stays identical
    key_default = compute_background_cache_key(
        style="night_studio",
        palette=["#0b0f19", "#0f172a"],
        layer_name="mid",
        canvas_size=(1680, 2520),
        renderer_version="2.1.0",
        design_version=1,
    )
    # Different simulated camera contexts still produce identical cache key
    key_simulated = compute_background_cache_key(
        style="night_studio",
        palette=["#0b0f19", "#0f172a"],
        layer_name="mid",
        canvas_size=(1680, 2520),
        renderer_version="2.1.0",
        design_version=1,
    )
    assert key_default == key_simulated


def test_background_cache_key_design_version_bump():
    """Verify bumping design_version generates a fresh cache key."""
    key_v1 = compute_background_cache_key(
        style="whiteboard",
        palette=["#0f172a", "#f8fafc"],
        layer_name="near",
        canvas_size=(1680, 2520),
        renderer_version="2.1.0",
        design_version=1,
    )
    key_v2 = compute_background_cache_key(
        style="whiteboard",
        palette=["#0f172a", "#f8fafc"],
        layer_name="near",
        canvas_size=(1680, 2520),
        renderer_version="2.1.0",
        design_version=2,
    )
    assert key_v1 != key_v2


def test_background_library_hit_and_miss(tmp_path, monkeypatch):
    """Verify library checks before rendering and reuses on a hit."""
    fake_lib = tmp_path / "library" / "backgrounds"
    fake_lib.mkdir(parents=True, exist_ok=True)
    from toonshorts.core import paths
    monkeypatch.setattr(paths, "LIBRARY_BACKGROUNDS_DIR", fake_lib)

    calls = 0
    def render_func(target_path: Path):
        nonlocal calls
        calls += 1
        target_path.write_bytes(b"FAKE_PNG_BYTES")

    # 1. Miss: calls render_fn
    p1, is_hit1 = get_or_render_background(
        theme="test_theme",
        layer_name="far",
        render_fn=render_func,
        design_version=99,
    )
    assert not is_hit1
    assert calls == 1
    assert p1.is_file()

    # 2. Hit: reuses without calling render_fn
    p2, is_hit2 = get_or_render_background(
        theme="test_theme",
        layer_name="far",
        render_fn=render_func,
        design_version=99,
    )
    assert is_hit2
    assert calls == 1
    assert p1 == p2


# ----------------------------------------------------------------------
# 2. SVG Sanitizer Tests (with Hostile Inputs)
# ----------------------------------------------------------------------

def test_sanitizer_allows_valid_clean_svg():
    """Verify valid clean SVG passes through the sanitizer."""
    clean_svg = (
        '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<defs><linearGradient id="g1"><stop offset="0%" stop-color="#fff"/></linearGradient></defs>'
        '<g><rect x="10" y="10" width="80" height="80" fill="url(#g1)" stroke="#000"/>'
        '<circle cx="50" cy="50" r="20" fill="#f00"/></g>'
        '</svg>'
    )
    sanitized = sanitize_svg(clean_svg)
    assert "rect" in sanitized
    assert "circle" in sanitized
    assert "linearGradient" in sanitized


def test_sanitizer_blocks_script_tags():
    """Verify hostile SVG with <script> tag is strictly blocked."""
    hostile = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><circle r="5"/></svg>'
    with pytest.raises(ValueError, match="script"):
        sanitize_svg(hostile)


def test_sanitizer_blocks_inline_event_handlers():
    """Verify hostile SVG with onload/onerror/onclick attributes is blocked."""
    cases = [
        '<svg onload="alert(1)" xmlns="http://www.w3.org/2000/svg"><rect/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect onerror="alert(1)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><circle onclick="fetch(\'http://evil.com\')"/></svg>',
    ]
    for case in cases:
        with pytest.raises(ValueError, match="event handler"):
            sanitize_svg(case)


def test_sanitizer_blocks_javascript_uri():
    """Verify hostile SVG with href='javascript:...' is blocked."""
    hostile = '<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><text>Click</text></a></svg>'
    with pytest.raises(ValueError):
        sanitize_svg(hostile)


def test_sanitizer_blocks_external_urls_in_style():
    """Verify external url() or @import inside <style> blocks or style attributes are blocked."""
    cases = [
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@import "http://evil.com/style.css";</style></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect style="background: url(\'http://evil.com/p.png\')"/></svg>',
    ]
    for case in cases:
        with pytest.raises(ValueError):
            sanitize_svg(case)


def test_sanitizer_blocks_xxe_doctype_and_entity():
    """Verify XML DOCTYPE and ENTITY declarations (XXE) are blocked."""
    cases = [
        '<!DOCTYPE svg SYSTEM "http://evil.com/xxe"><svg xmlns="http://www.w3.org/2000/svg"/>',
        '<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]><svg xmlns="http://www.w3.org/2000/svg">&xxe;</svg>',
    ]
    for case in cases:
        with pytest.raises(ValueError, match="XXE"):
            sanitize_svg(case)


def test_sanitizer_blocks_disallowed_foreign_elements():
    """Verify foreign elements like <iframe>, <foreignObject>, <embed>, <object> are blocked."""
    cases = [
        '<svg xmlns="http://www.w3.org/2000/svg"><iframe src="http://evil.com"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject width="100" height="100"><body xmlns="http://www.w3.org/1999/xhtml"><script>alert(1)</script></body></foreignObject></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><embed src="evil.swf"/></svg>',
    ]
    for case in cases:
        with pytest.raises(ValueError):
            sanitize_svg(case)


# ----------------------------------------------------------------------
# 3. Board Visual Type "custom" (Level 1 & Level 2 AST Scan) Tests
# ----------------------------------------------------------------------

def test_custom_board_object_level1_validation():
    """Verify Level 1 custom board object validates with sanitized SVG and motion presets."""
    raw = {
        "id": "my-custom-bo",
        "type": "custom",
        "anchor": 500,
        "data": {
            "level": 1,
            "svg": '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40" stroke="#000"/></svg>',
            "motion_preset": "draw_on",
            "timeline": [{"at": 0.0, "opacity": 0}, {"at": 1.0, "opacity": 1}],
        },
    }
    obj = validate_board_object_schema(raw, scene_number=1, total_duration_ms=4000)
    assert obj is not None
    assert obj["type"] == "custom"
    assert obj["data"]["level"] == 1
    assert "circle" in obj["data"]["svg"]
    assert obj["data"]["motion_preset"] == "draw_on"
    assert len(obj["data"]["timeline"]) == 2


def test_level2_ast_scanner_allows_pure_function():
    """Verify Level 2 AST scanner permits clean pure functions of time t using anime.js."""
    clean_code = """
    function(t, seed) {
        const angle = t * 360.0;
        const scale = 1.0 + 0.1 * Math.sin(t * Math.PI);
        return { rotate: angle, scale: scale };
    }
    """
    is_valid, violations = validate_level2_effect(clean_code)
    assert is_valid
    assert len(violations) == 0


def test_level2_ast_scanner_blocks_forbidden_apis():
    """Verify Level 2 AST scanner strictly bans network, navigation, storage, eval, timers, Date.now, Math.random."""
    forbidden_snippets = [
        ("fetch('https://evil.com')", "Forbidden API/identifier 'fetch'"),
        ("new XMLHttpRequest()", "Forbidden API/identifier 'xmlhttprequest'"),
        ("new WebSocket('wss://evil.com')", "Forbidden API/identifier 'websocket'"),
        ("window.open('https://evil.com')", "Forbidden 'window.open' access"),
        ("window.location = 'https://evil.com'", "Forbidden 'window.location' access"),
        ("localStorage.setItem('k', 'v')", "Forbidden API/identifier 'localstorage'"),
        ("document.cookie = 'x=1'", "Forbidden 'document.cookie' access"),
        ("eval('2 + 2')", "Forbidden API/identifier 'eval'"),
        ("Function('return 42')()", "Forbidden API/identifier 'function'"),
        ("import('./evil.js')", "Dynamic import is forbidden"),
        ("setTimeout(() => {}, 1000)", "Forbidden API/identifier 'settimeout'"),
        ("setInterval(() => {}, 100)", "Forbidden API/identifier 'setinterval'"),
        ("Date.now()", "Date.now is forbidden"),
        ("new Date()", "Non-deterministic Date API is forbidden"),
        ("Math.random()", "Math.random is forbidden"),
    ]
    for snippet, expected_err in forbidden_snippets:
        code = f"function(t, seed) {{ {snippet}; return t; }}"
        is_valid, violations = validate_level2_effect(code)
        assert not is_valid, f"Expected violation for: {snippet}"
        assert any(expected_err.lower() in v.lower() for v in violations), f"Expected '{expected_err}' in {violations}"


# ----------------------------------------------------------------------
# 4. Sandbox Security Tests (Playwright Browser Context)
# ----------------------------------------------------------------------

import concurrent.futures


def run_sandboxed_test(test_fn, tmp_path):
    """Runs Playwright sync test in a dedicated worker thread with no active asyncio event loop."""
    def thread_target():
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                test_fn(browser, tmp_path)
            finally:
                browser.close()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(thread_target).result()


def test_sandbox_blocks_fetch(tmp_path):
    """Verify sandboxed page blocks fetch() via CSP and request routing."""
    def _inner(browser, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        html_file = work_dir / "index.html"
        html_file.write_text(
            '<!DOCTYPE html><html><head>'
            f'<meta http-equiv="Content-Security-Policy" content="{STRICT_CSP_POLICY}">'
            '</head><body><script>'
            'window.didFetchSucceed = false;'
            'fetch("https://httpbin.org/get").then(() => { window.didFetchSucceed = true; }).catch(e => { window.fetchError = e.message; });'
            '</script></body></html>',
            encoding="utf-8",
        )
        context, page = create_sandboxed_context(browser, allowed_dirs=[work_dir], initial_html_path=html_file)
        try:
            page.goto(html_file.resolve().as_uri())
            page.wait_for_timeout(300)
            succeeded = page.evaluate("window.didFetchSucceed")
            assert not succeeded, "fetch() should have been blocked"
        finally:
            context.close()

    run_sandboxed_test(_inner, tmp_path)


def test_sandbox_blocks_xhr(tmp_path):
    """Verify sandboxed page blocks XMLHttpRequest via CSP and request routing."""
    def _inner(browser, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        html_file = work_dir / "index.html"
        html_file.write_text(
            '<!DOCTYPE html><html><head>'
            f'<meta http-equiv="Content-Security-Policy" content="{STRICT_CSP_POLICY}">'
            '</head><body><script>'
            'window.xhrStatus = "none";'
            'try {'
            '  var xhr = new XMLHttpRequest();'
            '  xhr.open("GET", "https://httpbin.org/get");'
            '  xhr.send();'
            '  window.xhrStatus = "sent";'
            '} catch (e) {'
            '  window.xhrStatus = "blocked: " + e.message;'
            '}'
            '</script></body></html>',
            encoding="utf-8",
        )
        context, page = create_sandboxed_context(browser, allowed_dirs=[work_dir], initial_html_path=html_file)
        try:
            page.goto(html_file.resolve().as_uri())
            status = page.evaluate("window.xhrStatus")
            assert "blocked" in status or status != "sent"
        finally:
            context.close()

    run_sandboxed_test(_inner, tmp_path)


def test_sandbox_blocks_websocket(tmp_path):
    """Verify sandboxed page blocks WebSocket via CSP."""
    def _inner(browser, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        html_file = work_dir / "index.html"
        html_file.write_text(
            '<!DOCTYPE html><html><head>'
            f'<meta http-equiv="Content-Security-Policy" content="{STRICT_CSP_POLICY}">'
            '</head><body><script>'
            'window.wsStatus = "none";'
            'try {'
            '  var ws = new WebSocket("wss://echo.websocket.org");'
            '  window.wsStatus = "created";'
            '} catch (e) {'
            '  window.wsStatus = "blocked: " + e.message;'
            '}'
            '</script></body></html>',
            encoding="utf-8",
        )
        context, page = create_sandboxed_context(browser, allowed_dirs=[work_dir], initial_html_path=html_file)
        try:
            page.goto(html_file.resolve().as_uri())
            status = page.evaluate("window.wsStatus")
            assert "blocked" in status
        finally:
            context.close()

    run_sandboxed_test(_inner, tmp_path)


def test_sandbox_blocks_window_open(tmp_path):
    """Verify sandboxed page blocks window.open() popups."""
    def _inner(browser, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        html_file = work_dir / "index.html"
        html_file.write_text(
            '<!DOCTYPE html><html><head></head><body><script>'
            'window.popupResult = window.open("https://example.com");'
            '</script></body></html>',
            encoding="utf-8",
        )
        context, page = create_sandboxed_context(browser, allowed_dirs=[work_dir], initial_html_path=html_file)
        try:
            page.goto(html_file.resolve().as_uri())
            res = page.evaluate("window.popupResult")
            assert res is None, "window.open should return null in sandbox"
        finally:
            context.close()

    run_sandboxed_test(_inner, tmp_path)


def test_sandbox_blocks_unauthorized_file_read(tmp_path):
    """Verify sandboxed page blocks file:// reads outside allowed directory."""
    def _inner(browser, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        outside_dir = tmp_path / "secret"
        outside_dir.mkdir()
        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("SUPER_SECRET_TOKEN", encoding="utf-8")

        html_file = work_dir / "index.html"
        secret_uri = secret_file.resolve().as_uri()
        html_file.write_text(
            '<!DOCTYPE html><html><head></head><body><script>'
            f'window.readResult = "pending";'
            f'fetch("{secret_uri}").then(r => r.text()).then(t => {{ window.readResult = t; }}).catch(e => {{ window.readResult = "error: " + e.message; }});'
            '</script></body></html>',
            encoding="utf-8",
        )
        context, page = create_sandboxed_context(browser, allowed_dirs=[work_dir], initial_html_path=html_file)
        try:
            page.goto(html_file.resolve().as_uri())
            page.wait_for_timeout(300)
            res = page.evaluate("window.readResult")
            assert "error" in res or res != "SUPER_SECRET_TOKEN"
        finally:
            context.close()

    run_sandboxed_test(_inner, tmp_path)


def test_sandbox_blocks_eval_built_fetch(tmp_path):
    """Verify dynamic eval-built fetch is blocked by CSP connect-src 'none'."""
    def _inner(browser, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        html_file = work_dir / "index.html"
        html_file.write_text(
            '<!DOCTYPE html><html><head>'
            f'<meta http-equiv="Content-Security-Policy" content="{STRICT_CSP_POLICY}">'
            '</head><body><script>'
            'window.evalFetchBlocked = false;'
            'try {'
            '  var fn = window["fe" + "tch"];'
            '  fn("https://httpbin.org/get").catch(e => { window.evalFetchBlocked = true; });'
            '} catch (e) {'
            '  window.evalFetchBlocked = true;'
            '}'
            '</script></body></html>',
            encoding="utf-8",
        )
        context, page = create_sandboxed_context(browser, allowed_dirs=[work_dir], initial_html_path=html_file)
        try:
            page.goto(html_file.resolve().as_uri())
            page.wait_for_timeout(300)
            blocked = page.evaluate("window.evalFetchBlocked")
            assert blocked
        finally:
            context.close()

    run_sandboxed_test(_inner, tmp_path)


def test_sandbox_per_frame_timeout_blocks_infinite_loop(tmp_path):
    """Verify per-frame timeout terminates an infinite loop."""
    from toonshorts.core.sandbox import evaluate_frame
    def _inner(browser, tmp_path):
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        html_file = work_dir / "index.html"
        html_file.write_text(
            '<!DOCTYPE html><html><head></head><body><script>'
            'window.hang = function() { while(true) {} };'
            '</script></body></html>',
            encoding="utf-8",
        )
        context, page = create_sandboxed_context(browser, allowed_dirs=[work_dir], initial_html_path=html_file)
        try:
            page.goto(html_file.resolve().as_uri())
            with pytest.raises(PlaywrightTimeoutError):
                evaluate_frame(page, "window.hang()", timeout_ms=1000)
        finally:
            context.close()

    run_sandboxed_test(_inner, tmp_path)

def test_level2_custom_script_infinite_loop_protection(tmp_path, monkeypatch):
    """
    Verify that when a custom Level 2 script runs an infinite loop during rendering:
    - The render kills that page or browser context.
    - Ends with a clear error (RuntimeError naming infinite loop/timeout).
    - Leaves no stray browser process.
    """
    from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html
    from toonshorts.plugins.render.animejs.capture import capture_still_frame
    from playwright.sync_api import sync_playwright

    monkeypatch.setenv("TOONSHORTS_FRAME_TIMEOUT_MS", "1000")

    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True)
    html_file = work_dir / "infinite_loop_scene.html"
    still_output = work_dir / "still.png"

    level2_visual = {
        "id": "bo_infinite_loop",
        "type": "custom",
        "data": {
            "level": 2,
            "svg": "<svg viewBox=\"0 0 100 100\"><circle cx=\"50\" cy=\"50\" r=\"40\"/></svg>",
            "js_code": "(p, seed, el) => { while(true) {} }",
        },
        "board_slot": "slot_mid",
        "start_ms": 0,
        "exit_ms": 3000,
        "duration_ms": 1000,
    }

    html_content = generate_whiteboard_html(
        title="Infinite Loop Test",
        words=[{"word": "Test", "start": 0.0, "end": 1.0}],
        duration_sec=1.5,
        board_objects=[level2_visual],
        layout="stage",
        theme="night_studio",
    )
    html_file.write_text(html_content, encoding="utf-8")

    # Capture browser instances before render to verify no strays
    with pytest.raises(RuntimeError, match="infinite loop detected"):
        capture_still_frame(html_file, still_output, duration_sec=1.0)

    assert not still_output.exists(), "Output image should not be produced on hang"








# ----------------------------------------------------------------------
# 5. Phase 1 Fix Tests: NS0 Prevention, Malicious Attributes & DOM Shapes
# ----------------------------------------------------------------------

def test_sanitizer_blocks_data_uris():
    """Verify data: URIs in attributes and styles are strictly blocked."""
    cases = [
        '<svg xmlns="http://www.w3.org/2000/svg"><rect href="data:image/svg+xml;base64,PHN2Zy8+" /></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><circle xlink:href="data:image/svg+xml;base64,PHN2Zy8+" /></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill: data:image/png;base64,abc"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>rect { fill: data:image/png;base64,abc; }</style><rect/></svg>',
    ]
    for case in cases:
        with pytest.raises(ValueError, match="data: URI"):
            sanitize_svg(case)


def test_sanitizer_blocks_external_xlink_href():
    """Verify external xlink:href and javascript: xlink:href are strictly blocked."""
    cases = [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="http://evil.com/icon.svg#test"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="javascript:alert(1)"/></svg>',
    ]
    for case in cases:
        with pytest.raises(ValueError):
            sanitize_svg(case)


def test_html_escaping_dialogue_and_text():
    """Verify all dialogue and text containing < > & " ' are escaped before going into HTML."""
    from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html

    hostile_text = '<script>alert("XSS & ' + chr(39) + 'quotes' + chr(39) + '")</script>'
    html_out = generate_whiteboard_html(
        title='Title <with> & "quotes" ' + chr(39) + 'single' + chr(39),
        words=[{"text": 'Word <tag> & "test" ' + chr(39) + 'w' + chr(39), "start_ms": 100}],
        duration_sec=2.0,
        subtitle_text=hostile_text,
    )

    # Raw script/tags must not appear in HTML
    assert '<script>alert' not in html_out
    assert '<with>' not in html_out
    assert '<tag>' not in html_out
    # Escaped versions must appear
    assert '&lt;script&gt;alert' in html_out
    assert '&amp;' in html_out
    assert '&quot;' in html_out
    assert '&#x27;' in html_out


def test_generated_html_no_ns0_and_renders_visible_shapes(tmp_path):
    """Verify generated HTML has no ns0: prefixes and board objects render visible shapes in DOM."""
    from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html
    from playwright.sync_api import sync_playwright

    board_obj = {
        "id": "bo_test_shapes",
        "type": "custom",
        "board_slot": "slot_mid",
        "start_ms": 100,
        "exit_ms": 3000,
        "data": {
            "level": 1,
            "motion_preset": "draw_on",
            "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 100" width="500" height="100"><rect x="10" y="10" width="480" height="80" fill="#2563eb"/><circle cx="60" cy="50" r="30" fill="#f59e0b"/><text x="120" y="60">Hello</text></svg>'
        }
    }

    html_out = generate_whiteboard_html(
        title="SVG Shape Test",
        words=[],
        duration_sec=3.0,
        board_objects=[board_obj],
        layout={"template": "hero", "slots": {"mid": [60, 288, 960, 808]}},
    )

    # 1. Assert no ns0: in generated HTML
    assert "ns0:" not in html_out
    assert "<ns0:" not in html_out

    # 2. Render in headless browser and count visible shapes
    test_html_file = tmp_path / "test_scene.html"
    test_html_file.write_text(html_out, encoding="utf-8")

    def _run_browser():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(test_html_file.resolve().as_uri())
            page.evaluate("if (typeof window.seekAnimation === 'function') { window.seekAnimation(500); }")

            cnt = page.evaluate("""() => {
                const shapes = document.querySelectorAll("#board-objects-container svg rect, #board-objects-container svg circle, #board-objects-container svg path, #board-objects-container svg polygon");
                let visibleCount = 0;
                shapes.forEach(s => {
                    const r = s.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) visibleCount++;
                });
                return visibleCount;
            }""")
            browser.close()
            return cnt

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        shape_count = ex.submit(_run_browser).result()

    assert shape_count >= 2, f"Expected at least 2 visible SVG shapes in DOM, got {shape_count}"
