#!/usr/bin/env node
/**
 * Visual / editorial audit against the EP015 brief and Kit v2 conventions.
 *
 * Checks the things that are easy to get quietly wrong and hard to see in a
 * 20-minute export: Elly's size and placement, shot lengths, camera discipline,
 * and whether every shot actually has real art behind it.
 *
 * Imports the compositor's own functions rather than re-deriving the maths, so
 * the numbers here are the numbers the renderer uses.
 *
 *   node tools/audit_visual.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const JS = path.join(ROOT, "web", "js");

const { ellyPose, ellyHeight, camera, W, H } =
  await import(pathToFileURL(path.join(JS, "compose.js")).href);
const { buildEpisode } = await import(pathToFileURL(path.join(JS, "episode.js")).href);

const ep = buildEpisode({});
const problems = [];
const notes = [];

// ---------------------------------------------------------------- Elly size
let minH = Infinity, maxH = 0, tooBig = 0, tooSmall = 0, samples = 0;
const bigShots = [];
for (const s of ep.shots) {
  for (const p of [0, 0.25, 0.5, 0.75, 0.99]) {
    const e = ellyPose(s, p);
    const cam = camera(s, p);
    // breathe ranges 0.994..1.006; audit the extremes
    for (const b of [0.994, 1.006]) {
      const h = ellyHeight(e, cam, b);
      samples++;
      minH = Math.min(minH, h); maxH = Math.max(maxH, h);
      if (h / H > 0.5001) { tooBig++; bigShots.push(`p${s.pi} ${s.id} ${(h / H * 100).toFixed(0)}%`); }
      if (h / H < 0.3499) tooSmall++;
    }
  }
}
console.log(`Elly height      : ${(minH / H * 100).toFixed(1)}% - ${(maxH / H * 100).toFixed(1)}%  (brief 35-50%)`);
if (tooBig) problems.push(`Elly exceeds 50% height on ${tooBig}/${samples} samples`);
if (tooSmall) problems.push(`Elly under 35% height on ${tooSmall}/${samples} samples`);

// ------------------------------------------------------------ Elly placement
let offRight = 0, cropped = 0;
const offShots = [];
for (const s of ep.shots) {
  const e = ellyPose(s, 0.5);
  if (e.x < W * 0.62) { offRight++; offShots.push(`p${s.pi} ${s.id} x=${e.x}`); }
  // top of head must stay inside the frame
  const cam = camera(s, 0.5);
  const h = ellyHeight(e, cam, 1.006);
  if (e.y - h < 0 || e.y > H + 1) cropped++;
}
console.log(`Elly placement   : ${ep.shots.length - offRight}/${ep.shots.length} in right third`);
if (offShots.length) {
  notes.push(`${offShots.length} shot(s) place Elly left of the right third: ` +
             offShots.slice(0, 4).join(", "));
}
if (cropped) problems.push(`Elly cropped vertically on ${cropped} shots`);

// ------------------------------------------------------------- shot lengths
const lens = ep.shots.map((s) => s.t1 - s.t0);
const tooShort = ep.shots.filter((s) => s.t1 - s.t0 < 3);
const tooLong = ep.shots.filter((s) => s.t1 - s.t0 > 12);
const zero = ep.shots.filter((s) => s.t1 - s.t0 <= 0);
lens.sort((a, b) => a - b);
console.log(`Shot length      : min ${lens[0].toFixed(1)}s  median ${lens[lens.length >> 1].toFixed(1)}s  max ${lens[lens.length - 1].toFixed(1)}s`);
if (zero.length) problems.push(`${zero.length} zero-length shots`);
if (tooLong.length) notes.push(`${tooLong.length} shot(s) over the 12s cap (brief: never >12s)`);
if (tooShort.length) notes.push(`${tooShort.length} shot(s) under 3s - may read as strobing`);

// ------------------------------------------------------------------ camera
const cams = {};
ep.shots.forEach((s) => { cams[s.camera?.type || "static"] = (cams[s.camera?.type || "static"] || 0) + 1; });
const shaken = ep.shots.filter((s) => s.camera?.shake);
console.log(`Camera types     : ${Object.entries(cams).map(([k, v]) => `${k} ${v}`).join(", ")}`);
console.log(`Shake            : ${shaken.length} shot(s) (brief: only on crash impacts)`);

// ------------------------------------------------------------------- assets
const arted = ep.shots.filter((s) => s.plate);
const missing = arted.filter((s) => !fs.existsSync(path.join(ROOT, s.plate)));
const bare = ep.shots.filter((s) => !s.plate);
console.log(`Plates           : ${arted.length}/${ep.shots.length} shots (${Math.round(arted.length / ep.shots.length * 100)}%)`);
if (missing.length) problems.push(`${missing.length} shot(s) point at a missing plate file`);
if (bare.length) {
  problems.push(`${bare.length} shot(s) have NO plate - would render as procedural placeholder, which the brief forbids in the final video`);
}

const poses = await import(pathToFileURL(path.join(JS, "poses.js")).href);
const poseMissing = Object.entries(poses.POSES)
  .filter(([, v]) => !fs.existsSync(path.join(ROOT, v)));
console.log(`Poses            : ${Object.keys(poses.POSES).length} in manifest, ${poseMissing.length} missing`);
if (poseMissing.length) problems.push(`${poseMissing.length} pose(s) missing from disk`);

// ------------------------------------------------------------------ report
console.log("");
console.log(`runtime          : ${(ep.TOTAL / 60).toFixed(2)} min`);
console.log(`cues matched     : ${ep.shots.length - ep.unmatched.length}/${ep.shots.length}`);

if (notes.length) {
  console.log("\nNOTES:");
  notes.forEach((n) => console.log(`  - ${n}`));
}
if (problems.length) {
  console.log("\nPROBLEMS:");
  problems.forEach((p) => console.log(`  - ${p}`));
  process.exit(1);
}
console.log("\nVISUAL AUDIT PASSED");
