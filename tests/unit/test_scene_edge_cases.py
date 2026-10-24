"""
Purpose: Unit tests verifying pipeline and rendering edge cases.
Inputs: Scenes without word timings, single-speaker casts, very short durations, and scenes with no visuals.
Outputs: Verified boundary clamping, graceful fallbacks, and error-free HTML rendering.
Depends on: pytest, toonshorts.core.camera, toonshorts.core.models, toonshorts.plugins.render.animejs.html_builder
Used by: tests
Config keys: None
Tests: tests/unit/test_scene_edge_cases.py
"""

import concurrent.futures
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright


def _run_in_clean_thread(fn):
    """Executes a function in a fresh thread to avoid asyncio loop collisions on Windows."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        return future.result()

from toonshorts.core import config
from toonshorts.core.camera import plan_scene_camera_shots
from toonshorts.core.models import Character, Scene, Pose, CameraMove, Transition
from toonshorts.plugins.render.animejs.cast import build_characters_data, resolve_scene_cast
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html


def test_scene_without_word_timings(tmp_path: Path):
    """
    Edge case 1: Scene with word_timings=None or empty list.
    Shot planner defaults gracefully to wide framing or visual cues without crash,
    and HTML renders cleanly without JavaScript errors in browser.
    """
    scene = Scene(
        scene_number=1,
        speaker="boy_b",
        dialogue_line="Speech without word alignment timestamps.",
        action="Explains concept casually",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
        cast=["boy_b", "girl_a"],
        word_timings=None,
    )

    shots = plan_scene_camera_shots(
        duration_sec=3.0,
        word_timings=None,
        visuals=[],
        speaker_id="character-rig",
    )
    assert shots == [], "Zero cues without word timings must result in 0 camera moves (locked on wide)"

    chars = [
        Character(name="boy_b", visual_description="Boy in dark hoodie"),
        Character(name="girl_a", visual_description="Girl with blonde hair"),
    ]
    cast = resolve_scene_cast(scene, chars)
    chars_data = build_characters_data(cast, scene=scene)

    html = generate_whiteboard_html(
        title="No Word Timings",
        words=[{"text": "No Timings", "start_ms": 300}],
        duration_sec=3.0,
        scene_number=1,
        word_timings=None,
        characters_data=chars_data,
        theme="night_studio",
    )

    html_file = tmp_path / "edge_no_wts.html"
    html_file.write_text(html, encoding="utf-8")

    def _check_browser():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.goto(html_file.resolve().as_uri())
            assert not page_errors, f"JavaScript error on page: {page_errors}"

            # Seek to middle of scene
            page.evaluate("window.seekTo(1500)")
            cam_state = page.evaluate("window.computeCameraState(1500, 45)")
            assert cam_state["camZoom"] == 1.0, "Camera must stay at 1.0 zoom (wide)"
            browser.close()

    _run_in_clean_thread(_check_browser)


def test_single_speaker_scene(tmp_path: Path):
    """
    Edge case 2: Single-speaker scene with only 1 character in cast.
    Verifies listener glance eye resolution does not crash,
    only 1 character slot is populated, and DOM renders cleanly.
    """
    solo_char = Character(name="solo_presenter", visual_description="Solo tech presenter")
    scene = Scene(
        scene_number=1,
        speaker="solo_presenter",
        dialogue_line="Welcome to this single speaker tutorial.",
        action="Greets audience solo",
        pose=Pose.WAVING,
        gesture="wave",
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
        cast=["solo_presenter"],
    )

    cast = resolve_scene_cast(scene, [solo_char])
    assert len(cast) == 1
    assert cast[0] == "solo_presenter"

    chars_data = build_characters_data(cast, scene=scene)
    assert len(chars_data) == 1
    assert chars_data[0]["is_speaker"] is True
    assert chars_data[0]["slot"] == "left"

    html = generate_whiteboard_html(
        title="Single Speaker",
        words=[{"text": "Solo Show", "start_ms": 200}],
        duration_sec=2.5,
        scene_number=1,
        characters_data=chars_data,
        theme="whiteboard",
    )

    # Must contain left rig and NOT contain right rig
    assert 'id="character-rig"' in html
    assert 'id="character-rig-right"' not in html

    html_file = tmp_path / "edge_single_speaker.html"
    html_file.write_text(html, encoding="utf-8")

    def _check_browser():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.goto(html_file.resolve().as_uri())
            assert not page_errors

            # Check DOM presence
            left_exists = page.evaluate("document.getElementById('character-rig') !== null")
            right_exists = page.evaluate("document.getElementById('character-rig-right') !== null")
            assert left_exists is True
            assert right_exists is False
            browser.close()

    _run_in_clean_thread(_check_browser)


def test_very_short_scene(tmp_path: Path):
    """
    Edge case 3: Very short scene (0.8 seconds / 800ms).
    Verifies shot transitions clamp within scene boundaries without negative holds,
    and frame stepping completes all frames safely.
    """
    short_duration = 0.8
    fps = 30
    total_frames = int(short_duration * fps)  # 24 frames

    wts = [{"word": "quick", "start_time": 0.1, "end_time": 0.4}]
    shots = plan_scene_camera_shots(
        duration_sec=short_duration,
        word_timings=wts,
        speaker_id="character-rig",
    )
    for s in shots:
        assert s["t_start"] >= 0
        assert s["t_end"] <= int(short_duration * 1000)

    html = generate_whiteboard_html(
        title="Quick Cut",
        words=[{"text": "Blink", "start_ms": 100}],
        duration_sec=short_duration,
        fps=fps,
        scene_number=1,
        word_timings=wts,
        theme="night_studio",
    )

    html_file = tmp_path / "edge_short_scene.html"
    html_file.write_text(html, encoding="utf-8")

    def _check_browser():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.goto(html_file.resolve().as_uri())
            assert not page_errors

            # Step through every frame of the very short scene
            for i in range(total_frames):
                t_ms = (i / fps) * 1000.0
                page.evaluate(f"window.seekTo({t_ms})")
            browser.close()

    _run_in_clean_thread(_check_browser)


def test_scene_with_no_visuals(tmp_path: Path):
    """
    Edge case 4: Scene with visuals=[] or None.
    Board objects resolve to empty list, stage visuals are empty,
    camera stays locked or targets speaker without searching for nonexistent visual IDs.
    """
    html = generate_whiteboard_html(
        title="Pure Dialogue",
        words=[{"text": "Talking Head", "start_ms": 300}],
        duration_sec=3.5,
        scene_number=1,
        layout="stage",
        visuals=[],
        board_objects=[],
        theme="night_studio",
    )

    # Empty board objects and empty stage visuals in JS payload
    assert 'window.__stageVisuals = [];' in html
    assert 'window.__boardObjects = [];' in html

    html_file = tmp_path / "edge_no_visuals.html"
    html_file.write_text(html, encoding="utf-8")

    def _check_browser():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.goto(html_file.resolve().as_uri())
            assert not page_errors

            vis_len = page.evaluate("window.__stageVisuals.length")
            bo_len = page.evaluate("window.__boardObjects.length")
            assert vis_len == 0
            assert bo_len == 0

            # SeekTo works cleanly
            page.evaluate("window.seekTo(2000)")
            browser.close()

    _run_in_clean_thread(_check_browser)
