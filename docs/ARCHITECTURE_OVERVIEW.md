# ToonShorts Architecture Overview

## 1. What This Project Does

ToonShorts is a Python CLI pipeline that turns a text brief or topic into a short animated vertical video (MP4) ready for YouTube Shorts. It generates a screenplay with an LLM, synthesizes voiceovers, renders animated scenes with whiteboard-style characters and board animations, then assembles them into a final video with burned-in subtitles.

---

## 2. Pipeline — Brief to Final MP4

Entry: `toonshorts make --topic "..." --style whiteboard`  
Entry point: `src/toonshorts/cli.py:main()` → `src/toonshorts/core/pipeline.py:run_pipeline()`

| Step | File → Function | Input | Output |
|------|----------------|-------|--------|
| 1 · Planning | `plugins/llm/gemini.py:generate_plan()` | topic string + style preset | `ScriptPlan` (Pydantic model, scenes 4–10) |
| 2 · Critic | `plugins/llm/gemini.py:review_and_refine()` | `ScriptPlan` | refined `ScriptPlan` + `CriticReview` (score logged) |
| 3 · Cost gate | `core/pipeline.py:confirm_cost_gate()` | estimated token/TTS cost | user confirmation or abort |
| 4 · Voice | `plugins/voice/{engine}.py:generate_all_voices()` | refined plan + temp dir | `List[SceneAudio]` (WAV per scene) |
| 5 · Render | `plugins/render/animejs/plugin.py:render_all_scenes()` | plan + style + scene audios | `List[Path]` (PNG/MP4 per scene via Playwright) |
| 6 · Assemble | `core/assembler.py:assemble_final_video()` | scene images + scene audios + motion plugin | final `{title}.mp4` in output/ |

Brief-mode entry (`toonshorts make --brief brief.json`) goes through `run_pipeline_from_brief()` in the same file; it caches the generated scene JSON to `briefs/{name}_scene.json` and skips LLM if that file already exists.

---

## 3. Folder Map

