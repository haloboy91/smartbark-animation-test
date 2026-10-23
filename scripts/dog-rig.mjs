/**
 * dog-rig.mjs — "Elly" the fluffy white dog, built as a StykAnimate/Pivot figure
 * from thick round lines and filled circles with black outline twins.
 *
 * Design references the attached character art:
 *  - big fluffy white head with floppy ears, black nose and dot eyes
 *  - pink scarf/collar tucked under the head fluff, tail hanging on the chest
 *  - navy sweater decorated with yellow stars and a crescent-moon dot
 *  - short stubby legs with big fluffy paws and a curled tail
 *
 * The returned `nodes` map holds every posable visual node id so the animation
 * builder can express poses as absolute node angles.
 */

import {Rig} from './styk-rig.mjs';

const WHITE = [244, 243, 240];
const NAVY = [42, 57, 104];
const PINK = [216, 102, 116];
const YELLOW = [240, 196, 92];
const BLACK = [26, 26, 28];
const PI = Math.PI;

export function buildDogRig() {
  const rig = new Rig('Elly the dog');
  const nodes = {};

  // ---- Curled tail (behind the rump) --------------------------------------
  nodes.tail1 = rig.bone(0, { length: 20, angle: 2.9, thickness: 14, color: WHITE, layer: 2 });
  nodes.tail2 = rig.bone(nodes.tail1, { length: 18, angle: -2.8, thickness: 12, color: WHITE, layer: 2 });
  nodes.tail3 = rig.bone(nodes.tail2, { length: 13, angle: -2.3, thickness: 9, color: WHITE, layer: 2 });
  rig.ball(nodes.tail3, { radius: 8, color: WHITE, layer: 2 });

  // ---- Back (far) hind leg -------------------------------------------------
  nodes.thighB = rig.bone(0, { length: 34, angle: 2.0, thickness: 23, color: WHITE, layer: 1 });
  nodes.shinB = rig.bone(nodes.thighB, { length: 30, angle: 1.85, thickness: 19, color: WHITE, layer: 1 });
  nodes.footB = rig.stub(nodes.shinB, { length: 12, angle: 1.85, layer: 1 });
  rig.ball(nodes.footB, { radius: 13, color: WHITE, layer: 1 });

  // ---- Front (near) hind leg ----------------------------------------------
  nodes.thighF = rig.bone(0, { length: 34, angle: 1.16, thickness: 25, color: WHITE, layer: 6 });
  nodes.shinF = rig.bone(nodes.thighF, { length: 30, angle: 1.3, thickness: 21, color: WHITE, layer: 6 });
  nodes.footF = rig.stub(nodes.shinF, { length: 14, angle: 1.45, layer: 6 });
  rig.ball(nodes.footF, { radius: 15, color: WHITE, layer: 6 });

  // ---- Torso (navy sweater) ------------------------------------------------
  nodes.chest = rig.bone(0, { length: 82, angle: -PI / 2, thickness: 62, color: NAVY, layer: 5 });
  nodes.neck = rig.bone(nodes.chest, { length: 18, angle: -PI / 2, thickness: 28, color: NAVY, layer: 5 });

  // ---- Head assembly -------------------------------------------------------
  const headStart = rig.visualCount();
  nodes.headPivot = rig.stub(nodes.neck, { length: 16, angle: -PI / 2, layer: 6 });
  // fluffy fur tufts around the head outline (overlap the main head ball)
  for (const [ang, len, r] of [
    [-2.95, 40, 12], [-2.45, 44, 13], [-1.95, 46, 14], [-1.45, 46, 14],
    [-0.95, 44, 13], [-0.5, 41, 12],
  ]) {
    const tuft = rig.stub(nodes.headPivot, { length: len, angle: ang, layer: 4 });
    rig.ball(tuft, { radius: r, color: WHITE, layer: 4 });
  }
  rig.ball(nodes.headPivot, { radius: 52, color: WHITE, layer: 6 });

  // floppy ears: anchors on the upper sides of the head, soft ear flaps hang
  // outside the head silhouette so they never get swallowed by the head disc
  const earBAnchor = rig.stub(nodes.headPivot, { length: 40, angle: 2.72, layer: 2 });
  nodes.earB = rig.bone(earBAnchor, { length: 26, angle: 2.1, thickness: 18, color: WHITE, layer: 2 });
  nodes.earB2 = rig.bone(nodes.earB, { length: 22, angle: 1.72, thickness: 15, color: WHITE, layer: 2 });
  rig.ball(nodes.earB2, { radius: 11, color: WHITE, layer: 2 });
  const earFAnchor = rig.stub(nodes.headPivot, { length: 40, angle: 0.42, layer: 5.5 });
  nodes.earF = rig.bone(earFAnchor, { length: 26, angle: 1.04, thickness: 17, color: WHITE, layer: 5.5 });
  nodes.earF2 = rig.bone(nodes.earF, { length: 22, angle: 1.38, thickness: 14, color: WHITE, layer: 5.5 });
  rig.ball(nodes.earF2, { radius: 10, color: WHITE, layer: 5.5 });

  // ---- Face ----------------------------------------------------------------
  nodes.snout = rig.stub(nodes.headPivot, { length: 30, angle: 0.78, layer: 10 });
  rig.ball(nodes.snout, { radius: 22, color: WHITE, layer: 10 });
  nodes.nose = rig.stub(nodes.snout, { length: 14, angle: 0.78, layer: 11 });
  rig.ball(nodes.nose, { radius: 9.5, color: BLACK, layer: 11, outline: 0 });
  // small smile under the snout (stub carries the line to the lower snout edge)
  const mouthBase = rig.stub(nodes.snout, { length: 12, angle: 1.2, layer: 11 });
  nodes.mouth = rig.bone(mouthBase, { length: 10, angle: 1.5, thickness: 4, color: BLACK, layer: 11, outline: false });
  // eyes (3/4 view: front eye larger)
  nodes.eyeF = rig.stub(nodes.headPivot, { length: 33, angle: 0.18, layer: 10 });
  rig.ball(nodes.eyeF, { radius: 8.4, color: BLACK, layer: 10, outline: 0 });
  nodes.eyeB = rig.stub(nodes.headPivot, { length: 29, angle: -0.52, layer: 10 });
  rig.ball(nodes.eyeB, { radius: 7.2, color: BLACK, layer: 10, outline: 0 });
  const glintF = rig.stub(nodes.eyeF, { length: 3.6, angle: -1.3, layer: 11 });
  rig.ball(glintF, { radius: 2.6, color: [255, 255, 255], layer: 11, outline: 0 });
  const glintB = rig.stub(nodes.eyeB, { length: 3.1, angle: -1.3, layer: 11 });
  rig.ball(glintB, { radius: 2.2, color: [255, 255, 255], layer: 11, outline: 0 });
  // eyebrows for expression (stub to the brow anchor, then a short tangent dash)
  const browFBase = rig.stub(nodes.headPivot, { length: 28, angle: 0.22, layer: 11 });
  nodes.browF = rig.bone(browFBase, { length: 11, angle: -1.1, thickness: 3.4, color: BLACK, layer: 11, outline: false });
  const browBBase = rig.stub(nodes.headPivot, { length: 25, angle: -0.58, layer: 11 });
  nodes.browB = rig.bone(browBBase, { length: 9, angle: -2.1, thickness: 3.2, color: BLACK, layer: 11, outline: false });
  const headGroup = rig.visualsSince(headStart);

  // ---- Pink scarf collar (tucks under the chin; head covers its top edge) ----
  // stub points DOWN from the chest-top joint so the ring sits below the head
  // disc's lower edge, showing a collar crescent under the chin
  const scarfPos = rig.stub(nodes.chest, { length: 26, angle: PI / 2, layer: 5.8 });
  rig.ball(scarfPos, { radius: 19, color: PINK, layer: 5.8 });
  nodes.scarfTail = rig.bone(scarfPos, { length: 34, angle: 1.5, thickness: 12, color: PINK, layer: 5.8 });
  rig.ball(nodes.scarfTail, { radius: 8, color: PINK, layer: 5.8 });

  // ---- Sweater stars + moon (yellow), a starry band below the collar --------
  // (x, y) are offsets from the chest-top joint; +y runs down onto the torso,
  // so every point sits below the collar and inside the navy sweater
  for (const [x, y, r] of [[-8, 48, 8], [14, 46, 4.5], [-15, 62, 4.5], [8, 63, 4.5], [0, 72, 4], [15, 70, 3.8]]) {
    const ang = Math.atan2(y, x), len = Math.hypot(x, y);
    const deco = rig.stub(nodes.chest, { length: len, angle: ang, layer: 7 });
    rig.ball(deco, { radius: r, color: YELLOW, layer: 7 });
  }

  // ---- Arms (front legs) ----------------------------------------------------
  nodes.armB1 = rig.bone(nodes.chest, { length: 28, angle: 2.1, thickness: 15, color: NAVY, layer: 1 });
  nodes.armB2 = rig.bone(nodes.armB1, { length: 26, angle: 1.82, thickness: 13, color: NAVY, layer: 1 });
  rig.ball(nodes.armB2, { radius: 10, color: WHITE, layer: 1 });
  nodes.armF1 = rig.bone(nodes.chest, { length: 28, angle: 1.02, thickness: 16, color: NAVY, layer: 9 });
  nodes.armF2 = rig.bone(nodes.armF1, { length: 26, angle: 1.28, thickness: 14, color: NAVY, layer: 9 });
  rig.ball(nodes.armF2, { radius: 11, color: WHITE, layer: 9 });

  return {rig, nodes, groups: {head: headGroup}};
}
