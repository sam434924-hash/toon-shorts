"""
Unit tests for speaker-to-voice mapping, label prefix stripping, and subtitle strip clearance.
Tests Phase A requirements:
- Speaker -> Voice -> Character mapping (boy_b -> Puck, girl_a -> Aoede).
- Detection of mismatched speaker/voice.
- Stripping of 'Boy:' and 'Girl:' prefixes across TTS, subtitles, board, and kinetic words.
- Subtitle strip clearance in night_studio layout.
"""

import json
from pathlib import Path
import pytest

from toonshorts.core import config
from toonshorts.core.models import Character, Scene, ScriptPlan, WordTiming, strip_speaker_label
from toonshorts.core.subtitles import generate_ass_subtitles, escape_ass_text
from toonshorts.plugins.graphics.kinetic_words import KineticWordsPlugin
from toonshorts.plugins.render.animejs.cast import build_characters_data
from toonshorts.plugins.render.animejs.layout import verify_subtitle_strip_clearance, SUBTITLE_STRIP
from toonshorts.plugins.voice.gemini_tts import GeminiTTSVoicePlugin
from toonshorts.voice_utils import assign_character_voices


def test_boy_girl_voice_mapping_octopus_facts():
    """Verify that boy_b maps to Puck and girl_a maps to Aoede."""
    chars = [
        Character(name="boy_b", visual_description="Boy with dark hoodie", voice_id="Puck"),
        Character(name="girl_a", visual_description="Girl with blonde hair", voice_id="Aoede"),
    ]
    plan = ScriptPlan(
        title="Octopus Facts Test",
        art_style="night_studio",
        emotional_arc="Educational curiosity",
        characters=chars,
        scenes=[
            Scene(scene_number=1, speaker="boy_b", dialogue_line="Hey, did you know that an octopus has three hearts?", action="explain"),
            Scene(scene_number=2, speaker="girl_a", dialogue_line="Wait, what? Three hearts?", action="shocked"),
            Scene(scene_number=3, speaker="boy_b", dialogue_line="An octopus has one central brain.", action="explain"),
            Scene(scene_number=4, speaker="boy_b", dialogue_line="And its blood is blue.", action="explain"),
        ],
    )

    voice_map = assign_character_voices(plan, config.GEMINI_VOICES)
    assert voice_map["boy_b"] == "Puck", f"boy_b must map to Puck, got {voice_map.get('boy_b')}"
    assert voice_map["girl_a"] == "Aoede", f"girl_a must map to Aoede, got {voice_map.get('girl_a')}"

    # Also test case-insensitive / aliases
    assert voice_map.get("boy") == "Puck"
    assert voice_map.get("girl") == "Aoede"


def test_fails_when_speaker_mapped_to_wrong_voice_or_character():
    """Fails when a boy speaker receives a female voice or girl receives a male voice."""
    male_voices = {"Puck", "Fenrir", "Charon", "Enceladus", "Zephyr"}
    female_voices = {"Aoede", "Kore", "Leda"}

    chars = [
        Character(name="boy_b", visual_description="Boy with dark hoodie", voice_id="Puck"),
        Character(name="girl_a", visual_description="Girl with blonde hair", voice_id="Aoede"),
    ]
    plan = ScriptPlan(
        title="Test",
        art_style="night_studio",
        emotional_arc="Testing arcs",
        characters=chars,
        scenes=[
            Scene(scene_number=1, speaker="boy_b", dialogue_line="Line 1", action="explain"),
            Scene(scene_number=2, speaker="girl_a", dialogue_line="Line 2", action="listen"),
            Scene(scene_number=3, speaker="boy_b", dialogue_line="Line 3", action="explain"),
            Scene(scene_number=4, speaker="girl_a", dialogue_line="Line 4", action="listen"),
        ],
    )
    voice_map = assign_character_voices(plan, config.GEMINI_VOICES)

    # Validate gender/voice pairing
    assert voice_map["boy_b"] in male_voices, "boy_b must not have a female voice"
    assert voice_map["girl_a"] in female_voices, "girl_a must not have a male voice"

    # Verify character slot matching
    scene_boy = plan.scenes[0]
    cdata_boy = build_characters_data(["boy_b", "girl_a"], scene=scene_boy)
    boy_slot = [c for c in cdata_boy if c["id"] == "boy_b"][0]
    girl_slot = [c for c in cdata_boy if c["id"] == "girl_a"][0]
    assert boy_slot["is_speaker"] is True, "boy_b must be active speaker in scene 1"
    assert girl_slot["is_speaker"] is False, "girl_a must not be active speaker in scene 1"

    scene_girl = plan.scenes[1]
    cdata_girl = build_characters_data(["boy_b", "girl_a"], scene=scene_girl)
    boy_slot_2 = [c for c in cdata_girl if c["id"] == "boy_b"][0]
    girl_slot_2 = [c for c in cdata_girl if c["id"] == "girl_a"][0]
    assert girl_slot_2["is_speaker"] is True, "girl_a must be active speaker in scene 2"
    assert boy_slot_2["is_speaker"] is False, "boy_b must not be active speaker in scene 2"


