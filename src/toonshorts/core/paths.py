"""
Purpose: Central path definitions for single-root assets and output directories.
Inputs: Project root directory resolved from module location.
Outputs: Strongly-typed Path objects for assets, sources, 2d, 3d, output, and fixtures.
Depends on: pathlib
Used by: core.character2d, core.character_pack
Config keys: None
Tests: tests/unit/test_paths.py
"""

from pathlib import Path

# Base repository root
_current_file = Path(__file__).resolve()
PROJECT_ROOT = _current_file.parents[3]

# Top-level directories
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMP_DIR = PROJECT_ROOT / "temp"
CACHE_DIR = PROJECT_ROOT / "cache"
TESTS_DIR = PROJECT_ROOT / "tests"

# Assets single-root layout subdirectories
ASSETS_SOURCES_DIR = ASSETS_DIR / "sources"
ASSETS_SOURCES_INCOMING_DIR = ASSETS_SOURCES_DIR / "incoming"
ASSETS_2D_DIR = ASSETS_DIR / "2d"
CHARACTERS_2D_DIR = ASSETS_2D_DIR / "characters"
LAYOUTS_2D_DIR = ASSETS_2D_DIR / "layouts"

ASSETS_3D_DIR = ASSETS_DIR / "3d"
MODELS_3D_DIR = ASSETS_3D_DIR / "models"
SCRIPTS_3D_DIR = ASSETS_3D_DIR / "scripts"

VOICES_DIR = ASSETS_DIR / "voices"
PIPER_VOICES_DIR = VOICES_DIR / "piper"

# Test fixtures and golden baselines
TESTS_FIXTURES_DIR = TESTS_DIR / "fixtures"
TESTS_GOLDEN_DIR = TESTS_FIXTURES_DIR / "golden"

# Cache subdirectories
TTS_CACHE_DIR = CACHE_DIR / "tts"
