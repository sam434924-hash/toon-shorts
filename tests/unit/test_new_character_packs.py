"""
Purpose: Unit tests for new 2D full-body layered character packs (boy_b and girl_a).
Inputs: Assets in assets/sources/ and assets/2d/characters/<id>/
Outputs: Test assertions for layer integrity, manifest schema, and preview sheet rendering.
Depends on: json, numpy, pathlib, pytest, PIL, core.config, core.paths, core.character_pack, core.character2d
Used by: Test suite
"""

import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from toonshorts.core import paths
from toonshorts.core.config import PROJECT_ROOT
from toonshorts.core.character_pack import validate_manifest_schema
from toonshorts.core.character2d import Character2D


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_character_pack_structure_and_manifest(char_id):
    """Verifies that the character pack exists with a valid manifest and character.json."""
    pack_dir = paths.CHARACTERS_2D_DIR / char_id
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
    layers_dir = paths.CHARACTERS_2D_DIR / char_id / "layers"
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
            alpha = img.split()[3]
            extrema = alpha.getextrema()
            assert extrema[0] < 255, f"Layer {layer_name} has no transparency: {extrema}"
            assert extrema[1] > 0, f"Layer {layer_name} is completely invisible: {extrema}"


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_body_parts_exclude_head_artifacts(char_id):
    """Verifies torso and arms do not erroneously include head hair or chin fragments."""
    layers_dir = paths.CHARACTERS_2D_DIR / char_id / "layers"

    if char_id == "girl_a":
        # Upper arms and torso must not contain orange hair
        for part in ["arm_upper_left.png", "arm_upper_right.png", "torso.png"]:
            arr = np.array(Image.open(layers_dir / part))
            alpha = arr[:, :, 3]
            nz = arr[alpha > 0]
            orange_hair = (nz[:, 0] > 180) & (nz[:, 1] > 60) & (nz[:, 2] < 50)
            assert np.sum(orange_hair) == 0, f"Found orange hair fragments in {part}!"
    else:  # boy_b
        # Torso collar must be blue hoodie, not head skin
        arr_t = np.array(Image.open(layers_dir / "torso.png"))
        top_collar_rgb = np.median(arr_t[:10, 40:170, :3], axis=(0, 1)).astype(int)
        # Blue hoodie: Blue > Red + 30
        assert top_collar_rgb[2] > top_collar_rgb[0] + 30, f"Torso collar is not hoodie: {top_collar_rgb}"


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_swappable_face_layers_diff_cleanliness(char_id):
    """Verifies mouth and eye layers are clean feature diffs rather than full-box skin cutouts."""
    layers_dir = paths.CHARACTERS_2D_DIR / char_id / "layers"

    # 1. Closed mouth layer must be isolated mouth line, not huge 3000+ px skin block
    mc_arr = np.array(Image.open(layers_dir / "mouth_closed.png"))
    mc_alpha = mc_arr[:, :, 3]
    mc_count = np.sum(mc_alpha > 0)
    assert 100 < mc_count < 1500, f"Mouth closed pixel count abnormal: {mc_count}"
    # Must have smooth semi-transparent antialiasing
    assert np.sum((mc_alpha > 0) & (mc_alpha < 255)) > 20

    # 2. Eye layers must have smooth antialiasing and reasonable area
    for eye_name in ["eyes_open.png", "eyes_blink.png", "eyes_look_left.png", "eyes_look_right.png"]:
        eye_arr = np.array(Image.open(layers_dir / eye_name))
        eye_alpha = eye_arr[:, :, 3]
        eye_count = np.sum(eye_alpha > 0)
        assert 500 < eye_count < 2200, f"Eye layer {eye_name} pixel count abnormal: {eye_count}"
        assert np.sum((eye_alpha > 0) & (eye_alpha < 255)) > 50


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_character_preview_sheets_exist(char_id):
    """Verifies staging preview poses, comparison sheet, and contact sheets exist for review."""
    staging_dir = paths.CHARACTERS_2D_DIR / char_id / "staging"
    assert staging_dir.is_dir()

    contact_sheet = staging_dir / f"{char_id}_preview_sheet.png"
    assert contact_sheet.is_file(), f"Missing preview sheet: {contact_sheet}"

    cmp_sheet = staging_dir / f"{char_id}_source_comparison.png"
    assert cmp_sheet.is_file(), f"Missing source comparison sheet: {cmp_sheet}"

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


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_vector_character_pack_structure_and_manifest(char_id):
    """Verifies that vector character pack exists with a valid manifest and character.json."""
    vector_dir = paths.CHARACTERS_2D_DIR / char_id / "vector"
    assert vector_dir.is_dir(), f"Missing vector directory: {vector_dir}"

    manifest_file = vector_dir / "manifest.json"
    assert manifest_file.is_file(), f"Missing manifest.json in {vector_dir}"

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Manifest schema validation
    errors = validate_manifest_schema(manifest)
    assert errors == [], f"Vector manifest validation errors for {char_id}: {errors}"

    assert manifest["id"] == char_id
    assert manifest["kind"] == "vector"
    assert manifest["type"] == "layered"
    assert manifest["viewBox"] == "0 0 1000 1500"

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
        assert p in pivots, f"Missing pivot '{p}' in vector {char_id} manifest"
        assert len(pivots[p]) == 2

    # 3. Check z_order and head_position
    assert "z_order" in manifest
    assert "head_position" in manifest
    assert len(manifest["head_position"]) == 2

    # 4. Character2D skeletal loading
    char_json_file = vector_dir / "character.json"
    assert char_json_file.is_file()
    char2d = Character2D.from_json(char_json_file)
    assert char2d.name == char_id
    assert len(char2d.parts) >= 11


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_vector_character_pack_layers_and_security(char_id):
    """Verifies all 22 SVG layers exist, pass strict security validation, and have consistent viewBox."""
    from toonshorts.core.character_pack import validate_svg_security
    layers_dir = paths.CHARACTERS_2D_DIR / char_id / "vector" / "layers"
    assert layers_dir.is_dir()

    expected_layers = [
        "head_base.svg",
        "head_back.svg",
        "eyes_open.svg",
        "eyes_blink.svg",
        "eyes_look_left.svg",
        "eyes_look_right.svg",
        "mouth_closed.svg",
        "mouth_slightly_open.svg",
        "mouth_wide_open.svg",
        "mouth_round_o.svg",
        "mouth_open_smile.svg",
        "torso.svg",
        "arm_upper_left.svg",
        "arm_lower_left.svg",
        "arm_upper_right.svg",
        "arm_lower_right.svg",
        "leg_upper_left.svg",
        "leg_lower_left.svg",
        "shoe_left.svg",
        "leg_upper_right.svg",
        "leg_lower_right.svg",
        "shoe_right.svg",
    ]

    for layer_name in expected_layers:
        layer_path = layers_dir / layer_name
        assert layer_path.is_file(), f"Missing vector layer: {layer_path}"
        content = layer_path.read_text(encoding="utf-8")

        # Security check
        sec_errors = validate_svg_security(content)
        assert sec_errors == [], f"Security error in {layer_name}: {sec_errors}"

        # Consistent viewBox
        assert 'viewBox="0 0 1000 1500"' in content
        # No shared CSS classes / styles
        assert "<style>" not in content
        assert "class=" not in content


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_vector_character_preview_sheets_exist(char_id):
    """Verifies preview sheets, comparison sheets, and multi-resolution renders exist."""
    staging_dir = paths.CHARACTERS_2D_DIR / char_id / "vector" / "staging"
    assert staging_dir.is_dir()

    contact_sheet = staging_dir / f"{char_id}_preview_sheet.png"
    assert contact_sheet.is_file(), f"Missing preview sheet: {contact_sheet}"

    cmp_sheet = staging_dir / f"{char_id}_source_comparison.png"
    assert cmp_sheet.is_file(), f"Missing source comparison sheet: {cmp_sheet}"

    for res in ["1x", "2x", "4x"]:
        res_file = staging_dir / f"{char_id}_standing_{res}.png"
        assert res_file.is_file(), f"Missing {res} render: {res_file}"

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


