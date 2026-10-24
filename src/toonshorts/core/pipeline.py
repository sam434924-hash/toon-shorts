"""
Purpose: Pipeline runner orchestrating LLM, voice, render, and motion into self-contained video bundles.
Inputs: Video production topic, style name, flags, and plugin selections.
Outputs: Path to finalized vertical animation MP4 short inside dedicated video directory.
Depends on: brief, core.assembler, core.camera, core.config, core.cost, core.errors, core.images, core.layout_checker, core.library, core.models, core.paths, core.registry, core.validator, core.visual_checker, json, logging, pathlib, platform, shutil, subprocess, sys, time, typing, uuid
Used by: cli, core
Config keys: DEFAULT_LLM, DEFAULT_MOTION, DEFAULT_RENDERER, DEFAULT_VOICE, STYLES_DIR, VIDEOS_DIR
Tests: tests/smoke/test_smoke_pipeline.py, tests/unit/test_video_folders.py
"""

import json
import logging
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional, Union
import uuid

from . import config, paths
from .camera import validate_camera_config
from .errors import PipelineError
from .models import (
    ScriptPlan,
    SceneAudio,
    Character,
    CameraMove,
    sanitize_video_name,
    resolve_video_dir,
    CharacterManifestItem,
    VoiceManifestItem,
    VideoManifest,
)
from .cost import estimate_costs, confirm_cost_gate
from .assembler import assemble_final_video, check_ffmpeg_subtitles_support
from .registry import get_llm, get_voice, get_renderer, get_motion
from .library import copy_library_asset, clean_temp_builds
from .sync import enforce_and_prepare_word_timings, generate_sync_report, tidy_video_folder
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

    if "camera" in preset:
        preset["camera"] = validate_camera_config(preset["camera"])

    return preset


def generate_manifest(
    video_name: str,
    style: str,
    plan: ScriptPlan,
    voice_plugin: Any,
    brief: Optional[Any] = None,
    library_pieces_used: Optional[List[str]] = None,
    tools_used: Optional[List[Any]] = None,
    renderer_name: Optional[str] = None,
) -> VideoManifest:
    """Builds a structured manifest recording character packs, voice model, tools, and library assets."""
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    characters = []
    for c in plan.characters:
        characters.append(
            CharacterManifestItem(
                name=c.name,
                pack=c.name,
                version="1.0.0",
            )
        )

    voice_name = getattr(brief, "voice", None) or getattr(voice_plugin, "name", "unknown")
    voice_model = getattr(voice_plugin, "model_name", None)
    voice_info = VoiceManifestItem(
        engine=getattr(voice_plugin, "name", "unknown"),
        voice_name=voice_name,
        model=voice_model,
    )

    tool_versions = {
        "python": platform.python_version(),
        "ffmpeg": "installed",
        "toonshorts": "1.0.0",
    }

    unique_pieces = sorted(list(set(library_pieces_used or [])))

    level2_visuals = []
    custom_visuals_list = []
    if plan and getattr(plan, "scenes", None):
        for sc in plan.scenes:
            for bo in getattr(sc, "board_objects", []) or []:
                if isinstance(bo, dict) and bo.get("type") == "custom":
                    data = bo.get("data", {})
                    lvl = data.get("level", 1) if isinstance(data, dict) else 1
                    custom_visuals_list.append({
                        "scene": sc.scene_number,
                        "id": bo.get("id"),
                        "level": lvl,
                        "effect": data.get("level2_effect_name", "custom_svg") if lvl == 2 else "custom_svg",
                    })
                    if lvl == 2:
                        level2_visuals.append({
                            "scene": sc.scene_number,
                            "id": bo.get("id"),
                            "effect": data.get("level2_effect_name", "custom_js"),
                        })
            for vis in getattr(sc, "visuals", []) or []:
                v_type = getattr(vis, "type", None) or (vis.get("type") if isinstance(vis, dict) else None)
                v_params = getattr(vis, "params", None) or (vis.get("params") if isinstance(vis, dict) else {})
                if v_type == "custom":
                    lvl = v_params.get("level", 1) if isinstance(v_params, dict) else 1
                    custom_visuals_list.append({
                        "scene": sc.scene_number,
                        "id": getattr(vis, "id", f"vis_{sc.scene_number}"),
                        "level": lvl,
                        "effect": v_params.get("level2_effect_name", "custom_svg") if lvl == 2 else "custom_svg",
                    })
                    if lvl == 2:
                        level2_visuals.append({
                            "scene": sc.scene_number,
                            "id": getattr(vis, "id", f"vis_{sc.scene_number}"),
                            "effect": v_params.get("level2_effect_name", "custom_js"),
                        })

    # Assemble tools_used: (skills, image generation, library hits, custom visuals)
    tools_used_list: List[Dict[str, Any]] = list(tools_used or [])

    # 1. Skills
    for sk in ["toon-shorts-directing", "animejs-animation", "toon-shorts-visual-check", "toon-shorts-style"]:
        if not any(isinstance(x, dict) and x.get("category") == "skills" and x.get("name") == sk for x in tools_used_list):
            tools_used_list.append({"category": "skills", "name": sk})

    # 2. Image generation
    r_name = renderer_name or getattr(brief, "renderer", None) or "animejs"
    if r_name in {"gemini", "pillow"}:
        if not any(isinstance(x, dict) and x.get("category") == "image generation" for x in tools_used_list):
            tools_used_list.append({"category": "image generation", "name": r_name})

    # 3. Library hits
    for piece in unique_pieces:
        if not any(isinstance(x, dict) and x.get("category") == "library hits" and x.get("name") == piece for x in tools_used_list):
            tools_used_list.append({"category": "library hits", "name": piece})

    # 4. Custom visuals
    for cv in custom_visuals_list:
        tools_used_list.append({
            "category": "custom visuals",
            "scene": cv["scene"],
            "id": cv["id"],
            "level": cv["level"],
            "effect": cv["effect"],
        })

    return VideoManifest(
        video_name=video_name,
        created_at=created_at,
        style=style,
        characters=characters,
        voice=voice_info,
        library_pieces_used=unique_pieces,
        tool_versions=tool_versions,
        level2_custom_visuals=level2_visuals,
        tools_used=tools_used_list,
    )


