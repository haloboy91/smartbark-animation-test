#!/usr/bin/env python3
"""
render.py — local preview renderer for the generated StykAnimate project.

It implements the same forward-kinematics geometry as StykAnimate:
  node 0 sits at (root_x, root_y); every segment extends from its parent node
  by length * (cos angle, sin angle). Thick round segments become stroked
  lines with round caps, circleFill segments become filled circles whose
  radius is (length + thickness) / 2, centred on the segment midpoint.

Outputs (in render/):
  dog-walk-sit-stand.gif   animated GIF preview
  dog-walk-sit-stand.mp4   H.264 video preview
  contact-sheet.png        key poses grid
"""

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "animation" / "dog-walk-sit-stand.styk"
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
        px_row = (
            int(WALL_TOP[0] + (WALL_BOTTOM[0] - WALL_TOP[0]) * t),
            int(WALL_TOP[1] + (WALL_BOTTOM[1] - WALL_TOP[1]) * t),
            int(WALL_TOP[2] + (WALL_BOTTOM[2] - WALL_TOP[2]) * t),
        )
        for x in range(w):
            px[x, y] = px_row
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, GROUND_Y, w, h], fill=FLOOR_COLOR)
    draw.line([0, GROUND_Y, w, GROUND_Y], fill=(196, 190, 180), width=2)
    return img


def figure_map(doc):
    return {f["figure_type_id"]: f for f in doc["figure_types"]}


def compute_joints(figure, obj):
    """Forward kinematics: segment id -> (x, y) world position of its end node."""
    scale = float(obj.get("scale", 1))
    angles = obj["angles"]
    joints = {0: (float(obj["root_x"]), float(obj["root_y"]))}
    segs = figure["segments"]
    remaining = list(range(len(segs)))
    for _ in range(len(segs) + 1):
        progressed = False
        still = []
        for i in remaining:
            seg = segs[i]
            parent = seg["parent_id"]
            if parent not in joints:
                still.append(i)
                continue
            x, y = joints[parent]
            length = float(seg["length"]) * scale
            a = float(angles[i])
            joints[seg["segment_id"]] = (x + length * math.cos(a), y + length * math.sin(a))
            progressed = True
        remaining = still
        if not remaining or not progressed:
            break
    return joints, scale


def draw_object(base, figure, obj):
    joints, scale = compute_joints(figure, obj)
    segs = sorted(enumerate(figure["segments"]), key=lambda pair: pair[1].get("z_order", pair[0] + 1))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, seg in segs:
        transparency = seg.get("transparency", 0)
        alpha = int(255 * (1 - transparency / 255))
        if alpha <= 2:
            continue
        start = joints.get(seg["parent_id"])
        end = joints.get(seg["segment_id"])
        if start is None or end is None:
            continue
        rgb = tuple(seg["color_rgb"][:3])
        thickness = max(0.0, float(seg["thickness"]) * abs(scale))
        kind = seg.get("segment_kind", "line")
        if kind in ("circleFill", "circle", "circleClear"):
            r = (math.dist(start, end) + thickness) / 2
            cx, cy = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            if r <= 0:
                continue
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb + (alpha,))
            if kind == "circle" and thickness > 0:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=rgb + (alpha,), width=max(1, int(thickness)))
        else:
            if thickness <= 0.5:
                continue
            w = max(1, int(round(thickness)))
            d.line([start, end], fill=rgb + (alpha,), width=w, joint="curve")
            r = w / 2
            for p in (start, end):
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=rgb + (alpha,))
    base.alpha_composite(layer)


def render_frame(doc, frame, w, h):
    img = backdrop(w, h).convert("RGBA")
    types = figure_map(doc)
    for slot in frame.get("object_draw_order", range(len(frame["objects"]))):
        obj = frame["objects"][slot]
        draw_object(img, types[obj["figure_type_id"]], obj)
    return img.convert("RGB")


def main():
    doc = json.loads(PROJECT.read_text())
    w, h = doc["canvas_width"], doc["canvas_height"]
    fps = doc["fps"]
    frames = doc["keyframes"]

    rendered = [render_frame(doc, frame, w, h) for frame in frames]
    print(f"rendered {len(rendered)} frames at {w}x{h}")

    # GIF (adaptive palette keeps file size reasonable)
    gif_frames = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in rendered]
    gif_path = OUT / "dog-walk-sit-stand.gif"
    gif_frames[0].save(
        gif_path, save_all=True, append_images=gif_frames[1:],
        duration=int(1000 / fps), loop=0, optimize=True, disposal=2,
    )
    print("wrote", gif_path)

    # MP4 via bundled ffmpeg (raw RGB piped into libx264)
    mp4_path = OUT / "dog-walk-sit-stand.mp4"
    cmd = [
        get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-movflags", "+faststart", str(mp4_path),
    ]
    proc = subprocess.run(cmd, input=b"".join(f.tobytes() for f in rendered), capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode()[-800:])
    print("wrote", mp4_path)

    # Contact sheet of story beats
    beats = [
        (0, "1. Idle"), (28, "2. Walking"), (56, "3. Walking"),
        (76, "4. Arriving"), (96, "5. Sitting down"), (118, "6. Sat at table"),
        (136, "7. Standing up"), (len(rendered) - 1, "8. Standing"),
    ]
    thumb_w, thumb_h = w // 2, h // 2
    sheet = Image.new("RGB", (thumb_w * 4, thumb_h * 2 + 44), (250, 248, 244))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    sd = ImageDraw.Draw(sheet)
    for idx, (frame_idx, label) in enumerate(beats):
        col, row = idx % 4, idx // 4
        x, y = col * thumb_w, row * (thumb_h + 22) + 22
        sheet.paste(rendered[frame_idx].resize((thumb_w, thumb_h), Image.LANCZOS), (x, y))
        sd.text((x + 10, y - 21), label, fill=(40, 40, 40), font=font)
    sheet_path = OUT / "contact-sheet.png"
    sheet.save(sheet_path)
    print("wrote", sheet_path)


if __name__ == "__main__":
    main()
