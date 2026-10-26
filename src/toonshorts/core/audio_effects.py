"""
Purpose: Royalty-free sound effect generation for comedic punchlines.
Inputs: SFX identifiers (boing, whistle, pop, click, whoosh, task_complete) and destination paths.
Outputs: Synthesized standalone cartoon sound effect WAV files.
Depends on: math, pathlib, struct, typing, wave, core.library
Used by: core.assembler
Config keys: None
Tests: tests/unit/test_timing.py
"""

import math
import wave
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional

from toonshorts.core.library import get_or_create_sfx, copy_library_asset


def create_synthesized_sfx(sfx_type: str, output_path: Path):
    """Generates clean standalone cartoon sound effect WAV files without external assets."""
    sample_rate = 44100

    if sfx_type == "boing":
        duration = 0.35
        num_samples = int(duration * sample_rate)
        raw = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            freq = 150.0 + 350.0 * (t / duration) + 35.0 * math.sin(2.0 * math.pi * 18.0 * t)
            decay = math.exp(-3.5 * t)
            val = int(decay * 16000.0 * math.sin(2.0 * math.pi * freq * t))
            raw.extend(struct.pack("<h", max(-32767, min(32767, val))))
    elif sfx_type == "whistle":
        duration = 0.30
        num_samples = int(duration * sample_rate)
        raw = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            freq = 900.0 + 800.0 * (t / duration)
            decay = math.sin(math.pi * (t / duration))
            val = int(decay * 14000.0 * math.sin(2.0 * math.pi * freq * t))
            raw.extend(struct.pack("<h", max(-32767, min(32767, val))))
    elif sfx_type == "click":
        duration = 0.04
        num_samples = int(duration * sample_rate)
        raw = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            decay = math.exp(-70.0 * t)
            val = int(decay * 16000.0 * math.sin(2.0 * math.pi * 1800.0 * t))
            raw.extend(struct.pack("<h", max(-32767, min(32767, val))))
    elif sfx_type == "whoosh":
        duration = 0.35
        num_samples = int(duration * sample_rate)
        raw = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            env = math.sin(math.pi * (t / duration)) ** 2
            freq = 250.0 + 550.0 * (t / duration)
            noise = (math.sin(2.0 * math.pi * freq * t) + 0.3 * math.sin(2.0 * math.pi * (freq * 1.5) * t))
            val = int(env * 12000.0 * noise)
            raw.extend(struct.pack("<h", max(-32767, min(32767, val))))
    elif sfx_type in ("task_complete", "task-complete", "complete", "bell"):
        duration = 0.45
        num_samples = int(duration * sample_rate)
        raw = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            decay1 = math.exp(-8.0 * t)
            decay2 = math.exp(-6.0 * max(0.0, t - 0.12)) if t >= 0.12 else 0.0
            tone1 = math.sin(2.0 * math.pi * 523.25 * t) * decay1
            tone2 = math.sin(2.0 * math.pi * 783.99 * (t - 0.12)) * decay2 if t >= 0.12 else 0.0
            val = int((tone1 + tone2) * 14000.0)
            raw.extend(struct.pack("<h", max(-32767, min(32767, val))))
    else:  # pop / ding
        duration = 0.15
        num_samples = int(duration * sample_rate)
        raw = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            freq = 950.0 * math.exp(-12.0 * t) + 120.0
            decay = math.exp(-18.0 * t)
            val = int(decay * 22000.0 * math.sin(2.0 * math.pi * freq * t))
            raw.extend(struct.pack("<h", max(-32767, min(32767, val))))

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw)


def create_ambient_bg_music(duration_sec: float, output_path: Path):
    """Generates quiet ambient lo-fi synth chord progression without external assets."""
    sample_rate = 44100
    num_samples = int(max(1.0, duration_sec) * sample_rate)
    raw = bytearray()
    chord_dur = 4.0
    chords = [
        [261.63, 329.63, 392.00, 523.25],  # C
        [196.00, 246.94, 293.66, 392.00],  # G
        [220.00, 261.63, 329.63, 440.00],  # Am
        [174.61, 220.00, 261.63, 349.23],  # F
    ]
    for i in range(num_samples):
        t = float(i) / sample_rate
        c_idx = int(t / chord_dur) % len(chords)
        chord = chords[c_idx]
        t_chord = t % chord_dur
        env = math.sin(math.pi * (t_chord / chord_dur)) ** 0.5
        sig = 0.0
        for f in chord:
            sig += math.sin(2.0 * math.pi * f * t) + 0.15 * math.sin(4.0 * math.pi * f * t)
        val = int(env * sig * 650.0)  # ~-25dB
        raw.extend(struct.pack("<h", max(-32767, min(32767, val))))

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw)


