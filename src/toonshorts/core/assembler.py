"""
Purpose: FFmpeg video assembly, startup capability verification, and ASS subtitles.
Inputs: Script plan, image paths, audio clips, and motion provider.
Outputs: Rendered vertical MP4 video file path.
Depends on: core.audio_effects, core.config, core.models, core.subtitles, logging, pathlib, shutil, subprocess, typing
Used by: core.pipeline
Config keys: VIDEO_FPS
Tests: tests/smoke/test_smoke_pipeline.py, tests/unit/test_ffmpeg_check.py
"""

import subprocess
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import ScriptPlan, SceneAudio, sanitize_video_name
from .subtitles import generate_ass_subtitles
from .audio_effects import prepare_sound_effects
from . import config

logger = logging.getLogger("toonshorts.assembler")


def escape_ffmpeg_subtitles_path(path: Any) -> str:
    """Escapes a subtitle file path for FFmpeg's subtitles/libass filter.

    Handles Windows drive-letter colon, backslashes, spaces, and single quotes:
    - Normalizes backslashes to forward slashes.
    - Escapes colons with backslash (e.g. C: -> C\\:).
    - Escapes single quotes (e.g. ' -> \\').
    - Encloses path in single quotes so spaces and special characters are preserved.
    """
    p = str(path).replace("\\", "/")
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")
    return f"'{p}'"


