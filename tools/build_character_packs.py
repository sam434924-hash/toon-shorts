"""
Purpose: Extracts, aligns, and builds full-body layered character packs (boy_b, girl_a) with gapless joints and preview sheets.
Inputs: Source body and face sheets in assets/sources/
Outputs: Transparent PNG layers, manifest.json, character.json, and verification preview sheets in assets2d/characters/<id>/
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
    # Smooth edges slightly to avoid aliased fringing
    arr[visited_bg, 3] = 0
    return Image.fromarray(arr)


def add_overlap_joint_cap(
    layer: Image.Image,
    pivot: Tuple[int, int],
    radius: int,
    fill_color: Tuple[int, int, int, int],
    outline_color: Tuple[int, int, int, int],
    outline_width: int = 2,
    direction: str = "top",  # 'top' or 'bottom'
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

    # Composite original layer over or under cap
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

    # Verified grid coordinates
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
    1. head_base: hair, ears, skin, brows, glasses frame; eyes and mouth removed and filled with skin tone.
    2. eye layers: open, blink, look_left, look_right.
    3. mouth layers: closed, slightly_open, wide_open, round_o, open_smile.
    """
    closed_tile = tiles["closed"]
    tile_w, tile_h = closed_tile.size

    # 1. Base transparency
    closed_trans = floodfill_transparent_bg(closed_tile, bg_thresh=238)
    closed_arr = np.array(closed_trans)

    # Sample skin tone
    # Skin area between nose and mouth
    skin_patch = closed_arr[150:165, 130:155, :3]
    skin_r, skin_g, skin_b = np.median(skin_patch, axis=(0, 1)).astype(int)
    skin_color = (int(skin_r), int(skin_g), int(skin_b), 255)

    # Glasses centers
    if char_id == "boy_b":
        left_eye_center = (92, 116)
        right_eye_center = (192, 110)
        glasses_r = 23
        mouth_center = (144, 186)
        mouth_w, mouth_h = 26, 14
    else:  # girl_a
        left_eye_center = (96, 125)
        right_eye_center = (194, 128)
        glasses_r = 23
        mouth_center = (144, 187)
        mouth_w, mouth_h = 26, 14

    # --- Build Head Base ---
    head_base_img = closed_trans.copy()
    hb_draw = ImageDraw.Draw(head_base_img)

    # Inpaint / fill inside eye lenses with skin color (preserving glasses rim and brows)
    # Lenses are circle interior with radius r - 3
    lens_r = glasses_r - 4
    hb_draw.ellipse(
        [
            left_eye_center[0] - lens_r,
            left_eye_center[1] - lens_r,
            left_eye_center[0] + lens_r,
            left_eye_center[1] + lens_r,
        ],
        fill=skin_color,
    )
    hb_draw.ellipse(
        [
            right_eye_center[0] - lens_r,
            right_eye_center[1] - lens_r,
            right_eye_center[0] + lens_r,
            right_eye_center[1] + lens_r,
        ],
        fill=skin_color,
    )

    # Inpaint mouth area with skin color
    hb_draw.ellipse(
        [
            mouth_center[0] - mouth_w,
            mouth_center[1] - mouth_h,
            mouth_center[0] + mouth_w,
            mouth_center[1] + mouth_h,
        ],
        fill=skin_color,
    )

    # --- Build Eye Layers ---
    eye_layers = {}
    eye_states = {
        "open": tiles["closed"],
        "blink": tiles["blink"],
        "look_left": tiles["look_left"],
        "look_right": tiles["look_right"],
    }

    for state_name, src_tile in eye_states.items():
        eye_img = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        src_arr = np.array(src_tile)

        # Create mask of inner lens area
        mask = Image.new("L", (tile_w, tile_h), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.ellipse(
            [
                left_eye_center[0] - lens_r,
                left_eye_center[1] - lens_r,
                left_eye_center[0] + lens_r,
                left_eye_center[1] + lens_r,
            ],
            fill=255,
        )
        mdraw.ellipse(
            [
                right_eye_center[0] - lens_r,
                right_eye_center[1] - lens_r,
                right_eye_center[0] + lens_r,
                right_eye_center[1] + lens_r,
            ],
            fill=255,
        )

        mask_arr = np.array(mask) == 255
        out_arr = np.zeros((tile_h, tile_w, 4), dtype=np.uint8)
        out_arr[mask_arr, :3] = src_arr[mask_arr, :3]
        out_arr[mask_arr, 3] = 255

        # For blink, extract the curved eyelid line transparently
        if state_name == "blink":
            # Mask out skin pixels inside lens so only dark blink line is visible
            skin_diff = np.max(np.abs(src_arr[:, :, :3] - np.array(skin_color[:3])), axis=2)
            is_feature = mask_arr & (skin_diff > 25)
            out_arr[~is_feature, 3] = 0

        eye_layers[state_name] = Image.fromarray(out_arr)

    # --- Build Mouth Layers ---
    mouth_layers = {}
    mouth_tiles = {
        "closed": tiles["closed"],
        "slightly_open": tiles["slightly_open"],
        "wide_open": tiles["wide_open"],
        "round_o": tiles["round_o"],
        "open_smile": tiles["open_smile"],
    }

    for state_name, src_tile in mouth_tiles.items():
        src_arr = np.array(src_tile)
        mouth_img = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))

        # Bounding box around mouth
        mx, my = mouth_center
        mw = mouth_w + 12
        mh = mouth_h + 12

        # Extract features differing from skin tone
        skin_diff = np.max(np.abs(src_arr[:, :, :3] - np.array(skin_color[:3])), axis=2)
        box_mask = np.zeros((tile_h, tile_w), dtype=bool)
        box_mask[my - mh : my + mh, mx - mw : mx + mw] = True

        mouth_pixels = box_mask & (skin_diff > 18)
        # Dilate slightly to capture lip antialiasing
        mouth_pixels = cv2.dilate(mouth_pixels.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)

        out_arr = np.zeros((tile_h, tile_w, 4), dtype=np.uint8)
        out_arr[mouth_pixels, :3] = src_arr[mouth_pixels, :3]
        out_arr[mouth_pixels, 3] = 255

        mouth_layers[state_name] = Image.fromarray(out_arr)

    return {
        "head_base": head_base_img,
        **{f"eyes_{k}": v for k, v in eye_layers.items()},
        **{f"mouth_{k}": v for k, v in mouth_layers.items()},
    }


