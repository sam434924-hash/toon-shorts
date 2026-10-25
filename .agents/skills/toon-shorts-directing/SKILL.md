---
name: toon-shorts-directing
description: Use ONLY when planning or validating shot lists, camera zooms, and character staging for toon-shorts 2D scene files. Not for 3D or Blender work.
---

# 2D directing rules for toon-shorts

## Video intake rules (mandatory for every video)
Whenever a story or video idea is provided:
1. **Ask first, wait, then build**: Never jump straight to building or rendering. All intake questions must be asked, answered, and confirmed before execution begins.
2. **Run inventory first**: Always inspect live installed components via `python -m toonshorts.inventory`.
3. **Ask the 9 intake questions in ONE message** with numbered choices:
   1. Format: explanation video, comedy story, or other
   2. Board theme / style (from inventory)
   3. Characters (from inventory) and who speaks
   4. Voice (from inventory)
   5. Board animations to USE (from inventory) and any to AVOID
   6. Hand gestures: on or off
   7. Camera: zoom on the speaker, or fixed
   8. Length (e.g. 30 or 40 seconds)
   9. Custom: anything special to add or avoid (free text)
   - Every question must provide a "custom" option and a "you choose" option.
   - If a previous brief exists in `briefs/`, offer "same as last video".
   - If a requested feature does not exist in inventory (e.g. a new animation or character), state that it does not exist and ask whether to build it now or skip it.
   - Do not start building until all answers are in.
4. **Save & validate brief**: Store answers in `briefs/<video-name>.json`. Validate strictly on load: only known keys permitted, and all selected values must exist in current inventory. The renderer reads only this brief file.
5. **Security & argument lists**: Never interpolate story text or file names into shell command strings; always pass argument lists and validate filesystem paths.
6. **Confirm, then build**:
   - Present a concise brief summary (strictly <= 10 lines) and wait for the user's "go".
   - After "go": generate the scene file from the story and brief, create voice audio, render stills of key scenes for approval, then render the full MP4 into `output/`.
   - If an error occurs, halt immediately and state the error in plain words. Do not retry in a loop.

## Asset Planning (Mandatory Step)
For every scene during directing and planning, the director must execute the **Asset Planning** step to designate the visual asset strategy before writing or rendering:
1. **Library Asset**: Search existing indexed elements in `library/elements/<type>/index.json` or backgrounds in `library/backgrounds/`. If an asset exists matching the required theme tags and visual key, reuse it directly without regenerating.
2. **Custom Animated SVG**: Author vector artwork and motion using sanitized SVG (Level 1) or sandboxed pure JavaScript (Level 2). When writing animation timelines and keyframed motion, use the **animejs-animation** skill.
3. **Generated Image**: generate with the built-in image tool, then register-image. Check `library/elements/images/index.json` first before generating. Save newly generated images once into `library/elements/images/` via `toonshorts register-image <file> --prompt "..." --theme ... --style ...` and record the image in manifest.json `tools_used`.
4. **Screen Recording**: Clean screen capture walkthroughs, UI recordings, or demo clips.

Record all planned assets and their sources in the scene manifest under `tools_used`.

## Scene Layout Planning (Mandatory)
Writing a script now requires an explicit `layout` block for every scene. Validation strictly FAILS if a scene has none.
- **Generation**: Generated automatically by the layout planner (`plan_scene_layout` / `plan_script_layouts`) from dialogue lines, visuals, and word timings, then reviewed.
- **Rules**:
  - 1 main visual = `hero` or `title-card`
  - 2 visuals that compare = `split`
  - 3 or more in sequence = `chain`
  - a list = `stack`
  - The hero is the visual tied to the key claim or punchline.
  - Enter and exit times come from trigger words.
  - Max 3 elements on screen at once, strictly one hero per beat.
- **Review**: The agent may adjust the planner's layout result, but it must pass validation.

