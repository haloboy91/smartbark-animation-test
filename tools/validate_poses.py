#!/usr/bin/env python3
"""Quality gate for generated Elly pose plates, run before keying.

Catches the failure modes that are expensive to spot later:
  * no green plate at all (the model painted a scene instead) -> unkeyable
  * plate is a gradient / vignette rather than flat -> key leaves a halo
  * identity drift: navy sweater, pink scarf or white fur missing
  * subject too small (generator zoomed out) or cropped by the frame edge

Crispness of the cut edge is checked after keying by key_elly.py's coverage
figure; here we only care that the plate is keyable.

Exit code 1 if any plate fails, so it can gate a batch.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image

# Signature: white fluffy bichon + navy star/moon sweater + pink scarf.
MIN_NAVY = 4.0     # % of subject pixels
MIN_WHITE = 25.0
MIN_PINK = 0.4
MIN_GREEN_BG = 25.0   # % of frame that is plate
MAX_PLATE_SD = 8.0    # plate greenness spread across the border ring
MIN_SUBJECT = 6.0     # % of frame the character covers
MAX_EDGE_TOUCH = 0.4  # % of the subject bbox allowed to sit on a frame edge


def check(path: str) -> tuple[bool, dict]:
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    h, w, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gd = g - np.maximum(r, b)

    ring = np.concatenate([gd[0], gd[-1], gd[:, 0], gd[:, -1]])
    plate = float(np.median(ring))

    green = gd > 0.55 * max(plate, 1)
    subj = ~green
    s = a[subj] if subj.any() else a[:1, :1].reshape(-1, 3)
    mn, mx = s.min(1), s.max(1)

    navy = float(((s[:, 2] > s[:, 0] + 18) & (s[:, 2] > s[:, 1] + 10)).mean() * 100)
    pink = float(((s[:, 0] > 140) & (s[:, 0] - s[:, 1] > 32) & (s[:, 2] >= s[:, 1])).mean() * 100)
    white = float((mn > 185).mean() * 100)

    ys, xs = np.where(subj)
    edge = 0.0
    if len(ys):
        on_edge = ((xs < 3) | (xs > w - 4) | (ys < 3) | (ys > h - 4)).mean()
        edge = float(on_edge * 100)

    m = {
        "plate": plate,
        "plate_sd": float(ring.std()),
        "green_bg": float(green.mean() * 100),
        "subject": float(subj.mean() * 100),
        "navy": navy, "pink": pink, "white": white,
        "edge_touch": edge,
        "bbox": (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(ys) else None,
    }
    m["fails"] = []
    if m["green_bg"] < MIN_GREEN_BG:
        m["fails"].append(f"no usable green plate ({m['green_bg']:.0f}% < {MIN_GREEN_BG}%)")
    if m["plate_sd"] > MAX_PLATE_SD:
        m["fails"].append(f"plate not flat (sd {m['plate_sd']:.1f} > {MAX_PLATE_SD})")
    if navy < MIN_NAVY:
        m["fails"].append(f"navy sweater missing ({navy:.1f}% < {MIN_NAVY}%)")
    if white < MIN_WHITE:
        m["fails"].append(f"white fur missing ({white:.1f}% < {MIN_WHITE}%)")
    if pink < MIN_PINK:
        m["fails"].append(f"pink scarf missing ({pink:.1f}% < {MIN_PINK}%)")
    if m["subject"] < MIN_SUBJECT:
        m["fails"].append(f"subject too small ({m['subject']:.1f}% < {MIN_SUBJECT}%)")
    if edge > MAX_EDGE_TOUCH:
        m["fails"].append(f"subject cropped by frame edge ({edge:.1f}%)")
    return not m["fails"], m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="assets/elly/greenscreen")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any plate fails")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src, "*.png")))
    if not files:
        raise SystemExit(f"no plates in {args.src}")

    print(f"{'plate':30s} {'grnbg':>6s} {'sd':>5s} {'subj':>5s} {'navy':>5s} {'pink':>5s} {'white':>5s}  status")
    bad = []
    for f in files:
        ok, m = check(f)
        name = os.path.basename(f)[:30]
        print(f"{name:30s} {m['green_bg']:5.0f}% {m['plate_sd']:5.1f} {m['subject']:4.0f}% "
              f"{m['navy']:4.1f}% {m['pink']:4.1f}% {m['white']:4.1f}%  "
              f"{'ok' if ok else 'FAIL'}")
        if not ok:
            bad.append((os.path.basename(f), m["fails"]))

    if bad:
        print("\nfailures:")
        for n, fails in bad:
            for x in fails:
                print(f"  {n}: {x}")
    print(f"\n{len(files) - len(bad)}/{len(files)} plates pass")
    if bad and args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