def register_plan_custom_elements(plan: ScriptPlan, style: str, library_tracker: List[str]) -> None:
    """Registers any custom visual elements and images from the screenplay into library/elements/."""
    from toonshorts.core.library import (
        compute_element_key,
        resolve_theme_tags,
        save_element_once,
    )
    from toonshorts.core.images import (
        compute_image_key,
        find_image_in_library,
        save_image_to_library,
    )
    theme_tags = resolve_theme_tags(style)
    if not plan or not getattr(plan, "scenes", None):
        return

    for sc in plan.scenes:
        for bo in getattr(sc, "board_objects", []) or []:
            if isinstance(bo, dict):
                b_type = bo.get("type")
                if b_type == "custom":
                    bo_data = bo.get("data") or {}
                    key = compute_element_key(
                        element_type="custom",
                        content=bo_data,
                        theme_tags=theme_tags,
                        source="code",
                        animated=True,
                    )
                    elem_path, is_hit = save_element_once(
                        element_type="custom",
                        key=key,
                        file_name=f"custom_{key[:16]}.json",
                        content=bo_data,
                        theme_tags=theme_tags,
                        animated=True,
                        source="code",
                    )
                    library_tracker.append(f"library/elements/custom/{elem_path.name}")
                elif b_type == "image":
                    bo_data = bo.get("data") or {}
                    prompt = bo_data.get("prompt") or bo.get("prompt") or ""
                    img_path_str = bo_data.get("image_url") or bo_data.get("src") or bo_data.get("path") or ""
                    if prompt:
                        key = compute_image_key(prompt, style)
                        hit = find_image_in_library(key)
                        if hit:
                            fpath = paths.LIBRARY_ELEMENTS_DIR / "images" / hit.get("file_name", "")
                            bo_data["image_url"] = str(fpath)
                            library_tracker.append(f"library/elements/images/{fpath.name}")
                        elif img_path_str and Path(img_path_str).is_file():
                            from PIL import Image as PILImage
                            with PILImage.open(img_path_str) as p_img:
                                saved_path, is_hit = save_image_to_library(
                                    p_img,
                                    prompt=prompt,
                                    style=style,
                                    source="generated",
                                )
                                bo_data["image_url"] = str(saved_path)
                                library_tracker.append(f"library/elements/images/{saved_path.name}")
                    elif img_path_str:
                        library_tracker.append(f"library/elements/images/{Path(img_path_str).name}")

        for vis in getattr(sc, "visuals", []) or []:
            v_type = getattr(vis, "type", None) or (vis.get("type") if isinstance(vis, dict) else None)
            if v_type == "custom":
                v_params = getattr(vis, "params", None) or (vis.get("params") if isinstance(vis, dict) else {})
                key = compute_element_key(
                    element_type="custom",
                    content=v_params,
                    theme_tags=theme_tags,
                    source="code",
                    animated=True,
                )
                elem_path, is_hit = save_element_once(
                    element_type="custom",
                    key=key,
                    file_name=f"custom_{key[:16]}.json",
                    content=v_params,
                    theme_tags=theme_tags,
                    animated=True,
                    source="code",
                )
                library_tracker.append(f"library/elements/custom/{elem_path.name}")
            elif v_type == "image":
                v_params = getattr(vis, "params", None) or (vis.get("params") if isinstance(vis, dict) else {})
                prompt = v_params.get("prompt") or ""
                img_path_str = v_params.get("image_url") or v_params.get("src") or v_params.get("path") or ""
                if prompt:
                    key = compute_image_key(prompt, style)
                    hit = find_image_in_library(key)
                    if hit:
                        fpath = paths.LIBRARY_ELEMENTS_DIR / "images" / hit.get("file_name", "")
                        v_params["image_url"] = str(fpath)
                        library_tracker.append(f"library/elements/images/{fpath.name}")
                    elif img_path_str and Path(img_path_str).is_file():
                        from PIL import Image as PILImage
                        with PILImage.open(img_path_str) as p_img:
                            saved_path, is_hit = save_image_to_library(
                                p_img,
                                prompt=prompt,
                                style=style,
                                source="generated",
                            )
                            v_params["image_url"] = str(saved_path)
                            library_tracker.append(f"library/elements/images/{saved_path.name}")
                elif img_path_str:
                    library_tracker.append(f"library/elements/images/{Path(img_path_str).name}")


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
    workers: Optional[int] = None,
    overwrite: bool = False,
    allow_fallback: bool = False,
    allow_low_score: bool = False,
) -> Optional[Path]:
    """Executes video generation pipeline into a single self-contained video folder."""
    config.check_cloud_sync_warning()
    check_ffmpeg_subtitles_support()

    style_clean = style_name.lower().strip()
    preset = load_style_preset(style_clean)

    if renderer_name:
        render_plugin_name = renderer_name
    elif mock:
        render_plugin_name = "fake"
    else:
        preset_renderer = preset.get("renderer", "gemini").lower()
        if preset_renderer in ("pillow", "cairo", "animejs", "blender3d"):
            render_plugin_name = preset_renderer
        elif style_clean == "stickman":
            render_plugin_name = "cairo"
        else:
            render_plugin_name = "gemini"

    renderer = get_renderer(render_plugin_name)
    if fast and not getattr(renderer, "supports_fast", False):
        raise PipelineError(
            f"Renderer '{renderer.name}' does not support fast draft mode (--fast)."
        )

    # 1. Video name resolution and security checks
    video_name = sanitize_video_name(topic)
    base_videos_dir = output_dir or paths.VIDEOS_DIR
    target_video_dir = resolve_video_dir(video_name, base_dir=base_videos_dir)

    # Exists-guard: stop and fail if directory already exists unless --overwrite
    if target_video_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Video directory '{target_video_dir}' already exists. Choose a different name or use --overwrite."
            )
        logger.warning("Overwriting existing video directory: %s", target_video_dir)

    # Clean failure build folder: build in .tmp-<name>-<id>
    build_id = uuid.uuid4().hex[:8]
    build_dir = base_videos_dir / f".tmp-{video_name}-{build_id}"
    build_dir.mkdir(parents=True, exist_ok=True)
    voice_dir = build_dir / "voice"
    stills_dir = build_dir / "stills"
    visuals_dir = build_dir / "visuals"
    voice_dir.mkdir(exist_ok=True)
    stills_dir.mkdir(exist_ok=True)
    visuals_dir.mkdir(exist_ok=True)

    # Set up dedicated run.log inside video folder
    log_file = build_dir / "run.log"
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s", datefmt="%H:%M:%S")
    )
    toon_logger = logging.getLogger("toonshorts")
    toon_logger.addHandler(file_handler)

    library_pieces_used: List[str] = []
    build_succeeded = False

    try:
        # Normalize engine aliases
        resolved_voice = voice_name
        if resolved_voice:
            resolved_voice = resolved_voice.lower().strip()
            if resolved_voice == "gemini":
                resolved_voice = "gemini_tts"
            elif resolved_voice == "sapi":
                resolved_voice = "windows_sapi"

        if fast:
            llm_plugin_name = "fake"
            auto_confirm = True
        else:
            llm_plugin_name = "fake" if mock else (llm_name or config.DEFAULT_LLM)

        voice_plugin_name = "fake" if mock else (resolved_voice or preset.get("voice") or config.DEFAULT_VOICE)
        motion_plugin_name = motion_name or config.DEFAULT_MOTION

        llm = get_llm(llm_plugin_name)
        try:
            voice = get_voice(voice_plugin_name, allow_noncommercial=allow_noncommercial)
        except TypeError:
            voice = get_voice(voice_plugin_name)

        if fast:
            setattr(voice, "cache_only", True)

        renderer = get_renderer(render_plugin_name)
        motion = get_motion(motion_plugin_name)

        # 1. Planning Screenplay fresh (never silent reuse)
        logger.info("[1/6] Planning screenplay for '%s' using %s...", topic, llm.name)
        t_start = time.time()
        plan: ScriptPlan = llm.generate_plan(topic, style_clean, preset)
        refined_plan, review = llm.review_and_refine(plan, preset)
        logger.info("Screenplay planned in %.2fs. Critic Score: %.1f/10", time.time() - t_start, review.score)

        if review.score < 7.0:
            if not allow_low_score:
                if not auto_confirm and sys.stdin.isatty():
                    try:
                        ans = input(f"Critic score {review.score:.1f}/10 is below 7.0. Continue anyway? (y/N): ").strip().lower()
                        if ans != "y":
                            raise ValueError(f"Pipeline stopped: Critic score {review.score:.1f}/10 is under 7.0. Pass --allow-low-score to continue.")
                    except (EOFError, KeyboardInterrupt):
                        raise ValueError(f"Pipeline stopped: Critic score {review.score:.1f}/10 is under 7.0. Pass --allow-low-score to continue.")
                else:
                    raise ValueError(f"Pipeline stopped: Critic score {review.score:.1f}/10 is under 7.0 after repair. Pass --allow-low-score to continue.")
            else:
                logger.warning("Proceeding despite low critic score (%.1f/10) due to --allow-low-score flag.", review.score)

        # Write self-contained brief.json and scene.json
        brief_data = {
            "video_name": video_name,
            "story": topic,
            "style": style_clean,
            "characters": [c.name for c in refined_plan.characters],
            "speaker": refined_plan.scenes[0].speaker if refined_plan.scenes else "all",
            "voice": voice.name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        (build_dir / "brief.json").write_text(json.dumps(brief_data, indent=2), encoding="utf-8")
        (build_dir / "scene.json").write_text(json.dumps(refined_plan.model_dump(), indent=2), encoding="utf-8")

        # 2. Cost Gate
        cost_est = estimate_costs(refined_plan, preset, rewrite_count=1)
        if not confirm_cost_gate(cost_est, auto_confirm=auto_confirm):
            return None

        # 3. Voice Generation into videos/<video>/voice/
        logger.info("[3/6] Generating voice track via %s...", voice.name)
        t_voice = time.time()
        scene_audios = voice.generate_all_voices(refined_plan, voice_dir)
        logger.info("Voice generated in %.2fs", time.time() - t_voice)

        # Track any TTS cached files used
        for sa in scene_audios:
            if sa.audio_path and sa.audio_path.is_file():
                # Check if matching hash is in library/tts
                stem = sa.audio_path.stem
                if (paths.LIBRARY_TTS_DIR / f"{stem}.wav").is_file():
                    library_pieces_used.append(f"library/tts/{stem}.wav")

        # Register any custom elements into library/elements/custom/
        register_plan_custom_elements(refined_plan, style_clean, library_pieces_used)

        # Mandatory audio-visual word timing alignment and trigger resolution
        enforce_and_prepare_word_timings(
            plan=refined_plan,
            scene_audios=scene_audios,
            video_dir=build_dir,
            allow_fallback=allow_fallback,
        )
        generate_sync_report(
            plan=refined_plan,
            output_path=build_dir / "sync_report.txt",
            max_diff_ms=getattr(config, "MAX_SYNC_DIFFERENCE_MS", 150),
            allow_fallback=allow_fallback,
        )

        # 4. Scene Rendering
        logger.info("[4/6] Rendering scene images via %s...", renderer.name)
        t_render = time.time()
        render_kwargs: Dict[str, Any] = {}
        if getattr(renderer, "supports_scene_audios", False) and scene_audios:
            render_kwargs["scene_audios"] = scene_audios
        elif scene_audios:
            logger.info("Renderer '%s' does not support scene_audios; generating still scene frames.", renderer.name)

        if fast:
            if not getattr(renderer, "supports_fast", False):
                raise PipelineError(
                    f"Renderer '{renderer.name}' does not support fast draft mode (--fast)."
                )
            render_kwargs["fast"] = True

        if workers is not None:
            render_kwargs["workers"] = workers

        scene_images = renderer.render_all_scenes(refined_plan, preset, build_dir, **render_kwargs)
        logger.info("Scenes rendered in %.2fs", time.time() - t_render)

        # Copy background layers to visuals/ and track
        if paths.LIBRARY_BACKGROUNDS_DIR.exists():
            for bg_f in paths.LIBRARY_BACKGROUNDS_DIR.glob(f"bg_{style_clean}_*.png"):
                dest_bg = visuals_dir / bg_f.name
                if not dest_bg.exists():
                    copy_library_asset(bg_f, dest_bg)
                library_pieces_used.append(f"library/backgrounds/{bg_f.name}")

        # 5. Assembly & Motion
        logger.info("[5/6] Assembling video using %s motion...", motion.name)
        t_assembly = time.time()
        final_video_raw = assemble_final_video(
            plan=refined_plan,
            scene_images=scene_images,
            scene_audios=scene_audios,
            style_preset=preset,
            temp_dir=build_dir,
            output_dir=build_dir,
            motion_plugin=motion,
            fast=fast,
            video_name=video_name,
            library_tracker=library_pieces_used,
        )
        logger.info("Assembly completed in %.2fs", time.time() - t_assembly)

        # 6. Generate manifest.json
        manifest = generate_manifest(
            video_name=video_name,
            style=style_clean,
            plan=refined_plan,
            voice_plugin=voice,
            library_pieces_used=library_pieces_used,
        )
        (build_dir / "manifest.json").write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")

        build_succeeded = True

    finally:
        # Close and detach log file handler
        if file_handler:
            file_handler.flush()
            file_handler.close()
            toon_logger.removeHandler(file_handler)

    if build_succeeded:
        tidy_video_folder(build_dir)
        # Atomic rename build_dir to target_video_dir
        if target_video_dir.exists():
            shutil.rmtree(target_video_dir, ignore_errors=True)
        shutil.move(str(build_dir), str(target_video_dir))
        final_video_path = target_video_dir / f"{video_name}.mp4"
        logger.info("Pipeline completed successfully: %s", final_video_path)
        return final_video_path
    else:
        # On failure: keep the tmp folder with run.log and print its path
        sys.stderr.write(f"\n[BUILD FAILED] Preserving temporary build directory: {build_dir}\n")
        sys.stderr.flush()
        return None


def run_pipeline_from_brief(
    brief_source: Union[str, Path, brief_module.VideoBrief],
    renderer_name: Optional[str] = None,
    output_dir: Optional[Path] = None,
    stills_only: bool = False,
    auto_confirm: bool = True,
    mock: bool = False,
    keep_temp: bool = False,
    fast: bool = False,
    workers: Optional[int] = None,
    overwrite: bool = False,
    scene_source: Optional[Union[str, Path, ScriptPlan, Dict[str, Any]]] = None,
    allow_fallback: bool = False,
    allow_low_score: bool = False,
) -> Dict[str, Any]:
    """
    Executes the video build pipeline strictly driven by a validated VideoBrief.
    Builds inside an isolated self-contained folder under videos/<video_name>/.
    Never silently reuses old scene files.
    """
    if isinstance(brief_source, brief_module.VideoBrief):
        brief = brief_source
    else:
        brief = brief_module.load_brief(brief_source)

    config.check_cloud_sync_warning()
    check_ffmpeg_subtitles_support()

    video_name = sanitize_video_name(brief.video_name)
    base_videos_dir = output_dir or paths.VIDEOS_DIR
    target_video_dir = resolve_video_dir(video_name, base_dir=base_videos_dir)

    # Exists guard
    if target_video_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Video directory '{target_video_dir}' already exists. Choose a different name or use --overwrite."
            )
        logger.warning("Overwriting existing video directory: %s", target_video_dir)

    # Clean failure build folder
    build_id = uuid.uuid4().hex[:8]
    build_dir = base_videos_dir / f".tmp-{video_name}-{build_id}"
    build_dir.mkdir(parents=True, exist_ok=True)
    voice_dir = build_dir / "voice"
    stills_dir = build_dir / "stills"
    visuals_dir = build_dir / "visuals"
    voice_dir.mkdir(exist_ok=True)
    stills_dir.mkdir(exist_ok=True)
    visuals_dir.mkdir(exist_ok=True)

    # Set up dedicated run.log
    log_file = build_dir / "run.log"
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s", datefmt="%H:%M:%S")
    )
    toon_logger = logging.getLogger("toonshorts")
    toon_logger.addHandler(file_handler)

    library_pieces_used: List[str] = []
    build_succeeded = False

    try:
        # 1. Preset setup
        preset = load_style_preset(brief.style)
        preset["gestures"] = brief.hand_gestures
        if brief.board_animations_avoid:
            preset.setdefault("avoid", []).extend(brief.board_animations_avoid)

        # 2. Plan Screenplay fresh from story & brief (no silent reuse!)
        llm_plugin = "fake" if mock else config.DEFAULT_LLM
        try:
            llm = get_llm(llm_plugin)
        except Exception as l_err:
            if not mock:
                logger.warning("Live LLM failed (%s), falling back to offline planner for critic.", l_err)
                llm = get_llm("fake")
            else:
                raise

        if scene_source is None:
            cand1 = config.PROJECT_ROOT / "briefs" / f"{video_name}_scene.json"
            cand2 = paths.VIDEOS_DIR / f"{video_name}_scene.json"
            if cand1.is_file():
                scene_source = cand1
            elif cand2.is_file():
                scene_source = cand2

        if scene_source is not None:
            if isinstance(scene_source, ScriptPlan):
                plan = scene_source
            elif isinstance(scene_source, dict):
                plan = ScriptPlan.model_validate(scene_source)
            else:
                p_path = Path(scene_source)
                plan = ScriptPlan.model_validate(json.loads(p_path.read_text(encoding="utf-8")))
            from toonshorts.core.validator import validate_plan
            plan = validate_plan(plan)
            logger.info("Loaded pre-authored screenplay from %s", scene_source)
        else:
            try:
                plan = llm.generate_plan(brief.story, brief.style, preset)
            except Exception as l_err:
                if not mock:
                    logger.warning("Live LLM failed (%s), falling back to offline planner for brief.", l_err)
                    llm = get_llm("fake")
                    plan = llm.generate_plan(brief.story, brief.style, preset)
                else:
                    raise

        # Critic review MUST run on EVERY script, including pre-authored or hand-written scene files
        logger.info("Running critic review on screenplay...")
        refined_plan, review = llm.review_and_refine(plan, preset)
        logger.info("Critic review score: %.1f/10", review.score)

        if review.score < 7.0:
            if not allow_low_score:
                raise ValueError(
                    f"Pipeline stopped: Critic score {review.score:.1f}/10 is under 7.0 after repair. Pass --allow-low-score to continue."
                )
            else:
                logger.warning("Proceeding despite low critic score (%.1f/10) due to --allow-low-score flag.", review.score)
        plan = refined_plan

        plan.title = video_name

        if brief.characters:
            chars = [Character(name=c, visual_description=f"Character {c}") for c in brief.characters]
            if len(chars) < 2:
                sec_name = "boy_b" if chars[0].name != "boy_b" else "girl_a"
                chars.append(Character(name=sec_name, visual_description=f"Character {sec_name}"))
            if plan.characters:
                char_voice_map = {c.name.lower(): c.voice_id for c in plan.characters if getattr(c, "voice_id", None)}
                for c in chars:
                    if c.name.lower() in char_voice_map:
                        c.voice_id = char_voice_map[c.name.lower()]
            plan.characters = chars

        if scene_source is None:
            if brief.speaker and brief.speaker not in ("both", "all", "none"):
                for sc in plan.scenes:
                    sc.speaker = brief.speaker

            if brief.camera in ("fixed", "static"):
                for sc in plan.scenes:
                    sc.camera_move = CameraMove.STATIC
            elif brief.camera in ("zoom_speaker", "zoom on speaker"):
                for idx, sc in enumerate(plan.scenes):
                    if idx in (1, len(plan.scenes) - 1):
                        sc.camera_move = CameraMove.ZOOM_IN
                    else:
                        sc.camera_move = CameraMove.STATIC

        # Save brief.json and scene.json inside video folder
        (build_dir / "brief.json").write_text(json.dumps(brief.model_dump(), indent=2), encoding="utf-8")
        (build_dir / "scene.json").write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")

        # Register any custom elements into library/elements/custom/
        register_plan_custom_elements(plan, brief.style, library_pieces_used)

        # 3. Voice generation into voice_dir
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
        if fast:
            setattr(voice, "cache_only", True)

        logger.info("Generating voice tracks using engine '%s' (voice: %s)...", voice.name, brief.voice)
        try:
            scene_audios = voice.generate_all_voices(plan, voice_dir)
        except Exception as v_err:
            if not mock:
                logger.warning("Voice engine %s failed (%s), falling back to offline audio.", voice.name, v_err)
                voice = get_voice("fake")
                scene_audios = voice.generate_all_voices(plan, voice_dir)
            else:
                raise

        # Track TTS cached audio used
        for sa in scene_audios:
            if sa.audio_path and sa.audio_path.is_file():
                stem = sa.audio_path.stem
                if (paths.LIBRARY_TTS_DIR / f"{stem}.wav").is_file():
                    library_pieces_used.append(f"library/tts/{stem}.wav")

        # Register any custom elements into library/elements/custom/
        register_plan_custom_elements(plan, brief.style, library_pieces_used)

        # Mandatory audio-visual word timing alignment and trigger resolution
        enforce_and_prepare_word_timings(
            plan=plan,
            scene_audios=scene_audios,
            video_dir=build_dir,
            allow_fallback=allow_fallback,
        )
        generate_sync_report(
            plan=plan,
            output_path=build_dir / "sync_report.txt",
            max_diff_ms=getattr(config, "MAX_SYNC_DIFFERENCE_MS", 150),
            allow_fallback=allow_fallback,
        )

        # 4. Render key scene stills first
        active_renderer_name = renderer_name or getattr(brief, "renderer", None) or ("fake" if mock else (preset.get("renderer") or config.DEFAULT_RENDERER))
        if active_renderer_name == "auto":
            active_renderer_name = "cairo" if brief.style == "stickman" else "animejs"

        renderer = get_renderer(active_renderer_name)
        still_paths: List[Path] = []
        if stills_only or renderer_name == "animejs":
            key_indices = list(range(len(plan.scenes)))
        else:
            key_indices = [0]
            if len(plan.scenes) > 1:
                punchline_idx = next((i for i, s in enumerate(plan.scenes) if s.is_punchline), len(plan.scenes) - 1)
                if punchline_idx not in key_indices:
                    key_indices.append(punchline_idx)

        for s_idx in key_indices:
            sc = plan.scenes[s_idx]
            still_path = stills_dir / f"{video_name}_still_sc{sc.scene_number}.png"
            renderer.render_scene(
                scene=sc,
                characters=plan.characters,
                style_preset=preset,
                output_path=still_path,
                temp_dir=build_dir,
            )
            still_paths.append(still_path)

        logger.info("Rendered %d scene stills: %s", len(still_paths), [p.name for p in still_paths])

        # Automated Layout & Safe-Zone Check on generated scene stills
        html_still_files = list(build_dir.glob("scene_*_still.html"))
        if html_still_files:
            from toonshorts.core.layout_checker import verify_video_layout
            logger.info("Running automated layout and safe-zone check on all scene stills...")
            layout_report = verify_video_layout(build_dir)
            if not layout_report.get("passed", False):
                failed_msg = (
                    f"Automated layout check FAILED for {len(layout_report.get('failed_scenes', []))} scene(s): "
                    f"{'; '.join(layout_report.get('violations', []))}"
                )
                logger.error(failed_msg)
                raise PipelineError(failed_msg)
            logger.info("Automated layout check PASSED for all %d scenes.", layout_report.get("total_scenes", 0))

        # Automated Visual Review Gate & Contrast Check (up to 2 fix rounds)
        from toonshorts.core.visual_checker import perform_visual_check
        logger.info("Running automated visual quality review on scene stills...")
        review_result = perform_visual_check(build_dir, plan=plan, round_num=1)

        fix_round = 1
        while not review_result.get("passed", False) and fix_round < 2:
            fix_round += 1
            logger.warning("Visual review Round %d FAILED (Score: %.1f). Re-rendering stills for Round %d...", fix_round - 1, review_result.get("score", 0), fix_round)
            for s_idx in key_indices:
                sc = plan.scenes[s_idx]
                still_path = stills_dir / f"{video_name}_still_sc{sc.scene_number}.png"
                renderer.render_scene(
                    scene=sc,
                    characters=plan.characters,
                    style_preset=preset,
                    output_path=still_path,
                    temp_dir=build_dir,
                )
            review_result = perform_visual_check(build_dir, plan=plan, round_num=fix_round)

        if not review_result.get("passed", False):
            if not auto_confirm and sys.stdin.isatty():
                ans = input(f"Visual review score {review_result.get('score', 0):.1f}/10 did not pass all checks. Approve full render anyway? (y/N): ").strip().lower()
                if ans != "y":
                    raise PipelineError(f"Full render halted: Visual review score {review_result.get('score', 0):.1f}/10 failed quality gate. See visual_review.md.")
            elif not auto_confirm:
                raise PipelineError(f"Full render halted: Visual review score {review_result.get('score', 0):.1f}/10 failed quality gate after {fix_round} round(s). See visual_review.md.")
            else:
                logger.warning("Visual review score %.1f/10 below threshold, but --yes/auto-confirm was set. Proceeding.", review_result.get("score", 0))
        else:
            logger.info("Visual quality review PASSED (Score: %.1f/10). Proceeding to full render.", review_result.get("score", 0))

        # Write manifest before stills exit
        manifest = generate_manifest(
            video_name=video_name,
            style=brief.style,
            plan=plan,
            voice_plugin=voice,
            brief=brief,
            library_pieces_used=library_pieces_used,
        )
        (build_dir / "manifest.json").write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")

        if stills_only:
            build_succeeded = True
        else:
            # 5. Render all frames & Assemble full MP4
            motion_name = preset.get("motion") or config.DEFAULT_MOTION
            motion = get_motion(motion_name)

            render_kwargs: Dict[str, Any] = {}
            if getattr(renderer, "supports_scene_audios", False) and scene_audios:
                render_kwargs["scene_audios"] = scene_audios
            elif scene_audios:
                logger.info("Renderer '%s' does not support scene_audios; generating still scene frames.", renderer.name)

            if fast:
                if not getattr(renderer, "supports_fast", False):
                    raise PipelineError(
                        f"Renderer '{renderer.name}' does not support fast draft mode (--fast)."
                    )
                render_kwargs["fast"] = True

            if workers is not None:
                render_kwargs["workers"] = workers

            scene_images = renderer.render_all_scenes(plan, preset, build_dir, **render_kwargs)

            # Copy background layers to visuals/
            if paths.LIBRARY_BACKGROUNDS_DIR.exists():
                for bg_f in paths.LIBRARY_BACKGROUNDS_DIR.glob(f"bg_{brief.style}_*.png"):
                    dest_bg = visuals_dir / bg_f.name
                    if not dest_bg.exists():
                        copy_library_asset(bg_f, dest_bg)
                    library_pieces_used.append(f"library/backgrounds/{bg_f.name}")

            final_raw_video = assemble_final_video(
                plan=plan,
                scene_images=scene_images,
                scene_audios=scene_audios,
                style_preset=preset,
                temp_dir=build_dir,
                output_dir=build_dir,
                motion_plugin=motion,
                fast=fast,
                video_name=video_name,
                library_tracker=library_pieces_used,
            )

            # Update manifest with final library pieces used
            manifest.library_pieces_used = sorted(list(set(library_pieces_used)))
            (build_dir / "manifest.json").write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")

            build_succeeded = True

    finally:
        if file_handler:
            file_handler.flush()
            file_handler.close()
            toon_logger.removeHandler(file_handler)

    if build_succeeded:
        tidy_video_folder(build_dir)
        if target_video_dir.exists():
            shutil.rmtree(target_video_dir, ignore_errors=True)
        shutil.move(str(build_dir), str(target_video_dir))
        if stills_only:
            return {
                "status": "stills_ready",
                "scene_file": target_video_dir / "scene.json",
                "stills": [target_video_dir / "stills" / p.name for p in still_paths],
                "video": None,
                "video_dir": target_video_dir,
            }
        final_video_path = target_video_dir / f"{video_name}.mp4"
        logger.info("Full MP4 video generated successfully at: %s", final_video_path)
        return {
            "status": "complete",
            "scene_file": target_video_dir / "scene.json",
            "stills": [target_video_dir / "stills" / p.name for p in still_paths],
            "video": final_video_path,
            "video_dir": target_video_dir,
        }
    else:
        sys.stderr.write(f"\n[BUILD FAILED] Preserving temporary build directory: {build_dir}\n")
        sys.stderr.flush()
        raise RuntimeError(f"Brief execution failed. Temporary files preserved at: {build_dir}")
