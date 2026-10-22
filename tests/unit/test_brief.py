"""Unit tests for brief data model, validation against inventory, and serialization."""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from toonshorts.brief import (
    VideoBrief,
    validate_brief_filename,
    save_brief,
    load_brief,
    get_last_brief,
    format_brief_summary,
)


def test_validate_brief_filename():
    assert validate_brief_filename("My First Video") == "My_First_Video"
    assert validate_brief_filename("test-123_abc") == "test-123_abc"
    with pytest.raises(ValueError):
        validate_brief_filename("   ")


def test_valid_video_brief(tmp_path):
    brief = VideoBrief(
        video_name="api_explainer",
        story="A funny explanation of what an API is using a restaurant waiter metaphor.",
        format="explanation video",
        style="whiteboard",
        characters=["presenter"],
        speaker="presenter",
        voice="Kore",
        board_animations_use=["request_response", "flow"],
        board_animations_avoid=[],
        hand_gestures="on",
        camera="zoom_speaker",
        length_seconds=30,
        custom="Make the waiter hold a platter",
    )
    errors = brief.validate_against_inventory()
    assert errors == []

    # Save and reload
    saved_path = save_brief(brief, briefs_dir=tmp_path)
    assert saved_path.is_file()
    assert saved_path.name == "api_explainer.json"

    loaded = load_brief(saved_path, briefs_dir=tmp_path)
    assert loaded.video_name == "api_explainer"
    assert loaded.style == "whiteboard"
    assert loaded.voice == "Kore"
    assert loaded.speaker == "presenter"


def test_brief_rejects_unknown_style(tmp_path):
    brief = VideoBrief(
        video_name="bad_style",
        story="Valid story line",
        style="non_existent_style_xyz",
        characters=["presenter"],
        speaker="presenter",
        voice="Kore",
    )
    errors = brief.validate_against_inventory()
    assert any("Style 'non_existent_style_xyz' not found" in e for e in errors)
    with pytest.raises(ValueError):
        save_brief(brief, briefs_dir=tmp_path)


def test_brief_rejects_unknown_character(tmp_path):
    brief = VideoBrief(
        video_name="bad_char",
        story="Valid story line",
        style="whiteboard",
        characters=["alien_monster_99"],
        speaker="alien_monster_99",
        voice="Kore",
    )
    errors = brief.validate_against_inventory()
    assert any("Character 'alien_monster_99' not found" in e for e in errors)


def test_brief_rejects_unknown_animation(tmp_path):
    brief = VideoBrief(
        video_name="bad_anim",
        story="Valid story line",
        style="whiteboard",
        characters=["presenter"],
        speaker="presenter",
        voice="Kore",
        board_animations_use=["non_existent_flame_burst"],
    )
    errors = brief.validate_against_inventory()
    assert any("non_existent_flame_burst" in e for e in errors)


def test_brief_rejects_extra_keys(tmp_path):
    bad_json = {
        "video_name": "extra_keys_test",
        "story": "Story",
        "format": "explanation video",
        "style": "whiteboard",
        "characters": ["presenter"],
        "speaker": "presenter",
        "voice": "Kore",
        "illegal_extra_key": "injected_value",
    }
    file_path = tmp_path / "extra_keys_test.json"
    file_path.write_text(json.dumps(bad_json), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown keys"):
        load_brief(file_path, briefs_dir=tmp_path)


def test_format_brief_summary_max_10_lines():
    brief = VideoBrief(
        video_name="summary_test",
        story="A short explanation of git merge vs rebase.",
        format="explanation video",
        style="whiteboard",
        characters=["presenter", "boy_a"],
        speaker="presenter",
        voice="Kore",
        board_animations_use=["flow"],
        board_animations_avoid=["typed_code"],
        hand_gestures="on",
        camera="zoom_speaker",
        length_seconds=30,
        custom="Include branch diagram",
    )
    summary = format_brief_summary(brief)
    lines = summary.strip().split("\n")
    assert len(lines) <= 10, f"Summary exceeded 10 lines: {len(lines)}"
    assert "Brief: summary_test" in lines[0]
    assert "Reply 'go' to confirm" in lines[-1]


def test_get_last_brief(tmp_path):
    assert get_last_brief(briefs_dir=tmp_path) is None

    brief1 = VideoBrief(
        video_name="vid1",
        story="Story 1",
        style="whiteboard",
        characters=["presenter"],
        speaker="presenter",
        voice="Kore",
    )
    save_brief(brief1, briefs_dir=tmp_path)

    last = get_last_brief(briefs_dir=tmp_path)
    assert last is not None
    assert last.video_name == "vid1"


def test_run_pipeline_from_brief_mock(tmp_path):
    from toonshorts.core.pipeline import run_pipeline_from_brief

    brief = VideoBrief(
        video_name="test_brief_run",
        story="Mock story for testing pipeline execution from brief.",
        style="stickman",
        characters=["boy_a"],
        speaker="boy_a",
        voice="fake",
        board_animations_use=[],
        board_animations_avoid=[],
        hand_gestures="off",
        camera="fixed",
        length_seconds=30,
    )
    briefs_dir = tmp_path / "briefs"
    saved_brief_path = save_brief(brief, briefs_dir=briefs_dir)

    out_dir = tmp_path / "output"
    result = run_pipeline_from_brief(
        brief_source=saved_brief_path,
        output_dir=out_dir,
        stills_only=True,
        mock=True,
        auto_confirm=True,
    )
    assert result["status"] == "stills_ready"
    assert len(result["stills"]) >= 1
    assert result["stills"][0].is_file()
    assert result["scene_file"].is_file()