| Path | Contents |
|------|----------|
| `src/toonshorts/` | Main Python package (entry point, CLI, config, voice, subtitles) |
| `src/toonshorts/core/` | Pipeline engine: pipeline.py, models.py, registry.py, assembler.py, character2d.py, character_pack.py, client.py, config.py |
| `src/toonshorts/plugins/` | All swappable plugin implementations (llm/, voice/, render/, motion/, graphics/) |
| `src/toonshorts/plugins/render/animejs/` | Primary production renderer — HTML5 + Playwright + Rough.js; templates/*.js (rough_draw, stage_visuals, camera_engine, gestures_fk, main) is the modular animation engine |
| `src/toonshorts/styles/` | Style preset JSON files (7 styles: whiteboard, chalkboard, night_studio, stickman, crayon, paper_cutout, pixel_art) |
| `src/toonshorts/assets/` | Vendored JS libs (anime.js 3.2.2, rough.js 4.6.6) |
| `assets/2d/characters/` | Character packs (SVG layers + PNG rasters, see §6) |
| `assets/3d/` | Blender 3D models and scripts |
| `briefs/` | Input brief JSON files; cached scene JSONs saved here |
| `output/` | Final MP4 files |
| `temp/` | Pipeline intermediate renders (deleted unless --keep-temp) |
| `tests/` | Full test suite (unit/, contract/, smoke/, fixtures/) |
| `docs/` | CODEMAP.md, ARCHITECTURE.md, KNOWN_ISSUES.md, CHANGELOG.md, decisions/ |
| `tools/` | update_docs.py — regenerates CODEMAP.md from source headers |
| `voices.json` | Voice alias registry (maps voice names to TTS engine + voice ID) |

---

## 4. Scene JSON Format (v2)

Defined as Pydantic models in `src/toonshorts/core/models.py`.

**Top-level `ScriptPlan`**

| Field | What it controls |
|-------|-----------------|
| `version` | 1 or 2. v2 unlocks shots, visuals, cast, layout per scene. |
| `title` | Video filename base (sanitized) |
| `art_style` | Passed to style-preset loader |
| `emotional_arc` | Tone guidance used by the LLM critic |
| `characters` | 2–3 entries; each has `name`, `visual_description`, `voice_id` |
| `scenes` | Ordered list of 4–10 `Scene` objects |

**Per-scene `Scene`**

| Field | What it controls |
|-------|-----------------|
| `speaker` | Which character speaks; drives voice selection and camera focus |
| `dialogue_line` | The spoken line (max 250 chars); TTS input |
| `action` | Whiteboard card text drawn on the board |
| `gesture` | One of 13 allowed gestures (wave, point, explain, shrug, etc.); drives FK rig animation in gestures_fk.js |
| `camera_move` | zoom_in, zoom_out, pan_left, pan_right, shake, or static; passed to motion plugin |
| `pose` | Coarse body pose enum (idle, waving, jumping, shocked, laughing) |
| `transition` | Scene-to-scene edit (cut, fade, wipe, none) |
| `is_punchline` | Tags the climax scene; used for still-image preview export |
| `cast` | v2 — which characters appear in this scene |
| `layout` | v2 — "cards" (whiteboard) or "stage" (characters front) |
| `shots` | v2 — list of `Shot` objects with start/end ms, type (wide/close_up), zoom, ease |
| `visuals` | v2 — list of `Visual` objects; each has `type` (flow, request_response, typed_code, step_ladder, check_cross, counter), `trigger_word` (synced to speech), and `params` |
| `word_timings` | v2 — per-word ms offsets from TTS alignment; drives visual triggers and annotation drawing |
| `annotations` | (unverified — not found as a named field in models.py; annotation logic lives in `animejs/annotations.py`) |

---

## 5. Plugins

**Registration**: decorator-based. Each plugin applies `@register_llm("name")`, `@register_voice("name")`, `@register_renderer("name")`, or `@register_motion("name")` from `core/registry.py`. Auto-discovery in `plugins/__init__.py` imports all plugin modules at startup, triggering the decorators. No changes to pipeline or registry needed to add a new one.

| Type | Existing plugins | Notes |
|------|-----------------|-------|
| LLM | `fake`, `gemini` | fake = deterministic offline mock; gemini = live Gemini screenplay + critic |
| Voice | `fake`, `gemini_tts`, `piper`, `windows_sapi` | fake = mock WAV; piper = local binary subprocess; sapi = pyttsx3 |
| Renderer | `animejs` (prod), `fake`, `pillow`, `cairo`, `blender3d`, `gemini` | animejs = HTML5+Playwright; others are alt/experimental |
| Motion | `ffmpeg`, `static` | ffmpeg = mathematical filter chain pan/zoom/shake; static = no motion |
| Graphics | `blue_blood_drop`, `draw_svg`, `hearts_pop`, `kinetic_words`, `octopus_vector` | Sub-plugins used by animejs renderer for stage visuals; not in main registry |

---

## 6. Characters

| Pack | Format | Gesture-ready? |
|------|--------|---------------|
| `boy_b` | SVG layers (named body parts) + PNG rasters | Yes — FK rig: fk_arm_r/l, fk_arm_lower_r/l, fk_head_base; full gesture pose set |
| `girl_a` | SVG layers + PNG rasters (same structure as boy_b) | Yes — same FK rig |
| `stick_hoodie` | PNG rasters only (face variants: happy/sad/shocked/talking etc.) | Yes — face-swap per emotion; 7 face states |
| `presenter` | Single SVG + manifest.json | Partial — arm-gesture element fallback only |
| `boy_a` | Staging PNG poses only | Unknown — no layers/ or vector/ found |

Character loading is split: `core/character_pack.py` handles SVG pack validation; `core/character2d.py` (43KB, largest file) handles FK skeleton layered rendering.

---

## 7. Camera, Depth Layers, Gestures, Board Animation

All live across modular templates in `src/toonshorts/plugins/render/animejs/templates/` (`rough_draw.js`, `stage_visuals.js`, `camera_engine.js`, `gestures_fk.js`, `main.js`) and the surrounding animejs module.

**5 most important functions across animejs modular templates**

| Function | What it does |
|----------|-------------|
| `initRoughSketches()` (`rough_draw.js`) | Page-load setup — creates Rough.js hand-drawn title underlines, card circles, and arrows; sets up stroke-dasharray for progressive draw |
| `computeCameraState(ms, frameIdx)` (`camera_engine.js`) | Deterministic multiplane camera — builds a timeline of preset positions (wide, boy_close, girl_close, board_close), interpolates with smootherstep, adds sine-wave drift and slow push-in; returns camX/camY/camZoom/driftRot |
| `applyMultiplaneParallax(camState)` (`camera_engine.js`) | Applies 4 depth layers (foreground ×2.0, subject ×1.0, board ×0.5, deep-bg ×0.12) to DOM elements; adds rack-focus blur between board and subject |
| `window.seekAnimation(ms)` (`main.js`) | Main per-frame update called by Playwright at every captured timestamp — orchestrates mouth sync, eye blink, breathing bob, FK gesture animation, annotation stroke drawing, word-card highlighting, stage visuals |
| `window.updateStageVisuals(ms)` (`stage_visuals.js`) | Drives board visual templates synced to ms — flow arrows, request/response packets, typed code reveal, step ladders, check/cross reveals, counter roll-ups |

Supporting files: `animejs/capture.py` (Playwright headless stepping + FFmpeg pipe), `animejs/html_builder.py` (injects all JSON into `window.__` globals), `animejs/annotations.py` (card layout, word-sync sketch), `animejs/gestures.py` (gesture whitelist + resolve), `plugins/motion/ffmpeg.py` (final MP4 pan/zoom/shake filter chain).

---

## 8. Tests

| Suite | Location | Count |
|-------|----------|-------|
| Fast unit tests | `tests/unit/` (29 files) | **202 tests** |
| Slow / contract | `tests/smoke/` + `tests/contract/` | 13 tests |
| Total | | 215 |

Run fast tests: `python -m pytest tests/unit -q`  
Run slow tests: `python -m pytest tests/smoke tests/contract -q`  
Run by marker: `python -m pytest -m slow`

The skipped live Gemini test is in `tests/contract/test_llm_contract.py` line 24 — it calls `pytest.skip()` when the Gemini network is unavailable (catches `RuntimeError` from `generate_plan()`).

---

## 9. Known Weak Spots

1. **Critic bypass**: if Gemini's critic response fails JSON schema validation, score defaults to 7.5 (≥ 7.0 pass threshold) — the screenplay is never rewritten even if flawed. `plugins/llm/gemini.py:evaluate_script()`.
2. **Renderer compat shim**: pipeline wraps `renderer.render_all_scenes()` in a `TypeError` waterfall to handle renderers that don't accept `scene_audios=` or `fast=` kwargs — fragile duck-typing.
3. **Stale KNOWN_ISSUES reference**: `KNOWN_ISSUES.md` mentions `plugins/voice/edge_tts.py` with a hardcoded 3.0s fallback, but that file does not exist in the current codebase.
4. **Windows reserved filename gap**: `core/models.py:sanitize_filename()` strips illegal characters but does not block Windows reserved names (CON, NUL, COM1–9, etc.).
5. **Subtitle silent failure**: if FFmpeg lacks `libass`, subtitles are silently omitted and the unsubtitled video is kept. No user-visible error. `core/assembler.py`.
6. **GenAI SDK deprecation**: `google/genai/types.py:42` uses `_UnionGenericAlias`, deprecated in Python 3.14+, broken in 3.17. Surfaces as a warning on every test run.
7. **Split files**: `core/character2d.py` (split into `fk_solver.py` and `svg_renderer.py`), `templates/script.js` (split into 5 modular template files). Remaining large files: `plugins/render/cairo.py` (34KB), `core/character_pack.py` (31KB).
8. **Compat re-export sprawl**: `models.py`, `schemas.py`, `client.py`, `config.py`, `voice.py`, `subtitles.py` at the package root are thin re-exports of `core.*` equivalents — kept for backwards compatibility but add navigation noise.

---

## 10. Where to Start (First 6 Files, In Order)

| Order | File | Why |
|-------|------|-----|
| 1 | `docs/CODEMAP.md` | Self-updating map of every module, its purpose, and its Used-by list — the fastest orientation |
| 2 | `src/toonshorts/core/models.py` | Defines `ScriptPlan`, `Scene`, `Character`, `Visual`, `Shot` — the data contract everything else passes around |
| 3 | `src/toonshorts/core/pipeline.py` | The orchestrator — read `run_pipeline()` and `run_pipeline_from_brief()` to see the full flow |
| 4 | `src/toonshorts/core/registry.py` | Tiny file; shows exactly how plugins register and are looked up |
| 5 | `src/toonshorts/plugins/render/animejs/plugin.py` | Entry point for the production renderer — shows how a scene JSON becomes frames |
| 6 | `src/toonshorts/plugins/render/animejs/templates/main.js` | The animation engine entry point; read `camera_engine.js` and `main.js` first |
