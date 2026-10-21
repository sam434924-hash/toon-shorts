# ToonShorts Feature Catalog

Comprehensive index of commands, swappable plugins, art styles, configuration, and corresponding test suites.

## CLI Commands

### `make`
- **Description**: Generates an end-to-end 9:16 vertical short animated video.
- **Files**: `src/toonshorts/cli.py`, `src/toonshorts/core/pipeline.py`
- **Config Flags / Options**: `--style`, `--topic`, `--yes`, `--mock`, `--llm`, `--voice`, `--renderer`, `--motion`, `--output-dir`, `--keep-temp`
- **Tests**: `tests/smoke/test_smoke_pipeline.py`

---

## LLM Plugins (`plugins/llm`)

### `gemini`
- **Description**: Google Gemini screenplay writer and critic scoring loop.
- **Files**: `src/toonshorts/plugins/llm/gemini.py`, `src/toonshorts/core/client.py`
- **Config Flags**: `GEMINI_API_KEY`, `TEXT_MODEL_NAME`, `CRITIC_MODEL_NAME`, `MAX_CRITIC_REWRITES`
- **Tests**: `tests/contract/test_llm_contract.py`

### `fake`
- **Description**: Deterministic mock screenplay planner and critic for fast offline runs.
- **Files**: `src/toonshorts/plugins/llm/fake.py`
- **Config Flags**: None
- **Tests**: `tests/contract/test_llm_contract.py`, `tests/smoke/test_smoke_pipeline.py`

---

## Voice Plugins (`plugins/voice`)

### `edge_tts`
- **Description**: High-fidelity speech synthesizer using Edge-TTS with word-level boundary detection.
- **Files**: `src/toonshorts/plugins/voice/edge_tts.py`
- **Config Flags**: `DEFAULT_VOICE`
- **Tests**: `tests/contract/test_voice_contract.py`

### `synthetic`
- **Description**: Standalone offline synthesized tone audio generator with word-level proportional timing.
- **Files**: `src/toonshorts/plugins/voice/synthetic.py`
- **Config Flags**: None
- **Tests**: `tests/contract/test_voice_contract.py`, `tests/unit/test_timing.py`

### `fake`
- **Description**: Minimal silence/tone audio generator for offline smoke testing.
- **Files**: `src/toonshorts/plugins/voice/fake.py`
- **Config Flags**: None
- **Tests**: `tests/contract/test_voice_contract.py`, `tests/smoke/test_smoke_pipeline.py`

---

## Render Plugins (`plugins/render`)

### `pillow`
- **Description**: Procedural stick figure illustration engine drawing anti-aliased 1080x1920 frames in code.
- **Files**: `src/toonshorts/plugins/render/pillow.py`
- **Config Flags**: `VIDEO_WIDTH`, `VIDEO_HEIGHT`
- **Tests**: `tests/contract/test_render_contract.py`

### `gemini`
- **Description**: Imagen-based character sheet and story frame generator.
- **Files**: `src/toonshorts/plugins/render/gemini.py`, `src/toonshorts/core/client.py`
- **Config Flags**: `GEMINI_API_KEY`, `IMAGE_MODEL_NAME`
- **Tests**: `tests/contract/test_render_contract.py`

### `fake`
- **Description**: Ultra-fast in-memory solid frame generator for offline smoke testing.
- **Files**: `src/toonshorts/plugins/render/fake.py`
- **Config Flags**: `VIDEO_WIDTH`, `VIDEO_HEIGHT`
- **Tests**: `tests/contract/test_render_contract.py`, `tests/smoke/test_smoke_pipeline.py`

---

## Motion Plugins (`plugins/motion`)

### `ffmpeg`
- **Description**: Mathematical FFmpeg zoompan filter chains (zoom in/out, pan left/right, screen shake).
- **Files**: `src/toonshorts/plugins/motion/ffmpeg.py`
- **Config Flags**: `VIDEO_FPS`
- **Tests**: `tests/contract/test_motion_contract.py`

### `static`
- **Description**: Fixed scale-and-pad framing filter chain without camera movement.
- **Files**: `src/toonshorts/plugins/motion/static.py`
- **Config Flags**: None
- **Tests**: `tests/contract/test_motion_contract.py`

---

## Art Styles (`styles/`)

### `stickman`
- **Files**: `src/toonshorts/styles/stickman.json`
- **Renderer**: `pillow`

### `crayon`
- **Files**: `src/toonshorts/styles/crayon.json`
- **Renderer**: `gemini`

### `paper_cutout`
- **Files**: `src/toonshorts/styles/paper_cutout.json`
- **Renderer**: `gemini`

### `pixel_art`
- **Files**: `src/toonshorts/styles/pixel_art.json`
- **Renderer**: `gemini`

### `chalkboard`
- **Files**: `src/toonshorts/styles/chalkboard.json`
- **Renderer**: `gemini`
