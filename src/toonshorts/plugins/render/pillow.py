"""
Purpose: Procedural stickman rendering engine implemented in Pillow.
Inputs: Scene action, character poses, and style palette presets.
Outputs: Generated 1080x1920 PNG story frame images.
Depends on: PIL, core.config, core.models, core.registry, math, pathlib, typing
Used by: None
Config keys: VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/contract/test_render_contract.py
"""

import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw

from toonshorts.core import config
from toonshorts.core.models import ScriptPlan, Scene, Character, Pose
from toonshorts.core.registry import RenderInterface, register_renderer


def _hex_to_rgb(hex_str: str, default: tuple = (30, 30, 30)) -> tuple:
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 6:
        return tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
    return default


def _draw_stick_figure(
    draw: ImageDraw.ImageDraw,
    x: int,
    ground_y: int,
    char: Character,
    pose: Pose,
    is_speaking: bool,
    palette: dict,
):
    line_color = _hex_to_rgb(palette.get("line", "#1A1A1A"))
    accent_color = _hex_to_rgb(palette.get("accent", "#E63946"))
    secondary_color = _hex_to_rgb(palette.get("secondary", "#457B9D"))

    head_radius = 55
    torso_length = 180
    leg_length = 200
    arm_length = 160

    y_offset = -120 if pose == Pose.JUMPING else 0
    hip_y = ground_y - leg_length + y_offset
    neck_y = hip_y - torso_length
    head_center_y = neck_y - head_radius

    # Legs
    if pose == Pose.JUMPING:
        draw.line([(x, hip_y), (x - 50, hip_y + 80), (x - 70, hip_y + 140)], fill=line_color, width=12)
        draw.line([(x, hip_y), (x + 50, hip_y + 80), (x + 70, hip_y + 140)], fill=line_color, width=12)
    elif pose == Pose.SHOCKED:
        draw.line([(x, hip_y), (x - 20, hip_y + 100), (x - 60, ground_y)], fill=line_color, width=12)
        draw.line([(x, hip_y), (x + 20, hip_y + 100), (x + 60, ground_y)], fill=line_color, width=12)
    else:
        draw.line([(x, hip_y), (x - 50, ground_y)], fill=line_color, width=12)
        draw.line([(x, hip_y), (x + 50, ground_y)], fill=line_color, width=12)

    # Torso
    draw.line([(x, neck_y), (x, hip_y)], fill=line_color, width=14)

    # Arms
    shoulder_y = neck_y + 35
    if pose == Pose.WAVING:
        draw.line([(x, shoulder_y), (x - 70, shoulder_y - 60), (x - 100, shoulder_y - 130)], fill=line_color, width=12)
        draw.arc([x - 140, shoulder_y - 170, x - 70, shoulder_y - 100], start=180, end=330, fill=accent_color, width=5)
        draw.line([(x, shoulder_y), (x + 55, shoulder_y + 60), (x + 20, hip_y - 10)], fill=line_color, width=12)
    elif pose == Pose.SHOCKED:
        draw.line([(x, shoulder_y), (x - 60, neck_y - 20), (x - 45, head_center_y)], fill=line_color, width=12)
        draw.line([(x, shoulder_y), (x + 60, neck_y - 20), (x + 45, head_center_y)], fill=line_color, width=12)
        for angle in (-45, 0, 45):
            rad = math.radians(angle - 90)
            draw.line([(x + int((head_radius + 15) * math.cos(rad)), head_center_y + int((head_radius + 15) * math.sin(rad))),
                       (x + int((head_radius + 45) * math.cos(rad)), head_center_y + int((head_radius + 45) * math.sin(rad)))], fill=accent_color, width=6)
    elif pose == Pose.JUMPING:
        draw.line([(x, shoulder_y), (x - 80, shoulder_y - 90)], fill=line_color, width=12)
        draw.line([(x, shoulder_y), (x + 80, shoulder_y - 90)], fill=line_color, width=12)
    elif pose == Pose.LAUGHING:
        draw.line([(x, shoulder_y), (x - 60, shoulder_y + 70), (x - 15, hip_y - 30)], fill=line_color, width=12)
        draw.line([(x, shoulder_y), (x + 60, shoulder_y + 70), (x + 15, hip_y - 30)], fill=line_color, width=12)
    else:
        draw.line([(x, shoulder_y), (x - 45, shoulder_y + arm_length)], fill=line_color, width=12)
        draw.line([(x, shoulder_y), (x + 45, shoulder_y + arm_length)], fill=line_color, width=12)

    # Head
    draw.ellipse([x - head_radius, head_center_y - head_radius, x + head_radius, head_center_y + head_radius], fill=(255, 255, 255), outline=line_color, width=12)

    # Face
    eye_y = head_center_y - 12
    if pose == Pose.SHOCKED:
        draw.ellipse([x - 28, eye_y - 14, x - 10, eye_y + 10], fill=line_color)
        draw.ellipse([x + 10, eye_y - 14, x + 28, eye_y + 10], fill=line_color)
        draw.ellipse([x - 15, head_center_y + 12, x + 15, head_center_y + 38], fill=accent_color, outline=line_color, width=4)
    elif pose == Pose.LAUGHING:
        draw.arc([x - 30, eye_y - 10, x - 10, eye_y + 10], start=200, end=340, fill=line_color, width=6)
        draw.arc([x + 10, eye_y - 10, x + 30, eye_y + 10], start=200, end=340, fill=line_color, width=6)
        draw.chord([x - 25, head_center_y + 8, x + 25, head_center_y + 40], start=0, end=180, fill=accent_color, outline=line_color, width=4)
    else:
        draw.ellipse([x - 22, eye_y - 6, x - 12, eye_y + 6], fill=line_color)
        draw.ellipse([x + 12, eye_y - 6, x + 22, eye_y + 6], fill=line_color)
        if is_speaking:
            draw.ellipse([x - 14, head_center_y + 14, x + 14, head_center_y + 32], fill=line_color)
        else:
            draw.arc([x - 20, head_center_y + 8, x + 20, head_center_y + 30], start=30, end=150, fill=line_color, width=5)

    # Accessories
    desc = char.visual_description.lower()
    if "hat" in desc or "top hat" in desc:
        hat_top = head_center_y - head_radius - 65
        brim_y = head_center_y - head_radius + 5
        draw.rectangle([x - 35, hat_top, x + 35, brim_y], fill=secondary_color, outline=line_color, width=6)
        draw.line([(x - 55, brim_y), (x + 55, brim_y)], fill=line_color, width=10)
        draw.rectangle([x - 34, brim_y - 16, x + 34, brim_y], fill=accent_color)
    elif "glass" in desc or "glasses" in desc:
        draw.ellipse([x - 36, eye_y - 18, x - 4, eye_y + 16], outline=accent_color, width=7)
        draw.ellipse([x + 4, eye_y - 18, x + 36, eye_y + 16], outline=accent_color, width=7)
        draw.line([(x - 4, eye_y), (x + 4, eye_y)], fill=accent_color, width=6)
    else:
        draw.polygon([(x - 22, neck_y + 10), (x + 22, neck_y + 26), (x + 22, neck_y + 10), (x - 22, neck_y + 26)], fill=accent_color)


