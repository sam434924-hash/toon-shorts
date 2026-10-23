"""
Purpose: Graphics plugins discovery, registry, and factory invocation.
Inputs: Plugin identifier and rendering parameters.
Outputs: Registered graphics plugin instances.
Depends on: importlib, pathlib, typing
Used by: inventory, plugins.render.animejs.visual_renderer
Config keys: None
Tests: tests/unit/test_graphics_plugins.py
"""

from pathlib import Path
from typing import Any, Dict, List, Type

_GRAPHICS_REGISTRY: Dict[str, Any] = {}


def register_graphics_plugin(name: str):
    """Decorator to register a graphics plugin class."""
    def decorator(cls):
        _GRAPHICS_REGISTRY[name.lower()] = cls
        return cls
    return decorator


def get_graphics_plugin(name: str) -> Any:
    """Retrieves registered graphics plugin class by name."""
    key = name.lower()
    if key not in _GRAPHICS_REGISTRY:
        raise KeyError(f"Graphics plugin '{name}' not found. Available: {list_graphics_plugins()}")
    return _GRAPHICS_REGISTRY[key]


def list_graphics_plugins() -> List[str]:
    """Returns sorted list of registered graphics plugin names."""
    return sorted(list(_GRAPHICS_REGISTRY.keys()))


# Import and register graphics plugins
from toonshorts.plugins.graphics.kinetic_words import KineticWordsPlugin
from toonshorts.plugins.graphics.draw_svg import DrawSVGPlugin
from toonshorts.plugins.graphics.octopus_vector import OctopusVectorPlugin
from toonshorts.plugins.graphics.hearts_pop import HeartsPopPlugin
from toonshorts.plugins.graphics.blue_blood_drop import BlueBloodDropPlugin

register_graphics_plugin("kinetic_words")(KineticWordsPlugin)
register_graphics_plugin("draw_svg")(DrawSVGPlugin)
register_graphics_plugin("octopus_vector")(OctopusVectorPlugin)
register_graphics_plugin("hearts_pop")(HeartsPopPlugin)
register_graphics_plugin("blue_blood_drop")(BlueBloodDropPlugin)
