"""
Purpose: 2D character and scene frame renderer with composition, ground shadow, and contact sheet generation.
Inputs: Character2D models, SkeletonPose2D poses, dimensions, and output paths.
Outputs: Rendered RGBA PIL Images and contact sheet PNG files.
Depends on: math, numpy, pathlib, typing, PIL, core.fk_solver
Used by: core.character2d
Config keys: None
Tests: tests/unit/test_character2d.py
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from toonshorts.core.fk_solver import (
    SkeletonPose2D,
    compute_forward_kinematics,
    get_face_for_audio,
)

if TYPE_CHECKING:
    from toonshorts.core.character2d import Character2D


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
