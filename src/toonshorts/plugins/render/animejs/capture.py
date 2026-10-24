"""
Purpose: Playwright headless browser frame stepping, FFmpeg pipe video capture, and parallel worker pool.
Inputs: Compiled whiteboard HTML, audio files, animation durations, target FPS, and scene jobs.
Outputs: Generated MP4 scene clips and still preview PNG frames.
Depends on: concurrent.futures, dataclasses, hashlib, logging, pathlib, playwright, plugins.render.animejs.audio_sync, plugins.render.animejs.html_builder, plugins.render.animejs.layout, shutil, subprocess, tempfile, threading, typing
Used by: plugins.render.animejs, plugins.render.animejs.plugin
Config keys: ENABLE_PARALLAX_BACKGROUND, ENABLE_PARALLAX_CACHE, ENABLE_SPLIT_CAMERA_ZONES, LAYOUT_CAMERA_VERSION, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_animejs.py, tests/unit/test_split_camera_zones.py
"""

import concurrent.futures
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from typing import Any, Dict, List, Optional

from playwright.sync_api import Browser, sync_playwright

from toonshorts.core import config
from toonshorts.plugins.render.animejs.audio_sync import compute_mouth_cues_from_audio
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html
from toonshorts.plugins.render.animejs.layout import build_parallax_background_layers

logger = logging.getLogger(__name__)

DEFAULT_WORKERS = 2
MAX_WORKERS = 4


def validate_worker_count(workers: Optional[int]) -> int:
    """
    Validates the worker count for parallel rendering.
    Defaults to 2; accepts integers from 1 up to MAX_WORKERS (4);
    rejects any value below 1 or above 4 with an explicit ValueError.
    """
    if workers is None:
        return DEFAULT_WORKERS
    if not isinstance(workers, int) or workers < 1 or workers > MAX_WORKERS:
        raise ValueError(
            f"Invalid worker count: {workers}. Worker count must be an integer between 1 and {MAX_WORKERS}."
        )
    return workers


def derive_scene_seed(scene_number: int, global_seed: int = 42) -> int:
    """
    Derives a deterministic Rough.js integer seed per scene from the scene number and a global seed.
    Never uses time-based or completion-order-based seeds so parallel equals sequential output.
    """
    return (int(global_seed) * 10007 + int(scene_number) * 1013) & 0x7FFFFFFF


@dataclass
class SceneRenderJob:
    """Specification of a single scene to render into an MP4 video clip."""
    scene_number: int
    title: str
    words: List[Dict[str, Any]]
    audio_path: Optional[Path]
    output_path: Path
    duration_sec: float = 3.0
    gesture: str = "idle"
    fps: int = config.VIDEO_FPS
    annotations: Optional[List[Dict[str, Any]]] = None
    characters_data: Optional[List[Dict[str, Any]]] = None
    width: int = config.VIDEO_WIDTH
    height: int = config.VIDEO_HEIGHT
    layout: str = "cards"
    visuals: Optional[List[Any]] = None
    word_timings: Optional[List[Any]] = None
    theme: str = "whiteboard"
    rough_seed: Optional[int] = None
    fast: bool = False
    temp_dir: Optional[Path] = None
    bg_layer_images: Optional[Dict[str, str]] = None
    enable_split_camera_zones: Optional[bool] = None


_CACHE_LOCK = threading.Lock()


def render_cached_parallax_layers(
    themes: List[str],
    cache_dir: Path,
    browser: Optional[Browser] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Renders each vector SVG parallax layer (far, mid, near) ONCE per scene into a cached PNG image.
    Keyed by a SHA-256 content hash with strictly no user text in any path.
    Reuses existing cached PNGs when available.
    Returns mapping: {theme: {"far": uri, "mid": uri, "near": uri}}.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, Dict[str, str]] = {}

    own_browser = False
    p_inst = None
    b_inst = browser

    if b_inst is None:
        try:
            import asyncio
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(
                    render_cached_parallax_layers,
                    themes=themes,
                    cache_dir=cache_dir,
                    browser=None,
                ).result()

        p_inst = sync_playwright().start()
        b_inst = p_inst.chromium.launch(headless=True)
        own_browser = True

    try:
        with _CACHE_LOCK:
            page = b_inst.new_page(viewport={"width": 1680, "height": 2520})
            try:
                for theme in themes:
                    theme_results: Dict[str, str] = {}
                    bg_layers = build_parallax_background_layers(theme=theme, style_profile=None)
                    for layer_name in ("far", "mid", "near"):
                        svg_content = bg_layers.get(layer_name, "")
                        if not svg_content:
                            continue
                        layout_ver = getattr(config, "LAYOUT_CAMERA_VERSION", "2.1.0")
                        split_mode = "split" if getattr(config, "ENABLE_SPLIT_CAMERA_ZONES", False) else "single"
                        content_hash = hashlib.sha256(f"{layout_ver}:{split_mode}:{svg_content}".encode("utf-8")).hexdigest()[:16]
                        png_path = cache_dir / f"bg_{theme}_{layer_name}_{content_hash}.png"
                        if not png_path.exists():
                            tmp_html = cache_dir / f"tmp_{theme}_{layer_name}_{threading.get_ident()}.html"
                            tmp_html.write_text(
                                f"<!DOCTYPE html><html><head><style>"
                                f"* {{ margin: 0; padding: 0; box-sizing: border-box; }}"
                                f"html, body {{ width: 1680px; height: 2520px; overflow: hidden; background: transparent; }}"
                                f"svg {{ width: 1680px; height: 2520px; display: block; }}"
                                f"</style></head><body>{svg_content}</body></html>",
                                encoding="utf-8",
                            )
                            page.goto(tmp_html.resolve().as_uri())
                            page.screenshot(path=str(png_path), type="png", omit_background=True)
                            tmp_html.unlink(missing_ok=True)
                        theme_results[layer_name] = png_path.resolve().as_uri()
                    results[theme] = theme_results
            finally:
                page.close()
    finally:
        if own_browser:
            if b_inst:
                try:
                    b_inst.close()
                except Exception:
                    pass
            if p_inst:
                try:
                    p_inst.stop()
                except Exception:
                    pass

    return results


