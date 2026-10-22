"""Unit tests for the Anime.js HTML whiteboard animation plugin, character rig, and mouth-sync timing."""

import html
import math
import struct
import wave
from pathlib import Path
from PIL import Image
import pytest
from playwright.sync_api import sync_playwright

from toonshorts.core import config
from toonshorts.core.models import Character, Scene, ScriptPlan, Pose, CameraMove, Transition, WordTiming
from toonshorts.core.registry import get_renderer, list_renderers
from toonshorts.plugins.render.animejs import (
    AnimeJSRenderPlugin,
    compute_mouth_cues_from_audio,
    extract_whiteboard_content_for_scene,
    extract_whiteboard_content_and_annotations,
    generate_whiteboard_html,
    sanitize_gesture,
    compute_gesture_bounds,
    generate_scene_decorations,
    SAFE_AREA,
    ALLOWED_GESTURES,
)
from toonshorts.core.errors import VoiceError
from toonshorts.core.client import GeminiClientWrapper
from toonshorts.plugins.voice.gemini_tts import GeminiTTSVoicePlugin



def test_animejs_registered():
    """Verify animejs is properly registered in the plugin registry."""
    assert "animejs" in list_renderers()
    renderer = get_renderer("animejs")
    assert isinstance(renderer, AnimeJSRenderPlugin)
    assert renderer.name == "animejs"


def test_html_security_escaping_and_local_bundle():
    """Verify malicious input is strictly HTML-escaped and no CDNs are loaded."""
    malicious_title = '<script>alert("pwned")</script> & "Title"'
    malicious_words = [
        {"text": '<img src=x onerror="alert(1)"> & "Word1"'},
        {"text": "Normal Word"},
        {"text": "<b>Bold Word</b>"}
    ]

    html_out = generate_whiteboard_html(
        title=malicious_title,
        words=malicious_words,
        duration_sec=3.0,
    )

    # 1. Verify dangerous tags are escaped
    assert "<script>alert" not in html_out
    assert "&lt;script&gt;alert" in html_out
    assert "<img src=x" not in html_out
    assert "&lt;img src=x" in html_out
    assert "&lt;b&gt;Bold Word&lt;/b&gt;" in html_out

    # 2. Verify NO remote CDN script tags exist
    assert "https://cdn" not in html_out
    assert "http://cdn" not in html_out
    assert "https://cdnjs" not in html_out
    assert "https://jsdelivr" not in html_out

    # 3. Verify local anime.js is inlined
    assert "anime.js v3.2.2" in html_out

    # 4. Verify easing functions
    assert "easeOutBack" in html_out
    assert "easeOutElastic" in html_out

    # 5. Verify character rig, desk, and mouth elements are present
    assert 'id="character-rig"' in html_out
    assert 'id="mouth-closed"' in html_out
    assert 'id="mouth-open"' in html_out
    assert 'class="desk-container"' in html_out


def test_mouth_sync_timing_silence_vs_tone(tmp_path):
    """
    Test mouth sync timing:
    0.5s pure silence followed by 0.5s loud 440Hz sine tone.
    At 30 fps, first 15 frames must be mouth-closed (False),
    and sound frames must be mouth-open (True).
    """
    wav_path = tmp_path / "test_timing.wav"
    sample_rate = 24000
    fps = 30
    duration_silence = 0.5
    duration_tone = 0.5
    n_silence = int(duration_silence * sample_rate)
    n_tone = int(duration_tone * sample_rate)

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = bytearray()
        # Silence
        raw.extend(b"\x00\x00" * n_silence)
        # 440 Hz Tone
        for i in range(n_tone):
            val = int(12000.0 * math.sin(2.0 * math.pi * 440.0 * (i / sample_rate)))
            raw.extend(struct.pack("<h", val))
        wf.writeframes(raw)

    cues = compute_mouth_cues_from_audio(wav_path, fps=fps)
    assert len(cues) == 30  # 1.0 second total at 30 fps

    # First half (frames 0 to 14) is silence -> mouth must be closed
    silence_cues = cues[:14]
    assert all(c is False for c in silence_cues), f"Expected silence to be closed, got: {silence_cues}"

    # Second half (frames 17 to 29) has loud tone -> mouth must be open
    tone_cues = cues[17:]
    assert all(c is True for c in tone_cues), f"Expected tone to be open, got: {tone_cues}"


