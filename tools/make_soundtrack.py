#!/usr/bin/env python3
"""Build the EP015 soundtrack: music beds + SFX, ducked under the real VO.

Everything is synthesized from scratch with numpy - no samples, nothing to
license. The technique follows Kit v2 (make_sfx.py generates procedurally), but
the palette is EP015's own: the brief's SFX master table supersedes the Templar
medieval plan, and the music brief is a 1929 jazz-age motif, not medieval drone.

Pipeline:
    music beds per part  (one motif, reorchestrated per the colour arc)
  + SFX placed on spoken cues
  -> ducked 6-10 dB under the actual VO envelope
  -> assets/audio/soundtrack.wav  (24 kHz mono, matching the VO)

    python tools/make_soundtrack.py
"""
from __future__ import annotations

import json
import os
import re
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "assets", "audio")
VO = os.path.join(AUDIO, "vo_full.wav")
TIMELINE = os.path.join(ROOT, "web", "js", "timeline.js")
BRIEF = os.path.join(ROOT, "docs", "EP015_storyboard_brief.txt")
OUT = os.path.join(AUDIO, "soundtrack.wav")

SR = 24000
rng = np.random.default_rng(1929)


# ---------------------------------------------------------------- primitives
def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.01, r=0.1):
    """Attack/release envelope, `a` and `r` in seconds."""
    n = int(n)
    e = np.ones(n)
    a = max(1, int(a * SR))
    r = max(1, int(r * SR))
    if a < n:
        e[:a] = np.linspace(0, 1, a)
    if r < n:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def lp(x, k=8):
    """One-pole lowpass, k in Hz-ish (higher = brighter)."""
    a = 1 - np.exp(-2 * np.pi * k / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def hp(x, k=80):
    return x - lp(x, k)


def norm(x, peak=0.9):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def tone(f, d, wave="sine", vib=0.0, vr=5.0):
    tt = t(d)
    fr = f * (1 + vib * np.sin(2 * np.pi * vr * tt))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    if wave == "sine":
        return np.sin(ph)
    if wave == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if wave == "square":
        return np.sign(np.sin(ph))
    return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1


def sweep(f0, f1, d, wave="sine", curve=1.0):
    tt = t(d)
    u = (tt / d) ** curve
    ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * u) / SR
    return np.sin(ph) if wave == "sine" else 2 * ((ph / (2 * np.pi)) % 1) - 1


def noise(d):
    return rng.standard_normal(int(SR * d))


def pluck(f, d=0.8, damp=0.996):
    """Karplus-Strong plucked string."""
    N = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, N)
    n = int(SR * d)
    out = np.zeros(n)
    seg = buf.copy()
    for a in range(0, n, N):
        b = min(n, a + N)
        out[a:b] = seg[: b - a]
        seg = damp * 0.5 * (seg + np.roll(seg, -1))
    return out * env(n, 0.002, 0.06)


def place(x, s, at, g=1.0):
    p = int(at * SR)
    L = min(len(s), len(x) - p)
    if L > 0:
        x[p : p + L] += s[:L] * g


def mix(*parts):
    """Add signals of differing length, padded to the longest.

    Effects combine a short transient with a longer tail; padding to the longest
    keeps the tail rather than raising a broadcast error.
    """
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


# ------------------------------------------------------- the EP015 motif
# One musical identity, reorchestrated per the colour arc. A minor-tinged
# four-note figure (A-C-E-D) that can be pizzicato, bowed, plucked or piano
# depending on the chapter.
MOTIF = [220.0, 261.63, 329.63, 293.66]


def _fit(x, n):
    """Resize (pad or truncate) to exactly n samples."""
    if len(x) == n:
        return x
    if len(x) > n:
        return x[:n]
    return np.pad(x, (0, n - len(x)))