def prepare_sound_effects(
    temp_dir: Path,
    library_tracker: Optional[List[str]] = None,
) -> Dict[str, Path]:
    """Generates standard comedic sound effect library in temp dir using shared library cache."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    sfx_map = {}
    for name in ["pop", "boing", "whistle", "click", "whoosh", "task_complete", "bell"]:
        dest_path = temp_dir / f"sfx_{name}.wav"
        lib_path, is_hit = get_or_create_sfx(name, lambda p: create_synthesized_sfx(name, p))
        if library_tracker is not None:
            lib_entry = f"library/sfx/{lib_path.name}"
            if lib_entry not in library_tracker:
                library_tracker.append(lib_entry)
        copy_library_asset(lib_path, dest_path)
        sfx_map[name] = dest_path
    return sfx_map


def create_timeline_sfx_track(
    plan: Any,
    scene_audios: List[Any],
    sfx_map: Dict[str, Path],
    total_duration: float,
    output_path: Path,
):
    """
    Synthesizes an audio track overlaying subtle SFX (click, whoosh, task_complete)
    at key storyboard event timestamps across the entire video timeline.
    """
    sample_rate = 44100
    num_samples = int(max(1.0, total_duration) * sample_rate)
    samples = [0] * num_samples

    # Cache decoded sound effect samples
    cached_sfx: Dict[str, List[int]] = {}
    for name, p in sfx_map.items():
        if p and Path(p).is_file():
            try:
                with wave.open(str(p), "rb") as wf:
                    n_frames = wf.getnframes()
                    raw_data = wf.readframes(n_frames)
                    count = len(raw_data) // 2
                    if count > 0:
                        cached_sfx[name] = list(struct.unpack(f"<{count}h", raw_data[: count * 2]))
            except Exception:
                pass

    def mix_sfx(sfx_name: str, time_sec: float, volume: float = 0.65):
        audio_samples = cached_sfx.get(sfx_name) or cached_sfx.get("click")
        if not audio_samples:
            return
        start_idx = int(time_sec * sample_rate)
        if start_idx >= num_samples:
            return
        for idx_offset, val in enumerate(audio_samples):
            idx = start_idx + idx_offset
            if idx >= num_samples:
                break
            samples[idx] = max(-32767, min(32767, samples[idx] + int(val * volume)))

    scenes = getattr(plan, "scenes", []) or (plan.get("scenes", []) if isinstance(plan, dict) else [])
    current_timeline = 0.0

    for i, scene in enumerate(scenes):
        audio = scene_audios[i] if i < len(scene_audios) else None
        scene_dur = getattr(audio, "scene_total_duration", 5.0) if audio else 5.0

        # Examine board objects or visuals in the scene
        board_objs = getattr(scene, "board_objects", None) or (scene.get("board_objects") if isinstance(scene, dict) else None) or []
        events_found = 0

        for bo in board_objs:
            start_ms = getattr(bo, "start_ms", None) or (bo.get("start_ms") if isinstance(bo, dict) else 0) or 0
            enter_type = str(getattr(bo, "enter", "") or (bo.get("enter", "") if isinstance(bo, dict) else "")).lower()
            data = getattr(bo, "data", {}) or (bo.get("data", {}) if isinstance(bo, dict) else {})
            preset = str(data.get("motion_preset", enter_type)).lower()
            label = str(data.get("label", "")).lower()

            t_event = current_timeline + (float(start_ms) / 1000.0)

            if "slide_in" in preset or "whoosh" in preset or "travel" in preset:
                mix_sfx("whoosh", t_event, volume=0.55)
                events_found += 1
            elif any(w in label for w in ("task_complete", "done", "timeline", "report", "complete", "verify", "shield", "approval")):
                mix_sfx("task_complete", t_event, volume=0.60)
                events_found += 1
            elif "pop" in preset or any(w in label for w in ("click", "step", "node", "prompt", "adjust")):
                mix_sfx("click", t_event, volume=0.50)
                events_found += 1

        if events_found == 0:
            mix_sfx("whoosh", current_timeline + 0.8, volume=0.45)
            mix_sfx("click", current_timeline + min(4.0, scene_dur * 0.5), volume=0.45)
            if i == len(scenes) - 1:
                mix_sfx("task_complete", current_timeline + max(1.0, scene_dur - 1.5), volume=0.55)

        current_timeline += scene_dur

    packed = bytearray()
    for s in samples:
        packed.extend(struct.pack("<h", s))

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(packed)
