"""
Purpose: Dynamic asset and plugin inventory discovery without hardcoded lists.
Inputs: File system directories for packs, styles, plugins, voices, and assets.
Outputs: Formatted inventory output for CLI and structured dictionary.
Depends on: json, pathlib, sys, typing, core.config, core.models, core.paths, core.registry, core.visuals, plugins
Used by: brief, cli
Config keys: GEMINI_VOICES, PIPER_VOICES_DIR, STYLES_DIR, VOICES_REGISTRY_PATH
Tests: tests/unit/test_inventory.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure package plugins are registered
import toonshorts.plugins  # noqa: F401
from toonshorts.core import config, paths
from toonshorts.core.models import CameraMove
from toonshorts.core.registry import list_llms, list_motions, list_renderers, list_voices, get_renderer
from toonshorts.core.visuals import ALLOWED_VISUAL_TYPES


def get_installed_characters(
    characters_2d_dir: Optional[Path] = None,
    models_3d_dir: Optional[Path] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """Dynamically inspects character asset directories and procedural renderer capabilities with honest load validation."""
    result: Dict[str, List[Dict[str, str]]] = {
        "2d_packs": [],
        "broken_packs": [],
        "procedural": [],
        "3d_models": [],
    }

    char_2d_dir = characters_2d_dir or paths.CHARACTERS_2D_DIR
    if char_2d_dir.is_dir():
        for item in sorted(char_2d_dir.iterdir()):
            if item.is_dir() and not item.name.startswith((".", "_")):
                from toonshorts.core.character2d import get_character, Character2D
                from toonshorts.core.character_pack import CharacterPack

                char_obj = get_character(item.name, base_dir=char_2d_dir)

                if isinstance(char_obj, CharacterPack):
                    validation_errors = char_obj.validate()
                    if validation_errors:
                        result["broken_packs"].append({
                            "id": item.name,
                            "reason": f"Validation failed: {validation_errors[0]}",
                        })
                    else:
                        desc = char_obj.manifest.get("description") or f"2D vector pack ({char_obj.name})"
                        result["2d_packs"].append({
                            "id": item.name,
                            "name": item.name,
                            "pack_type": "vector pack",
                            "description": desc,
                        })
                elif isinstance(char_obj, Character2D):
                    desc = f"2D sliced pack ({char_obj.name})"
                    result["2d_packs"].append({
                        "id": item.name,
                        "name": f"{item.name} sliced pack",
                        "pack_type": "sliced pack",
                        "description": desc,
                    })
                elif isinstance(char_obj, dict) and char_obj.get("status") in ("error", "missing"):
                    result["broken_packs"].append({
                        "id": item.name,
                        "reason": char_obj.get("message", "Failed to load character pack"),
                    })
                else:
                    msg = char_obj.get("message") if isinstance(char_obj, dict) else "Unknown character format"
                    result["broken_packs"].append({
                        "id": item.name,
                        "reason": msg,
                    })

    # Procedural characters provided dynamically by renderer engines
    for r in list_renderers():
        try:
            rend = get_renderer(r)
            doc = type(rend).__doc__ or ""
        except Exception:
            doc = ""
        if "stickman" in doc.lower() or "stick figure" in doc.lower():
            char_title = f"{r.capitalize()} stickman"
            result["procedural"].append({
                "id": f"{r}_stickman",
                "name": char_title,
                "description": f"Procedural vector character ({char_title} via {r} renderer)",
            })

    models_dir = models_3d_dir or paths.MODELS_3D_DIR
    if models_dir.is_dir():
        for item in sorted(models_dir.iterdir()):
            if item.is_file() and item.suffix.lower() in (".glb", ".gltf", ".blend"):
                result["3d_models"].append({
                    "id": item.stem,
                    "name": item.stem,
                    "file": item.name,
                    "description": f"3D model ({item.name})",
                })

    return result


def get_installed_styles() -> List[Dict[str, Any]]:
    """Dynamically reads style presets from STYLES_DIR."""
    styles: List[Dict[str, Any]] = []
    styles_dir = config.STYLES_DIR
    if styles_dir.is_dir():
        for file in sorted(styles_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                styles.append({
                    "id": file.stem,
                    "name": data.get("name", file.stem),
                    "renderer": data.get("renderer", "auto"),
                    "voice": data.get("voice", "auto"),
                    "pacing": data.get("pacing", "moderate"),
                    "prompt_prefix": data.get("image_prompt_prefix", "")[:60],
                })
            except Exception:
                styles.append({"id": file.stem, "name": file.stem, "renderer": "unknown"})
    return styles


def get_installed_board_animations() -> Dict[str, List[str]]:
    """Reads available whiteboard visual animations and annotations."""
    visual_templates = sorted(list(ALLOWED_VISUAL_TYPES))
    sketch_annotations = ["underline", "circle", "arrow", "bullet_cards", "title_badge"]
    graphics_plugins_list: List[str] = []
    try:
        from toonshorts.plugins.graphics import list_graphics_plugins
        graphics_plugins_list = list_graphics_plugins()
    except Exception:
        pass

    return {
        "visual_templates": visual_templates,
        "sketch_annotations": sketch_annotations,
        "graphics_plugins": graphics_plugins_list,
    }


def get_installed_voices() -> Dict[str, Any]:
    """Dynamically discovers voice engines, cloud voices, and installed local voices."""
    engines = list_voices()
    gemini_voices = list(config.GEMINI_VOICES)

    piper_models: List[str] = []
    if config.PIPER_VOICES_DIR.is_dir():
        for onnx_file in sorted(config.PIPER_VOICES_DIR.glob("*.onnx")):
            piper_models.append(onnx_file.stem)

    registry_voices: List[Dict[str, str]] = []
    if config.VOICES_REGISTRY_PATH.is_file():
        try:
            data = json.loads(config.VOICES_REGISTRY_PATH.read_text(encoding="utf-8"))
            for v in data.get("voices", []):
                registry_voices.append({
                    "name": v.get("name", ""),
                    "engine": v.get("engine", ""),
                    "license": v.get("license", "unknown"),
                })
        except Exception:
            pass

    return {
        "engines": engines,
        "gemini_voices": gemini_voices,
        "piper_models": piper_models,
        "registered_voices": registry_voices,
    }


def get_installed_camera_options() -> Dict[str, Any]:
    """Returns camera options, whiteboard framing modes, and motion plugins."""
    framing_modes = [
        {"id": "zoom_speaker", "name": "Zoom on speaker (ease in to medium close-up, hold, ease out)"},
        {"id": "fixed", "name": "Fixed / Wide shot (both characters fully visible, static)"},
    ]
    camera_moves = [m.value for m in CameraMove]
    motion_plugins = list_motions()
    return {
        "framing_modes": framing_modes,
        "camera_moves": camera_moves,
        "motion_plugins": motion_plugins,
    }


def get_installed_props_and_backgrounds() -> Dict[str, List[str]]:
    """Returns available props and room backgrounds."""
    props = [
        "desk_laptop (Modern laptop with syntax lines on desk)",
        "desk_mug (Ceramic navy coffee mug with steam on desk)",
        "wall_shelf (Floating studio shelf with ivy plant and books)",
    ]
    custom_props_dir = paths.ASSETS_DIR / "props"
    if custom_props_dir.is_dir():
        for p in sorted(custom_props_dir.iterdir()):
            if not p.name.startswith((".", "_")):
                props.append(f"custom:{p.name}")

    backgrounds = [
        "studio_room (Modern studio room with whiteboard, wall shelf, desk)",
    ]
    custom_bg_dir = paths.ASSETS_DIR / "backgrounds"
    if custom_bg_dir.is_dir():
        for bg in sorted(custom_bg_dir.iterdir()):
            if not bg.name.startswith((".", "_")):
                backgrounds.append(f"custom:{bg.name}")

    styles_dir = config.STYLES_DIR
    if styles_dir.is_dir():
        for sf in sorted(styles_dir.glob("*.json")):
            backgrounds.append(f"style_theme:{sf.stem}")

    return {
        "props": props,
        "backgrounds": backgrounds,
    }


def get_inventory(
    characters_2d_dir: Optional[Path] = None,
    models_3d_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Assembles complete dynamic inventory from real plugin/pack folders."""
    return {
        "characters": get_installed_characters(characters_2d_dir=characters_2d_dir, models_3d_dir=models_3d_dir),
        "styles": get_installed_styles(),
        "board_animations": get_installed_board_animations(),
        "voices": get_installed_voices(),
        "camera_options": get_installed_camera_options(),
        "props_and_backgrounds": get_installed_props_and_backgrounds(),
        "plugins": {
            "llm": list_llms(),
            "voice": list_voices(),
            "render": list_renderers(),
            "motion": list_motions(),
        },
    }


