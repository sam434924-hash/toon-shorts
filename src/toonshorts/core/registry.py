"""
Purpose: Interface definitions and centralized plugin registry.
Inputs: Component registrations and plugin lookup queries.
Outputs: Swappable plugin interfaces and resolved component instances.
Depends on: abc, core.errors, core.models, pathlib, typing
Used by: core, core.pipeline, inventory, plugins.llm.fake, plugins.llm.gemini, plugins.motion.ffmpeg, plugins.motion.static, plugins.render.animejs.plugin, plugins.render.blender3d, plugins.render.cairo, plugins.render.fake, plugins.render.gemini, plugins.render.pillow, plugins.voice.fake, plugins.voice.gemini_tts, plugins.voice.piper, plugins.voice.windows_sapi
Config keys: None
Tests: tests/contract/test_llm_contract.py, tests/contract/test_motion_contract.py, tests/contract/test_render_contract.py, tests/contract/test_voice_contract.py, tests/unit/test_registry.py
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Tuple, Type, Any, Optional

from .errors import PluginNotFoundError
from .models import ScriptPlan, CriticReview, Scene, Character, CameraMove, SceneAudio


# --- Component Interfaces (ABCs) ---

class LLMInterface(ABC):
    """Abstract interface for LLM screenplay planning and critic evaluation."""
    name: str

    @abstractmethod
    def generate_plan(
        self,
        topic: str,
        style_name: str,
        style_preset: Dict[str, Any],
    ) -> ScriptPlan:
        """Generates a structured screenplay conforming to ScriptPlan."""
        pass

    @abstractmethod
    def review_and_refine(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
    ) -> Tuple[ScriptPlan, CriticReview]:
        """Critiques and iteratively refines the script plan."""
        pass


class VoiceInterface(ABC):
    """Abstract interface for voiceover generation and word timestamp alignment."""
    name: str

    @abstractmethod
    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.35,
    ) -> SceneAudio:
        """Generates audio for a single scene and returns timing metadata."""
        pass

    @abstractmethod
    def generate_all_voices(
        self,
        plan: ScriptPlan,
        temp_dir: Path,
    ) -> List[SceneAudio]:
        """Generates voice audio for all scenes sequentially."""
        pass


class RenderInterface(ABC):
    """Abstract interface for visual scene and character frame generation."""
    name: str

    @abstractmethod
    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Renders an individual vertical 9:16 story frame image."""
        pass

    @abstractmethod
    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
    ) -> List[Path]:
        """Renders visual frames for all scenes in the screenplay."""
        pass


class MotionInterface(ABC):
    """Abstract interface for camera movement video filter chains."""
    name: str

    @abstractmethod
    def get_filter_chain(
        self,
        camera_move: CameraMove,
        duration_seconds: float,
    ) -> str:
        """Returns FFmpeg filter chain representing the camera motion."""
        pass


# --- Central Registries ---

_LLM_REGISTRY: Dict[str, Type[LLMInterface]] = {}
_VOICE_REGISTRY: Dict[str, Type[VoiceInterface]] = {}
_RENDER_REGISTRY: Dict[str, Type[RenderInterface]] = {}
_MOTION_REGISTRY: Dict[str, Type[MotionInterface]] = {}


def register_llm(name: str):
    def decorator(cls: Type[LLMInterface]):
        _LLM_REGISTRY[name.lower()] = cls
        cls.name = name.lower()
        return cls
    return decorator


def register_voice(name: str):
    def decorator(cls: Type[VoiceInterface]):
        _VOICE_REGISTRY[name.lower()] = cls
        cls.name = name.lower()
        return cls
    return decorator


def register_renderer(name: str):
    def decorator(cls: Type[RenderInterface]):
        _RENDER_REGISTRY[name.lower()] = cls
        cls.name = name.lower()
        return cls
    return decorator


def register_motion(name: str):
    def decorator(cls: Type[MotionInterface]):
        _MOTION_REGISTRY[name.lower()] = cls
        cls.name = name.lower()
        return cls
    return decorator


def get_llm(name: str, **kwargs) -> LLMInterface:
    key = name.lower()
    if key not in _LLM_REGISTRY:
        raise PluginNotFoundError(f"LLM plugin '{name}' not found. Available: {list_llms()}")
    return _LLM_REGISTRY[key](**kwargs)


def get_voice(name: str, **kwargs) -> VoiceInterface:
    key = name.lower()
    if key not in _VOICE_REGISTRY:
        raise PluginNotFoundError(f"Voice plugin '{name}' not found. Available: {list_voices()}")
    return _VOICE_REGISTRY[key](**kwargs)


def get_renderer(name: str, **kwargs) -> RenderInterface:
    key = name.lower()
    if key not in _RENDER_REGISTRY:
        raise PluginNotFoundError(f"Render plugin '{name}' not found. Available: {list_renderers()}")
    return _RENDER_REGISTRY[key](**kwargs)


def get_motion(name: str, **kwargs) -> MotionInterface:
    key = name.lower()
    if key not in _MOTION_REGISTRY:
        raise PluginNotFoundError(f"Motion plugin '{name}' not found. Available: {list_motions()}")
    return _MOTION_REGISTRY[key](**kwargs)


def list_llms() -> List[str]:
    return sorted(list(_LLM_REGISTRY.keys()))


def list_voices() -> List[str]:
    return sorted(list(_VOICE_REGISTRY.keys()))


def list_renderers() -> List[str]:
    return sorted(list(_RENDER_REGISTRY.keys()))


def list_motions() -> List[str]:
    return sorted(list(_MOTION_REGISTRY.keys()))
