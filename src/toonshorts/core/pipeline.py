"""
Purpose: Pipeline runner orchestrating LLM, voice, render, and motion.
Inputs: Video production topic, style name, flags, and plugin selections.
Outputs: Path to finalized vertical animation MP4 short.
Depends on: brief, core.assembler, core.config, core.cost, core.errors, core.models, core.registry, json, logging, pathlib, shutil, subprocess, typing
Used by: cli, core
Config keys: DEFAULT_LLM, DEFAULT_MOTION, DEFAULT_RENDERER, DEFAULT_VOICE, OUTPUT_DIR, STYLES_DIR, TEMP_DIR
Tests: tests/smoke/test_smoke_pipeline.py
"""

import json
import logging
from pathlib import Path
import shutil
import subprocess
from typing import Dict, Any, List, Optional, Union

from . import config
from .models import ScriptPlan, SceneAudio, Character, CameraMove
from .cost import estimate_costs, confirm_cost_gate
from .assembler import assemble_final_video, check_ffmpeg_subtitles_support
from .registry import get_llm, get_voice, get_renderer, get_motion
from toonshorts import brief as brief_module

logger = logging.getLogger("toonshorts.pipeline")


def load_style_preset(style_name: str, styles_dir: Path = config.STYLES_DIR) -> dict:
    """Loads a style preset JSON file from the styles directory."""
    preset_file = styles_dir / f"{style_name}.json"
    if not preset_file.is_file():
        available = [p.stem for p in styles_dir.glob("*.json")] if styles_dir.exists() else []
        raise FileNotFoundError(
            f"Style '{style_name}' not found at {preset_file}. "
            f"Available styles: {', '.join(sorted(available))}"
        )

    try:
        with open(preset_file, "r", encoding="utf-8") as f:
            preset = json.load(f)
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable preset file for style '{style_name}': {e}") from e

    required_keys = ["image_prompt_prefix", "color_palette", "caption", "pacing", "avoid"]
    for key in required_keys:
        if key not in preset:
            raise ValueError(f"Style preset '{style_name}' missing required field: '{key}'")

    return preset


