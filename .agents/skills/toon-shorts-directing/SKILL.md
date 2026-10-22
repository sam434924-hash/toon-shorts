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
- Board text and drawn annotations appear at the moment the related word is spoken.

## Output
- Every shot has: start, end, type (wide or close_up), target (speaker id), ease. The validator rejects any plan that breaks the limits above.
