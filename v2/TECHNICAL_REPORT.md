# Elly v2 — Walk, Turn, Sit, Settle — Technical Report

**Shot:** Elly walks to a wooden chair, stops, turns toward it, backs up, sits, and settles.
**Length:** 186 frames @ 24 fps = **7.75 s** (brief: 6–8 s). Canvas 960×540, static camera.
**Isolation:** Everything lives under `v2/`. No EP015 or other production asset was modified, and the accepted v1 work is untouched.
**Reference toolchain:** rigging/IK/interpolation conventions follow the local clone of
[filippocalippo/StykAnimate-App](https://github.com/filippocalippo/StykAnimate-App)
(`src/ik.mjs`, Pivot/Styk model). This is a character-animation quality test, not an engine rebuild.

---

## 1. Why replacement artwork (no PNG articulation)

The Smart Bark Kit v2 ships only **flat, full-body pose cutouts** — there are no separated,
pivot-rigged parts. Per the constraint to never stretch/squash/warp/rotate a flat bitmap to fake
articulation, Elly and the chair were rebuilt as **vector primitive rigs** (stroked round-cap
bones + filled circles + stroked rings), drawn in the kit's palette and proportions:

- white fluffy bichon: scalloped cloud-fur head outline, round fur-puff ears, fluffy toed paws, pom tail
- **large round glasses** (v2 identity requirement), black round nose, soft muzzle
- navy sweater with yellow stars and crescent moons, ribbed hem/cuffs
- pink scarf with a hanging tail
- wooden chair in the kit's plain-stool style, given a simple two-post backrest so Elly can face away from it

Identity is recreated from the official references; no kit pixel is warped. All structural segment
lengths are constant for the entire shot (QA gate, §5), so nothing ever stretches or collapses.

---

## 2. Architecture / pipeline

| File | Role |
|---|---|
| `scripts/styk-rig.mjs` | Rig DSL. Nodes/visuals, physical segments, primitives (`line`, `circleFill`, `circleClear` rings, plain balls), transparency, painter z-order, `.stk`/figure export. Added `visualCount`, `visualsSince`, `segmentIds`, `restLengths` for length-override animation. |
| `scripts/ik.mjs` | Analytic **two-bone IK** (law of cosines, reach clamp, bend sign), `angleDelta`, damping, footstep planning. |
| `scripts/elly-rig.mjs` | Elly + ground-shadow rigs. Root node 0 = hip. Separately controlled head, torso, two arms, two legs, paws, tail, scarf, face. |
| `scripts/chair-rig.mjs` | Fixed chair (seat planks, seams, four legs, two back posts, rail, finials, floor contact shadow) and the room/floor rig. |
| `scripts/build-v2.mjs` | Timeline builder. Bakes per-frame IK and angles, writes the `.styk`, three `.stk` rigs, and `preview/project-data.js`. |
| `scripts/qa-v2.mjs` | Numeric quality gates (§5). |
| `render/render.py` | Pillow forward-kinematics renderer matching the app geometry; honors length overrides and rings; emits MP4, GIF, contact sheet. |
| `preview/index.html` | In-browser canvas preview with the same FK + length-override + ring rules and a scrubber/beat readout. |

Outputs use **explicit held keyframes** (`auto_easing=false`, per-keyframe
`interpolation:'hold'`): every frame is fully solved, so the Python renderer, the browser preview
and the StykAnimate app all show the identical baked result rather than relying on three different
interpolators.

---

## 3. Rig and controls

Elly is a hierarchical figure whose root is the **hip**. Independent controls:

- **Spine/torso:** chest bone with per-frame lean; neck → head pivot carrying the whole head/face group.
- **Legs (×2):** thigh + shin bones solved by two-bone IK to a world-space foot target, plus a foot
  node and fluffy paw with toe lines. The solved joint angles are **baked** each frame.
- **Arms (×2):** upper + forearm with paw; FK swing during locomotion, IK to lap targets while sitting.
- **Head/face:** two round lens rings (anchored so ring centers track the eyes exactly), eyes with
  glints, sliding eyelid stubs for blinks, brows, muzzle, nose, smile line, an open-mouth ball and
  tongue that slide out during the settle, fur-puff ears.
- **Scarf & tail:** band + hanging tail and a two-bone pom tail that flip sides and wag.
- **Length overrides** animate only the eyelid, mouth and tongue stubs; every structural bone keeps
  its rest length.

---

## 4. IK and motion design

**Legs.** Stance feet are pinned to constant world targets (zero slide); swing feet follow lifted
arcs. The two feet run half a cycle apart. The stride length × cadence is deliberately matched to
hip travel (72 px step over 13 frames ≈ 5.5 px/frame, inside the 76 px two-bone reach) — an earlier
mismatch made the hips outrun the feet and forced reach-clamp "skating"; this was found and fixed.
Analytic IK is solved and baked per frame, matching StykAnimate's unpinned-IK bake semantics. The IK
bend sign is held through the pivot so knees don't pop.

**Timeline (frame ranges):**

| Phase | Frames | Notes |
|---|---|---|
| Idle | 0–11 | breathing, tail/ear drift, first blink |
| Walk | 12–91 | alternating contacts, body bounce, counter arm-swing, weight lean |
| Stop | 92–101 | eases out of the gait, settles to a stance |
| Turn | 102–127 | crossing step, torso lean, arm and tail/scarf flip, anticipatory head nod |
| Back up | 128–137 | small step to line the hips over the seat |
| Sit | 138–161 | knees bend, hips lower onto the seat, arms IK onto the lap |
| Settle | 162–185 | posture micro-adjust, two blinks, happy open-mouth pant, stable end pose |

**Hip-to-seat contact.** The seated hip target (`642, 350`) is tuned to the chair seat surface and
holds to within **0.8 px** for the whole settle. Feet stay fully planted through sit + settle.

### The turn — an explicit design decision
A literal 180° head rotation drives two symmetric eyes/lenses through an overlapping "top-down"
state that a 2D rig has no back-of-head pose for, and it produced a garbled mid-turn face. Because
the redesigned face is **near-symmetric** (round head, centered muzzle, equal lenses), its mirrored
end pose reads identically to its start. The turn is therefore carried by the **feet (crossing
step), torso lean, arms, tail and scarf**, while the head keeps a coherent near-frontal arrangement
with only a small anticipatory nod. This removes the face tangle and every boundary snap (the QA
teleport gate dropped from 116 px to ≤18.5 px on non-locomotion joints).

---

## 5. Validation (mandatory review, not just code)

1. **StykAnimate validator** — `decodeDocument → normalizeDecodedDocument → validateSceneSteps`
   passes on the written `.styk` (186 frames, no pose/figure mismatches).
2. **Numeric QA (`scripts/qa-v2.mjs`) — all green:**
   - planted paws hold constant world position through sit + settle (no foot slide);
   - paw tips never cross the floor line (range y 382.9–419.0, floor limit 420);
   - seated hip stays on the seat (max deviation 0.80 px);
   - no teleport/jump: largest non-locomotion single-frame move 18.5 px (fastest swing foot 25.1 px,
     expected for a moving foot);
   - **all structural segment lengths constant** — no stretch/squash/warp;
   - head-to-hip distance constant (139.9–140.0 px) — proportions preserved.
3. **Full visual review** — every render was inspected, not just sampled: idle, multiple walk
   contacts/swings, stop, each turn beat, backup, the whole sit, the settle, blink close-ups, the
   mouth/tongue reveal, and the 10-beat contact sheet. Defects found this way and fixed include:
   glasses displaced off-face (ring anchor lost its π angle), chair backrest tangle, a floor shadow
   floating at seat height, too-short legs reach-clamping during the walk, speed/cadence skate,
   turn-face lens/eye de-sync, and head/arm boundary snaps.
4. **Media check** — MP4 is H.264, 960×540, 24 fps, 7.75 s; GIF and contact sheet render at 960×540.

---

## 6. Honest limitations

- **Primitive replacement art, not production-rigged sprites.** The look is clean flat vector
  cartooning consistent with the kit palette, but it is geometric primitives rather than
  hand-drawn separated parts; fine fur/texture detail is simplified.
- **3/4-view approximation with a near-frontal head.** There is no true back/side head model; the
  facing change is expressed through body, feet, arms, tail and scarf rather than a full head spin.
- **2D depth is faked with painter order and scale**, not parallax/3D; the camera is locked and the
  background intentionally minimal.
- **Blink/mouth/tail** are simple length/angle-driven primitives (sliding lids, sliding mouth ball,
  two-bone tail), not shape-morphing flesh.
- IK is the analytic two-bone solver only; there is no full-body physics, cloth sim or squash
  deformation — all motion is authored key poses, breakdowns, easing and follow-through.
- The renderer is purpose-built for this figure set (line/ball/ring primitives); it is not a general
  StykAnimate renderer.

---

## 7. Deliverables (all under `v2/`)

- `render/elly-v2-walk-turn-sit.mp4` — H.264, 960×540, 24 fps, 7.75 s
- `render/elly-v2-walk-turn-sit.gif` — looping GIF, 960×540
- `render/contact-sheet.png` — 10 key-pose beats
- `animation/elly-v2-walk-turn-sit.styk` — full baked scene (186 frames, 4 figures)
- `animation/elly-v2.stk`, `chair.stk`, `room.stk` — reusable rigs/figures
- `scripts/*.mjs`, `render/render.py` — reusable rig, IK, timeline and renderer sources
- `preview/index.html` + `preview/project-data.js` — browser preview (served on port 47841)
- `scripts/qa-v2.mjs` — repeatable numeric quality gates

### Rebuild / re-check
```bash
cd v2
python3 -m venv .venv && .venv/bin/pip install -r render/requirements.txt
node scripts/build-v2.mjs     # bake the .styk, .stk and preview data
node scripts/qa-v2.mjs        # numeric quality gates
.venv/bin/python render/render.py   # MP4 + GIF + contact sheet
```
The StykAnimate schema check additionally needs a local clone of the app
(`STYK_ANIMATE_HOME=/path/to/StykAnimate-App`); the build, QA and render do not.
The pipeline is deterministic — a clean rebuild reproduces the committed MP4/GIF/contact-sheet
byte-for-byte (verified by checksum).
