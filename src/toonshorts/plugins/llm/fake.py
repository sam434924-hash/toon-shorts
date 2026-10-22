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
        if topic.strip().lower() in ("what is an api?", "what is an api", "what_is_an_api"):
            return ScriptPlan(
                title="What_is_an_API",
                art_style=style_name,
                emotional_arc="Clear informative revelation through a fun restaurant metaphor",
                characters=[
                    Character(name="Host", visual_description="Friendly tech presenter sitting at a modern desk next to a whiteboard", voice_id="Kore"),
                    Character(name="Zack", visual_description="Curious coder sitting at the studio desk listening to the lesson", voice_id="Puck"),
                ],
                scenes=[
                    Scene(scene_number=1, speaker="Host", dialogue_line="Ever wonder what an API actually is? Imagine you are sitting at a restaurant.", action="What is an API?: Application, Programming, Interface", pose=Pose.IDLE, gesture="wave", camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False),
                    Scene(scene_number=2, speaker="Host", dialogue_line="You are the customer, and the kitchen is a massive database full of delicious food.", action="The Restaurant Setup: Customer as Client, Kitchen as Server, Menu as Endpoints", pose=Pose.IDLE, gesture="explain", camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False),
                    Scene(scene_number=3, speaker="Host", dialogue_line="The API is your friendly waiter! It takes your request directly to the chef.", action="The Waiter in Action: Sends Order, Connects Systems, Fetches Results", pose=Pose.WAVING, gesture="point", camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False),
                    Scene(scene_number=4, speaker="Host", dialogue_line="Weather forecasts, ride sharing apps, and credit card payments all talk through APIs.", action="Everyday Examples: Weather Apps, Ride Sharing, Payment Gateways", pose=Pose.IDLE, gesture="explain", camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False),
                    Scene(scene_number=5, speaker="Host", dialogue_line="They exchange structured JSON data packets in milliseconds back and forth.", action="Fast Data Exchange: JSON Payloads, REST Endpoints, Instant Response", pose=Pose.IDLE, gesture="point", camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False),
                    Scene(scene_number=6, speaker="Host", dialogue_line="So without APIs, the modern connected internet would just be screaming in the dark!", action="The Connected World: Automation, Web Integration, Seamless Tech", pose=Pose.LAUGHING, gesture="thumbs_up", camera_move=CameraMove.STATIC, transition=Transition.FADE, is_punchline=True),
                ],
            )

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
            ],
        )

    def review_and_refine(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
    ) -> Tuple[ScriptPlan, CriticReview]:
        score = 9.0 if plan.title == "What_is_an_API" else 8.5
        review = CriticReview(
            score=score,
            hook_strength=9.0,
            joke_quality=score,
            pacing=8.5,
            variety=8.0,
            weakest_scene_index=None,
            revision_instructions=None,
        )
        return plan, review
