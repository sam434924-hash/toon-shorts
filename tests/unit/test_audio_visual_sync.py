"""
Purpose: Unit tests for audio-visual word timing synchronization and sync verification report.
Inputs: Synthetic script plans, simulated Whisper misheard transcripts, and cue timings.
Outputs: Assertion results verifying mandatory timing, fuzzy alignment, and 150ms check enforcement.
Depends on: pathlib, pytest, toonshorts.core.errors, toonshorts.core.models, toonshorts.core.sync
Used by: tests
Config keys: MAX_SYNC_DIFFERENCE_MS
Tests: tests/unit/test_audio_visual_sync.py
"""

from pathlib import Path
import pytest

from toonshorts.core.errors import PipelineError
from toonshorts.core.models import Character, Scene, SceneAudio, ScriptPlan, Visual, WordTiming
from toonshorts.core.sync import (
    enforce_and_prepare_word_timings,
    fuzzy_align_script_to_whisper,
    generate_sync_report,
    tidy_video_folder,
)


def _make_dummy_plan() -> ScriptPlan:
    return ScriptPlan(
        title="Sync Test Video",
        art_style="night_studio",
        emotional_arc="Curiosity to empowerment",
        characters=[
            Character(name="boy_b", visual_description="Boy character"),
            Character(name="girl_a", visual_description="Girl character"),
        ],
        scenes=[
            Scene(
                scene_number=1,
                speaker="boy_b",
                dialogue_line="Wait, do movie hackers really smash keyboards to break into your account?",
                action="Boy wonders about hackers",
                visuals=[
                    Visual(type="check_cross", trigger_word="account", params={"icon": "cross"})
                ],
            ),
            Scene(
                scene_number=2,
                speaker="girl_a",
                dialogue_line="Not even close! Most breaches happen because people reuse simple passwords everywhere.",
                action="Girl explains password reuse",
                visuals=[
                    Visual(type="flow", trigger_word="everywhere", params={"nodes": ["A", "B"]})
                ],
            ),
            Scene(
                scene_number=3,
                speaker="boy_b",
                dialogue_line="So if one random shopping site leaks, they get into everything?",
                action="Boy is shocked",
            ),
            Scene(
                scene_number=4,
                speaker="girl_a",
                dialogue_line="Definitely not! Make it long, make it unique, and lock it down!",
                action="Girl gives closing advice",
                is_punchline=True,
            ),
        ],
    )


def test_timing_is_required(tmp_path: Path):
    """Word timing is mandatory: missing word timings without fallback raises PipelineError."""
    plan = _make_dummy_plan()
    dummy_audios = [
        SceneAudio(
            scene_index=i,
            audio_path=tmp_path / f"non_existent_{i}.wav",
            duration_seconds=4.5,
            scene_total_duration=5.0,
            word_timings=[],
        )
        for i in range(4)
    ]

    with pytest.raises(PipelineError, match="Word timing is mandatory"):
        enforce_and_prepare_word_timings(
            plan=plan,
            scene_audios=dummy_audios,
            video_dir=tmp_path,
            allow_fallback=False,
        )


def test_fallback_needs_the_flag(tmp_path: Path):
    """Fallback to proportional timing is rejected by default and requires allow_fallback=True."""
    plan = _make_dummy_plan()
    dummy_audios = [
        SceneAudio(
            scene_index=i,
            audio_path=tmp_path / f"non_existent_{i}.wav",
            duration_seconds=4.5,
            scene_total_duration=5.0,
            word_timings=[],
        )
        for i in range(4)
    ]

    # 1. Without flag: fails
    with pytest.raises(PipelineError):
        enforce_and_prepare_word_timings(
            plan=plan,
            scene_audios=dummy_audios,
            video_dir=tmp_path,
            allow_fallback=False,
        )

    # 2. With allow_fallback=True: succeeds with proportional timing
    res = enforce_and_prepare_word_timings(
        plan=plan,
        scene_audios=dummy_audios,
        video_dir=tmp_path,
        allow_fallback=True,
    )
    assert "scene_1" in res
    assert len(res["scene_1"]) > 0
    assert (tmp_path / "word_timings.json").is_file()


