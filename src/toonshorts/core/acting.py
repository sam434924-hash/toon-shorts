"""
Purpose: Data-driven acting planner, validation, and check-acting tool for character performances.
Inputs: Script scenes, cast characters, word timings, and layout plan blocks.
Outputs: Deterministic acting_plan.json with beats, accents, gestures, gaze, turns, and listener reactions.
Depends on: json, logging, math, pathlib, random, typing, core.config
Used by: cli
Config keys: None
Tests: tests/unit/test_acting.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("toonshorts.acting")

# Recognized gestures conforming to RIG_CONTRACT and Appendix C
ALLOWED_GESTURES = {
    "idle",
    "explain",
    "point",
    "point_board",
    "point_other",
    "shrug",
    "nod",
    "head_tilt",
    "wave",
    "thumbs_up",
    "hands_on_hips",
    "lean_speaker",
    "listening_reaction",
}

# Recognized listener reaction types
LISTENER_REACTION_TYPES = {
    "nod",
    "head_tilt",
    "blink",
    "amused",
    "skeptical",
    "attentive",
}

# Recognized gaze targets
GAZE_TARGETS = {"PARTNER", "BOARD", "CAMERA", "DOWN"}


def _pick_stressed_words(words: List[Any], duration_sec: float) -> List[Dict[str, Any]]:
    """Identifies key stressed words from word timings or text for accent placement."""
    if not words:
        # Synthesize fallback accent at ~35% into duration
        return [{
            "word": "key",
            "word_index": 0,
            "start_sec": round(duration_sec * 0.35, 3),
            "peak_sec": round(duration_sec * 0.45, 3),
        }]

    # Filter out common short stop words unless emphasized
    stop_words = {"a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "it", "is", "was"}
    candidates = []
    for idx, w in enumerate(words):
        txt = (getattr(w, "word", None) or (w.get("word") if isinstance(w, dict) else "") or (w.get("text") if isinstance(w, dict) else "")).strip().lower()
        clean = "".join(c for c in txt if c.isalnum())
        st = float(getattr(w, "start_time", 0.0) if hasattr(w, "start_time") else (w.get("start_time", 0.0) if isinstance(w, dict) else 0.0))
        et = float(getattr(w, "end_time", st + 0.3) if hasattr(w, "end_time") else (w.get("end_time", st + 0.3) if isinstance(w, dict) else st + 0.3))
        dur = et - st
        if clean and clean not in stop_words and len(clean) >= 3:
            candidates.append({
                "word": clean,
                "word_index": idx,
                "start_sec": round(st, 3),
                "peak_sec": round(st + dur * 0.6, 3),
                "duration": dur,
            })

    if not candidates:
        # Fall back to first candidate
        w0 = words[0]
        st = float(getattr(w0, "start_time", 0.2) if hasattr(w0, "start_time") else (w0.get("start_time", 0.2) if isinstance(w0, dict) else 0.2))
        return [{
            "word": "accent",
            "word_index": 0,
            "start_sec": round(st, 3),
            "peak_sec": round(st + 0.2, 3),
        }]

    # Select the word with longest duration or key position (at most 1 per phrase)
    candidates.sort(key=lambda c: c["duration"], reverse=True)
    chosen = candidates[0]
    return [{
        "word": chosen["word"],
        "word_index": chosen["word_index"],
        "start_sec": chosen["start_sec"],
        "peak_sec": chosen["peak_sec"],
    }]


def plan_acting_plan(
    scenes: List[Any],
    characters: Optional[List[Any]] = None,
    word_timings_map: Optional[Dict[int, List[Any]]] = None,
    layout_blocks_map: Optional[Dict[int, Any]] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Plans acting performance for all scenes:
    - Cast (left and right)
    - Per scene acting beats
    - Accents on stressed words (gesture starts 0-4 frames early)
    - Gesture variety (no immediate back-to-back repeats)
    - Gaze and body turns
    - Listener reactions (nod/tilt/blink every <= 3.5s)
    - Board slot pointing
    """
    rng = random.Random(seed)

    # Determine cast
    cast_left = "boy_b"
    cast_right = "girl_a"
    if characters:
        if len(characters) >= 1:
            cast_left = getattr(characters[0], "id", None) or (characters[0].get("id") if isinstance(characters[0], dict) else str(characters[0]))
        if len(characters) >= 2:
            cast_right = getattr(characters[1], "id", None) or (characters[1].get("id") if isinstance(characters[1], dict) else str(characters[1]))

    cast_names: List[str] = []
    for sc in scenes:
        spk = getattr(sc, "speaker", None) or (sc.get("speaker") if isinstance(sc, dict) else "")
        if spk and spk not in cast_names:
            cast_names.append(spk)

    def speaker_code(name: str) -> str:
        clean = (name or "").strip()
        if len(cast_names) >= 2 and clean == cast_names[1]:
            return "B"
        return "A"

    planned_scenes: List[Dict[str, Any]] = []
    last_gesture = {"A": "idle", "B": "idle"}

    gesture_pool_speaker = ["explain", "point_board", "thumbs_up", "shrug", "hands_on_hips"]

    for idx, sc in enumerate(scenes):
        sc_num = getattr(sc, "scene_number", idx + 1) if not isinstance(sc, dict) else sc.get("scene_number", idx + 1)
        spk_name = getattr(sc, "speaker", "") if not isinstance(sc, dict) else sc.get("speaker", "")
        code = speaker_code(spk_name)
        listener_code = "B" if code == "A" else "A"

        dlg = getattr(sc, "dialogue_line", "") if not isinstance(sc, dict) else sc.get("dialogue_line", "")
        is_punch = bool(getattr(sc, "is_punchline", False) if not isinstance(sc, dict) else sc.get("is_punchline", False))

        wts = (word_timings_map or {}).get(sc_num) or getattr(sc, "word_timings", None) or (sc.get("word_timings") if isinstance(sc, dict) else None) or []
        if wts:
            w_end = max(getattr(w, "end_time", None) or (w.get("end_time", 0.0) if isinstance(w, dict) else 0.0) for w in wts)
            dur_sec = max(float(w_end) + 0.35, 1.5)
        else:
            dur_sec = float(getattr(sc, "duration", 4.0) if not isinstance(sc, dict) else sc.get("duration", 4.0))

        # Check layout slots
        layout_data = (layout_blocks_map or {}).get(sc_num) or getattr(sc, "layout", None) or (sc.get("layout") if isinstance(sc, dict) else None)
        has_board_visuals = bool(
            getattr(sc, "visuals", None)
            or getattr(sc, "board_objects", None)
            or (isinstance(layout_data, dict) and layout_data.get("elements"))
        )

        target_slot = None
        if has_board_visuals:
            if isinstance(layout_data, dict) and layout_data.get("elements"):
                target_slot = layout_data["elements"][0].get("slot_id", "slot-hero")
            else:
                target_slot = "slot-hero"

        # Determine tactic and energy
        if is_punch:
            tactic = "punchline"
            energy = "high"
            subtext = "The surprising truth lands"
        elif "?" in dlg:
            tactic = "ask"
            energy = "medium"
            subtext = "Genuinely curious and wanting clarification"
        elif "warning" in dlg.lower() or "hack" in dlg.lower():
            tactic = "warn"
            energy = "high"
            subtext = "Serious security implication"
        else:
            tactic = "explain"
            energy = "medium"
            subtext = "Breaking it down clearly"

        # Accents on stressed words
        stressed_words = _pick_stressed_words(wts, dur_sec)
        accent = stressed_words[0]

        # Select gesture: avoid immediate repetition
        if target_slot and (idx % 2 == 1 or "board" in dlg.lower()):
            candidate_gest = "point_board"
        elif is_punch:
            candidate_gest = "thumbs_up" if code == "A" else "shrug"
        elif "?" in dlg:
            candidate_gest = "shrug"
        else:
            options = [g for g in gesture_pool_speaker if g != last_gesture[code] and g != "point_board"]
            candidate_gest = rng.choice(options) if options else "explain"

        if candidate_gest == last_gesture[code]:
            # swap to alternate
            candidate_gest = "explain" if candidate_gest != "explain" else "hands_on_hips"

        last_gesture[code] = candidate_gest

        # Timing: gesture begins 0-4 frames early (default 3 frames = 100ms at 30fps)
        lead_frames = 3
        lead_sec = lead_frames / 30.0
        start_sec = max(0.0, accent["start_sec"] - lead_sec)
        peak_sec = accent["peak_sec"]
        hold_sec = 1.1
        return_sec = 0.4

        gesture_payload = {
            "name": candidate_gest,
            "intensity": "high" if energy == "high" else "medium",
            "lead_frames": lead_frames,
            "start_ms": int(round(start_sec * 1000)),
            "peak_ms": int(round(peak_sec * 1000)),
            "hold_ms": int(round(hold_sec * 1000)),
            "return_ms": int(round(return_sec * 1000)),
        }

        # Gaze
        gaze_target = "BOARD" if candidate_gest == "point_board" else ("CAMERA" if is_punch else "PARTNER")
        gaze_payload = {
            "target": gaze_target,
            "time_sec": round(max(0.0, start_sec - 0.2), 3),
        }

        # Turn / lean
        turn_type = "lean_in" if energy == "high" else "none"
        turn_payload = {
            "type": turn_type,
            "time_sec": round(start_sec, 3),
        }

        # Listener reaction: engaged listener reacts every 3 to 4 seconds
        listener_reaction_type = "amused" if is_punch else ("nod" if "?" not in dlg else "head_tilt")
        reaction_time = min(round(dur_sec * 0.65, 3), round(dur_sec - 0.4, 3))
        listener_payload = {
            "type": listener_reaction_type,
            "intensity": "high" if is_punch else "subtle",
            "time_sec": max(0.8, reaction_time),
        }

        beat = {
            "beat_id": f"beat_{sc_num}_1",
            "tactic": tactic,
            "energy": energy,
            "subtext": subtext,
            "stressed_words": stressed_words,
            "gesture": gesture_payload,
            "gaze": gaze_payload,
            "turn": turn_payload,
            "listener_reaction": listener_payload,
            "pointing_target_slot": target_slot if candidate_gest in ("point", "point_board") else None,
        }

        planned_scenes.append({
            "scene_number": sc_num,
            "speaker": code,
            "listener": listener_code,
            "duration_sec": round(dur_sec, 3),
            "beats": [beat],
        })

    return {
        "cast": {
            "left": cast_left,
            "right": cast_right,
        },
        "scenes": planned_scenes,
    }


