"""
Purpose: Offline synthetic tone audio speech synthesizer and timing engine.
Inputs: Scene dialogue lines and output file destinations.
Outputs: Generated WAV audio and aligned WordTiming lists.
Depends on: core.models, core.registry, math, pathlib, struct, typing, wave
Used by: plugins.voice.edge_tts, voice
Config keys: None
Tests: tests/contract/test_voice_contract.py, tests/unit/test_timing.py
"""

import math
import wave
import struct
from pathlib import Path
from typing import List, Dict
from toonshorts.core.models import ScriptPlan, Scene, SceneAudio, WordTiming
from toonshorts.core.registry import VoiceInterface, register_voice

PRESET_VOICES = [
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-US-ChristopherNeural",
    "en-US-AriaNeural",
    "en-US-EricNeural",
]


def assign_character_voices(plan: ScriptPlan) -> Dict[str, str]:
    """Maps characters to distinct voice personas."""
    voice_map = {}
    for i, char in enumerate(plan.characters):
        voice_map[char.name.lower()] = PRESET_VOICES[i % len(PRESET_VOICES)]
    return voice_map


def compute_fallback_word_timings(
    text: str, total_duration: float, start_offset: float = 0.0
) -> List[WordTiming]:
    """Proportionally distributes duration across words based on character weight."""
    words = [w.strip() for w in text.split() if w.strip()]
    if not words:
        return []

    weights = []
    for w in words:
        weight = max(len(w), 1)
        if any(w.endswith(p) for p in [".", "!", "?", ",", ";", ":"]):
            weight += 2
        weights.append(weight)

    total_weight = sum(weights)
    current_time = start_offset
    timings = []

    for word, w in zip(words, weights):
        duration = (w / total_weight) * total_duration
        timings.append(WordTiming(
            word=word,
            start_time=round(current_time, 2),
            end_time=round(current_time + duration, 2),
        ))
        current_time += duration

    return timings


def generate_synthetic_audio(text: str, output_path: Path) -> float:
    """Generates synthetic audio waveform and returns duration in seconds."""
    words = text.split()
    word_count = max(len(words), 1)
    duration = max(word_count * 0.38, 1.8)
    sample_rate = 24000
    num_samples = int(duration * sample_rate)

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw_bytes = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            freq = 240.0 + 80.0 * math.sin(2.0 * math.pi * 3.5 * t)
            envelope = math.sin(math.pi * (t / duration))
            val = int(envelope * 12000.0 * math.sin(2.0 * math.pi * freq * t))
            raw_bytes.extend(struct.pack("<h", val))
        wf.writeframes(raw_bytes)

    return duration


@register_voice("synthetic")
class SyntheticVoicePlugin(VoiceInterface):
    """Offline voice synthesizer producing cartoon tone audio tracks."""
    name = "synthetic"

    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.35,
    ) -> SceneAudio:
        out_wav = temp_dir / f"scene_{scene_index}_synth.wav"
        duration = generate_synthetic_audio(scene.dialogue_line, out_wav)
        timings = compute_fallback_word_timings(scene.dialogue_line, duration)
        return SceneAudio(
            scene_index=scene_index,
            audio_path=out_wav,
            duration_seconds=duration,
            scene_total_duration=duration + pause_seconds,
            word_timings=timings,
        )

    def generate_all_voices(
        self,
        plan: ScriptPlan,
        temp_dir: Path,
    ) -> List[SceneAudio]:
        voice_map = assign_character_voices(plan)
        results = []
        for i, scene in enumerate(plan.scenes):
            voice = voice_map.get(scene.speaker.lower(), PRESET_VOICES[0])
            results.append(self.generate_scene_voice(i, scene, voice, temp_dir))
        return results
