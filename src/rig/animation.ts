/**
 * Pure, dependency-free animation math for Elly's 12-second coin scene.
 *
 * Everything is expressed as plain functions of time so the exact same
 * keyframes can be ported 1:1 to the headless Python renderer (the sandbox
 * has no browser). The Motion Canvas scene simply feeds `poseAt(clock)` into
 * the rig's signals; articulation never touches global placement.
 */
import type {MouthShape} from './ellyRig';

export const SCENE_DURATION = 12;

// --- rig geometry (must match ellyRig.tsx / rig-manifest.json) -------------
const HIPS = {x: 0, y: 172};
const WAIST = {x: 0, y: 232};
const SHOULDER_R = {x: 310, y: 542}; // right shoulder, rig frame
// Fingertip offset inside its shoulder joint at armR = 0 (native art measured).
const HAND_TIP = {x: 327, y: 211};
const TIP_LEN = Math.hypot(HAND_TIP.x, HAND_TIP.y);
const ARM_R_HANG = -128; // degrees: rotate the raised reference arm to hang
const COIN_GROUND = {x: 250, y: 34}; // where the coin lies, root rig space
const COIN_EXAMINE = {x: 450, y: 800}; // palm hold near the face while examining

export interface RigState {
  rootX: number;
  rootY: number;
  rootScale: number;
  rootRotation: number;
  legL: number;
  legR: number;
  flexL: number;
  flexR: number;
  spine: number;
  head: number;
  armL: number;
  armR: number;
  /** Cartoon stretch of the reaching arm (1 = natural art size). */
  armScale: number;
  earL: number;
  earR: number;
  tail: number;
  blink: number;
  gazeX: number;
  gazeY: number;
  browLift: number;
  mouth: MouthShape;
  mouthOpen: number;
  cameraZoom: number;
  coin: {
    visible: boolean;
    attached: boolean;
    x: number;
    y: number;
    scale: number;
    spin: number;
  };
}

// --- tiny math helpers ------------------------------------------------------
const TAU = Math.PI * 2;
const rad = (deg: number) => (deg * Math.PI) / 180;
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const easeInOut = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 2.2);
const seg = (t: number, a: number, b: number) => clamp((t - a) / (b - a), 0, 1);

function rot(x: number, y: number, deg: number) {
  const c = Math.cos(rad(deg));
  const s = Math.sin(rad(deg));
  return {x: x * c - y * s, y: x * s + y * c};
}

/** World position of the right shoulder pivot in root rig coordinates. */
export function shoulderR(spine: number) {
  const waistToShoulder = {
    x: SHOULDER_R.x - WAIST.x,
    y: SHOULDER_R.y - WAIST.y,
  };
  return {
    x: HIPS.x + rot(WAIST.x - HIPS.x, WAIST.y - HIPS.y, spine).x +
      rot(waistToShoulder.x, waistToShoulder.y, spine).x,
    y: HIPS.y + rot(WAIST.x - HIPS.x, WAIST.y - HIPS.y, spine).y +
      rot(waistToShoulder.x, waistToShoulder.y, spine).y,
  };
}

/** Forward kinematics: fingertip position in root rig coordinates. */
export function rightHand(s: Pick<RigState, 'spine' | 'armR' | 'armScale'>) {
  // The arm node visually rotates by spine + armR (it inherits the waist bend).
  const shoulder = shoulderR(s.spine);
  const h = rot(HAND_TIP.x, HAND_TIP.y, s.spine + s.armR);
  return {
    x: shoulder.x + h.x * s.armScale,
    y: shoulder.y + h.y * s.armScale,
  };
}

// Measured glove-palm offset from the fingertip, in arm-local coordinates.
const PALM_OFFSET = {x: -89, y: -58};

/** Palm position (where a carried object rests), root rig coordinates. */
export function rightPalm(s: Pick<RigState, 'spine' | 'armR' | 'armScale'>) {
  const shoulder = shoulderR(s.spine);
  const p = rot(
    HAND_TIP.x + PALM_OFFSET.x,
    HAND_TIP.y + PALM_OFFSET.y,
    s.spine + s.armR,
  );
  return {
    x: shoulder.x + p.x * s.armScale,
    y: shoulder.y + p.y * s.armScale,
  };
}

const PALM_LOCAL = {
  x: HAND_TIP.x + PALM_OFFSET.x,
  y: HAND_TIP.y + PALM_OFFSET.y,
};
const PALM_LEN = Math.hypot(PALM_LOCAL.x, PALM_LOCAL.y);

