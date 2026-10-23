#!/usr/bin/env python3
"""
render_clips.py — Phase 5: render the three required 5s test clips through the
QA gates, then export MP4 (H.264) and GIF. Also renders per-clip contact
sheets so every clip can be visually inspected before it is accepted.

  clip 1  walking          -> walk_5s
  clip 2  sitting + talking-> sit_talk_5s
  clip 3  pointing + react -> point_react_5s
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw

from sprite_engine import SpriteRig, smooth
from anim_presets import Anim, PRESETS

ROOT = Path(__file__).resolve().parents[1]
FPS = 24
SECONDS = 5
FRAMES = FPS * SECONDS
W, H = 960, 540

JOINT_PAIRS = [
    ("root_hip", "torso"), ("torso", "head"), ("head", "eye_l"),
    ("head", "mouth"), ("torso", "arm_up_l"), ("arm_up_l", "arm_lo_l"),
    ("torso", "arm_up_r"), ("arm_up_r", "arm_lo_r"),
    ("root_hip", "leg_up_l"), ("leg_up_l", "leg_lo_l"), ("leg_lo_l", "foot_l"),
    ("root_hip", "leg_up_r"), ("leg_up_r", "leg_lo_r"), ("leg_lo_r", "foot_r"),
]


def clip_walk(a: Anim, i, n):
    return PRESETS["walking"](a, i, n)


def clip_sit_talk(a: Anim, i, n):
    # settle into the seat over the first 12 frames, then talk
    p = PRESETS["talking"](a, i, n)
    if i < 12:
        k = smooth(i / 12)
        rest = a.base()
        for name in p:
            for key in ("x", "y"):
                p[name][key] = rest[name][key] * (1 - k) + p[name][key] * k
    return p


def clip_point_react(a: Anim, i, n):
    """Point (raise -> hold -> lower toward neutral), then a clean cut into the
    surprised reaction, whose first frame is the neutral base pose, so no node
    ever teleports and no cross-pose blend can pull the rig apart."""
    half = n // 2
    if i < half:
        rise = smooth(i / (half * 0.5))
        fall = 1.0 - 0.92 * smooth((i - half * 0.62) / (half * 0.38))
        u = max(0.0, min(1.0, rise * fall))
        return PRESETS["pointing"](a, i, half, u_env=u)
    return PRESETS["surprised"](a, i - half, n - half)


CLIPS = {
    "walk_5s": (clip_walk, {"l": 0.0, "r": 0.5}),
    "sit_talk_5s": (clip_sit_talk, None),
    "point_react_5s": (clip_point_react, None),
}


def contact_sheet(frames, path, label):
    cols, rows = 6, 2
    tw, th = W // 3, H // 3
    sheet = Image.new("RGB", (cols * tw, rows * th + 24), (30, 30, 34))
    d = ImageDraw.Draw(sheet)
    d.text((8, 4), label, fill=(255, 220, 120))
    for idx, fr in enumerate(frames):
        im = Image.fromarray(fr).resize((tw, th))
        x = (idx % cols) * tw
        y = 24 + (idx // cols) * th
        sheet.paste(im, (x, y))
    sheet.save(path)


def main():
    spec = json.loads((ROOT / "rig" / "rig_front.json").read_text())
    rig = SpriteRig(spec)
    a = Anim(rig)
    from qa_pipeline import run_all

    # neutral reference height from rest-pose pivot extents
    rest_world = rig.world_transforms(rig.rest_pose())
    ys = [v[1] for v in rest_world.values()]
    neutral_h = max(ys) - min(ys)

    out_dir = ROOT / "clips"
    (out_dir / "tmp").mkdir(parents=True, exist_ok=True)
    qa_summary = {}

    for name, (builder, gait_offsets) in CLIPS.items():
        poses = [builder(a, i, FRAMES) for i in range(FRAMES)]
        frames = [np.asarray(rig.render(p, size=(W, H)).convert("RGB")) for p in poses]

        if gait_offsets:  # stance windows derived from the same gait parametric
            planted = {}
            for side, off in gait_offsets.items():
                foot = f"foot_{side}"
                planted[foot] = a.planted_ranges(FRAMES, off, cycles=4)
            expected = neutral_h
        elif name == "sit_talk_5s":
            planted = {"foot_l": [(12, FRAMES - 1)], "foot_r": [(12, FRAMES - 1)]}
            expected = neutral_h * 0.93
        else:
            planted = {"foot_l": [(0, FRAMES - 1)], "foot_r": [(0, FRAMES - 1)]}
            expected = neutral_h

        sweep = ("foot_l", "foot_r") if gait_offsets else ()
        ok = run_all(rig, poses, planted, JOINT_PAIRS, expected, name,
                     allow_x_sweep=sweep)
        qa_summary[name] = bool(ok)
        if not ok:
            print(f"!! {name} failed QA — no export until fixed")
            contact_sheet(frames[::10], ROOT / "qc" / f"{name}-sheet.png", name + " (FAILED)")
            continue

        mp4 = out_dir / f"{name}.mp4"
        imageio.mimsave(mp4, frames, fps=FPS, codec="libx264",
                        quality=8, macro_block_size=2,
                        output_params=["-pix_fmt", "yuv420p"])
        gif_frames = [Image.fromarray(f).resize((480, 270), Image.LANCZOS)
                      .quantize(colors=128, method=Image.FASTOCTREE) for f in frames]
        gif = out_dir / f"{name}.gif"
        # GIF durations are quantized to 10ms; mix 40/50ms frames (one 50ms
        # every fifth) so 120 frames total ~5.04s instead of a flat 4.8s.
        n_gif = len(gif_frames)
        durations = [50 if idx % 5 == 0 else 40 for idx in range(n_gif)]
        gif_frames[0].save(gif, save_all=True, append_images=gif_frames[1:],
                           duration=durations, loop=0, optimize=False, disposal=2)
        contact_sheet(frames[::10], ROOT / "qc" / f"{name}-sheet.png", name)
        print(f"exported {mp4.name} ({mp4.stat().st_size//1024} KB) and "
              f"{gif.name} ({gif.stat().st_size//1024} KB)")

    (ROOT / "qc" / "qa-summary.json").write_text(json.dumps(qa_summary, indent=2))
    print("\nQA summary:", qa_summary)
    return 0 if all(qa_summary.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