def test_strip_speaker_labels():
    """Verify 'Boy:' and 'Girl:' prefixes are stripped from dialogue, kinetic words, and subtitles."""
    assert strip_speaker_label("Boy: Three hearts?") == "Three hearts?"
    assert strip_speaker_label("Girl: Wait, what?") == "Wait, what?"
    assert strip_speaker_label("boy_b: Hello world") == "Hello world"
    assert strip_speaker_label("Presenter : Welcome back") == "Welcome back"
    assert strip_speaker_label("Plain text without prefix") == "Plain text without prefix"

    # Test Scene model auto-stripping
    scene = Scene(
        scene_number=1,
        speaker="Boy:",
        dialogue_line="Boy: Hey, did you know that an octopus has three hearts?",
        action="explain",
    )
    assert scene.speaker == "Boy", f"Speaker colon should be stripped, got '{scene.speaker}'"
    assert scene.dialogue_line == "Hey, did you know that an octopus has three hearts?", f"Got '{scene.dialogue_line}'"

    # Test kinetic words stripping
    rendered_kw = KineticWordsPlugin.render(
        element_id="test-kw",
        text="Girl: Three Hearts?",
        highlight_term="Hearts",
    )
    assert "Girl:" not in rendered_kw["html"]
    assert "Three" in rendered_kw["html"]
    assert "Hearts?" in rendered_kw["html"]

    # Test escape_ass_text stripping
    sub_text = escape_ass_text("Boy: Look at this!")
    assert "Boy:" not in sub_text
    assert "Look at this!" in sub_text


def test_night_studio_subtitle_strip_clearance(tmp_path: Path):
    """Verify night_studio layout reserves a clear subtitle strip with no overlaps."""
    assert verify_subtitle_strip_clearance("night_studio") is True
    assert SUBTITLE_STRIP["top"] == 1640
    assert SUBTITLE_STRIP["bottom"] == 1860

    # Test ASS generation places subtitles within reserved strip
    plan = ScriptPlan(
        title="Sub Test",
        art_style="night_studio",
        emotional_arc="Curious",
        characters=[
            Character(name="boy_b", visual_description="Boy character in dark hoodie", voice_id="Puck"),
            Character(name="girl_a", visual_description="Girl with blonde hair", voice_id="Aoede"),
        ],
        scenes=[
            Scene(scene_number=1, speaker="boy_b", dialogue_line="An octopus has three hearts.", action="explain"),
            Scene(scene_number=2, speaker="boy_b", dialogue_line="Line 2 here.", action="explain"),
            Scene(scene_number=3, speaker="boy_b", dialogue_line="Line 3 here.", action="explain"),
            Scene(scene_number=4, speaker="boy_b", dialogue_line="Line 4 here.", action="explain"),
        ],
    )
    from toonshorts.core.models import SceneAudio
    audio = SceneAudio(
        scene_index=0,
        audio_path=tmp_path / "dummy.wav",
        duration_seconds=2.0,
        scene_total_duration=2.5,
        word_timings=[
            WordTiming(word="An", start_time=0.0, end_time=0.3),
            WordTiming(word="octopus", start_time=0.3, end_time=0.8),
            WordTiming(word="has", start_time=0.8, end_time=1.1),
            WordTiming(word="three", start_time=1.1, end_time=1.5),
            WordTiming(word="hearts.", start_time=1.5, end_time=2.0),
        ],
    )

    style_preset = {
        "name": "night_studio",
        "caption": {
            "font": "Arial",
            "font_size": 76,
            "margin_v": 120,
            "border_style": 3,
            "back_color": "&H60050811",
        },
    }
    ass_file = tmp_path / "test.ass"
    generate_ass_subtitles(plan, [audio], style_preset, ass_file)
    content = ass_file.read_text(encoding="utf-8")

    assert ",3," in content, "Should specify BorderStyle=3 (box)"
    assert "&H60050811" in content, "Should include dark translucent back_color"
    assert "MarginV" in content
    assert ",120,1" in content or "120" in content, "Should use margin_v 120"
