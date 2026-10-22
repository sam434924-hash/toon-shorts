"""
Purpose: HTML/SVG whiteboard animation rendering engine using Anime.js, Rough.js, and headless browser.
Inputs: Scene plans, characters, style presets, voice timing cues, and whiteboard text elements.
Outputs: Rendered 9:16 PNG image frames and animated MP4 video sequences.
Depends on: PIL, core.config, core.models, core.registry, html, json, logging, numpy, os, pathlib, playwright, subprocess, typing, wave
Used by: None
Config keys: ANIME_JS_PATH, ROUGH_JS_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/contract/test_render_contract.py, tests/unit/test_animejs.py
"""

from __future__ import annotations
import html
import json
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import wave

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from toonshorts.core import config
from toonshorts.core.models import Character, Scene, ScriptPlan, SceneAudio, WordTiming
from toonshorts.core.registry import RenderInterface, register_renderer

logger = logging.getLogger(__name__)

# Video composition layout & Safe Area boundaries (9:16 vertical 1080x1920)
SAFE_AREA = {
    "min_x": 50.0,
    "max_x": 1030.0,
    "min_y": 50.0,
    "max_y": 1870.0,
}

CHAR_RIG_LAYOUT = {
    "left": 75.0,
    "top": 670.0,
    "width": 560.0,
    "height": 630.0,
}

ALLOWED_GESTURES = frozenset({"idle", "wave", "point", "explain", "open_hand", "thumbs_up", "shrug"})


def sanitize_gesture(gesture: Optional[str]) -> str:
    """Validates gesture against allowed whitelist. Rejects invalid names without building file paths."""
    if not gesture:
        return "idle"
    clean = str(gesture).lower().strip()
    if clean == "open_hand":
        clean = "explain"
    if clean not in ALLOWED_GESTURES:
        raise ValueError(f"Invalid gesture '{gesture}'. Must be one of {sorted(list(ALLOWED_GESTURES))}")
    return clean


def compute_mouth_cues_from_audio(
    audio_path: Optional[Path],
    fps: int = config.VIDEO_FPS,
    threshold_ratio: float = 0.18,
) -> List[bool]:
    """
    Computes frame-by-frame mouth open/closed states from WAV audio loudness (RMS).
    Returns list of booleans of length corresponding to audio duration in frames.
    """
    if not audio_path:
        return []

    p = Path(audio_path)
    if not p.is_file() or p.stat().st_size == 0:
        return []

    try:
        with wave.open(str(p), "rb") as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            raw_bytes = wf.readframes(nframes)
    except Exception as e:
        logger.warning("Could not read audio file for mouth cues (%s): %s", audio_path, e)
        return []

    if nframes == 0 or framerate == 0:
        return []

    # Parse raw PCM bytes to float array in [-1.0, 1.0]
    if sampwidth == 2:
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 1:
        samples = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if nchannels > 1:
        samples = samples.reshape(-1, nchannels).mean(axis=1)

    duration_sec = nframes / framerate
    total_frames = max(1, int(round(duration_sec * fps)))

    rms_per_frame: List[float] = []
    for k in range(total_frames):
        s0 = int(k * framerate / fps)
        s1 = int((k + 1) * framerate / fps)
        chunk = samples[s0:s1]
        if len(chunk) == 0:
            rms_per_frame.append(0.0)
        else:
            rms = float(np.sqrt(np.mean(chunk**2)))
            rms_per_frame.append(rms)

    max_rms = float(np.max(rms_per_frame)) if rms_per_frame else 0.0
    threshold = max(0.015, max_rms * threshold_ratio)

    raw_cues = [bool(r >= threshold) for r in rms_per_frame]

    # Smooth mouth flapping: avoid single-frame flickering
    smoothed = list(raw_cues)
    for i in range(1, len(smoothed) - 1):
        if not smoothed[i] and smoothed[i - 1] and smoothed[i + 1]:
            smoothed[i] = True
        elif smoothed[i] and not smoothed[i - 1] and not smoothed[i + 1]:
            smoothed[i] = False

    return smoothed