def check_ffmpeg_subtitles_support() -> bool:
    """Verifies that FFmpeg is installed and has the subtitles/ass filter enabled.

    Raises:
        RuntimeError: If FFmpeg is missing or does not support subtitles/ass filter,
                      with platform-specific installation instructions.
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    install_instructions = (
        "Install FFmpeg with libass/subtitles support:\n"
        "  - On Windows: choco install ffmpeg-full  OR  winget install Gyan.FFmpeg\n"
        "  - On macOS: brew install ffmpeg\n"
        "  - On Linux: sudo apt update && sudo apt install ffmpeg libass-dev"
    )
    if not ffmpeg_bin:
        raise RuntimeError(
            f"FFmpeg is not installed or not found on PATH. FFmpeg with subtitles/ass filter is required.\n"
            f"{install_instructions}"
        )

    try:
        res = subprocess.run([ffmpeg_bin, "-filters"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    except Exception as e:
        raise RuntimeError(f"Failed to execute FFmpeg to check filters: {e}\n{install_instructions}") from e

    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed while checking filters:\n{res.stderr}\n{install_instructions}")

    lines = res.stdout.splitlines()
    has_subtitles = any(
        ("subtitles" in line and "Render text subtitles" in line)
        or line.strip().startswith(".. subtitles")
        or " subtitles " in line
        or ("ass" in line and "Render ASS subtitles" in line)
        or line.strip().startswith(".. ass")
        or " ass " in line
        for line in lines
    )
    if not has_subtitles:
        raise RuntimeError(
            "FFmpeg exists but does not support the 'subtitles' or 'ass' filter. "
            "ToonShorts requires FFmpeg built with libass/subtitles support to ensure videos have captions.\n"
            f"{install_instructions}"
        )
    return True


def assemble_final_video(
    plan: ScriptPlan,
    scene_images: List[Path],
    scene_audios: List[SceneAudio],
    style_preset: Dict[str, Any],
    temp_dir: Path,
    output_dir: Path,
    motion_plugin: Optional[Any] = None,
    fast: bool = False,
    video_name: Optional[str] = None,
    library_tracker: Optional[List[str]] = None,
) -> Path:
    """Renders scenes, burns in ASS subtitles, and outputs finished vertical MP4."""
    check_ffmpeg_subtitles_support()
    temp_dir.mkdir(parents=True, exist_ok=True)
    if output_dir == config.OUTPUT_DIR and fast:
        output_dir = config.OUTPUT_DIR / "fast"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = sanitize_video_name(video_name or plan.title)
    final_output_path = output_dir / f"{safe_title}.mp4"

    target_fps = 15 if fast else config.VIDEO_FPS
    target_width = 540 if fast else config.VIDEO_WIDTH
    target_height = 960 if fast else config.VIDEO_HEIGHT

    # 1. Prepare sound effects
    sfx_map = prepare_sound_effects(temp_dir, library_tracker=library_tracker)
    default_sfx = style_preset.get("default_sound_effects", ["pop", "boing"])

    # 2. Render each scene into an intermediate MP4 clip with camera motion and audio
    scene_clips: List[Path] = []
    for i, (scene, img_path, audio) in enumerate(zip(plan.scenes, scene_images, scene_audios)):
        clip_path = temp_dir / f"clip_{i}.mp4"

        # Check if scene was directly rendered as an animated video clip
        if img_path.suffix.lower() == ".mp4":
            if fast:
                scaled_clip = temp_dir / f"fast_scaled_clip_{i}.mp4"
                scale_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(img_path),
                    "-vf", f"scale={target_width}:{target_height}",
                    "-r", str(target_fps),
                    "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "copy",
                    str(scaled_clip)
                ]
                subprocess.run(scale_cmd, capture_output=True, check=True, stdin=subprocess.DEVNULL)
                img_path = scaled_clip

            has_punchline = scene.is_punchline
            if has_punchline and default_sfx:
                chosen_sfx = sfx_map.get(default_sfx[0], sfx_map.get("boing"))
                if chosen_sfx and chosen_sfx.is_file():
                    mixed_clip = temp_dir / f"mixed_clip_{i}.mp4"
                    mix_cmd = [
                        "ffmpeg", "-y",
                        "-i", str(img_path),
                        "-i", str(chosen_sfx),
                        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[a]",
                        "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac",
                        str(mixed_clip)
                    ]
                    try:
                        subprocess.run(mix_cmd, capture_output=True, check=True, stdin=subprocess.DEVNULL)
                        clip_path = mixed_clip
                    except Exception as e:
                        logger.warning("SFX mix failed for video clip (%s); using original clip.", e)
                        clip_path = img_path
                else:
                    clip_path = img_path
            else:
                clip_path = img_path
            scene_clips.append(clip_path)
            continue

        if motion_plugin and hasattr(motion_plugin, "get_filter_chain") and not fast:
            motion_filter = motion_plugin.get_filter_chain(scene.camera_move, audio.scene_total_duration)
        else:
            motion_filter = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"

        # Mix punchline sfx if flagged
        has_punchline = scene.is_punchline
        audio_input = audio.audio_path
        if has_punchline and default_sfx:
            chosen_sfx = sfx_map.get(default_sfx[0], sfx_map.get("boing"))
            if chosen_sfx and chosen_sfx.is_file():
                mixed_audio = temp_dir / f"mixed_scene_{i}.wav"
                mix_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(audio.audio_path),
                    "-i", str(chosen_sfx),
                    "-filter_complex", "amix=inputs=2:duration=first:dropout_transition=2",
                    "-ac", "2",
                    str(mixed_audio)
                ]
                try:
                    subprocess.run(mix_cmd, capture_output=True, check=True, stdin=subprocess.DEVNULL)
                    audio_input = mixed_audio
                except Exception as e:
                    logger.warning("SFX mix failed (%s); using original voice audio.", e)

        scene_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img_path),
            "-i", str(audio_input),
            "-t", f"{audio.scene_total_duration:.2f}",
            "-vf", motion_filter,
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2",
            "-r", str(target_fps),
            str(clip_path)
        ]

        logger.info("Rendering Scene %d video clip (motion: %s)...", i + 1, scene.camera_move.value)
        res = subprocess.run(scene_cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg scene render failed for Scene {i+1}:\n{res.stderr}")
        scene_clips.append(clip_path)

    # 3. Concatenate scene clips
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.resolve().as_posix()}'\n")

    unsubbed_video = temp_dir / "unsubbed_full.mp4"
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "concat_list.txt",
        "-c", "copy",
        str(unsubbed_video.name)
    ]
    logger.info("Concatenating all scenes into unified video stream...")
    res = subprocess.run(concat_cmd, cwd=temp_dir, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg concat failed:\n{res.stderr}")

    # 4. Generate ASS subtitles
    ass_path = temp_dir / "captions.ass"
    generate_ass_subtitles(plan, scene_audios, style_preset, ass_path)
    if output_dir != temp_dir:
        try:
            shutil.copyfile(str(ass_path), str(output_dir / "captions.ass"))
        except Exception:
            pass

    # 5. Burn in subtitles using properly escaped path
    escaped_ass = escape_ffmpeg_subtitles_path(ass_path.resolve())
    final_burn_cmd = [
        "ffmpeg", "-y",
        "-i", str(unsubbed_video.name),
        "-vf", f"subtitles={escaped_ass}",
        "-c:v", "libx264", "-preset", "ultrafast" if fast else "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-r", str(target_fps),
    ]
    final_burn_cmd.append(str(final_output_path.resolve()))

    logger.info("Burning in ASS word-level captions to final video...")
    res = subprocess.run(final_burn_cmd, cwd=temp_dir, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        raise RuntimeError(
            f"Subtitle burn-in failed (never output a video without captions):\n{res.stderr}"
        )

    logger.info("Successfully assembled video: %s", final_output_path)
    return final_output_path
