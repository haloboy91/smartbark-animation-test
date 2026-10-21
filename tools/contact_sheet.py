#!/usr/bin/env python3
"""Build a labelled contact sheet for one part's background plates.

The proof sheet in web/js/proofsheet.js renders through the compositor, so it
needs a browser. This is the flat alternative: it grids the raw plates straight
off disk so the art can be reviewed without running anything.

    python tools/contact_sheet.py 1            # Chapter 1 -> docs/sheets/part1.png
    python tools/contact_sheet.py 0 --cols 4
"""
import argparse
import pathlib
import re
import sys

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCENES = ROOT / "assets" / "scenes"
OUTDIR = ROOT / "docs" / "sheets"

# Part 0 predates the pN_sNN convention; its plates are named sNN_<slug>.
CAPTIONS = {}


def load_captions():
    """Pull the shot captions out of the storyboard brief, keyed by (part, id)."""
    brief = ROOT / "docs" / "EP015_storyboard_brief.txt"
    if not brief.exists():
        return
    part = -1
    for line in brief.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^CHAPTER (\d+):", line)
        if m:
            part = int(m.group(1))
            continue
        m = re.match(r"^\[S(\d+)\]", line)
        if m and part >= 0:
            CAPTIONS[(part, int(m.group(1)))] = ""
            cur = (part, int(m.group(1)))
            continue
        m = re.match(r'^CAPTION / EDIT LABEL:\s*"?(.+?)"?\s*$', line.strip())
        if m and part >= 0 and CAPTIONS:
            key = max(CAPTIONS)
            if key[0] == part:
                CAPTIONS[key] = m.group(1).strip()
        _ = cur if False else None


def plates_for(part):
    """Return [(shot_id, path)] for a part, preferring jpg (the shipped format)."""
    found = {}
    for p in sorted(SCENES.iterdir()):
        if p.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        m = re.match(r"^p(\d+)_s(\d+)\.", p.name)
        if m and int(m.group(1)) == part:
            sid = int(m.group(2))
            # jpg wins: it is what the compositor actually loads.
            if sid not in found or p.suffix.lower() in {".jpg", ".jpeg"}:
                found[sid] = p
        elif part == 0 and not m:
            m0 = re.match(r"^s(\d+)_", p.name)
            if m0:
                sid = int(m0.group(1))
                if sid not in found or p.suffix.lower() in {".jpg", ".jpeg"}:
                    found[sid] = p
    return sorted(found.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", type=int)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--cell", type=int, default=320, help="cell width in px")
    args = ap.parse_args()

    load_captions()
    items = plates_for(args.part)
    if not items:
        sys.exit(f"no plates found for part {args.part}")

    cw = args.cell
    ch = int(cw * 9 / 16)
    label = 26
    pad = 14
    cols = args.cols
    rows = (len(items) + cols - 1) // cols

    sheet = Image.new(
        "RGB",
        (cols * (cw + pad) + pad, rows * (ch + label + pad) + pad),
        (22, 22, 26),
    )
    d = ImageDraw.Draw(sheet)

    for i, (sid, path) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = pad + r * (ch + label + pad)
        im = Image.open(path).convert("RGB").resize((cw, ch), Image.LANCZOS)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + cw, y + ch], outline=(70, 70, 78), width=1)
        cap = CAPTIONS.get((args.part, sid), "")
        text = f"S{sid:02d}" + (f"  {cap}" if cap else "")
        if len(text) > 34:
            text = text[:33] + "\u2026"
        d.text((x + 4, y + ch + 6), text, fill=(214, 214, 222))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / f"part{args.part}.png"
    sheet.save(out, optimize=True)
    kb = out.stat().st_size / 1024
    print(f"{len(items)} plates -> {out.relative_to(ROOT)}  ({sheet.width}x{sheet.height}, {kb:.0f} KB)")


if __name__ == "__main__":
    main()
