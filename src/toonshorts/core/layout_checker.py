"""
Purpose: Automated bounding box and safe-zone layout verification using Playwright.
Inputs: Rendered scene HTML files, video directories, camera zoom peak states.
Outputs: Layout validation report with element bounding boxes and pass/fail diagnostics.
Depends on: asyncio, json, logging, pathlib, typing, core.config, core.paths
Used by: cli, core.pipeline
Config keys: SAFE_ZONE_TOP_PX, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_layout_checker.py
"""

import asyncio
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from toonshorts.core import config, paths

logger = logging.getLogger("toonshorts.layout_checker")

# Safe zone constants
SAFE_ZONE_TOP_PX = getattr(config, "SAFE_ZONE_TOP_PX", 288)  # 15% of 1920 = 288px
CANVAS_WIDTH = getattr(config, "VIDEO_WIDTH", 1080)
CANVAS_HEIGHT = getattr(config, "VIDEO_HEIGHT", 1920)
FLOAT_TOLERANCE_PX = 1.0  # 1px tolerance for subpixel browser layout rounding


def _evaluate_dom_layout_js() -> str:
    return """
    () => {
        function getBox(el) {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity || '1') > 0;
            return {
                top: Math.round(r.top * 100) / 100,
                bottom: Math.round(r.bottom * 100) / 100,
                left: Math.round(r.left * 100) / 100,
                right: Math.round(r.right * 100) / 100,
                width: Math.round(r.width * 100) / 100,
                height: Math.round(r.height * 100) / 100,
                visible: isVisible,
                scrollWidth: el.scrollWidth,
                scrollHeight: el.scrollHeight,
                clientWidth: el.clientWidth,
                clientHeight: el.clientHeight
            };
        }

        const boardZoneEl = document.getElementById('zone-board') || document.querySelector('.whiteboard-outer') || document.getElementById('layer-board');
        const titleBadgeEl = document.querySelector('.title-badge') || document.getElementById('wb-title');
        const charZoneEl = document.getElementById('zone-character') || document.getElementById('layer-subject');
        const charRigLeftEl = document.getElementById('character-rig') || document.querySelector('.char-slot-left');
        const charRigRightEl = document.getElementById('character-rig-right') || document.querySelector('.char-slot-right');
        const captionsZoneEl = document.getElementById('zone-subtitles');
        const captionsTextEl = document.getElementById('subtitles-text');

        // Collect all board visual elements
        const visualSelectors = [
            '.stage-visual',
            '.board-object',
            '#rough-canvas',
            '.stage-container',
            '.word-card',
            '.flow-visual',
            '.cc-visual',
            '.counter-visual',
            '.bar-visual',
            '.step-card',
            '.bo-svg-draw',
            '.bo-diagram',
            '.slot-top > *',
            '.slot-mid > *',
            '.slot-bottom > *',
            '.slot-center > *'
        ];

        const visuals = [];
        visualSelectors.forEach(sel => {
            document.querySelectorAll(sel).forEach((el, idx) => {
                const box = getBox(el);
                if (box && box.width > 0 && box.height > 0) {
                    visuals.push({
                        selector: sel + `[${idx}]`,
                        id: el.id || '',
                        box: box
                    });
                }
            });
        });

        // Check text elements for overflow clipping
        const textElements = [];
        document.querySelectorAll('.title-badge, .word-text, .cc-label-text, .counter-label-text, .step-label, .flow-node-text, .bo-text').forEach(el => {
            if (el.clientWidth > 0 && el.clientHeight > 0) {
                const isClipped = (el.scrollWidth > el.clientWidth + 3) || (el.scrollHeight > el.clientHeight + 3);
                textElements.push({
                    text: (el.textContent || '').trim().substring(0, 30),
                    isClipped: isClipped,
                    scrollWidth: el.scrollWidth,
                    clientWidth: el.clientWidth,
                    scrollHeight: el.scrollHeight,
                    clientHeight: el.clientHeight
                });
            }
        });

        // Detect zoom peak time
        let peakTimeMs = 1000;
        if (window.__splitCharShots && window.__splitCharShots.length > 0) {
            for (const s of window.__splitCharShots) {
                if (s.to_target && s.to_target !== 'wide') {
                    peakTimeMs = Math.round((s.t_start + s.t_end) / 2);
                    break;
                }
            }
        }
        if (window.__splitBoardShots && window.__splitBoardShots.length > 0) {
            for (const s of window.__splitBoardShots) {
                if (s.to_target && s.to_target !== 'wide') {
                    peakTimeMs = Math.round((s.t_start + s.t_end) / 2);
                    break;
                }
            }
        }

        return {
            boardZone: getBox(boardZoneEl),
            titleBadge: getBox(titleBadgeEl),
            charZone: getBox(charZoneEl),
            charLeft: getBox(charRigLeftEl),
            charRight: getBox(charRigRightEl),
            captionsZone: getBox(captionsZoneEl),
            captionsText: getBox(captionsTextEl),
            visuals: visuals,
            textElements: textElements,
            peakTimeMs: peakTimeMs
        };
    }
    """


