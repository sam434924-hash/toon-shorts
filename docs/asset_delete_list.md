# Proposed Asset Deletion & Cleanup List (Stage 1)

> **Status**: PROPOSAL ONLY. No files, code, or assets have been deleted, moved, or renamed.
> **Decision Rule**: All deletions require explicit user approval. Items marked **UNSURE** are preserved.
> **Hoodie Stickman Policy**: `assets2d/characters/stick_hoodie/`, `sheet_03.png`, and `sheet_03_layout.json` belong to the required hoodie stickman and are strictly KEPT.

---

## 1. Summary of Proposed Actions

| Category | Proposed Items | Items to Delete | Items to Keep / Move | Unsure Items |
| :--- | :---: | :---: | :---: | :---: |
| **(a) Deleted-Stickman Leftovers & Dead References** | 6 | 5 code/test edits, 4 scratch files | 0 | 0 |
| **(b) Exact Duplicates (Hash Collisions)** | 9 groups | 8 duplicate copies | 8 canonical copies | 0 |
| **(c) Unused Files & Intermediate Slices** | 9 | 9 files | 0 | 0 |
| **(d) Obsolete Links & Stale Doc References** | 3 | 3 doc cleanups | 0 | 0 |
| **(e) Unsure Items (Preserved until confirmed)** | 4 | 0 | 4 preserved | 4 |

---

## 2. Group (a): Deleted-Stickman Leftovers & Dead References

These items reference files deleted by hand (such as `output/stickman_acceptance` or `assets3d/models/Stickman.blend`). Per project decision, these files will not be regenerated; dependent tests and references will be cleanly pruned so the suite passes.

| Target / Path | Type | Reason | Action Proposed | References to Update |
| :--- | :--- | :--- | :--- | :--- |
| `tests/unit/test_blender3d.py:118-136` (`test_stickman_acceptance_renders_exist`) | Test Function | Asserts existence of 13 deleted PNG frames in `output/stickman_acceptance/` (`tpose.png`, `walking_*.png`, etc.). Fails in pytest. | **Remove test** | Entire test function removed in Stage 2 Batch 3 |
| `tests/unit/test_blender3d.py:138-145` (`test_stickman_pixel_differences_recorded`) | Test Function | Asserts existence of `output/stickman_acceptance/pixel_diffs.json`. Fails in pytest. | **Remove test** | Entire test function removed in Stage 2 Batch 3 |
| `tests/unit/test_blender3d.py:101-103` in `test_robot_model_preserved` | Test Assertion | Explicitly references `stickman_path = config.PROJECT_ROOT / "assets3d" / "models" / "Stickman.blend"` to assert it was deleted. | **Trim stale assertion** | Keep `assert robot_path.is_file()`, delete stale `stickman_path` assertion lines |
| `scratch/wave_test/` (4 files: `tpose.png`, `wave_01.png`, `wave_02.png`, `wave_03.png`) | Scratch Files | Old test frames from manual stickman blender renders. | **Delete** | None (scratch files) |
| `src/toonshorts/plugins/voice/piper.py:56` | Code Fallback | Dead path candidate `config.PROJECT_ROOT / "assets" / "piper" / "piper.exe"` pointing to non-existent local binary. | **Remove line** | Piper engine already checks system PATH via `shutil.which('piper')` |
| `tools/render_golden_baseline.py:4`, `tools/render_v2_pack.py:7` | Script Comments | References to non-existent directory `output/keep/`. | **Trim comments** | Docstring / comment cleanup only |

---

## 3. Group (b): Exact Duplicates

Every item below has an identical SHA-256 hash to another file in the repository. One canonical copy is retained and all references point to the retained copy.

