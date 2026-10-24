"""
Purpose: Visual template schemas, parameter validators, stage safe-area bounds, and layout overflow checking.
Inputs: Visual definitions, template parameters, and scene layout declarations.
Outputs: Validated visual parameters, dimensions, and sanitized HTML/SVG structures.
Depends on: html, re, typing
Used by: core.validator, inventory, plugins.render.animejs.visual_renderer
Config keys: None
Tests: tests/unit/test_visual_templates.py, tests/unit/test_v2_validation.py
"""

import html
import re
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_VISUAL_TYPES = {
    "flow",
    "request_response",
    "typed_code",
    "step_ladder",
    "check_cross",
    "counter",
    "kinetic_words",
    "draw_svg",
    "octopus_vector",
    "hearts_pop",
    "blue_blood_drop",
    "custom",
}

ALLOWED_PALETTES = {
    "default": {"stroke": "#1e293b", "accent": "#2563eb", "bg": "#f8fafc", "text": "#0f172a"},
    "blue": {"stroke": "#1d4ed8", "accent": "#3b82f6", "bg": "#eff6ff", "text": "#1e3a8a"},
    "green": {"stroke": "#15803d", "accent": "#22c55e", "bg": "#f0fdf4", "text": "#14532d"},
    "purple": {"stroke": "#6d28d9", "accent": "#a855f7", "bg": "#faf5ff", "text": "#581c87"},
    "orange": {"stroke": "#c2410c", "accent": "#f97316", "bg": "#fff7ed", "text": "#7c2d12"},
    "red": {"stroke": "#b91c1c", "accent": "#ef4444", "bg": "#fef2f2", "text": "#7f1d1d"},
    "teal": {"stroke": "#0f766e", "accent": "#14b8a6", "bg": "#f0fdfa", "text": "#134e4a"},
    "yellow": {"stroke": "#b45309", "accent": "#eab308", "bg": "#fefce8", "text": "#713f12"},
}

# Stage safe area dimensions inside whiteboard (Whiteboard is 880x560, inner is 808x510)
# Title badge occupies ~95px vertical space at top
STAGE_SAFE_WIDTH = 760.0
STAGE_SAFE_HEIGHT = 385.0
STAGE_GAP_PX = 16.0

DISALLOWED_PATTERNS = [
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"onerror\s*=", re.IGNORECASE),
    re.compile(r"onload\s*=", re.IGNORECASE),
    re.compile(r"<\s*svg", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
]


def sanitize_text(text: str) -> str:
    """Escapes text for safe inclusion in HTML/SVG and strips speaker label prefixes."""
    from toonshorts.core.models import strip_speaker_label
    clean = strip_speaker_label(str(text))
    return html.escape(clean, quote=True)


def check_script_injection(val: Any) -> bool:
    """Returns True if any forbidden executable or markup string is detected."""
    if isinstance(val, str):
        for pattern in DISALLOWED_PATTERNS:
            if pattern.search(val):
                return True
    elif isinstance(val, list):
        for item in val:
            if check_script_injection(item):
                return True
    elif isinstance(val, dict):
        for k, v in val.items():
            if check_script_injection(k) or check_script_injection(v):
                return True
    return False


def get_visual_dimensions(visual_type: str, params: Dict[str, Any]) -> Tuple[float, float]:
    """Returns (width, height) in pixels for layout safe area planning."""
    if visual_type == "flow":
        return (740.0, 110.0)
    elif visual_type == "request_response":
        return (740.0, 150.0)
    elif visual_type == "typed_code":
        lines = params.get("lines", [])
        line_count = len(lines) if isinstance(lines, list) else 1
        h = max(70.0, 40.0 + line_count * 26.0)
        return (720.0, h)
    elif visual_type == "step_ladder":
        steps = params.get("steps", [])
        step_count = len(steps) if isinstance(steps, list) else 2
        h = max(80.0, step_count * 36.0 + 20.0)
        return (720.0, h)
    elif visual_type == "check_cross":
        return (600.0, 65.0)
    elif visual_type == "counter":
        return (600.0, 75.0)
    elif visual_type == "kinetic_words":
        return (720.0, 80.0)
    elif visual_type in ("draw_svg", "octopus_vector"):
        return (720.0, 320.0)
    elif visual_type == "hearts_pop":
        return (720.0, 160.0)
    elif visual_type == "blue_blood_drop":
        return (720.0, 240.0)
    elif visual_type == "custom":
        w = float(params.get("width", 200.0))
        h = float(params.get("height", 200.0))
        return (w, h)
    return (600.0, 80.0)