def test_fuzzy_matcher_handles_misheard_word():
    """Fuzzy matcher matches Whisper heard tokens ('actors' -> 'hackers') and interpolates gaps."""
    script_text = "Wait, do movie hackers really smash keyboards to break into your account?"
    # Whisper hears 'actors' instead of 'hackers', and misses 'keyboards'
    whisper_output = [
        WordTiming(word="Wait,", start_time=0.0, end_time=0.50),
        WordTiming(word="do", start_time=0.64, end_time=0.80),
        WordTiming(word="movie", start_time=0.80, end_time=1.04),
        WordTiming(word="actors", start_time=1.04, end_time=1.48),  # Misheard 'hackers'
        WordTiming(word="really", start_time=1.48, end_time=2.18),
        WordTiming(word="smash", start_time=2.18, end_time=2.70),
        # 'keyboards' is completely missing in audio transcription
        WordTiming(word="to", start_time=3.10, end_time=3.46),
        WordTiming(word="break", start_time=3.46, end_time=3.64),
        WordTiming(word="into", start_time=3.64, end_time=3.82),
        WordTiming(word="your", start_time=3.82, end_time=3.98),
        WordTiming(word="account?", start_time=3.98, end_time=4.24),
    ]

    aligned = fuzzy_align_script_to_whisper(
        script_text=script_text,
        whisper_words=whisper_output,
        total_duration=4.5,
        scene_number=1,
    )

    word_map = {wt.word: wt for wt in aligned}

    # 1. Ground truth word preserved despite Whisper hearing 'actors'
    assert "hackers" in word_map
    assert word_map["hackers"].start_time == 1.04
    assert word_map["hackers"].end_time == 1.48

    # 2. Unmatched word 'keyboards' was interpolated between 'smash' (2.70) and 'to' (3.10)
    assert "keyboards" in word_map
    assert 2.70 <= word_map["keyboards"].start_time < word_map["keyboards"].end_time <= 3.10

    # 3. Exact word 'account?' matched cleanly
    assert "account?" in word_map
    assert word_map["account?"].start_time == 3.98


def test_150ms_check_fails_correctly(tmp_path: Path):
    """Sync report fails the pipeline when cue timing difference exceeds 150ms."""
    # 1. Valid sync within 150ms (diff = 0ms for visual, 130ms for camera lead-in)
    plan_good = _make_dummy_plan()
    for s in plan_good.scenes:
        s.word_timings = [
            WordTiming(word="Wait,", start_time=0.0, end_time=0.5),
            WordTiming(word="account", start_time=3.98, end_time=4.24),
            WordTiming(word="everywhere", start_time=4.50, end_time=4.80),
            WordTiming(word="down!", start_time=3.00, end_time=3.50),
        ]

    report_good = generate_sync_report(
        plan=plan_good,
        output_path=tmp_path / "sync_good.txt",
        max_diff_ms=150,
        allow_fallback=False,
    )
    assert report_good["passed"] is True
    assert report_good["overall_max_diff"] <= 150
    assert (tmp_path / "sync_good.txt").is_file()

    # 2. Desynchronized cue (trigger word missing or placed with even-spacing offset > 150ms)
    plan_bad = _make_dummy_plan()
    plan_bad.scenes[0].word_timings = [
        WordTiming(word="Wait,", start_time=0.0, end_time=0.5),
        WordTiming(word="other", start_time=1.0, end_time=1.5),
    ]

    with pytest.raises(PipelineError, match="Audio-visual sync verification FAILED"):
        generate_sync_report(
            plan=plan_bad,
            output_path=tmp_path / "sync_bad.txt",
            max_diff_ms=150,
            allow_fallback=False,
        )


def test_tidy_video_folder(tmp_path: Path):
    """Intermediate files are moved into work/ leaving only clean top-level files."""
    # Create top level allowed files
    (tmp_path / "test.mp4").write_text("mp4", encoding="utf-8")
    (tmp_path / "brief.json").write_text("{}", encoding="utf-8")
    (tmp_path / "scene.json").write_text("{}", encoding="utf-8")
    (tmp_path / "word_timings.json").write_text("{}", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "captions.ass").write_text("ass", encoding="utf-8")
    (tmp_path / "run.log").write_text("log", encoding="utf-8")
    (tmp_path / "layout_check.txt").write_text("layout", encoding="utf-8")
    (tmp_path / "sync_report.txt").write_text("sync", encoding="utf-8")

    # Create intermediate files that should be moved
    (tmp_path / "animejs_scene_1.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "mixed_clip_1.mp4").write_text("mixed", encoding="utf-8")
    (tmp_path / "unsubbed_full.mp4").write_text("raw", encoding="utf-8")
    (tmp_path / "scene_1_still.html").write_text("html", encoding="utf-8")
    (tmp_path / "sfx_pop.wav").write_text("wav", encoding="utf-8")
    (tmp_path / "concat_list.txt").write_text("concat", encoding="utf-8")
    (tmp_path / "layout_check.json").write_text("json", encoding="utf-8")

    tidy_video_folder(tmp_path)

    work_dir = tmp_path / "work"
    assert work_dir.is_dir()
    assert (work_dir / "animejs_scene_1.mp4").is_file()
    assert (work_dir / "mixed_clip_1.mp4").is_file()
    assert (work_dir / "unsubbed_full.mp4").is_file()
    assert (work_dir / "scene_1_still.html").is_file()
    assert (work_dir / "sfx_pop.wav").is_file()
    assert (work_dir / "concat_list.txt").is_file()
    assert (work_dir / "layout_check.json").is_file()

    # Verify they no longer exist in top-level
    assert not (tmp_path / "animejs_scene_1.mp4").exists()
    assert not (tmp_path / "mixed_clip_1.mp4").exists()
    assert not (tmp_path / "scene_1_still.html").exists()

    # Verify allowed top-level files remain
    assert (tmp_path / "test.mp4").is_file()
    assert (tmp_path / "sync_report.txt").is_file()
    assert (tmp_path / "word_timings.json").is_file()
