# 2D Character Rig Contract

Specification for ToonShorts 2D multi-part full-body character rigs.
All characters in the pipeline are evaluated against this contract. Packs fulfilling all requirements are labeled **`gesture-ready`** in the asset inventory. Packs with missing parts remain usable with **`limited-gestures`** and their missing parts are reported explicitly.

## 1. Anatomy & Layer Hierarchy

A gesture-ready rig consists of separated, articulated vector/SVG parts:

| Segment | Layers / Sub-elements | Description |
|---|---|---|
| **Head** | `head_back`, `head_base`, eye states, mouth states | Cranium, facial features, hair, eyes, and mouth. |
| **Neck** | `neck` (or integrated in `head_base`) | Pivots under chin into torso collar. |
| **Torso** | `torso`, `torso_back` | Main body segment, chest, waist, and clothing base. |
| **Upper Arms** | `arm_upper_left`, `arm_upper_right` | Shoulder to elbow segment with rounded joint caps. |
| **Forearms** | `arm_lower_left`, `arm_lower_right` | Elbow to wrist segment with sleeve cuffs. |
| **Hands** | `hand_left`, `hand_right` | Articulated hands with 5 distinct shapes: `open`, `point`, `fist`, `thumbs_up`, `wave`. |
| **Thighs** | `leg_upper_left`, `leg_upper_right` | Hip to knee segment. |
| **Shins** | `leg_lower_left`, `leg_lower_right` | Knee to ankle segment. |
| **Feet** | `shoe_left`, `shoe_right` | Grounded shoes/sneakers with contoured soles. |

## 2. Joint Pivots

Joint coordinates are specified in the character pack's `manifest.json` under `"pivots"` in local viewBox space:

- `neck`: Center of rotation between neck base and torso.
- `shoulder_left`, `shoulder_right`: Center of rotation for upper arms.
- `elbow_left`, `elbow_right`: Joint center between upper arm and forearm.
- `wrist_left`, `wrist_right`: Joint center between forearm and hand.
- `hip_left`, `hip_right`: Center of rotation between pelvis and thighs.
- `knee_left`, `knee_right`: Joint center between thigh and shin.
- `ankle_left`, `ankle_right`: Joint center between shin and foot.

All joints use overlapping circular caps with zero gaps and constant limb thickness across rotations.

## 3. Required Rig Poses

Every gesture-ready character supports the standard 11 poses:

1. **`idle`**: Natural relaxed standing or seated rest with hands by sides or resting comfortably.
2. **`explain`**: Two-handed open communicative gesture emphasizing key concepts.
3. **`point_board`**: Direct arm gesture pointing towards the whiteboard/screen graphics.
4. **`point_other`**: Direct arm gesture pointing towards the co-host / partner.
5. **`wave`**: Friendly raised forearm hand wave with oscillating palm sway.
6. **`thumbs_up`**: Positive affirmative hand gesture with vertical thumb extended.
7. **`shrug`**: Raised shoulders, outward rotated hands, and tilted head expressing question or doubt.
8. **`nod`**: Subtle head pitch affirmation down and up.
9. **`head_tilt`**: Inquisitive 4-degree lateral tilt expressing curiosity.
10. **`lean_speaker`**: Torso and spine inclination leaning slightly toward the active speaker.
11. **`listening_reaction`**: Attentive listener posture with slight head tilt and glance towards speaker.

## 4. Seated Desk vs. Standing Layout

- **Seated Desk Layout (default studio)**:
  Upper body (torso, arms, hands, head) is fully visible. Lower body (thighs, shins, feet) exists in the rig but is placed behind the desk surface ($Y > 1540$ px), eliminating clutter while maintaining full anatomical integrity.
- **Standing Layout**:
  Full body rendered from head to feet for stage walk-ins or presentation sequences.

## 5. Procedural Stickman Migration Assessment

1. **`stick_hoodie`**: Needs a standard `manifest.json` mapping its 10 PNG/SVG slice layers to the rig contract, separated hand shape sprites (`point`, `fist`, `thumbs_up`, `wave`), and knee/ankle pivot definitions.
2. **`cairo_stickman`**: Procedural Pycairo stickman currently drawn as single stroke lines; needs a 2D forward-kinematics tree with joint angles for the 11 poses and segmented hand shapes.
3. **`pillow_stickman`**: Procedural Pillow stickman currently drawn with `ImageDraw.line`; needs multi-node FK joint tables, hand endpoint draw functions, and pose angle dictionaries for the 11 poses.
