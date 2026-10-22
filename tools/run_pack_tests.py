"""
Acceptance test script for 2D character packs in Whiteboard renderer:
1. Test 1: Original whiteboard plan with Presenter alone (scenes 1 & 2) using cached audio.
2. Test 2: Two characters (Presenter on left, Boy A on right, facing each other) with gestures, speaker mouth sync, and listener blinking.
3. Extracts frames (start, middle, end) and face crops into output/pack_tests/frames/.
4. Strictly protects output/What_is_an_API.mp4.
"""

import json
import logging
import os
from pathlib import Path
import subprocess
from PIL import Image

from toonshorts.core import config
from toonshorts.core.models import Character, Scene, ScriptPlan, SceneAudio, WordTiming
from toonshorts.plugins.render.animejs import AnimeJSRenderPlugin
from toonshorts.plugins.voice.gemini_tts import compute_tts_cache_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_pack_tests")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "pack_tests"
FRAMES_DIR = OUTPUT_DIR / "frames"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# 0. Protection check
protected_file = PROJECT_ROOT / "output" / "What_is_an_API.mp4"
protected_initial_mtime = protected_file.stat().st_mtime if protected_file.exists() else None

def get_cached_audio_for_scene(dialogue: str, voice: str = "Kore") -> Path:
    key = compute_tts_cache_key(dialogue, voice, config.TTS_MODEL_NAME)
    audio_path = PROJECT_ROOT / "cache" / "tts" / f"{key}.wav"
    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio cache miss for dialogue: {dialogue} (key: {key})")
    return audio_path


