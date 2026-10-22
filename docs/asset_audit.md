# Asset Audit & Single-Root Migration Plan

> **Status**: REPORT ONLY. No files, code, or assets have been moved, renamed, deleted, or committed.
> **Target Layout**: Single root `assets/` (`assets/sources/`, `assets/2d/`, `assets/3d/`, `assets/voices/`, etc.) with `assets2d/` and `assets3d/` merged, and `output/` strictly reserved for generated render results.

---

## 1. Executive Summary & Quick Counts

| Category | Count | Details |
| :--- | :--- | :--- |
| **Total Assets/Asset-like Files Indexed** | **1014** | `assets/` (11), `assets2d/` (128), `assets3d/` (3), `output/` (766), Outside (106) |
| **Exact Duplicate Groups (Hash Collisions)** | **109** | 2 in assets/assets2d, 7 cross-folder (audio/scratch), 100 in output/ |
| **Near-Duplicate Groups** | **8** | Resolution/format variants of sources, sheet cards, and test frames |
| **Broken References** | **17** | 14 missing acceptance renders in `output/stickman_acceptance`, 1 missing fallback binary in `assets/piper/piper.exe`, 2 obsolete docs/licenses |
| **Unused Files (Zero Code/Manifest/Test Refs)** | **15** | Untracked large source crops, staging frame slices, unreferenced incoming cards |
| **Misplaced Files** | **41** | 2 input images & 6 test baselines in `output/`, 36 staging renders in `assets2d/` |
| **Active Reference Locations to Asset Folders** | **102** | Spread across 40 files in `src/`, `tests/`, `tools/`, and `docs/` |

---

## 2. Skipped Cache & System Directories

The following cache, environment, and version-control directory trees were discovered and explicitly skipped during asset auditing:
- `.git/`: Internal Git repository metadata and object store
- `.venv/` & `venv/`: Python virtual environment libraries and binaries
- `__pycache__/`: Python bytecode cache files (`.pyc`) across 485 package subdirectories
- `.pytest_cache/`: Pytest test execution cache and step failure database
- `.mypy_cache/`: MyPy static type check incremental cache
- `.ruff_cache/`: Ruff linter and formatter cache
- `node_modules/`: (None present, but excluded by scanning filter)

---

## 3. Inventory & One-Line Captions Grouped by Folder

### A. `assets/` (11 files)

| File / Group | Count | Caption (What it is, Character/Feature, Used by) |
| :--- | :---: | :--- |
| `assets/sources/boy_b_body.png` | 1 | Source body character art; boy_b; used by `tests/unit/test_new_character_packs.py` & `tools/build_character_packs.py` |
| `assets/sources/boy_b_face.jpg` | 1 | Source face expressions photo sheet; boy_b; used by `tests/unit/test_new_character_packs.py` & `tools/build_character_packs.py` |
| `assets/sources/boy_b_front_large.png` | 1 | High-res full front source body; boy_b; UNUSED (untracked source image) |
| `assets/sources/girl_a_body.png` | 1 | Source body character art; girl_a; used by `tests/unit/test_new_character_packs.py` & `tools/build_character_packs.py` |
| `assets/sources/girl_a_face.jpg` | 1 | Source face expressions photo sheet; girl_a; used by `tests/unit/test_new_character_packs.py` & `tools/build_character_packs.py` |
| `assets/sources/girl_a_front_large.png` | 1 | High-res full front source body; girl_a; UNUSED (untracked source image) |
| `assets/sources/hands_sheet.png` | 1 | Hand gestures source sheet; shared/character gestures; used by `tests/unit/test_new_character_packs.py` |
| `assets/sources/hands_sheet_lr.png` | 1 | Hand gestures source sheet left/right mirror; shared/character gestures; used by `tests/unit/test_new_character_packs.py` |
| `assets/voices/piper/en_US-lessac-medium.onnx` | 1 | Piper neural TTS ONNX voice model; Piper voice plugin; used by `src/toonshorts/plugins/voice/piper.py` & `tools/build_2d_hoodie_video.py` |
| `assets/voices/piper/en_US-lessac-medium.onnx.json` | 1 | Piper voice model configuration JSON; Piper voice plugin; used by `src/toonshorts/plugins/voice/piper.py` & `tools/build_2d_hoodie_video.py` |
| `assets/voices/piper/.gitkeep` | 1 | Directory placeholder marker; Piper voice directory; used by git |

### B. `assets2d/` (128 files)

