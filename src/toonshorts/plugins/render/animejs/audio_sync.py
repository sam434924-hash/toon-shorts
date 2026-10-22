"""
Purpose: Audio loudness envelope extraction and frame-by-frame mouth cue synchronization.
Inputs: WAV audio file paths, video frame rate, and threshold ratio.
Outputs: Boolean sequence representing open/closed mouth states for animation.
Depends on: core.config, logging, numpy, pathlib, typing, wave
Used by: plugins.render.animejs, plugins.render.animejs.capture
Config keys: VIDEO_FPS
Tests: tests/unit/test_animejs.py
"""

import logging
from pathlib import Path
from typing import List, Optional
import wave

import numpy as np

from toonshorts.core import config

logger = logging.getLogger(__name__)


def compute_mouth_cues_from_audio(
    audio_path: Optional[Path],
    fps: int = config.VIDEO_FPS,
    threshold_ratio: float = 0.18,
) -> List[bool]:
    """
    Computes frame-by-frame mouth open/closed states from WAV audio loudness (RMS).
    Returns list of booleans of length corresponding to audio duration in frames.
    """
    if not audio_path:
        return []

    p = Path(audio_path)
    if not p.is_file() or p.stat().st_size == 0:
        return []

    try:
        with wave.open(str(p), "rb") as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            nframes = wf.getnframes()
            raw_bytes = wf.readframes(nframes)
    except Exception as e:
        logger.warning("Could not read audio file for mouth cues (%s): %s", audio_path, e)
        return []

    if nframes == 0 or framerate == 0:
        return []

    # Parse raw PCM bytes to float array in [-1.0, 1.0]
    if sampwidth == 2:
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 1:
        samples = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if nchannels > 1:
        samples = samples.reshape(-1, nchannels).mean(axis=1)

    duration_sec = nframes / framerate
    total_frames = max(1, int(round(duration_sec * fps)))

    rms_per_frame: List[float] = []
    for k in range(total_frames):
        s0 = int(k * framerate / fps)
        s1 = int((k + 1) * framerate / fps)
        chunk = samples[s0:s1]
        if len(chunk) == 0:
            rms_per_frame.append(0.0)
        else:
            rms = float(np.sqrt(np.mean(chunk**2)))
            rms_per_frame.append(rms)

    max_rms = float(np.max(rms_per_frame)) if rms_per_frame else 0.0
    threshold = max(0.015, max_rms * threshold_ratio)

    raw_cues = [bool(r >= threshold) for r in rms_per_frame]

    # Smooth mouth flapping: avoid single-frame flickering
    smoothed = list(raw_cues)
    for i in range(1, len(smoothed) - 1):
        if not smoothed[i] and smoothed[i - 1] and smoothed[i + 1]:
            smoothed[i] = True
        elif smoothed[i] and not smoothed[i - 1] and not smoothed[i + 1]:
            smoothed[i] = False

    return smoothed