def capture_still_frame(
    html_file: Path,
    output_path: Path,
    duration_sec: float = 2.5,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
) -> Path:
    """Renders a single still frame at animation completion using Playwright."""
    try:
        import asyncio
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Playwright sync API cannot run directly inside a thread with an active asyncio event loop.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(
                capture_still_frame,
                html_file=html_file,
                output_path=output_path,
                duration_sec=duration_sec,
                width=width,
                height=height,
            ).result()

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


def _render_job_with_browser(
    job: SceneRenderJob,
    browser: Optional[Browser] = None,
    cancel_event: Optional[threading.Event] = None,
    active_procs: Optional[Dict[int, subprocess.Popen]] = None,
    shared_bg_cache_dir: Optional[Path] = None,
) -> Path:
    """
    Renders a single SceneRenderJob to output_path using Playwright and an FFmpeg stdin pipe.
    Drains stderr to a dedicated log file to prevent Windows pipe deadlocks.
    Cleanly terminates FFmpeg and removes partial output on error or cancellation.
    """
    if cancel_event and cancel_event.is_set():
        raise InterruptedError(f"Rendering cancelled before Scene {job.scene_number} started.")

    job.output_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = job.temp_dir or job.output_path.parent / f"temp_animejs_sc{job.scene_number}"
    work_dir.mkdir(parents=True, exist_ok=True)

    mouth_cues = compute_mouth_cues_from_audio(job.audio_path, fps=job.fps)
    rough_seed = job.rough_seed if job.rough_seed is not None else derive_scene_seed(job.scene_number)

    if job.bg_layer_images is None and getattr(config, "ENABLE_PARALLAX_CACHE", True) and getattr(config, "ENABLE_PARALLAX_BACKGROUND", True):
        bg_cache_dir = shared_bg_cache_dir or (work_dir / "bg_cache")
        cached_bg = render_cached_parallax_layers([job.theme], cache_dir=bg_cache_dir, browser=browser)
        if job.theme in cached_bg:
            job.bg_layer_images = cached_bg[job.theme]

    html_content = generate_whiteboard_html(
        title=job.title,
        words=job.words,
        duration_sec=job.duration_sec,
        mouth_cues=mouth_cues,
        gesture=job.gesture,
        fps=job.fps,
        width=job.width,
        height=job.height,
        scene_number=job.scene_number,
        annotations=job.annotations,
        characters_data=job.characters_data,
        layout=job.layout,
        visuals=job.visuals,
        word_timings=job.word_timings,
        theme=job.theme,
        rough_seed=rough_seed,
        fast=job.fast,
        bg_layer_images=job.bg_layer_images,
        enable_split_camera_zones=job.enable_split_camera_zones,
    )

    html_file = (work_dir / "whiteboard_scene.html").resolve()
    html_file.write_text(html_content, encoding="utf-8")

    total_frames = max(1, int(round(job.fps * job.duration_sec)))

    cmd = [
        "ffmpeg", "-y",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-r", str(job.fps),
        "-i", "pipe:0",
    ]

    if job.audio_path and job.audio_path.is_file():
        cmd.extend([
            "-i", str(job.audio_path.resolve()),
            "-af", "apad",
            "-c:a", "aac",
            "-b:a", "192k",
        ])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", str(job.fps),
        "-t", f"{job.duration_sec:.3f}",
        str(job.output_path.resolve()),
    ])

    log_file = work_dir / f"ffmpeg_scene_{job.scene_number}.log"
    proc: Optional[subprocess.Popen] = None
    own_browser: Optional[Browser] = None
    context = None

    try:
        with open(log_file, "wb") as lf:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=lf,
            )
            if active_procs is not None:
                active_procs[job.scene_number] = proc

            if browser is None:
                p_inst = sync_playwright().start()
                own_browser = p_inst.chromium.launch(headless=True)
                active_browser = own_browser
            else:
                active_browser = browser

            context = active_browser.new_context(viewport={"width": job.width, "height": job.height})
            page = context.new_page()

            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.goto(html_file.as_uri())

            if page_errors:
                raise RuntimeError(f"JavaScript execution error in {html_file.name}: {'; '.join(page_errors)}")

            missing = page.evaluate(
                "typeof window.__checkModulesLoaded === 'function' ? window.__checkModulesLoaded() : ['window.__checkModulesLoaded missing']"
            )
            if missing:
                raise RuntimeError(f"Missing required JS modules or functions in {html_file.name}: {', '.join(missing)}")

            for frame_idx in range(total_frames):
                if cancel_event and cancel_event.is_set():
                    raise InterruptedError(f"Rendering cancelled for Scene {job.scene_number}")

                t_ms = (frame_idx / job.fps) * 1000.0
                page.evaluate(f"window.seekTo({t_ms})")
                buf = page.screenshot(type="png")

                try:
                    if proc.stdin and not proc.stdin.closed:
                        proc.stdin.write(buf)
                except (BrokenPipeError, OSError) as bpe:
                    logger.warning("FFmpeg pipe broken at frame %d for scene %d: %s", frame_idx, job.scene_number, bpe)
                    break

            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            ret = proc.wait()

            if ret != 0:
                last_err = ""
                if log_file.exists():
                    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                    last_err = "\n".join(lines[-20:])
                raise RuntimeError(f"FFmpeg pipeline failed for scene {job.scene_number} with return code {ret}:\n{last_err}")

    except BaseException as exc:
        if proc and proc.poll() is None:
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        if job.output_path.exists():
            try:
                job.output_path.unlink()
            except Exception:
                pass
        raise

    finally:
        if active_procs is not None and job.scene_number in active_procs:
            active_procs.pop(job.scene_number, None)

        if context:
            try:
                context.close()
            except Exception:
                pass

        if own_browser:
            try:
                own_browser.close()
            except Exception:
                pass

    return job.output_path


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
    rough_seed: Optional[int] = None,
    fast: bool = False,
    enable_split_camera_zones: Optional[bool] = None,
) -> Path:
    """
    Renders a fully animated MP4 video clip with mouth sync, camera moves, and Rough.js sketches.
    Pipes frames directly to FFmpeg stdin without intermediate PNG files on disk.
    """
    job = SceneRenderJob(
        scene_number=scene_number,
        title=title,
        words=words,
        audio_path=audio_path,
        output_path=output_path,
        duration_sec=duration_sec,
        gesture=gesture,
        fps=fps,
        annotations=annotations,
        characters_data=characters_data,
        width=width,
        height=height,
        layout=layout,
        visuals=visuals,
        word_timings=word_timings,
        theme=theme,
        rough_seed=rough_seed,
        fast=fast,
        temp_dir=temp_dir,
        enable_split_camera_zones=enable_split_camera_zones,
    )
    return _render_job_with_browser(job)


