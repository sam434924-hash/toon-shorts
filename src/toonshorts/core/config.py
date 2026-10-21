"""
Purpose: Central configuration, paths, model names, pricing, and limits.
Inputs: Environment variables and optional .env file.
Outputs: Path objects, model constants, hard caps, pricing dictionaries.
Depends on: dotenv, os, pathlib, sys
Used by: cli, config, core, core.assembler, core.caps, core.client, core.cost, core.pipeline, plugins.llm.gemini, plugins.motion.ffmpeg, plugins.render.fake, plugins.render.gemini, plugins.render.pillow
Config keys: GEMINI_API_KEY, OneDrive
Tests: tests/unit/test_spend_cap.py, tests/unit/test_styles.py
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

OUTPUT_DIR = PROJECT_ROOT / "output"
TEMP_DIR = PROJECT_ROOT / "temp"

# Load environment variables strictly from .env located at PROJECT_ROOT
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.is_file():
    load_dotenv(dotenv_path=ENV_FILE)

# API Keys - Never log or print these!
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Default Plugins
DEFAULT_LLM = "gemini"
DEFAULT_VOICE = "edge_tts"
DEFAULT_RENDERER = "auto"
DEFAULT_MOTION = "ffmpeg"

# Gemini Model Names - Configured here, never hardcoded in logic
TEXT_MODEL_NAME = "gemini-2.5-flash"
CRITIC_MODEL_NAME = "gemini-2.5-flash"
IMAGE_MODEL_NAME = "imagen-3.0-generate-002"
TTS_MODEL_NAME = "gemini-2.5-flash-preview-tts"

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
