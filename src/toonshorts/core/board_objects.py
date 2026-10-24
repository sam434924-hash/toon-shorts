"""
Purpose: Board object schema validation, slot layout allocation, and security capping.
Inputs: Scene visual items, word timings, scene duration, and style profile tokens.
Outputs: Validated BoardObject models, safe JSON data payloads, and DOM slot assignments.
Depends on: json, logging, math, re, typing, core.config, core.models, core.style_profile
Used by: plugins.render.animejs.html_builder
Config keys: ENABLE_BOARD_OBJECTS
Tests: tests/unit/test_board_objects.py
"""

from dataclasses import dataclass
import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from toonshorts.core import config
from toonshorts.core.models import strip_speaker_label
from toonshorts.core.style_profile import validate_hex_color

logger = logging.getLogger("toonshorts.board_objects")

ALLOWED_TYPES = {
    "text_pop",
    "text_typewriter",
    "highlight_word",
    "svg_draw",
    "diagram_flow",
    "icon_pop",
    "custom",
    "image",
}

ALLOWED_IMAGE_PRESETS = {
    "slide_in_tilt",
    "paper_tear_reveal",
    "detail_highlight",
    "stamp_slam",
    "push_in",
}

ALLOWED_ENTER_STYLES = {"draw_on", "pop", "slide_in"}

BOARD_SLOTS = ["slot_top", "slot_mid", "slot_bottom", "slot_center"]
TEMPLATE_BOARD_SLOTS = {
    "hero", "left", "right", "step_1", "step_2", "step_3",
    "top", "mid", "bottom", "title", "card",
    "slot_hero", "slot_left", "slot_right", "slot_title", "slot_card",
    "slot_step_1", "slot_step_2", "slot_step_3",
}
ALL_BOARD_SLOTS = set(BOARD_SLOTS) | TEMPLATE_BOARD_SLOTS

# Security & Design Hard Caps
MAX_OBJECTS_PER_SCENE = 8
MAX_TEXT_LENGTH = 80
MAX_DIAGRAM_NODES = 6
MIN_FONT_SIZE_PX = 28
DEFAULT_HOLD_MS = 4000


def derive_object_seed(scene_number: int, object_id: str) -> int:
    """Derives deterministic integer seed per object for Rough.js reproducibility."""
    obj_hash = 0
    for ch in str(object_id):
        obj_hash = (obj_hash * 31 + ord(ch)) & 0x7FFFFFFF
    return (int(scene_number) * 10007 + obj_hash) & 0x7FFFFFFF


def compute_auto_font_size(text_len: int) -> int:
    """Computes legible font size for 1080x1920 mobile viewport with minimum 28px."""
    if text_len <= 18:
        return 44
    if text_len <= 35:
        return 36
    if text_len <= 55:
        return 32
    return MIN_FONT_SIZE_PX


def sanitize_board_text(text: str) -> str:
    """
    Strips speaker labels (Boy:, Girl:), clamps length to MAX_TEXT_LENGTH (80 chars),
    and truncates with an ellipsis if length exceeds limit.
    """
    if not isinstance(text, str):
        return ""
    clean = strip_speaker_label(text).strip()
    # Strip any HTML tags that might be in the string
    clean = re.sub(r"<[^>]*>", "", clean).strip()
    if len(clean) > MAX_TEXT_LENGTH:
        clean = clean[: MAX_TEXT_LENGTH - 3].rstrip() + "..."
    return clean


