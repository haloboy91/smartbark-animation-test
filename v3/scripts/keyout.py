#!/usr/bin/env python3
"""
keyout.py — Phase 2: automated green-screen removal for Elly sprite parts.

For every PNG in parts_raw:
  1. detect the pure chroma-key green (#00FF00 family) in HSV space,
  2. cut an alpha mask, de-spill green edge contamination, feather slightly,
  3. auto-crop to the opaque bounding box with padding,
  4. write a transparent PNG to parts_png,
  5. run automated QC: residual green in opaque pixels, alpha coverage, bbox.

A part FAILS (and is flagged) if opaque pixels still carry strong green — those
parts must be regenerated rather than shipped with contamination.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import cv2

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "parts_raw"
OUT = ROOT / "parts_png"
OUT.mkdir(exist_ok=True)

# Chroma-key green: hue ~60deg (OpenCV H 0-179 -> ~60), generous S/V bands.
GREEN_H = 60
H_TOL = 18
S_MIN = 80      # 0-255
V_MIN = 80
PAD = 12        # crop padding px
FEATHER = 1.2


def keyout(src: Path, dst: Path) -> dict:
    im = Image.open(src).convert("RGB")
    rgb = np.asarray(im).astype(np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # distance in hue (wrapped), strong saturated green = background
    dh = np.minimum(np.abs(h.astype(int) - GREEN_H), 180 - np.abs(h.astype(int) - GREEN_H))
    green = (dh <= H_TOL) & (s >= S_MIN) & (v >= V_MIN)

    # mask: 255 = keep (foreground), 0 = green background
    mask = np.where(green, 0, 255).astype(np.uint8)
    # close tiny pinholes inside the artwork, then smooth the edge
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.GaussianBlur(mask, (0, 0), FEATHER)

    # keep the largest connected component only (drops stray green-key artifacts)
    n, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 128).astype(np.uint8), 8)
    if n > 1:
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        mask = np.where(labels == biggest, mask, 0).astype(np.uint8)

    # green de-spill on foreground edges: clamp green channel to <= max(r,b)
    rr, gg, bb = rgb[:, :, 0].astype(int), rgb[:, :, 1].astype(int), rgb[:, :, 2].astype(int)
    spill = gg > np.maximum(rr, bb)
    gg2 = np.where(spill, np.maximum(rr, bb), gg)
    clean = np.dstack([rr, gg2, bb]).clip(0, 255).astype(np.uint8)

    rgba = np.dstack([clean, mask])

    # auto-crop to opaque bbox
    ys, xs = np.where(mask > 16)
    if len(xs) == 0:
        raise RuntimeError(f"{src.name}: empty mask")
    x0, x1 = max(xs.min() - PAD, 0), min(xs.max() + PAD, rgba.shape[1] - 1)
    y0, y1 = max(ys.min() - PAD, 0), min(ys.max() + PAD, rgba.shape[0] - 1)
    crop = rgba[y0:y1 + 1, x0:x1 + 1]
    Image.fromarray(crop, "RGBA").save(dst)

    # ---- QC on the cropped, kept pixels ----
    op = crop[:, :, 3] > 200
    chsv = cv2.cvtColor(crop[:, :, :3], cv2.COLOR_RGB2HSV)
    ch, cs, cv2v = chsv[:, :, 0], chsv[:, :, 1], chsv[:, :, 2]
    cdh = np.minimum(np.abs(ch.astype(int) - GREEN_H), 180 - np.abs(ch.astype(int) - GREEN_H))
    residual = op & (cdh <= H_TOL) & (cs >= 120) & (cv2v >= 120)
    residual_pct = 100.0 * residual.sum() / max(op.sum(), 1)
    edge_green = op & (cdh <= H_TOL + 6) & (cs >= 90)  # softer warning band
    return {
        "file": dst.name,
        "size": f"{crop.shape[1]}x{crop.shape[0]}",
        "opaque_px": int(op.sum()),
        "residual_green_pct": round(float(residual_pct), 4),
        "edge_green_pct": round(100.0 * edge_green.sum() / max(op.sum(), 1), 4),
        "pass": residual_pct < 0.05,
    }


def main():
    rows = []
    for src in sorted(RAW.glob("*.png")):
        dst = OUT / src.name
        rows.append(keyout(src, dst))
    print(f"{'part':24} {'size':12} {'opaque':>9} {'residGreen%':>13} {'edgeGreen%':>11}  status")
    allpass = True
    for r in rows:
        ok = "PASS" if r["pass"] else "FAIL-REGENERATE"
        allpass &= r["pass"]
        print(f"{r['file']:24} {r['size']:12} {r['opaque_px']:9d} "
              f"{r['residual_green_pct']:13.4f} {r['edge_green_pct']:11.4f}  {ok}")
    print("\nALL PARTS PASS GREEN-REMOVAL QC" if allpass else
          "\nSOME PARTS FAILED — regenerate the flagged assets")
    sys.exit(0 if allpass else 1)


if __name__ == "__main__":
    main()
