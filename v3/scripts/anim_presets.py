#!/usr/bin/env python3
"""
anim_presets.py — Phase 4: eleven intent-driven animation presets for the
sprite rig. Every preset is a function (anim, frame, n) -> pose dict layered
over the calibrated rest pose. Nothing ever translates one whole static PNG:
limbs use analytic two-bone IK with foot pinning, the face swaps real mouth
sprites, lids/blinks and brows move independently, and side-view sprites are
swapped in for turns.
"""
from __future__ import annotations
import copy
import math
from sprite_engine import two_bone_ik, norm, smooth

MOUTHS = {
    "smile": "mouth_smile.png",
    "talk": "mouth_talk.png",
    "happy": "mouth_happy.png",
    "surprised": "mouth_surprised.png",
    "angry": "mouth_angry.png",
}
TAU = 2 * math.pi


class Anim:
    # chains whose end effector is a real child pivot: (upper, lower, child)
    IK_CHAINS = [
        ("leg_up_l", "leg_lo_l", "foot_l"),
        ("leg_up_r", "leg_lo_r", "foot_r"),
        ("arm_up_l", "arm_lo_l", None),
        ("arm_up_r", "arm_lo_r", None),
    ]
    # for arms (no wrist node), hand anchor sits this fraction down the forearm
    HAND_ANCHOR_FRAC = 0.72

    def __init__(self, rig):
        self.rig = rig
        self.rest = rig.rest_pose()
        rest_world = rig.world_transforms(self.rest)
        self._bone = {}
        self._effector = {}
        self._rest_ang = {}     # (upper,lower) -> canvas angle of each rest bone
        for upper, lower, child in self.IK_CHAINS:
            up, lo = rest_world[upper], rest_world[lower]
            # l1 = real shoulder/hip -> elbow/knee pivot distance at rest.
            # Leg bones get an 8% reach margin: the fur sprites overlap at the
            # hidden knee, and the margin lets a planted sole stay pinned while
            # the hip bobs through the gait instead of clamping short.
            margin = 1.08 if child is not None else 1.0
            self._bone[upper] = math.hypot(lo[0] - up[0], lo[1] - up[1]) * margin
            r1 = math.atan2(lo[1] - up[1], lo[0] - up[0])
            if child is not None:                       # l2 = real knee -> ankle
                ch = rest_world[child]
                self._bone[lower] = math.hypot(ch[0] - lo[0], ch[1] - lo[1]) * margin
                r2 = math.atan2(ch[1] - lo[1], ch[0] - lo[0])
                self._effector[lower] = (ch[0], ch[1])
            else:                                       # forearm -> hand anchor
                node = rig.nodes[lower]
                ws = self._rest_world_scale(lower)
                hand_len = node.img.height * (1 - node.pivot[1]) * ws * self.HAND_ANCHOR_FRAC
                self._bone[lower] = hand_len
                r2 = math.pi / 2                        # forearm hangs straight down
                self._effector[lower] = (lo[0], lo[1] + hand_len)
            self._rest_ang[(upper, lower)] = (r1, r2)

    # ------------------------------------------------------------ helpers
    def _rest_world_scale(self, name):
        ws, cur = 1.0, name
        while cur is not None:
            ws *= self.rig.nodes[cur].base_scale
            cur = self.rig.nodes[cur].parent
        return ws

    def bone(self, name):
        return self._bone[name]

    def base(self):
        return copy.deepcopy(self.rest)

    def world(self, pose, name):
        return self.rig.world_transforms(pose)[name]

    def aim_ik(self, pose, upper, lower, target, bend, rel_twist=0.0):
        """Drive a two-bone chain to a world target; write local angles.

        two_bone_ik speaks canvas angles from +x, while each sprite bone points
        along its rest offset at local angle 0, so subtract the rest bone
        angles and the parent's world rotation to get local FK angles.
        """
        ox, oy, pa, _ = self.world(pose, upper)
        a1, a2 = two_bone_ik((ox, oy), target, self.bone(upper),
                             self.bone(lower), bend)
        a2 += rel_twist
        r1, r2 = self._rest_ang[(upper, lower)]
        upper_world_rot = a1 - r1
        pose[upper]["a"] = norm(upper_world_rot - pa)
        # lower bone canvas direction must be a2 -> its world rotation is a2-r2
        pose[lower]["a"] = norm((a2 - r2) - upper_world_rot)
        return a1, a2

    def flatten_foot(self, pose, lower, foot):
        """Hold the sole at world angle 0 regardless of the shin angle."""
        pose[foot]["a"] = norm(-self.world(pose, lower)[2])

    def pin_foot(self, pose, upper, lower, foot, target, bend):
        """Two-bone IK to the ankle, then inverse-FK correct the foot node so
        its pivot lands EXACTLY on the world target with a flat sole — planted
        feet therefore have zero x/y slide even while the hip bobs."""
        rest_lo = self.world(self.rest, lower)
        rest_ft = self.world(self.rest, foot)
        ankle_drop = rest_ft[1] - rest_lo[1]
        self.aim_ik(pose, upper, lower, (target[0], target[1] - ankle_drop), bend)
        ax, ay, pa, ps = self.world(pose, lower)
        dx, dy = target[0] - ax, target[1] - ay
        ca, sa = math.cos(pa), math.sin(pa)
        # world delta = R(pa) * (ps * local)  =>  local = R(-pa) * delta / ps
        pose[foot]["x"] = (ca * dx + sa * dy) / ps
        pose[foot]["y"] = (-sa * dx + ca * dy) / ps
        pose[foot]["a"] = norm(-pa)

    def pose_arm(self, pose, side, upper_ang, lower_ang, front=False):
        """Direct FK for an arm (more predictable than IK for sleeve sprites).
        side 'l': positive angles raise outward; side 'r': negative raises.
        front=True raises the arm's draw order above the head so the sleeve is
        not occluded when the arm is lifted."""
        up = f"arm_up_{side}"; lo = f"arm_lo_{side}"
        pose[up]["a"] = norm(upper_ang)
        pose[lo]["a"] = norm(lower_ang)
        if front:
            pose[up]["z"] = pose[lo]["z"] = 12

    def set_mouth(self, pose, kind):
        """Swap the mouth sprite AND apply its per-shape anchor so every mouth
        shape centers under the nose instead of sharing one pivot."""
        img = MOUTHS[kind]
        node = pose["mouth"]
        node["image"] = img
        dx, dy, smul = self.rig.spec.get("mouth_anchors", {}).get(
            img, [0, 0, 1.0])
        node["x"] = self.rest["mouth"]["x"] + dx
        node["y"] = self.rest["mouth"]["y"] + dy
        node["s"] = self.rest["mouth"]["s"] * smul

    def clear_mouth_anchor(self, pose):
        """Reset the mouth node to its smile baseline."""
        node = pose["mouth"]
        node["image"] = MOUTHS["smile"]
        node["x"] = self.rest["mouth"]["x"]
        node["y"] = self.rest["mouth"]["y"]
        node["s"] = self.rest["mouth"]["s"]

    def blink(self, pose, t, period=2.6, dur=0.3):
        """Blink both lids: lids slide fully over the eyes, then retract.
        Stronger travel and a longer hold so the blink reads on camera."""
        ph = (t % period) / period
        q = dur / period
        on = ph < q
        for lid, eye in (("lid_l", "eye_l"), ("lid_r", "eye_r")):
            pose[lid]["visible"] = on
            if on:
                k = math.sin(math.pi * ph / q)          # 0..1..0
                pose[lid]["y"] = self.rest[lid]["y"] - 14 * (1 - k)
                pose[eye]["scale_y"] = self.world(pose, eye)[3] * (1 - 0.75 * k)

    def foot_path(self, phase, offset, ground_y, sx, lift, stance=0.62):
        """Treadmill gait foot target; returns (dx, dy, planted)."""
        t = (phase / TAU + offset) % 1.0
        if t < stance:  # stance: planted, sweeps backward relative to body
            p = t / stance
            return (sx * (1 - 2 * p), 0.0, True)
        p = (t - stance) / (1 - stance)                  # swing: arc forward
        return (-sx + 2 * sx * smooth(p), -lift * math.sin(math.pi * p), False)

    def planted_ranges(self, n, offset, stance=0.62, cycles=None, period=None):
        """Frame ranges where a foot is planted, for the foot-contact QA."""
        ranges, start = [], None
        for i in range(n):
            t = (self._phase(i, n, cycles, period) / TAU + offset) % 1.0
            planted = t < stance
            if planted and start is None:
                start = i
            if not planted and start is not None:
                ranges.append((start, i - 1)); start = None
        if start is not None:
            ranges.append((start, n - 1))
        return ranges

    def _phase(self, i, n, cycles=None, period=None):
        if cycles is not None:
            return TAU * cycles * i / max(1, n - 1)
        return TAU * i / max(1, period * 24)


