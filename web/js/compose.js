// Single compositor: draws one 1920x1080 frame.
//
// The live preview and the proof-sheet export both go through paintFrame(), so
// a proof frame is pixel-identical to what you see on screen. That matters: the
// brief calls for proof frames at every chapter opening and dramatic change,
// and they are only useful if they show the real composite (camera + Elly +
// overlays), not an approximation of it.
//
// Overlays are drawn here, never baked into plate art, per the caption policy.
import { SCENES } from "./scenes.js";

export const W = 1920;
export const H = 1080;

const OUT = "#1b1a1c";

const clamp01 = (t) => Math.max(0, Math.min(1, t));
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);

// ------------------------------------------------------------------ camera
export function camera(shot, p) {
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
      const s = clamp01(p / (c.settle || 0.35));
      const settled = c.from + (1 - c.from) * easeOut(s);
      const creep = (c.then - 1) * easeInOut(clamp01((p - (c.settle || 0.35)) / 0.65));
      scale = settled * (1 + creep);
      break;
    }
    case "pan": {
      dx = -(c.dx || 0) * easeInOut(p);
      const z = (c.zoom || 1) - 1;
      const b = (c.then || 1) - 1;
      scale = 1 + z * easeInOut(p) + b * easeInOut(p);
      break;
    }
    case "parallax":
      dx = -(c.dx || 0) * Math.sin(p * Math.PI * 2) * 0.5;
      break;
    case "pulse": {
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
    case "static":
    default:
      scale = 1;
  }

  // Impact shake only where the storyboard calls for a crash impact.
  if (shot.shake && p >= shot.shake.from && p <= shot.shake.to) {
    const k = 1 - (p - shot.shake.from) / (shot.shake.to - shot.shake.from);
    const a = shot.shake.amp * k;
    dx += (Math.random() - 0.5) * a * 2;
    dy += (Math.random() - 0.5) * a * 2;
  }
  return { scale, dx, dy };
}

// --------------------------------------------------------------------- Elly
export function ellyPose(shot, p) {
  let cur = shot.elly[0];
  for (const e of shot.elly) if (p >= e.t) cur = e;
  return cur;
}

/**
 * Elly's composited height in pixels.
 *
 * Exported so the audit script measures the real value instead of re-deriving
 * the formula - a re-derivation would drift the moment this changes.
 *
 * The camera affects her only partially (45% of its scale) so she stays
 * readable and uncropped, then the result is hard-clamped to the brief's
 * 35-50% of frame height. Without the clamp the camera term alone pushed her
 * to 55.7% on zoom-in shots, which reads as distortion.
 */
export function ellyHeight(e, cam, breathe = 1) {
  const raw = e.h * breathe * (1 + (cam.scale - 1) * 0.45);
  return Math.min(H * 0.50, Math.max(H * 0.35, raw));
}

