"""
Purpose: Whiteboard text parsing, card layout extraction, and word-synchronized sketch annotations.
Inputs: Scene action/dialogue descriptions, scene durations, and Whisper word timings.
Outputs: Synchronized whiteboard titles, word cards, underlines, circles, and connection arrows.
Depends on: core.models, re, typing
Used by: plugins.render.animejs, plugins.render.animejs.plugin
Config keys: None
Tests: tests/unit/test_animejs.py
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from toonshorts.core.models import Scene, WordTiming, strip_speaker_label


def extract_whiteboard_content_and_annotations(
    scene: Scene,
    duration_sec: float,
    word_timings: Optional[List[WordTiming]] = None,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts whiteboard title, bullet point cards, and synchronized annotations (underlines, circles, arrows).
    Each annotation is tied to a specific word and starts drawing when that word starts.
    """
    clean_dlg = strip_speaker_label(scene.dialogue_line)
    action_text = strip_speaker_label(scene.action or "").strip()
    if ":" in action_text:
        title_part, points_part = action_text.split(":", 1)
        title = title_part.strip()
        points = [p.strip() for p in points_part.replace(";", ",").split(",") if p.strip()]
    elif action_text:
        title = action_text[:45]
        words_dlg = clean_dlg.split()
        if len(words_dlg) >= 6:
            points = [
                " ".join(words_dlg[: len(words_dlg) // 3]),
                " ".join(words_dlg[len(words_dlg) // 3 : 2 * len(words_dlg) // 3]),
                " ".join(words_dlg[2 * len(words_dlg) // 3 :]),
            ]
        else:
            points = [clean_dlg[:30]]
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
        dlg_words = [w for w in clean_dlg.split() if w.strip()]
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
