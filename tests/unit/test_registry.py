"""Tests for plugin registry and component discovery."""

import pytest
from toonshorts.core.registry import (
    get_llm,
    get_voice,
    get_renderer,
    get_motion,
    list_llms,
    list_voices,
    list_renderers,
    list_motions,
    register_llm,
    LLMInterface,
)
from toonshorts.core.errors import PluginNotFoundError


def test_registry_lists_plugins():
    assert "fake" in list_llms()
    assert "gemini" in list_llms()
    assert "fake" in list_voices()
    assert "edge_tts" in list_voices()
    assert "synthetic" in list_voices()
    assert "fake" in list_renderers()
    assert "pillow" in list_renderers()
    assert "gemini" in list_renderers()
    assert "ffmpeg" in list_motions()
    assert "static" in list_motions()


def test_get_valid_plugins():
    llm = get_llm("fake")
    assert llm.name == "fake"

    voice = get_voice("fake")
    assert voice.name == "fake"

    renderer = get_renderer("fake")
    assert renderer.name == "fake"

    motion = get_motion("static")
    assert motion.name == "static"


def test_get_unknown_plugin_raises():
    with pytest.raises(PluginNotFoundError):
        get_llm("non_existent_llm")

    with pytest.raises(PluginNotFoundError):
        get_voice("non_existent_voice")

    with pytest.raises(PluginNotFoundError):
        get_renderer("non_existent_renderer")

    with pytest.raises(PluginNotFoundError):
        get_motion("non_existent_motion")
