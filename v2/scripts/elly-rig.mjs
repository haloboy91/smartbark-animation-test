/**
 * elly-rig.mjs (v2) — Elly rebuilt from the Smart Bark Kit v2 references.
 *
 * Identity features preserved from the reference art:
 *   big round scalloped bichon head, large round glasses, black nose with
 *   smiling muzzle, pink scarf, navy star/moon sweater with ribbed cuffs and
 *   hem, short stubby legs, fluffy paws with toe lines, pom-pom tail.
 *
 * Everything is replacement artwork drawn natively from Pivot primitives
 * (thick lines, filled discs, stroke rings) — no bitmap warping.
 * Root node 0 is the hip; local space faces +x (right), y down.
 */

import {Rig} from './styk-rig.mjs';

const WHITE = [247, 246, 242];
const WHITE_FUR = [242, 240, 235];
const NAVY = [43, 58, 106];
const NAVY_DARK = [31, 42, 80];
const PINK = [214, 96, 110];
const PINK_DARK = [184, 74, 88];
const YELLOW = [240, 196, 92];
const BLACK = [28, 28, 31];
const SHADOW = [74, 66, 58];
const PI = Math.PI;

export function buildEllyRig() {
  const rig = new Rig('Elly v2');
  const N = {};

  // ---------------------------------------------------------------- tail ---
  N.tail1 = rig.bone(0, {length: 16, angle: 2.55, thickness: 13, color: WHITE_FUR, layer: 2});
  N.tail2 = rig.bone(N.tail1, {length: 12, angle: 2.95, thickness: 11, color: WHITE_FUR, layer: 2});
  N.tailPom = rig.ball(N.tail2, {radius: 14, color: WHITE, layer: 2});

  // ------------------------------------------------- far (back) hind leg ----
  N.thighB = rig.bone(0, {length: 38, angle: 1.95, thickness: 21, color: WHITE_FUR, layer: 1});
  N.shinB = rig.bone(N.thighB, {length: 38, angle: 1.7, thickness: 18, color: WHITE_FUR, layer: 1});
  N.footB = rig.stub(N.shinB, {length: 12, angle: 1.55, layer: 1});
  N.pawB = rig.ball(N.footB, {radius: 15, color: WHITE, layer: 1});
  for (const a of [1.25, 1.62]) {
    const toe = rig.stub(N.footB, {length: 11, angle: a, layer: 1.2});
    rig.bone(toe, {length: 5, angle: a, thickness: 2.6, color: BLACK, layer: 1.2, outline: false});
  }

  // ------------------------------------------------- near (front) hind leg ---
  N.thighF = rig.bone(0, {length: 38, angle: 1.2, thickness: 23, color: WHITE_FUR, layer: 7});
  N.shinF = rig.bone(N.thighF, {length: 38, angle: 1.42, thickness: 20, color: WHITE_FUR, layer: 7});
  N.footF = rig.stub(N.shinF, {length: 12, angle: 1.5, layer: 7});
  N.pawF = rig.ball(N.footF, {radius: 16, color: WHITE, layer: 7});
  for (const a of [1.2, 1.58]) {
    const toe = rig.stub(N.footF, {length: 12, angle: a, layer: 7.2});
    rig.bone(toe, {length: 5, angle: a, thickness: 2.8, color: BLACK, layer: 7.2, outline: false});
  }

  // ------------------------------------------------------------- torso ------
  N.chest = rig.bone(0, {length: 92, angle: -PI / 2, thickness: 74, color: NAVY, layer: 4});
  // ribbed hem at the sweater's bottom edge (near the hip, not the chest top)
  const hemPos = rig.stub(0, {length: 8, angle: -PI / 2, layer: 4.2});
  N.hem = rig.ball(hemPos, {radius: 29, color: NAVY_DARK, layer: 4.2, outline: 3});
  const hemStitch = rig.stub(hemPos, {length: 18, angle: PI / 2, layer: 4.4});
  rig.bone(hemStitch, {length: 10, angle: PI / 2, thickness: 3, color: NAVY, layer: 4.4, outline: false});

  // sweater decorations: crescent moons and sparkles on the visible flank
  const deco = (x, y, kind, size) => {
    const ang = Math.atan2(y, x), len = Math.hypot(x, y);
    const anchor = rig.stub(N.chest, {length: len, angle: ang, layer: 6});
    if (kind === 'moon') rig.moon(anchor, {radius: size, bite: size * 0.82, offset: size * 0.55, color: YELLOW, biteColor: NAVY, layer: 6});
    else rig.sparkle(anchor, {radius: size, color: YELLOW, layer: 6, point: size * 0.66});
  };
  // (x, y) offsets from chest-top joint, +y downward onto the torso front
  deco(20, 42, 'moon', 9);
  deco(-16, 50, 'sparkle', 4.6);
  deco(12, 66, 'sparkle', 4);
  deco(-20, 72, 'moon', 7);
  deco(22, 82, 'sparkle', 3.8);
  deco(-6, 86, 'sparkle', 3.6);

  // ------------------------------------------------------------- arms -------
  // far arm behind the torso
  N.armB1 = rig.bone(N.chest, {length: 32, angle: 2.05, thickness: 15, color: NAVY, layer: 1.4});
  N.armB2 = rig.bone(N.armB1, {length: 28, angle: 1.75, thickness: 13, color: NAVY, layer: 1.4});
  rig.ball(N.armB2, {radius: 9, color: NAVY_DARK, layer: 1.5, outline: 2}); // cuff
  N.pawArmB = rig.ball(N.armB2, {radius: 11, color: WHITE, layer: 1.6});
  // near arm in front
  N.armF1 = rig.bone(N.chest, {length: 34, angle: 1.08, thickness: 16, color: NAVY, layer: 8});
  N.armF2 = rig.bone(N.armF1, {length: 30, angle: 1.32, thickness: 14, color: NAVY, layer: 8});
  rig.ball(N.armF2, {radius: 10, color: NAVY_DARK, layer: 8.1, outline: 2}); // cuff
  N.pawArmF = rig.ball(N.armF2, {radius: 12, color: WHITE, layer: 8.2});
  for (const a of [1.1, 1.5]) {
    const toe = rig.stub(N.armF2, {length: 9, angle: a, layer: 8.3});
    rig.bone(toe, {length: 4, angle: a, thickness: 2.4, color: BLACK, layer: 8.3, outline: false});
  }

  // ------------------------------------------------------------- neck -------
  N.neck = rig.bone(N.chest, {length: 14, angle: -PI / 2, thickness: 30, color: NAVY, layer: 4.5});

  // pink scarf: wide band just under the head fluff, plus a hanging tail
  const scarfPos = rig.stub(N.chest, {length: 10, angle: PI / 2, layer: 4.7});
  N.scarf = rig.ball(scarfPos, {radius: 27, color: PINK, layer: 4.7, outline: 3});
  const scarfFold = rig.stub(scarfPos, {length: 18, angle: 0.35, layer: 4.8});
  rig.bone(scarfFold, {length: 14, angle: 0.35, thickness: 2.6, color: PINK_DARK, layer: 4.8, outline: false});
  N.scarfTail = rig.bone(scarfPos, {length: 32, angle: 1.42, thickness: 13, color: PINK, layer: 4.7});
  rig.ball(N.scarfTail, {radius: 8, color: PINK, layer: 4.7});
  const scarfCrease = rig.stub(N.scarfTail, {length: 17, angle: 1.42, layer: 4.8});
  rig.bone(scarfCrease, {length: 10, angle: 1.42, thickness: 2.4, color: PINK_DARK, layer: 4.8, outline: false});

  // ============================================================== HEAD ======
  const headStart = rig.visualCount();
  N.headPivot = rig.stub(N.neck, {length: 34, angle: -PI / 2, layer: 5});

  // far ear puff (round bichon ear, behind the head)
  N.earB = rig.stub(N.headPivot, {length: 46, angle: 2.62, layer: 3});
  rig.ball(N.earB, {radius: 22, color: WHITE_FUR, layer: 3});
  const eb1 = rig.stub(N.earB, {length: 18, angle: 2.25, layer: 3});
  rig.ball(eb1, {radius: 12, color: WHITE_FUR, layer: 3, outline: 2.5});
  const eb2 = rig.stub(N.earB, {length: 18, angle: 2.95, layer: 3});
  rig.ball(eb2, {radius: 11, color: WHITE_FUR, layer: 3, outline: 2.5});

  // scalloped cloud fur around the head (behind the main head disc)
  for (const [ang, dist, r] of [
    [2.95, 44, 15], [2.45, 48, 16], [2.0, 50, 16], [-2.9, 46, 15],
    [-2.4, 50, 16], [-1.9, 50, 15], [-1.45, 48, 15], [-0.95, 46, 14],
    [-0.5, 44, 13], [3.05, 40, 13],
  ]) {
    const scallop = rig.stub(N.headPivot, {length: dist, angle: ang, layer: 3.6});
    rig.ball(scallop, {radius: r, color: WHITE_FUR, layer: 3.6, outline: 2.8});
  }
  N.head = rig.ball(N.headPivot, {radius: 54, color: WHITE, layer: 5});

  // near ear puff (smaller, in front of the head edge, behind the face)
  N.earF = rig.stub(N.headPivot, {length: 47, angle: 0.42, layer: 8});
  rig.ball(N.earF, {radius: 17, color: WHITE_FUR, layer: 8, outline: 2.8});
  const ef1 = rig.stub(N.earF, {length: 14, angle: 0.05, layer: 8});
  rig.ball(ef1, {radius: 10, color: WHITE_FUR, layer: 8, outline: 2.4});

  // ------------------------------------------------------------- face -------
  // Near-symmetric face: anchors are mirrored pairs about the vertical axis,
  // so the turn's horizontal mirror yields the same clean arrangement.
  // glasses: two big round lenses side by side
  N.lensFarAnchor = rig.stub(N.headPivot, {length: 25, angle: PI + 0.30, layer: 10});
  N.lensFar = rig.ring(N.lensFarAnchor, {radius: 17, thickness: 5, color: BLACK, layer: 10});
  N.lensNearAnchor = rig.stub(N.headPivot, {length: 25, angle: -0.30, layer: 10});
  N.lensNear = rig.ring(N.lensNearAnchor, {radius: 17, thickness: 5, color: BLACK, layer: 10});
  // bridge between the lens centers
  N.bridge = rig.bone(N.lensFarAnchor, {length: 15, angle: -0.30, thickness: 3.4, color: BLACK, layer: 10, outline: false});
  // temples running back to the ear puffs
  const templeF = rig.stub(N.lensNearAnchor, {length: 14, angle: -0.35, layer: 9.9});
  rig.bone(templeF, {length: 14, angle: -0.6, thickness: 3, color: BLACK, layer: 9.9, outline: false});
  const templeB = rig.stub(N.lensFarAnchor, {length: 14, angle: PI + 0.35, layer: 9.9});
  rig.bone(templeB, {length: 14, angle: PI + 0.6, thickness: 3, color: BLACK, layer: 9.9, outline: false});

  // eyes behind the lenses (centered in each ring)
  N.eyeFar = rig.stub(N.headPivot, {length: 25, angle: PI + 0.30, layer: 9.6});
  rig.plainBall(N.eyeFar, {radius: 6, color: BLACK, layer: 9.6});
  N.eyeNear = rig.stub(N.headPivot, {length: 25, angle: -0.30, layer: 9.6});
  rig.plainBall(N.eyeNear, {radius: 6, color: BLACK, layer: 9.6});
  const glintF = rig.stub(N.eyeNear, {length: 2.6, angle: -1.3, layer: 9.7});
  rig.plainBall(glintF, {radius: 2, color: [255, 255, 255], layer: 9.7});
  const glintB = rig.stub(N.eyeFar, {length: 2.6, angle: -1.3, layer: 9.7});
  rig.plainBall(glintB, {radius: 2, color: [255, 255, 255], layer: 9.7});

  // eyelids: head-white discs parked just above each eye; shortening their
  // stub slides them down over the eye to blink, inside the lens ring
  N.lidFar = rig.stub(N.eyeFar, {length: 13, angle: -PI / 2, layer: 9.8});
  rig.plainBall(N.lidFar, {radius: 9, color: WHITE, layer: 9.8});
  N.lidNear = rig.stub(N.eyeNear, {length: 13, angle: -PI / 2, layer: 9.8});
  rig.plainBall(N.lidNear, {radius: 9, color: WHITE, layer: 9.8});

  // eyebrows above the lens rings
  const browFBase = rig.stub(N.headPivot, {length: 34, angle: -0.42, layer: 10.2});
  N.browF = rig.bone(browFBase, {length: 9, angle: -PI / 2, thickness: 3.2, color: BLACK, layer: 10.2, outline: false});
  const browBBase = rig.stub(N.headPivot, {length: 34, angle: PI + 0.42, layer: 10.2});
  N.browB = rig.bone(browBBase, {length: 9, angle: -PI / 2, thickness: 3.2, color: BLACK, layer: 10.2, outline: false});

  // muzzle + nose, centered low on the face so a mirror keeps it centered
  N.muzzle = rig.stub(N.headPivot, {length: 31, angle: PI / 2, layer: 9});
  rig.ball(N.muzzle, {radius: 21, color: WHITE, layer: 9});
  N.nose = rig.stub(N.muzzle, {length: 11, angle: PI / 2, layer: 11});
  rig.plainBall(N.nose, {radius: 8.5, color: BLACK, layer: 11});
  const noseHi = rig.stub(N.nose, {length: 3.4, angle: -1.4, layer: 11.1});
  rig.plainBall(noseHi, {radius: 2.1, color: [255, 255, 255], layer: 11.1});
  // smile line
  const mouthBase = rig.stub(N.muzzle, {length: 12, angle: 1.35, layer: 10.6});
  N.mouth = rig.bone(mouthBase, {length: 10, angle: 1.6, thickness: 3.2, color: BLACK, layer: 10.6, outline: false});
  // open happy mouth: a black ball parked fully behind the nose at rest;
  // lengthening the stub slides it below the muzzle edge for a happy pant.
  N.mouthOpen = rig.stub(N.muzzle, {length: 12, angle: PI / 2, layer: 10.7});
  rig.plainBall(N.mouthOpen, {radius: 8.5, color: BLACK, layer: 10.7});
  N.tongue = rig.stub(N.mouthOpen, {length: 0, angle: PI / 2, layer: 10.8});
  rig.plainBall(N.tongue, {radius: 4.2, color: PINK, layer: 10.8});

  // Every head visual — including the lens-ring anchor stubs, which must
  // rotate with the head so the rings travel with the eyes — joins the turn.
  // The ring segments themselves are circles, so their own angle is moot.
  const headGroup = rig.visualsSince(headStart);

  return {rig, nodes: N, groups: {head: headGroup}};
}

/** Soft contact shadow figure (repositioned per frame, fixed ground height). */
export function buildShadowRig() {
  const rig = new Rig('Elly shadow');
  rig.plainBall(0, {radius: 48, color: SHADOW, layer: 0, transparency: 196});
  return rig;
}
