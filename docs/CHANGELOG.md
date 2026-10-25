# Changelog

- 2026-10-25: part 4 roadmap: created docs/ROADMAP.md documenting remaining project steps and future milestones from Appendix D.

- 2026-10-25: part 3 v5 stills and fast preview review: generated camera_plan.json, acting_plan.json, rendered key scene stills and 540x960 fast preview for How_hackers_actually_break_into_systems_v5, validated with check-camera, check-acting, check-layout, and check-visuals, and documented visual_review.md.

- 2026-10-25: part 2 acting skill and plan: implemented Appendix C acting skill, core acting planner generating acting_plan.json with beats, accents, gestures, gaze, turns, listener reactions, pointing slots, and check-acting CLI.

- 2026-10-25: part 1 camera language: implemented Appendix A presets, transitions, zoom cap 1.9, depth parallax math, bg blur smoothstep ramp, check-camera CLI tool, and character slice sharpness tests.

- 2026-10-25: part 0 baseline verification: verified repo hygiene, fixed postponed annotations in models.py, validated Gemini script generation from idea, and recorded Gemini image API modality status.

- 2026-10-25: voice matching and audio assembly fix: restored gender-aware character voice assignment for Puck and Aoede, ensuring 100% TTS library cache hits and high-quality dialogue voiceover in How_hackers_actually_break_into_systems_v4.

- 2026-10-25: full-quality v4 render with automatic layouts and calm background: rendered 1080x1920 How_hackers_actually_break_into_systems_v4 with automatic layouts, restored pop-in overshoot, registered 2FA image, verified 10/10 visual review, and documented per-scene visual_review.md.

- 2026-10-25: calm topic-aware background and pixel contrast check: created calm dimmed/blurred monitor variant, bumped BACKGROUND_DESIGN_VERSION to 2, archived legacy backgrounds, added cached slowly drifting topic-aware elements layer under board, and enforced automated contrast check (>= 4.5:1) for text and thin strokes.

- 2026-10-25: register-image command, single-save indexing, and visual-check review: added register-image CLI validating formats (PNG/JPEG/WebP) and dimensions, re-encoding and stripping metadata, caching in library/elements/images/ by deterministic key, updated directing asset planning, and added registered image quality review to visual-check.

- 2026-10-25: automatic layout planning and directing validation: added plan_scene_layout and plan_script_layouts with template rules (hero, split, chain, stack, title-card), updated toon-shorts-directing skill with mandatory layout blocks, enforced plan validation rejecting missing layouts or conflicting slot bounds, and verified parity against hackers v3 layouts.

- 2026-10-25: layout motion margin, restored bounce overshoot, layout elements, and staggered balance: added ~12% inner motion margin to layout slots, restored pop-in overshoot preset to 1.14 while passing peak overshoot sampling, integrated title and keyword cards as layout elements, and evaluated visual balance only when all planned beat elements are visible.

- 2026-10-25: layout planned stills review: planned and rendered 7 scene stills for How_hackers_actually_break_into_systems_v3 using layout templates and board objects, resolved base64 asset encoding, verified zero layout violations and 10/10 visual review, and documented visual_review.md.

- 2026-10-25: image asset planning, travel and wobble presets, and test isolation: wired image asset planning with library lookup first into pipeline, added travel and pop-with-wobble animation presets, generated real 2FA shield asset, and isolated fast preview test to temporary directory.

- 2026-10-25: layout checks and comparison: extended layout verification with continuous beat-time sampling every 100ms and enter/exit, pairwise overlap, slot boundary containment, 3-element concurrency, horizontal visual balance warning, and check-visuals still-to-layout plan comparison.

- 2026-10-25: board visual layout planning: implemented deterministic layout templates (hero, split, chain, stack, title-card) with slot bounds, element lifecycle, and declared corner badge overlap validation.


- 2026-10-24: re-rendered hackers v2: authored custom Level 1 board visuals and Level 2 particle/radar effects with timing persistence, generated 1080x1920 MP4 video in 328s with manifest tracking, and documented 2-round visual review.

- 2026-10-24: images and references: added reference intake with purpose notes and theme analysis draft, strict guard against copying reference images, single-save library indexing in library/elements/images/, background removal cutouts with torn-paper edge masks and soft shadows, image safety checks, and 5 data-driven image animation presets.

- 2026-10-24: verification and hardening: added Level 2 infinite loop protection test with per-frame timeout and clean browser termination, enforced critic review threshold on pre-authored scene files, and added tree-sitter and playwright dependencies to requirements.

- 2026-10-24: phase 3 tools actually used: added asset planning step to directing skill, element indexing and single-save deduplication in library/elements/<type>/, and manifest tools_used tracking across skills, image generation, library hits, and custom visuals.

