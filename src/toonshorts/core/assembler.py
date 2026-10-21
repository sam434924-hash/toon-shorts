"""
Purpose: FFmpeg video assembly using argument lists and ASS subtitles.
Inputs: Script plan, image paths, audio clips, and motion provider.
Outputs: Rendered vertical MP4 video file path.
Depends on: core.audio_effects, core.config, core.models, core.subtitles, logging, pathlib, shutil, subprocess, typing
Used by: core.pipeline
Config keys: VIDEO_FPS
Tests: tests/smoke/test_smoke_pipeline.py
"""

import subprocess
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import ScriptPlan, SceneAudio, sanitize_filename
from .subtitles import generate_ass_subtitles
from .audio_effects import prepare_sound_effects
from . import config

logger = logging.getLogger("toonshorts.assembler")


def assemble_final_video(
    plan: ScriptPlan,
    scene_images: List[Path],
    scene_audios: List[SceneAudio],
    style_preset: Dict[str, Any],
    temp_dir: Path,
    output_dir: Path,
    motion_plugin: Optional[Any] = None,
) -> Path:
    """Renders scenes, burns in ASS subtitles, and outputs finished vertical MP4."""
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = sanitize_filename(plan.title)
    final_output_path = output_dir / f"{safe_title}.mp4"

    # 1. Prepare sound effects
    sfx_map = prepare_sound_effects(temp_dir)
    default_sfx = style_preset.get("default_sound_effects", ["pop", "boing"])

    # 2. Render each scene into an intermediate MP4 clip with camera motion and audio
    scene_clips: List[Path] = []
    for i, (scene, img_path, audio) in enumerate(zip(plan.scenes, scene_images, scene_audios)):
        clip_path = temp_dir / f"clip_{i}.mp4"
        if motion_plugin and hasattr(motion_plugin, "get_filter_chain"):
            motion_filter = motion_plugin.get_filter_chain(scene.camera_move, audio.scene_total_duration)
        else:
            motion_filter = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"

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
                    subprocess.run(mix_cmd, capture_output=True, check=True)
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
            "-r", str(config.VIDEO_FPS),
            str(clip_path)
        ]

        logger.info("Rendering Scene %d video clip (motion: %s)...", i + 1, scene.camera_move.value)
        res = subprocess.run(scene_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg scene render failed for Scene {i+1}:\n{res.stderr}")
        scene_clips.append(clip_path)

    # 3. Concatenate scene clips
    concat_list_file = temp_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.name}'\n")

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
    res = subprocess.run(concat_cmd, cwd=temp_dir, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg concat failed:\n{res.stderr}")

    # 4. Generate ASS subtitles
    ass_path = temp_dir / "captions.ass"
    generate_ass_subtitles(plan, scene_audios, style_preset, ass_path)

    # 5. Burn in subtitles using relative filename inside temp_dir
    final_burn_cmd = [
        "ffmpeg", "-y",
        "-i", str(unsubbed_video.name),
        "-vf", f"subtitles={ass_path.name}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(final_output_path.resolve())
    ]
    logger.info("Burning in ASS word-level captions to final video...")
    res = subprocess.run(final_burn_cmd, cwd=temp_dir, capture_output=True, text=True)
    if res.returncode != 0:
        logger.warning("Subtitle burn-in returned non-zero code:\n%s. Copying unsubbed video.", res.stderr)
        shutil.copy2(unsubbed_video, final_output_path)

    logger.info("Successfully assembled video: %s", final_output_path)
    return final_output_path
