# ToonShorts Feature Catalog

Comprehensive index of commands, swappable plugins, art styles, configuration, and corresponding test suites.

## CLI Commands

### `make`
- **Description**: Generates an end-to-end 9:16 vertical short animated video.
- **Files**: `src/toonshorts/cli.py`, `src/toonshorts/core/pipeline.py`
- **Config Flags / Options**: `--style`, `--topic`, `--yes`, `--mock`, `--llm`, `--voice`, `--voice-engine`, `--allow-noncommercial`, `--renderer`, `--motion`, `--output-dir`, `--keep-temp`
- **Tests**: `tests/smoke/test_smoke_pipeline.py`

---

## LLM Plugins (`plugins/llm`)

### `gemini`
- **Description**: Google Gemini screenplay writer and critic scoring loop.
- **Files**: `src/toonshorts/plugins/llm/gemini.py`, `src/toonshorts/core/client.py`
- **Config Flags**: `GEMINI_API_KEY`, `TEXT_MODEL_NAME`, `CRITIC_MODEL_NAME`, `MAX_CRITIC_REWRITES`
- **Tests**: `tests/contract/test_llm_contract.py`, `tests/unit/test_validation.py`

### `fake`
- **Description**: Deterministic mock screenplay planner and critic for fast offline runs.
- **Files**: `src/toonshorts/plugins/llm/fake.py`
- **Config Flags**: None
- **Tests**: `tests/contract/test_llm_contract.py`, `tests/smoke/test_smoke_pipeline.py`

---

## Voice Plugins (`plugins/voice`)

### `gemini_tts`
- **Description**: Official Google Gemini text-to-speech audio generator with deterministic SHA-256 disk audio caching, immediate quota/rate limit error abort, and speech verification.
- **Files**: `src/toonshorts/plugins/voice/gemini_tts.py`, `src/toonshorts/core/client.py`
- **Config Flags**: `GEMINI_API_KEY`, `TTS_MODEL_NAME`, `GEMINI_VOICES`
- **Tests**: `tests/contract/test_voice_contract.py`, `tests/unit/test_gemini_tts_cache.py`

### `piper`
- **Description**: Local fast neural TTS engine running through subprocess argument lists and stdin.
- **Files**: `src/toonshorts/plugins/voice/piper.py`
- **Config Flags**: `PIPER_VOICES_DIR`, `VOICES_REGISTRY_PATH`
- **Tests**: `tests/contract/test_voice_contract.py`

### `windows_sapi`
- **Description**: Local Windows SAPI voice synthesizer via pyttsx3 for offline testing.
- **Files**: `src/toonshorts/plugins/voice/windows_sapi.py`
- **Config Flags**: `VOICES_REGISTRY_PATH`
- **Tests**: `tests/contract/test_voice_contract.py`

### `fake`
- **Description**: Deterministic mock WAV audio generator for rapid test suite execution.
- **Files**: `src/toonshorts/plugins/voice/fake.py`
- **Config Flags**: None
- **Tests**: `tests/contract/test_voice_contract.py`, `tests/smoke/test_smoke_pipeline.py`

---

## Render Plugins (`plugins/render`)

### `animejs`
- **Description**: HTML5/SVG code-driven whiteboard animation engine with local Anime.js easing curves, bundled Rough.js progressive stroke-by-stroke drawing synced to Whisper word timings (underlines, keyword circles, inter-card arrows), 7-layer character head architecture, physically attached hands and arm sleeves, 100% constant studio set and static camera across all scenes, safe area gesture boundaries (wave, point, explain, thumbs_up, shrug), and headless browser frame capture.
- **Files**: `src/toonshorts/plugins/render/animejs.py`
- **Config Flags**: `ANIME_JS_PATH`, `ROUGH_JS_PATH`, `VIDEO_WIDTH`, `VIDEO_HEIGHT`, `VIDEO_FPS`
- **Tests**: `tests/contract/test_render_contract.py`, `tests/unit/test_animejs.py`

### `blender3d`
- **Description**: Headless Blender 3D robot character renderer for RobotExpressive.glb with validated built-in actions (dance, idle, jump, running, wave, thumbs_up, etc.), clean 3-point lighting, and execution caps.
- **Files**: `src/toonshorts/plugins/render/blender3d.py`, `assets3d/scripts/blender_render.py`
- **Config Flags**: `BLENDER_PATH`, `BLENDER_DRAFT_WIDTH`, `BLENDER_DRAFT_HEIGHT`, `BLENDER_FINAL_WIDTH`, `BLENDER_FINAL_HEIGHT`, `BLENDER_MAX_FRAMES`, `BLENDER_MAX_SECONDS_PER_RUN`, `BLENDER_RENDER_TIMEOUT_SECONDS`
- **Tests**: `tests/contract/test_render_contract.py`, `tests/unit/test_blender3d.py`

