"""
Purpose: Forward kinematics skeleton solver, action pose generator, and joint transformer.
Inputs: Action type, timing parameter t, intensity, speed, audio loudness, and character definitions.
Outputs: SkeletonPose2D structures and computed world transformations for character layers.
Depends on: math, typing
Used by: core.character2d, core.svg_renderer
Config keys: None
Tests: tests/unit/test_character2d.py
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from toonshorts.core.character2d import Character2D


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

        # Foot flexion
        angles["shoe_left"] = -15.0 * cos_p * clamped_intensity
        angles["shoe_right"] = 15.0 * cos_p * clamped_intensity

        # Opposite sleeve swing (sleeve_upper_left opposes leg_upper_left)
        angles["sleeve_upper_left"] = -24.0 * sin_p * clamped_intensity
        angles["sleeve_lower_left"] = -12.0 * max(0.0, -sin_p) * clamped_intensity
        angles["sleeve_upper_right"] = 24.0 * sin_p * clamped_intensity
        angles["sleeve_lower_right"] = -12.0 * max(0.0, sin_p) * clamped_intensity

        # Head bob
        angles["head"] = 2.0 * math.sin(two_pi * phase * 2.0) * clamped_intensity
        face = get_face_for_audio(loudness, base_emotion=base_emotion)

    elif action == "wave":
        # Left sleeve raises and waves hand while right arm rests at side
        wave_cycle = math.sin(two_pi * phase * 3.0)  # 3 quick wave oscillations per period

        # Raise left upper sleeve ~115 degrees
        angles["sleeve_upper_left"] = 115.0 * clamped_intensity
        # Forearm bent ~40 degrees + wave oscillation
        angles["sleeve_lower_left"] = (40.0 + (22.0 * wave_cycle)) * clamped_intensity
        # Hand wave flip
        angles["hand_left"] = (18.0 * wave_cycle) * clamped_intensity
        hand_left = "open_palm"

        # Slight head tilt towards waving arm
        angles["head"] = -5.0 * clamped_intensity
        face = get_face_for_audio(loudness, base_emotion="happy" if base_emotion == "neutral" else base_emotion)

        # Right arm hangs naturally
        angles["sleeve_upper_right"] = -4.0 * clamped_intensity
        angles["sleeve_lower_right"] = -2.0 * clamped_intensity

    elif action == "jump":
        # 4 distinct phases: crouch (0.0-0.2), push/stretch (0.2-0.4), apex (0.4-0.7), land (0.7-1.0)
        p = phase

        if p < 0.20:
            # Anticipation crouch: compress root_y down, squash vertically, expand horizontally
            t_sub = p / 0.20
            ease = math.sin(t_sub * math.pi * 0.5)
            crouch_depth = 48.0 * ease * clamped_intensity
            cur_root_y = root_y + crouch_depth
            scale_y = 1.0 - (0.16 * ease * clamped_intensity)
            scale_x = 1.0 + (0.12 * ease * clamped_intensity)

            # Deep knee bend
            angles["leg_upper_left"] = -32.0 * ease * clamped_intensity
            angles["leg_lower_left"] = 55.0 * ease * clamped_intensity
            angles["leg_upper_right"] = -32.0 * ease * clamped_intensity
            angles["leg_lower_right"] = 55.0 * ease * clamped_intensity

            # Arms swing back
            angles["sleeve_upper_left"] = -25.0 * ease * clamped_intensity
            angles["sleeve_lower_left"] = -15.0 * ease * clamped_intensity
            angles["sleeve_upper_right"] = -25.0 * ease * clamped_intensity
            angles["sleeve_lower_right"] = -15.0 * ease * clamped_intensity
            hand_left = "fist"
            hand_right = "fist"

        elif p < 0.40:
            # Push-off & stretch: explosive upward velocity, stretch vertically
            t_sub = (p - 0.20) / 0.20
            # From crouch_depth to apex
            jump_h = (math.sin(t_sub * math.pi * 0.5) * 110.0) * clamped_intensity
            jump_height = jump_h
            cur_root_y = root_y - jump_h
            scale_y = 1.0 + (0.18 * math.sin(t_sub * math.pi) * clamped_intensity)
            scale_x = 1.0 - (0.10 * math.sin(t_sub * math.pi) * clamped_intensity)

            # Legs snap straight / toe point
            angles["leg_upper_left"] = 8.0 * (1.0 - t_sub)
            angles["leg_lower_left"] = 4.0 * (1.0 - t_sub)
            angles["leg_upper_right"] = 8.0 * (1.0 - t_sub)
            angles["leg_lower_right"] = 4.0 * (1.0 - t_sub)
            angles["shoe_left"] = 20.0 * t_sub
            angles["shoe_right"] = 20.0 * t_sub

            # Arms thrust up
            angles["sleeve_upper_left"] = 120.0 * t_sub * clamped_intensity
            angles["sleeve_lower_left"] = 20.0 * t_sub * clamped_intensity
            angles["sleeve_upper_right"] = 120.0 * t_sub * clamped_intensity
            angles["sleeve_lower_right"] = 20.0 * t_sub * clamped_intensity

        elif p < 0.70:
            # Apex: hang time, slight tuck
            t_sub = (p - 0.40) / 0.30
            # Peak arc
            jump_h = (110.0 + (25.0 * math.sin(t_sub * math.pi))) * clamped_intensity
            jump_height = jump_h
            cur_root_y = root_y - jump_h
            scale_y = 1.0
            scale_x = 1.0

            # Slight leg tuck at peak
            angles["leg_upper_left"] = -18.0 * math.sin(t_sub * math.pi) * clamped_intensity
            angles["leg_lower_left"] = 35.0 * math.sin(t_sub * math.pi) * clamped_intensity
            angles["leg_upper_right"] = -18.0 * math.sin(t_sub * math.pi) * clamped_intensity
            angles["leg_lower_right"] = 35.0 * math.sin(t_sub * math.pi) * clamped_intensity

            # Arms celebrate up in air
            angles["sleeve_upper_left"] = (130.0 + (10.0 * math.sin(t_sub * math.pi))) * clamped_intensity
            angles["sleeve_lower_left"] = 30.0 * clamped_intensity
            angles["sleeve_upper_right"] = (130.0 + (10.0 * math.sin(t_sub * math.pi))) * clamped_intensity
            angles["sleeve_lower_right"] = 30.0 * clamped_intensity
            face = get_face_for_audio(loudness, base_emotion="happy")

        else:
            # Landing impact: recover to idle
            t_sub = (p - 0.70) / 0.30
            ease = 1.0 - math.cos(t_sub * math.pi * 0.5)
            # From jump_h back down to ground then quick recovery
            cur_root_y = root_y + (28.0 * math.sin(t_sub * math.pi) * (1.0 - t_sub) * clamped_intensity)
            # Impact squash
            squash = math.sin(t_sub * math.pi) * 0.12 * (1.0 - t_sub) * clamped_intensity
            scale_y = 1.0 - squash
            scale_x = 1.0 + squash

            # Dampen leg angles back to 0
            damp = (1.0 - t_sub)
            angles["leg_upper_left"] = -20.0 * damp * clamped_intensity
            angles["leg_lower_left"] = 35.0 * damp * clamped_intensity
            angles["leg_upper_right"] = -20.0 * damp * clamped_intensity
            angles["leg_lower_right"] = 35.0 * damp * clamped_intensity

            # Arms settle down
            angles["sleeve_upper_left"] = 60.0 * damp * clamped_intensity
            angles["sleeve_lower_left"] = 15.0 * damp * clamped_intensity
            angles["sleeve_upper_right"] = 60.0 * damp * clamped_intensity
            angles["sleeve_lower_right"] = 15.0 * damp * clamped_intensity

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


