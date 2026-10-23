# V3 Visual Quality Audit — Elly sprite pipeline

Date: 2026-10-23. Scope: visual/numeric audit of the shipped V3 pipeline only.
No assets were regenerated and no V4/episode work was started. All evidence
images are in this folder; numbers come from `connectivity.json` and direct
sprite measurements.

## Artifacts in this folder

| File | Content |
| --- | --- |
| `parts-sprite-sheet.png` | All 20 keyed parts, labelled, on neutral gray |
| `views.png` | Assembled Elly: front / 3-4 rotation / side-sprite swap |
| `reference-comparison.png` | Original reference next to the V3 assembled rig |
| `still-walk-strip.png` | Four walk-cycle phases (f8/f23/f38/f53) |
| `still-sit.png`, `still-talk.png`, `still-point.png` | Requested action stills |
| `face-expressions.png` | Open/smile/surprised/angry/happy/blink face close-ups |
| `tail-zoom.png`, `side-full.png` | Documented defects (tail placement, side view) |
| `connectivity.json` | Worst-frame joint coverage over all 360 clip frames + palette deltas |

## What passes

- **Keying is clean.** 0.0000% saturated-green residue on all 20 parts, fully
  transparent corners, no matte fringes visible on the gray contact sheet.
- **No disconnected limbs in the shipped clips.** Joint-coverage rasterization
  over every frame of all three clips: minimum coverage 0.40 (threshold 0.12),
  zero failures. Pointing and talking arms stay attached after the 38px
  upper/forearm overlap was baked into the rig.
- **Motion is smooth and grounded.** QA reports no teleport/jitter and planted
  feet hold the ground line; walk/sit/run read correctly as movement.
- **Core identity is recognizable.** Bichon cloud fur, black nose, droopy
  half-lidded eyes, navy star/moon sweater, pink scarf, toed paws, pom tail all
  match the reference's design language. Fur color is near-exact
  (median RGB delta 6.2) and sweater navy is close (delta 14).
- **Expression system works.** All five mouth shapes and the brow/lid parts are
  legible; talk/open, surprised O, angry frown and happy pant read at a glance.

## Defects found

### Fixable through rigging / animation code (no new art)

| # | Defect | Evidence | Suggested fix |
| --- | --- | --- | --- |
| R1 | **Tail poof lands at the front-center hem, between the legs** (looks like a third paw) instead of peeking from behind a hip. | `tail-zoom.png`, `still-sit.png`; tail pivot world (408,344), sprite ~72px wide so it spans into the front leg gap. | Move tail world target further left/back (~x392) and keep z below the legs; mostly a `build_rig_front.py` retune. |
| R2 | **Mouth shapes don't share an anchor.** Native aspect ratios run 0.69 (surprised O) to 3.06 (angry frown); all use one pivot, so the tall open/O mouths droop onto the chin while the wide smile sits correctly. | `face-expressions.png`; sprite sizes measured in audit run. | Per-mouth offset+scale table in the rig/pose layer (each shape anchored by its own visual center under the nose). |
| R3 | **Navy neck-gap crescent** between the head's fur ruff and the scarf collar. | `views.png` front panel. | Lower head pivot ~4–6px or raise torso overlap at the neck. |
| R4 | **Side view is a composite, not a real side rig.** Front-view arm/leg sprites are bolted onto the side torso: one leg dangles under the body center and the far arm floats; hidden-limb logic is incomplete. | `side-full.png`. | Build a side pose config (repositioned/hidden front limbs, side-appropriate IK targets) reusing existing sprites. Limited by missing side face art (see A1). |
| R5 | **Blink is barely perceptible** — lid travel and eye squash are small and only last ~5 frames. | `face-expressions.png` blink panel. | Increase lid slide distance and blink duration in `anim_presets.blink`. |
| R6 | **Walk is an in-place treadmill** (feet sweep x relative to a static, centered body). Fine for a loop test, not for episode staging. | `still-walk-strip.png`, QA x-sweep annotations. | Add root translation / background scroll for locomotion shots. |
| R7 | Arm raise range is capped (~0.7–1.2 rad) to keep sleeve sprites connected. | Documented in manifest; visible as compact gestures. | Can be softened with more joint overlap, but fully overhead poses also need new art (see A5). |

