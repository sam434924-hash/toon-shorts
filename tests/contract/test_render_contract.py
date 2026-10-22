"""Contract tests for RenderInterface implementations."""

import pytest
from PIL import Image
from toonshorts.core.registry import list_renderers, get_renderer, RenderInterface
from toonshorts.core.models import ScriptPlan, Scene, Character, Pose, CameraMove, Transition
from toonshorts.core.pipeline import load_style_preset


@pytest.fixture
def sample_plan():
    return ScriptPlan(
        title="Render Test Story",
        art_style="stickman",
        emotional_arc="Excitement",
        characters=[
            Character(name="Pip", visual_description="Stickman with round red glasses"),
            Character(name="Zack", visual_description="Stickman with tall blue hat"),
        ],
        scenes=[
            Scene(scene_number=1, speaker="Pip", dialogue_line="Scene one visual.", action="Action 1", pose=Pose.IDLE, camera_move=CameraMove.STATIC, transition=Transition.CUT),
            Scene(scene_number=2, speaker="Zack", dialogue_line="Scene two visual.", action="Action 2", pose=Pose.WAVING, camera_move=CameraMove.STATIC, transition=Transition.CUT),
            Scene(scene_number=3, speaker="Pip", dialogue_line="Scene three visual.", action="Action 3", pose=Pose.SHOCKED, camera_move=CameraMove.STATIC, transition=Transition.CUT),
            Scene(scene_number=4, speaker="Zack", dialogue_line="Scene four punchline.", action="Action 4", pose=Pose.LAUGHING, camera_move=CameraMove.STATIC, transition=Transition.CUT, is_punchline=True),
        ]
    )


def _get_render_params():
    params = []
    for r in list_renderers():
        if r in ("animejs", "blender3d"):
            params.append(pytest.param(r, marks=pytest.mark.slow))
        else:
            params.append(r)
    return params


@pytest.mark.parametrize("plugin_name", _get_render_params())
def test_render_contract(plugin_name, sample_plan, tmp_path):
    """Every Render plugin must fulfill the RenderInterface contract."""
    renderer = get_renderer(plugin_name)
    assert isinstance(renderer, RenderInterface)
    assert renderer.name == plugin_name

    preset = load_style_preset("stickman")
    scene = sample_plan.scenes[0]
    out_img = tmp_path / f"test_render_{plugin_name}.png"

    result_path = renderer.render_scene(scene, sample_plan.characters, preset, out_img, tmp_path)
    assert result_path.is_file()
    assert result_path.stat().st_size > 0

    # Verify image dimensions
    with Image.open(result_path) as img:
        assert img.size == (1080, 1920)

    # Test batch generation
    batch_images = renderer.render_all_scenes(sample_plan, preset, tmp_path)
    assert len(batch_images) == len(sample_plan.scenes)
    for p in batch_images:
        assert p.is_file()
