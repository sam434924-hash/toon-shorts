"""
Purpose: AST security scanner for agent-written Level 2 JavaScript animation effects.
Inputs: JavaScript code string.
Outputs: List of security violations (empty if clean), and validation helper.
Depends on: tree_sitter, tree_sitter_javascript
Used by: core.board_objects
Config keys: None
Tests: tests/unit/test_phase1_safe_foundation.py
"""

import logging
from typing import List, Tuple
import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser

logger = logging.getLogger("toonshorts.ast_scanner")

_JS_LANG = Language(tsjs.language())
_PARSER = Parser(_JS_LANG)

# Disallowed identifiers across global and object scopes
BANNED_IDENTIFIERS = frozenset({
    # Network
    "fetch",
    "xmlhttprequest",
    "websocket",
    "eventsource",
    "sendbeacon",
    "headers",
    "request",
    "response",
    # Navigation
    "location",
    "history",
    "open",
    "navigate",
    # Storage
    "localstorage",
    "sessionstorage",
    "indexeddb",
    "cookie",
    # Dynamic evaluation
    "eval",
    "function",
    # Timers
    "settimeout",
    "setinterval",
    "setimmediate",
    "requestanimationframe",
    "cancelanimationframe",
})


def scan_javascript_ast(code: str) -> List[str]:
    """
    Scans JavaScript source using Tree-Sitter AST.
    Bans:
    - Network (fetch, XMLHttpRequest, WebSocket, EventSource, sendBeacon)
    - Navigation (location, window.location, window.open, history)
    - Storage (localStorage, sessionStorage, indexedDB, cookie)
    - Eval/Function constructors
    - Dynamic imports (import(...))
    - Timers (setTimeout, setInterval, setImmediate, requestAnimationFrame)
    - Non-deterministic Date (Date.now, new Date)
    - Non-deterministic Math.random
    """
    if not code or not isinstance(code, str):
        return ["Empty or invalid JavaScript code"]

    code_bytes = code.encode("utf-8")
    tree = _PARSER.parse(code_bytes)
    violations: List[str] = []

    def visit(node):
        ntype = node.type

        # 1. Dynamic imports
        if ntype in ("import", "import_call"):
            violations.append("Security violation: Dynamic import is forbidden")

        # 2. Banned identifiers
        elif ntype == "identifier":
            ident = node.text.decode("utf-8", errors="replace").lower()
            if ident in BANNED_IDENTIFIERS:
                violations.append(f"Security violation: Forbidden API/identifier '{ident}'")
            elif ident == "date":
                violations.append("Security violation: Non-deterministic Date API is forbidden")

        # 3. Member expressions: Math.random, Date.now, window.open, document.cookie, etc.
        elif ntype == "member_expression":
            obj_node = node.child_by_field_name("object")
            prop_node = node.child_by_field_name("property")
            if obj_node and prop_node:
                obj_name = obj_node.text.decode("utf-8", errors="replace").lower()
                prop_name = prop_node.text.decode("utf-8", errors="replace").lower()

                if obj_name == "math" and prop_name == "random":
                    violations.append("Security violation: Math.random is forbidden (use seeded PRNG)")
                elif obj_name == "date" and prop_name in ("now", "parse"):
                    violations.append(f"Security violation: Date.{prop_name} is forbidden")
                elif obj_name in ("window", "document", "navigator", "globalthis"):
                    if prop_name in BANNED_IDENTIFIERS or prop_name in ("cookie", "location", "open"):
                        violations.append(f"Security violation: Forbidden '{obj_name}.{prop_name}' access")

        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return violations


def validate_level2_effect(code: str) -> Tuple[bool, List[str]]:
    """
    Validates agent-written Level 2 JavaScript:
    1. Must pass AST scan banning network, navigation, storage, eval, dynamic imports, timers, Date.now, Math.random.
    2. Must be parseable without syntax errors.
    3. Exposes a function of time t.
    """
    violations = scan_javascript_ast(code)
    # Check syntax error nodes in AST
    code_bytes = code.encode("utf-8")
    tree = _PARSER.parse(code_bytes)
    if tree.root_node.has_error:
        violations.append("Syntax error in JavaScript effect code")

    # Verify function exposure
    lower_code = code.lower()
    has_func = "function" in lower_code or "=>" in lower_code
    if not has_func:
        violations.append("Effect must define or return a function of time t: (t, seed) => { ... }")

    is_valid = len(violations) == 0
    return is_valid, violations
