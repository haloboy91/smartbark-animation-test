#!/usr/bin/env node
/**
 * Headless smoke test for the EP015 web rig.
 *
 * There is no browser in this sandbox, so this shims just enough DOM/canvas to
 * actually execute the module graph and call paintFrame(). It answers the
 * questions static checks cannot: does the graph import, do frames render
 * without throwing, does the proof sheet build, and do the storyboard cues
 * resolve against the script?
 *
 * It lives in the repo rather than /tmp on purpose - /tmp was wiped once and
 * took an earlier version of this with it.
 *
 *   node tools/smoke_test.mjs
 */
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const JS = path.join(__dirname, "..", "web", "js");

// ------------------------------------------------------------- canvas shim
const CTX_METHODS = [
  "clearRect", "drawImage", "fillRect", "fillText", "strokeText", "strokeRect",
  "save", "restore", "scale", "translate", "rotate", "beginPath", "closePath",
  "moveTo", "lineTo", "arc", "arcTo", "ellipse", "rect", "roundRect",
  "quadraticCurveTo", "bezierCurveTo", "fill", "stroke", "clip",
  "setTransform", "resetTransform", "transform", "setLineDash",
  "createLinearGradient", "createRadialGradient", "createPattern",
];
function makeCtx(w, h) {
  const ctx = { canvas: { width: w, height: h } };
  for (const m of CTX_METHODS) ctx[m] = () => {
    if (m === "createLinearGradient") return { addColorStop() {} };
    return undefined;
  };
  ctx.measureText = (s) => ({ width: (s ? s.length : 0) * 11 });
  return ctx;
}

// --------------------------------------------------------------- element shim
function makeEl(id) {
  const el = {
    id,
    textContent: "",
    innerHTML: "",
    value: 0,
    checked: true,
    width: 1920,
    height: 1080,
    style: {},
    dataset: {},
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    getContext: () => makeCtx(1920, 1080),
    addEventListener() {},
    removeEventListener() {},
    appendChild() {},
    getBoundingClientRect: () => ({ width: 1920, height: 1080, top: 0, left: 0 }),
    // Node 22 has a real Blob; proofsheet.js feeds this to createObjectURL,
    // which type-checks its argument.
    toBlob(cb) { cb(new Blob([new Uint8Array([1, 2, 3, 4])], { type: "image/png" })); },
    onclick: null,
    oninput: null,
  };
  return el;
}

const elements = new Map();
global.document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, makeEl(id));
    return elements.get(id);
  },
  createElement(tag) {
    return tag === "canvas"
      ? Object.assign(makeEl("canvas"), { getContext: () => makeCtx(1920, 1080) })
      : makeEl(tag);
  },
  addEventListener() {},
};

// Images resolve immediately and empty; the compositor only needs .width/.height
// and a truthy object in the plate/pose maps.
global.Image = class Image {
  constructor() { this.width = 1376; this.height = 768; this.complete = true; }
  set src(v) { this._src = v; }
  get src() { return this._src; }
  addEventListener(ev, fn) { if (ev === "load") setTimeout(fn, 0); }
};

global.window = {
  addEventListener() {},
  devicePixelRatio: 1,
  requestAnimationFrame: () => 0,
};
global.requestAnimationFrame = () => 0;
global.performance = global.performance || { now: () => Date.now() };
global.URL.createObjectURL = global.URL.createObjectURL || ((b) => `blob:stub/${b.size}`);

// ------------------------------------------------------------------- run
(async () => {
  const { paintFrame } = await import(path.join(JS, "compose.js"));
  const { buildProofSheet } = await import(path.join(JS, "proofsheet.js"));
  const { PARTS, buildWords, partDuration, TIMING_SOURCE, REAL_DURATIONS } =
    await import(path.join(JS, "script.js"));
  const { SHOTS } = await import(path.join(JS, "timeline.js"));
  const { POSES } = await import(path.join(JS, "poses.js"));
  const { buildEpisode } = await import(path.join(JS, "episode.js"));

  console.log("module loaded OK");
  console.log(`timing source: ${TIMING_SOURCE}`);

  // Use the production timing model, not a lookalike. Duplicating it here is
  // what let the renderer and preview diverge in the first place.
  const ep = buildEpisode({ onWarning: (m) => console.log(m) });
  const { shots, parts, words, TOTAL, activeShot, unmatched: un } = ep;
  let unmatched = un.length;

  const plates = new Map();
  const poses = new Map();
  shots.forEach((s) => { if (s.plate) plates.set(s.plate, new global.Image()); });
  Object.keys(POSES).forEach((k) => poses.set(k, new global.Image()));

  const state = { shots, parts, words, plates, poses, usePlates: true,
                  activeShot: (t) => { for (let i = shots.length - 1; i >= 0; i--) if (t >= shots[i].t0) return i; return 0; } };

  const ctx = makeCtx(1920, 1080);
  const N = 9;
  for (let i = 0; i < N; i++) {
    const t = (TOTAL * i) / (N - 1);
    paintFrame(ctx, t, state);
  }
  console.log(`frames rendered without throwing: ${N}`);

  const blob = await buildProofSheet(state, {});
  console.log(`proof sheet built: ${blob}`);

  // ---- invariants
  const problems = [];
  const negative = shots.filter((s) => s.t1 <= s.t0);
  if (negative.length) problems.push(`${negative.length} zero/negative-length shots`);
  for (let i = 1; i < shots.length; i++) {
    if (shots[i].pi === shots[i - 1].pi && shots[i].t0 < shots[i - 1].t0) {
      problems.push(`non-monotonic at shot ${i} (p${shots[i].pi} ${shots[i].id})`);
      break;
    }
  }
  const overflow = shots.filter((s) => s.t1 > TOTAL + 0.01);
  if (overflow.length) problems.push(`${overflow.length} shots past end of audio`);
  const missingPlate = shots.filter((s) => s.plate && !fs.existsSync(path.join(__dirname, "..", s.plate)));
  if (missingPlate.length) problems.push(`${missingPlate.length} shots point at a missing plate file`);

  const arted = shots.filter((s) => s.plate).length;
  console.log("");
  console.log(`shots           : ${shots.length}`);
  console.log(`arted           : ${arted} (${Math.round((100 * arted) / shots.length)}%)`);
  console.log(`cues matched    : ${shots.length - unmatched}/${shots.length}`);
  console.log(`runtime         : ${(TOTAL / 60).toFixed(2)} min (${TOTAL.toFixed(2)}s)`);
  console.log(`part durations  : ${REAL_DURATIONS.map((d) => d.toFixed(2)).join(" / ")}`);

  if (problems.length) {
    console.log("\nPROBLEMS:");
    problems.forEach((p) => console.log(`  - ${p}`));
    process.exit(1);
  }
  if (unmatched) console.log(`\n${unmatched} cue(s) unmatched (see above)`);
  console.log("\nNO RUNTIME ERRORS");
})().catch((e) => { console.error("FAILED:", e); process.exit(1); });
