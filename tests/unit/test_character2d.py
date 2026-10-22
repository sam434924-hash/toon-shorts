"""Unit tests for 2D layered character system, registry, FK skeleton, and actions."""

from pathlib import Path
import math
import numpy as np
import pytest
from PIL import Image

from toonshorts.core import paths
from toonshorts.core.character2d import (
    CHARACTER_SLOTS,
    Character2D,
    SkeletonPose2D,
    validate_character_name,
    ensure_path_inside_dir,
    get_character,
    slice_character_sheet,
    compute_action_pose,
    compute_forward_kinematics,
    get_face_for_audio,
    render_scene_frame,
    create_faces_contact_sheet,
    create_parts_contact_sheet,
    PROJECT_ROOT,
)


@pytest.fixture
def test_dirs(tmp_path):
    sheet_src = paths.ASSETS_SOURCES_INCOMING_DIR / "sheet_03.png"
    layout_src = paths.LAYOUTS_2D_DIR / "sheet_03_layout.json"
    return {
        "sheet": sheet_src,
        "layout": layout_src,
        "chars_dir": tmp_path / "characters",
        "output_dir": tmp_path / "renders",
    }


def test_character_name_validation():
    """Verifies strict character name validation rules."""
    assert validate_character_name("valid_name") == "valid_name"
    assert validate_character_name("stick-01") == "stick-01"
    assert validate_character_name("A123_-") == "A123_-"

    # Invalid names
    with pytest.raises(ValueError, match="Invalid character name"):
        validate_character_name("")
    with pytest.raises(ValueError, match="Invalid character name"):
        validate_character_name("has space")
    with pytest.raises(ValueError, match="Invalid character name"):
        validate_character_name("../traversal")
    with pytest.raises(ValueError, match="Invalid character name"):
        validate_character_name("special!@#")
    with pytest.raises(ValueError, match="Invalid character name"):
        validate_character_name("a" * 33)


def test_path_security_check(tmp_path):
    """Verifies that path traversal attempts outside the character folder are rejected."""
    char_dir = tmp_path / "character_a"
    char_dir.mkdir(parents=True)
    inside_file = char_dir / "layers" / "head.png"

    assert ensure_path_inside_dir(inside_file, char_dir) == inside_file.resolve()

    outside_file = tmp_path / "secret.env"
    with pytest.raises(ValueError, match="Security error"):
        ensure_path_inside_dir(outside_file, char_dir)


def test_character_registry_and_missing(test_dirs):
    """Verifies registry lookup and missing character reporting."""
    missing = get_character("unknown_char_99", base_dir=test_dirs["chars_dir"])
    assert isinstance(missing, dict)
    assert missing["status"] == "missing"
    assert "unknown_char_99" in missing["message"]

    invalid = get_character("../evil", base_dir=test_dirs["chars_dir"])
    assert invalid["status"] == "error"


def test_sheet_slicing_and_registry(test_dirs):
    """Verifies cutting the sheet into layers, saving registry JSON, and loading via get_character."""
    char = slice_character_sheet(
        sheet_path=test_dirs["sheet"],
        layout_path=test_dirs["layout"],
        character_name="test_stickman",
        output_base_dir=test_dirs["chars_dir"],
    )
    assert char.name == "test_stickman"
    assert (char.folder / "character.json").is_file()

    # Verify key layers exist and are RGBA PNGs
    expected_parts = [
        "head", "torso",
        "sleeve_upper_left", "sleeve_lower_left",
        "sleeve_upper_right", "sleeve_lower_right",
        "leg_upper_left", "leg_lower_left", "shoe_left",
        "leg_upper_right", "leg_lower_right", "shoe_right"
    ]
    for part in expected_parts:
        assert part in char.parts
        img_path = char.parts[part].image_path
        assert img_path.is_file()
        with Image.open(img_path) as im:
            assert im.mode == "RGBA"

    # Verify 8 expressions
    assert len(char.expressions) == 8
    for exp_name in ["neutral", "happy", "angry", "sad", "shocked", "smirk", "talking_open", "talking_round"]:
        assert exp_name in char.expressions
        assert char.expressions[exp_name].is_file()

    # Verify hands (4 poses x 2 sides = 8 hand parts)
    for pose in ["open_palm", "fist", "pointing", "waving"]:
        assert f"hand_{pose}_left" in char.parts
        assert f"hand_{pose}_right" in char.parts

    # Verify lookup via get_character
    loaded = get_character("test_stickman", base_dir=test_dirs["chars_dir"])
    assert isinstance(loaded, Character2D)
    assert loaded.name == "test_stickman"
    assert len(loaded.parts) == len(char.parts)


def test_slots_replacement(test_dirs):
    """Verifies modular slot system where items in the same slot replace each other."""
    char = Character2D("slot_test", test_dirs["chars_dir"] / "slot_test")
    for slot in CHARACTER_SLOTS:
        assert char.get_slot(slot) is None

    # Equip torso
    char.equip_slot("torso", "torso_hoodie_grey")
    assert char.get_slot("torso") == "torso_hoodie_grey"

    # Replace torso
    char.equip_slot("torso", "torso_tshirt_blue")
    assert char.get_slot("torso") == "torso_tshirt_blue"

    # Invalid slot
    with pytest.raises(ValueError, match="Invalid slot"):
        char.equip_slot("invalid_slot", "item_xyz")


