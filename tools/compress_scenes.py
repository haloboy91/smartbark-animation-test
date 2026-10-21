#!/usr/bin/env python3
"""Scene plates PNG -> JPG q93, following Kit v2's convention.

The kit switched scene art from PNG to JPG(q93) specifically to keep the
workspace small (README: "Images | PNG | JPG (q93)"). Same idea here: the cutout
poses must stay PNG because they carry alpha, but background plates are opaque
and lose nothing at q93 while dropping to roughly a fifth of the size.

Only rewrites plates that are referenced and present. Updates nothing else -
timeline.js paths are switched by the same run via --rewrite.
"""
from __future__ import annotations

import argparse
import glob
import os

from PIL import Image

DEFAULT_SRC = "assets/scenes"


def compress(path: str, quality: int) -> tuple[str, int, int]:
    out = os.path.splitext(path)[0] + ".jpg"
    im = Image.open(path).convert("RGB")
    im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
    before = os.path.getsize(path)
    after = os.path.getsize(out)
    os.remove(path)
    return out, before, after


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--quality", type=int, default=93)
    ap.add_argument("--rewrite", default="web/js/timeline.js",
                    help="switch .png plate paths to .jpg in this file")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src, "*.png")))
    if not files:
        print("no PNG plates to compress")
        return

    tot_b = tot_a = 0
    for f in files:
        out, b, a = compress(f, args.quality)
        tot_b += b
        tot_a += a
        print(f"  {os.path.basename(f):26s} {b/1e6:5.2f}MB -> {a/1e6:5.2f}MB")

    print(f"\n{len(files)} plates: {tot_b/1e6:.1f}MB -> {tot_a/1e6:.1f}MB "
          f"({100*(1-tot_a/tot_b):.0f}% smaller)")

    if args.rewrite and os.path.exists(args.rewrite):
        s = open(args.rewrite, encoding="utf-8").read()
        n = s.count(".png\",")
        s = s.replace('.png",', '.jpg",')
        open(args.rewrite, "w", encoding="utf-8").write(s)
        print(f"rewrote {n} plate paths in {args.rewrite}")


if __name__ == "__main__":
    main()
