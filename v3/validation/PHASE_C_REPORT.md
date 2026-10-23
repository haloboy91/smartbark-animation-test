# V3 Quality Correction — Phase C Validation Report

Date: 2026-10-23. Branch `arena/b791917a-smartbark-animation-test`.
Rollback: git tag `v3-checkpoint` (commit `ac71f4d`); v1 part backups in
`v3/parts_png_v1/` and `v3/parts_raw_v1/`.

## 1. What was delivered

### Phase A — rig fixes
| # | Defect | Status | Evidence |
|---|--------|--------|----------|
| R1 | tail position / layering | **fixed** | tail repositioned to (382,386), z=1, peeks behind left hip; visible in `views-v2.png` |
| R2 | one anchor per mouth shape | **fixed** | `MOUTH_ANCHORS` table; per-shape dx/dy/scale; new QA gate `check_mouth_alignment` passes all 5 mouths |
| R3 | neck-gap crescent | **fixed** | head lowered to world y285; ruff overlaps collar (see before/after) |
| R4 | dedicated side-view config | **mechanism done, blocked on art** | `p_side_view` swaps side sprites, hides far-side limbs, repositions near arm/leg with pinned flat foot; profile head is still the blank v1 sprite pending regen |
| R5 | weak blink | **fixed** | duration 0.30s, lid travel −14px, eye scale_y 0.75 |
| R6 | root-motion walk | **fixed** | new `pin_foot()` does IK then inverse-FK correction so the foot pivot lands *exactly* on the world contact; planted-foot measured drift **0.0px x / 0.0px y** for both feet; world scrolls via parallax background |
| R7 | (arm gesture retune) | **fixed** | point/talk/happy amplitudes retuned to ~0.55 rad after compacting proportions |

### Phase B — selective regeneration
- **9 of 12 planned parts regenerated and keyed**: head_base (symmetrical front, nose centered), ear, torso, torso_side, arm_upper, arm_lower_paw, leg_upper, leg_lower, eye_open.
- All 20 keyed parts pass green-screen removal: residual green **0.0000%** on every part (`keyout.py`, `consistency.json`).
- **Still pending — blocked only by the 10-image/turn generation quota, not art rejection**:
  `head_side.png` (v1 is a blank, featureless profile), `eyelid.png`, `eyebrow.png`
  (v1 brow is thick and reads stern; thinner relaxed-arc prompt is queued).
  These three remain v1 sprites and must not be treated as regenerated.

## 2. Phase C deliverables (this report's folder + clips/)

| Deliverable | Path |
|---|---|
| Before/after comparison (checkpoint vs corrected) | `validation/before-after.png` |
| Updated 20-part sprite sheet (regen parts marked `*`) | `validation/sprite-sheet-v2.png` |
| Front / 3-4 / side assembled views | `validation/views-v2.png` |
| Palette + keying + proportion measurements | `validation/consistency.json` |
| Four 5s clips (MP4 **and** GIF), 120 frames @24fps | `clips/{walk,talk,sit,point}_5s.{mp4,gif}` |
| Per-clip contact sheets | `qc/{walk,talk,sit,point}_5s-sheet.png` |
| Automated audit (joint coverage + palette) | `audit/connectivity.json`, `qc/audit-rerun.log` |
| QA gate summary | `qc/qa-summary.json`, `qc/full-qa-log.txt` |

## 3. Automated validation results

- **QA pipeline (`qa_pipeline.run_all`) — all four clips: ALL CHECKS PASS.**
  Gates: transparency/keying, limb connectivity, joint coverage, foot contact
  (no slide), **mouth alignment (new)**, motion smoothness (no teleport).
- **Foot contact, root walk:** stance windows derived from the same gait
  parametric; max per-frame planted-foot drift = 0.0px (numeric) and contact
  shadow stays under the body while the background scrolls (visual).
- **Joint coverage** (fraction of opaque pixels around each joint, threshold 0.12):
  walk min 0.357, talk 0.366, sit 0.373, point 0.388 — no joint below threshold
  in any clip.
- **Mouth alignment:** all five mouth shapes stay inside the head footprint on
  every sampled frame of talk/surprise/angry/happy/idle.
- **Palette vs identity anchor** (RGB euclidean distance of medians):
  fur 8.3, navy 16.1, scarf 12.7, yellow 17.0 — small deltas; identity colors,
  scalloped fur, star/moon sweater and pink scarf retained (visually confirmed).
- **Residual chroma green:** 0.0000% across all 20 parts.

## 4. Visual review (mandatory; numeric results are not treated as sufficient)

Contact sheets and stills were inspected frame-by-frame:
- `walk_5s`: genuine forward travel, alternating gait, both feet visibly plant
  and hold while the parallax bushes/clouds scroll; no moonwalking/sliding.
- `talk_5s`: seated, talk mouth opens/closes under the nose, blink visible,
  gesture arm stays in frame.
- `sit_5s`: stable seated idle with breathing/brow motion; no foot slide.
- `point_5s`: pointing arm raises, holds, lowers smoothly; hand-point sprite
  aimed outward; body returns to neutral without teleport.
- `before-after.png`: corrected Elly is front-facing and symmetrical, neck gap
  gone, tail visible behind hip, stubby legs and compact proportions.
- `sprite-sheet-v2.png`: part outlines/colors consistent; the three v1 parts
  (02 head_side, 06 eyelid, 07 eyebrow) are visibly the older assets.
- `views-v2.png`: front and 3/4 read correctly. **Side view is explicitly NOT
  signed off** — the blank profile head is a known pending regeneration; the
  configuration around it is proven and will inherit the new head automatically.

## 5. Honest open items / not done

1. Regenerate `head_side`, `eyelid`, `eyebrow` (quota-blocked; first action of
   the next turn), re-run `keyout.py`, then re-verify the side view and blink.
2. Final visual sign-off of the side profile after the new head lands.
3. No full episode production was started, per instruction.
4. The engine was not rebuilt: changes were additive (`rest_angle`, `pin_foot`,
   mouth anchors, side preset, QA gate); all pre-existing presets still render.