@register_renderer("pillow")
class PillowStickmanRenderPlugin(RenderInterface):
    """Procedural 2D stick figure rendering engine powered by Pillow."""
    supports_scene_audios: bool = False
    supports_fast: bool = False
    name = "pillow"

    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        palette = style_preset.get("color_palette", {})
        bg_color = _hex_to_rgb(palette.get("background", "#FDFBF7"))

        img = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=bg_color)
        draw = ImageDraw.Draw(img)

        ground_y = 1420
        ground_color = (210, 205, 195)
        draw.rectangle([0, ground_y, config.VIDEO_WIDTH, config.VIDEO_HEIGHT], fill=ground_color)
        draw.line([(0, ground_y), (config.VIDEO_WIDTH, ground_y)], fill=(170, 165, 155), width=8)

        num_chars = len(characters)
        positions = [360, 720] if num_chars == 2 else [280, 540, 800]

        for i, char in enumerate(characters):
            pos_x = positions[i % len(positions)]
            is_speaker = (char.name.lower() == scene.speaker.lower())
            char_pose = scene.pose if is_speaker else Pose.IDLE
            _draw_stick_figure(draw, pos_x, ground_y, char, char_pose, is_speaker, palette)

        img.save(output_path, "PNG")
        return output_path

    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
    ) -> List[Path]:
        image_paths = []
        for scene in plan.scenes:
            out_img = temp_dir / f"scene_{scene.scene_number}_visual.png"
            self.render_scene(scene, plan.characters, style_preset, out_img, temp_dir)
            image_paths.append(out_img)
        return image_paths
