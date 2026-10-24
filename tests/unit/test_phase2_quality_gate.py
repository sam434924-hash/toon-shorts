"""
Purpose: Unit tests for Phase 2 Quality Gate:
         - Contrast-ratio calculation and WCAG thresholds
         - Quality gate checklist (6 items) and visual_review.md generation
         - Fix rounds recording in visual review
         - Critic score stop-and-ask gate with --allow-low-score override
         - CLI check-visuals command
Inputs: Mock scene stills, test video folders, color tokens.
Outputs: Pytest assertions verifying quality gate enforcement.
Depends on: pytest, PIL, toonshorts.core.visual_checker, toonshorts.cli, toonshorts.core.pipeline
Used by: Test suite
Config keys: None
Tests: tests/unit/test_phase2_quality_gate.py
"""

import json
from pathlib import Path
import pytest
from PIL import Image

from toonshorts.core.visual_checker import (
    calculate_contrast_ratio,
    calculate_relative_luminance,
    check_contrast_ratio,
    perform_visual_check,
)
from toonshorts.core.models import ScriptPlan, Scene
from toonshorts.core.pipeline import run_pipeline
from toonshorts.cli import main


def test_contrast_ratio_calculations():
    """Verify WCAG relative luminance and contrast ratio calculations."""
    # Maximum contrast: Black on White is 21.0:1
    assert calculate_contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, 0.1)

    # Identical colors: 1.0:1
    assert calculate_contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0, 0.01)

    # Whiteboard theme colors (#0f172a on #f8fafc)
    ratio, passes = check_contrast_ratio("#0f172a", "#f8fafc")
    assert ratio > 15.0
    assert passes is True

    # Low contrast failure (#777777 on #888888)
    low_ratio, low_passes = check_contrast_ratio("#777777", "#888888", is_large_text=False)
    assert low_ratio < 2.0
    assert low_passes is False


def test_visual_checker_checklist_and_markdown(tmp_path):
    """Verify visual check validates 6 checklist items and writes visual_review.md."""
    vid_dir = tmp_path / "test_video"
    stills_dir = vid_dir / "stills"
    stills_dir.mkdir(parents=True)

    # Create dummy still image
    still_img = Image.new("RGB", (1080, 1920), color=(248, 250, 252))
    still_file = stills_dir / "test_video_still_sc1.png"
    still_img.save(still_file)

    scene_data = {
        "art_style": "whiteboard",
        "scenes": [
            {
                "scene_number": 1,
                "dialogue": "Welcome to our video!",
                "visuals": [{"type": "text_pop", "data": {"text": "Welcome"}}],
            }
        ]
    }
    (vid_dir / "scene.json").write_text(json.dumps(scene_data), encoding="utf-8")

    result = perform_visual_check(vid_dir, round_num=1)
    assert result["score"] >= 7.0
    assert (vid_dir / "visual_review.md").is_file()

    md_content = (vid_dir / "visual_review.md").read_text(encoding="utf-8")
    assert "Quality Gate Checklist" in md_content
    assert "Text readable against its background" in md_content
    assert "Nothing overlapping or clipped" in md_content
    assert "Board looks designed and not plain" in md_content
    assert "Style matches the characters" in md_content
    assert "Motion beats exist for every key word" in md_content
    assert "Nothing important in top 288 px or under captions" in md_content
    assert "Automated Contrast Ratio Verification" in md_content


def test_visual_checker_multiple_rounds(tmp_path):
    """Verify up to 2 fix rounds append audit logs to visual_review.md."""
    vid_dir = tmp_path / "fix_video"
    stills_dir = vid_dir / "stills"
    stills_dir.mkdir(parents=True)

    still_img = Image.new("RGB", (1080, 1920), color=(20, 20, 30))
    (stills_dir / "fix_video_still_sc1.png").touch()
    still_img.save(stills_dir / "fix_video_still_sc1.png")

    # Round 1
    r1 = perform_visual_check(vid_dir, round_num=1)
    assert r1["round"] == 1

    # Round 2
    r2 = perform_visual_check(vid_dir, round_num=2)
    assert r2["round"] == 2

    md_content = (vid_dir / "visual_review.md").read_text(encoding="utf-8")
    assert "Round 1" in md_content
    assert "Round 2" in md_content


def test_critic_low_score_stopping_and_allow_flag(tmp_path, monkeypatch):
    """Verify critic stopping when score < 7.0 unless --allow-low-score is passed."""
    from toonshorts.plugins.llm.fake import FakeLLMPlugin
    from toonshorts.core.models import CriticReview

    base_dir = tmp_path / "videos"
    base_dir.mkdir()

    # Mock FakeLLMPlugin to return low critic score (5.5)
    def mock_refine(self, plan, preset):
        low_review = CriticReview(
            score=5.5,
            hook_strength=5.0,
            joke_quality=5.5,
            pacing=6.0,
            variety=5.5,
            weakest_scene_index=1,
            revision_instructions="Hook lacks punch",
        )
        return plan, low_review

    monkeypatch.setattr(FakeLLMPlugin, "review_and_refine", mock_refine)

    # 1. Without allow_low_score, pipeline must halt
    with pytest.raises(ValueError, match="Critic score 5.5/10 is under 7.0"):
        run_pipeline(
            topic="low_score_topic",
            style_name="stickman",
            output_dir=base_dir,
            mock=True,
            auto_confirm=True,
            allow_low_score=False,
        )

    # 2. With allow_low_score=True, pipeline proceeds
    result = run_pipeline(
        topic="low_score_topic",
        style_name="stickman",
        output_dir=base_dir,
        mock=True,
        auto_confirm=True,
        overwrite=True,
        allow_low_score=True,
    )
    assert result is not None
    assert result.is_file()
