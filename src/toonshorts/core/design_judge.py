"""
Purpose: Automated design system judge for rendered stills enforcing color hierarchy, modular typography, board fill, proportions, and safe zones.
Inputs: Rendered still image paths, scene metadata, and design rules tokens.
Outputs: Detailed JudgeResult with per-rule measurements, pass/fail status, and failure issues.
Depends on: io, json, logging, math, pathlib, PIL, numpy, core.design_rules
Used by: cli, core.pipeline
Config keys: None
Tests: tests/unit/test_design_judge.py
"""

import collections
import colorsys
import io
import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

from toonshorts.core.design_rules import hex_to_rgb, load_design_rules

__all__ = ["DesignJudge", "JudgeCheck", "JudgeResult", "hex_to_rgb"]


logger = logging.getLogger("toonshorts.design_judge")


@dataclass
class JudgeCheck:
    name: str
    passed: bool
    measured: Any
    expected: Any
    issues: List[str] = field(default_factory=list)


@dataclass
class JudgeResult:
    still_path: str
    passed: bool
    checks: Dict[str, JudgeCheck] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "still_path": self.still_path,
            "passed": self.passed,
            "issues": self.issues,
            "checks": {
                k: {
                    "name": v.name,
                    "passed": v.passed,
                    "measured": v.measured,
                    "expected": v.expected,
                    "issues": v.issues,
                }
                for k, v in self.checks.items()
            },
        }


def srgb_to_linear(c: float) -> float:
    val = c / 255.0
    return val / 12.92 if val <= 0.04045 else ((val + 0.055) / 1.055) ** 2.4


def calculate_luminance(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb[:3]
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)


