"""
Purpose: HTML/SVG whiteboard animation rendering package using Anime.js, Rough.js, and Playwright.
Inputs: Scene plans, characters, style presets, voice timing cues, and whiteboard text elements.
Outputs: Rendered 9:16 PNG image frames and animated MP4 video sequences.
Depends on: plugins.render.animejs.annotations, plugins.render.animejs.audio_sync, plugins.render.animejs.capture, plugins.render.animejs.cast, plugins.render.animejs.gestures, plugins.render.animejs.html_builder, plugins.render.animejs.layout, plugins.render.animejs.plugin
Used by: None
Config keys: ANIME_JS_PATH, ROUGH_JS_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/contract/test_render_contract.py, tests/unit/test_animejs.py
"""

from toonshorts.plugins.render.animejs.annotations import (
    extract_whiteboard_content_and_annotations,
    extract_whiteboard_content_for_scene,
)
from toonshorts.plugins.render.animejs.audio_sync import compute_mouth_cues_from_audio
from toonshorts.plugins.render.animejs.capture import (
    capture_still_frame,
    render_whiteboard_video,
)
from toonshorts.plugins.render.animejs.cast import (
    build_characters_data,
    resolve_scene_cast,
)
from toonshorts.plugins.render.animejs.gestures import (
    ALLOWED_GESTURES,
    resolve_character_gesture,
    sanitize_gesture,
)
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html
from toonshorts.plugins.render.animejs.layout import (
    CHAR_RIG_LAYOUT,
    SAFE_AREA,
    compute_gesture_bounds,
    generate_scene_decorations,
    resolve_listener_glance_eye,
)
from toonshorts.plugins.render.animejs.plugin import AnimeJSRenderPlugin

__all__ = [
    "AnimeJSRenderPlugin",
    "compute_mouth_cues_from_audio",
    "extract_whiteboard_content_for_scene",
    "extract_whiteboard_content_and_annotations",
    "generate_whiteboard_html",
    "sanitize_gesture",
    "compute_gesture_bounds",
    "generate_scene_decorations",
    "resolve_character_gesture",
    "resolve_scene_cast",
    "build_characters_data",
    "capture_still_frame",
    "render_whiteboard_video",
    "SAFE_AREA",
    "CHAR_RIG_LAYOUT",
    "ALLOWED_GESTURES",
    "resolve_listener_glance_eye",
]
