"""
Purpose: Rapid deterministic offline voice generator for test suites.
Inputs: Scene dialogue lines and temporary directories.
Outputs: Lightweight WAV files and deterministic WordTiming lists.
Depends on: core.models, core.registry, pathlib, typing, wave
Used by: None
Config keys: None
Tests: tests/contract/test_voice_contract.py, tests/smoke/test_smoke_pipeline.py
"""

import wave
from pathlib import Path
from typing import List
from toonshorts.core.models import ScriptPlan, Scene, SceneAudio, WordTiming
from toonshorts.core.registry import VoiceInterface, register_voice


@register_voice("fake")
class FakeVoicePlugin(VoiceInterface):
    """Zero-overhead mock voice plugin generating instantaneous audio for smoke tests."""
    name = "fake"

    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.2,
    ) -> SceneAudio:
        audio_path = temp_dir / f"fake_voice_{scene_index}.wav"
        # Generate 0.5s of valid silence/tone
        sample_rate = 8000
        duration = 0.5
        num_samples = int(sample_rate * duration)
        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * num_samples)

        words = scene.dialogue_line.split() or ["Hello"]
        timings = [
            WordTiming(word=w, start_time=round(i * 0.1, 2), end_time=round((i + 1) * 0.1, 2))
            for i, w in enumerate(words)
        ]

        return SceneAudio(
            scene_index=scene_index,
            audio_path=audio_path,
            duration_seconds=duration,
            scene_total_duration=duration + pause_seconds,
            word_timings=timings,
        )

    def generate_all_voices(
        self,
        plan: ScriptPlan,
        temp_dir: Path,
    ) -> List[SceneAudio]:
        return [
            self.generate_scene_voice(i, scene, "fake_voice", temp_dir)
            for i, scene in enumerate(plan.scenes)
        ]