function wrapText(ctx, text, maxWidth) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = "";
  for (const w of words) {
    const test = line ? `${line} ${w}` : w;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = w;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

// ------------------------------------------------------------------ painting
export function paintFrame(ctx, t, state) {
  const { shots, parts, words, plates, poses, usePlates } = state;
  const i = state.activeShot(t);
  const shot = shots[i];
  const span = Math.max(0.001, shot.t1 - shot.t0);
  const p = clamp01((t - shot.t0) / span);
  const cam = camera(shot, p);

  ctx.clearRect(0, 0, W, H);

  // --- scene, under the camera move
  ctx.save();
  ctx.translate(W / 2 + cam.dx, H / 2 + cam.dy);
  ctx.scale(cam.scale, cam.scale);
  ctx.translate(-W / 2, -H / 2);

  const plate = usePlates && shot.plate ? plates.get(shot.plate) : null;
  if (plate && plate.complete && plate.naturalWidth) {
    ctx.drawImage(plate, 0, 0, W, H);
  } else {
    const fn = SCENES[shot.scene] || SCENES.generic;
    if (fn) fn(ctx, p, t);
    else { ctx.fillStyle = "#222"; ctx.fillRect(0, 0, W, H); }
  }
  ctx.restore();

  // --- Elly: separate composited layer, never baked into a plate.
  const e = ellyPose(shot, p);
  const img = poses.get(e.pose);
  if (img && img.complete && img.naturalWidth) {
    const bob = Math.sin(t * 2.1) * 7;
    const breathe = 1 + Math.sin(t * 2.1) * 0.006;
    const enter = clamp01(p / 0.14);
    const rise = (1 - easeOut(enter)) * 40;

    // Camera affects her only partially, so she stays readable and uncropped.
    const cx = cam.dx * 0.35 + (e.x - W / 2) * (1 + (cam.scale - 1) * 0.35) + W / 2;
    // See ellyHeight: partial camera influence, clamped to 35-50% of frame.
    const h = ellyHeight(e, cam, breathe);
    const w = (img.naturalWidth / img.naturalHeight) * h;
    const top = e.y + bob + rise - h;

    ctx.save();
    ctx.globalAlpha = enter;
    ctx.translate(cx, top + h / 2);
    if (e.flip) ctx.scale(-1, 1);
    ctx.drawImage(img, -w / 2, -h / 2, w, h);
    ctx.restore();
  }

  // --- caption (edit overlay)
  if (shot.caption && p > 0.06 && p < 0.92) {
    ctx.save();
    ctx.font = '62px "Luckiest Guy", "Arial Black", Impact, sans-serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.lineWidth = 8;
    ctx.strokeStyle = "rgba(0,0,0,.55)";
    const cap = shot.caption.toUpperCase();
    const lines = wrapText(ctx, cap, W - 240);
    let y = 96;
    for (const ln of lines) {
      ctx.strokeText(ln, W / 2, y);
      ctx.fillStyle = "#fff";
      ctx.fillText(ln, W / 2, y);
      y += 70;
    }
    ctx.restore();
  }

  // --- chapter card at the start of each part
  const cur = parts.find((q) => t >= q.offset && t < q.offset + q.dur) || parts[parts.length - 1];
  if (t - cur.offset < 2.6) {
    const k = clamp01((2.6 - (t - cur.offset)) / 0.4);
    ctx.save();
    ctx.globalAlpha = k;
    ctx.font = '78px "Luckiest Guy", "Arial Black", Impact, sans-serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 10;
    ctx.strokeStyle = "rgba(0,0,0,.5)";
    const lines = wrapText(ctx, cur.card, 1500);
    let y = H * 0.46 - ((lines.length - 1) * 88) / 2;
    for (const ln of lines) {
      ctx.strokeText(ln, W / 2, y);
      ctx.fillStyle = "#ffe9c2";
      ctx.fillText(ln, W / 2, y);
      y += 88;
    }
    ctx.restore();
  }

  // --- subtitles, word-highlighted
  const idx = words.findIndex((w) => t >= w.t0 && t < w.t1);
  if (idx >= 0) {
    const from = Math.max(0, idx - 5);
    const to = Math.min(words.length, idx + 7);
    const line = words.slice(from, to).map((w) => w.w).join(" ");
    ctx.save();
    ctx.font = '800 54px "Lato", ui-sans-serif, system-ui, sans-serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    const lines = wrapText(ctx, line, 1640).slice(-2);

    // highlight the active word
    const before = words.slice(from, idx).map((w) => w.w).join(" ");
    const active = words[idx].w;
    const after = words.slice(idx + 1, to).map((w) => w.w).join(" ");

    let y = H - 104;
    for (let li = lines.length - 1; li >= 0; li--) {
      const ln = lines[li];
      const total = ctx.measureText(ln).width;
      let x = W / 2 - total / 2;
      const isLast = li === lines.length - 1;
      ctx.textAlign = "left";
      ctx.lineWidth = 8;
      ctx.strokeStyle = "rgba(0,0,0,.9)";

      if (isLast) {
        for (const [seg, on] of [[before, false], [active, true], [after, false]]) {
          if (!seg) continue;
          const piece = (on ? "" : "") + seg;
          ctx.strokeText(piece, x, y);
          ctx.fillStyle = on ? "#ffd98a" : "rgba(255,255,255,.62)";
          ctx.fillText(piece, x, y);
          x += ctx.measureText(piece).width + ctx.measureText(" ").width;
        }
      } else {
        ctx.strokeText(ln, x, y);
        ctx.fillStyle = "rgba(255,255,255,.62)";
        ctx.fillText(ln, x, y);
      }
      y -= 68;
    }
    ctx.restore();
  }
}