def motif(d, voice="pizz", gain=1.0, octave=1.0):
    """Play the motif once, in the given voice.

    Every voice is fitted to the same per-note length so they can be layered
    and concatenated without broadcast errors.
    """
    seg = max(1, int(SR * d / len(MOTIF)))
    note = d / len(MOTIF)
    out = []
    for f0 in MOTIF:
        f = f0 * octave
        if voice == "pizz":
            s = _fit(pluck(f, note * 1.6), seg) * 0.5
            s += _fit(tone(f, note, "tri") * env(int(SR * note), 0.004, 0.12), seg) * 0.18
        elif voice == "piano":
            s = _fit(tone(f, note * 2.2, "sine", 0.002, 3.0), seg) * 0.5
            s += _fit(tone(f * 2, note * 1.1, "sine"), seg) * 0.12
            s *= env(seg, 0.006, 0.5)
        elif voice == "bowed":
            s = _fit(lp(tone(f, note * 1.9, "saw", 0.006, 4.5), 6), seg)
            s *= env(seg, 0.25, 0.5) * 0.32
        elif voice == "wood":
            s = _fit(lp(tone(f, note * 1.8, "tri"), 40), seg)
            s *= env(seg, 0.06, 0.3) * 0.4
        else:
            s = _fit(tone(f, note, "sine"), seg) * env(seg, 0.01, 0.2) * 0.3
        out.append(s)
    return np.concatenate(out) * gain


def tick_perc(d, rate=2.0, gain=0.05):
    """Tick percussion: the clock that runs under the whole episode."""
    n = int(SR * d)
    x = np.zeros(n)
    step = int(SR / rate)
    for p in range(0, n, step):
        L = min(int(0.02 * SR), n - p)
        if L > 0:
            x[p : p + L] += hp(noise(L / SR), 3000) * env(L, 0.001, 0.02) * gain
    return x


# Part-specific orchestration, following the brief's MUSIC BRIEF section.
PART_MUSIC = [
    # (voice, octave, tick_rate, gain)
    ("pizz", 1.0, 2.0, 0.55),   # P0 sparse ticking piano, tense pizzicato
    ("pizz", 1.0, 2.2, 0.60),   # CH1 optimistic warm gold
    ("bowed", 0.5, 1.6, 0.62),  # CH2 crash: dark bowed bass, restrained brass
    ("pizz", 1.0, 2.4, 0.50),   # CH3 short-selling explainer: rhythmic plucks
    ("piano", 1.0, 1.8, 0.52),  # CH4 Kennedy: thoughtful jazz-tinged piano
    ("piano", 1.0, 2.0, 0.54),  # CH5 cash becomes power
    ("bowed", 0.5, 1.2, 0.40),  # CH6 grief: sparse, desaturated
    ("piano", 1.0, 2.0, 0.58),  # CH7 warm reprise, optimistic but not triumphal
]


def build_music(parts_dur):
    total = sum(parts_dur)
    music = np.zeros(int(SR * total))
    for i, d in enumerate(parts_dur):
        voice, oct_, rate, gain = PART_MUSIC[i]
        bed = np.zeros(int(SR * d))
        bar = 3.2  # one motif statement
        n_bars = int(d / bar)
        for b in range(n_bars):
            seg = motif(bar * 0.95, voice, gain, oct_)
            place(bed, seg, b * bar)
        if voice == "pizz":
            # light woodwinds over the plucks
            for b in range(n_bars):
                place(bed, motif(bar * 0.95, "wood", gain * 0.5, 2.0), b * bar)
        bed += tick_perc(d, rate, 0.05)
        bed *= env(len(bed), 1.5, 2.5)
        offset = int(SR * sum(parts_dur[:i]))
        L = min(len(bed), len(music) - offset)
        music[offset : offset + L] += bed[:L]
    return norm(music, 0.55)