| File / Group | Count | Caption (What it is, Character/Feature, Used by) |
| :--- | :---: | :--- |
| `assets2d/characters/boy_a/character.svg` | 1 | Vector character rig with swappable eyes/mouths; boy_a character; used by `src/toonshorts/core/character_pack.py` & `tests/unit/test_character_pack.py` |
| `assets2d/characters/boy_a/manifest.json` | 1 | Character pack metadata, anchors, allowed gestures; boy_a; used by `src/toonshorts/core/character_pack.py` & `tests/unit/test_character_pack.py` |
| `assets2d/characters/boy_a/staging/boy_a_contact_sheet.png` | 1 | Preview contact grid of boy_a mouth and eye states; boy_a staging; used by `tools/render_boy_a_preview.py` |
| `assets2d/characters/boy_a/staging/index.html` | 1 | Interactive visual staging inspector; boy_a staging; used by `tests/unit/test_character_pack.py` |
| `assets2d/characters/boy_a/staging/r*c*.png` (8 files) | 8 | Rendered state slices (closed, open, blink, look); boy_a staging; UNUSED intermediate debug renders |
| `assets2d/characters/boy_b/character.json` | 1 | Skeletal FK rig configuration with joints & pivots; boy_b; used by `src/toonshorts/core/character2d.py` & `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/boy_b/manifest.json` | 1 | Character pack manifest, z-ordering, pivots; boy_b; used by `src/toonshorts/core/character_pack.py` & `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/boy_b/layers/*.png` (22 files) | 22 | Transparent RGBA body, limb, mouth, and eye layers; boy_b; used by `character.json`, `manifest.json`, & `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/boy_b/staging/boy_b_preview_sheet.png` | 1 | Grid sheet of 11 verification poses; boy_b; used by `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/boy_b/staging/boy_b_source_comparison.png` | 1 | Side-by-side comparison with source photo; boy_b; used by `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/boy_b/staging/pose_*.png` (11 files) | 11 | Rendered verification poses (front, walking, arms, mouths); boy_b; used by `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/girl_a/character.json` | 1 | Skeletal FK rig configuration with joints & pivots; girl_a; used by `src/toonshorts/core/character2d.py` & `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/girl_a/manifest.json` | 1 | Character pack manifest, z-ordering, pivots; girl_a; used by `src/toonshorts/core/character_pack.py` & `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/girl_a/layers/*.png` (22 files) | 22 | Transparent RGBA body, limb, mouth, and eye layers; girl_a; used by `character.json`, `manifest.json`, & `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/girl_a/staging/girl_a_preview_sheet.png` | 1 | Grid sheet of 11 verification poses; girl_a; used by `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/girl_a/staging/girl_a_source_comparison.png` | 1 | Side-by-side comparison with source photo; girl_a; used by `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/girl_a/staging/pose_*.png` (11 files) | 11 | Rendered verification poses (front, walking, arms, mouths); girl_a; used by `tests/unit/test_new_character_packs.py` |
| `assets2d/characters/presenter/character.svg` | 1 | Vector character rig with swappable arm gestures and face states; presenter; used by `src/toonshorts/core/character_pack.py` & tests |
| `assets2d/characters/presenter/manifest.json` | 1 | Character pack manifest with allowed gestures and anchors; presenter; used by `src/toonshorts/core/character_pack.py` & tests |
| `assets2d/characters/stick_hoodie/character.json` | 1 | Skeletal FK rig configuration for 2D hoodie stickman; stick_hoodie; used by `src/toonshorts/core/character2d.py` |
| `assets2d/characters/stick_hoodie/layers/*.png` (32 files) | 32 | Transparent PNG body, limb, sleeve, face expression, and hand layers; stick_hoodie; used by `character.json` & `tools/build_2d_hoodie_video.py` |
| `assets2d/incoming/boy_a_sheet.png` | 1 | Input source sheet for boy_a vectorization; boy_a incoming; UNUSED (untracked) |
| `assets2d/incoming/reference_card.png` | 1 | Character design reference card; stickman incoming; UNUSED (exact duplicate of reference_sheet.png) |
| `assets2d/incoming/reference_sheet.png` | 1 | Character design reference card; stickman incoming; UNUSED |
| `assets2d/incoming/reference_uploaded.jpg` | 1 | Original uploaded reference photograph; stickman incoming; UNUSED |
| `assets2d/incoming/sheet_03.png` | 1 | Master sprite sheet for stick_hoodie slices; stick_hoodie; used by `tests/unit/test_character2d.py` & `tools/build_2d_hoodie_video.py` |
| `assets2d/incoming/target_poses.png` | 1 | Reference target pose specification sheet; stick_hoodie; used by `src/toonshorts/core/character2d.py` docstrings |
| `assets2d/layouts/sheet_03_layout.json` | 1 | Sprite coordinates and slice bounding boxes for sheet_03; stick_hoodie; used by `tests/unit/test_character2d.py` & `tools/build_2d_hoodie_video.py` |

### C. `assets3d/` (3 files)

| File / Group | Count | Caption (What it is, Character/Feature, Used by) |
| :--- | :---: | :--- |
| `assets3d/models/RobotExpressive.glb` | 1 | 3D GLTF robot model with armature & facial blendshapes; 3D robot feature; used by `src/toonshorts/plugins/render/blender3d.py` & `tests/unit/test_blender3d.py` |
| `assets3d/scripts/blender_render.py` | 1 | Standalone Blender headless rendering script; Blender 3D pipeline; used by `src/toonshorts/plugins/render/blender3d.py` |
| `assets3d/LICENSES.md` | 1 | CC-BY attribution and license information for 3D assets; 3D robot feature; used for legal documentation |

### D. `output/` (766 files)

