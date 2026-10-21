"""
Purpose: Deterministic mock voice generator for rapid test suite execution.
Inputs: Scene dialogue lines and temporary directories.
Outputs: Validated 16-bit PCM WAV audio and word timings.
Depends on: core.models, core.registry, pathlib, typing, voice_utils, wave
Used by: None
Config keys: None
Tests: tests/contract/test_voice_contract.py
"""

import math
import struct
import wave
from pathlib import Path
from typing import List

from toonshorts.core.models import ScriptPlan, Scene, SceneAudio, WordTiming
from toonshorts.core.registry import VoiceInterface, register_voice
from toonshorts.voice_utils import (
    compute_proportional_word_timings,
    check_speech_audio,
    assign_character_voices,
)


def _write_fake_speech_wav(output_path: Path, text: str) -> float:
    """Generates a valid 16-bit WAV with moderate energy (not silence) for tests."""
    words = text.split()
    word_count = max(len(words), 1)
    duration = word_count * 0.40  # 2.5 words per second (plausible rate)
    sample_rate = 24000
    num_samples = int(duration * sample_rate)

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw_bytes = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Harmonic tone simulating voice formant
            val = int(8000.0 * math.sin(2.0 * math.pi * 300.0 * t))
            raw_bytes.extend(struct.pack("<h", val))
        wf.writeframes(raw_bytes)

    return duration


@register_voice("fake")
class FakeVoicePlugin(VoiceInterface):
    """Deterministic offline mock voice generator for tests."""
    name = "fake"

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
        output_path = temp_dir / f"scene_{scene_index}_fake.wav"
        duration = _write_fake_speech_wav(output_path, scene.dialogue_line)
        check_speech_audio(output_path, scene.dialogue_line, target_sample_rate=24000, verify_with_whisper=False)
        timings = compute_proportional_word_timings(scene.dialogue_line, duration)

        return SceneAudio(
            scene_index=scene_index,
            audio_path=output_path,
            duration_seconds=duration,
            scene_total_duration=duration + pause_seconds,
            word_timings=timings,
        )

    def generate_all_voices(
        self,
        plan: ScriptPlan,
        temp_dir: Path,
    ) -> List[SceneAudio]:
        voice_map = assign_character_voices(plan, ["mock_voice_a", "mock_voice_b"])
        results = []
        for i, scene in enumerate(plan.scenes):
            voice = voice_map.get(scene.speaker.lower(), "mock_voice_a")
            results.append(self.generate_scene_voice(i, scene, voice, temp_dir))
        return results
