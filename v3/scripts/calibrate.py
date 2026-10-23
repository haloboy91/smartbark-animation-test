#!/usr/bin/env python3
"""Render the neutral rig with joint markers for placement calibration."""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from sprite_engine import SpriteRig

ROOT = Path(__file__).resolve().parents[1]
spec_name = sys.argv[1] if len(sys.argv) > 1 else "rig_front.json"
out_name = sys.argv[2] if len(sys.argv) > 2 else "qc/calibrate-front.png"
W, H = 960, 540
HIP = (470, 372)

spec = json.loads((ROOT / "rig" / spec_name).read_text())
rig = SpriteRig(spec)
pose = rig.rest_pose()
pose["root_hip"].update(x=HIP[0], y=HIP[1])

canvas = rig.render(pose, size=(W, H))
# draw markers for every node world pivot
world = rig.world_transforms(pose)
d = ImageDraw.Draw(canvas)
for name, (x, y, a, s) in world.items():
    d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(230, 40, 40, 255))
    d.text((x + 6, y - 6), name, fill=(200, 30, 30, 255))
# ground line
d.line((0, 478, W, 478), fill=(90, 120, 200, 180), width=2)
canvas.convert("RGB").save(ROOT / out_name)
print("saved", out_name, "hip at", HIP)
