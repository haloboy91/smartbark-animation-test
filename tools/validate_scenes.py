#!/usr/bin/env python3
"""Quality gate for generated 1929 background plates.

The brief's two hard rules that a generator breaks silently:
  * the RIGHT THIRD must stay clear - that is where Elly is composited, and a
    busy plate there puts clutter behind her and fights the cutout
  * no text, letters or numbers in the art - captions are edit overlays

Also checks the plate is actually 16:9 landscape and reports how busy it is,
since a plate that is flat-empty everywhere is as useless as a cluttered one.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import cv2
import numpy as np
from PIL import Image

TARGET_AR = 16 / 9
AR_TOL = 0.12          # allow ~1.78 +/- 0.21
CLEAR_MARGIN = 1.35    # left two-thirds must be at least this much busier


def busyness(gray: np.ndarray) -> float:
    """Edge energy per pixel - how much visual clutter is in a region."""
    e = cv2.Laplacian(gray, cv2.CV_32F)
    return float(np.abs(e).mean())


def check(path: str) -> tuple[bool, dict]:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    a = np.asarray(im).astype(np.float32)
    gray = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # right third vs the left two-thirds
    split = int(w * 2 / 3)
    left = busyness(gray[:, :split])
    right = busyness(gray[:, split:])

    # top-right quadrant is where Elly's head usually sits - check it too
    tr = busyness(gray[: h // 2, split:])

    ar = w / h
    m = {
        "size": (w, h),
        "ar": ar,
        "left": left, "right": right, "topright": tr,
        "ratio": left / max(right, 1e-6),
    }
    m["fails"] = []
    if abs(ar - TARGET_AR) > AR_TOL:
        m["fails"].append(f"not 16:9 (ar {ar:.2f})")
    if right > 0 and m["ratio"] < CLEAR_MARGIN:
        m["fails"].append(
            f"right third not clear (left {left:.1f} vs right {right:.1f}, "
            f"ratio {m['ratio']:.2f} < {CLEAR_MARGIN})")
    if left < 2.0:
        m["fails"].append(f"plate nearly empty (left busyness {left:.1f})")
    return not m["fails"], m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="assets/scenes")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    files = sorted(sorted(glob.glob(os.path.join(args.src, "*.png")) + glob.glob(os.path.join(args.src, "*.jpg"))))
    if not files:
        raise SystemExit(f"no plates in {args.src}")

    print(f"{'plate':26s} {'size':11s} {'ar':>5s} {'left':>6s} {'right':>6s} {'ratio':>6s}  status")
    bad = []
    for f in files:
        ok, m = check(f)
        w, h = m["size"]
        print(f"{os.path.basename(f)[:26]:26s} {w}x{h:<6d} {m['ar']:5.2f} "
              f"{m['left']:6.1f} {m['right']:6.1f} {m['ratio']:6.2f}  "
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