def parse_anchor_time_ms(
    anchor: Union[int, float, str],
    word_timings: Optional[List[Any]] = None,
    total_duration_ms: int = 5000,
) -> int:
    """
    Parses anchor value into a millisecond timestamp inside the scene:
    - If anchor is an integer index < len(word_timings), uses that word's start time.
    - If anchor is a float, treats as seconds.
    - If anchor is a string matching a word in word_timings, uses that word's start time.
    - If anchor is numeric string or int >= 100, treats as ms.
    """
    if word_timings and isinstance(anchor, int) and 0 <= anchor < len(word_timings):
        wt = word_timings[anchor]
        s_t = getattr(wt, "start_time", None) if hasattr(wt, "start_time") else (
            wt.get("start_time", wt.get("start_ms", 0) / 1000.0 if "start_ms" in wt else 0.0)
            if isinstance(wt, dict) else 0.0
        )
        return int(float(s_t) * 1000)

    if word_timings and isinstance(anchor, str) and not anchor.replace(".", "", 1).isdigit():
        clean_target = re.sub(r"[^\w]", "", anchor).lower()
        for wt in word_timings:
            w_str = getattr(wt, "word", None) or (wt.get("word") if isinstance(wt, dict) else "")
            clean_w = re.sub(r"[^\w]", "", str(w_str)).lower()
            if clean_target and (clean_target == clean_w or clean_target in clean_w or clean_w in clean_target):
                s_t = getattr(wt, "start_time", None) if hasattr(wt, "start_time") else (
                    wt.get("start_time", wt.get("start_ms", 0) / 1000.0 if "start_ms" in wt else 0.0)
                    if isinstance(wt, dict) else 0.0
                )
                return int(float(s_t) * 1000)

    try:
        val = float(anchor)
        # If small float (< 60.0), interpret as seconds; else ms
        if val < 60.0 and val < (total_duration_ms / 1000.0) + 1.0:
            return int(val * 1000)
        return int(val)
    except Exception:
        return 500


