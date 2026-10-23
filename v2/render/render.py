#!/usr/bin/env python3
"""
render.py (v2) — preview renderer matching StykAnimate's geometry.

Supports the full primitive set used by the v2 rigs:
  line        round-capped stroke, width = thickness
  circleFill  filled disc, radius = (length + thickness) / 2 at the midpoint
  circleClear stroke-only ring of that radius, line width = thickness
Per-frame length overrides (obj.lengths / len_flag) and segment transparency
are honoured, and the FK walk is the same math as src/pivot/geometry.mjs.
"""

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "animation" / "elly-v2-walk-turn-sit.styk"
OUT = ROOT / "render"
OUT.mkdir(exist_ok=True)

WALL_TOP = (246, 241, 232)
WALL_BOTTOM = (231, 223, 210)
FLOOR_COLOR = (222, 216, 205)
GROUND_Y = 432


def backdrop(w, h):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(GROUND_Y):
        t = y / GROUND_Y
        row = tuple(int(WALL_TOP[i] + (WALL_BOTTOM[i] - WALL_TOP[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = row
    d = ImageDraw.Draw(img)
    d.rectangle([0, GROUND_Y, w, h], fill=FLOOR_COLOR)
    d.line([0, GROUND_Y, w, GROUND_Y], fill=(196, 190, 180), width=2)
    return img


def compute_joints(figure, obj):
    scale = float(obj.get("scale", 1))
    angles = obj["angles"]
    use_lengths = bool(obj.get("len_flag")) and len(obj.get("lengths", [])) == len(figure["segments"])
    segs = figure["segments"]
    joints = {0: (float(obj["root_x"]), float(obj["root_y"]))}
    remaining = list(range(len(segs)))
    for _ in range(len(segs) + 1):
        nxt = []
        for i in remaining:
            seg = segs[i]
            parent = seg["parent_id"]
            if parent not in joints:
                nxt.append(i)
                continue
            x, y = joints[parent]
            length = float(obj["lengths"][i] if use_lengths else seg["length"]) * scale
            a = float(angles[i])
            joints[seg["segment_id"]] = (x + length * math.cos(a), y + length * math.sin(a))
        remaining = nxt
        if not remaining:
            break
    return joints, scale, use_lengths


def draw_object(base, figure, obj):
    joints, scale, use_lengths = compute_joints(figure, obj)
    segs = sorted(enumerate(figure["segments"]),
                  key=lambda pair: pair[1].get("z_order", pair[0] + 1))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, seg in segs:
        alpha = int(255 * (1 - seg.get("transparency", 0) / 255))
        if alpha <= 2:
            continue
        start = joints.get(seg["parent_id"])
        end = joints.get(seg["segment_id"])
        if start is None or end is None:
            continue
        rgb = tuple(seg["color_rgb"][:3])
        thickness = max(0.0, float(seg["thickness"]) * abs(scale))
        kind = seg.get("segment_kind", "line")
        dist = math.dist(start, end)
        if kind in ("circleFill", "circle", "circleClear"):
            radius = (dist + thickness) / 2
            if radius <= 0:
                continue
            cx, cy = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            box = [cx - radius, cy - radius, cx + radius, cy + radius]
            if kind == "circleClear":
                width = max(1, int(round(thickness)))
                d.ellipse(box, outline=rgb + (alpha,), width=width)
            else:
                d.ellipse(box, fill=rgb + (alpha,))
                if kind == "circle" and thickness > 0:
                    d.ellipse(box, outline=rgb + (alpha,), width=max(1, int(thickness)))
        else:
            if thickness <= 0.5:
                continue
            width = max(1, int(round(thickness)))
            d.line([start, end], fill=rgb + (alpha,), width=width, joint="curve")
            r = width / 2
            for p in (start, end):
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=rgb + (alpha,))
    base.alpha_composite(layer)


def render_frame(doc, frame, w, h):
    img = backdrop(w, h).convert("RGBA")
    types = {f["figure_type_id"]: f for f in doc["figure_types"]}
    for slot in frame.get("object_draw_order", range(len(frame["objects"]))):
        obj = frame["objects"][slot]
        draw_object(img, types[obj["figure_type_id"]], obj)
    return img.convert("RGB")


def main():
    doc = json.loads(PROJECT.read_text())
    w, h, fps, frames = doc["canvas_width"], doc["canvas_height"], doc["fps"], doc["keyframes"]
    rendered = [render_frame(doc, frame, w, h) for frame in frames]
    print(f"rendered {len(rendered)} frames at {w}x{h}")

    gif_frames = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in rendered]
    gif_path = OUT / "elly-v2-walk-turn-sit.gif"
    gif_frames[0].save(gif_path, save_all=True, append_images=gif_frames[1:],
                       duration=int(1000 / fps), loop=0, optimize=True, disposal=2)
    print("wrote", gif_path)

    mp4_path = OUT / "elly-v2-walk-turn-sit.mp4"
    cmd = [get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-crf", "20", "-movflags", "+faststart", str(mp4_path)]
    proc = subprocess.run(cmd, input=b"".join(f.tobytes() for f in rendered), capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode()[-800:])
    print("wrote", mp4_path)

    beats = [
        (2, "1. Idle"), (24, "2. Walking"), (48, "3. Mid walk"), (74, "4. Stop"),
        (88, "5. Turning"), (100, "6. Turn / back up"), (118, "7. Sitting down"),
        (140, "8. Settled"), (160, "9. Resting"), (167, "10. Final pose"),
    ]
    tw, th = w // 2, h // 2
    sheet = Image.new("RGB", (tw * 5, th * 2 + 48), (250, 248, 244))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    sd = ImageDraw.Draw(sheet)
    for idx, (fi, label) in enumerate(beats):
        col, row = idx % 5, idx // 5
        x, y = col * tw, row * (th + 24) + 24
        sheet.paste(rendered[fi].resize((tw, th), Image.LANCZOS), (x, y))
        sd.text((x + 10, y - 21), label, fill=(40, 40, 40), font=font)
    sheet_path = OUT / "contact-sheet.png"
    sheet.save(sheet_path)
    print("wrote", sheet_path)


if __name__ == "__main__":
    main()