| File / Group | Count | Caption (What it is, Character/Feature, Used by) |
| :--- | :---: | :--- |
| `output/What_is_an_API.mp4` | 1 | Protected golden reference full video; pipeline integration; verified by `tools/run_pack_tests.py`, `render_v2_pack.py`, `render_golden_baseline.py` |
| `output/fast/What_is_an_API_fast.mp4` | 1 | Fast preview generated video (540x960, 15fps); preview mode; verified by `tests/unit/test_fast_preview.py` |
| `output/pack_tests/golden/*.png` (6 files) | 6 | Golden baseline frame extracts (scenes 1 & 2); two-character whiteboard regression; generated by `tools/render_golden_baseline.py`, compared by `tools/compare_golden_split.py` |
| `output/pack_tests/*.mp4` (2 files) | 2 | Full test renders (test1_presenter_solo, test2_two_characters); test suite; generated by `tools/run_pack_tests.py` |
| `output/pack_tests/frames/*.png` (14 files) | 14 | Extracted video frame verification stills; test suite; generated by `tools/run_pack_tests.py` |
| `output/pack_tests/split_test/*.png` (6 files) | 6 | Extracted frames from modular visual renderer split; regression comparison; generated by test tools |
| `output/pack_tests/v2/*.mp4` (2 files) | 2 | Full-size (v2) and fast preview (v2_fast) rendered videos; scene format v2; generated by `tools/render_v2_pack.py` |
| `output/pack_tests/v2/frames/*.png` (6 files) | 6 | Extracted video frames for 2 visuals (before, mid, finished); scene format v2; generated by `tools/render_v2_pack.py` |
| `output/pack_tests/v2/temp_render/...` (58 files) | 58 | Scene clip MP4s, HTML templates, assembly concat lists, audio WAVs; scene format v2; generated by `tools/render_v2_pack.py` |
| `output/pack_tests/v2/tmp_audio/*.wav` (6 files) | 6 | Per-scene audio files; scene format v2; generated during v2 rendering |
| `output/pack_tests/temp_golden_render/...` (6 files) | 6 | Intermediate scene MP4 clips and logs; golden baseline rendering; generated by `tools/render_golden_baseline.py` |
| `output/pack_tests/test1_temp/...` (13 files) | 13 | Intermediate per-scene MP4s, HTML, and ffmpeg logs; presenter solo test; generated by `tools/run_pack_tests.py` |
| `output/pack_tests/test2_temp/...` (13 files) | 13 | Intermediate per-scene MP4s, HTML, and ffmpeg logs; two-character test; generated by `tools/run_pack_tests.py` |
| `output/renders2d/Gemini_Generated_Image_c6rp0kc6rp0kc6rp (1).png` | 1 | Raw source Gemini generation image; MISPLACED INPUT in output; UNUSED |
| `output/renders2d/contact_sheet_faces.png` | 1 | Contact sheet image; MISPLACED INPUT/INSPECTION in output; UNUSED |
| `output/renders2d/hoodie_video/frames/*.png` (488 files) | 488 | Rendered animation frames for stick_hoodie short; 2D hoodie video; generated by `tools/build_2d_hoodie_video.py` |
| `output/renders2d/hoodie_video/audio/*.wav` (6 files) | 6 | Synthesized beat audio clips and sound effects; 2D hoodie video; generated by `tools/build_2d_hoodie_video.py` |
| `output/renders2d/hoodie_video/stills/*.png` (4 files) | 4 | Keyframe stills (wave, walk, idle, run); 2D hoodie video; generated by `tools/build_2d_hoodie_video.py` |
| `output/renders2d/hoodie_video/captions.ass` & `master_audio.wav` | 2 | Subtitles and master audio track; 2D hoodie video; generated by `tools/build_2d_hoodie_video.py` |
| `output/previews/trial_robot/*.png` (13 files) | 13 | Rendered frames of 3D robot actions (jump, walk, wave); Blender 3D preview; generated by `src/toonshorts/plugins/render/blender3d.py` |
| `output/stage_character/boy_a/*.png` (10 files) | 10 | Debug cropped face tiles and contact sheet; boy_a character; generated by `tools/render_boy_a_preview.py` |
| `output/aligned_faces/`, `face_full_tiles/`, `face_inspect/`, `face_labels/`, `tile_inspect/`, `parts_inspect/` (108 files) | 108 | Intermediate debug crops, aligned facial tiles, and body slices for boy_b and girl_a; character pack builder; generated by `tools/build_character_packs.py` |

### E. Asset-Like Files Outside Asset/Output Folders (106 files)

| File / Group | Count | Caption (What it is, Character/Feature, Used by) |
| :--- | :---: | :--- |
| `cache/tts/*.wav` (7 files) | 7 | Cached Piper/Gemini synthesized voice clips keyed by sha256; Voice system; used by `src/toonshorts/plugins/voice/gemini_tts.py` & tests |
| `tests/fixtures/what_is_an_api_plan.json` | 1 | Integration test screenplay plan fixture; Pipeline test; used by `tests/contract/test_motion_contract.py` & `tools/render_golden_baseline.py` |
| `tests/fixtures/what_is_an_api_v2_plan.json` | 1 | Scene format v2 test screenplay plan fixture; Visuals engine; used by `tests/unit/test_v2_validation.py` & `tools/render_v2_pack.py` |
| `temp/test_robot_render.png` | 1 | Intermediate single-frame render; Blender 3D; generated by `tests/contract/test_render_contract.py` |
| `scratch/*.png` & `scratch/*.wav` (96 files) | 96 | Ad-hoc development experiments, stickman acceptance tests, audio extraction scratch files; Scratch workspace; UNUSED by production pipeline |
| `src/toonshorts/assets/vendor/anime-3.2.2.min.js` | 1 | Vendor JavaScript animation library; AnimeJS render engine; referenced by `src/toonshorts/core/config.py` (`ANIME_JS_PATH`) |
| `src/toonshorts/assets/vendor/rough-4.6.6.min.js` | 1 | Vendor JavaScript sketchy graphics library; AnimeJS whiteboard engine; referenced by `src/toonshorts/core/config.py` (`ROUGH_JS_PATH`) |

---

## 4. Reference Catalog: Every Mention Across Code, Tests, Tools, and Docs