# ------------------------------------------------------------------- SFX
def sfx_bank():
    """The brief's SFX master table and nothing else."""
    S = {}

    # paper flip
    x = hp(noise(0.16), 1200) * env(int(SR * 0.16), 0.004, 0.13)
    S["paper_flip"] = norm(x, 0.5)

    # parchment / paper rustle (softer, longer)
    x = hp(noise(0.5), 900) * env(int(SR * 0.5), 0.08, 0.4) * 0.7
    S["paper_rustle"] = norm(x, 0.3)

    # market bell
    x = mix(tone(880, 1.6, "sine"), tone(1320, 1.6, "sine") * 0.5,
            tone(1760, 1.2, "sine") * 0.25) * env(int(SR * 1.6), 0.005, 1.4)
    S["market_bell"] = norm(x, 0.45)

    # ticker clicks (rapid mechanical)
    n = int(SR * 1.2)
    x = np.zeros(n)
    for k in range(22):
        p = int(k * SR * 0.05 + rng.uniform(0, 0.008) * SR)
        L = min(int(0.012 * SR), n - p)
        if L > 0:
            x[p : p + L] += hp(noise(L / SR), 2500) * env(L, 0.001, 0.012) * 0.6
    S["ticker"] = norm(x, 0.35)

    # crowd murmur
    x = lp(noise(3.0), 30) * env(int(SR * 3.0), 0.5, 0.8) * 0.9
    S["crowd"] = norm(x, 0.22)

    # cash coin single
    x = mix(tone(2400, 0.35, "sine"), tone(3600, 0.28, "sine") * 0.6)
    x = x * env(len(x), 0.002, 0.32)
    S["coin"] = norm(x, 0.4)

    # coin pile clatter
    n = int(SR * 0.9)
    x = np.zeros(n)
    for k in range(14):
        f = rng.uniform(1800, 4200)
        place(x, tone(f, 0.3, "sine") * env(int(SR * 0.3), 0.002, 0.28) * rng.uniform(0.3, 0.8),
              rng.uniform(0, 0.6))
    S["coin_pile"] = norm(x, 0.42)

    # soft stamp
    x = mix(lp(noise(0.12), 400) * 1.2, tone(120, 0.16, "sine") * 0.5)
    x = x * env(len(x), 0.002, 0.15)
    S["stamp"] = norm(x, 0.5)

    # descending swoosh
    x = sweep(2400, 260, 0.7, "sine", 1.6)
    x = lp(hp(x * noise(0.7) * 0.4 + x, 200), 3000) * env(int(SR * 0.7), 0.03, 0.6)
    S["swoosh_down"] = norm(x, 0.35)

    # soft stock crash impact (not a triumph, not a boom)
    x = mix(lp(noise(1.1), 180) * 1.1,
            tone(58, 1.0, "sine") * 0.8,
            tone(87, 0.8, "sine") * 0.35)
    x = x * env(len(x), 0.01, 1.0)
    S["crash_impact"] = norm(x, 0.6)

    # narrow camera whoosh
    x = sweep(300, 1800, 0.28, "sine", 0.7)
    x = lp(x * noise(0.28) * 0.5 + x * 0.6, 4000) * env(int(SR * 0.28), 0.02, 0.24)
    S["whoosh"] = norm(x, 0.28)

    # low suspense pulse
    x = tone(70, 2.0, "sine") * (0.5 + 0.5 * np.sin(2 * np.pi * 1.2 * t(2.0)))
    x *= env(int(SR * 2.0), 0.3, 0.6)
    S["pulse"] = norm(x, 0.4)

    # clock tick (single)
    x = mix(hp(noise(0.05), 3000), tone(1800, 0.04, "square") * 0.2)
    x = x * env(len(x), 0.001, 0.045)
    S["clock_tick"] = norm(x, 0.3)

    # bank latch
    x = mix(lp(noise(0.09), 1500) * 0.9, tone(320, 0.22, "square") * 0.25)
    x = x * env(len(x), 0.001, 0.2)
    S["latch"] = norm(x, 0.42)

    # machinery slow-down
    n = int(SR * 2.2)
    x = np.zeros(n)
    for k in range(40):
        at = k * 0.05 + (k ** 1.6) * 0.0016
        if at > 2.0:
            break
        f = max(90, 260 - k * 4)
        place(x, tone(f, 0.18, "saw") * env(int(SR * 0.18), 0.004, 0.16) * 0.35, at)
    S["machinery"] = norm(lp(x, 12), 0.35)

    # shutter (rolling down)
    n = int(SR * 1.1)
    x = np.zeros(n)
    for k in range(26):
        at = k * 0.04 + (k ** 1.5) * 0.0012
        if at > 1.0:
            break
        place(x, lp(noise(0.05), 2200) * env(int(SR * 0.05), 0.002, 0.045) * 0.5, at)
    S["shutter"] = norm(x, 0.34)

    # shoe brush
    x = hp(noise(0.9), 2000) * (0.55 + 0.45 * np.sin(2 * np.pi * 4.5 * t(0.9)))
    x *= env(int(SR * 0.9), 0.08, 0.35)
    S["shoe_brush"] = norm(x, 0.28)

    # scale creak
    x = tone(240, 0.9, "saw", 0.09, 3.0) * env(int(SR * 0.9), 0.15, 0.6)
    S["creak"] = norm(lp(x, 20), 0.3)

    # tiny comedic pluck (irony points only - never on hardship)
    x = mix(pluck(392, 0.5, 0.994) * 0.7, pluck(523.25, 0.45, 0.994) * 0.5)
    S["pluck_comic"] = norm(x, 0.3)

    # low piano note
    x = mix(tone(110, 1.8, "sine", 0.001, 2.0) * 0.6, tone(220, 1.4, "sine") * 0.2)
    S["piano_low"] = norm(x * env(len(x), 0.01, 1.6), 0.4)

    # restrained brass note
    x = lp(tone(146.83, 1.6, "saw", 0.005, 5.0), 7) * env(int(SR * 1.6), 0.2, 0.9)
    S["brass"] = norm(x, 0.32)

    # quiet outro chime
    x = mix(tone(523.25, 2.4, "sine"), tone(659.25, 2.2, "sine") * 0.6,
            tone(783.99, 2.0, "sine") * 0.35) * env(int(SR * 2.4), 0.01, 2.2)
    S["chime"] = norm(x, 0.38)

    return S