def validate_measurements(
    data: Dict[str, Any],
    camera_state: str,
    scene_num: int,
) -> List[str]:
    """Validates measured bounding boxes against all layout and safe-zone rules."""
    violations: List[str] = []
    bz = data.get("boardZone")
    tb = data.get("titleBadge")
    cz = data.get("charZone")
    cap = data.get("captionsZone")

    if not bz:
        violations.append(f"Scene {scene_num} ({camera_state}): Board zone element (#zone-board / .whiteboard-outer) was not found in DOM.")
        return violations

    # Rule 1: No board element above y=0
    if bz["top"] < -FLOAT_TOLERANCE_PX:
        violations.append(
            f"Scene {scene_num} ({camera_state}): Board zone top is above canvas boundary (y={bz['top']} < 0)."
        )

    # Rule 2: Outside 1080 canvas width
    if bz["left"] < -FLOAT_TOLERANCE_PX or bz["right"] > CANVAS_WIDTH + FLOAT_TOLERANCE_PX:
        violations.append(
            f"Scene {scene_num} ({camera_state}): Board zone exceeds 1080 canvas width (left={bz['left']}, right={bz['right']})."
        )

    # Rule 3: Must sit strictly below YouTube Shorts top 15% (288 px)
    if bz["top"] < SAFE_ZONE_TOP_PX - FLOAT_TOLERANCE_PX:
        violations.append(
            f"Scene {scene_num} ({camera_state}): Board zone is inside top {SAFE_ZONE_TOP_PX}px YouTube Shorts safe area (top={bz['top']} < {SAFE_ZONE_TOP_PX})."
        )

    if tb and tb.get("visible", True) and tb["width"] > 0:
        if tb["top"] < -FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Title badge is above canvas boundary (y={tb['top']} < 0)."
            )
        if tb["top"] < SAFE_ZONE_TOP_PX - FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Title badge is inside top {SAFE_ZONE_TOP_PX}px YouTube Shorts safe area (top={tb['top']} < {SAFE_ZONE_TOP_PX})."
            )

    # Validate each board visual
    for v in data.get("visuals", []):
        box = v.get("box")
        if not box or not box.get("visible", True):
            continue
        v_sel = v.get("selector", "visual")
        # Visual above canvas
        if box["top"] < -FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Board visual '{v_sel}' is above canvas boundary (y={box['top']} < 0)."
            )
        # Visual inside top 288px
        if box["top"] < SAFE_ZONE_TOP_PX - FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Board visual '{v_sel}' is inside top {SAFE_ZONE_TOP_PX}px safe area (top={box['top']} < {SAFE_ZONE_TOP_PX})."
            )
        # Visual outside 1080 width
        if box["left"] < -FLOAT_TOLERANCE_PX or box["right"] > CANVAS_WIDTH + FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Board visual '{v_sel}' is outside canvas width (left={box['left']}, right={box['right']})."
            )

    # Rule 4: Overlap with characters or captions
    if cz and bz:
        if bz["bottom"] > cz["top"] + FLOAT_TOLERANCE_PX and bz["top"] < cz["bottom"] - FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Board zone overlaps Character zone (board bottom={bz['bottom']} > char top={cz['top']})."
            )

    if cz and cap:
        if cz["bottom"] > cap["top"] + FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Character zone overlaps Captions zone (char bottom={cz['bottom']} > captions top={cap['top']})."
            )

    if bz and cap:
        if bz["bottom"] > cap["top"] + FLOAT_TOLERANCE_PX:
            violations.append(
                f"Scene {scene_num} ({camera_state}): Board zone overlaps Captions zone (board bottom={bz['bottom']} > captions top={cap['top']})."
            )

    # Rule 5: Text clipping by overflow hidden
    for t_info in data.get("textElements", []):
        if t_info.get("isClipped"):
            violations.append(
                f"Scene {scene_num} ({camera_state}): Text element '{t_info.get('text')}' is clipped by overflow hidden "
                f"(scrollW={t_info.get('scrollWidth')} > clientW={t_info.get('clientWidth')})."
            )

    return violations