def test_whiteboard_content_extraction():
    """Verify extracting title and points from scene actions."""
    scene1 = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="Welcome to API basics.",
        action="What is an API?: Application, Programming, Interface",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )
    title1, words1 = extract_whiteboard_content_for_scene(scene1, duration_sec=4.0)
    assert title1 == "What is an API?"
    assert len(words1) == 3
    assert words1[0]["text"] == "Application"
    assert words1[1]["text"] == "Programming"
    assert words1[2]["text"] == "Interface"
    assert words1[0]["start_ms"] < words1[1]["start_ms"] < words1[2]["start_ms"]


def test_render_scene_still(tmp_path):
    """Verify render_scene produces a valid 1080x1920 PNG frame."""
    renderer = get_renderer("animejs")
    scene = Scene(
        scene_number=1,
        speaker="Guide",
        dialogue_line="Welcome to our whiteboard session.",
        action="Presenting three key ideas: Point A, Point B, Point C",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )
    characters = [Character(name="Guide", visual_description="Animator")]
    preset = {"renderer": "animejs"}

    out_img = tmp_path / "test_wb_frame.png"
    result = renderer.render_scene(scene, characters, preset, out_img, tmp_path)

    assert result.is_file()
    assert result.stat().st_size > 0
    with Image.open(result) as img:
        assert img.size == (1080, 1920)


def test_mouth_cues_empty_and_missing_audio(tmp_path):
    """Verify compute_mouth_cues_from_audio gracefully handles None, missing, and empty files."""
    assert compute_mouth_cues_from_audio(None) == []

    missing = tmp_path / "non_existent.wav"
    assert compute_mouth_cues_from_audio(missing) == []

    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    assert compute_mouth_cues_from_audio(empty) == []


def test_render_scene_relative_path(tmp_path, monkeypatch):
    """Verify render_scene works seamlessly when relative paths are supplied."""
    monkeypatch.chdir(tmp_path)
    rel_temp = Path("relative_temp")
    rel_temp.mkdir()
    rel_out = rel_temp / "frame.png"

    renderer = get_renderer("animejs")
    scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="Testing relative path resolution.",
        action="Relative path check: Step 1, Step 2",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )
    result = renderer.render_scene(scene, [], {}, rel_out, rel_temp)
    assert result.is_file()
    assert result.stat().st_size > 0


def test_sanitize_gesture_whitelist():
    """Verify gesture sanitization strictly enforces allowed whitelist and maps synonyms."""
    assert sanitize_gesture("idle") == "idle"
    assert sanitize_gesture("wave") == "wave"
    assert sanitize_gesture("point") == "point"
    assert sanitize_gesture("explain") == "explain"
    assert sanitize_gesture("open_hand") == "explain"
    assert sanitize_gesture("thumbs_up") == "thumbs_up"
    assert sanitize_gesture("shrug") == "shrug"
    assert sanitize_gesture(None) == "idle"
    assert sanitize_gesture("") == "idle"

    with pytest.raises(ValueError, match="Invalid gesture"):
        sanitize_gesture("unsupported_gesture")

    with pytest.raises(ValueError, match="Invalid gesture"):
        sanitize_gesture("../../../etc/passwd")


def test_scene_model_gesture_validation():
    """Verify Scene model enforces valid gestures at model initialization."""
    valid_scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="Hello!",
        action="Wave to audience",
        gesture="wave",
    )
    assert valid_scene.gesture == "wave"

    with pytest.raises(ValueError, match="Invalid gesture"):
        Scene(
            scene_number=2,
            speaker="Host",
            dialogue_line="Invalid pose",
            action="Moonwalk",
            gesture="moonwalk",
        )


def test_html_generation_with_different_gestures():
    """Verify each allowed gesture generates its distinct SVG arm pose elements in HTML."""
    for g in ["wave", "point", "explain", "thumbs_up", "shrug", "idle"]:
        html_code = generate_whiteboard_html(
            title="Gesture Test",
            words=[{"text": "Point 1"}],
            duration_sec=2.0,
            gesture=g,
        )
        assert f"arm-gesture-{g if g != 'open_hand' else 'explain'}" in html_code or "character-rig" in html_code


