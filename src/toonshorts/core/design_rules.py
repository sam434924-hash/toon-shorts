"""
Purpose: Design system tokens, modular typography scales, layout rules, and CSS variables single source of truth.
Inputs: Design tokens JSON specification and per-video theme parameter overrides.
Outputs: Validated design rules, CSS variables block, and WCAG contrast assertions.
Depends on: json, logging, pathlib, typing
Used by: cli, core.design_judge, core.pipeline, plugins.render.animejs.html_builder
Config keys: None
Tests: tests/unit/test_design_judge.py
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("toonshorts.design_rules")

DESIGN_RULES_PATH = Path(__file__).resolve().parent.parent / "styles" / "design_rules.json"

_RULES_CACHE: Optional[Dict[str, Any]] = None


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Converts hex color string (#RRGGBB or #RGB) to RGB integer tuple."""
    clean = hex_str.lstrip("#")
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    return int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)


def find_theme_file(
    video_name: Optional[str] = None,
    video_dir: Optional[Union[str, Path]] = None,
) -> Optional[Path]:
    """Resolves per-video theme file path if one exists, otherwise returns None."""
    candidates: List[Path] = []
    if video_dir:
        vd = Path(video_dir).resolve()
        candidates.append(vd / "theme.json")
        candidates.append(vd / f"{vd.name}_theme.json")
    if video_name:
        root = Path(__file__).resolve().parent.parent.parent.parent
        candidates.append(root / "briefs" / f"{video_name}_theme.json")
        candidates.append(root / "videos" / video_name / "theme.json")
        candidates.append(Path(__file__).resolve().parent.parent / "styles" / "themes" / f"{video_name}.json")

    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def load_theme_for_video(
    video_name: Optional[str] = None,
    video_dir: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Loads per-video theme dictionary if defined for the video, else returns None."""
    theme_path = find_theme_file(video_name=video_name, video_dir=video_dir)
    if not theme_path:
        return None
    try:
        return json.loads(theme_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load theme from %s: %s", theme_path, exc)
        return None


def merge_theme_into_rules(
    global_rules: Dict[str, Any],
    theme: Optional[Union[str, Path, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Applies per-video theme overrides onto global design rules."""
    merged = json.loads(json.dumps(global_rules))
    if not theme:
        return merged

    theme_data: Dict[str, Any] = {}
    if isinstance(theme, (str, Path)):
        p = Path(theme).resolve()
        if p.is_file():
            try:
                theme_data = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Could not read theme file %s: %s", p, e)
    elif isinstance(theme, dict):
        theme_data = theme

    if not theme_data:
        return merged

    merged["theme_applied"] = theme_data.get("theme_name") or theme_data.get("name", "custom_theme")
    if "background_style" in theme_data:
        merged["background_style"] = theme_data["background_style"]

    # Palette roles override
    palette = theme_data.get("palette") or theme_data.get("color")
    if palette and isinstance(palette, dict):
        merged.setdefault("color", {})
        for k, v in palette.items():
            if isinstance(v, dict) and k in merged["color"] and isinstance(merged["color"][k], dict):
                merged["color"][k].update(v)
            else:
                merged["color"][k] = v

    return merged


def load_design_rules(
    custom_path: Optional[Path] = None,
    theme: Optional[Union[str, Path, Dict[str, Any]]] = None,
    video_name: Optional[str] = None,
    video_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Loads global design rules, overlaid with per-video theme if present."""
    global _RULES_CACHE
    path = custom_path or DESIGN_RULES_PATH
    if _RULES_CACHE is not None and custom_path is None:
        base_data = _RULES_CACHE
    else:
        try:
            base_data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load design rules from %s: %s; using defaults", path, exc)
            base_data = get_default_design_rules()
        if custom_path is None:
            _RULES_CACHE = base_data

    # Resolve theme if not explicitly provided
    resolved_theme = theme
    if resolved_theme is None and (video_name or video_dir):
        resolved_theme = load_theme_for_video(video_name=video_name, video_dir=video_dir)

    return merge_theme_into_rules(base_data, resolved_theme)


def get_default_design_rules() -> Dict[str, Any]:
    """Fallback programmatic definition of design system rules."""
    return {
        "color": {
            "dominant": {"hex": "#F7F4FF", "target_share": 0.60},
            "secondary": {
                "deep": {"hex": "#3D1F7A"},
                "mid": {"hex": "#6D3FD0"},
                "text": {"hex": "#1B1240"},
                "target_share": 0.30,
            },
            "accent": {
                "hex": "#FFB800",
                "target_share": 0.10,
                "min_share": 0.05,
                "max_share": 0.15,
                "max_card_fill_share": 0.10,
            },
            "meaning": {
                "done_safe": {"hex": "#17B8A6"},
                "danger_blocked": {"hex": "#E5484D"},
                "agent_ai": {"hex": "#6D3FD0"},
                "key_item": {"hex": "#FFB800"},
            },
            "rules": {
                "max_hues_per_board": 3,
                "color_by_meaning_only": True,
                "min_text_contrast": 4.5,
            },
        },
        "typography": {
            "modular_scale": {
                "ratio": 1.333,
                "base_px": 48,
                "scale": {"smallest": 48, "card_title": 64, "scene_title": 85, "hero": 114},
            },
            "min_board_font_px": 48,
            "caption": {"font_size_min_px": 60, "font_size_max_px": 75, "font_size_target_px": 68, "max_lines": 2},
        },
        "spacing_and_shape": {
            "grid_step_px": 24,
            "card_corner_radius_px": 24,
            "card_stroke_width_px": 4,
            "uniform_card_height": True,
        },
        "safe_zone": {
            "viewport_width": 1080,
            "viewport_height": 1920,
            "top_cutoff_px": 230,
            "bottom_cutoff_px": 1535,
            "margin_x_min_px": 60,
            "max_empty_strip_px": 120,
        },
        "board_fill": {
            "top_target_px": 230,
            "content_start_max_offset_px": 48,
            "content_coverage_min": 0.50,
            "content_coverage_max": 0.78,
            "hero_element_coverage_min": 0.40,
            "board_height_safe_area_ratio_min": 0.45,
            "min_whitespace_ratio": 0.20,
        },
        "character_proportions": {
            "height_ratio_to_board_min": 0.55,
            "height_ratio_to_board_max": 0.70,
            "shared_floor_line": True,
            "feet_max_y_px": 1535,
        },
        "layout_rules": {
            "max_card_columns": 1,
            "max_words_per_line": 6,
            "max_cards_per_scene": 3,
            "no_long_all_caps": True,
        },
    }


def generate_css_variables(rules: Optional[Dict[str, Any]] = None) -> str:
    """Generates a standard CSS :root token variables block from design rules."""
    r = rules or load_design_rules()
    c = r.get("color", {})
    dom = c.get("dominant", {}).get("hex", "#F7F4FF")
    sec_deep = c.get("secondary", {}).get("deep", {}).get("hex", "#3D1F7A")
    sec_mid = c.get("secondary", {}).get("mid", {}).get("hex", "#6D3FD0")
    text_dark = c.get("secondary", {}).get("text", {}).get("hex", "#1B1240")
    accent = c.get("accent", {}).get("hex", "#FFB800")
    teal = c.get("meaning", {}).get("done_safe", {}).get("hex", "#17B8A6")
    red = c.get("meaning", {}).get("danger_blocked", {}).get("hex", "#E5484D")

    scale = r.get("typography", {}).get("modular_scale", {}).get("scale", {})
    cap_px = r.get("typography", {}).get("caption", {}).get("font_size_target_px", 68)

    sp = r.get("spacing_and_shape", {})
    grid_px = sp.get("grid_step_px", 24)
    radius_px = sp.get("card_corner_radius_px", 24)
    stroke_px = sp.get("card_stroke_width_px", 4)

    bf = r.get("board_fill", {})
    board_top = bf.get("top_target_px", 230)

    css = f""":root {{
  /* Design System Color Tokens */
  --color-dominant: {dom};
  --color-secondary-deep: {sec_deep};
  --color-secondary-mid: {sec_mid};
  --color-text-dark: {text_dark};
  --color-accent: {accent};
  --color-meaning-teal: {teal};
  --color-meaning-red: {red};
  --color-meaning-purple: {sec_mid};
  --color-meaning-amber: {accent};

  /* Typography Modular Scale (1.333 ratio from 48px) */
  --font-hero: {scale.get("hero", 114)}px;
  --font-scene-title: {scale.get("scene_title", 85)}px;
  --font-card-title: {scale.get("card_title", 64)}px;
  --font-body-min: {scale.get("smallest", 48)}px;
  --font-caption: {cap_px}px;

  /* Spacing and Geometry */
  --grid-step: {grid_px}px;
  --card-radius: {radius_px}px;
  --card-stroke: {stroke_px}px;
  --board-top: {board_top}px;
}}
"""
    return css