def validate_visual_item(
    v_type: str,
    trigger_word: str,
    params: Dict[str, Any],
    scene_number: int,
    visual_index: int,
) -> List[str]:
    """Strictly validates a single visual template against the allowlist and param constraints."""
    errors: List[str] = []
    prefix = f"Scene {scene_number}: visuals[{visual_index}]"

    # 1. Type check
    if v_type not in ALLOWED_VISUAL_TYPES:
        errors.append(
            f"{prefix}: unknown visual type '{v_type}'. Allowed types: {sorted(list(ALLOWED_VISUAL_TYPES))}"
        )
        return errors

    # 2. Trigger word check
    if not trigger_word or len(trigger_word) > 30:
        errors.append(
            f"{prefix}: trigger_word must be between 1 and 30 characters (got '{trigger_word}')"
        )

    # 3. Injection check
    if check_script_injection(trigger_word):
        errors.append(f"{prefix}: forbidden script, HTML, or SVG markup detected in visual trigger_word")

    if v_type != "custom":
        if check_script_injection(params):
            errors.append(f"{prefix}: forbidden script, HTML, or SVG markup detected in visual params")
    else:
        # Validate Level 1 or Level 2 custom visual
        level = params.get("level", 1)
        if level == 1:
            from toonshorts.core.sanitizer import sanitize_svg
            svg_code = params.get("svg", "")
            if svg_code:
                try:
                    sanitize_svg(svg_code)
                except Exception as e:
                    errors.append(f"{prefix}: custom visual Level 1 SVG rejected by sanitizer: {e}")
        elif level == 2:
            from toonshorts.core.ast_scanner import scan_js_code
            js_code = params.get("js", "")
            if js_code:
                is_valid, violations = scan_js_code(js_code)
                if not is_valid:
                    errors.append(f"{prefix}: custom visual Level 2 JS security violations: {', '.join(violations)}")

    # 4. Color / style check
    color = params.get("color", "default")
    if v_type not in ("kinetic_words", "draw_svg", "octopus_vector", "hearts_pop", "blue_blood_drop", "custom"):
        if color not in ALLOWED_PALETTES:
            errors.append(
                f"{prefix}: color '{color}' is not in allowed palette: {sorted(list(ALLOWED_PALETTES.keys()))}"
            )

    # 5. Type-specific parameter validation
    if v_type == "flow":
        allowed_keys = {"nodes", "color"}
        for k in params:
            if k not in allowed_keys:
                errors.append(f"{prefix}: unknown param '{k}' for flow visual")
        nodes = params.get("nodes")
        if not isinstance(nodes, list) or not (2 <= len(nodes) <= 4):
            count = len(nodes) if isinstance(nodes, list) else 0
            errors.append(f"{prefix}: flow must have between 2 and 4 nodes (got {count})")
        else:
            for idx, label in enumerate(nodes):
                if not isinstance(label, str) or len(label) > 14:
                    errors.append(
                        f"{prefix}: flow node[{idx}] label '{label}' exceeds maximum 14 characters"
                    )

    elif v_type == "request_response":
        allowed_keys = {"client_label", "server_label", "request_label", "response_label", "color"}
        for k in params:
            if k not in allowed_keys:
                errors.append(f"{prefix}: unknown param '{k}' for request_response visual")
        for field in ("client_label", "server_label", "request_label", "response_label"):
            val = params.get(field)
            if val is not None:
                if not isinstance(val, str) or len(val) > 14:
                    errors.append(
                        f"{prefix}: request_response {field} '{val}' exceeds maximum 14 characters"
                    )

    elif v_type == "typed_code":
        allowed_keys = {"lines", "language", "color"}
        for k in params:
            if k not in allowed_keys:
                errors.append(f"{prefix}: unknown param '{k}' for typed_code visual")
        lines = params.get("lines")
        if not isinstance(lines, list) or not (1 <= len(lines) <= 6):
            count = len(lines) if isinstance(lines, list) else 0
            errors.append(f"{prefix}: typed_code must have between 1 and 6 lines (got {count})")
        else:
            for idx, line in enumerate(lines):
                if not isinstance(line, str) or len(line) > 40:
                    errors.append(
                        f"{prefix}: typed_code line[{idx}] exceeds maximum 40 characters"
                    )
        lang = params.get("language")
        if lang is not None and (not isinstance(lang, str) or len(lang) > 14):
            errors.append(f"{prefix}: typed_code language '{lang}' exceeds maximum 14 characters")

    elif v_type == "step_ladder":
        allowed_keys = {"steps", "color"}
        for k in params:
            if k not in allowed_keys:
                errors.append(f"{prefix}: unknown param '{k}' for step_ladder visual")
        steps = params.get("steps")
        if not isinstance(steps, list) or not (2 <= len(steps) <= 4):
            count = len(steps) if isinstance(steps, list) else 0
            errors.append(f"{prefix}: step_ladder must have between 2 and 4 steps (got {count})")
        else:
            for idx, step in enumerate(steps):
                if not isinstance(step, str) or len(step) > 14:
                    errors.append(
                        f"{prefix}: step_ladder step[{idx}] '{step}' exceeds maximum 14 characters"
                    )

    elif v_type == "check_cross":
        allowed_keys = {"icon", "label", "color"}
        for k in params:
            if k not in allowed_keys:
                errors.append(f"{prefix}: unknown param '{k}' for check_cross visual")
        icon = params.get("icon")
        if icon not in ("check", "cross"):
            errors.append(f"{prefix}: check_cross icon must be 'check' or 'cross' (got '{icon}')")
        label = params.get("label", "")
        if not isinstance(label, str) or len(label) > 14:
            errors.append(f"{prefix}: check_cross label '{label}' exceeds maximum 14 characters")

    elif v_type == "counter":
        allowed_keys = {"from_val", "to_val", "label", "prefix", "suffix", "color"}
        for k in params:
            if k not in allowed_keys:
                errors.append(f"{prefix}: unknown param '{k}' for counter visual")
        from_val = params.get("from_val")
        to_val = params.get("to_val")
        if not isinstance(from_val, (int, float)) or not (-1000000 <= from_val <= 1000000):
            errors.append(
                f"{prefix}: counter from_val must be a number between -1000000 and 1000000 (got {from_val})"
            )
        if not isinstance(to_val, (int, float)) or not (-1000000 <= to_val <= 1000000):
            errors.append(
                f"{prefix}: counter to_val must be a number between -1000000 and 1000000 (got {to_val})"
            )
        label = params.get("label")
        if label is not None and (not isinstance(label, str) or len(label) > 14):
            errors.append(f"{prefix}: counter label '{label}' exceeds maximum 14 characters")
        pfx = params.get("prefix")
        if pfx is not None and (not isinstance(pfx, str) or len(pfx) > 6):
            errors.append(f"{prefix}: counter prefix '{pfx}' exceeds maximum 6 characters")
        sfx = params.get("suffix")
        if sfx is not None and (not isinstance(sfx, str) or len(sfx) > 6):
            errors.append(f"{prefix}: counter suffix '{sfx}' exceeds maximum 6 characters")

    elif v_type in ("kinetic_words", "draw_svg", "octopus_vector", "hearts_pop", "blue_blood_drop"):
        # Graphics plugins validate their parameters safely
        pass

    return errors


