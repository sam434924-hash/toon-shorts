"""
Purpose: Compatibility re-export of voice types, timing functions, and speech verification.
Inputs: Voice text and duration timings.
Outputs: Word timings, SceneAudio, and verification utilities.
Depends on: core.models, voice_utils
Used by: None
Config keys: None
Tests: tests/unit/test_timing.py
"""

from .core.models import WordTiming, SceneAudio
from .voice_utils import (
    compute_proportional_word_timings,
    align_words_with_whisper,
    check_speech_audio,
    check_voice_license,
    assign_character_voices,
)

# Backward compatibility alias
compute_fallback_word_timings = compute_proportional_word_timings

__all__ = [
    "WordTiming",
    "SceneAudio",
    "compute_proportional_word_timings",
    "compute_fallback_word_timings",
    "align_words_with_whisper",
    "check_speech_audio",
    "check_voice_license",
    "assign_character_voices",
]
