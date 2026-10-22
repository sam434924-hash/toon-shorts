"""
Renders the Scene Format v2 'What is an API' fixture with animated whiteboard visuals.
Generates:
1. Fast preview render (540x960, 15fps) to output/pack_tests/v2/What_is_an_API_v2_fast.mp4
2. 3 extracted frames per visual to output/pack_tests/v2/frames/
3. Full-size normal render (1080x1920, 30fps) to output/pack_tests/v2/What_is_an_API_v2.mp4
Strictly preserves output/What_is_an_API.mp4.
"""

import json
import logging
from pathlib import Path
import shutil
import subprocess

from playwright.sync_api import sync_playwright

from toonshorts.core import config
from toonshorts.core.assembler import assemble_final_video
from toonshorts.core.models import ScriptPlan
from toonshorts.plugins.render.animejs import AnimeJSRenderPlugin
from toonshorts.plugins.voice.gemini_tts import GeminiTTSVoicePlugin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("render_v2_pack")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "pack_tests" / "v2"
FRAMES_DIR = OUTPUT_DIR / "frames"

PROTECTED_ORIGINAL = PROJECT_ROOT / "output" / "What_is_an_API.mp4"
ORIGINAL_MTIME = PROTECTED_ORIGINAL.stat().st_mtime if PROTECTED_ORIGINAL.exists() else None


def verify_protected_files():
    if ORIGINAL_MTIME is not None and PROTECTED_ORIGINAL.exists():
        assert PROTECTED_ORIGINAL.stat().st_mtime == ORIGINAL_MTIME, "CRITICAL ERROR: output/What_is_an_API.mp4 was altered!"


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "what_is_an_api_v2_plan.json"
    plan_data = json.loads(fixture_path.read_text(encoding="utf-8"))
    plan = ScriptPlan.model_validate(plan_data)

    style_preset = {
        "pacing": "fast",
        "default_sound_effects": ["pop"],
    }

    temp_root = OUTPUT_DIR / "temp_render"
    temp_root.mkdir(parents=True, exist_ok=True)

    # 1. Voice generation (100% cache hits, zero live Gemini API calls)
    logger.info("Generating/retrieving cached audio...")
    audio_dir = temp_root / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    tts = GeminiTTSVoicePlugin(allow_noncommercial=True)
    tts.cache_only = True  # Strict safeguard: fails immediately if any cache miss
    scene_audios = tts.generate_all_voices(plan, audio_dir)
    assert tts.cache_hits == len(plan.scenes), f"Expected all {len(plan.scenes)} scenes to hit cache, got {tts.cache_hits}"

    renderer = AnimeJSRenderPlugin()

    # 2. Extract frames at 3 timestamps for each visual using Playwright
    logger.info("Extracting visual inspection frames...")
    # Pre-render HTML for scenes 3 and 5 to capture frames
    from toonshorts.plugins.render.animejs import (
        extract_whiteboard_content_and_annotations,
        resolve_scene_cast,
        build_characters_data,
    )
    from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for sc_num, v_name, timestamps in [
            (3, "flow", [("before", 200), ("mid", 1300), ("finished", 3500)]),
            (5, "reqres", [("before", 1000), ("mid", 3300), ("finished", 4800)]),
        ]:
            scene = plan.scenes[sc_num - 1]
            audio = scene_audios[sc_num - 1]
            title, words, annotations = extract_whiteboard_content_and_annotations(
                scene, audio.scene_total_duration, audio.word_timings
            )
            scene_cast = resolve_scene_cast(scene, plan.characters)
            chars_data = build_characters_data(scene_cast, scene=scene, style_preset=style_preset)

            html = generate_whiteboard_html(
                title=title,
                words=words,
                duration_sec=audio.scene_total_duration,
                gesture=scene.gesture or "idle",
                fps=30,
                width=1080,
                height=1920,
                scene_number=scene.scene_number,
                annotations=annotations,
                characters_data=chars_data,
                layout=scene.layout,
                visuals=scene.visuals,
                word_timings=audio.word_timings,
            )
            sc_html_file = temp_root / f"scene_{sc_num}_inspect.html"
            sc_html_file.write_text(html, encoding="utf-8")

            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.goto(sc_html_file.resolve().as_uri())

            for stage_name, t_ms in timestamps:
                page.evaluate(f"window.seekTo({t_ms})")
                out_png = FRAMES_DIR / f"scene{sc_num}_{v_name}_{stage_name}.png"
                page.screenshot(path=str(out_png), type="png")
                logger.info("Saved inspection frame: %s (at %d ms)", out_png.name, t_ms)

            page.close()

        browser.close()

    # 3. Fast preview render (15 fps, 540x960)
    logger.info("Rendering fast preview video...")
    fast_temp = temp_root / "fast_scenes"
    fast_clips = renderer.render_all_scenes(
        plan=plan,
        style_preset=style_preset,
        temp_dir=fast_temp,
        scene_audios=scene_audios,
        fast=True,
    )
    # Concatenate fast clips with assembler
    fast_output = OUTPUT_DIR / "What_is_an_API_v2_fast.mp4"
    assemble_final_video(
        plan=plan,
        scene_images=fast_clips,
        scene_audios=scene_audios,
        style_preset=style_preset,
        temp_dir=fast_temp / "asm",
        output_dir=OUTPUT_DIR,
        fast=True,
    )
    # Move the fast video from output/fast if generated there
    generated_fast = config.OUTPUT_DIR / "fast" / f"{plan.title}_fast.mp4"
    if generated_fast.exists():
        shutil.move(str(generated_fast), str(fast_output))

    logger.info("Fast video generated: %s (exists=%s)", fast_output, fast_output.is_file())

    # 4. Full-size normal render (30 fps, 1080x1920)
    logger.info("Rendering full-size normal video (1080x1920, 30fps)...")
    normal_temp = temp_root / "normal_scenes"
    normal_clips = renderer.render_all_scenes(
        plan=plan,
        style_preset=style_preset,
        temp_dir=normal_temp,
        scene_audios=scene_audios,
        fast=False,
    )
    normal_output = OUTPUT_DIR / "What_is_an_API_v2.mp4"
    assemble_final_video(
        plan=plan,
        scene_images=normal_clips,
        scene_audios=scene_audios,
        style_preset=style_preset,
        temp_dir=normal_temp / "asm",
        output_dir=OUTPUT_DIR,
        fast=False,
    )
    logger.info("Normal video generated: %s (exists=%s)", normal_output, normal_output.is_file())

    verify_protected_files()
    logger.info("All renders and frame extractions completed successfully!")


if __name__ == "__main__":
    run()
