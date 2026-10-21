# Future Voice Cloning Plugins Policy & Guidelines

This document outlines the strict technical, ethical, and legal requirements for any future voice cloning plugins (e.g. ElevenLabs voice clones, Coqui, Chatterbox, or custom diffusion-based cloning) integrated into the ToonShorts pipeline.

## 1. Ownership and Consent Policy
- **Authorized Voices Only**: Voice cloning plugins may ONLY be used to clone your own personal voice or voices of individuals who have provided explicit, written, verifiable permission and consent for commercial animation use.
- **No Impersonation**: Cloning public figures, celebrities, or non-consenting individuals is strictly forbidden.

## 2. Voice License Registry Enforcement
- Any voice profile created via cloning MUST be explicitly cataloged in `voices.json` before execution:
  - `name`: Unique identifier for the cloned model/voice profile.
  - `source`: Provenance of the training audio samples (e.g., "Personal studio recording 2026").
  - `license`: Written consent reference or personal ownership declaration.
  - `commercial_ok`: Set to `true` only if verified written rights cover commercial video distribution; otherwise `false` or `unknown`.
- The pipeline will refuse execution if `commercial_ok` is not `true`, unless explicitly overridden with `--allow-noncommercial`.

## 3. Implementation Requirements
When implementing a voice cloning plugin:
1. Inherit from `VoiceInterface` and register via `@register_voice("<plugin_name>")`.
2. Output standard 16-bit PCM WAV audio.
3. Pass all generated audio through `check_speech_audio(...)` to verify duration, non-silence, and rate sanity.
4. Align timestamps using `align_words_with_whisper(...)`.
