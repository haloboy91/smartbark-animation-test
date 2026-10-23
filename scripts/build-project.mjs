/**
 * build-project.mjs — assembles the StykAnimate project "Elly walks to the
 * table, sits down and stands up".
 *
 * Outputs (in animation/):
 *   dog-walk-sit-stand.styk  plain-JSON StykAnimate project (opens directly,
 *                            no backend/codec needed)
 *   smartbark-dog.stk        Pivot v5 figure file for the dog
 *   table.stk / room.stk     Pivot v5 figure files for the props
 *
 * Every animation frame is authored explicitly (duration_raw = 1), which is
 * the classic Pivot workflow: no interpolation settings are relied upon.
 */

import {writeFileSync, mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import {Rig, writeStk} from './styk-rig.mjs';
import {buildDogRig} from './dog-rig.mjs';
import {buildTableRig, buildRoomRig} from './scene-rig.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'animation');
mkdirSync(OUT, {recursive: true});

const PI = Math.PI;
const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = t => Math.min(1, Math.max(0, t));
const easeInOut = t => (t < 0.5 ? 2 * t * t : 1 - ((-2 * t + 2) ** 2) / 2);
const easeOut = t => 1 - (1 - t) ** 2;

// ---------------------------------------------------------------- figures ---
const {rig: dogRig, nodes: N, groups} = buildDogRig();
const {rig: tableRig} = buildTableRig();
const {rig: roomRig} = buildRoomRig();

const dogFigure = dogRig.figure(1, 'Elly the dog');
const tableFigure = tableRig.figure(2, 'Table');
const roomFigure = roomRig.figure(3, 'Room');

// Visual-id rest angle maps (covers bones, stubs and balls).
const restMap = new Map();
for (const [id, node] of dogRig.nodes) restMap.set(id, node.restAngle);
const tableRest = new Map();
for (const [id, node] of tableRig.nodes) tableRest.set(id, node.restAngle);
const roomRest = new Map();
for (const [id, node] of roomRig.nodes) roomRest.set(id, node.restAngle);

const clone = m => new Map(m);
const blend = (a, b, t) => {
  const out = new Map();
  for (const k of new Set([...a.keys(), ...b.keys()])) {
    const av = a.get(k), bv = b.get(k);
    out.set(k, av === undefined ? bv : bv === undefined ? av : lerp(av, bv, t));
  }
  return out;
};
const tiltHead = (map, delta) => {
  for (const id of groups.head) map.set(id, (map.get(id) ?? restMap.get(id) ?? 0) + delta);
};

// ------------------------------------------------------------- pose states ---
function walkPose(p) {
  const m = clone(restMap);
  const s = Math.sin(p);
  const lift = Math.sin(p - 0.9);
  // hind legs: opposite swings, knee flex on the lift phase
  m.set(N.thighF, 1.16 + 0.45 * s);
  m.set(N.shinF, m.get(N.thighF) + 0.18 + 0.55 * Math.max(0, lift) ** 1.2);
  m.set(N.footF.visualId, m.get(N.shinF) + 0.12);
  m.set(N.thighB, 2.0 - 0.45 * s);
  m.set(N.shinB, m.get(N.thighB) - 0.18 - 0.45 * Math.max(0, -lift) ** 1.2);
  m.set(N.footB.visualId, m.get(N.shinB) - 0.1);
  // arms counter-swing
  m.set(N.armF1, 1.02 - 0.38 * s);
  m.set(N.armF2, m.get(N.armF1) + 0.26 + 0.08 * s);
  m.set(N.armB1, 2.1 + 0.38 * s);
  m.set(N.armB2, m.get(N.armB1) - 0.28);
  // tail + ear sway, gentle head bob
  m.set(N.tail1, 2.9 + 0.14 * s);
  m.set(N.tail2, -2.8 + 0.1 * s);
  m.set(N.tail3, -2.3 + 0.08 * s);
  m.set(N.earF, 1.04 + 0.07 * s);
  tiltHead(m, 0.045 * Math.sin(p + 0.6));
  return m;
}

function sitPose() {
  const m = clone(restMap);
  // folded hind legs: haunches down, knees forward, paws out front
  m.set(N.thighF, 0.4);
  m.set(N.shinF, 2.55);
  m.set(N.footF.visualId, 2.2);
  m.set(N.thighB, 2.85);
  m.set(N.shinB, 2.2);
  m.set(N.footB.visualId, 2.0);
  // slight recline, paws resting toward the lap
  m.set(N.chest, -PI / 2 + 0.16);
  m.set(N.armF1, 0.85);
  m.set(N.armF2, 1.55);
  m.set(N.armB1, 2.3);
  m.set(N.armB2, 2.0);
  // tail curled behind
  m.set(N.tail1, 2.55);
  m.set(N.tail2, -2.45);
  m.set(N.tail3, -1.95);
  return m;
}

function leanForwardPose() {
  const m = sitPose();
  m.set(N.chest, -PI / 2 - 0.14); // anticipation: nose over toes
  m.set(N.armF1, 0.95);
  m.set(N.armF2, 1.35);
  tiltHead(m, -0.06);
  return m;
}

function idlePose(globalIndex) {
  const m = clone(restMap);
  const breath = Math.sin(globalIndex * 0.22);
  m.set(N.chest, -PI / 2 + 0.015 * breath);
  m.set(N.tail1, 2.9 + 0.05 * breath);
  m.set(N.tail2, -2.8 + 0.04 * breath);
  tiltHead(m, 0.02 * Math.sin(globalIndex * 0.18));
  return m;
}

// ------------------------------------------------------------- scene layout ---
const CANVAS_W = 960, CANVAS_H = 540, FPS = 24;
const GROUND_Y = 432;
const HIP_Y = 344;            // standing hip height (root node 0 of the dog)
const START_X = 150;          // dog starts screen-left
const END_X = 545;            // dog stops just in front of the table
const SIT_X = 535;
const SIT_Y = 375;            // hips drop when sitting
const TABLE_X = 800, TABLE_Y = 300;
const ROOM_X = 480;

// -------------------------------------------------------------- timeline -----
const phases = [
  {name: 'idle', frames: 12},
  {name: 'walk', frames: 64},
  {name: 'settle', frames: 12},
  {name: 'sit', frames: 20},
  {name: 'sitHold', frames: 22},
  {name: 'anticipate', frames: 4},
  {name: 'stand', frames: 18},
  {name: 'idle2', frames: 12},
];

function frameSpec(globalIndex, phase, local, span) {
  const t = span <= 1 ? 1 : local / (span - 1);
  switch (phase) {
    case 'idle':
    case 'idle2':
      return {map: idlePose(globalIndex), x: phase === 'idle' ? START_X : END_X, y: HIP_Y};
    case 'walk': {
      const p = (local / 24) * PI * 2;
      const progress = easeOut(clamp01(local / (span - 1)));
      return {
        map: walkPose(p),
        x: lerp(START_X, END_X, progress),
        y: HIP_Y - 3.5 * Math.abs(Math.sin(p)),
      };
    }
    case 'settle': {
      const p = ((span - 1) / 24) * PI * 2;
      return {
        map: blend(walkPose(p), restMap, easeInOut(t)),
        x: lerp(END_X, SIT_X, t),
        y: lerp(HIP_Y - 3.5 * Math.abs(Math.sin(p)), HIP_Y, t),
      };
    }
    case 'sit': {
      const e = easeInOut(t);
      return {map: blend(restMap, sitPose(), e), x: lerp(END_X, SIT_X, e), y: lerp(HIP_Y, SIT_Y, e)};
    }
    case 'sitHold': {
      const m = sitPose();
      const breath = Math.sin(local * 0.3);
      m.set(N.chest, -PI / 2 + 0.16 + 0.012 * breath);
      m.set(N.tail1, 2.55 + 0.05 * breath);
      tiltHead(m, 0.03 * Math.sin(local * 0.2));
      m.set(N.earF, 1.04 + 0.05 * breath);
      return {map: m, x: SIT_X, y: SIT_Y};
    }
    case 'anticipate':
      return {map: blend(sitPose(), leanForwardPose(), easeInOut(t)), x: SIT_X, y: SIT_Y};
    case 'stand': {
      const e = easeInOut(t);
      return {map: blend(leanForwardPose(), restMap, e), x: lerp(SIT_X, END_X, e), y: lerp(SIT_Y, HIP_Y, e)};
    }
  }
}

function makeObject(uid, figure, rig, rest, x, y, map) {
  return {
    object_slot: 0,
    unique_id: uid,
    figure_type_id: figure.figure_type_id,
    root_x: x,
    root_y: y,
    scale: 1,
    color_override_raw: 0,
    field28: 0,
    angles: rig.poseAngles(map ?? rest),
    len_flag: 0,
    lengths: [],
    bend_flag: 0,
    bends: [],
    join: null,
  };
}

const keyframes = [];
let globalIndex = 0;
for (const phase of phases) {
  for (let local = 0; local < phase.frames; local++) {
    const spec = frameSpec(globalIndex, phase.name, local, phase.frames);
    const roomObj = makeObject(3, roomFigure, roomRig, roomRest, ROOM_X, GROUND_Y, roomRest);
    const tableObj = makeObject(2, tableFigure, tableRig, tableRest, TABLE_X, TABLE_Y, tableRest);
    const dogObj = makeObject(1, dogFigure, dogRig, restMap, spec.x, spec.y, spec.map);
    keyframes.push({
      duration_raw: 1,
      background_id: 0,
      background_id_b: 0,
      background_mix: 0,
      camera: {is_default: true, x: 0, y: 0, scale: 1, angle_rad: 0},
      objects: [roomObj, tableObj, dogObj],
      object_draw_order: [0, 1, 2],
      object_draw_order_unique_ids: [3, 2, 1],
      _styk: {easing: {interpolation: 'hold'}},
    });
    globalIndex++;
  }
}

const document_ = {
  version: 5,
  canvas_width: CANVAS_W,
  canvas_height: CANVAS_H,
  fps: FPS,
  auto_easing: false,
  auto_easing_disabled_raw: 1,
  auto_easing_source: 'file',
  backgrounds: [],
  figure_types: [dogFigure, tableFigure, roomFigure],
  keyframes,
  _styk: {format: 'StykAnimate', format_version: 1, name: 'Elly — walk to table, sit and stand'},
};

writeFileSync(join(OUT, 'dog-walk-sit-stand.styk'), JSON.stringify(document_));
writeFileSync(join(OUT, 'smartbark-dog.stk'), writeStk(dogFigure));
writeFileSync(join(OUT, 'table.stk'), writeStk(tableFigure));
writeFileSync(join(OUT, 'room.stk'), writeStk(roomFigure));

// Self-contained browser preview data (plain <script> assignment works from file://)
const previewDir = join(ROOT, 'preview');
mkdirSync(previewDir, {recursive: true});
writeFileSync(
  join(previewDir, 'project-data.js'),
  `// Auto-generated by scripts/build-project.mjs — do not edit by hand.\n` +
  `window.SMARTBARK_PROJECT = ${JSON.stringify(document_)};\n`,
);

console.log(`Wrote ${keyframes.length} frames (~${(keyframes.length / FPS).toFixed(1)}s)`);
console.log(`Figures: dog=${dogFigure.segment_count} segments, table=${tableFigure.segment_count}, room=${roomFigure.segment_count}`);
console.log('Outputs in', OUT);