### `cairo`
- **Description**: Headless 2D vector stickman engine with hierarchical skeleton, facial expressions, actions with squash and stretch, hand-drawn wobble, contact shadows, and garment layering.
- **Files**: `src/toonshorts/plugins/render/cairo.py`
- **Config Flags**: `VIDEO_WIDTH`, `VIDEO_HEIGHT`
- **Tests**: `tests/contract/test_render_contract.py`, `tests/unit/test_cairo_stickman.py`

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
- **Description**: Fixed camera framing without dynamic pan or zoom.
- **Files**: `src/toonshorts/plugins/motion/static.py`
- **Config Flags**: None
- **Tests**: `tests/contract/test_motion_contract.py`

---

## Art Styles (`src/toonshorts/styles/*.json`)

### `stickman`
- **Description**: Minimalist 2D vector stick figure animation on textured paper, using the Cairo renderer (`cairo.py`).
- **Files**: `src/toonshorts/styles/stickman.json`
- **Renderer**: `cairo`
- **Tests**: `tests/unit/test_styles.py`, `tests/unit/test_cairo_stickman.py`

### `whiteboard`
- **Description**: Modern clean whiteboard explainer video with animated presenter character and dynamic Rough.js sketch annotations, using Anime.js and Playwright.
- **Files**: `src/toonshorts/styles/whiteboard.json`
- **Renderer**: `animejs`
- **Tests**: `tests/unit/test_styles.py`, `tests/unit/test_animejs.py`

### `crayon`
- **Description**: Gemini Imagen wax crayon drawing on construction paper.
- **Files**: `src/toonshorts/styles/crayon.json`
- **Renderer**: `gemini`
- **Tests**: `tests/unit/test_styles.py`

### `paper_cutout`
- **Description**: Layered papercraft stop-motion collage with drop shadows.
- **Files**: `src/toonshorts/styles/paper_cutout.json`
- **Renderer**: `gemini`
- **Tests**: `tests/unit/test_styles.py`

### `pixel_art`
- **Description**: 16-bit retro arcade pixel sprites.
- **Files**: `src/toonshorts/styles/pixel_art.json`
- **Renderer**: `gemini`
- **Tests**: `tests/unit/test_styles.py`

### `chalkboard`
- **Description**: Dusty chalk classroom illustration on dark slate blackboard.
- **Files**: `src/toonshorts/styles/chalkboard.json`
- **Renderer**: `gemini`
- **Tests**: `tests/unit/test_styles.py`

---

## 2D Layered Character System (`core/character2d`, `core/character_pack`)

### `boy_a` (2D Layered SVG Character Pack)
- **Description**: Modular 2D layered SVG character pack with swappable eye states (`open`, `blink`, `screen_left`, `screen_right`) and mouth states (`closed`, `slightly_open`, `wide_open`, `round_o`) preserving identical head, hair (merged 2-tone facets), and eyebrows geometry. Includes simple neck and plain hoodie shoulders.
- **Files**: `src/toonshorts/core/character_pack.py`, `src/toonshorts/core/character2d.py`, `assets2d/characters/boy_a/character.svg`, `assets2d/characters/boy_a/manifest.json`
- **Capabilities**: Safe loading, path traversal prevention, strict XML/SVG safety checks (forbids `<script>`, event handlers, external entities, and gradients), file size <= 200 KB, state-switching SVG generation, PNG rendering via Playwright, and test staging workbench (`staging/index.html` and 4x2 contact sheet).
- **Tests**: `tests/unit/test_character_pack.py`, `tests/unit/test_character2d.py`

### `stick_hoodie`
- **Description**: 2D layered character system sliced from coordinate layout sheets with transparent layers (head, 8 expressions, hoodie torso, articulated stick limbs, mirrored hands and shoes). Reusable asset pack (not yet connected to the main CLI pipeline).
- **Files**: `src/toonshorts/core/character2d.py`, `assets2d/layouts/sheet_03_layout.json`, `tools/build_2d_hoodie_video.py`
- **Capabilities**: Character registry, modular slots (hair, hat, torso, legs, shoes, hands), forward-kinematic 2D skeletal rotation, audio loudness mouth shape swapping, squash & stretch actions (idle, walk, wave, jump), soft pastel gradient background rendering with ground shadow, and standalone short video generator (`tools/build_2d_hoodie_video.py`) with Piper TTS speech and burned ASS subtitles.
- **Tests**: `tests/unit/test_character2d.py`
