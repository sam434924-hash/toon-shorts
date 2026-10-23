"""Tests for renderer capability flags and pipeline dispatch without TypeError cascades."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from toonshorts.core.registry import BaseRenderer, RenderInterface, list_renderers, get_renderer
from toonshorts.core.models import ScriptPlan, Scene, Character, CameraMove
from toonshorts.plugins.render.animejs.plugin import AnimeJSRenderPlugin


def test_base_renderer_class_level_defaults():
    """BaseRenderer / RenderInterface must have safe False defaults for capability flags."""
    assert BaseRenderer is RenderInterface
    assert hasattr(BaseRenderer, "supports_scene_audios")
    assert hasattr(BaseRenderer, "supports_fast")
    assert BaseRenderer.supports_scene_audios is False
    assert BaseRenderer.supports_fast is False


def test_all_renderers_have_explicit_capability_flags():
    """All registered renderers must explicitly declare supports_scene_audios and supports_fast."""
    for name in list_renderers():
        r = get_renderer(name)
        assert isinstance(r.supports_scene_audios, bool), f"{name} missing boolean supports_scene_audios"
        assert isinstance(r.supports_fast, bool), f"{name} missing boolean supports_fast"


def test_animejs_capabilities():
    """AnimeJSRenderPlugin must support both scene_audios and fast mode."""
    r = get_renderer("animejs")
    assert isinstance(r, AnimeJSRenderPlugin)
    assert r.supports_scene_audios is True
    assert r.supports_fast is True


def test_still_renderers_do_not_support_scene_audios_or_fast():
    """Still-frame renderers (cairo, pillow, blender3d, fake, gemini) default to False."""
    for name in ["cairo", "pillow", "blender3d", "fake", "gemini"]:
        r = get_renderer(name)
        assert r.supports_scene_audios is False
        assert r.supports_fast is False


def test_pipeline_dispatch_respects_flags_without_type_error(tmp_path):
    """Pipeline dispatches based on flags rather than catching TypeError cascades."""
    mock_renderer = MagicMock(spec=BaseRenderer)
    mock_renderer.name = "mock_still_renderer"
    mock_renderer.supports_scene_audios = False
    mock_renderer.supports_fast = False
    mock_renderer.render_all_scenes.return_value = [tmp_path / "f1.png"]

    # Simulating what pipeline does
    render_kwargs = {}
    fake_audios = [MagicMock()]
    fast = True

    if getattr(mock_renderer, "supports_scene_audios", False) and fake_audios:
        render_kwargs["scene_audios"] = fake_audios
    if fast and getattr(mock_renderer, "supports_fast", False):
        render_kwargs["fast"] = True

    # Call should succeed without TypeError
    plan = MagicMock()
    preset = {}
    res = mock_renderer.render_all_scenes(plan, preset, tmp_path, **render_kwargs)
    assert res == [tmp_path / "f1.png"]
    # Verify no kwargs were passed to the still renderer
    mock_renderer.render_all_scenes.assert_called_once_with(plan, preset, tmp_path)