def test_forward_kinematics_rigidity(test_dirs):
    """Verifies that all child pivots stay 100% connected to parent joints across frames."""
    char = slice_character_sheet(
        sheet_path=test_dirs["sheet"],
        layout_path=test_dirs["layout"],
        character_name="fk_test",
        output_base_dir=test_dirs["chars_dir"],
    )

    for action in ["idle", "walk", "wave", "jump"]:
        for t in [0.0, 0.25, 0.5, 0.75]:
            pose = compute_action_pose(action, t=t, intensity=1.2)
            transforms = compute_forward_kinematics(char, pose)

            # Neck to head
            neck_world = transforms["head"]["world_pos"]
            # Shoulder to upper sleeve
            shoulder_pos = transforms["sleeve_upper_left"]["world_pos"]
            # Elbow to lower sleeve
            elbow_world = transforms["sleeve_lower_left"]["world_pos"]
            # Cuff to hand
            active_hand_key = f"hand_{pose.hand_left_pose}_left"
            cuff_world = transforms[active_hand_key]["world_pos"]

            # Shoulder to elbow distance
            d_upper = math.hypot(elbow_world[0] - shoulder_pos[0], elbow_world[1] - shoulder_pos[1])
            expected_upper = math.hypot(
                char.parts["sleeve_upper_left"].joints["elbow"][0] - char.parts["sleeve_upper_left"].pivot[0],
                char.parts["sleeve_upper_left"].joints["elbow"][1] - char.parts["sleeve_upper_left"].pivot[1],
            )
            assert abs(d_upper - expected_upper) < 1e-4

            # Elbow to cuff distance
            d_lower = math.hypot(cuff_world[0] - elbow_world[0], cuff_world[1] - elbow_world[1])
            expected_lower = math.hypot(
                char.parts["sleeve_lower_left"].joints["cuff"][0] - char.parts["sleeve_lower_left"].pivot[0],
                char.parts["sleeve_lower_left"].joints["cuff"][1] - char.parts["sleeve_lower_left"].pivot[1],
            )
            assert abs(d_lower - expected_lower) < 1e-4


def test_action_settings_clamped_and_squash_stretch():
    """Verifies intensity clamping [0.5, 1.5] and squash & stretch deformation."""
    pose_low = compute_action_pose("jump", t=0.1, intensity=0.1)
    assert pose_low.intensity == 0.5

    pose_high = compute_action_pose("jump", t=0.1, intensity=2.5)
    assert pose_high.intensity == 1.5

    crouch_pose = compute_action_pose("jump", t=0.10, intensity=1.0)
    assert crouch_pose.root_scale_y < 1.0  # squashed vertically
    assert crouch_pose.root_scale_x > 1.0  # expanded horizontally

    stretch_pose = compute_action_pose("jump", t=0.35, intensity=1.0)
    assert stretch_pose.root_scale_y > 1.0  # stretched vertically
    assert stretch_pose.root_scale_x < 1.0  # compressed horizontally
    assert stretch_pose.jump_height > 80.0


def test_audio_loudness_mouth_shapes():
    """Verifies mouth shape swaps driven by loudness levels."""
    assert get_face_for_audio(0.0) == "neutral"
    assert get_face_for_audio(0.10, base_emotion="happy") == "happy"
    assert get_face_for_audio(0.30) == "talking_round"
    assert get_face_for_audio(0.75) == "talking_open"


def test_frame_render_framing_and_contact_sheets(test_dirs):
    """Verifies 55-65% vertical framing, jump headroom, and contact sheet generation."""
    char = slice_character_sheet(
        sheet_path=test_dirs["sheet"],
        layout_path=test_dirs["layout"],
        character_name="render_test",
        output_base_dir=test_dirs["chars_dir"],
    )

    # 1. Framing check: 55-65% height
    pose_idle = compute_action_pose("idle", t=0.0)
    frame = render_scene_frame(char, pose_idle, width=1080, height=1920)
    arr = np.array(frame)
    char_mask = np.any(arr[:, 350:730, :3] < 200, axis=2)
    rows = np.where(np.any(char_mask, axis=1))[0]
    char_height = rows.max() - rows.min() + 1
    pct = (char_height / 1920.0) * 100.0
    assert 55.0 <= pct <= 65.0, f"Character height {pct:.1f}% outside 55-65% target!"

    # 2. Jump apex: head never leaves frame
    pose_jump = compute_action_pose("jump", t=0.55)
    frame_jump = render_scene_frame(char, pose_jump, width=1080, height=1920)
    arr_j = np.array(frame_jump)
    j_mask = np.any(arr_j[:, 250:830, :3] < 200, axis=2)
    j_rows = np.where(np.any(j_mask, axis=1))[0]
    head_top = j_rows.min()
    assert head_top > 100, f"Head came too close to top of frame (y={head_top})!"

    # 3. Contact sheets
    faces_file = test_dirs["output_dir"] / "test_faces.png"
    create_faces_contact_sheet(char, faces_file)
    assert faces_file.is_file()

    parts_file = test_dirs["output_dir"] / "test_parts.png"
    create_parts_contact_sheet(char, parts_file)
    assert parts_file.is_file()
