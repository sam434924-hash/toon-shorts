"""
Purpose: Unit tests for Phase 2 Quality Gate:
         - Contrast-ratio calculation and WCAG thresholds
         - Real DOM and MP4 frame measurement engine (checks a-f)
         - Measured numbers markdown table per scene (no 10/10 self-graded score)
         - Failure of build on timing or framing violations
         - Fix rounds recording in visual review
         - Critic score stop-and-ask gate with --allow-low-score override
         - Layout block comparison and mismatch reporting
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
    measure_board_pixel_contrast,
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


def test_visual_checker_measured_table_and_markdown(tmp_path):
    """Verify visual check produces measured metrics table in visual_review.md and evaluates real requirements."""
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
                "board_objects": [{"id": "bo1", "start_ms": 500, "enter": "pop", "data": {"label": "Welcome"}}],
                "acting_plan": {"beats": [{"time_sec": 0.5, "cue": "wave"}]},
            }
        ]
    }
    (vid_dir / "scene.json").write_text(json.dumps(scene_data), encoding="utf-8")

    result = perform_visual_check(vid_dir, round_num=1)
    assert result["passed"] is True
    assert (vid_dir / "visual_review.md").is_file()

    md_content = (vid_dir / "visual_review.md").read_text(encoding="utf-8")
    assert "Measured Scene Performance (DOM & MP4 Frames)" in md_content
    assert "| Scene | Board Objects Valid | Max Board Gap (s) | Max Blank Board (s) | Max Gesture Gap (s) | In-Frame | Safe-Zone | Text Overlap Clear | Status |" in md_content
    assert "| 1 |" in md_content
    assert "10/10" not in md_content


def test_visual_checker_fails_build_on_violations(tmp_path):
    """Verify visual check fails and reports violations when timing or motion criteria are violated."""
    vid_dir = tmp_path / "fail_video"
    stills_dir = vid_dir / "stills"
    stills_dir.mkdir(parents=True)

    scene_data = {
        "art_style": "whiteboard",
        "scenes": [
            {
                "scene_number": 1,
                "dialogue": "Long delay before anything happens.",
                # First board object appears at 3500ms (> 2.0s blank board failure!)
                "board_objects": [{"id": "bo_late", "start_ms": 3500, "enter": "pop", "data": {"label": "Late"}}],
            }
        ]
    }
    (vid_dir / "scene.json").write_text(json.dumps(scene_data), encoding="utf-8")

    result = perform_visual_check(vid_dir, round_num=1)
    assert result["passed"] is False
    assert any("blank_board_le_2s" in iss for iss in result["issues"])
    md_content = (vid_dir / "visual_review.md").read_text(encoding="utf-8")
    assert "FAILED" in md_content


def test_visual_checker_multiple_rounds(tmp_path):
    """Verify up to 2 fix rounds append audit logs to visual_review.md."""
    vid_dir = tmp_path / "fix_video"
    stills_dir = vid_dir / "stills"
    stills_dir.mkdir(parents=True)

    still_img = Image.new("RGB", (1080, 1920), color=(20, 20, 30))
    still_img.save(stills_dir / "fix_video_still_sc1.png")

    scene_data = {
        "art_style": "whiteboard",
        "scenes": [
            {
                "scene_number": 1,
                "dialogue": "Round test",
                "board_objects": [{"id": "bo1", "start_ms": 500, "enter": "pop", "data": {"label": "Round"}}],
                "acting_plan": {"beats": [{"time_sec": 0.5, "cue": "nod"}]},
            }
        ]
    }
    (vid_dir / "scene.json").write_text(json.dumps(scene_data), encoding="utf-8")

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


def test_critic_runs_on_pre_authored_scene_files(tmp_path, monkeypatch):
    """Verify critic runs on hand-written or pre-authored scene files and stops if score < 7.0 unless --allow-low-score."""
    from toonshorts.plugins.llm.fake import FakeLLMPlugin
    from toonshorts.core.models import CriticReview, ScriptPlan, Scene, Character, Pose, CameraMove, Transition
    from toonshorts.core.pipeline import run_pipeline_from_brief
    from toonshorts.brief import VideoBrief

    base_dir = tmp_path / "videos"
    base_dir.mkdir()

    pre_authored_plan = ScriptPlan(
        version=2,
        title="pre_authored_test",
        art_style="stickman",
        emotional_arc="Pre-authored script test",
        characters=[
            Character(name="Pip", visual_description="Stickman", voice_id="v1"),
            Character(name="Zack", visual_description="Stickman 2", voice_id="v2"),
        ],
        scenes=[
            Scene(scene_number=1, speaker="Pip", dialogue_line="This is a hand-written scene.", action="Talks", pose=Pose.IDLE, camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False, cast=["Pip", "Zack"], layout="cards"),
            Scene(scene_number=2, speaker="Zack", dialogue_line="What is the scene about?", action="Questions", pose=Pose.IDLE, camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False, cast=["Pip", "Zack"], layout="cards"),
            Scene(scene_number=3, speaker="Pip", dialogue_line="It is about testing pre-authored scripts.", action="Explains", pose=Pose.WAVING, camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=False, cast=["Pip", "Zack"], layout="cards"),
            Scene(scene_number=4, speaker="Zack", dialogue_line="And here is the punchline!", action="Laughs", pose=Pose.LAUGHING, camera_move=CameraMove.STATIC, transition=Transition.FADE, is_punchline=True, cast=["Pip", "Zack"], layout="cards"),
        ],
    )

    brief = VideoBrief(
        video_name="pre_authored_test",
        story="Pre-authored story test",
        format="comedy story",
        style="stickman",
        characters=["Pip", "Zack"],
        speaker="both",
        voice="fake",
        voice_engine="fake",
        camera="fixed",
        length_seconds=10,
    )

    def mock_refine(self, plan, preset):
        low_review = CriticReview(
            score=6.2,
            hook_strength=6.0,
            joke_quality=6.0,
            pacing=6.5,
            variety=6.0,
            weakest_scene_index=1,
            revision_instructions="Pacing needs work",
        )
        return plan, low_review

    monkeypatch.setattr(FakeLLMPlugin, "review_and_refine", mock_refine)

    # 1. Pipeline MUST halt on low score even for pre-authored scene file
    with pytest.raises(ValueError, match="Critic score 6.2/10 is under 7.0"):
        run_pipeline_from_brief(
            brief_source=brief,
            output_dir=base_dir,
            mock=True,
            overwrite=True,
            scene_source=pre_authored_plan,
            allow_low_score=False,
        )

    # 2. Pipeline proceeds when allow_low_score=True
    result = run_pipeline_from_brief(
        brief_source=brief,
        output_dir=base_dir,
        mock=True,
        overwrite=True,
        scene_source=pre_authored_plan,
        allow_low_score=True,
    )
    assert result is not None
    assert (base_dir / "pre_authored_test" / "pre_authored_test.mp4").is_file()


def test_visual_checker_compares_stills_with_layout_block(tmp_path):
    """Verifies that check-visuals compares each still with its layout block and identifies mismatches."""
    vid_dir = tmp_path / "layout_compare_video"
    stills_dir = vid_dir / "stills"
    stills_dir.mkdir(parents=True)

    # Valid still image with sufficient visual range
    from PIL import ImageDraw
    img = Image.new("RGB", (1080, 1920), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([200, 400, 500, 700], fill=(56, 189, 248))
    img.save(stills_dir / "layout_compare_video_still_sc1.png")

    # Mismatched layout: declares unknown template and non-existent hero
    bad_scene_data = {
        "art_style": "night_studio",
        "scenes": [
            {
                "scene_number": 1,
                "dialogue": "Notice the padlock graphic right here.",
                "visuals": [{"id": "diff_elem", "type": "text_pop", "data": {"text": "Hello"}}],
                "layout": {
                    "template": "nonexistent_template",
                    "hero": "missing_hero_padlock",
                    "slots": {"invalid_slot": "diff_elem"},
                },
            }
        ],
    }
    (vid_dir / "scene.json").write_text(json.dumps(bad_scene_data), encoding="utf-8")

    result = perform_visual_check(vid_dir, round_num=1)
    md_content = (vid_dir / "visual_review.md").read_text(encoding="utf-8")

    assert "Layout template 'nonexistent_template' is not recognized" in md_content
    assert "Declared hero 'missing_hero_padlock' not found" in md_content
    assert any("not recognized" in iss for iss in result["issues"])


def test_calm_background_topic_layers_and_contrast_check(tmp_path):
    """Verifies calm background design version 2, topic-aware ambient layer, and automatic contrast ratio >= 4.5:1."""
    from toonshorts.core import config
    from toonshorts.plugins.render.animejs.layout import build_topic_background_layer
    from PIL import ImageDraw

    # 1. Background design version bumped to 2
    assert config.BACKGROUND_DESIGN_VERSION == 2

    # 2. Topic-aware background elements layer
    security_svg = build_topic_background_layer(topic="How hackers actually break into systems", theme="night_studio")
    assert "topic-lock" in security_svg
    assert "topic-shield" in security_svg
    assert "topic-drift-slow" in security_svg

    # 3. Automatic contrast ratio check on calm dark board with background layers on
    test_still = tmp_path / "still_sc1.png"
    still_img = Image.new("RGB", (1080, 1920), color=(5, 11, 20))
    draw = ImageDraw.Draw(still_img)
    draw.rectangle([60, 288, 960, 808], fill=(8, 14, 25))
    draw.rectangle([200, 400, 600, 600], fill=(30, 41, 59))
    draw.text((250, 450), "Safe White Text", fill=(248, 250, 252))
    draw.line([250, 500, 550, 500], fill=(56, 189, 248), width=2)
    still_img.save(test_still, format="PNG")

    contrast = measure_board_pixel_contrast(
        test_still,
        board_rect=(60, 288, 960, 808),
        text_color="#f8fafc",
        thin_stroke_color="#38bdf8",
    )
    assert contrast["passed"] is True
    assert contrast["text_contrast_ratio"] >= 4.5
    assert contrast["thin_stroke_contrast_ratio"] >= 4.5