def render_scenes_in_parallel(
    jobs: List[SceneRenderJob],
    workers: Optional[int] = None,
    global_seed: int = 42,
) -> List[Path]:
    """
    Renders multiple scenes in parallel using a worker pool of Playwright browser contexts.
    - Worker pool bounded between 1 and MAX_WORKERS (4), defaulting to 2.
    - Rejects invalid worker counts with clear ValueError.
    - Does not start more browsers than worker count.
    - Rough.js seeded deterministically per scene id so parallel equals sequential output.
    - Each worker uses a unique temp directory created via tempfile.
    - Always joins scenes in scene order, never completion order.
    - If one worker fails, cancels others, cleans up temp files and partial clips, and raises
      an error clearly naming the failed scene.
    - Closes all browsers and cleans temp files on success, failure, and Ctrl+C.
    """
    num_workers = validate_worker_count(workers)
    if not jobs:
        return []

    # Assign deterministic rough_seed to each job if not already set
    for job in jobs:
        if job.rough_seed is None:
            job.rough_seed = derive_scene_seed(job.scene_number, global_seed=global_seed)

    created_temp_dirs: List[Path] = []
    active_procs: Dict[int, subprocess.Popen] = {}
    active_browsers: List[Browser] = []
    active_playwrights: List[Any] = []
    resource_lock = threading.Lock()
    cancel_event = threading.Event()
    scene_results: Dict[int, Path] = {}
    failed_scene: Optional[int] = None
    first_error: Optional[BaseException] = None

    shared_bg_cache_dir: Optional[Path] = None
    if getattr(config, "ENABLE_PARALLAX_CACHE", True) and getattr(config, "ENABLE_PARALLAX_BACKGROUND", True):
        shared_bg_cache_dir = Path(tempfile.mkdtemp(prefix="toonshorts_bg_cache_"))
        created_temp_dirs.append(shared_bg_cache_dir)

    tls = threading.local()

    def get_thread_browser() -> Browser:
        if not hasattr(tls, "playwright") or tls.playwright is None:
            pw = sync_playwright().start()
            b = pw.chromium.launch(headless=True)
            tls.playwright = pw
            tls.browser = b
            with resource_lock:
                active_playwrights.append(pw)
                active_browsers.append(b)
        return tls.browser

    def cleanup_thread():
        if hasattr(tls, "browser") and tls.browser is not None:
            try:
                tls.browser.close()
            except Exception:
                pass
            with resource_lock:
                if tls.browser in active_browsers:
                    active_browsers.remove(tls.browser)
            tls.browser = None
        if hasattr(tls, "playwright") and tls.playwright is not None:
            try:
                tls.playwright.stop()
            except Exception:
                pass
            with resource_lock:
                if tls.playwright in active_playwrights:
                    active_playwrights.remove(tls.playwright)
            tls.playwright = None

    def cleanup_all():
        cancel_event.set()
        # 1. Terminate all active FFmpeg processes
        with resource_lock:
            procs = list(active_procs.values())
        for proc in procs:
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        # 2. Close all active browsers and stop playwright
        with resource_lock:
            browsers = list(active_browsers)
            active_browsers.clear()
            pws = list(active_playwrights)
            active_playwrights.clear()

        for b in browsers:
            try:
                b.close()
            except Exception:
                pass
        for pw in pws:
            try:
                pw.stop()
            except Exception:
                pass

        # 3. Clean up partial outputs
        for job in jobs:
            if job.output_path.exists():
                try:
                    job.output_path.unlink()
                except Exception:
                    pass

        # 4. Clean up all created temp directories
        for td in created_temp_dirs:
            shutil.rmtree(td, ignore_errors=True)

    def worker_runner(job: SceneRenderJob) -> Optional[Path]:
        nonlocal failed_scene, first_error
        if cancel_event.is_set():
            return None

        # Unique temp directory created with tempfile (not from user text)
        job_temp = Path(tempfile.mkdtemp(prefix=f"toonshorts_sc{job.scene_number}_"))
        with resource_lock:
            created_temp_dirs.append(job_temp)
        job.temp_dir = job_temp

        thread_browser = get_thread_browser()
        return _render_job_with_browser(
            job=job,
            browser=thread_browser,
            cancel_event=cancel_event,
            active_procs=active_procs,
            shared_bg_cache_dir=shared_bg_cache_dir,
        )

    actual_workers = min(num_workers, len(jobs))

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
            future_to_job = {executor.submit(worker_runner, j): j for j in jobs}

            for fut in concurrent.futures.as_completed(future_to_job):
                j = future_to_job[fut]
                try:
                    clip_path = fut.result()
                    if clip_path:
                        scene_results[j.scene_number] = clip_path
                except KeyboardInterrupt:
                    cancel_event.set()
                    for other_fut in future_to_job:
                        other_fut.cancel()
                    cleanup_all()
                    raise
                except BaseException as exc:
                    if first_error is None:
                        failed_scene = j.scene_number
                        first_error = exc
                    cancel_event.set()

                    # Cancel remaining pending futures
                    for other_fut in future_to_job:
                        other_fut.cancel()

                    cleanup_all()
                    break

            # Close all browsers across worker threads
            cleanup_futs = [executor.submit(cleanup_thread) for _ in range(actual_workers)]
            concurrent.futures.wait(cleanup_futs, timeout=5)

    except KeyboardInterrupt:
        cleanup_all()
        raise

    finally:
        if first_error is not None:
            cleanup_all()
        else:
            # Clean up all created temp directories on success
            for td in created_temp_dirs:
                shutil.rmtree(td, ignore_errors=True)
            # Ensure any leftover browsers are closed
            with resource_lock:
                browsers = list(active_browsers)
                active_browsers.clear()
                pws = list(active_playwrights)
                active_playwrights.clear()
            for b in browsers:
                try:
                    b.close()
                except Exception:
                    pass
            for pw in pws:
                try:
                    pw.stop()
                except Exception:
                    pass

    if first_error is not None:
        raise RuntimeError(f"Rendering failed in Scene {failed_scene}: {first_error}") from first_error

    # Strictly ordered by scene number (never completion order)
    ordered_clips = [scene_results[job.scene_number] for job in jobs]
    return ordered_clips
