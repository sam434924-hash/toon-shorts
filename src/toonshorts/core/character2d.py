"""
Purpose: 2D layered character system with registry, FK skeleton, character packs, and actions.
Inputs: Layout JSON, character sheet images, action parameters, audio loudness.
Outputs: Cut transparent character layers, character registry JSON, rendered frames.
Depends on: json, math, os, pathlib, re, time, typing, PIL, numpy, core.character_pack, core.config
Used by: None
Config keys: None
Tests: tests/unit/test_character2d.py
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from toonshorts.core.config import PROJECT_ROOT
from toonshorts.core.character_pack import (
    CharacterPack,
    load_character_pack,
    create_character_staging,
    validate_pack_name,
)

# Directory paths
ASSETS2D_DIR = PROJECT_ROOT / "assets2d"
CHARACTERS2D_DIR = ASSETS2D_DIR / "characters"
LAYOUTS2D_DIR = ASSETS2D_DIR / "layouts"
INCOMING2D_DIR = ASSETS2D_DIR / "incoming"

# Strict character name regex: letters, digits, dash, underscore, max 32 chars
CHARACTER_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")

# Slots for variety
CHARACTER_SLOTS = ("hair", "hat", "torso", "legs", "shoes", "hands")


def validate_character_name(name: str) -> str:
    """Validates character name against strict alphanumeric + dash/underscore, max 32 chars."""
    if not isinstance(name, str):
        raise ValueError(f"Character name must be a string, got {type(name).__name__}")
    if not CHARACTER_NAME_REGEX.match(name):
        raise ValueError(
            f"Invalid character name '{name}'. Names must be 1-32 chars containing only letters, numbers, '-', '_'"
        )
    return name


def ensure_path_inside_dir(target_path: Path, parent_dir: Path) -> Path:
    """Ensures target_path resolves strictly within parent_dir to prevent path traversal."""
    resolved_parent = parent_dir.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_parent)
    except ValueError:
        raise ValueError(f"Security error: path '{target_path}' escapes outside '{parent_dir}'")
    return resolved_target


def make_exterior_transparent(img: Image.Image, bg_thresh: int = 240) -> Image.Image:
    """Flood-fills from borders to remove exterior white background while preserving enclosed white areas."""
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    h, w = arr.shape[:2]

    # Mask of pixels that are near white
    is_bg = np.all(arr[:, :, :3] >= bg_thresh, axis=2)
    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    # Seed flood-fill from all 4 borders
    for x in range(w):
        if is_bg[0, x]:
            q.append((0, x))
            visited[0, x] = True
        if is_bg[h - 1, x]:
            q.append((h - 1, x))
            visited[h - 1, x] = True
    for y in range(h):
        if is_bg[y, 0]:
            q.append((y, 0))
            visited[y, 0] = True
        if is_bg[y, w - 1]:
            q.append((y, w - 1))
            visited[y, w - 1] = True

    while q:
        y, x = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    # Exterior connected background is made fully transparent
    arr[visited, 3] = 0
    return Image.fromarray(arr)


def add_rounded_joint_cap(
    img: Image.Image,
    cap_center: Tuple[int, int],
    radius: int,
    fill_color: Tuple[int, int, int, int] = (125, 128, 131, 255),
    outline_color: Tuple[int, int, int, int] = (30, 30, 30, 255),
    outline_width: int = 3,
) -> Image.Image:
    """Adds a circular rounded cap at joint pivot to ensure gapless rotation at any angle."""
    w, h = img.size
    cx, cy = cap_center
    pad = radius + 4
    new_w = w + pad * 2
    new_h = h + pad * 2
    new_img = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))

    # Draw rounded cap
    draw = ImageDraw.Draw(new_img)
    draw.ellipse(
        [cx + pad - radius, cy + pad - radius, cx + pad + radius, cy + pad + radius],
        fill=fill_color,
        outline=outline_color,
        width=outline_width,
    )
    # Paste original image over cap
    new_img.alpha_composite(img, (pad, pad))
    return new_img


class PartDefinition:
    """Definition of a single 2D skeletal part layer."""

    def __init__(
        self,
        name: str,
        image_path: Path,
        pivot: Tuple[float, float],
        parent: Optional[str] = None,
        parent_joint: Optional[str] = None,
        slot: Optional[str] = None,
        z_index: int = 0,
        base_rotation: float = 0.0,
        joints: Optional[Dict[str, Tuple[float, float]]] = None,
    ):
        self.name = name
        self.image_path = Path(image_path)
        self.pivot = (float(pivot[0]), float(pivot[1]))
        self.parent = parent
        self.parent_joint = parent_joint
        self.slot = slot
        self.z_index = z_index
        self.base_rotation = float(base_rotation)
        self.joints = {k: (float(v[0]), float(v[1])) for k, v in (joints or {}).items()}

    def to_dict(self, base_folder: Optional[Path] = None) -> Dict[str, Any]:
        img_str = str(self.image_path.relative_to(base_folder)) if base_folder else str(self.image_path)
        return {
            "name": self.name,
            "image": img_str.replace("\\", "/"),
            "pivot": [self.pivot[0], self.pivot[1]],
            "parent": self.parent,
            "parent_joint": self.parent_joint,
            "slot": self.slot,
            "z_index": self.z_index,
            "base_rotation": self.base_rotation,
            "joints": {k: [v[0], v[1]] for k, v in self.joints.items()},
        }


class Character2D:
    """Layered 2D character model with slots, expressions, and forward kinematics."""

    def __init__(self, name: str, folder: Path):
        self.name = validate_character_name(name)
        self.folder = folder
        self.parts: Dict[str, PartDefinition] = {}
        self.slots: Dict[str, Optional[str]] = {slot: None for slot in CHARACTER_SLOTS}
        self.expressions: Dict[str, Path] = {}
        self.active_expression: str = "neutral"
        self.active_hand_left: str = "open_palm"
        self.active_hand_right: str = "open_palm"
        self._image_cache: Dict[str, Image.Image] = {}

    def get_image(self, path: Path) -> Image.Image:
        p_str = str(path)
        if p_str not in self._image_cache:
            self._image_cache[p_str] = Image.open(path).convert("RGBA")
        return self._image_cache[p_str]

    def equip_slot(self, slot_name: str, item_id: Optional[str]) -> None:
        """Equips an item in a slot, replacing the current item."""
        if slot_name not in CHARACTER_SLOTS:
            raise ValueError(f"Invalid slot '{slot_name}'. Valid slots: {CHARACTER_SLOTS}")
        self.slots[slot_name] = item_id

    def get_slot(self, slot_name: str) -> Optional[str]:
        if slot_name not in CHARACTER_SLOTS:
            raise ValueError(f"Invalid slot '{slot_name}'. Valid slots: {CHARACTER_SLOTS}")
        return self.slots.get(slot_name)

    def set_expression(self, face_name: str) -> None:
        if face_name in self.expressions:
            self.active_expression = face_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "slots": self.slots,
            "active_expression": self.active_expression,
            "active_hand_left": self.active_hand_left,
            "active_hand_right": self.active_hand_right,
            "parts": {name: part.to_dict(self.folder) for name, part in self.parts.items()},
            "expressions": {
                name: str(p.relative_to(self.folder)).replace("\\", "/")
                for name, p in self.expressions.items()
            },
        }

    def save_json(self, json_path: Optional[Path] = None) -> Path:
        target = json_path or (self.folder / "character.json")
        ensure_path_inside_dir(target, self.folder)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return target

    @classmethod
    def from_json(cls, json_path: Path) -> Character2D:
        char_dir = json_path.parent
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        name = validate_character_name(data.get("name", char_dir.name))
        char = cls(name=name, folder=char_dir)
        char.slots = {k: data.get("slots", {}).get(k) for k in CHARACTER_SLOTS}
        char.active_expression = data.get("active_expression", "neutral")
        char.active_hand_left = data.get("active_hand_left", "open_palm")
        char.active_hand_right = data.get("active_hand_right", "open_palm")

        # Load parts
        for part_name, pdata in data.get("parts", {}).items():
            img_rel = Path(pdata["image"])
            img_full = char_dir / img_rel
            ensure_path_inside_dir(img_full, char_dir)

            part = PartDefinition(
                name=part_name,
                image_path=img_full,
                pivot=pdata.get("pivot", [0, 0]),
                parent=pdata.get("parent"),
                parent_joint=pdata.get("parent_joint"),
                slot=pdata.get("slot"),
                z_index=pdata.get("z_index", 0),
                base_rotation=pdata.get("base_rotation", 0.0),
                joints=pdata.get("joints", {}),
            )
            char.parts[part_name] = part

        # Load expressions
        for exp_name, exp_rel in data.get("expressions", {}).items():
            exp_full = char_dir / Path(exp_rel)
            ensure_path_inside_dir(exp_full, char_dir)
            char.expressions[exp_name] = exp_full

        return char


def get_character(
    name: str, base_dir: Optional[Path] = None
) -> Union[Character2D, CharacterPack, Dict[str, Any]]:
    """Returns saved character from registry (either Character2D or CharacterPack) if it exists, otherwise reports 'missing'."""
    try:
        validate_character_name(name)
    except ValueError as e:
        return {"status": "error", "name": name, "message": str(e)}

    characters_root = base_dir or CHARACTERS2D_DIR
    char_folder = characters_root / name
    char_json = char_folder / "character.json"
    manifest_json = char_folder / "manifest.json"

    if not char_folder.is_dir():
        return {
            "status": "missing",
            "name": name,
            "message": f"Character '{name}' not found in registry",
        }

    # 1. Check for SVG Character Pack (manifest.json)
    if manifest_json.is_file():
        try:
            return load_character_pack(name, base_dir=characters_root)
        except Exception as e:
            return {"status": "error", "name": name, "message": f"Failed to load character pack '{name}': {e}"}

    # 2. Check for skeletal Character2D (character.json)
    if char_json.is_file():
        try:
            return Character2D.from_json(char_json)
        except Exception as e:
            return {"status": "error", "name": name, "message": f"Failed to load character '{name}': {e}"}

    return {
        "status": "missing",
        "name": name,
        "message": f"Character '{name}' not found in registry (no manifest.json or character.json)",
    }


def slice_character_sheet(
    sheet_path: Path,
    layout_path: Path,
    character_name: str,
    output_base_dir: Optional[Path] = None,
) -> Character2D:
    """Cuts an incoming character sheet into transparent layers based on layout coordinates."""
    validate_character_name(character_name)
    sheet_path = Path(sheet_path).resolve()
    layout_path = Path(layout_path).resolve()

    if not sheet_path.is_file():
        raise FileNotFoundError(f"Character sheet not found at: {sheet_path}")
    if not layout_path.is_file():
        raise FileNotFoundError(f"Layout definition not found at: {layout_path}")

    with open(layout_path, "r", encoding="utf-8") as f:
        layout = json.load(f)

    char_dir = (output_base_dir or CHARACTERS2D_DIR) / character_name
    layers_dir = char_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)

    sheet_img = Image.open(sheet_path).convert("RGBA")
    char = Character2D(name=character_name, folder=char_dir)
    bg_thresh = layout.get("transparency", {}).get("background_threshold", 240)

    # 1. Cut base parts
    for part_name, pinfo in layout.get("parts", {}).items():
        box = pinfo["box"]  # [xmin, ymin, xmax, ymax]
        crop = sheet_img.crop(box)
        trans = make_exterior_transparent(crop, bg_thresh=bg_thresh)

        if pinfo.get("mirror", False):
            trans = ImageOps.mirror(trans)

        img_file = layers_dir / f"{part_name}.png"
        ensure_path_inside_dir(img_file, char_dir)
        trans.save(img_file)

        part = PartDefinition(
            name=part_name,
            image_path=img_file,
            pivot=pinfo.get("pivot", [0, 0]),
            parent=pinfo.get("parent"),
            parent_joint=pinfo.get("parent_joint"),
            slot=pinfo.get("slot"),
            z_index=pinfo.get("z_index", 0),
            base_rotation=pinfo.get("base_rotation", 0.0),
            joints=pinfo.get("joints", {}),
        )
        char.parts[part_name] = part

        if part.slot and not char.slots.get(part.slot):
            char.slots[part.slot] = part_name

    # 2. Cut hands (4 poses x 2 sides)
    for hand_pose, hinfo in layout.get("hands", {}).items():
        box = hinfo["box"]
        crop = sheet_img.crop(box)
        trans_left = make_exterior_transparent(crop, bg_thresh=bg_thresh)
        trans_right = ImageOps.mirror(trans_left)

        left_name = f"hand_{hand_pose}_left"
        right_name = f"hand_{hand_pose}_right"

        left_file = layers_dir / f"{left_name}.png"
        right_file = layers_dir / f"{right_name}.png"

        ensure_path_inside_dir(left_file, char_dir)
        ensure_path_inside_dir(right_file, char_dir)

        trans_left.save(left_file)
        trans_right.save(right_file)

        char.parts[left_name] = PartDefinition(
            name=left_name,
            image_path=left_file,
            pivot=hinfo.get("pivot_left", [0, 0]),
            parent="sleeve_lower_left",
            parent_joint="cuff",
            slot="hands",
            z_index=7,
            base_rotation=180.0,
        )
        char.parts[right_name] = PartDefinition(
            name=right_name,
            image_path=right_file,
            pivot=hinfo.get("pivot_right", [0, 0]),
            parent="sleeve_lower_right",
            parent_joint="cuff",
            slot="hands",
            z_index=2,
            base_rotation=180.0,
        )

    # 3. Cut faces (8 expressions)
    for exp_name, einfo in layout.get("expressions", {}).items():
        box = einfo["box"]
        crop = sheet_img.crop(box)
        trans = make_exterior_transparent(crop, bg_thresh=bg_thresh)
        exp_file = layers_dir / f"face_{exp_name}.png"
        ensure_path_inside_dir(exp_file, char_dir)
        trans.save(exp_file)
        char.expressions[exp_name] = exp_file

    char.save_json()
    return char


class SkeletonPose2D:
    """Forward kinematics skeletal pose specification."""

    def __init__(
        self,
        action: str = "idle",
        t: float = 0.0,
        intensity: float = 1.0,
        speed: float = 1.0,
        root_x: float = 540.0,
        root_y: float = 1260.0,
        root_scale_x: float = 1.0,
        root_scale_y: float = 1.0,
        angles: Optional[Dict[str, float]] = None,
        face_name: str = "neutral",
        hand_left_pose: str = "open_palm",
        hand_right_pose: str = "open_palm",
        jump_height: float = 0.0,
        blink: bool = False,
    ):
        self.action = action
        self.t = t
        self.intensity = max(0.5, min(1.5, float(intensity)))
        self.speed = float(speed)
        self.root_x = float(root_x)
        self.root_y = float(root_y)
        self.root_scale_x = float(root_scale_x)
        self.root_scale_y = float(root_scale_y)
        self.angles: Dict[str, float] = angles or {}
        self.face_name = face_name
        self.hand_left_pose = hand_left_pose
        self.hand_right_pose = hand_right_pose
        self.jump_height = float(jump_height)
        self.blink = bool(blink)


def get_face_for_audio(loudness: float, base_emotion: str = "neutral") -> str:
    """Maps audio loudness to speech mouth shapes or fallback emotion."""
    l_val = max(0.0, float(loudness))
    if l_val >= 0.55:
        return "talking_open"
    elif l_val >= 0.15:
        return "talking_round"
    return base_emotion


def compute_action_pose(
    action: str,
    t: float,
    intensity: float = 1.0,
    speed: float = 1.0,
    root_x: float = 540.0,
    root_y: float = 1260.0,
    loudness: float = 0.0,
    blink: bool = False,
    base_emotion: str = "neutral",
) -> SkeletonPose2D:
    """Computes skeletal angles and squash/stretch for idle, walk, wave, or jump with follow-through."""
    clamped_intensity = max(0.5, min(1.5, float(intensity)))
    phase = (t * speed) % 1.0
    two_pi = 2.0 * math.pi

    angles: Dict[str, float] = {
        "head": 0.0,
        "torso": 0.0,
        "sleeve_upper_left": 0.0,
        "sleeve_lower_left": 0.0,
        "hand_left": 0.0,
        "sleeve_upper_right": 0.0,
        "sleeve_lower_right": 0.0,
        "hand_right": 0.0,
        "leg_upper_left": 0.0,
        "leg_lower_left": 0.0,
        "shoe_left": 0.0,
        "leg_upper_right": 0.0,
        "leg_lower_right": 0.0,
        "shoe_right": 0.0,
    }

    effective_base = base_emotion
    face = get_face_for_audio(loudness, base_emotion=effective_base)
    hand_left = "open_palm"
    hand_right = "open_palm"
    scale_x = 1.0
    scale_y = 1.0
    cur_root_y = root_y
    jump_height = 0.0

    if action == "idle":
        # Subtle breathing bob and slight follow-through on sleeves
        breath = math.sin(two_pi * phase)
        cur_root_y = root_y + (8.0 * breath * clamped_intensity)
        scale_y = 1.0 + (0.025 * breath * clamped_intensity)
        scale_x = 1.0 - (0.025 * breath * clamped_intensity)

        angles["head"] = 1.5 * math.sin(two_pi * phase) * clamped_intensity
        # Sleeve follow-through trails breathing motion slightly
        angles["sleeve_upper_left"] = 3.0 * math.sin(two_pi * phase - 0.3) * clamped_intensity
        angles["sleeve_lower_left"] = 2.0 * math.sin(two_pi * phase - 0.5) * clamped_intensity
        angles["sleeve_upper_right"] = -3.0 * math.sin(two_pi * phase - 0.3) * clamped_intensity
        angles["sleeve_lower_right"] = -2.0 * math.sin(two_pi * phase - 0.5) * clamped_intensity
        face = get_face_for_audio(loudness, base_emotion=base_emotion)

    elif action == "walk":
        # Forward/backward leg and sleeve swing with pelvis bounce
        sin_p = math.sin(two_pi * phase)
        cos_p = math.cos(two_pi * phase)

        # Pelvis bounce (2 bounces per stride cycle)
        bounce = abs(math.sin(two_pi * phase)) * 14.0 * clamped_intensity
        cur_root_y = root_y - bounce

        # Leg swing
        angles["leg_upper_left"] = 28.0 * sin_p * clamped_intensity
        angles["leg_lower_left"] = max(0.0, 36.0 * sin_p) * clamped_intensity
        angles["leg_upper_right"] = -28.0 * sin_p * clamped_intensity
        angles["leg_lower_right"] = max(0.0, -36.0 * sin_p) * clamped_intensity

        # Sleeve counter-swing with lower sleeve follow-through
        angles["sleeve_upper_left"] = -22.0 * sin_p * clamped_intensity
        angles["sleeve_lower_left"] = -15.0 * sin_p * clamped_intensity
        angles["sleeve_upper_right"] = 22.0 * sin_p * clamped_intensity
        angles["sleeve_lower_right"] = 15.0 * sin_p * clamped_intensity

        # Slight forward torso lean with subtle follow-through bob
        angles["torso"] = 3.5 * clamped_intensity + 1.0 * math.sin(two_pi * phase)
        angles["head"] = -2.0 * sin_p * clamped_intensity

        face = get_face_for_audio(loudness, base_emotion=base_emotion if base_emotion != "neutral" else "happy")
        hand_left = "open_palm"
        hand_right = "open_palm"

    elif action == "wave":
        # Left sleeve relaxed at side
        angles["sleeve_upper_left"] = 6.0 * clamped_intensity
        angles["sleeve_lower_left"] = 4.0 * clamped_intensity

        # Right arm raised up in wave position:
        # Upper sleeve points up and right (~ -110 deg), lower sleeve bends inward (~ -30 deg)
        angles["sleeve_upper_right"] = -110.0 * clamped_intensity
        wave_osc = math.sin(two_pi * phase * 2.5)
        # Forearm / lower sleeve oscillates cleanly with follow-through
        angles["sleeve_lower_right"] = (-25.0 + (30.0 * wave_osc)) * clamped_intensity
        angles["hand_right"] = (18.0 * wave_osc) * clamped_intensity

        angles["head"] = 3.0 * math.sin(two_pi * phase) * clamped_intensity
        face = get_face_for_audio(loudness, base_emotion=base_emotion if base_emotion != "neutral" else "happy")
        hand_left = "open_palm"
        hand_right = "waving"

    elif action == "jump":
        # 5-phase ballistic jump: crouch squash -> takeoff stretch -> apex leg tuck -> descent -> landing squash
        if phase < 0.20:
            # Phase 1: Anticipation crouch / squash
            p1 = phase / 0.20
            crouch = math.sin(math.pi * p1)
            cur_root_y = root_y + (48.0 * crouch * clamped_intensity)
            scale_y = 1.0 - (0.18 * crouch * clamped_intensity)
            scale_x = 1.0 + (0.16 * crouch * clamped_intensity)

            angles["leg_upper_left"] = 32.0 * crouch * clamped_intensity
            angles["leg_lower_left"] = -48.0 * crouch * clamped_intensity
            angles["leg_upper_right"] = 32.0 * crouch * clamped_intensity
            angles["leg_lower_right"] = -48.0 * crouch * clamped_intensity
            angles["sleeve_upper_left"] = 35.0 * crouch * clamped_intensity
            angles["sleeve_upper_right"] = 35.0 * crouch * clamped_intensity

        elif phase < 0.55:
            # Phase 2: Launch & Rocket Stretch
            p2 = (phase - 0.20) / 0.35
            height_factor = math.sin(math.pi * p2)
            jump_height = 200.0 * height_factor * clamped_intensity
            cur_root_y = root_y - jump_height
            scale_y = 1.0 + (0.22 * math.sin(math.pi * p2) * clamped_intensity)
            scale_x = 1.0 - (0.14 * math.sin(math.pi * p2) * clamped_intensity)

            # Arms swing upward into overhead 'V'
            arm_raise = math.sin(math.pi * p2 / 2)
            angles["sleeve_upper_left"] = -135.0 * arm_raise * clamped_intensity
            angles["sleeve_lower_left"] = -15.0 * arm_raise * clamped_intensity
            angles["sleeve_upper_right"] = -135.0 * arm_raise * clamped_intensity
            angles["sleeve_lower_right"] = -15.0 * arm_raise * clamped_intensity
            angles["leg_upper_left"] = -5.0 * clamped_intensity
            angles["leg_lower_left"] = 0.0
            angles["leg_upper_right"] = -5.0 * clamped_intensity
            angles["leg_lower_right"] = 0.0
            face = get_face_for_audio(loudness, base_emotion="shocked")

        elif phase < 0.75:
            # Phase 3: Apex Hang & Inverted-V Leg Tuck (matching target_poses.png)
            p3 = (phase - 0.55) / 0.20
            jump_height = 200.0 * (1.0 - (p3 * 0.5)) * clamped_intensity
            cur_root_y = root_y - jump_height
            scale_y = 1.0 + (0.06 * (1.0 - p3) * clamped_intensity)
            scale_x = 1.0 - (0.04 * (1.0 - p3) * clamped_intensity)

            # Both sleeves raised high in V shape
            angles["sleeve_upper_left"] = -140.0 * clamped_intensity
            angles["sleeve_lower_left"] = -10.0 * clamped_intensity
            angles["sleeve_upper_right"] = -140.0 * clamped_intensity
            angles["sleeve_lower_right"] = -10.0 * clamped_intensity

            # Inverted V leg tuck: hips swing outward (+28 / -28), knees bend sharply (-55 / -55)
            tuck = math.sin(math.pi * p3)
            angles["leg_upper_left"] = -28.0 * tuck * clamped_intensity
            angles["leg_lower_left"] = 55.0 * tuck * clamped_intensity
            angles["leg_upper_right"] = 28.0 * tuck * clamped_intensity
            angles["leg_lower_right"] = -55.0 * tuck * clamped_intensity
            face = get_face_for_audio(loudness, base_emotion="talking_open")

        else:
            # Phase 4: Landing Impact Squash & Spring Recovery
            p4 = (phase - 0.75) / 0.25
            impact = math.sin(math.pi * p4)
            cur_root_y = root_y + (36.0 * impact * clamped_intensity)
            scale_y = 1.0 - (0.18 * impact * clamped_intensity)
            scale_x = 1.0 + (0.16 * impact * clamped_intensity)

            angles["leg_upper_left"] = 26.0 * impact * clamped_intensity
            angles["leg_lower_left"] = -38.0 * impact * clamped_intensity
            angles["leg_upper_right"] = 26.0 * impact * clamped_intensity
            angles["leg_lower_right"] = -38.0 * impact * clamped_intensity
            # Sleeves swing down with follow-through
            angles["sleeve_upper_left"] = -30.0 * (1.0 - p4) * clamped_intensity
            angles["sleeve_upper_right"] = -30.0 * (1.0 - p4) * clamped_intensity

    return SkeletonPose2D(
        action=action,
        t=t,
        intensity=clamped_intensity,
        speed=speed,
        root_x=root_x,
        root_y=cur_root_y,
        root_scale_x=scale_x,
        root_scale_y=scale_y,
        angles=angles,
        face_name=face,
        hand_left_pose=hand_left,
        hand_right_pose=hand_right,
        jump_height=jump_height,
        blink=blink,
    )


def compute_forward_kinematics(
    character: Character2D,
    pose: SkeletonPose2D,
) -> Dict[str, Dict[str, Any]]:
    """Calculates exact world positions, rotations, and scales for all character layers."""
    transforms: Dict[str, Dict[str, Any]] = {}
    computed_joints: Dict[str, Tuple[float, float]] = {}

    torso_part = character.parts.get("torso")
    if not torso_part:
        return transforms

    torso_rot = pose.angles.get("torso", 0.0)
    torso_scale = (pose.root_scale_x, pose.root_scale_y)
    torso_world_pos = (pose.root_x, pose.root_y)

    transforms["torso"] = {
        "world_pos": torso_world_pos,
        "pivot": torso_part.pivot,
        "world_rot": torso_rot,
        "scale": torso_scale,
        "z_index": torso_part.z_index,
        "image_path": torso_part.image_path,
    }

    # Compute torso child joints in world space
    rad = math.radians(torso_rot)
    cos_t = math.cos(rad)
    sin_t = math.sin(rad)
    for j_name, j_local in torso_part.joints.items():
        dx = (j_local[0] - torso_part.pivot[0]) * torso_scale[0]
        dy = (j_local[1] - torso_part.pivot[1]) * torso_scale[1]
        rx = dx * cos_t - dy * sin_t
        ry = dx * sin_t + dy * cos_t
        computed_joints[j_name] = (torso_world_pos[0] + rx, torso_world_pos[1] + ry)

    def resolve_chain(part_name: str, parent_joint_name: str, local_rot_name: str):
        part = character.parts.get(part_name)
        if not part or parent_joint_name not in computed_joints:
            return

        parent_pos = computed_joints[parent_joint_name]
        parent_rot = transforms[part.parent]["world_rot"] if part.parent in transforms else 0.0

        local_angle = pose.angles.get(local_rot_name, 0.0) + part.base_rotation
        world_angle = parent_rot + local_angle

        transforms[part_name] = {
            "world_pos": parent_pos,
            "pivot": part.pivot,
            "world_rot": world_angle,
            "scale": (1.0, 1.0),
            "z_index": part.z_index,
            "image_path": part.image_path,
        }

        c_rad = math.radians(world_angle)
        c_cos = math.cos(c_rad)
        c_sin = math.sin(c_rad)
        for cj_name, cj_local in part.joints.items():
            dx = cj_local[0] - part.pivot[0]
            dy = cj_local[1] - part.pivot[1]
            rx = dx * c_cos - dy * c_sin
            ry = dx * c_sin + dy * c_cos
            computed_joints[f"{part_name}_{cj_name}"] = (parent_pos[0] + rx, parent_pos[1] + ry)

    # Head
    head_part = character.parts.get("head")
    if head_part and "neck" in computed_joints:
        neck_pos = computed_joints["neck"]
        head_local_rot = pose.angles.get("head", 0.0)
        head_world_rot = torso_rot + head_local_rot

        transforms["head"] = {
            "world_pos": neck_pos,
            "pivot": head_part.pivot,
            "world_rot": head_world_rot,
            "scale": (1.0, 1.0),
            "z_index": head_part.z_index,
            "image_path": head_part.image_path,
        }

        # Face expression position
        face_j = head_part.joints.get("face", (96, 105))
        h_rad = math.radians(head_world_rot)
        h_cos = math.cos(h_rad)
        h_sin = math.sin(h_rad)
        fdx = face_j[0] - head_part.pivot[0]
        fdy = face_j[1] - head_part.pivot[1]
        face_world_pos = (neck_pos[0] + (fdx * h_cos - fdy * h_sin), neck_pos[1] + (fdx * h_sin + fdy * h_cos))

        face_img = character.expressions.get(pose.face_name) or character.expressions.get("neutral")
        if face_img:
            transforms["face"] = {
                "world_pos": face_world_pos,
                "pivot": (29, 21),
                "world_rot": head_world_rot,
                "scale": (1.0, 1.0),
                "z_index": head_part.z_index + 1,
                "image_path": face_img,
                "blink": pose.blink,
            }

    # Left Arm Chain (Upper sleeve -> Lower sleeve -> Hand)
    resolve_chain("sleeve_upper_left", "shoulder_left", "sleeve_upper_left")
    resolve_chain("sleeve_lower_left", "sleeve_upper_left_elbow", "sleeve_lower_left")
    left_hand_key = f"hand_{pose.hand_left_pose}_left"
    resolve_chain(left_hand_key, "sleeve_lower_left_cuff", "hand_left")

    # Right Arm Chain (Upper sleeve -> Lower sleeve -> Hand)
    resolve_chain("sleeve_upper_right", "shoulder_right", "sleeve_upper_right")
    resolve_chain("sleeve_lower_right", "sleeve_upper_right_elbow", "sleeve_lower_right")
    right_hand_key = f"hand_{pose.hand_right_pose}_right"
    resolve_chain(right_hand_key, "sleeve_lower_right_cuff", "hand_right")

    # Left Leg Chain (Upper leg -> Lower leg -> Shoe)
    resolve_chain("leg_upper_left", "hip_left", "leg_upper_left")
    resolve_chain("leg_lower_left", "leg_upper_left_knee", "leg_lower_left")
    resolve_chain("shoe_left", "leg_lower_left_ankle", "shoe_left")

    # Right Leg Chain (Upper leg -> Lower leg -> Shoe)
    resolve_chain("leg_upper_right", "hip_right", "leg_upper_right")
    resolve_chain("leg_lower_right", "leg_upper_right_knee", "leg_lower_right")
    resolve_chain("shoe_right", "leg_lower_right_ankle", "shoe_right")

    return transforms


def render_scene_frame(
    character: Character2D,
    pose: SkeletonPose2D,
    width: int = 1080,
    height: int = 1920,
    character_scale: float = 1.58,
) -> Image.Image:
    """Renders a complete vertical frame with pastel background, props, ground shadow, and 55-65% framing."""
    top_color = (252, 234, 222)     # #FCEADE pastel peach
    mid_color = (235, 230, 240)     # #EBE6F0 pastel lavender
    ground_color = (234, 226, 214)  # #EAE2D6 pastel floor

    canvas = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    canvas_arr = np.zeros((height, width, 4), dtype=np.uint8)
    canvas_arr[:, :, 3] = 255

    # Horizon line placed so character feet rest cleanly
    horizon_y = int(height * 0.82)  # y=1574 for 1920 height
    for y in range(horizon_y):
        t = y / max(1, horizon_y)
        if t < 0.5:
            st = t / 0.5
            r = int(top_color[0] + (mid_color[0] - top_color[0]) * st)
            g = int(top_color[1] + (mid_color[1] - top_color[1]) * st)
            b = int(top_color[2] + (mid_color[2] - top_color[2]) * st)
        else:
            st = (t - 0.5) / 0.5
            r = int(mid_color[0] + (ground_color[0] - mid_color[0]) * st)
            g = int(mid_color[1] + (ground_color[1] - mid_color[1]) * st)
            b = int(mid_color[2] + (ground_color[2] - mid_color[2]) * st)
        canvas_arr[y, :, 0] = r
        canvas_arr[y, :, 1] = g
        canvas_arr[y, :, 2] = b

    for y in range(horizon_y, height):
        canvas_arr[y, :, 0] = ground_color[0]
        canvas_arr[y, :, 1] = ground_color[1]
        canvas_arr[y, :, 2] = ground_color[2]

    canvas = Image.fromarray(canvas_arr)
    draw = ImageDraw.Draw(canvas)

    # Subtle horizon ground line
    draw.line([(0, horizon_y), (width, horizon_y)], fill=(215, 206, 195, 255), width=max(1, int(width / 540)))

    # Simple background props: Cute pastel potted plant
    plant_x = int(width * 0.16)
    plant_y = horizon_y
    prop_scale = width / 1080.0
    pw35 = int(35 * prop_scale)
    pw25 = int(25 * prop_scale)
    ph60 = int(60 * prop_scale)
    pw40 = int(40 * prop_scale)

    pot_coords = [(plant_x - pw35, plant_y), (plant_x + pw35, plant_y), (plant_x + pw25, plant_y + ph60), (plant_x - pw25, plant_y + ph60)]
    draw.polygon(pot_coords, fill=(225, 168, 140, 255), outline=(170, 115, 95, 255), width=max(1, int(3 * prop_scale)))
    draw.rounded_rectangle([plant_x - pw40, plant_y - int(10 * prop_scale), plant_x + pw40, plant_y + int(2 * prop_scale)], radius=int(4 * prop_scale), fill=(235, 178, 150, 255), outline=(170, 115, 95, 255), width=max(1, int(3 * prop_scale)))
    leaf_color = (130, 185, 145, 255)
    leaf_outline = (85, 135, 100, 255)
    draw.ellipse([plant_x - int(55 * prop_scale), plant_y - int(65 * prop_scale), plant_x - int(10 * prop_scale), plant_y - int(15 * prop_scale)], fill=leaf_color, outline=leaf_outline, width=max(1, int(3 * prop_scale)))
    draw.ellipse([plant_x + int(10 * prop_scale), plant_y - int(70 * prop_scale), plant_x + int(55 * prop_scale), plant_y - int(20 * prop_scale)], fill=leaf_color, outline=leaf_outline, width=max(1, int(3 * prop_scale)))
    draw.ellipse([plant_x - int(25 * prop_scale), plant_y - int(95 * prop_scale), plant_x + int(25 * prop_scale), plant_y - int(35 * prop_scale)], fill=(145, 198, 160, 255), outline=leaf_outline, width=max(1, int(3 * prop_scale)))

    # Ground shadow beneath character (scales down and fades as jump altitude increases)
    ground_y = horizon_y
    shadow_scale = max(0.35, 1.0 - (pose.jump_height / 350.0)) * prop_scale * character_scale
    shadow_alpha = int(max(25, 110 * (1.0 - (pose.jump_height / 300.0))))
    sw = max(20, int(150 * shadow_scale))
    sh = max(10, int(32 * shadow_scale))

    shadow_img = Image.new("RGBA", (sw + 40, sh + 40), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_img)
    sdraw.ellipse([20, 20, 20 + sw, 20 + sh], fill=(55, 48, 52, shadow_alpha))
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=max(2, int(8 * prop_scale))))
    canvas.alpha_composite(shadow_img, (int(pose.root_x - (sw / 2) - 20), int(ground_y - (sh / 2) - 20)))

    # Render character layers via Forward Kinematics
    transforms = compute_forward_kinematics(character, pose)
    sorted_items = sorted(transforms.items(), key=lambda item: item[1]["z_index"])

    for part_key, tdata in sorted_items:
        img_path = tdata["image_path"]
        if not img_path.is_file():
            continue

        layer_img = character.get_image(img_path)
        pivot = tdata["pivot"]
        world_pos = tdata["world_pos"]
        world_rot = tdata["world_rot"]
        scale = tdata.get("scale", (1.0, 1.0))

        # Overall framing zoom scale applied
        total_scale_x = scale[0] * character_scale
        total_scale_y = scale[1] * character_scale

        # Calculate transformed position relative to canvas center
        cx = width / 2.0
        cy = horizon_y - (1574 - 1260) * character_scale
        scaled_world_x = cx + (world_pos[0] - pose.root_x) * character_scale
        scaled_world_y = cy + (world_pos[1] - pose.root_y) * character_scale - (pose.jump_height * character_scale * 0.7)

        # Scale image layer
        lw, lh = layer_img.size
        new_w = max(1, int(round(lw * abs(total_scale_x))))
        new_h = max(1, int(round(lh * abs(total_scale_y))))
        layer_img = layer_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        scaled_pivot = (pivot[0] * abs(total_scale_x), pivot[1] * abs(total_scale_y))

        # Check for blink overlay on face layer
        if part_key == "face" and tdata.get("blink", False):
            # Render closed eyes (two curved arcs) over the face
            bdraw = ImageDraw.Draw(layer_img)
            # Cover open eyes with white fill and draw curved closed lines
            eye_y = int(new_h * 0.35)
            left_eye_x = int(new_w * 0.30)
            right_eye_x = int(new_w * 0.70)
            ew = int(new_w * 0.18)
            bdraw.rectangle([left_eye_x - ew, eye_y - ew, left_eye_x + ew, eye_y + ew], fill=(255, 255, 255, 255))
            bdraw.rectangle([right_eye_x - ew, eye_y - ew, right_eye_x + ew, eye_y + ew], fill=(255, 255, 255, 255))
            bdraw.arc([left_eye_x - ew, eye_y - 4, left_eye_x + ew, eye_y + 8], start=180, end=360, fill=(30, 30, 30, 255), width=max(2, int(3 * character_scale)))
            bdraw.arc([right_eye_x - ew, eye_y - 4, right_eye_x + ew, eye_y + 8], start=180, end=360, fill=(30, 30, 30, 255), width=max(2, int(3 * character_scale)))

        # Pad layer into square centered on pivot
        px, py = scaled_pivot
        max_dist = max(
            math.hypot(px, py),
            math.hypot(new_w - px, py),
            math.hypot(px, new_h - py),
            math.hypot(new_w - px, new_h - py),
        )
        pad_r = int(math.ceil(max_dist)) + 4
        pad_size = 2 * pad_r

        padded = Image.new("RGBA", (pad_size, pad_size), (0, 0, 0, 0))
        paste_corner_x = int(round(pad_r - px))
        paste_corner_y = int(round(pad_r - py))
        padded.paste(layer_img, (paste_corner_x, paste_corner_y), layer_img)

        # Rotate around pivot
        rotated = padded.rotate(-world_rot, resample=Image.Resampling.BILINEAR)

        paste_x = int(round(scaled_world_x - pad_r))
        paste_y = int(round(scaled_world_y - pad_r))

        canvas.alpha_composite(rotated, (paste_x, paste_y))

    return canvas


def create_parts_contact_sheet(character: Character2D, output_path: Path) -> Path:
    """Generates a comprehensive contact sheet of all cut parts in the character registry."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    part_names = list(character.parts.keys())
    cols = 5
    rows = math.ceil(len(part_names) / cols)
    cell_w, cell_h = 210, 210
    sheet_w = cols * cell_w + 40
    sheet_h = rows * cell_h + 80

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (250, 248, 245, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((25, 20), f"Character Parts Manifest: {character.name} ({len(part_names)} parts)", fill=(40, 40, 45, 255))

    for idx, name in enumerate(part_names):
        c = idx % cols
        r = idx // cols
        x = 20 + c * cell_w
        y = 60 + r * cell_h

        draw.rounded_rectangle([x + 5, y + 5, x + cell_w - 5, y + cell_h - 5], radius=8, fill=(255, 255, 255, 255), outline=(225, 220, 215, 255), width=2)

        part = character.parts[name]
        if part.image_path.is_file():
            img = Image.open(part.image_path).convert("RGBA")
            iw, ih = img.size
            max_fit = 140
            scale = min(max_fit / max(1, iw), max_fit / max(1, ih), 1.0)
            tw = max(1, int(iw * scale))
            th = max(1, int(ih * scale))
            thumb = img.resize((tw, th), Image.Resampling.BILINEAR)
            tx = x + (cell_w - tw) // 2
            ty = y + 15 + (max_fit - th) // 2
            sheet.alpha_composite(thumb, (tx, ty))

        draw.text((x + 10, y + cell_h - 26), name[:22], fill=(60, 60, 65, 255))

    sheet.save(output_path)
    return output_path


def create_faces_contact_sheet(character: Character2D, output_path: Path) -> Path:
    """Generates a high-resolution contact sheet displaying all 8 expression layers."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    expressions = [
        "neutral", "happy", "angry", "sad",
        "shocked", "smirk", "talking_open", "talking_round"
    ]

    cell_w, cell_h = 240, 240
    cols, rows = 4, 2
    sheet_w = cols * cell_w + 40
    sheet_h = rows * cell_h + 80

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (250, 248, 245, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((25, 20), f"Character Faces: {character.name}", fill=(40, 40, 45, 255))

    for idx, exp_name in enumerate(expressions):
        c = idx % cols
        r = idx // cols
        x = 20 + c * cell_w
        y = 60 + r * cell_h

        draw.rounded_rectangle([x + 10, y + 10, x + cell_w - 10, y + cell_h - 10], radius=10, fill=(255, 255, 255, 255), outline=(220, 215, 210, 255), width=2)

        head_cx = x + (cell_w // 2)
        head_cy = y + (cell_h // 2) - 15
        head_r = 60
        draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r], fill=(255, 255, 255, 255), outline=(30, 30, 30, 255), width=4)

        exp_path = character.expressions.get(exp_name)
        if exp_path and exp_path.is_file():
            face_img = Image.open(exp_path).convert("RGBA")
            fw, fh = face_img.size
            fx = head_cx - (fw // 2)
            fy = head_cy - (fh // 2)
            sheet.alpha_composite(face_img, (fx, fy))

        label_text = exp_name.replace("_", " ").title()
        draw.text((x + 25, y + cell_h - 35), label_text, fill=(50, 50, 55, 255))

    sheet.save(output_path)
    return output_path
