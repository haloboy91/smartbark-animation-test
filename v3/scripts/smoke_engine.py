#!/usr/bin/env python3
"""Smoke test: assemble the available parts and exercise FK/rotation/swaps."""
from pathlib import Path
from sprite_engine import SpriteRig, smooth, lerp
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = {
    "name": "elly-smoke",
    "nodes": [
        {"name": "torso", "image": "torso.png", "pivot": (0.5, 0.20), "z": 2},
        {"name": "arm_up_r", "image": "arm_upper.png", "pivot": (0.5, 0.07),
         "parent": "torso", "rest": (175, 95), "z": 1},
        {"name": "head", "image": "head_base.png", "pivot": (0.5, 0.93),
         "parent": "torso", "rest": (0, -40), "z": 4},
        {"name": "eye_l", "image": "eye_open.png", "pivot": (0.5, 0.5),
         "parent": "head", "rest": (-105, -120), "z": 6},
        {"name": "eye_r", "image": "eye_open.png", "pivot": (0.5, 0.5),
         "parent": "head", "rest": (105, -120), "z": 6},
        {"name": "brow_l", "image": "eyebrow.png", "pivot": (0.5, 0.5),
         "parent": "head", "rest": (-105, -215), "z": 7},
        {"name": "brow_r", "image": "eyebrow.png", "pivot": (0.5, 0.5),
         "parent": "head", "rest": (105, -215), "z": 7, "mirror_x": True},
        {"name": "mouth", "image": "mouth_smile.png", "pivot": (0.5, 0.5),
         "parent": "head", "rest": (0, 90), "z": 6},
    ],
}
rig = SpriteRig(spec)
base = rig.rest_pose()
# root placement happens by giving torso an absolute world position via a wrapper:
base["torso"].update(x=480, y=330)

frames = []
for f in range(24):
    t = f / 23
    pose = {k: dict(v) for k, v in base.items()}
    pose["head"]["a"] = 0.25 * smooth(t) - 0.12            # head tilt
    pose["arm_up_r"]["a"] = lerp(0.15, -0.9, smooth(t))    # arm raise
    # swap mouth smile -> happy halfway
    pose["mouth"]["image"] = "mouth_happy.png" if t > 0.5 else "mouth_smile.png"
    pose["eye_l"]["s"] = pose["eye_r"]["s"] = 1.0
    frames.append(rig.render(pose))

strip = Image.new("RGBA", (960 * 3, 540), (247, 242, 234, 255))
for i, idx in enumerate((0, 11, 23)):
    strip.paste(frames[idx], (i * 960, 0))
strip.convert("RGB").save(ROOT / "qc" / "engine-smoke.png")
print("smoke frames rendered; pivot/swap test saved to qc/engine-smoke.png")
