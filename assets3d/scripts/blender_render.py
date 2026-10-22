"""
Purpose: Production headless Blender rendering script for ToonShorts (RobotExpressive 3D).
Inputs: JSON configuration file passed via command line specifying action, camera, and resolution.
Outputs: Rendered PNG frames of the 3D RobotExpressive character.
"""

import sys
import os
import json
import math
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None


ACTION_NAME_MAP = {
    "dance": "Dance",
    "death": "Death",
    "idle": "Idle",
    "jump": "Jump",
    "no": "No",
    "punch": "Punch",
    "running": "Running",
    "run": "Running",
    "sitting": "Sitting",
    "sit": "Sitting",
    "standing": "Standing",
    "stand": "Standing",
    "thumbsup": "ThumbsUp",
    "thumbs_up": "ThumbsUp",
    "walking": "Walking",
    "walk": "Walking",
    "walkjump": "WalkJump",
    "wave": "Wave",
    "yes": "Yes",
}


def render_robot_scene(config_path: Path):
    with open(config_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    output_dir = Path(payload.get("output_dir", "."))
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_prefix = payload.get("frame_prefix", "frame")

    resolution = payload.get("resolution", [540, 960])
    action_key = payload.get("action", "idle").lower().strip()
    target_action_name = ACTION_NAME_MAP.get(action_key, "Idle")
    render_single_frame = payload.get("render_single_frame", 15)

    # 1. Reset factory scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    # 2. Import RobotExpressive.glb
    project_root = Path(__file__).resolve().parents[2]
    model_path = project_root / "assets3d" / "models" / "RobotExpressive.glb"
    if not model_path.is_file():
        raise FileNotFoundError(f"Robot model not found at {model_path}")

    bpy.ops.import_scene.gltf(filepath=str(model_path))

    # 3. Locate Armature and apply action
    armature = None
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            armature = obj
            break

    if armature and armature.animation_data and bpy.data.actions:
        action = bpy.data.actions.get(target_action_name)
        if not action:
            # Fallback to case-insensitive match
            for act in bpy.data.actions:
                if act.name.lower() == target_action_name.lower():
                    action = act
                    break
        if action:
            armature.animation_data.action = action

    # 4. Set frame
    frame_num = render_single_frame if render_single_frame is not None else 15
    scene.frame_set(frame_num)

    # 5. Add Camera
    cam_data = bpy.data.cameras.new("RobotCamera")
    cam_data.lens = 50
    cam_obj = bpy.data.objects.new("RobotCamera", cam_data)
    scene.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -3.2, 1.1)
    cam_obj.rotation_euler = (math.radians(85), 0, 0)
    scene.camera = cam_obj

    # 6. Add Clean 3-Point Lighting
    # Key Light (Sun)
    key_light = bpy.data.lights.new("KeyLight", type="SUN")
    key_light.energy = 3.5
    key_obj = bpy.data.objects.new("KeyLight", key_light)
    scene.collection.objects.link(key_obj)
    key_obj.location = (2.0, -2.5, 3.5)
    key_obj.rotation_euler = (math.radians(45), math.radians(20), math.radians(30))

    # Fill Light (Sun, softer)
    fill_light = bpy.data.lights.new("FillLight", type="SUN")
    fill_light.energy = 1.5
    fill_obj = bpy.data.objects.new("FillLight", fill_light)
    scene.collection.objects.link(fill_obj)
    fill_obj.location = (-2.0, -2.5, 2.0)
    fill_obj.rotation_euler = (math.radians(45), math.radians(-30), math.radians(-30))

    # 7. Render output frame
    out_file = output_dir / f"{frame_prefix}_{frame_num:04d}.png"
    scene.render.filepath = str(out_file)
    bpy.ops.render.render(write_still=True)


def main():
    if "--" not in sys.argv:
        print("Usage: blender -b --python blender_render.py -- <config_json>")
        sys.exit(1)
    config_arg = sys.argv[sys.argv.index("--") + 1]
    render_robot_scene(Path(config_arg))


if __name__ == "__main__":
    main()
