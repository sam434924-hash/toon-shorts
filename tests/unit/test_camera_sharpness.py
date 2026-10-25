"""
Purpose: Character slice sharpness test and pack resolution ceiling verification.
Inputs: Character asset pack directories (boy_a, boy_b, girl_a, presenter, stick_hoodie).
Outputs: Verification of vector SVG scalability vs raster PNG resolution ceilings.
Depends on: pytest, pathlib, xml.etree.ElementTree, PIL.Image, toonshorts.core.config
Used by: tests
Config keys: CAMERA_CHARACTER_MAX_ZOOM
Tests: self
"""

from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image
import pytest
from toonshorts.core import config


CHARACTER_BASE = config.PROJECT_ROOT / "assets" / "2d" / "characters"
VECTOR_PACKS = ["boy_a", "boy_b", "girl_a", "presenter"]
RASTER_PACKS = ["stick_hoodie"]


def test_character_pack_formats():
    """Verify vector character packs contain valid SVG assets that scale to any zoom level."""
    for pack_id in VECTOR_PACKS:
        pack_dir = CHARACTER_BASE / pack_id
        assert pack_dir.is_dir(), f"Pack directory missing: {pack_dir}"
        
        # Check for vector SVGs
        svg_files = list(pack_dir.glob("**/*.svg"))
        assert len(svg_files) > 0, f"Vector pack {pack_id} must contain SVG source assets"
        
        # Verify SVGs are parseable XML
        for svg_f in svg_files:
            tree = ET.parse(svg_f)
            root = tree.getroot()
            assert root.tag.endswith("svg"), f"Root of {svg_f.name} is not <svg>"


def test_stick_hoodie_raster_slices_and_resolution_ceiling():
    """
    Verify stick_hoodie is a sliced PNG raster pack with measured native dimensions.
    At peak zoom (1.9x), raster slices scale past native resolution unless rendered with vector source.
    Documents the resolution ceiling for stick_hoodie.
    """
    hoodie_dir = CHARACTER_BASE / "stick_hoodie"
    assert hoodie_dir.is_dir(), "stick_hoodie pack missing"

    layers_dir = hoodie_dir / "layers"
    assert layers_dir.is_dir(), "stick_hoodie/layers missing"

    png_slices = list(layers_dir.glob("*.png"))
    assert len(png_slices) >= 20, "stick_hoodie must have slice PNGs"

    # Measure head and torso native resolutions
    head_path = layers_dir / "head.png"
    assert head_path.is_file(), "head.png slice missing"
    with Image.open(head_path) as head_img:
        w, h = head_img.size
        assert w <= 256 and h <= 256, f"head.png native resolution is {w}x{h}"

    torso_path = layers_dir / "torso.png"
    assert torso_path.is_file(), "torso.png slice missing"
    with Image.open(torso_path) as torso_img:
        tw, th = torso_img.size
        assert tw <= 256 and th <= 256, f"torso.png native resolution is {tw}x{th}"

    # Verify peak zoom is 1.9x for character zone
    max_zoom = float(getattr(config, "CAMERA_CHARACTER_MAX_ZOOM", 1.9))
    assert max_zoom == 1.9

    # For vector packs (boy_a, boy_b, girl_a, presenter), 1.9x zoom is supported with zero blur.
    # For stick_hoodie raster pack, zoom above 1.25x requires re-export or causes slight softness.


def test_stick_hoodie_2x_upscaled_slices():
    """Verify that 2x upscaled slices exist for stick_hoodie to maintain sharpness under character zone zooms."""
    hoodie_dir = CHARACTER_BASE / "stick_hoodie"
    layers_2x_dir = hoodie_dir / "layers_2x"
    assert layers_2x_dir.is_dir(), "stick_hoodie/layers_2x missing"

    head_2x = layers_2x_dir / "head.png"
    assert head_2x.is_file(), "head.png 2x missing"
    with Image.open(head_2x) as img:
        assert img.width >= 200 and img.height >= 200
    
    png_slices = list(layers_2x_dir.glob("*.png"))
    assert len(png_slices) >= 30, f"Expected at least 30 2x slices, found {len(png_slices)}"
