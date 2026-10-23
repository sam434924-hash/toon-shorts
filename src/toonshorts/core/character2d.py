"""
Purpose: 2D layered character system with registry, FK skeleton, character packs, and actions.
Inputs: Layout JSON, character sheet images, action parameters, audio loudness.
Outputs: Cut transparent character layers, character registry JSON, rendered frames.
Depends on: json, math, os, pathlib, re, time, typing, PIL, numpy, core.character_pack, core.config, core.fk_solver, core.paths, core.svg_renderer
Used by: core.fk_solver, core.svg_renderer, inventory, plugins.render.animejs.cast
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

from toonshorts.core import paths
from toonshorts.core.config import PROJECT_ROOT
from toonshorts.core.character_pack import (
    CharacterPack,
    load_character_pack,
    create_character_staging,
    validate_pack_name,
)
from toonshorts.core.fk_solver import (
    SkeletonPose2D,
    get_face_for_audio,
    compute_action_pose,
    compute_forward_kinematics,
)
from toonshorts.core.svg_renderer import (
    render_scene_frame,
    create_parts_contact_sheet,
    create_faces_contact_sheet,
)

# Directory paths
ASSETS2D_DIR = paths.ASSETS_2D_DIR
CHARACTERS2D_DIR = paths.CHARACTERS_2D_DIR
LAYOUTS2D_DIR = paths.LAYOUTS_2D_DIR
INCOMING2D_DIR = paths.ASSETS_SOURCES_INCOMING_DIR

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

    # 1. Check for SVG Character Pack (vector/manifest.json or root manifest.json)
    vector_manifest = char_folder / "vector" / "manifest.json"
    if vector_manifest.is_file() or manifest_json.is_file():
        try:
            return load_character_pack(name, base_dir=characters_root)
        except Exception as e:
            if char_json.is_file() and not vector_manifest.is_file():
                try:
                    return Character2D.from_json(char_json)
                except Exception:
                    pass
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


__all__ = [
    "CHARACTER_SLOTS",
    "CHARACTER_NAME_REGEX",
    "validate_character_name",
    "ensure_path_inside_dir",
    "make_exterior_transparent",
    "add_rounded_joint_cap",
    "PartDefinition",
    "Character2D",
    "get_character",
    "slice_character_sheet",
    "SkeletonPose2D",
    "get_face_for_audio",
    "compute_action_pose",
    "compute_forward_kinematics",
    "render_scene_frame",
    "create_parts_contact_sheet",
    "create_faces_contact_sheet",
]
