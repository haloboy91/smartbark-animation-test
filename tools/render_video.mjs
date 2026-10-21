#!/usr/bin/env node
/**
 * Headless MP4 renderer for Smart Bark episodes.
 *
 * Draws every frame through the SAME paintFrame() the browser preview uses,
 * so what you review on screen is what gets encoded. Frames are piped straight
 * to ffmpeg as raw RGBA - no intermediate image files.
 *
 *   node tools/render_video.mjs --from 0 --to 30 --out out/preview.mp4
 *   node tools/render_video.mjs --part 0 --out out/part0.mp4
 *   node tools/render_video.mjs --out out/full.mp4 --segment 120   # chunked
 *
 * Requires: npm install   (pulls @napi-rs/canvas)
 *           ffmpeg        (imageio-ffmpeg, or on PATH)
 */
import { createCanvas, loadImage, GlobalFonts } from "@napi-rs/canvas";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..");
const JS = path.join(ROOT, "web", "js");

const arg = (name, dflt) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
};
const has = (name) => process.argv.includes(`--${name}`);

const FROM = parseFloat(arg("from", "0"));
const TO = parseFloat(arg("to", "30"));
const PART = arg("part", null);
const OUT = arg("out", "out/preview.mp4");
const FPS = parseInt(arg("fps", "30"), 10);
const CRF = parseInt(arg("crf", "25"), 10);
const SEGMENT = arg("segment", null) ? parseFloat(arg("segment")) : null;
const SCALE = parseFloat(arg("scale", "1"));
const VO = arg("vo", "assets/audio/vo_full.wav");
const MUTE = has("mute");

// ------------------------------------------------------------------ ffmpeg
function ffmpegBin() {
  const onPath = spawnSync("ffmpeg", ["-version"], { stdio: "ignore" });
  if (onPath.status === 0) return "ffmpeg";
  // imageio-ffmpeg ships a static binary; find it without importing python.
  const cands = [
    "/home/user/.venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries",
    "/home/user/.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries",
  ];
  for (const d of cands) {
    if (!fs.existsSync(d)) continue;
    const b = fs.readdirSync(d).find((f) => f.startsWith("ffmpeg-"));
    if (b) return path.join(d, b);
  }
  return null;
}

// ------------------------------------------------------------------- fonts
// The kit ships Luckiest Guy (chapter cards / pop captions) and Lato
// (subtitles). Without these the compositor falls back to a generic sans and
// the type no longer matches the Smart Bark look.
const FONT_DIR = path.join(ROOT, "kit", "Smart_Bark_Kit_v2", "fonts");
let fontsLoaded = 0;
for (const [file, family] of [
  ["LuckiestGuy.ttf", "Luckiest Guy"],
  ["Lato-Bold.ttf", "Lato"],
  ["Lato-Black.ttf", "Lato"],
]) {
  const p = path.join(FONT_DIR, file);
  if (fs.existsSync(p) && GlobalFonts.registerFromPath(p, family)) fontsLoaded++;
}

// ------------------------------------------------------------------- load
const { paintFrame, W, H } = await import(pathToFileURL(path.join(JS, "compose.js")).href);
const { buildEpisode } = await import(pathToFileURL(path.join(JS, "episode.js")).href);
const { POSES } = await import(pathToFileURL(path.join(JS, "poses.js")).href);

const warnings = [];
const ep = buildEpisode({ onWarning: (m) => warnings.push(m) });

// Restrict to one part if asked.
let from = FROM, to = TO;
if (PART !== null) {
  const i = parseInt(PART, 10);
  from = ep.parts[i].offset;
  to = from + ep.parts[i].dur;
}
to = Math.min(to, ep.TOTAL);
from = Math.max(0, Math.min(from, to));

// ----------------------------------------------------------------- assets
const missing = [];
async function fill(map, entries) {
  for (const [key, rel] of entries) {
    if (!rel || map.has(key)) continue;
    const abs = path.join(ROOT, rel);
    if (!fs.existsSync(abs)) { missing.push(rel); continue; }
    map.set(key, await loadImage(abs));
  }
}
const plates = new Map();
const poses = new Map();
await fill(plates, ep.shots.filter((s) => s.plate).map((s) => [s.plate, s.plate]));
await fill(poses, Object.entries(POSES));

// Any shot without a plate would fall through to the procedural painter, which
// is a placeholder - the brief forbids those in a deliverable. Report, loudly.
const bare = ep.shots.filter((s) => !s.plate && s.t1 > from && s.t0 < to);

const state = {
  shots: ep.shots,
  parts: ep.parts,
  words: ep.words,
  plates,
  poses,
  usePlates: true,
  activeShot: ep.activeShot,
};

// ------------------------------------------------------------------ render
const OW = Math.round(W * SCALE), OH = Math.round(H * SCALE);
const canvas = createCanvas(OW, OH);
const ctx = canvas.getContext("2d");
if (SCALE !== 1) ctx.scale(SCALE, SCALE);