| Hash (Prefix) | Duplicate Path (Proposed for Deletion) | Canonical Path (TO KEEP) | Size | Reason & References |
| :--- | :--- | :--- | :--- | :--- |
| `e6286e77...` | `assets2d/incoming/reference_card.png` | `assets2d/incoming/reference_sheet.png` (migrating to `assets/sources/incoming/`) | 129,162 B | Bitwise identical duplicate. Neither copy was referenced; keeping `reference_sheet.png` matches project naming convention. |
| `db746208...` | `assets2d/characters/boy_a/staging/r3_c0_neutral.png` | `assets2d/characters/boy_a/staging/r1_c0_closed.png` | 75,591 B | Identical frame slice in `boy_a/staging`. Both are unreferenced intermediate debug crops (see Group (c)). |
| `857dc633...` | `output/pack_tests/v2/tmp_audio/scene_0_voice.wav` | `cache/tts/e007ab6f...wav` | 267,884 B | Ephemeral audio copy in test folder. The canonical audio is cached in `cache/tts/` keyed by `(dialogue, voice_id, model)`. |
| `18cb4a7e...` | `output/pack_tests/v2/tmp_audio/scene_1_voice.wav` | `cache/tts/d4f221c6...wav` | 243,244 B | Ephemeral audio copy in test folder. Cached copy preserved in `cache/tts/`. |
| `c1f87403...` | `output/pack_tests/v2/tmp_audio/scene_2_voice.wav` | `cache/tts/dbfa8092...wav` | 237,612 B | Ephemeral audio copy in test folder. Cached copy preserved in `cache/tts/`. |
| `38f3894f...` | `output/pack_tests/v2/tmp_audio/scene_3_voice.wav` | `cache/tts/6ddc9c87...wav` | 239,660 B | Ephemeral audio copy in test folder. Cached copy preserved in `cache/tts/`. |
| `a9ca9066...` | `output/pack_tests/v2/tmp_audio/scene_4_voice.wav` | `cache/tts/f182eb28...wav` | 245,292 B | Ephemeral audio copy in test folder. Cached copy preserved in `cache/tts/`. |
| `7949a390...` | `output/pack_tests/v2/tmp_audio/scene_5_voice.wav` | `cache/tts/4a17d9ff...wav` | 224,204 B | Ephemeral audio copy in test folder. Cached copy preserved in `cache/tts/`. |
| `474bd59b...` | `scratch/scene_1_voice.wav` | `cache/tts/c4c97643...wav` | 185,388 B | Ephemeral audio copy in scratch. Cached copy preserved in `cache/tts/`. |

---

## 4. Group (c): Unused Files & Intermediate Slices

Files with zero incoming references across all production code, configuration, manifests, and test assertions.

| Path | Description | Size | Reason Proposed for Deletion |
| :--- | :--- | :--- | :--- |
| `assets/voices/piper/.gitkeep` | Empty placeholder file | 1 B | Directory already contains tracked `.onnx` and `.onnx.json` files; placeholder no longer needed. |
| `assets2d/characters/boy_a/staging/r1_c0_closed.png` | Intermediate debug crop | 75,591 B | Unreferenced debug slice from initial boy_a SVG extraction tool. |
| `assets2d/characters/boy_a/staging/r1_c1_slightly_open.png` | Intermediate debug crop | 75,989 B | Unreferenced debug slice from initial boy_a SVG extraction tool. |
| `assets2d/characters/boy_a/staging/r2_c0_wide_open.png` | Intermediate debug crop | 77,295 B | Unreferenced debug slice from initial boy_a SVG extraction tool. |
| `assets2d/characters/boy_a/staging/r2_c1_round_o.png` | Intermediate debug crop | 76,069 B | Unreferenced debug slice from initial boy_a SVG extraction tool. |
| `assets2d/characters/boy_a/staging/r3_c1_blink.png` | Intermediate debug crop | 69,710 B | Unreferenced debug slice from initial boy_a SVG extraction tool. |
| `assets2d/characters/boy_a/staging/r4_c0_screen_left.png` | Intermediate debug crop | 74,919 B | Unreferenced debug slice from initial boy_a SVG extraction tool. |
| `assets2d/characters/boy_a/staging/r4_c1_screen_right.png` | Intermediate debug crop | 74,778 B | Unreferenced debug slice from initial boy_a SVG extraction tool. |
| `scratch/extracted_short_audio.wav` | One-off test audio file | 44,144 B | Scratch test file; unreferenced. |

