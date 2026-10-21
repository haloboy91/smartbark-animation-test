#!/usr/bin/env python3
"""Parse docs/EP015_storyboard_brief.txt -> web/js/timeline.js (all 8 parts).

Hand-writing 217 shots is unmaintainable and drifts from the brief. The
storyboard is strictly structured ([Snn] / VO CUE / VISUAL / CAMERA / ELLY
ACTIVENESS / SFX / CAPTION), so we parse it and derive:

  * the cue phrase each shot is anchored to  (-> cues.py T(v, "phrase"))
  * the camera move, from the CAMERA sentence
  * Elly's pose, by routing the ELLY ACTIVENESS beat through poses.json's tags
  * the plate, when generated art exists for that shot

Part 0's hand-authored entries (camera params, Elly placement) are preserved:
this script only emits the parts that are still auto-derived.
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEF = os.path.join(ROOT, "docs", "EP015_storyboard_brief.txt")
POSES = os.path.join(ROOT, "assets", "elly", "poses.json")
PART0 = os.path.join(ROOT, "web", "js", "timeline_part0.js")
OUT = os.path.join(ROOT, "web", "js", "timeline.js")

SHOT_RE = re.compile(r"^\[S(\d+)\]")
FIELD = {
    "cue": re.compile(r'^VO CUE \(excerpt\):\s*"?(.+?)"?\s*$'),
    "visual": re.compile(r"^VISUAL:\s*(.+)$"),
    "camera": re.compile(r"^CAMERA:\s*(.+)$"),
    "elly": re.compile(r"^ELLY ACTIVENESS:\s*(.+)$"),
    "caption": re.compile(r'^CAPTION / EDIT LABEL:\s*"?(.+?)"?\s*$'),
}
PART_RE = re.compile(r'^(?:PART 0|CHAPTER [1-7]):\s*"(.+)"')

# Elly's default placement: right third, 35-50% of frame height.
DEFAULT_X, DEFAULT_Y, DEFAULT_H = 1470, 1020, 510


def route_pose(beat: str, poses: list[dict]) -> str:
    """Same routing rules as build_pose_manifest.py, kept in sync by hand."""
    b = beat.lower()
    sensitive = ("solemn", "somber", "sober", "memorial", "no joke", "sympathet",
                 "empathet", "serious", "respectful", "grave", "human cost",
                 "tragic", "suicide", "hardship", "breadline")
    if any(k in b for k in sensitive):
        return "solemn_direct"

    def stem(w):
        w = re.sub(r"[^\w']", "", w).lower()
        return w[:-1] if len(w) > 4 and w.endswith("s") else w

    toks = {stem(w) for w in re.split(r"[\s,;:\u2192\-/]+", b) if w}
    best, score = None, 0
    for p in poses:
        s = 0
        for tag in p["tags"]:
            parts = [stem(t) for t in tag.split()]
            if len(tag) < 4 and tag not in toks:
                continue
            if tag in b:
                s += 10 + len(tag)
            elif any(t in toks for t in parts):
                s += 6 + len(tag)
        if s > score:
            best, score = p["id"], s
    return best or "think"


def camera_from(text: str) -> tuple[dict, dict | None]:
    """Map a CAMERA sentence to a rig camera move + optional impact shake."""
    t = text.lower()
    shake = None
    if "shake" in t or "impact" in t:
        shake = {"amp": 16, "from": 0.55, "to": 0.8}

    if "snap-zoom" in t or "snap zoom" in t:
        return {"type": "snapZoom", "from": 1.22, "settle": 0.34, "then": 1.08}, shake
    if "rhythmic" in t or "two push" in t:
        n = 3 if "three" in t else 2
        return {"type": "pulse", "n": n, "amount": 0.09}, shake
    if "parallax" in t:
        return {"type": "parallax", "dx": 90}, shake
    if "dolly" in t or "tracking" in t:
        if "pull-out" in t or "pull out" in t or "pull-back" in t:
            return {"type": "pullOut", "from": 1.2, "to": 1.0}, shake
        return {"type": "pan", "dx": -280}, shake
    if "pan" in t:
        d = -1 if "left" in t else (1 if "right" in t else -1)
        return {"type": "pan", "dx": 260 * d}, shake
    if "pull-out" in t or "pull out" in t or "zoom-out" in t or "zoom out" in t \
            or "pull-back" in t or "pull back" in t or "wide" in t:
        return {"type": "pullOut", "from": 1.18, "to": 1.0}, shake
    if "push-in" in t or "push in" in t or "zoom-in" in t or "zoom in" in t \
            or "punch-in" in t or "punch in" in t:
        return {"type": "pushIn", "to": 1.18}, shake
    if "crossfade" in t or "dissolve" in t or "static" in t or "hold" in t:
        return {"type": "static"}, shake
    if "cut" in t or "match-cut" in t:
        return {"type": "static"}, shake
    return {"type": "pushIn", "to": 1.12}, shake


def parse(brief_path: str) -> list[dict]:
    part_idx, shots, cur = -1, [], None
    for line in open(brief_path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = PART_RE.match(line)
        if m:
            part_idx += 1
            continue
        m = SHOT_RE.match(line)
        if m:
            if cur:
                shots.append(cur)
            cur = {"part": part_idx, "id": f"S{int(m.group(1)):02d}"}
            continue
        if cur is None:
            continue
        for key, rx in FIELD.items():
            m = rx.match(line.strip())
            if m:
                cur[key] = m.group(1).strip()
                break
    if cur:
        shots.append(cur)
    return shots


def main() -> None:
    poses = json.load(open(POSES, encoding="utf-8"))["poses"]
    shots = parse(BRIEF)
    shots = [s for s in shots if s.get("part", -1) >= 0 and s.get("cue")]

    print(f"parsed {len(shots)} shots across "
          f"{len({s['part'] for s in shots})} parts")

    # Part 0 lives in its own hand-authored file. An earlier version tried to
    # re-extract it from the generated output, which silently dropped it once
    # the generated file also contained `part:` keys.
    if not os.path.exists(PART0):
        raise SystemExit(f"missing {PART0} (Part 0 hand-authored shot list)")
    src0 = open(PART0, encoding="utf-8").read()
    m0 = re.search(r"export const SHOTS_PART0 = \[(.*?)\n\];", src0, re.S)
    if not m0:
        raise SystemExit(f"{PART0}: could not find SHOTS_PART0 array")
    hand = m0.group(1).rstrip()

    lines = [
        "// GENERATED by tools/build_timeline.py from docs/EP015_storyboard_brief.txt.",
        "// Do not edit by hand - run: python3 tools/build_timeline.py",
        "//",
        "// Shot boundaries are NOT hardcoded times. Each shot declares the `cue`",
        "// phrase it belongs to and the engine locates that phrase in the word",
        "// stream, mirroring kit v2's cues.py T(v, \"phrase\"). The storyboard's",
        "// evenly-allocated windows are explicit placeholders and are ignored.",
        "//",
        "// Part 0 is hand-authored (real camera params + Elly placement); parts 1-7",
        "// are derived from the brief and are scaffolding until their art exists.",
        "",
        "import { SHOTS_PART0 } from './timeline_part0.js';",
        "",
        "export const SHOTS = [",
        "  ...SHOTS_PART0,",
        "",
        "  // ---- parts 1-7: generated from the storyboard ----",
    ]

    n_by_part = {}
    for s in shots:
        if s["part"] == 0:
            continue  # hand-authored above
        n_by_part[s["part"]] = n_by_part.get(s["part"], 0) + 1
        cam, shake = camera_from(s.get("camera", ""))
        pose = route_pose(s.get("elly", ""), poses)
        plate = None
        stem = f"p{s['part']}_{s['id'].lower()}"
        for ext in ("jpg", "png"):
            p = f"assets/scenes/{stem}.{ext}"
            if os.path.exists(os.path.join(ROOT, p)):
                plate = p
                break
        lines.append("  {")
        lines.append(f"    part: {s['part']}, id: \"{s['id']}\",")
        lines.append(f"    cue: {json.dumps(clean_cue(s['cue']))},")
        if plate:
            lines.append(f"    plate: {json.dumps(plate)},")
        lines.append(f"    scene: {json.dumps(scene_key(s.get('visual', '')))},")
        lines.append(f"    camera: {json.dumps(cam)},")
        if shake:
            lines.append(f"    shake: {json.dumps(shake)},")
        lines.append(f"    elly: [{{ t: 0, pose: {json.dumps(pose)}, "
                     f"x: {DEFAULT_X}, y: {DEFAULT_Y}, h: {DEFAULT_H} }}],")
        if s.get("caption"):
            lines.append(f"    caption: {json.dumps(s['caption'])},")
        lines.append(f"    beat: {json.dumps(s.get('elly', ''))},")
        lines.append("  },")
    lines.append("];")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("auto-derived shots per part:",
          dict(sorted(n_by_part.items())))
    print(f"-> {os.path.relpath(OUT, ROOT)}")


def clean_cue(cue: str) -> str:
    """Trim a cue to a contiguous run of script words we can actually locate.

    Storyboard cues are excerpts, so they routinely elide across sentences
    ("But when everything goes wrong? Suddenly... yesterday."). Only the first
    contiguous run can be matched against the script, so we keep that and drop
    the elision. Curly apostrophes are folded to ASCII so they compare equal to
    the script's straight ones.
    """
    c = cue.strip().strip('"').strip()
    c = c.replace("\u2019", "'").replace("\u2018", "'")
    c = c.replace("\u201c", '"').replace("\u201d", '"')
    # A cue can also START with an elision ("...and even increase them"), which
    # would leave an empty first chunk - take the first non-empty one instead.
    chunks = [x for x in re.split(r"\s*\.\.\.?\s*", c) if x.strip(" ,;:")]
    if not chunks:
        return ""
    # Prefer the longest chunk: it is the most specific thing we can locate.
    c = max(chunks, key=lambda x: len(x.split()))
    return re.sub(r"\s+", " ", c).strip(" ,;:")


SCENE_HINTS = [
    ("farm", "farm"), ("breadline", "breadline"), ("bank", "bank"),
    ("factory", "factory"), ("studio", "studio"), ("office", "office"),
    ("street", "street"), ("chart", "chart"), ("ticker", "ticker"),
    ("desk", "desk"), ("skyline", "skyline"), ("home", "home"),
]


def scene_key(visual: str) -> str:
    v = (visual or "").lower()
    for needle, key in SCENE_HINTS:
        if needle in v:
            return key
    return "generic"


if __name__ == "__main__":
    main()
