import { PARTS, buildWords } from "./script.js";
import { SHOTS } from "./timeline.js";
import { POSES } from "./poses.js";
import { paintFrame, camera, ellyPose, W, H } from "./compose.js";

const $ = (id) => document.getElementById(id);
const stage = $("stage");
const stageWrap = $("stageWrap");
const frame = $("frame");
const ctx = frame.getContext("2d");
const usePlates = $("usePlates");

// ------------------------------------------------------------------ timing
// The brief: "8 independent WAV files; each part begins at LOCAL 0:00. Agent
// concatenates WAVs in precise order." So each part owns a local timeline and
// they are laid end to end to form the global one.
const parts = PARTS.map((p, i) => {
  const w = buildWords(p);
  return { ...p, index: i, words: w, dur: w[w.length - 1].t1 + 0.9 };
});
let acc = 0;
for (const p of parts) { p.offset = acc; acc += p.dur; }
const TOTAL = acc;

const words = parts.flatMap((p) =>
  p.words.map((w) => ({ ...w, t0: w.t0 + p.offset, t1: w.t1 + p.offset })));

// ---------------------------------------------------------------- alignment
const norm = (s) => s
  .replace(/[\u2018\u2019]/g, "'").replace(/[\u201C\u201D]/g, '"')
  .toLowerCase().replace(/[^a-z0-9'\s]/g, "").trim();

// Storyboard cues are excerpts and often elide across sentences, so the whole
// phrase may not exist contiguously. Try the full phrase, then shorter prefixes.
function findPhrase(partIndex, phrase) {
  const toks = parts[partIndex].words.map((x) => norm(x.w));
  const want = norm(phrase).split(/\s+/).filter(Boolean);
  if (!want.length) return -1;
  const floor = Math.min(3, want.length); // "October 1929." is only 2 words
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

// Assign in story order and force monotonicity: a cut landing before the
// previous one is worse than an approximated one, so an unmatched cue is placed
// at the end of the preceding shot instead of being allowed to jump backwards.
let cursor = 0;
shots.forEach((s) => {
  if (s.wi < 0) console.warn(`cue not found for p${s.pi}/${s.id}: "${s.cue}"`);
  const found = s.wi >= 0 ? parts[s.pi].offset + parts[s.pi].words[s.wi].t0 : null;
  s.cueMatched = found !== null;
  s.t0 = found !== null ? Math.max(found, cursor) : cursor;
  cursor = s.t0;
});
shots.forEach((s, i) => {
  const nxt = shots[i + 1];
  s.t1 = nxt ? nxt.t0 : TOTAL;
  if (s.t1 <= s.t0) s.t1 = s.t0 + 1;
});

const unmatched = shots.filter((s) => !s.cueMatched);
const perPart = {};
shots.forEach((s) => { perPart[s.pi] = (perPart[s.pi] || 0) + 1; });
$("timingNote").innerHTML =
  `${parts.length} parts · ${shots.length} shots · word-cue aligned ` +
  `(<b>synthetic timings</b> — no VO WAVs in repo; replaced by asr/align words.json)` +
  ` · ${unmatched.length
      ? `<b>${unmatched.length} cue(s) unmatched</b>`
      : "all cues matched"}` +
  ` · ${(TOTAL / 60).toFixed(1)} min · shots/part: ${Object.values(perPart).join("/")}`;

// ----------------------------------------------------------------- assets
function preload(map, key, src) {
  if (!src || map.has(key)) return map.get(key);
  const im = new Image();
  im.src = src;
  map.set(key, im);
  return im;
}
const plates = new Map();
const poses = new Map();
shots.forEach((s) => { if (s.plate) preload(plates, s.plate, s.plate); });
shots.forEach((s) => s.elly.forEach((e) => preload(poses, e.pose, POSES[e.pose])));
// make sure every pose in the manifest is warm, not just the ones in shots
Object.entries(POSES).forEach(([k, v]) => preload(poses, k, v));

function activeShot(t) {
  for (let i = shots.length - 1; i >= 0; i--) if (t >= shots[i].t0) return i;
  return 0;
}

const state = {
  shots, parts, words, plates, poses,
  get usePlates() { return usePlates.checked; },
  activeShot,
};

// ------------------------------------------------------------------ render
let t = 0, playing = false, last = 0;

function render(now) {
  const dt = last ? (now - last) / 1000 : 0;
  last = now;
  if (playing) {
    t += dt;
    if (t >= TOTAL) { t = TOTAL; playing = false; $("play").textContent = "▶ Play"; }
  }

  paintFrame(ctx, t, state);

  const i = activeShot(t);
  const shot = shots[i];
  const p = Math.max(0, Math.min(1, (t - shot.t0) / Math.max(0.001, shot.t1 - shot.t0)));

  $("clock").textContent = fmt(t);
  $("scrub").value = Math.round((t / TOTAL) * 1000);
  $("hShot").textContent = `p${shot.pi} ${shot.id}  ${shot.t0.toFixed(2)}–${shot.t1.toFixed(2)}s`;
  $("hCam").textContent = shot.camera ? shot.camera.type : "static";
  $("hPose").textContent = ellyPose(shot, p).pose;
  $("hBeat").textContent = shot.beat || "—";

  document.querySelectorAll(".shot").forEach((el, k) => el.classList.toggle("on", k === i));
  requestAnimationFrame(render);
}

const fmt = (s) => {
  const m = Math.floor(s / 60), r = s - m * 60;
  return `${m}:${r < 10 ? "0" : ""}${r.toFixed(2)}`;
};

// ------------------------------------------------------------------ layout
function fit() {
  const avail = Math.min(stageWrap.parentElement.clientWidth, 1460) - 4;
  const s = Math.max(0.2, Math.min(1, avail / W));
  stage.style.setProperty("--s", s);
  stageWrap.style.height = `${Math.round(H * s)}px`;
}
window.addEventListener("resize", fit);
fit();

// ---------------------------------------------------------------- controls
$("play").onclick = () => {
  if (t >= TOTAL) t = 0;
  playing = !playing;
  $("play").textContent = playing ? "❚❚ Pause" : "▶ Play";
};
$("restart").onclick = () => { t = 0; playing = false; $("play").textContent = "▶ Play"; };
$("scrub").oninput = (e) => {
  t = (+e.target.value / 1000) * TOTAL;
  playing = false;
  $("play").textContent = "▶ Play";
};

// --------------------------------------------------------------- shot list
$("shotlist").innerHTML = shots.map((s, i) => `
  <div class="shot" data-i="${i}">
    <div class="id">p${s.pi} · ${s.id} · ${s.camera ? s.camera.type : "static"}</div>
    <div class="meta">${s.t0.toFixed(1)}s · ${s.plate ? "plate" : "proc"} · ${(s.t1 - s.t0).toFixed(1)}s</div>
    <div class="cap">${escapeHtml(s.caption || "")}</div>
  </div>`).join("");
$("shotlist").onclick = (e) => {
  const el = e.target.closest(".shot");
  if (!el) return;
  t = shots[+el.dataset.i].t0 + 0.01;
  playing = false;
  $("play").textContent = "▶ Play";
};

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ------------------------------------------------------------- proof sheet
$("proof").onclick = async () => {
  const btn = $("proof");
  btn.disabled = true;
  try {
    const { buildProofSheet } = await import("./proofsheet.js");
    btn.textContent = "rendering…";
    const url = await buildProofSheet(state);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ep015_proof_sheet.png";
    a.click();
    $("proofStatus").textContent =
      `${shots.length} proof frames · ${shots.filter((s) => s.plate).length} with plates`;
  } catch (err) {
    $("proofStatus").textContent = "proof sheet failed: " + err.message;
    console.error(err);
  } finally {
    btn.disabled = false;
    btn.textContent = "Proof sheet";
  }
};

requestAnimationFrame(render);
