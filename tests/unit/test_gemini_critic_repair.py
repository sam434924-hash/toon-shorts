"""Tests for Gemini LLM critic review parsing, single repair attempt, and score 6.0 fallback."""

import json
from unittest.mock import MagicMock
import pytest

from toonshorts.core.models import CriticReview, ScriptPlan, Character, Scene, CameraMove
from toonshorts.plugins.llm.gemini import GeminiLLMPlugin


@pytest.fixture
def sample_plan():
    return ScriptPlan(
        title="Test_Script",
        art_style="whiteboard",
        emotional_arc="Curiosity to comedic enlightenment",
        characters=[
            Character(name="Pip", visual_description="Pip character"),
            Character(name="Zack", visual_description="Zack character"),
        ],
        scenes=[
            Scene(scene_number=1, speaker="Pip", dialogue_line="Scene one dialogue", action="action 1", camera_move=CameraMove.STATIC),
            Scene(scene_number=2, speaker="Zack", dialogue_line="Scene two dialogue", action="action 2", camera_move=CameraMove.STATIC),
            Scene(scene_number=3, speaker="Pip", dialogue_line="Scene three dialogue", action="action 3", camera_move=CameraMove.STATIC),
            Scene(scene_number=4, speaker="Zack", dialogue_line="Scene four punchline", action="action 4", camera_move=CameraMove.STATIC, is_punchline=True),
        ],
    )


def test_critic_valid_first_attempt(sample_plan):
    """When critic returns valid JSON on the first attempt, it parses and returns directly."""
    valid_review_dict = {
        "score": 8.5,
        "hook_strength": 8.0,
        "joke_quality": 8.5,
        "pacing": 9.0,
        "variety": 8.0,
        "weakest_scene_index": None,
        "revision_instructions": None,
    }
    mock_client = MagicMock()
    mock_client.api_key = "valid_api_key_123"
    mock_client.is_auto_fallback = False
    mock_client.generate_text_with_retry.return_value = json.dumps(valid_review_dict)

    plugin = GeminiLLMPlugin(client=mock_client)
    review = plugin.evaluate_script(sample_plan)

    assert isinstance(review, CriticReview)
    assert review.score == 8.5
    assert mock_client.generate_text_with_retry.call_count == 1


def test_critic_repaired_output(sample_plan):
    """When first attempt fails schema validation, exactly one repair call is made, and repaired output is returned."""
    invalid_raw = "INVALID_JSON_NOT_A_DICT: {score: 7.0}"
    repaired_dict = {
        "score": 7.8,
        "hook_strength": 7.5,
        "joke_quality": 8.0,
        "pacing": 7.0,
        "variety": 7.5,
        "weakest_scene_index": 1,
        "revision_instructions": "Punch up dialogue in scene 1",
    }
    mock_client = MagicMock()
    mock_client.api_key = "valid_api_key_123"
    mock_client.is_auto_fallback = False
    mock_client.generate_text_with_retry.side_effect = [
        invalid_raw,  # First attempt fails json.loads
        json.dumps(repaired_dict),  # Repair attempt succeeds
    ]

    plugin = GeminiLLMPlugin(client=mock_client)
    review = plugin.evaluate_script(sample_plan)

    assert isinstance(review, CriticReview)
    assert review.score == 7.8
    assert review.weakest_scene_index == 1
    assert mock_client.generate_text_with_retry.call_count == 2
    # Verify repair prompt was passed
    second_call_prompt = mock_client.generate_text_with_retry.call_args_list[1][1]["prompt"]
    assert "failed JSON schema validation" in second_call_prompt


def test_critic_failed_repair_fallback_to_6(sample_plan):
    """When both first attempt and repair attempt fail, score is set to 6.0 (below 7.0 pass threshold), never 7.5."""
    mock_client = MagicMock()
    mock_client.api_key = "valid_api_key_123"
    mock_client.is_auto_fallback = False
    mock_client.generate_text_with_retry.side_effect = [
        "First bad output",
        "Second bad output after repair",
    ]

    plugin = GeminiLLMPlugin(client=mock_client)
    review = plugin.evaluate_script(sample_plan)

    assert isinstance(review, CriticReview)
    assert review.score == 6.0
    assert review.score < 7.0
    assert review.score != 7.5
    assert mock_client.generate_text_with_retry.call_count == 2


def test_critic_replan_loop_respects_hard_max_limit(sample_plan, caplog):
    """Verifies review_and_refine caps re-plans at MAX_CRITIC_REWRITES and logs an alert when score remains < 7.0."""
    import logging
    from toonshorts.core import config

    mock_client = MagicMock()
    mock_client.api_key = "valid_api_key_123"
    mock_client.is_auto_fallback = False

    plugin = GeminiLLMPlugin(client=mock_client)

    low_review = CriticReview(
        score=6.0,
        hook_strength=6.0,
        joke_quality=6.0,
        pacing=6.0,
        variety=6.0,
        weakest_scene_index=1,
        revision_instructions="Needs punchier humor",
    )

    # Mock evaluate_script to always return low_review
    plugin.evaluate_script = MagicMock(return_value=low_review)

    # Mock generate_text_with_retry for rewrites returning valid JSON plan
    plan_json = json.dumps(sample_plan.model_dump())
    mock_client.generate_text_with_retry.return_value = plan_json

    with caplog.at_level(logging.WARNING):
        best_plan, best_review = plugin.review_and_refine(sample_plan, style_preset={})

    # Must only call generate_text_with_retry MAX_CRITIC_REWRITES times
    assert mock_client.generate_text_with_retry.call_count == config.MAX_CRITIC_REWRITES
    assert best_review.score == 6.0
    # Must log warning alert about reaching limit
    assert any("remained below the 7.0 pass threshold" in rec.message for rec in caplog.records)

