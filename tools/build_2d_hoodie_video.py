"""
Purpose: End-to-end 2D animated comedy short video generator for the layered hoodie character.
Inputs: Character reference sheet (assets/sources/incoming/sheet_03.png), layout JSON, Piper voice model.
Outputs: output/renders2d/hoodie_comedy_short.mp4, stills, and audio master.
Depends on: core.character2d, core.audio_effects, core.config, core.subtitles, numpy, wave, subprocess
Used by: User verification, 2D pipeline
Config keys: None
Tests: tests/unit/test_character2d.py
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from toonshorts.core.audio_effects import create_synthesized_sfx
from toonshorts.core.character2d import (
    compute_action_pose,
    get_character,
    render_scene_frame,
    slice_character_sheet,
)
from toonshorts.core.config import PROJECT_ROOT
from toonshorts.core.subtitles import escape_ass_text, format_ass_time

OUTPUT_DIR = PROJECT_ROOT / "output" / "renders2d"
HOODIE_RUN_DIR = OUTPUT_DIR / "hoodie_video"
FRAMES_DIR = HOODIE_RUN_DIR / "frames"
STILLS_DIR = HOODIE_RUN_DIR / "stills"
AUDIO_DIR = HOODIE_RUN_DIR / "audio"

FPS = 24

# Script beats for comedy short
BEATS = [
    {
        "id": "beat1_intro",
        "action": "wave",
        "base_emotion": "smirk",
        "speed": 1.0,
        "intensity": 1.0,
        "text": "People always ask me: 'Bro, why a sleeveless hoodie? Isn't that an oxymoron?!'",
        "length_scale": 0.88,
    },
    {
        "id": "beat2_walk",
        "action": "walk",
        "base_emotion": "happy",
        "speed": 1.2,
        "intensity": 1.1,
        "text": "Like, is my core freezing cold, while my biceps are in tropical vacation mode?!",
        "length_scale": 0.86,
    },
    {
        "id": "beat3_panic",
        "action": "idle",
        "base_emotion": "shocked",
        "speed": 2.2,  # Faster shivering/breathing
        "intensity": 1.4,
        "text": "And what if it starts raining?! Do my forearms just absorb the entire thunderstorm?!",
        "length_scale": 0.84,
    },
    {
        "id": "beat4_jump",
        "action": "jump",
        "base_emotion": "shocked",
        "speed": 0.7,  # Slowed jump cycle to span the phrase
        "intensity": 1.3,
        "text": "Fashion makes zero meteorological sense! Somebody please send sleeves!",
        "length_scale": 0.84,
    },
]


def ensure_character():
    """Slices or retrieves the stick_hoodie character from the reference sheet."""
    sheet_path = PROJECT_ROOT / "assets" / "sources" / "incoming" / "sheet_03.png"
    layout_path = PROJECT_ROOT / "assets2d" / "layouts" / "sheet_03_layout.json"

    print("Checking character in registry...")
    char = get_character("stick_hoodie")
    if isinstance(char, dict) and char.get("status") in ("missing", "error"):
        print("Slicing stick_hoodie from reference sheet...")
        char = slice_character_sheet(sheet_path, layout_path, "stick_hoodie")
    print(f"Character ready: {char.name} ({len(char.parts)} parts, {len(char.expressions)} expressions)")
    return char


def generate_speech_and_sfx() -> tuple[list[dict], Path, int]:
    """Generates speech lines via Piper TTS and cartoon sound effects, then mixes master audio."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    piper_bin = shutil.which("piper")
    model_path = PROJECT_ROOT / "assets" / "voices" / "piper" / "en_US-lessac-medium.onnx"
    config_path = PROJECT_ROOT / "assets" / "voices" / "piper" / "en_US-lessac-medium.onnx.json"

    if not piper_bin or not model_path.is_file():
        raise RuntimeError("Piper TTS or en_US-lessac-medium.onnx voice model not found!")

    sample_rate = 22050
    current_time = 0.5  # 0.5s pause before first dialogue line

    for beat in BEATS:
        wav_path = AUDIO_DIR / f"{beat['id']}.wav"
        cmd = [
            piper_bin,
            "-m", str(model_path),
            "-c", str(config_path),
            "-f", str(wav_path),
            "--length-scale", str(beat["length_scale"]),
        ]
        res = subprocess.run(cmd, input=beat["text"].encode("utf-8"), capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(f"Piper TTS failed: {res.stderr.decode('utf-8')}")

        with wave.open(str(wav_path), "rb") as wf:
            dur = wf.getnframes() / float(wf.getframerate())
            sample_rate = wf.getframerate()
            beat["wav_path"] = wav_path
            beat["duration"] = dur
            beat["start_time"] = current_time
            beat["end_time"] = current_time + dur
            print(f"  {beat['id']}: [{current_time:.2f}s - {beat['end_time']:.2f}s] ({dur:.2f}s)")
            current_time = beat["end_time"] + 0.45  # 0.45s pause between comedy beats

    total_duration = current_time + 0.6  # 0.6s outro padding
    total_samples = int(total_duration * sample_rate)
    master_audio = np.zeros(total_samples, dtype=np.float32)

    # 1. Add dialogue audio
    for beat in BEATS:
        with wave.open(str(beat["wav_path"]), "rb") as wf:
            n_frames = wf.getnframes()
            samples = np.frombuffer(wf.readframes(n_frames), dtype=np.int16).astype(np.float32) / 32768.0

        s0 = int(beat["start_time"] * sample_rate)
        s1 = min(total_samples, s0 + len(samples))
        master_audio[s0:s1] += samples[: s1 - s0]

    # 2. Add synthesized cartoon sound effects: "boing" on beat4 jump start, "pop" on landing
    beat4 = BEATS[3]
    boing_wav = AUDIO_DIR / "sfx_boing.wav"
    pop_wav = AUDIO_DIR / "sfx_pop.wav"
    create_synthesized_sfx("boing", boing_wav)
    create_synthesized_sfx("pop", pop_wav)

    for sfx_path, sfx_time in [
        (boing_wav, beat4["start_time"] + 0.2),
        (pop_wav, beat4["start_time"] + beat4["duration"] * 0.75),
    ]:
        with wave.open(str(sfx_path), "rb") as wf:
            sfx_samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            # Resample if sample rate differs
            sfx_sr = wf.getframerate()
            if sfx_sr != sample_rate:
                indices = np.round(np.arange(0, len(sfx_samples), sfx_sr / sample_rate)).astype(int)
                indices = indices[indices < len(sfx_samples)]
                sfx_samples = sfx_samples[indices]

            s0 = int(sfx_time * sample_rate)
            s1 = min(total_samples, s0 + len(sfx_samples))
            if s1 > s0:
                master_audio[s0:s1] += sfx_samples[: s1 - s0] * 0.45

    # Normalize audio
    peak = np.max(np.abs(master_audio))
    if peak > 0.95:
        master_audio *= 0.95 / peak

    master_path = HOODIE_RUN_DIR / "master_audio.wav"
    int16_audio = (master_audio * 32767.0).astype(np.int16)
    with wave.open(str(master_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_audio.tobytes())

    print(f"Master audio created: {master_path} (Duration: {total_duration:.2f}s, {total_samples} samples)")
    return BEATS, master_path, sample_rate


def generate_subtitles(beats: list[dict], ass_path: Path):
    """Generates vibrant YouTube Shorts ASS subtitles."""
    header = """[Script Info]
Title: The Sleeveless Hoodie Paradox
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,58,&H0000FFFF,&H000000FF,&H00111111,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for beat in beats:
        t0 = format_ass_time(beat["start_time"])
        t1 = format_ass_time(beat["end_time"] + 0.15)
        escaped_txt = escape_ass_text(beat["text"])
        events.append(f"Dialogue: 0,{t0},{t1},Caption,,0,0,0,,{escaped_txt}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"ASS subtitles saved: {ass_path}")


def render_all_frames(char, beats: list[dict], master_path: Path, sample_rate: int) -> int:
    """Renders all 1080x1920 video frames driven by skeletal animation and audio loudness."""
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    STILLS_DIR.mkdir(parents=True, exist_ok=True)

    with wave.open(str(master_path), "rb") as wf:
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        audio_data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    total_duration = len(audio_data) / float(sample_rate)
    total_frames = int(math.ceil(total_duration * FPS))
    print(f"Rendering {total_frames} frames ({total_duration:.2f}s at {FPS} FPS)...")

    # Clean existing frames
    for old_frame in FRAMES_DIR.glob("frame_*.png"):
        old_frame.unlink()

    stills_to_save = [
        int(beats[0]["start_time"] * FPS + 10),
        int(beats[1]["start_time"] * FPS + 15),
        int(beats[2]["start_time"] * FPS + 15),
        int(beats[3]["start_time"] * FPS + 18),
    ]

    for f in range(total_frames):
        t_sec = f / float(FPS)

        # 1. Determine active beat
        active_beat = beats[0]
        for b in beats:
            if t_sec >= b["start_time"] - 0.2:
                active_beat = b

        action = active_beat["action"]
        speed = active_beat["speed"]
        intensity = active_beat["intensity"]
        base_emotion = active_beat["base_emotion"]

        # 2. Compute loudness for current frame
        f_sample_start = int(t_sec * sample_rate)
        f_sample_end = min(len(audio_data), int((t_sec + (1.0 / FPS)) * sample_rate))
        chunk = audio_data[f_sample_start:f_sample_end]
        rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0

        # Normalization factor for speech loudness
        loudness = min(1.0, rms * 4.5)

        # Subtle natural eye blinking
        blink = (f % 60) in (0, 1)

        # Compute skeletal pose
        beat_local_t = max(0.0, t_sec - active_beat["start_time"])
        pose = compute_action_pose(
            action=action,
            t=beat_local_t,
            intensity=intensity,
            speed=speed,
            root_x=540.0,
            root_y=1260.0,
            loudness=loudness,
            blink=blink,
            base_emotion=base_emotion,
        )

        frame_img = render_scene_frame(char, pose, width=1080, height=1920, character_scale=1.58)

        frame_path = FRAMES_DIR / f"frame_{f:04d}.png"
        frame_img.save(frame_path)

        if f in stills_to_save:
            still_path = STILLS_DIR / f"still_{f:04d}_{action}.png"
            frame_img.save(still_path)

        if f % 40 == 0 or f == total_frames - 1:
            print(f"  Frame {f}/{total_frames} ({(f/total_frames)*100:.1f}%) [Action: {action}, Face: {pose.face_name}]")

    print(f"All {total_frames} frames rendered successfully!")
    return total_frames


def assemble_final_video(master_audio: Path, ass_path: Path) -> Path:
    """Assembles final vertical MP4 short via FFmpeg with burned ASS captions."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg executable not found in PATH!")

    output_mp4 = OUTPUT_DIR / "hoodie_comedy_short.mp4"
    if output_mp4.exists():
        output_mp4.unlink()

    # Run FFmpeg from HOODIE_RUN_DIR so ass_path.name has no path escaping issues
    cmd = [
        ffmpeg_bin,
        "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "frame_%04d.png"),
        "-i", str(master_audio),
        "-vf", f"subtitles={ass_path.name}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_mp4),
    ]

    print(f"Executing FFmpeg assembly: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(HOODIE_RUN_DIR), capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg assembly failed: {res.stderr.decode('utf-8', errors='ignore')}")

    print(f"\n=======================================================")
    print(f"  SUCCESS! Video generated at: {output_mp4}")
    print(f"  File size: {output_mp4.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"=======================================================\n")
    return output_mp4


def main():
    print("=== ToonShorts 2D Hoodie Comedy Video Generator ===")
    char = ensure_character()
    beats, master_audio, sample_rate = generate_speech_and_sfx()
    ass_path = HOODIE_RUN_DIR / "captions.ass"
    generate_subtitles(beats, ass_path)
    render_all_frames(char, beats, master_audio, sample_rate)
    video_path = assemble_final_video(master_audio, ass_path)
    return video_path


if __name__ == "__main__":
    main()
