"""Unit tests for Phase C 2D Rig Contract, validation, and dynamic inventory labeling."""

import json
from pathlib import Path
import pytest

from toonshorts.core import paths
from toonshorts.core.character_pack import (
    check_pack_rig_contract,
    REQUIRED_RIG_PARTS,
    REQUIRED_RIG_PIVOTS,
    REQUIRED_RIG_POSES,
    load_character_pack,
    CharacterPack,
)
from toonshorts.inventory import get_installed_characters, format_inventory_display


def test_rig_contract_constants_completeness():
    assert "head" in REQUIRED_RIG_PARTS
    assert "torso" in REQUIRED_RIG_PARTS
    assert "upper_arms" in REQUIRED_RIG_PARTS
    assert "forearms" in REQUIRED_RIG_PARTS
    assert "hands" in REQUIRED_RIG_PARTS
    assert "thighs" in REQUIRED_RIG_PARTS
    assert "shins" in REQUIRED_RIG_PARTS
    assert "feet" in REQUIRED_RIG_PARTS

    assert "wrist_left" in REQUIRED_RIG_PIVOTS
    assert "wrist_right" in REQUIRED_RIG_PIVOTS
    assert "elbow_left" in REQUIRED_RIG_PIVOTS
    assert "elbow_right" in REQUIRED_RIG_PIVOTS
    assert "shoulder_left" in REQUIRED_RIG_PIVOTS
    assert "shoulder_right" in REQUIRED_RIG_PIVOTS

    assert "idle" in REQUIRED_RIG_POSES
    assert "explain" in REQUIRED_RIG_POSES
    assert "point_board" in REQUIRED_RIG_POSES
    assert "point_other" in REQUIRED_RIG_POSES
    assert "wave" in REQUIRED_RIG_POSES
    assert "thumbs_up" in REQUIRED_RIG_POSES
    assert "shrug" in REQUIRED_RIG_POSES
    assert "nod" in REQUIRED_RIG_POSES
    assert "head_tilt" in REQUIRED_RIG_POSES
    assert "lean_speaker" in REQUIRED_RIG_POSES
    assert "listening_reaction" in REQUIRED_RIG_POSES


def test_boy_b_and_girl_a_are_gesture_ready():
    for cid in ["boy_b", "girl_a"]:
        pack = load_character_pack(cid)
        is_ready, missing = pack.check_rig_contract()
        assert is_ready is True, f"Expected {cid} to be gesture-ready, missing: {missing}"
        assert len(missing) == 0


def test_boy_a_and_presenter_flagged_with_missing_parts():
    for cid in ["boy_a", "presenter"]:
        pack = load_character_pack(cid)
        is_ready, missing = pack.check_rig_contract()
        assert is_ready is False, f"Expected {cid} to be flagged with missing parts"
        assert len(missing) > 0


def test_dynamic_gesture_ready_pack_in_temp_dir(tmp_path):
    temp_chars_dir = tmp_path / "temp_chars"
    temp_chars_dir.mkdir(parents=True)

    # Clone boy_b into temp dir as a gesture-ready pack
    new_pack_dir = temp_chars_dir / "scout_alex"
    new_pack_dir.mkdir()

    boy_b_vec = paths.CHARACTERS_2D_DIR / "boy_b" / "vector"
    manifest = json.loads((boy_b_vec / "manifest.json").read_text(encoding="utf-8"))
    manifest["id"] = "scout_alex"
    manifest["name"] = "Scout Alex"
    (new_pack_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (new_pack_dir / "character.svg").write_text((boy_b_vec / "character.svg").read_text(encoding="utf-8"), encoding="utf-8")

    discovered = get_installed_characters(characters_2d_dir=temp_chars_dir)
    packs = {p["id"]: p for p in discovered["2d_packs"]}

    assert "scout_alex" in packs
    assert packs["scout_alex"]["gesture_ready"] is True
    assert len(packs["scout_alex"]["missing_rig_parts"]) == 0


def test_pack_with_missing_parts_is_flagged_in_inventory(tmp_path):
    temp_chars_dir = tmp_path / "temp_chars"
    temp_chars_dir.mkdir(parents=True)

    # Clone boy_a into temp dir (valid character pack schema, but incomplete rig contract)
    inc_dir = temp_chars_dir / "mini_bot"
    inc_dir.mkdir()

    boy_a_dir = paths.CHARACTERS_2D_DIR / "boy_a"
    manifest = json.loads((boy_a_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["id"] = "mini_bot"
    manifest["name"] = "Mini Bot"
    (inc_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (inc_dir / "character.svg").write_text((boy_a_dir / "character.svg").read_text(encoding="utf-8"), encoding="utf-8")

    discovered = get_installed_characters(characters_2d_dir=temp_chars_dir)
    packs = {p["id"]: p for p in discovered["2d_packs"]}

    assert "mini_bot" in packs
    assert packs["mini_bot"]["gesture_ready"] is False
    assert len(packs["mini_bot"]["missing_rig_parts"]) > 0

    # Test formatted display includes [limited-gestures]
    inv = {
        "characters": discovered,
        "styles": [],
        "board_animations": {},
        "voices": {},
        "camera_options": {},
        "props_and_backgrounds": {},
    }
    display = format_inventory_display(inv)
    assert "[limited-gestures" in display
    assert "mini_bot" in display
