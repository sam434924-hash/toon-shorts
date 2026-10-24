"""
Purpose: Central reusable asset library for backgrounds, graphics, SFX, and TTS cache.
Inputs: Content identifiers, style names, renderer versions, and creation callbacks.
Outputs: Cached file paths, hit/miss indicators, and asset copy helpers.
Depends on: hashlib, logging, pathlib, shutil, typing, core.paths
Used by: cli, core.audio_effects, core.pipeline
Config keys: None
Tests: tests/unit/test_video_folders.py
"""

import hashlib
import logging
from pathlib import Path
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple

from toonshorts.core import paths

logger = logging.getLogger("toonshorts.library")


def compute_library_key(
    category: str,
    content: str,
    style: str = "",
    version: str = "1.0.0",
) -> str:
    """Computes a deterministic SHA-256 hash key for a reusable library asset."""
    raw = f"{category.strip()}:{style.strip()}:{version.strip()}:{content.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get_or_render_background(
    theme: str,
    layer_name: str,
    svg_content: str,
    render_fn: Callable[[Path], None],
    style: str = "whiteboard",
    renderer_version: str = "2.1.0",
) -> Tuple[Path, bool]:
    """Retrieves cached background layer from library/backgrounds or renders it on miss."""
    paths.LIBRARY_BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    key = compute_library_key("bg", svg_content, f"{style}_{theme}_{layer_name}", renderer_version)
    cache_path = paths.LIBRARY_BACKGROUNDS_DIR / f"bg_{theme}_{layer_name}_{key[:16]}.png"

    if cache_path.is_file() and cache_path.stat().st_size > 0:
        logger.info("Library HIT for background %s %s (%s)", theme, layer_name, key[:8])
        return cache_path, True

    logger.info("Library MISS for background %s %s (%s) - rendering into library", theme, layer_name, key[:8])
    render_fn(cache_path)
    return cache_path, False


def get_or_create_sfx(
    name: str,
    create_fn: Callable[[Path], None],
    version: str = "1.0.0",
) -> Tuple[Path, bool]:
    """Retrieves cached SFX from library/sfx or synthesizes it on miss."""
    paths.LIBRARY_SFX_DIR.mkdir(parents=True, exist_ok=True)
    key = compute_library_key("sfx", name, "", version)
    cache_path = paths.LIBRARY_SFX_DIR / f"sfx_{name}_{key[:16]}.wav"

    if cache_path.is_file() and cache_path.stat().st_size > 0:
        logger.info("Library HIT for SFX %s (%s)", name, key[:8])
        return cache_path, True

    logger.info("Library MISS for SFX %s (%s) - synthesizing into library", name, key[:8])
    create_fn(cache_path)
    return cache_path, False


def copy_library_asset(library_path: Path, video_dest_path: Path) -> Path:
    """Plain-copies a library asset into a video folder (never symlink or hardlink)."""
    video_dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(library_path), str(video_dest_path))
    return video_dest_path


def clean_temp_builds(videos_dir: Optional[Path] = None) -> List[Path]:
    """Removes all lingering temporary build directories (.tmp-*) inside videos/."""
    target_dir = videos_dir or paths.VIDEOS_DIR
    deleted: List[Path] = []
    if not target_dir.exists():
        return deleted

    for item in target_dir.iterdir():
        if item.is_dir() and item.name.startswith(".tmp-"):
            try:
                shutil.rmtree(item, ignore_errors=True)
                deleted.append(item)
                logger.info("Cleaned temporary build folder: %s", item.name)
            except Exception as e:
                logger.warning("Could not delete %s: %s", item.name, e)
    return deleted
