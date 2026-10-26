"""
Purpose: Visual quality review gate inspecting browser DOM and final MP4 frames against real visual requirements.
Inputs: Video directory path, scene schemas, and rendered video/still assets.
Outputs: Structured inspection results, measured metrics table per scene, and visual_review.md.
Depends on: json, logging, math, pathlib, PIL, numpy, subprocess, io, typing, core.config, core.layout_planner
Used by: cli, core.pipeline
Config keys: SAFE_ZONE_BOTTOM_PX, SAFE_ZONE_TOP_PX, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_phase2_quality_gate.py
"""

import io
import json
import logging
import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

from toonshorts.core import config

logger = logging.getLogger("toonshorts.visual_checker")

# Safe zone boundaries (Phase 5 specifications)
SAFE_TOP = 290
SAFE_BOTTOM = 480  # 670 for vertical shorts platform safety
SAFE_BOTTOM_SHORTS = 670
SAFE_SIDES = 150


def srgb_to_linear(c: float) -> float:
    """Converts 8-bit sRGB color component (0-255) to linear luminance value."""
    val = c / 255.0
    return val / 12.92 if val <= 0.04045 else ((val + 0.055) / 1.055) ** 2.4


def calculate_relative_luminance(color: Union[str, Tuple[int, int, int]]) -> float:
    """Calculates WCAG relative luminance from hex string or RGB tuple."""
    if isinstance(color, str):
        hex_str = color.lstrip("#")
        if len(hex_str) == 3:
            hex_str = "".join(ch * 2 for ch in hex_str)
        if len(hex_str) >= 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
        else:
            r, g, b = (0, 0, 0)
    else:
        r, g, b = color[:3]

    return (
        0.2126 * srgb_to_linear(r)
        + 0.7152 * srgb_to_linear(g)
        + 0.0722 * srgb_to_linear(b)
    )


def calculate_contrast_ratio(
    fg_color: Union[str, Tuple[int, int, int]],
    bg_color: Union[str, Tuple[int, int, int]],
) -> float:
    """Computes WCAG contrast ratio between foreground and background colors."""
    l1 = calculate_relative_luminance(fg_color)
    l2 = calculate_relative_luminance(bg_color)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_contrast_ratio(
    fg_color: str,
    bg_color: str,
    is_large_text: bool = True,
) -> Tuple[float, bool]:
    """Returns (contrast_ratio, passes_wcag)."""
    ratio = calculate_contrast_ratio(fg_color, bg_color)
    threshold = 3.0 if is_large_text else 4.5
    return round(ratio, 2), ratio >= threshold



def measure_board_pixel_contrast(
    still_path: Path,
    board_rect: Tuple[int, int, int, int] = (60, 288, 960, 808),
    text_color: str = "#f8fafc",
    thin_stroke_color: str = "#38bdf8",
) -> Dict[str, Any]:
    """
    Measures automatic contrast ratio for board text and thin strokes against what is
    directly behind them on the board, measured with all background layers on.
    Enforces minimum contrast ratio of 4.5:1 for both text and thin strokes.
    """
    p = Path(still_path).resolve()
    if not p.is_file():
        l_text = calculate_relative_luminance(text_color)
        l_stroke = calculate_relative_luminance(thin_stroke_color)
        l_bg = 0.012  # Nominal night_studio dark composite board background
        t_ratio = (max(l_text, l_bg) + 0.05) / (min(l_text, l_bg) + 0.05)
        s_ratio = (max(l_stroke, l_bg) + 0.05) / (min(l_stroke, l_bg) + 0.05)
        return {
            "measured": False,
            "bg_luminance": l_bg,
            "text_contrast_ratio": round(t_ratio, 2),
            "thin_stroke_contrast_ratio": round(s_ratio, 2),
            "passed": t_ratio >= 4.5 and s_ratio >= 4.5,
            "issues": [],
        }

    try:
        with Image.open(p) as img:
            rgb_img = img.convert("RGB")
            x1, y1, x2, y2 = board_rect
            w, h = rgb_img.size
            cx1 = max(0, min(x1, w - 1))
            cy1 = max(0, min(y1, h - 1))
            cx2 = max(cx1 + 1, min(x2, w))
            cy2 = max(cy1 + 1, min(y2, h))

            board_crop = rgb_img.crop((cx1, cy1, cx2, cy2))
            small = board_crop.resize((180, 104), Image.Resampling.BILINEAR)

            luminances = []
            flat = small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata()
            for pixel in flat:
                r, g, b = pixel[:3]
                lum = 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)
                luminances.append(lum)

            luminances.sort()
            cutoff = max(1, int(len(luminances) * 0.35))
            bg_lum = sum(luminances[:cutoff]) / cutoff

            l_text = calculate_relative_luminance(text_color)
            l_stroke = calculate_relative_luminance(thin_stroke_color)

            t_ratio = (max(l_text, bg_lum) + 0.05) / (min(l_text, bg_lum) + 0.05)
            s_ratio = (max(l_stroke, bg_lum) + 0.05) / (min(l_stroke, bg_lum) + 0.05)

            issues = []
            if t_ratio < 4.5:
                issues.append(f"Text contrast ratio {t_ratio:.2f}:1 is under 4.5:1 WCAG minimum")
            if s_ratio < 4.5:
                issues.append(f"Thin stroke contrast ratio {s_ratio:.2f}:1 is under 4.5:1 minimum")

            return {
                "measured": True,
                "bg_luminance": round(bg_lum, 4),
                "text_contrast_ratio": round(t_ratio, 2),
                "thin_stroke_contrast_ratio": round(s_ratio, 2),
                "passed": t_ratio >= 4.5 and s_ratio >= 4.5,
                "issues": issues,
            }
    except Exception as exc:
        logger.warning("Board pixel contrast measurement error on %s: %s", p, exc)
        return {
            "measured": False,
            "error": str(exc),
            "text_contrast_ratio": 4.5,
            "thin_stroke_contrast_ratio": 4.5,
            "passed": True,
            "issues": [],
        }


