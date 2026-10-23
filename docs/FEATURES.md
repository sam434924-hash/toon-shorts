# ToonShorts Feature Catalog

Comprehensive index of commands, swappable plugins, art styles, configuration, and corresponding test suites.

## CLI Commands

### `make`
- **Description**: Generates an end-to-end 9:16 vertical short animated video.
- **Files**: `src/toonshorts/cli.py`, `src/toonshorts/core/pipeline.py`
- **Config Flags / Options**: `--style`, `--topic`, `--yes`, `--mock`, `--fast`, `--llm`, `--voice`, `--voice-engine`, `--allow-noncommercial`, `--renderer`, `--motion`, `--output-dir`, `--keep-temp`
- **Tests**: `tests/smoke/test_smoke_pipeline.py`, `tests/unit/test_fast_preview.py`

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
- **Description**: Official Google Gemini text-to-speech audio generator with deterministic SHA-256 disk audio caching, character voice mapping, rate-limit retry with limits and missing line reporting, and speech verification.
- **Files**: `src/toonshorts/plugins/voice/gemini_tts.py`, `src/toonshorts/core/client.py`
- **Config Flags**: `GEMINI_API_KEY`, `TTS_MODEL_NAME`, `GEMINI_VOICES`
- **Tests**: `tests/contract/test_voice_contract.py`, `tests/unit/test_gemini_tts_cache.py`, `tests/unit/test_speaker_voice_mapping.py`

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
- **Description**: HTML5/SVG code-driven whiteboard animation engine with local Anime.js easing curves, bundled Rough.js progressive stroke-by-stroke drawing synced to Whisper word timings (underlines, keyword circles, inter-card arrows), dynamic 2D character pack loading into left and right slots (with mirrored right placement), loudness-driven mouth sync for active speaker, idle blinking/glancing for non-speaking listener, gesture resolution with style presets and scene overrides, 4-layer multiplane depth layering (foreground, subject, board, deep background) with camera parallax factors (2.0, 1.0, 0.5, 0.12), camera presets (wide, boy_close, girl_close, board_close), deterministic frame-based camera drift and punch-in zoom with shake, rack focus blur, safe area gesture boundaries (wave, point, explain, thumbs_up, shrug), and headless browser frame capture.
- **Files**: `src/toonshorts/plugins/render/animejs/`
- **Config Flags**: `ANIME_JS_PATH`, `ROUGH_JS_PATH`, `VIDEO_WIDTH`, `VIDEO_HEIGHT`, `VIDEO_FPS`, `CAMERA_PARALLAX_FACTORS`, `CAMERA_PRESETS`
- **Tests**: `tests/contract/test_render_contract.py`, `tests/unit/test_animejs.py`, `tests/unit/test_depth_camera_parallax.py`

### `blender3d`
- **Description**: Headless Blender 3D robot character renderer for RobotExpressive.glb with validated built-in actions (dance, idle, jump, running, wave, thumbs_up, etc.), clean 3-point lighting, and execution caps.
- **Files**: `src/toonshorts/plugins/render/blender3d.py`, `assets/3d/scripts/blender_render.py`
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

## Scene Format v2 & Directing Validator (`core/models`, `core/validator`)

### `Scene Format v2`
- **Description**: Extended screenplay format supporting `plan.version` (defaults to 1 with transparent v1 adapter), per-scene `layout` ("cards" or "stage"), `cast` assignments, `shots` lists, and `visuals` lists. Enforces strict schema validation, extra field rejection (`extra="forbid"`), text length bounds, and directing skill limits.
- **Files**: `src/toonshorts/core/models.py`, `src/toonshorts/core/validator.py`, `src/toonshorts/core/visuals.py`
- **Capabilities**: Backwards compatible v1 adapter, maximum 2 characters per scene, 180-degree rule enforcement, shot zoom limit (<= 1.35x), ease times (0.4 to 0.6s), minimum hold (>= 1.2s), zoom frequency limits (at most one zoom per 5s), target in cast check, non-overlapping shots, and scene length bounding.
- **Tests**: `tests/unit/test_v2_validation.py`, `tests/unit/test_validation.py`

