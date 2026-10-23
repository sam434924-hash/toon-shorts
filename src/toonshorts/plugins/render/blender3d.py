"""
Purpose: 3D Blender headless rendering engine plugin with Pydantic validation and caps.
Inputs: Scene definitions, characters, style presets, and 3D scene parameters.
Outputs: Rendered 9:16 PNG image frames and optional video sequences.
Depends on: PIL, core.config, core.models, core.registry, json, logging, os, pathlib, pydantic, subprocess, typing
Used by: None
Config keys: BLENDER_MAX_FRAMES, BLENDER_MAX_RESOLUTION, BLENDER_MAX_SECONDS_PER_RUN, BLENDER_PATH, BLENDER_RENDER_TIMEOUT_SECONDS
Tests: tests/contract/test_render_contract.py, tests/unit/test_blender3d.py
"""

import json
import logging
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Literal, Optional, Tuple
from PIL import Image
from pydantic import BaseModel, Field, field_validator, model_validator

from toonshorts.core import config, paths
from toonshorts.core.models import Character, Scene, ScriptPlan
from toonshorts.core.registry import RenderInterface, register_renderer

logger = logging.getLogger(__name__)

# Validated actions natively provided by RobotExpressive.glb
ROBOT_ACTIONS = {
    "dance", "death", "idle", "jump", "no", "punch",
    "running", "run", "sitting", "sit", "standing", "stand",
    "thumbsup", "thumbs_up", "walking", "walk", "walkjump", "wave", "yes"
}
KNOWN_ACTIONS = ROBOT_ACTIONS

CameraMoveType = Literal["static", "zoom", "pan", "shake"]


class Camera3DPreset(BaseModel):
    move_type: CameraMoveType = "static"
    start_pos: Tuple[float, float, float] = (0.0, -3.2, 1.1)
    target_pos: Tuple[float, float, float] = (0.0, 0.0, 0.9)
    fov: float = Field(default=50.0, ge=10.0, le=120.0)

    model_config = {"extra": "forbid"}


class ActionTrack(BaseModel):
    character_name: str = Field(..., min_length=1)
    action_name: str
    start_frame: int = Field(default=1, ge=1)

    model_config = {"extra": "forbid"}

    @field_validator("action_name")
    @classmethod
    def validate_action_name(cls, v: str) -> str:
        clean = v.lower().strip()
        if clean not in ROBOT_ACTIONS:
            raise ValueError(f"Unknown action '{v}'. Valid actions: {sorted(ROBOT_ACTIONS)}")
        return clean


class Scene3DDescription(BaseModel):
    action: str = "idle"
    camera: Camera3DPreset = Field(default_factory=Camera3DPreset)
    resolution: Tuple[int, int] = (540, 960)
    fps: int = Field(default=12, ge=1, le=60)
    frame_count: int = Field(default=24, ge=1, le=config.BLENDER_MAX_FRAMES)
    render_single_frame: Optional[int] = None
    mode: Literal["draft", "final"] = "draft"

    model_config = {"extra": "forbid"}

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        clean = v.lower().strip()
        if clean not in ROBOT_ACTIONS:
            raise ValueError(f"Unknown action '{v}'. Valid actions: {sorted(ROBOT_ACTIONS)}")
        return clean

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: Tuple[int, int]) -> Tuple[int, int]:
        w, h = v
        max_w, max_h = config.BLENDER_MAX_RESOLUTION
        if w < 100 or h < 100 or w > max_w or h > max_h:
            raise ValueError(f"Resolution {v} out of bounds (max {config.BLENDER_MAX_RESOLUTION})")
        return v

    @model_validator(mode="after")
    def apply_mode_defaults(self) -> "Scene3DDescription":
        if self.mode == "draft":
            if self.resolution == (1080, 1920):
                self.resolution = (config.BLENDER_DRAFT_WIDTH, config.BLENDER_DRAFT_HEIGHT)
            if self.fps == 24:
                self.fps = config.BLENDER_DRAFT_FPS
        elif self.mode == "final":
            if self.resolution == (540, 960):
                self.resolution = (config.BLENDER_FINAL_WIDTH, config.BLENDER_FINAL_HEIGHT)
            if self.fps == 12:
                self.fps = config.BLENDER_FINAL_FPS

        duration_sec = self.frame_count / float(self.fps)
        if duration_sec > config.BLENDER_MAX_SECONDS_PER_RUN:
            raise ValueError(
                f"Requested render duration {duration_sec:.1f}s exceeds max limit "
                f"of {config.BLENDER_MAX_SECONDS_PER_RUN}s"
            )
        return self


def estimate_render_time(scene_desc: Scene3DDescription) -> float:
    """Estimates render time based on mode, resolution, and frame count."""
    frames = 1 if scene_desc.render_single_frame is not None else scene_desc.frame_count
    rate = 0.08 if scene_desc.mode == "draft" else 0.20
    startup_overhead = 1.5
    return round(startup_overhead + frames * rate, 1)


