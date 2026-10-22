"""Unit tests for Gemini TTS disk caching, quota abort, speech verification, and cache key security."""

import io
import math
import re
import struct
import wave
from pathlib import Path
import pytest

from toonshorts.core import config
from toonshorts.core.errors import VoiceError
from toonshorts.core.models import Scene, Pose, CameraMove, Transition
from toonshorts.plugins.voice.gemini_tts import GeminiTTSVoicePlugin, compute_tts_cache_key
from toonshorts.voice_utils import check_speech_audio


def test_cache_key_deterministic_and_safe():
    """Verify cache keys are deterministic 64-hex SHA-256 strings with no path traversal risks."""
    key1 = compute_tts_cache_key("What is an API?", "Kore", "gemini-3.8-flash-tts")
    key2 = compute_tts_cache_key("What is an API?", "Kore", "gemini-3.8-flash-tts")
    assert key1 == key2
    assert re.match(r"^[0-9a-f]{64}$", key1) is not None

    # Path traversal attempts in input must not produce unsafe keys
    malicious_key = compute_tts_cache_key("../../../etc/passwd", "Kore", "gemini-3.8-flash-tts")
    assert re.match(r"^[0-9a-f]{64}$", malicious_key) is not None
    assert "/" not in malicious_key
    assert "\\" not in malicious_key
    assert ".." not in malicious_key

    # Different inputs must produce different keys
    key_diff_voice = compute_tts_cache_key("What is an API?", "Puck", "gemini-3.8-flash-tts")
    key_diff_text = compute_tts_cache_key("Different text", "Kore", "gemini-3.8-flash-tts")
    assert key1 != key_diff_voice
    assert key1 != key_diff_text


def _create_dummy_speech_wav_bytes(duration_sec: float = 2.0, sample_rate: int = 24000) -> bytes:
    """Helper creating valid 16-bit mono 24kHz WAV bytes with modulated speech formants for testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        n_samples = int(duration_sec * sample_rate)
        raw = bytearray()
        for i in range(n_samples):
            t = float(i) / sample_rate
            syllable_env = max(0.0, math.sin(2.0 * math.pi * 4.0 * t))
            carrier = (
                0.5 * math.sin(2.0 * math.pi * 220.0 * t)
                + 0.3 * math.sin(2.0 * math.pi * 700.0 * t)
                + 0.2 * math.sin(2.0 * math.pi * 2400.0 * t)
            )
            val = int(8000.0 * syllable_env * carrier)
            raw.extend(struct.pack("<h", val))
        wf.writeframes(raw)
    return buf.getvalue()


def _create_pure_tone_wav_bytes(duration_sec: float = 2.0, freq_hz: float = 320.0, sample_rate: int = 24000) -> bytes:
    """Helper creating a flat, unmodulated sinusoidal beep."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        n_samples = int(duration_sec * sample_rate)
        raw = bytearray()
        for i in range(n_samples):
            t = float(i) / sample_rate
            val = int(8000.0 * math.sin(2.0 * math.pi * freq_hz * t))
            raw.extend(struct.pack("<h", val))
        wf.writeframes(raw)
    return buf.getvalue()


