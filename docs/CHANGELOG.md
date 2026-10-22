# Changelog

- 2026-10-22: Standardized character pack manifest schema (anchors, safe_bounding_box, default_slot, scale, allowed_gestures) and upgraded SVG security to element allowlist with strict URI/event safety.
- 2026-10-22: Unified boy_a SVG front hair into single continuous closed path eliminating seams and gaps between crown and forehead bangs while keeping eyebrows clear.
- 2026-10-22: Built 2D character pack system with boy_a reference sheet vectorization, layered SVG code (<20 KB, flat 2-tone look, no gradients, clean hair-eyebrow clearance), safe loading with XXE/script defense, swappable eye/mouth states, and interactive test staging.

- 2026-10-22: Completed safe cleanup: sanitized secrets in .env.example, removed hardcoded script intercept in gemini plugin with fallback error, deleted obsolete root styles and assets, simplified blender3d plugin to robot-only, and synchronized documentation.
- 2026-10-22: Redesigned whiteboard short style with progressive stroke-by-stroke SVG drawing synced to Whisper word timings, 7-layer character head architecture, physically attached hands/arms with smooth easing, and 100% constant studio set with fixed camera across scenes.
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