## Camera Planning (Mandatory)
Every scene and video now requires an explicit camera plan (`camera_plan.json`) following the **toon-shorts-camera** skill. Validation fails if it is missing or invalid.
- **Generation**: Generated automatically by the camera shot planner from dialogue lines, word timings, layout blocks, and acting beats.
- **Rules**:
  - Open on wide 2-shot (`CAM_01_WIDE_2SHOT`) with creep.
  - Medium board (`CAM_02_MED_BOARD`) while the board explains.
  - Snap-zoom on interrupt or punchline.
  - Close-up (`CAM_04_CU_SPEAKER_B` / `CAM_05_CU_SPEAKER_A`) on question, hesitation, realization, or reaction.
  - Cuts on speech: 3 frames before speaker change, 2 frames before interrupt, 12 frames before reaction.
  - Character zone zoom cap 1.9; cuts and character zoom never move the board zone.
  - Something changes at least every 2.5 s; no shot longer than 6 s.
- **Output**: `videos/<name>/camera_plan.json`.

## Acting Planning (Mandatory)
Every scene and video now requires an explicit acting plan (`acting_plan.json`) following the **toon-shorts-acting** skill. Validation fails if it is missing or invalid.
- **Generation**: Generated automatically by the acting planner from script scenes, cast, word timings, and layout plan.
- **Rules**:
  - Max 2 actors on screen (Character A left, Character B right).
  - Split dialogue into acting beats: tactic, energy, subtext. Tactic changes at least once per scene.
  - Accents placed on stressed words: gesture begins 0 to 4 frames before stressed word, peaks on accent, holds, and returns to rest.
  - At most one accent gesture per phrase; no gesture repeated twice in a row.
  - Listener behavior: never frozen; nods, blinks, or head tilts at least every 3 to 4 s; no actor motionless > 2 s.
  - Gaze, turns (lean plus flip with anticipation and settle), and pointing directly at board visual slots.
  - Secondary motion (breathing, sway) offset between actors so they never breathe in unison.
- **Output**: `videos/<name>/acting_plan.json`.

## Cast and staging
- Max 2 speaking characters per scene. Character A stands LEFT and faces right. Character B stands RIGHT and faces left. Never swap sides inside a scene (180-degree rule).
- Only the current speaker's mouth moves. The listener only blinks and glances toward the speaker. No arm or hand gestures.

## Shots
- Default shot is WIDE (both characters fully visible).
- When a speaker starts an important line, ease in to a MEDIUM CLOSE-UP on that speaker, hold, then ease back out to WIDE or move straight to the other speaker.
- Short lines (under about 1.5 s) and fast back-and-forth stay in the wide shot. Zoom on emphasis only, never on every line.

## Camera limits (a validator must enforce these)
- Max zoom 1.35x. Ease in and ease out each 0.4 to 0.6 s. Minimum hold 1.2 s.
- At most one zoom per 5 s of video.
- The speaker is always fully inside the frame. Subtitles stay outside the camera layer and never scale.
- Zoom targets come from the speaker's face position (not the frame center). Render at 2x resolution so zooms stay sharp.

## Story beats
- Hook (first 3 s): a question or surprising line, wide shot.
- Setup, then Turn (the twist or key explanation, best place for a zoom), then Payoff, then a short outro.

## 2D Full-Body Rig Contract
- **Anatomy**: head, neck, torso, upper arms, forearms, hands (open, point, fist, thumbs_up, wave), thighs, shins, feet.
- **Pivots**: neck, shoulder_left/right, elbow_left/right, wrist_left/right, hip_left/right, knee_left/right, ankle_left/right.
- **11 Standard Poses**: idle, explain, point_board, point_other, wave, thumbs_up, shrug, nod, head_tilt, lean_speaker, listening_reaction.
- **Seated vs Standing**: Seated desk layout shows upper body while legs remain behind desk ($Y > 1540$ px); standing layout renders full body.
- **Inventory Labeling**: Character packs meeting all rig criteria are marked `[gesture-ready]`; packs missing lower limbs or gestures are labeled `[limited-gestures]` with missing parts listed.
- Board text and drawn annotations appear at the moment the related word is spoken.

## Output
- Every shot has: start, end, type (wide or close_up), target (speaker id), ease. The validator rejects any plan that breaks the limits above.
