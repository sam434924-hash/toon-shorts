"""
Purpose: Royalty-free sound effect generation for comedic punchlines.
Inputs: SFX identifiers (boing, whistle, pop) and destination paths.
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
from typing import Dict, List, Optional

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


def prepare_sound_effects(
    temp_dir: Path,
    library_tracker: Optional[List[str]] = None,
) -> Dict[str, Path]:
    """Generates standard comedic sound effect library in temp dir using shared library cache."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    sfx_map = {}
    for name in ["pop", "boing", "whistle"]:
        dest_path = temp_dir / f"sfx_{name}.wav"
        lib_path, is_hit = get_or_create_sfx(name, lambda p: create_synthesized_sfx(name, p))
        if library_tracker is not None:
            lib_entry = f"library/sfx/{lib_path.name}"
            if lib_entry not in library_tracker:
                library_tracker.append(lib_entry)
        copy_library_asset(lib_path, dest_path)
        sfx_map[name] = dest_path
    return sfx_map
