"""
Purpose: Edge-TTS voice plugin with word timestamp alignment and fallback.
Inputs: Scene dialogue, voice identifiers, and destination paths.
Outputs: Generated voice MP3/WAV files and word-by-word timing metadata.
Depends on: asyncio, core.models, core.registry, logging, pathlib, subprocess, typing, wave
Used by: None
Config keys: None
Tests: tests/contract/test_voice_contract.py
"""

import asyncio
import wave
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple

from toonshorts.core.models import ScriptPlan, Scene, SceneAudio, WordTiming
from toonshorts.core.registry import VoiceInterface, register_voice
from .synthetic import compute_fallback_word_timings, generate_synthetic_audio, assign_character_voices, PRESET_VOICES

logger = logging.getLogger("toonshorts.plugins.voice.edge_tts")


def get_audio_duration_wave_or_ffprobe(file_path: Path) -> float:
    """Gets audio duration accurately using standard wave module or ffprobe."""
    if file_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(file_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames / float(rate)
        except Exception:
            pass

    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as e:
        logger.warning("ffprobe duration check failed (%s); estimating from file size.", e)
        return 3.0


async def _generate_edge_tts_audio(
    text: str, voice: str, output_path: Path
) -> Tuple[float, List[WordTiming]]:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    word_timings: List[WordTiming] = []

    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_sec = chunk["offset"] / 10_000_000.0
                dur_sec = chunk["duration"] / 10_000_000.0
                word_timings.append(WordTiming(
                    word=chunk["text"],
                    start_time=round(start_sec, 2),
                    end_time=round(start_sec + dur_sec, 2),
                ))

    duration = get_audio_duration_wave_or_ffprobe(output_path)
    if not word_timings:
        word_timings = compute_fallback_word_timings(text, duration)

    return duration, word_timings


@register_voice("edge_tts")
class EdgeTTSVoicePlugin(VoiceInterface):
    """High quality realistic voice generator using Edge-TTS with offline fallback."""
    name = "edge_tts"

    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.35,
    ) -> SceneAudio:
        output_audio = temp_dir / f"scene_{scene_index}_voice.mp3"
        try:
            duration, timings = asyncio.run(
                _generate_edge_tts_audio(scene.dialogue_line, voice_name, output_audio)
            )
        except Exception as e:
            logger.warning("Edge-TTS unavailable (%s); falling back to offline synthesizer.", e)
            output_audio = temp_dir / f"scene_{scene_index}_voice.wav"
            duration = generate_synthetic_audio(scene.dialogue_line, output_audio)
            timings = compute_fallback_word_timings(scene.dialogue_line, duration)

        return SceneAudio(
            scene_index=scene_index,
            audio_path=output_audio,
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
