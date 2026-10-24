"""
Purpose: Gemini Imagen image generation renderer plugin.
Inputs: Scene action descriptions, character designs, and style presets.
Outputs: High-resolution vertical 9:16 PNG story frames.
Depends on: core.client, core.config, core.library, core.models, core.paths, core.registry, logging, pathlib, typing
Used by: None
Config keys: GEMINI_API_KEY, IMAGE_MODEL_NAME
Tests: tests/contract/test_render_contract.py
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from toonshorts.core import config, paths
from toonshorts.core.models import ScriptPlan, Scene, Character
from toonshorts.core.client import GeminiClientWrapper
from toonshorts.core.registry import RenderInterface, register_renderer
from toonshorts.core.library import (
    compute_element_key,
    find_element,
    save_element_once,
    resolve_theme_tags,
    copy_library_asset,
)

logger = logging.getLogger("toonshorts.plugins.render.gemini")


@register_renderer("gemini")
class GeminiRenderPlugin(RenderInterface):
    """AI image generation renderer powered by Google Imagen."""
    supports_scene_audios: bool = False
    supports_fast: bool = False
    name = "gemini"

    def __init__(self, client: Any = None):
        # API keys loaded strictly from core config
        self.client = client or GeminiClientWrapper()

    def generate_character_reference(
        self,
        character: Character,
        style_preset: Dict[str, Any],
        temp_dir: Path,
    ) -> Path:
        ref_path = temp_dir / f"ref_{character.name.lower()}.png"
        prefix = style_preset.get("image_prompt_prefix", "")
        avoid = ", ".join(style_preset.get("avoid", []))
        prompt = (
            f"{prefix}. Full-body character portrait of {character.name}: {character.visual_description}. "
            f"Neutral standing pose on simple solid studio background, character model sheet, single subject."
        )
        theme_tags = resolve_theme_tags(style_preset.get("name"))
        key = compute_element_key("image", prompt, theme_tags=theme_tags, source="image", animated=False)
        existing = find_element("image", key=key)
        if existing:
            lib_path = paths.LIBRARY_ELEMENTS_DIR / "image" / existing["file_name"]
            copy_library_asset(lib_path, ref_path)
            return ref_path

        img_bytes = self.client.generate_image_with_retry(prompt=prompt, negative_prompt=avoid)
        save_element_once(
            "image",
            key=key,
            file_name=f"ref_{character.name.lower()}_{key[:16]}.png",
            content=img_bytes,
            theme_tags=theme_tags,
            animated=False,
            source="image",
        )
        with open(ref_path, "wb") as f:
            f.write(img_bytes)
        return ref_path

    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        prefix = style_preset.get("image_prompt_prefix", "")
        avoid = ", ".join(style_preset.get("avoid", []))
        char_details = "; ".join([f"{c.name}: {c.visual_description}" for c in characters])

        prompt = (
            f"{prefix}. Vertical 9:16 story frame. Action: {scene.action}. "
            f"Active speaker: {scene.speaker} with {scene.pose} pose. "
            f"Characters present: {char_details}. "
            f"Maintain consistent character designs matching the character reference sheets."
        )
        theme_tags = resolve_theme_tags(style_preset.get("name"))
        key = compute_element_key("image", prompt, theme_tags=theme_tags, source="image", animated=False)
        existing = find_element("image", key=key)
        if existing:
            lib_path = paths.LIBRARY_ELEMENTS_DIR / "image" / existing["file_name"]
            copy_library_asset(lib_path, output_path)
            return output_path

        img_bytes = self.client.generate_image_with_retry(prompt=prompt, negative_prompt=avoid)
        save_element_once(
            "image",
            key=key,
            file_name=f"scene_{scene.scene_number}_{key[:16]}.png",
            content=img_bytes,
            theme_tags=theme_tags,
            animated=False,
            source="image",
        )
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        return output_path

    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
    ) -> List[Path]:
        char_refs: Dict[str, Path] = {}
        for char in plan.characters:
            char_refs[char.name.lower()] = self.generate_character_reference(char, style_preset, temp_dir)

        image_paths = []
        for scene in plan.scenes:
            out_img = temp_dir / f"scene_{scene.scene_number}_visual.png"
            self.render_scene(scene, plan.characters, style_preset, out_img, temp_dir, char_refs)
            image_paths.append(out_img)
        return image_paths