def check_stage_layout_overflow(
    visuals: List[Any],
    scene_number: int,
) -> List[str]:
    """
    Checks that visuals in 'stage' layout fit within board safe area without overflowing or overlapping.
    """
    errors: List[str] = []
    if not visuals:
        return errors

    total_height = 0.0
    for idx, v in enumerate(visuals):
        v_type = getattr(v, "type", None) or (v.get("type") if isinstance(v, dict) else "")
        params = getattr(v, "params", None) or (v.get("params") if isinstance(v, dict) else {})
        w, h = get_visual_dimensions(v_type, params)
        if w > STAGE_SAFE_WIDTH:
            errors.append(
                f"Scene {scene_number}: layout 'stage': visual[{idx}] width ({w:.1f}px) exceeds safe board width ({STAGE_SAFE_WIDTH:.1f}px)"
            )
        total_height += h

    # Add gaps between stacked visuals
    total_height += max(0, len(visuals) - 1) * STAGE_GAP_PX

    # In tall panel / night_studio layout, safe board height extends up to 820px
    max_safe_height = 820.0 if any(getattr(v, "type", None) in ("octopus_vector", "draw_svg", "blue_blood_drop", "hearts_pop") for v in visuals) else STAGE_SAFE_HEIGHT

    if total_height > max_safe_height + 1e-4:
        errors.append(
            f"Scene {scene_number}: layout 'stage': visuals overflow board safe area (total height {total_height:.1f}px > max {max_safe_height:.1f}px)"
        )

    return errors
