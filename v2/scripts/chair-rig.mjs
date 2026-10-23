/**
 * chair-rig.mjs (v2) — fixed wooden chair in the Kit v2 stool style.
 * Plank seat, four legs, two straight back posts with a rounded top rail.
 * The backrest is on the +x side: Elly turns to face -x before sitting, so
 * her back rests against it. Root 0 is the seat center (seat surface level).
 */

import {Rig} from './styk-rig.mjs';

const WOOD = [158, 108, 66];
const WOOD_LIGHT = [178, 124, 80];
const WOOD_DARK = [118, 78, 46];
const FLOOR = [216, 211, 203];
const BOARD = [200, 195, 187];
const SHADOW = [74, 66, 58];
const PI = Math.PI;

export function buildChairRig() {
  const rig = new Rig('Chair');
  const N = {};

  // seat planks
  N.seatL = rig.bone(0, {length: 78, angle: PI, thickness: 18, color: WOOD, layer: 3});
  N.seatR = rig.bone(0, {length: 78, angle: 0, thickness: 18, color: WOOD, layer: 3});
  // plank seams
  for (const dy of [-6, 6]) {
    const seam = rig.stub(0, {length: Math.abs(dy), angle: dy < 0 ? -PI / 2 : PI / 2, layer: 3.2});
    rig.bone(seam, {length: 68, angle: PI, thickness: 2, color: WOOD_DARK, layer: 3.2, outline: false});
    rig.bone(seam, {length: 68, angle: 0, thickness: 2, color: WOOD_DARK, layer: 3.2, outline: false});
  }

  // front legs (near viewer) at the seat ends
  rig.bone(N.seatL, {length: 78, angle: PI / 2, thickness: 13, color: WOOD_DARK, layer: 2});
  rig.bone(N.seatR, {length: 78, angle: PI / 2, thickness: 13, color: WOOD_DARK, layer: 2});
  // back legs, slightly inset
  const backL = rig.stub(0, {length: 60, angle: PI, layer: 1.6});
  const backR = rig.stub(0, {length: 60, angle: 0, layer: 1.6});
  rig.bone(backL, {length: 74, angle: PI / 2, thickness: 10, color: WOOD_DARK, layer: 1.6});
  rig.bone(backR, {length: 74, angle: PI / 2, thickness: 10, color: WOOD_DARK, layer: 1.6});

  // backrest posts (straight up from the +x seat edge)
  const postBase1 = rig.stub(0, {length: 66, angle: 0, layer: 3.4});
  N.post1 = rig.bone(postBase1, {length: 92, angle: -PI / 2, thickness: 13, color: WOOD, layer: 3.4});
  const postBase2 = rig.stub(0, {length: 40, angle: 0, layer: 3.3});
  N.post2 = rig.bone(postBase2, {length: 84, angle: -PI / 2, thickness: 11, color: WOOD, layer: 3.3});
  // top rail joining the post tips
  rig.bone(N.post1, {length: 27, angle: 2.92, thickness: 13, color: WOOD_LIGHT, layer: 3.5});
  // finial balls
  rig.ball(N.post1, {radius: 8, color: WOOD_LIGHT, layer: 3.6});
  rig.ball(N.post2, {radius: 7, color: WOOD_LIGHT, layer: 3.6});

  // soft contact shadow pooled on the floor beneath the chair
  const shadowPos = rig.stub(0, {length: 80, angle: PI / 2, layer: 0});
  rig.plainBall(shadowPos, {radius: 78, color: SHADOW, layer: 0, transparency: 208});

  return {rig, nodes: N};
}

export function buildRoomRig() {
  const rig = new Rig('Room');
  const N = {};
  N.floorL = rig.bone(0, {length: 640, angle: PI, thickness: 12, color: FLOOR, layer: 0});
  N.floorR = rig.bone(0, {length: 640, angle: 0, thickness: 12, color: FLOOR, layer: 0});
  N.boardL = rig.bone(0, {length: 640, angle: PI, thickness: 5, color: BOARD, layer: 0.1});
  N.boardR = rig.bone(0, {length: 640, angle: 0, thickness: 5, color: BOARD, layer: 0.1});
  return {rig, nodes: N};
}