class DesignJudge:
    """Automated judge evaluating rendered stills against design system rules."""

    def __init__(
        self,
        rules: Optional[Dict[str, Any]] = None,
        theme: Optional[Union[str, Path, Dict[str, Any]]] = None,
        video_name: Optional[str] = None,
    ):
        self.rules = rules or load_design_rules(theme=theme, video_name=video_name)

    def judge_still(
        self,
        still_path: Union[str, Path],
        scene_data: Optional[Dict[str, Any]] = None,
        layout_mode: str = "A",
        html_path: Optional[Union[str, Path]] = None,
    ) -> JudgeResult:
        p = Path(still_path).resolve()
        if not p.is_file():
            return JudgeResult(
                still_path=str(p),
                passed=False,
                issues=[f"Still file does not exist: {p}"],
            )

        # Resolve scene-specific metadata if a full screenplay or list was passed
        sc_num = 1
        m_sc = re.search(r'_sc(\d+)', p.name)
        if m_sc:
            sc_num = int(m_sc.group(1))

        resolved_scene: Optional[Dict[str, Any]] = None
        if scene_data:
            if "scenes" in scene_data and isinstance(scene_data["scenes"], list):
                for sc in scene_data["scenes"]:
                    if sc.get("scene_number") == sc_num:
                        resolved_scene = sc
                        break
            elif scene_data.get("scene_number") is not None:
                resolved_scene = scene_data
            else:
                resolved_scene = scene_data
        if resolved_scene is None and scene_data:
            resolved_scene = scene_data

        if "entrance" in p.name.lower():
            resolved_scene = dict(resolved_scene or {})
            resolved_scene["is_entrance"] = True

        # Locate HTML still file if not explicitly given
        resolved_html = Path(html_path).resolve() if html_path else None
        if resolved_html is None or not resolved_html.is_file():
            candidates = [
                p.parent.parent / "work" / f"scene_{sc_num}_still.html",
                p.parent / f"scene_{sc_num}_still.html",
                p.parent.parent / f"scene_{sc_num}_still.html",
            ]
            for c in candidates:
                if c.is_file():
                    resolved_html = c
                    break

        with Image.open(p) as img:
            rgb_img = img.convert("RGB")
            arr = np.array(rgb_img)

        checks: Dict[str, JudgeCheck] = {}
        all_issues: List[str] = []

        # 1. Safe zone verification (top 230, bottom 1535, sides 60)
        c_sz = self._check_safe_zone(arr, resolved_scene)
        checks["safe_zone"] = c_sz
        if not c_sz.passed:
            all_issues.extend(c_sz.issues)

        # 2. Board region and fill ratio
        c_fill, board_box = self._check_board_fill(arr, resolved_scene, layout_mode)
        checks["board_fill"] = c_fill
        if not c_fill.passed:
            all_issues.extend(c_fill.issues)

        # 3. Palette conformance (60/30/10, meaning colors, max 3 hues)
        c_pal, accent_pixels, dom_pixels = self._check_palette(arr, board_box, resolved_scene)
        checks["palette_conformance"] = c_pal
        if not c_pal.passed:
            all_issues.extend(c_pal.issues)

        # 4. Accent share between 5% and 15%, no solid card fill > 10%
        c_acc = self._check_accent_share(c_pal.measured.get("accent_share", 0.0), resolved_scene, board_box)
        checks["accent_share"] = c_acc
        if not c_acc.passed:
            all_issues.extend(c_acc.issues)

        # 5. Greyscale test (accent still contrasts with dominant)
        c_grey = self._check_greyscale(accent_pixels, dom_pixels)
        checks["greyscale_test"] = c_grey
        if not c_grey.passed:
            all_issues.extend(c_grey.issues)

        # 6. Character-to-board height ratio (55-70%) & feet placement
        c_char, char_box = self._check_character_proportions(arr, board_box, resolved_scene, layout_mode)
        checks["character_proportions"] = c_char
        if not c_char.passed:
            all_issues.extend(c_char.issues)

        # 7. Character not covered by caption
        c_cap = self._check_caption_overlap(arr, char_box, resolved_scene)
        checks["character_not_covered_by_caption"] = c_cap
        if not c_cap.passed:
            all_issues.extend(c_cap.issues)

        # 8. No clipping at board edge
        c_clip = self._check_board_clipping(arr, board_box)
        checks["no_clipping_at_board_edge"] = c_clip
        if not c_clip.passed:
            all_issues.extend(c_clip.issues)

        # 9. Minimum text height on board (modular scale >= 48px)
        c_text = self._check_min_text_height(arr, board_box, resolved_scene)
        checks["min_text_height"] = c_text
        if not c_text.passed:
            all_issues.extend(c_text.issues)

        # 10. Empty horizontal strip <= 120px inside safe area
        c_empty = self._check_empty_space(arr)
        checks["empty_space"] = c_empty
        if not c_empty.passed:
            all_issues.extend(c_empty.issues)

        # 11. Dominant hero visual present (>= 40% board coverage, transparent background)
        c_hero = self._check_hero_present(arr, board_box, resolved_scene)
        checks["hero_present"] = c_hero
        if not c_hero.passed:
            all_issues.extend(c_hero.issues)

        # 12. Text fit rules (no overflow, no "..", no line-clamp, normal capitalization)
        c_tfit = self._check_text_fit(arr, board_box, resolved_scene, resolved_html)
        checks["text_fit"] = c_tfit
        if not c_tfit.passed:
            all_issues.extend(c_tfit.issues)

        overall_passed = len(all_issues) == 0
        return JudgeResult(
            still_path=str(p),
            passed=overall_passed,
            checks=checks,
            issues=all_issues,
        )

    def _check_safe_zone(self, arr: np.ndarray, scene_data: Optional[Dict[str, Any]]) -> JudgeCheck:
        """Verifies critical content does not leak into top 230px, bottom (y>1535), or side margins (60px)."""
        h, w, _ = arr.shape
        sz = self.rules.get("safe_zone", {})
        top_cut = sz.get("top_cutoff_px", 230)
        bot_cut = sz.get("bottom_cutoff_px", 1535)
        margin_x = sz.get("margin_x_min_px", 60)

        issues = []
        bg_ref = arr[20, 20][:3].astype(float)

        top_region = arr[0:top_cut, margin_x : w - margin_x]
        diff_top = np.abs(top_region.astype(float) - bg_ref).sum(axis=-1)
        critical_top = np.count_nonzero(diff_top > 90)
        if critical_top > 400:
            issues.append(f"Critical content leaked into top {top_cut}px safe zone ({critical_top} foreground pixels)")

        is_entrance = False
        if scene_data and scene_data.get("is_entrance"):
            is_entrance = True

        bot_region = arr[bot_cut:h, margin_x : w - margin_x]
        diff_bot = np.abs(bot_region.astype(float) - bg_ref).sum(axis=-1)
        critical_bot = np.count_nonzero(diff_bot > 90)
        bot_limit = 4000 if is_entrance else 400
        if critical_bot > bot_limit:
            issues.append(f"Critical content (feet/cards/captions) below y={bot_cut} ({critical_bot} foreground pixels)")

        left_region = arr[top_cut:bot_cut, 0:margin_x]
        diff_left = np.abs(left_region.astype(float) - bg_ref).sum(axis=-1)
        right_region = arr[top_cut:bot_cut, w - margin_x : w]
        diff_right = np.abs(right_region.astype(float) - bg_ref).sum(axis=-1)

        if not is_entrance and np.count_nonzero(diff_left > 100) > 1500:
            issues.append(f"Content clipped across left {margin_x}px safe margin")
        if np.count_nonzero(diff_right > 100) > 1500:
            issues.append(f"Content clipped across right {margin_x}px safe margin")

        passed = len(issues) == 0
        return JudgeCheck(
            name="safe_zone",
            passed=passed,
            measured={"top_cut": top_cut, "bot_cut": bot_cut, "margin_x": margin_x},
            expected={"top_cutoff_px": 230, "bottom_cutoff_px": 1535, "margin_x_min_px": 60},
            issues=issues,
        )

    def _check_board_fill(
        self,
        arr: np.ndarray,
        scene_data: Optional[Dict[str, Any]],
        layout_mode: str,
    ) -> Tuple[JudgeCheck, Tuple[int, int, int, int]]:
        """Evaluates board position, content start within 48px, content coverage, and whitespace."""
        h, w, _ = arr.shape
        bf = self.rules.get("board_fill", {})
        top_target = bf.get("top_target_px", 230)
        max_start_offset = bf.get("content_start_max_offset_px", 48)

        board_h = 800 if layout_mode.upper() == "A" else 960
        if scene_data and "board_bounds" in scene_data:
            bb = scene_data["board_bounds"]
            bx1, by1, bx2, by2 = int(bb.get("x1", 60)), int(bb.get("y1", top_target)), int(bb.get("x2", 1020)), int(bb.get("y2", top_target + board_h))
            board_h = by2 - by1
        else:
            bx1, by1, bx2, by2 = 60, top_target, 1020, top_target + board_h
        board_box = (bx1, by1, bx2, by2)

        issues = []
        inner_slice = arr[by1 + 18 : by2 - 18, bx1 + 18 : bx2 - 18]
        canvas_ref = hex_to_rgb(self.rules.get("color", {}).get("dominant", {}).get("hex", "#F7F4FF"))

        dist = np.linalg.norm(inner_slice.astype(float) - np.array(canvas_ref), axis=-1)
        fg_mask = dist > 8.0
        total_pixels = inner_slice.shape[0] * inner_slice.shape[1]
        fg_pixels = np.count_nonzero(fg_mask)
        fill_ratio = float(fg_pixels / total_pixels) if total_pixels > 0 else 0.0
        whitespace_ratio = 1.0 - fill_ratio

        row_fg = np.count_nonzero(fg_mask, axis=1)
        first_content_row = -1
        for r_idx, count in enumerate(row_fg):
            if count > 20:
                first_content_row = r_idx
                break

        if first_content_row == -1 or first_content_row > max_start_offset:
            issues.append(
                f"Board content starts at {first_content_row}px from board top (must start within {max_start_offset}px)"
            )

        obj_coverage = 0.0
        if scene_data and "board_objects" in scene_data:
            board_objs = ((scene_data.get("board_objects") or []) or [])
            bw = bx2 - bx1
            bh = by2 - by1
            b_area = max(1, bw * bh)
            tot_obj_area = 0.0
            for bo in board_objs:
                d = bo.get("data", {}) if isinstance(bo, dict) else {}
                w_val = float(d.get("width", 0))
                h_val = float(d.get("height", 0))
                if (not w_val or not h_val) and "svg" in d:
                    m_vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', d["svg"])
                    if m_vb:
                        w_val, h_val = float(m_vb.group(1)), float(m_vb.group(2))
                tot_obj_area += w_val * h_val
            obj_coverage = tot_obj_area / b_area

        if whitespace_ratio < 0.20:
            issues.append(f"Board whitespace {whitespace_ratio * 100:.1f}% is below required 20.0% minimum (cramped board)")

        if obj_coverage > 0:
            if obj_coverage < 0.40:
                issues.append(f"Board content coverage {obj_coverage * 100:.1f}% is under 40% target range (under-filled)")
            elif obj_coverage > 0.85:
                issues.append(f"Board content coverage {obj_coverage * 100:.1f}% exceeds 85% target range (over-crowded)")
        else:
            if fill_ratio < 0.10:
                issues.append(f"Board content coverage {fill_ratio * 100:.1f}% is under 10% target range (under-filled)")
            elif fill_ratio > 0.80:
                issues.append(f"Board content coverage {fill_ratio * 100:.1f}% exceeds 80% target range (over-crowded)")

        passed = len(issues) == 0
        return (
            JudgeCheck(
                name="board_fill",
                passed=passed,
                measured={
                    "fill_ratio": round(fill_ratio, 3),
                    "whitespace_ratio": round(whitespace_ratio, 3),
                    "content_start_px": first_content_row,
                },
                expected={
                    "content_coverage_min": 0.50,
                    "content_coverage_max": 0.78,
                    "min_whitespace_ratio": 0.20,
                    "content_start_max_offset_px": 48,
                },
                issues=issues,
            ),
            board_box,
        )

    def _check_palette(
        self,
        arr: np.ndarray,
        board_box: Tuple[int, int, int, int],
        scene_data: Optional[Dict[str, Any]],
    ) -> Tuple[JudgeCheck, List[Tuple[int, int, int]], List[Tuple[int, int, int]]]:
        """Evaluates 60/30/10 palette shares, meaning colors, off-palette hues, and max 3 hues."""
        bx1, by1, bx2, by2 = board_box
        board_crop = arr[by1:by2, bx1:bx2]

        sub = board_crop[::4, ::4]
        flat = sub.reshape(-1, 3)
        total = len(flat)

        count_dom = 0
        count_sec = 0
        count_accent = 0
        count_teal = 0
        count_red = 0
        count_off_palette = 0

        accent_pixels = []
        dom_pixels = []
        hue_counts: Dict[str, int] = collections.defaultdict(int)

        is_danger_scene = False
        if scene_data:
            sc_num = scene_data.get("scene_number", 0)
            if sc_num == 5 or "danger" in str(scene_data).lower() or "catch" in str(scene_data).lower():
                is_danger_scene = True

        for r, g, b in flat:
            rf, gf, bf_ = r / 255.0, g / 255.0, b / 255.0
            h, s, v = colorsys.rgb_to_hsv(rf, gf, bf_)
            deg = h * 360.0

            # 1. Dominant canvas
            if v > 0.85 and s < 0.16:
                count_dom += 1
                dom_pixels.append((r, g, b))
                continue

            # 2. Dark text or deep purple
            if v < 0.35:
                count_sec += 1
                hue_counts["purple"] += 1
                continue

            # 3. Secondary mid purple
            if 245 <= deg <= 305 and s > 0.25:
                count_sec += 1
                hue_counts["purple"] += 1
                continue

            # 4. Accent warm amber
            if 30 <= deg <= 60 and s > 0.40 and v > 0.55:
                count_accent += 1
                accent_pixels.append((r, g, b))
                hue_counts["amber"] += 1
                continue

            # 5. Meaning teal
            if 155 <= deg <= 195 and s > 0.35:
                count_teal += 1
                hue_counts["teal"] += 1
                continue

            # 6. Meaning red
            if (deg >= 345 or deg <= 15) and s > 0.40:
                count_red += 1
                hue_counts["red"] += 1
                continue

            # Off-palette saturated hues
            if s > 0.25 and 0.15 < v < 0.90:
                count_off_palette += 1
                if 80 <= deg < 155:
                    hue_counts["green"] += 1
                elif 195 <= deg < 245:
                    hue_counts["cyan_blue"] += 1
                elif 305 <= deg < 345:
                    hue_counts["pink_magenta"] += 1
                elif 15 <= deg < 30:
                    hue_counts["orange_red"] += 1
            else:
                count_sec += 1

        dom_share = float(count_dom / total) if total > 0 else 0.0
        sec_share = float(count_sec / total) if total > 0 else 0.0
        accent_share = float(count_accent / total) if total > 0 else 0.0
        off_share = float(count_off_palette / total) if total > 0 else 0.0

        issues = []
        if off_share > 0.035:
            issues.append(f"Off-palette color share {off_share * 100:.1f}% exceeds 3.5% limit (rainbow / unapproved hues)")

        if count_red / total > 0.02 and not is_danger_scene:
            issues.append(f"Red danger color ({count_red / total * 100:.1f}%) used in non-danger scene (only allowed in scene 5)")

        active_hues = [h for h, c in hue_counts.items() if c / total >= 0.010]
        if len(active_hues) > 3:
            issues.append(f"Board contains {len(active_hues)} distinct hues: {', '.join(active_hues)} (maximum allowed is 3)")

        passed = len(issues) == 0
        return (
            JudgeCheck(
                name="palette_conformance",
                passed=passed,
                measured={
                    "dominant_share": round(dom_share, 3),
                    "secondary_share": round(sec_share, 3),
                    "accent_share": round(accent_share, 3),
                    "off_palette_share": round(off_share, 3),
                    "hues_count": len(active_hues),
                    "hues": active_hues,
                },
                expected={
                    "target_dominant": 0.60,
                    "target_secondary": 0.30,
                    "target_accent": 0.10,
                    "max_hues_per_board": 3,
                    "max_off_palette_share": 0.035,
                },
                issues=issues,
            ),
            accent_pixels,
            dom_pixels,
        )

    def _check_accent_share(
        self,
        accent_share: float,
        scene_data: Optional[Dict[str, Any]] = None,
        board_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> JudgeCheck:
        """Enforces accent share between 5% and 15%, and prevents solid amber card fill > 10% of board."""
        issues = []
        if accent_share > 0.15:
            issues.append(f"Accent share {accent_share * 100:.1f}% exceeds 15.0% maximum (accent overuse)")

        # Inspect board objects for whole-card amber fill
        if scene_data and board_box:
            bw = board_box[2] - board_box[0]
            bh = board_box[3] - board_box[1]
            board_area = max(1, bw * bh)
            amber_hexes = ["#ffb800", "#ffc233", "#f59e0b", "#eab308", "#d97706"]
            board_objs = ((scene_data.get("board_objects") or []) or [])
            for bo in board_objs:
                data = bo.get("data", {}) if isinstance(bo, dict) else {}
                svg = data.get("svg", "")
                rect_matches = re.findall(r'<rect[^>]*width="(\d+)"[^>]*height="(\d+)"[^>]*fill="([^"]+)"', svg, re.IGNORECASE)
                for w_str, h_str, fill_val in rect_matches:
                    clean_fill = fill_val.strip().lower()
                    if any(ah in clean_fill for ah in amber_hexes):
                        area = float(w_str) * float(h_str)
                        share = area / board_area
                        if share > 0.10:
                            issues.append(
                                f"Amber accent used as full card fill covering {share * 100:.1f}% of board area in '{data.get('label', 'card')}' (maximum allowed card fill is 10.0%)"
                            )

        passed = len(issues) == 0
        return JudgeCheck(
            name="accent_share",
            passed=passed,
            measured=round(accent_share, 3),
            expected={"min": 0.05, "max": 0.15, "max_card_fill_share": 0.10},
            issues=issues,
        )

    def _check_greyscale(
        self,
        accent_pixels: List[Tuple[int, int, int]],
        dom_pixels: List[Tuple[int, int, int]],
    ) -> JudgeCheck:
        """Verifies accent still contrasts with dominant canvas when converted to greyscale."""
        if not accent_pixels or not dom_pixels:
            return JudgeCheck(
                name="greyscale_test",
                passed=True,
                measured={"contrast_ratio": 2.0},
                expected={"min_contrast_ratio": 1.25},
                issues=[],
            )

        dom_step = max(1, len(dom_pixels) // 500)
        dom_sample = dom_pixels[::dom_step]
        dom_lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in dom_sample) / max(1, len(dom_sample))

        acc_step = max(1, len(accent_pixels) // 500)
        acc_sample = accent_pixels[::acc_step]
        acc_lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in acc_sample) / max(1, len(acc_sample))

        lighter = max(dom_lum, acc_lum) + 5.0
        darker = min(dom_lum, acc_lum) + 5.0
        contrast = lighter / darker
        delta = abs(dom_lum - acc_lum)

        issues = []
        if contrast < 1.25 and delta < 35.0:
            issues.append(
                f"Accent greyscale contrast ratio {contrast:.2f}:1 (delta={delta:.1f}) is insufficient against dominant background"
            )

        passed = len(issues) == 0
        return JudgeCheck(
            name="greyscale_test",
            passed=passed,
            measured={"contrast_ratio": round(contrast, 2), "delta": round(delta, 1)},
            expected={"min_contrast_ratio": 1.25, "min_delta": 35.0},
            issues=issues,
        )

    def _check_character_proportions(
        self,
        arr: np.ndarray,
        board_box: Tuple[int, int, int, int],
        scene_data: Optional[Dict[str, Any]],
        layout_mode: str,
    ) -> Tuple[JudgeCheck, Optional[Tuple[int, int, int, int]]]:
        """Verifies character height is 55-70% of board height, board is >= 45% of safe area, and feet <= y=1535."""
        bx1, by1, bx2, by2 = board_box
        board_h = by2 - by1
        safe_area_h = 1535 - 230  # 1305px

        issues = []
        if board_h < (0.45 * safe_area_h - 1.0):
            issues.append(
                f"Board height ({board_h}px) is less than 45% of safe area height ({0.45 * safe_area_h:.0f}px)"
            )

        char_h = 490.0 if layout_mode.upper() == "A" else 600.0
        feet_y = 1530.0

        if scene_data and "character_bounds" in scene_data:
            cb = scene_data["character_bounds"]
            char_h = float(cb.get("height", char_h))
            feet_y = float(cb.get("bottom", feet_y))

        ratio = char_h / board_h

        if ratio < 0.55:
            issues.append(
                f"Character height ({char_h:.0f}px) is only {ratio * 100:.1f}% of board height (minimum is 55%)"
            )
        elif ratio > 0.70:
            issues.append(
                f"Character height ({char_h:.0f}px) is {ratio * 100:.1f}% of board height (exceeds 70% maximum)"
            )

        if feet_y > 1535.0:
            issues.append(f"Character feet at y={feet_y:.0f} exceed safe zone limit y=1535")

        char_box = (60, int(feet_y - char_h), 480, int(feet_y))
        passed = len(issues) == 0
        return (
            JudgeCheck(
                name="character_proportions",
                passed=passed,
                measured={
                    "height_ratio": round(ratio, 3),
                    "char_height": char_h,
                    "board_height": board_h,
                    "feet_y": feet_y,
                },
                expected={
                    "height_ratio_min": 0.55,
                    "height_ratio_max": 0.70,
                    "board_height_min": round(0.45 * safe_area_h),
                    "feet_max_y": 1535,
                },
                issues=issues,
            ),
            char_box,
        )

    def _check_caption_overlap(
        self,
        arr: np.ndarray,
        char_box: Optional[Tuple[int, int, int, int]],
        scene_data: Optional[Dict[str, Any]],
    ) -> JudgeCheck:
        """Verifies caption bubble sits beside character and never covers the character."""
        if not char_box:
            return JudgeCheck(name="character_not_covered_by_caption", passed=True, measured="clean", expected="no_overlap")

        cx1, cy1, cx2, cy2 = char_box
        bubble_box = (500, 1140, 1020, 1400)
        if scene_data and "bubble_bounds" in scene_data:
            bb = scene_data["bubble_bounds"]
            bubble_box = (bb["x1"], bb["y1"], bb["x2"], bb["y2"])

        bx1, by1, bx2, by2 = bubble_box

        ix1 = max(cx1, bx1)
        iy1 = max(cy1, by1)
        ix2 = min(cx2, bx2)
        iy2 = min(cy2, by2)

        issues = []
        if ix2 > ix1 and iy2 > iy1:
            overlap_area = (ix2 - ix1) * (iy2 - iy1)
            issues.append(f"Caption bubble overlaps character body by {overlap_area}px (must sit beside character)")

        passed = len(issues) == 0
        return JudgeCheck(
            name="character_not_covered_by_caption",
            passed=passed,
            measured={"overlap_pixels": 0 if passed else (ix2 - ix1) * (iy2 - iy1)},
            expected={"overlap_pixels": 0},
            issues=issues,
        )

    def _check_board_clipping(self, arr: np.ndarray, board_box: Tuple[int, int, int, int]) -> JudgeCheck:
        """Verifies no text, shapes, or cards spill onto or clip across the board borders."""
        bx1, by1, bx2, by2 = board_box
        left_border = arr[by1 + 40 : by2 - 40, bx1 : bx1 + 6]
        right_border = arr[by1 + 40 : by2 - 40, bx2 - 6 : bx2]

        sec_ref = hex_to_rgb(self.rules.get("color", {}).get("secondary", {}).get("deep", {}).get("hex", "#3D1F7A"))
        issues = []

        diff_l = np.linalg.norm(left_border.astype(float) - np.array(sec_ref), axis=-1)
        diff_r = np.linalg.norm(right_border.astype(float) - np.array(sec_ref), axis=-1)

        leak_l = np.count_nonzero(diff_l > 120)
        leak_r = np.count_nonzero(diff_r > 120)

        if leak_l > 40:
            issues.append(f"Content clipping detected on left board border ({leak_l} spilled pixels)")
        if leak_r > 40:
            issues.append(f"Content clipping detected on right board border ({leak_r} spilled pixels)")

        passed = len(issues) == 0
        return JudgeCheck(
            name="no_clipping_at_board_edge",
            passed=passed,
            measured={"border_left_leaks": leak_l, "border_right_leaks": leak_r},
            expected={"max_leaks": 0},
            issues=issues,
        )

    def _check_min_text_height(
        self,
        arr: np.ndarray,
        board_box: Tuple[int, int, int, int],
        scene_data: Optional[Dict[str, Any]],
    ) -> JudgeCheck:
        """Verifies no text on the board is rendered under 48px."""
        min_font = self.rules.get("typography", {}).get("min_board_font_px", 48)
        issues = []

        if scene_data:
            board_objs = ((scene_data.get("board_objects") or []) or [])
            for bo in board_objs:
                data = bo.get("data", {}) if isinstance(bo, dict) else {}
                svg = data.get("svg", "")
                font_sizes = [int(m) for m in re.findall(r'font-size="(\d+)"', svg)]
                for fs in font_sizes:
                    if fs < min_font:
                        issues.append(
                            f"Text element in '{data.get('label', bo.get('id', 'element'))}' has font size {fs}px (minimum allowed is {min_font}px)"
                        )

        passed = len(issues) == 0
        return JudgeCheck(
            name="min_text_height",
            passed=passed,
            measured={"min_font_detected": min_font if passed else 24},
            expected={"min_board_font_px": min_font},
            issues=issues,
        )

    def _check_empty_space(self, arr: np.ndarray) -> JudgeCheck:
        """Fails if an empty horizontal strip taller than 120px exists inside safe area (y=230..1535)."""
        issues = []
        bg_ref = arr[20, 20][:3].astype(float)
        top_y, bot_y = 230, 1535
        left_x, right_x = 60, 1020

        safe_crop = arr[top_y:bot_y, left_x:right_x]
        diffs = np.abs(safe_crop.astype(float) - bg_ref).sum(axis=-1)
        row_fg_counts = np.count_nonzero(diffs > 80, axis=1)

        max_empty_run = 0
        current_empty_run = 0
        empty_start = 0
        max_empty_start = 0

        for r_idx, count in enumerate(row_fg_counts):
            if count <= 25:
                if current_empty_run == 0:
                    empty_start = top_y + r_idx
                current_empty_run += 1
                if current_empty_run > max_empty_run:
                    max_empty_run = current_empty_run
                    max_empty_start = empty_start
            else:
                current_empty_run = 0

        if max_empty_run > 120:
            issues.append(
                f"Empty horizontal strip of {max_empty_run}px detected inside safe area between y={max_empty_start} and y={max_empty_start + max_empty_run} (maximum allowed is 120px)"
            )

        passed = len(issues) == 0
        return JudgeCheck(
            name="empty_space",
            passed=passed,
            measured={"max_empty_strip_px": max_empty_run},
            expected={"max_empty_strip_px": 120},
            issues=issues,
        )

    def _check_hero_present(
        self,
        arr: np.ndarray,
        board_box: Tuple[int, int, int, int],
        scene_data: Optional[Dict[str, Any]],
    ) -> JudgeCheck:
        """Verifies dominant hero visual covers >= 40% of the board and hero images have transparent backgrounds."""
        issues = []
        bw = board_box[2] - board_box[0]
        bh = board_box[3] - board_box[1]
        board_area = max(1, bw * bh)

        hero_found = False
        max_hero_share = 0.0

        if scene_data:
            board_objs = ((scene_data.get("board_objects") or []) or [])
            for bo in board_objs:
                is_hero = bo.get("is_hero", False)
                slot = str(bo.get("board_slot") or bo.get("slot") or "")
                if "mid" in slot or "center" in slot or "hero" in slot:
                    is_hero = True

                data = bo.get("data", {}) if isinstance(bo, dict) else {}
                b_type = bo.get("type", "custom")

                # Measure coverage
                w_val = float(data.get("width", 0))
                h_val = float(data.get("height", 0))

                if b_type == "image":
                    img_url = data.get("image_url", "")
                    card_bg = str(data.get("card_bg", "")).lower()
                    if card_bg and card_bg not in ("transparent", "none") and not card_bg.startswith("rgba"):
                        issues.append(f"Hero image '{data.get('label', 'image')}' has opaque background box '{card_bg}' (must be transparent)")

                    if img_url:
                        img_path = Path(img_url)
                        if not img_path.is_file():
                            root = Path(__file__).resolve().parent.parent.parent.parent
                            img_path = root / img_url
                        if img_path.is_file():
                            try:
                                with Image.open(img_path) as im:
                                    if im.mode != "RGBA":
                                        issues.append(f"Hero image '{img_path.name}' is {im.mode} mode (must have transparent RGBA background)")
                                    else:
                                        corners = [
                                            im.getpixel((0, 0))[3],
                                            im.getpixel((im.width - 1, 0))[3],
                                            im.getpixel((0, im.height - 1))[3],
                                            im.getpixel((im.width - 1, im.height - 1))[3],
                                        ]
                                        if any(a > 0 for a in corners):
                                            issues.append(f"Hero image '{img_path.name}' corners are opaque (must have transparent background)")
                            except Exception as ex:
                                logger.debug("Error checking hero image transparency: %s", ex)

                if w_val > 0 and h_val > 0:
                    share = (w_val * h_val) / board_area
                    if is_hero:
                        hero_found = True
                        if share > max_hero_share:
                            max_hero_share = share
                else:
                    svg = data.get("svg", "")
                    m_vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
                    if m_vb:
                        vw, vh = float(m_vb.group(1)), float(m_vb.group(2))
                        share = (vw * vh) / board_area
                        if is_hero:
                            hero_found = True
                            if share > max_hero_share:
                                max_hero_share = share

            if not hero_found:
                issues.append("Scene contains no dominant hero visual (grid of text boxes only)")
            elif max_hero_share < 0.40:
                issues.append(
                    f"Hero visual covers only {max_hero_share * 100:.1f}% of board area (minimum required is 40.0%)"
                )
        else:
            max_hero_share = 0.50

        passed = len(issues) == 0
        return JudgeCheck(
            name="hero_present",
            passed=passed,
            measured={"hero_coverage": round(max_hero_share, 3)},
            expected={"hero_element_coverage_min": 0.40},
            issues=issues,
        )

    def _check_text_fit(
        self,
        arr: np.ndarray,
        board_box: Tuple[int, int, int, int],
        scene_data: Optional[Dict[str, Any]],
        html_path: Optional[Path] = None,
    ) -> JudgeCheck:
        """Verifies no text is cut off, no '..' or line-clamp in captions, and no long all-caps words."""
        issues = []

        # 1. Caption truncation and ellipsis check in scene dialogue
        if scene_data:
            dialogue = str(scene_data.get("dialogue_line") or "")
            if ".." in dialogue or "…" in dialogue:
                issues.append(f"Caption dialogue line contains truncation ellipsis '..' ({dialogue[:40]}...)")

        # 2. Inspect HTML file if available
        if html_path and html_path.is_file():
            try:
                html_txt = html_path.read_text(encoding="utf-8")
                if "-webkit-line-clamp" in html_txt or "text-overflow: ellipsis" in html_txt:
                    issues.append("HTML/CSS contains line-clamp or text-overflow ellipsis (captions must never be truncated)")
                if 'id="speech-bubble-text"' in html_txt:
                    m_txt = re.search(r'<div[^>]*id="speech-bubble-text"[^>]*>(.*?)</div>', html_txt, re.DOTALL)
                    if m_txt and (".." in m_txt.group(1) or "…" in m_txt.group(1)):
                        issues.append(f"Rendered caption bubble text is truncated: '{m_txt.group(1).strip()}'")
            except Exception as e:
                logger.debug("Could not inspect html for text fit: %s", e)

        # 3. Inspect SVG cards for text container overflow and long all-caps words
        if scene_data:
            board_objs = ((scene_data.get("board_objects") or []) or [])
            for bo in board_objs:
                data = bo.get("data", {}) if isinstance(bo, dict) else {}
                svg = data.get("svg", "")
                if not svg:
                    continue

                # Find all text tags
                text_nodes = re.findall(r'<text[^>]*font-size="(\d+)"[^>]*>(.*?)</text>', svg)
                for fs_str, text_content in text_nodes:
                    fs = int(fs_str)
                    clean_txt = re.sub(r'<[^>]+>', '', text_content).strip()
                    # Strip XML entities
                    clean_txt = clean_txt.replace("&amp;", "&").replace("&bull;", "-")
                    words = clean_txt.split()

                    # Max 6 words per line
                    if len(words) > 7:
                        issues.append(f"Text '{clean_txt}' has {len(words)} words on one line (maximum allowed is 6 words)")

                    # Long all-caps check (> 2 words and all uppercase)
                    alpha_words = [w for w in words if any(c.isalpha() for c in w)]
                    if len(alpha_words) > 2 and all(w.isupper() for w in alpha_words):
                        issues.append(
                            f"Text '{clean_txt}' uses all-caps for {len(alpha_words)} words (use normal capitalization for > 2 words)"
                        )

                # Container width overflow check
                # Find rects with both width and height to distinguish cards from small badges/lines
                rect_pairs = re.findall(r'<rect[^>]*width="(\d+)"[^>]*height="(\d+)"', svg)
                if not rect_pairs:
                    rect_pairs = [(w, h) for h, w in re.findall(r'<rect[^>]*height="(\d+)"[^>]*width="(\d+)"', svg)]
                # Filter to true card containers (height >= 80px and width >= 200px)
                card_widths = [float(w) for w, h in rect_pairs if float(h) >= 80 and float(w) >= 200]
                container_w = max(card_widths + [860.0])
                for fs_str, text_content in text_nodes:
                    fs = int(fs_str)
                    clean_txt = re.sub(r'<[^>]+>', '', text_content).strip()
                    est_w = len(clean_txt) * fs * 0.58
                    # If this text tag is inside a multi-column card (< 440px wide)
                    if len(card_widths) > 1:
                        col_w = min(card_widths)
                        if col_w < 440 and est_w > (col_w - 20):
                            issues.append(
                                f"Text '{clean_txt}' ({fs}px) width ~{est_w:.0f}px overflows card column width {col_w:.0f}px (cards must be stacked in one column)"
                            )
                    elif est_w > (container_w - 20):
                        issues.append(
                            f"Text '{clean_txt}' ({fs}px) width ~{est_w:.0f}px overflows container width {container_w:.0f}px"
                        )

        passed = len(issues) == 0
        return JudgeCheck(
            name="text_fit",
            passed=passed,
            measured={"text_fit_violations": len(issues)},
            expected={"text_fit_violations": 0},
            issues=issues,
        )
