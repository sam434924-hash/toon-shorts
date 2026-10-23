"""
Purpose: Playwright headless browser frame stepping and FFmpeg pipe video capture.
Inputs: Compiled whiteboard HTML, audio files, animation durations, and target FPS.
Outputs: Generated MP4 scene clips and still preview PNG frames.
Depends on: core.config, logging, pathlib, playwright, plugins.render.animejs.audio_sync, plugins.render.animejs.html_builder, subprocess, typing
Used by: plugins.render.animejs, plugins.render.animejs.plugin
Config keys: VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_animejs.py
"""

import logging
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright

from toonshorts.core import config
from toonshorts.plugins.render.animejs.audio_sync import compute_mouth_cues_from_audio
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html

logger = logging.getLogger(__name__)


def capture_still_frame(
    html_file: Path,
    output_path: Path,
    duration_sec: float = 2.5,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
) -> Path:
    """Renders a single still frame at animation completion using Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(html_file.resolve().as_uri())
        if page_errors:
            browser.close()
            raise RuntimeError(f"JavaScript execution error in {html_file.name}: {'; '.join(page_errors)}")
        missing = page.evaluate("typeof window.__checkModulesLoaded === 'function' ? window.__checkModulesLoaded() : ['window.__checkModulesLoaded missing']")
        if missing:
            browser.close()
            raise RuntimeError(f"Missing required JS modules or functions in {html_file.name}: {', '.join(missing)}")
        page.evaluate(f"window.seekTo({int(duration_sec * 1000)})")
        page.screenshot(path=str(output_path), type="png")
        browser.close()
    return output_path


def render_whiteboard_video(
    title: str,
    words: List[Dict[str, Any]],
    audio_path: Optional[Path],
    output_path: Path,
    duration_sec: float = 3.0,
    gesture: str = "idle",
    fps: int = config.VIDEO_FPS,
    temp_dir: Optional[Path] = None,
    scene_number: int = 1,
    annotations: Optional[List[Dict[str, Any]]] = None,
    characters_data: Optional[List[Dict[str, Any]]] = None,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
    layout: str = "cards",
    visuals: Optional[List[Any]] = None,
    word_timings: Optional[List[Any]] = None,
    theme: str = "whiteboard",
) -> Path:
    """
    Renders a fully animated MP4 video with easing transitions synced to an audio clip.
    Mouth flapping is driven by voice audio loudness (RMS).
    Character exhibits subtle idle motion.
    Streams Playwright frames directly into FFmpeg stdin.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = temp_dir or output_path.parent / "temp_animejs"
    work_dir.mkdir(parents=True, exist_ok=True)

    mouth_cues = compute_mouth_cues_from_audio(audio_path, fps=fps)

    html_content = generate_whiteboard_html(
        title=title,
        words=words,
        duration_sec=duration_sec,
        mouth_cues=mouth_cues,
        gesture=gesture,
        fps=fps,
        width=width,
        height=height,
        scene_number=scene_number,
        annotations=annotations,
        characters_data=characters_data,
        layout=layout,
        visuals=visuals,
        word_timings=word_timings,
        theme=theme,
    )

    html_file = (work_dir / "whiteboard_scene.html").resolve()
    html_file.write_text(html_content, encoding="utf-8")

    total_frames = max(1, int(round(fps * duration_sec)))

    cmd = [
        "ffmpeg", "-y",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-r", str(fps),
        "-i", "pipe:0",
    ]

    if audio_path and audio_path.is_file():
        cmd.extend([
            "-i", str(audio_path.resolve()),
            "-af", "apad",
            "-c:a", "aac",
            "-b:a", "192k",
        ])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-t", f"{duration_sec:.3f}",
        str(output_path.resolve()),
    ])

    log_file = work_dir / "ffmpeg_render.log"
    with open(log_file, "wb") as lf:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=lf,
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.goto(html_file.as_uri())

            if page_errors:
                browser.close()
                if proc.stdin:
                    proc.stdin.close()
                proc.kill()
                raise RuntimeError(f"JavaScript execution error in {html_file.name}: {'; '.join(page_errors)}")

            missing = page.evaluate("typeof window.__checkModulesLoaded === 'function' ? window.__checkModulesLoaded() : ['window.__checkModulesLoaded missing']")
            if missing:
                browser.close()
                if proc.stdin:
                    proc.stdin.close()
                proc.kill()
                raise RuntimeError(f"Missing required JS modules or functions in {html_file.name}: {', '.join(missing)}")

            try:
                for frame_idx in range(total_frames):
                    t_ms = (frame_idx / fps) * 1000.0
                    page.evaluate(f"window.seekTo({t_ms})")
                    buf = page.screenshot(type="png")
                    proc.stdin.write(buf)
            finally:
                if proc.stdin:
                    proc.stdin.close()
                proc.wait()
                browser.close()

    if proc.returncode != 0:
        log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else "No log"
        raise RuntimeError(f"FFmpeg pipeline failed with return code {proc.returncode}:\n{log_text}")

    return output_path