# ============================================================ presets ======
def p_idle(a: Anim, i, n):
    t = i / 24.0
    p = a.base()
    br = math.sin(TAU * t / 3.2)                                  # breathing
    p["torso"]["scale_y"] = a.world(p, "torso")[3] * (1 + 0.018 * br)
    p["head"]["y"] = a.rest["head"]["y"] - 1.6 * br
    p["tail"]["a"] = 0.14 * math.sin(TAU * t / 1.9)
    p["ear_l"]["a"] = 0.05 * math.sin(TAU * t / 2.7 + 1)
    p["ear_r"]["a"] = -0.05 * math.sin(TAU * t / 2.7 + 1)
    p["arm_up_l"]["a"] = 0.05 * math.sin(TAU * t / 3.2)
    p["arm_up_r"]["a"] = -0.05 * math.sin(TAU * t / 3.2)
    a.blink(p, t)
    return p


def _gait(a: Anim, i, n, *, cycles, stride, lift, lean, arm_swing, bob):
    p = a.base()
    ph = a._phase(i, n, cycles=cycles)
    p["torso"]["a"] = lean
    p["root_hip"]["y"] = a.rest["root_hip"]["y"] + bob * abs(math.sin(ph))
    # legs: IK to pinned/swinging foot targets
    for side, off, hip, up, lo, foot in (
            ("l", 0.0, "leg_up_l", "leg_up_l", "leg_lo_l", "foot_l"),
            ("r", 0.5, "leg_up_r", "leg_up_r", "leg_lo_r", "foot_r")):
        hx, hy, _, _ = a.world(p, hip)
        rest_foot = a.world(a.rest, foot)
        rest_hip = a.world(a.rest, hip)
        dx, dy, planted = a.foot_path(ph, off, rest_foot[1], stride, lift)
        # target relative to THIS leg's hip so it stays inside chain reach.
        # While planted the foot holds the fixed ground line (no vertical
        # slide); the swing phase arcs up off that line.
        target = (hx + (rest_foot[0] - rest_hip[0]) + dx,
                  rest_foot[1] if planted else rest_foot[1] + dy)
        bend = 1.0 if side == "l" else -1.0
        a.aim_ik(p, up, lo, target, bend)
        a.flatten_foot(p, lo, foot)                            # keep sole flat
    # arms counter-swing (FK)
    sw = arm_swing * math.sin(ph)
    p["arm_up_l"]["a"] = sw
    p["arm_up_r"]["a"] = -sw
    p["tail"]["a"] = 0.18 * math.sin(ph)
    p["head"]["a"] = -lean * 0.4
    a.blink(p, i / 24.0)
    return p


