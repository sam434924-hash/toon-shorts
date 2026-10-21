# ADR 0001: Plugin-Based Architecture for Swappable Components

## Context
ToonShorts supports multiple art styles, animation engines (Pillow vs Gemini Imagen), speech providers (Edge-TTS vs Synthetic tones), and LLMs. The original codebase intertwined these within monolithic files.

## Decision
Define explicit abstract base classes (`LLMInterface`, `VoiceInterface`, `RenderInterface`, `MotionInterface`) in `core/registry.py`. Allow plugins to register via decorators (`@register_llm`, etc.) and be discovered automatically at runtime.

## Consequences
- Adding a plugin requires creating exactly one new file in `plugins/<type>/` and adding a config entry if needed.
- No changes required to pipeline runners or existing plugins.
