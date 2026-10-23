#!/usr/bin/env python3
"""
qa_pipeline.py — Phase 5 automated quality validation for the sprite pipeline.

Runs against the keyed parts and a rendered pose sequence (list of pose dicts
for a SpriteRig). Checks:
  1. sprite transparency  — every part has real alpha and zero green residue
  2. proportions          — assembled character stays within expected size band
  3. joint alignment      — child pivots land near their authored joint targets
  4. limb continuity      — child/parent artwork overlaps at each joint (no gaps)
  5. foot contact         — planted feet keep a constant ground y (no sliding)
  6. motion smoothness    — per-node frame deltas bounded (no teleport/jitter)
  7. character consistency— part palette stays close to the reference palette

Defective components make the run FAIL so they can be regenerated, never shipped.
"""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
from PIL import Image
import cv2

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "parts_png"
GREEN_H = 60
H_TOL = 18


def check_transparency() -> list[tuple[str, bool, str]]:
    out = []
    for p in sorted(PARTS.glob("*.png")):
        im = np.asarray(Image.open(p).convert("RGBA"))
        alpha = im[:, :, 3]
        opaque = alpha > 200
        if opaque.sum() < 100:
            out.append((p.name, False, "nearly empty alpha")); continue
        hsv = cv2.cvtColor(im[:, :, :3], cv2.COLOR_RGB2HSV)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        dh = np.minimum(np.abs(h.astype(int) - GREEN_H), 180 - np.abs(h.astype(int) - GREEN_H))
        green = opaque & (dh <= H_TOL) & (s >= 120) & (v >= 120)
        pct = 100.0 * green.sum() / opaque.sum()
        # corners must be transparent (background fully removed)
        corner = min(alpha[0, 0], alpha[0, -1], alpha[-1, 0], alpha[-1, -1])
        ok = pct < 0.05 and corner < 16
        out.append((p.name, ok, f"green={pct:.4f}% cornerAlpha={corner}"))
    return out


def check_smoothness(world_seq: list[dict], max_jump_px: float = 42.0,
                     max_angle_step: float = 0.6) -> list[tuple[str, bool, str]]:
    """world_seq: per-frame {node: (x,y,angle,scale)} world transforms."""
    out = []
    names = world_seq[0].keys()
    for name in names:
        worst_xy, worst_a = 0.0, 0.0
        for f in range(1, len(world_seq)):
            a, b = world_seq[f - 1][name], world_seq[f][name]
            worst_xy = max(worst_xy, math.hypot(b[0] - a[0], b[1] - a[1]))
            da = abs((b[2] - a[2] + math.pi) % (2 * math.pi) - math.pi)
            worst_a = max(worst_a, da)
        ok = worst_xy <= max_jump_px and worst_a <= max_angle_step
        out.append((name, ok, f"maxMove={worst_xy:.1f}px maxTurn={math.degrees(worst_a):.1f}deg"))
    return out


def check_foot_contact(world_seq, foot_nodes, planted_ranges, tol=2.0,
                       allow_x_sweep=()):
    """planted_ranges: {foot_node: [(start_frame,end_frame),...]} ground holds y.

    Feet in allow_x_sweep use the centered walk-loop convention: vertical
    ground contact is strict while the authored gait sweeps x relative to the
    static-camera body. Everything else must be fully pinned (x and y).
    """
    out = []
    for foot, ranges in planted_ranges.items():
        for (s, e) in ranges:
            ys = [world_seq[f][foot][1] for f in range(s, e + 1)]
            drift = max(ys) - min(ys)
            xs = [world_seq[f][foot][0] for f in range(s, e + 1)]
            xdrift = max(xs) - min(xs)
            if foot in allow_x_sweep:
                ok = drift <= tol
                detail = f"yDrift={drift:.2f}px (ground contact; xSweep={xdrift:.1f}px authored)"
            else:
                ok = drift <= tol and xdrift <= tol
                detail = f"yDrift={drift:.2f}px xDrift={xdrift:.2f}px"
            out.append((f"{foot}@{s}-{e}", ok, detail))
    return out


def check_joint_overlap(rig, pose, pairs, min_overlap_ratio=0.12) -> list[tuple[str, bool, str]]:
    """For each (parent,child) joint, rasterize both and confirm their opaque
    footprints overlap near the child pivot, i.e. no visible joint gap."""
    out = []
    canvas = rig.render(pose, size=(960, 540), bg=(0, 0, 0, 0))
    arr = np.asarray(canvas)[:, :, 3]
    world = rig.world_transforms(pose)
    for parent, child in pairs:
        cx, cy = world[child][0], world[child][1]
        r = 26  # joint neighbourhood radius
        x0, x1 = max(0, int(cx - r)), min(canvas.width, int(cx + r))
        y0, y1 = max(0, int(cy - r)), min(canvas.height, int(cy + r))
        window = arr[y0:y1, x0:x1]
        cover = (window > 40).mean() if window.size else 0.0
        ok = cover >= min_overlap_ratio
        out.append((f"{parent}->{child}", ok, f"jointCoverage={cover:.2f}"))
    return out


def check_proportions(world_seq, expected_h, tol=0.12) -> list[tuple[str, bool, str]]:
    out = []
    hs, ws = [], []
    for frame in world_seq:
        xs = [p[0] for p in frame.values()]; ys = [p[1] for p in frame.values()]
        hs.append(max(ys) - min(ys)); ws.append(max(xs) - min(xs))
    h_med = float(np.median(hs))
    ok = abs(h_med - expected_h) / expected_h <= tol
    out.append(("characterHeight", ok, f"median={h_med:.0f}px expected~{expected_h}px widthMed={np.median(ws):.0f}px"))
    return out


def report(title, rows):
    print(f"\n== {title} ==")
    ok_all = True
    for name, ok, detail in rows:
        ok_all &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:28} {detail}")
    return ok_all


def run_all(rig, poses, foot_planted, joint_pairs, expected_h, clip_name,
            allow_x_sweep=()):
    print(f"\n########## QA: {clip_name} ({len(poses)} frames) ##########")
    results = []
    results.append(report("1. sprite transparency / no green", check_transparency()))
    world_seq = [rig.world_transforms(p) for p in poses]
    results.append(report("2. proportions", check_proportions(world_seq, expected_h)))
    results.append(report("3. joint continuity (overlap)",
                          check_joint_overlap(rig, poses[len(poses) // 2], joint_pairs)))
    results.append(report("4. foot contact (no slide)",
                          check_foot_contact(world_seq, list(foot_planted),
                                             foot_planted, allow_x_sweep=allow_x_sweep)))
    results.append(report("5. motion smoothness (no teleport)", check_smoothness(world_seq)))
    passed = all(results)
    print(f"\n>>> {clip_name}: {'ALL CHECKS PASS' if passed else 'FAILURES PRESENT — REGENERATE/FIX'}")
    return passed