def check_scene_html_layout(
    html_path: Path,
    scene_num: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Renders scene HTML in Playwright headless browser at 1080x1920.
    Measures DOM bounding boxes at resting state and peak zoom state.
    """
    from playwright.sync_api import sync_playwright

    if scene_num is None:
        m = re.search(r"scene_(\d+)", html_path.stem)
        scene_num = int(m.group(1)) if m else 1

    file_uri = html_path.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT})
        page.goto(file_uri)
        page.wait_for_timeout(300)

        # 1. Measure resting state (t = 0)
        resting_data = page.evaluate(_evaluate_dom_layout_js())
        resting_violations = validate_measurements(resting_data, "resting_state", scene_num)

        # 2. Seek to zoom peak and measure
        peak_ms = resting_data.get("peakTimeMs", 1000)
        page.evaluate(f"""
            () => {{
                if (window.__cameraTimeline) window.__cameraTimeline.seek({peak_ms});
                if (window.__mainTimeline) window.__mainTimeline.seek({peak_ms});
                if (typeof window.seekAnimation === 'function') window.seekAnimation({peak_ms});
            }}
        """)
        page.wait_for_timeout(200)
        peak_data = page.evaluate(_evaluate_dom_layout_js())
        peak_violations = validate_measurements(peak_data, f"zoom_peak_{peak_ms}ms", scene_num)

        browser.close()

    all_violations = resting_violations + peak_violations
    return {
        "scene": scene_num,
        "html_file": html_path.name,
        "passed": len(all_violations) == 0,
        "violations": all_violations,
        "resting_measurements": resting_data,
        "peak_measurements": peak_data,
    }


def verify_video_layout(video_dir: Path) -> Dict[str, Any]:
    """
    Scans a video directory for scene HTML files, checks every scene's layout in Playwright,
    generates summary reports (JSON & text), and writes them into the video folder.
    """
    video_dir = Path(video_dir)
    html_files = sorted(
        list(video_dir.glob("scene_*_still.html")) + list(video_dir.glob("*.html")),
        key=lambda p: p.name,
    )
    # Deduplicate while preserving order
    seen = set()
    unique_htmls = []
    for f in html_files:
        if f.name not in seen and "still" in f.name:
            seen.add(f.name)
            unique_htmls.append(f)

    if not unique_htmls:
        # Fallback to any html
        for f in html_files:
            if f.name not in seen:
                seen.add(f.name)
                unique_htmls.append(f)

    if not unique_htmls:
        raise FileNotFoundError(f"No scene HTML still files found in {video_dir} to check layout.")

    results: List[Dict[str, Any]] = []
    failed_scenes: List[int] = []
    all_violations: List[str] = []

    for f in unique_htmls:
        res = check_scene_html_layout(f)
        results.append(res)
        if not res["passed"]:
            failed_scenes.append(res["scene"])
            all_violations.extend(res["violations"])

    passed = len(failed_scenes) == 0

    report_data = {
        "video_dir": str(video_dir),
        "total_scenes": len(results),
        "passed": passed,
        "failed_scenes": failed_scenes,
        "violations_count": len(all_violations),
        "violations": all_violations,
        "scene_results": [
            {
                "scene": r["scene"],
                "html_file": r["html_file"],
                "passed": r["passed"],
                "violations": r["violations"],
                "board_zone": r["resting_measurements"].get("boardZone"),
                "title_badge": r["resting_measurements"].get("titleBadge"),
            }
            for r in results
        ],
    }

    # Save layout_check.json
    json_path = video_dir / "layout_check.json"
    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    # Format human-readable text report
    lines = [
        "=======================================================",
        f"        AUTOMATED LAYOUT & SAFE-ZONE REPORT",
        "=======================================================",
        f"Directory:     {video_dir}",
        f"Total Scenes:  {len(results)}",
        f"Overall Status: {'PASSED' if passed else 'FAILED'}",
        "-------------------------------------------------------",
    ]
    for r in results:
        status_str = "PASS" if r["passed"] else "FAIL"
        bz = r["resting_measurements"].get("boardZone") or {}
        tb = r["resting_measurements"].get("titleBadge") or {}
        lines.append(
            f"Scene {r['scene']:2d} [{status_str}]: Board Y=[{bz.get('top', '?')}, {bz.get('bottom', '?')}], "
            f"Title Y=[{tb.get('top', '?')}, {tb.get('bottom', '?')}]"
        )
        for v in r["violations"]:
            lines.append(f"    - ERROR: {v}")

    lines.append("=======================================================")
    txt_report = "\n".join(lines) + "\n"

    txt_path = video_dir / "layout_check.txt"
    txt_path.write_text(txt_report, encoding="utf-8")

    return report_data