Found **102 reference locations** across 40 files in the codebase.

### A. Production Core Code (`src/toonshorts/core/` & `src/toonshorts/`)

| File | Line | Target Mentioned | Code Snippet |
| :--- | :---: | :--- | :--- |
| `src/toonshorts/cli.py` | 89 | `output/` | `help="Fast preview mode: ... saved to output/fast/"` |
| `src/toonshorts/core/config.py` | 25 | `output/` | `OUTPUT_DIR = PROJECT_ROOT / "output"` |
| `src/toonshorts/core/config.py` | 28 | `assets/` | `ASSETS_DIR = PROJECT_ROOT / "assets"` |
| `src/toonshorts/core/config.py` | 31 | `assets/` | `ANIME_JS_PATH = PROJECT_ROOT / "src" / "toonshorts" / "assets" / "vendor" / "anime-3.2.2.min.js"` |
| `src/toonshorts/core/config.py` | 32 | `assets/` | `ROUGH_JS_PATH = PROJECT_ROOT / "src" / "toonshorts" / "assets" / "vendor" / "rough-4.6.6.min.js"` |
| `src/toonshorts/core/character2d.py` | 34 | `assets2d/` | `ASSETS2D_DIR = PROJECT_ROOT / "assets2d"` |
| `src/toonshorts/core/character_pack.py` | 25 | `assets2d/` | `CHARACTERS2D_DIR = PROJECT_ROOT / "assets2d" / "characters"` |

### B. Plugins (`src/toonshorts/plugins/`)

| File | Line | Target Mentioned | Code Snippet |
| :--- | :---: | :--- | :--- |
| `src/toonshorts/plugins/render/blender3d.py` | 154 | `assets3d/` | `self.script_path = config.PROJECT_ROOT / "assets3d" / "scripts" / "blender_render.py"` |
| `src/toonshorts/plugins/render/blender3d.py` | 155 | `assets3d/` | `self.robot_model = config.PROJECT_ROOT / "assets3d" / "models" / "RobotExpressive.glb"` |
| `src/toonshorts/plugins/voice/piper.py` | 42 | `assets/` | `# Place the voice files in: assets/voices/piper/` |
| `src/toonshorts/plugins/voice/piper.py` | 56 | `assets/` | `config.PROJECT_ROOT / "assets" / "piper" / "piper.exe"` |

### C. Test Suite (`tests/`)

| File | Line | Target Mentioned | Code Snippet |
| :--- | :---: | :--- | :--- |
| `tests/unit/test_blender3d.py` | 101 | `assets3d/` | `stickman_path = config.PROJECT_ROOT / "assets3d" / "models" / "Stickman.blend"` |
| `tests/unit/test_blender3d.py` | 102 | `assets3d/` | `robot_path = config.PROJECT_ROOT / "assets3d" / "models" / "RobotExpressive.glb"` |
| `tests/unit/test_blender3d.py` | 122 | `output/` | `out_dir = config.PROJECT_ROOT / "output" / "stickman_acceptance"` |
| `tests/unit/test_blender3d.py` | 140 | `output/` | `diff_file = config.PROJECT_ROOT / "output" / "stickman_acceptance" / "pixel_diffs.json"` |
| `tests/unit/test_character2d.py` | 29 | `assets2d/` | `sheet_src = PROJECT_ROOT / "assets2d" / "incoming" / "sheet_03.png"` |
| `tests/unit/test_character2d.py` | 30 | `assets2d/` | `layout_src = PROJECT_ROOT / "assets2d" / "layouts" / "sheet_03_layout.json"` |
| `tests/unit/test_fast_preview.py` | 5 | `output/` | `3. Verifies output is written strictly into output/fast/` |
| `tests/unit/test_fast_preview.py` | 41 | `output/` | `saved in output/fast/` |
| `tests/unit/test_fast_preview.py` | 64 | `output/` | `assert not normal_out.exists(), "... must be in output/fast/"` |
| `tests/unit/test_new_character_packs.py` | 3 | `assets/`, `assets2d/` | `Inputs: Assets in assets/sources/ and assets2d/characters/<id>/` |
| `tests/unit/test_new_character_packs.py` | 23 | `assets2d/` | `pack_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id` |
| `tests/unit/test_new_character_packs.py` | 70 | `assets2d/` | `layers_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id / "layers"` |
| `tests/unit/test_new_character_packs.py` | 113 | `assets2d/` | `layers_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id / "layers"` |
| `tests/unit/test_new_character_packs.py` | 134 | `assets2d/` | `layers_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id / "layers"` |
| `tests/unit/test_new_character_packs.py` | 156 | `assets2d/` | `staging_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id / "staging"` |
| `tests/unit/test_new_character_packs.py` | 184 | `assets/` | `Verifies original sources are saved in assets/sources.` |
| `tests/unit/test_new_character_packs.py` | 185 | `assets/` | `sources_dir = PROJECT_ROOT / "assets" / "sources"` |

### D. Tools and Helper Scripts (`tools/` & `assets3d/scripts/`)