- 2026-10-24: phase 2 quality gate: added visual review checklist and automated contrast-ratio inspection, check-visuals command, up to 2 fix rounds before rendering, and critic score threshold stops (< 7.0) with --allow-low-score override.

- 2026-10-24: phase 1 safe foundation: deterministic background cache key without camera/split flags with library reuse, parse-based SVG sanitizer, custom board visuals (Level 1 presets & Level 2 AST scanner), and hardened Playwright render sandbox.

- 2026-10-24: audio-visual sync: enforced mandatory Whisper word timing with monotonic fuzzy script alignment, automatic trigger word resolution, 150ms sync verification report, explicit --allow-fallback flag, and work/ directory tidying.

- 2026-10-24: layout and split camera zones: enabled split camera zones by default, neutralized board layer negative offset, and added automated safe-zone layout verification in pipeline and CLI.

- 2026-10-24: test video pipeline: added pre-authored scene source option to CLI and pipeline, generated full-quality 1080x1920 test video 'How hackers actually break into systems' with Gemini TTS and night_studio style.

- 2026-10-24: shared folder cleanup: removed legacy references to briefs/, output/, temp/, and cache/, archived legacy contents into _old_cleanup_20261024/, and redirected all output to self-contained video folders.

- 2026-10-24: self-contained video folders: reorganized file handling into self-contained videos/<name>/ folders, library/ reusable asset cache, exists-guard, and clean failure recovery.

- 2026-10-24: camera framing: corrected camera preset signs in config.py, added dynamic bounds safety clamp inside parallax engine, synchronized FK limb poses prior to clamp evaluation, and verified zero edge clipping across all scenes.

- 2026-10-24: annotations: fixed underline alignment, resting position measurement, keyword-scoped wrapping, idempotent Rough.js init, clean topic headings, and subtitle escaping.

- 2026-10-24: split camera zones: implemented independent board and character camera zones preventing cut-off speakers, bounding box containment and safe zone clearance verification, and peak zoom stills.

- 2026-10-24: phase4b-6: optimized render speed via pre-rendered parallax layer image caching and filter cache invalidation fix, verified camera moves, and added edge tests & scene edge-case test suite.

- 2026-10-24: phase4b-5: Remotion trial spike comparing kinetic words & diagram flow overlay compositing, determinism, performance, and license evaluation.

- 2026-10-24: phase4b-4: board objects engine with 6 fixed types, slot overlap allocation, strict security caps (8 objects, 80 chars, 6 nodes), Rough.js per-object seed, and textContent DOM injection.

- 2026-10-24: phase4b-3: 3-layer vector SVG parallax background (far, mid, near) with configured depths, 300px boundary oversizing, and fast mode blur suppression.

- 2026-10-24: phase4b-2: style profile extractor, safe SVG palette parsing, single style per video enforcement, and toon-shorts-style skill.

- 2026-10-24: phase4b-1: purposeful camera shot plan with lead-in moves, hold constraints, easeInOutCubic transitions, zero continuous drift, and timeline reporting.

- 2026-10-23: Phase 4C: implemented word-aligned Rough.js annotations synchronized with speech timings, text content validation, and strict JSON/textContent XSS safety.

- 2026-10-23: Phase 4B: implemented deterministic FK right arm snap to active visual targets clamped to [-75.0, -35.0] with graceful fallback.

- 2026-10-23: Phase 4A: implemented closed-form damped spring camera zoom for punch-ins with bounded overshoot (1.066x) and zero accumulated state.

- 2026-10-23: Phase 3b hardening: enhanced thread-safe browser and process registry for parallel worker pool, guaranteeing zero leaked browser or FFmpeg processes and full temp cleanup on interrupt or failure.

- 2026-10-23: Phase 3 performance: added fast draft mode (540x960, 15fps, roughness 0, blur off) and parallel scene rendering in Anime.js (worker pool 1-4, deterministic scene seeding, safe error handling and tempfile cleanup) cutting render time by more than 2x.
- 2026-10-23: Phase 2b cleanup: removed obsolete monolithic script.js and redundant fallback injection, updated architecture overview docs, and retained tools/verify_raw_split.py.
- 2026-10-23: Phase 2: split script.js into modular templates (camera_engine, gestures_fk, rough_draw, stage_visuals, main) with fixed-order local loading & error detection, and separated FK math into fk_solver.py and rendering into svg_renderer.py with identical raw browser frame determinism.
- 2026-10-23: Phase 1b hardening: added MAX_CRITIC_REWRITES limit alert for critic re-plans and live FFmpeg execution test with Windows drive path and spaces.
- 2026-10-23: Phase 1: fixed critic bypass with single repair attempt & 6.0 fallback, added FFmpeg libass preflight check with Windows path escaping, enhanced filename sanitizer for Windows reserved names, and replaced TypeError cascade with explicit renderer capability flags.
- 2026-10-23: Phase C: defined 2D full-body rig contract, updated vector generator and inventory labeling for gesture-ready status, and implemented FK gesture rig animation and director in Anime.js.
- 2026-10-23: Phase B: implemented 4 multiplane depth layers in night_studio, deterministic camera motion (speaker focus, board focus, drift, punch-in, rack focus blur), and spring-overshoot board animations.
- 2026-10-23: Phase A fixes: mapped speaker voices (Boy/boy_b -> Puck, Girl/girl_a -> Aoede), stripped speaker label prefixes across board, subtitles, kinetic text and TTS, and reserved clear subtitle strip in night_studio layout.
- 2026-10-23: Built night_studio theme with dark board panel, code editor backdrop, LED glow pulses, city window twinkling, motion graphics plugins (kinetic_words, draw_svg, octopus_vector, hearts_pop, blue_blood_drop), word timing alignment, and octopus_facts_v2 stills preview.
- 2026-10-23: Upgraded boy_b and girl_a vector character packs to full 27-layer modular SVGs passing CharacterPack.validate() with zero errors, added vector subpack loading and honest inventory validation with broken_packs listing, and deleted invalid octopus stickman graphic.

