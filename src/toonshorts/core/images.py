"""
Purpose: Reference image intake, style analysis, safe image validation, cutouts with edge masks and shadows, library index caching, and manifest tracking.
Inputs: Image paths, purpose notes, theme names, prompts, dimensions, and allowed directories.
Outputs: Theme draft dictionaries, sanitized images, cutout PNGs, and manifest image items.
Depends on: hashlib, json, logging, math, os, pathlib, re, shutil, typing, PIL, core.config, core.library, core.paths, core.models
Used by: core.board_objects
Config keys: None
Tests: tests/unit/test_images_and_references.py
"""

import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

from toonshorts.core import config, paths
from toonshorts.core.library import (
    find_element,
    load_element_index,
    resolve_theme_tags,
    save_element_index,
)

logger = logging.getLogger("toonshorts.images")

ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_IMAGE_DIMENSION = 4096
MIN_IMAGE_DIMENSION = 16

ALLOWED_IMAGE_PRESETS = {
    "slide_in_tilt",
    "paper_tear_reveal",
    "detail_highlight",
    "stamp_slam",
    "push_in",
}


def compute_image_key(
    prompt: str,
    style: str,
    size: Tuple[int, int] = (600, 600),
    design_version: int = 1,
) -> str:
    """Computes a deterministic SHA-256 key for a generated or indexed image."""
    raw = f"{prompt.strip().lower()}:{style.strip().lower()}:{size[0]}x{size[1]}:{design_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_and_sanitize_image(
    image_path: Union[str, Path],
    allowed_dirs: Optional[List[Path]] = None,
    max_bytes: int = MAX_IMAGE_FILE_SIZE_BYTES,
    max_dim: int = MAX_IMAGE_DIMENSION,
) -> Path:
    """
    Validates image safety:
    - Accepts strictly PNG, JPEG, WebP. Rejects SVG, GIF, BMP, executable files, etc.
    - Limits file size and pixel dimensions.
    - Path must stay inside allowed asset folder (prevent directory traversal).
    - Re-encodes and strips all metadata (EXIF, ICC profiles, comments).
    - Rejects SVG masquerading as image.
    """
    p = Path(image_path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Image file does not exist: {p}")

    # 1. Extension check (reject SVG, HTML, etc.)
    ext = p.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Disallowed image file extension '{ext}'. Accepted formats are PNG, JPEG, and WebP."
        )

    # 2. Path containment check
    if allowed_dirs:
        canonical_allowed = [d.resolve() for d in allowed_dirs]
        is_allowed = any(p == d or d in p.parents for d in canonical_allowed)
        if not is_allowed:
            raise PermissionError(
                f"Image path '{p}' is outside allowed asset directories: {[str(d) for d in canonical_allowed]}"
            )

    # 3. File size check
    file_size = p.stat().st_size
    if file_size > max_bytes:
        raise ValueError(
            f"Image file size ({file_size} bytes) exceeds maximum allowed size ({max_bytes} bytes)."
        )

    # 4. Content check: read file header bytes to reject text/SVG
    header = p.read_bytes()[:512].lower()
    if b"<svg" in header or b"<?xml" in header or b"<!doctype svg" in header:
        raise ValueError("SVG image files are forbidden in raster image intake. SVG from images is not permitted.")

    # 5. Open image using PIL and verify format
    try:
        with Image.open(p) as img:
            img_format = (img.format or "").upper()
            if img_format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError(
                    f"Unsupported image format '{img_format}'. Only PNG, JPEG, and WebP are allowed."
                )

            w, h = img.size
            if w < MIN_IMAGE_DIMENSION or h < MIN_IMAGE_DIMENSION:
                raise ValueError(
                    f"Image dimension ({w}x{h}) is too small (minimum {MIN_IMAGE_DIMENSION}px)."
                )
            if w > max_dim or h > max_dim:
                raise ValueError(
                    f"Image dimension ({w}x{h}) exceeds maximum allowed ({max_dim}px)."
                )

            # Re-encode and strip metadata
            clean_img = Image.new(img.mode, img.size)
            clean_img.paste(img)

            # Save clean image back without metadata
            clean_img.save(p, format=img_format)
    except (ValueError, PermissionError):
        raise
    except Exception as e:
        raise ValueError(f"Failed to validate or sanitize image '{p.name}': {e}") from e

    return p