| File | Line | Target Mentioned | Code Snippet |
| :--- | :---: | :--- | :--- |
| `assets3d/scripts/blender_render.py` | 65 | `assets3d/` | `model_path = project_root / "assets3d" / "models" / "RobotExpressive.glb"` |
| `tools/build_2d_hoodie_video.py` | 3 | `assets2d/` | `Inputs: Character reference sheet (assets2d/incoming/sheet_03.png)` |
| `tools/build_2d_hoodie_video.py` | 4 | `output/` | `Outputs: output/renders2d/hoodie_comedy_short.mp4` |
| `tools/build_2d_hoodie_video.py` | 37 | `output/` | `OUTPUT_DIR = PROJECT_ROOT / "output" / "renders2d"` |
| `tools/build_2d_hoodie_video.py` | 88 | `assets2d/` | `sheet_path = PROJECT_ROOT / "assets2d" / "incoming" / "sheet_03.png"` |
| `tools/build_2d_hoodie_video.py` | 89 | `assets2d/` | `layout_path = PROJECT_ROOT / "assets2d" / "layouts" / "sheet_03_layout.json"` |
| `tools/build_2d_hoodie_video.py` | 104 | `assets/` | `model_path = PROJECT_ROOT / "assets" / "voices" / "piper" / "...onnx"` |
| `tools/build_2d_hoodie_video.py` | 105 | `assets/` | `config_path = PROJECT_ROOT / "assets" / "voices" / "piper" / "...json"` |
| `tools/build_character_packs.py` | 3 | `assets/` | `Inputs: Source body and face sheets in assets/sources/` |
| `tools/build_character_packs.py` | 4 | `assets2d/` | `Outputs: ... in assets2d/characters/<id>/` |
| `tools/build_character_packs.py` | 844 | `assets2d/` | `base_dir = PROJECT_ROOT / "assets2d" / "characters" / char_id` |
| `tools/build_character_packs.py` | 850 | `assets/` | `sources_dir = PROJECT_ROOT / "assets" / "sources"` |
| `tools/compare_golden_split.py` | 12 | `output/` | `GOLDEN_DIR = PROJECT_ROOT / "output" / "pack_tests" / "golden"` |
| `tools/compare_golden_split.py` | 13 | `output/` | `SPLIT_DIR = PROJECT_ROOT / "output" / "pack_tests" / "split_test"` |
| `tools/generate_boy_a_svg.py` | 269 | `assets2d/` | `target_dir = Path("assets2d/characters/boy_a")` |
| `tools/render_boy_a_preview.py` | 10 | `assets2d/` | `svg_path = Path("assets2d/characters/boy_a/character.svg")` |
| `tools/render_boy_a_preview.py` | 13 | `output/` | `out_dir = Path("output/stage_character/boy_a")` |
| `tools/render_golden_baseline.py` | 3 | `output/` | `Saves 6 frames to output/pack_tests/golden/.` |
| `tools/render_golden_baseline.py` | 4 | `output/` | `Strictly protects output/What_is_an_API.mp4 and output/keep/.` |
| `tools/render_golden_baseline.py` | 26 | `output/` | `OUTPUT_DIR = PROJECT_ROOT / "output" / "pack_tests"` |
| `tools/render_golden_baseline.py` | 30 | `output/` | `PROTECTED_FILE = PROJECT_ROOT / "output" / "What_is_an_API.mp4"` |
| `tools/render_golden_baseline.py` | 153 | `output/` | `assert PROTECTED_FILE.stat().st_mtime == PROTECTED_MTIME` |
| `tools/render_v2_pack.py` | 4 | `output/` | `Fast preview render to output/pack_tests/v2/What_is_an_API_v2_fast.mp4` |
| `tools/render_v2_pack.py` | 5 | `output/` | `3 extracted frames per visual to output/pack_tests/v2/frames/` |
| `tools/render_v2_pack.py` | 6 | `output/` | `Full-size normal render to output/pack_tests/v2/What_is_an_API_v2.mp4` |
| `tools/render_v2_pack.py` | 7 | `output/` | `Strictly preserves output/What_is_an_API.mp4 and output/keep/.` |
| `tools/render_v2_pack.py` | 28 | `output/` | `OUTPUT_DIR = PROJECT_ROOT / "output" / "pack_tests" / "v2"` |
| `tools/render_v2_pack.py` | 31 | `output/` | `PROTECTED_ORIGINAL = PROJECT_ROOT / "output" / "What_is_an_API.mp4"` |
| `tools/render_v2_pack.py` | 37 | `output/` | `assert PROTECTED_ORIGINAL.stat().st_mtime == ORIGINAL_MTIME` |
| `tools/render_v2_pack.py` | 144 | `output/` | `Move the fast video from output/fast if generated there` |
| `tools/run_pack_tests.py` | 5 | `output/` | `Extracts frames ... into output/pack_tests/frames/.` |
| `tools/run_pack_tests.py` | 6 | `output/` | `Strictly protects output/What_is_an_API.mp4.` |
| `tools/run_pack_tests.py` | 25 | `output/` | `OUTPUT_DIR = PROJECT_ROOT / "output" / "pack_tests"` |
| `tools/run_pack_tests.py` | 31 | `output/` | `protected_file = PROJECT_ROOT / "output" / "What_is_an_API.mp4"` |
| `tools/run_pack_tests.py` | 234 | `output/` | `assert final_mtime == protected_initial_mtime` |
| `tools/test_layer_points.py` | 8 | `assets2d/` | `tree = ET.parse("assets2d/characters/boy_a/character.svg")` |

### E. Documentation (`docs/`, `LICENSES.md`, `README.md`)

