"""Unit tests for dynamic inventory discovery."""

import json
from pathlib import Path
import pytest
from toonshorts.inventory import (
    get_inventory,
    get_installed_characters,
    get_installed_styles,
    get_installed_board_animations,
    get_installed_voices,
    get_installed_camera_options,
    get_installed_props_and_backgrounds,
    format_inventory_display,
)


def test_inventory_returns_all_required_sections():
    inv = get_inventory()
    assert isinstance(inv, dict)
    for section in ["characters", "styles", "board_animations", "voices", "camera_options", "props_and_backgrounds"]:
        assert section in inv, f"Missing section '{section}' in inventory"


def test_characters_discovery():
    chars = get_installed_characters()
    assert "2d_packs" in chars
    assert "3d_models" in chars
    assert "procedural" in chars
    pack_ids = [p["id"] for p in chars["2d_packs"]]
    assert "presenter" in pack_ids
    assert "boy_a" in pack_ids
    assert "boy_b" in pack_ids
    assert "girl_a" in pack_ids
    assert "stick_hoodie" in pack_ids

    # Check that stick_hoodie is detected as sliced pack
    stick_pack = next(p for p in chars["2d_packs"] if p["id"] == "stick_hoodie")
    assert "sliced pack" in stick_pack["name"] or stick_pack["pack_type"] == "sliced pack"

    # Check Cairo stickman is detected under procedural
    proc_names = [p["name"] for p in chars["procedural"]]
    assert "Cairo stickman" in proc_names


def test_format_inventory_contains_all_required_characters():
    output = format_inventory_display()
    assert "presenter" in output
    assert "boy_a" in output
    assert "boy_b" in output
    assert "girl_a" in output
    assert "stick_hoodie sliced pack" in output
    assert "Cairo stickman" in output


def test_dynamic_new_pack_in_temp_assets_without_code_changes(tmp_path):
    temp_chars_dir = tmp_path / "temp_characters"
    temp_chars_dir.mkdir(parents=True)

    # Place a brand new character pack in temp assets folder
    new_pack = temp_chars_dir / "astronaut_sam"
    new_pack.mkdir()
    manifest_data = {
        "character_name": "astronaut_sam",
        "description": "Space explorer in reflective helmet",
        "slots": ["suit", "helmet"],
    }
    (new_pack / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (new_pack / "vector").mkdir()

    # Discover characters pointing to temp directory
    discovered = get_installed_characters(characters_2d_dir=temp_chars_dir)
    discovered_ids = [p["id"] for p in discovered["2d_packs"]]
    assert "astronaut_sam" in discovered_ids
    found_pack = next(p for p in discovered["2d_packs"] if p["id"] == "astronaut_sam")
    assert "Space explorer" in found_pack["description"]

    # Also test via get_inventory
    inv = get_inventory(characters_2d_dir=temp_chars_dir)
    assert any(p["id"] == "astronaut_sam" for p in inv["characters"]["2d_packs"])


def test_styles_discovery():
    styles = get_installed_styles()
    style_ids = [s["id"] for s in styles]
    assert "whiteboard" in style_ids
    assert "stickman" in style_ids
    assert "chalkboard" in style_ids


def test_board_animations_discovery():
    anims = get_installed_board_animations()
    assert "visual_templates" in anims
    assert "sketch_annotations" in anims
    templates = anims["visual_templates"]
    assert "flow" in templates
    assert "typed_code" in templates
    assert "request_response" in templates


def test_voices_discovery():
    voices = get_installed_voices()
    assert "engines" in voices
    assert "gemini_voices" in voices
    assert "Kore" in voices["gemini_voices"]
    assert "Puck" in voices["gemini_voices"]
    assert "piper" in voices["engines"]
    assert "windows_sapi" in voices["engines"]


def test_camera_options_discovery():
    cams = get_installed_camera_options()
    assert "framing_modes" in cams
    framing_ids = [f["id"] for f in cams["framing_modes"]]
    assert "zoom_speaker" in framing_ids
    assert "fixed" in framing_ids
    assert "motion_plugins" in cams
    assert "ffmpeg" in cams["motion_plugins"]


def test_props_and_backgrounds_discovery():
    pb = get_installed_props_and_backgrounds()
    assert "props" in pb
    assert "backgrounds" in pb
    assert any("laptop" in p for p in pb["props"])
    assert any("studio_room" in b for b in pb["backgrounds"])
