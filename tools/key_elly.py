#!/usr/bin/env python3
"""
Key Elly pose plates into transparent RGBA cutouts.

The v2 kit ships `scripts/key_elly.py`, but that one is hard-wired to the
green-screen knight plates (chroma key on greenness + grey floor-shadow
detection). The original "Elly Behavior" Family Guy references - and any new
pose we generate for EP015 - sit on a flat *black* plate instead, so the green
keyer would treat them as fully opaque foreground.

This keyer handles both:

  --bg black   alpha from a luminance ramp + flood fill from the plate border,
               then un-premultiply to kill the dark fringe the black plate
               leaves on the fur.
  --bg green   the original chroma-key path, plus the grey floor-shadow pass.

Usage:
    python3 tools/key_elly.py --src assets/elly/references --dst assets/elly/cutouts
    python3 tools/key_elly.py --src assets/elly/greenscreen --dst assets/elly/cutouts --bg green
"""
from __future__ import annotations

import argparse
import glob
import os

import cv2
import numpy as np
from PIL import Image

# ---------------------------------------------------------------- helpers


def luma(a: np.ndarray) -> np.ndarray:
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def detect_bg(a: np.ndarray) -> str:
    """Guess the plate colour from the border ring."""
    ring = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]).astype(np.float32)
    g = ring[:, 1] - np.maximum(ring[:, 0], ring[:, 2])
    if g.mean() > 40:
        return "green"
    return "black"


def alpha_black(a: np.ndarray) -> np.ndarray:
    """Black plate -> alpha.

    Background is exactly 0,0,0 while Elly's thick outlines sit well above it,
    so a luminance ramp keeps the outlines intact (a naive lum<128 key would
    eat them and destroy the style).
    """
    l = luma(a)
    alpha = np.clip((l - LO) / float(HI - LO), 0.0, 1.0)

    # Anything the border can reach is definitely background even if JPEG
    # ringing pushed it above the ramp.
    ext = flood_exterior(l < LO_REACH)
    alpha = np.where(ext, 0.0, alpha)

    # Hair/fur gaps that the fill could not reach stay opaque.
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.1)
    return np.clip(alpha, 0.0, 1.0)


def flood_exterior(seed: np.ndarray) -> np.ndarray:
    """Flood fill `seed` from the image border (4-connected)."""
    h, w = seed.shape
    m = np.zeros((h + 2, w + 2), np.uint8)
    m[1:-1, 1:-1] = (seed > 0).astype(np.uint8) * 255
    cv2.floodFill(m, None, (0, 0), 128)
    return m[1:-1, 1:-1] == 128


def alpha_green(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Green plate -> alpha, auto-calibrated to the actual plate colour.

    The v2 kit hard-codes `greenness > 80`, which is right for its own pure
    (0,255,0) knight plates. Newly generated poses come back on a *muted* sage
    green (around RGB 90,160,105, greenness 55), and the fixed threshold then
    keys out almost nothing - the cutout comes back fully opaque. So we measure
    the plate from the border ring and normalise against it, which works for
    both the saturated knight plates and the muted generated ones.
    """
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gd = g - np.maximum(r, b)

    ring = np.concatenate([gd[0], gd[-1], gd[:, 0], gd[:, -1]])
    plate = float(np.median(ring))
    if plate < 20:  # not really a green plate; caller should have used --bg black
        raise RuntimeError("no green plate detected (median greenness "
                           f"{plate:.1f}) - try --bg black")

    s = gd / plate                       # 1.0 on the plate, near 0 on the subject
    alpha = np.clip((HI_S - s) / (HI_S - LO_S), 0, 1)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

    # Despill: pull green back toward the red/blue envelope on edge pixels.
    spill = (s > 0.15) & (alpha > 0)
    a = a.copy()
    a[..., 1] = np.where(spill, np.minimum(g, np.maximum(r, b) + 10), g)
    return alpha, a


def floor_shadow(a: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Grey floor puck under Elly -> soft translucent shadow (v2 behaviour)."""
    mx, mn = a.max(2), a.min(2)
    h = a.shape[0]
    yy = np.arange(h)[:, None] * np.ones((1, a.shape[1]))
    fg = alpha > 0.5
    if not fg.any():
        return np.zeros_like(alpha)
    ys = np.where(fg.any(1))[0]
    y0, y1 = ys[0], ys[-1]
    sh = fg & ((mx - mn) < 18) & (mx > 95) & (mx < 175) & (yy > y0 + 0.78 * (y1 - y0))
    n, lab, st, _ = cv2.connectedComponentsWithStats(sh.astype(np.uint8))
    shm = np.zeros_like(sh)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_WIDTH] > 150 and st[i, cv2.CC_STAT_HEIGHT] < 140:
            shm |= lab == i
    shm = cv2.morphologyEx(
        shm.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)
    ).astype(bool)
    return shm


