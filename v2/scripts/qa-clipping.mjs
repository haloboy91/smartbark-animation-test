/**
 * qa-clipping.mjs — chair-contact / clipping gates for the sit and settle.
 *
 * The dog is painted after the chair, so a chair leg is only a defect if part
 * of it is visible in the gap between the paws (or beside them) rather than
 * occluded by a paw ball. This script tests each chair leg against the paw
 * circles instead of using a flat centerline distance.
 */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import {buildEllyRig} from './elly-rig.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const doc = JSON.parse(readFileSync(join(ROOT, 'animation/elly-v2-walk-turn-sit.styk'), 'utf8'));
const {nodes: N, rig} = buildEllyRig();

const segs = doc.figure_types[0].segments;
const chairSegs = doc.figure_types[1].segments;

function joints(figureSegments, obj) {
  const j = {0: [obj.root_x, obj.root_y]};
  let rem = figureSegments.map((_, i) => i);
  for (let p = 0; rem.length && p < figureSegments.length + 1; p++) {
    const nx = [];
    for (const i of rem) {
      const s = figureSegments[i], par = j[s.parent_id];
      if (!par) { nx.push(i); continue; }
      const useLen = obj.len_flag === 1 && Array.isArray(obj.lengths) && obj.lengths.length;
      const L = (useLen ? obj.lengths[i] : s.length) * (obj.scale ?? 1);
      j[s.segment_id] = [par[0] + L * Math.cos(obj.angles[i]), par[1] + L * Math.sin(obj.angles[i])];
    }
    rem = nx;
  }
  return j;
}

const tipF = rig.segmentIds(N.pawF.visualId).at(-1);
const tipB = rig.segmentIds(N.pawB.visualId).at(-1);
const PAW_R = 16;

// Real chair legs: vertical, solid (thickness >= 8), reaching the floor (y > 410).
// Excludes the zero-thickness contact-shadow stub and the tall backrest posts.
function chairLegs(cj) {
  const seen = new Set();
  const out = [];
  for (const s of chairSegs) {
    const st = cj[s.parent_id], en = cj[s.segment_id];
    if (!st || !en || s.thickness < 8) continue;
    if (Math.abs(en[1] - st[1]) > 60 && Math.abs(en[0] - st[0]) < 4 && Math.max(st[1], en[1]) > 410) {
      const x = Math.round((st[0] + en[0]) / 2);
      if (seen.has(x)) continue; // front/back legs aligned in side view share one silhouette
      seen.add(x);
      out.push({x, yTop: Math.min(st[1], en[1]), yBot: Math.max(st[1], en[1]), half: s.thickness / 2});
    }
  }
  return out;
}

let failures = 0;
const fail = m => { failures++; console.log('  FAIL:', m); };

for (let f = 138; f < 186; f++) {
  const kf = doc.keyframes[f];
  const dog = kf.objects.find(o => o.unique_id === 1);
  const chair = kf.objects.find(o => o.figure_type_id === 2);
  const dj = joints(segs, dog);
  const cj = joints(chairSegs, chair);
  const paws = [dj[tipF], dj[tipB]].map(p => ({x: p[0], y: p[1], r: PAW_R}));
  const [hipX, hipY] = dj[0];
  const seatY = chair.root_y, seatL = chair.root_x - 78, seatR = chair.root_x + 78;

  // hips meet the seat and stay over its footprint
  if (hipX < seatL + 8 || hipX > seatR - 8) fail(`f${f}: hip x=${hipX.toFixed(1)} outside seat ${seatL}..${seatR}`);
  if (hipY < seatY - 6) fail(`f${f}: hip y=${hipY.toFixed(1)} floats >6px above seat ${seatY}`);
  if (hipY > seatY + 14) fail(`f${f}: hip y=${hipY.toFixed(1)} sinks below seat surface`);

  // A leg can only clip if it falls between the two paws (inside their x span);
  // legs outside the dog's footprint are supposed to remain visible.
  const pawMinX = Math.min(...paws.map(p => p.x - p.r));
  const pawMaxX = Math.max(...paws.map(p => p.x + p.r));
  for (const leg of chairLegs(cj)) {
    if (leg.x < pawMinX - 2 || leg.x > pawMaxX + 2) continue;
    // every lower cross-section of an inside leg must be occluded by a paw ball
    for (let y = Math.max(leg.yTop, 404); y <= leg.yBot; y += 2) {
      const covered = paws.some(p => Math.hypot(leg.x - p.x, y - p.y) <= p.r + 1.5);
      if (!covered) { fail(`f${f}: chair leg x=${leg.x} peeks through paw gap at y=${y}`); break; }
    }
  }
}

// approach: nothing reaches into the chair seat footprint before the turn
for (let f = 0; f < 102; f++) {
  const kf = doc.keyframes[f];
  const dog = kf.objects.find(o => o.unique_id === 1);
  const chair = kf.objects.find(o => o.figure_type_id === 2);
  const j = joints(segs, dog);
  const headTip = rig.segmentIds(N.headPivot.visualId).at(-1);
  const rightmost = Math.max(j[0][0], j[tipF][0], j[tipB][0], j[headTip][0]);
  const seatLeft = chair.root_x - 78;
  if (rightmost > seatLeft - 4) { fail(`f${f}: body reaches x=${rightmost.toFixed(1)} into chair seat (edge ${seatLeft})`); break; }
}

console.log(failures === 0 ? '\nCLIPPING QA PASS — chair legs occluded by paws, hips meet the seat, approach stays clear.'
  : `\nCLIPPING QA FAIL — ${failures} issue(s).`);
process.exit(failures === 0 ? 0 : 1);