def p_walk(a, i, n):
    return _gait(a, i, n, cycles=4, stride=18, lift=18, lean=0.05,
                 arm_swing=0.38, bob=3.5)


# Root-motion walk: the hip translates across the frame and planted feet are
# pinned at fixed world contact points (zero slide), while swing feet arc to
# the next contact. Used for the locomotion clip with a parallax background.
WALK_STEP = 34.0          # px advanced per footfall
WALK_CYCLES = 4
WALK_HIP_X0 = 400.0       # hip x at the first frame
STRIKE_AHEAD = 22.0       # planted foot sits this far ahead of the hip at strike
STANCE = 0.62


def _walk_foot_target(a, foot_node, phase_offset, s, lift):
    """Absolute-world foot target for the root-motion walk."""
    gy = a.world(a.rest, foot_node)[1]
    local = (s + phase_offset) % 1.0
    k = math.floor(s + phase_offset)
    contact = WALK_HIP_X0 + (k + phase_offset) * WALK_STEP + STRIKE_AHEAD
    if local < STANCE:                                   # planted: fixed contact
        return contact, gy, True
    p = (local - STANCE) / (1 - STANCE)                  # swing to next contact
    nxt = WALK_HIP_X0 + (k + 1 + phase_offset) * WALK_STEP + STRIKE_AHEAD
    x = contact + (nxt - contact) * smooth(p)
    return x, gy - lift * math.sin(math.pi * p), False


