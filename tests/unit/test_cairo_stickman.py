"""Unit tests for the 2D stickman Pycairo rendering engine."""

from pathlib import Path
import math
import cairo
import pytest

from toonshorts.plugins.render.cairo import (
    CairoStickmanRenderPlugin,
    EyebrowState,
    MouthShape,
    ActionType,
    SkeletonPose,
    GarmentLayer,
    compute_action_pose,
    draw_stickman_skeleton,
    draw_handdrawn_background,
    draw_feet_shadow,
)
from toonshorts.core.models import Scene, Character, Pose, CameraMove, Transition


def test_eyebrow_and_mouth_states(tmp_path):
    """Verifies that all eyebrow states and mouth shapes render cleanly."""
    plugin = CairoStickmanRenderPlugin()
    preset = {
        "color_palette": {
            "background": "#FDFBF7",
            "line": "#1A1A1A",
            "character_body": "#FFFFFF",
            "character_shoe": "#2B2D42",
            "accent": "#E63946",
        }
    }

    for eyebrow in [EyebrowState.NEUTRAL, EyebrowState.RAISED, EyebrowState.ANGRY, EyebrowState.SAD]:
        for mouth in [MouthShape.CLOSED, MouthShape.OPEN, MouthShape.WIDE, MouthShape.ROUND]:
            pose = SkeletonPose(
                root_x=540.0,
                root_y=1140.0,
                eyebrow_state=eyebrow,
                mouth_shape=mouth,
                blink=False,
            )
            surface = plugin.render_frame_to_surface(pose, lift_height=0.0, style_preset=preset)
            out_file = tmp_path / f"face_{eyebrow.value}_{mouth.value}.png"
            surface.write_to_png(str(out_file))
            assert out_file.is_file()
            assert out_file.stat().st_size > 0


def test_blink_toggle(tmp_path):
    """Verifies blink rendering toggle."""
    plugin = CairoStickmanRenderPlugin()
    preset = {"color_palette": {"line": "#1A1A1A", "character_body": "#FFFFFF", "accent": "#E63946"}}

    pose_open = SkeletonPose(root_x=540.0, root_y=1140.0, blink=False)
    pose_blink = SkeletonPose(root_x=540.0, root_y=1140.0, blink=True)

    surf_open = plugin.render_frame_to_surface(pose_open, lift_height=0.0, style_preset=preset)
    surf_blink = plugin.render_frame_to_surface(pose_blink, lift_height=0.0, style_preset=preset)

    p_open = tmp_path / "eye_open.png"
    p_blink = tmp_path / "eye_blink.png"
    surf_open.write_to_png(str(p_open))
    surf_blink.write_to_png(str(p_blink))

    assert p_open.is_file() and p_blink.is_file()
    # Different pixel data
    assert p_open.stat().st_size != p_blink.stat().st_size or p_open.read_bytes() != p_blink.read_bytes()


def test_action_intensity_clamping():
    """Verifies intensity settings are clamped strictly to [0.5, 1.5]."""
    # Under min: 0.1 should clamp to 0.5
    pose_low, _ = compute_action_pose(ActionType.WALK, time_sec=0.25, intensity=0.1)
    pose_exact_low, _ = compute_action_pose(ActionType.WALK, time_sec=0.25, intensity=0.5)
    assert math.isclose(pose_low.hip_l_angle, pose_exact_low.hip_l_angle, rel_tol=1e-5)

    # Over max: 2.5 should clamp to 1.5
    pose_high, _ = compute_action_pose(ActionType.WALK, time_sec=0.25, intensity=2.5)
    pose_exact_high, _ = compute_action_pose(ActionType.WALK, time_sec=0.25, intensity=1.5)
    assert math.isclose(pose_high.hip_l_angle, pose_exact_high.hip_l_angle, rel_tol=1e-5)


def test_jump_squash_and_stretch():
    """Verifies squash and stretch behavior through jump animation cycle."""
    # Crouch phase (t = 0.1): squashed (squash_y < 1.0, squash_x > 1.0)
    pose_crouch, _ = compute_action_pose(ActionType.JUMP, time_sec=0.10, speed=1.0, intensity=1.0)
    assert pose_crouch.squash_y < 1.0
    assert pose_crouch.squash_x > 1.0
    assert math.isclose(pose_crouch.squash_x * math.sqrt(pose_crouch.squash_y), 1.0, rel_tol=1e-4)

    # Launch phase (t = 0.25): stretched (squash_y > 1.0, squash_x < 1.0)
    pose_launch, lift = compute_action_pose(ActionType.JUMP, time_sec=0.25, speed=1.0, intensity=1.0)
    assert pose_launch.squash_y > 1.0
    assert pose_launch.squash_x < 1.0
    assert lift > 0.0


def test_garment_attachment_layering():
    """Verifies that garments can be attached to skeleton slots as extra drawn layers."""
    called_slots = []

    def mock_hat_draw(ctx, length, radius, extra):
        called_slots.append("head_hat")

    def mock_sleeve_draw(ctx, length, radius, extra):
        called_slots.append("arm_sleeve")

    pose = SkeletonPose(root_x=540.0, root_y=1140.0)
    pose.garments.append(GarmentLayer(slot="head", name="top_hat", z_order=1, render_fn=mock_hat_draw))
    pose.garments.append(GarmentLayer(slot="upper_arm_l", name="sleeve", z_order=1, render_fn=mock_sleeve_draw))

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1080, 1920)
    ctx = cairo.Context(surface)
    draw_stickman_skeleton(ctx, pose, {})

    assert "head_hat" in called_slots
    assert "arm_sleeve" in called_slots


def test_scene_render_pipeline_integration(tmp_path):
    """Verifies full scene render pipeline integration with Scene and Character models."""
    plugin = CairoStickmanRenderPlugin()
    char1 = Character(name="Pip", visual_description="Minimalist black line stickman")
    char2 = Character(name="Zack", visual_description="Stickman with blue accents")
    scene = Scene(
        scene_number=1,
        speaker="Pip",
        dialogue_line="Testing 2D stickman rendering pipeline.",
        action="Waves enthusiastically",
        pose=Pose.WAVING,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )
    preset = {
        "color_palette": {
            "background": "#FDFBF7",
            "line": "#1A1A1A",
            "character_body": "#FFFFFF",
            "character_shoe": "#2B2D42",
            "accent": "#E63946",
        }
    }
    out_file = tmp_path / "scene_test.png"
    result = plugin.render_scene(scene, [char1, char2], preset, out_file, tmp_path)
    assert result.is_file()
    assert result.stat().st_size > 5000  # valid image file
