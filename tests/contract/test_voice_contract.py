"""Contract tests for VoiceInterface implementations."""

import pytest
from toonshorts.core.registry import list_voices, get_voice, VoiceInterface
from toonshorts.core.models import ScriptPlan, Scene, Character, Pose, CameraMove, Transition, SceneAudio, WordTiming


@pytest.fixture
def sample_plan():
    return ScriptPlan(
        title="Test Story",
        art_style="stickman",
        emotional_arc="Joyful revelation",
        characters=[
            Character(name="Pip", visual_description="Stickman with round red glasses"),
            Character(name="Zack", visual_description="Stickman with tall blue hat"),
        ],
        scenes=[
            Scene(scene_number=1, speaker="Pip", dialogue_line="Hello world from the contract test!", action="Waits", pose=Pose.IDLE, camera_move=CameraMove.STATIC, transition=Transition.CUT),
            Scene(scene_number=2, speaker="Zack", dialogue_line="This is a test of voice synthesis.", action="Nods", pose=Pose.WAVING, camera_move=CameraMove.STATIC, transition=Transition.CUT),
            Scene(scene_number=3, speaker="Pip", dialogue_line="Third scene for completeness.", action="Smiles", pose=Pose.IDLE, camera_move=CameraMove.STATIC, transition=Transition.CUT),
            Scene(scene_number=4, speaker="Zack", dialogue_line="Punchline moment!", action="Laughs", pose=Pose.LAUGHING, camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=True),
        ]
    )


@pytest.mark.parametrize("plugin_name", list_voices())
def test_voice_contract(plugin_name, sample_plan, tmp_path):
    """Every Voice plugin must fulfill the VoiceInterface contract."""
    voice = get_voice(plugin_name)
    assert isinstance(voice, VoiceInterface)
    assert voice.name == plugin_name

    scene = sample_plan.scenes[0]
    audio = voice.generate_scene_voice(0, scene, "en-US-GuyNeural", tmp_path)

    assert isinstance(audio, SceneAudio)
    assert audio.scene_index == 0
    assert audio.duration_seconds > 0.0
    assert audio.scene_total_duration >= audio.duration_seconds
    assert audio.audio_path.is_file()
    assert audio.audio_path.stat().st_size > 0
    assert len(audio.word_timings) > 0

    for timing in audio.word_timings:
        assert isinstance(timing, WordTiming)
        assert timing.start_time >= 0.0
        assert timing.end_time >= timing.start_time

    # Test batch generation
    all_audios = voice.generate_all_voices(sample_plan, tmp_path)
    assert len(all_audios) == len(sample_plan.scenes)
    for a in all_audios:
        assert a.audio_path.is_file()