# ------------------------------------------------------- SFX placement
# Keyword -> sfx. Deliberately conservative: the brief says "Pick only where
# indicated in storyboard; don't fill every second."
# The brief writes SFX in free prose - 229 distinct phrasings across 217 shots.
# These are routed onto the master table's effects by keyword, first match wins.
CUE_RULES = [
    (r"ticker|tick-tock|timeline tick|ticking|typewriter", "ticker"),
    (r"clock",                                             "clock_tick"),
    (r"shoe|brush",                                        "shoe_brush"),
    (r"shutter",                                           "shutter"),
    (r"vault|latch|unlock|bolt",                           "latch"),
    (r"machinery|machine|factory|production|engine|gear",  "machinery"),
    (r"creak|scale|weigh|balance",                         "creak"),
    (r"shuffle|slide|flutter|rustle|newsprint",            "paper_rustle"),
    (r"paper|page|parchment|card|ledger|note|certificate", "paper_flip"),
    (r"coin|clatter|ping",                                 "coin_pile"),
    (r"cash|money|purse",                                  "coin"),
    (r"bell",                                              "market_bell"),
    (r"stamp|thud|slam",                                   "stamp"),
    (r"crash|collapse",                                    "crash_impact"),
    (r"swoosh|swish|whoosh|descend",                       "swoosh_down"),
    (r"murmer|murmur|crowd|ambience|ambient|street|wind",  "crowd"),
    (r"snore|breath",                                      "crowd"),
    (r"pluck|magic|comedic|comic",                         "pluck_comic"),
    (r"piano",                                             "piano_low"),
    (r"brass|trumpet|horn",                                "brass"),
    (r"pulse|drone|sting|rise|tense|suspense|ominous",     "pulse"),
    (r"chime|ding|chord|pop|tone|tap|click|swell|motif|"
     r"transition|footstep|reveal",                        "chime"),
]

