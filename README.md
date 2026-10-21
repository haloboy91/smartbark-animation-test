# smartbark-animation-test

Elly pose library + animation test rig for **Smart Bark EP015 — "How Some People
Got Rich During the Great Depression (1929)"**.

## What's here

```
assets/elly/
  cutouts/      transparent PNG poses  <-- what the renderer loads
  greenscreen/  raw generator output (gitignored, intermediate)
  poses.json    the contract: pose table + storyboard beat routing
## The rig (live preview)

Everything composites through one function, `paintFrame()` in
`web/js/compose.js`. The live preview and the proof-sheet export both call it,
so a proof frame is pixel-identical to what you see on screen - the brief asks
for proof frames at every chapter opening and dramatic change, and they are only
useful if they show the real composite (camera + Elly + overlays).

The **Proof sheet** button renders one frame per shot and downloads it as a PNG,
labelled and tinted so shots still on procedural fallback are obvious at a
glance. That is the review artefact for framing problems, captions colliding
with Elly, and plates that do not leave the right third clear.

```
python3 tools/build_web_assets.py   # poses.json -> web/js/poses.js
python3 tools/build_script_js.py    # docs/script.txt -> web/js/script.js
python3 tools/build_timeline.py     # storyboard -> web/js/timeline.js
python3 -m http.server 8000 --bind 0.0.0.0
```

## Tools

```
tools/
  key_elly.py            plate -> transparent cutout (black AND green plates)
  validate_poses.py      quality gate for generated plates, run before keying
  check_no_drive_assets.py  guard: no Drive-sourced Elly may enter the project
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

`33 / 33` poses cut out - library complete. **217** storyboard "ELLY ACTIVENESS" beats are routed to
canonical poses, **0 unresolved**. Run for the current state:

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

## No Elly from Google Drive

Nothing from Drive is used. The "Elly Behavior" masters and Kit v2's knight-Elly
set are excluded by policy, and `tools/check_no_drive_assets.py` enforces it with
an md5 blocklist of the originals (captured before deletion), filename patterns,
and a scan of the git index. Run it after any asset update:

```bash
python3 tools/check_no_drive_assets.py   # exit 1 if Drive art reappears
```

Every pose in `cutouts/` is AI-generated from a text prompt on a flat chroma-green
plate, anchored on our own generated art rather than on any Drive image.

### Why those photos can't be used at all

The 11 original masters are kept **only as identity anchors for image
generation** - never as cutouts. Their plate is pure black, and Elly's signature
look is *thick black outlines*. Plate and outline sit at the same luminance, so
any luminance key makes the outline itself semi-transparent: the character comes
out ragged and broken.

Every pose shipped to the renderer is therefore generated on a flat chroma-green
plate and keyed with `tools/key_elly.py`. The generator is anchored on our own
clean-pose art (`elly_solemn_direct.png`), not on the Drive photos, which also
keeps identity consistent across the set.

Consequence: Kit v2's note that the Drive filenames are mismatched
(`03_Proud` is actually worried, `10_Crying` actually sleepy, ...) no longer
matters - those files are never used as poses.

## Quality gate

```bash
python3 tools/validate_poses.py --src assets/elly/greenscreen --strict
```

Rejects a generated plate if it has no usable green plate, if the plate is a
gradient rather than flat (which leaves a halo), if the navy sweater / pink
scarf / white fur signature has drifted, or if the character is too small or
cropped by the frame.

It has already earned its keep: the first `elly_newspaper` attempt looked fine
but failed the gate with navy 0.2% / pink 0.0% - the newspaper was covering
Elly's whole body, hiding both her and her outfit. Rejected plates are kept in
`greenscreen/rejected/` with the reason recorded in the manifest.

The retry then came back with a **vignetted** plate (ring sd 11.3) rather than a
flat one, which a single global key value would have turned into a halo around
her. `key_elly.py` therefore estimates the plate as a smooth *field* - the local
average greenness of confidently-background pixels - so varying plates key
cleanly. Measured green leak inside the opaque body: max 0.63% across all 33.