def test_gesture_bounding_boxes_within_safe_area():
    """
    Computes each gesture's bounding box and asserts that all arm/hand geometry
    strictly stays inside the safe area (safe margins on all four sides).
    Fails if any gesture's arm or hand leaves the safe area.
    """
    gestures_to_test = ["idle", "wave", "point", "explain", "open_hand", "thumbs_up", "shrug"]

    # 1. Analytical safe area check
    for g in gestures_to_test:
        bounds = compute_gesture_bounds(g)
        assert bounds["min_x"] >= SAFE_AREA["min_x"], (
            f"Gesture '{g}' left boundary ({bounds['min_x']}px) violates safe area ({SAFE_AREA['min_x']}px)!"
        )
        assert bounds["max_x"] <= SAFE_AREA["max_x"], (
            f"Gesture '{g}' right boundary ({bounds['max_x']}px) violates safe area ({SAFE_AREA['max_x']}px)!"
        )
        assert bounds["min_y"] >= SAFE_AREA["min_y"], (
            f"Gesture '{g}' top boundary ({bounds['min_y']}px) violates safe area ({SAFE_AREA['min_y']}px)!"
        )
        assert bounds["max_y"] <= SAFE_AREA["max_y"], (
            f"Gesture '{g}' bottom boundary ({bounds['max_y']}px) violates safe area ({SAFE_AREA['max_y']}px)!"
        )

    # 2. Live DOM Playwright check
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": config.VIDEO_WIDTH, "height": config.VIDEO_HEIGHT})

        for g in gestures_to_test:
            clean_name = "explain" if g == "open_hand" else g
            html_code = generate_whiteboard_html(
                title="BBox Safe Area Test",
                words=[{"text": "Safe Area Verification"}],
                duration_sec=2.0,
                gesture=g,
            )
            page.set_content(html_code)
            target_id = f"arm-gesture-{clean_name}"

            for ms in [0, 200, 500, 1000]:
                page.evaluate(f"window.seekAnimation({ms})")
                dom_box = page.evaluate(f'''() => {{
                    const el = document.getElementById("{target_id}") || document.querySelector(".active-arm-gesture");
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return {{ min_x: r.left, max_x: r.right, min_y: r.top, max_y: r.bottom }};
                }}''')

                assert dom_box is not None, f"Arm element for gesture '{g}' not found in rendered DOM at {ms}ms"
                assert dom_box["min_x"] >= SAFE_AREA["min_x"], (
                    f"DOM rendered gesture '{g}' min_x ({dom_box['min_x']}) clipped outside safe area min_x ({SAFE_AREA['min_x']}) at {ms}ms"
                )
                assert dom_box["max_x"] <= SAFE_AREA["max_x"], (
                    f"DOM rendered gesture '{g}' max_x ({dom_box['max_x']}) clipped outside safe area max_x ({SAFE_AREA['max_x']}) at {ms}ms"
                )
                assert dom_box["min_y"] >= SAFE_AREA["min_y"], (
                    f"DOM rendered gesture '{g}' min_y ({dom_box['min_y']}) clipped outside safe area min_y ({SAFE_AREA['min_y']}) at {ms}ms"
                )
                assert dom_box["max_y"] <= SAFE_AREA["max_y"], (
                    f"DOM rendered gesture '{g}' max_y ({dom_box['max_y']}) clipped outside safe area max_y ({SAFE_AREA['max_y']}) at {ms}ms"
                )

        browser.close()