def extract_whiteboard_content_and_annotations(
    scene: Scene,
    duration_sec: float,
    word_timings: Optional[List[WordTiming]] = None,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts whiteboard title, bullet point cards, and synchronized annotations (underlines, circles, arrows).
    Each annotation is tied to a specific word and starts drawing when that word starts.
    """
    action_text = (scene.action or "").strip()
    if ":" in action_text:
        title_part, points_part = action_text.split(":", 1)
        title = title_part.strip()
        points = [p.strip() for p in points_part.replace(";", ",").split(",") if p.strip()]
    elif action_text:
        title = action_text[:45]
        words_dlg = scene.dialogue_line.split()
        if len(words_dlg) >= 6:
            points = [
                " ".join(words_dlg[: len(words_dlg) // 3]),
                " ".join(words_dlg[len(words_dlg) // 3 : 2 * len(words_dlg) // 3]),
                " ".join(words_dlg[2 * len(words_dlg) // 3 :]),
            ]
        else:
            points = [scene.dialogue_line[:30]]
    else:
        title = f"Scene {scene.scene_number}"
        points = ["Key Idea", "Implementation", "Result"]

    title = title[:50]
    total_ms = int(duration_sec * 1000)

    # 1. Synthesize fallback word timings if none provided
    raw_timings: List[WordTiming] = []
    if word_timings and len(word_timings) > 0:
        raw_timings = list(word_timings)
    else:
        dlg_words = [w for w in scene.dialogue_line.split() if w.strip()]
        if not dlg_words:
            dlg_words = ["API", "metaphor", "service", "system"]
        speech_span = max(duration_sec - 0.6, 1.2)
        step = speech_span / len(dlg_words)
        for idx, w in enumerate(dlg_words):
            st = 0.3 + idx * step
            et = st + step * 0.85
            raw_timings.append(WordTiming(word=w, start_time=round(st, 3), end_time=round(et, 3)))

    def clean_word(w: str) -> str:
        return re.sub(r"[^\w]", "", w).lower()

    # 2. Match Title Underline to a keyword in dialogue
    title_words = [clean_word(tw) for tw in title.split() if len(clean_word(tw)) >= 3]
    matched_title_wt = None
    for tw in title_words:
        matched_title_wt = next((wt for wt in raw_timings if clean_word(wt.word) == tw), None)
        if matched_title_wt:
            break

    if not matched_title_wt:
        pick_idx = min(len(raw_timings) - 1, max(0, len(raw_timings) // 6))
        matched_title_wt = raw_timings[pick_idx]

    annotations: List[Dict[str, Any]] = []

    # Title underline starts exactly at matched title word start_time
    title_u_start_sec = matched_title_wt.start_time
    title_u_start_ms = max(50, int(round(title_u_start_sec * 1000)))
    annotations.append({
        "id": "rough-title-underline",
        "type": "underline",
        "tied_word": matched_title_wt.word,
        "tied_word_obj": matched_title_wt,
        "start_time": title_u_start_sec,
        "start_ms": title_u_start_ms,
        "duration_ms": 380,
    })

    # 3. Match Card items and Circles
    num_pts = max(len(points), 1)
    word_cards: List[Dict[str, Any]] = []
    card_matched_timings: List[WordTiming] = []

    prev_timing_idx = 0
    for i, pt in enumerate(points):
        pt_words = [clean_word(pw) for pw in pt.split() if len(clean_word(pw)) >= 3]
        matched_card_wt = None
        matched_idx = -1

        for idx in range(prev_timing_idx, len(raw_timings)):
            cw = clean_word(raw_timings[idx].word)
            if cw in pt_words:
                matched_card_wt = raw_timings[idx]
                matched_idx = idx
                break

        if not matched_card_wt:
            frac = 0.30 + (i / max(num_pts, 1)) * 0.58
            matched_idx = min(len(raw_timings) - 1, max(prev_timing_idx, int(len(raw_timings) * frac)))
            matched_card_wt = raw_timings[matched_idx]

        prev_timing_idx = min(len(raw_timings) - 1, matched_idx + 1)
        card_matched_timings.append(matched_card_wt)

        c_start_sec = matched_card_wt.start_time
        c_start_ms = int(round(c_start_sec * 1000))
        word_cards.append({
            "text": pt[:42],
            "start_time": c_start_sec,
            "start_ms": c_start_ms,
            "duration_ms": 420,
            "tied_word": matched_card_wt.word,
            "tied_word_obj": matched_card_wt,
        })

        # Circle around card keyword text (NOT covering list numbers)
        annotations.append({
            "id": f"rough-circle-{i+1}",
            "type": "circle",
            "card_index": i,
            "tied_word": matched_card_wt.word,
            "tied_word_obj": matched_card_wt,
            "start_time": c_start_sec,
            "start_ms": c_start_ms,
            "duration_ms": 420,
        })

    # 4. Arrows connecting card i to card i+1
    # Drawn when speech moves from one item to the next
    for i in range(len(card_matched_timings) - 1):
        wt_cur = card_matched_timings[i]
        wt_next = card_matched_timings[i + 1]

        idx_cur = raw_timings.index(wt_cur) if wt_cur in raw_timings else i
        idx_next = raw_timings.index(wt_next) if wt_next in raw_timings else i + 1

        if idx_next > idx_cur + 1:
            arrow_idx = max(idx_cur + 1, idx_next - 1)
        else:
            arrow_idx = idx_next

        arrow_wt = raw_timings[arrow_idx]
        arrow_start_sec = arrow_wt.start_time
        arrow_start_ms = int(round(arrow_start_sec * 1000))

        # Ensure card i+1 appears at or before the arrow connecting to it begins drawing
        word_cards[i + 1]["start_ms"] = min(word_cards[i + 1]["start_ms"], arrow_start_ms)

        annotations.append({
            "id": f"rough-arrow-{i+1}",
            "type": "arrow",
            "card_from": i,
            "card_to": i + 1,
            "tied_word": arrow_wt.word,
            "tied_word_obj": arrow_wt,
            "start_time": arrow_start_sec,
            "start_ms": arrow_start_ms,
            "duration_ms": 400,
        })

    return title, word_cards, annotations


def extract_whiteboard_content_for_scene(
    scene: Scene,
    duration_sec: float,
    word_timings: Optional[List[WordTiming]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extracts whiteboard title and bullet point cards for a scene.
    Provides backwards compatibility returning (title, words).
    """
    title, words, _ = extract_whiteboard_content_and_annotations(
        scene=scene,
        duration_sec=duration_sec,
        word_timings=word_timings,
    )
    return title, words


def generate_scene_decorations(scene_number: int = 1) -> Tuple[str, str]:
    """
    Generates consistent SVG studio wall fixtures and foreground desk props.
    The room, desk, shelf, and all props are 100% IDENTICAL in every scene.
    Only the board content changes between scenes.
    """
    shelf_svg = """
    <!-- Floating Studio Shelf on Right Wall (Constant Across All Scenes) -->
    <div class="studio-shelf" style="top: 710px; left: 810px; width: 210px;"></div>
    <svg viewBox="0 0 100 90" style="position: absolute; top: 635px; left: 825px; width: 100px; height: 90px; z-index: 3;">
      <rect x="15" y="42" width="28" height="32" rx="4" fill="#ffffff" stroke="#94a3b8" stroke-width="2"/>
      <path d="M 29 42 C 18 24, 6 30, 14 42 Z" fill="#22c55e"/>
      <path d="M 29 42 C 34 16, 50 22, 42 42 Z" fill="#15803d"/>
      <path d="M 22 50 Q 8 68 14 84" stroke="#16a34a" stroke-width="3" fill="none" stroke-linecap="round"/>
      <circle cx="14" cy="84" r="4.5" fill="#22c55e"/>
      <path d="M 34 52 Q 44 68 40 80" stroke="#16a34a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <circle cx="40" cy="80" r="3.5" fill="#15803d"/>
      <rect x="52" y="32" width="12" height="42" rx="2" fill="#3b82f6"/>
      <rect x="66" y="24" width="14" height="50" rx="2" fill="#f59e0b"/>
      <rect x="82" y="36" width="10" height="38" rx="2" fill="#ec4899"/>
    </svg>"""

    desk_svg = """
    <!-- Constant Foreground Desk Props Across All Scenes -->
    <!-- Modern Laptop with Clean Syntax Lines -->
    <rect x="650" y="38" width="180" height="84" rx="6" fill="#334155"/>
    <rect x="660" y="46" width="160" height="68" rx="4" fill="#090d16"/>
    <line x1="672" y1="58" x2="730" y2="58" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="70" x2="780" y2="70" stroke="#818cf8" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="82" x2="745" y2="82" stroke="#34d399" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="94" x2="710" y2="94" stroke="#f472b6" stroke-width="4" stroke-linecap="round"/>
    <polygon points="620,122 860,122 840,116 640,116" fill="#475569"/>
    <!-- Ceramic Navy Coffee Mug with Steam -->
    <rect x="548" y="58" width="46" height="56" rx="8" fill="#1e3a8a"/>
    <path d="M 594 70 Q 610 70 610 86 Q 610 100 594 100" stroke="#1e3a8a" stroke-width="6" fill="none"/>
    <path d="M 563 50 Q 558 40 563 30" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" fill="none"/>
    <path d="M 576 50 Q 581 40 576 30" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" fill="none"/>"""

    return shelf_svg, desk_svg


def compute_gesture_bounds(
    gesture: str,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
) -> Dict[str, float]:
    """
    Computes screen-space bounding box for all arm and hand geometry of a gesture.
    Returns dictionary with min_x, max_x, min_y, max_y in pixel coordinates.
    All bounds are guaranteed to lie strictly within the safe area.
    """
    clean = sanitize_gesture(gesture)
    rig_x = CHAR_RIG_LAYOUT["left"]
    rig_y = CHAR_RIG_LAYOUT["top"]

    # Hand & arm bounds inside SVG local viewBox (0..560, 0..630)
    # Physically attached to arm sleeve with zero gaps
    if clean == "wave":
        local_min_x = 348.0
        local_max_x = 495.0
        local_min_y = 145.0
        local_max_y = 572.0
    elif clean == "point":
        local_min_x = 348.0
        local_max_x = 520.0
        local_min_y = 150.0
        local_max_y = 572.0
    elif clean == "explain":
        local_min_x = 348.0
        local_max_x = 518.0
        local_min_y = 320.0
        local_max_y = 572.0
    elif clean == "thumbs_up":
        local_min_x = 348.0
        local_max_x = 475.0
        local_min_y = 260.0
        local_max_y = 572.0
    elif clean == "shrug":
        local_min_x = 90.0
        local_max_x = 440.0
        local_min_y = 350.0
        local_max_y = 572.0
    else:  # idle
        local_min_x = 120.0
        local_max_x = 405.0
        local_min_y = 360.0
        local_max_y = 572.0

    return {
        "min_x": float(rig_x + local_min_x),
        "max_x": float(rig_x + local_max_x),
        "min_y": float(rig_y + local_min_y),
        "max_y": float(rig_y + local_max_y),
    }


def generate_whiteboard_html(
    title: str,
    words: List[Dict[str, Any]],
    duration_sec: float,
    mouth_cues: Optional[List[bool]] = None,
    gesture: str = "idle",
    fps: int = config.VIDEO_FPS,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
    scene_number: int = 1,
    annotations: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Generates a high-contrast HTML5/SVG composition with Anime.js whiteboard animation,
    Rough.js progressive stroke-by-stroke drawing (underlines, circles around keywords,
    prominent inter-card arrows), 7-layer character head redesign, physically attached hands,
    and a 100% constant studio set. Loaded strictly from local bundled scripts (no CDNs).
    """
    anime_js_path = config.ANIME_JS_PATH
    if not anime_js_path.is_file():
        raise FileNotFoundError(f"Local Anime.js bundle not found at {anime_js_path}")

    rough_js_path = config.ROUGH_JS_PATH
    if not rough_js_path.is_file():
        raise FileNotFoundError(f"Local Rough.js bundle not found at {rough_js_path}")

    anime_js = anime_js_path.read_text(encoding="utf-8")
    rough_js = rough_js_path.read_text(encoding="utf-8")

    clean_gesture = sanitize_gesture(gesture)
    safe_title = html.escape(title)

    total_duration_ms = int(duration_sec * 1000)
    title_start_ms = 100
    title_duration_ms = 420

    # Build fallback annotations if not provided
    if annotations is None:
        annotations = [{
            "id": "rough-title-underline",
            "type": "underline",
            "start_ms": 100,
            "duration_ms": 380,
        }]
        for idx, w in enumerate(words):
            s_ms = int(w.get("start_ms", title_start_ms + title_duration_ms + idx * 580))
            annotations.append({
                "id": f"rough-circle-{idx+1}",
                "type": "circle",
                "card_index": idx,
                "start_ms": s_ms,
                "duration_ms": 420,
            })
            if idx < len(words) - 1:
                next_s = int(words[idx+1].get("start_ms", s_ms + 580))
                arr_ms = (s_ms + next_s) // 2
                annotations.append({
                    "id": f"rough-arrow-{idx+1}",
                    "type": "arrow",
                    "card_from": idx,
                    "card_to": idx + 1,
                    "start_ms": arr_ms,
                    "duration_ms": 400,
                })

    # Anime.js timeline for title and cards entry
    timeline_steps = [
        f"""    .add({{
      targets: '#wb-title',
      opacity: [0, 1],
      translateY: [-28, 0],
      duration: {title_duration_ms},
      easing: 'easeOutBack'
    }}, {title_start_ms})"""
    ]

    card_colors = [
        ("#2563eb", "#eff6ff"),  # Vibrant Royal Blue
        ("#059669", "#ecfdf5"),  # Emerald Green
        ("#d97706", "#fffbeb"),  # Warm Amber
        ("#7c3aed", "#f5f3ff"),  # Deep Violet
        ("#db2777", "#fdf2f8"),  # Rose Pink
    ]

    word_cards_html = []
    card_timing_info = []

    for i, w_info in enumerate(words):
        word_text = html.escape(str(w_info.get("text", f"Point {i+1}")))
        start_ms = int(w_info.get("start_ms", (title_start_ms + title_duration_ms + i * 580)))
        dur_ms = int(w_info.get("duration_ms", 420))
        border_col, bg_col = card_colors[i % len(card_colors)]

        card_id = f"word-card-{i+1}"
        card_timing_info.append({
            "id": card_id,
            "start_ms": start_ms,
            "end_ms": 0,
        })

        word_cards_html.append(
            f"""      <div class="word-card" id="{card_id}" style="border-left-color: {border_col}; background-color: {bg_col};">
        <span class="word-num" style="color: {border_col};">{i+1}.</span>
        <span class="word-text-wrapper"><span class="word-text">{word_text}</span></span>
      </div>"""
        )

        timeline_steps.append(
            f"""    .add({{
      targets: '#{card_id}',
      opacity: [0, 1],
      translateX: [-35, 0],
      duration: {dur_ms},
      easing: 'easeOutBack'
    }}, {start_ms})"""
        )

    for i in range(len(card_timing_info)):
        if i + 1 < len(card_timing_info):
            card_timing_info[i]["end_ms"] = card_timing_info[i + 1]["start_ms"]
        else:
            card_timing_info[i]["end_ms"] = total_duration_ms

    cards_markup = "\n".join(word_cards_html)
    card_timing_json = json.dumps(card_timing_info)

    # Clean annotations for JS serializing (remove non-JSON objects)
    serializable_annotations = []
    for a in annotations:
        serializable_annotations.append({
            "id": a["id"],
            "type": a.get("type", ""),
            "start_ms": int(a.get("start_ms", 0)),
            "duration_ms": int(a.get("duration_ms", 400)),
        })
    annotations_json = json.dumps(serializable_annotations)

    # Determine meaningful gesture trigger moment
    if clean_gesture == "wave":
        gesture_trigger_ms = 350
    elif words and len(words) > 0:
        gesture_trigger_ms = int(words[0].get("start_ms", 600))
    else:
        gesture_trigger_ms = 600

    # Build gesture arms: hand physically attached to arm sleeve in every frame
    # All geometry strictly inside Safe Area [50..1030, 50..1870]
    if clean_gesture == "wave":
        arm_markup = """
      <!-- Left Arm (Resting on Desk) -->
      <path d="M 155 375 Q 120 450 145 540" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
      <ellipse cx="148" cy="552" rx="28" ry="20" fill="#fed7aa"/>
      <!-- Right Arm Waving Rig (Physically Attached Shoulder Rotation) -->
      <g class="active-arm-gesture" id="arm-gesture-wave" style="transform-origin: 370px 375px;">
        <path d="M 370 375 Q 425 290 450 210" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
        <circle cx="452" cy="198" r="22" fill="#fed7aa"/>
        <path d="M 440 184 L 436 160 M 450 180 L 450 154 M 460 182 L 463 158 M 468 188 L 476 166" stroke="#fed7aa" stroke-width="7" stroke-linecap="round"/>
        <path d="M 438 200 L 426 195" stroke="#fed7aa" stroke-width="7" stroke-linecap="round"/>
      </g>"""
    elif clean_gesture == "point":
        arm_markup = """
      <!-- Left Arm (Resting on Desk) -->
      <path d="M 155 375 Q 120 450 145 540" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
      <ellipse cx="148" cy="552" rx="28" ry="20" fill="#fed7aa"/>
      <!-- Right Arm Pointing Rig (Physically Attached Shoulder Rotation) -->
      <g class="active-arm-gesture" id="arm-gesture-point" style="transform-origin: 370px 375px;">
        <path d="M 370 375 Q 430 300 460 220" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
        <circle cx="460" cy="216" r="22" fill="#fed7aa"/>
        <path d="M 465 210 L 510 160" stroke="#fed7aa" stroke-width="14" stroke-linecap="round"/>
        <path d="M 450 216 Q 456 206 464 212" stroke="#fed7aa" stroke-width="10" stroke-linecap="round"/>
        <path d="M 452 226 Q 462 232 472 224" stroke="#fba785" stroke-width="3" fill="none"/>
      </g>"""
    elif clean_gesture == "explain":
        arm_markup = """
      <!-- Left Arm (Resting on Desk) -->
      <path d="M 155 375 Q 120 450 145 540" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
      <ellipse cx="148" cy="552" rx="28" ry="20" fill="#fed7aa"/>
      <!-- Right Arm Explain Rig (Physically Attached Shoulder Rotation) -->
      <g class="active-arm-gesture" id="arm-gesture-explain" style="transform-origin: 370px 375px;">
        <path d="M 370 375 Q 425 410 460 360" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
        <ellipse cx="468" cy="354" rx="22" ry="16" fill="#fed7aa"/>
        <path d="M 480 348 L 506 340 M 482 355 L 510 352 M 480 363 L 506 365 M 474 370 L 498 376" stroke="#fed7aa" stroke-width="6.5" stroke-linecap="round"/>
        <path d="M 460 346 L 454 334" stroke="#fed7aa" stroke-width="7" stroke-linecap="round"/>
      </g>"""
    elif clean_gesture == "thumbs_up":
        arm_markup = """
      <!-- Left Arm (Resting on Desk) -->
      <path d="M 155 375 Q 120 450 145 540" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
      <ellipse cx="148" cy="552" rx="28" ry="20" fill="#fed7aa"/>
      <!-- Right Arm Thumbs Up Rig (Physically Attached Shoulder Rotation) -->
      <g class="active-arm-gesture" id="arm-gesture-thumbs_up" style="transform-origin: 370px 375px;">
        <path d="M 370 375 Q 425 390 450 320" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
        <circle cx="450" cy="312" r="20" fill="#fed7aa"/>
        <path d="M 450 312 L 450 270" stroke="#fed7aa" stroke-width="14" stroke-linecap="round"/>
      </g>"""
    elif clean_gesture == "shrug":
        arm_markup = """
      <!-- Left Arm (Resting on Desk) -->
      <path d="M 155 375 Q 120 450 145 540" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
      <ellipse cx="148" cy="552" rx="28" ry="20" fill="#fed7aa"/>
      <!-- Right Arm Shrug Rig (Physically Attached Shoulder Rotation) -->
      <g class="active-arm-gesture" id="arm-gesture-shrug" style="transform-origin: 370px 375px;">
        <path d="M 370 375 Q 405 400 420 375" stroke="#1e40af" stroke-width="42" stroke-linecap="round" fill="none"/>
        <ellipse cx="425" cy="365" rx="20" ry="16" fill="#fed7aa"/>
      </g>"""
    else:  # idle
        arm_markup = """
      <!-- Left Arm (Resting on Desk) -->
      <path d="M 155 375 Q 120 450 145 540" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
      <ellipse cx="148" cy="552" rx="28" ry="20" fill="#fed7aa"/>
      <!-- Right Arm Idle Rest (Resting on Desk) -->
      <g class="active-arm-gesture" id="arm-gesture-idle" style="transform-origin: 370px 375px;">
        <path d="M 370 375 Q 400 450 375 540" stroke="#1e40af" stroke-width="44" stroke-linecap="round" fill="none"/>
        <ellipse cx="372" cy="552" rx="28" ry="20" fill="#fed7aa"/>
      </g>"""

    timeline_chain = "\n".join(timeline_steps)
    mouth_cues_json = json.dumps(mouth_cues or [])
    shelf_decor_html, desk_props_html = generate_scene_decorations(scene_number)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={width}, height={height}">
  <title>{safe_title}</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      width: {width}px;
      height: {height}px;
      /* Rich Colored Gradient Wall for dramatic whiteboard contrast */
      background: radial-gradient(ellipse at 50% 20%, #222b3d 0%, #171d2b 50%, #0d121c 100%);
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      position: relative;
    }}

    /* Light Vignette at Canvas Edges (Pure CSS) */
    .vignette-overlay {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      background: radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 62%, rgba(5, 8, 15, 0.45) 100%);
      z-index: 90;
    }}

    /* Studio Wall Shelf */
    .studio-shelf {{
      position: absolute;
      height: 16px;
      background: #475569;
      border-radius: 4px;
      box-shadow: 0 8px 18px rgba(0,0,0,0.35);
    }}

    /* Whiteboard Outer Frame with Soft Ambient Glow */
    .whiteboard-outer {{
      position: absolute;
      top: 65px;
      left: 100px;
      width: 880px;
      height: 560px;
      background: #ffffff;
      border: 22px solid #1e293b;
      border-radius: 32px;
      box-shadow: 0 0 50px rgba(56, 189, 248, 0.20), 0 0 100px rgba(99, 102, 241, 0.16), 0 30px 60px -12px rgba(0, 0, 0, 0.55);
      padding: 24px 36px 26px 36px;
      display: flex;
      flex-direction: column;
      align-items: center;
      z-index: 2;
    }}
    .whiteboard-outer::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 30%;
      background: linear-gradient(180deg, rgba(255,255,255,0.45) 0%, rgba(255,255,255,0) 100%);
      pointer-events: none;
      border-radius: 8px 8px 0 0;
    }}

    /* Rough.js hand-drawn sketch overlay inside the whiteboard */
    #rough-canvas {{
      position: absolute;
      top: 0;
      left: 0;
      width: 880px;
      height: 560px;
      pointer-events: none;
      z-index: 10;
    }}

    /* Marker Tray */
    .marker-tray {{
      position: absolute;
      bottom: -18px;
      left: 25%;
      width: 50%;
      height: 18px;
      background: #334155;
      border-radius: 0 0 10px 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 24px;
    }}
    .marker {{
      width: 50px;
      height: 7px;
      border-radius: 3px;
    }}
    .marker.black {{ background: #0f172a; }}
    .marker.blue {{ background: #2563eb; }}
    .marker.red {{ background: #dc2626; }}
    .marker.eraser {{ width: 80px; height: 11px; background: #475569; }}

    /* Whiteboard Title Badge */
    .title-badge {{
      margin-top: 4px;
      padding: 14px 42px;
      background: #0f172a;
      color: #ffffff;
      font-size: 46px;
      font-weight: 800;
      letter-spacing: -0.02em;
      border-radius: 18px;
      text-align: center;
      max-width: 90%;
      box-shadow: 0 12px 25px -4px rgba(15, 23, 42, 0.35);
      opacity: 0;
    }}

    /* Whiteboard Word Cards */
    .word-list {{
      margin-top: 18px;
      display: flex;
      flex-direction: column;
      gap: 46px;
      width: 100%;
      align-items: center;
    }}
    .word-card {{
      width: 92%;
      padding: 16px 32px;
      border-left: 18px solid #2563eb;
      border-radius: 18px;
      box-shadow: 0 8px 20px -3px rgba(0, 0, 0, 0.08);
      display: flex;
      align-items: center;
      gap: 24px;
      opacity: 0;
      transition: box-shadow 0.25s ease, border-left-width 0.25s ease, background-color 0.25s ease;
    }}
    .word-card.active-speaking {{
      background-color: #ffffff !important;
      border-left-width: 26px !important;
      box-shadow: 0 14px 30px rgba(37, 99, 235, 0.35), 0 0 0 4px rgba(37, 99, 235, 0.32) !important;
    }}
    .word-num {{
      font-size: 46px;
      font-weight: 900;
      user-select: none;
      min-width: 48px;
    }}
    .word-text-wrapper {{
      display: inline-block;
      padding: 2px 10px;
    }}
    .word-text {{
      font-size: 42px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.01em;
      display: inline-block;
    }}

    /* Presenter Character Rig: 560x630, Soft Drop Shadow & Warm Side Lighting */
    #character-rig {{
      position: absolute;
      top: 670px;
      left: 75px;
      width: 560px;
      height: 630px;
      z-index: 5;
      transform-origin: 280px 600px;
      filter: drop-shadow(0 20px 28px rgba(0, 0, 0, 0.50));
    }}

    /* Desk and Surface Props */
    .desk-container {{
      position: absolute;
      top: 1220px;
      left: 0;
      width: {width}px;
      height: 700px;
      z-index: 6;
    }}
    .desk-bevel {{
      width: 100%;
      height: 12px;
      background: #475569;
    }}
    .desk-top {{
      width: 100%;
      height: 38px;
      background: #1e293b;
      box-shadow: 0 14px 28px rgba(0,0,0,0.4);
    }}
    .desk-body {{
      width: 100%;
      height: 650px;
      background: #0f172a;
    }}
    .desk-props {{
      position: absolute;
      top: 1100px;
      left: 0;
      width: {width}px;
      height: 130px;
      z-index: 7;
      pointer-events: none;
    }}
  </style>
  <script>
{anime_js}
{rough_js}
  </script>
</head>
<body>
  <div class="vignette-overlay"></div>

  <!-- Studio Room Wall Details (Constant Set Across All Scenes) -->
{shelf_decor_html}

  <!-- Whiteboard on Wall -->
  <div class="whiteboard-outer">
    <svg id="rough-canvas" width="880" height="560"></svg>
    <div class="title-badge" id="wb-title">{safe_title}</div>
    <div class="word-list">
{cards_markup}
    </div>
    <div class="marker-tray">
      <div class="marker black"></div>
      <div class="marker blue"></div>
      <div class="marker red"></div>
      <div class="marker eraser"></div>
    </div>
  </div>

  <!-- Presenter Character Rig (Clean 7-Layer Head Redesign, Physically Attached Arms) -->
  <div id="character-rig">
    <svg viewBox="0 0 560 630" width="560" height="630" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- Warm Side Light Gradient from the Right -->
        <linearGradient id="warm-sidelight" x1="1" y1="0" x2="0" y2="0">
          <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.65"/>
          <stop offset="35%" stop-color="#f59e0b" stop-opacity="0.22"/>
          <stop offset="100%" stop-color="#fbbf24" stop-opacity="0"/>
        </linearGradient>
      </defs>

      <!-- Ergonomic Chair -->
      <rect x="130" y="190" width="260" height="370" rx="46" fill="#1e293b"/>

      <!-- Body & Royal Blue Sweater (Raised shoulders for natural neck height) -->
      <path d="M 115 365 Q 260 320 405 365 L 440 630 L 80 630 Z" fill="#1e40af"/>
      <!-- Warm Side Light on Right Shoulder of Sweater -->
      <path d="M 320 335 Q 370 355 405 365 L 440 630 L 380 630 Z" fill="url(#warm-sidelight)"/>

      <!-- Shirt Collar (Crisp White V-Neck, nicely seated) -->
      <path d="M 224 320 L 260 375 L 296 320 Z" fill="#ffffff"/>
      <path d="M 240 320 L 260 355 L 280 320 Z" fill="#0f172a" opacity="0.15"/>

      <!-- ARM MARKUP (Left resting, Right rest & gesture) -->
{arm_markup}

      <!-- ==================== HEAD REDESIGN (7 STRICT LAYERS) ==================== -->
      <!-- 1. Hair Back -->
      <g id="layer-1-hair-back">
        <path d="M 145 250 C 125 140, 165 45, 260 42 C 355 45, 395 140, 375 250 C 360 275, 345 240, 345 200 C 345 115, 310 85, 260 85 C 210 85, 175 115, 175 200 C 175 240, 160 275, 145 250 Z" fill="#0f172a"/>
        <path d="M 260 42 C 355 45, 395 140, 375 250 C 360 275, 345 240, 345 200 C 345 115, 310 85, 260 85 Z" fill="url(#warm-sidelight)" opacity="0.35"/>
      </g>

      <!-- 2. Neck (Natural, proportional height and width) -->
      <g id="layer-2-neck">
        <rect x="222" y="275" width="76" height="55" rx="8" fill="#fed7aa"/>
        <path d="M 222 280 Q 260 304 298 280 L 298 296 Q 260 316 222 296 Z" fill="#d97706" opacity="0.25"/>
        <rect x="264" y="275" width="34" height="55" rx="4" fill="url(#warm-sidelight)" opacity="0.7"/>
      </g>

      <!-- 3. Head Base -->
      <g id="layer-3-head">
        <path d="M 172 185 C 170 105, 210 75, 260 75 C 310 75, 350 105, 348 185 C 348 245, 326 302, 260 302 C 194 302, 172 245, 172 185 Z" fill="#fed7aa"/>
        <path d="M 285 80 C 330 100, 350 145, 348 205 C 346 255, 322 298, 260 302 C 295 296, 336 260, 336 200 C 336 145, 305 105, 285 80 Z" fill="url(#warm-sidelight)" opacity="0.85"/>
      </g>

      <!-- 4. Ears -->
      <g id="layer-4-ears">
        <!-- Left Ear -->
        <ellipse cx="168" cy="206" rx="14" ry="18" fill="#fed7aa"/>
        <path d="M 172 198 Q 161 206 170 214" stroke="#fba785" stroke-width="3" fill="none" stroke-linecap="round"/>
        <!-- Right Ear -->
        <ellipse cx="352" cy="206" rx="14" ry="18" fill="#fed7aa"/>
        <path d="M 348 198 Q 359 206 350 214" stroke="#fba785" stroke-width="3" fill="none" stroke-linecap="round"/>
        <ellipse cx="352" cy="206" rx="14" ry="18" fill="url(#warm-sidelight)" opacity="0.6"/>
      </g>

      <!-- 5. Face Features -->
      <g id="layer-5-face">
        <!-- Cheeks Blush -->
        <ellipse cx="196" cy="236" rx="14" ry="8" fill="#fb7185" opacity="0.38"/>
        <ellipse cx="324" cy="236" rx="14" ry="8" fill="#fb7185" opacity="0.45"/>

        <!-- Eyebrows (Smart, expressive arch) -->
        <path d="M 194 172 Q 215 160 235 170" stroke="#0f172a" stroke-width="4.8" stroke-linecap="round" fill="none"/>
        <path d="M 285 170 Q 305 160 326 172" stroke="#0f172a" stroke-width="4.8" stroke-linecap="round" fill="none"/>

        <!-- Eyes -->
        <circle cx="215" cy="204" r="14" fill="#0f172a"/>
        <circle cx="219" cy="199" r="4.5" fill="#ffffff"/>
        <circle cx="212" cy="207" r="2" fill="#ffffff" opacity="0.6"/>

        <circle cx="305" cy="204" r="14" fill="#0f172a"/>
        <circle cx="309" cy="199" r="4.5" fill="#ffffff"/>
        <circle cx="302" cy="207" r="2" fill="#ffffff" opacity="0.6"/>

        <!-- Nose -->
        <path d="M 258 218 Q 264 232 257 236" stroke="#d97706" stroke-width="2.6" stroke-linecap="round" fill="none" opacity="0.75"/>

        <!-- Mouth Closed (Friendly Smile) -->
        <g id="mouth-closed">
          <path d="M 242 260 Q 260 274 278 260" stroke="#0f172a" stroke-width="4.5" stroke-linecap="round" fill="none"/>
        </g>
        <!-- Mouth Open (Speaking Viseme) -->
        <g id="mouth-open" style="display: none;">
          <path d="M 240 254 Q 260 248 280 254 Q 278 278 260 280 Q 242 278 240 254 Z" fill="#881337" stroke="#0f172a" stroke-width="3.5"/>
          <path d="M 245 254 Q 260 260 275 254" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" fill="none"/>
          <ellipse cx="260" cy="272" rx="8" ry="4" fill="#f43f5e"/>
        </g>
      </g>

      <!-- 6. Designer Glasses -->
      <g id="layer-6-glasses">
        <rect x="186" y="178" width="58" height="52" rx="16" stroke="#1e293b" stroke-width="4.8" fill="rgba(255,255,255,0.18)"/>
        <rect x="276" y="178" width="58" height="52" rx="16" stroke="#1e293b" stroke-width="4.8" fill="rgba(255,255,255,0.18)"/>
        <path d="M 244 200 Q 260 192 276 200" stroke="#1e293b" stroke-width="4.8" fill="none" stroke-linecap="round"/>
        <path d="M 186 200 L 169 204" stroke="#1e293b" stroke-width="3.5" stroke-linecap="round"/>
        <path d="M 334 200 L 351 204" stroke="#1e293b" stroke-width="3.5" stroke-linecap="round"/>
        <line x1="194" y1="186" x2="208" y2="186" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>
        <line x1="284" y1="186" x2="298" y2="186" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>
      </g>

      <!-- 7. Hair Front (Volume, Hairline, Fringe & Sideburns framing face) -->
      <g id="layer-7-hair-front">
        <!-- Full solid hair volume over cranium with clean outline down to hairline -->
        <path d="M 158 175 C 150 75, 198 35, 260 35 C 322 35, 370 75, 362 175 C 348 135, 305 110, 260 110 C 215 110, 172 135, 158 175 Z" fill="#0f172a"/>
        <!-- Solid hair crown filling cranium down to hairline at Y=125 -->
        <path d="M 162 170 C 158 100, 200 60, 260 60 C 320 60, 362 100, 358 170 C 340 135, 305 122, 260 122 C 215 122, 180 135, 162 170 Z" fill="#0f172a"/>
        <!-- Natural parted fringe sweeping across forehead framing face -->
        <path d="M 162 165 C 175 132, 215 125, 260 125 C 310 125, 345 138, 360 165 C 340 144, 305 136, 260 136 C 215 136, 180 146, 162 165 Z" fill="#1e293b"/>
        <path d="M 235 126 C 275 126, 320 136, 350 162 C 328 146, 288 142, 252 142 C 225 142, 200 148, 182 156 C 200 138, 220 126, 235 126 Z" fill="#0f172a"/>
        <!-- Left & Right Sideburns framing face in front of ears -->
        <path d="M 168 165 C 166 186, 168 205, 174 212 C 176 204, 177 186, 174 165 Z" fill="#0f172a"/>
        <path d="M 352 165 C 354 186, 352 205, 346 212 C 344 204, 343 186, 346 165 Z" fill="#0f172a"/>
        <!-- Warm rim highlight on top hair -->
        <path d="M 260 35 C 322 35, 370 75, 362 175 C 348 115, 310 80, 260 80 Z" fill="url(#warm-sidelight)" opacity="0.35"/>
      </g>
    </svg>
  </div>

  <!-- Foreground Desk Props (Constant Across All Scenes) -->
  <div class="desk-props">
    <svg viewBox="0 0 1080 130" width="1080" height="130">
{desk_props_html}
    </svg>
  </div>

  <!-- Desk Surface -->
  <div class="desk-container">
    <div class="desk-bevel"></div>
    <div class="desk-top"></div>
    <div class="desk-body"></div>
  </div>

  <script>
    const fps = {fps};
    window.__mouthCues = {mouth_cues_json};
    window.__cardTimings = {card_timing_json};
    window.__annotations = {annotations_json};
    window.__gestureTriggerMs = {gesture_trigger_ms};
    window.__gestureType = "{clean_gesture}";

    window.__timeline = anime.timeline({{
      autoplay: false,
      duration: {total_duration_ms}
    }});

    window.__timeline
{timeline_chain};

    // Store stroke drawing items for progressive animated line drawing
    window.__annotationDrawers = [];

    // Initialize Rough.js Sketch Drawings with Fixed Deterministic Seeds
    function initRoughSketches() {{
      const roughSvg = document.getElementById("rough-canvas");
      const wbEl = document.querySelector(".whiteboard-outer");
      if (!roughSvg || !wbEl || typeof rough === "undefined") return;

      const rc = rough.svg(roughSvg);
      const canvasRect = roughSvg.getBoundingClientRect();

      // 1. Hand-sketched underline under the title badge (fixed seed: 101)
      const titleEl = document.getElementById("wb-title");
      if (titleEl) {{
        const tRect = titleEl.getBoundingClientRect();
        const leftX = (tRect.left - canvasRect.left) + 16;
        const rightX = (tRect.right - canvasRect.left) - 16;
        const underY = (tRect.bottom - canvasRect.top) + 8;
        const uLine = rc.line(leftX, underY, rightX, underY, {{
          seed: 101,
          stroke: '#f59e0b',
          strokeWidth: 5.5,
          roughness: 1.3,
          bowing: 1.2
        }});
        uLine.id = 'rough-title-underline';
        roughSvg.appendChild(uLine);
      }}

      // 2. Hand-sketched circles around keyword text (NOT list numbers)
      const cards = document.querySelectorAll(".word-card");
      const cardRects = [];

      cards.forEach((card, idx) => {{
        const textEl = card.querySelector(".word-text") || card.querySelector(".word-text-wrapper") || card;
        const numEl = card.querySelector(".word-num");
        const tRect = textEl.getBoundingClientRect();
        const nRect = numEl ? numEl.getBoundingClientRect() : null;

        const cX = (tRect.left + tRect.right) / 2 - canvasRect.left;
        const cY = (tRect.top + tRect.bottom) / 2 - canvasRect.top;

        // Ensure circle clears the number prefix with safe padding
        const numRight = nRect ? (nRect.right - canvasRect.left) : 0;
        const minLeft = numRight > 0 ? numRight + 12 : 0;
        let cW = Math.max(tRect.width + 56, 150);
        if (cX - cW / 2 < minLeft) {{
          cW = Math.max(tRect.width + 30, (cX - minLeft) * 2 - 4);
        }}
        const cH = Math.max(tRect.height + 36, 80);

        const circleNode = rc.ellipse(cX, cY, cW, cH, {{
          seed: 201 + idx * 13,
          stroke: '#2563eb',
          strokeWidth: 4.5,
          roughness: 1.25,
        }});
        circleNode.id = `rough-circle-${{idx+1}}`;
        circleNode.classList.add("rough-card-circle");
        roughSvg.appendChild(circleNode);

        cardRects.push(card.getBoundingClientRect());
      }});

      // 3. Hand-sketched larger, clearly visible arrows between list cards (fixed seeds: 301, 351)
      for (let i = 0; i < cardRects.length - 1; i++) {{
        const r1 = cardRects[i];
        const r2 = cardRects[i + 1];
        const arrowX = (r1.left + r1.right) / 2 - canvasRect.left;
        const y1 = (r1.bottom - canvasRect.top) + 2;
        const y2 = (r2.top - canvasRect.top) - 2;
        if (y2 > y1) {{
          const shaft = rc.line(arrowX, y1, arrowX, y2, {{
            seed: 301 + i * 17,
            stroke: '#1e40af',
            strokeWidth: 6.0,
            roughness: 1.1
          }});
          shaft.classList.add("arrow-shaft");

          const head = rc.linearPath([
            [arrowX - 22, y2 - 20],
            [arrowX, y2],
            [arrowX + 22, y2 - 20]
          ], {{
            seed: 351 + i * 17,
            stroke: '#1e40af',
            strokeWidth: 6.0,
            roughness: 1.1
          }});
          head.classList.add("arrow-head");

          const arrowGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
          arrowGroup.id = `rough-arrow-${{i+1}}`;
          arrowGroup.classList.add("rough-arrow");
          arrowGroup.appendChild(shaft);
          arrowGroup.appendChild(head);
          roughSvg.appendChild(arrowGroup);
        }}
      }}

      // Prepare progressive drawing stroke-dasharray & stroke-dashoffset for each annotation
      window.__annotations.forEach(ann => {{
        const node = document.getElementById(ann.id);
        if (!node) return;
        const paths = node.querySelectorAll("path");
        const pathData = [];
        paths.forEach(p => {{
          const len = p.getTotalLength();
          p.style.strokeDasharray = len;
          p.style.strokeDashoffset = len;
          pathData.push({{ el: p, len: len }});
        }});
        node.style.opacity = "0";
        window.__annotationDrawers.push({{
          id: ann.id,
          node: node,
          type: ann.type,
          start_ms: ann.start_ms,
          duration_ms: ann.duration_ms,
          paths: pathData,
        }});
      }});
    }}

    // Call sketch initialization on page load
    initRoughSketches();

    window.seekAnimation = function(ms) {{
      window.__timeline.seek(ms);

      // 1. Loudness-driven mouth sync
      const frameIdx = Math.floor((ms / 1000.0) * fps);
      const isOpen = (window.__mouthCues && window.__mouthCues[frameIdx]) || false;
      const mClosed = document.getElementById("mouth-closed");
      const mOpen = document.getElementById("mouth-open");
      if (mClosed && mOpen) {{
        mClosed.style.display = isOpen ? "none" : "block";
        mOpen.style.display = isOpen ? "block" : "none";
      }}

      // 2. Relaxed rest pose with gentle breathing sway only (NO constant bobbing)
      const charRig = document.getElementById("character-rig");
      if (charRig) {{
        const breatheY = Math.sin(ms * 0.0015) * 1.5;
        charRig.style.transform = `translateY(${{breatheY.toFixed(2)}}px)`;
      }}

      // 3. Purposeful gesture animation: raises at meaningful moment, holds, returns to rest with easing
      const gestType = window.__gestureType;
      const gestArm = document.getElementById(`arm-gesture-${{gestType}}`);
      const trigMs = window.__gestureTriggerMs;

      const restAngles = {{
        wave: 132,
        point: 130,
        explain: 78,
        thumbs_up: 110,
        shrug: 45,
        idle: 0
      }};
      const restDeg = restAngles[gestType] || 0;

      if (gestArm && gestType !== "idle") {{
        const raiseDur = 350;
        const holdDur = 1100;
        const lowerDur = 400;
        const holdEnd = trigMs + raiseDur + holdDur;
        const animEnd = holdEnd + lowerDur;

        if (ms < trigMs) {{
          gestArm.style.transform = `rotate(${{restDeg}}deg)`;
        }} else if (ms < trigMs + raiseDur) {{
          const t = (ms - trigMs) / raiseDur;
          // easeOutCubic
          const p = 1 - Math.pow(1 - t, 3);
          const curDeg = restDeg * (1 - p);
          gestArm.style.transform = `rotate(${{curDeg.toFixed(2)}}deg)`;
        }} else if (ms < holdEnd) {{
          if (gestType === "wave") {{
            const waveSway = Math.sin((ms - trigMs - raiseDur) * 0.012) * 5;
            gestArm.style.transform = `rotate(${{waveSway.toFixed(2)}}deg)`;
          }} else {{
            gestArm.style.transform = "rotate(0deg)";
          }}
        }} else if (ms < animEnd) {{
          const t = (ms - holdEnd) / lowerDur;
          // easeInOutQuad
          const p = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
          const curDeg = restDeg * p;
          gestArm.style.transform = `rotate(${{curDeg.toFixed(2)}}deg)`;
        }} else {{
          gestArm.style.transform = `rotate(${{restDeg}}deg)`;
        }}
      }} else if (gestArm) {{
        gestArm.style.transform = "rotate(0deg)";
      }}

      // 4. Progressive stroke-by-stroke drawing synced to speech
      if (window.__annotationDrawers) {{
        window.__annotationDrawers.forEach(drawer => {{
          const s = drawer.start_ms;
          const d = drawer.duration_ms;

          if (ms < s) {{
            drawer.node.style.opacity = "0";
            drawer.paths.forEach(p => p.el.style.strokeDashoffset = String(p.len));
          }} else if (ms >= s + d) {{
            drawer.node.style.opacity = "1";
            drawer.paths.forEach(p => p.el.style.strokeDashoffset = "0");
          }} else {{
            const pVal = (ms - s) / d;
            drawer.node.style.opacity = "1";
            if (drawer.type === "arrow") {{
              const shaftNodes = drawer.node.querySelectorAll(".arrow-shaft path");
              const headNodes = drawer.node.querySelectorAll(".arrow-head path");
              const pShaft = Math.min(1, pVal / 0.60);
              const pHead = Math.max(0, (pVal - 0.60) / 0.40);
              shaftNodes.forEach(p => {{
                const len = parseFloat(p.style.strokeDasharray) || 50;
                p.style.strokeDashoffset = String(len * (1 - pShaft));
              }});
              headNodes.forEach(p => {{
                const len = parseFloat(p.style.strokeDasharray) || 50;
                p.style.strokeDashoffset = String(len * (1 - pHead));
              }});
            }} else {{
              drawer.paths.forEach(item => {{
                item.el.style.strokeDashoffset = String(item.len * (1 - pVal));
              }});
            }}
          }}
        }});
      }}

      // 5. Highlight item currently being spoken
      if (window.__cardTimings && window.__cardTimings.length > 0) {{
        window.__cardTimings.forEach(timing => {{
          const cardEl = document.getElementById(timing.id);
          const isSpoken = (ms >= timing.start_ms && ms < timing.end_ms);
          if (cardEl) {{
            if (isSpoken) {{
              cardEl.classList.add("active-speaking");
            }} else {{
              cardEl.classList.remove("active-speaking");
            }}
          }}
        }});
      }}
    }};
  </script>
</body>
</html>
"""


@register_renderer("animejs")
class AnimeJSRenderPlugin(RenderInterface):
    """HTML5 / Anime.js code-driven whiteboard rendering engine with Rough.js hand-drawn sketches and character mouth sync."""

    @property
    def name(self) -> str:
        return "animejs"

    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Renders a single still scene image frame at the completion state of the animation."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration_sec = 2.5
        title, words_data, annotations = extract_whiteboard_content_and_annotations(scene, duration_sec)

        scene_gesture = getattr(scene, "gesture", None) or "idle"
        html_str = generate_whiteboard_html(
            title=title,
            words=words_data,
            duration_sec=duration_sec,
            mouth_cues=[False] * int(duration_sec * config.VIDEO_FPS),
            gesture=scene_gesture,
            width=config.VIDEO_WIDTH,
            height=config.VIDEO_HEIGHT,
            scene_number=scene.scene_number,
            annotations=annotations,
        )

        html_file = (temp_dir / f"animejs_scene_{scene.scene_number}.html").resolve()
        html_file.write_text(html_str, encoding="utf-8")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": config.VIDEO_WIDTH, "height": config.VIDEO_HEIGHT})
            page.goto(html_file.as_uri())
            # Seek to completion of the animations
            page.evaluate(f"window.seekAnimation({int(duration_sec * 1000)})")
            page.screenshot(path=str(output_path), type="png")
            browser.close()

        return output_path

    def render_whiteboard_video(
        self,
        title: str,
        words: List[Dict[str, Any]],
        audio_path: Optional[Path],
        output_path: Path,
        duration_sec: float = 3.0,
        gesture: str = "idle",
        fps: int = config.VIDEO_FPS,
        temp_dir: Optional[Path] = None,
        scene_number: int = 1,
        annotations: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """
        Renders a fully animated MP4 video with easing transitions synced to an audio clip.
        Mouth flapping is driven by voice audio loudness (RMS).
        Character exhibits subtle idle motion.
        Streams Playwright frames directly into FFmpeg stdin.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = temp_dir or output_path.parent / "temp_animejs"
        work_dir.mkdir(parents=True, exist_ok=True)

        mouth_cues = compute_mouth_cues_from_audio(audio_path, fps=fps)

        html_content = generate_whiteboard_html(
            title=title,
            words=words,
            duration_sec=duration_sec,
            mouth_cues=mouth_cues,
            gesture=gesture,
            fps=fps,
            width=config.VIDEO_WIDTH,
            height=config.VIDEO_HEIGHT,
            scene_number=scene_number,
            annotations=annotations,
        )

        html_file = (work_dir / "whiteboard_scene.html").resolve()
        html_file.write_text(html_content, encoding="utf-8")

        total_frames = max(1, int(round(fps * duration_sec)))

        cmd = [
            "ffmpeg", "-y",
            "-f", "image2pipe",
            "-vcodec", "png",
            "-r", str(fps),
            "-i", "pipe:0",
        ]

        if audio_path and audio_path.is_file():
            cmd.extend([
                "-i", str(audio_path.resolve()),
                "-af", "apad",
                "-c:a", "aac",
                "-b:a", "192k",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-t", f"{duration_sec:.3f}",
            str(output_path.resolve()),
        ])

        log_file = work_dir / "ffmpeg_render.log"
        with open(log_file, "wb") as lf:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=lf,
            )

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": config.VIDEO_WIDTH, "height": config.VIDEO_HEIGHT})
                page.goto(html_file.as_uri())

                try:
                    for frame_idx in range(total_frames):
                        t_ms = (frame_idx / fps) * 1000.0
                        page.evaluate(f"window.seekAnimation({t_ms})")
                        png_bytes = page.screenshot(type="png")
                        proc.stdin.write(png_bytes)
                except (BrokenPipeError, OSError) as e:
                    logger.error("FFmpeg stdin pipe closed prematurely: %s", e)

                browser.close()

            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.wait()

        if proc.returncode != 0:
            err_msg = log_file.read_text(encoding="utf-8", errors="ignore") if log_file.exists() else "Unknown error"
            raise RuntimeError(f"FFmpeg animejs video render failed: {err_msg}")

        return output_path

    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
        character_refs: Optional[Dict[str, Path]] = None,
        scene_audios: Optional[List[SceneAudio]] = None,
    ) -> List[Path]:
        """
        Renders scenes for the screenplay plan.
        If scene_audios is provided, generates animated MP4 video clips with mouth sync and idle motion.
        Otherwise renders still PNG frames.
        """
        temp_dir.mkdir(parents=True, exist_ok=True)
        results = []

        if scene_audios and len(scene_audios) == len(plan.scenes):
            for i, (scene, audio) in enumerate(zip(plan.scenes, scene_audios)):
                clip_path = temp_dir / f"animejs_scene_{scene.scene_number}.mp4"
                title, words, annotations = extract_whiteboard_content_and_annotations(
                    scene, audio.scene_total_duration, audio.word_timings
                )
                scene_gesture = getattr(scene, "gesture", None) or "idle"
                self.render_whiteboard_video(
                    title=title,
                    words=words,
                    audio_path=audio.audio_path,
                    output_path=clip_path,
                    duration_sec=audio.scene_total_duration,
                    gesture=scene_gesture,
                    fps=config.VIDEO_FPS,
                    temp_dir=temp_dir / f"scene_{scene.scene_number}_tmp",
                    scene_number=scene.scene_number,
                    annotations=annotations,
                )
                results.append(clip_path)
        else:
            for scene in plan.scenes:
                out_path = temp_dir / f"animejs_scene_{scene.scene_number}.png"
                self.render_scene(scene, plan.characters, style_preset, out_path, temp_dir)
                results.append(out_path)

        return results