# The brief: "during serious human hardship and suicide mention ... absolutely
# no comedy stingers". These tokens are never allowed on those beats.
COMEDY_TOKENS = re.compile(r"pluck|magic|comedic|comic|ding|pop|snore", re.I)
SENSITIVE_BEAT = re.compile(
    r"suicide|died by suicide|unemploy|poverty|breadline|hunger|"
    r"lose (his|their) job|lost (his|their) job|tragic|funeral|grief",
    re.I)


def route_sfx(token):
    for rx, name in CUE_RULES:
        if re.search(rx, token):
            return name
    return None


def parse_brief_sfx():
    """[(part_index, shot_id, [sfx tokens])] from the storyboard's SFX: lines."""
    out = []
    part = -1
    sid = None
    for line in open(BRIEF, encoding="utf-8"):
        m = re.match(r"^CHAPTER (\d+):", line)
        if m:
            part = int(m.group(1))
            continue
        m = re.match(r"^PART (\d+):", line)
        if m:
            part = int(m.group(1))
            continue
        m = re.match(r"^\[S(\d+)\]", line)
        if m:
            sid = int(m.group(1))
            continue
        m = re.match(r"^SFX:\s*(.+?)\s*$", line)
        if m and sid is not None and part >= 0:
            toks = [x.strip() for x in m.group(1).split(",") if x.strip()]
            out.append((part, f"S{sid:02d}", toks))
    return out


