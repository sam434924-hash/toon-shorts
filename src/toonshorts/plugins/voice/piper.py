"""
Purpose: Local Piper TTS plugin executing binary via subprocess with stdin.
Inputs: Scene dialogue lines, piper model paths, and output destinations.
Outputs: Generated 16-bit WAV audio files and aligned word timestamps.
Depends on: core.config, core.errors, core.models, core.registry, logging, pathlib, shutil, subprocess, typing, voice_utils
Used by: None
Config keys: PIPER_VOICES_DIR
Tests: tests/contract/test_voice_contract.py
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from toonshorts.core import config
from toonshorts.core.errors import VoiceError
from toonshorts.core.models import ScriptPlan, Scene, SceneAudio
from toonshorts.core.registry import VoiceInterface, register_voice
from toonshorts.voice_utils import (
    check_speech_audio,
    check_voice_license,
    align_words_with_whisper,
    assign_character_voices,
)

logger = logging.getLogger("toonshorts.plugins.voice.piper")

INSTALL_INSTRUCTIONS = """
[PIPER SETUP REQUIRED]
Piper executable or voice model file not found!
To use the local Piper TTS engine:
1. Download the Piper standalone binary from:
   https://github.com/rhasspy/piper/releases
   (e.g., piper_windows_amd64.zip for Windows, piper_linux_x86_64.tar.gz for Linux).
2. Extract 'piper.exe' (or 'piper') and place it on your system PATH.
3. Download a voice ONNX model and its config JSON from:
   https://huggingface.co/rhasspy/piper-voices
   (e.g., en_US-lessac-medium.onnx and en_US-lessac-medium.onnx.json).
4. Place the voice files in:
   assets/voices/piper/
5. Verify license terms and update voices.json before generating commercial content.
"""


def find_piper_executable() -> Optional[str]:
    """Locates piper executable on system PATH or local project paths."""
    found = shutil.which("piper")
    if found:
        return found
    # Check potential local binary locations
    local_candidates = [
        config.PROJECT_ROOT / "bin" / "piper.exe",
        config.PROJECT_ROOT / "piper" / "piper.exe",
        config.PROJECT_ROOT / "assets" / "piper" / "piper.exe",
    ]
    for c in local_candidates:
        if c.is_file():
            return str(c)
    return None


@register_voice("piper")
class PiperVoicePlugin(VoiceInterface):
    """Local Piper neural TTS engine running through subprocess argument lists and stdin."""
    name = "piper"

    def __init__(self, allow_noncommercial: bool = False, voices_dir: Optional[Path] = None):
        self.allow_noncommercial = allow_noncommercial
        self.voices_dir = voices_dir or config.PIPER_VOICES_DIR

    def generate_scene_voice(
        self,
        scene_index: int,
        scene: Scene,
        voice_name: str,
        temp_dir: Path,
        pause_seconds: float = 0.35,
    ) -> SceneAudio:
        piper_exe = find_piper_executable()
        if not piper_exe:
            logger.error(INSTALL_INSTRUCTIONS)
            raise VoiceError(f"Piper binary not found on PATH or in project bin.\n{INSTALL_INSTRUCTIONS}")

        # Check license in voices.json
        check_voice_license(voice_name, "piper", allow_noncommercial=self.allow_noncommercial)

        model_file = self.voices_dir / f"{voice_name}.onnx"
        if not model_file.is_file():
            # Check with potential extension stripped
            clean_name = voice_name[:-5] if voice_name.endswith(".onnx") else voice_name
            model_file = self.voices_dir / f"{clean_name}.onnx"

        if not model_file.is_file():
            logger.error(INSTALL_INSTRUCTIONS)
            raise VoiceError(
                f"Piper voice model file not found: '{model_file}'. "
                f"Download voice ONNX and JSON files to '{self.voices_dir}'.\n{INSTALL_INSTRUCTIONS}"
            )

        output_wav = temp_dir / f"scene_{scene_index}_piper.wav"

        # Safe execution without shell strings: text delivered via stdin
        cmd = [
            piper_exe,
            "--model", str(model_file),
            "--output-file", str(output_wav),
        ]

        try:
            res = subprocess.run(
                cmd,
                input=scene.dialogue_line,
                text=True,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error("Piper synthesis failed: %s\nStderr: %s", e, e.stderr)
            raise VoiceError(f"Piper synthesis command failed: {e.stderr or e}") from e
        except Exception as e:
            raise VoiceError(f"Unexpected error running Piper subprocess: {e}") from e

        # Validate speech audio (16-bit WAV, rate, silence)
        duration = check_speech_audio(output_wav, scene.dialogue_line)

        # Word timing alignment via faster-whisper (falls back to proportional timing with warning)
        word_timings = align_words_with_whisper(output_wav, scene.dialogue_line, duration)

        return SceneAudio(
            scene_index=scene_index,
            audio_path=output_wav,
            duration_seconds=duration,
            scene_total_duration=duration + pause_seconds,
            word_timings=word_timings,
        )

    def generate_all_voices(
        self,
        plan: ScriptPlan,
        temp_dir: Path,
    ) -> List[SceneAudio]:
        # Gather available piper voices or fallback to requested/registered
        available = [p.stem for p in self.voices_dir.glob("*.onnx")] if self.voices_dir.exists() else []
        voice_pool = available if available else ["en_US-lessac-medium", "en_US-amy-medium"]
        voice_map = assign_character_voices(plan, voice_pool)

        results = []
        for i, scene in enumerate(plan.scenes):
            voice = voice_map.get(scene.speaker.lower(), voice_pool[0])
            results.append(self.generate_scene_voice(i, scene, voice, temp_dir))
        return results
