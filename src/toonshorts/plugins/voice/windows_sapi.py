"""
Purpose: Local Windows SAPI voice plugin using pyttsx3 for offline testing.
Inputs: Scene dialogue lines and output audio file paths.
Outputs: Generated 16-bit WAV audio files and aligned word timestamps.
Depends on: core.errors, core.models, core.registry, logging, pathlib, pyttsx3, typing, voice_utils
Used by: None
Config keys: None
Tests: tests/contract/test_voice_contract.py
"""

import logging
from pathlib import Path
from typing import List, Optional

from toonshorts.core.errors import VoiceError
from toonshorts.core.models import ScriptPlan, Scene, SceneAudio
from toonshorts.core.registry import VoiceInterface, register_voice
from toonshorts.voice_utils import (
    check_speech_audio,
    check_voice_license,
    align_words_with_whisper,
    assign_character_voices,
)

logger = logging.getLogger("toonshorts.plugins.voice.windows_sapi")


@register_voice("windows_sapi")
class WindowsSAPIVoicePlugin(VoiceInterface):
    """Local Windows SAPI voices via pyttsx3 for testing."""
    name = "windows_sapi"

    def __init__(self, allow_noncommercial: bool = False):
        self.allow_noncommercial = allow_noncommercial

    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.35,
    ) -> SceneAudio:
        # Check license in voices.json
        check_voice_license(voice_name, "windows_sapi", allow_noncommercial=self.allow_noncommercial)

        try:
            import pyttsx3
        except ImportError as e:
            raise VoiceError(f"pyttsx3 is not installed: {e}") from e

        output_wav = temp_dir / f"scene_{scene_index}_sapi.wav"

        try:
            engine = pyttsx3.init()
            installed_voices = engine.getProperty("voices")
            # Match voice by name token or use first available
            matched_id = None
            for v in installed_voices:
                if voice_name.lower() in v.name.lower() or voice_name.lower() in v.id.lower():
                    matched_id = v.id
                    break

            if matched_id:
                engine.setProperty("voice", matched_id)
            elif installed_voices:
                engine.setProperty("voice", installed_voices[0].id)

            engine.save_to_file(scene.dialogue_line, str(output_wav))
            engine.runAndWait()
        except Exception as e:
            raise VoiceError(f"Windows SAPI generation failed: {e}") from e

        # Validate speech audio
        duration = check_speech_audio(output_wav, scene.dialogue_line)

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
        voice_pool = ["david", "zira", "hazel"]
        voice_map = assign_character_voices(plan, voice_pool)
        results = []
        for i, scene in enumerate(plan.scenes):
            voice = voice_map.get(scene.speaker.lower(), voice_pool[0])
            results.append(self.generate_scene_voice(i, scene, voice, temp_dir))
        return results
