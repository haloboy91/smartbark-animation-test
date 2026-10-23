# Smartbark animation test — Elly walks to the table

A 2D character animation built for the
[**StykAnimate-App**](https://github.com/filippocalippo/StykAnimate-App)
(free, open-source Pivot/Stick Nodes-compatible animation studio).

The dog **Elly** is an original 2D figure based on the attached reference art —
a fluffy white dog wearing a navy star-and-moon sweater, a pink scarf and a
black nose. In a ~7-second, 164-frame shot she:

1. idles,
2. **walks to the table**,
3. **sits down** beside it,
4. holds the sit (with breathing / tail / ear motion),
5. leans forward and **stands up** again.

## What's in this repo

```
animation/
  dog-walk-sit-stand.styk   ← open this in StykAnimate (native plain-JSON project)
  smartbark-dog.stk         ← Pivot v5 figure: Elly (reusable in any project)
  table.stk                 ← Pivot v5 figure: table with dog bowl
  room.stk                  ← Pivot v5 figure: floor strip
preview/
  index.html                ← self-contained browser player (play, scrub, loop)
  project-data.js           ← generated animation data used by the player
render/
  dog-walk-sit-stand.mp4    ← rendered H.264 preview
  dog-walk-sit-stand.gif    ← animated GIF preview
  contact-sheet.png         ← key story-beat grid
  render.py                 ← Pillow/ffmpeg renderer (same FK math as the app)
scripts/
  styk-rig.mjs              ← small rig DSL (bones, stubs, filled circles, outlines)
  dog-rig.mjs               ← Elly figure definition (117 segments)
  scene-rig.mjs             ← table + room figure definitions
  build-project.mjs         ← assembles the 164-frame animation and all files
  validate-project.mjs      ← runs StykAnimate's own loader/validator on the .styk
  cross-check.mjs           ← compares every joint with StykAnimate's geometry engine
```

## Opening it in StykAnimate

1. Install / open StykAnimate (desktop build, or the browser app at
   <https://app.stykanimate.com>).
2. **File → Open** and choose `animation/dog-walk-sit-stand.styk`.
   It is a plain-JSON native project, so it opens with no backend/codec setup
   and every one of the 164 keyframes is fully editable.
3. Press **Play**. The timeline shows the simple Pivot-style frame strip;
   each frame is an explicit held pose (`duration_raw = 1`), the classic
   frame-by-frame Pivot workflow.
4. To reuse Elly elsewhere, **File → Import figure** with
   `animation/smartbark-dog.stk` (a modern Pivot v5 `aff7f8` STK container).

## How the character is built

StykAnimate/Pivot figures are trees of fixed-length segments
(`end = parent + length · (cos angle, sin angle)`, y-down). The helper in
`scripts/styk-rig.mjs` turns that into a small rig DSL:

- `bone(...)` — a thick round line, emitted as a black "outline" twin plus a
  colored twin, so the character gets the bold cartoon outline of the
  reference art;
- `ball(...)` — a filled circle (Pivot `circleFill` primitive) drawn as a
  black ring behind a colored disc;
- `stub(...)` — an invisible zero-thickness segment used to place details
  (eyes, nose, stars, paws, head/ear pivots).

Elly uses 117 segments across about 60 posable nodes: two-bone arms and legs
with fluffy paw balls, a curled tail, two-bone floppy ears, a big fluffy
head with snout/nose/eyes/eyebrows, a pink scarf collar, and a yellow
star/moon band on the navy sweater. Every pose is authored as absolute node
angles in `scripts/build-project.mjs`.

## Rebuilding

```sh
npm run build        # regenerate animation/*.styk, *.stk and preview/project-data.js
npm run validate     # StykAnimate's own decode + full scene validation
npm run cross-check  # joint-by-joint match vs StykAnimate's geometry engine
pip install -r render/requirements.txt
npm run render       # GIF, MP4 and contact sheet in render/
```

`validate` and `cross-check` need a local checkout of StykAnimate-App next to
this repo (or set `STYK_ANIMATE_HOME` to its path).

## Verification

- StykAnimate's `decodeDocument` + `validateSceneSteps` accept the project:
  164 frames, 3 figures, every pose array matching its figure definition.
- All three `.stk` files decode via StykAnimate's Pivot v5 `aff7f8` parser
  with a 1.0 valid-segment ratio, colors and draw order preserved.
- The cross-check evaluates 1,740 joints across 12 frames with the app's own
  geometry engine: **worst positional delta 0.00 px**, so the bundled
  previews are pixel-identical in geometry to what StykAnimate renders.
