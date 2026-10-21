"""
Purpose: Deterministic offline mock LLM plugin for fast test execution.
Inputs: Story topic, style name, and style preset dictionary.
Outputs: Fixed valid ScriptPlan screenplay and CriticReview score.
Depends on: core.models, core.registry, typing
Used by: None
Config keys: None
Tests: tests/contract/test_llm_contract.py, tests/smoke/test_smoke_pipeline.py
"""

from typing import Dict, Any, Tuple
from toonshorts.core.models import ScriptPlan, CriticReview, Character, Scene, Pose, CameraMove, Transition
from toonshorts.core.registry import LLMInterface, register_llm


@register_llm("fake")
class FakeLLMPlugin(LLMInterface):
    """Deterministic offline mock LLM for testing without network or API costs."""
    name = "fake"

    def generate_plan(
        self,
        topic: str,
        style_name: str,
        style_preset: Dict[str, Any],
    ) -> ScriptPlan:
        return ScriptPlan(
            title=f"Mock_{topic[:20].replace(' ', '_')}",
            art_style=style_name,
            emotional_arc="Curiosity gives way to sudden comedic enlightenment",
            characters=[
                Character(name="Pip", visual_description="Stickman with round red glasses", voice_id="v1"),
                Character(name="Zack", visual_description="Stickman with tall blue hat", voice_id="v2"),
            ],
            scenes=[
                Scene(scene_number=1, speaker="Pip", dialogue_line="Stop right there! Where is my semicolon?", action="Points accusingly", pose=Pose.SHOCKED, camera_move=CameraMove.ZOOM_IN, transition=Transition.CUT, is_punchline=False),
                Scene(scene_number=2, speaker="Zack", dialogue_line="Relax, what does it even look like?", action="Adjusts hat casually", pose=Pose.IDLE, camera_move=CameraMove.PAN_LEFT, transition=Transition.CUT, is_punchline=False),
                Scene(scene_number=3, speaker="Pip", dialogue_line="A period that refuses to fully stop!", action="Waves hands wildly", pose=Pose.WAVING, camera_move=CameraMove.ZOOM_OUT, transition=Transition.CUT, is_punchline=False),
                Scene(scene_number=4, speaker="Zack", dialogue_line="Oh you mean this sticker on my shoe?", action="Lifts foot displaying semicolon", pose=Pose.JUMPING, camera_move=CameraMove.SHAKE, transition=Transition.FADE, is_punchline=True),
            ]
        )

    def review_and_refine(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
    ) -> Tuple[ScriptPlan, CriticReview]:
        review = CriticReview(
            score=8.5,
            hook_strength=9.0,
            joke_quality=8.5,
            pacing=8.5,
            variety=8.0,
            weakest_scene_index=None,
            revision_instructions=None,
        )
        return plan, review
