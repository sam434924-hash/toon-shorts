"""
Purpose: Visual style profile extraction, schema validation, and multi-character consistency.
Inputs: Character pack SVGs, manifest files, and brief style specifications.
Outputs: Validated StyleProfile dictionaries, style JSON assets, and similarity checks.
Depends on: json, logging, math, os, pathlib, re, typing, xml.etree.ElementTree
Used by: core, core.board_objects
Config keys: ENABLE_STYLE_PROFILE
Tests: tests/unit/test_style_profile.py
"""

from collections import Counter
import json
import logging
import math
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

from toonshorts.core import config

logger = logging.getLogger("toonshorts.style_profile")

HEX_COLOR_REGEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
FORBIDDEN_SVG_ELEMENTS = {"script", "iframe", "foreignobject", "audio", "video"}


def validate_hex_color(color_str: str) -> Optional[str]:
    """Validates and normalizes hex color strings to #RRGGBB format."""
    if not isinstance(color_str, str):
        return None
    cleaned = color_str.strip()
    match = HEX_COLOR_REGEX.match(cleaned)
    if not match:
        return None
    hex_val = match.group(1)
    if len(hex_val) == 3:
        hex_val = "".join([c * 2 for c in hex_val])
    return f"#{hex_val.lower()}"


def safe_parse_svg(svg_content: str) -> ET.Element:
    """
    Safely parses SVG XML content using standard library.
    Guarantees no external entities, no scripts executed, and no network access.
    """
    # Strict XXE and Entity check
    if "<!ENTITY" in svg_content.upper() or "<!DOCTYPE" in svg_content.upper():
        raise ValueError("Security violation: DOCTYPE and ENTITY declarations forbidden in SVG")

    if any(f"<{tag}" in svg_content.lower() for tag in FORBIDDEN_SVG_ELEMENTS):
        raise ValueError("Security violation: Script or embedded executable tags forbidden in SVG")

    # Safe ElementTree parse
    try:
        root = ET.fromstring(svg_content)
    except Exception as e:
        raise ValueError(f"Malformed SVG content: {e}") from e

    return root


