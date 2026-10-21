# ToonShorts Architecture

## Overview
ToonShorts is an automated pipeline that produces vertical (9:16, 1080x1920) animated comedy videos for YouTube Shorts. It combines screenplay generation, voice acting, visual animation, camera motion, and karaoke-style subtitle burn-in.

The codebase is organized around a strict **plugin-based architecture**:
- **Core (`src/toonshorts/core`)**: Contains schemas, configuration, spend caps, errors, assembler, and the plugin registry. **Core never imports plugins.**
- **Plugins (`src/toonshorts/plugins`)**: Swappable implementations for `llm`, `voice`, `render`, and `motion`. Plugins import only `core`.
- **Styles (`src/toonshorts/styles`)**: Self-contained art style preset files defining color palettes, pacing, avoid tokens, and captions.

## Data Flow
```
Topic & Style Preset
       │
       ▼
[1] LLM Plugin (Screenplay Planning) ──> ScriptPlan
       │
       ▼
[2] LLM Plugin (Critic Review Loop)  ──> Refined ScriptPlan (Score >= 7.0)
       │
       ▼
[3] Cost Gate (Pre-flight estimation & confirmation)
       │
       ▼
[4] Voice Plugin (The Timing Spine)  ──> SceneAudio (MP3/WAV + WordTimings)
       │
       ▼
[5] Render Plugin (Visual Frames)    ──> 9:16 Scene Images (PNG)
       │
       ▼
[6] Motion Plugin & Assembler        ──> FFmpeg Filters + ASS Subtitles ──> Final MP4
```

## Plugin System & Contracts
Each swappable component implements an ABC defined in `core/registry.py`:
- `LLMInterface`: Screenplay generation and critic review (`generate_plan`, `review_and_refine`).
- `VoiceInterface`: Speech synthesis and word boundary timestamps (`generate_scene_voice`, `generate_all_voices`).
- `RenderInterface`: Frame rendering (`render_scene`, `render_all_scenes`).
- `MotionInterface`: Mathematical camera movement filters (`get_filter_chain`).

### Adding a New Plugin
1. Create a single file in `src/toonshorts/plugins/<category>/<plugin_name>.py`.
2. Inherit from `<Category>Interface` and decorate with `@register_<category>("<plugin_name>")`.
3. Add any required config or credentials into `core/config.py`.
4. No edits to the pipeline, registry, or other plugins are required.
