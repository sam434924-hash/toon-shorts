"""
Purpose: 2D vector stickman rendering engine implemented in Pycairo.
Inputs: Scene action, character poses, facial states, and style presets.
Outputs: Generated 1080x1920 PNG story frames and character animations.
Depends on: cairo, core.config, core.models, core.registry, math, pathlib, typing
Used by: None
Config keys: VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/contract/test_render_contract.py, tests/unit/test_cairo_stickman.py
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import cairo

from toonshorts.core import config
from toonshorts.core.models import ScriptPlan, Scene, Character, Pose
from toonshorts.core.registry import RenderInterface, register_renderer


# --- Enums & Data Structures ---

class EyebrowState(str, Enum):
    NEUTRAL = "neutral"
    RAISED = "raised"
    ANGRY = "angry"
    SAD = "sad"


class MouthShape(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    WIDE = "wide"
    ROUND = "round"


class ActionType(str, Enum):
    IDLE = "idle"
    WALK = "walk"
    WAVE = "wave"
    JUMP = "jump"


@dataclass
class GarmentLayer:
    """Extra drawn layer attached to a specific skeleton part (e.g. sleeve, hat, trousers)."""
    slot: str  # e.g. "head", "torso", "upper_arm_l", "lower_arm_l", "upper_leg_l", "lower_leg_l", "shoe_l"
    name: str
    z_order: int = 1  # <0: under body part, >=0: over body part
    render_fn: Optional[Callable[[cairo.Context, float, float, Dict[str, Any]], None]] = None


@dataclass
class SkeletonPose:
    """Skeletal rotation and translation state."""
    root_x: float = 540.0
    root_y: float = 1420.0
    squash_x: float = 1.0
    squash_y: float = 1.0
    torso_angle: float = 0.0  # radians
    head_angle: float = 0.0
    # Left Arm
    shoulder_l_angle: float = 0.0
    elbow_l_angle: float = 0.0
    wrist_l_angle: float = 0.0
    # Right Arm
    shoulder_r_angle: float = 0.0
    elbow_r_angle: float = 0.0
    wrist_r_angle: float = 0.0
    # Left Leg
    hip_l_angle: float = 0.0
    knee_l_angle: float = 0.0
    ankle_l_angle: float = 0.0
    # Right Leg
    hip_r_angle: float = 0.0
    knee_r_angle: float = 0.0
    ankle_r_angle: float = 0.0
    # Facial
    eyebrow_state: EyebrowState = EyebrowState.NEUTRAL
    mouth_shape: MouthShape = MouthShape.CLOSED
    blink: bool = False
    # Garment attachments
    garments: List[GarmentLayer] = field(default_factory=list)


# --- Helper Utilities ---

def hex_to_rgb01(hex_str: str, default: Tuple[float, float, float] = (0.1, 0.1, 0.1)) -> Tuple[float, float, float]:
    """Converts a hex color code to RGB values normalized to 0.0 - 1.0."""
    cleaned = hex_str.lstrip("#")
    if len(cleaned) == 6:
        try:
            return (
                int(cleaned[0:2], 16) / 255.0,
                int(cleaned[2:4], 16) / 255.0,
                int(cleaned[4:6], 16) / 255.0,
            )
        except ValueError:
            pass
    return default


def _draw_wobbly_line(
    ctx: cairo.Context,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    wobble: float = 2.0,
    seed: int = 0,
):
    """Draws a line with subtle hand-drawn organic curvature."""
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 1e-4:
        ctx.line_to(x2, y2)
        return

    nx = -dy / dist
    ny = dx / dist

    w1 = wobble * math.sin(seed * 2.3 + 1.1)
    w2 = wobble * math.cos(seed * 3.7 + 2.4)

    cp1_x = x1 + dx * 0.33 + nx * w1
    cp1_y = y1 + dy * 0.33 + ny * w1
    cp2_x = x1 + dx * 0.67 + nx * w2
    cp2_y = y1 + dy * 0.67 + ny * w2

    ctx.curve_to(cp1_x, cp1_y, cp2_x, cp2_y, x2, y2)


def _draw_rounded_limb(
    ctx: cairo.Context,
    length: float,
    radius: float,
    fill_color: Tuple[float, float, float],
    outline_color: Tuple[float, float, float],
    outline_width: float = 6.0,
    wobble: float = 1.8,
    seed: int = 0,
):
    """Draws a thick rounded capsule limb from (0, 0) to (0, length)."""
    ctx.new_path()
    # Top semicircular cap around (0, 0)
    ctx.arc(0, 0, radius, math.pi, 0)
    # Right edge downward with wobble
    _draw_wobbly_line(ctx, radius, 0, radius, length, wobble=wobble, seed=seed)
    # Bottom semicircular cap around (0, length)
    ctx.arc(0, length, radius, 0, math.pi)
    # Left edge upward with wobble
    _draw_wobbly_line(ctx, -radius, length, -radius, 0, wobble=wobble, seed=seed + 1)
    ctx.close_path()

    # Flat color fill
    ctx.set_source_rgb(*fill_color)
    ctx.fill_preserve()

    # Dark hand-drawn outline
    ctx.set_source_rgb(*outline_color)
    ctx.set_line_width(outline_width)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


# --- Part Rendering with Garment Slot Hooks ---

def _render_garments_for_slot(
    ctx: cairo.Context,
    garments: List[GarmentLayer],
    slot: str,
    length: float,
    radius: float,
    z_filter: str = "all",  # "under", "over", or "all"
):
    """Renders garment layers attached to a specific skeleton slot."""
    for g in garments:
        if g.slot != slot or not g.render_fn:
            continue
        if z_filter == "under" and g.z_order >= 0:
            continue
        if z_filter == "over" and g.z_order < 0:
            continue
        g.render_fn(ctx, length, radius, {})


def _draw_hand(
    ctx: cairo.Context,
    fill_color: Tuple[float, float, float],
    outline_color: Tuple[float, float, float],
    outline_width: float = 6.0,
):
    """Draws a rounded hand mitten attached at (0, 0)."""
    ctx.new_path()
    ctx.arc(0, 16, 15, -math.pi * 0.8, math.pi * 0.8)
    ctx.close_path()
    ctx.set_source_rgb(*fill_color)
    ctx.fill_preserve()
    ctx.set_source_rgb(*outline_color)
    ctx.set_line_width(outline_width)
    ctx.stroke()


def _draw_shoe(
    ctx: cairo.Context,
    shoe_color: Tuple[float, float, float],
    outline_color: Tuple[float, float, float],
    outline_width: float = 6.0,
    facing_left: bool = False,
):
    """Draws a rounded shoe attached at ankle (0, 0)."""
    ctx.save()
    if facing_left:
        ctx.scale(-1.0, 1.0)

    ctx.new_path()
    # Heel back, bottom sole, toe curve, and ankle top
    ctx.move_to(-16, -2)
    ctx.line_to(36, -2)
    ctx.arc(36, 14, 15, -math.pi * 0.5, math.pi * 0.5)
    ctx.line_to(-16, 29)
    ctx.arc(-16, 14, 15, math.pi * 0.5, math.pi * 1.5)
    ctx.close_path()

    ctx.set_source_rgb(*shoe_color)
    ctx.fill_preserve()
    ctx.set_source_rgb(*outline_color)
    ctx.set_line_width(outline_width)
    ctx.stroke()
    ctx.restore()


def _draw_face(
    ctx: cairo.Context,
    eyebrow_state: EyebrowState,
    mouth_shape: MouthShape,
    blink: bool,
    outline_color: Tuple[float, float, float],
    accent_color: Tuple[float, float, float],
):
    """Renders eyes, 2 eyebrows, and mouth shapes inside head coordinate frame."""
    eye_x = 22.0
    eye_y = -8.0
    eye_r = 7.0

    # 1. Eyes
    ctx.set_source_rgb(*outline_color)
    ctx.set_line_width(5.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    if blink:
        # Curved horizontal slits for closed blinking eyes
        ctx.new_path()
        ctx.arc(-eye_x, eye_y + 2, 9, math.pi * 0.15, math.pi * 0.85)
        ctx.stroke()
        ctx.new_path()
        ctx.arc(eye_x, eye_y + 2, 9, math.pi * 0.15, math.pi * 0.85)
        ctx.stroke()
    else:
        # Round/oval eyes with pupil
        ctx.new_path()
        ctx.arc(-eye_x, eye_y, eye_r, 0, 2 * math.pi)
        ctx.fill()
        ctx.new_path()
        ctx.arc(eye_x, eye_y, eye_r, 0, 2 * math.pi)
        ctx.fill()
        # Highlights
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.new_path()
        ctx.arc(-eye_x + 2, eye_y - 2, 2.2, 0, 2 * math.pi)
        ctx.fill()
        ctx.new_path()
        ctx.arc(eye_x + 2, eye_y - 2, 2.2, 0, 2 * math.pi)
        ctx.fill()

    # 2. Eyebrows (4 states: neutral, raised, angry, sad)
    ctx.set_source_rgb(*outline_color)
    ctx.set_line_width(6.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    brow_y = eye_y - 18.0
    brow_w = 16.0

    if eyebrow_state == EyebrowState.RAISED:
        by = brow_y - 10.0
        ctx.new_path()
        ctx.arc(-eye_x, by + 10, brow_w, -math.pi * 0.75, -math.pi * 0.25)
        ctx.stroke()
        ctx.new_path()
        ctx.arc(eye_x, by + 10, brow_w, -math.pi * 0.75, -math.pi * 0.25)
        ctx.stroke()

    elif eyebrow_state == EyebrowState.ANGRY:
        ctx.new_path()
        ctx.move_to(-eye_x - brow_w * 0.8, brow_y - 6.0)
        ctx.line_to(-eye_x + brow_w * 0.8, brow_y + 8.0)
        ctx.stroke()
        ctx.new_path()
        ctx.move_to(eye_x - brow_w * 0.8, brow_y + 8.0)
        ctx.line_to(eye_x + brow_w * 0.8, brow_y - 6.0)
        ctx.stroke()

    elif eyebrow_state == EyebrowState.SAD:
        ctx.new_path()
        ctx.move_to(-eye_x - brow_w * 0.8, brow_y + 8.0)
        ctx.line_to(-eye_x + brow_w * 0.8, brow_y - 5.0)
        ctx.stroke()
        ctx.new_path()
        ctx.move_to(eye_x - brow_w * 0.8, brow_y - 5.0)
        ctx.line_to(eye_x + brow_w * 0.8, brow_y + 8.0)
        ctx.stroke()

    else:  # NEUTRAL
        ctx.new_path()
        ctx.arc(-eye_x, brow_y + 16, brow_w, -math.pi * 0.65, -math.pi * 0.35)
        ctx.stroke()
        ctx.new_path()
        ctx.arc(eye_x, brow_y + 16, brow_w, -math.pi * 0.65, -math.pi * 0.35)
        ctx.stroke()

    # 3. Mouth (4 shapes: closed, open, wide, round)
    mouth_y = eye_y + 32.0

    if mouth_shape == MouthShape.ROUND:
        ctx.new_path()
        ctx.arc(0, mouth_y, 11, 0, 2 * math.pi)
        ctx.set_source_rgb(*accent_color)
        ctx.fill_preserve()
        ctx.set_source_rgb(*outline_color)
        ctx.set_line_width(5.0)
        ctx.stroke()

    elif mouth_shape == MouthShape.OPEN:
        ctx.new_path()
        ctx.arc(0, mouth_y, 14, 0, 2 * math.pi)
        ctx.set_source_rgb(*outline_color)
        ctx.fill()
        ctx.new_path()
        ctx.arc(0, mouth_y + 5, 8, 0, math.pi)
        ctx.set_source_rgb(*accent_color)
        ctx.fill()

    elif mouth_shape == MouthShape.WIDE:
        ctx.new_path()
        ctx.arc(0, mouth_y - 5, 26, 0.1 * math.pi, 0.9 * math.pi)
        ctx.close_path()
        ctx.set_source_rgb(*accent_color)
        ctx.fill_preserve()
        ctx.set_source_rgb(*outline_color)
        ctx.set_line_width(5.0)
        ctx.stroke()

    else:  # CLOSED
        ctx.new_path()
        ctx.arc(0, mouth_y - 12, 22, math.pi * 0.25, math.pi * 0.75)
        ctx.set_source_rgb(*outline_color)
        ctx.set_line_width(5.5)
        ctx.stroke()


# --- Complete 2D Skeleton Renderer ---

def draw_stickman_skeleton(
    ctx: cairo.Context,
    pose: SkeletonPose,
    palette: Dict[str, Any],
):
    """
    Renders 2D stickman character with hierarchical forward kinematics.
    Guarantees every part stays perfectly connected to its parent joint in all frames.
    """
    line_col = hex_to_rgb01(palette.get("line", "#1A1A1A"))
    body_col = hex_to_rgb01(palette.get("character_body", "#FFFFFF"))
    shoe_col = hex_to_rgb01(palette.get("character_shoe", "#2B2D42"))
    accent_col = hex_to_rgb01(palette.get("accent", "#E63946"))

    # Dimensions
    torso_len = 175.0
    upper_arm_len = 135.0
    lower_arm_len = 120.0
    upper_leg_len = 155.0
    lower_leg_len = 145.0

    limb_radius = 12.0
    torso_radius = 16.0
    head_radius = 62.0
    shoulder_w = 60.0
    hip_w = 38.0

    ctx.save()

    # Position at root hip / pelvis with squash & stretch
    ctx.translate(pose.root_x, pose.root_y)
    ctx.scale(pose.squash_x, pose.squash_y)

    # ---------------- 1. LEGS (drawn behind torso) ----------------

    # Left Leg (Hip -> Upper Leg -> Knee -> Lower Leg -> Ankle -> Shoe)
    ctx.save()
    ctx.translate(-hip_w * 0.5, 0)
    ctx.rotate(pose.hip_l_angle)
    _render_garments_for_slot(ctx, pose.garments, "upper_leg_l", upper_leg_len, limb_radius, "under")
    _draw_rounded_limb(ctx, upper_leg_len, limb_radius, body_col, line_col, seed=1)
    _render_garments_for_slot(ctx, pose.garments, "upper_leg_l", upper_leg_len, limb_radius, "over")

    ctx.translate(0, upper_leg_len)  # Exact Knee Joint
    ctx.rotate(pose.knee_l_angle)
    _render_garments_for_slot(ctx, pose.garments, "lower_leg_l", lower_leg_len, limb_radius, "under")
    _draw_rounded_limb(ctx, lower_leg_len, limb_radius, body_col, line_col, seed=2)
    _render_garments_for_slot(ctx, pose.garments, "lower_leg_l", lower_leg_len, limb_radius, "over")

    ctx.translate(0, lower_leg_len)  # Exact Ankle Joint
    ctx.rotate(pose.ankle_l_angle)
    _render_garments_for_slot(ctx, pose.garments, "shoe_l", 40.0, limb_radius, "under")
    _draw_shoe(ctx, shoe_col, line_col, facing_left=True)
    _render_garments_for_slot(ctx, pose.garments, "shoe_l", 40.0, limb_radius, "over")
    ctx.restore()

    # Right Leg
    ctx.save()
    ctx.translate(hip_w * 0.5, 0)
    ctx.rotate(pose.hip_r_angle)
    _render_garments_for_slot(ctx, pose.garments, "upper_leg_r", upper_leg_len, limb_radius, "under")
    _draw_rounded_limb(ctx, upper_leg_len, limb_radius, body_col, line_col, seed=3)
    _render_garments_for_slot(ctx, pose.garments, "upper_leg_r", upper_leg_len, limb_radius, "over")

    ctx.translate(0, upper_leg_len)  # Exact Knee Joint
    ctx.rotate(pose.knee_r_angle)
    _render_garments_for_slot(ctx, pose.garments, "lower_leg_r", lower_leg_len, limb_radius, "under")
    _draw_rounded_limb(ctx, lower_leg_len, limb_radius, body_col, line_col, seed=4)
    _render_garments_for_slot(ctx, pose.garments, "lower_leg_r", lower_leg_len, limb_radius, "over")

    ctx.translate(0, lower_leg_len)  # Exact Ankle Joint
    ctx.rotate(pose.ankle_r_angle)
    _render_garments_for_slot(ctx, pose.garments, "shoe_r", 40.0, limb_radius, "under")
    _draw_shoe(ctx, shoe_col, line_col, facing_left=False)
    _render_garments_for_slot(ctx, pose.garments, "shoe_r", 40.0, limb_radius, "over")
    ctx.restore()

    # ---------------- 2. TORSO & UPPER BODY ----------------
    ctx.save()
    ctx.rotate(pose.torso_angle)

    # Torso runs upward from (0, 0) to (0, -torso_len)
    ctx.save()
    ctx.translate(0, -torso_len)
    _render_garments_for_slot(ctx, pose.garments, "torso", torso_len, torso_radius, "under")
    _draw_rounded_limb(ctx, torso_len, torso_radius, body_col, line_col, outline_width=7.0, seed=5)
    _render_garments_for_slot(ctx, pose.garments, "torso", torso_len, torso_radius, "over")
    ctx.restore()

    # Neck is at (0, -torso_len)
    neck_y = -torso_len

    # ---------------- 3. ARMS ----------------
    # Left Arm
    ctx.save()
    ctx.translate(-shoulder_w * 0.5, neck_y + 12.0)
    ctx.rotate(pose.shoulder_l_angle)
    _render_garments_for_slot(ctx, pose.garments, "upper_arm_l", upper_arm_len, limb_radius, "under")
    _draw_rounded_limb(ctx, upper_arm_len, limb_radius, body_col, line_col, seed=6)
    _render_garments_for_slot(ctx, pose.garments, "upper_arm_l", upper_arm_len, limb_radius, "over")

    ctx.translate(0, upper_arm_len)  # Exact Elbow Joint
    ctx.rotate(pose.elbow_l_angle)
    _render_garments_for_slot(ctx, pose.garments, "lower_arm_l", lower_arm_len, limb_radius, "under")
    _draw_rounded_limb(ctx, lower_arm_len, limb_radius, body_col, line_col, seed=7)
    _render_garments_for_slot(ctx, pose.garments, "lower_arm_l", lower_arm_len, limb_radius, "over")

    ctx.translate(0, lower_arm_len)  # Exact Wrist Joint
    ctx.rotate(pose.wrist_l_angle)
    _render_garments_for_slot(ctx, pose.garments, "hand_l", 30.0, limb_radius, "under")
    _draw_hand(ctx, body_col, line_col)
    _render_garments_for_slot(ctx, pose.garments, "hand_l", 30.0, limb_radius, "over")
    ctx.restore()

    # Right Arm
    ctx.save()
    ctx.translate(shoulder_w * 0.5, neck_y + 12.0)
    ctx.rotate(pose.shoulder_r_angle)
    _render_garments_for_slot(ctx, pose.garments, "upper_arm_r", upper_arm_len, limb_radius, "under")
    _draw_rounded_limb(ctx, upper_arm_len, limb_radius, body_col, line_col, seed=8)
    _render_garments_for_slot(ctx, pose.garments, "upper_arm_r", upper_arm_len, limb_radius, "over")

    ctx.translate(0, upper_arm_len)  # Exact Elbow Joint
    ctx.rotate(pose.elbow_r_angle)
    _render_garments_for_slot(ctx, pose.garments, "lower_arm_r", lower_arm_len, limb_radius, "under")
    _draw_rounded_limb(ctx, lower_arm_len, limb_radius, body_col, line_col, seed=9)
    _render_garments_for_slot(ctx, pose.garments, "lower_arm_r", lower_arm_len, limb_radius, "over")

    ctx.translate(0, lower_arm_len)  # Exact Wrist Joint
    ctx.rotate(pose.wrist_r_angle)
    _render_garments_for_slot(ctx, pose.garments, "hand_r", 30.0, limb_radius, "under")
    _draw_hand(ctx, body_col, line_col)
    _render_garments_for_slot(ctx, pose.garments, "hand_r", 30.0, limb_radius, "over")
    ctx.restore()

    # ---------------- 4. HEAD & FACE ----------------
    ctx.save()
    ctx.translate(0, neck_y - head_radius)
    ctx.rotate(pose.head_angle)

    _render_garments_for_slot(ctx, pose.garments, "head", head_radius * 2.0, head_radius, "under")

    # Round Head Circle with slight wobble
    ctx.new_path()
    steps = 48
    for i in range(steps):
        angle = i * (2.0 * math.pi / steps)
        r_wobble = head_radius + 1.2 * math.sin(angle * 5.0 + 1.5)
        hx = r_wobble * math.cos(angle)
        hy = r_wobble * math.sin(angle)
        if i == 0:
            ctx.move_to(hx, hy)
        else:
            ctx.line_to(hx, hy)
    ctx.close_path()

    ctx.set_source_rgb(*body_col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*line_col)
    ctx.set_line_width(7.0)
    ctx.stroke()

    # Face details
    _draw_face(
        ctx,
        eyebrow_state=pose.eyebrow_state,
        mouth_shape=pose.mouth_shape,
        blink=pose.blink,
        outline_color=line_col,
        accent_color=accent_col,
    )

    _render_garments_for_slot(ctx, pose.garments, "head", head_radius * 2.0, head_radius, "over")

    ctx.restore()  # Head
    ctx.restore()  # Torso
    ctx.restore()  # Root


# --- Hand-Drawn Room Background & Props ---

def draw_handdrawn_background(
    ctx: cairo.Context,
    width: int,
    height: int,
    ground_y: float,
    palette: Dict[str, Any],
):
    """Renders a simple hand-drawn room: wall, floor line, and a cozy room prop."""
    wall_col = hex_to_rgb01(palette.get("background", "#FDFBF7"))
    floor_col = (0.91, 0.88, 0.82)
    line_col = hex_to_rgb01(palette.get("line", "#1A1A1A"))
    accent_col = hex_to_rgb01(palette.get("accent", "#E63946"))
    plant_pot_col = (0.82, 0.52, 0.40)
    plant_leaf_col = (0.35, 0.62, 0.42)

    # 1. Wall
    ctx.set_source_rgb(*wall_col)
    ctx.rectangle(0, 0, width, ground_y)
    ctx.fill()

    # 2. Floor
    ctx.set_source_rgb(*floor_col)
    ctx.rectangle(0, ground_y, width, height - ground_y)
    ctx.fill()

    # 3. Baseboard / Floor Line with hand-drawn wobble
    ctx.set_source_rgb(*line_col)
    ctx.set_line_width(7.0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.move_to(0, ground_y)
    _draw_wobbly_line(ctx, 0, ground_y, width, ground_y, wobble=2.5, seed=42)
    ctx.stroke()

    # Secondary skirting line
    ctx.set_line_width(4.0)
    ctx.new_path()
    ctx.move_to(0, ground_y - 25)
    _draw_wobbly_line(ctx, 0, ground_y - 25, width, ground_y - 25, wobble=1.5, seed=43)
    ctx.stroke()

    # 4. Prop: Hand-drawn framed wall picture
    frame_x = 760.0
    frame_y = 480.0
    frame_w = 190.0
    frame_h = 240.0

    # Frame outer
    ctx.set_source_rgb(0.96, 0.94, 0.90)
    ctx.rectangle(frame_x, frame_y, frame_w, frame_h)
    ctx.fill()
    ctx.set_source_rgb(*line_col)
    ctx.set_line_width(6.0)
    ctx.rectangle(frame_x, frame_y, frame_w, frame_h)
    ctx.stroke()

    # Picture art: Minimalist mountain & sun
    ctx.save()
    ctx.rectangle(frame_x + 12, frame_y + 12, frame_w - 24, frame_h - 24)
    ctx.clip()
    # Sun
    ctx.set_source_rgb(*accent_col)
    ctx.arc(frame_x + frame_w * 0.5, frame_y + 80, 24, 0, 2 * math.pi)
    ctx.fill()
    # Mountains
    ctx.set_source_rgb(0.70, 0.75, 0.80)
    ctx.move_to(frame_x + 20, frame_y + frame_h - 20)
    ctx.line_to(frame_x + 85, frame_y + 110)
    ctx.line_to(frame_x + 150, frame_y + frame_h - 20)
    ctx.fill_preserve()
    ctx.set_source_rgb(*line_col)
    ctx.set_line_width(4.0)
    ctx.stroke()
    ctx.restore()

    # 5. Prop: Hand-drawn potted floor plant
    pot_x = 180.0
    pot_y = ground_y
    pot_w = 120.0
    pot_h = 90.0

    # Pot
    ctx.new_path()
    ctx.move_to(pot_x - pot_w * 0.5, pot_y - pot_h)
    ctx.line_to(pot_x + pot_w * 0.5, pot_y - pot_h)
    ctx.line_to(pot_x + pot_w * 0.38, pot_y)
    ctx.line_to(pot_x - pot_w * 0.38, pot_y)
    ctx.close_path()
    ctx.set_source_rgb(*plant_pot_col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*line_col)
    ctx.set_line_width(6.0)
    ctx.stroke()

    # Plant leaves
    ctx.set_source_rgb(*plant_leaf_col)
    for leaf_angle in (-0.7, -0.3, 0.0, 0.3, 0.7):
        ctx.save()
        ctx.translate(pot_x, pot_y - pot_h)
        ctx.rotate(leaf_angle)
        ctx.new_path()
        ctx.scale(0.8, 1.3)
        ctx.arc(0, -55, 25, 0, 2 * math.pi)
        ctx.fill_preserve()
        ctx.set_source_rgb(*line_col)
        ctx.set_line_width(5.0)
        ctx.stroke()
        ctx.restore()


def draw_feet_shadow(
    ctx: cairo.Context,
    x: float,
    ground_y: float,
    lift_height: float = 0.0,
):
    """Draws a soft elliptical contact shadow under the feet on the floor line."""
    h_clamped = max(0.0, lift_height)
    scale = max(0.2, 1.0 - (h_clamped / 500.0))
    alpha = max(0.05, 0.30 * (1.0 - (h_clamped / 400.0)))

    rx = 85.0 * scale
    ry = 20.0 * scale

    ctx.save()
    ctx.translate(x, ground_y + 10)
    ctx.scale(rx, ry)

    pattern = cairo.RadialGradient(0, 0, 0, 0, 0, 1.0)
    pattern.add_color_stop_rgba(0.0, 0.1, 0.1, 0.1, alpha)
    pattern.add_color_stop_rgba(0.7, 0.1, 0.1, 0.1, alpha * 0.5)
    pattern.add_color_stop_rgba(1.0, 0.1, 0.1, 0.1, 0.0)

    ctx.set_source(pattern)
    ctx.arc(0, 0, 1.0, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


# --- Action & Animation Synthesis ---

def compute_action_pose(
    action: ActionType,
    time_sec: float,
    base_x: float = 540.0,
    ground_y: float = 1420.0,
    intensity: float = 1.0,
    speed: float = 1.0,
    eyebrow_state: EyebrowState = EyebrowState.NEUTRAL,
    mouth_shape: MouthShape = MouthShape.CLOSED,
    blink: bool = False,
) -> Tuple[SkeletonPose, float]:
    """
    Computes skeletal joint angles and squash/stretch for an action state.
    Intensity is strictly clamped between 0.5 and 1.5.
    Returns (SkeletonPose, lift_height).
    """
    clamped_intensity = max(0.5, min(1.5, float(intensity)))
    phase = time_sec * speed * 2.0 * math.pi

    pose = SkeletonPose(
        root_x=base_x,
        root_y=ground_y - 295.0,  # Resting hip height so feet touch ground_y
        eyebrow_state=eyebrow_state,
        mouth_shape=mouth_shape,
        blink=blink,
    )
    lift_height = 0.0

    if action == ActionType.WALK:
        walk_phase = phase * 1.5
        leg_amp = 0.55 * clamped_intensity
        knee_amp = 0.70 * clamped_intensity
        arm_amp = 0.50 * clamped_intensity

        # Alternating leg swings
        pose.hip_l_angle = math.sin(walk_phase) * leg_amp
        pose.hip_r_angle = -math.sin(walk_phase) * leg_amp

        # Knee bending during forward recovery swing
        pose.knee_l_angle = max(0.0, -math.cos(walk_phase)) * knee_amp
        pose.knee_r_angle = max(0.0, math.cos(walk_phase)) * knee_amp

        # Arm swinging along flanks
        pose.shoulder_l_angle = math.radians(14.0) - math.sin(walk_phase) * arm_amp
        pose.shoulder_r_angle = math.radians(10.0) + math.sin(walk_phase) * arm_amp
        pose.elbow_l_angle = max(0.0, math.sin(walk_phase)) * 0.35 * clamped_intensity
        pose.elbow_r_angle = max(0.0, -math.sin(walk_phase)) * 0.35 * clamped_intensity

        # Vertical hip bounce
        bounce = abs(math.sin(walk_phase)) * 20.0 * clamped_intensity
        pose.root_y -= bounce
        pose.squash_y = 1.0 - (bounce / 320.0)
        pose.squash_x = 1.0 / math.sqrt(pose.squash_y)
        pose.torso_angle = math.radians(3.5) * math.sin(walk_phase)

    elif action == ActionType.WAVE:
        wave_phase = phase * 2.0
        # Right arm waving up high
        pose.shoulder_r_angle = math.radians(-125.0)
        pose.elbow_r_angle = math.radians(25.0) + math.sin(wave_phase) * math.radians(35.0) * clamped_intensity
        pose.wrist_r_angle = math.sin(wave_phase) * math.radians(20.0) * clamped_intensity

        # Left arm hangs relaxed at flank
        pose.shoulder_l_angle = math.radians(14.0)
        pose.elbow_l_angle = math.radians(6.0)

        pose.torso_angle = math.radians(3.0) * math.sin(phase)
        pose.head_angle = -pose.torso_angle * 0.6
        pose.squash_y = 1.0 + math.sin(phase) * 0.02 * clamped_intensity
        pose.squash_x = 1.0 / math.sqrt(pose.squash_y)

    elif action == ActionType.JUMP:
        jump_t = (time_sec * speed) % 1.0

        if jump_t < 0.20:
            # Crouch anticipation (squash)
            crouch_p = math.sin((jump_t / 0.20) * math.pi * 0.5)
            pose.squash_y = 1.0 - 0.20 * clamped_intensity * crouch_p
            pose.squash_x = 1.0 / math.sqrt(pose.squash_y)
            pose.root_y += 35.0 * clamped_intensity * crouch_p
            pose.hip_l_angle = math.radians(-20.0) * crouch_p
            pose.hip_r_angle = math.radians(-20.0) * crouch_p
            pose.knee_l_angle = math.radians(45.0) * crouch_p
            pose.knee_r_angle = math.radians(45.0) * crouch_p
            pose.shoulder_l_angle = math.radians(25.0) * crouch_p
            pose.shoulder_r_angle = -math.radians(25.0) * crouch_p

        elif jump_t < 0.55:
            # Launch & Ascent (stretch & rise)
            asc_p = (jump_t - 0.20) / 0.35
            pose.squash_y = 1.0 + 0.18 * clamped_intensity * (1.0 - asc_p)
            pose.squash_x = 1.0 / math.sqrt(pose.squash_y)
            lift_height = math.sin(asc_p * math.pi * 0.5) * 230.0 * clamped_intensity
            pose.root_y -= lift_height
            # Arms raise up in victory V
            pose.shoulder_l_angle = math.radians(-125.0)
            pose.shoulder_r_angle = math.radians(125.0)
            pose.hip_l_angle = math.radians(8.0)
            pose.hip_r_angle = math.radians(8.0)

        elif jump_t < 0.80:
            # Apex Float & Descent
            desc_p = (jump_t - 0.55) / 0.25
            lift_height = (1.0 - math.sin(desc_p * math.pi * 0.5)) * 230.0 * clamped_intensity
            pose.root_y -= lift_height
            pose.squash_y = 1.0 + 0.05 * clamped_intensity
            pose.squash_x = 1.0 / math.sqrt(pose.squash_y)
            pose.shoulder_l_angle = math.radians(-115.0)
            pose.shoulder_r_angle = math.radians(115.0)
            pose.knee_l_angle = math.radians(20.0)
            pose.knee_r_angle = math.radians(20.0)

        else:
            # Landing Impact (squash absorption)
            land_p = (jump_t - 0.80) / 0.20
            squash_factor = math.sin((1.0 - land_p) * math.pi * 0.5)
            pose.squash_y = 1.0 - 0.15 * clamped_intensity * squash_factor
            pose.squash_x = 1.0 / math.sqrt(pose.squash_y)
            pose.root_y += 20.0 * clamped_intensity * squash_factor
            pose.hip_l_angle = math.radians(-15.0) * squash_factor
            pose.hip_r_angle = math.radians(-15.0) * squash_factor
            pose.knee_l_angle = math.radians(30.0) * squash_factor
            pose.knee_r_angle = math.radians(30.0) * squash_factor
            pose.shoulder_l_angle = -math.radians(15.0)
            pose.shoulder_r_angle = math.radians(15.0)

    else:  # IDLE
        idle_dy = math.sin(phase) * 6.0 * clamped_intensity
        pose.root_y += idle_dy
        pose.squash_y = 1.0 + math.sin(phase) * 0.02 * clamped_intensity
        pose.squash_x = 1.0 / math.sqrt(pose.squash_y)
        pose.shoulder_l_angle = math.radians(14.0) + math.sin(phase) * 0.03
        pose.shoulder_r_angle = -math.radians(14.0) - math.sin(phase) * 0.03
        pose.elbow_l_angle = -math.radians(4.0)
        pose.elbow_r_angle = math.radians(4.0)
        pose.elbow_l_angle = math.radians(6.0)
        pose.elbow_r_angle = math.radians(6.0)

    return pose, lift_height


# --- Render Plugin Class ---

@register_renderer("cairo")
class CairoStickmanRenderPlugin(RenderInterface):
    """Headless 2D vector stickman rendering engine implemented in Pycairo."""
    supports_scene_audios: bool = False
    supports_fast: bool = False
    name = "cairo"

    def render_frame_to_surface(
        self,
        pose: SkeletonPose,
        lift_height: float,
        style_preset: Dict[str, Any],
        width: int = config.VIDEO_WIDTH,
        height: int = config.VIDEO_HEIGHT,
        ground_y: float = 1420.0,
    ) -> cairo.ImageSurface:
        """Renders background, contact shadow, and stickman to an ARGB32 Cairo ImageSurface."""
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        palette = style_preset.get("color_palette", {})

        # 1. Background room & props
        draw_handdrawn_background(ctx, width, height, ground_y, palette)

        # 2. Soft floor shadow under feet
        draw_feet_shadow(ctx, pose.root_x, ground_y, lift_height=lift_height)

        # 3. Stickman character
        draw_stickman_skeleton(ctx, pose, palette)

        return surface

    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Renders a 9:16 vertical story frame conforming to RenderInterface."""
        ground_y = 1420.0
        width = config.VIDEO_WIDTH
        height = config.VIDEO_HEIGHT

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        palette = style_preset.get("color_palette", {})

        # 1. Room background
        draw_handdrawn_background(ctx, width, height, ground_y, palette)

        # 2. Characters
        num_chars = len(characters)
        positions = [380.0, 700.0] if num_chars == 2 else [300.0, 540.0, 780.0]

        for i, char in enumerate(characters):
            pos_x = positions[i % len(positions)]
            is_speaker = (char.name.lower() == scene.speaker.lower())

            # Map scene pose & speech state to Action and Face
            action = ActionType.IDLE
            eyebrows = EyebrowState.NEUTRAL
            mouth = MouthShape.OPEN if is_speaker else MouthShape.CLOSED

            char_pose = scene.pose if is_speaker else Pose.IDLE
            if char_pose == Pose.WAVING:
                action = ActionType.WAVE
                eyebrows = EyebrowState.RAISED
                mouth = MouthShape.WIDE
            elif char_pose == Pose.JUMPING:
                action = ActionType.JUMP
                eyebrows = EyebrowState.RAISED
                mouth = MouthShape.ROUND
            elif char_pose == Pose.SHOCKED:
                action = ActionType.IDLE
                eyebrows = EyebrowState.ANGRY
                mouth = MouthShape.ROUND
            elif char_pose == Pose.LAUGHING:
                action = ActionType.IDLE
                eyebrows = EyebrowState.RAISED
                mouth = MouthShape.WIDE
            elif getattr(char_pose, "value", str(char_pose)).lower() in ("walk", "walking"):
                action = ActionType.WALK
                eyebrows = EyebrowState.NEUTRAL

            skel_pose, lift_height = compute_action_pose(
                action=action,
                time_sec=0.25,
                base_x=pos_x,
                ground_y=ground_y,
                intensity=1.0,
                speed=1.0,
                eyebrow_state=eyebrows,
                mouth_shape=mouth,
                blink=False,
            )

            draw_feet_shadow(ctx, pos_x, ground_y, lift_height=lift_height)
            draw_stickman_skeleton(ctx, skel_pose, palette)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        surface.write_to_png(str(output_path))
        return output_path

    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
    ) -> List[Path]:
        """Renders visual frames for all scenes in the script plan."""
        image_paths = []
        for scene in plan.scenes:
            out_img = temp_dir / f"scene_{scene.scene_number}_visual.png"
            self.render_scene(scene, plan.characters, style_preset, out_img, temp_dir)
            image_paths.append(out_img)
        return image_paths
