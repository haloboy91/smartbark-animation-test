/**
 * ik.mjs — analytic two-bone inverse kinematics, matching the approach
 * documented in StykAnimate (docs/inverse-kinematics.md): law-of-cosines
 * solve with an explicit bend direction, reach clamping and no stretch.
 *
 * Solutions are baked into absolute segment angles at authoring time, which
 * is exactly what StykAnimate does on "unpin/disable IK", so the resulting
 * .styk renders identically in the app, the browser preview and Pillow.
 */

const {sqrt, atan2, cos, sin, acos, PI} = Math;

/**
 * Solve a two-bone chain.
 *
 * @param {{x:number,y:number}} root   world position of the chain root (hip/shoulder)
 * @param {{x:number,y:number}} target world position of the end effector (ankle/wrist)
 * @param {number} l1 first bone length
 * @param {number} l2 second bone length
 * @param {number} bend +1 / -1 selects the knee/elbow side
 * @returns {{a1:number, a2:number, knee:{x:number,y:number}, reach:number}}
 *          a1, a2 are ABSOLUTE world angles of the two bones.
 */
export function solveTwoBoneIK(root, target, l1, l2, bend = 1) {
  let dx = target.x - root.x;
  let dy = target.y - root.y;
  let d = sqrt(dx * dx + dy * dy);
  const maxReach = l1 + l2 - 1e-4;
  const minReach = Math.abs(l1 - l2) + 1e-4;
  const clamped = Math.min(maxReach, Math.max(minReach, d));
  if (d > 1e-6) {
    const k = clamped / d;
    dx *= k; dy *= k; d = clamped;
  }
  const base = atan2(dy, dx);
  const cosKnee = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d);
  const kneeOffset = acos(Math.min(1, Math.max(-1, cosKnee)));
  const a1 = base + bend * kneeOffset;
  const knee = {x: root.x + l1 * cos(a1), y: root.y + l1 * sin(a1)};
  const a2 = atan2(target.y - knee.y, target.x - knee.x);
  return {a1, a2, knee, reach: d};
}

/** Shortest signed angular difference a - b in (-PI, PI]. */
export function angleDelta(a, b) {
  let d = a - b;
  while (d > PI) d -= 2 * PI;
  while (d <= -PI) d += 2 * PI;
  return d;
}

/** Frame-rate independent ease factor for critically-damped smoothing. */
export function damp(current, target, lambda, dt) {
  return current + (target - current) * (1 - Math.exp(-lambda * dt));
}

/**
 * Walk-cycle footstep planner. Given a moving hip track and a step length,
 * emits stance/swing targets so stance feet stay pinned to one world point
 * (zero slide) and swing feet follow a lifted arc to the next contact.
 */
export function planFootsteps({startX, endX, hipY, footY, stepLength, framesPerStep, phaseOffset = 0, lift = 26}) {
  const targets = [];
  const steps = Math.max(1, Math.round(Math.abs(endX - startX) / stepLength));
  const totalFrames = steps * framesPerStep;
  const contacts = [];
  for (let i = 0; i <= steps + 1; i++) contacts.push(startX + Math.sign(endX - startX) * i * stepLength);
  for (let f = 0; f < totalFrames; f++) {
    const cycle = (f + phaseOffset) / framesPerStep;
    const i0 = Math.floor(cycle);
    const t = cycle - i0;
    const from = contacts[Math.min(i0, contacts.length - 1)];
    const to = contacts[Math.min(i0 + 1, contacts.length - 1)];
    let x, y;
    if (t < 0.62) {
      // stance: planted (the hip travels over the fixed foot)
      x = to; y = footY;
    } else {
      // swing: eased arc from old contact to new
      const u = (t - 0.62) / 0.38;
      const e = u * u * (3 - 2 * u);
      x = from + (to - from) * e;
      y = footY - lift * Math.sin(Math.PI * e);
    }
    targets.push({x, y, grounded: t < 0.62});
  }
  return {targets, totalFrames};
}