def _create_silent_wav_bytes(duration_sec: float = 2.0, sample_rate: int = 24000) -> bytes:
    """Helper creating a zero-amplitude silent WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = bytearray(int(duration_sec * sample_rate * 2))
        wf.writeframes(raw)
    return buf.getvalue()


class MockGeminiClientWrapper:
    def __init__(self, should_fail_quota: bool = False, audio_type: str = "speech"):
        self.call_count = 0
        self.should_fail_quota = should_fail_quota
        self.audio_type = audio_type
        self.mock = False  # Allows cache writing in tests when valid

    def generate_speech_with_retry(self, text: str, voice_name: str, model: str, **kwargs) -> bytes:
        self.call_count += 1
        if self.should_fail_quota:
            raise VoiceError("Gemini TTS quota or rate limit exceeded: 429 ResourceExhausted")
        word_count = max(len(text.split()), 1)
        dur = max(word_count * 0.40, 1.5)
        if self.audio_type == "pure_tone":
            return _create_pure_tone_wav_bytes(duration_sec=dur, freq_hz=320.0)
        elif self.audio_type == "silence":
            return _create_silent_wav_bytes(duration_sec=dur)
        return _create_dummy_speech_wav_bytes(duration_sec=dur)


def test_cache_miss_then_hit(tmp_path):
    """Verify first request generates audio and writes cache (miss), second request reuses cache (hit)."""
    cache_dir = tmp_path / "tts_cache"
    temp_dir = tmp_path / "run_temp"
    temp_dir.mkdir()

    mock_client = MockGeminiClientWrapper(should_fail_quota=False)
    plugin = GeminiTTSVoicePlugin(
        client=mock_client,
        model="gemini-3.8-flash-tts",
        cache_dir=cache_dir,
    )

    scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="Welcome to our whiteboard explainer.",
        action="Host welcomes audience",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )

    # 1. First execution: Cache MISS
    audio1 = plugin.generate_scene_voice(0, scene, "Kore", temp_dir)
    assert plugin.cache_misses == 1
    assert plugin.cache_hits == 0
    assert mock_client.call_count == 1
    assert audio1.audio_path.is_file()

    expected_key = compute_tts_cache_key(scene.dialogue_line, "Kore", "gemini-3.8-flash-tts")
    cached_file = cache_dir / f"{expected_key}.wav"
    assert cached_file.is_file()
    assert cached_file.stat().st_size > 0

    # 2. Second execution with same parameters: Cache HIT
    audio2 = plugin.generate_scene_voice(0, scene, "Kore", temp_dir)
    assert plugin.cache_misses == 1
    assert plugin.cache_hits == 1
    # Mock client call count must NOT have increased!
    assert mock_client.call_count == 1
    assert audio2.audio_path.is_file()
    assert audio2.audio_path.stat().st_size == cached_file.stat().st_size


def test_quota_error_stops_immediately_without_retries(tmp_path):
    """Verify quota/rate limit error stops immediately and raises VoiceError without looping."""
    cache_dir = tmp_path / "tts_cache"
    temp_dir = tmp_path / "run_temp"
    temp_dir.mkdir()

    mock_client = MockGeminiClientWrapper(should_fail_quota=True)
    plugin = GeminiTTSVoicePlugin(
        client=mock_client,
        model="gemini-3.8-flash-tts",
        cache_dir=cache_dir,
    )

    scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="This scene triggers a quota error.",
        action="Host encounters rate limit",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )

    with pytest.raises(VoiceError) as exc_info:
        plugin.generate_scene_voice(0, scene, "Kore", temp_dir)

    assert "quota or rate limit exceeded" in str(exc_info.value).lower()
    # Ensure it only attempted once and did not loop retries
    assert mock_client.call_count == 1


def test_pure_tone_audio_rejected_and_never_cached(tmp_path):
    """Verify check_speech_audio rejects pure tone beeps and prevents caching."""
    tone_path = tmp_path / "beep_test.wav"
    tone_path.write_bytes(_create_pure_tone_wav_bytes(duration_sec=2.0, freq_hz=320.0))

    with pytest.raises(VoiceError) as exc_info:
        check_speech_audio(tone_path, "This is speech text.")

    err_msg = str(exc_info.value).lower()
    assert "pure" in err_msg or "beep" in err_msg or "variation" in err_msg

    # Also verify plugin stops and does not cache if a pure tone is returned
    cache_dir = tmp_path / "tts_cache"
    temp_dir = tmp_path / "temp_run"
    temp_dir.mkdir()
    beep_client = MockGeminiClientWrapper(should_fail_quota=False, audio_type="pure_tone")
    plugin = GeminiTTSVoicePlugin(client=beep_client, cache_dir=cache_dir)
    scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="Testing beep rejection.",
        action="Host test",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )

    with pytest.raises(VoiceError):
        plugin.generate_scene_voice(0, scene, "Kore", temp_dir)

    # Nothing must be cached!
    cache_key = compute_tts_cache_key(scene.dialogue_line, "Kore", config.TTS_MODEL_NAME)
    assert not (cache_dir / f"{cache_key}.wav").exists()


def test_silent_audio_rejected_and_never_cached(tmp_path):
    """Verify check_speech_audio rejects silent audio files."""
    silence_path = tmp_path / "silent_test.wav"
    silence_path.write_bytes(_create_silent_wav_bytes(duration_sec=2.0))

    with pytest.raises(VoiceError) as exc_info:
        check_speech_audio(silence_path, "This is speech text.")

    assert "silence" in str(exc_info.value).lower()


def test_corrupt_or_beep_cache_file_deleted_and_regenerated(tmp_path):
    """Verify that if a beep file is in cache, it is deleted and regenerated with real speech."""
    cache_dir = tmp_path / "tts_cache"
    cache_dir.mkdir()
    temp_dir = tmp_path / "temp_run"
    temp_dir.mkdir()

    scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="A corrupt beep in cache should be purged.",
        action="Host test",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )
    cache_key = compute_tts_cache_key(scene.dialogue_line, "Kore", "gemini-3.8-flash-tts")
    beep_file = cache_dir / f"{cache_key}.wav"
    # Seed cache with bad beep
    beep_file.write_bytes(_create_pure_tone_wav_bytes(duration_sec=2.0, freq_hz=320.0))
    assert beep_file.is_file()

    # Good client that returns valid speech
    good_client = MockGeminiClientWrapper(should_fail_quota=False, audio_type="speech")
    plugin = GeminiTTSVoicePlugin(client=good_client, model="gemini-3.8-flash-tts", cache_dir=cache_dir)

    audio = plugin.generate_scene_voice(0, scene, "Kore", temp_dir)
    # The cache miss must have been triggered because cached beep was rejected
    assert plugin.cache_misses == 1
    assert good_client.call_count == 1
    # Cached file must now be valid speech
    assert beep_file.is_file()
    dur = check_speech_audio(beep_file, scene.dialogue_line)
    assert dur > 0.5


def test_raw_pcm_automatically_wrapped_in_wav(tmp_path):
    """Verify raw PCM bytes without a WAV header are automatically converted to valid 16-bit 24kHz WAV."""
    cache_dir = tmp_path / "tts_cache"
    temp_dir = tmp_path / "run_temp"
    temp_dir.mkdir()

    class MockRawPcmClient:
        def __init__(self):
            self.call_count = 0
            self.mock = False

        def generate_speech_with_retry(self, text: str, voice_name: str, model: str, **kwargs) -> bytes:
            self.call_count += 1
            # 2.0s of raw 16-bit 24kHz PCM with speech formants (no RIFF header)
            n_samples = 48000
            raw = bytearray()
            for i in range(n_samples):
                t = float(i) / 24000.0
                syllable_env = max(0.0, math.sin(2.0 * math.pi * 4.0 * t))
                carrier = 0.5 * math.sin(2.0 * math.pi * 220.0 * t) + 0.3 * math.sin(2.0 * math.pi * 700.0 * t)
                val = int(8000.0 * syllable_env * carrier)
                raw.extend(struct.pack("<h", val))
            return bytes(raw)

    mock_client = MockRawPcmClient()
    plugin = GeminiTTSVoicePlugin(
        client=mock_client,
        model="gemini-3.8-flash-tts",
        cache_dir=cache_dir,
    )

    scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="Raw PCM dialogue test without RIFF.",
        action="Host tests raw PCM",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )

    audio = plugin.generate_scene_voice(0, scene, "Kore", temp_dir)
    assert audio.audio_path.is_file()
    with wave.open(str(audio.audio_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 24000
        assert wf.getnframes() == 48000