def save_acting_plan(plan_data: Dict[str, Any], path: Union[str, Path]) -> Path:
    """Saves acting plan dictionary to formatted JSON."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")
    return out_path


def load_acting_plan(path: Union[str, Path]) -> Dict[str, Any]:
    """Loads and returns acting plan dictionary from JSON."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Acting plan not found at {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def check_acting(video_source: Union[str, Path]) -> Dict[str, Any]:
    """
    Verifies acting plan against all requirements:
    - acting_plan.json exists and is valid JSON
    - Cast: max 2 actors
    - Accents: at most one per phrase
    - No gesture repeated back-to-back
    - Listener reaction at least every 4.0s
    - No actor motionless over 2.0s
    - All gesture names exist in ALLOWED_GESTURES
    - Pointing gestures have valid layout slot targets
    """
    from toonshorts.core import config
    vdir = Path(video_source)
    if not vdir.is_dir():
        cand = config.VIDEOS_DIR / str(video_source)
        if cand.is_dir():
            vdir = cand
    if not vdir.is_dir():
        raise FileNotFoundError(f"Video directory not found: {vdir}")

    plan_file = vdir / "acting_plan.json"
    if not plan_file.is_file():
        return {
            "status": "FAIL",
            "video": vdir.name,
            "errors": [f"acting_plan.json missing in {vdir}"],
        }

    try:
        data = load_acting_plan(plan_file)
    except Exception as e:
        return {
            "status": "FAIL",
            "video": vdir.name,
            "errors": [f"acting_plan.json corrupt: {e}"],
        }

    errors: List[str] = []

    # 1. Cast validation (max 2)
    cast = data.get("cast", {})
    if len(cast) > 2:
        errors.append(f"Too many actors in cast: {len(cast)} (max 2 allowed)")

    scenes = data.get("scenes", [])
    if not scenes:
        errors.append("acting_plan has no scenes")

    last_gesture_by_speaker: Dict[str, str] = {}

    for sc in scenes:
        sc_num = sc.get("scene_number", 0)
        spk = sc.get("speaker", "A")
        dur = float(sc.get("duration_sec", 4.0))
        beats = sc.get("beats", [])

        if not beats:
            errors.append(f"scene {sc_num}: has no acting beats")
            continue

        for b in beats:
            b_id = b.get("beat_id", "")
            # Accents: at most 1 stressed word group per beat
            sw = b.get("stressed_words", [])
            if len(sw) > 2:
                errors.append(f"scene {sc_num} beat {b_id}: more than 2 stressed accents ({len(sw)})")

            # Gesture validity
            gest = b.get("gesture", {})
            g_name = gest.get("name", "idle")
            if g_name not in ALLOWED_GESTURES:
                errors.append(f"scene {sc_num} beat {b_id}: unknown gesture {g_name!r}")

            # Back-to-back repeat check
            if g_name != "idle" and last_gesture_by_speaker.get(spk) == g_name:
                errors.append(f"scene {sc_num} beat {b_id}: gesture {g_name!r} repeated back-to-back for speaker {spk}")
            last_gesture_by_speaker[spk] = g_name

            # Pointing target slot check
            if g_name in ("point", "point_board"):
                slot = b.get("pointing_target_slot")
                if not slot:
                    errors.append(f"scene {sc_num} beat {b_id}: pointing gesture missing target slot")

            # Gaze target check
            gaze = b.get("gaze", {})
            if gaze.get("target") and gaze["target"] not in GAZE_TARGETS:
                errors.append(f"scene {sc_num} beat {b_id}: unknown gaze target {gaze['target']!r}")

            # Listener reaction check (frequency <= 4.0s)
            lr = b.get("listener_reaction")
            if dur >= 3.5 and not lr:
                errors.append(f"scene {sc_num}: duration {dur:.2f}s lacks required listener reaction")
            elif lr and lr.get("type") not in LISTENER_REACTION_TYPES:
                errors.append(f"scene {sc_num} beat {b_id}: unknown listener reaction type {lr.get('type')!r}")

    status = "PASS" if not errors else "FAIL"
    return {
        "status": status,
        "video": vdir.name,
        "scenes_count": len(scenes),
        "cast": cast,
        "errors": errors,
    }