| File | Line | Target Mentioned | Context |
| :--- | :---: | :--- | :--- |
| `LICENSES.md` | 10 | `assets3d/` | `- **Location**: assets3d/models/RobotExpressive.glb` |
| `LICENSES.md` | 26 | `assets3d/` | `- **Directory**: assets3d/motion/raw/*.bvh` |
| `LICENSES.md` | 31 | `assets3d/` | `See [assets3d/motion/LICENSES.md](assets3d/motion/LICENSES.md)` |
| `LICENSES.md` | 41, 50, 59, 68, 77 | `assets3d/` | Raw props location (`ice_cream.glb`, `cup.glb`, `table.glb`, `chair.glb`, `backpack.fbx`) |
| `LICENSES.md` | 89, 101 | `src/.../assets/` | Vendor assets (`anime-3.2.2.min.js`, `rough-4.6.6.min.js`) |
| `README.md` | 24 | `assets2d/` | `## 2D Layered Character System (assets2d/characters/stick_hoodie/)` |
| `docs/CHANGELOG.md` | 12 | `output/` | `saved to output/fast/ with cached audio` |
| `docs/FEATURES.md` | 69 | `assets3d/` | `src/toonshorts/plugins/render/blender3d.py, assets3d/scripts/blender_render.py` |
| `docs/FEATURES.md` | 175, 181, 187, 193, 199 | `assets2d/` | Character pack specifications for `presenter`, `boy_a`, `stick_hoodie`, `boy_b`, `girl_a` |

### F. Proposal for Centralized Paths Module: `src/toonshorts/core/paths.py`

> [!TIP]
> Currently, path construction is scattered across at least 15 modules and test files constructing `PROJECT_ROOT / 'assets2d'`, `PROJECT_ROOT / 'assets3d'`, etc., directly. Introducing a single module `src/toonshorts/core/paths.py` (or extending `src/toonshorts/core/config.py`) ensures that future directory renames require updating only ONE file.

```python
# src/toonshorts/core/paths.py (Proposed)
from pathlib import Path
from toonshorts.core.config import PROJECT_ROOT

ASSETS_DIR = PROJECT_ROOT / 'assets'
ASSETS_SOURCES_DIR = ASSETS_DIR / 'sources'
ASSETS_2D_DIR = ASSETS_DIR / '2d'
CHARACTERS_2D_DIR = ASSETS_2D_DIR / 'characters'
LAYOUTS_2D_DIR = ASSETS_2D_DIR / 'layouts'
ASSETS_3D_DIR = ASSETS_DIR / '3d'
MODELS_3D_DIR = ASSETS_3D_DIR / 'models'
SCRIPTS_3D_DIR = ASSETS_3D_DIR / 'scripts'
VOICES_DIR = ASSETS_DIR / 'voices'
PIPER_VOICES_DIR = VOICES_DIR / 'piper'
OUTPUT_DIR = PROJECT_ROOT / 'output'
TESTS_FIXTURES_DIR = PROJECT_ROOT / 'tests' / 'fixtures'
TESTS_GOLDEN_DIR = PROJECT_ROOT / 'tests' / 'golden'
```

---

## 5. Identified Problems

### A. Broken References (Files Deleted or Missing)
1. **`output/stickman_acceptance` (14 missing files)**:
   - Referenced by `tests/unit/test_blender3d.py:118-145`.
   - Missing files: `tpose.png`, `walking_01.png`, `walking_02.png`, `walking_03.png`, `running_01.png`, `running_02.png`, `running_03.png`, `jump_01.png`, `jump_02.png`, `jump_03.png`, `wave_01.png`, `wave_02.png`, `wave_03.png`, and `pixel_diffs.json`.
   - **Current Impact**: Causes 2 test failures in `test_blender3d.py` when running pytest.
2. **`assets/piper/piper.exe`**:
   - Referenced in fallback candidates in `src/toonshorts/plugins/voice/piper.py:56`.
   - The local binary is missing; engine falls back to system PATH. Recommend removing or pointing to standard tool location.
3. **`output/keep/`**:
   - Referenced in docstrings and comments of `tools/render_golden_baseline.py:4` and `tools/render_v2_pack.py:7`.
   - Folder does not exist on disk.
4. **`assets3d/motion/raw/*.bvh`, `assets3d/motion/LICENSES.md`, `assets3d/items/raw/*.glb/fbx`**:
   - Referenced in `LICENSES.md:26-80`.
   - Files were deleted or never committed; doc links are broken.

### B. Exact Duplicates (Matching SHA256 Hashes)
A total of **109 duplicate hash groups** were found:
- **Assets / Sources duplicates (2 groups)**:
  1. `assets2d/incoming/reference_card.png` == `assets2d/incoming/reference_sheet.png` (SHA256: `e6286e77...`, 129,162 bytes)
  2. `assets2d/characters/boy_a/staging/r1_c0_closed.png` == `assets2d/characters/boy_a/staging/r3_c0_neutral.png` (SHA256: `db746208...`, 75,591 bytes)
- **Cross-folder Audio Duplicates (7 groups)**:
  - Identical voice WAVs exist across `output/pack_tests/v2/temp_render/audio/`, `output/pack_tests/v2/tmp_audio/`, `cache/tts/`, and `scratch/test_voice/` for scenes 0 through 5.
- **Output internal duplicates (100 groups)**:
  - Identical face crops replicated across `output/aligned_faces/`, `output/face_inspect/`, and `output/tile_inspect/`.
  - Identical sound effects (`sfx_boing.wav`, `sfx_pop.wav`) and captions (`captions.ass`) copied across test folders.