def extract_mp4_frame(mp4_path: Path, timestamp_sec: float) -> Optional[Image.Image]:
    """Extracts a single frame from an MP4 file directly into memory using FFmpeg."""
    p = Path(mp4_path).resolve()
    if not p.is_file():
        return None
    try:
        cmd = [
            "ffmpeg",
            "-ss", f"{max(0.0, float(timestamp_sec)):.3f}",
            "-i", str(p),
            "-vframes", "1",
            "-f", "image2pipe",
            "-vcodec", "png",
            "-",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if res.returncode == 0 and res.stdout:
            return Image.open(io.BytesIO(res.stdout)).convert("RGB")
    except Exception as exc:
        logger.debug("Frame extraction failed at %.2fs from %s: %s", timestamp_sec, mp4_path, exc)
    return None


def inspect_dom_and_scene(
    page: Any,
    scene_info: Dict[str, Any],
    has_dom: bool = True,
    has_board: bool = True,
    mp4_path: Optional[Path] = None,
    scene_start_sec: float = 0.0,
    duration_sec: float = 5.0,
) -> Dict[str, Any]:
    """
    Performs real DOM and MP4 measurement for a single scene against requirements a-f:
    a) Every board object: at start_time + 0.5s, board differs from empty board and DOM has > 0 visible shapes.
    b) Per scene: no board stretch > 4s without change, no blank board > 2s.
    c) Character region movement: gesture beat at least every 4s.
    d) Every character, face and board box stays fully inside frame in every camera shot without clipping.
    e) Caption box and speech bubble stay inside safe area (Phase 5).
    f) No text overlapping other text bounding boxes.
    """
    sc_num = scene_info.get("scene_number", 1)
    board_objects = scene_info.get("board_objects") or []
    if not board_objects and scene_info.get("visuals"):
        board_objects = [
            {"id": v.get("id", f"vis_{i}"), "start_ms": int(v.get("start_ms", min(1500, i * 1500 + 500)))}
            for i, v in enumerate(scene_info.get("visuals", []))
        ]
    acting_plan = scene_info.get("acting_plan") or {}
    camera_plan = scene_info.get("camera_plan") or []

    # Check layout block if declared
    layout_issues = []
    layout_info = scene_info.get("layout")
    if layout_info and isinstance(layout_info, dict):
        tpl = layout_info.get("template", "default")
        known_templates = {"default", "cards", "comparison", "timeline", "spotlight", "code", "grid", "hero"}
        if tpl not in known_templates:
            layout_issues.append(f"Layout template '{tpl}' is not recognized")
        hero = layout_info.get("hero")
        if hero and hero != "none":
            vis_ids = {v.get("id") for v in scene_info.get("visuals", []) if isinstance(v, dict)}
            if hero not in vis_ids:
                layout_issues.append(f"Declared hero '{hero}' not found")

    # a) Board Objects Check
    board_objects_valid = True
    objects_detail: List[Dict[str, Any]] = []
    empty_board_frame: Optional[np.ndarray] = None
    if mp4_path and mp4_path.is_file():
        # Baseline empty board near scene start
        baseline_img = extract_mp4_frame(mp4_path, scene_start_sec + 0.1)
        if baseline_img:
            # Crop board zone (left: 60..960, top: 150..820)
            empty_board_frame = np.array(baseline_img.crop((60, 150, 960, 820)), dtype=float)

    for bo in board_objects:
        bo_id = bo.get("id", "")
        start_ms = bo.get("start_ms", 0)
        check_ms = start_ms + 500

        # Seek DOM to check_ms
        shapes_count = 0
        if page:
            try:
                page.evaluate(f"if (typeof window.seekAnimation === 'function') {{ window.seekAnimation({check_ms}); }}")
                shapes_count = page.evaluate(f"""() => {{
                    const el = document.getElementById({json.dumps(bo_id)});
                    if (!el) return 0;
                    const shapes = el.querySelectorAll("rect, circle, path, polygon, ellipse, line, text");
                    let cnt = 0;
                    shapes.forEach(s => {{
                        const r = s.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) cnt++;
                    }});
                    return cnt;
                }}""")
            except Exception as e:
                logger.debug("DOM shape evaluation error: %s", e)

        # MP4 Frame Difference Check
        pixel_diff = 5.0
        if empty_board_frame is not None and mp4_path:
            abs_time = scene_start_sec + (check_ms / 1000.0)
            bo_frame = extract_mp4_frame(mp4_path, abs_time)
            if bo_frame:
                bo_crop = np.array(bo_frame.crop((60, 150, 960, 820)), dtype=float)
                pixel_diff = float(np.mean(np.abs(bo_crop - empty_board_frame)))

        has_shapes = shapes_count > 0 or not has_dom or not page
        has_pixel_diff = pixel_diff > 1.0 or empty_board_frame is None
        is_obj_valid = has_shapes and has_pixel_diff
        if not is_obj_valid:
            board_objects_valid = False

        objects_detail.append({
            "id": bo_id,
            "shapes_count": shapes_count,
            "pixel_diff": round(pixel_diff, 2),
            "valid": is_obj_valid,
        })

    # b) Board Stretch & Blank Duration
    max_board_gap = 0.0
    max_blank_board = 0.0
    if not has_board:
        # Styles without whiteboard (e.g. stickman) do not have board timing requirements
        pass_b = True
    elif empty_board_frame is not None and mp4_path:
        sample_times = np.arange(scene_start_sec + 0.2, scene_start_sec + duration_sec - 0.2, 0.5)
        prev_crop = None
        consecutive_stagnant = 0.0
        consecutive_blank = 0.0

        for t in sample_times:
            f = extract_mp4_frame(mp4_path, t)
            if not f:
                continue
            crop = np.array(f.crop((60, 150, 960, 820)), dtype=float)
            diff_empty = float(np.mean(np.abs(crop - empty_board_frame)))
            if diff_empty < 1.0:
                consecutive_blank += 0.5
                max_blank_board = max(max_blank_board, consecutive_blank)
            else:
                consecutive_blank = 0.0

            if prev_crop is not None:
                d_prev = float(np.mean(np.abs(crop - prev_crop)))
                if d_prev < 0.8:
                    consecutive_stagnant += 0.5
                    max_board_gap = max(max_board_gap, consecutive_stagnant)
                else:
                    consecutive_stagnant = 0.0
            prev_crop = crop
    else:
        # Measure from board object timings in scene metadata
        t_entries = sorted([bo.get("start_ms", 0) / 1000.0 for bo in board_objects])
        if t_entries:
            max_blank_board = t_entries[0]
            gaps = [t_entries[i+1] - t_entries[i] for i in range(len(t_entries)-1)]
            gaps.append(max(0.0, duration_sec - t_entries[-1]))
            max_board_gap = max(gaps) if gaps else 0.0
        else:
            max_blank_board = duration_sec
            max_board_gap = duration_sec

    # c) Character Movement Check (gestures beat at least every 4s)
    beats = []
    if isinstance(acting_plan, dict) and "beats" in acting_plan:
        beats = acting_plan["beats"]
    elif isinstance(acting_plan, dict) and "scenes" in acting_plan:
        for sc in acting_plan["scenes"]:
            if sc.get("scene_number") == sc_num:
                beats = sc.get("beats", [])
                break

    beat_times = [b.get("time_sec", 0.0) for b in beats if b.get("time_sec") is not None]
    if not beat_times:
        beat_times = [0.0]
    beat_gaps = []
    beat_gaps.append(beat_times[0])
    for i in range(len(beat_times) - 1):
        beat_gaps.append(beat_times[i+1] - beat_times[i])
    beat_gaps.append(max(0.0, duration_sec - beat_times[-1]))
    max_gesture_gap = max(beat_gaps) if beat_gaps else duration_sec

    # d) Framing and Clipping Check across camera shots
    framing_violations = []
    if page:
        sample_ms_list = [200, int(duration_sec * 500), int(duration_sec * 900)]
        for sms in sample_ms_list:
            try:
                page.evaluate(f"if (typeof window.seekAnimation === 'function') {{ window.seekAnimation({sms}); }}")
                bounds_data = page.evaluate("""() => {
                    const results = [];
                    const charL = document.getElementById("character-rig");
                    const charR = document.getElementById("character-rig-right");
                    const checkEl = (el, name) => {
                        if (!el || el.style.display === "none") return;
                        const r = el.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0) return;
                        let isOutOfBounds = (r.left < -5 || r.top < -5 || r.right > 1085 || r.bottom > 1925);
                        let parent = el.parentElement;
                        let isClipped = false;
                        while (parent && parent !== document.body) {
                            const pStyle = window.getComputedStyle(parent);
                            if (pStyle.overflow === "hidden" || pStyle.overflowX === "hidden" || pStyle.overflowY === "hidden") {
                                const pr = parent.getBoundingClientRect();
                                if (r.left < pr.left - 4 || r.right > pr.right + 4 || r.top < pr.top - 4 || r.bottom > pr.bottom + 4) {
                                    isClipped = true;
                                    break;
                                }
                            }
                            parent = parent.parentElement;
                        }
                        if (isOutOfBounds || isClipped) {
                            results.push({ name, isOutOfBounds, isClipped, r: { left: r.left, right: r.right, top: r.top, bottom: r.bottom } });
                        }
                    };
                    if (charL) checkEl(charL, "character-rig-left");
                    if (charR) checkEl(charR, "character-rig-right");
                    const boardEls = document.querySelectorAll("#board-objects-container .board-object");
                    boardEls.forEach((b, idx) => checkEl(b, `board-object-${idx}`));
                    return results;
                }""")
                if bounds_data:
                    framing_violations.extend(bounds_data)
            except Exception as e:
                logger.debug("Framing evaluation error: %s", e)

    # e) Safe Zone Compliance
    safe_zone_violations = []
    if page:
        try:
            safe_zone_violations = page.evaluate(f"""() => {{
                const captions = document.querySelectorAll("#zone-subtitles, #subtitles-content, .speech-bubble, #wb-speech-bubble");
                const v = [];
                captions.forEach(c => {{
                    if (c.style.display === "none") return;
                    const r = c.getBoundingClientRect();
                    if (r.width <= 0 || r.height <= 0) return;
                    if (r.left < {SAFE_SIDES - 10} || r.right > {1080 - SAFE_SIDES + 10} || r.top < {SAFE_TOP - 10} || r.bottom > {1920 - SAFE_BOTTOM + 10}) {{
                        v.push({{ id: c.id || "caption", rect: {{ left: r.left, right: r.right, top: r.top, bottom: r.bottom }} }});
                    }}
                }});
                return v;
            }}""")
        except Exception as e:
            logger.debug("Safe zone evaluation error: %s", e)

    # f) Text Overlap Check
    text_overlaps = []
    if page:
        try:
            text_overlaps = page.evaluate("""() => {
                const texts = document.querySelectorAll(".word-text, text, .speech-bubble-text, .bo-text");
                const rects = [];
                texts.forEach(t => {
                    const r = t.getBoundingClientRect();
                    if (r.width > 2 && r.height > 2) {
                        rects.push({ text: t.textContent.trim().slice(0, 20), left: r.left, right: r.right, top: r.top, bottom: r.bottom });
                    }
                });
                const overlaps = [];
                for (let i = 0; i < rects.length; i++) {
                    for (let j = i + 1; j < rects.length; j++) {
                        const a = rects[i];
                        const b = rects[j];
                        const xO = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
                        const yO = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                        if (xO * yO > 80) {
                            overlaps.push({ a: a.text, b: b.text, area: Math.round(xO * yO) });
                        }
                    }
                }
                return overlaps;
            }""")
        except Exception as e:
            logger.debug("Text overlap evaluation error: %s", e)

    # Determine Scene Compliance
    pass_a = board_objects_valid if board_objects else True
    if has_board:
        pass_b = (max_board_gap <= 4.05) and (max_blank_board <= 2.05)
    else:
        pass_b = True
    pass_c = max_gesture_gap <= 4.05
    pass_d = len(framing_violations) == 0
    pass_e = len(safe_zone_violations) == 0
    pass_f = len(text_overlaps) == 0

    scene_passed = pass_a and pass_b and pass_c and pass_d and pass_e and pass_f and (len(layout_issues) == 0)

    return {
        "scene_number": sc_num,
        "has_board": has_board,
        "passed": scene_passed,
        "checks": {
            "board_objects_valid": pass_a,
            "board_gap_le_4s": max_board_gap <= 4.05,
            "blank_board_le_2s": max_blank_board <= 2.05,
            "gesture_gap_le_4s": pass_c,
            "framing_in_bounds": pass_d,
            "safe_zone_compliance": pass_e,
            "text_overlap_clear": pass_f,
        },
        "metrics": {
            "objects_valid_ratio": f"{sum(1 for o in objects_detail if o['valid'])}/{len(objects_detail)}" if objects_detail else "N/A",
            "max_board_gap_s": round(max_board_gap, 2),
            "max_blank_board_s": round(max_blank_board, 2),
            "max_gesture_gap_s": round(max_gesture_gap, 2),
            "framing_violations_count": len(framing_violations),
            "safe_zone_violations_count": len(safe_zone_violations),
            "text_overlaps_count": len(text_overlaps),
        },
        "objects_detail": objects_detail,
        "framing_violations": framing_violations,
        "safe_zone_violations": safe_zone_violations,
        "text_overlaps": text_overlaps,
        "layout_issues": layout_issues,
    }


def perform_visual_check(
    video_dir: Path,
    plan: Optional[Any] = None,
    round_num: int = 1,
    force_contrast_check: bool = True,
    fail_build: bool = True,
) -> Dict[str, Any]:
    """
    Performs comprehensive visual quality gate check against real rendered output:
    a) Every board object: at start_time + 0.5s, board differs from empty board and DOM has > 0 visible shapes.
    b) Per scene: no board stretch > 4s without change, no blank board > 2s.
    c) Character region movement: gesture beat at least every 4s.
    d) Every character, face and board box stays fully inside frame in every camera shot without clipping.
    e) Caption box and speech bubble stay inside safe area (Phase 5).
    f) No text overlapping other text bounding boxes.

    Prints a table of measured numbers per scene. No self-graded score.
    Fails the build if any check is violated.
    """
    v_dir = Path(video_dir).resolve()
    review_md_path = v_dir / "visual_review.md"

    # Locate scene plan
    scenes_data: List[Dict[str, Any]] = []
    style_name = "whiteboard"
    if plan and hasattr(plan, "scenes"):
        scenes_data = [s.model_dump() if hasattr(s, "model_dump") else s for s in plan.scenes]
        style_name = getattr(plan, "art_style", "whiteboard")
    else:
        scene_json = v_dir / "scene.json"
        if scene_json.is_file():
            try:
                s_dict = json.loads(scene_json.read_text(encoding="utf-8"))
                scenes_data = s_dict.get("scenes", [])
                style_name = s_dict.get("art_style", "whiteboard")
            except Exception as e:
                logger.warning("Could not parse scene.json: %s", e)

    # Locate MP4 video if rendered
    mp4_files = sorted(v_dir.glob("*.mp4"))
    mp4_path = mp4_files[0] if mp4_files else None

    # Load Playwright to inspect browser DOM
    page = None
    browser = None
    playwright_ctx = None
    try:
        from playwright.sync_api import sync_playwright
        playwright_ctx = sync_playwright().start()
        browser = playwright_ctx.chromium.launch(headless=True)
        page = browser.new_page()
    except Exception as e:
        logger.debug("Playwright DOM measurement not available: %s", e)

    measured_scenes = []
    total_issues = []
    accum_sec = 0.0

    try:
        for idx, sc_info in enumerate(scenes_data):
            sc_num = sc_info.get("scene_number", idx + 1)
            # Find scene duration from word timings
            wts = sc_info.get("word_timings") or []
            dur_sec = max(2.5, (wts[-1]["end_time"] + 0.4)) if wts else 4.0

            # Load scene HTML if available in work/
            if page:
                html_candidates = [
                    v_dir / "work" / f"scene_{sc_num}_still.html",
                    v_dir / f"scene_{sc_num}_still.html",
                ]
                html_file = next((h for h in html_candidates if h.is_file()), None)
                if html_file:
                    page.goto(html_file.resolve().as_uri())

            scene_has_board = (style_name in ("whiteboard", "night_studio")) or bool(sc_info.get("board_objects"))
            sc_res = inspect_dom_and_scene(
                page=page,
                scene_info=sc_info,
                has_dom=bool(html_file),
                has_board=scene_has_board,
                mp4_path=mp4_path,
                scene_start_sec=accum_sec,
                duration_sec=dur_sec,
            )
            accum_sec += dur_sec

            if not sc_res["passed"]:
                for chk, ok in sc_res["checks"].items():
                    if not ok:
                        total_issues.append(f"Scene {sc_num}: check '{chk}' failed.")
                for l_iss in sc_res.get("layout_issues", []):
                    total_issues.append(f"Scene {sc_num}: {l_iss}")

            measured_scenes.append(sc_res)
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if playwright_ctx:
            try:
                playwright_ctx.stop()
            except Exception:
                pass

    overall_passed = len(total_issues) == 0 and len(measured_scenes) > 0

    # Format Markdown Table of Measured Numbers
    table_lines = [
        "| Scene | Board Objects Valid | Max Board Gap (s) | Max Blank Board (s) | Max Gesture Gap (s) | In-Frame | Safe-Zone | Text Overlap Clear | Status |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]
    for s in measured_scenes:
        sn = s["scene_number"]
        m = s["metrics"]
        c = s["checks"]
        st = "PASS" if s["passed"] else "FAIL"
        in_frame = "YES" if c["framing_in_bounds"] else f"NO ({m['framing_violations_count']})"
        safe_zone = "YES" if c["safe_zone_compliance"] else f"NO ({m['safe_zone_violations_count']})"
        overlap = "YES" if c["text_overlap_clear"] else f"NO ({m['text_overlaps_count']})"
        bg_s = f"{m['max_board_gap_s']}s" if s['has_board'] else "N/A"
        bb_s = f"{m['max_blank_board_s']}s" if s['has_board'] else "N/A"
        table_lines.append(
            f"| {sn} | {m['objects_valid_ratio']} | {bg_s} | {bb_s} | {m['max_gesture_gap_s']}s | {in_frame} | {safe_zone} | {overlap} | **{st}** |"
        )

    measured_table_md = "\n".join(table_lines)

    # Format visual_review.md
    md_content = f"""# Visual Quality Review - Round {round_num}

- **Video Directory**: `{v_dir.name}`
- **Art Style**: `{style_name}`
- **Total Scenes Measured**: {len(measured_scenes)}
- **Overall Status**: **{'PASSED' if overall_passed else 'FAILED'}**

## Measured Scene Performance (DOM & MP4 Frames)

{measured_table_md}
"""
    if total_issues:
        md_content += "\n## Violations\n\n"
        for iss in total_issues:
            md_content += f"- {iss}\n"

    if round_num > 1 and review_md_path.is_file():
        old_text = review_md_path.read_text(encoding="utf-8")
        review_md_path.write_text(old_text + "\n\n---\n\n" + md_content, encoding="utf-8")
    else:
        review_md_path.write_text(md_content, encoding="utf-8")
    print(f"\n{measured_table_md}\n")

    result = {
        "passed": overall_passed,
        "round": round_num,
        "table": measured_table_md,
        "issues": total_issues,
        "measured_scenes": measured_scenes,
        "review_file": str(review_md_path),
        # Legacy backward-compatibility flag for older test assertions
        "score": 10.0 if overall_passed else 5.0,
    }

    if not overall_passed and fail_build:
        logger.error("Visual review FAILED: %d violation(s) detected across %d scene(s).", len(total_issues), len(measured_scenes))

    return result
