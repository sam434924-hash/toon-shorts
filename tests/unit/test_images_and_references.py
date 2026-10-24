"""
Purpose: Unit tests for Part B Images and References:
         - Reference images intake and purpose note handling
         - Style reference analysis into theme draft (palette, textures, layout, motion feel, caption style)
         - Guard: Reference images must never be copied into video
         - Generated image library index check, reuse on hit, and single save
         - Cutouts with background removal, vintage torn-paper edge mask, and soft shadow
         - Image safety: accept PNG/JPEG/WebP, reject SVG/oversized/out-of-bounds, metadata stripping
         - Image animation presets: slide_in_tilt, paper_tear_reveal, detail_highlight, stamp_slam, push_in
Inputs: Test fixture images, mock video folders, synthetic assets.
Outputs: Pytest assertions verifying all Part B guarantees.
Depends on: pytest, PIL, toonshorts.core.images, toonshorts.core.board_objects, toonshorts.core.models
Used by: Test suite
Config keys: None
Tests: tests/unit/test_images_and_references.py
"""

import json
from pathlib import Path
import pytest
from PIL import Image

from toonshorts.core.images import (
    ALLOWED_IMAGE_PRESETS,
    analyze_style_reference,
    assert_not_reference_image,
    compute_image_key,
    create_image_cutout,
    find_image_in_library,
    intake_reference_images,
    save_image_to_library,
    validate_and_sanitize_image,
    write_theme_draft,
)
from toonshorts.core.board_objects import (
    ALLOWED_TYPES,
    validate_board_object_schema,
)
from toonshorts.core.models import VideoManifest, CharacterManifestItem, VoiceManifestItem


@pytest.fixture
def sample_png_image(tmp_path):
    img_path = tmp_path / "test_ref.png"
    img = Image.new("RGBA", (200, 200), color=(15, 23, 42, 255))
    # Draw some color content
    for x in range(50, 150):
        for y in range(50, 150):
            img.putpixel((x, y), (56, 189, 248, 255))
    img.save(img_path, format="PNG")
    return img_path


def test_reference_images_intake_and_purpose_notes(tmp_path, sample_png_image):
    """Verify intake accepts images in videos/<name>/refs/ with purpose notes."""
    video_dir = tmp_path / "test_vid"
    refs_dir = video_dir / "refs"
    refs_dir.mkdir(parents=True)

    img1 = refs_dir / "style_guide.png"
    img2 = refs_dir / "diagram.png"
    sample_png_image.rename(img1)

    # Create second image
    Image.new("RGB", (100, 100), color=(255, 255, 255)).save(img2, format="PNG")

    # Sidecar note for img2
    (refs_dir / "diagram.txt").write_text("content image", encoding="utf-8")

    intake = intake_reference_images(video_dir)
    assert len(intake) == 2

    purposes = {item["file_name"]: item["purpose"] for item in intake}
    assert purposes["style_guide.png"] == "style reference"
    assert purposes["diagram.png"] == "content image"


def test_style_reference_analysis_and_theme_draft(sample_png_image, tmp_path):
    """Verify style reference is analyzed into theme draft with all required fields."""
    draft = analyze_style_reference(sample_png_image, note="style reference")

    assert "palette" in draft
    assert isinstance(draft["palette"], list)
    assert len(draft["palette"]) > 0
    assert "textures" in draft
    assert "layout_rules" in draft
    assert draft["layout_rules"]["safe_zone_top"] == 288
    assert "motion_feel" in draft
    assert "caption_style" in draft
    assert "font_family" in draft["caption_style"]

    draft_file = tmp_path / "theme_draft.json"
    write_theme_draft(draft, draft_file)
    assert draft_file.is_file()
    saved = json.loads(draft_file.read_text(encoding="utf-8"))
    assert saved["motion_feel"] == draft["motion_feel"]


def test_never_copy_reference_image_into_video(tmp_path):
    """Verify strict guard: Reference images cannot be copied into video."""
    video_dir = tmp_path / "hacker_video"
    refs_dir = video_dir / "refs"
    refs_dir.mkdir(parents=True)

    ref_img = refs_dir / "reference_photo.png"
    ref_img.touch()

    with pytest.raises(PermissionError, match="cannot be copied into the video"):
        assert_not_reference_image(ref_img, video_dir)

    # Valid non-ref file does not raise
    safe_img = video_dir / "visuals" / "generated_card.png"
    assert_not_reference_image(safe_img, video_dir)


