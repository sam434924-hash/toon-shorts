"""
Purpose: Central configuration, paths, model names, pricing, and limits.
Inputs: Environment variables and optional .env file.
Outputs: Path objects, model constants, hard caps, pricing dictionaries.
Depends on: dotenv, os, pathlib, sys
Used by: brief, cli, config, core, core.assembler, core.board_objects, core.camera, core.caps, core.character2d, core.character_pack, core.client, core.cost, core.layout_checker, core.pipeline, core.style_profile, core.sync, inventory, plugins.llm.gemini, plugins.motion.ffmpeg, plugins.render.animejs.audio_sync, plugins.render.animejs.capture, plugins.render.animejs.html_builder, plugins.render.animejs.layout, plugins.render.animejs.plugin, plugins.render.animejs.visual_renderer, plugins.render.blender3d, plugins.render.cairo, plugins.render.fake, plugins.render.gemini, plugins.render.pillow, plugins.voice.gemini_tts, plugins.voice.piper, voice_utils
Config keys: ANIME_JS_PATH, BLENDER_PATH, ENABLE_BOARD_OBJECTS, ENABLE_PARALLAX_BACKGROUND, ENABLE_PARALLAX_CACHE, ENABLE_PURPOSEFUL_CAMERA, ENABLE_SPLIT_CAMERA_ZONES, ENABLE_STYLE_PROFILE, GEMINI_API_KEY, OneDrive, ROUGH_JS_PATH, TTS_CACHE_DIR
Tests: tests/unit/test_board_objects.py, tests/unit/test_spend_cap.py, tests/unit/test_split_camera_zones.py, tests/unit/test_styles.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Base paths - robust across src/ layout
_current_file = Path(__file__).resolve()
# core -> toonshorts -> src -> project_root
PROJECT_ROOT = _current_file.parents[3]
# Built-in styles located within package
STYLES_DIR = _current_file.parents[1] / "styles"
if not STYLES_DIR.exists() and (PROJECT_ROOT / "styles").exists():
    STYLES_DIR = PROJECT_ROOT / "styles"

OUTPUT_DIR = PROJECT_ROOT / "videos"
TEMP_DIR = PROJECT_ROOT / ".tmp"
VIDEOS_DIR = PROJECT_ROOT / "videos"
LIBRARY_DIR = PROJECT_ROOT / "library"
LIBRARY_TTS_DIR = LIBRARY_DIR / "tts"
LIBRARY_BACKGROUNDS_DIR = LIBRARY_DIR / "backgrounds"
LIBRARY_SFX_DIR = LIBRARY_DIR / "sfx"
LIBRARY_GRAPHICS_DIR = LIBRARY_DIR / "graphics"
CHARACTERS_DIR = PROJECT_ROOT / "characters" if (PROJECT_ROOT / "characters").exists() else PROJECT_ROOT / "assets" / "2d" / "characters"
TTS_CACHE_DIR = LIBRARY_TTS_DIR
ASSETS_DIR = PROJECT_ROOT / "assets"
PIPER_VOICES_DIR = ASSETS_DIR / "voices" / "piper"
VOICES_REGISTRY_PATH = PROJECT_ROOT / "voices.json"
ANIME_JS_PATH = PROJECT_ROOT / "src" / "toonshorts" / "assets" / "vendor" / "anime-3.2.2.min.js"
ROUGH_JS_PATH = PROJECT_ROOT / "src" / "toonshorts" / "assets" / "vendor" / "rough-4.6.6.min.js"

# Load environment variables strictly from .env located at PROJECT_ROOT
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.is_file():
    load_dotenv(dotenv_path=ENV_FILE)

# API Keys - Never log or print these!
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Blender executable path
_default_blender = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
BLENDER_PATH = os.getenv("BLENDER_PATH", "").strip()
if not BLENDER_PATH and os.path.isfile(_default_blender):
    BLENDER_PATH = _default_blender

# Default Plugins
DEFAULT_LLM = "gemini"
DEFAULT_VOICE = "gemini_tts"
DEFAULT_RENDERER = "auto"
DEFAULT_MOTION = "ffmpeg"

# Gemini Model Names - Configured here, never hardcoded in logic
TEXT_MODEL_NAME = "gemini-2.5-flash"
CRITIC_MODEL_NAME = "gemini-2.5-flash"
IMAGE_MODEL_NAME = "imagen-3.0-generate-002"
TTS_MODEL_NAME = "gemini-3.8-flash-tts"

# Gemini Prebuilt Voice Names for Character Assignment
GEMINI_VOICES = [
    "Kore",
    "Puck",
    "Fenrir",
    "Aoede",
    "Charon",
    "Enceladus",
    "Zephyr",
    "Leda",
]

# Hard Caps Per Run
MAX_API_CALLS_PER_RUN = 35
MAX_IMAGES_PER_RUN = 12
MAX_CRITIC_REWRITES = 2

# Output Video Specs
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
MIN_DURATION_SECONDS = 25
MAX_DURATION_SECONDS = 65

# Reserved subtitle strip for vertical video layouts (night_studio, whiteboard)
# Strictly clear of board (65..1045), characters (1040..1540), desk props (1420..1550), and desk bevel (1540..1578)
NIGHT_STUDIO_SUBTITLE_STRIP = {
    "top": 1640,
    "bottom": 1860,
    "left": 60,
    "right": 1020,
    "margin_v": 120,
    "font_size": 76,
    "max_lines": 2,
}

# 4-Layer Depth & Parallax factors (Foreground, Subject, Board, Deep Background)
# 3-Layer Parallax Background Depths (Far, Mid, Near)
BACKGROUND_PARALLAX_DEPTHS = {
    "far": 0.08,
    "mid": 0.18,
    "near": 0.32,
}

# Phase 4B: Parallax Background & Caching
ENABLE_PARALLAX_BACKGROUND = True
ENABLE_PARALLAX_CACHE = True

CAMERA_PARALLAX_FACTORS = {
    "bg_far": 0.08,
    "bg_mid": 0.18,
    "bg_near": 0.32,
    "foreground": 2.0,
    "subject": 1.0,
    "board": 0.5,
    "deep_bg": 0.12,
}

# Camera presets for deterministic framing
CAMERA_PRESETS = {
    "wide": {"x": 0.0, "y": 0.0, "zoom": 1.0, "focus": "subject"},
    "boy_close": {"x": -130.0, "y": -45.0, "zoom": 1.18, "focus": "subject"},
    "girl_close": {"x": 130.0, "y": -45.0, "zoom": 1.18, "focus": "subject"},
    "board_close": {"x": 0.0, "y": 90.0, "zoom": 1.25, "focus": "board"},
}

CAMERA_TRANSITION_SEC = 0.80  # 0.3 to 0.5s with easing
CAMERA_DRIFT_ROT_MAX = 0.35   # under 0.4 degrees
CAMERA_PUNCH_IN_ZOOM = 1.16   # 1.12 to 1.18
CAMERA_PUNCH_IN_SHAKE_PX = 1.5
CAMERA_RACK_FOCUS_BLUR = {
    "sharp": 0.0,
    "near_defocus": 2.2,
    "far_defocus": 3.8,
    "transition_frames": 10,
}

# Camera zoom settings for dynamic framing
CAMERA_ZOOM_SPEAKER = 1.18
CAMERA_ZOOM_BOARD = 1.25
CAMERA_EASE_DURATION_SEC = 0.50

# Phase 4B: Purposeful Camera Shot Planning
ENABLE_PURPOSEFUL_CAMERA = True
ENABLE_STYLE_PROFILE = True
ENABLE_BOARD_OBJECTS = True

# Phase 4C / Two Independent Camera Zones Layout (fixes cut-off speakers)
ENABLE_SPLIT_CAMERA_ZONES = os.getenv("ENABLE_SPLIT_CAMERA_ZONES", "true").lower() in ("true", "1", "yes")
LAYOUT_CAMERA_VERSION = "2.1.0_split_zones"

# YouTube Shorts Safe Zones (clear of top 15%, bottom 25%, right 120px)
SAFE_ZONE_TOP_PERCENT = 0.15
SAFE_ZONE_BOTTOM_PERCENT = 0.25
SAFE_ZONE_RIGHT_PX = 120.0
SAFE_ZONE_TOP_PX = int(VIDEO_HEIGHT * SAFE_ZONE_TOP_PERCENT)                # 288
SAFE_ZONE_BOTTOM_PX = int(VIDEO_HEIGHT * (1.0 - SAFE_ZONE_BOTTOM_PERCENT))   # 1440
SAFE_ZONE_RIGHT_BOUNDARY_PX = float(VIDEO_WIDTH - SAFE_ZONE_RIGHT_PX)       # 960.0

# Split Zones Dimensions and Placement (9:16 vertical 1080x1920)
SPLIT_BOARD_ZONE = {
    "top": 288.0,
    "bottom": 808.0,
    "left": 60.0,
    "right": 960.0,
    "width": 900.0,
    "height": 520.0,
}

SPLIT_CHARACTER_ZONE = {
    "top": 820.0,
    "bottom": 1350.0,
    "left": 60.0,
    "right": 960.0,
    "width": 900.0,
    "height": 530.0,
}

SPLIT_SUBTITLE_ZONE = {
    "top": 1355.0,
    "bottom": 1435.0,
    "left": 60.0,
    "right": 960.0,
    "width": 900.0,
    "height": 80.0,
    "margin_v": 485,
}

SPLIT_STAGE_ANCHORS = {
    "left": {"left": 60.0, "top": 20.0, "width": 420.0, "height": 480.0},
    "right": {"left": 420.0, "top": 20.0, "width": 420.0, "height": 480.0},
}

CAMERA_MAX_ZOOM = 1.35
CAMERA_MIN_HOLD_SEC = 1.2

# Cost Estimator Pricing (USD, based on current Google GenAI API rates)
PRICING = {
    "text_input_per_million_tokens": 0.10,
    "text_output_per_million_tokens": 0.40,
    "image_per_generation": 0.04,   # Imagen 3 tier
    "tts_per_thousand_characters": 0.02, # Speech generation tier
}


def check_cloud_sync_warning(project_path: Path = PROJECT_ROOT) -> bool:
    """Warns if project directory is situated inside a cloud-synced folder (e.g., OneDrive)."""
    resolved = str(project_path.resolve()).lower()
    onedrive_env = os.getenv("OneDrive", "")
    sync_indicators = ["onedrive", "dropbox", "google drive", "icloud", "box sync"]

    is_cloud_synced = False
    if onedrive_env and onedrive_env.lower() in resolved:
        is_cloud_synced = True
    elif any(ind in resolved for ind in sync_indicators):
        is_cloud_synced = True

    if is_cloud_synced:
        sys.stderr.write(
            "\n[WARNING] SECURITY NOTICE: Project folder appears to be located inside a "
            "cloud-synced directory (e.g. OneDrive, Dropbox).\n"
            "Ensure '.env' remains explicitly in '.gitignore' so credentials are never "
            "synced to remote repositories or shared cloud drives.\n\n"
        )
        sys.stderr.flush()
        return True
    return False

# 3D Blender Render Caps and Settings
BLENDER_DRAFT_WIDTH = 540
BLENDER_DRAFT_HEIGHT = 960
BLENDER_DRAFT_FPS = 12

BLENDER_FINAL_WIDTH = 1080
BLENDER_FINAL_HEIGHT = 1920
BLENDER_FINAL_FPS = 24

BLENDER_MAX_FRAMES = 720
BLENDER_MAX_SECONDS_PER_RUN = 120.0
BLENDER_MAX_RESOLUTION = (1920, 1920)
BLENDER_RENDER_TIMEOUT_SECONDS = 300

# Audio-Visual Word Sync and Fallback Caps
MAX_SYNC_DIFFERENCE_MS = 150
ALLOW_FALLBACK = os.getenv("ALLOW_FALLBACK", "false").lower() in ("true", "1", "yes")
