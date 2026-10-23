---
name: toon-shorts-style
description: Resolves and enforces the visual style profile for backgrounds, props, text styles, and generated assets in toon-shorts.
---

# Visual Style Profile Guidelines for toon-shorts

When a new video idea, brief, or images arrive:

1. **Resolve style profile first**:
   - Always load or extract the primary character's style profile from `assets/style/<pack>.style.json`.
   - Never proceed to storyboard generation, background layout, or prop creation before the style profile is resolved.

2. **Single style per video**:
   - Every video must have exactly one unified visual style.
   - If the selected characters differ beyond the style distance threshold (e.g. line art thickness, fill technique, or roughness), warn immediately and require an explicit `style_pack` in the brief.
   - Never mix visual styles silently.

3. **Strict asset and image enforcement**:
   - Use the resolved style profile's exact color palette (maximum 8 hex colors), stroke width, outline color, fill style, font family, and roughness for every background layer, prop, and board visual.
   - Inject the profile's `style_description` into all image generation prompts.
   - Link the character's reference contact sheet in `assets/style/<pack>.style.json` to ground visual continuity.
   - Reject any generated background, prop, or asset that does not match the outline color, stroke width range, or palette.