/** Solve armR + stretch so the palm lands on a root-space target. */
function palmReach(target: {x: number; y: number}, spine: number) {
  const shoulder = shoulderR(spine);
  const dist = Math.hypot(target.x - shoulder.x, target.y - shoulder.y);
  const scale = clamp(dist / PALM_LEN, 1, 1.9);
  const restAngle = Math.atan2(PALM_LOCAL.y, PALM_LOCAL.x);
  const total =
    Math.atan2(target.y - shoulder.y, target.x - shoulder.x) - restAngle;
  return {angle: (total * 180) / Math.PI - spine, scale};
}

/**
 * Solve armR angle + cartoon stretch so the fingertip touches a target.
 * Scale is clamped so the flat arm never stretches beyond 1.9x.
 */
function reach(target: {x: number; y: number}, spine: number) {
  const shoulder = shoulderR(spine);
  const dist = Math.hypot(target.x - shoulder.x, target.y - shoulder.y);
  const scale = clamp(dist / TIP_LEN, 1, 1.9);
  const restAngle = Math.atan2(HAND_TIP.y, HAND_TIP.x);
  const total =
    Math.atan2(target.y - shoulder.y, target.x - shoulder.x) - restAngle;
  return {angle: (total * 180) / Math.PI - spine, scale};
}

function blinkPulse(t: number, center: number, width = 0.16) {
  const d = Math.abs(t - center);
  return d > width ? 0 : Math.cos((d / width) * (Math.PI / 2));
}

// --- the timeline -----------------------------------------------------------
/** Root x of the eased walk at step-coordinate u (4 steps over 3 s). */
function bodyX(u: number) {
  return lerp(-720, 0, easeInOut(clamp(u / 4, 0, 1)));
}

/**
 * Footprint walk cycle. A planted foot keeps a constant WORLD x while the
 * body travels over it; a foot only moves while airborne (swing), so there
 * is no foot sliding. Returns leg angles, flex and counter-swing arm angles.
 */
function walkPose(t: number) {
  const u = t / 0.75;
  const j = Math.min(Math.floor(u), 3);
  const frac = clamp(u - j, 0, 1);
  const rx = bodyX(u);
  const hipR = rx + 170;
  const hipL = rx - 220;
  const printsR = [bodyX(0) + 170, bodyX(2) + 170, bodyX(4) + 170];
  const printsL = [bodyX(1) - 220, bodyX(3) - 220];

  const target = (foot: 'R' | 'L'): {x: number; airborne: boolean} => {
    if (foot === 'R') {
      if (j === 0 || j === 2) return {x: printsR[j / 2], airborne: false};
      const k = (j - 1) / 2;
      return {x: lerp(printsR[k], printsR[k + 1], easeInOut(frac)), airborne: true};
    }
    if (j === 1 || j === 3) {
      return {x: printsL[(j - 1) / 2], airborne: false};
    }
    if (j === 0) {
      // Entry: left foot starts under its hip and steps onto its first print.
      return {x: lerp(bodyX(0) - 220, printsL[0], easeInOut(frac)), airborne: true};
    }
    return {x: lerp(printsL[0], printsL[1], easeInOut(frac)), airborne: true};
  };

  const leg = (foot: 'R' | 'L', hip: number) => {
    const g = target(foot);
    const dx = clamp(g.x - hip, -160, 160);
    const angle = (Math.atan2(dx, 165) * 180) / Math.PI;
    const flex = g.airborne
      ? 1 - 0.24 * Math.sin(Math.PI * frac)
      : Math.abs(g.x - hip) > 150
        ? 0.95
        : 1;
    return {angle, flex};
  };

  const r = leg('R', hipR);
  const l = leg('L', hipL);
  return {legR: r.angle, legL: l.angle, flexR: r.flex, flexL: l.flex};
}

