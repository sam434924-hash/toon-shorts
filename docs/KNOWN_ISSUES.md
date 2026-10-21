# Known Issues & Pre-Existing Bugs

This document tracks bugs and architectural anomalies observed in the original codebase prior to and during refactoring.

## 1. Upstream Google GenAI SDK Deprecation Warning
- **Symptom**: `DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17` emitted from `google/genai/types.py:42`.
- **Location**: `google-genai` SDK v0.1.x integration in `core/client.py`.
- **Impact**: Harmless deprecation warning on Python 3.14+ test runs; will become an error on Python 3.17 if unpatched upstream.

## 2. Hardcoded Fallback Duration for Audio Probing
- **Symptom**: When `ffprobe` fails or is absent for non-WAV formats, duration defaults to a static `3.0` seconds rather than estimating from audio payload length.
- **Location**: `plugins/voice/edge_tts.py` (`get_audio_duration_wave_or_ffprobe`).
- **Impact**: Can lead to inaccurate scene duration or clipped speech on environments lacking ffprobe.

## 3. Subtitle Burn-In Libass Dependency
- **Symptom**: Video assembly subtitle burn-in (`-vf subtitles=captions.ass`) fails if local FFmpeg was compiled without `libass` support.
- **Location**: `core/assembler.py`.
- **Mitigation in code**: Pipeline catches the error and copies the unsubtitled video to destination, but captions are omitted.

## 4. Critic JSON Parse Fallback Skips Revision Loop
- **Symptom**: If the Critic LLM output fails schema validation, the fallback review defaults to a score of `7.5`.
- **Location**: `plugins/llm/gemini.py` (`evaluate_script`).
- **Impact**: Because `7.5 >= 7.0`, the script bypasses rewrite iterations even if the original screenplay was flawed.

## 5. Reserved Filename Collisions on Windows
- **Symptom**: `sanitize_filename` removes illegal characters (`<>:"/\\|?*`), but does not check for reserved Windows device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
- **Location**: `core/models.py` (`sanitize_filename`).
- **Impact**: Script titles using reserved names could fail to write output files on Windows.