def format_inventory_display(inv: Optional[Dict[str, Any]] = None) -> str:
    """Formats inventory into a human-readable CLI summary."""
    if inv is None:
        inv = get_inventory()

    lines: List[str] = [
        "=======================================================",
        "            TOON-SHORTS INSTALLED INVENTORY            ",
        "=======================================================",
        "",
        "1. CHARACTERS & PACKS:",
    ]
    chars = inv.get("characters", {})
    for pack in chars.get("2d_packs", []):
        display_label = pack.get("name", pack["id"])
        lines.append(f"   - [2D {pack.get('pack_type', 'Pack').title()}] {display_label}: {pack['description']}")
    for proc in chars.get("procedural", []):
        lines.append(f"   - [Procedural] {proc['name']}: {proc['description']}")
    for model in chars.get("3d_models", []):
        lines.append(f"   - [3D Model] {model['id']} ({model.get('file', '')})")
    for broken in chars.get("broken_packs", []):
        lines.append(f"   - [Broken Pack] {broken['id']}: {broken['reason']}")

    lines.append("")
    lines.append("2. BOARD THEMES / STYLES:")
    for style in inv.get("styles", []):
        lines.append(f"   - {style['id']} (renderer: {style.get('renderer')}, voice: {style.get('voice')})")

    lines.append("")
    lines.append("3. BOARD ANIMATIONS:")
    anims = inv.get("board_animations", {})
    lines.append(f"   - Visual Templates: {', '.join(anims.get('visual_templates', []))}")
    lines.append(f"   - Sketch Annotations: {', '.join(anims.get('sketch_annotations', []))}")

    lines.append("")
    lines.append("4. VOICES:")
    voices = inv.get("voices", {})
    lines.append(f"   - Voice Engines: {', '.join(voices.get('engines', []))}")
    lines.append(f"   - Gemini Prebuilt Voices: {', '.join(voices.get('gemini_voices', []))}")
    if voices.get("piper_models"):
        lines.append(f"   - Piper Local Voices: {', '.join(voices.get('piper_models', []))}")
    sapi_names = [v["name"] for v in voices.get("registered_voices", []) if v.get("engine") == "windows_sapi"]
    if sapi_names:
        lines.append(f"   - Windows SAPI Voices: {', '.join(sapi_names)}")

    lines.append("")
    lines.append("5. CAMERA & MOTION OPTIONS:")
    cam = inv.get("camera_options", {})
    for fm in cam.get("framing_modes", []):
        lines.append(f"   - {fm['id']}: {fm['name']}")
    lines.append(f"   - Camera Moves: {', '.join(cam.get('camera_moves', []))}")
    lines.append(f"   - Motion Plugins: {', '.join(cam.get('motion_plugins', []))}")

    lines.append("")
    lines.append("6. PROPS & BACKGROUNDS:")
    pb = inv.get("props_and_backgrounds", {})
    lines.append("   - Props:")
    for prop in pb.get("props", []):
        lines.append(f"     * {prop}")
    lines.append("   - Backgrounds:")
    for bg in pb.get("backgrounds", []):
        lines.append(f"     * {bg}")

    lines.append("")
    lines.append("=======================================================")
    return "\n".join(lines)


def main():
    if "--json" in sys.argv:
        print(json.dumps(get_inventory(), indent=2))
    else:
        print(format_inventory_display())


if __name__ == "__main__":
    main()