def unmultiply(a: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Remove the dark fringe left by compositing against a black plate.

    Edge pixels are a blend of true colour and plate, so dividing by alpha
    recovers (an approximation of) the un-blended colour. Clamped so the very
    faint edge pixels do not blow up into noise.
    """
    safe = np.maximum(alpha, 0.35)[..., None]
    return np.clip(a / safe, 0, 255)


# ---------------------------------------------------------------- driver

LO, HI, LO_REACH = 6.0, 30.0, 14.0
# Normalised green-plate cut points: fully opaque below LO_S, fully keyed at HI_S.
LO_S, HI_S = 0.45, 0.80


def key_one(path: str, dst: str, bg: str | None = None, pad: int = 4,
            max_h: int | None = None, defringe: bool = False) -> tuple[str, tuple[int, int]]:
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    mode = bg or detect_bg(a)

    if mode == "green":
        alpha, a = alpha_green(a)
        shm = floor_shadow(a, alpha)
        a[shm] = 0
        alpha = np.where(shm, 0.30, alpha)
    else:
        alpha = alpha_black(a)
        if defringe:
            a = unmultiply(a, alpha)

    rgba = np.dstack([np.clip(a, 0, 255), alpha * 255]).astype(np.uint8)

    ys, xs = np.where(alpha > 0.05)
    if len(ys) == 0:
        raise RuntimeError(f"{path}: key produced an empty cutout")
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, rgba.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, rgba.shape[1])
    rgba = rgba[y0:y1, x0:x1]

    # Elly is 35-50% of a 1080p frame, so ~900px of cutout is already more
    # than enough resolution; keeping full 1024-1600px plates just bloats git.
    if max_h and rgba.shape[0] > max_h:
        im2 = Image.fromarray(rgba)
        w2 = max(1, round(rgba.shape[1] * max_h / rgba.shape[0]))
        rgba = np.asarray(im2.resize((w2, max_h), Image.LANCZOS))

    name = os.path.splitext(os.path.basename(path))[0] + ".png"
    out = os.path.join(dst, name)
    Image.fromarray(rgba).save(out, optimize=True, compress_level=9)
    return out, rgba.shape[:2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--bg", choices=["auto", "black", "green"], default="auto")
    ap.add_argument("--pad", type=int, default=4)
    ap.add_argument("--max-h", type=int, default=900,
                    help="cap cutout height (px); 900 covers Elly at 50%% frame height")
    ap.add_argument("--defringe", action="store_true",
                    help="un-premultiply to remove the dark rim a black plate leaves. "
                         "Off by default: amplifies JPEG noise in the feather, which "
                         "balloons PNG size for a rim the outline style hides anyway.")
    args = ap.parse_args()

    os.makedirs(args.dst, exist_ok=True)
    mode = None if args.bg == "auto" else args.bg
    files = sorted(
        f for f in glob.glob(os.path.join(args.src, "*"))
        if os.path.splitext(f)[1].lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not files:
        raise SystemExit(f"no images in {args.src}")

    print(f"{'file':40s} {'mode':6s} {'cutout':>16s}  coverage")
    for f in files:
        out, (h, w) = key_one(f, args.dst, mode, args.pad, args.max_h, args.defringe)
        a = np.asarray(Image.open(out))
        cov = (a[..., 3] > 128).mean() * 100
        print(f"{os.path.basename(f)[:40]:40s} {detect_bg(np.asarray(Image.open(f).convert('RGB')).astype(np.float32)):6s} "
              f"{w:5d}x{h:<5d} {cov:5.1f}%")
    print(f"\n{len(files)} cutouts -> {args.dst}")


if __name__ == "__main__":
    main()
