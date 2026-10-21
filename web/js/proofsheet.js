// Proof sheet: one proof frame per shot, laid out on a grid.
//
// The brief asks for proof frames at every chapter opening and on every
// dramatic change, and for contact sheets to be reviewed after each art batch.
// This renders the real composite - same paintFrame() the live preview uses -
// so a framing problem, a caption colliding with Elly, or a plate that does not
// leave the right third clear shows up here before anything is rendered.
import { paintFrame, W, H } from "./compose.js";

const COLS = 8;
const CELL_W = 420;
const CELL_H = Math.round((CELL_W * H) / W);   // keeps 16:9
const LABEL_H = 24;
const ROW_H = CELL_H + LABEL_H;

function ready(img) {
  if (!img) return Promise.resolve();
  if (img.complete && img.naturalWidth) return Promise.resolve();
  return new Promise((res) => {
    img.addEventListener("load", res, { once: true });
    img.addEventListener("error", res, { once: true });
  });
}

export async function buildProofSheet(state, { from = 0, to = null } = {}) {
  const shots = state.shots.slice(from, to ?? state.shots.length);

  // Every plate and pose must be decoded before we draw, or frames come out
  // with missing art and the sheet is useless as a review artefact.
  await Promise.all([
    ...[...state.plates.values()].map(ready),
    ...[...state.poses.values()].map(ready),
  ]);

  const rows = Math.ceil(shots.length / COLS);
  const out = document.createElement("canvas");
  out.width = COLS * CELL_W;
  out.height = rows * ROW_H;
  const octx = out.getContext("2d");
  octx.fillStyle = "#101215";
  octx.fillRect(0, 0, out.width, out.height);

  const one = document.createElement("canvas");
  one.width = W;
  one.height = H;
  const oneCtx = one.getContext("2d");

  shots.forEach((shot, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    const x = col * CELL_W;
    const y = row * ROW_H;

    // Sample just after the cut: the caption is up and the camera has started,
    // but the chapter card has cleared.
    const sample = shot.t0 + Math.min(0.42, 0.42) * (shot.t1 - shot.t0);
    paintFrame(oneCtx, sample, state);
    octx.drawImage(one, x, y, CELL_W, CELL_H);

    octx.fillStyle = shot.plate ? "#7f6a3a" : "#2a2d33";
    octx.fillRect(x, y + CELL_H, CELL_W, LABEL_H);
    octx.fillStyle = shot.plate ? "#ffe6b0" : "#8b929c";
    octx.font = '13px ui-monospace, SFMono-Regular, Menlo, monospace';
    octx.textBaseline = "middle";
    octx.fillText(`p${shot.pi} ${shot.id} ${shot.cueMatched ? "" : "[cue?]"}`, x + 5, y + CELL_H + LABEL_H / 2);

    octx.strokeStyle = "#000";
    octx.lineWidth = 1;
    octx.strokeRect(x + 0.5, y + 0.5, CELL_W - 1, CELL_H - 1);
  });

  return new Promise((resolve, reject) => {
    out.toBlob((blob) => {
      if (!blob) return reject(new Error("toBlob failed"));
      resolve(URL.createObjectURL(blob));
    }, "image/png");
  });
}