- 2026-10-22: Added video intake step, dynamic inventory command (toonshorts.inventory), brief validation and serialization (briefs/<video-name>.json), key scene stills rendering, and directing skill intake rules.
- 2026-10-22: Fixed front SVG assembly z-ordering (tucking neck and upper arm caps under torso) to prevent sleeve overlap on girl_a's vest, continuous dark crew-neck t-shirt underlay without exposed waistband/button, and reconstructed authentic raster back views for boy_b and girl_a.
- 2026-10-22: Refined girl_a torso garment structure with crew-neck collar, curved sleeveless waistcoat lapels, and denim waistband/fly, and reconstructed full back view vector layers (torso_back, shoe_back_left/right, leg_upper_back_left/right) across 27 SVG layers for boy_b and girl_a character packs.
- 2026-10-22: Fixed hair facet holes and white spot transparency in boy_b and girl_a vector character packs with solid silhouette underlays, and upgraded shoes to authentic 3/4 perspective faceted sneakers with contoured soles and laces matching reference artwork.
- 2026-10-22: Refined boy_b and girl_a vector character packs: corrected boy_b elbow split to waist level with full hoodie sleeves and cuffs, aligned girl_a knee/ankle pivots with joint cap centers, and added layer_paths to manifest schemas.
- 2026-10-22: Rebuilt boy_b and girl_a character packs as clean vector (SVG) layers with elbow/knee splits, 22 independent layers each, direct fills/strokes, consistent 1000x1500 viewBox, redrawn shoes/hands/hair, and multi-resolution preview sheets in vector/ subfolders.

- 2026-10-22: Batch 5 asset migration: relocated golden baselines from output/ to tests/fixtures/golden/, updated tools, and cleaned output directory.

- 2026-10-22: Batch 4 asset migration: preserved Piper voice model and fallbacks, pruned redundant scratch and test audio duplicates without invalidating TTS cache.

- 2026-10-22: Batch 3 asset migration: migrated assets3d/ to assets/3d/, removed obsolete stickman tests, pruned stale licenses, and updated 3D blender references.

- 2026-10-22: Batch 2 asset migration: moved assets2d/ to assets/2d/, updated character pack references to paths module, and eliminated assets2d root directory.

- 2026-10-22: Batch 1 asset migration: consolidated incoming sources to assets/sources/incoming/, pruned boy_a debug staging crops, and removed duplicate reference_card.

- 2026-10-22: Built and refined two new full-body layered character packs (boy_b and girl_a) with 22 transparent layers each, clean antialiased eye/mouth diffing, torso/limb crops free of head artifacts, gapless rotation caps, manifest schemas, and preview sheets.
- 2026-10-22: Completed Scene Format v2 testing, XSS plain text verification, golden baseline comparisons, and full test suite validation with fast and full-size renders.

- 2026-10-22: Updated Gemini planner prompt and validation retry logic for scene format v2 and board visuals, and updated fake LLM with v2 What is an API fixture.

- 2026-10-22: Fixed listener eye glance direction in mirrored right character slot so pupils always point toward speaker on screen, and added unit tests for both slot configurations.

- 2026-10-22: Configured pytest slow marker for end-to-end and browser renders, enabling fast daily test execution via -m 'not slow'.

- 2026-10-22: Added --fast preview mode limiting video to 6s, half resolution (540x960), 15 fps, saved to output/fast/ with cached audio and zero Gemini API calls.

- 2026-10-22: Refactored whiteboard animejs renderer into small modular package (<300 lines each) with external CSS, JS, and HTML templates, verified against golden baseline renders.