export function poseAt(t: number): RigState {
  const s: RigState = {
    rootX: 0, rootY: -450, rootScale: 0.57, rootRotation: 0,
    legL: 0, legR: 0, flexL: 1, flexR: 1,
    spine: 0, head: 0, armL: 0, armR: ARM_R_HANG, armScale: 1,
    earL: 0, earR: 0, tail: 0,
    blink: 0, gazeX: 0, gazeY: 0, browLift: 0,
    mouth: 'open', mouthOpen: 0.85,
    cameraZoom: 1,
    coin: {visible: false, attached: false, x: COIN_GROUND.x, y: COIN_GROUND.y, scale: 1, spin: 0},
  };

  // Blinks happen at fixed story moments.
  s.blink = Math.max(
    blinkPulse(t, 3.35),
    blinkPulse(t, 8.75),
    blinkPulse(t, 11.55, 0.13),
  );

  /* ---------------- 0–3 s: four visible walking steps ---------------- */
  if (t < 3) {
    const period = 0.75; // 4 steps in 3 s
    const phase = t / period;
    s.rootX = bodyX(phase);
    const wp = walkPose(t);
    s.legR = wp.legR;
    s.legL = wp.legL;
    s.flexR = wp.flexR;
    s.flexL = wp.flexL;
    // Arms counter-swing against the same-side legs.
    s.armL = -0.6 * wp.legL;
    s.armR = ARM_R_HANG - 0.6 * wp.legR;
    const wave = Math.sin(TAU * phase);
    s.spine = -3.5 * wave;
    s.head = -0.35 * s.spine;
    s.earL = 7 * Math.sin(TAU * phase + 0.7);
    s.earR = 6 * Math.sin(TAU * phase + 0.7);
    s.tail = 9 * Math.sin(TAU * phase - 0.9);
    // Body rises on each weight transfer; head stays comparatively stable.
    s.rootY = -450 + 7 * (0.5 - 0.5 * Math.cos(TAU * phase));
    s.mouth = 'open';
    s.mouthOpen = 0.85;
  }

  /* ---------------- 3–5 s: stop, plant feet, look down --------------- */
  if (t >= 3 && t < 5) {
    const q = easeInOut(seg(t, 3, 3.5));
    s.legL = lerp(s.legL, 0, q);
    s.legR = lerp(s.legR, 0, q);
    s.armL = lerp(s.armL, 0, q);
    s.armR = lerp(s.armR, ARM_R_HANG, q);
    s.spine = lerp(s.spine, 0, q);
    s.tail = lerp(s.tail, 0, q);
    const look = easeInOut(seg(t, 3.6, 4.6));
    s.head = lerp(0, -20, look);
    s.gazeY = lerp(0, -16, look);
    s.gazeX = lerp(0, 10, look);
    s.mouth = 'small';
  }

  /* ---------------- 5–8 s: notice and pick up the coin --------------- */
  if (t >= 5) {
    s.coin.visible = true;
    s.coin.spin = TAU * 1.5 * seg(t, 5, 6.4);
  }
  if (t >= 5 && t < 8) {
    // Eyes lock onto the coin first.
    const gazeQ = easeOutCubic(seg(t, 5, 5.7));
    s.gazeX = lerp(10, 26, gazeQ);
    s.gazeY = lerp(-16, -22, gazeQ);
    s.head = lerp(-20, -28, easeInOut(seg(t, 5, 5.8)));
    s.browLift = 0.25;

    // Bend: spine forward, knees flex, then reach with the right arm.
    const bend = easeInOut(seg(t, 5.5, 6.5));
    const rise = easeInOut(seg(t, 6.7, 7.8));
    const bendAmount = bend * (1 - rise);
    s.spine = 34 * bendAmount;
    s.flexL = 1 - 0.22 * bendAmount;
    s.flexR = 1 - 0.22 * bendAmount;
    s.legL = -7 * bendAmount;
    s.legR = 7 * bendAmount;
    s.rootY = -450 - 55 * bendAmount;
    // Arm reaches the coin by t≈6.6 (fingertip contact), holds, then carries
    // it up while standing, ending with the coin resting in the palm.
    if (t < 6.6) {
      const reachQ = easeInOut(seg(t, 5.7, 6.6));
      const goal = reach(COIN_GROUND, s.spine);
      s.armR = lerp(ARM_R_HANG, goal.angle, reachQ);
      s.armScale = lerp(1, goal.scale, reachQ);
    } else if (t < 6.9) {
      const goal = reach(COIN_GROUND, s.spine);
      s.armR = goal.angle;
      s.armScale = goal.scale;
    } else {
      const carryQ = easeInOut(seg(t, 6.9, 7.8));
      const onGround = reach(COIN_GROUND, s.spine);
      const held = palmReach(COIN_EXAMINE, s.spine);
      s.armR = lerp(onGround.angle, held.angle, carryQ);
      s.armScale = lerp(onGround.scale, held.scale, carryQ);
    }
    s.mouth = 'small';

    // Coin: ground until contact, snaps to the fingertip, then settles into
    // the palm as the arm rises.
    if (t >= 6.6) {
      s.coin.attached = true;
      const tip = rightHand(s);
      if (t < 6.9) {
        const follow = easeOutCubic(seg(t, 6.6, 6.9));
        s.coin.x = lerp(COIN_GROUND.x, tip.x, follow);
        s.coin.y = lerp(COIN_GROUND.y, tip.y, follow);
      } else {
        const palm = rightPalm(s);
        const settle = easeInOut(seg(t, 6.9, 7.2));
        s.coin.x = lerp(tip.x, palm.x, settle);
        s.coin.y = lerp(tip.y, palm.y, settle);
      }
    }
  }

  /* ---------------- 8–10 s: examine, blink, exaggerated surprise ------ */
  if (t >= 8 && t < 10) {
    // Hold the coin up near the face and look at it.
    const holdQ = easeInOut(seg(t, 8, 8.4));
    const held = palmReach(COIN_EXAMINE, 0);
    s.armR = lerp(s.armR, held.angle, holdQ);
    s.armScale = lerp(s.armScale, held.scale, holdQ);
    s.spine = lerp(s.spine, 0, holdQ);
    s.flexL = s.flexR = 1;
    s.legL = s.legR = 0;
    s.head = lerp(s.head, -6, holdQ);
    s.gazeX = 22;
    s.gazeY = 6;
    s.mouth = 'small';
    s.coin.attached = true;

    // Surprise hit at 9.0 s.
    const hit = seg(t, 9, 9.25);
    if (t >= 9) {
      const q = easeOutCubic(hit);
      s.browLift = lerp(0.25, 1, q);
      s.head = lerp(-6, -14, q);
      s.mouth = 'oh';
      s.mouthOpen = lerp(0.2, 1, q);
      s.gazeX = 6;
      s.gazeY = 10;
      s.earL = s.earR = 3 * q;
      // Whole-body take: quick stretch, then settle.
      const stretch = Math.sin(Math.PI * seg(t, 9, 9.5));
      s.rootY = -450 + 26 * stretch;
      s.rootScale = 0.57 * (1 + 0.05 * stretch);
      s.spine = -5 * stretch;
    }
    // Coin follows the final palm pose of the frame (after the take).
    const palm = rightPalm(s);
    s.coin.x = palm.x;
    s.coin.y = palm.y;
  }

  /* ---------------- 10–12 s: coin vanishes, freeze, look at camera ---- */
  if (t >= 10) {
    // Coin pops out of existence in the first 0.15 s.
    const vanish = seg(t, 10, 10.15);
    s.coin.visible = vanish < 1;
    s.coin.attached = true;
    const palm = rightPalm(s);
    s.coin.x = palm.x;
    s.coin.y = palm.y;
    s.coin.scale = 1 - vanish;

    // Freeze: damp every joint to stillness, neutral worried face.
    const freeze = easeInOut(seg(t, 10, 10.4));
    s.armR = lerp(s.armR, ARM_R_HANG + 6, freeze);
    s.armScale = lerp(s.armScale, 1, freeze);
    s.head = lerp(s.head, -8, freeze);
    s.browLift = lerp(s.browLift, 0.55, freeze);
    s.mouth = 'flat';
    s.mouthOpen = 1;
    s.rootY = lerp(s.rootY, -450, freeze);
    s.rootScale = lerp(s.rootScale, 0.57, freeze);
    s.spine = lerp(s.spine, 0, freeze);
    s.earL = s.earR = 0;
    s.gazeX = lerp(6, 22, freeze);
    s.gazeY = lerp(10, -14, freeze);

    // Glance at the empty hand...
    const glance = easeInOut(seg(t, 10.5, 11.1));
    s.head = lerp(-8, 14, glance);
    s.gazeX = lerp(22, 30, glance);
    s.gazeY = lerp(-14, -6, glance);

    // ...then turn to the camera and hold the joke.
    const toCam = easeInOut(seg(t, 11.2, 11.7));
    s.head = lerp(14, 0, toCam);
    s.gazeX = lerp(30, 0, toCam);
    s.gazeY = lerp(-6, 2, toCam);
    s.mouth = t > 11.5 ? 'small' : 'flat';
  }

  // Gentle camera push-in across the whole scene.
  s.cameraZoom = lerp(1.0, 1.06, easeInOut(seg(t, 0, SCENE_DURATION)));
  return s;
}
