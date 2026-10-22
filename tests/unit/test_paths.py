"""
Purpose: Unit tests for central single-root paths module.
Inputs: Path constants from toonshorts.core.paths.
Outputs: Pytest assertions for path resolution and single-root hierarchy.
Depends on: pathlib, pytest, toonshorts.core.paths
Used by: Test suite
"""

from pathlib import Path
from toonshorts.core import paths


def test_project_root_resolution():
    """Verify PROJECT_ROOT accurately locates project root containing pyproject.toml."""
    assert paths.PROJECT_ROOT.is_dir()
    assert (paths.PROJECT_ROOT / "pyproject.toml").is_file()


def test_single_root_assets_hierarchy():
    """Verify all input asset subdirectories reside under ASSETS_DIR."""
    assert paths.ASSETS_DIR == paths.PROJECT_ROOT / "assets"
    assert paths.ASSETS_SOURCES_DIR == paths.ASSETS_DIR / "sources"
    assert paths.ASSETS_SOURCES_INCOMING_DIR == paths.ASSETS_SOURCES_DIR / "incoming"
    assert paths.ASSETS_2D_DIR == paths.ASSETS_DIR / "2d"
    assert paths.CHARACTERS_2D_DIR == paths.ASSETS_2D_DIR / "characters"
    assert paths.LAYOUTS_2D_DIR == paths.ASSETS_2D_DIR / "layouts"
    assert paths.ASSETS_3D_DIR == paths.ASSETS_DIR / "3d"
    assert paths.MODELS_3D_DIR == paths.ASSETS_3D_DIR / "models"
    assert paths.SCRIPTS_3D_DIR == paths.ASSETS_3D_DIR / "scripts"
    assert paths.VOICES_DIR == paths.ASSETS_DIR / "voices"
    assert paths.PIPER_VOICES_DIR == paths.VOICES_DIR / "piper"


def test_output_and_fixtures_paths():
    """Verify output and test fixture paths are isolated from assets."""
    assert paths.OUTPUT_DIR == paths.PROJECT_ROOT / "output"
    assert paths.TESTS_DIR == paths.PROJECT_ROOT / "tests"
    assert paths.TESTS_FIXTURES_DIR == paths.PROJECT_ROOT / "tests" / "fixtures"
    assert paths.TESTS_GOLDEN_DIR == paths.TESTS_FIXTURES_DIR / "golden"
