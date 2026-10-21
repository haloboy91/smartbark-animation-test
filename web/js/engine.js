import { PARTS, buildWords, partDuration, TIMING_SOURCE } from "./script.js";
import { SHOTS } from "./timeline.js";
import { POSES } from "./poses.js";
import { paintFrame, camera, ellyPose, W, H } from "./compose.js";
import { buildEpisode } from "./episode.js";

const $ = (id) => document.getElementById(id);
const stage = $("stage");
const stageWrap = $("stageWrap");
const frame = $("frame");
const ctx = frame.getContext("2d");
const usePlates = $("usePlates");

// ------------------------------------------------------------------ timing
// Shared with the MP4 renderer and the smoke test - see episode.js.
const { parts, words, shots, TOTAL, activeShot, unmatched } = buildEpisode({
  onWarning: (m) => console.warn(m),
});

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
