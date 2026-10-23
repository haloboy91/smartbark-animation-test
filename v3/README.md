# Elly V3 — fully automated 2D sprite animation pipeline

V3 replaces the hand-built vector rig of V2 with an end-to-end automated
pipeline: the reference character is split by an image model into separate
green-screen body parts, the green is removed by a chroma-key stage, the
transparent parts are assembled into a skeletal sprite rig, and the rig is
driven through intent-based animation presets whose output is gated by
automated QA before MP4/GIF export.

## Pipeline stages

| Stage | Script | Output |
| --- | --- | --- |
| 1. Part generation | image model (10 images/turn batches), green `#00FF00` backgrounds | `parts_raw/*.png` (gitignored) |
| 2. Chroma key + QC | `scripts/keyout.py` | `parts_png/*.png` — 20 transparent parts, 0.0000% residual green |
| 3. Rig build | `scripts/build_rig_front.py` | `rig/rig_front.json` — 23 nodes from world-space joint targets |
| 3. Rig engine | `scripts/sprite_engine.py` | pivot FK with parent-scale inheritance, analytic two-bone IK, per-pose image + z swaps |
| 4. Presets | `scripts/anim_presets.py` | 11 presets: idle, walk, run, sit, talk, point, surprised, angry, happy, head turn, body turn |
| 5. QA + export | `scripts/qa_pipeline.py`, `scripts/render_clips.py` | gated `clips/*.mp4` + `clips/*.gif` |
| Calibration | `scripts/calibrate.py` | joint-marker render for tuning `build_rig_front.py` |

## Running it

```bash
# one-time deps (free / open source)
pip install Pillow imageio imageio-ffmpeg numpy opencv-python-headless

# from v3/
../.venv/bin/python scripts/keyout.py           # green-screen -> transparent PNG + part QC
../.venv/bin/python scripts/build_rig_front.py  # regenerate rig JSON from joint targets
PYTHONPATH=scripts ../.venv/bin/python scripts/calibrate.py rig_front.json qc/calibrate-front.png
PYTHONPATH=scripts ../.venv/bin/python scripts/render_clips.py   # QA gates, then MP4+GIF
```

A clip is only exported when every QA check passes; a failed run stops export
and writes a contact sheet for diagnosis.

## QA gates (191 PASS / 0 FAIL on the shipped run)

1. **Transparency** — real alpha on every part, zero saturated-green residue,
   transparent corners.
2. **Proportions** — assembled character height stays within ±12% of the
   calibrated neutral height.
3. **Joint continuity** — rasterized opaque coverage at every joint pivot
   (no visible gaps; the forearm is tucked ~38px inside the upper sleeve and
   other joints overlap artwork similarly).
4. **Foot contact** — planted feet hold a constant ground line; sitting and
   pointing clips additionally pin x (zero horizontal slide). The centered
   walk loop uses an authored x sweep relative to the static-camera body with
   strict vertical contact.
5. **Motion smoothness** — per-node per-frame position/rotation deltas bounded
   so nothing teleports or jitters.

## Deliverables (clips/)

- `walk_5s.mp4/.gif` — full walk cycle, IK legs with pinned soles, counter-swing arms
- `sit_talk_5s.mp4/.gif` — seated fold, syllable-driven mouth swaps, illustrative paw raises
- `point_react_5s.mp4/.gif` — pointing-paw raise/hold/lower, then surprised reaction

MP4s are 120 frames at 24 fps (exactly 5.00 s, H.264/yuv420p). GIFs are
480×270; the format quantizes frame timing to 10 ms, so they run ~5.04 s.

## Honest limitations

- `head_base.png` is a 3/4-view sprite with the black nose baked in; the
  independent eyes/brows/mouth layer over its blank feature area. There is no
  back-of-head art, so turns use the `head_side`/`torso_side` sprites inside a
  limited angle range rather than a full 360° spin.
- The two sleeve sprites only remain visually connected within a limited raise
  range, so arm presets are deliberately angle-limited instead of allowing
  forearms to detach.
- All twenty parts come from independent image-model generations; identity is
  held by the reference-anchored prompts and verified on the assembled rig.
  No part was repaired with primitive shapes or manual cutout work — defective
  parts are meant to be regenerated through the same stage.