def confirm_render_gate(estimated_seconds: float, auto_confirm: bool = False) -> bool:
    """Pre-flight confirmation prompt for 3D rendering."""
    print(f"\n[3D Render Pre-flight] Estimated time: ~{estimated_seconds:.1f}s")
    if auto_confirm:
        print("[Auto-Confirm] --yes flag provided. Proceeding with 3D render...")
        return True

    if not os.isatty(0):
        return True

    try:
        ans = input("Proceed with 3D render? [Y/n]: ").strip().lower()
        return ans in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def get_scrubbed_env() -> Dict[str, str]:
    """Returns environment with sensitive API keys and secrets removed."""
    scrubbed = {}
    secret_terms = ("KEY", "SECRET", "TOKEN", "AUTH", "PASSWORD", "CREDENTIAL")
    for k, v in os.environ.items():
        if not any(term in k.upper() for term in secret_terms):
            scrubbed[k] = v
    return scrubbed


@register_renderer("blender3d")
class Blender3DRenderPlugin(RenderInterface):
    """3D robot character renderer using headless Blender subprocesses."""
    supports_scene_audios: bool = False
    supports_fast: bool = False
    name = "blender3d"

    def __init__(self, blender_path: Optional[str] = None):
        self.blender_path = blender_path or config.BLENDER_PATH
        self.script_path = paths.SCRIPTS_3D_DIR / "blender_render.py"
        self.robot_model = paths.MODELS_3D_DIR / "RobotExpressive.glb"

    def _verify_blender_installed(self):
        if not self.blender_path or not Path(self.blender_path).is_file():
            raise RuntimeError(
                f"Blender executable not found at '{self.blender_path}'. "
                "Set BLENDER_PATH in .env to a valid Blender executable."
            )

    def render_3d_scene(
        self,
        scene_desc: Scene3DDescription,
        output_dir: Path,
        auto_confirm: bool = False,
    ) -> List[Path]:
        """Validates payload, enforces caps, prompts confirmation, and renders robot in Blender."""
        self._verify_blender_installed()

        est_sec = estimate_render_time(scene_desc)
        if not confirm_render_gate(est_sec, auto_confirm=auto_confirm):
            raise RuntimeError("Render aborted by user confirmation gate.")

        output_dir.mkdir(parents=True, exist_ok=True)
        temp_json = config.TEMP_DIR / f"scene3d_payload_{os.getpid()}.json"
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)

        payload_dict = scene_desc.model_dump()
        payload_dict["output_dir"] = str(output_dir.resolve())
        payload_dict["frame_prefix"] = "frame"

        temp_json.write_text(json.dumps(payload_dict, indent=2), encoding="utf-8")

        cmd = [
            str(self.blender_path),
            "-b",
            "--python",
            str(self.script_path.resolve()),
            "--",
            str(temp_json.resolve()),
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=get_scrubbed_env(),
                timeout=config.BLENDER_RENDER_TIMEOUT_SECONDS,
            )
            if res.returncode != 0:
                raise RuntimeError(
                    f"Blender process exited with code {res.returncode}.\n"
                    f"Output: {res.stdout[-600:]}\nError: {res.stderr[-300:]}"
                )
        finally:
            if temp_json.exists():
                try:
                    temp_json.unlink()
                except OSError:
                    pass

        frames = sorted(output_dir.glob("frame_*.png"))
        return frames

    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Fulfills RenderInterface contract by rendering a 1080x1920 still frame."""
        pose_action_map = {
            "idle": "idle",
            "talking": "wave",
            "waving": "wave",
            "laughing": "thumbsup",
            "shocked": "no",
            "pointing": "wave",
            "thinking": "sitting",
            "punchline": "thumbsup",
            "jumping": "jump",
        }
        action_name = pose_action_map.get(scene.pose.value.lower(), "idle")

        desc = Scene3DDescription(
            action=action_name,
            resolution=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT),
            fps=24,
            frame_count=24,
            render_single_frame=15,
            mode="final",
        )

        render_tmp = temp_dir / f"scene_{scene.scene_number}_render"
        frames = self.render_3d_scene(desc, render_tmp, auto_confirm=True)

        if not frames:
            img = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=(240, 230, 220))
            img.save(output_path, "PNG")
            return output_path

        rendered_frame = frames[0]
        with Image.open(rendered_frame) as im:
            rgb_im = im.convert("RGB")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            rgb_im.save(output_path, "PNG")

        return output_path

    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
    ) -> List[Path]:
        """Renders still frames for all scenes in the screenplay plan."""
        results = []
        for scene in plan.scenes:
            out_path = temp_dir / f"blender3d_scene_{scene.scene_number}.png"
            self.render_scene(scene, plan.characters, style_preset, out_path, temp_dir)
            results.append(out_path)
        return results