def p_walk_root(a, i, n):
    p = a.base()
    s = WALK_CYCLES * i / max(1, n - 1)                  # continuous step count
    ph = TAU * s
    p["root_hip"]["x"] = WALK_HIP_X0 + s * WALK_STEP     # hip travels with the gait
    p["root_hip"]["y"] = a.rest["root_hip"]["y"] + 3.2 * abs(math.sin(ph))
    p["torso"]["a"] = 0.05
    for side, off, up, lo, foot in (
            ("l", 0.0, "leg_up_l", "leg_lo_l", "foot_l"),
            ("r", 0.5, "leg_up_r", "leg_lo_r", "foot_r")):
        tx, ty, _planted = _walk_foot_target(a, foot, off, s, lift=18)
        bend = 1.0 if side == "l" else -1.0
        a.pin_foot(p, up, lo, foot, (tx, ty), bend)
    sw = 0.36 * math.sin(ph)
    p["arm_up_l"]["a"], p["arm_up_r"]["a"] = sw, -sw
    p["tail"]["a"] = 0.18 * math.sin(ph)
    p["head"]["a"] = -0.02
    a.blink(p, i / 24.0)
    return p


def p_run(a, i, n):
    return _gait(a, i, n, cycles=6, stride=26, lift=32, lean=0.16,
                 arm_swing=0.7, bob=4.0)


def p_sit(a: Anim, i, n):
    t = i / 24.0
    p = a.base()
    br = math.sin(TAU * t / 3.0)
    p["root_hip"]["y"] = a.rest["root_hip"]["y"] + 40 + 1.2 * br
    p["torso"]["a"] = -0.03
    # hips rise while the planted paws stay at their rest ground positions, so
    # the two-bone IK folds the thighs out and shins down — a dog-sitting fold.
    for up, lo, foot, bend in (("leg_up_l", "leg_lo_l", "foot_l", 1.0),
                               ("leg_up_r", "leg_lo_r", "foot_r", -1.0)):
        tx, ty = a._effector[lo]
        a.aim_ik(p, up, lo, (tx, ty), bend)
        a.flatten_foot(p, lo, foot)                 # sole stays flat on ground
    # front paws hang relaxed at the sides, elbows tucked against the sweater
    a.pose_arm(p, "l", 0.14, 0.05)
    a.pose_arm(p, "r", -0.14, -0.05)
    p["tail"]["a"] = 0.1 * math.sin(TAU * t / 2.1)
    a.blink(p, t, period=3.4)
    return p


def p_talking(a: Anim, i, n):
    t = i / 24.0
    p = p_sit(a, i, n)
    # syllable mouth track: open talk shapes on beats, smile between
    beat = (t * 3.2) % 1.0
    a.set_mouth(p, "talk" if beat < 0.42 else "smile")
    p["head"]["a"] = 0.07 * math.sin(TAU * t / 1.1)
    p["head"]["y"] = a.rest["head"]["y"] - 1.5 * math.sin(TAU * t / 1.1)
    p["brow_l"]["a"] = 0.12 * math.sin(TAU * t / 1.7)
    p["brow_r"]["a"] = -0.12 * math.sin(TAU * t / 1.7)
    # illustrative right paw raises outward twice while speaking
    gest = max(0.0, math.sin(TAU * t / 2.5))
    a.pose_arm(p, "r", -0.5 * gest, -0.15 * gest, front=gest > 0.2)
    return p


