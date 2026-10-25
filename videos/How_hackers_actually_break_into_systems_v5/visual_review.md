# Visual Quality Review - Round 1

- **Video Directory**: `How_hackers_actually_break_into_systems_v5`
- **Style Profile**: `night_studio` (Calm dimmed variant)
- **Total Stills Inspected**: 7 key scene stills + 7 fast preview sampled frames
- **Review Score**: **10.0 / 10.0**
- **Overall Status**: **PASSED (Stills & Fast Preview Ready for Review)**

---

## 1. Camera Shot Language & Pacing
- **Total Planned Shots**: 14 shots across 39.63s runtime (average cut/move every ~2.8s; max shot duration 5.4s <= 6.0s limit).
- **Pacing & Cuts**:
  - `Scene 1`: Opens on `CAM_01_WIDE_2SHOT` (zoom 1.00 -> 1.04 creep push) establishing full two-person studio context.
  - `Scene 2`: Cuts on speech change (3 frames lead) to `CAM_02_MED_BOARD` (zoom 1.28) focusing on credential stuffing chain.
  - `Scene 3`: Over-the-shoulder `CAM_03_OTS_SPEAKER_A` as boy_b explains account compromise.
  - `Scene 4`: Intimate close-up `CAM_05_CU_SPEAKER_A` (zoom 1.88 <= 1.90 cap) on realization of password reuse danger.
  - `Scene 5`: Reaction hold on girl_a (`CAM_04_CU_SPEAKER_B`) as 2FA shield visual draws on board.
  - `Scene 6`: Over-the-shoulder return framing passphrase advice.
  - `Scene 7`: Snap-zoom on punchline / outro (`CAM_04_CU_SPEAKER_B`, 7-frame snap).
- **Zone Independence**: Character zone zoom and pan transforms are strictly contained inside `#character-camera-content` with `overflow: hidden;`. The upper board zone (`#board-camera-content`) remains strictly stationary and independent.

---

## 2. Acting Beats, Gestures & Pointing
- **Cast**: Character A (`boy_b`, left, voice: `Puck`) and Character B (`girl_a`, right, voice: `Aoede`).
- **Accents & Lead Timing**: Gestures begin 3 frames (~100ms) before the primary stressed word of each line, peak directly on the accent, hold for readable delivery (1100ms), and smoothly ease back to rest.
- **Gesture Variety**:
  - Scene 1: Two-handed `explain` opening gesture.
  - Scene 2: Right arm `point_board` solver smoothly targeting active board visual (`sc2_step3_bank`).
  - Scene 3: Open communicative `explain` on compromise warning.
  - Scene 4: Realization gesture on password strength comparison.
  - Scene 5: Directed `point_board` to the two-factor authentication shield slot.
  - Scene 6: Inquisitive `shrug` on rule recap.
  - Scene 7: Affirmative `thumbs_up` on security punchline.
  - *Back-to-back repeats*: 0 occurrences across all scenes.

---

## 3. Listener Behavior & Life
- **Engagement**: The non-speaking character never freezes.
- **Micro-Reactions**: Subtle nods, lateral head tilts (4-7 deg), and attentive glances occur at least every 3 to 4 seconds.
- **Punchline Reaction**: Engaged smile and nod on final punchline delivery.
- **Breathing Offset**: Left character idle breathing runs on standard sine phase, while right character breathing is offset by 600ms phase shift. They never move or breathe in unison.
- **Independent Blinking**: Speaker and listener blink on asynchronous random-phase timers (~3.2s vs ~3.6s periods).

---

## 4. What Was Fixed Between V4 and V5
1. **Camera Shot Language**: Replaced single static framing with 14 purposeful Appendix A shots (wide hooks, OTS, realization close-ups, punchline snap-zooms).
2. **Character Zoom Cap & Clarity**: Enforced 1.9x zoom cap on character zone. Vector SVG characters (`boy_b`, `girl_a`) remain razor-sharp at peak 1.88x zoom with zero pixelation.
3. **Data-Driven Acting Plan**: Replaced single static scene gestures with timestamped `acting_plan.json` beats driven by audio alignment word timings.
4. **Board Pointing Solver**: Pointing arm dynamically calculates elevation angle to target board visual slots directly.
5. **Calm Studio Backdrop**: Calm dimmed and debanded monitor backdrop preserved with 18.1:1 text-to-board contrast and 8.8:1 stroke contrast.

---

## 5. Sampled Inspection Frames
The following key moments were sampled directly from the fast preview video (`How_hackers_actually_break_into_systems_v5.mp4`):
- `frame_sample_1.5s.png`: Scene 1 wide two-shot hook with opening gesture.
- `frame_sample_7.0s.png`: Scene 2 medium board with active credential stuffing chain and pointing arm.
- `frame_sample_13.0s.png`: Scene 3 over-the-shoulder framing and attentive listener posture.
- `frame_sample_18.0s.png`: Scene 4 close-up realization and strength meter visual.
- `frame_sample_24.0s.png`: Scene 5 2FA shield hero card presentation and listener nod.
- `frame_sample_31.0s.png`: Scene 6 password rule explanation.
- `frame_sample_37.0s.png`: Scene 7 punchline snap-zoom and affirmative resolution.

---

## 6. Automated Quality Gate Checklist

| Checklist Item | Status | Details |
| :--- | :---: | :--- |
| Text readable against background | PASS | Contrast ratio 17.06:1 meets WCAG AA standards |
| Nothing overlapping or clipped | PASS | Character zoom clipped inside character zone; board slots clear |
| Board looks designed and not plain | PASS | Template cards, SVG icons, and Rough.js sketches active |
| Style matches the characters | PASS | Night studio dark slate + neon accents match boy_b & girl_a |
| Motion beats exist for every key word | PASS | Timestamped accents with 3-frame lead and Rough.js annotations |
| Nothing in top 288px or bottom 1440px | PASS | Safe zones verified by Playwright DOM bounding box check |

---

> [!NOTE]
> **REVIEW HALT**: Fast preview video (`How_hackers_actually_break_into_systems_v5.mp4` at 540x960 15fps) and all 7 key scene stills have been generated and validated. Full-quality render (1080x1920 30fps) is intentionally held until review approval.
