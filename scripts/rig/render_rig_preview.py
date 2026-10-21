#!/usr/bin/env python3
"""Headless renderer for the articulated Elly rig (viewing/validation aid).

Ports src/rig/animation.ts:poseAt 1:1 and composites the cutout layers from
src/assets/rig with the same pivot hierarchy as src/rig/ellyRig.tsx, then draws
the vector facial rig and coin. The Motion Canvas scene remains the source of
truth; this exists only because the sandbox has no browser to render in.
"""
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RIG = ROOT / 'src/assets/rig'
OUT = ROOT / 'output/rig-preview.mp4'
FRAMES = Path('/tmp/rig_frames')
W, H, FPS, DURATION = 1920, 1080, 30, 12
N = FPS * DURATION
TAU = math.tau

# ============================================================ poseAt port
ARM_R_HANG = -128.0
COIN_GROUND = (250.0, 34.0)
COIN_EXAMINE = (450.0, 800.0)
HAND_OFFSET = (195.0, 125.0)
# Fingertip offset from the shoulder at armR = 0 (the contact point).
HAND_TIP = (327.0, 211.0)
TIP_LEN = math.hypot(*HAND_TIP)
HIPS = (0.0, 172.0)
WAIST = (0.0, 232.0)
SHOULDER_R = (310.0, 542.0)


def clamp(v, a, b):
    return max(a, min(b, v))


def lerp(a, b, t):
    return a + (b - a) * t


def seg(t, a, b):
    return clamp((t - a) / (b - a), 0, 1)


def ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_cubic(t):
    return 1 - (1 - t) ** 2.2


