"""
Purpose: Central reusable asset library for backgrounds, graphics, SFX, and TTS cache.
Inputs: Content identifiers, style names, renderer versions, and creation callbacks.
Outputs: Cached file paths, hit/miss indicators, and asset copy helpers.
Depends on: hashlib, json, logging, pathlib, shutil, typing, core.config, core.paths
Used by: cli, core.audio_effects, core.pipeline, plugins.render.animejs.capture
Config keys: BACKGROUND_DESIGN_VERSION, RENDERER_VERSION
Tests: tests/unit/test_video_folders.py, tests/unit/test_phase1_safe_foundation.py
"""

import hashlib
import json
import logging
from pathlib import Path
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from toonshorts.core import config, paths

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


def compute_background_cache_key(
    style: str,
    palette: Any,
    layer_name: str,
    canvas_size: Any = (1680, 2520),
    renderer_version: str = "2.1.0",
    design_version: Any = 1,
) -> str:
    """
    Computes deterministic background cache key built ONLY from:
    style, palette, layer name, canvas size, renderer version, design_version.
    Camera and split-mode flags are strictly excluded.
    """
    s_style = str(style or "").strip().lower()
    if isinstance(palette, (list, tuple)):
        pal_str = ",".join(str(c).strip().lower() for c in palette)
    elif isinstance(palette, dict):
        pal_str = json.dumps(palette, sort_keys=True)
    else:
        pal_str = str(palette or "").strip().lower()

    s_layer = str(layer_name or "").strip().lower()
    if isinstance(canvas_size, (tuple, list)) and len(canvas_size) == 2:
        size_str = f"{canvas_size[0]}x{canvas_size[1]}"
    else:
        size_str = str(canvas_size or "").strip()

    r_ver = str(renderer_version or "").strip()
    d_ver = str(design_version if design_version is not None else 1).strip()

    raw = f"{s_style}:{pal_str}:{s_layer}:{size_str}:{r_ver}:{d_ver}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_or_render_background(
    theme: str,
    layer_name: str,
    svg_content: str = "",
    render_fn: Optional[Callable[[Path], None]] = None,
    style: str = "whiteboard",
    palette: Optional[Any] = None,
    canvas_size: Any = (1680, 2520),
    renderer_version: Optional[str] = None,
    design_version: Optional[Any] = None,
) -> Tuple[Path, bool]:
    """
    Retrieves cached background layer from library/backgrounds or renders it on miss.
    Checks library/ before rendering and reuses on a hit.
    Key is built strictly without camera or split-mode flags.
    """
    paths.LIBRARY_BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    active_style = theme or style or "whiteboard"
    r_ver = renderer_version or getattr(config, "RENDERER_VERSION", "2.1.0")
    d_ver = design_version if design_version is not None else getattr(config, "BACKGROUND_DESIGN_VERSION", 1)

    if palette is None:
        palette = (
            ["#0b0f19", "#0f172a", "#1e293b", "#38bdf8", "#818cf8"]
            if active_style == "night_studio"
            else ["#0f172a", "#f8fafc", "#2563EB", "#F59E0B", "#e2e8f0"]
        )

    key = compute_background_cache_key(
        style=active_style,
        palette=palette,
        layer_name=layer_name,
        canvas_size=canvas_size,
        renderer_version=r_ver,
        design_version=d_ver,
    )
    cache_path = paths.LIBRARY_BACKGROUNDS_DIR / f"bg_{active_style}_{layer_name}_{key[:16]}.png"

    # 1. Exact key hit in library/
    if cache_path.is_file() and cache_path.stat().st_size > 0:
        logger.info("Library HIT for background %s %s (%s)", active_style, layer_name, key[:8])
        return cache_path, True

    # 2. Check for existing cached file in library/ if design_version == 1
    if str(d_ver) == "1":
        existing = sorted(paths.LIBRARY_BACKGROUNDS_DIR.glob(f"bg_{active_style}_{layer_name}_*.png"))
        for ext in existing:
            if ext.is_file() and ext.stat().st_size > 0:
                logger.info("Library HIT (existing) for background %s %s -> %s", active_style, layer_name, ext.name)
                return ext, True

    # 3. Miss: render into library
    logger.info("Library MISS for background %s %s (%s) - rendering into library", active_style, layer_name, key[:8])
    if render_fn is not None:
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