### C. Near-Duplicates (Same Pack/Image Under Different Names/Scales)
1. **Boy B Source Bodies**: `assets/sources/boy_b_front_large.png` (796 KB, full resolution) vs `assets/sources/boy_b_body.png` (238 KB, cropped/scaled). `test_new_character_packs.py` references `boy_b_body.png`.
2. **Girl A Source Bodies**: `assets/sources/girl_a_front_large.png` (1,021 KB, full resolution) vs `assets/sources/girl_a_body.png` (232 KB, cropped/scaled). `test_new_character_packs.py` references `girl_a_body.png`.
3. **Hands Sheets**: `assets/sources/hands_sheet.png` (318 KB, full sheet) vs `assets/sources/hands_sheet_lr.png` (287 KB, split left/right). Both are referenced in `test_new_character_packs.py`.
4. **Reference Card**: `assets2d/incoming/reference_uploaded.jpg` (63 KB) vs `reference_sheet.png` (129 KB). Identical image converted to PNG.
5. **Golden vs Split Test Frames**: `output/pack_tests/golden/test2_s*.png` vs `output/pack_tests/split_test/test2_s*.png` vs `output/pack_tests/frames/test2_s*.png` (minor pixel differences between render modes).

### D. Unused Files
The following 15 files in `assets/` and `assets2d/` have zero references in code, manifests, tests, or tools:
- `assets/sources/boy_b_front_large.png` (untracked full front source)
- `assets/sources/girl_a_front_large.png` (untracked full front source)
- `assets/voices/piper/.gitkeep` (empty placeholder)
- `assets2d/incoming/boy_a_sheet.png` (untracked source sprite sheet)
- `assets2d/incoming/reference_card.png` (exact duplicate of reference_sheet.png)
- `assets2d/incoming/reference_sheet.png` (unreferenced reference image)
- `assets2d/incoming/reference_uploaded.jpg` (unreferenced original JPG)
- `assets2d/characters/boy_a/staging/r1_c0_closed.png` through `r4_c1_screen_right.png` (8 unreferenced intermediate stage crops)

### E. Misplaced Files
1. **Inputs stored in `output/`**:
   - `output/renders2d/Gemini_Generated_Image_c6rp0kc6rp0kc6rp (1).png`: Raw AI source image sitting in output.
   - `output/renders2d/contact_sheet_faces.png`: Reference input sheet sitting in output.
   - `output/pack_tests/golden/*.png` (6 files): Golden test comparison frames stored in `output/` (which is gitignored and ephemeral) rather than `tests/golden/` or `tests/fixtures/`.
2. **Generated/Intermediate Results stored in `assets/` & `assets2d/`**:
   - `assets2d/characters/boy_a/staging/` (10 files): Rendered contact sheets and HTML viewer.
   - `assets2d/characters/boy_b/staging/` (13 files): Rendered verification pose stills and preview sheets.
   - `assets2d/characters/girl_a/staging/` (13 files): Rendered verification pose stills and preview sheets.
   - `assets2d/incoming/` (6 files): Raw/in-progress incoming sources mixed with processed production assets.
3. **Code in Assets**:
   - `assets3d/scripts/blender_render.py`: Executable Python automation script placed under `assets3d/scripts/` rather than `src/toonshorts/plugins/render/` or `tools/`.

---

## 6. Migration Plan to Single-Root `assets/` Layout

### A. Path Mapping Table

| Current Path | Target Path | Action | Reason |
| :--- | :--- | :---: | :--- |
| `assets/sources/*` | `assets/sources/*` | **Keep** | Already conforms to target single-root layout |
| `assets2d/incoming/*` | `assets/sources/incoming/*` | **Move** | Consolidates all raw input sheets under `assets/sources/` |
| `assets2d/characters/boy_a/` | `assets/2d/characters/boy_a/` | **Move** | Migrates vector character pack into single-root `assets/2d` |
| `assets2d/characters/boy_b/` | `assets/2d/characters/boy_b/` | **Move** | Migrates raster layered character pack into `assets/2d` |
| `assets2d/characters/girl_a/` | `assets/2d/characters/girl_a/` | **Move** | Migrates raster layered character pack into `assets/2d` |
| `assets2d/characters/presenter/` | `assets/2d/characters/presenter/` | **Move** | Migrates vector presenter pack into `assets/2d` |
| `assets2d/characters/stick_hoodie/` | `assets/2d/characters/stick_hoodie/` | **Move** | Migrates 2D layered stickman into `assets/2d` |
| `assets2d/layouts/*` | `assets/2d/layouts/*` | **Move** | Consolidates 2D slice layouts into `assets/2d/layouts` |
| `assets3d/models/*` | `assets/3d/models/*` | **Move** | Migrates 3D models into single-root `assets/3d` |
| `assets3d/scripts/blender_render.py` | `assets/3d/scripts/blender_render.py` | **Move** | Preserves Blender render script under `assets/3d/scripts/` |
| `assets3d/LICENSES.md` | `assets/3d/LICENSES.md` | **Move** | Preserves 3D license notices under `assets/3d/` |
| `assets/voices/*` | `assets/voices/*` | **Keep** | Already in single root |
| `output/pack_tests/golden/*` | `tests/fixtures/golden/whiteboard/*` | **Move** | Moves test fixtures out of ephemeral/gitignored `output/` |
| `output/renders2d/Gemini_...png` | `assets/sources/incoming/gemini_source.png` | **Move** | Rescues misplaced original source image from output |
| `output/renders2d/contact_sheet_faces.png` | `assets/sources/incoming/contact_sheet_faces.png` | **Move** | Rescues reference contact sheet from output |
| `output/stickman_acceptance/` | `output/stickman_acceptance/` | **Regenerate** | Re-run blender acceptance render tool to fix broken tests |
| `assets2d/` & `assets3d/` (roots) | *(Removed)* | **Delete** | Old root folders eliminated once contents moved |

