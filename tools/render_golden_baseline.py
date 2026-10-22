"""
Renders golden baseline for two-character whiteboard test (scenes 1 & 2) using cached audio.
Saves 6 frames to output/pack_tests/golden/.
Strictly protects output/What_is_an_API.mp4 and output/keep/.
"""

import json
import logging
from pathlib import Path
import subprocess

from toonshorts.core import config
from toonshorts.core.models import Character, Scene, SceneAudio
from toonshorts.plugins.render.animejs import (
    AnimeJSRenderPlugin,
    extract_whiteboard_content_and_annotations,
    resolve_scene_cast,
    build_characters_data,
)
from toonshorts.plugins.voice.gemini_tts import compute_tts_cache_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("render_golden_baseline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "pack_tests"
GOLDEN_DIR = OUTPUT_DIR / "golden"
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

PROTECTED_FILE = PROJECT_ROOT / "output" / "What_is_an_API.mp4"
PROTECTED_MTIME = PROTECTED_FILE.stat().st_mtime if PROTECTED_FILE.exists() else None


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


def run_baseline(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    fixtures_plan_file = PROJECT_ROOT / "tests" / "fixtures" / "what_is_an_api_plan.json"
    with open(fixtures_plan_file, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    test2_scenes_data = plan_data["scenes"][:2]
    characters = [
        Character(name="presenter", visual_description="Presenter", voice_id="Kore"),
        Character(name="boy_a", visual_description="Boy A", voice_id="Puck"),
    ]
    test2_scenes = [
        Scene(
            scene_number=1,
            speaker="presenter",
            dialogue_line=test2_scenes_data[0]["dialogue_line"],
            action="What is an API?: Application, Programming, Interface",
            gesture="wave",
            cast=["presenter", "boy_a"],
        ),
        Scene(
            scene_number=2,
            speaker="boy_a",
            dialogue_line=test2_scenes_data[1]["dialogue_line"],
            action="The Restaurant Setup: Customer as Client, Kitchen as Server",
            gesture="wave",
            cast=["presenter", "boy_a"],
        ),
    ]

    temp_render_dir = OUTPUT_DIR / "temp_golden_render"
    temp_render_dir.mkdir(parents=True, exist_ok=True)

    renderer = AnimeJSRenderPlugin()
    style_preset = {"gestures": "on"}

    clips = []
    audios = []
    for sc in test2_scenes:
        aud_path = get_cached_audio_for_scene(sc.dialogue_line, "Kore")
        dur = get_audio_duration(aud_path)
        scene_audio = SceneAudio(
            scene_index=sc.scene_number - 1,
            audio_path=aud_path,
            duration_seconds=dur,
            scene_total_duration=dur,
            word_timings=[],
        )
        audios.append(scene_audio)

        clip_path = temp_render_dir / f"animejs_scene_{sc.scene_number}.mp4"
        title, words, annotations = extract_whiteboard_content_and_annotations(
            sc, scene_audio.scene_total_duration, scene_audio.word_timings
        )
        scene_gesture = getattr(sc, "gesture", None) or "idle"
        scene_cast = resolve_scene_cast(sc, characters)
        characters_data = build_characters_data(
            scene_cast,
            scene=sc,
            style_preset=style_preset,
        )
        renderer.render_whiteboard_video(
            title=title,
            words=words,
            audio_path=scene_audio.audio_path,
            output_path=clip_path,
            duration_sec=scene_audio.scene_total_duration,
            gesture=scene_gesture,
            fps=config.VIDEO_FPS,
            temp_dir=temp_render_dir / f"scene_{sc.scene_number}_tmp",
            scene_number=sc.scene_number,
            annotations=annotations,
            characters_data=characters_data,
        )
        clips.append(clip_path)

    # Extract 6 frames
    s1_dur = audios[0].scene_total_duration
    extract_frame(clips[0], 0.1, target_dir / "test2_s1_start.png")
    extract_frame(clips[0], s1_dur / 2.0, target_dir / "test2_s1_mid.png")
    extract_frame(clips[0], max(0.1, s1_dur - 0.2), target_dir / "test2_s1_end.png")

    s2_dur = audios[1].scene_total_duration
    extract_frame(clips[1], 0.1, target_dir / "test2_s2_start.png")
    extract_frame(clips[1], s2_dur / 2.0, target_dir / "test2_s2_mid.png")
    extract_frame(clips[1], max(0.1, s2_dur - 0.2), target_dir / "test2_s2_end.png")

    if PROTECTED_FILE.exists():
        assert PROTECTED_FILE.stat().st_mtime == PROTECTED_MTIME, "CRITICAL ERROR: output/What_is_an_API.mp4 modified!"

    logger.info("Successfully extracted 6 frames to %s", target_dir)


if __name__ == "__main__":
    run_baseline(GOLDEN_DIR)
