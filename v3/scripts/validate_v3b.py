#!/usr/bin/env python3
"""
validate_v3b.py — Phase C validation artifacts for the V3 quality correction.

Builds into v3/validation/:
  - sprite-sheet-v2.png      all 20 current keyed parts (regenerated marked *)
  - views-v2.png             front / 3-4 / side assembled views
  - before-after.png         v3-checkpoint rig vs corrected rig
  - consistency.json         palette + keying + proportion measurements
The BEFORE render uses the rig spec from git tag v3-checkpoint and the backed-up
v1 parts in parts_png_v1 (monkeypatched sprite asset path).
"""
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import sprite_engine
from sprite_engine import SpriteRig
from anim_presets import Anim, PRESETS, _turn_swap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation"
OUT.mkdir(exist_ok=True)
spec = json.loads((ROOT / "rig" / "rig_front.json").read_text())
rig = SpriteRig(spec)
a = Anim(rig)
FPS, N = 24, 120
REGEN = {"head_base", "torso", "torso_side", "ear", "arm_upper",
         "arm_lower_paw", "leg_upper", "leg_lower", "eye_open"}


def save(im, name):
    im.convert("RGB").save(OUT / name)
    print("wrote", name)


# ------------------------------------------------------------ sprite sheet ---
parts = ["head_base", "head_side", "torso", "torso_side", "eye_open", "eyelid",
         "eyebrow", "mouth_smile", "mouth_talk", "mouth_happy", "mouth_surprised",
         "mouth_angry", "arm_upper", "arm_lower_paw", "hand_point", "leg_upper",
         "leg_lower", "foot_paw", "tail", "ear"]
