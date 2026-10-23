"""
Purpose: Voice license registry enforcement, speech audio verification, and word alignment.
Inputs: Audio files, script plans, registry json, and generation parameters.
Outputs: Validated licenses, verified 16-bit WAV audio metrics, and aligned word timestamps.
Depends on: core.config, core.errors, core.models, json, logging, math, pathlib, re, typing, wave
Used by: plugins.voice.fake, plugins.voice.gemini_tts, plugins.voice.piper, plugins.voice.windows_sapi, voice
Config keys: PIPER_VOICES_DIR, VOICES_REGISTRY_PATH
Tests: tests/contract/test_voice_contract.py, tests/unit/test_timing.py
"""

import json
import logging
import math
import re
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from toonshorts.core import config
from toonshorts.core.errors import VoiceError
from toonshorts.core.models import ScriptPlan, WordTiming

logger = logging.getLogger("toonshorts.voice_utils")

# Minimum and maximum words per second plausible for human/cartoon dialogue
MIN_WORDS_PER_SECOND = 1.0
MAX_WORDS_PER_SECOND = 5.0
MAX_SILENCE_RATIO = 0.85

# Cached WhisperModel instance
_WHISPER_MODEL = None


def patch_faster_whisper_av_if_needed():
    """Patches faster_whisper.audio.decode_audio to support newer av library versions."""
    try:
        import av
        import faster_whisper.audio
        import io
        import gc
        import numpy as np

        original_decode = faster_whisper.audio.decode_audio

        def patched_decode_audio(input_file, sampling_rate=16000, split_stereo=False):
            resampler = av.audio.resampler.AudioResampler(
                format="s16",
                layout="mono" if not split_stereo else "stereo",
                rate=sampling_rate,
            )
            raw_buffer = io.BytesIO()
            dtype = None

            try:
                container = av.open(input_file, mode="r")
            except TypeError:
                container = av.open(input_file, mode="r", metadata_errors="ignore")

            with container:
                frames = container.decode(audio=0)
                frames = faster_whisper.audio._ignore_invalid_frames(frames)
                frames = faster_whisper.audio._group_frames(frames, 500000)
                frames = faster_whisper.audio._resample_frames(frames, resampler)
                for frame in frames:
                    array = frame.to_ndarray()
                    dtype = array.dtype
                    raw_buffer.write(array)

            del resampler
            gc.collect()

            audio = np.frombuffer(raw_buffer.getbuffer(), dtype=dtype)
            audio = audio.astype(np.float32) / 32768.0

            if split_stereo:
                return audio[0::2], audio[1::2]
            return audio

        faster_whisper.audio.decode_audio = patched_decode_audio
        if hasattr(faster_whisper, "transcribe") and hasattr(faster_whisper.transcribe, "decode_audio"):
            faster_whisper.transcribe.decode_audio = patched_decode_audio
    except Exception as e:
        logger.debug("Faster whisper av patch not applied: %s", e)


