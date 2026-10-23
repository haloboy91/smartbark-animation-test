#!/usr/bin/env python3
"""
build_rig_front.py — generate rig_front.json from WORLD-space joint targets.

W[name] gives the desired WORLD pivot position and WORLD sprite scale for the
regenerated V3-correction parts. The builder derives local rest offsets and
chain-relative local scales so the engine's scale-inheriting FK reproduces
exactly these neutral-pose targets. Edit targets here, re-run, then re-render
calibration to tune visually.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# name: (image, pivot_fraction, parent, world_xy, WORLD_scale, z, mirror, visible)
W = {
    "root_hip":  (None,              (0.5, 0.5),  None,       (470, 400), 1.000, 0, False, True),
    "torso":     ("torso.png",       (0.5, 0.16), "root_hip", (470, 300), 0.166, 4, False, True),
    # tail peeks out behind the LEFT edge of the body (z below legs/torso)
    "tail":      ("tail.png",        (0.18, 0.82),"root_hip", (382, 386), 0.072, 1, False, True),

    # true front-facing head; nose centered at sprite frac ~(0.49,0.59).
    # lowered so the neck ruff overlaps the sweater collar (no neck gap).
    "head":      ("head_base.png",   (0.5, 0.92), "torso",    (470, 285), 0.159, 8, False, True),
    # long floppy ears hang from the top-sides of the head
    "ear_l":     ("ear.png",         (0.5, 0.10), "head",     (404, 172), 0.110, 7, False, True),
    "ear_r":     ("ear.png",         (0.5, 0.10), "head",     (536, 172), 0.110, 9, True,  True),
    # face parts arranged symmetrically around the centered nose (~world 469,229)
    "eye_l":     ("eye_open.png",    (0.5, 0.5),  "head",     (442, 202), 0.098, 10, False, True),
    "eye_r":     ("eye_open.png",    (0.5, 0.5),  "head",     (498, 202), 0.098, 10, False, True),
    "lid_l":     ("eyelid.png",      (0.5, 0.62), "head",     (442, 194), 0.080, 11, False, False),
    "lid_r":     ("eyelid.png",      (0.5, 0.62), "head",     (498, 194), 0.080, 11, True,  False),
    "brow_l":    ("eyebrow.png",     (0.5, 0.5),  "head",     (442, 172), 0.042, 11, False, True),
    "brow_r":    ("eyebrow.png",     (0.5, 0.5),  "head",     (498, 172), 0.042, 11, True,  True),
    "mouth":     ("mouth_smile.png", (0.5, 0.5),  "head",     (470, 256), 0.102, 10, False, True),

    # arms tuck under the torso's shoulder silhouette; forearm overlaps sleeve
    "arm_up_l":  ("arm_upper.png",      (0.5, 0.10), "torso",    (414, 298), 0.108, 3, False, True),
    "arm_lo_l":  ("arm_lower_paw.png",  (0.5, 0.08), "arm_up_l", (411, 350), 0.096, 3, False, True),
    "arm_up_r":  ("arm_upper.png",      (0.5, 0.10), "torso",    (526, 298), 0.108, 6, True,  True),
    "arm_lo_r":  ("arm_lower_paw.png",  (0.5, 0.08), "arm_up_r", (529, 350), 0.096, 6, True,  True),

    # short stubby legs: wider fur columns, smaller feet so proportions match
    "leg_up_l":  ("leg_upper.png",   (0.5, 0.10), "root_hip", (447, 402), 0.066, 3, False, True),
    "leg_lo_l":  ("leg_lower.png",   (0.5, 0.10), "leg_up_l", (445, 435), 0.060, 3, False, True),
    "foot_l":    ("foot_paw.png",    (0.5, 0.22), "leg_lo_l", (443, 458), 0.080, 3, False, True),
    "leg_up_r":  ("leg_upper.png",   (0.5, 0.10), "root_hip", (493, 402), 0.066, 6, True,  True),
    "leg_lo_r":  ("leg_lower.png",   (0.5, 0.10), "leg_up_r", (495, 435), 0.060, 6, True,  True),
    "foot_r":    ("foot_paw.png",    (0.5, 0.22), "leg_lo_r", (497, 458), 0.080, 6, True,  True),
}

# authored rest angles (radians): relax the mirrored brows into gentle arcs
REST_ANGLE = {"brow_l": 0.12, "brow_r": -0.12}

# Per-shape mouth anchors: [dx, dy, scale_mult] relative to the mouth node's
# smile baseline, so differently-shaped sprites all center under the nose.
MOUTH_ANCHORS = {
    "mouth_smile.png":     [0,   0, 1.00],
    "mouth_talk.png":      [0,   6, 0.62],
    "mouth_happy.png":     [0,   8, 0.60],
    "mouth_surprised.png": [0,   4, 0.85],
    "mouth_angry.png":     [0,  -2, 0.80],
}

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
    if name in REST_ANGLE:
        node["angle"] = REST_ANGLE[name]
    nodes.append(node)

spec = {"name": "elly-front-v2", "view": "front-three-quarter",
        "world_targets": {k: list(v[3]) for k, v in W.items()},
        "mouth_anchors": MOUTH_ANCHORS, "nodes": nodes}
(ROOT / "rig" / "rig_front.json").write_text(json.dumps(spec, indent=2))
print("wrote rig/rig_front.json with", len(nodes), "nodes")
