"""
Purpose: Gemini LLM plugin for screenplay writing and critic reviews.
Inputs: Story topic, style presets, and script plans.
Outputs: Generated ScriptPlan screenplays and CriticReview scores.
Depends on: core.client, core.config, core.models, core.registry, core.validator, json, logging, typing
Used by: None
Config keys: CRITIC_MODEL_NAME, GEMINI_API_KEY, MAX_CRITIC_REWRITES, TEXT_MODEL_NAME
Tests: tests/contract/test_llm_contract.py
"""

import json
import logging
from typing import Dict, Any, Tuple
from pydantic import ValidationError

from toonshorts.core import config
from toonshorts.core.models import ScriptPlan, CriticReview, Character, Scene, Pose, CameraMove, Transition
from toonshorts.core.validator import validate_plan, PlanValidationError
from toonshorts.core.client import GeminiClientWrapper
from toonshorts.core.registry import LLMInterface, register_llm

logger = logging.getLogger("toonshorts.plugins.llm.gemini")

PLANNER_SYSTEM_PROMPT = """
You are an elite comedy writer and animation director creating viral 9:16 vertical shorts (30-50s).
RULES:
1. ORIGINALITY: Create 100% original, quirky characters and fresh comedic premises. NEVER imitate copyrighted characters, real public figures, brands, or existing internet memes.
2. FAMILY FRIENDLY: Witty, absurd, visual slapstick, or relatable misunderstandings suitable for all ages.
3. STRUCTURE:
   - Scene 1 (0-3s): Instant visual & dialogue hook. No slow greetings.
   - Scene 2-3: Setup and escalating comic tension.
   - Scene 4: Absurd twist.
   - Scene 5-6: Rapid punchline payoff and hilarious tag.
4. CHARACTERS: 2 or 3 recurring characters. Give each a clear, simple distinguishing visual feature (e.g. 'wearing round red glasses', 'wearing a tall blue top hat', 'bright yellow bowtie').
5. DIALOGUE: Snappy, short punchy lines (under 18 words per line).
6. VERSION & SCENE FORMAT V2:
   - Output version = 2.
   - Each scene must declare "cast": list of 1-2 character names present in the scene (must match names declared in characters; speaker must be in cast). Maintain 180-degree rule: character order in cast must not swap left/right positions.
   - Each scene must declare "layout": "cards" (list of action bullet cards, default) or "stage" (visual graphics safe area).
   - "shots" (optional list of camera shots):
     - start, end: relative time in seconds within scene duration.
     - type: "wide" or "close_up".
     - target: character name from cast or null.
     - zoom: float between 1.0 and 1.35.
     - ease_in, ease_out: float between 0.4 and 0.6 seconds.
     - Directing rules: hold duration (end - start) must be at least 1.2s. At most one zoom per 5 seconds. Shots must not overlap and must fit within scene duration.
   - "visuals" (optional, up to 3 visuals per scene, used primarily with layout="stage"):
     Allowed template types:
     * flow: params: nodes (list of 2-4 strings, max 14 chars each), optional direction ("right" or "down", default "right"), optional color ("default", "blue", "green", "purple", "orange", "red", "teal", "yellow").
     * request_response: params: client_label (max 14 chars), server_label (max 14 chars), request_label (max 14 chars), response_label (max 14 chars), optional color.
     * typed_code: params: lines (list of 1-6 strings, max 40 chars each), optional language (max 14 chars), optional color.
     * step_ladder: params: steps (list of 2-4 strings, max 14 chars each), optional color.
     * check_cross: params: items (list of 1-4 objects with 'label' (max 14 chars) and 'status' ('check' or 'cross')), optional color.
     * counter: params: start (int), end (int), optional prefix (max 6 chars), optional suffix (max 6 chars), optional label (max 14 chars), optional color.
     - trigger_word: A word from the scene dialogue_line where the visual should appear.
     - NEVER supply raw HTML, CSS, JavaScript, URLs, or SVG. Only use the allowed template types and params.
7. FORMAT: Respond ONLY with valid JSON conforming to the ScriptPlan schema (version 2). No markdown outside JSON.
"""

CRITIC_SYSTEM_PROMPT = """
You are a ruthless comedy showrunner and YouTube Shorts algorithm specialist.
Evaluate the animation script on:
1. Hook Strength (1-10): Does Scene 1 grab instant attention within 2 seconds?
2. Joke Quality (1-10): Is the punchline genuinely surprising, clever, and funny?
3. Pacing (1-10): Is dialogue fast and tight with zero filler words?
4. Variety (1-10): Are camera moves, character emotions, and physical comedy varied?

Provide an overall score (1.0 to 10.0), pinpoint the weakest scene index (1-based), and give crisp revision instructions.
Return strictly valid JSON conforming to CriticReview.
"""


