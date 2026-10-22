"""Contract tests for LLMInterface implementations."""

import pytest
from toonshorts.core.registry import list_llms, get_llm, LLMInterface
from toonshorts.core.models import ScriptPlan, CriticReview
from toonshorts.core.pipeline import load_style_preset


@pytest.mark.parametrize("plugin_name", list_llms())
def test_llm_contract(plugin_name):
    """Every LLM plugin must fulfill the LLMInterface contract."""
    llm = get_llm(plugin_name)
    assert isinstance(llm, LLMInterface)
    assert llm.name == plugin_name

    preset = load_style_preset("stickman")
    topic = "The Semicolon Mystery"

    # Test screenplay generation
    if plugin_name == "gemini":
        try:
            plan = llm.generate_plan(topic, "stickman", preset)
        except RuntimeError as e:
            pytest.skip(f"Live Gemini LLM is unavailable: {e}")
    else:
        plan = llm.generate_plan(topic, "stickman", preset)
    assert isinstance(plan, ScriptPlan)
    assert len(plan.characters) >= 2
    assert len(plan.scenes) >= 4
    assert plan.art_style == "stickman"

    # Test critic review loop
    refined_plan, review = llm.review_and_refine(plan, preset)
    assert isinstance(refined_plan, ScriptPlan)
    assert isinstance(review, CriticReview)
    assert 1.0 <= review.score <= 10.0
