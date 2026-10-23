/**
 * scene-rig.mjs — static environment figures: the table the dog walks to and
 * the room/floor figure. Both are ordinary StykAnimate figures built from the
 * same rig DSL, so they render identically in the app and in the local preview.
 */

import {Rig} from './styk-rig.mjs';

const WOOD = [150, 101, 62];
const WOOD_DARK = [120, 79, 47];
const RED = [198, 74, 74];
const RED_DARK = [150, 48, 48];
const FLOOR = [214, 210, 202];
const BOARD = [198, 194, 186];

/** Dining table with a dog bowl on top. Root node = center of the tabletop. */
export function buildTableRig() {
  const rig = new Rig('Table');
  const nodes = {};

  nodes.topLeft = rig.bone(0, { length: 150, angle: Math.PI, thickness: 22, color: WOOD, layer: 2 });
  nodes.topRight = rig.bone(0, { length: 150, angle: 0, thickness: 22, color: WOOD, layer: 2 });
  // apron beam under the tabletop
  rig.bone(0, { length: 132, angle: Math.PI, thickness: 15, color: WOOD_DARK, layer: 1.5 });
  rig.bone(0, { length: 132, angle: 0, thickness: 15, color: WOOD_DARK, layer: 1.5 });

  // front legs (near side)
  rig.bone(nodes.topLeft, { length: 120, angle: Math.PI / 2, thickness: 15, color: WOOD_DARK, layer: 1 });
  rig.bone(nodes.topRight, { length: 120, angle: Math.PI / 2, thickness: 15, color: WOOD_DARK, layer: 1 });
  // back legs, slightly splayed so they read behind the front pair
  rig.bone(nodes.topLeft, { length: 114, angle: 1.42, thickness: 11, color: WOOD_DARK, layer: 0 });
  rig.bone(nodes.topRight, { length: 114, angle: 1.72, thickness: 11, color: WOOD_DARK, layer: 0 });

  // dog bowl resting on the tabletop
  const bowlStub = rig.stub(0, { length: 78, angle: -0.12, layer: 3 });
  rig.ball(bowlStub, { radius: 17, color: RED, layer: 3 });
  rig.ball(bowlStub, { radius: 10, color: RED_DARK, layer: 3.1 });

  return {rig, nodes};
}

/** Wide floor strip + baseboard. Root node = center of the floor strip. */
export function buildRoomRig() {
  const rig = new Rig('Room');
  const nodes = {};
  nodes.floorL = rig.bone(0, { length: 640, angle: Math.PI, thickness: 11, color: FLOOR, layer: 0 });
  nodes.floorR = rig.bone(0, { length: 640, angle: 0, thickness: 11, color: FLOOR, layer: 0 });
  return {rig, nodes};
}