### `Visual Templates & Motion Graphics Plugins`
- **Description**: Safe, deterministic animated visual components rendered inside the whiteboard and night studio in 'stage' layout. Supports 6 visual templates (`flow`, `request_response`, `typed_code`, `step_ladder`, `check_cross`, `counter`) as well as 5 standalone graphics plugins (`kinetic_words`, `draw_svg`, `octopus_vector`, `hearts_pop`, `blue_blood_drop`).
- **Files**: `src/toonshorts/core/visuals.py`, `src/toonshorts/plugins/graphics/`, `src/toonshorts/plugins/render/animejs/visual_renderer.py`
- **Capabilities**: Whitelist validation, automatic inventory registration, script injection safety, word-synchronized animations (pop, slide, stroke-dashoffset reveal, spring bounce), deterministic night studio particle effects, and board safe area validation.
- **Tests**: `tests/unit/test_visual_templates.py`, `tests/unit/test_graphics_plugins.py`, `tests/unit/test_animejs.py`

---

## 2D Layered Character System (`core/character2d`, `core/character_pack`)

### `presenter` (Whiteboard Presenter Character Pack)
- **Description**: Modular 2D layered SVG character pack extracted from whiteboard inline markup. Features a continuous unified hairline with elegant side-swept bangs clearing eyebrows, seamless sideburns, aligned golden rim sidelight, swappable arm rigs (`idle`, `wave`, `point`, `explain`, `thumbs_up`, `shrug`), 4 mouth states (`closed`, `slightly_open`, `wide_open`, `round_o` with legacy `open` alias), and eye states (`open`, `blink`, `screen_left`, `screen_right`).
- **Files**: `src/toonshorts/core/character_pack.py`, `src/toonshorts/core/character2d.py`, `assets/2d/characters/presenter/character.svg`, `assets/2d/characters/presenter/manifest.json`
- **Capabilities**: Full manifest compliance, 0 validation errors, swappable arm gesture rigs, eye blinking, speech-synced lip sync, and left/right slot rendering.
- **Tests**: `tests/unit/test_character_pack.py`, `tests/unit/test_animejs.py`

### `boy_a` (2D Layered SVG Character Pack)
- **Description**: Modular 2D layered SVG character pack with anatomically and stylistically aligned ears ($y=215\dots288$), anchored head base, synchronized hair-back framing, swappable eye states (`open`, `blink`, `screen_left`, `screen_right`), and mouth states (`closed`, `slightly_open`, `wide_open`, `round_o`) preserving identical head, hair (merged 2-tone facets), and eyebrows geometry. Includes simple neck and plain hoodie shoulders.
- **Files**: `src/toonshorts/core/character_pack.py`, `src/toonshorts/core/character2d.py`, `assets/2d/characters/boy_a/character.svg`, `assets/2d/characters/boy_a/manifest.json`
- **Capabilities**: Safe loading, path traversal prevention, strict XML/SVG safety checks (forbids `<script>`, event handlers, external entities, and gradients), file size <= 200 KB, state-switching SVG generation, PNG rendering via Playwright, and test staging workbench (`staging/index.html` and 4x2 contact sheet).
- **Tests**: `tests/unit/test_character_pack.py`, `tests/unit/test_character2d.py`

### `stick_hoodie`
- **Description**: 2D layered character system sliced from coordinate layout sheets with transparent layers (head, 8 expressions, hoodie torso, articulated stick limbs, mirrored hands and shoes). Reusable asset pack (not yet connected to the main CLI pipeline).
- **Files**: `src/toonshorts/core/character2d.py`, `assets/2d/layouts/sheet_03_layout.json`, `tools/build_2d_hoodie_video.py`
- **Capabilities**: Character registry, modular slots (hair, hat, torso, legs, shoes, hands), forward-kinematic 2D skeletal rotation, audio loudness mouth shape swapping, squash & stretch actions (idle, walk, wave, jump), soft pastel gradient background rendering with ground shadow, and standalone short video generator (`tools/build_2d_hoodie_video.py`) with Piper TTS speech and burned ASS subtitles.
- **Tests**: `tests/unit/test_character2d.py`

