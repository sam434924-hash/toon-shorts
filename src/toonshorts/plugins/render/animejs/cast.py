"""
Purpose: Scene cast resolution, character pack binding, slot assignment, and gesture overrides.
Inputs: Scene schemas, character manifests, and style presets.
Outputs: Structured character slot configurations with loaded SVG representations.
Depends on: core.character2d, core.models, logging, plugins.render.animejs.gestures, typing
Used by: plugins.render.animejs, plugins.render.animejs.html_builder, plugins.render.animejs.plugin
Config keys: None
Tests: tests/unit/test_animejs.py
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from toonshorts.core.character2d import get_character
from toonshorts.core.models import Character, Scene
from toonshorts.plugins.render.animejs.gestures import resolve_character_gesture

logger = logging.getLogger(__name__)


def resolve_scene_cast(
    scene: Scene,
    characters: Optional[List[Character]] = None,
    default_character: str = "presenter",
) -> List[str]:
    """
    Resolves the list of character IDs present in a scene.
    Supports explicit scene.cast or scene.characters, falls back to plan characters or default presenter.
    """
    scene_cast = getattr(scene, "cast", None)
    if scene_cast:
        if isinstance(scene_cast, str):
            return [scene_cast]
        return list(scene_cast)

    scene_chars = getattr(scene, "characters", None)
    if scene_chars:
        if isinstance(scene_chars, str):
            return [scene_chars]
        return [c if isinstance(c, str) else getattr(c, "id", None) or getattr(c, "name", str(c)) for c in scene_chars]

    if characters:
        if len(characters) == 1:
            name = characters[0].name.lower()
            return [name if name != "host" else "presenter"]
        names = [c.name.lower() for c in characters]
        if names == ["host", "zack"]:
            return ["presenter"]
        if "presenter" in names and "boy_a" not in names:
            return ["presenter"]
        return names

    return [default_character]


def build_characters_data(
    cast_ids: List[str],
    scene: Scene,
    style_preset: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Loads character packs and resolves slots, gestures, and speaker status for each character."""
    if not cast_ids:
        cast_ids = ["presenter"]

    seen = set()
    unique_cast = []
    for cid in cast_ids:
        c_clean = str(cid).lower().strip()
        if c_clean and c_clean not in seen:
            seen.add(c_clean)
            unique_cast.append(c_clean)
            if len(unique_cast) == 2:
                break

    packs = []
    for cid in unique_cast:
        p = get_character(cid)
        if isinstance(p, dict) and p.get("status") in ("missing", "error"):
            if cid in ("host", "speaker"):
                p = get_character("presenter")
            else:
                logger.warning("Character '%s' not found in registry: %s", cid, p.get("message"))
                p = get_character("presenter")
        packs.append((cid, p))

    assigned_slots: List[Tuple[str, Any, str]] = []
    if len(packs) == 1:
        cid, p = packs[0]
        assigned_slots.append((cid, p, "left"))
    else:
        p0_slot = getattr(packs[0][1], "default_slot", "left")
        p1_slot = getattr(packs[1][1], "default_slot", "right")
        if p0_slot == "right" and p1_slot == "left":
            assigned_slots.append((packs[1][0], packs[1][1], "left"))
            assigned_slots.append((packs[0][0], packs[0][1], "right"))
        else:
            assigned_slots.append((packs[0][0], packs[0][1], "left"))
            assigned_slots.append((packs[1][0], packs[1][1], "right"))

    speaker_val = getattr(scene, "speaker", None)
    speaker_lower = str(speaker_val).lower().strip() if speaker_val else ""

    speaker_idx = 0
    if speaker_lower:
        for idx, (cid, p, slot) in enumerate(assigned_slots):
            c_name = getattr(p, "name", "").lower()
            if speaker_lower in (cid, c_name) or (speaker_lower in ("host", "speaker") and cid == "presenter"):
                speaker_idx = idx
                break

    scene_req_gesture = getattr(scene, "gesture", None)
    scene_gestures_override = getattr(scene, "gestures", None)
    scene_num = getattr(scene, "scene_number", 1)

    result = []
    for idx, (cid, p, slot) in enumerate(assigned_slots):
        is_spk = (idx == speaker_idx)
        req_gest = scene_req_gesture if is_spk else "idle"
        res_gest = resolve_character_gesture(
            requested_gesture=req_gest,
            character_pack=p,
            scene_number=scene_num,
            style_preset=style_preset,
            scene_gestures_override=scene_gestures_override,
        )

        raw_svg = getattr(p, "raw_svg", "")
        result.append({
            "id": cid,
            "pack": p,
            "slot": slot,
            "svg": raw_svg,
            "is_speaker": is_spk,
            "gesture": res_gest,
            "scale": getattr(p, "scale", 1.0),
        })

    return result
