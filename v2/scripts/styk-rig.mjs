/**
 * styk-rig.mjs (v2) — rig DSL for authoring StykAnimate / Pivot v5 figures.
 *
 * Segment tree rooted at node 0. A segment runs from its parent node to a new
 * node: end = parent + length * (cos(angle), sin(angle)); y-down, facing +x.
 * Cartoon outlines are black "twin" primitives drawn before colored ones.
 *
 * Primitives used:
 *   line (0)       stroked round line, radius = thickness / 2
 *   circleFill (3) filled disc, radius = (length + thickness) / 2 at midpoint
 *   circleClear(4) stroke-only ring of that radius with line width = thickness
 */

import {deflateSync} from 'node:zlib';

export const OUTLINE = [30, 30, 33];
let nextZ = 0;

export class Rig {
  constructor(name) {
    this.name = name;
    this.nodes = new Map(); // visualId -> node info
    this.segments = [];     // physical segments, segment_id = index+1
    this._visualCount = 0;
    this.nonTurning = new Set(); // visuals that keep fixed rest angles (rings)
  }

  _addSegment({parent, length, angle, thickness, color, prim, layer, visualId, transparent = false, transparency = 0}) {
    const id = this.segments.length + 1;
    const alpha = transparent ? 255 : transparency;
    this.segments.push({
      segment_id: id,
      parent_id: parent,
      length,
      angle_rad: angle,
      thickness,
      bend_rad: 0,
      primitive_code: prim,
      aux_code: 0,
      flags: prim,
      segment_type: [1, 3, 4].includes(prim) ? 'circle' : 'line',
      segment_kind: ['line', 'circle', 'image', 'circleFill', 'circleClear', 'text', 'squareLine'][prim],
      color_rgb: [...color],
      transparency: alpha,
      color_alpha: 1 - alpha / 255,
      visible: !transparent && (thickness > 0.01 || prim > 0),
      z_order: ++nextZ,
      _layer: layer,
      _visual: visualId,
    });
    return id;
  }

  _newVisual(restAngle) {
    const visualId = ++this._visualCount;
    this.nodes.set(visualId, {restAngle, segIds: []});
    return visualId;
  }

  _resolveParent(parent) {
    if (parent === 0 || parent == null) return {ol: 0, col: 0};
    if (typeof parent === 'number') {
      const [ol, col] = this.nodes.get(parent).segIds;
      return {ol, col};
    }
    if (parent.stubId !== undefined) return {ol: parent.stubId, col: parent.stubId};
    if (parent.ol !== undefined) return {ol: parent.ol, col: parent.col};
    throw new Error('Unknown parent reference');
  }

  /** Thick round line with black outline twin. Returns visual node id. */
  bone(parent, {length, angle, thickness, color, layer, outline = true, outlineGap = 7}) {
    const visualId = this._newVisual(angle);
    const p = this._resolveParent(parent);
    const segIds = [];
    if (outline) segIds.push(this._addSegment({parent: p.ol, length, angle, thickness: thickness + outlineGap, color: OUTLINE, prim: 0, layer, visualId}));
    segIds.push(this._addSegment({parent: p.col, length, angle, thickness, color, prim: 0, layer: layer + 0.1, visualId}));
    this.nodes.get(visualId).segIds = segIds;
    return visualId;
  }

  /** Invisible zero-thickness positioning segment. */
  stub(parentPhysical, {length, angle, layer = 0}) {
    const visualId = this._newVisual(angle);
    const p = this._resolveParent(parentPhysical);
    const id = this._addSegment({parent: p.col, length, angle, thickness: 0, color: OUTLINE, prim: 0, layer, visualId, transparent: true});
    this.nodes.set(visualId, {restAngle: angle, segIds: [id], stub: true});
    return {stubId: id, visualId};
  }

  /** Filled disc centered on a node (zero-length segment pair). */
  ball(parentPhysical, {radius, color, layer, outline = 3.5, transparency = 0}) {
    const visualId = this._newVisual(0);
    this.nodes.set(visualId, {restAngle: 0, segIds: [], ball: true});
    const p = this._resolveParent(parentPhysical);
    const segIds = [];
    if (outline > 0) segIds.push(this._addSegment({parent: p.ol, length: 0, angle: 0, thickness: 2 * (radius + outline), color: OUTLINE, prim: 3, layer, visualId}));
    segIds.push(this._addSegment({parent: p.col, length: 0, angle: 0, thickness: 2 * radius, color, prim: 3, layer: layer + 0.1, visualId, transparency}));
    this.nodes.get(visualId).segIds = segIds;
    return {ol: segIds[0], col: segIds.at(-1), visualId};
  }

  /** Disc without outline (eyes, nose, glints, eyelids, shadow blobs). */
  plainBall(parentPhysical, {radius, color, layer, transparency = 0}) {
    return this.ball(parentPhysical, {radius, color, layer, outline: 0, transparency});
  }

