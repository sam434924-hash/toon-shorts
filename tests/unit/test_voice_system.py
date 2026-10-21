"""Tests verifying that no synthetic tone generator or fallback exists."""

import ast
import pytest
from pathlib import Path
from toonshorts.core.registry import list_voices

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_no_synthetic_or_edge_tts_plugins():
    """Confirms edge_tts and synthetic are deleted from voice plugins."""
    voice_plugins = list_voices()
    assert "edge_tts" not in voice_plugins, "edge_tts plugin must be deleted"
    assert "synthetic" not in voice_plugins, "synthetic tone plugin must be deleted"


def test_no_synthetic_tone_fallback_in_codebase():
    """Scans all python files to ensure no sine wave tone generator fallback exists."""
    src_dir = PROJECT_ROOT / "src" / "toonshorts"
    banned_patterns = ["generate_synthetic_audio", "edge_tts.Communicate"]

    for py_file in src_dir.glob("**/*.py"):
        text = py_file.read_text(encoding="utf-8")
        for pattern in banned_patterns:
            assert pattern not in text, f"Found banned pattern '{pattern}' in {py_file.name}"


def test_no_automatic_engine_switch():
    """Checks that when an engine fails, it raises VoiceError rather than switching engines."""
    from toonshorts.core.errors import VoiceError
    from toonshorts.plugins.voice.piper import PiperVoicePlugin
    from toonshorts.core.models import Scene, Pose, CameraMove, Transition

    # Piper should fail because binary/model is not installed, and raise VoiceError directly
    piper = PiperVoicePlugin()
    dummy_scene = Scene(
        scene_number=1,
        speaker="Pip",
        dialogue_line="Testing failure",
        action="idle",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )
    with pytest.raises(VoiceError):
        piper.generate_scene_voice(0, dummy_scene, "nonexistent_voice", Path("."))
