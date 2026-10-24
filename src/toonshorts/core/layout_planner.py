"""
Purpose: Board visual layout templates, slot placement, lifecycle validation, and balance checks.
Inputs: Theme style presets, scene layout blocks, element enter/exit timings, and board zone bounds.
Outputs: Validated layout models, computed slot coordinates, timing overlap checks, and balance diagnostics.
Depends on: json, logging, math, typing, core.config, core.models
Used by: core.layout_checker, core.validator, core.visual_checker, plugins.render.animejs.html_builder
Config keys: VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_layout_planner.py
"""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from toonshorts.core import config
from toonshorts.core.models import Scene

logger = logging.getLogger("toonshorts.layout_planner")

# Canvas & Board Zone Coordinates (1080x1920 canvas)
CANVAS_WIDTH = getattr(config, "VIDEO_WIDTH", 1080)
CANVAS_HEIGHT = getattr(config, "VIDEO_HEIGHT", 1920)

BOARD_ZONE_TOP = 288.0
BOARD_ZONE_BOTTOM = 808.0
BOARD_ZONE_LEFT = 60.0
BOARD_ZONE_RIGHT = 960.0
BOARD_ZONE_WIDTH = 900.0
BOARD_ZONE_HEIGHT = 520.0

# 5 Core Layout Templates
DEFAULT_LAYOUT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "hero": {
        "name": "hero",
        "description": "One big focal visual centered inside the board zone",
        "padding": 16,
        "min_gap": 20,
        "slots": {
            "hero": {"x": 80, "y": 308, "width": 860, "height": 480},
        },
    },
    "split": {
        "name": "split",
        "description": "Two side-by-side visual slots for comparisons or two-element layouts",
        "padding": 16,
        "min_gap": 20,
        "slots": {
            "left": {"x": 80, "y": 308, "width": 415, "height": 480},
            "right": {"x": 525, "y": 308, "width": 415, "height": 480},
        },
    },
    "chain": {
        "name": "chain",
        "description": "Left-to-right sequence with three stages or steps",
        "padding": 14,
        "min_gap": 20,
        "slots": {
            "step_1": {"x": 80, "y": 308, "width": 266, "height": 480},
            "step_2": {"x": 377, "y": 308, "width": 266, "height": 480},
            "step_3": {"x": 674, "y": 308, "width": 266, "height": 480},
        },
    },
    "stack": {
        "name": "stack",
        "description": "Vertical list layout with three stacked slots",
        "padding": 14,
        "min_gap": 16,
        "slots": {
            "top": {"x": 80, "y": 308, "width": 860, "height": 140},
            "mid": {"x": 80, "y": 468, "width": 860, "height": 140},
            "bottom": {"x": 80, "y": 628, "width": 860, "height": 140},
        },
    },
    "title-card": {
        "name": "title-card",
        "description": "Top title banner plus one large content card below",
        "padding": 16,
        "min_gap": 20,
        "slots": {
            "title": {"x": 80, "y": 308, "width": 860, "height": 95},
            "card": {"x": 80, "y": 425, "width": 860, "height": 363},
        },
    },
}

# Slot Aliases for flexible authoring
SLOT_ALIASES: Dict[str, Dict[str, str]] = {
    "hero": {
        "slot_hero": "hero",
        "center": "hero",
        "main": "hero",
        "slot_center": "hero",
    },
    "split": {
        "slot_left": "left",
        "slot_right": "right",
        "slot_1": "left",
        "slot_2": "right",
    },
    "chain": {
        "step1": "step_1",
        "step2": "step_2",
        "step3": "step_3",
        "slot_1": "step_1",
        "slot_2": "step_2",
        "slot_3": "step_3",
        "left": "step_1",
        "center": "step_2",
        "right": "step_3",
    },
    "stack": {
        "slot_top": "top",
        "slot_mid": "mid",
        "slot_bottom": "bottom",
        "slot_center": "mid",
        "slot_1": "top",
        "slot_2": "mid",
        "slot_3": "bottom",
    },
    "title-card": {
        "slot_title": "title",
        "slot_card": "card",
        "top": "title",
        "bottom": "card",
        "header": "title",
        "body": "card",
    },
}

