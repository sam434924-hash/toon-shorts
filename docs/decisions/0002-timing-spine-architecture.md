# ADR 0002: Voice-First Timing Spine

## Context
Short-form vertical video comedy relies heavily on snappy timing, cadence, and punchline pauses. Determining scene durations before generating audio produces robotic or misaligned video.

## Decision
Generate audio voice tracks and word timestamps first. The resulting audio duration establishes the authoritative timing spine for visual rendering, camera motion duration, and word-by-word subtitle burn-in.

## Consequences
- Zero audio-visual desync.
- Subtitle highlighting aligns with actual speech.