def validate_board_object_schema(
    raw_obj: Dict[str, Any],
    scene_number: int,
    total_duration_ms: int,
    word_timings: Optional[List[Any]] = None,
    index: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Strictly validates a single board object against the schema and security caps:
    - id: str
    - type: one of the 6 fixed types
    - anchor: resolved to timestamp in ms inside scene bounds
    - enter: draw_on, pop, or slide_in
    - exit_time: resolved to timestamp in ms, default hold applied
    - board_slot: assigned to valid board slot
    - data: validated payload
    Returns sanitized dict, or None if invalid. Unknown types are skipped and logged (never crash).
    """
    if not isinstance(raw_obj, dict):
        logger.warning("Scene %d: Board object is not a dict: %s. Skipping.", scene_number, raw_obj)
        return None

    obj_id = str(raw_obj.get("id") or f"board-obj-{scene_number}-{index+1}").strip()
    obj_type = str(raw_obj.get("type", "")).strip().lower()

    if obj_type not in ALLOWED_TYPES:
        logger.warning(
            "Scene %d: Unknown board object type '%s' (allowed: %s). Skipping safely.",
            scene_number,
            obj_type,
            sorted(ALLOWED_TYPES),
        )
        return None

    # Resolve timing
    raw_anchor = raw_obj.get("anchor")
    if raw_anchor is None:
        raw_anchor = raw_obj.get("start_ms", index * 1000)
    start_ms = parse_anchor_time_ms(raw_anchor, word_timings, total_duration_ms)
    start_ms = max(0, min(start_ms, max(0, total_duration_ms - 300)))

    raw_exit = raw_obj.get("exit_time")
    if raw_exit is None:
        raw_exit = raw_obj.get("exit_ms")
    if raw_exit is not None:
        try:
            exit_val = float(raw_exit)
            exit_ms = int(exit_val * 1000) if exit_val < 60.0 else int(exit_val)
        except Exception:
            exit_ms = total_duration_ms
    else:
        exit_ms = total_duration_ms

    exit_ms = max(start_ms + 400, min(exit_ms, total_duration_ms))

    # Enter animation
    enter_style = str(raw_obj.get("enter", "")).strip().lower()
    if enter_style not in ALLOWED_ENTER_STYLES:
        enter_style = "draw_on" if obj_type in ("svg_draw", "diagram_flow") else "pop"

    # Board slot
    raw_slot = str(raw_obj.get("board_slot", "")).strip().lower()
    slot = raw_slot if raw_slot in ALL_BOARD_SLOTS else (raw_slot if raw_slot in BOARD_SLOTS else BOARD_SLOTS[index % len(BOARD_SLOTS)])

    # Validate data payload
    raw_data = raw_obj.get("data") or {}
    if not isinstance(raw_data, dict):
        raw_data = {"text": str(raw_data)}

    sanitized_data: Dict[str, Any] = {}

    if obj_type in ("text_pop", "text_typewriter", "highlight_word"):
        raw_text = raw_data.get("text") or raw_data.get("title") or raw_obj.get("text", "")
        clean_text = sanitize_board_text(raw_text)
        if not clean_text:
            logger.warning("Scene %d: Text object %s has empty text. Skipping.", scene_number, obj_id)
            return None
        sanitized_data["text"] = clean_text
        sanitized_data["font_size"] = compute_auto_font_size(len(clean_text))
        if obj_type == "highlight_word":
            sanitized_data["target_word"] = sanitize_board_text(raw_data.get("target_word", ""))

    elif obj_type == "diagram_flow":
        nodes = raw_data.get("nodes") or ["Client", "Server"]
        if not isinstance(nodes, list):
            nodes = [str(nodes)]
        # Cap diagram nodes to MAX_DIAGRAM_NODES (6)
        clean_nodes = [sanitize_board_text(str(n)) for n in nodes[:MAX_DIAGRAM_NODES]]
        sanitized_data["nodes"] = clean_nodes
        sanitized_data["arrows"] = [
            sanitize_board_text(str(a))
            for a in (raw_data.get("arrows") or ["Request", "Response"])[:5]
        ]

    elif obj_type == "svg_draw":
        svg_type = str(raw_data.get("svg_type") or raw_data.get("icon") or "box")
        sanitized_data["svg_type"] = svg_type
        sanitized_data["label"] = sanitize_board_text(raw_data.get("label", ""))

    elif obj_type == "icon_pop":
        icon_name = str(raw_data.get("icon") or "heart")
        sanitized_data["icon"] = icon_name
        sanitized_data["count"] = min(5, max(1, int(raw_data.get("count", 3))))

    elif obj_type == "image":
        from toonshorts.core.images import ALLOWED_IMAGE_PRESETS
        preset = str(raw_data.get("preset") or raw_data.get("motion_preset") or "slide_in_tilt").strip().lower()
        if preset not in ALLOWED_IMAGE_PRESETS:
            preset = "slide_in_tilt"
        sanitized_data["preset"] = preset
        sanitized_data["image_url"] = str(raw_data.get("image_url") or raw_data.get("src") or raw_data.get("path") or "")
        sanitized_data["alt"] = sanitize_board_text(raw_data.get("alt", ""))
        sanitized_data["highlight_region"] = raw_data.get("highlight_region") or [50, 50]
        sanitized_data["push_region"] = raw_data.get("push_region") or [50, 50]

    elif obj_type == "custom":
        level = int(raw_data.get("level", 1))
        if level not in (1, 2):
            level = 1
        sanitized_data["level"] = level

        raw_svg = raw_data.get("svg") or raw_obj.get("svg", "")
        if raw_svg:
            from toonshorts.core.sanitizer import sanitize_svg
            sanitized_data["svg"] = sanitize_svg(raw_svg)
        else:
            sanitized_data["svg"] = ""

        if level == 1:
            timeline = raw_data.get("timeline") or []
            if isinstance(timeline, (list, dict)):
                sanitized_data["timeline"] = timeline
            else:
                sanitized_data["timeline"] = []
            preset = str(raw_data.get("motion_preset") or raw_data.get("preset") or enter_style or "draw_on").strip().lower()
            sanitized_data["motion_preset"] = preset
            sanitized_data["label"] = sanitize_board_text(raw_data.get("label", ""))
        elif level == 2:
            js_code = str(raw_data.get("js_code") or raw_data.get("script") or raw_data.get("code") or "")
            from toonshorts.core.ast_scanner import validate_level2_effect
            is_valid, violations = validate_level2_effect(js_code)
            if not is_valid:
                v_msg = "; ".join(violations)
                logger.error("Scene %d: Custom Level 2 JS failed AST scan: %s", scene_number, v_msg)
                raise ValueError(f"Custom Level 2 effect rejected by AST scan: {v_msg}")
            sanitized_data["js_code"] = js_code
            sanitized_data["level2_effect_name"] = str(raw_data.get("effect_name") or f"custom_fx_{obj_id}")

    seed = derive_object_seed(scene_number, obj_id)

    ret_obj = {
        "id": obj_id,
        "type": obj_type,
        "start_ms": start_ms,
        "exit_ms": exit_ms,
        "duration_ms": max(300, min(1000, exit_ms - start_ms)),
        "enter": enter_style,
        "board_slot": slot,
        "seed": seed,
        "data": sanitized_data,
    }
    decl_ov = raw_obj.get("overlap") or raw_obj.get("declared_overlap")
    if decl_ov:
        ret_obj["overlap"] = decl_ov
    return ret_obj


def resolve_board_objects_for_scene(
    raw_objects: List[Any],
    scene_number: int,
    duration_sec: float,
    word_timings: Optional[List[Any]] = None,
    style_profile: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Validates, caps (max 8 objects), resolves slot overlaps, and maps styling from style profile.
    Never crashes on malformed data.
    """
    total_duration_ms = int(round(duration_sec * 1000))
    valid_objects: List[Dict[str, Any]] = []

    # Hard cap: max 8 objects per scene
    items_to_check = (raw_objects or [])[:MAX_OBJECTS_PER_SCENE]

    for idx, item in enumerate(items_to_check):
        val = validate_board_object_schema(
            item,
            scene_number=scene_number,
            total_duration_ms=total_duration_ms,
            word_timings=word_timings,
            index=idx,
        )
        if val is not None:
            valid_objects.append(val)

    if not valid_objects:
        return []

    # Overlap resolution: ensure no two objects in the same slot overlap in time
    slot_occupancy: Dict[str, List[Tuple[int, int]]] = {s: [] for s in ALL_BOARD_SLOTS}

    for obj in valid_objects:
        slot = obj["board_slot"]
        s_ms = obj["start_ms"]
        e_ms = obj["exit_ms"]

        # Declared overlaps skip collision reallocation
        if obj.get("overlap") or obj.get("declared_overlap"):
            slot_occupancy.setdefault(slot, []).append((s_ms, e_ms))
            continue

        slot_occupancy.setdefault(slot, [])

        # Check collision with already allocated intervals in this slot
        collision = any(
            not (e_ms <= occ_s or s_ms >= occ_e) for (occ_s, occ_e) in slot_occupancy[slot]
        )

        if collision:
            # Find an alternative slot without collision
            assigned = False
            for alt_slot in BOARD_SLOTS:
                if alt_slot == slot:
                    continue
                alt_collision = any(
                    not (e_ms <= occ_s or s_ms >= occ_e)
                    for (occ_s, occ_e) in slot_occupancy[alt_slot]
                )
                if not alt_collision:
                    obj["board_slot"] = alt_slot
                    slot_occupancy[alt_slot].append((s_ms, e_ms))
                    assigned = True
                    break
            if not assigned:
                # Clamp exit time to start of collision
                for occ_s, occ_e in slot_occupancy[slot]:
                    if s_ms < occ_s < e_ms:
                        obj["exit_ms"] = occ_s - 50
                        break
                slot_occupancy[slot].append((obj["start_ms"], obj["exit_ms"]))
        else:
            slot_occupancy[slot].append((s_ms, e_ms))

    # Apply style tokens
    prof = style_profile or {}
    palette = prof.get("palette") or ["#1b1516", "#ffffff", "#38bdf8", "#818cf8"]
    outline = prof.get("outline_color", "#1b1516")
    font = prof.get("font_family", "Arial, sans-serif")
    highlight = prof.get("highlight_color", "#38bdf8")

    for obj in valid_objects:
        obj["style"] = {
            "font_family": font,
            "outline_color": outline,
            "highlight_color": highlight,
            "palette": palette[:4],
        }

    return valid_objects


def convert_visuals_to_board_objects(
    visuals: List[Any],
    scene_number: int,
    duration_sec: float,
    word_timings: Optional[List[Any]] = None,
    style_profile: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Wraps existing graphics plugins and visual templates into board objects:
    - kinetic_words -> text_pop or highlight_word
    - typed_code -> text_typewriter
    - draw_svg / octopus_vector -> svg_draw
    - flow / request_response -> diagram_flow
    - hearts_pop / blue_blood_drop -> icon_pop
    - check_cross -> svg_draw
    - counter -> text_pop
    """
    if not visuals:
        return []

    raw_board_objs = []
    total_ms = int(duration_sec * 1000)

    for idx, item in enumerate(visuals):
        v_type = getattr(item, "type", None) or (item.get("type", "") if isinstance(item, dict) else "")
        trigger = getattr(item, "trigger_word", None) or (item.get("trigger_word", "") if isinstance(item, dict) else "")
        params = getattr(item, "params", None) or (item.get("params", {}) if isinstance(item, dict) else {})
        if not isinstance(params, dict):
            params = {}

        anchor = trigger if trigger else idx * 1000
        obj_id = f"vis-board-{scene_number}-{idx+1}"

        if v_type == "kinetic_words":
            text = params.get("text", "")
            h_term = params.get("highlight_term")
            if h_term:
                b_type = "highlight_word"
                payload = {"text": text, "target_word": h_term}
            else:
                b_type = "text_pop"
                payload = {"text": text}
            raw_board_objs.append({
                "id": obj_id,
                "type": b_type,
                "anchor": anchor,
                "enter": params.get("animation_type", "pop"),
                "board_slot": "slot_mid",
                "data": payload,
            })

        elif v_type == "custom":
            raw_board_objs.append({
                "id": obj_id,
                "type": "custom",
                "anchor": anchor,
                "enter": params.get("enter", params.get("animation_type", "draw_on")),
                "board_slot": params.get("board_slot", "slot_center"),
                "data": params,
            })

        elif v_type == "typed_code":
            lines = params.get("lines", [])
            txt = "\n".join(lines) if isinstance(lines, list) else str(lines)
            raw_board_objs.append({
                "id": obj_id,
                "type": "text_typewriter",
                "anchor": anchor,
                "enter": "slide_in",
                "board_slot": "slot_center",
                "data": {"text": txt},
            })

        elif v_type in ("draw_svg", "octopus_vector"):
            raw_board_objs.append({
                "id": obj_id,
                "type": "svg_draw",
                "anchor": anchor,
                "enter": "draw_on",
                "board_slot": "slot_center",
                "data": {
                    "svg_type": "vector",
                    "label": params.get("label", "Diagram"),
                },
            })

        elif v_type in ("flow", "request_response"):
            if v_type == "flow":
                nodes = params.get("nodes", ["Client", "Server"])
                arrows = ["->"] * max(0, len(nodes) - 1)
            else:
                nodes = [params.get("client_label", "Client"), params.get("server_label", "Server")]
                arrows = [params.get("request_label", "Request"), params.get("response_label", "Response")]
            raw_board_objs.append({
                "id": obj_id,
                "type": "diagram_flow",
                "anchor": anchor,
                "enter": "draw_on",
                "board_slot": "slot_mid",
                "data": {"nodes": nodes, "arrows": arrows},
            })

        elif v_type in ("hearts_pop", "blue_blood_drop"):
            icon = "heart" if v_type == "hearts_pop" else "drop"
            cnt = params.get("count", 3 if v_type == "hearts_pop" else 1)
            raw_board_objs.append({
                "id": obj_id,
                "type": "icon_pop",
                "anchor": anchor,
                "enter": "pop",
                "board_slot": "slot_mid",
                "data": {"icon": icon, "count": cnt},
            })

        elif v_type == "check_cross":
            raw_board_objs.append({
                "id": obj_id,
                "type": "svg_draw",
                "anchor": anchor,
                "enter": "draw_on",
                "board_slot": "slot_top",
                "data": {"svg_type": params.get("icon", "check"), "label": params.get("label", "")},
            })

        elif v_type == "counter":
            val = f"{params.get('prefix', '')}{params.get('to_val', 100)}{params.get('suffix', '')}"
            raw_board_objs.append({
                "id": obj_id,
                "type": "text_pop",
                "anchor": anchor,
                "enter": "pop",
                "board_slot": "slot_top",
                "data": {"text": val},
            })

    return resolve_board_objects_for_scene(
        raw_board_objs,
        scene_number=scene_number,
        duration_sec=duration_sec,
        word_timings=word_timings,
        style_profile=style_profile,
    )