@register_llm("gemini")
class GeminiLLMPlugin(LLMInterface):
    """LLM provider plugin powered by Google Gemini models."""
    name = "gemini"

    def __init__(self, client: Any = None):
        # Reads key strictly from config; never prints or logs it
        self.client = client or GeminiClientWrapper()

    def _ensure_available(self):
        """Ensures Gemini API credentials are valid and active; prevents silent fallback."""
        api_key = getattr(self.client, "api_key", None)
        if getattr(self.client, "is_auto_fallback", False) or not api_key or api_key in ("your-key-here", "your_gemini_api_key_here"):
            raise RuntimeError(
                "GEMINI_API_KEY is missing or invalid. Gemini LLM requires a valid GEMINI_API_KEY and will not fall back silently."
            )

    def generate_plan(
        self,
        topic: str,
        style_name: str,
        style_preset: Dict[str, Any],
    ) -> ScriptPlan:
        self._ensure_available()

        pacing = style_preset.get("pacing", "fast")
        user_prompt = f"""
Create a hilarious short animation script about: "{topic}".
Art Style: {style_name}
Target Pacing: {pacing} (aim for 5-7 punchy scenes totaling ~35-45 seconds).

Make sure each scene includes:
- speaker (must match one of the declared characters)
- dialogue_line (funny, sharp, quick)
- action (visual physical comedy)
- pose (one of: idle, waving, jumping, shocked, laughing)
- gesture (one of: idle, wave, point, explain, thumbs_up, shrug)
- camera_move (one of: zoom_in, zoom_out, pan_left, pan_right, shake, static)
- transition (one of: cut, fade, wipe, none)
- is_punchline (boolean flag for punchline/twist scenes)
- cast (list of 1-2 character names present in the scene)
- layout ("cards" or "stage")
- shots (optional camera shot directives)
- visuals (optional board visual templates from the allowed list: flow, request_response, typed_code, step_ladder, check_cross, counter)
"""
        max_attempts = 2
        last_error = None

        for attempt in range(max_attempts):
            prompt = user_prompt if attempt == 0 else f"{user_prompt}\n\nPREVIOUS ATTEMPT FAILED WITH VALIDATION ERROR:\n{last_error}\nPlease fix the JSON according to the schema and directing rules."
            raw_text = self.client.generate_text_with_retry(
                prompt=prompt,
                system_instruction=PLANNER_SYSTEM_PROMPT,
                model=config.TEXT_MODEL_NAME,
                response_schema=ScriptPlan,
            )
            try:
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                parsed = json.loads(cleaned.strip())
                parsed["art_style"] = style_name
                plan = ScriptPlan.model_validate(parsed)
                return validate_plan(plan)
            except (json.JSONDecodeError, ValidationError, PlanValidationError, ValueError) as e:
                last_error = e
                logger.warning("Plan validation failed (attempt %d/%d): %s", attempt + 1, max_attempts, e)

        raise ValueError(f"Failed to generate valid ScriptPlan after {max_attempts} attempts: {last_error}")

    def evaluate_script(self, plan: ScriptPlan) -> CriticReview:
        self._ensure_available()
        prompt = f"Review this script plan:\n\n{json.dumps(plan.model_dump(), indent=2)}"
        raw_text = self.client.generate_text_with_retry(
            prompt=prompt,
            system_instruction=CRITIC_SYSTEM_PROMPT,
            model=config.CRITIC_MODEL_NAME,
            response_schema=CriticReview,
        )
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            return CriticReview.model_validate(json.loads(cleaned.strip()))
        except (json.JSONDecodeError, ValidationError) as e:
            raise RuntimeError(f"Failed to parse Gemini CriticReview response: {e}")

    def review_and_refine(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
    ) -> Tuple[ScriptPlan, CriticReview]:
        self._ensure_available()

        best_plan = plan
        best_review = self.evaluate_script(plan)

        rewrites = 0
        current_plan = plan
        while best_review.score < 7.0 and rewrites < config.MAX_CRITIC_REWRITES:
            rewrites += 1
            rewrite_prompt = f"""
The current script scored {best_review.score}/10.
Critic Weakness Feedback: {best_review.revision_instructions}
Weakest Scene: Scene {best_review.weakest_scene_index}

Original Script:
{json.dumps(current_plan.model_dump(), indent=2)}

Please rewrite and punch up this script to address the feedback. Keep the title, art style, and character names consistent.
"""
            raw_text = self.client.generate_text_with_retry(
                prompt=rewrite_prompt,
                system_instruction=PLANNER_SYSTEM_PROMPT,
                model=config.TEXT_MODEL_NAME,
                response_schema=ScriptPlan,
            )
            try:
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                rewritten_dict = json.loads(cleaned.strip())
                rewritten_dict["art_style"] = current_plan.art_style
                new_plan = ScriptPlan.model_validate(rewritten_dict)
                new_review = self.evaluate_script(new_plan)
                if new_review.score >= best_review.score:
                    best_plan = new_plan
                    best_review = new_review
                current_plan = new_plan
            except Exception:
                break

        return best_plan, best_review