def get_audio_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def extract_frame(video_path: Path, time_sec: float, out_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{time_sec:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def main():
    renderer = AnimeJSRenderPlugin()
    fixtures_plan_file = PROJECT_ROOT / "tests" / "fixtures" / "what_is_an_api_plan.json"
    with open(fixtures_plan_file, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    # -------------------------------------------------------------
    # Test 1: Original Whiteboard Plan with Presenter Alone
    # -------------------------------------------------------------
    logger.info("=== Running Test 1: Presenter Alone (Original Plan) ===")
    test1_scenes_data = plan_data["scenes"][:4]
    test1_scenes = [Scene(**s) for s in test1_scenes_data]
    test1_characters = [Character(**c) for c in plan_data["characters"]]
    test1_plan = ScriptPlan(
        title="Test1_Presenter_Solo",
        art_style="whiteboard",
        emotional_arc=plan_data.get("emotional_arc", "Clear informative revelation through fun metaphor"),
        characters=test1_characters,
        scenes=test1_scenes,
    )

    test1_audios = []
    for i, sc in enumerate(test1_scenes):
        aud_path = get_cached_audio_for_scene(sc.dialogue_line, "Kore")
        dur = get_audio_duration(aud_path)
        test1_audios.append(SceneAudio(
            scene_index=i,
            audio_path=aud_path,
            duration_seconds=dur,
            scene_total_duration=dur,
            word_timings=[],
        ))

    test1_out_dir = OUTPUT_DIR / "test1_temp"
    test1_clips = renderer.render_all_scenes(
        plan=test1_plan,
        style_preset={"gestures": "on"},
        temp_dir=test1_out_dir,
        scene_audios=test1_audios,
    )

    test1_video = OUTPUT_DIR / "test1_presenter_solo.mp4"
    # Concatenate clips
    concat_list_file = test1_out_dir / "concat.txt"
    concat_list_file.write_text("\n".join([f"file '{c.resolve().as_posix()}'" for c in test1_clips]), encoding="utf-8")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(test1_video)
    ], capture_output=True, check=True)
    logger.info("Test 1 completed: %s", test1_video)

    # Extract Test 1 frames (start, middle, end for scene 1 and scene 2)
    s1_dur = test1_audios[0].scene_total_duration
    extract_frame(test1_clips[0], 0.1, FRAMES_DIR / "test1_s1_start.png")
    extract_frame(test1_clips[0], s1_dur / 2.0, FRAMES_DIR / "test1_s1_mid.png")
    extract_frame(test1_clips[0], max(0.1, s1_dur - 0.2), FRAMES_DIR / "test1_s1_end.png")

    s2_dur = test1_audios[1].scene_total_duration
    extract_frame(test1_clips[1], 0.1, FRAMES_DIR / "test1_s2_start.png")
    extract_frame(test1_clips[1], s2_dur / 2.0, FRAMES_DIR / "test1_s2_mid.png")
    extract_frame(test1_clips[1], max(0.1, s2_dur - 0.2), FRAMES_DIR / "test1_s2_end.png")

    # -------------------------------------------------------------
    # Test 2: Two Characters (Presenter Left, Boy A Right)
    # -------------------------------------------------------------
    logger.info("=== Running Test 2: Two Characters (Presenter + Boy A) ===")
    test2_scenes = [
        Scene(
            scene_number=1,
            speaker="presenter",
            dialogue_line=test1_scenes_data[0]["dialogue_line"],
            action="What is an API?: Application, Programming, Interface",
            gesture="wave",
            cast=["presenter", "boy_a"],
        ),
        Scene(
            scene_number=2,
            speaker="boy_a",
            dialogue_line=test1_scenes_data[1]["dialogue_line"],
            action="The Restaurant Setup: Customer as Client, Kitchen as Server",
            gesture="wave",  # Unsupported by boy_a, triggers fallback to idle and warning log!
            cast=["presenter", "boy_a"],
        ),
        Scene(
            scene_number=3,
            speaker="presenter",
            dialogue_line=test1_scenes_data[2]["dialogue_line"],
            action="The Waiter in Action: Sends Order, Connects Systems",
            gesture="point",
            cast=["presenter", "boy_a"],
        ),
        Scene(
            scene_number=4,
            speaker="boy_a",
            dialogue_line=test1_scenes_data[3]["dialogue_line"],
            action="Everyday Examples: Weather Apps, Ride Sharing",
            gesture="idle",
            cast=["presenter", "boy_a"],
        ),
    ]
    test2_plan = ScriptPlan(
        title="Test2_Two_Characters",
        art_style="whiteboard",
        emotional_arc="Engaging banter between presenter and curious boy",
        characters=[
            Character(name="presenter", visual_description="Presenter", voice_id="Kore"),
            Character(name="boy_a", visual_description="Boy A", voice_id="Puck"),
        ],
        scenes=test2_scenes,
    )

    test2_audios = [
        SceneAudio(
            scene_index=i,
            audio_path=test1_audios[i].audio_path,
            duration_seconds=test1_audios[i].duration_seconds,
            scene_total_duration=test1_audios[i].scene_total_duration,
            word_timings=[],
        )
        for i in range(4)
    ]

    test2_out_dir = OUTPUT_DIR / "test2_temp"
    test2_clips = renderer.render_all_scenes(
        plan=test2_plan,
        style_preset={"gestures": "on"},
        temp_dir=test2_out_dir,
        scene_audios=test2_audios,
    )

    test2_video = OUTPUT_DIR / "test2_two_characters.mp4"
    concat_list_file2 = test2_out_dir / "concat.txt"
    concat_list_file2.write_text("\n".join([f"file '{c.resolve().as_posix()}'" for c in test2_clips]), encoding="utf-8")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file2),
        "-c", "copy",
        str(test2_video)
    ], capture_output=True, check=True)
    logger.info("Test 2 completed: %s", test2_video)

    # Extract Test 2 frames (start, middle, end for scene 1 and scene 2)
    t2_s1_dur = test2_audios[0].scene_total_duration
    extract_frame(test2_clips[0], 0.1, FRAMES_DIR / "test2_s1_start.png")
    extract_frame(test2_clips[0], t2_s1_dur / 2.0, FRAMES_DIR / "test2_s1_mid.png")
    extract_frame(test2_clips[0], max(0.1, t2_s1_dur - 0.2), FRAMES_DIR / "test2_s1_end.png")

    t2_s2_dur = test2_audios[1].scene_total_duration
    extract_frame(test2_clips[1], 0.1, FRAMES_DIR / "test2_s2_start.png")
    extract_frame(test2_clips[1], t2_s2_dur / 2.0, FRAMES_DIR / "test2_s2_mid.png")
    extract_frame(test2_clips[1], max(0.1, t2_s2_dur - 0.2), FRAMES_DIR / "test2_s2_end.png")

    # Zoomed Face Crops from test2_s1_mid.png (mid animation)
    img_mid = Image.open(FRAMES_DIR / "test2_s1_mid.png")
    # Presenter face (left slot): x: 180..420, y: 700..960
    crop_presenter = img_mid.crop((180, 700, 420, 960))
    crop_presenter.save(FRAMES_DIR / "test2_crop_presenter_face.png")

    # Boy A face (right slot): x: 660..900, y: 700..960
    crop_boy = img_mid.crop((660, 700, 900, 960))
    crop_boy.save(FRAMES_DIR / "test2_crop_boy_a_face.png")

    logger.info("Cropped face images generated successfully.")

    # 0. Verify protected file was untouched
    if protected_file.exists():
        final_mtime = protected_file.stat().st_mtime
        assert final_mtime == protected_initial_mtime, "CRITICAL ERROR: output/What_is_an_API.mp4 was modified!"
        logger.info("Protected file output/What_is_an_API.mp4 verified untouched.")

    print("\nALL ACCEPTANCE RENDERS COMPLETE:")
    print(f"Test 1 Video: {test1_video}")
    print(f"Test 2 Video: {test2_video}")
    print(f"Frames saved to: {FRAMES_DIR}")

if __name__ == "__main__":
    main()