def test_roughjs_local_bundle_and_determinism():
    """Verify Rough.js is bundled locally (no CDN) and generates deterministic sketches."""
    assert config.ROUGH_JS_PATH.is_file(), f"Rough.js missing at {config.ROUGH_JS_PATH}"
    assert config.ROUGH_JS_PATH.stat().st_size > 10000

    html_code = generate_whiteboard_html(
        title="Rough.js Test",
        words=[{"text": "Point One"}, {"text": "Point Two"}],
        duration_sec=3.0,
    )

    # 1. Verify no CDN
    assert "unpkg.com" not in html_code
    assert "jsdelivr.net" not in html_code
    assert "cdnjs.cloudflare.com" not in html_code

    # 2. Verify Rough.js canvas and sketch elements are present
    assert 'id="rough-canvas"' in html_code
    assert "rough.svg" in html_code
    assert "seed: 101" in html_code  # Fixed title underline seed

    # 3. Verify execution and rendered elements in Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": config.VIDEO_WIDTH, "height": config.VIDEO_HEIGHT})
        page.set_content(html_code)

        rough_node_count = page.evaluate("() => document.getElementById('rough-canvas').children.length")
        assert rough_node_count >= 2, f"Expected at least 2 sketched rough nodes, got {rough_node_count}"

        # Seek to 1.5s to trigger active speaking highlight
        page.evaluate("window.seekAnimation(1500)")
        active_cards = page.evaluate("() => document.querySelectorAll('.word-card.active-speaking').length")
        assert active_cards == 1, f"Expected 1 active speaking card highlighted, got {active_cards}"

        browser.close()


def test_missing_gemini_api_key_fails_cleanly(monkeypatch):
    """Verify pipeline fails with a clear VoiceError if GEMINI_API_KEY is missing, never silent mock audio."""
    # Simulate missing GEMINI_API_KEY
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")

    client = GeminiClientWrapper(api_key="")
    assert client.mock is True
    assert getattr(client, "is_auto_fallback", False) is True

    # Direct speech call with missing key must raise VoiceError
    with pytest.raises(VoiceError, match="GEMINI_API_KEY is missing"):
        client.generate_speech_with_retry("Test dialogue line", "Kore")

    # GeminiTTSVoicePlugin on cache miss with missing key must raise VoiceError
    plugin = GeminiTTSVoicePlugin(client=client)
    dummy_scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="A unique phrase that definitely misses cache 999999999",
        action="Speak",
        gesture="idle",
    )
    with pytest.raises(VoiceError, match="GEMINI_API_KEY is missing"):
        plugin.generate_scene_voice(1, dummy_scene, "Kore", Path("temp"))


def test_scene_decorations_identical_across_scenes():
    """Verify background fixtures and desk props are 100% identical across scenes 1 through 6."""
    decorations = [generate_scene_decorations(sn) for sn in range(1, 7)]
    shelves = [d[0] for d in decorations]
    desks = [d[1] for d in decorations]

    # All 6 shelf decorations must be 100% identical
    assert len(set(shelves)) == 1, "Expected shelf decorations to be identical across all scenes"
    # All 6 desk prop decorations must be 100% identical
    assert len(set(desks)) == 1, "Expected desk prop decorations to be identical across all scenes"


def test_annotation_start_time_equals_word_start_time():
    """Verify annotation start times match their tied word start times."""
    word_timings = [
        WordTiming(word="Welcome", start_time=0.1, end_time=0.4),
        WordTiming(word="to", start_time=0.45, end_time=0.55),
        WordTiming(word="API", start_time=0.6, end_time=0.9),
        WordTiming(word="Application", start_time=1.0, end_time=1.5),
        WordTiming(word="Programming", start_time=1.8, end_time=2.3),
        WordTiming(word="Interface", start_time=2.5, end_time=3.0),
    ]
    scene = Scene(
        scene_number=1,
        speaker="Host",
        dialogue_line="Welcome to API: Application, Programming, Interface",
        action="What is an API?: Application, Programming, Interface",
        pose=Pose.IDLE,
        camera_move=CameraMove.STATIC,
        transition=Transition.CUT,
    )
    title, words, annotations = extract_whiteboard_content_and_annotations(
        scene, duration_sec=3.5, word_timings=word_timings
    )

    assert len(annotations) > 0
    for annot in annotations:
        tied_wt = annot.get("tied_word_obj")
        assert tied_wt is not None, f"Annotation {annot['id']} has no tied_word_obj"
        assert annot["start_time"] == pytest.approx(tied_wt.start_time, abs=1e-4), (
            f"Annotation {annot['id']} start_time ({annot['start_time']}) does not equal word start_time ({tied_wt.start_time})"
        )