def test_vector_boy_b_hoodie_sleeve_continuity():
    """Verifies boy_b lower arms are hoodie sleeves with cuffs and hand, and elbow is at natural waist level."""
    vector_dir = paths.CHARACTERS_2D_DIR / "boy_b" / "vector"
    layers_dir = vector_dir / "layers"

    la_l_svg = (layers_dir / "arm_lower_left.svg").read_text(encoding="utf-8")
    la_r_svg = (layers_dir / "arm_lower_right.svg").read_text(encoding="utf-8")

    # Both lower arms must contain blue hoodie fabric colors
    assert "#3b689a" in la_l_svg or "#4f82ba" in la_l_svg
    assert "#3b689a" in la_r_svg or "#4f82ba" in la_r_svg

    # Must contain hoodie cuff rect
    assert "rect" in la_l_svg and "rect" in la_r_svg

    # Manifest elbow pivot must be around mid-torso (y between 600 and 700), not at wrist (y > 750)
    with open(vector_dir / "manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
    el_l = manifest["pivots"]["elbow_left"]
    el_r = manifest["pivots"]["elbow_right"]
    assert 600 <= el_l[1] <= 700, f"Boy B left elbow pivot abnormal: {el_l}"
    assert 600 <= el_r[1] <= 700, f"Boy B right elbow pivot abnormal: {el_r}"


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_vector_manifest_layer_paths_and_pivots(char_id):
    """Verifies manifest layer_paths map every layer to a valid existing SVG, and joint pivots align with caps."""
    vector_dir = paths.CHARACTERS_2D_DIR / char_id / "vector"
    with open(vector_dir / "manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "layer_paths" in manifest
    layer_paths = manifest["layer_paths"]
    for lname in manifest["layers"]:
        assert lname in layer_paths
        rel_p = layer_paths[lname]
        full_p = vector_dir / rel_p
        assert full_p.is_file(), f"Missing layer file referenced in layer_paths: {full_p}"

    # Verify character.svg exists in vector pack directory
    char_svg = vector_dir / "character.svg"
    assert char_svg.is_file(), f"Missing character.svg in {vector_dir}"


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_vector_shoe_coordinates_within_viewbox(char_id):
    """Verifies shoe SVGs do not exceed y=1495, preventing canvas bottom clipping in 1000x1500 viewBox."""
    import re
    vector_dir = paths.CHARACTERS_2D_DIR / char_id / "vector" / "layers"
    for sname in ["shoe_left.svg", "shoe_right.svg"]:
        svg_content = (vector_dir / sname).read_text(encoding="utf-8")
        # Extract content inside <g id="layer_shoe_...">
        g_start = svg_content.find("<g id=")
        g_end = svg_content.rfind("</g>")
        inner_content = svg_content[g_start:g_end]
        # Extract all numeric values in path d, points, cx, cy, etc.
        numbers = [float(n) for n in re.findall(r"(?<![a-zA-Z\d#])(\d+(?:\.\d+)?)", inner_content)]
        y_coords = [n for n in numbers if 1200 <= n <= 1600]
        assert y_coords, f"No y-coordinates found in {sname}"
        max_y = max(y_coords)
        assert max_y <= 1495, f"{char_id} {sname} exceeds viewBox height (max_y={max_y} > 1495)!"


@pytest.mark.parametrize("char_id", ["boy_b", "girl_a"])
def test_vector_standing_render_no_bottom_clipping(char_id):
    """Verifies rendered standing 2x image has zero non-zero pixels in bottom rows (y=1495..1499)."""
    staging_dir = paths.CHARACTERS_2D_DIR / char_id / "vector" / "staging"
    img_path = staging_dir / f"{char_id}_standing_2x.png"
    assert img_path.is_file()
    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img)
    # Bottom 5 rows (1495 to 1499 in 1500-height image)
    bottom_alpha = arr[1495:1500, :, 3]
    assert np.all(bottom_alpha == 0), f"Bottom edge clipping detected in {img_path.name}!"



