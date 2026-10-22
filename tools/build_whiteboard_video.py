"""
Tool: build_whiteboard_video.py
Renders a small test scene: a whiteboard where a title and three words
appear one by one with easing, synced to a voice clip using Anime.js and Playwright.
"""

import shutil
import sys
from pathlib import Path

# Ensure src is in python path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))

import toonshorts.plugins
from toonshorts.core import config
from toonshorts.core.registry import get_renderer
from toonshorts.plugins.render.animejs import AnimeJSRenderPlugin


def main():
    print("[1/3] Preparing synchronized speech audio clip...")
    temp_dir = config.TEMP_DIR / "whiteboard_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_dir = config.OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use the generated audio track from scratch or fallback
    audio_wav = temp_dir / "whiteboard_voice.wav"
    scratch_wav = Path("scratch/scene_0_sapi.wav")
    if scratch_wav.is_file():
        shutil.copyfile(scratch_wav, audio_wav)
    else:
        # Fallback to test_piper.wav
        piper_wav = Path("scratch/test_piper.wav")
        if piper_wav.is_file():
            shutil.copyfile(piper_wav, audio_wav)
        else:
            raise FileNotFoundError("Audio file not found in scratch directory.")

    import wave
    with wave.open(str(audio_wav), "rb") as wf:
        duration_sec = wf.getnframes() / float(wf.getframerate())

    print(f"Loaded speech audio: {audio_wav.resolve()} (Duration: {duration_sec:.2f}s)")

    # Words synchronized to speech cues
    words_data = [
        {"text": "Plan", "start_ms": 1800, "duration_ms": 550},
        {"text": "Code", "start_ms": 2800, "duration_ms": 550},
        {"text": "Ship", "start_ms": 3800, "duration_ms": 550},
    ]

    title = "WHITEBOARD ANIMATION"
    output_video = out_dir / "whiteboard_animejs_test.mp4"

    print("[2/3] Initializing Anime.js swappable renderer plugin...")
    renderer: AnimeJSRenderPlugin = get_renderer("animejs")

    print(f"[3/3] Rendering video composition to {output_video} (total duration: {duration_sec:.2f}s)...")
    renderer.render_whiteboard_video(
        title=title,
        words=words_data,
        audio_path=audio_wav,
        output_path=output_video,
        duration_sec=duration_sec,
        fps=config.VIDEO_FPS,
        temp_dir=temp_dir,
    )

    print("\n" + "=" * 60)
    print("WHITEBOARD ANIMATION RENDER COMPLETE")
    print(f"Output File: {output_video.resolve()}")
    print(f"File Size:   {output_video.stat().st_size:,} bytes")
    print("=" * 60)


if __name__ == "__main__":
    main()
