"""
Purpose: Google GenAI client wrapper with backoff, limits, and offline mock.
Inputs: Prompts, model parameters, schemas, and credentials.
Outputs: Generated text responses and image byte streams.
Depends on: core.caps, core.config, core.errors, core.models, google.genai, json, logging, random, time, typing
Used by: client, plugins.llm.gemini, plugins.render.gemini
Config keys: GEMINI_API_KEY, IMAGE_MODEL_NAME, TEXT_MODEL_NAME
Tests: tests/unit/test_spend_cap.py
"""

import time
import random
import json
import logging
from typing import Optional, Any
from google import genai
from google.genai import types
from google.genai.errors import APIError

from . import config
from .errors import SpendCapExceededError
from .caps import SpendCapTracker
from .models import ScriptPlan, CriticReview

logger = logging.getLogger("toonshorts.client")


class GeminiClientWrapper:
    """Wrapper around Google GenAI client enforcing exponential backoff and safety limits."""

    def __init__(self, api_key: Optional[str] = None, mock: bool = False, tracker: Optional[SpendCapTracker] = None):
        self.mock = mock
        self.tracker = tracker or SpendCapTracker()
        self.critic_rewrite_count = 0
        
        self.api_key = api_key or config.GEMINI_API_KEY
        if not self.api_key and not self.mock:
            logger.info("No GEMINI_API_KEY found; defaulting to mock mode for offline safety.")
            self.mock = True

        if not self.mock:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    @property
    def api_call_count(self) -> int:
        return self.tracker.api_call_count

    @api_call_count.setter
    def api_call_count(self, val: int):
        self.tracker.api_call_count = val

    @property
    def image_generation_count(self) -> int:
        return self.tracker.image_generation_count

    @image_generation_count.setter
    def image_generation_count(self, val: int):
        self.tracker.image_generation_count = val

    def _increment_api_call(self):
        self.tracker.increment_api_call()

    def _increment_image_gen(self):
        self.tracker.increment_image_gen()

    def generate_text_with_retry(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        response_schema: Optional[Any] = None,
        max_retries: int = 3,
    ) -> str:
        """Executes text generation with exponential backoff for 429/503 errors."""
        self._increment_api_call()
        model_name = model or config.TEXT_MODEL_NAME

        if self.mock:
            return self._mock_text_response(prompt, response_schema)

        backoff = 2.0
        for attempt in range(max_retries + 1):
            try:
                gen_config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json" if response_schema else "text/plain",
                    response_schema=response_schema,
                )
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=gen_config,
                )
                return response.text or ""
            except APIError as e:
                status_code = getattr(e, "code", None)
                if status_code in (429, 503) and attempt < max_retries:
                    sleep_time = backoff + random.uniform(0.1, 0.5)
                    logger.warning("Gemini API %s on attempt %d. Backing off for %.2fs...", status_code, attempt + 1, sleep_time)
                    time.sleep(sleep_time)
                    backoff *= 2.0
                else:
                    raise RuntimeError(f"Gemini API call failed after {attempt+1} attempts: {e}") from e
            except Exception as e:
                if attempt < max_retries and "429" in str(e):
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise RuntimeError(f"Unexpected error calling Gemini API: {e}") from e

    def generate_image_with_retry(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        reference_image_bytes: Optional[bytes] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ) -> bytes:
        """Executes image generation with exponential backoff for 429/503 errors."""
        self._increment_image_gen()
        self._increment_api_call()
        model_name = model or config.IMAGE_MODEL_NAME

        if self.mock:
            return self._mock_image_response(prompt)

        backoff = 2.5
        for attempt in range(max_retries + 1):
            try:
                img_config = types.GenerateImageConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                    aspect_ratio="9:16",
                    negative_prompt=negative_prompt,
                )
                response = self.client.models.generate_images(
                    model=model_name,
                    prompt=prompt,
                    config=img_config,
                )
                if response.generated_images:
                    return response.generated_images[0].image.image_bytes
                raise RuntimeError("No image was returned by Gemini Imagen API")
            except APIError as e:
                status_code = getattr(e, "code", None)
                if status_code in (429, 503) and attempt < max_retries:
                    sleep_time = backoff + random.uniform(0.1, 0.5)
                    logger.warning("Gemini Image API %s. Retrying in %.2fs...", status_code, sleep_time)
                    time.sleep(sleep_time)
                    backoff *= 2.0
                else:
                    raise RuntimeError(f"Image generation failed after {attempt+1} attempts: {e}") from e
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise RuntimeError(f"Unexpected image generation error: {e}") from e

    def _mock_text_response(self, prompt: str, schema: Any) -> str:
        """Deterministic mock responses for offline runs and automated test suites."""
        if schema == ScriptPlan or "ScriptPlan" in str(prompt) or "original characters" in prompt:
            topic_str = "Toon Short Story"
            if 'about: "' in prompt:
                try:
                    topic_str = prompt.split('about: "')[1].split('"')[0]
                except Exception:
                    pass
            style_str = "stickman"
            if "Art Style: " in prompt:
                try:
                    style_str = prompt.split("Art Style: ")[1].split()[0]
                except Exception:
                    pass

            return json.dumps({
                "title": f"{topic_str}_{style_str}",
                "art_style": style_str,
                "emotional_arc": "Intense suspicion leads to hilarious misunderstanding",
                "characters": [
                    {"name": "Pip", "visual_description": "Stickman wearing oversized round red glasses", "voice_id": "en-US-GuyNeural"},
                    {"name": "Zack", "visual_description": "Stickman wearing a tall jaunty blue top hat", "voice_id": "en-US-JennyNeural"}
                ],
                "scenes": [
                    {"scene_number": 1, "speaker": "Pip", "dialogue_line": "Stop right there! Someone stole my semicolon!", "action": "Pip points accusingly while trembling with rage", "pose": "shocked", "camera_move": "zoom_in", "transition": "cut", "is_punchline": False},
                    {"scene_number": 2, "speaker": "Zack", "dialogue_line": "Relax Pip, what does a semicolon even look like?", "action": "Zack adjusts his top hat casually", "pose": "idle", "camera_move": "pan_left", "transition": "cut", "is_punchline": False},
                    {"scene_number": 3, "speaker": "Pip", "dialogue_line": "It looks like a period that could not commit to stopping!", "action": "Pip waves arms wildly in frustration", "pose": "waving", "camera_move": "zoom_out", "transition": "cut", "is_punchline": False},
                    {"scene_number": 4, "speaker": "Zack", "dialogue_line": "Oh you mean this thing stuck to my shoe?", "action": "Zack lifts his foot revealing a giant semicolon", "pose": "jumping", "camera_move": "shake", "transition": "cut", "is_punchline": True},
                    {"scene_number": 5, "speaker": "Pip", "dialogue_line": "My entire codebase was resting on your left heel!", "action": "Both characters burst into hysterical laughter", "pose": "laughing", "camera_move": "static", "transition": "fade", "is_punchline": True}
                ]
            })
        elif schema == CriticReview or "CriticReview" in str(prompt) or "hook strength" in prompt:
            return json.dumps({
                "score": 8.5,
                "hook_strength": 9.0,
                "joke_quality": 8.5,
                "pacing": 8.0,
                "variety": 8.5,
                "weakest_scene_index": 2,
                "revision_instructions": "Make Zack's second line even more nonchalant to contrast Pip's panic."
            })
        return "{}"

    def _mock_image_response(self, prompt: str) -> bytes:
        """Generates a stylized vertical 9:16 placeholder PNG in memory."""
        from io import BytesIO
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=(240, 235, 225))
        draw = ImageDraw.Draw(img)
        color_accent = (230, 80, 60) if "crayon" in prompt else (70, 130, 180)
        draw.rectangle([60, 60, 1020, 1860], outline=color_accent, width=8)
        draw.line([100, 1400, 980, 1400], fill=(80, 80, 80), width=6)
        draw.ellipse([440, 600, 640, 800], fill=color_accent, outline=(20, 20, 20), width=4)
        draw.line([540, 800, 540, 1200], fill=(20, 20, 20), width=10)
        draw.line([540, 920, 400, 1050], fill=(20, 20, 20), width=8)
        draw.line([540, 920, 680, 1050], fill=(20, 20, 20), width=8)

        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