### Require regenerating / adding image assets

| # | Defect | Evidence | What must be generated |
| --- | --- | --- | --- |
| A1 | **Side head has no face.** `head_side.png` is a blank fluffy profile with a nose only — no side eye, brow, or mouth. Side view therefore cannot show expression or speech. | `parts-sprite-sheet.png` #02, `side-full.png`. | Side-view eye + mouth sprites (or a fully featured side head), plus a side rig to place them. |
| A2 | **No true frontal head exists.** `head_base.png` is a fixed 3/4 view with the black nose baked toward one side; a straight-on front view is impossible, and full head turns are faked with the profile swap. | `views.png` front vs 3/4 are nearly identical. | Front-facing head (centered nose, symmetric muzzle) and ideally a back-of-head sprite for full turns. |
| A3 | **Ear shape mismatch.** Reference has long, floppy hanging ears; generated `ear.png` is a round fur-puff (aspect 1.47, pom-like). | `reference-comparison.png`, parts sheet #20. | Regenerate long floppy ear sprite matching reference silhouette. |
| A4 | **Legs are too long and slender.** Reference Elly is compact with short stubby legs under a round body; the rig's standing proportions are lankier. Leg sprites are elongated fur columns. | `reference-comparison.png`, parts sheet #16–17. | Regenerate shorter/stubbier leg segments. Rig scaling can shorten them somewhat but can't fix the columnar shape. |
| A5 | **Sleeve sprites separate at steep angles** because the two independently generated sleeve pieces only overlap in a narrow pose band. | Arm-angle experiments in `qc/`; reason for R7's angle cap. | Regenerate upper/forearm as an explicit matched pair with generous shared overlap art (or one bent-arm sprite per gesture). |
| A6 | **Color drift in two materials.** Scarf pink median RGB (243,145,148) vs reference (207,115,115), delta 57 — too light/pale. Star yellow (249,210,113) vs (221,184,101), delta 40 — too pale. Navy (delta 14) and fur (delta 6) are fine. | Median sampling of opaque sprite pixels vs reference JPG. | Palette-locked regeneration; alternatively an automated HSL color-grade pass (pipeline-fixable, but it modulates the artwork and should be an explicit decision). |
| A7 | **`torso_side.png` bakes its own hem/leg nubs** (bottom 15% is 50% opaque), which fight the rigged legs in the side view. | Opaque-pixel measurement; `side-full.png`. | Regenerate a clean side torso cropped at the waist with no baked limbs. |
| A8 | **Eye style is glossier/larger than reference.** Reference eyes are small, heavy-lidded, understated; generated eyes are large glossy cartoon orbs (mitigated in-engine by drooping lids). | `reference-comparison.png`, parts sheet #05. | Optional: regenerate flatter, smaller eye/lid art if a stricter match is required. |

## Reference comparison summary

The assembled rig is unmistakably the same character and outfit, and the
fur/navy colors are faithful. The biggest visual gaps versus the reference are
(1) the compact, short-legged sitting silhouette vs the lankier standing rig,
(2) round puff ears vs long floppy ears, (3) the paler scarf and star colors,
and (4) the inability to present a true front or expressive side view with the
current head assets.

## Recommendation before V4

Proceed in two tracks: (a) apply the seven rigging-level fixes (R1–R6 are
cheap and need no new art), and (b) queue one regeneration batch targeting
A1–A4 and A7 — the side face parts, front/back head, floppy ears, stubby legs,
and clean side torso. A5/A6/A8 can follow based on how strict the episode style
target is. No episode production should start until R2 (mouth anchors) and R1
(tail) are fixed, since they are visible in every talking and standing shot.
