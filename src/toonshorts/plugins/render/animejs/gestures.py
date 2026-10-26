"""
Purpose: Whitelist sanitization and character capability resolution for animation gestures.
Inputs: Gesture name strings, character pack definitions, and style presets.
Outputs: Validated gesture identifiers with fallback logging.
Depends on: logging, typing
Used by: plugins.render.animejs, plugins.render.animejs.cast, plugins.render.animejs.html_builder, plugins.render.animejs.layout
Config keys: None
Tests: tests/unit/test_animejs.py
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ALLOWED_GESTURES = frozenset({
    "idle",
    "wave",
    "point",
    "explain",
    "open_hand",
    "thumbs_up",
    "shrug",
    "point_board",
    "point_other",
    "nod",
    "head_tilt",
    "lean_speaker",
    "listening_reaction",
    "walk",
    "raise_hand",
})


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


def resolve_character_gesture(
    requested_gesture: Optional[str],
    character_pack: Any,
    scene_number: int,
    style_preset: Optional[Dict[str, Any]] = None,
    scene_gestures_override: Optional[str] = None,
) -> str:
    """
    Resolves the gesture for a character in a scene:
    1. Checks style_preset['gestures'] (default: 'on') and per-scene override.
    2. If gestures are 'off' or no gesture requested, returns 'idle'.
    3. If character cannot perform the requested gesture, returns 'idle' AND logs a clear warning.
    4. Otherwise returns the sanitized requested gesture.
    """
    preset = style_preset or {}
    preset_gestures = str(preset.get("gestures", "on")).lower().strip()
    gestures_enabled = (preset_gestures != "off")

    if scene_gestures_override is not None:
        override = str(scene_gestures_override).lower().strip()
        if override in ("off", "none", "false", "0"):
            gestures_enabled = False
        elif override in ("on", "true", "1"):
            gestures_enabled = True

    if not gestures_enabled:
        return "idle"

    if not requested_gesture:
        return "idle"

    try:
        clean = sanitize_gesture(requested_gesture)
    except ValueError:
        clean = str(requested_gesture).lower().strip()

    allowed = getattr(character_pack, "allowed_gestures", ["idle"])
    char_id = getattr(character_pack, "pack_id", "character")
    if clean not in allowed:
        logger.warning(
            "Scene %d: Character '%s' does not support gesture '%s', falling back to 'idle'",
            scene_number,
            char_id,
            requested_gesture,
        )
        return "idle"

    return clean
