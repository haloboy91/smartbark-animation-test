# Elly character rig — notes and honest report

This document covers the reusable articulated rig, the 12-second coin scene,
and an honest list of what is fully achieved, what is approximated, and what
new artwork would be needed for a production-quality version.

**Just want to watch it?** Open
[`preview/Elly-rig-coin-scene.mp4`](../preview/Elly-rig-coin-scene.mp4) —
a normal 12-second, 1920×1080, 30 fps video. No tools required.

## 1. What was built

Elly started as **one flat illustration** (`src/assets/elly.png`). She now
drives a real hierarchical cut-out rig:

- **9 independently pivoted body layers**, all cut from the supplied artwork —
  head, torso, left arm, right arm, left leg, right leg, left ear, right ear,
  and tail. Nothing was redrawn or recolored.
- A joint hierarchy with measured pivots: hips → waist (spine bend) →
  torso/arms/neck → head/ears, exactly like a traditional 2D puppet.
- Global placement (position, scale, camera) is completely separate from the
  joint articulation.
- A reusable facial rig: movable pupils (with gaze clamping), fur-lid blinks,
  five mouth shapes, and liftable eyebrows.
- Reusable animation functions in `src/rig/animation.ts`:
  `walkPose()` (footprint walk cycle), `reach()` / `palmReach()` (inverse
  kinematics for the arm), `rightHand()` / `rightPalm()` (forward kinematics),
  and the full 12-second `poseAt(t)` timeline.
- The Motion Canvas scene (`src/scenes/coin.scene.tsx`) only feeds a clock
  into `poseAt()` — all animation math is pure and testable.

### How the flat image was separated

`scripts/rig/build_rig.py` cuts the nine layers from the original PNG using
polygon ownership masks and material masks (e.g. the star-patterned sleeve
fabric), so every pixel is claimed by exactly one part. The cut is verified:
**recomposing all nine layers reproduces the original illustration on every
solid pixel** (only 1-pixel alpha fringe differs). The mouth area and both
baked pupil discs are inpainted with the surrounding fur/eye-white so the
runtime facial rig can own them; every other facial line is untouched.

## 2. The 12-second scene, beat by beat

| Time | Beat | How it works |
| --- | --- | --- |
| 0–3 s | Four visible steps, left → center | Footprint walk: each foot holds a fixed world position while planted and only moves while airborne, so feet never slide. Legs alternate, arms counter-swing, body bobs, head stays comparatively stable, ears and tail overlap. |
| 3–5 s | Natural stop, both feet planted, looks down | Walk eases out, joints damp to neutral, head tilts down with a matching pupil gaze, blink included. |
| 5–8 s | Notices the coin, bends, reaches, picks it up | Eyes lock onto the coin first; spine bends forward, knees flex (leg squash), the right arm solves inverse-kinematics to the coin. The fingertip touches the coin exactly (verified numerically), then the coin transfers into the glove palm and rides the hand as she stands. |
| 8–10 s | Examines the coin, blinks, exaggerated surprise | Coin held up beside the face, pupils on the coin, blink at 8.75 s; at 9.0 s eyebrows shoot up, mouth opens, ears perk, whole body stretches, camera pushes in — face, head and body react together. |
| 10–12 s | Coin vanishes, freeze, looks at empty hand, then at camera | The coin scales out in 0.15 s; she freezes, glances at the empty palm, then snaps her gaze straight to the camera and holds the joke beat, with a final blink. |

## 3. Validation (the video was not declared done from compilation alone)

- `npm run typecheck` and `npm run build` both pass.
- A headless Python renderer (`scripts/rig/render_rig_preview.py`) ports the
  same `poseAt()` math and composites the same PNG layers with the same pivot
  hierarchy, then encodes an H.264 MP4 with the bundled FFmpeg.
- The TypeScript and Python timelines are diffed numerically at 20 timestamps
  across every beat: **all values match within 0.01**.
- Foot contact: a planted foot's world x is provably constant for its whole
  stance (no sliding).
- Hand/coin contact: fingertip and coin coordinates are identical at pickup;
  during carry/examine/surprise the coin sits on the measured glove palm.
- The rendered MP4 was extracted and visually checked at every story beat.

## 4. Honest limitations and approximations

These are deliberate, visible trade-offs of rigging a **single flat
illustration** — they are documented rather than hidden:

1. **Cartoon arm stretch.** The flat arm is too short to reach the ground
   from a standing bend without folding limbs the artwork cannot do. The arm
   scales up to at most 1.9× during the reach (classic cartoon "stretch"),
   computed from the true shoulder-to-coin distance, and returns to normal
   size afterward.
2. **No real elbow or knee joints.** Each limb is one image that rotates at
   one pivot. Knees are hinted with a vertical squash of the leg layer;
   there is no lower-leg/upper-leg separation because the source contains no
   such split.
3. **Facial animation is layered on top of the drawn face.** The eyes use the
   original eye-white outlines; pupils, eyelids, brows and mouths are
   procedural vector shapes. The baked pupils and mouth were erased from the
   head layer so nothing doubles up.
4. **Ears and tail rotate as whole pieces** (no inner-joint articulation).
5. **One head angle only.** Looking down/up is achieved with head rotation,
   gaze and lids; there are no 3/4 or profile views in the source art.
6. The right glove is a pointing hand in the source. The coin rests on the
   measured palm area; the fingers do not individually close around it.

## 5. New artwork that would unlock production quality

If a character artist can supply these, every approximation above can be
replaced without changing the rig code:

- **Front-view bent arms and legs** (upper/lower limb separated at elbow and
  knee, with matching pivot points), plus a relaxed open-hand shape and a
  grasping-hand shape for the coin pickup.
- **Profile and 3/4 head views** (and matching torso views) for real
  look-down and turn-around acting.
- **Separate eyelid, eyebrow and mouth-shape layers** (or a mouth chart:
  neutral, smile, open, "oh", flat) instead of vector overlays.
- **Independently pivoted ears and tail** with 2–3 bend segments each.
- A walk-cycle limb set (raised-foot versions of each leg) would remove the
  last bit of cut-out feel during steps.

## 6. File map

```
src/rig/
  ellyRig.tsx        Reusable <EllyRig> component: hierarchy, pivots, face rig
  animation.ts       Pure poseAt(t) timeline, walk/IK/FK functions, constants
src/scenes/
  coin.scene.tsx     12-second coin scene (clock → poseAt → rig signals)
  coin.scene.meta    Motion Canvas scene metadata
src/assets/rig/      9 cut body layers + head_clean + rig-manifest.json
scripts/rig/
  build_rig.py            Re-cuts the layers from src/assets/elly.png
  render_rig_preview.py   Headless renderer → output/rig-preview.mp4
preview/Elly-rig-coin-scene.mp4   Committed, ready-to-play rendered video
```

The earlier proof-of-concept scene (`src/scenes/elly.scene.tsx`) is untouched
and still works.