def p_pointing(a: Anim, i, n, u_env=None):
    # u_env lets a clip script its own raise/hold/lower envelope; default is a
    # single smooth raise that holds to the end.
    u = smooth(i / max(1, n - 1)) if u_env is None else u_env
    p = a.base()
    # raise the right arm out-right (FK); the point sprite's index finger
    # extends the gesture. Small pokes once fully extended.
    poke = 0.05 * math.sin(TAU * (i / 24.0) * 2.2) if u > 0.55 else 0.0
    a.pose_arm(p, "r", -0.55 * u - poke, -0.15 * u, front=u > 0.15)
    if u > 0.25:                                   # point hand only while raised
        p["arm_lo_r"]["image"] = "hand_point.png"
        p["arm_lo_r"]["s"] = a.rest["arm_lo_r"]["s"] * 0.92
    a.pose_arm(p, "l", 0.08, 0.05)                      # left paw relaxed at side
    p["head"]["a"] = -0.12 * u
    p["brow_l"]["a"], p["brow_r"]["a"] = 0.18 * u, -0.18 * u
    a.blink(p, i / 24.0, period=3.0)
    return p


def p_surprised(a: Anim, i, n):
    u = smooth(min(1.0, i / (n * 0.35)))           # pop in, then hold
    p = a.base()
    p["head"]["y"] = a.rest["head"]["y"] - 8 * u
    p["head"]["a"] = -0.09 * u
    for eye in ("eye_l", "eye_r"):
        ws = a.world(p, eye)[3]
        p[eye]["scale_x"] = ws * (1 + 0.18 * u)
        p[eye]["scale_y"] = ws * (1 + 0.22 * u)
    for b in ("brow_l", "brow_r"):
        p[b]["y"] = a.rest[b]["y"] - 7 * u
    a.set_mouth(p, "surprised")
    p["mouth"]["s"] = a.rest["mouth"]["s"] * (1 + 0.35 * u)
    p["torso"]["scale_y"] = a.world(p, "torso")[3] * (1 + 0.03 * u)
    p["tail"]["a"] = 0.22 * u * math.sin(i * 0.8)
    return p


def p_angry(a: Anim, i, n):
    t = i / 24.0
    p = a.base()
    trem = math.sin(TAU * t * 6) * 0.012
    p["head"]["y"] = a.rest["head"]["y"] + 5
    p["head"]["a"] = 0.1 + trem
    p["brow_l"]["a"] = 0.42 + trem
    p["brow_r"]["a"] = -0.42 - trem
    for lid, eye in (("lid_l", "eye_l"), ("lid_r", "eye_r")):
        p[lid]["visible"] = True
        p[lid]["y"] = a.rest[lid]["y"] + 9
        p[eye]["scale_y"] = a.world(p, eye)[3] * 0.55          # narrowed glare
    a.set_mouth(p, "angry")
    # elbows cocked outward in a tense hunch, paws kept near the waist so the
    # sleeve/forearm sprites stay visually connected (angle-limited on purpose)
    a.pose_arm(p, "l", 0.45, 0.25)
    a.pose_arm(p, "r", -0.45, -0.25)
    p["tail"]["a"] = -0.15 + 0.05 * trem
    return p


def p_happy(a: Anim, i, n):
    t = i / 24.0
    p = a.base()
    bounce = max(0.0, math.sin(TAU * t / 0.9)) ** 2             # two hops
    p["root_hip"]["y"] = a.rest["root_hip"]["y"] - 12 * bounce
    p["head"]["a"] = 0.12 * math.sin(TAU * t / 1.8)
    a.set_mouth(p, "happy")
    for eye in ("eye_l", "eye_r"):                              # joyful shut eyes
        p[eye]["scale_y"] = a.world(p, eye)[3] * 0.18
    for b in ("brow_l", "brow_r"):
        p[b]["a"] = 0.25
    # both arms flung up-out in a cheer, angle-limited so sleeves stay joined
    a.pose_arm(p, "l", 0.55, 0.15, front=True)
    a.pose_arm(p, "r", -0.55, -0.15, front=True)
    p["tail"]["a"] = 0.5 * math.sin(TAU * t * 3)                # fast wag
    return p


