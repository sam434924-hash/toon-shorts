"""
Purpose: Compatibility re-export of voice types and timing functions.
Inputs: Voice text and duration timings.
Outputs: Proportional word timings and WordTiming dataclasses.
Depends on: core.models, plugins.voice.synthetic
Used by: None
Config keys: None
Tests: tests/unit/test_timing.py
"""

from .core.models import WordTiming, SceneAudio
from .plugins.voice.synthetic import compute_fallback_word_timings, assign_character_voices, PRESET_VOICES

__all__ = [
    "WordTiming",
    "SceneAudio",
    "compute_fallback_word_timings",
    "assign_character_voices",
    "PRESET_VOICES",
]
