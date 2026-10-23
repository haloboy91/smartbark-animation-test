#!/usr/bin/env python3
"""
render_clips.py — Phase C: render the four required 5s clips through the QA
gates, then export MP4 (H.264) and GIF, with a simple parallax environment and
a root-following contact shadow for the root-motion walk.

  walk_5s   root-motion walk (planted feet truly pinned, world scrolls past)
  talk_5s   sitting + talking
  sit_5s    sitting idle
  point_5s  pointing raise / hold / lower
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw

from sprite_engine import SpriteRig, smooth
from anim_presets import (Anim, PRESETS, p_walk_root, WALK_CYCLES,
                          WALK_HIP_X0, WALK_STEP, STANCE)

ROOT = Path(__file__).resolve().parents[1]
FPS, SECONDS, FRAMES = 24, 5, 120
W, H = 960, 540
SKY = (247, 242, 234)
GROUND = (226, 219, 206)
GROUND_Y = 478

JOINT_PAIRS = [
    ("root_hip", "torso"), ("torso", "head"), ("head", "eye_l"),
    ("head", "mouth"), ("torso", "arm_up_l"), ("arm_up_l", "arm_lo_l"),
    ("torso", "arm_up_r"), ("arm_up_r", "arm_lo_r"),
    ("root_hip", "leg_up_l"), ("leg_up_l", "leg_lo_l"), ("leg_lo_l", "foot_l"),
    ("root_hip", "leg_up_r"), ("leg_up_r", "leg_lo_r"), ("leg_lo_r", "foot_r"),
]


# ------------------------------------------------------------- clip scripts --
def clip_walk(a, i, n):
    return p_walk_root(a, i, n)


def clip_talk(a, i, n):
    p = PRESETS["talking"](a, i, n)
    if i < 12:                                   # ease into the seat
        k = smooth(i / 12)
        rest = a.base()
        for name in p:
            for key in ("x", "y"):
                p[name][key] = rest[name][key] * (1 - k) + p[name][key] * k
    return p


def clip_sit(a, i, n):
    return PRESETS["sitting"](a, i, n)


def clip_point(a, i, n):
    half = n
    rise = smooth(i / (half * 0.5))
    fall = 1.0 - 0.92 * smooth((i - half * 0.62) / (half * 0.38))
    u = max(0.0, min(1.0, rise * fall))
    return PRESETS["pointing"](a, i, n, u_env=u)


CLIPS = {
    "walk_5s": (clip_walk, "locomotion"),
    "talk_5s": (clip_talk, "static"),
    "sit_5s": (clip_sit, "static"),
    "point_5s": (clip_point, "static"),
}


# --------------------------------------------------------------- environment --
def background(travel, root_x, ground_y):
    """Parallax backdrop: warm sky, ground band, two scrolling soft layers and
    a contact shadow under the character. Environment shapes only."""
    bg = Image.new("RGB", (W, H), SKY)
    d = ImageDraw.Draw(bg)
    d.rectangle((0, GROUND_Y, W, H), fill=GROUND)
    # far layer: slow rounded clouds
    for k in range(6):
        base = (k * 220 - travel * 0.25) % (W + 240) - 120
        cy = 90 + (k % 3) * 34
        d.ellipse((base, cy, base + 120, cy + 34), fill=(255, 255, 255))
    # near layer: bushes anchored to the ground, faster scroll
    for k in range(7):
        base = (k * 180 - travel * 0.6) % (W + 200) - 100
        d.ellipse((base, GROUND_Y - 46, base + 130, GROUND_Y + 18), fill=(205, 214, 190))
    # contact shadow tracks the root
    d.ellipse((root_x - 70, ground_y + 8, root_x + 70, ground_y + 26),
              fill=(120, 112, 100))
    return bg


def composite(rig, pose, mode, travel):
    char = rig.render(pose, size=(W, H), bg=(0, 0, 0, 0))
    hip = rig.world_transforms(pose)["root_hip"]
    gy = rig.world_transforms(pose)["foot_l"][1] + 24
    bg = background(travel if mode == "locomotion" else 0.0, hip[0], gy)
    bg = bg.convert("RGBA")
    bg.alpha_composite(char)
    return bg.convert("RGB")


def planted_windows():
    """Root-walk stance windows from the same phase used by p_walk_root."""
    out = {"foot_l": [], "foot_r": []}
    for foot, off in (("foot_l", 0.0), ("foot_r", 0.5)):
        start = None
        for i in range(FRAMES):
            s = WALK_CYCLES * i / (FRAMES - 1)
            planted = (s + off) % 1.0 < STANCE
            if planted and start is None:
                start = i
            if not planted and start is not None:
                out[foot].append((start, i - 1)); start = None
        if start is not None:
            out[foot].append((start, FRAMES - 1))
    return out


def contact_sheet(frames, path, label):
    cols, rows = 6, 2
    tw, th = W // 3, H // 3
    sheet = Image.new("RGB", (cols * tw, rows * th + 24), (30, 30, 34))
    d = ImageDraw.Draw(sheet)
    d.text((8, 4), label, fill=(255, 220, 120))
    for idx, fr in enumerate(frames):
        x, y = (idx % cols) * tw, 24 + (idx // cols) * th
        sheet.paste(Image.fromarray(fr).resize((tw, th)), (x, y))
    sheet.save(path)


def main():
    spec = json.loads((ROOT / "rig" / "rig_front.json").read_text())
    rig = SpriteRig(spec)
    a = Anim(rig)
    from qa_pipeline import run_all

    rest_world = rig.world_transforms(rig.rest_pose())
    neutral_h = max(v[1] for v in rest_world.values()) - min(v[1] for v in rest_world.values())
    travel_total = WALK_CYCLES * WALK_STEP

    out_dir = ROOT / "clips"
    (out_dir / "tmp").mkdir(parents=True, exist_ok=True)
    qa_summary = {}

    for name, (builder, mode) in CLIPS.items():
        poses = [builder(a, i, FRAMES) for i in range(FRAMES)]
        frames = []
        for i, p in enumerate(poses):
            travel = (WALK_HIP_X0 + WALK_CYCLES * i / (FRAMES - 1) * WALK_STEP
                      - WALK_HIP_X0) if mode == "locomotion" else 0.0
            frames.append(np.asarray(composite(rig, p, mode, travel)))

        if mode == "locomotion":
            planted = planted_windows()
            sweep = ()                                   # feet are truly pinned
            expected = neutral_h
        elif name == "talk_5s":
            planted = {"foot_l": [(12, FRAMES - 1)], "foot_r": [(12, FRAMES - 1)]}
            sweep = ("foot_l", "foot_r")
            expected = neutral_h * 0.93
        else:
            planted = {"foot_l": [(0, FRAMES - 1)], "foot_r": [(0, FRAMES - 1)]}
            sweep = ("foot_l", "foot_r")
            expected = neutral_h * (0.93 if name == "sit_5s" else 1.0)

        ok = run_all(rig, poses, planted, JOINT_PAIRS, expected, name,
                     allow_x_sweep=sweep)
        qa_summary[name] = bool(ok)
        if not ok:
            print(f"!! {name} failed QA — no export until fixed")
            contact_sheet(frames[::10], ROOT / "qc" / f"{name}-sheet.png", name + " (FAILED)")
            continue

        mp4 = out_dir / f"{name}.mp4"
        imageio.mimsave(mp4, frames, fps=FPS, codec="libx264", quality=8,
                        macro_block_size=2, output_params=["-pix_fmt", "yuv420p"])
        gif_frames = [Image.fromarray(f).resize((480, 270), Image.LANCZOS)
                      .quantize(colors=128, method=Image.FASTOCTREE) for f in frames]
        gif = out_dir / f"{name}.gif"
        durations = [50 if idx % 5 == 0 else 40 for idx in range(len(gif_frames))]
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