function encode(rangeFrom, rangeTo, outFile) {
  return new Promise((resolve, reject) => {
    const ff = spawn(FFMPEG, [
      "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
      "-s", `${OW}x${OH}`, "-r", String(FPS), "-i", "-",
      "-an",
      "-c:v", "libx264", "-preset", "veryfast", "-crf", String(CRF),
      "-pix_fmt", "yuv420p", "-movflags", "+faststart",
      outFile,
    ], { stdio: ["pipe", "ignore", "pipe"] });

    let err = "";
    ff.stderr.on("data", (d) => { err += d.toString(); });
    ff.on("error", reject);
    ff.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`ffmpeg exit ${code}\n${err.slice(-1500)}`));
    });

    const nFrames = Math.max(1, Math.round((rangeTo - rangeFrom) * FPS));
    void rangeFrom;
    (async () => {
      for (let i = 0; i < nFrames; i++) {
        const t = rangeFrom + i / FPS;
        paintFrame(ctx, t, state);
        const px = ctx.getImageData(0, 0, OW, OH).data;
        if (!ff.stdin.write(Buffer.from(px.buffer, px.byteOffset, px.byteLength))) {
          await new Promise((r) => ff.stdin.once("drain", r));
        }
        if (i % 30 === 0) {
          process.stdout.write(
            `\r  frame ${i}/${nFrames}  t=${t.toFixed(1)}s   `);
        }
      }
      ff.stdin.end();
    })().catch(reject);
  });
}

const FFMPEG = ffmpegBin();
if (!FFMPEG) {
  console.error("No ffmpeg found. Install: /home/user/.venv/bin/pip install imageio-ffmpeg");
  process.exit(1);
}

fs.mkdirSync(path.dirname(path.join(ROOT, OUT)), { recursive: true });

console.log(`rendering ${(to - from).toFixed(2)}s @ ${FPS}fps ${OW}x${OH} crf${CRF}`);
console.log(`  plates loaded : ${plates.size}`);
console.log(`  poses loaded  : ${poses.size}`);
if (missing.length) {
  console.log(`  MISSING FILES : ${missing.length}`);
  missing.slice(0, 5).forEach((m) => console.log(`    ${m}`));
}
if (bare.length) {
  console.log(`  NO PLATE (procedural fallback): ${bare.length} shot(s) in range`);
  bare.slice(0, 8).forEach((s) => console.log(`    p${s.pi} ${s.id}`));
}
warnings.forEach((w) => console.log(`  ${w}`));

/**
 * Mux the real VO onto a video-only file.
 *
 * The narration is one concatenated track (assets/audio/vo_full.wav) built from
 * v00..v07 in order, so a range is just a -ss/-t window into it. Audio is never
 * resampled or stretched: the brief requires each part's exact WAV runtime.
 */
function mux(videoOnly, outFile, rangeFrom, rangeTo) {
  const dur = rangeTo - rangeFrom;
  if (MUTE || !fs.existsSync(path.join(ROOT, VO))) {
    if (!MUTE) console.warn(`  (no VO at ${VO} - exporting silent)`);
    const r = spawnSync(FFMPEG, ["-y", "-i", videoOnly, "-c", "copy", outFile],
                        { stdio: "ignore" });
    fs.rmSync(videoOnly, { force: true });
    return r.status === 0;
  }
  const r = spawnSync(FFMPEG, [
    "-y",
    "-i", videoOnly,
    "-ss", String(rangeFrom), "-t", String(dur),
    "-i", path.join(ROOT, VO),
    "-map", "0:v:0", "-map", "1:a:0",
    "-c:v", "copy",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
    "-shortest",
    "-movflags", "+faststart",
    outFile,
  ], { stdio: ["ignore", "ignore", "pipe"] });
  fs.rmSync(videoOnly, { force: true });
  if (r.status !== 0) {
    console.error(r.stderr?.toString().slice(-1200) || "mux failed");
  }
  return r.status === 0;
}

const t0 = Date.now();
const absOut = path.join(ROOT, OUT);

if (!SEGMENT) {
  const tmp = absOut.replace(/\.mp4$/, ".video.mp4");
  await encode(from, to, tmp);
  if (!mux(tmp, absOut, from, to)) process.exit(1);
} else {
  // Chunked: keeps peak memory flat and survives long episodes.
  const segs = [];
  let s = from, n = 0;
  while (s < to) {
    const e = Math.min(to, s + SEGMENT);
    const f = path.join(path.dirname(absOut), `.seg_${String(n).padStart(3, "0")}.mp4`);
    console.log(`\n  segment ${n}: ${s.toFixed(1)}s -> ${e.toFixed(1)}s`);
    await encode(s, e, f);
    segs.push(f);
    s = e; n++;
  }
  const list = path.join(path.dirname(absOut), "segs.txt");
  fs.writeFileSync(list, segs.map((f) => `file '${path.basename(f)}'`).join("\n"));
  const joined = absOut.replace(/\.mp4$/, ".video.mp4");
  const r = spawnSync(FFMPEG, ["-y", "-f", "concat", "-safe", "0", "-i", list,
                               "-c", "copy", joined], { stdio: "inherit" });
  segs.forEach((f) => fs.rmSync(f, { force: true }));
  fs.rmSync(list, { force: true });
  if (r.status !== 0) process.exit(r.status ?? 1);
  if (!mux(joined, absOut, from, to)) process.exit(1);
}

const secs = (Date.now() - t0) / 1000;
const kb = (fs.statSync(absOut).size / 1024).toFixed(0);
console.log(`\nwrote ${OUT}  (${kb} KB, ${secs.toFixed(1)}s wall, ` +
            `${((to - from) / secs).toFixed(1)}x realtime)`);
