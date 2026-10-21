import { PARTS, buildWords } from "./script.js";
import { SHOTS } from "./timeline.js";
import { POSES } from "./poses.js";
import { SCENES } from "./scenes.js";

const W = 1920, H = 1080;

const $ = (id) => document.getElementById(id);
const stage = $("stage");
const stageWrap = $("stageWrap");
const canvas = $("scene");
const ctx = canvas.getContext("2d");
const ellyEl = $("elly");
const captionEl = $("caption");
const cardEl = $("card");
const subEl = $("subtitle");
const usePlates = $("usePlates");

// The brief: "8 independent WAV files; each part begins at LOCAL 0:00. Agent
// concatenates WAVs in precise order." So each part gets its own local timeline
// and they are laid end to end to make the global one.
const parts = PARTS.map((p, i) => {
  const w = buildWords(p);
  return { ...p, index: i, words: w, dur: w[w.length - 1].t1 + 0.9 };
});
let acc = 0;
for (const p of parts) { p.offset = acc; acc += p.dur; }
const TOTAL = acc;

// Flattened word list for subtitles, shifted into global time.
const words = parts.flatMap((p) =>
  p.words.map((w) => ({ ...w, t0: w.t0 + p.offset, t1: w.t1 + p.offset })));

// ---------------------------------------------------------------- alignment
// Locate a cue phrase in the word stream. This is the browser equivalent of the
// kit's cues.py T(v, "phrase"): shots are anchored to spoken words, never to
// the storyboard's evenly-allocated placeholder windows.
// Fold curly punctuation to ASCII: storyboard cues use ’ while the script uses '.
const norm = (s) => s
  .replace(/[\u2018\u2019]/g, "'").replace(/[\u201C\u201D]/g, '"')
  .toLowerCase().replace(/[^a-z0-9'\s]/g, "").trim();

// Storyboard cues are excerpts and often elide across sentences, so the full
// phrase may not exist contiguously in the script. Try the whole phrase, then
// progressively shorter prefixes down to 3 words.
function findPhrase(partIndex, phrase) {
  const toks = parts[partIndex].words.map((x) => norm(x.w));
  const want = norm(phrase).split(/\s+/).filter(Boolean);
  if (!want.length) return -1;
  const floor = Math.min(3, want.length); // short cues like "October 1929." are 2 words
  for (let len = want.length; len >= floor; len--) {
    const sub = want.slice(0, len);
    for (let i = 0; i + sub.length <= toks.length; i++) {
      let ok = true;
      for (let j = 0; j < sub.length; j++) {
        if (!toks[i + j].startsWith(sub[j])) { ok = false; break; }
      }
      if (ok) return i;
    }
  }
  return -1;
}

const shots = SHOTS.map((s) => {
  const pi = s.part == null ? 0 : s.part;
  return { ...s, pi, wi: findPhrase(pi, s.cue) };
});
// Assign times in story order and force monotonicity. A cut that lands before
// the previous one is worse than an approximated one, so an unmatched cue is
// placed at the end of the preceding shot rather than allowed to jump back.
let cursor = 0;
shots.forEach((s, i) => {
  if (s.wi < 0) console.warn(`cue not found for p${s.pi}/${s.id}: "${s.cue}"`);
  const found = s.wi >= 0 ? parts[s.pi].offset + parts[s.pi].words[s.wi].t0 : null;
  s.cueMatched = found !== null;
  s.t0 = found !== null ? Math.max(found, cursor) : cursor;
  cursor = s.t0;
});
shots.forEach((s, i) => {
  const nxt = shots[i + 1];
  s.t1 = nxt ? nxt.t0 : TOTAL;
  if (s.t1 <= s.t0) s.t1 = s.t0 + 1; // never leave a zero-length shot
});

const warnings = shots.filter((s) => s.wi < 0);
const perPart = {};
shots.forEach((s) => { perPart[s.pi] = (perPart[s.pi] || 0) + 1; });
$("timingNote").innerHTML =
  `${parts.length} parts · ${shots.length} shots · word-cue aligned ` +
  `(<b>synthetic timings</b> — no VO WAVs in repo; replaced by asr/align words.json)` +
  ` · ${warnings.length ? `<b>${warnings.length} cue(s) unmatched</b>` : "all cues matched"}` +
  ` · parts: ${Object.values(perPart).join("/")}`;

// ------------------------------------------------------------------ easing
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);
const clamp01 = (t) => Math.max(0, Math.min(1, t));

// ------------------------------------------------------------------ camera
function camera(shot, p) {
  const c = shot.camera || { type: "static" };
  let scale = 1, dx = 0, dy = 0;

  switch (c.type) {
    case "pushIn":
      scale = 1 + (c.to - 1) * easeInOut(p);
      break;
    case "pullOut":
      scale = c.from + (c.to - c.from) * easeInOut(p);
      break;
    case "snapZoom": {
      // fast settle, then the slow creep specified for the shot
      const s = clamp01(p / (c.settle || 0.35));
      const settled = c.from + (1 - c.from) * easeOut(s);
      const creep = (c.then - 1) * easeInOut(clamp01((p - (c.settle || 0.35)) / 0.65));
      scale = settled * (1 + creep);
      break;
    }
    case "pan":
      dx = -(c.dx || 0) * easeInOut(p);
      scale = 1 + ((c.zoom || 1) - 1) * easeInOut(p) * ((c.then ? -1 : 1));
      if (c.then) scale = 1 + (c.then - 1) * easeInOut(p) + ((c.zoom || 1) - 1) * easeInOut(p);
      break;
    case "parallax":
      dx = -(c.dx || 0) * Math.sin(p * Math.PI * 2) * 0.5;
      break;
    case "pulse": {
      // n rhythmic push-ins, the "two rhythmic push-ins" of S09
      const k = clamp01(p * (c.n || 2)) % 1;
      scale = 1 + (c.amount || 0.08) * Math.sin(k * Math.PI);
      break;
    }
    case "dollyInOut": {
      const a = c.at || 0.6;
      scale = p < a
        ? 1 + (c.inn - 1) * easeInOut(p / a)
        : c.inn + (c.out - c.inn) * easeInOut((p - a) / (1 - a));
      break;
    }
    case "sway":
      dx = -(c.dx || 0) * Math.sin(p * Math.PI * 2) * 0.6;
      scale = 1 + ((c.zoom || 1) - 1) * easeInOut(p);
      break;
    default:
      scale = 1;
  }

  // Impact shake: only where the storyboard calls for a crash impact.
  if (shot.shake && p >= shot.shake.from && p <= shot.shake.to) {
    const k = 1 - (p - shot.shake.from) / (shot.shake.to - shot.shake.from);
    const a = shot.shake.amp * k;
    dx += (Math.random() - 0.5) * a * 2;
    dy += (Math.random() - 0.5) * a * 2;
  }
  return { scale, dx, dy };
}

// --------------------------------------------------------------------- Elly
let ellyImg = new Image();
let ellyLoaded = "";

function ellyPose(shot, p) {
  const list = shot.elly;
  let cur = list[0];
  for (const e of list) if (p >= e.t) cur = e;
  return cur;
}

function drawElly(shot, p, cam, time) {
  const e = ellyPose(shot, p);
  const src = POSES[e.pose];
  if (!src) return;
  if (ellyLoaded !== src) {
    ellyLoaded = src;
    ellyImg.src = src;
  }
  // Idle life: gentle bob + breath so she is never a frozen cutout.
  const bob = Math.sin(time * 2.1) * 7;
  const breathe = 1 + Math.sin(time * 2.1) * 0.006;
  // Entrance over the first 0.35s of a shot.
  const enter = clamp01(p / 0.14);
  const rise = (1 - easeOut(enter)) * 40;

  // Camera affects her only partially: she must stay readable and uncropped.
  const px = (cam.dx * 0.35) + (e.x - W / 2) * (1 + (cam.scale - 1) * 0.35) + W / 2;
  const py = e.y + bob + rise;
  const h = e.h * breathe * (1 + (cam.scale - 1) * 0.45);

  ellyEl.style.height = `${h}px`;
  ellyEl.style.width = "auto";
  ellyEl.style.left = "0px";
  ellyEl.style.top = "0px";
  ellyEl.style.transform =
    `translate(${px - (ellyEl.naturalWidth ? (ellyEl.naturalWidth / ellyEl.naturalHeight) * h : h * 0.7) / 2}px, ${py - h}px)` +
    (e.flip ? " scaleX(-1)" : "");
  ellyEl.style.opacity = enter;
}

// ------------------------------------------------------------------ drawing
// Generated plates are preferred; the procedural painter is the fallback for
// shots whose art has not been made yet. The toggle lets you A/B them.
const plateCache = new Map();
function getPlate(src) {
  if (!plateCache.has(src)) {
    const im = new Image();
    im.src = src;
    plateCache.set(src, im);
  }
  return plateCache.get(src);
}

function drawScene(shot, p, time) {
  ctx.clearRect(0, 0, W, H);
  if (usePlates.checked && shot.plate) {
    const im = getPlate(shot.plate);
    if (im.complete && im.naturalWidth) {
      ctx.drawImage(im, 0, 0, W, H);
      return;
    }
  }
  const fn = SCENES[shot.scene];
  if (!fn) { ctx.fillStyle = "#222"; ctx.fillRect(0, 0, W, H); return; }
  ctx.save();
  fn(ctx, p, time);
  ctx.restore();
}

function drawSubtitle(t) {
  const idx = words.findIndex((w) => t >= w.t0 && t < w.t1);
  if (idx < 0) { subEl.innerHTML = ""; return; }
  const from = Math.max(0, idx - 5);
  const to = Math.min(words.length, idx + 7);
  subEl.innerHTML = words.slice(from, to)
    .map((w) => `<span class="w${w === words[idx] ? " on" : ""}">${escapeHtml(w.w)}</span>`)
    .join(" ");
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ------------------------------------------------------------------- render
let t = 0, playing = false, last = 0;

function activeShot(t) {
  for (let i = shots.length - 1; i >= 0; i--) if (t >= shots[i].t0) return i;
  return 0;
}

function render(now) {
  const dt = last ? (now - last) / 1000 : 0;
  last = now;
  if (playing) {
    t += dt;
    if (t >= TOTAL) { t = TOTAL; playing = false; $("play").textContent = "▶ Play"; }
  }

  const i = activeShot(t);
  const shot = shots[i];
  const p = clamp01((t - shot.t0) / Math.max(0.001, shot.t1 - shot.t0));
  const time = t;

  drawScene(shot, p, time);
  const cam = camera(shot, p);
  canvas.style.transform =
    `translate(${cam.dx}px, ${cam.dy}px) scale(${cam.scale})`;
  drawElly(shot, p, cam, time);
  drawSubtitle(t);

  // caption: on shortly after the cut, off before it, never over Elly's face
  const cOn = p > 0.06 && p < 0.92;
  captionEl.textContent = cOn ? shot.caption : "";
  captionEl.style.opacity = cOn ? 1 : 0;

  // chapter card: first 2.6s of each part, local to that part
  const curPart = parts.find((p) => t >= p.offset && t < p.offset + p.dur) || parts[parts.length - 1];
  cardEl.textContent = curPart.card;
  cardEl.classList.toggle("on", t - curPart.offset < 2.6);

  $("clock").textContent = fmt(t);
  $("scrub").value = Math.round((t / TOTAL) * 1000);
  $("hShot").textContent = `p${shot.pi} ${shot.id}  ${shot.t0.toFixed(2)}–${shot.t1.toFixed(2)}s`;
  $("hCam").textContent = shot.camera ? shot.camera.type : "static";
  $("hPose").textContent = ellyPose(shot, p).pose;
  $("hBeat").textContent = shot.beat;

  document.querySelectorAll(".shot").forEach((el, k) => el.classList.toggle("on", k === i));

  requestAnimationFrame(render);
}

function fmt(s) {
  const m = Math.floor(s / 60);
  const r = s - m * 60;
  return `${m}:${r < 10 ? "0" : ""}${r.toFixed(2)}`;
}

// ------------------------------------------------------------------- layout
function fit() {
  const avail = Math.min(stageWrap.parentElement.clientWidth, 1460) - 4;
  const s = Math.max(0.28, Math.min(1, avail / W));
  stage.style.setProperty("--s", s);
  stageWrap.style.height = `${Math.round(H * s)}px`;
}
window.addEventListener("resize", fit);
fit();

// ----------------------------------------------------------------- controls
$("play").onclick = () => {
  if (t >= TOTAL) t = 0;
  playing = !playing;
  $("play").textContent = playing ? "❚❚ Pause" : "▶ Play";
};
$("restart").onclick = () => { t = 0; playing = false; $("play").textContent = "▶ Play"; };
$("scrub").oninput = (e) => { t = (+e.target.value / 1000) * TOTAL; playing = false; $("play").textContent = "▶ Play"; };

// --------------------------------------------------------------- shot list
$("shotlist").innerHTML = shots.map((s, i) => `
  <div class="shot" data-i="${i}">
    <div class="id">p${s.pi ?? 0} · ${s.id} · ${s.camera ? s.camera.type : "static"}</div>
    <div class="meta">${s.t0.toFixed(1)}s · ${s.scene} · ${(s.t1 - s.t0).toFixed(1)}s</div>
    <div class="cap">${escapeHtml(s.caption)}</div>
  </div>`).join("");
$("shotlist").onclick = (e) => {
  const el = e.target.closest(".shot");
  if (!el) return;
  t = shots[+el.dataset.i].t0 + 0.01;
  playing = false;
  $("play").textContent = "▶ Play";
};

requestAnimationFrame(render);