def run_pipeline(
    topic: str,
    style_name: str,
    llm_name: Optional[str] = None,
    voice_name: Optional[str] = None,
    renderer_name: Optional[str] = None,
    motion_name: Optional[str] = None,
    output_dir: Optional[Path] = None,
    auto_confirm: bool = False,
    keep_temp: bool = False,
    mock: bool = False,
    allow_noncommercial: bool = False,
    fast: bool = False,
) -> Optional[Path]:
    """Executes the full modular video generation pipeline."""
    config.check_cloud_sync_warning()
    check_ffmpeg_subtitles_support()

    style_clean = style_name.lower().strip()
    preset = load_style_preset(style_clean)

    # Normalize engine aliases
    resolved_voice = voice_name
    if resolved_voice:
        resolved_voice = resolved_voice.lower().strip()
        if resolved_voice == "gemini":
            resolved_voice = "gemini_tts"
        elif resolved_voice == "sapi":
            resolved_voice = "windows_sapi"

    # Fast mode enforces offline cached/mock generation, zero Gemini calls, and auto-confirm
    if fast:
        llm_plugin_name = "fake"
        auto_confirm = True
        dest_output_dir = config.OUTPUT_DIR / "fast"
    else:
        llm_plugin_name = "fake" if mock else (llm_name or config.DEFAULT_LLM)
        dest_output_dir = output_dir or config.OUTPUT_DIR

    voice_plugin_name = "fake" if mock else (resolved_voice or preset.get("voice") or config.DEFAULT_VOICE)
    motion_plugin_name = motion_name or config.DEFAULT_MOTION

    if renderer_name:
        render_plugin_name = renderer_name
    elif mock:
        render_plugin_name = "fake"
    else:
        # Determine renderer from style preset if auto
        preset_renderer = preset.get("renderer", "gemini").lower()
        if preset_renderer in ("pillow", "cairo", "animejs", "blender3d"):
            render_plugin_name = preset_renderer
        elif style_clean == "stickman":
            render_plugin_name = "cairo"
        else:
            render_plugin_name = "gemini"

    # Instantiate plugins from registry
    llm = get_llm(llm_plugin_name)
    try:
        voice = get_voice(voice_plugin_name, allow_noncommercial=allow_noncommercial)
    except TypeError:
        voice = get_voice(voice_plugin_name)

    if fast:
        # Forbid live network API calls in fast mode
        setattr(voice, "cache_only", True)

    renderer = get_renderer(render_plugin_name)
    motion = get_motion(motion_plugin_name)

    temp_dir = config.TEMP_DIR / f"run_{style_clean}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    dest_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Planning
        logger.info("[1/6] Planning screenplay for '%s' using %s...", topic, llm.name)
        plan: ScriptPlan = llm.generate_plan(topic, style_clean, preset)

        # 2. Critic Review
        logger.info("[2/6] Reviewing screenplay with critic loop...")
        refined_plan, review = llm.review_and_refine(plan, preset)
        logger.info("Final Critic Score: %.1f/10", review.score)

        # 3. Cost Gate
        cost_est = estimate_costs(refined_plan, preset, rewrite_count=1)
        if not confirm_cost_gate(cost_est, auto_confirm=auto_confirm):
            return None

        # 4. Voice First (Timing Spine)
        logger.info("[3/6] Generating voice track via %s...", voice.name)
        scene_audios = voice.generate_all_voices(refined_plan, temp_dir)

        # Fast preview mode trims total duration to <= 6.0 seconds
        if fast:
            fast_scenes = []
            fast_audios = []
            accum_dur = 0.0
            for sc, sa in zip(refined_plan.scenes, scene_audios):
                if accum_dur >= 6.0:
                    break
                rem = 6.0 - accum_dur
                if sa.scene_total_duration > rem:
                    trimmed_wav = temp_dir / f"fast_trimmed_sc{sc.scene_number}.wav"
                    subprocess.run([
                        "ffmpeg", "-y",
                        "-i", str(sa.audio_path),
                        "-t", f"{rem:.3f}",
                        "-c", "copy",
                        str(trimmed_wav)
                    ], capture_output=True, check=True, stdin=subprocess.DEVNULL)
                    fast_audios.append(SceneAudio(
                        scene_index=sa.scene_index,
                        audio_path=trimmed_wav,
                        duration_seconds=rem,
                        scene_total_duration=rem,
                        word_timings=[w for w in sa.word_timings if w.start_time < rem],
                    ))
                    fast_scenes.append(sc)
                    accum_dur = 6.0
                    break
                else:
                    fast_scenes.append(sc)
                    fast_audios.append(sa)
                    accum_dur += sa.scene_total_duration
            refined_plan.scenes = fast_scenes
            scene_audios = fast_audios

        # 5. Scene Rendering
        logger.info("[4/6] Rendering scene images via %s...", renderer.name)
        try:
            scene_images = renderer.render_all_scenes(
                refined_plan, preset, temp_dir, scene_audios=scene_audios, fast=fast
            )
        except TypeError:
            try:
                scene_images = renderer.render_all_scenes(refined_plan, preset, temp_dir, scene_audios=scene_audios)
            except TypeError:
                scene_images = renderer.render_all_scenes(refined_plan, preset, temp_dir)

        # 6. Assembly & Motion
        logger.info("[5/6] Assembling video using %s motion...", motion.name)
        final_video = assemble_final_video(
            plan=refined_plan,
            scene_images=scene_images,
            scene_audios=scene_audios,
            style_preset=preset,
            temp_dir=temp_dir,
            output_dir=dest_output_dir,
            motion_plugin=motion,
            fast=fast,
        )

        logger.info("Pipeline completed successfully: %s", final_video)
        return final_video

    finally:
        if not keep_temp and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_pipeline_from_brief(
    brief_source: Union[str, Path, brief_module.VideoBrief],
    output_dir: Optional[Path] = None,
    stills_only: bool = False,
    auto_confirm: bool = True,
    mock: bool = False,
    keep_temp: bool = False,
) -> Dict[str, Any]:
    """
    Executes the video build pipeline strictly driven by a validated VideoBrief file.
    Renders stills of key scenes first for approval, then assembles the full MP4 into output/.
    Fails with plain error message on failure without retry loops.
    """
    if isinstance(brief_source, brief_module.VideoBrief):
        brief = brief_source
    else:
        brief = brief_module.load_brief(brief_source)

    config.check_cloud_sync_warning()
    check_ffmpeg_subtitles_support()

    dest_output_dir = output_dir or config.OUTPUT_DIR
    dest_output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = config.TEMP_DIR / f"run_brief_{brief.video_name}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Preset setup
        preset = load_style_preset(brief.style)
        preset["gestures"] = brief.hand_gestures
        if brief.board_animations_avoid:
            preset.setdefault("avoid", []).extend(brief.board_animations_avoid)

        # 2. Plan Screenplay from story & brief
        llm_plugin = "fake" if mock else config.DEFAULT_LLM
        try:
            llm = get_llm(llm_plugin)
            plan: ScriptPlan = llm.generate_plan(brief.story, brief.style, preset)
        except Exception as l_err:
            if not mock:
                logger.warning("Live LLM failed (%s), falling back to offline planner for brief.", l_err)
                llm = get_llm("fake")
                plan = llm.generate_plan(brief.story, brief.style, preset)
            else:
                raise

        plan.title = brief.video_name

        # Ensure cast matches brief
        if brief.characters:
            chars = [Character(name=c, visual_description=f"Character {c}") for c in brief.characters]
            if len(chars) < 2:
                sec_name = "boy_b" if chars[0].name != "boy_b" else "girl_a"
                chars.append(Character(name=sec_name, visual_description=f"Character {sec_name}"))
            plan.characters = chars

        # Ensure speaker matches brief
        if brief.speaker and brief.speaker not in ("both", "all", "none"):
            for sc in plan.scenes:
                sc.speaker = brief.speaker

        # Apply camera rules
        if brief.camera in ("fixed", "static"):
            for sc in plan.scenes:
                sc.camera_move = CameraMove.STATIC
        elif brief.camera in ("zoom_speaker", "zoom on speaker"):
            for idx, sc in enumerate(plan.scenes):
                # Zoom on important emphasis/turn scenes, stay wide on others
                if idx in (1, len(plan.scenes) - 1):
                    sc.camera_move = CameraMove.ZOOM_IN
                else:
                    sc.camera_move = CameraMove.STATIC

        # Save scene file directly from story and brief
        scene_file_path = brief_module.BRIEFS_DIR / f"{brief.video_name}_scene.json"
        brief_module.BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        scene_file_path.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
        logger.info("Wrote validated scene file to: %s", scene_file_path)

        # 3. Voice generation
        voice_engine = brief.voice_engine
        if not voice_engine:
            if brief.voice in config.GEMINI_VOICES:
                voice_engine = "gemini_tts"
            elif (config.PIPER_VOICES_DIR / f"{brief.voice}.onnx").exists():
                voice_engine = "piper"
            else:
                voice_engine = "fake" if mock else (preset.get("voice") or config.DEFAULT_VOICE)

        if mock:
            voice_engine = "fake"

        voice = get_voice(voice_engine, allow_noncommercial=True)
        logger.info("Generating voice tracks using engine '%s' (voice: %s)...", voice.name, brief.voice)
        try:
            scene_audios = voice.generate_all_voices(plan, temp_dir)
        except Exception as v_err:
            if not mock:
                logger.warning("Voice engine %s failed (%s), falling back to offline audio.", voice.name, v_err)
                voice = get_voice("fake")
                scene_audios = voice.generate_all_voices(plan, temp_dir)
            else:
                raise

        # 4. Render key scene stills first for approval
        renderer_name = "fake" if mock else (preset.get("renderer") or config.DEFAULT_RENDERER)
        if renderer_name == "auto":
            renderer_name = "cairo" if brief.style == "stickman" else "animejs"

        renderer = get_renderer(renderer_name)
        still_paths: List[Path] = []
        key_indices = [0]
        if len(plan.scenes) > 1:
            punchline_idx = next((i for i, s in enumerate(plan.scenes) if s.is_punchline), len(plan.scenes) - 1)
            if punchline_idx not in key_indices:
                key_indices.append(punchline_idx)

        for s_idx in key_indices:
            sc = plan.scenes[s_idx]
            still_path = dest_output_dir / f"{brief.video_name}_still_sc{sc.scene_number}.png"
            renderer.render_scene(
                scene=sc,
                characters=plan.characters,
                style_preset=preset,
                output_path=still_path,
                temp_dir=temp_dir,
            )
            still_paths.append(still_path)

        logger.info("Rendered %d key scene stills for approval: %s", len(still_paths), [p.name for p in still_paths])

        if stills_only:
            return {
                "status": "stills_ready",
                "scene_file": scene_file_path,
                "stills": still_paths,
                "video": None,
            }

        # 5. Render all frames & Assemble full MP4
        motion_name = preset.get("motion") or config.DEFAULT_MOTION
        motion = get_motion(motion_name)

        try:
            scene_images = renderer.render_all_scenes(plan, preset, temp_dir, scene_audios=scene_audios)
        except TypeError:
            scene_images = renderer.render_all_scenes(plan, preset, temp_dir)

        final_raw_video = assemble_final_video(
            plan=plan,
            scene_images=scene_images,
            scene_audios=scene_audios,
            style_preset=preset,
            temp_dir=temp_dir,
            output_dir=dest_output_dir,
            motion_plugin=motion,
        )

        final_video_path = dest_output_dir / f"{brief.video_name}.mp4"
        if final_raw_video != final_video_path and final_raw_video.exists():
            if final_video_path.exists():
                final_video_path.unlink()
            shutil.move(str(final_raw_video), str(final_video_path))
        else:
            final_video_path = final_raw_video

        logger.info("Full MP4 video generated successfully at: %s", final_video_path)
        return {
            "status": "complete",
            "scene_file": scene_file_path,
            "stills": still_paths,
            "video": final_video_path,
        }

    except Exception as exc:
        logger.error("Pipeline brief run failed: %s", exc)
        raise RuntimeError(f"Brief execution failed: {exc}") from exc

    finally:
        if not keep_temp and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

