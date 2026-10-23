# V3 Quality Correction — Phase C Validation Report

Date: 2026-10-23. Branch `arena/b791917a-smartbark-animation-test`.
Rollback: git tag `v3-checkpoint` (commit `ac71f4d`); v1 part backups in
`v3/parts_png_v1/` and `v3/parts_raw_v1/`.

## 1. What was delivered

### Phase A — rig fixes
| # | Defect | Status | Evidence |
|---|--------|--------|----------|
| R1 | tail position / layering | **fixed** | tail at (382,386), z=1, peeks behind left hip; visible in `views-v2.png` |
| R2 | one anchor per mouth shape | **fixed** | `MOUTH_ANCHORS` table; per-shape dx/dy/scale; QA gate `check_mouth_alignment` passes all 5 mouths |
| R3 | neck-gap crescent | **fixed** | head lowered to world y285; ruff overlaps collar (see before/after) |
| R4 | dedicated side-view config | **fixed** | `p_side_view` swaps side head+torso, hides far-side limbs, near arm hangs down, near leg pinned with bend=-1 (shin vertical), flat sole; featured profile head now connected — signed off below |
| R5 | weak blink | **fixed** | duration 0.30s, lid travel −14px, eye scale_y 0.75; new thinner lid recalibrated (world scale 0.080→0.060); full close visible in `qc/v2-blink-seq2.png` |
| R6 | root-motion walk | **fixed** | `pin_foot()` does IK then inverse-FK correction so the foot pivot lands *exactly* on the world contact; planted-foot measured drift **0.0px x / 0.0px y** for both feet; parallax world scrolls past |
| R7 | (arm gesture retune) | **fixed** | point/talk/happy amplitudes ~0.55 rad after compacting proportions |

Additional fix this round: `p_head_turn` no longer calls `blink()` while the
profile sprite is active — `blink()` was re-enabling the front-face lids,
which floated over the side head. Verified in `qc/v2-headturn-fix.png`.

### Phase B — selective regeneration (12/12 complete)
All planned parts are regenerated and keyed. The last three landed this round:
- `eyelid.png` — new half-dome lid with bold lower edge and lashes (710×413),
  rig world scale recalibrated to preserve the v1 on-screen width.
- `eyebrow.png` — thin relaxed arc (replaces the thick stern v1 brow);
  rest angles ±0.12 kept.
- `head_side.png` — fully featured left profile (nose, sleepy eye, thin brow,
  smile, floppy ear, neck ruff); replaces the blank v1 profile. It required
  the alternate multi-model image path (the primary endpoint repeatedly
  returned finishReason NONE); the user selected the final option.
- All 20 keyed parts pass green-screen removal: residual green **0.0000%**.

## 2. Phase C deliverables

| Deliverable | Path |
|---|---|
| Before/after comparison (checkpoint vs corrected) | `validation/before-after.png` |
| Updated 20-part sprite sheet (all 12 regen marked `*`) | `validation/sprite-sheet-v2.png` |
| Front / 3-4 / side assembled views | `validation/views-v2.png` |
| Palette + keying + proportion measurements | `validation/consistency.json` |
| Four 5s clips (MP4 **and** GIF), 120 frames @24fps | `clips/{walk,talk,sit,point}_5s.{mp4,gif}` |
| Per-clip contact sheets | `qc/{walk,talk,sit,point}_5s-sheet.png` |
| Automated audit (joint coverage + palette) | `audit/connectivity.json` |
| QA gate summary + full logs | `qc/qa-summary.json`, `qc/full-qa-log3.txt` |

## 3. Automated validation results

- **QA pipeline (`qa_pipeline.run_all`) — all four clips: ALL CHECKS PASS.**
  Gates: transparency/keying, limb connectivity, joint coverage, foot contact
  (no slide), mouth alignment, motion smoothness (no teleport).
- **Foot contact, root walk:** max per-frame planted-foot drift = 0.0px;
  contact shadow stays under the body while the background scrolls (visual).
- **Joint coverage** (opaque fraction around each joint, threshold 0.12):
  refreshed audit in `audit/connectivity.json` (no joint below threshold in
  walk/talk/sit/point).
- **Mouth alignment:** all five mouths stay inside the head footprint on
  every sampled frame of talk/surprise/angry/happy/idle.
- **Palette vs identity anchor** (RGB euclidean distance of medians):
  fur 8.3, navy 16.1, scarf 12.7, yellow 17.0 — small deltas; identity colors,
  scalloped fur, star/moon sweater and pink scarf retained (visually confirmed).
- **Residual chroma green:** 0.0000% across all 20 parts.

## 4. Visual review (mandatory; numeric results are not treated as sufficient)

- `walk_5s`: genuine forward travel, alternating gait, both feet visibly plant
  and hold while parallax bushes/clouds scroll; no sliding.
- `talk_5s`: seated, talk mouth opens/closes under the nose, visible blink,
  gesture arm stays in frame.
- `sit_5s`: stable seated idle with breathing/brow motion; no foot slide.
- `point_5s`: pointing arm raises, holds, lowers smoothly; returns to neutral
  without teleport.
- `views-v2.png`: front is symmetrical; 3/4 reads; **side profile now signed
  off** — featured head, connected neck, hanging near arm, vertical shin and
  flat grounded foot, far limbs hidden.
- `before-after.png`: corrected Elly is front-facing and symmetrical, neck gap
  gone, tail behind hip, stubby compact legs.
- `sprite-sheet-v2.png`: outline/color consistency across all 20 parts.
- `v2-blink-seq2.png`: half-lidded rest → fully closed (f2–f4) → open (f8).
- `v2-headturn-fix.png`: turn apex shows the clean profile with no floating lids.

## 5. Scope / engine safety

- No full episode production was started, per instruction.
- The engine was not rebuilt: changes were additive (`rest_angle`, `pin_foot`,
  mouth anchors, `p_side_view`, blink-suppression during turns, mouth QA gate);
  all pre-existing presets still render and pass.
- Rollback remains available at tag `v3-checkpoint` and the v1 part backups.
