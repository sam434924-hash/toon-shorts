"""
Purpose: Rapid offline mock rendering plugin generating valid image frames.
Inputs: Scene definitions, characters, and destination paths.
Outputs: Valid minimal 1080x1920 PNG images for smoke tests.
Depends on: PIL, core.config, core.models, core.registry, pathlib, typing
Used by: None
Config keys: VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/contract/test_render_contract.py, tests/smoke/test_smoke_pipeline.py
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image

from toonshorts.core import config
from toonshorts.core.models import ScriptPlan, Scene, Character
from toonshorts.core.registry import RenderInterface, register_renderer


@register_renderer("fake")
class FakeRenderPlugin(RenderInterface):
    """Fast in-memory mock renderer creating lightweight 1080x1920 PNG images."""
    name = "fake"

    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        img = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=(240, 230, 220))
        img.save(output_path, "PNG")
        return output_path

    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
    ) -> List[Path]:
        results = []
        for scene in plan.scenes:
            out_path = temp_dir / f"fake_scene_{scene.scene_number}.png"
            self.render_scene(scene, plan.characters, style_preset, out_path, temp_dir)
            results.append(out_path)
        return results
