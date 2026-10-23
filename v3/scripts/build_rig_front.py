#!/usr/bin/env python3
"""
build_rig_front.py — generate rig_front.json from WORLD-space joint targets.

W[name] gives the desired WORLD pivot position and WORLD sprite scale. The
builder derives local rest offsets and chain-relative local scales so the
engine's scale-inheriting FK reproduces exactly these neutral-pose targets.
Edit targets here, re-run, then re-render calibration to tune visually.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# name: (image, pivot_fraction, parent, world_xy, WORLD_scale, z, mirror, visible)
W = {
    "root_hip":  (None,              (0.5, 0.5),  None,       (470, 360), 1.000, 0, False, True),
    "torso":     ("torso.png",       (0.5, 0.16), "root_hip", (470, 272), 0.225, 4, False, True),
    "tail":      ("tail.png",        (0.18, 0.82),"root_hip", (408, 344), 0.085, 1, False, True),

    # head is a 3/4 view with the baked nose at sprite frac ~(0.79,0.48);
    # face parts are placed relative to that nose: eyes left+above, mouth below-left.
    "head":      ("head_base.png",   (0.5, 0.92), "torso",    (476, 260), 0.186, 8, False, True),
    "ear_l":     ("ear.png",         (0.5, 0.12), "head",     (405, 192), 0.088, 9, False, True),
    "ear_r":     ("ear.png",         (0.5, 0.12), "head",     (548, 186), 0.088, 7, True,  True),
    "eye_l":     ("eye_open.png",    (0.5, 0.5),  "head",     (472, 180), 0.062, 10, False, True),
    "eye_r":     ("eye_open.png",    (0.5, 0.5),  "head",     (500, 175), 0.066, 10, False, True),
    "lid_l":     ("eyelid.png",      (0.5, 0.55), "head",     (472, 172), 0.066, 11, False, False),
    "lid_r":     ("eyelid.png",      (0.5, 0.55), "head",     (500, 167), 0.070, 11, True,  False),
    "brow_l":    ("eyebrow.png",     (0.5, 0.5),  "head",     (470, 160), 0.045, 11, False, True),
    "brow_r":    ("eyebrow.png",     (0.5, 0.5),  "head",     (500, 155), 0.048, 11, True,  True),
    "mouth":     ("mouth_smile.png", (0.5, 0.5),  "head",     (486, 220), 0.060, 10, False, True),

    # forearm pivot sits ~38px UP inside the upper sleeve so the joint artwork
    # overlaps (hides the elbow) and stays connected when the arm is raised
    "arm_up_l":  ("arm_upper.png",      (0.5, 0.08), "torso",    (398, 286), 0.082, 3, False, True),
    "arm_lo_l":  ("arm_lower_paw.png",  (0.5, 0.07), "arm_up_l", (390, 316), 0.085, 3, False, True),
    "arm_up_r":  ("arm_upper.png",      (0.5, 0.08), "torso",    (542, 286), 0.082, 6, True,  True),
    "arm_lo_r":  ("arm_lower_paw.png",  (0.5, 0.07), "arm_up_r", (550, 316), 0.085, 6, True,  True),

    "leg_up_l":  ("leg_upper.png",   (0.5, 0.10), "root_hip", (448, 372), 0.072, 3, False, True),
    "leg_lo_l":  ("leg_lower.png",   (0.5, 0.10), "leg_up_l", (444, 412), 0.072, 3, False, True),
    "foot_l":    ("foot_paw.png",    (0.5, 0.22), "leg_lo_l", (440, 434), 0.090, 3, False, True),
    "leg_up_r":  ("leg_upper.png",   (0.5, 0.10), "root_hip", (492, 372), 0.072, 6, True,  True),
    "leg_lo_r":  ("leg_lower.png",   (0.5, 0.10), "leg_up_r", (496, 412), 0.072, 6, True,  True),
    "foot_r":    ("foot_paw.png",    (0.5, 0.22), "leg_lo_r", (500, 434), 0.090, 6, True,  True),
}

# explicit world scales; local scale is relative to the parent's world scale
world_scale = {name: W[name][4] for name in W}

nodes = []
for name, (img, pivot, parent, xy, _ws, z, mirror, visible) in W.items():
    node = {"name": name, "image": img, "pivot": list(pivot), "z": z,
            "mirror_x": mirror, "visible": visible}
    if parent is None:
        node["rest"] = list(xy)
        node["scale"] = world_scale[name]
    else:
        ps = world_scale[parent]
        node["rest"] = [round((xy[0] - W[parent][3][0]) / ps, 3),
                        round((xy[1] - W[parent][3][1]) / ps, 3)]
        node["scale"] = round(world_scale[name] / ps, 5)
        node["parent"] = parent
    nodes.append(node)

spec = {"name": "elly-front", "view": "front-three-quarter",
        "world_targets": {k: list(v[3]) for k, v in W.items()}, "nodes": nodes}
(ROOT / "rig" / "rig_front.json").write_text(json.dumps(spec, indent=2))
print("wrote rig/rig_front.json with", len(nodes), "nodes")