cols, cell = 4, 300
rows = math.ceil(len(parts) / cols)
sheet = Image.new("RGB", (cols * cell, rows * cell), (96, 96, 102))
d = ImageDraw.Draw(sheet)
for k, name in enumerate(parts):
    im = Image.open(ROOT / "parts_png" / f"{name}.png").convert("RGBA")
    s = min((cell - 40) / im.width, (cell - 56) / im.height)
    im2 = im.resize((int(im.width * s), int(im.height * s)))
    cx, cy = (k % cols) * cell, (k // cols) * cell
    d.rectangle((cx + 4, cy + 4, cx + cell - 4, cy + cell - 4), outline=(40, 40, 44))
    sheet.paste(im2, (cx + (cell - im2.width) // 2, cy + 40 + (cell - 56 - im2.height) // 2), im2)
    tag = "*" if name in REGEN else " "
    d.text((cx + 10, cy + 10), f"{k+1:02d}{tag}{name}", fill=(255, 220, 120))
d.text((8, rows * cell - 18), "* regenerated V3-correction part (9); other 11 retained", fill=(230, 230, 230))
save(sheet, "sprite-sheet-v2.png")

# ------------------------------------------------------------------ views -----
front = rig.render(rig.rest_pose())
p34 = a.base(); p34["torso"]["a"] = 0.10; p34["head"]["a"] = 0.16; p34["tail"]["a"] = 0.15
three_quarter = rig.render(p34)
side = PRESETS["side_view"](a, 0, N)
side_img = rig.render(side)
cw, ch = 440, 248
views = Image.new("RGB", (3 * cw, ch + 30), (28, 28, 32))
d = ImageDraw.Draw(views)
for k, (im, title) in enumerate((
        (front, "front (new symmetrical head)"),
        (three_quarter, "3/4 view"),
        (side_img, "side profile (side sprites, far limbs hidden)"))):
    views.paste(im.convert("RGB").resize((cw, ch)), (k * cw, 30))
    d.text((k * cw + 8, 8), title, fill=(255, 220, 120))
save(views, "views-v2.png")

# ------------------------------------------------------------- before/after ---
old_spec = json.loads(subprocess.run(
    ["git", "show", "v3-checkpoint:v3/rig/rig_front.json"], cwd=ROOT.parent,
    capture_output=True, text=True, check=True).stdout)
backup = ROOT / "parts_png_v1"
orig_parts = sprite_engine.PARTS
sprite_engine.PARTS = backup
try:
    old_rig = SpriteRig(old_spec)
    before = old_rig.render(old_rig.rest_pose())
finally:
    sprite_engine.PARTS = orig_parts
after = rig.render(rig.rest_pose())
panel = Image.new("RGB", (cw * 2, ch + 30), (28, 28, 32))
d = ImageDraw.Draw(panel)
panel.paste(before.convert("RGB").resize((cw, ch)), (0, 30))
panel.paste(after.convert("RGB").resize((cw, ch)), (cw, 30))
d.text((8, 8), "BEFORE (v3-checkpoint)", fill=(255, 170, 120))
d.text((cw + 8, 8), "AFTER (corrected)", fill=(160, 230, 160))
save(panel, "before-after.png")

# ------------------------------------------------------------ consistency -----
def median_rgb(png, mask):
    im = np.asarray(Image.open(ROOT / "parts_png" / f"{png}.png").convert("RGBA")).astype(int)
    px = im[:, :, :3][(im[:, :, 3] > 200) & mask(im[:, :, :3])]
    return np.median(px, axis=0).round(1).tolist() if len(px) else None

ref = np.asarray(Image.open(ROOT / "reference" / "elly-reference.jpg").convert("RGB")).astype(int)
ref_rgb = {
    "fur": np.median(ref[ref.mean(axis=2) > 215], axis=0).round(1).tolist(),
    "navy": np.median(ref[(ref[:, :, 2] > 70) & (ref[:, :, 2] < 140) & (ref[:, :, 0] < 70)], axis=0).round(1).tolist(),
    "scarf": np.median(ref[(ref[:, :, 0] > 180) & (ref[:, :, 1] > 90) & (ref[:, :, 1] < 170)], axis=0).round(1).tolist(),
    "yellow": np.median(ref[(ref[:, :, 0] > 200) & (ref[:, :, 1] > 150) & (ref[:, :, 2] < 140)], axis=0).round(1).tolist(),
}
new_rgb = {
    "fur": median_rgb("head_base", lambda r: r.mean(axis=2) > 205),
    "navy": median_rgb("torso", lambda r: (r[:, :, 2] > r[:, :, 0] + 15) & (r[:, :, 2] < 150)),
    "scarf": median_rgb("torso", lambda r: (r[:, :, 0] > 170) & (r[:, :, 1] < 170) & (r[:, :, 2] < 170)),
    "yellow": median_rgb("torso", lambda r: (r[:, :, 0] > 190) & (r[:, :, 1] > 150) & (r[:, :, 2] < 140)),
}
palette = {k: {"reference": ref_rgb[k], "current": new_rgb[k],
               "delta": round(float(np.linalg.norm(np.array(new_rgb[k]) - np.array(ref_rgb[k]))), 1)}
           for k in ref_rgb}

# keying + proportion facts
green = {}
import cv2
for p in sorted((ROOT / "parts_png").glob("*.png")):
    im = np.asarray(Image.open(p).convert("RGBA"))
    hsv = cv2.cvtColor(im[:, :, :3], cv2.COLOR_RGB2HSV)
    opaque = im[:, :, 3] > 200
    dh = np.minimum(np.abs(hsv[:, :, 0].astype(int) - 60), 180 - np.abs(hsv[:, :, 0].astype(int) - 60))
    g = opaque & (dh <= 18) & (hsv[:, :, 1] >= 120) & (hsv[:, :, 2] >= 120)
    green[p.name] = round(100 * g.sum() / opaque.sum(), 4)
rw = rig.world_transforms(rig.rest_pose())
height = max(v[1] for v in rw.values()) - min(v[1] for v in rw.values())
report = {"palette_vs_reference": palette, "residual_green_pct": green,
          "assembled_height_px": round(height, 1), "node_count": len(rig.nodes),
          "regenerated_parts": sorted(REGEN),
          "pending_regeneration": ["head_side", "eyelid", "eyebrow"]}
(OUT / "consistency.json").write_text(json.dumps(report, indent=2))
print(json.dumps(palette, indent=1))
print("green max:", max(green.values()))