def _turn_swap(p, a, on, side_image_head="head_side.png",
               side_image_torso=None):
    """Swap to side-view artwork at the apex of a turn; hide front-only parts."""
    face = ("eye_l", "eye_r", "lid_l", "lid_r", "brow_l", "brow_r", "mouth")
    if on:
        p["head"]["image"] = side_image_head
        for f in face:
            p[f]["visible"] = False
        p["ear_l"]["visible"], p["ear_r"]["visible"] = False, True
        if side_image_torso:
            p["torso"]["image"] = side_image_torso
    else:
        p["head"]["image"] = a.rest["head"]["image"]
        for f in face:
            p[f]["visible"] = a.rest[f].get("visible", True)
        p["ear_l"]["visible"] = p["ear_r"]["visible"] = True
        if side_image_torso:
            p["torso"]["image"] = a.rest["torso"]["image"]


def p_head_turn(a: Anim, i, n):
    u = i / max(1, n - 1)
    k = math.sin(math.pi * u)                                   # out and back
    p = a.base()
    p["head"]["a"] = -0.5 * k
    side = k > 0.75
    _turn_swap(p, a, side)
    # blink only while the front face is shown — blink() would otherwise
    # un-hide lids that _turn_swap removed for the profile sprite
    if not side:
        a.blink(p, i / 24.0, period=2.2)
    return p


def p_body_turn(a: Anim, i, n):
    u = i / max(1, n - 1)
    k = math.sin(math.pi * u)
    p = a.base()
    p["torso"]["a"] = -0.18 * k
    p["head"]["a"] = -0.3 * k
    side = k > 0.72
    _turn_swap(p, a, side, side_image_torso="torso_side.png")
    if side:  # far arm/leg tuck behind the side-view body
        p["arm_up_l"]["visible"] = p["arm_lo_l"]["visible"] = False
        p["leg_up_l"]["visible"] = p["leg_lo_l"]["visible"] = False
        p["foot_l"]["visible"] = False
    p["tail"]["a"] = 0.15 * math.sin(TAU * u * 2)
    return p


def p_side_view(a: Anim, i, n):
    """Dedicated profile configuration: side-view head/torso sprites with the
    far-side limbs hidden and the near-side arm/leg repositioned to read in
    profile (not front-view limbs bolted onto a side body)."""
    p = a.base()
    t = i / 24.0
    _turn_swap(p, a, True, side_image_torso="torso_side.png")
    # hide the far-side arm and leg entirely
    for k in ("arm_up_r", "arm_lo_r", "leg_up_r", "leg_lo_r", "foot_r"):
        p[k]["visible"] = False
    # near-side arm hangs straight down against the profile torso
    p["arm_up_l"]["a"] = 0.0
    p["arm_lo_l"]["a"] = -0.12
    # near-side leg tucks under the side body, sole flat on the ground.
    # bend=-1 keeps the shin vertical (the +1 sign rotates it ~horizontal);
    # target 6px ahead of the hip centres the leg under the profile torso.
    gy = a.world(a.rest, "foot_l")[1]
    hip = a.world(p, "root_hip")
    a.pin_foot(p, "leg_up_l", "leg_lo_l", "foot_l",
               (hip[0] + 6, gy), -1.0)
    p["tail"]["a"] = 0.12 * math.sin(TAU * t / 2.2)
    p["head"]["a"] = -0.05
    return p


PRESETS = {
    "idle_breathing": p_idle,
    "walking": p_walk,
    "running": p_run,
    "sitting": p_sit,
    "talking": p_talking,
    "pointing": p_pointing,
    "surprised": p_surprised,
    "angry": p_angry,
    "happy": p_happy,
    "head_turn": p_head_turn,
    "body_turn": p_body_turn,
    "side_view": p_side_view,
}
