"""
Purpose: Parse-based SVG sanitizer and allowlist validator for agent-written SVG.
Inputs: Raw SVG strings.
Outputs: Clean, valid, sanitized SVG strings, or ValueError on hostile input.
Depends on: xml.etree.ElementTree, re, typing
Used by: core.board_objects, core.visuals
Config keys: None
Tests: tests/unit/test_phase1_safe_foundation.py
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Set

# Register standard SVG namespaces globally so ElementTree never generates ns0: prefixes
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

MAX_SVG_SIZE_BYTES = 500 * 1024  # 500 KB limit for agent SVG

ALLOWED_SVG_ELEMENTS = frozenset({
    "svg",
    "g",
    "path",
    "circle",
    "ellipse",
    "rect",
    "polygon",
    "polyline",
    "line",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
    "style",
    "text",
    "tspan",
    "mask",
    "pattern",
})

URL_PATTERN = re.compile(r"url\s*\(\s*([^)]*)\s*\)", re.IGNORECASE)
IMPORT_PATTERN = re.compile(r"@import\b", re.IGNORECASE)
JAVASCRIPT_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)
DATA_PATTERN = re.compile(r"data\s*:", re.IGNORECASE)
ENTITY_PATTERN = re.compile(r"<!ENTITY\b", re.IGNORECASE)
DOCTYPE_PATTERN = re.compile(r"<!DOCTYPE\b", re.IGNORECASE)
SCRIPT_PATTERN = re.compile(r"<\s*script\b", re.IGNORECASE)


def sanitize_svg(svg_content: str, strict: bool = True) -> str:
    """
    Sanitizes SVG content using a strict parse-based allowlist.
    Rejects or strips any disallowed elements, attributes, scripts, and XXE declarations.
    Raises ValueError on hostile inputs.
    """
    if not svg_content or not isinstance(svg_content, str):
        raise ValueError("SVG content cannot be empty")

    # 1. Size check
    raw_bytes = svg_content.encode("utf-8")
    if len(raw_bytes) > MAX_SVG_SIZE_BYTES:
        raise ValueError(f"SVG size {len(raw_bytes)} exceeds maximum limit of {MAX_SVG_SIZE_BYTES} bytes")

    # 2. Hostile declaration and script checks
    if DOCTYPE_PATTERN.search(svg_content) or ENTITY_PATTERN.search(svg_content):
        raise ValueError("Security violation: DOCTYPE and ENTITY declarations are forbidden (XXE protection)")

    if SCRIPT_PATTERN.search(svg_content):
        raise ValueError("Security violation: <script> elements are strictly forbidden in SVG")

    # 3. XML parse
    try:
        root = ET.fromstring(svg_content)
    except Exception as exc:
        raise ValueError(f"Malformed SVG XML: {exc}")

    # 4. Parse-based allowlist validation
    root_tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if root_tag.lower() != "svg":
        raise ValueError(f"Root element must be <svg>, got <{root_tag}>")

    def check_element(elem: ET.Element):
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag not in ALLOWED_SVG_ELEMENTS:
            raise ValueError(f"Security violation: Disallowed SVG element '<{tag}>'")

        if tag == "style":
            style_text = (elem.text or "") + (elem.tail or "")
            if IMPORT_PATTERN.search(style_text):
                raise ValueError("Security violation: Disallowed @import in style block")
            if JAVASCRIPT_PATTERN.search(style_text):
                raise ValueError("Security violation: Disallowed javascript: in style block")
            if DATA_PATTERN.search(style_text):
                raise ValueError("Security violation: Disallowed data: URI in style block")
            for match in URL_PATTERN.finditer(style_text):
                target = match.group(1).strip("'\" \t\r\n")
                if not target.startswith("#"):
                    raise ValueError(f"Security violation: Disallowed external url() in style: '{target}'")

        for attr_raw, val in list(elem.attrib.items()):
            attr = attr_raw.split("}")[-1] if "}" in attr_raw else attr_raw
            attr_lower = attr.lower()
            val_str = str(val)

            if attr_lower.startswith("on"):
                raise ValueError(f"Security violation: Disallowed event handler '{attr}'")

            if JAVASCRIPT_PATTERN.search(val_str):
                raise ValueError(f"Security violation: Disallowed javascript: URI in '{attr}'")

            if DATA_PATTERN.search(val_str):
                raise ValueError(f"Security violation: Disallowed data: URI in '{attr}'")

            if attr_lower in ("href", "xlink:href"):
                if not val_str.startswith("#"):
                    raise ValueError(f"Security violation: Disallowed external href in '{attr}': '{val_str}'")

            if attr_lower == "style":
                if IMPORT_PATTERN.search(val_str):
                    raise ValueError("Security violation: Disallowed @import in style attribute")
                if JAVASCRIPT_PATTERN.search(val_str):
                    raise ValueError("Security violation: Disallowed javascript: in style attribute")
                if DATA_PATTERN.search(val_str):
                    raise ValueError("Security violation: Disallowed data: URI in style attribute")
                for match in URL_PATTERN.finditer(val_str):
                    target = match.group(1).strip("'\" \t\r\n")
                    if not target.startswith("#"):
                        raise ValueError(f"Security violation: Disallowed external url() in style attribute: '{target}'")

        for child in list(elem):
            check_element(child)

    check_element(root)

    # Register default namespaces before serialization
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    serialized = ET.tostring(root, encoding="unicode")

    # Clean any ns0: namespace artifacts to ensure valid standard SVG in browser DOM
    serialized = re.sub(r"<\s*/?\s*ns\d+:", lambda m: "<" if "/" not in m.group(0) else "</", serialized)
    serialized = re.sub(r'\s+xmlns:ns\d+="[^"]*"', "", serialized)
    return serialized
