"""
Purpose: Unit tests for visual style profile extraction, color validation, and multi-character consistency.
Inputs: SVGs, character packs, style distance comparisons, and security test payloads.
Outputs: Verified hex colors, XXE/script security rejection, style distance thresholds, and pack extraction.
Depends on: pytest, toonshorts.core.style_profile
Used by: tests
Config keys: None
Tests: tests/unit/test_style_profile.py
"""

from pathlib import Path
import json
import pytest

from toonshorts.core.style_profile import (
    build_style_profile_for_pack,
    calculate_style_distance,
    extract_style_from_svg,
    resolve_video_style_profile,
    safe_parse_svg,
    validate_hex_color,
)


def test_validate_hex_color():
    """Validates 3-digit and 6-digit hex colors and normalizes to #rrggbb lowercase."""
    assert validate_hex_color("#fff") == "#ffffff"
    assert validate_hex_color("#1B1516") == "#1b1516"
    assert validate_hex_color("#3b689a") == "#3b689a"
    assert validate_hex_color("rgb(0,0,0)") is None
    assert validate_hex_color("blue") is None
    assert validate_hex_color("not_a_color") is None
    assert validate_hex_color("") is None


def test_safe_parse_svg_security_rejections():
    """Rejects XXE entity injections, DOCTYPE declarations, and malicious script elements."""
    xxe_svg = '<!DOCTYPE svg [<!ENTITY xxe SYSTEM "http://malicious.com/evil">]><svg>&xxe;</svg>'
    with pytest.raises(ValueError, match="Security violation: DOCTYPE and ENTITY"):
        safe_parse_svg(xxe_svg)

    script_svg = '<svg><script>alert("xss")</script><rect width="10" height="10"/></svg>'
    with pytest.raises(ValueError, match="Security violation: Script or embedded"):
        safe_parse_svg(script_svg)

    iframe_svg = '<svg><iframe>http://evil.com</iframe></svg>'
    with pytest.raises(ValueError, match="Security violation: Script or embedded"):
        safe_parse_svg(iframe_svg)


def test_extract_style_from_svg(tmp_path: Path):
    """Extracts top colors (max 8), representative stroke width, and outline color."""
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <rect x="0" y="0" width="100" height="100" fill="#3b689a" stroke="#1b1516" stroke-width="6" />
      <circle cx="50" cy="50" r="30" fill="#fed7aa" stroke="#1b1516" stroke-width="4" />
      <path d="M10 10 L90 90" stroke="#1b1516" stroke-width="5" />
      <circle cx="20" cy="20" r="5" fill="#38bdf8" />
    </svg>"""
    test_svg = tmp_path / "test_char.svg"
    test_svg.write_text(svg_content, encoding="utf-8")

    style = extract_style_from_svg(test_svg)
    assert len(style["palette"]) <= 8
    assert all(c.startswith("#") and len(c) == 7 for c in style["palette"])
    assert style["outline_color"] == "#1b1516"
    assert style["stroke_width"] in (4.0, 5.0, 6.0)
    assert style["fill_style"] == "flat_solid"
    assert style["roughness"] == 0.0


def test_build_style_profile_for_existing_pack(tmp_path: Path):
    """Extracts and saves a full style profile for boy_b pack."""
    profile = build_style_profile_for_pack("boy_b", output_dir=tmp_path)
    assert profile["pack_id"] == "boy_b"
    assert len(profile["palette"]) <= 8
    assert profile["outline_color"].startswith("#")
    assert profile["stroke_width"] > 0
    assert "style_description" in profile
    assert len(profile["style_description"]) > 50
    assert "reference_contact_sheet" in profile
    assert (tmp_path / "boy_b.style.json").is_file()


def test_calculate_style_distance_identical_and_different():
    """Identical profiles have 0 distance; widely different profiles have high distance."""
    prof1 = {
        "outline_color": "#1b1516",
        "stroke_width": 5.0,
        "palette": ["#1b1516", "#3b689a", "#ffffff"],
        "roughness": 0.0,
    }
    prof2 = dict(prof1)
    assert calculate_style_distance(prof1, prof2) == 0.0

    different_prof = {
        "outline_color": "#ffffff",
        "stroke_width": 45.0,
        "palette": ["#ffffff", "#00ff00"],
        "roughness": 1.5,
    }
    dist = calculate_style_distance(prof1, different_prof)
    assert dist > 0.60


def test_resolve_video_style_profile_single_style_rule(tmp_path: Path):
    """Detects style divergence between mismatched character styles and requires explicit style_pack."""
    # Write two divergent style files
    style_a = {
        "pack_id": "clean_boy",
        "outline_color": "#1b1516",
        "stroke_width": 4.0,
        "palette": ["#1b1516", "#3b689a"],
        "roughness": 0.0,
    }
    style_b = {
        "pack_id": "heavy_sketch",
        "outline_color": "#ffffff",
        "stroke_width": 40.0,
        "palette": ["#ffffff", "#ff0000"],
        "roughness": 2.0,
    }
    (tmp_path / "clean_boy.style.json").write_text(json.dumps(style_a), encoding="utf-8")
    (tmp_path / "heavy_sketch.style.json").write_text(json.dumps(style_b), encoding="utf-8")

    # Mismatched characters raise ValueError when no explicit style_pack is provided
    with pytest.raises(ValueError, match="Explicit 'style_pack' must be specified in the brief"):
        resolve_video_style_profile(
            character_names=["clean_boy", "heavy_sketch"],
            style_dir=tmp_path,
        )

    # With explicit style_pack specified, resolution succeeds cleanly
    resolved = resolve_video_style_profile(
        character_names=["clean_boy", "heavy_sketch"],
        explicit_style_pack="clean_boy",
        style_dir=tmp_path,
    )
    assert resolved["pack_id"] == "clean_boy"
