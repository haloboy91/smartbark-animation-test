#!/usr/bin/env python3
"""Lay every Elly cutout out on a checkerboard contact sheet for review.

Composited over a checkerboard so keying mistakes (green/black fringes, half
keyed plates) are obvious, plus a second row-band over a 1929 sepia swatch so
you can see how she sits against the episode's actual palette.
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
from PIL import Image, ImageDraw

CELL = 300
PAD = 14
LABEL = 26


def checker(w: int, h: int, sq: int = 16) -> Image.Image:
    yy, xx = np.mgrid[0:h, 0:w]
    t = ((xx // sq) + (yy // sq)) % 2
    a = np.where(t == 0, 245, 205).astype(np.uint8)
    return Image.fromarray(np.dstack([a, a, a]), "RGB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="assets/elly/cutouts")
    ap.add_argument("--out", default="docs/elly_pose_contact_sheet.png")
    ap.add_argument("--cols", type=int, default=6)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src, "*.png")))
    if not files:
        raise SystemExit(f"no cutouts in {args.src}")

    cols = args.cols
    rows = (len(files) + cols - 1) // cols
    W = cols * (CELL + PAD) + PAD
    H = rows * (CELL + LABEL + PAD) + PAD

    sheet = Image.new("RGB", (W, H), (28, 28, 32))
    board = checker(W, H)
    sheet.paste(board, (0, 0))
    d = ImageDraw.Draw(sheet)

    for i, f in enumerate(files):
        im = Image.open(f).convert("RGBA")
        name = os.path.splitext(os.path.basename(f))[0]
        cx = PAD + (i % cols) * (CELL + PAD)
        cy = PAD + (i // cols) * (CELL + LABEL + PAD)

        # fit inside the cell, preserving aspect
        s = min(CELL / im.width, (CELL - 10) / im.height)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        ox = cx + (CELL - im.width) // 2
        oy = cy + (CELL - im.height)
        sheet.paste(im, (ox, oy), im)

        d.rectangle([cx, cy, cx + CELL, cy + CELL + LABEL], outline=(70, 70, 78), width=1)
        label = name if len(name) <= 26 else name[:25] + "\u2026"
        d.text((cx + 6, cy + CELL + 6), label, fill=(235, 235, 240))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    sheet.save(args.out)
    print(f"{len(files)} poses -> {args.out} ({W}x{H})")


if __name__ == "__main__":
    main()