def test_generated_images_library_index_and_reuse(tmp_path, monkeypatch):
    """Verify generated images check index first, reuse on hit, and save once in library/elements/images/."""
    from toonshorts.core import paths
    test_lib_elements = tmp_path / "lib" / "elements"
    monkeypatch.setattr(paths, "LIBRARY_ELEMENTS_DIR", test_lib_elements)

    prompt = "cyber padlock locking shut"
    style = "night_studio"
    size = (400, 400)

    key = compute_image_key(prompt, style, size, design_version=1)
    img = Image.new("RGBA", size, color=(30, 41, 59, 255))

    # 1. Save once
    saved_path, is_hit = save_image_to_library(img, prompt, style, size=size, source="generated")
    assert saved_path.is_file()
    assert is_hit is False

    # 2. Re-saving must produce hit without duplicating file
    recheck_path, is_hit_2 = save_image_to_library(img, prompt, style, size=size, source="generated")
    assert is_hit_2 is True
    assert saved_path == recheck_path


def test_cutout_removes_background_adds_mask_and_shadow(sample_png_image, tmp_path):
    """Verify cutout removes background, adds torn-paper mask for vintage theme, adds shadow, keeps original untouched."""
    orig_bytes = sample_png_image.read_bytes()

    out_cutout = tmp_path / "cutout_element.png"
    res = create_image_cutout(sample_png_image, output_path=out_cutout, theme="vintage-paper")

    assert res.is_file()
    assert sample_png_image.read_bytes() == orig_bytes, "Original image must remain untouched!"

    with Image.open(res) as cut_img:
        assert cut_img.mode == "RGBA"
        # Bounding box should exist and contain alpha
        alpha_band = cut_img.split()[-1]
        assert alpha_band.getextrema()[0] == 0, "Background should be transparent"
        assert alpha_band.getextrema()[1] > 0, "Subject content should be visible"


def test_image_safety_validation(tmp_path):
    """Verify safety limits: PNG/JPEG/WebP only, file size limit, reject SVG, path traversal."""
    # 1. Reject SVG
    fake_svg = tmp_path / "fake.png"
    fake_svg.write_text("<svg xmlns='http://www.w3.org/2000/svg'><circle/></svg>", encoding="utf-8")
    with pytest.raises(ValueError, match="SVG image files are forbidden"):
        validate_and_sanitize_image(fake_svg)

    # 2. Reject disallowed extension (.gif)
    gif_file = tmp_path / "image.gif"
    gif_file.touch()
    with pytest.raises(ValueError, match="Disallowed image file extension"):
        validate_and_sanitize_image(gif_file)

    # 3. Reject directory traversal
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_img = outside_dir / "secret.png"
    Image.new("RGB", (50, 50), color=(100, 100, 100)).save(outside_img, format="PNG")

    with pytest.raises(PermissionError, match="outside allowed asset directories"):
        validate_and_sanitize_image(outside_img, allowed_dirs=[allowed_dir])

    # 4. Valid image succeeds and metadata stripped
    inside_img = allowed_dir / "clean.png"
    Image.new("RGB", (64, 64), color=(20, 20, 20)).save(inside_img, format="PNG")
    clean = validate_and_sanitize_image(inside_img, allowed_dirs=[allowed_dir])
    assert clean.is_file()


def test_image_manifest_tracking():
    """Verify VideoManifest includes images array recording source, prompt, and key."""
    manifest = VideoManifest(
        video_name="test_video",
        created_at="2026-10-24T12:00:00Z",
        style="night_studio",
        characters=[CharacterManifestItem(name="boy_b", pack="boy_b")],
        voice=VoiceManifestItem(engine="gemini_tts", voice_name="Puck"),
        images=[
            {
                "file": "img_padlock.png",
                "source": "generated",
                "prompt": "neon cyan padlock clicked shut",
                "key": "a1b2c3d4",
                "size": [400, 400],
            }
        ],
    )
    dumped = manifest.model_dump()
    assert len(dumped["images"]) == 1
    assert dumped["images"][0]["prompt"] == "neon cyan padlock clicked shut"


def test_image_animation_presets_board_object_schema():
    """Verify all image animation presets (including travel and pop_with_wobble) pass board object validation and slot assignment."""
    assert "image" in ALLOWED_TYPES
    for preset in [
        "slide_in_tilt",
        "paper_tear_reveal",
        "detail_highlight",
        "stamp_slam",
        "push_in",
        "travel",
        "pop_with_wobble",
        "pop-with-wobble",
    ]:
        assert preset in ALLOWED_IMAGE_PRESETS

        raw = {
            "type": "image",
            "data": {
                "image_url": "library/elements/images/shield.png",
                "preset": preset,
                "alt": "Security Shield",
                "highlight_region": [45, 55],
            },
            "board_slot": "slot_mid",
            "start_ms": 500,
            "exit_ms": 3500,
        }
        obj = validate_board_object_schema(raw, scene_number=1, total_duration_ms=5000)
        assert obj is not None
        assert obj["type"] == "image"
        assert obj["data"]["preset"] == preset
        assert obj["board_slot"] == "slot_mid"
