/**
 * cross-check.mjs — evaluate frames through StykAnimate's own geometry engine
 * and compare every joint against the independent FK used by the Python/Canvas
 * previews. Proves the .styk renders identically inside StykAnimate.
 */

import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const APP = process.env.STYK_ANIMATE_HOME || join(ROOT, '../stykanimate');

const {buildGeometry} = await import(join(APP, 'src/pivot/geometry.mjs'));
const {validateSceneSteps} = await import(join(APP, 'src/pivot/model.mjs'));

const doc = JSON.parse(readFileSync(join(ROOT, 'animation/dog-walk-sit-stand.styk'), 'utf8'));
for (const _ of validateSceneSteps(doc, {sliceMs: 1000})) {}

function independentJoints(figure, obj) {
  const segs = figure.segments;
  const joints = new Map([[0, [obj.root_x, obj.root_y]]]);
  let remaining = segs.map((_, i) => i);
  for (let pass = 0; pass < segs.length + 1 && remaining.length; pass++) {
    const next = [];
    for (const i of remaining) {
      const seg = segs[i];
      const parent = joints.get(seg.parent_id);
      if (!parent) { next.push(i); continue; }
      const length = seg.length * (obj.scale ?? 1);
      const a = obj.angles[i];
      joints.set(seg.segment_id, [
        Math.fround(parent[0] + length * Math.cos(a)),
        Math.fround(parent[1] + length * Math.sin(a)),
      ]);
    }
    remaining = next;
  }
  return joints;
}

const types = new Map(doc.figure_types.map(f => [f.figure_type_id, f]));
const checkFrames = [0, 11, 27, 40, 55, 75, 87, 99, 118, 131, 145, 163];
let worst = 0, checked = 0;

for (const fi of checkFrames) {
  const frame = doc.keyframes[fi];
  const geometry = buildGeometry(doc, frame);

  for (const entry of geometry.orderedObjects) {
    const figure = types.get(entry.obj.figure_type_id);
    const mine = independentJoints(figure, entry.obj);
    if (mine.size !== entry.joints.size) {
      throw new Error(`frame ${fi} uid ${entry.obj.unique_id}: joint count ${mine.size} vs ${entry.joints.size}`);
    }
    for (const [id, point] of entry.joints) {
      const ref = mine.get(id);
      if (!ref) throw new Error(`frame ${fi}: missing joint ${id}`);
      const dx = Math.abs(point.x - ref[0]);
      const dy = Math.abs(point.y - ref[1]);
      worst = Math.max(worst, dx, dy);
      if (dx > 0.05 || dy > 0.05) {
        throw new Error(`frame ${fi} uid ${entry.obj.unique_id} joint ${id}: app=(${point.x},${point.y}) preview=(${ref[0]},${ref[1]})`);
      }
      checked++;
    }
  }
}
console.log(`cross-check OK: ${checked} joints over ${checkFrames.length} frames × 3 figures, worst delta ${worst.toExponential(2)}px`);