### `boy_b` (2D Full-Body Layered Character Pack)
- **Description**: Full-body layered character pack with brown hair, round glasses, and blue hoodie. Sourced from 8-face tile sheet and body sheet (front/back views), featuring 22 transparent raster layers as well as clean vector (SVG) layers in `vector/` across 27 layers including dedicated rear views (`torso_back`, `shoe_back_left`, `shoe_back_right`, `leg_upper_back_left`, `leg_upper_back_right`), full volumetric back/top cranium silhouette, solid dark hair underlay eliminating facet transparent holes/white spots, authentic 3/4 perspective purple canvas sneakers with 3D white toe caps and contoured rubber soles, elbow/knee splits, gapless joint rotation caps (shoulders, elbows, hips, knees, ankles), and full FK skeletal compatibility.
- **Files**: `assets/2d/characters/boy_b/manifest.json`, `assets/2d/characters/boy_b/character.json`, `assets/2d/characters/boy_b/layers/`, `assets/2d/characters/boy_b/vector/`, `tools/build_character_packs.py`, `tools/build_vector_character_packs.py`
- **Capabilities**: Full `CharacterPack` compliance (0 validation errors), modular master `character.svg` containing all 27 layers and swappable states, swappable eye states (`open`, `blink`, `look_left`, `look_right`), mouth states (`closed`, `slightly_open`, `wide_open`, `round_o`, `open_smile`), back-of-head layer from back view, gapless overlap joint caps, manifest and character.json schemas, vector SVG layers (1000x1500 viewBox, direct fills/strokes), authentic back view poses without front elements, and test staging previews (`staging/boy_b_preview_sheet.png`, `vector/staging/boy_b_preview_sheet.png`).
- **Tests**: `tests/unit/test_new_character_packs.py`

### `girl_a` (2D Full-Body Layered Character Pack)
- **Description**: Full-body layered character pack with orange hair, round glasses, freckles, and purple sleeveless waistcoat over dark shirt. Sourced from 8-face tile sheet and body sheet (front/back views), featuring 22 transparent raster layers as well as clean vector (SVG) layers in `vector/` across 27 layers with refined torso garment structure (crew-neck collar, continuous dark crew-neck t-shirt underlay, curved open waistcoat lapels, rounded bottom hems, clean armholes, pelvis underlay), dedicated rear view layers (`torso_back`, `shoe_back_left`, `shoe_back_right`, `leg_upper_back_left`, `leg_upper_back_right`), full volumetric back/top cranium silhouette, solid dark hair underlay eliminating facet transparent holes/white spots, authentic 3/4 perspective purple sneakers with 3D white toe caps and contoured rubber soles matching source artwork, elbow/knee splits, natural hands from hands sheet, gapless joint rotation caps (shoulders, elbows, hips, knees, ankles), and full FK skeletal compatibility.
- **Files**: `assets/2d/characters/girl_a/manifest.json`, `assets/2d/characters/girl_a/character.json`, `assets/2d/characters/girl_a/layers/`, `assets/2d/characters/girl_a/vector/`, `tools/build_character_packs.py`, `tools/build_vector_character_packs.py`
- **Capabilities**: Full `CharacterPack` compliance (0 validation errors), modular master `character.svg` containing all 27 layers and swappable states, swappable eye states (`open`, `blink`, `look_left`, `look_right`), mouth states (`closed`, `slightly_open`, `wide_open`, `round_o`, `open_smile`), back-of-head layer from back view, gapless overlap joint caps, manifest and character.json schemas, vector SVG layers (1000x1500 viewBox, direct fills/strokes), authentic back view poses without front elements, and test staging previews (`staging/girl_a_preview_sheet.png`, `vector/staging/girl_a_preview_sheet.png`).
- **Tests**: `tests/unit/test_new_character_packs.py`

