/**
 * styk-rig.mjs — tiny rig DSL for authoring StykAnimate / Pivot v5 figures.
 *
 * A figure is a tree of segments rooted at node 0. Each segment runs from its
 * parent node to a new node: end = parent + length * (cos(angle), sin(angle)),
 * angles are absolute radians in a y-down coordinate system.
 *
 * Cartoon outlines are produced by pairing every visible primitive with a
 * slightly larger black primitive drawn first (lower z_order).
 */

import {deflateSync} from 'node:zlib';

export const OUTLINE = [26, 26, 28];
let nextZ = 0;

export class Rig {
  constructor(name) {
    this.name = name;
    this.nodes = new Map(); // visualId -> {parent, length, restAngle, segIds:[]}
    this.segments = []; // physical segments, segment_id = index+1
    this._visualCount = 0;
  }

  _addSegment({ parent, length, angle, thickness, color, prim, layer, visualId, transparent = false }) {
    const id = this.segments.length + 1;
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
      transparency: transparent ? 255 : 0,
      color_alpha: transparent ? 0 : 1,
      visible: !transparent && (thickness > 0.01 || prim > 0),
      z_order: ++nextZ,
      _layer: layer,
      _visual: visualId,
    });
    return id;
  }

  _newVisual(parent, length, angle) {
    const visualId = ++this._visualCount;
    this.nodes.set(visualId, { parent, length, restAngle: angle, segIds: [] });
    return visualId;
  }

  /** Resolve a parent reference (visual id | {stubId} | {ol,col} | 0) to physical segment ids. */
  _resolveParent(parent) {
    if (parent === 0 || parent == null) return { ol: 0, col: 0 };
    if (typeof parent === 'number') {
      const [ol, col] = this.nodes.get(parent).segIds;
      return { ol, col };
    }
    if (parent.stubId !== undefined) return { ol: parent.stubId, col: parent.stubId };
    if (parent.ol !== undefined) return { ol: parent.ol, col: parent.col };
    throw new Error('Unknown parent reference');
  }

  /** Visible thick round line (with black outline twin unless outline:false). Returns visual node id. */
  bone(parent, { length, angle, thickness, color, layer, outline = true }) {
    const visualId = this._newVisual(parent, length, angle);
    const parentNode = this._resolveParent(parent);
    const segIds = [];
    if (outline) segIds.push(this._addSegment({ parent: parentNode.ol, length, angle, thickness: thickness + 7, color: OUTLINE, prim: 0, layer, visualId }));
    segIds.push(this._addSegment({ parent: parentNode.col, length, angle, thickness, color, prim: 0, layer: layer + 0.1, visualId }));
    this.nodes.get(visualId).segIds = segIds;
    return visualId;
  }

  /** Invisible positioning segment (zero thickness). Returns {stubId} usable as parent. */
  stub(parentPhysical, { length, angle, layer = 0 }) {
    const visualId = ++this._visualCount;
    const parentNode = this._resolveParent(parentPhysical);
    const id = this._addSegment({ parent: parentNode.col, length, angle, thickness: 0, color: OUTLINE, prim: 0, layer, visualId, transparent: true });
    this.nodes.set(visualId, { parent: 0, length, restAngle: angle, segIds: [id], stub: true });
    return { stubId: id, visualId };
  }

  /** Filled circle centered on the given parent node (zero-length segment pair). */
  ball(parentPhysical, { radius, color, layer, outline = 3.5 }) {
    const visualId = ++this._visualCount;
    this.nodes.set(visualId, { parent: 0, length: 0, restAngle: 0, segIds: [], ball: true });
    const parentNode = this._resolveParent(parentPhysical);
    const segIds = [];
    if (outline > 0) segIds.push(this._addSegment({ parent: parentNode.ol, length: 0, angle: 0, thickness: 2 * (radius + outline), color: OUTLINE, prim: 3, layer, visualId }));
    segIds.push(this._addSegment({ parent: parentNode.col, length: 0, angle: 0, thickness: 2 * radius, color, prim: 3, layer: layer + 0.1, visualId }));
    this.nodes.get(visualId).segIds = segIds;
    return { ol: segIds[0], col: segIds.at(-1) };
  }

  /** Physical segment ids of a visual bone node. */
  _physical(visualId) {
    const [ol, col] = this.nodes.get(visualId).segIds;
    return { ol, col };
  }

  physical(visualId) { return this._physical(visualId); }
  physicalId(visualId) { return this.nodes.get(visualId).segIds[1] ?? this.nodes.get(visualId).segIds[0]; }

  /** Emit a StykAnimate figure definition. */
  figure(figure_type_id, name) {
    // Reassign z_order deterministically by layer so draw order is explicit.
    const ordered = [...this.segments].sort((a, b) => a._layer - b._layer || a.segment_id - b.segment_id);
    ordered.forEach((seg, i) => { seg.z_order = i + 1; });
    const segments = this.segments.map(({ _layer, _visual, ...seg }) => seg);
    return {
      figure_type_id,
      name: name || this.name,
      segment_count: segments.length,
      segments,
      polyfills: [],
      image_assets: [],
      text_assets: [],
    };
  }

  /** Rest-pose angle for every physical segment, indexed by segment array position. */
  restAngles() {
    return this.segments.map(seg => this.nodes.get(seg._visual)?.restAngle ?? seg.angle_rad);
  }

  /** Expand a map of visual-node angles into a full per-segment angle array. */
  poseAngles(nodeAngles) {
    return this.segments.map(seg => {
      const v = seg._visual;
      const node = this.nodes.get(v);
      if (node?.ball) return nodeAngles.get(v) ?? 0;
      return nodeAngles.get(v) ?? node?.restAngle ?? seg.angle_rad;
    });
  }

  /** All visual (posable) node ids. */
  posableNodes() { return [...this.nodes.keys()]; }

  visualCount() { return this._visualCount; }

  visualsSince(n) {
    const out = [];
    for (let i = n + 1; i <= this._visualCount; i++) out.push(i);
    return out;
  }
}

/** Serialize a rig's figure to a modern Pivot v5 .stk file (aff7f8 stream, zlib, marker 0x79). */
export function writeStk(figure) {
  const segs = [...figure.segments].sort((a, b) => a.segment_id - b.segment_id);
  // flags: bits 0..3 clear -> per-segment primitive, aux, color, transparency present
  //        bit4 clear -> explicit z-map ; bit5 set -> implicit ids ; bit7 set -> no secondary color
  const flags = 0b10100000;
  const payload = [];
  payload.push(flags);
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
  pushU16(payload, 0); // bend count
  pushU16(payload, 0); // polyfill count
  // z-map keyed by segment id order
  const zById = new Map(segs.map(s => [s.segment_id, s.z_order]));
  for (const s of segs) pushU16(payload, zById.get(s.segment_id));
  // zlib compression via Node's built-in deflate sync (zlib wrapper)
  return Buffer.concat([Buffer.from([0x79]), deflateSync(Buffer.from(payload))]);
}

function pushU16(arr, v) { arr.push(v & 0xff, (v >> 8) & 0xff); }
function pushF32(arr, v) {
  const b = Buffer.alloc(4); b.writeFloatLE(v); arr.push(...b);
}
function pushF64(arr, v) {
  const b = Buffer.alloc(8); b.writeDoubleLE(v); arr.push(...b);
}