ALLOWED_OVERLAP_ROLES = {"badge", "label", "tag", "corner_badge"}
ALLOWED_OVERLAP_CORNERS = {"top_right", "top_left", "bottom_right", "bottom_left"}


def get_board_zone_bounds() -> Dict[str, float]:
    """Returns canonical board zone boundary on the 1080x1920 canvas."""
    return {
        "top": BOARD_ZONE_TOP,
        "bottom": BOARD_ZONE_BOTTOM,
        "left": BOARD_ZONE_LEFT,
        "right": BOARD_ZONE_RIGHT,
        "width": BOARD_ZONE_WIDTH,
        "height": BOARD_ZONE_HEIGHT,
    }


def resolve_slot_key(template_name: str, slot_key: str) -> str:
    """Resolves slot aliases to canonical slot key for a given template."""
    clean_tmpl = template_name.lower().strip()
    clean_slot = slot_key.lower().strip()
    if clean_tmpl in SLOT_ALIASES and clean_slot in SLOT_ALIASES[clean_tmpl]:
        return SLOT_ALIASES[clean_tmpl][clean_slot]
    return clean_slot


def load_layout_templates(style_preset: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Loads layout templates from theme style preset, merged with defaults."""
    templates = dict(DEFAULT_LAYOUT_TEMPLATES)
    if style_preset and isinstance(style_preset, dict):
        custom_templates = style_preset.get("layout_templates")
        if isinstance(custom_templates, dict):
            for k, v in custom_templates.items():
                if isinstance(v, dict) and "slots" in v:
                    templates[k.lower().strip()] = v
    return templates


def validate_layout_template_definition(
    template_name: str,
    template_data: Dict[str, Any],
) -> List[str]:
    """
    Validates that a layout template definition is well-formed:
    - slots are inside the board zone (y: 288 to 808, x: 60 to 960).
    - padding is >= 0.
    - minimum gap between non-overlapping slots is satisfied.
    """
    errors: List[str] = []
    slots = template_data.get("slots")
    if not isinstance(slots, dict) or not slots:
        errors.append(f"Layout template '{template_name}' has no slots defined.")
        return errors

    min_gap = float(template_data.get("min_gap", 16))
    slot_boxes: List[Tuple[str, Dict[str, float]]] = []

    for s_name, box in slots.items():
        if not isinstance(box, dict):
            errors.append(f"Template '{template_name}' slot '{s_name}' is not a dict.")
            continue
        x = float(box.get("x", 0))
        y = float(box.get("y", 0))
        w = float(box.get("width", 0))
        h = float(box.get("height", 0))

        if w <= 0 or h <= 0:
            errors.append(f"Template '{template_name}' slot '{s_name}' has non-positive size ({w}x{h}).")

        # Board zone boundary check (y: 288 to 808, x: 60 to 960)
        if y < BOARD_ZONE_TOP - 1.0 or (y + h) > BOARD_ZONE_BOTTOM + 1.0:
            errors.append(
                f"Template '{template_name}' slot '{s_name}' extends outside board zone Y bounds "
                f"(y={y}, bottom={y+h}, allowed=[{BOARD_ZONE_TOP}, {BOARD_ZONE_BOTTOM}])."
            )
        if x < BOARD_ZONE_LEFT - 1.0 or (x + w) > BOARD_ZONE_RIGHT + 1.0:
            errors.append(
                f"Template '{template_name}' slot '{s_name}' extends outside board zone X bounds "
                f"(x={x}, right={x+w}, allowed=[{BOARD_ZONE_LEFT}, {BOARD_ZONE_RIGHT}])."
            )

        slot_boxes.append((s_name, {"x": x, "y": y, "w": w, "h": h, "r": x + w, "b": y + h}))

    # Check minimum gap between all distinct slot pairs
    for i in range(len(slot_boxes)):
        for j in range(i + 1, len(slot_boxes)):
            n1, b1 = slot_boxes[i]
            n2, b2 = slot_boxes[j]
            # Calculate distance between rectangles
            dx = max(0.0, max(b1["x"] - b2["r"], b2["x"] - b1["r"]))
            dy = max(0.0, max(b1["y"] - b2["b"], b2["y"] - b1["b"]))
            dist = math.hypot(dx, dy)
            if dist < min_gap - 1.0:
                errors.append(
                    f"Template '{template_name}' minimum gap violated between '{n1}' and '{n2}': "
                    f"gap={dist:.1f}px < min_gap={min_gap}px."
                )

    return errors


def canvas_to_board_relative_box(box: Dict[str, float]) -> Dict[str, float]:
    """Converts 1080x1920 canvas slot box into relative coordinates inside #zone-board."""
    return {
        "left": round(box["x"] - BOARD_ZONE_LEFT, 1),
        "top": round(box["y"] - BOARD_ZONE_TOP, 1),
        "width": round(box["width"], 1),
        "height": round(box["height"], 1),
    }


def parse_layout_elements(layout_block: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalizes elements from a layout block into a uniform list of:
    [{'id': ..., 'slot': ..., 'is_hero': ..., 'enter_time': ..., 'exit_time': ..., 'overlap': ...}]
    """
    elements: List[Dict[str, Any]] = []
    hero_id = layout_block.get("hero") or layout_block.get("hero_element")

    if "elements" in layout_block and isinstance(layout_block["elements"], list):
        for item in layout_block["elements"]:
            if isinstance(item, dict):
                el_id = str(item.get("id", "")).strip()
                s_key = str(item.get("slot", "")).strip()
                is_hero = bool(item.get("is_hero") or (hero_id and el_id == hero_id))
                enter_t = float(item.get("enter_time", item.get("enter", 0.0)))
                exit_t = float(item.get("exit_time", item.get("exit", 5.0)))
                overlap = item.get("overlap") or item.get("declared_overlap")
                elements.append({
                    "id": el_id,
                    "slot": s_key,
                    "is_hero": is_hero,
                    "enter_time": enter_t,
                    "exit_time": exit_t,
                    "overlap": overlap,
                })
        return elements

    # Fallback / slot-mapping syntax: {"slots": {"left": "element_id", ...}}
    slots_map = layout_block.get("slots")
    if isinstance(slots_map, dict):
        for s_key, val in slots_map.items():
            if isinstance(val, dict):
                el_id = str(val.get("element_id") or val.get("id") or s_key).strip()
                is_hero = bool(val.get("is_hero") or (hero_id and el_id == hero_id))
                enter_t = float(val.get("enter_time", 0.0))
                exit_t = float(val.get("exit_time", 5.0))
                overlap = val.get("overlap") or val.get("declared_overlap")
                elements.append({
                    "id": el_id,
                    "slot": s_key,
                    "is_hero": is_hero,
                    "enter_time": enter_t,
                    "exit_time": exit_t,
                    "overlap": overlap,
                })
            elif isinstance(val, str):
                el_id = val.strip()
                elements.append({
                    "id": el_id,
                    "slot": s_key,
                    "is_hero": bool(hero_id and el_id == hero_id),
                    "enter_time": 0.0,
                    "exit_time": 5.0,
                    "overlap": None,
                })

    return elements


def validate_scene_layout(
    layout_data: Union[Dict[str, Any], Any],
    scene_duration: float,
    scene_number: int = 1,
    style_preset: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Validates a scene's layout block against strict pipeline rules:
    1. Template exists in theme layout templates.
    2. Which visual goes into which slot (valid slot names in template).
    3. One hero per beat (at most 1 hero element visible at any beat time).
    4. Max 3 elements on screen at once across the entire timeline.
    5. Enter/exit timings valid and within scene duration.
    6. Slot lifecycle: when a new element enters a slot, previous element must have exited.
    7. Declared overlaps allowed only as {badge or label on a card corner} with defined layer order.
    """
    errors: List[str] = []
    if not layout_data:
        errors.append(f"Scene {scene_number}: Missing required 'layout' block.")
        return errors

    if hasattr(layout_data, "model_dump"):
        layout_dict = layout_data.model_dump()
    elif isinstance(layout_data, dict):
        layout_dict = layout_data
    else:
        errors.append(f"Scene {scene_number}: Invalid layout data type: {type(layout_data)}.")
        return errors

    tmpl_name = str(layout_dict.get("template", "hero")).lower().strip()
    available_templates = load_layout_templates(style_preset)

    if tmpl_name not in available_templates:
        errors.append(
            f"Scene {scene_number}: Unknown layout template '{tmpl_name}'. "
            f"Allowed templates: {sorted(list(available_templates.keys()))}."
        )
        return errors

    active_template = available_templates[tmpl_name]
    template_slots = active_template.get("slots", {})

    elements = parse_layout_elements(layout_dict)
    if not elements:
        errors.append(f"Scene {scene_number}: Layout block defines no element slot assignments.")
        return errors

    # Check slot validity and timing bounds for each element
    for el in elements:
        el_id = el["id"]
        raw_slot = el["slot"]
        canonical_slot = resolve_slot_key(tmpl_name, raw_slot)
        el["slot"] = canonical_slot

        if canonical_slot not in template_slots:
            errors.append(
                f"Scene {scene_number}: Element '{el_id}' assigned to unknown slot '{raw_slot}' "
                f"for template '{tmpl_name}' (available slots: {sorted(list(template_slots.keys()))})."
            )

        enter_t = el["enter_time"]
        exit_t = el["exit_time"]
        if enter_t < -0.05:
            errors.append(f"Scene {scene_number}: Element '{el_id}' enter_time ({enter_t}s) cannot be negative.")
        if exit_t <= enter_t:
            errors.append(f"Scene {scene_number}: Element '{el_id}' exit_time ({exit_t}s) must be > enter_time ({enter_t}s).")
        if exit_t > scene_duration + 0.5:
            errors.append(
                f"Scene {scene_number}: Element '{el_id}' exit_time ({exit_t}s) exceeds scene duration ({scene_duration}s)."
            )

        # Validate declared overlap if present
        overlap = el.get("overlap")
        if overlap:
            if not isinstance(overlap, dict):
                errors.append(f"Scene {scene_number}: Element '{el_id}' overlap definition must be a dictionary.")
            else:
                role = str(overlap.get("role") or overlap.get("type", "")).lower().strip()
                corner = str(overlap.get("corner", "")).lower().strip()
                layer = overlap.get("layer_order", overlap.get("layer"))

                if role not in ALLOWED_OVERLAP_ROLES:
                    errors.append(
                        f"Scene {scene_number}: Element '{el_id}' declared overlap role '{role}' is forbidden. "
                        f"Declared overlaps are allowed only as {ALLOWED_OVERLAP_ROLES}."
                    )
                if corner and corner not in ALLOWED_OVERLAP_CORNERS:
                    errors.append(
                        f"Scene {scene_number}: Element '{el_id}' declared overlap corner '{corner}' is invalid. "
                        f"Allowed corners: {sorted(list(ALLOWED_OVERLAP_CORNERS))}."
                    )
                if layer is None or not isinstance(layer, int) or layer < 1:
                    errors.append(
                        f"Scene {scene_number}: Element '{el_id}' declared overlap must specify an integer 'layer_order' >= 1."
                    )

    # Lifecycle & Slot Collision check: when a new element enters a slot, the previous must exit
    slot_elements: Dict[str, List[Dict[str, Any]]] = {}
    for el in elements:
        slot_elements.setdefault(el["slot"], []).append(el)

    for s_name, el_list in slot_elements.items():
        if len(el_list) > 1:
            # Sort by enter time
            sorted_els = sorted(el_list, key=lambda x: x["enter_time"])
            for idx in range(len(sorted_els) - 1):
                cur = sorted_els[idx]
                nxt = sorted_els[idx + 1]
                # If neither is a declared corner badge on the other, they cannot overlap in time
                is_overlap_badge = bool(
                    (cur.get("overlap") and cur["overlap"].get("role") in ALLOWED_OVERLAP_ROLES) or
                    (nxt.get("overlap") and nxt["overlap"].get("role") in ALLOWED_OVERLAP_ROLES)
                )
                if not is_overlap_badge and cur["exit_time"] > nxt["enter_time"] + 0.05:
                    errors.append(
                        f"Scene {scene_number}: Slot '{s_name}' collision without lifecycle exit: "
                        f"'{cur['id']}' exits at {cur['exit_time']}s but '{nxt['id']}' enters at {nxt['enter_time']}s. "
                        f"Previous element must exit before or when new element enters."
                    )

    # Timeline sampling check: sample every 100 ms plus at each enter and exit time
    sample_times = {0.0, scene_duration}
    for el in elements:
        sample_times.add(round(el["enter_time"], 3))
        sample_times.add(round(el["exit_time"], 3))
    # Sample every 100ms
    t_step = 0.0
    while t_step <= scene_duration:
        sample_times.add(round(t_step, 3))
        t_step += 0.1

    sorted_samples = sorted(list(sample_times))

    for t in sorted_samples:
        # Elements active at time t (enter_time <= t < exit_time)
        active = [el for el in elements if el["enter_time"] <= t + 1e-4 < el["exit_time"]]

        # Rule: max 3 elements on screen at once
        if len(active) > 3:
            active_ids = [el["id"] for el in active]
            errors.append(
                f"Scene {scene_number}: More than 3 elements on screen at once at t={t:.2f}s: "
                f"{active_ids} (count={len(active)})."
            )
            break

        # Rule: one hero per beat (at most 1 hero visible at any beat time)
        heroes = [el for el in active if el.get("is_hero")]
        if len(heroes) > 1:
            hero_ids = [el["id"] for el in heroes]
            errors.append(
                f"Scene {scene_number}: Multiple hero elements visible at once at t={t:.2f}s: "
                f"{hero_ids} (strictly one hero per beat allowed)."
            )
            break

    return errors


def compute_board_visual_balance(
    element_boxes: List[Dict[str, float]],
    canvas_mid_x: float = CANVAS_WIDTH / 2.0,
) -> Tuple[float, float, bool]:
    """
    Computes horizontal visual balance of board elements:
    Returns (left_ratio, right_ratio, is_balanced).
    Warns if more than 70% of the visible area is on one side.
    """
    total_area = 0.0
    left_area = 0.0
    right_area = 0.0

    for b in element_boxes:
        w = float(b.get("width", 0))
        h = float(b.get("height", 0))
        area = w * h
        if area <= 0:
            continue
        total_area += area

        left_x = float(b.get("x", b.get("left", 0)))
        right_x = left_x + w

        if right_x <= canvas_mid_x:
            left_area += area
        elif left_x >= canvas_mid_x:
            right_area += area
        else:
            # Overlaps center: split proportionally
            l_portion = (canvas_mid_x - left_x) / w
            r_portion = (right_x - canvas_mid_x) / w
            left_area += area * l_portion
            right_area += area * r_portion

    if total_area <= 0:
        return 0.5, 0.5, True

    left_ratio = left_area / total_area
    right_ratio = right_area / total_area
    is_balanced = (left_ratio <= 0.70) and (right_ratio <= 0.70)
    return round(left_ratio, 3), round(right_ratio, 3), is_balanced