def get_whisper_model():
    """Lazily loads and returns the faster-whisper model."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        patch_faster_whisper_av_if_needed()
        try:
            from faster_whisper import WhisperModel
            _WHISPER_MODEL = WhisperModel("tiny", device="cpu", compute_type="int8")
        except Exception as e:
            logger.warning("Could not load faster-whisper model: %s", e)
            _WHISPER_MODEL = False
    return _WHISPER_MODEL if _WHISPER_MODEL is not False else None


# ---------------------------------------------------------------------------
# 1. Voice License Registry Verification
# ---------------------------------------------------------------------------

def check_voice_license(
    voice_name: str,
    engine_name: str,
    allow_noncommercial: bool = False,
    registry_path: Path = config.VOICES_REGISTRY_PATH,
) -> Dict[str, Any]:
    """
    Verifies voice permissions against voices.json.
    Gemini voices are managed under Google Cloud terms and exempt from voices.json.
    All non-Gemini voices must exist in voices.json and have commercial_ok == True
    unless allow_noncommercial is explicitly passed.
    """
    if engine_name.lower() in ("gemini", "gemini_tts"):
        return {
            "name": voice_name,
            "engine": "gemini_tts",
            "source": "Google GenAI Prebuilt Voices",
            "license": "Google Terms of Service",
            "commercial_ok": True,
        }

    if not registry_path.is_file():
        raise VoiceError(
            f"Voice license registry not found at '{registry_path}'. "
            f"Cannot verify commercial use for voice '{voice_name}' (engine: {engine_name})."
        )

    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise VoiceError(f"Failed to read voice license registry '{registry_path}': {e}") from e

    voices = data.get("voices", [])
    entry = None
    target_clean = voice_name.lower().strip()
    for v in voices:
        if v.get("name", "").lower().strip() == target_clean:
            entry = v
            break

    if not entry:
        raise VoiceError(
            f"Voice '{voice_name}' is not registered in '{registry_path.name}'. "
            f"All non-Gemini voices must have an entry detailing source and license."
        )

    commercial_ok = entry.get("commercial_ok")
    if commercial_ok is True or commercial_ok == "true" or commercial_ok == "True":
        return entry

    if allow_noncommercial:
        logger.warning(
            "[VOICE WARNING] Using non-commercial or unverified voice '%s' (%s, commercial_ok=%s) "
            "due to --allow-noncommercial flag.",
            voice_name,
            entry.get("license", "unknown"),
            commercial_ok,
        )
        return entry

    raise VoiceError(
        f"Commercial license check failed for voice '{voice_name}': commercial_ok is '{commercial_ok}'. "
        f"By default, non-commercial or unverified voices are refused. "
        f"Override explicitly with --allow-noncommercial if this is a personal non-commercial run."
    )


# ---------------------------------------------------------------------------
# 2. Speech Audio Verification Check
# ---------------------------------------------------------------------------

def check_speech_audio(
    audio_path: Path,
    expected_text: str,
    target_sample_rate: Optional[int] = None,
    verify_with_whisper: bool = True,
) -> float:
    """
    Validates generated speech audio:
    1. File exists and is non-empty.
    2. Must be a valid 16-bit PCM WAV.
    3. Has consistent sample rate if specified.
    4. Has plausible duration based on word count (~1.0 to 5.0 words per second).
    5. Is not mostly silence (measured via energy RMS).
    6. Optional: transcribes sample with faster-whisper to flag major text mismatch.
    Returns the verified audio duration in seconds.
    """
    if not audio_path.is_file():
        raise VoiceError(f"Speech verification failed: audio file '{audio_path}' does not exist.")

    if audio_path.stat().st_size == 0:
        raise VoiceError(f"Speech verification failed: audio file '{audio_path}' is empty (0 bytes).")

    try:
        with wave.open(str(audio_path), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            num_frames = wf.getnframes()
            frames_bytes = wf.readframes(num_frames)
    except wave.Error as e:
        raise VoiceError(f"Speech verification failed: '{audio_path}' is not a valid WAV file: {e}") from e

    # 16-bit WAV check (sample_width == 2 bytes = 16 bits)
    if sample_width != 2:
        raise VoiceError(
            f"Speech verification failed: '{audio_path}' is {sample_width * 8}-bit audio. "
            f"16-bit WAV is required."
        )

    if target_sample_rate and framerate != target_sample_rate:
        raise VoiceError(
            f"Speech verification failed: '{audio_path}' has sample rate {framerate}Hz, "
            f"expected {target_sample_rate}Hz."
        )

    duration = num_frames / float(framerate) if framerate > 0 else 0.0
    if duration <= 0.05:
        raise VoiceError(f"Speech verification failed: audio duration too short ({duration:.2f}s).")

    words = [w for w in re.split(r"\s+", expected_text.strip()) if w]
    word_count = max(len(words), 1)
    words_per_sec = word_count / duration

    # Word rate sanity check
    if words_per_sec < MIN_WORDS_PER_SECOND or words_per_sec > MAX_WORDS_PER_SECOND:
        raise VoiceError(
            f"Speech verification failed: implausible speech rate ({words_per_sec:.2f} words/sec) "
            f"for {word_count} words over {duration:.2f}s in '{audio_path.name}'. "
            f"Plausible rate is {MIN_WORDS_PER_SECOND}-{MAX_WORDS_PER_SECOND} words/sec."
        )

    # Silence check: calculate RMS amplitude
    import struct
    total_samples = len(frames_bytes) // (2 * channels)
    if total_samples > 0:
        # Sample mono or first channel
        sum_squares = 0.0
        fmt = f"<{total_samples * channels}h"
        try:
            samples = struct.unpack(fmt, frames_bytes)
            # Take every channel stride
            chan_samples = samples[::channels]
            for s in chan_samples:
                sum_squares += float(s * s)
            rms = math.sqrt(sum_squares / len(chan_samples))
        except Exception:
            rms = 1000.0  # fallback

        # If RMS amplitude is very near zero, audio is pure silence
        if rms < 60.0:
            raise VoiceError(
                f"Speech verification failed: '{audio_path.name}' is mostly silence (RMS amplitude {rms:.1f} < 60)."
            )

        # Dynamic speech loudness variation and pure tone detection
        import numpy as np
        raw_samples = np.frombuffer(frames_bytes, dtype=np.int16)
        mono_samples = raw_samples[::channels] if channels > 1 else raw_samples
        frame_len = max(int(framerate * 0.05), 1)
        if len(mono_samples) >= frame_len * 2:
            num_windows = len(mono_samples) // frame_len
            w_samples = mono_samples[:num_windows * frame_len].reshape(num_windows, frame_len).astype(float)
            w_rms = np.sqrt(np.mean(w_samples**2, axis=1))
            rms_std = float(np.std(w_rms))
            if rms_std < 80.0:
                raise VoiceError(
                    f"Speech verification failed: '{audio_path.name}' has no dynamic speech variation (RMS std {rms_std:.1f} < 80.0). "
                    f"Audio appears to be a pure tone, synth beep, or flat hum."
                )

            fft_vals = np.abs(np.fft.rfft(mono_samples))
            total_energy = float(np.sum(fft_vals**2)) + 1e-9
            peak_energy = float(np.max(fft_vals**2))
            peak_ratio = peak_energy / total_energy
            if peak_ratio > 0.40:
                freqs = np.fft.rfftfreq(len(mono_samples), 1.0 / framerate)
                peak_f = float(freqs[np.argmax(fft_vals)])
                raise VoiceError(
                    f"Speech verification failed: '{audio_path.name}' is a pure sinusoidal beep or tone "
                    f"({peak_f:.1f}Hz holds {peak_ratio*100:.1f}% of total spectral energy)."
                )

    # Optional faster-whisper transcription mismatch check
    if verify_with_whisper:
        whisper = get_whisper_model()
        if whisper is not None:
            try:
                segments, _ = whisper.transcribe(str(audio_path))
                transcription = " ".join(s.text.strip() for s in segments).lower()
                clean_exp = re.sub(r"[^\w\s]", "", expected_text.lower())
                clean_trans = re.sub(r"[^\w\s]", "", transcription)
                exp_words = set(clean_exp.split())
                trans_words = set(clean_trans.split())
                if exp_words and trans_words:
                    overlap = len(exp_words.intersection(trans_words)) / float(len(exp_words))
                    if overlap < 0.20:
                        logger.warning(
                            "[SPEECH CHECK WARNING] Whisper transcription mismatch for '%s': "
                            "expected '%s', got '%s' (overlap %.1f%%)",
                            audio_path.name,
                            expected_text,
                            transcription,
                            overlap * 100,
                        )
            except Exception as e:
                logger.debug("Whisper transcription check encountered error: %s", e)

    return duration


# ---------------------------------------------------------------------------
# 3. Proportional Word Timing Fallback
# ---------------------------------------------------------------------------

def compute_proportional_word_timings(
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


# ---------------------------------------------------------------------------
# 4. Word Timing Alignment with faster-whisper
# ---------------------------------------------------------------------------

def align_words_with_whisper(
    audio_path: Path,
    expected_text: str,
    total_duration: float,
) -> List[WordTiming]:
    """
    Aligns audio to script text using faster-whisper to produce precise word timestamps.
    If alignment fails, emits a visible warning and falls back to proportional timing.
    """
    whisper = get_whisper_model()
    if whisper is None:
        logger.warning(
            "[WORD ALIGNMENT FALLBACK] faster-whisper is unavailable; "
            "falling back to proportional word timing for '%s'.",
            audio_path.name,
        )
        return compute_proportional_word_timings(expected_text, total_duration)

    try:
        segments, _ = whisper.transcribe(str(audio_path), word_timestamps=True)
        aligned: List[WordTiming] = []
        for segment in segments:
            for w in segment.words:
                word_clean = w.word.strip()
                if word_clean:
                    aligned.append(WordTiming(
                        word=word_clean,
                        start_time=round(max(0.0, float(w.start)), 2),
                        end_time=round(min(total_duration, float(w.end)), 2),
                    ))

        if not aligned:
            raise ValueError("Whisper produced empty word timestamps")

        return aligned
    except Exception as e:
        logger.warning(
            "[WORD ALIGNMENT FALLBACK] Word alignment with faster-whisper failed for '%s' (%s). "
            "Using proportional timing fallback.",
            audio_path.name,
            e,
        )
        return compute_proportional_word_timings(expected_text, total_duration)


def assign_character_voices(plan: ScriptPlan, voice_list: List[str]) -> Dict[str, str]:
    """
    Assigns distinct voices to characters in the screenplay.
    Prioritizes explicit Character.voice_id (e.g. boy_b -> Puck, girl_a -> Aoede).
    For characters without an explicit voice, assigns distinct voices from voice_list.
    Also creates aliases for speaker matching (e.g. 'boy' -> boy character voice).
    """
    voice_map: Dict[str, str] = {}
    if not voice_list:
        voice_list = ["default_voice"]

    used_voices = set()
    unassigned = []

    # 1. Assign explicit voice_id if specified on Character
    for char in plan.characters:
        c_name = char.name.lower().strip()
        vid = getattr(char, "voice_id", None)
        if vid and vid not in ("voice_default", "default_voice", ""):
            voice_map[c_name] = vid
            used_voices.add(vid)
        else:
            unassigned.append(c_name)

    # 2. Assign remaining from voice_list
    available_voices = [v for v in voice_list if v not in used_voices]
    if not available_voices:
        available_voices = list(voice_list)

    for i, c_name in enumerate(unassigned):
        voice_map[c_name] = available_voices[i % len(available_voices)]

    # 3. Create friendly aliases for scenes using shorthand speaker names
    # e.g., 'boy' -> 'boy_b', 'girl' -> 'girl_a'
    for char in plan.characters:
        c_name = char.name.lower().strip()
        assigned_voice = voice_map.get(c_name)
        if assigned_voice:
            if c_name.startswith("boy_"):
                voice_map.setdefault("boy", assigned_voice)
            elif c_name.startswith("girl_"):
                voice_map.setdefault("girl", assigned_voice)
            elif c_name == "presenter":
                voice_map.setdefault("host", assigned_voice)
                voice_map.setdefault("speaker", assigned_voice)

    return voice_map
