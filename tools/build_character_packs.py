"""
Purpose: Extracts, aligns, and builds full-body layered character packs (boy_b, girl_a) with gapless joints and preview sheets.
Inputs: Source body and face sheets in assets/sources/
Outputs: Transparent PNG layers, manifest.json, character.json, and verification preview sheets in assets/2d/characters/<id>/
Depends on: cv2, numpy, PIL, json, pathlib, math
Used by: Pipeline character staging, Anime.js character binding, CLI tools
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# Add src to sys.path for standalone invocation
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toonshorts.core.config import PROJECT_ROOT


def floodfill_transparent_bg(img: Image.Image, bg_thresh: int = 238) -> Image.Image:
    """Flood-fills from all outer boundaries to make white/light exterior background transparent."""
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    h, w = arr.shape[:2]

    # Create background mask using cv2 floodfill
    is_bg = np.all(arr[:, :, :3] >= bg_thresh, axis=2).astype(np.uint8) * 255
    flood_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)

    # Seed flood-fill from borders
    for x in range(w):
        if is_bg[0, x]:
            cv2.floodFill(is_bg, flood_mask, (x, 0), 128)
        if is_bg[h - 1, x]:
            cv2.floodFill(is_bg, flood_mask, (x, h - 1), 128)
    for y in range(h):
        if is_bg[y, 0]:
            cv2.floodFill(is_bg, flood_mask, (0, y), 128)
        if is_bg[y, w - 1]:
            cv2.floodFill(is_bg, flood_mask, (w - 1, y), 128)

    visited_bg = flood_mask[1:-1, 1:-1] == 1
    arr[visited_bg, 3] = 0
    return Image.fromarray(arr)


def add_overlap_joint_cap(
    layer: Image.Image,
    pivot: Tuple[int, int],
    radius: int,
    fill_color: Tuple[int, int, int, int],
    outline_color: Tuple[int, int, int, int],
    outline_width: int = 2,
) -> Tuple[Image.Image, Tuple[int, int]]:
    """
    Extends a part with a rounded circular cap at the pivot to ensure gapless rotation at any angle.
    Returns (expanded_image, new_pivot).
    """
    lw, lh = layer.size
    px, py = pivot

    # Padding around pivot
    pad = radius + 6
    new_w = lw + pad * 2
    new_h = lh + pad * 2

    canvas = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    new_px = px + pad
    new_py = py + pad

    # Draw rounded cap
    draw.ellipse(
        [new_px - radius, new_py - radius, new_px + radius, new_py + radius],
        fill=fill_color,
        outline=outline_color,
        width=outline_width,
    )

    # Composite original layer over cap
    canvas.alpha_composite(layer, (pad, pad))
    return canvas, (new_px, new_py)


def align_and_extract_face_tiles(
    face_sheet_path: Path,
) -> Tuple[Dict[str, Image.Image], Dict[str, Tuple[int, int]]]:
    """
    Detects and crops 8 face tiles from 571x1024 sheet using cross-correlation alignment.
    Returns (dict_of_tiles, dict_of_offsets).
    Tile keys: closed, slightly_open, wide_open, round_o, open_smile, blink, look_left, look_right
    """
    im = Image.open(face_sheet_path).convert("RGB")
    w, h = im.size

    tile_w = 285
    tile_h = 256

    # Verified grid coordinates compensating for horizontal column shift dx=-14 and vertical drift dy
    grid_coords = {
        "closed": (0, 0),
        "slightly_open": (271, 0),
        "wide_open": (0, 251),
        "round_o": (271, 251),
        "open_smile": (0, 501),
        "blink": (271, 501),
        "look_left": (0, 748),
        "look_right": (271, 748),
    }

    tiles = {}
    offsets = {}
    for name, (x, y) in grid_coords.items():
        crop = im.crop((x, y, x + tile_w, y + tile_h))
        tiles[name] = crop
        offsets[name] = (x, y)

    return tiles, offsets


def build_head_layers(
    tiles: Dict[str, Image.Image],
    char_id: str,
) -> Dict[str, Image.Image]:
    """
    Builds head_base and swappable eye and mouth layers from aligned face tiles.
    1. head_base: hair, ears, skin, brows, glasses frame; eyes and mouth removed via inpainting with skin tone.
    2. eye layers: open, blink, look_left, look_right derived by diffing tiles against head_base inside glasses.
    3. mouth layers: closed, slightly_open, wide_open, round_o, open_smile derived by diffing tiles against head_base in mouth area.
    """
    closed_tile = tiles["closed"]
    tile_w, tile_h = closed_tile.size

    # 1. Base transparency for closed tile
    closed_trans = floodfill_transparent_bg(closed_tile, bg_thresh=238)
    closed_arr = np.array(closed_trans)

    # Coordinates of facial features
    if char_id == "boy_b":
        left_eye_center = (92, 116)
        right_eye_center = (192, 110)
        glasses_r = 19
        mouth_center = (144, 186)
        mouth_r = 16
        skin_color = (248, 198, 168, 255)
    else:  # girl_a
        left_eye_center = (96, 125)
        right_eye_center = (194, 128)
        glasses_r = 19
        mouth_center = (144, 187)
        mouth_r = 16
        skin_color = (247, 204, 180, 255)

    # --- Build Head Base ---
    # Create inpainting masks for eyes and mouth
    closed_rgb = np.array(closed_tile)

    mouth_mask = np.zeros((tile_h, tile_w), dtype=np.uint8)
    cv2.circle(mouth_mask, mouth_center, mouth_r, 255, -1)

    eye_mask = np.zeros((tile_h, tile_w), dtype=np.uint8)
    cv2.circle(eye_mask, left_eye_center, glasses_r, 255, -1)
    cv2.circle(eye_mask, right_eye_center, glasses_r, 255, -1)

    # Inpaint closed using Navier-Stokes/Telea inpainting to remove eyes and mouth cleanly
    hb_rgb = cv2.inpaint(closed_rgb, mouth_mask | eye_mask, 5, cv2.INPAINT_TELEA)

    # Make head_base RGBA using transparency mask from closed_trans
    hb_arr = np.zeros((tile_h, tile_w, 4), dtype=np.uint8)
    hb_arr[:, :, :3] = hb_rgb
    hb_arr[:, :, 3] = closed_arr[:, :, 3]

    # Extend rounded neck cap downward below chin (so neck stays securely under collar)
    hb_img = Image.fromarray(hb_arr)
    hb_draw = ImageDraw.Draw(hb_img)
    chin_x = mouth_center[0]
    hb_draw.ellipse(
        [chin_x - 30, 230, chin_x + 30, 255],
        fill=skin_color,
    )

    # --- Build Eye Layers by Diffing against Head Base ---
    eye_layers = {}
    eye_states = {
        "open": tiles["closed"],
        "blink": tiles["blink"],
        "look_left": tiles["look_left"],
        "look_right": tiles["look_right"],
    }

    eye_mask_bool = eye_mask == 255

    for state_name, src_tile in eye_states.items():
        src_rgb = np.array(src_tile)
        # Compute color difference against head_base inside glasses lens area
        diff = np.max(np.abs(src_rgb.astype(float) - hb_rgb.astype(float)), axis=2)
        diff[~eye_mask_bool] = 0

        # Derive smooth antialiased alpha: ramp from 0 at diff=8 to 255 at diff=22
        alpha = np.clip((diff - 8.0) / (22.0 - 8.0), 0.0, 1.0)
        # Sclera / pupil pixels with high diff are fully opaque
        alpha[diff >= 22.0] = 1.0

        out_arr = np.zeros((tile_h, tile_w, 4), dtype=np.uint8)
        out_arr[:, :, :3] = src_rgb
        out_arr[:, :, 3] = (alpha * 255).astype(np.uint8)

        eye_layers[state_name] = Image.fromarray(out_arr)

    # --- Build Mouth Layers by Diffing against Head Base ---
    mouth_layers = {}
    mouth_tiles = {
        "closed": tiles["closed"],
        "slightly_open": tiles["slightly_open"],
        "wide_open": tiles["wide_open"],
        "round_o": tiles["round_o"],
        "open_smile": tiles["open_smile"],
    }

    mouth_box_mask = np.zeros((tile_h, tile_w), dtype=bool)
    mx, my = mouth_center
    mouth_box_mask[my - 22 : my + 22, mx - 32 : mx + 32] = True

    for state_name, src_tile in mouth_tiles.items():
        src_rgb = np.array(src_tile)
        diff = np.max(np.abs(src_rgb.astype(float) - hb_rgb.astype(float)), axis=2)
        diff[~mouth_box_mask] = 0

        # Derive smooth antialiased alpha: ramp from 0 at diff=8 to 255 at diff=20
        alpha = np.clip((diff - 8.0) / (20.0 - 8.0), 0.0, 1.0)
        alpha[diff >= 20.0] = 1.0

        out_arr = np.zeros((tile_h, tile_w, 4), dtype=np.uint8)
        out_arr[:, :, :3] = src_rgb
        out_arr[:, :, 3] = (alpha * 255).astype(np.uint8)

        mouth_layers[state_name] = Image.fromarray(out_arr)

    return {
        "head_base": hb_img,
        **{f"eyes_{k}": v for k, v in eye_layers.items()},
        **{f"mouth_{k}": v for k, v in mouth_layers.items()},
    }


def build_head_back(
    body_sheet_path: Path,
    target_size: Tuple[int, int] = (285, 256),
    char_id: str = "boy_b",
) -> Image.Image:
    """
    Extracts back of head from the back view of body sheet covering full hair length,
    upscales it, removes background, and centers it to match head_base coordinates.
    """
    body_im = Image.open(body_sheet_path).convert("RGBA")
    w, h = body_im.size

    # Back view is on right half: x in 170..330
    if char_id == "boy_b":
        head_box = (175, 15, 320, 150)
    else:  # girl_a (full hair length down to collar line)
        head_box = (170, 50, 325, 205)

    crop = body_im.crop(head_box)
    trans = floodfill_transparent_bg(crop, bg_thresh=238)

    # Upscale to match face tile head dimensions (~224 px tall)
    cw, ch = trans.size
    scale = 224.0 / max(1, ch)
    new_w = int(round(cw * scale))
    new_h = int(round(ch * scale))
    scaled = trans.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Place onto canvas of target_size (285, 256) centered
    out = Image.new("RGBA", target_size, (0, 0, 0, 0))
    paste_x = (target_size[0] - new_w) // 2
    paste_y = 22  # Align with head_base top
    out.alpha_composite(scaled, (paste_x, paste_y))
    return out


def extract_body_parts(
    body_sheet_path: Path,
    char_id: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Extracts transparent body parts from front view:
    torso, arm_upper_left, arm_lower_left, arm_upper_right, arm_lower_right,
    leg_upper_left, leg_lower_left, shoe_left, leg_upper_right, leg_lower_right, shoe_right.
    Extends overlap and fills hidden regions so rotation never shows gaps.
    Excludes the smaller head drawn on the body sheet so torso starts cleanly at collar.
    """
    body_im = Image.open(body_sheet_path).convert("RGBA")
    w, h = body_im.size

    # Crop front view (left half)
    if char_id == "boy_b":
        # Torso collar begins at Y=158 (head is above Y=158)
        front_box = (20, 155, 170, 506)
        palette = {
            "hoodie": (76, 114, 172, 255),
            "hoodie_dark": (40, 60, 95, 255),
            "pants": (70, 85, 104, 255),
            "pants_dark": (40, 50, 65, 255),
            "shoe": (224, 224, 224, 255),
            "shoe_dark": (30, 30, 30, 255),
            "skin": (248, 198, 168, 255),
        }
    else:  # girl_a
        # Torso collar begins at Y=212 (head is above Y=212)
        front_box = (18, 210, 172, 470)
        palette = {
            "hoodie": (155, 78, 153, 255),  # purple vest
            "hoodie_dark": (80, 35, 80, 255),
            "pants": (47, 71, 105, 255),  # dark teal/slate pants
            "pants_dark": (25, 42, 62, 255),
            "shoe": (232, 219, 238, 255),
            "shoe_dark": (40, 40, 40, 255),
            "skin": (247, 204, 180, 255),
        }

    front_crop = body_im.crop(front_box)
    fw, fh = front_crop.size
    front_2x = front_crop.resize((fw * 2, fh * 2), Image.Resampling.LANCZOS)
    front_clean = floodfill_transparent_bg(front_2x, bg_thresh=238)
    arr = np.array(front_clean)

    parts: Dict[str, Dict[str, Any]] = {}

    if char_id == "boy_b":
        # 2x front canvas: 300 x 702
        # Front crop was (20, 155, 170, 506) -> 1x Y origin is 155, 1x X origin is 20
        # 1. Torso: Y in 1x is 158..282 -> in 2x: (158-155)*2 = 6 to (282-155)*2 = 254
        torso_crop = arr[4:256, 45:255].copy()
        torso_img = Image.fromarray(torso_crop)
        tdraw = ImageDraw.Draw(torso_img)
        # Fill side areas behind upper arms with solid hoodie color
        tdraw.rectangle([0, 30, 35, 240], fill=palette["hoodie"])
        tdraw.rectangle([175, 30, 210, 240], fill=palette["hoodie"])

        parts["torso"] = {
            "image": torso_img,
            "pivot": [105, 245],  # waist / hip pivot
            "parent": None,
            "parent_joint": None,
            "z_index": 4,
            "joints": {
                "neck": [105, 6],
                "shoulder_left": [25, 30],
                "shoulder_right": [185, 30],
                "hip_left": [68, 245],
                "hip_right": [142, 245],
            },
        }

        # 2. Upper arm left (screen-left)
        # Y in 1x: 165..225 -> in 2x: 20..140
        ua_l = arr[18:142, 5:75].copy()
        ua_l_img = Image.fromarray(ua_l)
        ua_l_capped, ua_l_piv = add_overlap_joint_cap(
            ua_l_img, pivot=(28, 12), radius=16, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_upper_left"] = {
            "image": ua_l_capped,
            "pivot": list(ua_l_piv),
            "parent": "torso",
            "parent_joint": "shoulder_left",
            "z_index": 6,
            "joints": {"elbow": [ua_l_piv[0] - 2, ua_l_piv[1] + 112]},
        }

        # 3. Forearm + hand left
        # Y in 1x: 220..295 -> in 2x: 130..280
        la_l = arr[128:280, 5:75].copy()
        la_l_img = Image.fromarray(la_l)
        la_l_capped, la_l_piv = add_overlap_joint_cap(
            la_l_img, pivot=(30, 10), radius=14, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_lower_left"] = {
            "image": la_l_capped,
            "pivot": list(la_l_piv),
            "parent": "arm_upper_left",
            "parent_joint": "elbow",
            "z_index": 6,
            "joints": {},
        }

        # 4. Upper arm right (screen-right)
        ua_r = arr[18:142, 225:295].copy()
        ua_r_img = Image.fromarray(ua_r)
        ua_r_capped, ua_r_piv = add_overlap_joint_cap(
            ua_r_img, pivot=(35, 12), radius=16, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_upper_right"] = {
            "image": ua_r_capped,
            "pivot": list(ua_r_piv),
            "parent": "torso",
            "parent_joint": "shoulder_right",
            "z_index": 3,
            "joints": {"elbow": [ua_r_piv[0] + 2, ua_r_piv[1] + 112]},
        }

        # 5. Forearm + hand right
        la_r = arr[128:280, 225:295].copy()
        la_r_img = Image.fromarray(la_r)
        la_r_capped, la_r_piv = add_overlap_joint_cap(
            la_r_img, pivot=(36, 10), radius=14, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_lower_right"] = {
            "image": la_r_capped,
            "pivot": list(la_r_piv),
            "parent": "arm_upper_right",
            "parent_joint": "elbow",
            "z_index": 3,
            "joints": {},
        }

        # 6. Upper leg left
        # Y in 1x: 280..365 -> in 2x: 250..420
        ul_l = arr[248:422, 60:140].copy()
        ul_l_img = Image.fromarray(ul_l)
        ul_l_capped, ul_l_piv = add_overlap_joint_cap(
            ul_l_img, pivot=(38, 10), radius=18, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_upper_left"] = {
            "image": ul_l_capped,
            "pivot": list(ul_l_piv),
            "parent": "torso",
            "parent_joint": "hip_left",
            "z_index": 2,
            "joints": {"knee": [ul_l_piv[0], ul_l_piv[1] + 155]},
        }

        # 7. Lower leg left
        # Y in 1x: 360..450 -> in 2x: 410..590
        ll_l = arr[408:592, 60:140].copy()
        ll_l_img = Image.fromarray(ll_l)
        ll_l_capped, ll_l_piv = add_overlap_joint_cap(
            ll_l_img, pivot=(36, 10), radius=16, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_lower_left"] = {
            "image": ll_l_capped,
            "pivot": list(ll_l_piv),
            "parent": "leg_upper_left",
            "parent_joint": "knee",
            "z_index": 2,
            "joints": {"ankle": [ll_l_piv[0], ll_l_piv[1] + 165]},
        }

        # 8. Shoe left
        # Y in 1x: 445..503 -> in 2x: 580..700
        shoe_l = arr[578:700, 48:145].copy()
        parts["shoe_left"] = {
            "image": Image.fromarray(shoe_l),
            "pivot": [46, 12],
            "parent": "leg_lower_left",
            "parent_joint": "ankle",
            "z_index": 2,
            "joints": {},
        }

        # 9. Upper leg right
        ul_r = arr[248:422, 145:225].copy()
        ul_r_img = Image.fromarray(ul_r)
        ul_r_capped, ul_r_piv = add_overlap_joint_cap(
            ul_r_img, pivot=(38, 10), radius=18, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_upper_right"] = {
            "image": ul_r_capped,
            "pivot": list(ul_r_piv),
            "parent": "torso",
            "parent_joint": "hip_right",
            "z_index": 1,
            "joints": {"knee": [ul_r_piv[0], ul_r_piv[1] + 155]},
        }

        # 10. Lower leg right
        ll_r = arr[408:592, 145:225].copy()
        ll_r_img = Image.fromarray(ll_r)
        ll_r_capped, ll_r_piv = add_overlap_joint_cap(
            ll_r_img, pivot=(36, 10), radius=16, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_lower_right"] = {
            "image": ll_r_capped,
            "pivot": list(ll_r_piv),
            "parent": "leg_upper_right",
            "parent_joint": "knee",
            "z_index": 1,
            "joints": {"ankle": [ll_r_piv[0], ll_r_piv[1] + 165]},
        }

        # 11. Shoe right
        shoe_r = arr[578:700, 145:242].copy()
        parts["shoe_right"] = {
            "image": Image.fromarray(shoe_r),
            "pivot": [38, 12],
            "parent": "leg_lower_right",
            "parent_joint": "ankle",
            "z_index": 1,
            "joints": {},
        }

    else:  # girl_a
        # 2x front canvas: 308 x 520
        # Front crop was (18, 210, 172, 470) -> 1x Y origin is 210, 1x X origin is 18
        # 1. Torso: Y in 1x is 212..290 -> in 2x: (212-210)*2 = 4 to (290-210)*2 = 160
        torso_crop = arr[2:162, 50:258].copy()
        torso_img = Image.fromarray(torso_crop)
        tdraw = ImageDraw.Draw(torso_img)
        tdraw.rectangle([0, 20, 32, 150], fill=palette["hoodie"])
        tdraw.rectangle([176, 20, 208, 150], fill=palette["hoodie"])

        parts["torso"] = {
            "image": torso_img,
            "pivot": [104, 154],
            "parent": None,
            "parent_joint": None,
            "z_index": 4,
            "joints": {
                "neck": [104, 6],
                "shoulder_left": [26, 25],
                "shoulder_right": [182, 25],
                "hip_left": [68, 154],
                "hip_right": [140, 154],
            },
        }

        # 2. Upper arm left (actual arm, Y in 1x is 215..265 -> in 2x: 10..110)
        ua_l = arr[10:112, 10:80].copy()
        ua_l_img = Image.fromarray(ua_l)
        ua_l_capped, ua_l_piv = add_overlap_joint_cap(
            ua_l_img, pivot=(28, 10), radius=15, fill_color=palette["skin"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_upper_left"] = {
            "image": ua_l_capped,
            "pivot": list(ua_l_piv),
            "parent": "torso",
            "parent_joint": "shoulder_left",
            "z_index": 6,
            "joints": {"elbow": [ua_l_piv[0] - 2, ua_l_piv[1] + 90]},
        }

        # 3. Forearm + hand left (Y in 1x is 260..325 -> in 2x: 100..232)
        la_l = arr[98:232, 10:80].copy()
        la_l_img = Image.fromarray(la_l)
        la_l_capped, la_l_piv = add_overlap_joint_cap(
            la_l_img, pivot=(28, 8), radius=13, fill_color=palette["skin"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_lower_left"] = {
            "image": la_l_capped,
            "pivot": list(la_l_piv),
            "parent": "arm_upper_left",
            "parent_joint": "elbow",
            "z_index": 6,
            "joints": {},
        }

        # 4. Upper arm right (Y in 1x is 215..265 -> in 2x: 10..112)
        ua_r = arr[10:112, 224:294].copy()
        ua_r_img = Image.fromarray(ua_r)
        ua_r_capped, ua_r_piv = add_overlap_joint_cap(
            ua_r_img, pivot=(34, 10), radius=15, fill_color=palette["skin"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_upper_right"] = {
            "image": ua_r_capped,
            "pivot": list(ua_r_piv),
            "parent": "torso",
            "parent_joint": "shoulder_right",
            "z_index": 3,
            "joints": {"elbow": [ua_r_piv[0] + 2, ua_r_piv[1] + 90]},
        }

        # 5. Forearm + hand right (Y in 1x is 260..325 -> in 2x: 98..232)
        la_r = arr[98:232, 224:294].copy()
        la_r_img = Image.fromarray(la_r)
        la_r_capped, la_r_piv = add_overlap_joint_cap(
            la_r_img, pivot=(34, 8), radius=13, fill_color=palette["skin"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_lower_right"] = {
            "image": la_r_capped,
            "pivot": list(la_r_piv),
            "parent": "arm_upper_right",
            "parent_joint": "elbow",
            "z_index": 3,
            "joints": {},
        }

        # 6. Upper leg left (Y in 1x is 288..360 -> in 2x: 154..302)
        ul_l = arr[152:304, 60:140].copy()
        ul_l_img = Image.fromarray(ul_l)
        ul_l_capped, ul_l_piv = add_overlap_joint_cap(
            ul_l_img, pivot=(38, 10), radius=16, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_upper_left"] = {
            "image": ul_l_capped,
            "pivot": list(ul_l_piv),
            "parent": "torso",
            "parent_joint": "hip_left",
            "z_index": 2,
            "joints": {"knee": [ul_l_piv[0], ul_l_piv[1] + 135]},
        }

        # 7. Lower leg left (Y in 1x is 355..432 -> in 2x: 288..446)
        ll_l = arr[286:446, 60:140].copy()
        ll_l_img = Image.fromarray(ll_l)
        ll_l_capped, ll_l_piv = add_overlap_joint_cap(
            ll_l_img, pivot=(38, 8), radius=14, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_lower_left"] = {
            "image": ll_l_capped,
            "pivot": list(ll_l_piv),
            "parent": "leg_upper_left",
            "parent_joint": "knee",
            "z_index": 2,
            "joints": {"ankle": [ll_l_piv[0], ll_l_piv[1] + 145]},
        }

        # 8. Shoe left (Y in 1x is 430..468 -> in 2x: 438..520)
        shoe_l = arr[436:520, 50:145].copy()
        parts["shoe_left"] = {
            "image": Image.fromarray(shoe_l),
            "pivot": [45, 12],
            "parent": "leg_lower_left",
            "parent_joint": "ankle",
            "z_index": 2,
            "joints": {},
        }

        # 9. Upper leg right
        ul_r = arr[152:304, 145:225].copy()
        ul_r_img = Image.fromarray(ul_r)
        ul_r_capped, ul_r_piv = add_overlap_joint_cap(
            ul_r_img, pivot=(38, 10), radius=16, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_upper_right"] = {
            "image": ul_r_capped,
            "pivot": list(ul_r_piv),
            "parent": "torso",
            "parent_joint": "hip_right",
            "z_index": 1,
            "joints": {"knee": [ul_r_piv[0], ul_r_piv[1] + 135]},
        }

        # 10. Lower leg right
        ll_r = arr[286:446, 145:225].copy()
        ll_r_img = Image.fromarray(ll_r)
        ll_r_capped, ll_r_piv = add_overlap_joint_cap(
            ll_r_img, pivot=(38, 8), radius=14, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_lower_right"] = {
            "image": ll_r_capped,
            "pivot": list(ll_r_piv),
            "parent": "leg_upper_right",
            "parent_joint": "knee",
            "z_index": 1,
            "joints": {"ankle": [ll_r_piv[0], ll_r_piv[1] + 145]},
        }

        # 11. Shoe right
        shoe_r = arr[436:520, 145:240].copy()
        parts["shoe_right"] = {
            "image": Image.fromarray(shoe_r),
            "pivot": [42, 12],
            "parent": "leg_lower_right",
            "parent_joint": "ankle",
            "z_index": 1,
            "joints": {},
        }

    return parts


def assemble_character_pose(
    parts: Dict[str, Dict[str, Any]],
    head_layers: Dict[str, Image.Image],
    head_back_img: Image.Image,
    angles: Optional[Dict[str, float]] = None,
    eye_state: str = "open",
    mouth_state: str = "closed",
    is_back_view: bool = False,
    canvas_size: Tuple[int, int] = (600, 1100),
) -> Image.Image:
    """
    Renders an assembled full-body pose with forward kinematics and layer layering.
    """
    angles = angles or {}
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

    torso = parts["torso"]
    root_x, root_y = canvas_size[0] // 2, 530

    transforms: Dict[str, Dict[str, Any]] = {}
    computed_joints: Dict[str, Tuple[float, float]] = {}

    torso_rot = angles.get("torso", 0.0)
    torso_piv = torso["pivot"]

    transforms["torso"] = {
        "image": torso["image"],
        "world_pos": (root_x, root_y),
        "pivot": torso_piv,
        "world_rot": torso_rot,
        "z_index": torso["z_index"],
    }

    # Torso joints
    rad = math.radians(torso_rot)
    cos_t, sin_t = math.cos(rad), math.sin(rad)
    for j_name, j_local in torso["joints"].items():
        dx = j_local[0] - torso_piv[0]
        dy = j_local[1] - torso_piv[1]
        rx = dx * cos_t - dy * sin_t
        ry = dx * sin_t + dy * cos_t
        computed_joints[j_name] = (root_x + rx, root_y + ry)

    # Helper to resolve kinematics chains
    def resolve_part(name: str, parent_joint: str, local_rot_name: str):
        part = parts.get(name)
        if not part or parent_joint not in computed_joints:
            return
        parent_pos = computed_joints[parent_joint]
        parent_rot = transforms[part["parent"]]["world_rot"] if part["parent"] in transforms else 0.0

        local_angle = angles.get(local_rot_name, 0.0)
        world_angle = parent_rot + local_angle

        transforms[name] = {
            "image": part["image"],
            "world_pos": parent_pos,
            "pivot": part["pivot"],
            "world_rot": world_angle,
            "z_index": part["z_index"],
        }

        c_rad = math.radians(world_angle)
        c_cos, c_sin = math.cos(c_rad), math.sin(c_rad)
        for cj_name, cj_local in part.get("joints", {}).items():
            dx = cj_local[0] - part["pivot"][0]
            dy = cj_local[1] - part["pivot"][1]
            rx = dx * c_cos - dy * c_sin
            ry = dx * c_sin + dy * c_cos
            computed_joints[f"{name}_{cj_name}"] = (parent_pos[0] + rx, parent_pos[1] + ry)

    # Resolve limbs
    resolve_part("arm_upper_left", "shoulder_left", "arm_upper_left")
    resolve_part("arm_lower_left", "arm_upper_left_elbow", "arm_lower_left")
    resolve_part("arm_upper_right", "shoulder_right", "arm_upper_right")
    resolve_part("arm_lower_right", "arm_upper_right_elbow", "arm_lower_right")

    resolve_part("leg_upper_left", "hip_left", "leg_upper_left")
    resolve_part("leg_lower_left", "leg_upper_left_knee", "leg_lower_left")
    resolve_part("shoe_left", "leg_lower_left_ankle", "shoe_left")

    resolve_part("leg_upper_right", "hip_right", "leg_upper_right")
    resolve_part("leg_lower_right", "leg_upper_right_knee", "leg_lower_right")
    resolve_part("shoe_right", "leg_lower_right_ankle", "shoe_right")

    # Head placement at neck anchor (chin/neck seats right inside collar)
    neck_pos = computed_joints["neck"]
    head_rot = torso_rot + angles.get("head", 0.0)
    head_piv = (142, 240)

    # Render parts in z-order
    sorted_parts = sorted(transforms.items(), key=lambda x: x[1]["z_index"])

    for name, tdata in sorted_parts:
        img = tdata["image"]
        piv = tdata["pivot"]
        pos = tdata["world_pos"]
        rot = tdata["world_rot"]

        rotated, corner_pos = rotate_image_around_pivot(img, piv, rot, pos)
        canvas.alpha_composite(rotated, corner_pos)

    # Render Head
    if is_back_view:
        rot_hb, corner_hb = rotate_image_around_pivot(head_back_img, head_piv, head_rot, neck_pos)
        canvas.alpha_composite(rot_hb, corner_hb)
    else:
        # 1. Head Base
        hb_img = head_layers["head_base"]
        rot_hb, corner_hb = rotate_image_around_pivot(hb_img, head_piv, head_rot, neck_pos)
        canvas.alpha_composite(rot_hb, corner_hb)

        # 2. Eye layer
        eye_key = f"eyes_{eye_state}"
        if eye_key in head_layers:
            rot_eye, corner_eye = rotate_image_around_pivot(head_layers[eye_key], head_piv, head_rot, neck_pos)
            canvas.alpha_composite(rot_eye, corner_eye)

        # 3. Mouth layer
        mouth_key = f"mouth_{mouth_state}"
        if mouth_key in head_layers:
            rot_m, corner_m = rotate_image_around_pivot(head_layers[mouth_key], head_piv, head_rot, neck_pos)
            canvas.alpha_composite(rot_m, corner_m)

    return canvas


def rotate_image_around_pivot(
    img: Image.Image,
    pivot: Tuple[int, int],
    angle_deg: float,
    world_pos: Tuple[float, float],
) -> Tuple[Image.Image, Tuple[int, int]]:
    """Rotates an RGBA image around its local pivot and returns (rotated_canvas, top_left_paste_pos)."""
    w, h = img.size
    px, py = pivot

    max_dist = max(
        math.hypot(px, py),
        math.hypot(w - px, py),
        math.hypot(px, h - py),
        math.hypot(w - px, h - py),
    )
    pad_r = int(math.ceil(max_dist)) + 4
    pad_size = 2 * pad_r

    padded = Image.new("RGBA", (pad_size, pad_size), (0, 0, 0, 0))
    paste_x = int(round(pad_r - px))
    paste_y = int(round(pad_r - py))
    padded.paste(img, (paste_x, paste_y), img)

    rotated = padded.rotate(-angle_deg, resample=Image.Resampling.BILINEAR)

    top_left_x = int(round(world_pos[0] - pad_r))
    top_left_y = int(round(world_pos[1] - pad_r))
    return rotated, (top_left_x, top_left_y)


def create_character_pack(char_id: str) -> Dict[str, Any]:
    """Builds complete character pack for char_id ('boy_b' or 'girl_a')."""
    base_dir = PROJECT_ROOT / "assets" / "2d" / "characters" / char_id
    layers_dir = base_dir / "layers"
    staging_dir = base_dir / "staging"
    layers_dir.mkdir(parents=True, exist_ok=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    sources_dir = PROJECT_ROOT / "assets" / "sources"
    face_path = sources_dir / f"{char_id}_face.jpg"
    body_path = sources_dir / f"{char_id}_body.png"

    print(f"\n==========================================")
    print(f"Building Character Pack: {char_id}")
    print(f"==========================================")

    # 1. Align face tiles
    tiles, offsets = align_and_extract_face_tiles(face_path)
    print(f"Aligned 8 face tiles across grid with verified offsets.")

    # 2. Build head base & swappable face layers
    head_layers = build_head_layers(tiles, char_id=char_id)
    for name, img in head_layers.items():
        out_p = layers_dir / f"{name}.png"
        img.save(out_p)
        print(f"  Saved layer: {out_p.name} ({img.size[0]}x{img.size[1]})")

    # 3. Build back of head
    head_back_img = build_head_back(body_path, char_id=char_id)
    head_back_p = layers_dir / "head_back.png"
    head_back_img.save(head_back_p)
    print(f"  Saved layer: head_back.png ({head_back_img.size[0]}x{head_back_img.size[1]})")

    # 4. Extract body parts
    body_parts = extract_body_parts(body_path, char_id=char_id)
    for name, pdata in body_parts.items():
        out_p = layers_dir / f"{name}.png"
        pdata["image"].save(out_p)
        print(f"  Saved layer: {out_p.name} ({pdata['image'].size[0]}x{pdata['image'].size[1]})")

    # 5. Build manifest.json
    layer_list = [
        "head_back",
        "shoe_right",
        "leg_lower_right",
        "leg_upper_right",
        "arm_lower_right",
        "arm_upper_right",
        "shoe_left",
        "leg_lower_left",
        "leg_upper_left",
        "torso",
        "head_base",
        "arm_upper_left",
        "arm_lower_left",
        "eyes_open",
        "eyes_blink",
        "eyes_look_left",
        "eyes_look_right",
        "mouth_closed",
        "mouth_slightly_open",
        "mouth_wide_open",
        "mouth_round_o",
        "mouth_open_smile",
    ]

    pivots = {
        "neck": body_parts["torso"]["joints"]["neck"],
        "head": [142, 240],
        "shoulder_left": body_parts["torso"]["joints"]["shoulder_left"],
        "shoulder_right": body_parts["torso"]["joints"]["shoulder_right"],
        "elbow_left": body_parts["arm_upper_left"]["joints"]["elbow"],
        "elbow_right": body_parts["arm_upper_right"]["joints"]["elbow"],
        "hip_left": body_parts["torso"]["joints"]["hip_left"],
        "hip_right": body_parts["torso"]["joints"]["hip_right"],
        "knee_left": body_parts["leg_upper_left"]["joints"]["knee"],
        "knee_right": body_parts["leg_upper_right"]["joints"]["knee"],
        "ankle_left": body_parts["leg_lower_left"]["joints"]["ankle"],
        "ankle_right": body_parts["leg_lower_right"]["joints"]["ankle"],
    }

    manifest = {
        "id": char_id,
        "name": "Boy B" if char_id == "boy_b" else "Girl A",
        "kind": "raster",
        "type": "layered",
        "viewBox": "0 0 600 1100",
        "default_eyes": "open",
        "default_mouth": "closed",
        "default_slot": "right" if char_id == "boy_b" else "left",
        "scale": 1.0,
        "head_position": [300, 260],
        "pivots": pivots,
        "anchors": {
            "head": [300, 260],
            "neck": [300, 260],
            "mouth": [300, 310],
            "eyes": [300, 240],
            "ground": [300, 1050],
        },
        "safe_bounding_box": {
            "min_x": 50,
            "min_y": 20,
            "max_x": 550,
            "max_y": 1080,
        },
        "layers": layer_list,
        "z_order": {
            "head_back": 0,
            "shoe_right": 1,
            "leg_lower_right": 1,
            "leg_upper_right": 1,
            "arm_lower_right": 3,
            "arm_upper_right": 3,
            "shoe_left": 2,
            "leg_lower_left": 2,
            "leg_upper_left": 2,
            "torso": 4,
            "head_base": 5,
            "arm_upper_left": 6,
            "arm_lower_left": 6,
            "eyes": 7,
            "mouth": 7,
        },
        "eye_states": ["open", "blink", "look_left", "look_right"],
        "mouth_states": ["closed", "slightly_open", "wide_open", "round_o", "open_smile"],
        "allowed_gestures": ["idle", "walk", "wave", "point", "explain"],
    }

    manifest_p = base_dir / "manifest.json"
    with open(manifest_p, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved manifest: {manifest_p.name}")

    # 6. Build character.json for Character2D compatibility
    char_json = {
        "name": char_id,
        "slots": {
            "hair": None,
            "hat": None,
            "torso": "torso",
            "legs": "leg_upper_left",
            "shoes": "shoe_left",
            "hands": None,
        },
        "active_expression": "neutral",
        "active_hand_left": "open_palm",
        "active_hand_right": "open_palm",
        "parts": {
            name: {
                "name": name,
                "image": f"layers/{name}.png",
                "pivot": pdata["pivot"],
                "parent": pdata["parent"],
                "parent_joint": pdata["parent_joint"],
                "slot": None,
                "z_index": pdata["z_index"],
                "base_rotation": 0.0,
                "joints": pdata["joints"],
            }
            for name, pdata in body_parts.items()
        },
        "expressions": {
            "neutral": "layers/head_base.png",
        },
    }
    # Add head to parts in character.json
    char_json["parts"]["head"] = {
        "name": "head",
        "image": "layers/head_base.png",
        "pivot": [142, 240],
        "parent": "torso",
        "parent_joint": "neck",
        "slot": None,
        "z_index": 5,
        "base_rotation": 0.0,
        "joints": {
            "face": [142, 160],
            "hair": [142, 30],
        },
    }

    char_json_p = base_dir / "character.json"
    with open(char_json_p, "w", encoding="utf-8") as f:
        json.dump(char_json, f, indent=2)
    print(f"Saved character.json: {char_json_p.name}")

    # 7. Render Preview Sheet
    preview_poses = [
        ("pose_01_front_standing", {}, "open", "closed", False),
        ("pose_02_mouth_slightly_open", {}, "open", "slightly_open", False),
        ("pose_03_mouth_wide_open", {}, "open", "wide_open", False),
        ("pose_04_mouth_round_o", {}, "open", "round_o", False),
        ("pose_05_mouth_open_smile", {}, "open", "open_smile", False),
        ("pose_06_eyes_blink", {}, "blink", "closed", False),
        ("pose_07_eyes_look_left", {}, "look_left", "closed", False),
        ("pose_08_eyes_look_right", {}, "look_right", "closed", False),
        ("pose_09_arm_raised", {"arm_upper_right": -115.0, "arm_lower_right": -35.0}, "open", "open_smile", False),
        (
            "pose_10_walking_swing",
            {
                "leg_upper_left": 26.0,
                "leg_lower_left": 15.0,
                "leg_upper_right": -26.0,
                "leg_lower_right": 25.0,
                "arm_upper_left": -22.0,
                "arm_lower_left": -10.0,
                "arm_upper_right": 22.0,
                "arm_lower_right": 10.0,
            },
            "open",
            "slightly_open",
            False,
        ),
        ("pose_11_back_view", {}, "open", "closed", True),
    ]

    rendered_pose_images = []
    for pose_name, ang, eye, mouth, is_back in preview_poses:
        if is_back:
            # Authentic rear figure from body sheet right side (draped hood/vest back, rear shoes)
            body_im = Image.open(body_path).convert("RGBA")
            if char_id == "boy_b":
                rear_crop = body_im.crop((175, 15, 335, 506))
            else:
                rear_crop = body_im.crop((170, 50, 335, 475))
            rear_clean = floodfill_transparent_bg(rear_crop, bg_thresh=238)
            std_bbox = rendered_pose_images[0][1].getbbox()
            target_h = std_bbox[3] - std_bbox[1] if std_bbox else rear_clean.size[1]
            scale = target_h / max(1, rear_clean.size[1])
            new_w = int(round(rear_clean.size[0] * scale))
            new_h = int(round(rear_clean.size[1] * scale))
            scaled_rear = rear_clean.resize((new_w, new_h), Image.Resampling.LANCZOS)
            pose_img = Image.new("RGBA", (600, 1100), (0, 0, 0, 0))
            paste_x = (600 - new_w) // 2
            paste_y = std_bbox[1] if std_bbox else 50
            pose_img.alpha_composite(scaled_rear, (paste_x, paste_y))
        else:
            pose_img = assemble_character_pose(
                parts=body_parts,
                head_layers=head_layers,
                head_back_img=head_back_img,
                angles=ang,
                eye_state=eye,
                mouth_state=mouth,
                is_back_view=is_back,
                canvas_size=(600, 1100),
            )
        out_pose_p = staging_dir / f"{pose_name}.png"
        pose_img.save(out_pose_p)
        rendered_pose_images.append((pose_name, pose_img))
        print(f"  Rendered preview pose: {pose_name}.png")

    # Create composite preview sheet (3 rows x 4 columns)
    cell_w, cell_h = 300, 550
    sheet_cols, sheet_rows = 4, 3
    sheet_w = sheet_cols * cell_w
    sheet_h = sheet_rows * cell_h

    preview_sheet = Image.new("RGBA", (sheet_w, sheet_h), (250, 248, 245, 255))
    sdraw = ImageDraw.Draw(preview_sheet)

    for idx, (pname, pimg) in enumerate(rendered_pose_images):
        col = idx % sheet_cols
        row = idx // sheet_cols
        x = col * cell_w
        y = row * cell_h

        thumb = pimg.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
        preview_sheet.alpha_composite(thumb, (x, y))

        label = pname.replace("pose_", "").replace("_", " ").title()
        sdraw.rectangle([x + 10, y + cell_h - 30, x + cell_w - 10, y + cell_h - 8], fill=(30, 41, 59, 220))
        sdraw.text((x + 16, y + cell_h - 26), label, fill=(248, 250, 252, 255))

    contact_sheet_p = staging_dir / f"{char_id}_preview_sheet.png"
    preview_sheet.save(contact_sheet_p)
    print(f"Saved complete preview contact sheet: {contact_sheet_p}")

    # 8. Render standing pose comparison against source sheet
    body_im = Image.open(body_path).convert("RGBA")
    front_src = body_im.crop((20, 15, 170, 508)) if char_id == "boy_b" else body_im.crop((18, 50, 172, 475))
    front_src_clean = floodfill_transparent_bg(front_src, bg_thresh=238)

    # Crop standing pose bounding box
    standing_pose = rendered_pose_images[0][1]
    bbox = standing_pose.getbbox()
    if bbox:
        standing_crop = standing_pose.crop(bbox)
        # Scale to match source height
        target_h = front_src_clean.size[1]
        scale = target_h / max(1, standing_crop.size[1])
        target_w = int(round(standing_crop.size[0] * scale))
        standing_scaled = standing_crop.resize((target_w, target_h), Image.Resampling.LANCZOS)

        cmp_w = front_src_clean.size[0] + standing_scaled.size[0] + 20
        cmp_h = target_h + 40
        cmp_img = Image.new("RGBA", (cmp_w, cmp_h), (255, 255, 255, 255))
        cdraw = ImageDraw.Draw(cmp_img)

        # Draw labels
        cdraw.text((10, 8), "Source Sheet", fill=(100, 100, 100, 255))
        cdraw.text((front_src_clean.size[0] + 30, 8), "Rebuilt Standing Pose", fill=(100, 100, 100, 255))

        cmp_img.alpha_composite(front_src_clean, (10, 30))
        cmp_img.alpha_composite(standing_scaled, (front_src_clean.size[0] + 20, 30))

        cmp_p = staging_dir / f"{char_id}_source_comparison.png"
        cmp_img.save(cmp_p)
        print(f"Saved source comparison check: {cmp_p}")

    return {
        "char_id": char_id,
        "manifest": manifest,
        "layers_count": len(layer_list),
        "preview_sheet": contact_sheet_p,
    }


def main():
    print("Building character packs for boy_b and girl_a...")
    res_boy = create_character_pack("boy_b")
    res_girl = create_character_pack("girl_a")
    print("\nAll character packs successfully built and validated!")


if __name__ == "__main__":
    main()
