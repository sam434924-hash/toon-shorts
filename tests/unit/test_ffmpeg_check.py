"""Tests for FFmpeg availability and subtitles filter support verification."""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from toonshorts.core.assembler import check_ffmpeg_subtitles_support, assemble_final_video
from toonshorts.core.models import ScriptPlan, Scene, Character, SceneAudio, CameraMove


def test_ffmpeg_check_real_host():
    """Verifies that the host environment has FFmpeg with subtitles filter enabled."""
    assert check_ffmpeg_subtitles_support() is True


def test_ffmpeg_missing_raises_error():
    """Verifies a clear error is raised if FFmpeg is not installed or not in PATH."""
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="FFmpeg is not installed or not found on PATH"):
            check_ffmpeg_subtitles_support()


def test_ffmpeg_missing_subtitles_filter_raises_error():
    """Verifies a clear error is raised if FFmpeg exists but lacks the subtitles filter."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = " .. scale      V->V       Scale the input video.\n .. crop       V->V       Crop the input video.\n"
    mock_res.stderr = ""

    with patch("shutil.which", return_value="C:\\ffmpeg\\bin\\ffmpeg.exe"):
        with patch("subprocess.run", return_value=mock_res):
            with pytest.raises(RuntimeError, match="does not support the 'subtitles' filter"):
                check_ffmpeg_subtitles_support()


def test_ffmpeg_filters_command_failure_raises_error():
    """Verifies error is raised if running ffmpeg -filters fails."""
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = "unknown error"

    with patch("shutil.which", return_value="C:\\ffmpeg\\bin\\ffmpeg.exe"):
        with patch("subprocess.run", return_value=mock_res):
            with pytest.raises(RuntimeError, match="FFmpeg failed while checking filters"):
                check_ffmpeg_subtitles_support()


def test_assemble_never_outputs_without_captions(tmp_path):
    """Verifies assemble_final_video fails if subtitle burn-in fails, never outputting unsubbed video."""
    characters = [
        Character(name="Pip", visual_description="Stickman with red glasses"),
        Character(name="Zack", visual_description="Stickman with blue hat"),
    ]
    scenes = [
        Scene(scene_number=1, speaker="Pip", dialogue_line="Hello", action="waves", camera_move=CameraMove.STATIC),
        Scene(scene_number=2, speaker="Zack", dialogue_line="Hi there", action="jumps", camera_move=CameraMove.STATIC),
        Scene(scene_number=3, speaker="Pip", dialogue_line="Funny joke", action="laughs", camera_move=CameraMove.STATIC),
        Scene(scene_number=4, speaker="Zack", dialogue_line="Punchline!", action="shocked", camera_move=CameraMove.STATIC, is_punchline=True),
    ]
    plan = ScriptPlan(
        title="Test Story",
        art_style="stickman",
        emotional_arc="Curiosity to realization",
        characters=characters,
        scenes=scenes,
    )
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake_image_bytes")
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake_audio_bytes")
    scene_audios = [
        SceneAudio(
            scene_index=i,
            audio_path=audio_path,
            duration_seconds=2.0,
            scene_total_duration=2.0,
            word_timings=[],
        )
        for i in range(4)
    ]
    scene_images = [img_path for _ in range(4)]

    # Mock subprocess.run to succeed for scene render and concat, but fail for burn-in
    def fake_run(cmd, *args, **kwargs):
        res = MagicMock()
        if any("subtitles=" in str(arg) for arg in cmd):
            res.returncode = 1
            res.stderr = "Error initializing filter 'subtitles'"
        else:
            res.returncode = 0
            res.stdout = ""
            res.stderr = ""
        return res

    with patch("toonshorts.core.assembler.check_ffmpeg_subtitles_support", return_value=True):
        with patch("toonshorts.core.assembler.prepare_sound_effects", return_value={}):
            with patch("subprocess.run", side_effect=fake_run):
                with pytest.raises(RuntimeError, match="Subtitle burn-in failed"):
                    assemble_final_video(
                        plan=plan,
                        scene_images=scene_images,
                        scene_audios=scene_audios,
                        style_preset={"caption": {"font": "Arial", "font_size": 18, "primary_color": "&H00FFFFFF&"}},
                        temp_dir=tmp_path / "temp",
                        output_dir=tmp_path / "output",
                    )
