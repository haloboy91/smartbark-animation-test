#!/usr/bin/env python3
"""
sprite_engine.py — Phase 3 core: sprite-based skeletal rig for Elly.

Unlike the v2 primitive rig, every node here is an AI-generated transparent PNG
part (from parts_png/). Parts are articulated with real 2D skeletal transforms:
each node has a pivot, a parent, and per-pose (x, y, angle, scale); the engine
computes world transforms by forward kinematics and composites with rotation
about the pivot, so overlapping joint artwork hides any gap.

Includes analytic two-bone IK (law of cosines) for arms/legs and foot-pin
helpers so planted feet do not slide.
"""
from __future__ import annotations
import math
import json
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "parts_png"


# ----------------------------------------------------------------- math -----
def norm(a: float) -> float:
    while a > math.pi:
        a -= 2 * math.pi
    while a <= -math.pi:
        a += 2 * math.pi
    return a


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def two_bone_ik(origin, target, l1: float, l2: float, bend: float = 1.0):
    """Return absolute angles (a1, a2) for upper/lower bones, y-down canvas."""
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    dist = math.hypot(dx, dy)
    reach = l1 + l2
    d = min(max(dist, abs(l1 - l2) + 0.001), reach - 0.001)
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    cos_a = max(-1.0, min(1.0, cos_a))
    a1 = base + bend * math.acos(cos_a)
    cos_b = (l1 * l1 + l2 * l2 - d * d) / (2 * l1 * l2)
    cos_b = max(-1.0, min(1.0, cos_b))
    # interior elbow fold (pi - beta) applied with the same bend sign so the
    # chain actually closes on the target: end == origin + l1 u1 + l2 u2
    a2 = norm(a1 + bend * (math.acos(cos_b) - math.pi))
    return norm(a1), norm(a2)


# ----------------------------------------------------------------- rig ------
@dataclass
class Node:
    name: str
    image: str | None
    pivot: tuple[float, float]          # fraction of part w/h
    parent: str | None = None
    # rest offset of THIS pivot from the parent pivot, in parent's local frame
    rest: tuple[float, float] = (0.0, 0.0)
    z: int = 0
    mirror_x: bool = False              # flip the sprite (left/right limbs)
    base_scale: float = 1.0
    rest_angle: float = 0.0
    img: Image.Image | None = field(default=None, repr=False)


class SpriteRig:
    def __init__(self, spec: dict):
        self.spec = spec
        self.nodes: dict[str, Node] = {}
        for n in spec["nodes"]:
            img = None
            if n.get("image"):
                img = Image.open(PARTS / n["image"]).convert("RGBA")
                if n.get("mirror_x"):
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
            self.nodes[n["name"]] = Node(
                name=n["name"], image=n.get("image"),
                pivot=tuple(n.get("pivot", (0.5, 0.5))), parent=n.get("parent"),
                rest=tuple(n.get("rest", (0, 0))), z=n.get("z", 0),
                mirror_x=bool(n.get("mirror_x")), base_scale=float(n.get("scale", 1.0)),
                rest_angle=float(n.get("angle", 0.0)),
                img=img,
            )
        self.order = sorted(self.nodes, key=lambda k: self.nodes[k].z)

    def part_pivot_px(self, name: str):
        n = self.nodes[name]
        if n.img is None:
            return (0, 0)
        return (n.pivot[0] * n.img.width, n.pivot[1] * n.img.height)

    def rest_pose(self):
        """Identity pose: every node at its authored rest offset, angle 0
        (or the spec's authored rest angle)."""
        return {k: {"x": n.rest[0], "y": n.rest[1], "a": n.rest_angle,
                    "s": n.base_scale, "visible": True, "image": n.image}
                for k, n in self.nodes.items()}

    def world_transforms(self, pose: dict):
        """FK: world pivot position + absolute angle for every node."""
        world = {}

        def solve(name):
            if name in world:
                return world[name]
            n = self.nodes[name]
            p = pose.get(name, {})
            local = (p.get("x", n.rest[0]), p.get("y", n.rest[1]))
            ang = p.get("a", 0.0)
            scl = p.get("s", 1.0)
            if n.parent is None:
                wx, wy, wa, ws = local[0], local[1], ang, scl
            else:
                px, py, pa, ps = solve(n.parent)
                ca, sa = math.cos(pa), math.sin(pa)
                # child local offsets inherit the parent's cumulative scale so a
                # whole subtree scales/rotates rigidly about the parent pivot
                lx, ly = local[0] * ps, local[1] * ps
                wx = px + lx * ca - ly * sa
                wy = py + lx * sa + ly * ca
                wa, ws = norm(pa + ang), ps * scl
            world[name] = (wx, wy, wa, ws)
            return world[name]

        for k in self.nodes:
            solve(k)
        return world

    def render(self, pose: dict, size=(960, 540), bg=(247, 242, 234, 255)):
        canvas = Image.new("RGBA", size, bg)
        world = self.world_transforms(pose)
        # per-pose z override lets raised arms composite in front of the head
        order = sorted(self.nodes,
                       key=lambda k: pose.get(k, {}).get("z", self.nodes[k].z))
        for name in order:
            n = self.nodes[name]
            p = pose.get(name, {})
            if p.get("visible", True) is False or n.img is None:
                continue
            # allow per-pose image swap (mouth shapes)
            img = n.img
            if p.get("image") and p["image"] != n.image:
                img = Image.open(PARTS / p["image"]).convert("RGBA")
                if n.mirror_x:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
            wx, wy, wa, ws = world[name]
            sx = p.get("scale_x", ws)
            sy = p.get("scale_y", ws)
            if abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3:
                img = img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))),
                                 Image.LANCZOS)
            pivot_px = (n.pivot[0] * img.width, n.pivot[1] * img.height)
            deg = -math.degrees(wa)  # PIL rotate is counter-clockwise
            rot = img.rotate(deg, resample=Image.BICUBIC, expand=True, center=pivot_px)
            # after expand=True rotation, pivot shifts by the bbox origin
            cos_a = math.cos(math.radians(deg))
            sin_a = math.sin(math.radians(deg))
            w0, h0 = img.size
            corners = [
                (0, 0), (w0, 0), (w0, h0), (0, h0),
            ]
            # new image bbox relative to old origin
            xs = []
            ys = []
            for cx, cy in corners:
                rx = cos_a * (cx - pivot_px[0]) - sin_a * (cy - pivot_px[1]) + pivot_px[0]
                ry = sin_a * (cx - pivot_px[0]) + cos_a * (cy - pivot_px[1]) + pivot_px[1]
                xs.append(rx)
                ys.append(ry)
            ox, oy = min(xs), min(ys)
            new_pivot_x = pivot_px[0] - ox
            new_pivot_y = pivot_px[1] - oy
            paste = (int(round(wx - new_pivot_x)), int(round(wy - new_pivot_y)))
            canvas.alpha_composite(rot, paste)
        return canvas

    def save_spec(self, path: Path):
        path.write_text(json.dumps(self.spec, indent=2))
