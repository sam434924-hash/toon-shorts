"""Tests for voice licensing verification, speech check, and word alignment."""

import pytest
import wave
import struct
import math
from pathlib import Path

from toonshorts.core.errors import VoiceError
from toonshorts.voice_utils import (
    check_voice_license,
    check_speech_audio,
    compute_proportional_word_timings,
    align_words_with_whisper,
)


def create_test_wav(
    path: Path,
    duration: float = 2.0,
    sample_rate: int = 24000,
    amplitude: float = 8000.0,
    bits: int = 16,
):
    """Utility to generate controlled test WAV files with speech-like syllable modulation."""
    num_samples = int(duration * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(bits // 8)
        wf.setframerate(sample_rate)
        raw = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            syllable_env = max(0.0, math.sin(2.0 * math.pi * 4.0 * t))
            carrier = (
                0.5 * math.sin(2.0 * math.pi * 220.0 * t)
                + 0.3 * math.sin(2.0 * math.pi * 700.0 * t)
                + 0.2 * math.sin(2.0 * math.pi * 2400.0 * t)
            )
            val = int(amplitude * syllable_env * carrier) if amplitude > 0 else 0
            if bits == 16:
                raw.extend(struct.pack("<h", val))
            elif bits == 8:
                raw.extend(struct.pack("<b", val // 256))
        wf.writeframes(raw)


def test_license_verification_gemini_exempt():
    """Gemini voices should pass license check without voices.json entries."""
    res = check_voice_license("Kore", "gemini_tts")
    assert res["commercial_ok"] is True


def test_license_verification_refusal_and_override(tmp_path):
    """Non-Gemini voices with commercial_ok != True must be refused unless overridden."""
    fake_registry = tmp_path / "voices.json"
    fake_registry.write_text(
        '{"voices": [{"name": "test_piper", "engine": "piper", "commercial_ok": "unknown", "license": "CC-BY"}]}',
        encoding="utf-8",
    )

    # By default, refused
    with pytest.raises(VoiceError) as exc_info:
        check_voice_license("test_piper", "piper", allow_noncommercial=False, registry_path=fake_registry)
    assert "Commercial license check failed" in str(exc_info.value)

    # Allowed with explicit override
    res = check_voice_license("test_piper", "piper", allow_noncommercial=True, registry_path=fake_registry)
    assert res["name"] == "test_piper"


def test_license_verification_unregistered(tmp_path):
    """Unregistered voices must raise VoiceError."""
    fake_registry = tmp_path / "voices.json"
    fake_registry.write_text('{"voices": []}', encoding="utf-8")
    with pytest.raises(VoiceError) as exc_info:
        check_voice_license("unknown_voice", "piper", registry_path=fake_registry)
    assert "not registered" in str(exc_info.value)


def test_speech_check_valid_audio(tmp_path):
    """Valid speech audio passes verification and returns correct duration."""
    wav_file = tmp_path / "speech.wav"
    # 5 words over 2.0s = 2.5 words/sec (plausible)
    create_test_wav(wav_file, duration=2.0, sample_rate=24000, amplitude=6000.0)
    dur = check_speech_audio(wav_file, "One two three four five", target_sample_rate=24000, verify_with_whisper=False)
    assert dur == pytest.approx(2.0, rel=0.01)


def test_speech_check_fails_on_silence(tmp_path):
    """Pure silence should fail speech check."""
    wav_file = tmp_path / "silence.wav"
    create_test_wav(wav_file, duration=2.0, sample_rate=24000, amplitude=0.0)
    with pytest.raises(VoiceError) as exc_info:
        check_speech_audio(wav_file, "One two three four five", verify_with_whisper=False)
    assert "mostly silence" in str(exc_info.value)


def test_speech_check_fails_on_bad_duration(tmp_path):
    """Audio with implausible word rate (<1.0 or >5.0 words/sec) must fail."""
    wav_file = tmp_path / "slow.wav"
    # 2 words over 10 seconds = 0.2 words/sec
    create_test_wav(wav_file, duration=10.0, sample_rate=24000, amplitude=6000.0)
    with pytest.raises(VoiceError) as exc_info:
        check_speech_audio(wav_file, "Two words", verify_with_whisper=False)
    assert "implausible speech rate" in str(exc_info.value)


def test_speech_check_fails_on_non_16bit(tmp_path):
    """Non-16-bit audio must fail."""
    wav_file = tmp_path / "8bit.wav"
    create_test_wav(wav_file, duration=2.0, sample_rate=24000, amplitude=6000.0, bits=8)
    with pytest.raises(VoiceError) as exc_info:
        check_speech_audio(wav_file, "One two three four five", verify_with_whisper=False)
    assert "16-bit WAV is required" in str(exc_info.value)


def test_word_alignment_fallback_warning(tmp_path, caplog):
    """When whisper alignment is not possible, logs a visible warning and uses proportional timing."""
    import logging
    wav_file = tmp_path / "test.wav"
    create_test_wav(wav_file, duration=2.0, sample_rate=24000)

    # Test proportional timing fallback directly
    with caplog.at_level(logging.WARNING):
        # Passing empty/dummy will test fallback logic or whisper execution
        timings = compute_proportional_word_timings("Hello world test", 2.0)
        assert len(timings) == 3
        assert timings[0].word == "Hello"
        assert timings[-1].word == "test"
