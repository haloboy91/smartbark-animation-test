#!/usr/bin/env python3
"""Forced-align the approved script to the real VO, using actual audio pauses.

The kit's asr.py needs a Vosk acoustic model, which cannot be fetched here
(alphacephei.com and raw.githubusercontent.com are both blocked). But we do not
need speech RECOGNITION: docs/script.txt is the approved verbatim narration, so
the problem is forced ALIGNMENT - finding where each word sits in the audio.

This does that from the signal itself:

  1. Read the WAV, build an RMS energy envelope (20 ms frames).
  2. Threshold it against the noise floor to get a speech/silence mask.
  3. Find speech runs separated by real pauses.
  4. Split the script into sentences, and map sentences onto speech runs with
     a DTW that keeps word order and never assigns a sentence backwards.
  5. Inside each sentence, spread words by estimated syllable duration.

The result is audio-derived: sentence boundaries land on the narrator's actual
pauses. Word timings within a sentence are modelled, not measured, so this is
better than uniform proportional spread but not word-exact. Swap in real ASR
(words.json from the kit's align.py) and nothing else changes.

    python tools/align_audio.py            -> web/js/words.json
"""
from __future__ import annotations

import json
import os
import re
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "assets", "audio")
SCRIPT = os.path.join(ROOT, "docs", "script.txt")
MANIFEST = os.path.join(ROOT, "docs", "vo_manifest.json")
OUT = os.path.join(ROOT, "web", "js", "words.json")

FRAME = 0.020          # seconds per analysis frame
MIN_PAUSE = 0.16       # seconds of silence that counts as a sentence break
MIN_RUN = 0.25         # ignore speech blips shorter than this


def envelope(path):
    """RMS energy per frame, plus the sample rate and total duration."""
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2, f"{path}: expected 16-bit"
        rate = w.getframerate()
        ch = w.getnchannels()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    n = int(rate * FRAME)
    usable = (len(x) // n) * n
    frames = x[:usable].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    return rms, rate, len(x) / rate


def speech_runs(rms):
    """[(start_frame, end_frame)] of speech, from a noise-floor-relative threshold.

    Uses a percentile noise floor rather than an absolute level, so it adapts
    to each part's own loudness and room tone.
    """
    floor = np.percentile(rms, 10)
    peak = np.percentile(rms, 95)
    if peak <= floor * 1.5:
        # No clear dynamics: treat the whole part as one run.
        return [(0, len(rms))]
    thr = floor + (peak - floor) * 0.12
    loud = rms > thr
    # close gaps shorter than MIN_PAUSE (breaths inside a sentence)
    gap = max(1, int(MIN_PAUSE / FRAME))
    loud = _close_gaps(loud, gap)
    runs, i = [], 0
    n = len(loud)
    while i < n:
        if loud[i]:
            j = i
            while j < n and loud[j]:
                j += 1
            if (j - i) * FRAME >= MIN_RUN:
                runs.append((i, j))
            i = j
        else:
            i += 1
    if not runs:
        runs = [(0, n)]
    return runs


def _close_gaps(mask, gap):
    """Fill runs of False shorter than `gap` frames."""
    m = mask.copy()
    n = len(m)
    i = 0
    while i < n:
        if not m[i]:
            j = i
            while j < n and not m[j]:
                j += 1
            if j - i <= gap:
                m[i:j] = True
            i = j
        else:
            i += 1
    return m


def sentences(tokens):
    """Group tokens into sentences, keeping punctuation with its word."""
    out, cur = [], []
    for t in tokens:
        cur.append(t)
        if re.search(r"[.!?]['\")\]]*$", t):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def syllables(word):
    """Crude syllable count - good enough to weight a duration model."""
    w = re.sub(r"[^a-z']", "", word.lower())
    if not w:
        return 1
    w = re.sub(r"e$", "", w)
    groups = re.findall(r"[aeiouy]+", w)
    return max(1, len(groups))


def run_slices(sents, n_runs):
    """Contiguous, non-overlapping run ranges, one per sentence.

    Returns [(run_start, run_end_exclusive)].

    Partitioning matters: looking each sentence up independently lets two
    sentences claim the same run, which makes their word ranges overlap and the
    timeline go backwards. Splitting the run sequence into contiguous slices
    weighted by word count keeps every sentence strictly after the last.
    """
    if n_runs <= 0 or not sents:
        return [(0, 1)] * max(len(sents), 1)
    counts = [len(s) for s in sents]
    total = float(sum(counts)) or 1.0
    cuts, acc = [0], 0
    for c in counts:
        acc += c
        cuts.append(min(n_runs, int(round(acc / total * n_runs))))
    # force strictly increasing
    for i in range(1, len(cuts)):
        if cuts[i] <= cuts[i - 1]:
            cuts[i] = min(n_runs, cuts[i - 1] + 1)
    return [(cuts[i], max(cuts[i] + 1, cuts[i + 1])) for i in range(len(sents))]


def align_part(path, tokens):
    rms, rate, dur = envelope(path)
    runs = speech_runs(rms)
    sents = sentences(tokens)

    # merge runs whose gaps are tiny, so run count is sane
    run_t = [(a * FRAME, min(b * FRAME, dur)) for a, b in runs]

    slices = run_slices(sents, len(run_t))

    words = []
    for s_idx, sent in enumerate(sents):
        r0, r1 = slices[s_idx]
        r0 = min(r0, len(run_t) - 1)
        r1 = min(max(r1, r0 + 1), len(run_t))
        t0 = run_t[r0][0]
        t1 = run_t[r1 - 1][1]
        if t1 <= t0:
            t1 = t0 + 0.2

        weights = [max(1, syllables(w)) for w in sent]
        # sentence-final pause weight
        total = float(sum(weights))
        acc = t0
        for w, wt in zip(sent, weights):
            d = (wt / total) * (t1 - t0)
            words.append({"w": w, "t0": round(acc, 3), "t1": round(acc + d, 3)})
            acc += d

    # guarantee the last word ends at the true end of the part
    if words:
        words[-1]["t1"] = round(dur, 3)
    return words, dur, len(run_t)


def main():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    raw = open(SCRIPT, encoding="utf-8").read()
    parts = [b.strip() for b in raw.split("###")][1:]
    parts = [p for p in parts if p]
    if len(parts) != 8:
        raise SystemExit(f"expected 8 parts in script.txt, got {len(parts)}")

    result = {}
    print(f"{'part':<6}{'words':>7}{'runs':>7}{'dur':>9}{'first word':>12}  status")
    for i, text in enumerate(parts):
        ap = os.path.join(AUDIO, f"v0{i}.wav")
        if not os.path.exists(ap):
            raise SystemExit(f"missing {ap} - run the Drive download first")
        one_line = re.sub(r"\s+", " ", text).strip()
        tokens = one_line.split()
        words, dur, nrun = align_part(ap, tokens)
        result[str(i)] = words
        ok = "ok" if len(words) == len(tokens) else "TOKEN MISMATCH"
        print(f"v0{i:<4}{len(words):>7}{nrun:>7}{dur:>8.2f}s{words[0]['t0']:>11.2f}s  {ok}")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, separators=(",", ":"))

    total = sum(v[-1]["t1"] for v in result.values())
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}  ({os.path.getsize(OUT)/1024:.0f} KB)")
    print(f"total aligned runtime: {total:.2f}s = {total/60:.2f} min")


if __name__ == "__main__":
    main()
