"""
Purpose: Google Gemini text-to-speech voice plugin using current GenAI SDK.
Inputs: Scene dialogue, prebuilt Gemini voice identifiers, and destination paths.
Outputs: Generated 16-bit 24kHz WAV speech files and aligned word timestamps.
Depends on: core.client, core.config, core.errors, core.models, core.registry, logging, pathlib, typing, voice_utils
Used by: None
Config keys: GEMINI_API_KEY, GEMINI_VOICES, TTS_MODEL_NAME
Tests: tests/contract/test_voice_contract.py
"""

import logging
from pathlib import Path
from typing import List, Optional

from toonshorts.core import config
from toonshorts.core.errors import VoiceError
from toonshorts.core.models import ScriptPlan, Scene, SceneAudio
from toonshorts.core.registry import VoiceInterface, register_voice
from toonshorts.core.client import GeminiClientWrapper
from toonshorts.voice_utils import (
    check_speech_audio,
    align_words_with_whisper,
    assign_character_voices,
)

logger = logging.getLogger("toonshorts.plugins.voice.gemini_tts")


@register_voice("gemini_tts")
class GeminiTTSVoicePlugin(VoiceInterface):
    """Google Gemini text-to-speech plugin with exponential backoff and speech verification."""
    name = "gemini_tts"

    def __init__(
        self,
        client: Optional[GeminiClientWrapper] = None,
        model: Optional[str] = None,
        allow_noncommercial: bool = False,
    ):
        self.client_wrapper = client or GeminiClientWrapper()
        self.model_name = model or config.TTS_MODEL_NAME
        self.allow_noncommercial = allow_noncommercial

    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.35,
    ) -> SceneAudio:
        output_wav = temp_dir / f"scene_{scene_index}_voice.wav"

        try:
            audio_bytes = self.client_wrapper.generate_speech_with_retry(
                text=scene.dialogue_line,
                voice_name=voice_name,
                model=self.model_name,
            )
            output_wav.write_bytes(audio_bytes)
        except Exception as e:
            logger.error("Gemini TTS synthesis failed for scene %d: %s", scene_index, e)
            raise VoiceError(f"Gemini TTS generation failed for scene {scene_index}: {e}") from e

        # Validate speech audio (16-bit WAV, valid duration, non-silent)
        duration = check_speech_audio(output_wav, scene.dialogue_line, target_sample_rate=24000)

        # Word timing alignment via faster-whisper (falls back to proportional timing with warning)
        word_timings = align_words_with_whisper(output_wav, scene.dialogue_line, duration)

        return SceneAudio(
            scene_index=scene_index,
            audio_path=output_wav,
            duration_seconds=duration,
            scene_total_duration=duration + pause_seconds,
            word_timings=word_timings,
        )

    def generate_all_voices(
        self,
        plan: ScriptPlan,
        temp_dir: Path,
    ) -> List[SceneAudio]:
        voice_pool = config.GEMINI_VOICES
        voice_map = assign_character_voices(plan, voice_pool)
        results = []
        for i, scene in enumerate(plan.scenes):
            voice = voice_map.get(scene.speaker.lower(), voice_pool[0])
            results.append(self.generate_scene_voice(i, scene, voice, temp_dir))
        return results
