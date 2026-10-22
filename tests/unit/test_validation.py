"""Tests for JSON and Pydantic schema validation."""

import pytest
from pydantic import ValidationError
from toonshorts.models import ScriptPlan, Character, Scene, CameraMove, Transition, Pose, CriticReview


def test_valid_script_plan():
    plan_dict = {
        "title": "A Day in Pixel Land",
        "art_style": "stickman",
        "emotional_arc": "Confusion turns to pure hilarity",
        "characters": [
            {"name": "Alice", "visual_description": "Stickman with round red glasses", "voice_id": "v1"},
            {"name": "Bob", "visual_description": "Stickman with tall blue hat", "voice_id": "v2"}
        ],
        "scenes": [
            {
                "scene_number": 1,
                "speaker": "Alice",
                "dialogue_line": "Who drank all the coffee?",
                "action": "Alice looks inside empty pot",
                "pose": "shocked",
                "camera_move": "zoom_in",
                "transition": "cut",
                "is_punchline": False
            },
            {
                "scene_number": 2,
                "speaker": "Bob",
                "dialogue_line": "It was not me, I only drink water!",
                "action": "Bob twitches with high energy",
                "pose": "waving",
                "camera_move": "pan_left",
                "transition": "cut",
                "is_punchline": False
            },
            {
                "scene_number": 3,
                "speaker": "Alice",
                "dialogue_line": "Your mug literally says World's Greatest Espresso Addict.",
                "action": "Alice points to Bob's giant cup",
                "pose": "idle",
                "camera_move": "zoom_out",
                "transition": "cut",
                "is_punchline": True
            },
            {
                "scene_number": 4,
                "speaker": "Bob",
                "dialogue_line": "It is a decorative emotional support mug!",
                "action": "Bob runs around the room at light speed",
                "pose": "jumping",
                "camera_move": "shake",
                "transition": "fade",
                "is_punchline": True
            }
        ]
    }
    plan = ScriptPlan.model_validate(plan_dict)
    assert plan.title == "A Day in Pixel Land"
    assert len(plan.scenes) == 4
    assert plan.scenes[0].pose == Pose.SHOCKED


def test_invalid_speaker_rejected():
    plan_dict = {
        "title": "Invalid Speaker Story",
        "art_style": "stickman",
        "emotional_arc": "Setup and punchline",
        "characters": [
            {"name": "Alice", "visual_description": "Stickman with glasses"},
            {"name": "Bob", "visual_description": "Stickman with hat"}
        ],
        "scenes": [
            {
                "scene_number": 1,
                "speaker": "Charlie",  # Not in characters!
                "dialogue_line": "I am an imposter!",
                "action": "Appears mysteriously",
                "pose": "idle",
                "camera_move": "static",
                "transition": "cut"
            },
            {"scene_number": 2, "speaker": "Alice", "dialogue_line": "Line 2", "action": "Act", "pose": "idle"},
            {"scene_number": 3, "speaker": "Bob", "dialogue_line": "Line 3", "action": "Act", "pose": "idle"},
            {"scene_number": 4, "speaker": "Alice", "dialogue_line": "Line 4", "action": "Act", "pose": "idle"}
        ]
    }
    with pytest.raises(ValidationError):
        ScriptPlan.model_validate(plan_dict)


def test_invalid_camera_move_rejected():
    with pytest.raises(ValidationError):
        Scene(
            scene_number=1,
            speaker="Alice",
            dialogue_line="Test line",
            action="Action description",
            pose=Pose.IDLE,
            camera_move="fly_through_wall",  # Invalid enum!
        )


def test_invalid_pose_rejected():
    with pytest.raises(ValidationError):
        Scene(
            scene_number=1,
            speaker="Alice",
            dialogue_line="Test line",
            action="Action description",
            pose="teleporting",  # Invalid pose!
        )


def test_critic_review_bounds():
    review = CriticReview(
        score=8.2,
        hook_strength=9.0,
        joke_quality=8.0,
        pacing=8.0,
        variety=7.5,
        weakest_scene_index=2,
        revision_instructions="Sharpen scene 2 dialogue"
    )
    assert review.score == 8.2

    with pytest.raises(ValidationError):
        CriticReview(score=15.0, hook_strength=10, joke_quality=10, pacing=10, variety=10)


def test_gemini_llm_plugin_no_silent_fallback():
    """Verify Gemini LLM plugin raises RuntimeError if API credentials are missing/invalid and never falls back silently."""
    from toonshorts.plugins.llm.gemini import GeminiLLMPlugin
    from toonshorts.core.client import GeminiClientWrapper

    # When client has no valid key
    client = GeminiClientWrapper(api_key="your-key-here")
    plugin = GeminiLLMPlugin(client=client)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is missing or invalid"):
        plugin.generate_plan("what is an api", "whiteboard", {})


def test_fake_llm_fixture_what_is_an_api():
    """Verify fake LLM plugin handles 'what is an api' and matches fixture schema."""
    from toonshorts.plugins.llm.fake import FakeLLMPlugin
    from pathlib import Path
    import json

    fake = FakeLLMPlugin()
    plan = fake.generate_plan("what is an api", "whiteboard", {})
    assert plan.title == "What_is_an_API"
    assert len(plan.scenes) == 6

    fixture_file = Path(__file__).resolve().parent.parent / "fixtures" / "what_is_an_api_plan.json"
    assert fixture_file.is_file()
    data = json.loads(fixture_file.read_text(encoding="utf-8"))
    assert data["title"] == "What_is_an_API"
    assert len(data["scenes"]) == 6