### B. Ordered Small Migration Batches

#### Batch 1: Centralized Paths Module
- **Actions**: Create `src/toonshorts/core/paths.py` (or update `src/toonshorts/core/config.py`) with `ASSETS_DIR`, `ASSETS_2D_DIR`, `ASSETS_3D_DIR`, `CHARACTERS_2D_DIR`, `LAYOUTS_2D_DIR`, `MODELS_3D_DIR`.
- **References Updated**: `src/toonshorts/core/character2d.py`, `src/toonshorts/core/character_pack.py`, `src/toonshorts/plugins/render/blender3d.py`.
- **Verification**: Run `pytest tests/unit/test_character_pack.py tests/unit/test_character2d.py`.

#### Batch 2: Raw Sources & Incoming Consolidation
- **Actions**: Move `assets2d/incoming/` to `assets/sources/incoming/`.
- **References Updated**: `tests/unit/test_character2d.py`, `tools/build_2d_hoodie_video.py`, `src/toonshorts/core/character2d.py`.
- **Verification**: Run `pytest tests/unit/test_character2d.py`.

#### Batch 3: 2D Character Packs & Layouts
- **Actions**: Move `assets2d/characters/*` to `assets/2d/characters/*`, and `assets2d/layouts/*` to `assets/2d/layouts/*`. Remove empty `assets2d/`.
- **References Updated**: `paths.py`, `tests/unit/test_new_character_packs.py`, `tests/unit/test_character_pack.py`, `tools/build_character_packs.py`, `tools/generate_boy_a_svg.py`, `tools/render_boy_a_preview.py`, `tools/test_layer_points.py`, `README.md`, `docs/FEATURES.md`.
- **Verification**: Run `pytest tests/unit/test_new_character_packs.py tests/unit/test_character_pack.py tests/unit/test_character2d.py`.

#### Batch 4: 3D Models & Scripts
- **Actions**: Move `assets3d/models/*` to `assets/3d/models/*`, `assets3d/scripts/*` to `assets/3d/scripts/*`, `assets3d/LICENSES.md` to `assets/3d/LICENSES.md`. Remove empty `assets3d/`.
- **References Updated**: `paths.py`, `src/toonshorts/plugins/render/blender3d.py`, `tests/unit/test_blender3d.py`, `assets/3d/scripts/blender_render.py`, `LICENSES.md`, `docs/FEATURES.md`.
- **Verification**: Run `pytest tests/unit/test_blender3d.py -k "robot"`.

#### Batch 5: Golden Baseline & Output Isolation
- **Actions**: Move `output/pack_tests/golden/` to `tests/fixtures/golden/whiteboard/`. Move stray source images from `output/renders2d/` to `assets/sources/incoming/`.
- **References Updated**: `tools/render_golden_baseline.py`, `tools/compare_golden_split.py`.
- **Verification**: Run `python tools/compare_golden_split.py`.

### C. High-Risk Items Flagged
1. **Golden Baseline Renders**: `output/pack_tests/golden/*.png` are compared pixel-for-pixel by test scripts. Moving them requires updating comparison targets in `tools/compare_golden_split.py` and `tools/render_golden_baseline.py`.
2. **Cached Audio Keys**: Piper and Gemini TTS cache keys (`cache/tts/<sha256>.wav`) are keyed on `(dialogue, voice_name, model_name)`. They are NOT keyed on disk file paths, so moving asset directories does not invalidate TTS cache.
3. **Tests Asserting Exact Folder Structure**: `test_new_character_packs.py` specifically tests `PROJECT_ROOT / 'assets2d' / 'characters' / char_id`. Updating this test must be coordinated with moving the folders.
4. **Protected Reference Video**: `output/What_is_an_API.mp4` has its mtime asserted in `render_golden_baseline.py`, `run_pack_tests.py`, and `render_v2_pack.py`. It must never be touched, modified, or deleted during migration.
5. **Untracked Staged Files**: 6 untracked files exist on disk (`assets/sources/boy_b_front_large.png`, `girl_a_front_large.png`, `assets2d/incoming/boy_a_sheet.png`, etc.) which are not in git. They must not be lost during folder moves.

### D. Rollback Plan & Current Git Status

#### Current Git Status
```text
On branch main
Untracked files:
  .agents/skills/
  assets/sources/boy_b_front_large.png
  assets/sources/girl_a_front_large.png
  assets2d/incoming/boy_a_sheet.png
  tools/generate_boy_a_svg.py
  tools/render_boy_a_preview.py
  tools/test_layer_points.py
  uv.lock
nothing added to commit but untracked files present
```

#### Rollback Procedures
1. **If code edits fail before commit**:
   ```bash
   git restore src/ tests/ tools/ docs/ LICENSES.md README.md
   ```
2. **If directory moves need to be reverted**:
   ```bash
   git restore --staged .
   git checkout -- assets/ assets2d/ assets3d/
   git clean -fd assets/2d/ assets/3d/
   ```
3. **Preserving untracked files during rollback**:
   - Ensure `assets/sources/*_large.png`, `assets2d/incoming/boy_a_sheet.png`, and tools scripts are backed up before running any `git clean` command.

---
*Audit generated on 2026-10-22. Complies with zero-modification constraint.*