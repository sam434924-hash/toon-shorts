"""
Purpose: Google Gemini text-to-speech voice plugin using current GenAI SDK.
Inputs: Scene dialogue, prebuilt Gemini voice identifiers, and destination paths.
Outputs: Generated 16-bit 24kHz WAV speech files and aligned word timestamps.
Depends on: core.client, core.config, core.errors, core.models, core.registry, hashlib, logging, pathlib, shutil, typing, voice_utils
Used by: None
Config keys: GEMINI_API_KEY, GEMINI_VOICES, TTS_CACHE_DIR, TTS_MODEL_NAME
Tests: tests/contract/test_voice_contract.py, tests/unit/test_gemini_tts_cache.py
"""

import hashlib
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from toonshorts.core import config
from toonshorts.core.errors import VoiceError
from toonshorts.core.models import ScriptPlan, Scene, SceneAudio, strip_speaker_label
from toonshorts.core.registry import VoiceInterface, register_voice
from toonshorts.core.client import GeminiClientWrapper
from toonshorts.voice_utils import (
    check_speech_audio,
    align_words_with_whisper,
    assign_character_voices,
)

logger = logging.getLogger("toonshorts.plugins.voice.gemini_tts")


def compute_tts_cache_key(text: str, voice_name: str, model_name: str) -> str:
    """
    Computes a deterministic SHA-256 hash key for TTS audio cache.
    The filename is strictly the 64-char hex hash to completely eliminate path traversal risks.
    """
    raw = f"{text.strip()}|{voice_name.strip()}|{model_name.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@register_voice("gemini_tts")
class GeminiTTSVoicePlugin(VoiceInterface):
    """Google Gemini text-to-speech plugin with sha256 disk caching, backoff, and quota protection."""
    name = "gemini_tts"

    def __init__(
        self,
        client: Optional[GeminiClientWrapper] = None,
        model: Optional[str] = None,
        allow_noncommercial: bool = False,
        cache_dir: Optional[Path] = None,
    ):
        self.client_wrapper = client or GeminiClientWrapper()
        self.model_name = model or config.TTS_MODEL_NAME
        self.allow_noncommercial = allow_noncommercial
        self.cache_dir = cache_dir or config.TTS_CACHE_DIR
        self.cache_hits: int = 0
        self.cache_misses: int = 0

    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.35,
    ) -> SceneAudio:
        clean_text = strip_speaker_label(scene.dialogue_line)
        output_wav = temp_dir / f"scene_{scene_index}_voice.wav"
        cache_key = compute_tts_cache_key(clean_text, voice_name, self.model_name)
        cached_file = self.cache_dir / f"{cache_key}.wav"







        cache_hit_valid = False
        if cached_file.is_file() and cached_file.stat().st_size > 0:
            try:
                check_speech_audio(cached_file, clean_text, target_sample_rate=24000)
                cache_hit_valid = True
            except Exception as e:
                logger.warning(
                    "Cached audio %s failed speech check (%s). Deleting invalid cache file.",
                    cached_file.name, e
                )
                try:
                    cached_file.unlink(missing_ok=True)
                except OSError:
                    pass

        if cache_hit_valid:
            logger.info("Gemini TTS cache HIT for scene %d (key: %s)", scene_index, cache_key)
            self.cache_hits += 1
            shutil.copyfile(cached_file, output_wav)
            duration = check_speech_audio(output_wav, clean_text, target_sample_rate=24000)
        else:
            if getattr(self, "cache_only", False):
                raise VoiceError(
                    f"Fast preview mode requires cached audio but found cache miss for dialogue: '{clean_text}'. Live Gemini API calls are forbidden in fast mode."
                )
            logger.info("Gemini TTS cache MISS for scene %d (key: %s) - synthesizing speech", scene_index, cache_key)
            self.cache_misses += 1
            if getattr(self.client_wrapper, "is_auto_fallback", False):
                raise VoiceError(
                    "GEMINI_API_KEY is missing. Gemini TTS requires a valid GEMINI_API_KEY to synthesize speech and will not fall back silently to mock audio."
                )
            try:
                audio_bytes = self.client_wrapper.generate_speech_with_retry(
                    text=clean_text,
                    voice_name=voice_name,
                    model=self.model_name,
                )
                if not audio_bytes.startswith(b"RIFF"):
                    import io, wave
                    buf = io.BytesIO()
                    with wave.open(buf, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(audio_bytes)
                    audio_bytes = buf.getvalue()
                
                output_wav.write_bytes(audio_bytes)
                # Verify speech before caching
                duration = check_speech_audio(output_wav, clean_text, target_sample_rate=24000)

                # Never cache mock audio in persistent cache; only cache verified real speech
                if not getattr(self.client_wrapper, "mock", False):
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    cached_file.write_bytes(audio_bytes)
            except VoiceError:
                # Quota or rate limit error: stop immediately and re-raise without retries
                raise
            except Exception as e:
                logger.error("Gemini TTS synthesis failed for scene %d: %s", scene_index, e)
                raise VoiceError(f"Gemini TTS generation failed for scene {scene_index}: {e}") from e

        # Word timing alignment via faster-whisper (falls back to proportional timing with warning)
        word_timings = align_words_with_whisper(output_wav, clean_text, duration)

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
            speaker_key = strip_speaker_label(scene.speaker).lower().strip().rstrip(":")
            voice = voice_map.get(speaker_key)
            if not voice:
                if "boy" in speaker_key:
                    voice = voice_map.get("boy") or voice_map.get("boy_b") or voice_map.get("boy_a")
                elif "girl" in speaker_key:
                    voice = voice_map.get("girl") or voice_map.get("girl_a")
            if not voice:
                voice = voice_pool[0]
            results.append(self.generate_scene_voice(i, scene, voice, temp_dir))
        return results
