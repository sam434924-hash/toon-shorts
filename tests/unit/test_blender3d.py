"""Unit tests for Blender 3D rendering plugin (RobotExpressive), Pydantic schemas, and caps."""

import json
import pytest
from pathlib import Path
from pydantic import ValidationError

from toonshorts.core import config
from toonshorts.core.registry import get_renderer
from toonshorts.plugins.render.blender3d import (
    Blender3DRenderPlugin,
    Scene3DDescription,
    ActionTrack,
    Camera3DPreset,
    get_scrubbed_env,
    ROBOT_ACTIONS,
    estimate_render_time,
)


def test_blender3d_plugin_registered():
    """Renderer plugin must be registered in central registry under 'blender3d'."""
    plugin = get_renderer("blender3d")
    assert isinstance(plugin, Blender3DRenderPlugin)
    assert plugin.name == "blender3d"


def test_unknown_action_rejected():
    """Reject unknown action names that are not in the validated action library."""
    with pytest.raises(ValidationError) as exc_info:
        ActionTrack(character_name="Robot", action_name="nonexistent_breakdance_move")
    assert "Unknown action" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Scene3DDescription(action="nonexistent_action")
    assert "Unknown action" in str(exc_info.value)


def test_unknown_field_rejected():
    """Reject unknown parameters in scene description (extra='forbid')."""
    with pytest.raises(ValidationError):
        ActionTrack(character_name="Robot", action_name="wave", malicious_param=123)

    with pytest.raises(ValidationError):
        Scene3DDescription(action="idle", injected_arbitrary_key="forbidden")


def test_out_of_bounds_resolution_rejected():
    """Resolutions exceeding max resolution caps or too small must be rejected."""
    with pytest.raises(ValidationError) as exc:
        Scene3DDescription(resolution=(50, 50))
    assert "out of bounds" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        Scene3DDescription(resolution=(3840, 3840))
    assert "out of bounds" in str(exc.value)


def test_max_duration_cap_rejected():
    """Requested render durations exceeding BLENDER_MAX_SECONDS_PER_RUN must be rejected."""
    # frame_count=700 at 5 fps = 140s (> 120s max limit)
    with pytest.raises(ValidationError) as exc:
        Scene3DDescription(frame_count=700, fps=5)
    assert "exceeds max limit" in str(exc.value)


def test_draft_vs_final_mode_settings():
    """Verify draft mode (540x960 @ 12fps) and final mode (1080x1920 @ 24fps) defaults."""
    draft_scene = Scene3DDescription(mode="draft")
    assert draft_scene.resolution == (config.BLENDER_DRAFT_WIDTH, config.BLENDER_DRAFT_HEIGHT)
    assert draft_scene.fps == config.BLENDER_DRAFT_FPS

    final_scene = Scene3DDescription(mode="final")
    assert final_scene.resolution == (config.BLENDER_FINAL_WIDTH, config.BLENDER_FINAL_HEIGHT)
    assert final_scene.fps == config.BLENDER_FINAL_FPS


def test_estimate_render_time():
    """Render time estimation produces positive non-zero seconds."""
    draft = Scene3DDescription(mode="draft", frame_count=36)
    est = estimate_render_time(draft)
    assert 1.0 <= est <= 20.0


def test_scrubbed_env_removes_secrets(monkeypatch):
    """Subprocess environment must never leak API keys, tokens, or passwords."""
    monkeypatch.setenv("GEMINI_API_KEY", "sensitive_secret_key_123")
    monkeypatch.setenv("MY_AUTH_TOKEN", "super_secret_auth")
    monkeypatch.setenv("USER_PASSWORD", "secret_pass")
    monkeypatch.setenv("PATH", "C:\\Windows\\system32")

    env = get_scrubbed_env()
    assert "GEMINI_API_KEY" not in env
    assert "MY_AUTH_TOKEN" not in env
    assert "USER_PASSWORD" not in env
    assert "PATH" in env


def test_robot_model_preserved():
    """Verify RobotExpressive 3D asset exists and Stickman.blend is removed."""
    stickman_path = config.PROJECT_ROOT / "assets3d" / "models" / "Stickman.blend"
    robot_path = config.PROJECT_ROOT / "assets3d" / "models" / "RobotExpressive.glb"
    assert not stickman_path.exists(), f"Stickman.blend should have been removed: {stickman_path}"
    assert robot_path.is_file(), f"Missing robot asset: {robot_path}"


def test_robot_actions_available():
    """Verify core robot animations are defined in ROBOT_ACTIONS."""
    assert "walking" in ROBOT_ACTIONS
    assert "running" in ROBOT_ACTIONS
    assert "jump" in ROBOT_ACTIONS
    assert "wave" in ROBOT_ACTIONS
    assert "idle" in ROBOT_ACTIONS
    assert "dance" in ROBOT_ACTIONS
    assert "thumbsup" in ROBOT_ACTIONS


def test_stickman_acceptance_renders_exist():
    """Verify stickman acceptance frames are preserved as requested by owner."""
    from PIL import Image

    out_dir = config.PROJECT_ROOT / "output" / "stickman_acceptance"
    expected = [
        "tpose.png",
        "walking_01.png", "walking_02.png", "walking_03.png",
        "running_01.png", "running_02.png", "running_03.png",
        "jump_01.png", "jump_02.png", "jump_03.png",
        "wave_01.png", "wave_02.png", "wave_03.png",
    ]
    for fname in expected:
        img_path = out_dir / fname
        assert img_path.is_file(), f"Missing acceptance frame: {img_path}"
        with Image.open(img_path) as img:
            assert img.size == (540, 960)
            assert img.format == "PNG"


def test_stickman_pixel_differences_recorded():
    """Verify pixel_diffs.json proves non-zero motion between frames and actions."""
    diff_file = config.PROJECT_ROOT / "output" / "stickman_acceptance" / "pixel_diffs.json"
    assert diff_file.is_file(), f"Missing diff file: {diff_file}"

    with open(diff_file, "r", encoding="utf-8") as f:
        diffs = json.load(f)

    for action in ["walking", "running", "jump", "wave"]:
        assert action in diffs
        assert diffs[action]["delta_1_2"] > 1.0, f"No motion detected in {action} delta_1_2"
        assert diffs[action]["delta_2_3"] > 1.0, f"No motion detected in {action} delta_2_3"
        assert diffs[action]["frame_1_vs_tpose"] > 1.0