def extract_style_from_svg(svg_path: Path) -> Dict[str, Any]:
    """
    Extracts visual style attributes from an SVG file:
    - palette: top colors (max 8 hex colors)
    - stroke_width: representative outline stroke width
    - outline_color: dominant stroke color
    - fill_style: flat_solid or shaded
    - roughness: 0.0 for clean vector
    """
    if not svg_path.is_file():
        raise FileNotFoundError(f"SVG file not found at {svg_path}")

    svg_content = svg_path.read_text(encoding="utf-8")
    root = safe_parse_svg(svg_content)

    color_counts: Counter = Counter()
    stroke_counts: Counter = Counter()
    stroke_widths: List[float] = []

    # Traverse all elements
    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
        if tag in FORBIDDEN_SVG_ELEMENTS:
            raise ValueError(f"Security violation: Forbidden tag <{tag}> detected")

        # Attribute checks
        fill_val = elem.get("fill")
        if fill_val and fill_val.lower() != "none" and not fill_val.startswith("url"):
            hex_c = validate_hex_color(fill_val)
            if hex_c:
                color_counts[hex_c] += 1

        stroke_val = elem.get("stroke")
        if stroke_val and stroke_val.lower() != "none" and not stroke_val.startswith("url"):
            hex_s = validate_hex_color(stroke_val)
            if hex_s:
                color_counts[hex_s] += 1
                stroke_counts[hex_s] += 1

        width_val = elem.get("stroke-width")
        if width_val:
            try:
                # Remove px or pt if present
                clean_w = re.sub(r"[^\d.]", "", width_val)
                if clean_w:
                    val_f = float(clean_w)
                    if val_f > 0:
                        stroke_widths.append(val_f)
            except Exception:
                pass

    # Select top 8 hex colors for palette
    top_colors = [c for c, _ in color_counts.most_common(8)]
    if not top_colors:
        top_colors = ["#1b1516", "#ffffff", "#3b82f6"]

    # Dominant outline color
    outline_color = stroke_counts.most_common(1)[0][0] if stroke_counts else top_colors[0]

    # Representative stroke width (median or mode)
    if stroke_widths:
        sorted_w = sorted(stroke_widths)
        rep_stroke_width = round(sorted_w[len(sorted_w) // 2], 1)
    else:
        rep_stroke_width = 5.0

    # Highlight color: pick a vibrant accent from top colors distinct from outline
    highlight_color = "#38bdf8"
    for c in top_colors:
        if c != outline_color and c not in ("#ffffff", "#000000", "#1b1516", "#0f172a"):
            highlight_color = c
            break

    return {
        "palette": top_colors[:8],
        "stroke_width": rep_stroke_width,
        "outline_color": outline_color,
        "fill_style": "flat_solid",
        "roughness": 0.0,
        "font_family": "Arial, sans-serif",
        "highlight_color": highlight_color,
    }


def build_style_profile_for_pack(
    pack_id: str,
    characters_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Extracts style data from the character pack, determines contact sheet path,
    generates a style description for image prompts, and writes assets/style/<pack_id>.style.json.
    """
    if characters_dir is None:
        characters_dir = config.PROJECT_ROOT / "assets" / "2d" / "characters"
    if output_dir is None:
        output_dir = config.PROJECT_ROOT / "assets" / "style"

    pack_dir = characters_dir / pack_id
    if not pack_dir.is_dir():
        raise FileNotFoundError(f"Character pack directory not found: {pack_dir}")

    # Find primary SVG file: check vector/character.svg then character.svg
    svg_candidate = pack_dir / "vector" / "character.svg"
    if not svg_candidate.is_file():
        svg_candidate = pack_dir / "character.svg"
    if not svg_candidate.is_file():
        # Search any svg
        svg_files = list(pack_dir.glob("*.svg"))
        if svg_files:
            svg_candidate = svg_files[0]
        else:
            raise FileNotFoundError(f"No valid SVG found in character pack {pack_id}")

    style_data = extract_style_from_svg(svg_candidate)

    # Find reference contact sheet
    contact_sheet_path = ""
    preview_candidates = [
        pack_dir / "staging" / f"{pack_id}_preview_sheet.png",
        pack_dir / "staging" / f"{pack_id}_contact_sheet.png",
        pack_dir / f"{pack_id}_preview.png",
    ]
    for cand in preview_candidates:
        if cand.is_file():
            contact_sheet_path = str(cand.relative_to(config.PROJECT_ROOT)).replace("\\", "/")
            break

    # Construct one-paragraph style description for image prompts
    palette_str = ", ".join(style_data["palette"][:5])
    style_desc = (
        f"2D modern animated vector cartoon style with crisp {style_data['stroke_width']}px "
        f"solid outlines in {style_data['outline_color']}, vibrant flat color fills with harmonic "
        f"palette ({palette_str}), subtle geometric shadows, zero sketchy roughness, expressive clean "
        f"facial features, and electric highlight accents in {style_data['highlight_color']}."
    )

    profile = {
        "pack_id": pack_id,
        "palette": style_data["palette"],
        "stroke_width": style_data["stroke_width"],
        "outline_color": style_data["outline_color"],
        "fill_style": style_data["fill_style"],
        "roughness": style_data["roughness"],
        "font_family": style_data["font_family"],
        "highlight_color": style_data["highlight_color"],
        "style_description": style_desc,
        "reference_contact_sheet": contact_sheet_path,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{pack_id}.style.json"
    out_file.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    logger.info("Saved style profile to %s", out_file)
    return profile


def calculate_style_distance(profile_a: Dict[str, Any], profile_b: Dict[str, Any]) -> float:
    """
    Computes a normalized difference metric in [0.0, 1.0] between two style profiles:
    - Outline color exact match (0.35 weight)
    - Stroke width difference ratio (0.30 weight)
    - Palette overlap (0.20 weight)
    - Roughness difference (0.15 weight)
    """
    # 1. Outline color mismatch
    color_diff = 0.0 if profile_a.get("outline_color") == profile_b.get("outline_color") else 1.0

    # 2. Stroke width difference ratio
    w_a = float(profile_a.get("stroke_width", 5.0))
    w_b = float(profile_b.get("stroke_width", 5.0))
    max_w = max(w_a, w_b, 1.0)
    width_diff = min(1.0, abs(w_a - w_b) / max_w)

    # 3. Palette overlap (Jaccard distance)
    pal_a = set(profile_a.get("palette", []))
    pal_b = set(profile_b.get("palette", []))
    if pal_a and pal_b:
        jaccard = 1.0 - (len(pal_a & pal_b) / float(len(pal_a | pal_b)))
    else:
        jaccard = 0.5

    # 4. Roughness difference
    r_a = float(profile_a.get("roughness", 0.0))
    r_b = float(profile_b.get("roughness", 0.0))
    rough_diff = min(1.0, abs(r_a - r_b))

    distance = (0.35 * color_diff) + (0.30 * width_diff) + (0.20 * jaccard) + (0.15 * rough_diff)
    return round(distance, 3)


def resolve_video_style_profile(
    character_names: List[str],
    explicit_style_pack: Optional[str] = None,
    threshold: float = 0.55,
    style_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Enforces 'One style per video':
    - Resolves style profiles for all characters in the cast.
    - If characters differ beyond threshold and no explicit style_pack is provided:
      warns and raises ValueError requiring an explicit style_pack. Never mix styles silently.
    - Returns the resolved primary style profile.
    """
    if style_dir is None:
        style_dir = config.PROJECT_ROOT / "assets" / "style"

    # Explicit override provided in brief
    if explicit_style_pack:
        style_file = style_dir / f"{explicit_style_pack}.style.json"
        if not style_file.is_file():
            build_style_profile_for_pack(explicit_style_pack, output_dir=style_dir)
        return json.loads(style_file.read_text(encoding="utf-8"))

    if not character_names:
        return build_style_profile_for_pack("presenter", output_dir=style_dir)

    profiles = []
    for c_name in character_names:
        style_file = style_dir / f"{c_name}.style.json"
        if not style_file.is_file():
            try:
                prof = build_style_profile_for_pack(c_name, output_dir=style_dir)
            except Exception as e:
                logger.warning("Could not build style profile for %s: %s", c_name, e)
                continue
        else:
            prof = json.loads(style_file.read_text(encoding="utf-8"))
        profiles.append(prof)

    if not profiles:
        return build_style_profile_for_pack("presenter", output_dir=style_dir)

    # Check pairwise consistency across characters
    primary = profiles[0]
    for other in profiles[1:]:
        dist = calculate_style_distance(primary, other)
        if dist > threshold:
            msg = (
                f"Style mismatch detected between '{primary.get('pack_id')}' and '{other.get('pack_id')}' "
                f"(distance: {dist:.3f} > threshold {threshold}). "
                f"Explicit 'style_pack' must be specified in the brief. Never mix styles silently."
            )
            logger.warning(msg)
            raise ValueError(msg)

    return primary
