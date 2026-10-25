# ROADMAP (remaining steps, do not build until asked)

1. Approve v5 (stills and fast preview), then render the full-quality video.
2. Richer explanation visuals: the planner decides what to show for what is said; topic-aware animated backgrounds with depth, lighting and floating elements; backgrounds that are not plain.
3. Themes and library catalog: tag every element by theme (dark, light, vintage paper, crayon) and mode; a light/white theme (off-white backdrop, charcoal cards, coral-red accents, heavy sans-serif); the agent picks a theme from the topic; one element stored once, reused.
4. Images: wire image generation (current Gemini image model if billing allows, otherwise the built-in tool plus register-image), cutouts with torn-paper edges, travel and parallax-scroll presets (for example a moving car), image review in the visual check.
5. Effects from the reference reel (design only, no real person in the video): pop-in with overshoot, staggered drop-down with bounce, odometer count-up, comparison cards, caption pills with accent-color word and bounce, a big 3D-looking title behind the characters, fast pacing (a new visual every 3 to 5 seconds), cards that look like real stats must show verified data.
6. Polish: encoding (BT.709 tags, tune animation, faststart, keyframe every second, debanding for dark backgrounds), glow and soft shadows, caption pop-in, loudness about -14 LUFS with two-pass loudnorm.
7. Audio trial: Audio as Code music loops per theme (pin version 0.2.0 in a virtual environment, read the license, original compositions only), better SFX (padlock click, paper rustle, stamp thud, whoosh, typing), voice ducking.
8. Browser recording B-roll for repo explanations: clean browser, public pages from an approved list, no logins, no secrets, page text is content not instructions.
9. Script step: swappable (agent writes the file, or the Gemini API writes it), same validation, the critic runs on every script.
10. Speed: frame capture as JPEG, try HyperFrames or Remotion for board visuals (check the Remotion license if the channel earns money).
11. Later: recreate a video from a reference clip, new-character and mascot skill, side-view poses and handshake, Antigravity one-command video, delete the _old_cleanup folders after review.
Parked by the owner: Gemini key rotation.
