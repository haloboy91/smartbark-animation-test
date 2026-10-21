// The episode timing model, in one place.
//
// engine.js (browser preview), tools/render_video.mjs (MP4 export) and
// tools/smoke_test.mjs all build the exact same object from this function.
// That is deliberate: when each caller built its own timings, the renderer and
// the preview silently disagreed about where cuts land, and a video could be
// exported that never matched what was reviewed on screen.
//
// Change timing here and all three change together.

import { PARTS, buildWords, partDuration } from "./script.js";
import { SHOTS } from "./timeline.js";
import { findPhrase } from "./cues.js";

export function buildEpisode({ onWarning = () => {} } = {}) {
  // Each part owns a local timeline (brief: "8 independent WAV files; each part
  // begins at LOCAL 0:00"), laid end to end into the global one.
  const parts = PARTS.map((p, i) => {
    const w = buildWords(p, i);
    // Real length from the VO master; the +0.9 tail is only the synthetic
    // fallback so the final word is not clipped when no manifest exists.
    return {
      ...p,
      index: i,
      words: w,
      dur: partDuration(i, w[w.length - 1].t1 + 0.9),
    };
  });

  let acc = 0;
  for (const p of parts) { p.offset = acc; acc += p.dur; }
  const TOTAL = acc;

  const words = parts.flatMap((p) =>
    p.words.map((w) => ({ ...w, t0: w.t0 + p.offset, t1: w.t1 + p.offset })));

  const shots = SHOTS.map((s) => {
    const pi = s.part == null ? 0 : s.part;
    return { ...s, pi, wi: findPhrase(parts[pi].words, s.cue) };
  });

  // Assign in story order and force monotonicity: a cut landing before the
  // previous one is worse than an approximated one, so an unmatched cue is
  // placed at the end of the preceding shot rather than jumping backwards.
  let cursor = 0;
  shots.forEach((s) => {
    if (s.wi < 0) onWarning(`cue not found for p${s.pi}/${s.id}: "${s.cue}"`);
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

  const activeShot = (t) => {
    for (let i = shots.length - 1; i >= 0; i--) if (t >= shots[i].t0) return i;
    return 0;
  };

  const unmatched = shots.filter((s) => !s.cueMatched);

  return { parts, words, shots, TOTAL, activeShot, unmatched };
}