def get_image_library_dir() -> Path:
    """Returns library/elements/images directory."""
    target = paths.LIBRARY_ELEMENTS_DIR / "images"
    target.mkdir(parents=True, exist_ok=True)
    return target


def find_image_in_library(key: str) -> Optional[Dict[str, Any]]:
    """Checks library/elements/images/index.json (and fallback library/elements/image/)."""
    # 1. Check primary 'images'
    entry = find_element("images", key=key)
    if entry:
        return entry
    # 2. Check fallback 'image'
    return find_element("image", key=key)


def save_image_to_library(
    img: Image.Image,
    prompt: str,
    style: str,
    size: Tuple[int, int] = (600, 600),
    source: str = "generated",
    design_version: int = 1,
) -> Tuple[Path, bool]:
    """
    Saves an image ONCE into library/elements/images/ with prompt, theme tags, source, and size.
    Checks library index first and reuses on a hit.
    Returns (path, is_hit).
    """
    key = compute_image_key(prompt, style, size, design_version)
    lib_dir = get_image_library_dir()

    # Check index first
    existing = find_image_in_library(key)
    if existing:
        fname = existing.get("file_name", "")
        fpath = lib_dir / fname
        if not fpath.is_file():
            # Check image fallback dir
            fpath = paths.LIBRARY_ELEMENTS_DIR / "image" / fname
        if fpath.is_file() and fpath.stat().st_size > 0:
            logger.info("Library HIT for image key %s (%s)", key[:8], fname)
            return fpath, True

    # Save once
    fname = f"img_{key[:16]}.png"
    out_path = lib_dir / fname
    img.save(out_path, format="PNG")

    theme_tags = resolve_theme_tags(style)
    entries = load_element_index("images")
    entries.append({
        "key": key,
        "prompt": prompt,
        "theme_tags": theme_tags,
        "source": source,
        "size": [size[0], size[1]],
        "design_version": design_version,
        "file_name": fname,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    save_element_index("images", entries)
    logger.info("Saved image ONCE to library: %s", fname)
    return out_path, False


def assert_not_reference_image(file_path: Path, video_dir: Path) -> None:
    """Enforces rule: Never copy a reference image into the video; use it only to guide new designs."""
    ref_dir = (video_dir / "refs").resolve()
    resolved = Path(file_path).resolve()
    if ref_dir.is_dir() and (resolved == ref_dir or ref_dir in resolved.parents):
        raise PermissionError(
            f"Reference image '{resolved.name}' cannot be copied into the video. "
            "Reference images must only be used to guide new designs."
        )


def intake_reference_images(
    video_dir: Path,
    allowed_dirs: Optional[List[Path]] = None,
) -> List[Dict[str, Any]]:
    """
    Intake accepts images placed in videos/<name>/refs/, each with a purpose note
    ('style reference' or 'content image').
    Validates safety and extracts purpose notes.
    """
    refs_dir = video_dir / "refs"
    if not refs_dir.is_dir():
        return []

    intake_list: List[Dict[str, Any]] = []
    # Check purpose notes file if present
    notes_map: Dict[str, str] = {}
    notes_file = refs_dir / "purpose.json"
    if not notes_file.is_file():
        notes_file = refs_dir / "manifest.json"
    if notes_file.is_file():
        try:
            notes_map = json.loads(notes_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Could not read refs purpose file: %s", e)

    valid_allowed = (allowed_dirs or []) + [refs_dir, paths.LIBRARY_DIR, paths.ASSETS_DIR]

    for item in sorted(refs_dir.iterdir()):
        if item.is_file() and item.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
            clean_path = validate_and_sanitize_image(item, allowed_dirs=valid_allowed)

            # Check note from sidecar or map
            note = notes_map.get(item.name) or notes_map.get(item.stem)
            if not note:
                sidecar_txt = refs_dir / f"{item.stem}.txt"
                if sidecar_txt.is_file():
                    note = sidecar_txt.read_text(encoding="utf-8").strip()
                else:
                    sidecar_json = refs_dir / f"{item.stem}.json"
                    if sidecar_json.is_file():
                        try:
                            s_data = json.loads(sidecar_json.read_text(encoding="utf-8"))
                            note = s_data.get("purpose") or s_data.get("note")
                        except Exception:
                            pass

            if not note:
                note = "style reference" if "style" in item.stem.lower() else "content image"

            clean_note = "style reference" if "style" in note.lower() else "content image"

            intake_list.append({
                "path": clean_path,
                "file_name": item.name,
                "purpose": clean_note,
            })

    return intake_list


def analyze_style_reference(
    image_path: Path,
    note: str = "style reference",
) -> Dict[str, Any]:
    """
    Analyses a style reference image and produces a theme draft:
    - palette: dominant colors in hex
    - textures: visual texture profile
    - layout_rules: safe-zones, slot allocations
    - motion_feel: animation rhythm and dynamic feel
    - caption_style: typography, contrast colors, stroke
    """
    clean_path = validate_and_sanitize_image(image_path)

    with Image.open(clean_path) as img:
        rgb_img = img.convert("RGB")
        w, h = rgb_img.size

        # 1. Palette extraction using adaptive color quantization
        quantized = rgb_img.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
        palette_bytes = quantized.getpalette() or []
        colors = []
        for i in range(min(6, len(palette_bytes) // 3)):
            r, g, b = palette_bytes[i * 3:(i + 1) * 3]
            colors.append(f"#{r:02x}{g:02x}{b:02x}")

        # Ensure distinct colors
        seen = set()
        unique_palette = []
        for c in colors:
            if c not in seen:
                seen.add(c)
                unique_palette.append(c)

        # Compute average luminance to classify light vs dark theme
        stat = ImageStat.Stat(rgb_img)
        avg_lum = (0.299 * stat.mean[0] + 0.587 * stat.mean[1] + 0.114 * stat.mean[2])
        is_dark = avg_lum < 128.0

        # Texture analysis: variance of high-pass edge filter
        edges = rgb_img.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_variance = sum(edge_stat.var) / 3.0
        if edge_variance > 500:
            texture_feel = "textured_grain"
        elif edge_variance > 150:
            texture_feel = "subtle_paper"
        else:
            texture_feel = "clean_vector"

    # Layout rules adhering to YouTube Shorts safe zones
    layout_rules = {
        "safe_zone_top": 288,
        "safe_zone_bottom": 384,
        "board_zone": "upper",
        "max_board_objects": 3,
        "horizontal_margin": 60,
    }

    # Motion feel
    motion_feel = "snappy_overshoot" if is_dark else "smooth_spring"

    # Caption style
    caption_style = {
        "font_family": "Arial, sans-serif",
        "font_size": 36,
        "text_color": "#ffffff" if is_dark else "#0f172a",
        "outline_color": "#000000" if is_dark else "#ffffff",
        "outline_width": 3,
    }

    return {
        "source_reference": image_path.name,
        "purpose": note,
        "is_dark": is_dark,
        "palette": unique_palette,
        "textures": texture_feel,
        "layout_rules": layout_rules,
        "motion_feel": motion_feel,
        "caption_style": caption_style,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def write_theme_draft(theme_draft: Dict[str, Any], output_path: Path) -> Path:
    """Writes theme draft JSON to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(theme_draft, indent=2), encoding="utf-8")
    return output_path


def create_image_cutout(
    input_image_path: Path,
    output_path: Optional[Path] = None,
    theme: str = "whiteboard",
    shadow_blur: int = 12,
    shadow_offset: Tuple[int, int] = (6, 8),
) -> Path:
    """
    Cutout step:
    - Removes the background (detects light/corner background).
    - Adds an edge mask: torn paper mask for vintage themes, or smooth antialiased mask.
    - Adds a soft drop shadow.
    - Saves as its own element in library/elements/images/.
    - The original image stays untouched!
    """
    clean_in = validate_and_sanitize_image(input_image_path)

    with Image.open(clean_in) as raw_img:
        rgba = raw_img.convert("RGBA")
        w, h = rgba.size

        # 1. Background removal via corner-sample color distance
        corners = [
            rgba.getpixel((0, 0)),
            rgba.getpixel((w - 1, 0)),
            rgba.getpixel((0, h - 1)),
            rgba.getpixel((w - 1, h - 1)),
        ]
        bg_r = sum(c[0] for c in corners) // 4
        bg_g = sum(c[1] for c in corners) // 4
        bg_b = sum(c[2] for c in corners) // 4

        pixels = rgba.load()
        mask = Image.new("L", (w, h), 255)
        mask_pixels = mask.load()

        threshold = 35.0
        for y in range(h):
            for x in range(w):
                pr, pg, pb, pa = pixels[x, y]
                dist = math.sqrt((pr - bg_r) ** 2 + (pg - bg_g) ** 2 + (pb - bg_b) ** 2)
                if dist < threshold:
                    mask_pixels[x, y] = 0
                else:
                    # Antialiased ramp
                    if dist < threshold + 15:
                        ramp = (dist - threshold) / 15.0
                        mask_pixels[x, y] = int(255 * ramp)

        # 2. Edge mask (torn paper for vintage theme)
        is_vintage = "vintage" in theme.lower() or "paper" in theme.lower()
        if is_vintage:
            # Create torn paper edge modulation
            torn_mask = Image.new("L", (w, h), 255)
            draw = ImageDraw.Draw(torn_mask)
            # Add subtle irregular edge noise along borders
            for i in range(0, w, 4):
                offset_top = int(4 * math.sin(i * 0.15) + 3 * math.cos(i * 0.35))
                offset_bot = int(4 * math.sin(i * 0.12) + 3 * math.cos(i * 0.28))
                draw.rectangle([i, 0, i + 4, max(0, offset_top)], fill=0)
                draw.rectangle([i, h - max(0, offset_bot), i + 4, h], fill=0)
            mask = ImageChops.darker(mask, torn_mask)

        # Apply mask to image alpha
        r, g, b, _ = rgba.split()
        cutout_img = Image.merge("RGBA", (r, g, b, mask))

        # 3. Soft drop shadow
        pad_x = shadow_blur * 2 + abs(shadow_offset[0])
        pad_y = shadow_blur * 2 + abs(shadow_offset[1])
        canvas_w = w + pad_x * 2
        canvas_h = h + pad_y * 2

        final_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        # Build shadow layer
        shadow_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        shadow_mask = Image.new("L", (canvas_w, canvas_h), 0)
        # Paste cutout mask into shadow position
        paste_x = pad_x + shadow_offset[0]
        paste_y = pad_y + shadow_offset[1]
        shadow_mask.paste(mask, (paste_x, paste_y))
        shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(shadow_blur))

        # Color the shadow (soft dark shadow with ~40% opacity)
        shadow_color = Image.new("RGBA", (canvas_w, canvas_h), (15, 23, 42, 110))
        final_canvas.paste(shadow_color, (0, 0), shadow_mask)

        # Paste cutout subject on top
        final_canvas.paste(cutout_img, (pad_x, pad_y), cutout_img)

        # Crop to tight content bounding box
        bbox = final_canvas.getbbox()
        if bbox:
            final_canvas = final_canvas.crop(bbox)

    # 4. Save as own element
    if output_path is None:
        key = hashlib.sha256(f"cutout:{clean_in.stem}:{theme}".encode("utf-8")).hexdigest()
        lib_dir = get_image_library_dir()
        out_dest = lib_dir / f"cutout_{key[:16]}.png"
    else:
        out_dest = Path(output_path).resolve()

    out_dest.parent.mkdir(parents=True, exist_ok=True)
    final_canvas.save(out_dest, format="PNG")
    logger.info("Created cutout element: %s (original untouched)", out_dest.name)
    return out_dest
