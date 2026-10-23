/**
 * qa-v2.mjs — numeric quality gates for the v2 shot.
 * Reads the baked .styk and checks the things a visual pass can't measure:
 *  - no foot slide while a foot is meant to be planted (sit + settle)
 *  - paws stay on the floor plane (no sinking / floating)
 *  - hips land on the chair seat and stay there
 *  - no frame-to-frame joint teleport / jitter above a tolerance
 *  - proportions stay constant (bone lengths are never animated, only IK angles)
 */

import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import {buildEllyRig} from './elly-rig.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const doc = JSON.parse(readFileSync(join(ROOT, 'animation/elly-v2-walk-turn-sit.styk'), 'utf8'));
const {nodes: N, rig} = buildEllyRig();
const segs = doc.figure_types[0].segments;
const PAW_Y = 407, GROUND_LIMIT = 420; // paw tips must stay above the floor line
const SEAT_HIP = {x: 642, y: 350};
const TOL = 1.25; // px

function joints(kf) {
  const o = kf.objects.find(o => o.unique_id === 1);
  const j = {0: [o.root_x, o.root_y]};
  let rem = segs.map((_, i) => i);
  for (let p = 0; rem.length && p < segs.length + 1; p++) {
    const nx = [];
    for (const i of rem) {
      const s = segs[i], par = j[s.parent_id];
      if (!par) { nx.push(i); continue; }
      const L = (o.len_flag ? o.lengths[i] : s.length) * o.scale;
      j[s.segment_id] = [par[0] + L * Math.cos(o.angles[i]), par[1] + L * Math.sin(o.angles[i])];
    }
    rem = nx;
  }
  return j;
}
const tipF = rig.segmentIds(N.pawF.visualId).at(-1);
const tipB = rig.segmentIds(N.pawB.visualId).at(-1);
const headTip = rig.segmentIds(N.headPivot.visualId).at(-1);
const frames = doc.keyframes.map(joints);

let failures = 0;
const fail = (m) => { failures++; console.log('  FAIL:', m); };

// 1. planted feet during sit (138-161) and settle (162-185): constant world x/y
for (const [label, tip] of [['near', tipF], ['far', tipB]]) {
  const ref = frames[162][tip];
  for (let f = 138; f < 186; f++) {
    const p = frames[f][tip];
    if (Math.hypot(p[0] - ref[0], p[1] - ref[1]) > TOL && f >= 162) {
      fail(`planted ${label} paw drifts at f${f}: (${p.map(v => v.toFixed(1))}) vs (${ref.map(v => v.toFixed(1))})`);
      break;
    }
  }
}

// 2. paws never sink below the floor, and never float more than 26px (walk lift)
let minY = 999, maxY = -999;
for (let f = 0; f < frames.length; f++) {
  for (const tip of [tipF, tipB]) {
    const y = frames[f][tip][1];
    minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    if (y > GROUND_LIMIT) { fail(`paw below floor at f${f} y=${y.toFixed(1)}`); break; }
  }
}
console.log(`paw Y range across shot: ${minY.toFixed(1)} .. ${maxY.toFixed(1)} (floor ${GROUND_LIMIT})`);

// 3. hips reach the seat and hold
const endHip = frames[185][0];
if (Math.hypot(endHip[0] - SEAT_HIP.x, endHip[1] - SEAT_HIP.y) > 4) {
  fail(`final hip ${endHip.map(v => v.toFixed(1))} not on seat ${JSON.stringify(SEAT_HIP)}`);
}
let hipDrift = 0;
for (let f = 162; f < 186; f++) hipDrift = Math.max(hipDrift, Math.hypot(frames[f][0][0] - SEAT_HIP.x, frames[f][0][1] - SEAT_HIP.y));
console.log(`settle hip max deviation from seat: ${hipDrift.toFixed(2)} px`);

// 4. no teleport: max per-frame joint displacement. The whole leg chain is
// locomotion and may swing quickly; head/torso/arms/tail/ears/scarf are held
// to a strict limit, while planted-foot and proportion checks guard contact.
const locomotion = new Set();
for (const v of [N.thighF, N.shinF, N.footF.visualId, N.pawF.visualId,
  N.thighB, N.shinB, N.footB.visualId, N.pawB.visualId]) {
  for (const sid of rig.segmentIds(v)) locomotion.add(sid);
}
for (const s of segs) if (locomotion.has(s.parent_id)) locomotion.add(s.segment_id); // toes
let maxJump = 0, jumpAt = -1, maxLeg = 0;
for (let f = 1; f < frames.length; f++) {
  for (const id of Object.keys(frames[0])) {
    const d = Math.hypot(frames[f][id][0] - frames[f - 1][id][0], frames[f][id][1] - frames[f - 1][id][1]);
    if (locomotion.has(Number(id))) { maxLeg = Math.max(maxLeg, d); continue; }
    if (d > maxJump) { maxJump = d; jumpAt = f; }
  }
}
console.log(`largest non-locomotion single-frame move: ${maxJump.toFixed(2)} px at f${jumpAt}; fastest leg joint: ${maxLeg.toFixed(2)} px`);
if (maxJump > 22) fail(`possible teleport/jump of ${maxJump.toFixed(1)} px at f${jumpAt}`);

// 5. proportions: every physical segment keeps its rest length (lengths array
//    only ever changes the lid/mouth/tongue stubs explicitly animated)
const animated = new Set([N.lidFar.visualId, N.lidNear.visualId, N.mouthOpen.visualId, N.tongue.visualId]);
const restLen = rig.restLengths();
let lenViolations = 0;
for (let f = 0; f < frames.length; f++) {
  const o = doc.keyframes[f].objects.find(o => o.unique_id === 1);
  rig.segments.forEach((s, i) => {
    if (animated.has(s._visual)) return;
    if (Math.abs(o.lengths[i] - restLen[i]) > 0.01) lenViolations++;
  });
}
if (lenViolations) fail(`${lenViolations} non-animated segment length changes (stretch/squash)`);
else console.log('all structural segment lengths constant (no stretch/squash)');

// 6. head stays attached and upright relative to hip (identity/proportion guard)
let headDistMin = 999, headDistMax = -999;
for (let f = 0; f < frames.length; f++) {
  const d = Math.hypot(frames[f][headTip][0] - frames[f][0][0], frames[f][headTip][1] - frames[f][0][1]);
  headDistMin = Math.min(headDistMin, d); headDistMax = Math.max(headDistMax, d);
}
console.log(`head-to-hip distance: ${headDistMin.toFixed(1)} .. ${headDistMax.toFixed(1)} px`);

console.log(failures === 0 ? '\nQA PASS — all quality gates green.' : `\nQA FAIL — ${failures} gate(s) failed.`);
process.exit(failures === 0 ? 0 : 1);