- 2026-10-22: Refined character packs: unified Presenter hairline into smooth continuous silhouette clearing eyebrows with seamless temple sideburns and golden rim sidelight; realigned Boy A ears upward (~55px) to natural eye/nose height with tight head base anchoring and synchronized hair-back framing.
- 2026-10-22: Integrated 2D character packs into whiteboard renderer with left/right slots, mirrored right placement, speech-driven mouth sync for active speaker, idle blinks/glances for listeners, and gesture resolution with warnings.
- 2026-10-22: Extracted whiteboard presenter into modular character pack with swappable arm rigs, 4 mouth states, and eye look/blink states.
- 2026-10-22: Standardized character pack manifest schema (anchors, safe_bounding_box, default_slot, scale, allowed_gestures) and upgraded SVG security to element allowlist with strict URI/event safety.
- 2026-10-22: Unified boy_a SVG front hair into single continuous closed path eliminating seams and gaps between crown and forehead bangs while keeping eyebrows clear.
- 2026-10-22: Built 2D character pack system with boy_a reference sheet vectorization, layered SVG code (<20 KB, flat 2-tone look, no gradients, clean hair-eyebrow clearance), safe loading with XXE/script defense, swappable eye/mouth states, and interactive test staging.

- 2026-10-22: Completed safe cleanup: sanitized secrets in .env.example, removed hardcoded script intercept in gemini plugin with fallback error, deleted obsolete root styles and assets, simplified blender3d plugin to robot-only, and synchronized documentation.
- 2026-10-22: Redesigned whiteboard short style with progressive stroke-by-stroke SVG drawing synced to Whisper word timings, 7-layer character head architecture, physically attached hands/arms with smooth easing, and 100% constant studio set with fixed camera across scenes.
- 2026-10-22: Implemented deterministic time-based visual animation engine in Anime.js whiteboard renderer with Whisper word alignment, progressive stroke reveals, eased packet motion, and subtle icon bobbing.
- 2026-10-22: Added visual templates system (flow, request_response, typed_code, step_ladder, check_cross, counter) with strict param validation, named palettes, XSS prevention, and stage layout overflow detection.
- 2026-10-22: Added Scene Format v2 with versioning adapter, directing validator enforcing camera rules (zoom <= 1.35, ease 0.4-0.6s, hold >= 1.2s, max 1 zoom per 5s, target in cast, inside scene length), and strict extra-field rejection.
- 2026-10-21: Polished whiteboard visual composition with gradient background, board glow, vignette, warm presenter side-light, dynamic Rough.js sketch annotations (title underline, number circles, inter-card arrows), safe area gesture boundaries, and enhanced subtitles.

- 2026-10-21: Fixed anime.js audio padding and scene video duration alignment to prevent subtitle drift, enforced WAV container wrapping for raw PCM Gemini speech, added relative-path Playwright URI support, and added corrupt cache recovery tests.
- 2026-10-21: Built full ~30s whiteboard explainer pipeline with Gemini TTS voice, SHA-256 disk audio caching, immediate quota-error abort, 2D character desk rig with loudness mouth-sync, and anime.js easing.
- 2026-10-21: Implemented Anime.js swappable HTML animation renderer plugin with local bundling, easing transitions, Playwright frame capture, and voice-synced whiteboard scene.

- 2026-10-21: Processed uploaded character reference sheet, updated incoming assets and character registry, and generated 2D comedy short video with Piper TTS, audio loudness lip-sync, and burned ASS subtitles.
- 2026-10-21: Implemented 2D layered character system from image-model sheet, coordinate layout slicing, character registry, forward kinematics skeleton, audio loudness mouth shapes, and squash/stretch action rendering.
- 2026-10-21: Implemented 2D stickman vector rendering engine with Pycairo, featuring forward-kinematic 2D skeleton, facial expressions, squash and stretch actions, hand-drawn room background, and modular garment slot system.
- 2026-10-21: Implemented 3D item and accessory catalog system, multi-character composition, and 4-beat animated story video pipeline with procedural facial lip sync and burned ASS subtitles.
- 2026-10-21: Created 3D stickman character with humanoid skeleton, joint spheres, thin capsule limbs, toon cel-shading, Freestyle outlines, and retargeted robot animations (Walking, Running, Jump, Wave).
- 2026-10-21: Built stylized 3D stick-figure character rig, CMU mocap motion library retargeting, 3D sets, props, and blender3d rendering plugin with caps and pre-flight validation.
- 2026-10-21: Migrated project to C:\dev\toon-shorts, configured Python 3.11 .venv, added FFmpeg subtitles filter startup check, and pinned dependencies in pyproject.toml.
- 2026-10-21: Replaced Edge-TTS and synthetic tone generator with pluggable voice engines (gemini_tts, piper, windows_sapi), voices.json licensing checks, speech verification, and faster-whisper word alignment.
- 2026-10-21: Restructured toon-shorts into a modular plugin-based layout with self-updating documentation and contracts.
