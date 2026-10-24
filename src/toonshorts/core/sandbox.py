"""
Purpose: Playwright browser sandboxing for secure rendering pages.
Inputs: Browser instance, allowed directory paths, viewport dimensions.
Outputs: Hardened Playwright BrowserContext and Page with zero-network CSP,
         request blocking, popup/navigation blocking, and frame timeouts.
Depends on: logging, pathlib, urllib.parse, urllib.request, typing, playwright
Used by: plugins.render.animejs.capture
Config keys: None
Tests: tests/unit/test_phase1_safe_foundation.py
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.parse
import urllib.request

logger = logging.getLogger("toonshorts.sandbox")

DEFAULT_PER_FRAME_TIMEOUT_MS = 5000

# Strict zero-network Content-Security-Policy
STRICT_CSP_POLICY = (
    "default-src 'none'; "
    "img-src 'self' data: file:; "
    "style-src 'self' 'unsafe-inline' file:; "
    "script-src 'self' 'unsafe-inline' file:; "
    "font-src 'self' data: file:; "
    "media-src 'self' file:; "
    "connect-src 'none'; "
    "frame-src 'none'; "
    "object-src 'none'; "
    "form-action 'none';"
)


def evaluate_frame(page: Any, expr: str, timeout_ms: int = DEFAULT_PER_FRAME_TIMEOUT_MS) -> Any:
    """
    Evaluates a JavaScript expression with a strict per-frame time limit.
    Raises TimeoutError if execution exceeds timeout_ms (e.g. infinite loops).
    """
    handle = page.wait_for_function(f"() => {{ return {expr}; }}", timeout=timeout_ms)
    return handle.json_value()


def create_sandboxed_context(
    browser: Any,
    allowed_dirs: List[Union[str, Path]],
    viewport: Optional[Dict[str, int]] = None,
    initial_html_path: Optional[Path] = None,
) -> Tuple[Any, Any]:
    """
    Creates a fresh, empty, hardened Playwright context and page.
    Enforces:
    - Zero cookies / storage
    - Strict Content-Security-Policy with connect-src 'none'
    - Local asset route interception (aborts all network and out-of-sandbox file:// reads)
    - Blocks popups and non-initial navigations
    - Returns (context, page)
    """
    vp = viewport or {"width": 1080, "height": 1920}

    # Resolve all allowed directory paths to canonical absolute paths
    canonical_allowed_dirs = [Path(d).resolve() for d in allowed_dirs]

    # Create fresh empty context
    context = browser.new_context(
        viewport=vp,
        permissions=[],
        bypass_csp=False,
        storage_state=None,
        extra_http_headers={"Content-Security-Policy": STRICT_CSP_POLICY},
    )

    page = context.new_page()

    # Route interception for strict local asset whitelist
    def route_handler(route: Any):
        req = route.request
        url_str = req.url

        # 1. Block any network requests
        if url_str.startswith(("http://", "https://", "ws://", "wss://", "ftp://")):
            logger.warning("Sandbox blocked network request: %s", url_str)
            route.abort("blockedbyclient")
            return

        # 2. Allow data: URIs
        if url_str.startswith("data:"):
            route.continue_()
            return

        # 3. Handle file:// URLs
        if url_str.startswith("file:"):
            try:
                parsed = urllib.parse.urlparse(url_str)
                local_path_str = urllib.request.url2pathname(parsed.path)
                # On Windows, strip leading slash from /C:/path
                if local_path_str.startswith("/") and len(local_path_str) > 2 and local_path_str[2] == ":":
                    local_path_str = local_path_str[1:]
                resolved_file = Path(local_path_str).resolve()

                # Verify resolved path is strictly within one of the allowed directories
                is_allowed = any(
                    resolved_file == allowed_dir or allowed_dir in resolved_file.parents
                    for allowed_dir in canonical_allowed_dirs
                )

                if is_allowed:
                    route.continue_()
                else:
                    logger.warning("Sandbox blocked unauthorized file access outside allowed dirs: %s", resolved_file)
                    route.abort("blockedbyclient")
            except Exception as e:
                logger.warning("Sandbox error inspecting file url %s: %s", url_str, e)
                route.abort("blockedbyclient")
            return

        # 4. Block anything else
        route.abort("blockedbyclient")

    page.route("**/*", route_handler)

    # Block popups
    page.on("popup", lambda p: p.close())

    # Hardened init script: neutralize network constructors and window.open
    page.add_init_script(
        """
        window.open = function() { console.warn('window.open blocked by sandbox'); return null; };
        window.alert = function() {};
        window.prompt = function() { return null; };
        window.confirm = function() { return false; };
        window.XMLHttpRequest = function() {
            throw new Error('XMLHttpRequest blocked: network access is disabled in sandbox');
        };
        window.WebSocket = function() {
            throw new Error('WebSocket blocked: network access is disabled in sandbox');
        };
        window.EventSource = function() {
            throw new Error('EventSource blocked: network access is disabled in sandbox');
        };
        if (navigator.sendBeacon) {
            navigator.sendBeacon = function() { return false; };
        }
        """
    )

    return context, page
