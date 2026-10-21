"""Contract tests for VoiceInterface implementations using a fake plugin and registered plugins."""

import pytest
import wave
from toonshorts.core.registry import list_voices, get_voice, VoiceInterface, register_voice
from toonshorts.core.models import ScriptPlan, Scene, Character, Pose, CameraMove, Transition, SceneAudio, WordTiming
from toonshorts.core.errors import VoiceError


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


def test_fake_voice_contract(sample_plan, tmp_path):
    """Fake voice plugin must satisfy the VoiceInterface contract completely."""
    voice = get_voice("fake")
    assert isinstance(voice, VoiceInterface)
    assert voice.name == "fake"

    scene = sample_plan.scenes[0]
    audio = voice.generate_scene_voice(0, scene, "mock_voice_a", tmp_path)

    assert isinstance(audio, SceneAudio)
    assert audio.scene_index == 0
    assert audio.duration_seconds > 0.0
    assert audio.scene_total_duration >= audio.duration_seconds
    assert audio.audio_path.is_file()
    assert audio.audio_path.stat().st_size > 0
    assert len(audio.word_timings) > 0

    # Verify audio is 16-bit WAV
    with wave.open(str(audio.audio_path), "rb") as wf:
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 24000

    for timing in audio.word_timings:
        assert isinstance(timing, WordTiming)
        assert timing.start_time >= 0.0
        assert timing.end_time >= timing.start_time

    # Test batch generation
    all_audios = voice.generate_all_voices(sample_plan, tmp_path)
    assert len(all_audios) == len(sample_plan.scenes)
    for a in all_audios:
        assert a.audio_path.is_file()


def test_custom_mock_voice_plugin_contract(sample_plan, tmp_path):
    """Tests that any custom plugin implementing VoiceInterface adheres to contract."""
    @register_voice("contract_test_mock")
    class MockCustomVoice(VoiceInterface):
        name = "contract_test_mock"

        def generate_scene_voice(self, scene_index, scene, voice_name, temp_dir, pause_seconds=0.35):
            from toonshorts.plugins.voice.fake import _write_fake_speech_wav
            out = temp_dir / f"test_{scene_index}.wav"
            dur = _write_fake_speech_wav(out, scene.dialogue_line)
            return SceneAudio(
                scene_index=scene_index,
                audio_path=out,
                duration_seconds=dur,
                scene_total_duration=dur + pause_seconds,
                word_timings=[WordTiming(word="test", start_time=0.0, end_time=dur)],
            )

        def generate_all_voices(self, plan, temp_dir):
            return [self.generate_scene_voice(i, s, "v", temp_dir) for i, s in enumerate(plan.scenes)]

    custom = get_voice("contract_test_mock")
    assert isinstance(custom, VoiceInterface)
    audio = custom.generate_scene_voice(0, sample_plan.scenes[0], "v", tmp_path)
    assert audio.audio_path.is_file()
