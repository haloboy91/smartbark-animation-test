# Smart Bark — Elly Animation (Motion Canvas proof of concept)

A small 2D character-animation proof of concept for the **Smart Bark** YouTube
channel, built with [Motion Canvas](https://motioncanvas.io/) (TypeScript).

- **Scene length:** 10 seconds
- **Resolution / frame rate:** 1920×1080 @ 30 fps
- **Character:** Elly, used exactly as supplied in the reference artwork —
  the project does **not** redraw or redesign her
- **Stack:** Motion Canvas 3.17.2, Vite 5, TypeScript — all free and
  open-source (MIT). The MP4 encoder (FFmpeg) is installed as an npm package,
  so no system-level FFmpeg install is required.

## The shot

1. Elly enters from off-screen left and walks toward the center with a
   procedural walk cycle (body bob, wobble, contact shadow, squash & stretch).
2. She stops, settles, and turns to face the camera (2D pose flip).
3. A short curious beat.
4. Surprise reaction: anticipation squash, jump with a stretch, pop-in
   exclamation mark and accent lines, camera punch-in with a shake.
5. Hold: nervous tremble, floating exclamation mark, slow camera push-in.

The background is a simple illustrated night scene (gradient sky, twinkling
stars, glowing moon, drifting clouds, layered hills) drawn entirely with
Motion Canvas shapes.

## Prerequisites

- [Node.js](https://nodejs.org/) 18+ (developed and tested on Node 22) and npm
- Only needed if you want to regenerate the cut-out from a new reference:
  Python 3 with `pip install pillow numpy`

## Quick start

```bash
npm install
npm start
```

Then open the local URL printed by Vite (default <http://localhost:5173/>).
This launches the Motion Canvas **editor**:

- Press **Space** (or the play button) to play the animation.
- Drag the playhead on the timeline to scrub frame by frame.
- The preview runs at 1920×1080 @ 30 fps as configured in
  [`src/project.meta`](src/project.meta).

Other scripts:

| Command | Purpose |
| --- | --- |
| `npm start` / `npm run dev` | Start the editor dev server |
| `npm run build` | Production build (validates the whole project bundles) |
| `npm run typecheck` | TypeScript check only |
| `npm run prepare-elly` | Re-run the reference-image cut-out script |

## Exporting an MP4

The [`@motion-canvas/ffmpeg`](https://www.npmjs.com/package/@motion-canvas/ffmpeg)
plugin is already wired up in [`vite.config.ts`](vite.config.ts), and the
rendering settings in [`src/project.meta`](src/project.meta) are preconfigured
to **1920×1080, 30 fps, sRGB, exporter "Video (FFmpeg)"**.

1. With `npm start` running, open the editor.
2. Open the **Video Settings** panel (left sidebar) and confirm:
   - Resolution `1920 × 1080`
   - Rendering frame rate `30`
   - Exporter **Video (FFmpeg)**
3. Open the **Export** panel, press the export button, and wait for the
   browser to render all 300 frames. The dev server encodes them locally.
4. The finished file is written to **`output/project.mp4`** (H.264 MP4,
   `fastStart` enabled so it streams well on YouTube).

### Alternative: PNG sequence + external FFmpeg

If you prefer to encode yourself, choose the image-sequence exporter in the
Export panel, then run (with a [system FFmpeg](https://ffmpeg.org/) installed):

```bash
ffmpeg -framerate 30 -i output/project/%06d.png -c:v libx264 -pix_fmt yuv420p output/elly.mp4
```

## Project structure

```
.
├── index.html                  # Vite entry (loads src/project.ts?project)
├── vite.config.ts              # Motion Canvas + FFmpeg exporter plugins
├── tsconfig.json
├── src
│   ├── project.ts              # Scene registration
│   ├── project.meta            # Resolution, fps, background, exporter config
│   ├── global.css
│   ├── scenes
│   │   ├── elly.scene.tsx      # The 10-second scene (all animation lives here)
│   │   └── elly.scene.meta     # Auto-generated scene metadata
│   └── assets
│       ├── elly.png            # Transparent cut-out used by the scene
│       └── reference
│           └── 02_Elly_Pointing_Explain_FamilyGuy.jpg  # Original reference
└── scripts
    └── prepare-elly.py         # Black-background removal (no redrawing)
```

## How Elly's artwork is handled

The supplied reference is a flat cartoon illustration on a pure black
background. [`scripts/prepare-elly.py`](scripts/prepare-elly.py) produces the
transparent `src/assets/elly.png` used by the scene by:

1. Flood-filling the black background **from the image edges only**, so
   interior black artwork (outlines, nose, eyes) is never touched;
2. Removing the soft gray ground-shadow ellipse (the scene renders its own
   animated contact shadow);
3. Eroding one pixel and feathering the edge to avoid a black fringe;
4. Auto-cropping to the artwork.

Nothing is recolored, redrawn, or redesigned. The exclamation mark and
surprise accent lines are generic scene elements, not character features.

To use a different reference image: replace the JPG in
`src/assets/reference/` and run `npm run prepare-elly`, or simply overwrite
`src/assets/elly.png` with any transparent character PNG.

## Scope

This is a proof of concept, not a video production pipeline: a single
10-second scene, one character, no audio, and no reusable rigging system.
All animation is defined declaratively in `elly.scene.tsx` with keyframe
tweens, signal-driven procedural motion, and a camera node.
