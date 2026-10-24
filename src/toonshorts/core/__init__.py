"""
Purpose: Core initialization exporting config, models, registry, and runner.
Inputs: Internal core module definitions.
Outputs: Public core functions and classes.
Depends on: core.camera, core.caps, core.config, core.errors, core.models, core.pipeline, core.registry, core.style_profile
Used by: brief, cli, core.assembler, core.board_objects, core.camera, core.caps, core.character2d, core.character_pack, core.client, core.cost, core.images, core.layout_checker, core.layout_planner, core.library, core.models, core.pipeline, core.style_profile, core.sync, core.visual_checker, inventory, plugins.llm.gemini, plugins.motion.ffmpeg, plugins.render.animejs.audio_sync, plugins.render.animejs.capture, plugins.render.animejs.html_builder, plugins.render.animejs.layout, plugins.render.animejs.plugin, plugins.render.animejs.visual_renderer, plugins.render.blender3d, plugins.render.cairo, plugins.render.fake, plugins.render.gemini, plugins.render.pillow, plugins.voice.gemini_tts, plugins.voice.piper, voice_utils
Config keys: None
Tests: tests/unit/test_validation.py
"""

from . import camera
from . import style_profile
from . import config
from .caps import SpendCapTracker
from .errors import SpendCapExceededError, PluginNotFoundError, PipelineError
from .models import (
    CameraMove,
    Transition,
    Pose,
    Character,
    Scene,
    ScriptPlan,
    CriticReview,
    WordTiming,
    SceneAudio,
    sanitize_filename,
)
from .registry import (
    LLMInterface,
    VoiceInterface,
    RenderInterface,
    MotionInterface,
    register_llm,
    register_voice,
    register_renderer,
    register_motion,
    get_llm,
    get_voice,
    get_renderer,
    get_motion,
    list_llms,
    list_voices,
    list_renderers,
    list_motions,
)
from .pipeline import run_pipeline, load_style_preset

__all__ = [
    "camera",
    "style_profile",
    "config",
    "SpendCapTracker",
    "SpendCapExceededError",
    "PluginNotFoundError",
    "PipelineError",
    "CameraMove",
    "Transition",
    "Pose",
    "Character",
    "Scene",
    "ScriptPlan",
    "CriticReview",
    "WordTiming",
    "SceneAudio",
    "sanitize_filename",
    "LLMInterface",
    "VoiceInterface",
    "RenderInterface",
    "MotionInterface",
    "register_llm",
    "register_voice",
    "register_renderer",
    "register_motion",
    "get_llm",
    "get_voice",
    "get_renderer",
    "get_motion",
    "list_llms",
    "list_voices",
    "list_renderers",
    "list_motions",
    "run_pipeline",
    "load_style_preset",
]