def rot(x, y, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return x * c - y * s, x * s + y * c


def shoulder_r(spine):
    w2s = (SHOULDER_R[0] - WAIST[0], SHOULDER_R[1] - WAIST[1])
    sx = HIPS[0] + rot(WAIST[0] - HIPS[0], WAIST[1] - HIPS[1], spine)[0] \
        + rot(*w2s, spine)[0]
    sy = HIPS[1] + rot(WAIST[0] - HIPS[0], WAIST[1] - HIPS[1], spine)[1] \
        + rot(*w2s, spine)[1]
    return sx, sy


def right_hand(spine, arm_r, arm_scale=1.0):
    # The arm node visually rotates by spine + armR (it inherits the waist bend).
    sx, sy = shoulder_r(spine)
    dx, dy = rot(HAND_TIP[0], HAND_TIP[1], spine + arm_r)
    return sx + dx * arm_scale, sy + dy * arm_scale


def reach(target, spine):
    """armR angle + cartoon stretch scale so the fingertip touches target."""
    sx, sy = shoulder_r(spine)
    dist = math.hypot(target[0] - sx, target[1] - sy)
    scale = clamp(dist / TIP_LEN, 1.0, 1.9)
    rest = math.atan2(HAND_TIP[1], HAND_TIP[0])
    total = math.atan2(target[1] - sy, target[0] - sx) - rest
    return math.degrees(total) - spine, scale


# Measured glove-palm offset from the fingertip, in arm-local coordinates.
PALM_OFFSET = (-89.0, -58.0)
PALM_LOCAL = (HAND_TIP[0] + PALM_OFFSET[0],
              HAND_TIP[1] + PALM_OFFSET[1])
PALM_LEN = math.hypot(*PALM_LOCAL)


def right_palm(spine, arm_r, arm_scale=1.0):
    sx, sy = shoulder_r(spine)
    dx, dy = rot(PALM_LOCAL[0], PALM_LOCAL[1], spine + arm_r)
    return sx + dx * arm_scale, sy + dy * arm_scale


def palm_reach(target, spine):
    """Solve armR + stretch so the palm lands on a root-space target."""
    sx, sy = shoulder_r(spine)
    dist = math.hypot(target[0] - sx, target[1] - sy)
    scale = clamp(dist / PALM_LEN, 1.0, 1.9)
    rest = math.atan2(PALM_LOCAL[1], PALM_LOCAL[0])
    total = math.atan2(target[1] - sy, target[0] - sx) - rest
    return math.degrees(total) - spine, scale


def body_x(u):
    """Root x of the eased walk at step-coordinate u (4 steps over 3 s)."""
    return lerp(-720.0, 0.0, ease_in_out(clamp(u / 4.0, 0.0, 1.0)))


def walk_pose(t):
    """Footprint walk cycle.

    A planted foot keeps a constant WORLD x while the body travels over it;
    a foot only moves while airborne (swing), so there is no foot sliding.
    Returns leg angles, flex values and counter-swinging arm angles.
    """
    u = t / 0.75
    j = min(int(u), 3)
    frac = clamp(u - j, 0.0, 1.0)
    rx = body_x(u)
    hip_r, hip_l = rx + 170.0, rx - 220.0
    prints_r = [body_x(0) + 170.0, body_x(2) + 170.0, body_x(4) + 170.0]
    prints_l = [body_x(1) - 220.0, body_x(3) - 220.0]

    def target(foot):
        if foot == 'R':
            if j in (0, 2):
                return prints_r[j // 2], False
            k = (j - 1) // 2
            return lerp(prints_r[k], prints_r[k + 1], ease_in_out(frac)), True
        if j in (1, 3):
            return prints_l[(j - 1) // 2], False
        if j == 0:  # entry: left foot starts under its hip and steps to print 1
            return lerp(body_x(0) - 220.0, prints_l[0], ease_in_out(frac)), True
        return lerp(prints_l[0], prints_l[1], ease_in_out(frac)), True

    out = {}
    for foot, hip in (('R', hip_r), ('L', hip_l)):
        tx, airborne = target(foot)
        dx = clamp(tx - hip, -160.0, 160.0)
        out[foot] = math.degrees(math.atan2(dx, 165.0))
        out['flex' + foot] = (1 - 0.24 * math.sin(math.pi * frac)) if airborne \
            else (0.95 if abs(tx - hip) > 150 else 1.0)
    return out


def blink_pulse(t, center, width=0.16):
    d = abs(t - center)
    return 0.0 if d > width else math.cos((d / width) * math.pi / 2)


def pose_at(t):
    s = dict(
        rootX=0.0, rootY=-450.0, rootScale=0.57, rootRotation=0.0,
        legL=0.0, legR=0.0, flexL=1.0, flexR=1.0,
        spine=0.0, head=0.0, armL=0.0, armR=ARM_R_HANG, armScale=1.0,
        earL=0.0, earR=0.0, tail=0.0,
        blink=0.0, gazeX=0.0, gazeY=0.0, browLift=0.0,
        mouth='open', mouthOpen=0.85, cameraZoom=1.0,
        coin=dict(visible=False, attached=False, x=COIN_GROUND[0],
                  y=COIN_GROUND[1], scale=1.0, spin=0.0),
    )
    s['blink'] = max(blink_pulse(t, 3.35), blink_pulse(t, 8.75),
                     blink_pulse(t, 11.55, 0.13))

    if t < 3:
        phase = t / 0.75
        s['rootX'] = body_x(phase)
        wp = walk_pose(t)
        s['legR'], s['legL'] = wp['R'], wp['L']
        s['flexR'], s['flexL'] = wp['flexR'], wp['flexL']
        # Arms counter-swing against the same-side legs.
        s['armL'] = -0.6 * wp['L']
        s['armR'] = ARM_R_HANG - 0.6 * wp['R']
        wave = math.sin(TAU * phase)
        s['spine'] = -3.5 * wave
        s['head'] = -0.35 * s['spine']
        s['earL'] = 7 * math.sin(TAU * phase + 0.7)
        s['earR'] = 6 * math.sin(TAU * phase + 0.7)
        s['tail'] = 9 * math.sin(TAU * phase - 0.9)
        s['rootY'] = -450 + 7 * (0.5 - 0.5 * math.cos(TAU * phase))
        s['mouth'] = 'open'
        s['mouthOpen'] = 0.85

    if 3 <= t < 5:
        q = ease_in_out(seg(t, 3, 3.5))
        s['legL'] = lerp(s['legL'], 0, q)
        s['legR'] = lerp(s['legR'], 0, q)
        s['armL'] = lerp(s['armL'], 0, q)
        s['armR'] = lerp(s['armR'], ARM_R_HANG, q)
        s['spine'] = lerp(s['spine'], 0, q)
        s['tail'] = lerp(s['tail'], 0, q)
        look = ease_in_out(seg(t, 3.6, 4.6))
        s['head'] = lerp(0, -20, look)
        s['gazeY'] = lerp(0, -16, look)
        s['gazeX'] = lerp(0, 10, look)
        s['mouth'] = 'small'

    if t >= 5:
        s['coin']['visible'] = True
        s['coin']['spin'] = TAU * 1.5 * seg(t, 5, 6.4)
    if 5 <= t < 8:
        gq = ease_out_cubic(seg(t, 5, 5.7))
        s['gazeX'] = lerp(10, 26, gq)
        s['gazeY'] = lerp(-16, -22, gq)
        s['head'] = lerp(-20, -28, ease_in_out(seg(t, 5, 5.8)))
        s['browLift'] = 0.25
        bend = ease_in_out(seg(t, 5.5, 6.5))
        rise = ease_in_out(seg(t, 6.7, 7.8))
        ba = bend * (1 - rise)
        s['spine'] = 34 * ba
        s['flexL'] = 1 - 0.22 * ba
        s['flexR'] = 1 - 0.22 * ba
        s['legL'] = -7 * ba
        s['legR'] = 7 * ba
        s['rootY'] = -450 - 55 * ba
        if t < 6.6:
            rq = ease_in_out(seg(t, 5.7, 6.6))
            ang, sc = reach(COIN_GROUND, s['spine'])
            s['armR'] = lerp(ARM_R_HANG, ang, rq)
            s['armScale'] = lerp(1.0, sc, rq)
        elif t < 6.9:
            ang, sc = reach(COIN_GROUND, s['spine'])
            s['armR'], s['armScale'] = ang, sc
        else:
            cq = ease_in_out(seg(t, 6.9, 7.8))
            ang0, sc0 = reach(COIN_GROUND, s['spine'])
            ang1, sc1 = palm_reach(COIN_EXAMINE, s['spine'])
            s['armR'] = lerp(ang0, ang1, cq)
            s['armScale'] = lerp(sc0, sc1, cq)
        s['mouth'] = 'small'
        if t >= 6.6:
            s['coin']['attached'] = True
            tx, ty = right_hand(s['spine'], s['armR'], s['armScale'])
            if t < 6.9:
                f = ease_out_cubic(seg(t, 6.6, 6.9))
                s['coin']['x'] = lerp(COIN_GROUND[0], tx, f)
                s['coin']['y'] = lerp(COIN_GROUND[1], ty, f)
            else:
                px, py = right_palm(s['spine'], s['armR'], s['armScale'])
                f = ease_in_out(seg(t, 6.9, 7.2))
                s['coin']['x'] = lerp(tx, px, f)
                s['coin']['y'] = lerp(ty, py, f)

    if 8 <= t < 10:
        hq = ease_in_out(seg(t, 8, 8.4))
        ang, sc = palm_reach(COIN_EXAMINE, 0)
        s['armR'] = lerp(s['armR'], ang, hq)
        s['armScale'] = lerp(s['armScale'], sc, hq)
        s['spine'] = lerp(s['spine'], 0, hq)
        s['flexL'] = s['flexR'] = 1
        s['legL'] = s['legR'] = 0
        s['head'] = lerp(s['head'], -6, hq)
        s['gazeX'], s['gazeY'] = 22, 6
        s['mouth'] = 'small'
        s['coin']['attached'] = True
        if t >= 9:
            q = ease_out_cubic(seg(t, 9, 9.25))
            s['browLift'] = lerp(0.25, 1, q)
            s['head'] = lerp(-6, -14, q)
            s['mouth'] = 'oh'
            s['mouthOpen'] = lerp(0.2, 1, q)
            s['gazeX'], s['gazeY'] = 6, 10
            s['earL'] = s['earR'] = 3 * q
            stretch = math.sin(math.pi * seg(t, 9, 9.5))
            s['rootY'] = -450 + 26 * stretch
            s['rootScale'] = 0.57 * (1 + 0.05 * stretch)
            s['spine'] = -5 * stretch
        # Coin follows the final palm pose of the frame (after the take).
        hx, hy = right_palm(s['spine'], s['armR'], s['armScale'])
        s['coin']['x'], s['coin']['y'] = hx, hy

    if t >= 10:
        vanish = seg(t, 10, 10.15)
        s['coin']['visible'] = vanish < 1
        s['coin']['attached'] = True
        hx, hy = right_palm(s['spine'], s['armR'], s['armScale'])
        s['coin']['x'], s['coin']['y'] = hx, hy
        s['coin']['scale'] = 1 - vanish
        freeze = ease_in_out(seg(t, 10, 10.4))
        s['armR'] = lerp(s['armR'], ARM_R_HANG + 6, freeze)
        s['armScale'] = lerp(s['armScale'], 1.0, freeze)
        s['head'] = lerp(s['head'], -8, freeze)
        s['browLift'] = lerp(s['browLift'], 0.55, freeze)
        s['mouth'] = 'flat'
        s['mouthOpen'] = 1
        s['rootY'] = lerp(s['rootY'], -450, freeze)
        s['rootScale'] = lerp(s['rootScale'], 0.57, freeze)
        s['spine'] = lerp(s['spine'], 0, freeze)
        s['earL'] = s['earR'] = 0
        s['gazeX'] = lerp(6, 22, freeze)
        s['gazeY'] = lerp(10, -14, freeze)
        glance = ease_in_out(seg(t, 10.5, 11.1))
        s['head'] = lerp(-8, 14, glance)
        s['gazeX'] = lerp(22, 30, glance)
        s['gazeY'] = lerp(-14, -6, glance)
        to_cam = ease_in_out(seg(t, 11.2, 11.7))
        s['head'] = lerp(14, 0, to_cam)
        s['gazeX'] = lerp(30, 0, to_cam)
        s['gazeY'] = lerp(-6, 2, to_cam)
        if t > 11.5:
            s['mouth'] = 'small'

    s['cameraZoom'] = lerp(1.0, 1.06, ease_in_out(seg(t, 0, DURATION)))
    return s


# ============================================================ rig geometry
# (box, native joint) and pivot rig-space computed like ellyRig.tsx `part()`.
def part_geom(box, joint):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    plx, ply = joint[0] - x0, joint[1] - y0
    pivot = (joint[0] - 650, 1476 - joint[1])
    img_offset = (-plx + w / 2, ply - h / 2)
    return dict(file=f'{RIG}/{None}.png', size=(w, h), offset=img_offset,
                pivot=pivot, box=box)


PARTS = {
    'legL':  dict(box=(250, 1285, 645, 1472), joint=(430, 1300), file='legL', flex=None),
    'legR':  dict(box=(635, 1285, 1000, 1472), joint=(820, 1300), file='legR', flex=None),
    'tail':  dict(box=(945, 1220, 1130, 1390), joint=(975, 1300), file='tail', flex=None),
    'torso': dict(box=(120, 770, 1120, 1345), joint=(650, 1240), file='torso', flex=None),
    'armL':  dict(box=(55, 920, 360, 1320), joint=(300, 960), file='armL', flex=None),
    'armR':  dict(box=(853, 691, 1291, 1022), joint=(960, 930), file='armR', flex=None),
    'head':  dict(box=(40, 10, 1230, 895), joint=(650, 830), file='head_clean', flex=None),
    'earL':  dict(box=(15, 180, 330, 770), joint=(300, 330), file='earL', flex=None),
    'earR':  dict(box=(930, 150, 1100, 620), joint=(980, 300), file='earR', flex=None),
}
for p in PARTS.values():
    g = part_geom(p['box'], p['joint'])
    p['size'], p['offset'], p['pivot'] = g['size'], g['offset'], g['pivot']
    p['img'] = Image.open(RIG / f"{p['file']}.png").convert('RGBA')

# local positions (relative to parent joint) mirroring ellyRig.tsx hierarchy
HIPS_P = (0.0, 172.0)
WAIST_P = (0.0, 232.0)
NECK_P = (0.0, 642.0)
# Node offsets mirror ellyRig.tsx exactly: part pivot minus parent joint.
LOCAL = {
    'tail':  ('hips', (325, 4)),
    'legR':  ('hips', (170, 4)),
    'legL':  ('hips', (-220, 4)),
    'spine': ('hips', (0, 60)),
    'torso': ('spine', (0, 4)),
    'armL':  ('spine', (-350, 284)),
    'armR':  ('spine', (310, 314)),
    'neck':  ('spine', (0, 410)),
    'earL':  ('neck', (-350, 504)),
    'earR':  ('neck', (330, 534)),
    'head':  ('neck', (0, 4)),
}
DRAW_ORDER = ['tail', 'legR', 'legL', 'torso', 'armL', 'armR',
              'earL', 'earR', 'head']

# face geometry, head-local (native point minus neck pivot 650,830)
# pupil centers measured from the rendered baked artwork (ground truth).
EYE_L = dict(c=(-209, 396), rx=101, ry=92, pupil=(-137, 389))
EYE_R = dict(c=(122, 425), rx=95, ry=87, pupil=(190, 419))
PUPIL_R = 17
EYE_WHITE = (253, 253, 253, 255)
MOUTH_C = (-42, 113)
FUR = (247, 246, 242, 255)
OUTLINE = (20, 17, 15, 255)
TONGUE = (215, 119, 127, 255)
BROW_L = [(-295, 540), (-235, 560), (-175, 575)]
BROW_R = [(95, 595), (150, 588), (200, 575)]
# Covers extend slightly past the redrawn brows to hide the full baked strokes.
BROW_COVER_L = [(-312, 534), (-235, 560), (-138, 582)]
BROW_COVER_R = [(82, 598), (150, 588), (214, 572)]


def mc_to_px(x, y, zoom):
    return 960 + x * zoom, 540 - y * zoom


def chain_world(s):
    """World pivot (MC coords) + total rotation for every joint."""
    k = s['rootScale']
    root = (s['rootX'], s['rootY'])
    hips = (root[0] + k * HIPS_P[0], root[1] + k * HIPS_P[1])
    spine_p = (hips[0] + k * LOCAL['spine'][1][0],
               hips[1] + k * LOCAL['spine'][1][1])
    neck_p = (spine_p[0] + k * LOCAL['neck'][1][0],
              spine_p[1] + k * LOCAL['neck'][1][1])
    parents = {'hips': (hips, 0.0), 'spine': (spine_p, s['spine']),
               'neck': (neck_p, s['spine'] + s['head'])}
    out = {}
    for name, (parent, local) in LOCAL.items():
        if name in ('spine', 'neck'):
            continue
        pp, pr = parents[parent]
        if name == 'tail':
            ang = pr + s['tail']
        elif name == 'legR':
            ang = pr + s['legR']
        elif name == 'legL':
            ang = pr + s['legL']
        elif name == 'torso':
            ang = pr
        elif name == 'armL':
            ang = pr + s['armL']
        elif name == 'armR':
            ang = pr + s['armR']
        elif name == 'earL':
            ang = pr + s['earL']
        elif name == 'earR':
            ang = pr + s['earR']
        else:  # head
            ang = pr
        wx = pp[0] + k * local[0]
        wy = pp[1] + k * local[1]
        out[name] = (wx, wy, ang)
    out['_neck'] = (neck_p, s['spine'] + s['head'])
    out['_root'] = (root, s['rootRotation'], k)
    return out


def paste_part(canvas, s, name, world):
    p = PARTS[name]
    wx, wy, ang = world[name]
    k = s['rootScale']
    img = p['img']
    if name == 'legL':
        img = img.resize((img.width, max(1, round(img.height * s['flexL']))))
    if name == 'legR':
        img = img.resize((img.width, max(1, round(img.height * s['flexR']))))
    if name == 'armR':
        asc = s['armScale']
        img = img.resize((max(1, round(img.width * asc)),
                          max(1, round(img.height * asc))), Image.BILINEAR)
    # mc_to_px already maps y-up world to y-down screen, so the texture needs
    # no vertical flip. A y-up rotation by ang is a standard rotation by -ang
    # on screen; PIL's positive angle equals standard R(-ang), so pass ang.
    rotated = img.rotate(ang, expand=True, resample=Image.BILINEAR)
    ox, oy = p['offset']
    # armR stretches about its shoulder pivot (MC scales the joint node), so
    # the image-center offset must scale with the same factor.
    if name == 'armR':
        ox, oy = ox * s['armScale'], oy * s['armScale']
    # image center relative to pivot, then rotated, scaled by root scale
    cx, cy = rot(ox, oy, ang)
    center_mc = (wx + k * cx, wy + k * cy)
    z = s['cameraZoom']
    px, py = mc_to_px(center_mc[0], center_mc[1], z)
    rotated = rotated.resize(
        (max(1, round(rotated.width * k * z)),
         max(1, round(rotated.height * k * z))), Image.BILINEAR)
    canvas.alpha_composite(rotated, (round(px - rotated.width / 2),
                                     round(py - rotated.height / 2)))


def head_transform(local, neck, k, z):
    (nx, ny), nang = neck
    rx, ry = rot(local[0], local[1], nang)
    return mc_to_px(nx + k * rx, ny + k * ry, z), nang


def draw_face(canvas, s, world):
    neck = world['_neck']
    k, z = s['rootScale'], s['cameraZoom']
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def pt(local):
        (px, py), _ = head_transform(local, neck, k, z)
        return px, py

    def scale_v(v):
        return v * k * z

    # --- cover: erase the baked brows so procedural ones can replace them.
    # Baked pupils are already erased inside head_clean.png itself.
    for brow in (BROW_COVER_L, BROW_COVER_R):
        d.line([pt(p) for p in brow], fill=FUR,
               width=round(scale_v(34)), joint='curve')

    # brows (redrawn on top of the cover; lift 0 == baked position)
    lift = s['browLift']
    for brow, sign in ((BROW_L, -1), (BROW_R, 1)):
        pts = [(x, y - 10 * lift) for x, y in brow]
        pts = [pt(p) for p in pts]
        d.line(pts, fill=OUTLINE, width=round(scale_v(10)), joint='curve')

    # eyes
    for eye, sign in ((EYE_L, -1), (EYE_R, 1)):
        c = pt(eye['c'])
        rx, ry = scale_v(eye['rx']), scale_v(eye['ry'])
        gx = clamp(s['gazeX'], -(eye['rx'] - PUPIL_R - 22),
                   eye['rx'] - PUPIL_R - 22)
        gy = clamp(s['gazeY'], -(eye['ry'] - PUPIL_R - 18),
                   eye['ry'] - PUPIL_R - 18)
        pr = scale_v(PUPIL_R)
        if s['blink'] < 0.99:
            pup = pt((eye['pupil'][0] + gx, eye['pupil'][1] + gy))
            alpha = round(255 * (1 - s['blink']))
            d.ellipse((pup[0] - pr, pup[1] - pr, pup[0] + pr, pup[1] + pr),
                      fill=(20, 17, 15, alpha))
        # eyelid: fur ellipse that grows down from the top of the eye
        b = s['blink']
        if b > 0.01:
            top = c[1] - ry
            lid = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lid)
            ld.ellipse((c[0] - rx, top, c[0] + rx, top + 2 * ry * b),
                       fill=FUR)
            layer = Image.alpha_composite(layer, lid)
            d = ImageDraw.Draw(layer)
        if b > 0.45:
            lx0, ly0 = pt((eye['c'][0] - eye['rx'] + 12, eye['c'][1]))
            lx1, ly1 = pt((eye['c'][0] + eye['rx'] - 12, eye['c'][1]))
            mx, my = pt((eye['c'][0], eye['c'][1] + 6))
            d.line([(lx0, ly0), (mx, my), (lx1, ly1)], fill=OUTLINE,
                   width=round(scale_v(9)), joint='curve')

    # mouth
    mc = pt(MOUTH_C)
    m, op = s['mouth'], s['mouthOpen']
    lw = round(scale_v(11))
    if m in ('smile', 'small'):
        local_pts = [(-34, 4), (0, 10), (34, 4)] if m == 'small' else \
            [(-58, -18), (-16, 30), (40, 24), (62, -8)]
        d.line([pt(p) for p in local_pts], fill=OUTLINE, width=lw, joint='curve')
    elif m == 'flat':
        a = pt((-40, 6)); b = pt((40, 6))
        d.line([a, b], fill=OUTLINE, width=round(scale_v(10)))
    elif m == 'open':
        sy = 0.3 + 0.7 * op
        rw, rh = scale_v(48), scale_v(58) * sy
        d.ellipse((mc[0] - rw, mc[1] - rh + scale_v(4),
                   mc[0] + rw, mc[1] + rh + scale_v(4)), fill=OUTLINE)
        tw, th = scale_v(31), scale_v(20)
        d.ellipse((mc[0] - tw, mc[1] + scale_v(14),
                   mc[0] + tw, mc[1] + scale_v(14) + 2 * th), fill=TONGUE)
    elif m == 'oh':
        sc = 0.6 + 0.4 * op
        rw, rh = scale_v(36) * sc, scale_v(41) * sc
        d.ellipse((mc[0] - rw, mc[1] - rh, mc[0] + rw, mc[1] + rh), fill=OUTLINE)
        tw, th = scale_v(17) * sc, scale_v(11) * sc
        d.ellipse((mc[0] - tw, mc[1], mc[0] + tw, mc[1] + 2 * th), fill=TONGUE)
    canvas.alpha_composite(layer)


def draw_coin(canvas, s, world):
    c = s['coin']
    if not c['visible'] or c['scale'] <= 0.01:
        return
    root = world['_root']
    k, z = root[2], s['cameraZoom']
    px, py = mc_to_px(root[0][0] + k * c['x'], root[0][1] + k * c['y'], z)
    r = 32 * k * z * c['scale']
    sx = abs(math.cos(c['spin']))
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((px - r * sx, py - r, px + r * sx, py + r),
              fill=(227, 182, 91, 255), outline=(138, 106, 47, 255),
              width=max(2, round(r * 0.16)))
    r2 = r * 0.66
    d.ellipse((px - r2 * sx, py - r2, px + r2 * sx, py + r2),
              fill=(243, 210, 126, 255), outline=(185, 143, 60, 255),
              width=max(1, round(r * 0.1)))
    d.ellipse((px - r * 0.28 * sx, py - r * 0.28, px + r * 0.1 * sx, py + r * 0.1),
              fill=(255, 243, 207, 230))
    canvas.alpha_composite(layer)


# ============================================================ background
def bg_px(x, y):
    """Scene background uses Motion Canvas screen coords (y-down)."""
    return 960 + x, 540 + y


def build_base():
    top, mid, bot = np.array((20, 22, 43)), np.array((35, 42, 85)), \
        np.array((58, 53, 102))
    grad = np.zeros((H, W, 3), np.uint8)
    for y in range(H):
        t = y / (H - 1)
        c = top + (mid - top) * (t / 0.55) if t < 0.55 else \
            mid + (bot - mid) * ((t - 0.55) / 0.45)
        grad[y] = c
    img = Image.fromarray(grad, 'RGB').convert('RGBA')
    d = ImageDraw.Draw(img)
    for x, y, sz in [(-760, -380, 13), (-540, -250, 9), (-260, -420, 11),
                     (120, -360, 9), (420, -460, 12), (760, -180, 9)]:
        px, py = bg_px(x, y)
        d.polygon([(px, py - sz), (px + sz, py), (px, py + sz), (px - sz, py)],
                  fill=(255, 233, 168, 200))
    for x, y, r in [(-820, -180, 4), (-640, -460, 3), (-420, -330, 4),
                    (-150, -220, 3), (60, -470, 3), (280, -260, 4),
                    (560, -360, 3), (830, -380, 4), (-880, -420, 3)]:
        px, py = bg_px(x, y)
        d.ellipse((px - r, py - r, px + r, py + r), fill=(253, 246, 221, 180))
    mx, my = bg_px(610, -325)
    for r, a in ((160, 26), (120, 34), (95, 60)):
        glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((mx - r, my - r, mx + r, my + r),
                                     fill=(255, 237, 176, a))
        img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    d.ellipse((mx - 75, my - 75, mx + 75, my + 75), fill=(246, 231, 189, 255))
    hx, hy = bg_px(0, 760)
    d.ellipse((hx - 1250, hy - 410, hx + 1250, hy + 410), fill=(37, 43, 82, 255))
    hx, hy = bg_px(-380, 820)
    d.ellipse((hx - 1050, hy - 360, hx + 1050, hy + 360), fill=(31, 37, 71, 255))
    gx, gy = bg_px(0, 500)
    d.rectangle((0, gy, W, H), fill=(26, 31, 61, 255))
    cx, cy = bg_px(0, 470)
    d.ellipse((cx - 750, cy - 95, cx + 750, cy + 95), fill=(35, 42, 85, 255))
    try:
        font = ImageFont.truetype(
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
        tx, ty = bg_px(700, 435)
        d.text((tx - 130, ty - 15), 'SMART BARK', fill=(255, 255, 255, 115),
               font=font)
    except OSError:
        pass
    return img


def render_frame(t):
    s = pose_at(t)
    canvas = build_base()
    z = s['cameraZoom']
    # contact shadow
    sw, sh = 165 * z, 26 * z
    spx, spy = mc_to_px(s['rootX'], s['rootY'] + 14, z)
    sh_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh_layer).ellipse(
        (spx - sw, spy - sh, spx + sw, spy + sh), fill=(10, 12, 28, 130))
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(7))
    canvas = Image.alpha_composite(canvas, sh_layer)

    world = chain_world(s)
    for name in DRAW_ORDER:
        paste_part(canvas, s, name, world)
    draw_face(canvas, s, world)
    draw_coin(canvas, s, world)  # coin on top so it never hides in the hand
    return canvas.convert('RGB')


def main():
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    for n in range(N):
        render_frame(n / FPS).save(FRAMES / f'{n + 1:04d}.png')
        if n % 30 == 0:
            print(f'frame {n}/{N}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.run(['node', '-e',
                         "console.log(require('@ffmpeg-installer/ffmpeg').path)"],
                        cwd=ROOT, capture_output=True, text=True, check=True
                        ).stdout.strip()
    subprocess.run([ff, '-y', '-framerate', str(FPS),
                    '-i', str(FRAMES / '%04d.png'), '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    str(OUT)], check=True)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
