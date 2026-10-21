# smartbark-animation-test

Elly pose library + animation test rig for **Smart Bark EP015 — "How Some People
Got Rich During the Great Depression (1929)"**.

## What's here

```
assets/elly/
  references/   11 original Family Guy Elly masters (Drive "Elly Behavior" folder)
  cutouts/      transparent PNG poses  <-- what the renderer loads
  greenscreen/  raw generator output (gitignored, intermediate)
  poses.json    the contract: pose table + storyboard beat routing
tools/
  key_elly.py            plate -> transparent cutout (black AND green plates)
  contact_sheet.py       contact sheet for visual review
  build_pose_manifest.py builds assets/elly/poses.json, fails on missing art
  fetch_kit.sh           how to re-fetch Kit v2 from Drive
docs/
  EP015_storyboard_brief.txt
  elly_pose_contact_sheet.png
```

## Elly's signature (locked)

White fluffy bichon · round black-rimmed glasses · navy sweater with white stars
and crescent moons · pink scarf · 2D cartoon, thick clean outlines, flat colour,
soft shadows. Small period flourishes (e.g. a 1920s newsboy cap) are fine; the
signature always stays.

## Pose status

`20 / 34` poses cut out. **217** storyboard "ELLY ACTIVENESS" beats are routed to
canonical poses (`6` unresolved → neutral thinking). Run for the current state:

```bash
python3 tools/build_pose_manifest.py
```

It prints the per-pose beat counts and a **generation queue** — the poses the
storyboard demands most that don't exist yet.

## Pipeline

```bash
# 1. key the original references (black plate)
python3 tools/key_elly.py --src assets/elly/references --dst assets/elly/cutouts

# 2. key newly generated poses (green plate)
python3 tools/key_elly.py --src assets/elly/greenscreen \
                          --dst assets/elly/cutouts --bg green

# 3. rebuild the manifest + contact sheet
python3 tools/build_pose_manifest.py
python3 tools/contact_sheet.py --src assets/elly/cutouts --out docs/elly_pose_contact_sheet.png
```

`key_elly.py` auto-detects the plate. The green path **auto-calibrates** to the
plate colour: Kit v2's own keyer hard-codes `greenness > 80`, which is correct
for its pure `(0,255,0)` knight plates but keys out almost nothing on the muted
sage green (≈ RGB 90,160,105, greenness 55) that the image generator returns.

## ⚠️ Open question: reference labels

Kit v2's README says the Drive Elly filenames are **wrong**:

| filename says | README says it actually is |
|---|---|
| `03_Elly_Proud_PiggyBank` | worried |
| `04_Elly_Worried` | proud (piggy bank) |
| `06_Elly_Excited` | waving |
| `07_Elly_Sitting_Quiet` | excited |
| `08_Elly_Welcome_Waving` | sitting |
| `10_Elly_Crying` | sleepy |
| `12_Elly_Sleepy` | crying |

These poses are therefore committed under neutral ids (`ref03`, `ref04`,
`ref06`, `ref07`, `ref08`, `ref10`, `ref12`) and flagged `LABEL UNVERIFIED` in
`poses.json`. **Please confirm against `docs/elly_pose_contact_sheet.png`** and
the ids will be renamed to semantic ones. `09_Elly_Thinking` is confirmed — it's
the master supplied for EP015.