### Note on Staging Preview Stills:
- `boy_a/staging/boy_a_contact_sheet.png` & `index.html`: **KEEP / MOVE** to `output/staging/characters/boy_a/` or `assets/2d/characters/boy_a/staging/` because `test_character_pack.py` asserts their generation.
- `boy_b/staging/` and `girl_a/staging/` (`preview_sheet.png`, `source_comparison.png`, `pose_01` to `pose_11`): **KEEP / MOVE** to `assets/2d/characters/<id>/staging/` because `tests/unit/test_new_character_packs.py:test_character_preview_sheets_exist` explicitly asserts their existence. They are permanent pack verification artifacts, not ephemeral debug trash.

---

## 5. Group (d): Obsolete Links & Stale Documentation

Documentation references pointing to paths that were deleted or never committed.

| File & Lines | Content | Problem | Proposed Remedy |
| :--- | :--- | :--- | :--- |
| `LICENSES.md:26-34` | Mentions `assets3d/motion/raw/*.bvh` and `assets3d/motion/LICENSES.md` | Files were removed or never committed; dead links. | Remove stale section in Stage 2 Batch 3. |
| `LICENSES.md:41-86` | Mentions `assets3d/items/raw/ice_cream.glb`, `cup.glb`, `table.glb`, `chair.glb`, `backpack.fbx` | Props files were removed in prior cleanup; dead links. | Remove stale sections in Stage 2 Batch 3. |
| `README.md:24` | Mentions `assets2d/characters/stick_hoodie/` | Path will change to `assets/2d/characters/stick_hoodie/` during migration. | Update path in Stage 2 Batch 2. |

---

## 6. Group (e): Unsure Items (DO NOT DELETE)

These items require explicit user guidance before any destructive action is taken. They are preserved in their current locations.

| Path | Type / Size | Current State & Context | Why Marked Unsure |
| :--- | :--- | :--- | :--- |
| `output/renders2d/Gemini_Generated_Image_c6rp0kc6rp0kc6rp (1).png` | PNG Image (1.9 MB, 2236x1888) | Sits inside `output/renders2d/`. Zero incoming references. | Could be an original AI generation intended as a source asset, or a discarded render test. **Preserved** until user specifies whether to move to `assets/sources/incoming/` or delete. |
| `output/renders2d/contact_sheet_faces.png` | PNG Image (1000x560) | Sits inside `output/renders2d/`. Contact grid of facial expressions. | Unclear if this is an author reference sheet to preserve in `assets/sources/` or an intermediate render output to discard. **Preserved**. |
| `assets2d/incoming/target_poses.png` | PNG Image (994 KB, 1024x571) | Reference pose guide for `stick_hoodie`. Referenced in `character2d.py` docstrings. | Belongs to `stick_hoodie`. Although not strictly parsed by code, it documents rigging poses. **Preserved** and queued for move to `assets/sources/incoming/target_poses.png`. |
| `assets2d/incoming/reference_uploaded.jpg` | JPEG Image (63 KB, 499x1024) | Original photo upload of reference sheet. | Converted to `reference_sheet.png`. May have provenance value. **Preserved** and queued for move to `assets/sources/incoming/reference_uploaded.jpg`. |

---

## 7. Protected Assets Checklist

- [x] `output/What_is_an_API.mp4` verified intact (`mtime` strictly preserved).
- [x] Full backup created at `C:\Users\Ria\.gemini\antigravity\brain\aa7b31d2-d295-4365-9204-ded2578c60c7\toon_shorts_backup_stage1.zip` (317.52 MB, 1,353 files).
- [x] High-res source bodies and untracked incoming sheet committed to git (`assets/sources/boy_b_front_large.png`, `girl_a_front_large.png`, `assets2d/incoming/boy_a_sheet.png`).
- [x] Central paths module created at `src/toonshorts/core/paths.py` with passing unit tests in `tests/unit/test_paths.py`.
- [x] **Zero asset files moved, deleted, or renamed.**