def build_head_back(
    body_sheet_path: Path,
    target_size: Tuple[int, int] = (285, 256),
    char_id: str = "boy_b",
) -> Image.Image:
    """
    Extracts back of head from the back view of body sheet,
    upscales it, removes background, and centers it to match head_base coordinates.
    """
    body_im = Image.open(body_sheet_path).convert("RGBA")
    w, h = body_im.size

    # Back view is on right half: x in 170..330
    if char_id == "boy_b":
        head_box = (175, 15, 320, 135)
    else:
        head_box = (170, 50, 325, 160)

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
    """
    body_im = Image.open(body_sheet_path).convert("RGBA")
    w, h = body_im.size

    # Crop front view (left half)
    if char_id == "boy_b":
        front_box = (20, 15, 170, 508)
        palette = {
            "hoodie": (64, 112, 160, 255),
            "hoodie_dark": (35, 60, 90, 255),
            "pants": (64, 80, 96, 255),
            "pants_dark": (40, 50, 65, 255),
            "shoe": (224, 224, 224, 255),
            "shoe_dark": (30, 30, 30, 255),
            "skin": (240, 176, 144, 255),
        }
    else:  # girl_a
        front_box = (18, 50, 172, 475)
        palette = {
            "hoodie": (144, 64, 144, 255),  # purple vest
            "hoodie_dark": (70, 30, 70, 255),
            "pants": (32, 64, 96, 255),  # dark teal pants
            "pants_dark": (20, 40, 60, 255),
            "shoe": (210, 194, 211, 255),
            "shoe_dark": (30, 30, 30, 255),
            "skin": (240, 192, 160, 255),
        }

    front_crop = body_im.crop(front_box)
    # Upscale 2x with Lanczos for smooth subpixel anti-aliasing
    fw, fh = front_crop.size
    front_2x = front_crop.resize((fw * 2, fh * 2), Image.Resampling.LANCZOS)
    front_clean = floodfill_transparent_bg(front_2x, bg_thresh=238)
    arr = np.array(front_clean)

    parts: Dict[str, Dict[str, Any]] = {}

    if char_id == "boy_b":
        # Coordinates on 300x986 2x canvas
        # 1. Torso
        torso_crop = arr[235:545, 45:255].copy()
        # Inpaint/fill arm overlap sides with solid hoodie color so raising arm leaves no hollow edge
        torso_img = Image.fromarray(torso_crop)
        # Expand side boundaries
        tdraw = ImageDraw.Draw(torso_img)
        tdraw.rectangle([0, 60, 35, 250], fill=palette["hoodie"])
        tdraw.rectangle([175, 60, 210, 250], fill=palette["hoodie"])

        parts["torso"] = {
            "image": torso_img,
            "pivot": [105, 290],  # waist / hip pivot
            "parent": None,
            "parent_joint": None,
            "z_index": 4,
            "joints": {
                "neck": [105, 12],
                "shoulder_left": [25, 45],
                "shoulder_right": [185, 45],
                "hip_left": [70, 290],
                "hip_right": [140, 290],
            },
        }

        # 2. Upper arm left (screen-left)
        ua_l = arr[250:415, 8:75].copy()
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
            "joints": {"elbow": [ua_l_piv[0] - 2, ua_l_piv[1] + 130]},
        }

        # 3. Forearm + hand left
        la_l = arr[395:575, 5:75].copy()
        la_l_img = Image.fromarray(la_l)
        la_l_capped, la_l_piv = add_overlap_joint_cap(
            la_l_img, pivot=(30, 8), radius=14, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
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
        ua_r = arr[250:415, 225:292].copy()
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
            "joints": {"elbow": [ua_r_piv[0] + 2, ua_r_piv[1] + 130]},
        }

        # 5. Forearm + hand right
        la_r = arr[395:575, 225:295].copy()
        la_r_img = Image.fromarray(la_r)
        la_r_capped, la_r_piv = add_overlap_joint_cap(
            la_r_img, pivot=(36, 8), radius=14, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
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
        ul_l = arr[535:715, 65:140].copy()
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
            "joints": {"knee": [ul_l_piv[0], ul_l_piv[1] + 145]},
        }

        # 7. Lower leg left
        ll_l = arr[695:875, 68:140].copy()
        ll_l_img = Image.fromarray(ll_l)
        ll_l_capped, ll_l_piv = add_overlap_joint_cap(
            ll_l_img, pivot=(36, 8), radius=16, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_lower_left"] = {
            "image": ll_l_capped,
            "pivot": list(ll_l_piv),
            "parent": "leg_upper_left",
            "parent_joint": "knee",
            "z_index": 2,
            "joints": {"ankle": [ll_l_piv[0], ll_l_piv[1] + 155]},
        }

        # 8. Shoe left
        shoe_l = arr[860:980, 52:145].copy()
        parts["shoe_left"] = {
            "image": Image.fromarray(shoe_l),
            "pivot": [46, 12],
            "parent": "leg_lower_left",
            "parent_joint": "ankle",
            "z_index": 2,
            "joints": {},
        }

        # 9. Upper leg right
        ul_r = arr[535:715, 145:220].copy()
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
            "joints": {"knee": [ul_r_piv[0], ul_r_piv[1] + 145]},
        }

        # 10. Lower leg right
        ll_r = arr[695:875, 145:218].copy()
        ll_r_img = Image.fromarray(ll_r)
        ll_r_capped, ll_r_piv = add_overlap_joint_cap(
            ll_r_img, pivot=(36, 8), radius=16, fill_color=palette["pants"], outline_color=palette["pants_dark"]
        )
        parts["leg_lower_right"] = {
            "image": ll_r_capped,
            "pivot": list(ll_r_piv),
            "parent": "leg_upper_right",
            "parent_joint": "knee",
            "z_index": 1,
            "joints": {"ankle": [ll_r_piv[0], ll_r_piv[1] + 155]},
        }

        # 11. Shoe right
        shoe_r = arr[860:980, 145:238].copy()
        parts["shoe_right"] = {
            "image": Image.fromarray(shoe_r),
            "pivot": [38, 12],
            "parent": "leg_lower_right",
            "parent_joint": "ankle",
            "z_index": 1,
            "joints": {},
        }

    else:  # girl_a
        # Coordinates on 308x850 2x canvas
        # 1. Torso
        torso_crop = arr[190:470, 50:258].copy()
        torso_img = Image.fromarray(torso_crop)
        tdraw = ImageDraw.Draw(torso_img)
        tdraw.rectangle([0, 50, 30, 220], fill=palette["hoodie"])
        tdraw.rectangle([178, 50, 208, 220], fill=palette["hoodie"])

        parts["torso"] = {
            "image": torso_img,
            "pivot": [104, 260],
            "parent": None,
            "parent_joint": None,
            "z_index": 4,
            "joints": {
                "neck": [104, 10],
                "shoulder_left": [28, 40],
                "shoulder_right": [180, 40],
                "hip_left": [68, 260],
                "hip_right": [140, 260],
            },
        }

        # Upper arm left
        ua_l = arr[210:355, 20:80].copy()
        ua_l_img = Image.fromarray(ua_l)
        ua_l_capped, ua_l_piv = add_overlap_joint_cap(
            ua_l_img, pivot=(28, 10), radius=15, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_upper_left"] = {
            "image": ua_l_capped,
            "pivot": list(ua_l_piv),
            "parent": "torso",
            "parent_joint": "shoulder_left",
            "z_index": 6,
            "joints": {"elbow": [ua_l_piv[0] - 2, ua_l_piv[1] + 115]},
        }

        # Forearm + hand left
        la_l = arr[335:495, 20:80].copy()
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

        # Upper arm right
        ua_r = arr[210:355, 225:285].copy()
        ua_r_img = Image.fromarray(ua_r)
        ua_r_capped, ua_r_piv = add_overlap_joint_cap(
            ua_r_img, pivot=(32, 10), radius=15, fill_color=palette["hoodie"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_upper_right"] = {
            "image": ua_r_capped,
            "pivot": list(ua_r_piv),
            "parent": "torso",
            "parent_joint": "shoulder_right",
            "z_index": 3,
            "joints": {"elbow": [ua_r_piv[0] + 2, ua_r_piv[1] + 115]},
        }

        # Forearm + hand right
        la_r = arr[335:495, 225:285].copy()
        la_r_img = Image.fromarray(la_r)
        la_r_capped, la_r_piv = add_overlap_joint_cap(
            la_r_img, pivot=(32, 8), radius=13, fill_color=palette["skin"], outline_color=palette["hoodie_dark"]
        )
        parts["arm_lower_right"] = {
            "image": la_r_capped,
            "pivot": list(la_r_piv),
            "parent": "arm_upper_right",
            "parent_joint": "elbow",
            "z_index": 3,
            "joints": {},
        }

        # Upper leg left
        ul_l = arr[460:615, 68:145].copy()
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
            "joints": {"knee": [ul_l_piv[0], ul_l_piv[1] + 125]},
        }

        # Lower leg left
        ll_l = arr[595:745, 68:145].copy()
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
            "joints": {"ankle": [ll_l_piv[0], ll_l_piv[1] + 130]},
        }

        # Shoe left
        shoe_l = arr[730:845, 58:148].copy()
        parts["shoe_left"] = {
            "image": Image.fromarray(shoe_l),
            "pivot": [45, 12],
            "parent": "leg_lower_left",
            "parent_joint": "ankle",
            "z_index": 2,
            "joints": {},
        }

        # Upper leg right
        ul_r = arr[460:615, 150:228].copy()
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
            "joints": {"knee": [ul_r_piv[0], ul_r_piv[1] + 125]},
        }

        # Lower leg right
        ll_r = arr[595:745, 150:228].copy()
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
            "joints": {"ankle": [ll_r_piv[0], ll_r_piv[1] + 130]},
        }

        # Shoe right
        shoe_r = arr[730:845, 150:240].copy()
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

    # Calculate Torso placement
    torso = parts["torso"]
    root_x, root_y = canvas_size[0] // 2, 540

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

    # Helper to resolve chains
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

    # Head placement at neck
    neck_pos = computed_joints["neck"]
    head_rot = torso_rot + angles.get("head", 0.0)
    head_piv = (142, 242)  # Chin / collar base of head

    # Render sorted layers
    sorted_parts = sorted(transforms.items(), key=lambda x: x[1]["z_index"])

    for name, tdata in sorted_parts:
        img = tdata["image"]
        piv = tdata["pivot"]
        pos = tdata["world_pos"]
        rot = tdata["world_rot"]

        # Rotate around pivot
        rotated, corner_pos = rotate_image_around_pivot(img, piv, rot, pos)
        canvas.alpha_composite(rotated, corner_pos)

    # Render Head on top (or back of head if back view)
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
    base_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id
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
        "neck": [105, 12] if char_id == "boy_b" else [104, 10],
        "head": [142, 242],
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
        "pivot": [142, 242],
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
    # Poses:
    # 1. Front standing (default eyes, closed mouth)
    # 2. Mouth closed
    # 3. Mouth slightly open
    # 4. Mouth wide open
    # 5. Mouth round O
    # 6. Mouth open smile
    # 7. Eyes blink
    # 8. Eyes look left
    # 9. Eyes look right
    # 10. One arm raised
    # 11. Walking leg swing
    # 12. Back view standing

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

        # Downscale pose to fit cell
        thumb = pimg.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
        preview_sheet.alpha_composite(thumb, (x, y))

        # Label
        label = pname.replace("pose_", "").replace("_", " ").title()
        sdraw.rectangle([x + 10, y + cell_h - 30, x + cell_w - 10, y + cell_h - 8], fill=(30, 41, 59, 220))
        sdraw.text((x + 16, y + cell_h - 26), label, fill=(248, 250, 252, 255))

    contact_sheet_p = staging_dir / f"{char_id}_preview_sheet.png"
    preview_sheet.save(contact_sheet_p)
    print(f"Saved complete preview contact sheet: {contact_sheet_p}")

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