def shot_times():
    """{part: {id: t0}} from the live episode model, so SFX land on real cuts."""
    import subprocess
    js = """
    import { buildEpisode } from './web/js/episode.js';
    const ep = buildEpisode({});
    const out = {};
    for (const s of ep.shots) {
      out[s.pi] = out[s.pi] || {};
      out[s.pi][s.id] = s.t0;
    }
    console.log(JSON.stringify(out));
    """
    r = subprocess.run(["node", "--input-type=module", "-e", js],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"could not read shot times:\n{r.stderr[-800:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def ensure_concat():
    """Rebuild assets/audio/vo_full.wav from v00..v07 if it is missing.

    The concatenated narration is 50 MB and trivially reproducible, so it is
    not kept in the workspace. It is rebuilt here whenever needed.
    """
    if os.path.exists(VO):
        return
    import subprocess
    parts = [os.path.join(AUDIO, f"v0{i}.wav") for i in range(8)]
    missing = [p for p in parts if not os.path.exists(p)]
    if missing:
        raise SystemExit(
            "missing VO masters: " + ", ".join(os.path.basename(m) for m in missing)
            + "\nRe-pull them from Drive (see docs/vo_manifest.json).")
    lst = os.path.join(AUDIO, ".concat.txt")
    with open(lst, "w") as fh:
        for p in parts:
            fh.write(f"file '{p}'\n")
    print("rebuilding vo_full.wav from v00..v07 ...")
    r = subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", VO])
    os.remove(lst)
    if r.returncode != 0:
        raise SystemExit("ffmpeg concat failed")
    with wave.open(VO) as w:
        print(f"  vo_full.wav: {w.getnframes()/w.getframerate():.2f}s")


def ffmpeg_bin():
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import glob
    c = glob.glob(os.path.expanduser(
        "~/.venv/lib/python3.*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*"))
    if c:
        return sorted(c)[-1]
    raise SystemExit("no ffmpeg; install with: pip install imageio-ffmpeg")


FFMPEG = ffmpeg_bin()


def main():
    man = json.load(open(os.path.join(ROOT, "docs", "vo_manifest.json"), encoding="utf-8"))
    durs = [p["seconds"] for p in sorted(man["parts"], key=lambda r: r["part"])]
    total = sum(durs)

    ensure_concat()
    if not os.path.exists(VO):
        raise SystemExit(f"missing {VO}")
    with wave.open(VO, "rb") as w:
        vorate = w.getframerate()
        vox = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        if w.getnchannels() > 1:
            vox = vox.reshape(-1, w.getnchannels()).mean(axis=1)
    assert vorate == SR, f"VO is {vorate}Hz, expected {SR}"

    print(f"VO: {len(vox)/SR:.2f}s @ {SR}Hz")

    print("building music beds...")
    music = build_music(durs)
    if len(music) < len(vox):
        music = np.pad(music, (0, len(vox) - len(music)))
    music = music[: len(vox)]

    print("synthesizing SFX bank...")
    S = sfx_bank()
    print(f"  {len(S)} effects: {', '.join(sorted(S))}")

    # --- place SFX on shot cues
    print("reading storyboard SFX cues...")
    cues = parse_brief_sfx()
    times = shot_times()

    # Sensitive beats are identified from the storyboard text around them, not
    # guessed from the effect names alone.
    brief_text = open(BRIEF, encoding="utf-8").read()
    sensitive_shots = set()
    for m in re.finditer(r"\[S(\d+)\](.*?)(?=\n\[S\d+\]|\nCHAPTER|\nPART|\Z)",
                         brief_text, re.S):
        if SENSITIVE_BEAT.search(m.group(2)):
            sensitive_shots.add(int(m.group(1)))

    print("placing SFX on storyboard cues...")
    sfx_track = np.zeros(len(vox))
    placed = 0
    unrouted = 0
    suppressed = 0
    used = {}
    for part, sid, tokens in cues:
        at = times.get(str(part), {}).get(sid)
        if at is None or at >= total:
            continue
        for tok in tokens:
            if int(sid[1:]) in sensitive_shots and COMEDY_TOKENS.search(tok):
                suppressed += 1
                continue
            nm = route_sfx(tok)
            if nm is None:
                unrouted += 1
                continue
            place(sfx_track, S[nm], at, 0.55)
            used[nm] = used.get(nm, 0) + 1
            placed += 1
    print(f"  {placed} SFX placed from {len(cues)} cued shots")
    print(f"  {suppressed} comedy effects suppressed on sensitive beats "
          f"({len(sensitive_shots)} sensitive shots identified)")
    if unrouted:
        print(f"  {unrouted} cue tokens had no route (left silent)")
    print("  effect usage: " + ", ".join(
        f"{k} {v}" for k, v in sorted(used.items(), key=lambda x: -x[1])))

    # --- duck music + sfx under the real VO envelope
    print("ducking under VO...")
    win = int(SR * 0.05)
    nw = len(vox) // win
    vrms = np.sqrt((vox[: nw * win].reshape(nw, win) ** 2).mean(axis=1))
    # 0 when silent, ->1 when loud speech
    act = np.clip((vrms - 0.012) / 0.05, 0, 1)
    act = np.repeat(act, win)
    if len(act) < len(vox):
        act = np.pad(act, (0, len(vox) - len(act)))
    act = act[: len(vox)]
    # Proper sidechain: a hysteresis gate (so speech and pauses classify
    # cleanly) followed by fast-attack / slow-release smoothing (so it sounds
    # musical rather than choppy).
    #
    # A plain lowpassed proportional envelope does NOT work here: measured, it
    # only spans 0.66 in loud passages to 0.33 in gaps, so a -8 dB duck came
    # out at under -4 dB. The gate reaches both rails, which is what makes the
    # depth predictable.
    hi = np.percentile(vrms, 65)
    lo = np.percentile(vrms, 25)
    gate = np.zeros(nw)
    state = 0
    for i in range(nw):
        if vrms[i] > hi:
            state = 1
        elif vrms[i] < lo:
            state = 0
        gate[i] = state

    act = np.repeat(gate, win)
    if len(act) < len(vox):
        act = np.pad(act, (0, len(vox) - len(act)))
    act = act[: len(vox)]

    # fast attack (20 ms), slow release (300 ms)
    a_atk = 1 - np.exp(-1.0 / (0.020 * SR))
    a_rel = 1 - np.exp(-1.0 / (0.300 * SR))
    act_s = np.zeros(len(act))
    lvl = 0.0
    for i in range(len(act)):
        a = a_atk if act[i] > lvl else a_rel
        lvl += a * (act[i] - lvl)
        act_s[i] = lvl

    # Exactly -8 dB while VO speaks, easing to full level in the gaps. Brief:
    # "Music 6-10 dB below intelligible voice, sidechain ducked."
    # Only ONE attenuation is applied - stacking a second one pushed the bed to
    # -16 dB, well past the spec.
    duck = 10 ** (-8.0 / 20.0)
    # Trim measured, not guessed: at 1.0 the bed sat -9.6 dB under the voice,
    # right on the -10 edge of the brief's 6-10 dB window. 1.2 brings it to
    # about -8 dB, comfortably centred.
    BED_TRIM = 1.2
    bed = (music * 0.85 + sfx_track) * BED_TRIM * ((1 - act_s) + act_s * duck)

    mix = vox + bed
    mix = norm(mix, 0.92)

    os.makedirs(AUDIO, exist_ok=True)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())

    # ---- verify against what the brief actually asks.
    #
    # "Music 6-10 dB below intelligible voice, sidechain ducked" - the spec is
    # the bed's level RELATIVE TO THE VOICE, not how far it is attenuated.
    # Measuring attenuation instead is misleading here because this narrator
    # barely pauses: even the quietest 20% of half-second windows are still
    # speech, so both ends of that comparison are ducked and the number means
    # nothing.
    #
    # Measure only where the gate says speech is present, and compare bed to VO.
    W = int(SR * 0.05)
    nb = len(bed) // W
    bed_r = np.sqrt((bed[: nb * W].reshape(nb, W) ** 2).mean(axis=1))
    vo_r = np.sqrt((vox[: nb * W].reshape(nb, W) ** 2).mean(axis=1))
    speaking = gate[:nb] > 0.5
    bl = bed_r[speaking].mean()
    vl = vo_r[speaking].mean()
    rel = 20 * np.log10(max(bl, 1e-9) / max(vl, 1e-9))
    print(f"\n  during speech ({speaking.mean()*100:.0f}% of the episode):")
    print(f"    VO level  : {vl:.4f}")
    print(f"    bed level : {bl:.4f}")
    print(f"    bed vs VO : {rel:+.1f} dB  "
          f"({'PASS, brief wants -6 to -10 dB below voice' if -10.5 <= rel <= -5.5 else 'OUT OF SPEC'})")
    g_sp = ((1 - act_s) + act_s * duck)[: nb * W].reshape(nb, W).mean(axis=1)[speaking]
    g_gap = ((1 - act_s) + act_s * duck)[: nb * W].reshape(nb, W).mean(axis=1)[~speaking]
    print(f"    duck gain : {g_sp.mean():.3f} speaking / {g_gap.mean():.3f} in gaps"
          f"  ({20*np.log10(g_sp.mean()/max(g_gap.mean(),1e-9)):+.1f} dB)")

    mb = os.path.getsize(OUT) / 1024 / 1024
    print(f"\nwrote {os.path.relpath(OUT, ROOT)}  ({mb:.1f} MB, {len(mix)/SR:.2f}s)")
    print(f"  music peak {np.abs(music).max():.3f}  sfx peak {np.abs(sfx_track).max():.3f}")
    print(f"  mix peak   {np.abs(mix).max():.3f}  "
          f"clipped samples: {int((np.abs(mix) > 0.999).sum())}")


if __name__ == "__main__":
    main()
