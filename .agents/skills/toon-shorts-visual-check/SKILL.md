---
name: toon-shorts-visual-check
description: Inspect scene still frames against quality checklist (contrast ratio, safe zones, text legibility, board design, character style, motion beats) and write visual_review.md before full video render.
---

# ToonShorts Visual Check Skill

A quality gate skill for inspecting generated scene stills before permitting full MP4 video rendering.

## When to Use
Run visual checks after scene still frames are rendered in `videos/<video>/stills/`. Full rendering must NOT proceed until the visual review passes or user explicit approval is provided.

## CLI Command
```bash
toonshorts check-visuals <video>
# or
python -m toonshorts check-visuals <video>
```

## The Quality Gate Checklist
Every scene still must be verified against these 6 criteria:

1. **Text Readable Against Background**:
   - Automated WCAG contrast ratio check: minimum 4.5:1 for standard body text, or 3.0:1 for large display titles/cards.
   - Text colors and card backgrounds must maintain high contrast without visual vibration.

2. **Nothing Overlapping or Clipped**:
   - Character limbs, dialogue balloons, cards, and diagrams must never overlap or occlude one another.
   - Slots must remain cleanly separated across `slot_top`, `slot_mid`, `slot_center`, and `slot_bottom`.

3. **Board Looks Designed and Not Plain**:
   - The whiteboard or digital board must feel intentional and designed, not empty or plain.
   - Includes decorative frames, badges, icons, cards, and multiplane vector background layers.

4. **Style Matches Characters**:
   - Outlines, palette accents, and stroke weights must harmonize across characters, props, and board objects.
   - Night studio uses glowing neon accents; whiteboard uses hand-drawn rough ink styling.

5. **Motion Beats Exist for Every Key Word**:
   - Key speech words must have synchronized kinetic cards, highlight triggers, or sketch annotations.
   - No scene dialogue should run longer than 5 seconds without a visual beat or board transition.

6. **Nothing Important in Top 288 px or Under Captions**:
   - Top 288 px (15% of vertical 1080x1920) is reserved for YouTube Shorts UI title, channel bar, and search icon.
   - Bottom 480 px (below 1440 px) is reserved for auto-captions and audio attribution.
   - All critical cards, character faces, and diagrams must sit strictly between Y=288 px and Y=1440 px.

## Fix Rounds Protocol
- If any check fails or the score is under 7.0/10:
  1. Trigger **Fix Round 1**: Adjust styling tokens, card coordinates, or contrast ratios in `scene.json` and re-render stills.
  2. If still failing, trigger **Fix Round 2**: Final automated adjustment and re-render.
  3. Record each round's results into `visual_review.md`.
  4. If review fails after Round 2, the pipeline HALTS and prompts the user for approval or stops. Full render will not proceed without approval.
