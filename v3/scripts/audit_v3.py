#!/usr/bin/env python3
"""
audit_v3.py — visual quality audit of the V3 pipeline (no asset generation).

Exports into v3/audit/:
  - action stills: walk (4 gait phases), sit, talk, point
  - parts-sprite-sheet.png: all 20 keyed parts, labelled
  - views.png: assembled Elly in front / 3-4 / side (side via side sprites)
  - reference-comparison.png: original reference vs assembled rig
  - connectivity.json: worst-frame joint coverage + palette distances
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from sprite_engine import SpriteRig
from anim_presets import Anim, PRESETS, _turn_swap
import render_clips as rc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audit"
OUT.mkdir(exist_ok=True)
FPS = 24
N = 120

spec = json.loads((ROOT / "rig" / "rig_front.json").read_text())
rig = SpriteRig(spec)
a = Anim(rig)


def save(im, name):
    im.convert("RGB").save(OUT / name)
    print("wrote", name)


# ------------------------------------------------------------- 1. stills ----
def strip(builder, frames, name, label):
    cw, ch = 440, 248
    sheet = Image.new("RGB", (len(frames) * cw, ch + 26), (28, 28, 32))
    d = ImageDraw.Draw(sheet)
    for k, i in enumerate(frames):
        p = builder(i)
        im = rig.render(p).convert("RGB").resize((cw, ch))
        sheet.paste(im, (k * cw, 26))
        d.text((k * cw + 8, 6), f"{label}  f{i} ({i / FPS:.2f}s)", fill=(255, 220, 120))
    save(sheet, name)


strip(lambda i: PRESETS["walking"](a, i, N), [8, 23, 38, 53], "still-walk-strip.png", "walking")
save(rig.render(PRESETS["sitting"](a, 70, N)), "still-sit.png")
save(rig.render(PRESETS["talking"](a, 58, N)), "still-talk.png")
save(rig.render(PRESETS["pointing"](a, 100, N, u_env=1.0)), "still-point.png")

# ----------------------------------------------------- 2. 20-part sheet ------
parts = [
    "head_base", "head_side", "torso", "torso_side", "eye_open", "eyelid",
    "eyebrow", "mouth_smile", "mouth_talk", "mouth_happy", "mouth_surprised",
    "mouth_angry", "arm_upper", "arm_lower_paw", "hand_point", "leg_upper",
    "leg_lower", "foot_paw", "tail", "ear",
]
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
    d.text((cx + 10, cy + 10), f"{k + 1:02d} {name}", fill=(255, 220, 120))
save(sheet, "parts-sprite-sheet.png")

# --------------------------------------------------------- 3. three views ----
front = rig.render(rig.rest_pose())
p34 = a.base()
p34["torso"]["a"] = 0.10
p34["head"]["a"] = 0.18
p34["tail"]["a"] = 0.15
three_quarter = rig.render(p34)

side = a.base()
_turn_swap(side, a, True, side_image_torso="torso_side.png")
side["torso"]["a"] = -0.12
side["head"]["a"] = -0.18
side["arm_up_l"]["visible"] = side["arm_lo_l"]["visible"] = False
side["leg_up_l"]["visible"] = side["leg_lo_l"]["visible"] = False
side["foot_l"]["visible"] = False
side_img = rig.render(side)

cw, ch = 440, 248
views = Image.new("RGB", (3 * cw, ch + 30), (28, 28, 32))
d = ImageDraw.Draw(views)
for k, (im, title) in enumerate((
        (front, "front assembly (head art is fixed 3/4)"),
        (three_quarter, "3/4 view (sprite rotation only)"),
        (side_img, "side view (head_side + torso_side swap)"))):
    views.paste(im.convert("RGB").resize((cw, ch)), (k * cw, 30))
    d.text((k * cw + 8, 8), title, fill=(255, 220, 120))
save(views, "views.png")

# ------------------------------------------------- 4. reference comparison ----
ref = Image.open(ROOT / "reference" / "elly-reference.jpg").convert("RGB")
panel = Image.new("RGB", (cw * 2, ch + 30), (28, 28, 32))
d = ImageDraw.Draw(panel)
panel.paste(ref.resize((cw, ch)), (0, 30))
panel.paste(front.convert("RGB").resize((cw, ch)), (cw, 30))
d.text((8, 8), "original reference", fill=(255, 220, 120))
d.text((cw + 8, 8), "V3 assembled rig", fill=(255, 220, 120))
save(panel, "reference-comparison.png")

# --------------------------------------- 5. connectivity across ALL frames ----
JOINT_PAIRS = [
    ("root_hip", "torso"), ("torso", "head"), ("head", "eye_l"), ("head", "mouth"),
    ("torso", "arm_up_l"), ("arm_up_l", "arm_lo_l"),
    ("torso", "arm_up_r"), ("arm_up_r", "arm_lo_r"),
    ("root_hip", "leg_up_l"), ("leg_up_l", "leg_lo_l"), ("leg_lo_l", "foot_l"),
    ("root_hip", "leg_up_r"), ("leg_up_r", "leg_lo_r"), ("leg_lo_r", "foot_r"),
]


def joint_coverage(pose, parent, child, radius=26):
    canvas = rig.render(pose, bg=(0, 0, 0, 0))
    arr = np.asarray(canvas)[:, :, 3]
    w = rig.world_transforms(pose)
    cx, cy = w[child][0], w[child][1]
    x0, x1 = max(0, int(cx - radius)), min(canvas.width, int(cx + radius))
    y0, y1 = max(0, int(cy - radius)), min(canvas.height, int(cy + radius))
    window = arr[y0:y1, x0:x1]
    return float((window > 40).mean()) if window.size else 0.0


clips = {
    "walk": lambda i: rc.clip_walk(a, i, N),
    "sit_talk": lambda i: rc.clip_sit_talk(a, i, N),
    "point_react": lambda i: rc.clip_point_react(a, i, N),
}
connectivity = {}
for cname, builder in clips.items():
    worst = {f"{p}->{c}": 1.0 for p, c in JOINT_PAIRS}
    worst_at = {}
    for i in range(N):
        pose = builder(i)
        for p, c in JOINT_PAIRS:
            cov = joint_coverage(pose, p, c)
            if cov < worst[f"{p}->{c}"]:
                worst[f"{p}->{c}"] = round(cov, 3)
                worst_at[f"{p}->{c}"] = i
    connectivity[cname] = {"worst_coverage": worst, "worst_at_frame": worst_at,
                           "threshold": 0.12,
                           "any_below_threshold": any(v < 0.12 for v in worst.values())}

# ------------------------------------------------------- 6. palette audit ------
manifest = json.loads((ROOT / "parts_manifest.json").read_text())
anchor = manifest["palette_anchor"]


def opaque_mean(png, mask_fn=None):
    im = np.asarray(Image.open(ROOT / "parts_png" / png).convert("RGBA")).astype(int)
    m = im[:, :, 3] > 200
    if mask_fn is not None:
        m &= mask_fn(im[:, :, :3])
    if m.sum() < 50:
        return None
    return im[:, :, :3][m].mean(axis=0).round(1).tolist()


fur = opaque_mean("head_base.png", lambda rgb: rgb.mean(axis=2) > 205)
navy = opaque_mean("torso.png", lambda rgb: (rgb[:, :, 2] > rgb[:, :, 0] + 15) & (rgb[:, :, 2] < 150))
scarf = opaque_mean("torso.png", lambda rgb: (rgb[:, :, 0] > 170) & (rgb[:, :, 1] < 150) & (rgb[:, :, 2] < 160))
yellow = opaque_mean("torso.png", lambda rgb: (rgb[:, :, 0] > 190) & (rgb[:, :, 1] > 150) & (rgb[:, :, 2] < 130))


def dist(c1, c2):
    return round(float(np.linalg.norm(np.array(c1) - np.array(c2))), 1) if c1 and c2 else None


palette = {
    "fur": {"sprite_rgb": fur, "anchor_rgb": anchor["fur"], "delta": dist(fur, anchor["fur"])},
    "sweater_navy": {"sprite_rgb": navy, "anchor_rgb": anchor["sweater_navy"], "delta": dist(navy, anchor["sweater_navy"])},
    "scarf_pink": {"sprite_rgb": scarf, "anchor_rgb": anchor["scarf_pink"], "delta": dist(scarf, anchor["scarf_pink"])},
    "star_moon_yellow": {"sprite_rgb": yellow, "anchor_rgb": anchor["star_moon_yellow"], "delta": dist(yellow, anchor["star_moon_yellow"])},
}
report = {"connectivity": connectivity, "palette": palette}
(OUT / "connectivity.json").write_text(json.dumps(report, indent=2))
print("wrote connectivity.json")
print(json.dumps(palette, indent=1))
print("any joint below threshold:", {k: v["any_below_threshold"] for k, v in connectivity.items()})
