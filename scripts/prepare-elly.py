#!/usr/bin/env python3
"""Prepare Elly's reference artwork for Motion Canvas.

The supplied reference is a flat-cartoon illustration on a pure black
background. This script:

1. Flood-fills the black background starting from the image edges.
   Interior black pixels (Elly's outlines, nose, eyes) are enclosed by
   colored shapes, so they are never reached and stay untouched.
2. Removes the soft gray ground-shadow ellipse under her feet (the scene
   provides its own animated contact shadow).
3. Erodes the cutout by one pixel to avoid a black fringe, then feathers
   the edge slightly for clean anti-aliasing.
4. Auto-crops to the artwork's bounding box and writes a transparent PNG.

It does NOT redraw, recolor, or otherwise redesign the character.

Usage:
    python3 scripts/prepare-elly.py
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src/assets/reference/02_Elly_Pointing_Explain_FamilyGuy.jpg"
DST = ROOT / "src/assets/elly.png"

# How different a pixel may be from pure black to count as background.
BG_TOLERANCE = 48
# Marker color used while flood-filling (does not appear in the artwork).
MARKER = (255, 0, 255)


def main() -> None:
    image = Image.open(SRC).convert("RGB")
    width, height = image.size
    pixels = np.asarray(image).astype(np.int16)

    # --- 1. Flood fill the black background from all four edges ----------
    work = image.copy()
    draw = ImageDraw.Draw(work)
    seeds = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    for seed in seeds:
        ImageDraw.floodfill(work, seed, MARKER, thresh=BG_TOLERANCE)

    filled = np.asarray(work)
    is_background = np.all(filled == MARKER, axis=-1)

    # --- 2. Drop the gray ground shadow in the bottom strip --------------
    luminance = pixels.mean(axis=-1)
    max_channel = pixels.max(axis=-1)
    min_channel = pixels.min(axis=-1)
    saturation = max_channel - min_channel
    bottom_band = np.zeros((height, width), dtype=bool)
    bottom_band[int(height * 0.86) :, :] = True
    is_gray_shadow = (
        bottom_band & (saturation < 28) & (luminance < 205) & ~is_background
    )

    mask = ~(is_background | is_gray_shadow)
    cutout = Image.fromarray((mask * 255).astype(np.uint8), mode="L")

    # --- 3. Kill the dark fringe, then feather the edge ------------------
    cutout = cutout.filter(ImageFilter.MinFilter(3))  # 1px erode
    cutout = cutout.filter(ImageFilter.GaussianBlur(0.8))

    result = image.convert("RGBA")
    result.putalpha(cutout)

    # --- 4. Auto-crop to content, with a small breathing pad -------------
    bbox = cutout.getbbox()
    if bbox is None:
        raise RuntimeError("Background removal produced an empty image")
    pad = 16
    left = max(bbox[0] - pad, 0)
    top = max(bbox[1] - pad, 0)
    right = min(bbox[2] + pad, width)
    bottom = min(bbox[3] + pad, height)
    result = result.crop((left, top, right, bottom))

    DST.parent.mkdir(parents=True, exist_ok=True)
    result.save(DST)
    print(f"Wrote {DST.relative_to(ROOT)} ({result.size[0]}x{result.size[1]})")


if __name__ == "__main__":
    main()
