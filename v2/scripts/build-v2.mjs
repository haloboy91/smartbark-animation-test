/**
 * build-v2.mjs — "Elly walks to the chair, turns, sits and settles".
 *
 * 186 frames @ 24 fps (7.75 s), static camera, explicit held keyframes.
 * Legs are solved with analytic two-bone IK against world-space foot targets:
 * stance feet stay pinned (zero slide), swing feet follow lifted arcs. The
 * solved angles are baked into each frame, as StykAnimate does when IK is
 * unpinned, so every renderer shares one result.
 *
 * Phases: idle(12) walk(80) stop(10) turn(26) backup(10) sit(24) settle(24)
 */

import {writeFileSync, mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import {Rig, writeStk} from './styk-rig.mjs';
import {buildEllyRig, buildShadowRig} from './elly-rig.mjs';
import {buildChairRig, buildRoomRig} from './chair-rig.mjs';
import {solveTwoBoneIK} from './ik.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'animation');
mkdirSync(OUT, {recursive: true});
const PI = Math.PI;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const smooth = t => t * t * (3 - 2 * t);
const easeInOut = t => (t < 0.5 ? 2 * t * t : 1 - ((-2 * t + 2) ** 2) / 2);
const norm = a => { while (a > PI) a -= 2 * PI; while (a <= -PI) a += 2 * PI; return a; };
const mirror = a => norm(PI - a);
const lerp = (a, b, t) => a + (b - a) * t;
/** shortest-path angular lerp, so a limb never spins the long way around. */
const angLerp = (a, b, t) => { let d = norm(b - a); return norm(a + d * t); };

// ------------------------------------------------------------------ rigs ----
const {rig, nodes: N, groups} = buildEllyRig();
const {rig: chairRig} = buildChairRig();
const {rig: roomRig} = buildRoomRig();
const shadowRig = buildShadowRig();

const ellyFig = rig.figure(1, 'Elly');
const chairFig = chairRig.figure(2, 'Chair');
const roomFig = roomRig.figure(3, 'Room');
const shadowFig = shadowRig.figure(4, 'Elly shadow');

const restMap = new Map();
for (const [id, node] of rig.nodes) restMap.set(id, node.restAngle);
const chairRest = new Map([...chairRig.nodes].map(([id, n]) => [id, n.restAngle]));
const roomRest = new Map([...roomRig.nodes].map(([id, n]) => [id, n.restAngle]));
const restLengths = rig.restLengths();
const segIndex = new Map(); // segment_id -> array index
rig.segments.forEach((s, i) => segIndex.set(s.segment_id, i));

// Face/head visuals that must flip through a downward bow during the turn
const faceIds = groups.head;
const rightRest = new Map(faceIds.map(id => [id, restMap.get(id)]));
const leftRest = new Map(faceIds.map(id => [id, mirror(restMap.get(id))]));
// tail + scarf flip sides too
for (const id of [N.tail1, N.tail2, N.scarfTail, N.scarf, N.tailPom.visualId]) {
  rightRest.set(id, restMap.get(id));
  leftRest.set(id, mirror(restMap.get(id)));
}

// ------------------------------------------------------------- layout -------
const GROUND_Y = 432, PAW_Y = 407, HIP_Y = 342;
const WALK_START = 120, WALK_END = 556;
const SEAT_HIP = {x: 642, y: 350};       // hips settle into the chair seat
const CHAIR = {x: 706, y: 344};
const ROOM = {x: 480, y: GROUND_Y};
const THIGH_L = 38, SHIN_L = 38, ARM1_L = 34, ARM2_L = 30;

const phases = [
  ['idle', 12], ['walk', 80], ['stop', 10], ['turn', 26],
  ['backup', 10], ['sit', 24], ['settle', 24],
]; // 186 frames = 7.75 s
const phaseAt = f => {
  let start = 0;
  for (const [name, len] of phases) { if (f < start + len) return {name, u: (f - start) / len, start}; start += len; }
  return {name: 'settle', u: 1, start: 162};
};

// ------------------------------------------------------- walk foot plan -----
// Stride length × cadence must match hip travel: 436 px / 79 walk frames ≈
// 5.52 px/frame, so STEP ≈ 5.52 × STEP_FRAMES and stays inside the 76 px
// two-bone reach. Two feet run half a cycle apart.
const STEP = 72, STEP_FRAMES = 13, SWING_AT = 0.5, LIFT = 24;
function walkFoot(footIndex, frame) {
  const offset = footIndex * STEP_FRAMES / 2;
  const cyclePos = ((frame + offset) % STEP_FRAMES) / STEP_FRAMES;
  const stepIndex = Math.floor((frame + offset) / STEP_FRAMES);
  const contact = WALK_START - footIndex * (STEP / 2) + stepIndex * STEP;
  if (cyclePos < SWING_AT) return {x: contact, y: PAW_Y, grounded: true};
  const u = smooth((cyclePos - SWING_AT) / (1 - SWING_AT));
  return {x: contact + STEP * u, y: PAW_Y - LIFT * Math.sin(PI * u), grounded: false};
}
// Stance positions at the very end of the walk, used to start the stop phase.
const WALK_END_NEAR = walkFoot(0, 79);
const WALK_END_FAR = walkFoot(1, 79);

// -------------------------------------------------------- frame building ----
function legIK(map, lengths, hip, target, thighNode, shinNode, footNode, facing, bend) {
  const {a1, a2} = solveTwoBoneIK(hip, target, THIGH_L, SHIN_L, bend);
  map.set(thighNode, a1);
  map.set(shinNode, a2);
  map.set(footNode, norm(a2 + 0.12 * facing));
}

function armIK(map, shoulder, target, n1, n2, facing, bendBias) {
  const {a1, a2} = solveTwoBoneIK(shoulder, target, ARM1_L, ARM2_L, bendBias * facing);
  map.set(n1, a1); map.set(n2, a2);
}

function blinkLength(f, centers, restLen) {
  for (const c of centers) {
    const d = Math.abs(f - c);
    if (d <= 2.2) return 2 + (restLen - 2) * smooth(d / 2.2); // closed in the middle
  }
  return null;
}
const REST_LID_FAR = 13, REST_LID_NEAR = 13;

function buildFrame(f) {
  const {name, u, start} = phaseAt(f);
  const local = f - start;
  const map = new Map(restMap);
  const lengths = [...restLengths];
  let hip = {x: WALK_START, y: HIP_Y};
  let facing = 1;
  const footTargets = {near: {x: WALK_START + 18, y: PAW_Y}, far: {x: WALK_START - 14, y: PAW_Y}};
  const body = {chestLean: 0, headTilt: 0, armSwing: 0, tailWag: 0, ear: 0};

  const setLen = (visualId, value) => { for (const sid of rig.segmentIds(visualId)) lengths[segIndex.get(sid)] = value; };

  // ---------------------------------------------------------- idle ----------
  if (name === 'idle') {
    const breath = Math.sin(f * 0.22);
    hip = {x: WALK_START, y: HIP_Y - 2 * breath};
    body.chestLean = 0.02 * breath; body.tailWag = 0.08 * breath;
    body.headTilt = 0.03 * Math.sin(f * 0.16);
    footTargets.near = {x: WALK_START + 18, y: PAW_Y}; footTargets.far = {x: WALK_START - 14, y: PAW_Y};
  }

  // ---------------------------------------------------------- walk ----------
  if (name === 'walk' || name === 'stop') {
    const wf = name === 'walk' ? local : STEP_FRAMES; // stop phase eases out of the cycle
    const progress = name === 'walk'
      ? easeInOut(clamp(local / (80 - 1), 0, 1))
      : 1;
    const stopEase = name === 'stop' ? easeInOut(local / 10) : 0;
    hip = {
      x: lerp(WALK_START, WALK_END, progress) + (name === 'stop' ? 0 : 0),
      y: HIP_Y - (name === 'stop' ? 3 * (1 - stopEase) : 3.5 * Math.abs(Math.sin((wf / STEP_FRAMES) * PI * 2))),
    };
    if (name === 'stop') { hip.x = lerp(WALK_END, WALK_END + 6, stopEase); hip.y = lerp(hip.y, HIP_Y, stopEase); }
    const a = walkFoot(0, Math.min(wf, 79));
    const b = walkFoot(1, Math.min(wf, 79));
    Object.assign(footTargets, {near: a, far: b});
    if (name === 'stop') {
      const e = easeInOut(local / 10);
      footTargets.near = {x: lerp(WALK_END_NEAR.x, WALK_END + 16, e), y: PAW_Y};
      footTargets.far = {x: lerp(WALK_END_FAR.x, WALK_END - 12, e), y: PAW_Y};
    }
    const s = Math.sin((wf / STEP_FRAMES) * PI * 2);
    body.armSwing = 0.32 * s * (name === 'stop' ? 1 - stopEase : 1);
    body.headTilt = 0.05 * s; body.tailWag = 0.18 * s; body.ear = 0.06 * s;
    body.chestLean = 0.05 * (name === 'stop' ? 1 - stopEase : 1);
  }

  // ---------------------------------------------------------- turn ----------
  if (name === 'turn' || name === 'backup' || name === 'sit' || name === 'settle') {
    // hip track through turn / backup / sit
    if (name === 'turn') {
      const crouch = u < 0.3 ? smooth(u / 0.3) * 7 : (1 - smooth((u - 0.3) / 0.7)) * 7;
      hip = {x: WALK_END + 6, y: HIP_Y + crouch};
      body.chestLean = 0.12 * Math.sin(u * PI);
      body.headTilt = -0.25 * Math.sin(u * PI);
    } else if (name === 'backup') {
      hip = {x: lerp(WALK_END + 6, SEAT_HIP.x - 6, easeInOut(u)), y: HIP_Y + 2 * Math.sin(u * PI)};
    } else if (name === 'sit') {
      const anti = u < 0.25 ? smooth(u / 0.25) : 1 - smooth(clamp((u - 0.25) / 0.75, 0, 1));
      hip = {x: lerp(SEAT_HIP.x - 6, SEAT_HIP.x, easeInOut(u)), y: lerp(HIP_Y, SEAT_HIP.y, easeInOut(u)) - 4 * anti};
      body.chestLean = -0.1 * anti + 0.06 * u;
    } else {
      hip = {x: SEAT_HIP.x, y: SEAT_HIP.y + 0.8 * Math.sin((f - 162) * 0.2)};
      body.chestLean = 0.06 + 0.012 * Math.sin((f - 162) * 0.18);
    }
    facing = -1;

    // feet: crossing step turn, then planted for the rest of the shot
    const nearFinal = {x: SEAT_HIP.x - 20, y: PAW_Y};
    const farFinal = {x: SEAT_HIP.x + 22, y: PAW_Y};
    if (name === 'turn') {
      if (u < 0.4) {
        footTargets.near = {x: WALK_END + 16, y: PAW_Y};
        footTargets.far = {x: WALK_END - 12, y: PAW_Y};
      } else if (u < 0.78) {
        const t = smooth((u - 0.4) / 0.38);
        // far foot crosses around in a lifted arc to the new side
        footTargets.near = {x: WALK_END + 16, y: PAW_Y};
        footTargets.far = {
          x: lerp(WALK_END - 12, farFinal.x + 6, t),
          y: PAW_Y - 22 * Math.sin(PI * t),
        };
      } else {
        const t = smooth((u - 0.78) / 0.22);
        footTargets.near = {x: lerp(WALK_END + 16, nearFinal.x, t), y: PAW_Y};
        footTargets.far = {x: farFinal.x + 6, y: PAW_Y};
      }
    } else if (name === 'backup') {
      const t = easeInOut(u);
      footTargets.near = {x: lerp(nearFinal.x, nearFinal.x + 8, t), y: PAW_Y};
      footTargets.far = {x: lerp(farFinal.x + 6, farFinal.x, t), y: PAW_Y};
    } else {
      // planted for the whole sit + settle: zero slide
      footTargets.near = nearFinal;
      footTargets.far = farFinal;
    }
  }

  // ---------------------------------------------------- solve legs (IK) ------
  // Bend sign stays fixed through the pivot turn (no knee pop); it flips only
  // once the body has settled into its left-facing stance.
  const bendSign = name === 'turn' || facing === 1 ? -1 : 1;
  legIK(map, lengths, hip, footTargets.near, N.thighF, N.shinF, N.footF.visualId, facing, bendSign);
  legIK(map, lengths, hip, footTargets.far, N.thighB, N.shinB, N.footB.visualId, facing, bendSign);

  // ------------------------------------------------------------ arms --------
  if (name === 'idle' || name === 'walk' || name === 'stop') {
    const sw = body.armSwing;
    map.set(N.armF1, restMap.get(N.armF1) - sw * facing);
    map.set(N.armF2, restMap.get(N.armF2) - sw * 0.6 * facing);
    map.set(N.armB1, restMap.get(N.armB1) + sw * 0.8 * facing);
    map.set(N.armB2, restMap.get(N.armB2) + sw * 0.5 * facing);
  } else if (name === 'turn') {
    // arms blend from the right-rest pose to the mirrored left-rest pose along
    // the short arc, with a brief outward flare at the middle — no hard switch
    const e = smooth(u);
    const flare = Math.sin(u * PI) * 0.28;
    map.set(N.armF1, angLerp(restMap.get(N.armF1), mirror(restMap.get(N.armF1)), e) + flare);
    map.set(N.armF2, angLerp(restMap.get(N.armF2), mirror(restMap.get(N.armF2)), e) + flare * 0.6);
    map.set(N.armB1, angLerp(restMap.get(N.armB1), mirror(restMap.get(N.armB1)), e) - flare * 0.6);
    map.set(N.armB2, angLerp(restMap.get(N.armB2), mirror(restMap.get(N.armB2)), e) - flare * 0.4);
  } else if (name === 'backup') {
    // mirrored resting arms with a gentle backward-step swing
    const sw = 0.18 * Math.sin(u * PI * 2);
    map.set(N.armF1, mirror(restMap.get(N.armF1)) + sw);
    map.set(N.armF2, mirror(restMap.get(N.armF2)) + sw * 0.6);
    map.set(N.armB1, mirror(restMap.get(N.armB1)) - sw * 0.8);
    map.set(N.armB2, mirror(restMap.get(N.armB2)) - sw * 0.5);
  } else {
    // paws come to rest together on the lap
    const lapT = name === 'sit' ? easeInOut(clamp(u / 0.8, 0, 1)) : 1;
    const shoulderF = nodeWorld(hip, map, N.chest, N.armF1);
    const shoulderB = nodeWorld(hip, map, N.chest, N.armB1);
    const lapNear = {x: hip.x - 16 * facing, y: hip.y + 30};
    const lapFar = {x: hip.x + 10 * facing, y: hip.y + 34};
    const solvedF = solveTwoBoneIK(shoulderF, lapNear, ARM1_L, ARM2_L, 1);
    const solvedB = solveTwoBoneIK(shoulderB, lapFar, ARM1_L, ARM2_L, 1);
    map.set(N.armF1, lerp(mirror(restMap.get(N.armF1)), solvedF.a1, lapT));
    map.set(N.armF2, lerp(mirror(restMap.get(N.armF2)), solvedF.a2, lapT));
    map.set(N.armB1, lerp(mirror(restMap.get(N.armB1)), solvedB.a1, lapT));
    map.set(N.armB2, lerp(mirror(restMap.get(N.armB2)), solvedB.a2, lapT));
  }

  // ---------------------------------------------------- spine / head ---------
  map.set(N.chest, -PI / 2 + body.chestLean * facing);
  map.set(N.tail1, restMap.get(N.tail1) + body.tailWag);
  map.set(N.tail2, restMap.get(N.tail2) + body.tailWag * 0.7);
  map.set(N.earF, restMap.get(N.earF) + body.ear);

  // face: a rigid common-angle turn keeps every facial element assembled.
  // The head rotates away (profile/back), the mirrored base swaps at the dip,
  // then it rotates back into the left-facing pose. No per-node absolute bow.
  const flipNodes = [N.tail1, N.tail2, N.scarfTail];
  if (facing === 1) {
    for (const id of faceIds) map.set(id, norm(rightRest.get(id) + body.headTilt));
  } else if (name === 'turn') {
    // The redesigned face is near-symmetric, so its mirrored end pose reads
    // identically to the start. A full 180° arc would drive the two lenses
    // through an overlapping top-down state this 2D rig has no "back of head"
    // pose for. Instead the face holds together with only an anticipatory nod,
    // and the turn is carried by the crossing step, torso lean, arms and the
    // tail/scarf flip. The end swap is visually seamless.
    const nod = 0.18 * Math.sin(Math.PI * u);
    for (const id of faceIds) map.set(id, norm(rightRest.get(id) + nod + body.headTilt));
    const e = smooth(u);
    for (const id of flipNodes) map.set(id, norm(lerp(rightRest.get(id), leftRest.get(id), e)));
  } else {
    // The round, near-symmetric head stays near-frontal for the whole shot —
    // it keeps its rest arrangement and never swaps sides, so there is no
    // turn-end snap. Facing is carried by the feet, torso, arms, tail & scarf.
    for (const id of faceIds) map.set(id, norm(rightRest.get(id) + body.headTilt));
    map.set(N.tail1, leftRest.get(N.tail1) + 0.05 * Math.sin((f - 102) * 0.2));
    map.set(N.tail2, leftRest.get(N.tail2) + 0.04 * Math.sin((f - 102) * 0.2));
    map.set(N.scarfTail, leftRest.get(N.scarfTail));
  }

  // ------------------------------------------------------------- blinks -----
  const blinkAt = [7, 150, 176];
  const lidFarLen = blinkLength(f, blinkAt, REST_LID_FAR);
  const lidNearLen = blinkLength(f, blinkAt, REST_LID_NEAR);
  if (lidFarLen !== null) setLen(N.lidFar.visualId, lidFarLen);
  if (lidNearLen !== null) setLen(N.lidNear.visualId, lidNearLen);

  // happy open mouth during the settle
  if (name === 'settle') {
    const t = clamp((local - 10) / 8, 0, 1); // opens
    const close = clamp((local - 20) / 6, 0, 1); // soft close
    const open = smooth(t) * (1 - 0.35 * smooth(close));
    setLen(N.mouthOpen.visualId, lerp(12, 33, open));
    map.set(N.mouthOpen, lerp(PI / 2, 1.6, open));
    setLen(N.tongue.visualId, lerp(0, 10, open));
  }

  return {hip, facing, map, lengths};
}

/** World position of a node by walking the current angle map (for arm IK). */
function nodeWorld(hip, map, ...chain) {
  let p = {...hip};
  let prevVisual = null;
  for (const visual of chain) {
    const segIds = rig.segmentIds(visual);
    const id = segIds[segIds.length - 1];
    const idx = segIndex.get(id);
    const seg = rig.segments[idx];
    const a = map.get(visual) ?? seg.angle_rad;
    p = {x: p.x + seg.length * Math.cos(a), y: p.y + seg.length * Math.sin(a)};
    prevVisual = visual;
  }
  return p;
}

// ------------------------------------------------------------- objects ------
function dogObject(state, uid) {
  return {
    object_slot: 0, unique_id: uid, figure_type_id: 1,
    root_x: state.hip.x, root_y: state.hip.y, scale: 1,
    color_override_raw: 0, field28: 0,
    angles: rig.poseAngles(state.map),
    len_flag: 1, lengths: state.lengths, bend_flag: 0, bends: [], join: null,
  };
}
const staticObj = (uid, tid, x, y, angles) => ({
  object_slot: 0, unique_id: uid, figure_type_id: tid,
  root_x: x, root_y: y, scale: 1, color_override_raw: 0, field28: 0,
  angles, len_flag: 0, lengths: [], bend_flag: 0, bends: [], join: null,
});

const keyframes = [];
for (let f = 0; f < 186; f++) {
  const state = buildFrame(f);
  const roomObj = staticObj(4, 3, ROOM.x, ROOM.y, roomRig.poseAngles(roomRest));
  const chairObj = staticObj(3, 2, CHAIR.x, CHAIR.y, chairRig.poseAngles(chairRest));
  const shadowObj = staticObj(2, 4, state.hip.x, GROUND_Y + 4, shadowRig.poseAngles(new Map()));
  const dogObj = dogObject(state, 1);
  keyframes.push({
    duration_raw: 1, background_id: 0, background_id_b: 0, background_mix: 0,
    camera: {is_default: true, x: 0, y: 0, scale: 1, angle_rad: 0},
    objects: [roomObj, shadowObj, chairObj, dogObj],
    object_draw_order: [0, 1, 2, 3],
    object_draw_order_unique_ids: [4, 2, 3, 1],
    _styk: {easing: {interpolation: 'hold'}},
  });
}

const document_ = {
  version: 5, canvas_width: 960, canvas_height: 540, fps: 24,
  auto_easing: false, auto_easing_disabled_raw: 1, auto_easing_source: 'file',
  backgrounds: [],
  figure_types: [ellyFig, chairFig, roomFig, shadowFig],
  keyframes,
  _styk: {format: 'StykAnimate', format_version: 1, name: 'Elly v2 — walk, turn, sit, settle'},
};

writeFileSync(join(OUT, 'elly-v2-walk-turn-sit.styk'), JSON.stringify(document_));
writeFileSync(join(OUT, 'elly-v2.stk'), writeStk(ellyFig));
writeFileSync(join(OUT, 'chair.stk'), writeStk(chairFig));
writeFileSync(join(OUT, 'room.stk'), writeStk(roomFig));

const previewDir = join(ROOT, 'preview');
mkdirSync(previewDir, {recursive: true});
writeFileSync(join(previewDir, 'project-data.js'),
  `// Auto-generated by v2/scripts/build-v2.mjs — do not edit by hand.\n` +
  `window.SMARTBARK_PROJECT = ${JSON.stringify(document_)};\n`);

console.log(`Wrote ${keyframes.length} frames (${(keyframes.length / 24).toFixed(1)}s)`);
console.log(`Segments: elly=${ellyFig.segment_count} chair=${chairFig.segment_count} room=${roomFig.segment_count} shadow=${shadowFig.segment_count}`);
