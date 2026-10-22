"""
Purpose: Unit tests for new 2D full-body layered character packs (boy_b and girl_a).
Inputs: Assets in assets/sources/ and assets2d/characters/<id>/
Outputs: Test assertions for layer integrity, manifest schema, and preview sheet rendering.
Depends on: json, pathlib, pytest, PIL, core.config, core.character_pack, core.character2d
Used by: Test suite
"""

import json
from pathlib import Path
import pytest
from PIL import Image

from toonshorts.core.config import PROJECT_ROOT
from toonshorts.core.character_pack import validate_manifest_schema
from toonshorts.core.character2d import Character2D


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_character_pack_structure_and_manifest(char_id):
    """Verifies that the character pack exists with a valid manifest and character.json."""
    pack_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id
    assert pack_dir.is_dir(), f"Missing character pack directory: {pack_dir}"

    manifest_file = pack_dir / "manifest.json"
    assert manifest_file.is_file(), f"Missing manifest.json in {pack_dir}"

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Manifest schema validation
    errors = validate_manifest_schema(manifest)
    assert errors == [], f"Manifest validation errors for {char_id}: {errors}"

    assert manifest["id"] == char_id
    assert manifest["kind"] == "raster"
    assert manifest["type"] == "layered"

    # 2. Check required pivots
    pivots = manifest.get("pivots", {})
    required_pivots = [
        "neck", "head",
        "shoulder_left", "shoulder_right",
        "elbow_left", "elbow_right",
        "hip_left", "hip_right",
        "knee_left", "knee_right",
        "ankle_left", "ankle_right",
    ]
    for p in required_pivots:
        assert p in pivots, f"Missing pivot '{p}' in {char_id} manifest"
        assert len(pivots[p]) == 2

    # 3. Check z_order and head_position
    assert "z_order" in manifest
    assert "head_position" in manifest
    assert len(manifest["head_position"]) == 2

    # 4. Character2D skeletal loading
    char_json_file = pack_dir / "character.json"
    assert char_json_file.is_file()
    char2d = Character2D.from_json(char_json_file)
    assert char2d.name == char_id
    assert len(char2d.parts) >= 11


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_character_pack_layers_integrity(char_id):
    """Verifies that all 22 transparent layers exist and are valid RGBA images."""
    layers_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id / "layers"
    assert layers_dir.is_dir()

    expected_layers = [
        "head_base.png",
        "head_back.png",
        "eyes_open.png",
        "eyes_blink.png",
        "eyes_look_left.png",
        "eyes_look_right.png",
        "mouth_closed.png",
        "mouth_slightly_open.png",
        "mouth_wide_open.png",
        "mouth_round_o.png",
        "mouth_open_smile.png",
        "torso.png",
        "arm_upper_left.png",
        "arm_lower_left.png",
        "arm_upper_right.png",
        "arm_lower_right.png",
        "leg_upper_left.png",
        "leg_lower_left.png",
        "shoe_left.png",
        "leg_upper_right.png",
        "leg_lower_right.png",
        "shoe_right.png",
    ]

    for layer_name in expected_layers:
        layer_path = layers_dir / layer_name
        assert layer_path.is_file(), f"Missing layer file: {layer_path}"

        with Image.open(layer_path) as img:
            assert img.mode == "RGBA", f"Layer {layer_name} is not RGBA: {img.mode}"
            # Check transparency (alpha channel exists and is not entirely 0 or 255)
            alpha = img.split()[3]
            extrema = alpha.getextrema()
            assert extrema[0] < 255, f"Layer {layer_name} has no transparency: {extrema}"
            assert extrema[1] > 0, f"Layer {layer_name} is completely invisible: {extrema}"


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_character_preview_sheets_exist(char_id):
    """Verifies staging preview poses and contact sheets exist for review."""
    staging_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id / "staging"
    assert staging_dir.is_dir()

    contact_sheet = staging_dir / f"{char_id}_preview_sheet.png"
    assert contact_sheet.is_file(), f"Missing preview sheet: {contact_sheet}"

    required_poses = [
        "pose_01_front_standing.png",
        "pose_02_mouth_slightly_open.png",
        "pose_03_mouth_wide_open.png",
        "pose_04_mouth_round_o.png",
        "pose_05_mouth_open_smile.png",
        "pose_06_eyes_blink.png",
        "pose_07_eyes_look_left.png",
        "pose_08_eyes_look_right.png",
        "pose_09_arm_raised.png",
        "pose_10_walking_swing.png",
        "pose_11_back_view.png",
    ]
    for pose_name in required_poses:
        pose_path = staging_dir / pose_name
        assert pose_path.is_file(), f"Missing pose render: {pose_path}"


def test_sources_preserved():
    """Verifies original sources are saved in assets/sources."""
    sources_dir = PROJECT_ROOT / "assets" / "sources"
    expected_sources = [
        "boy_b_body.png",
        "boy_b_face.jpg",
        "girl_a_body.png",
        "girl_a_face.jpg",
        "hands_sheet.png",
        "hands_sheet_lr.png",
    ]
    for src in expected_sources:
        p = sources_dir / src
        assert p.is_file(), f"Missing source file: {p}"