  /**
   * Stroke-only ring (Pivot circleClear). A hidden anchor stub reaches back
   * from the parent node so the ring segment's midpoint (its circle center)
   * lands exactly on the parent node. Rings are rotationally symmetric, so
   * callers should keep these visuals out of body-turn angle maps.
   */
  ring(parentPhysical, {radius, thickness, color = OUTLINE, layer}) {
    const length = Math.max(0.1, 2 * radius - thickness);
    const anchor = this.stub(parentPhysical, {length: length / 2, angle: Math.PI, layer});
    const visualId = this._newVisual(0);
    const id = this._addSegment({parent: anchor.stubId, length, angle: 0, thickness, color, prim: 4, layer: layer + 0.1, visualId});
    this.nodes.set(visualId, {restAngle: 0, segIds: [id], ring: true});
    this.nonTurning.add(anchor.visualId);
    this.nonTurning.add(visualId);
    return {segId: id, visualId, anchorVisual: anchor.visualId};
  }

  /** Crescent moon: yellow disc with a navy disc biting one side. */
  moon(parentPhysical, {radius = 9, bite = 7.5, offset = 5, color, biteColor, layer}) {
    this.ball(parentPhysical, {radius, color, layer, outline: 2.5});
    // bite disc rides slightly above and to one side, same family as the sweater
    const bitePos = this.stub(parentPhysical, {length: offset, angle: 0.15, layer: layer + 0.2});
    this.plainBall(bitePos, {radius: bite, color: biteColor, layer: layer + 0.3});
  }

  /** Four-point sparkle (star approximation): center dot plus four points. */
  sparkle(parentPhysical, {radius = 5, color, layer, point = 3.4}) {
    this.plainBall(parentPhysical, {radius, color, layer});
    for (const a of [0, Math.PI / 2, Math.PI, -Math.PI / 2]) {
      const tip = this.stub(parentPhysical, {length: radius * 0.9, angle: a, layer});
      this.plainBall(tip, {radius: point, color, layer});
    }
  }

  figure(figure_type_id, name) {
    const ordered = [...this.segments].sort((a, b) => a._layer - b._layer || a.segment_id - b.segment_id);
    ordered.forEach((seg, i) => {seg.z_order = i + 1;});
    const segments = this.segments.map(({_layer, _visual, ...seg}) => seg);
    return {figure_type_id, name: name || this.name, segment_count: segments.length, segments,
      polyfills: [], image_assets: [], text_assets: []};
  }

  restAngles() { return this.segments.map(seg => seg.angle_rad); }

  /** Expand visual-node absolute angles into a per-segment array. */
  poseAngles(nodeAngles) {
    return this.segments.map(seg => {
      const node = this.nodes.get(seg._visual);
      if (node?.ball || node?.ring) return nodeAngles.get(seg._visual) ?? 0;
      return nodeAngles.get(seg._visual) ?? node?.restAngle ?? seg.angle_rad;
    });
  }

  visualCount() { return this._visualCount; }

  visualsSince(n) {
    const out = [];
    for (let i = n + 1; i <= this._visualCount; i++) out.push(i);
    return out;
  }

  /** Physical segment ids belonging to a visual node. */
  segmentIds(visualId) { return [...this.nodes.get(visualId).segIds]; }

  /** Rest (definition) length of every physical segment, in segment-array order. */
  restLengths() { return this.segments.map(s => s.length); }
}

/** Modern Pivot v5 .stk writer (aff7f8 stream, zlib, marker 0x79). */
export function writeStk(figure) {
  const segs = [...figure.segments].sort((a, b) => a.segment_id - b.segment_id);
  const flags = 0b10100000;
  const payload = [flags];
  pushU16(payload, segs.length);
  for (const s of segs) {
    pushU16(payload, s.parent_id);
    pushF32(payload, s.length);
    pushF64(payload, s.angle_rad);
    pushF32(payload, s.thickness);
    payload.push(s.primitive_code & 0xff, s.aux_code & 0xff);
    payload.push(s.color_rgb[0] & 0xff, s.color_rgb[1] & 0xff, s.color_rgb[2] & 0xff);
    payload.push(s.transparency & 0xff);
  }
  pushU16(payload, 0); // bends
  pushU16(payload, 0); // polyfills
  for (const s of segs) pushU16(payload, s.z_order);
  return Buffer.concat([Buffer.from([0x79]), deflateSync(Buffer.from(payload))]);
}

const pushU16 = (arr, v) => arr.push(v & 0xff, (v >> 8) & 0xff);
function pushF32(arr, v) { const b = Buffer.alloc(4); b.writeFloatLE(v); arr.push(...b); }
function pushF64(arr, v) { const b = Buffer.alloc(8); b.writeDoubleLE(v); arr.push(...b); }
