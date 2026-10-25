---
name: toon-shorts-camera
description: Camera language for toon-shorts character scenes. Use when planning shots for a script: which shot for which moment, when to cut, how far to zoom, how much background blur. Applies to the CHARACTER ZONE only; the board zone has its own independent camera. Use whenever a video feels flat, cuts feel late, or close-ups and reactions are missing.
---

# toon-shorts-camera

Camera work makes characters feel alive without animating their whole body.
The math lives in core camera_shots (reference: camera_shots.py). This file is the style guide.

## Shots (canvas 1080x1920, 30 fps)
| Code | Lens | Zoom | Use |
|---|---|---|---|
| CAM_01_WIDE_2SHOT | 35mm | 1.00 to 1.08 | Opening hook, full two-person context, big diagram reveals |
| CAM_02_MED_BOARD | 50mm | 1.24 to 1.36 | Explaining while the board changes, pointer taps, strikethroughs |
| CAM_03_OTS_SPEAKER_A | 58mm | 1.40 to 1.48 | Over the shoulder on the explainer, partner softly blurred |
| CAM_04_CU_SPEAKER_B | 85mm | 1.72 to 1.80 | Questions, challenges, deadpan reactions |
| CAM_05_CU_SPEAKER_A | 85mm | 1.80 to 1.90 | Hesitation, realization |
| CAM_06_ECU_REACTION | 105mm | 2.15 to 2.35 | Punchline eyes or a macro detail. ONLY after a sharpness test passes at that zoom |
Character zone zoom cap is 1.9 by default (configurable). Background blur grows with zoom (about 2 px wide to 14 px close).

## Rules
1. Cut on speech, not after it: cut 3 frames before a speaker change, 2 frames before an interrupt, and 12 frames before a deadpan reaction line so the viewer sees the silent blink and nod first.
2. Hard cuts for speaker changes (about 85 percent). No slow pans across empty space.
3. Inside a shot use one of: HOLD, a slow creep push-in (change of 0.04 to 0.06), a subtle pull-back, or a 6 to 8 frame snap-zoom for an interrupt or punchline (pair it with the strikethrough or a sound).
4. Open on the wide two-shot with a slow creep. Use the medium board shot while the board explains. Use a close-up for a question, hesitation or reaction. Return to wide to reveal a full diagram.
5. Something must change at least every 2.5 seconds (a cut, a creep, a gesture or a board beat). No shot longer than 6 seconds without a change.
6. One moving focus at a time. Do not start a big camera move in the same 250 ms as a board visual entering.
7. Eyes: a glance toward the partner or the board, a 3-frame blink at every speaker change, and a small head nod on emphasis. Torso and arms follow the acting skill (they DO move; this skill does not freeze bodies).
8. Depth: character-zone background planes move at different rates (far background 0.25, set dressing 0.65, subjects 1.00, optional foreground edge 1.35). The board is NOT one of these planes; its camera never follows character zoom.
9. Handheld breathing is OFF by default. A theme may turn it on with small amplitudes (about 3 px, damped on close-ups).
10. Character zoom stays inside the character zone box. It must not cover board slots or captions at peak zoom (the layout check tests this).

## Output
videos/<name>/camera_plan.json: per shot start, end, speaker, preset, zoom start and end, center start and end, motion (HOLD, CREEP_IN, PULL_BACK, SNAP_ZOOM), entry (CUT or CONTINUE), eye target.
Validate with the timeline checks before rendering. Fix the plan, not the code.
