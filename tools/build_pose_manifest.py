#!/usr/bin/env python3
"""Build assets/elly/poses.json - the contract between the storyboard and the renderer.

EP015's storyboard names ~190 distinct "ELLY ACTIVENESS" beats. Generating 190
poses is wasteful and would wreck identity consistency, so each beat maps to a
canonical pose plus renderer-side modifiers (flip / tilt / scale / bob). This
script is the single source of truth for that mapping and fails loudly if a
pose named by the mapping has no cutout on disk.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUTOUTS = os.path.join(ROOT, "assets", "elly", "cutouts")
OUT = os.path.join(ROOT, "assets", "elly", "poses.json")
BRIEF = os.path.join(ROOT, "docs", "EP015_storyboard_brief.txt")

# --------------------------------------------------------------------------
# Canonical pose table.
#   id       stable name the timeline references
#   file     basename (without extension) in assets/elly/cutouts
#   source   reference (original art) | generated (new art) | planned (not made yet)
#   tags     semantic tags used for auto-routing storyboard beats
#   note     why it exists / caveats
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Canonical pose table.
#   id       stable name the timeline references
#   file     basename (without extension) in assets/elly/cutouts
#   source   generated (made for EP015) | planned (not made yet)
#   tags     semantic tags used for auto-routing storyboard beats
#   note     why it exists / caveats
#
# Every pose here is AI-generated on a flat green plate. No image from Drive is
# used anywhere in this project - see tools/check_no_drive_assets.py.
# --------------------------------------------------------------------------
POSES = [
    dict(id="think", file="elly_think", source="generated",
         tags=["thinking", "thoughtful", "ponder", "pondering", "reflective", "curious",
               "recollection", "puzzled", "perplexed", "confused", "doubtful",
               "investigative", "studies", "philosophical", "considers"],
         note="Highest-traffic neutral pose; also the fallback."),
    dict(id="point_side", file="elly_point_side", source="generated",
         tags=["point", "pointing", "points", "indicate", "present", "tracks", "follows",
               "traces", "raises", "lowers paw", "paw", "at each", "toward", "direction",
               "gestures left", "gestures right", "points left", "points right",
               "observes", "looks", "at clock", "at date", "at loan", "at evidence"],
         note="Highest-demand gap: 'Elly points at...' occurs ~20x in the storyboard."),
    dict(id="solemn_direct", file="elly_solemn_direct", source="generated",
         tags=["solemn", "somber", "sober", "serious", "direct-to-viewer", "respectful",
               "empathy", "sympathetic", "memorial", "concerned", "concern", "frown",
               "honest", "kind", "sincere", "quiet concern", "composed", "still",
               "listens", "empathy", "human cost", "tragic", "grief", "not comic",
               "not gleeful", "not celebratory", "restrained"],
         note="MANDATORY for the suicide reference (Ch6) and all hardship beats."),
    dict(id="open_arms", file="elly_open_arms", source="generated",
         tags=["open arms", "explains", "explanatory", "presents", "both paws",
               "gestures", "gesture", "moderating", "compares", "comparing", "contrasts",
               "sides", "both", "presents both", "across", "left", "right", "switches",
               "two-paw", "introducing", "introduces", "presentation", "quadrants"],
         note="Two-sided comparison shots (Investor A vs Investor B)."),
    dict(id="recoil", file="elly_recoil", source="generated",
         tags=["recoils", "pulls paw away", "wary", "steps back", "caution", "cautioning",
               "warns", "warning", "raises caution", "holds warning", "precise", "firm",
               "protective", "guarded", "defensive", "leans back"],
         note="Margin-call / debt-chain danger beats."),
    dict(id="calm_nod", file="elly_calm_nod", source="generated",
         tags=["nod", "nods", "acknowledging", "composed", "listening", "approving",
               "measured", "satisfied", "calm", "acknowledges timing", "serious nod",
               "approving measured", "recognition", "half-smile"],
         note="Low-energy connective beats; keeps pose churn down in long shots."),
    dict(id="shocked", file="elly_shocked", source="generated",
         tags=["shock", "shocked", "startled", "surprised", "surprise", "eyes widen",
               "stunned", "jaw", "admiration", "startled jump", "gasps", "eyes wide",
               "counting", "counts"],
         note="Crash reveals, 'one hundred million dollars'."),
    dict(id="magnifier", file="elly_magnifier", source="generated",
         tags=["investigative", "inspect", "magnifier", "examine", "insight", "shifts",
               "distressed", "studies", "looks closely", "clue"],
         note="Ch3/Ch6 investigation beats."),
    dict(id="firm_headshake", file="elly_firm_headshake", source="generated",
         tags=["head-shake", "shakes head", "firm", "refuses", "corrects", "correction",
               "direct-to-camera", "emphasizes unchanged", "no", "denies", "disapproving"],
         note="'A CRISIS IS NOT GOOD NEWS' + 'NOT ABOUT PREDICTION'."),
    dict(id="present_three", file="elly_present_three", source="generated",
         tags=["three", "three fingers", "three points", "lists", "three paws",
               "three important", "first", "second", "third"],
         note="Ch7 'three important differences' recurring motif."),
    dict(id="peek_side", file="elly_peek_side", source="generated",
         tags=["half-smile", "smiling side-eye", "amused", "knowing", "smirk", "wry",
               "eye-roll", "dry", "incredulous", "amused eyebrow"],
         note="Light irony where deadpan is too flat."),
    dict(id="point_self", file="elly_point_self", source="generated",
         tags=["point self", "me", "direct address", "introduces herself", "innocent",
               "welcoming", "kind introduction", "narrator"],
         note="Chapter-turn direct address."),
    dict(id="teach_pointer", file="elly_teach_pointer", source="generated",
         tags=["teacher", "classroom", "pointer", "lecture", "one step", "steps",
               "mechanism", "classroom pointer", "explains optimistically",
               "confident teacher", "lecture"],
         note="Explainer chapters 1/3/5/7."),
    dict(id="count_paws", file="elly_count_paws", source="generated",
         tags=["tally", "numbers", "emphasizes", "repeated", "playful hand tally",
               "counts two", "counts first", "counting factory", "counts on paws"],
         note="Short-selling worked example, margin math."),
    dict(id="alarmed_pawmouth", file="elly_alarmed_pawmouth", source="generated",
         tags=["alarmed", "paw to mouth", "gasps", "anxious", "knowing anxious",
               "alarmed at downside", "dread"],
         note="Crash beats; distinct from the flat 'shocked' stare."),
    dict(id="wince", file="elly_wince", source="generated",
         tags=["wince", "winces", "flinch", "flinches", "grimace", "distressed",
               "daydreams", "upward", "looks upward", "recoils lightly", "squeezes"],
         note="Crash + Livermore downfall."),
    dict(id="skeptical_brow", file="elly_skeptical_brow", source="generated",
         tags=["skeptical", "raised eyebrow", "side-eye", "doubtful", "intrigued",
               "questions", "questioningly", "eyebrow", "brow", "mild skepticism",
               "curious", "skeptical not celebratory", "impressed but skeptical",
               "intrigued", "suspicious"],
         note="Shoeshine-tale debunk, 'sounds familiar?' irony beats."),
    dict(id="deadpan", file="elly_deadpan", source="generated",
         tags=["deadpan", "flat", "unimpressed", "matter-of-fact", "dry eye-roll",
               "deadpan shock", "expressionless"],
         note="Comedy irony without a cartoon gag."),
    dict(id="relieved", file="elly_relieved", source="generated",
         tags=["relieved", "hopeful", "hope", "guarded optimism", "calm", "reassuring",
               "reassuring nod", "softens", "expression rises", "survive", "hopeful smile",
               "reassuring palms", "warm"],
         note="Chapter 5 liquidity + Chapter 7 recovery."),

    # ---- still to generate ----
    dict(id="welcome_wave", file="elly_welcome_wave", source="generated",
         tags=["welcome", "waving", "greeting", "sign-off", "final wave", "energetic greeting",
               "welcoming pose", "welcoming sign-off", "outro", "intro"],
         note="Episode open and the Smart Bark sign-off."),
    dict(id="worried", file="elly_worried", source="generated",
         tags=["worried", "worry", "anxious", "troubled", "uneasy", "concerned frown",
               "knowing anxious", "looks upward worried", "worried thought"],
         note="Crash and debt beats."),
    dict(id="proud", file="elly_proud", source="generated",
         tags=["proud", "proudly", "satisfied", "pleased", "impressed", "admiration",
               "approving", "success", "triumph"],
         note="Livermore's win, Kennedy's foresight."),
    dict(id="excited", file="elly_excited", source="generated",
         tags=["excited", "energetic", "enthusiastic", "bouncing", "booming", "obsessed",
               "big smile", "exaggerated smile"],
         note="Roaring Twenties mania (Ch1)."),
    dict(id="sitting_quiet", file="elly_sitting_quiet", source="generated",
         tags=["sitting", "quiet", "still", "listening", "resting", "contemplative"],
         note="Quiet connective beats and the slow blink on the memorial card."),
    dict(id="sad", file="elly_sad", source="generated",
         tags=["sad", "crying", "sorrow", "head tilt", "sad head tilt", "tiny exhale",
               "grief", "downcast"],
         note="Ch6 Livermore. Handled as solemn, never comic."),
    dict(id="angry", file="elly_angry", source="generated",
         tags=["angry", "mad", "furious", "indignant", "stern", "emphatic", "insistent"],
         note="Bank failures, margin calls."),
    dict(id="confused", file="elly_confused", source="generated",
         tags=["confused", "perplexed", "bewildered", "lost", "scratches head",
               "does not understand"],
         note="Margin/shorting explainer beats."),
    dict(id="empathetic", file="elly_empathetic", source="generated",
         tags=["empathetic", "sympathetic", "kind", "soft", "breadline", "hardship",
               "unemployment", "pity", "compassion"],
         note="Breadline / unemployment. Must not read as comic."),
    dict(id="newspaper", file="elly_newspaper", source="generated",
         tags=["newspaper", "headline", "black thursday", "black tuesday", "ticker",
               "press", "front page"],
         note="Ch2. No legible text in the art - headlines are edit overlays. "
              "Attempt 1 rejected by validate_poses.py (paper covered her body, navy "
              "0.2%/pink 0.0% - no character visible). Attempt 2 passed but with a "
              "vignetted plate (ring sd 11.3), handled by key_elly.py's local plate "
              "field; green leak inside the body measured at 0.63%."),
    dict(id="coin", file="elly_coin", source="generated",
         tags=["coin", "cash", "money", "liquid", "savings", "pile", "coins"],
         note="Ch5 'When Cash Becomes Power' hero prop."),
    dict(id="umbrella", file="elly_umbrella", source="generated",
         tags=["umbrella", "storm", "protect", "shelter", "survive", "rain"],
         note="Ch7 'SURVIVE THE STORM' - capital protected as the crash passes."),
    dict(id="newsboy_hat", file="elly_newsboy_hat", source="generated",
         tags=["hat", "1920s", "era", "period", "newsboy cap", "flat cap"],
         note="Client-approved era flourish: signature outfit + a 1920s cap."),
    dict(id="ledger", file="elly_ledger", source="generated",
         tags=["ledger", "notebook", "records", "books", "balances", "accounts",
               "balance sheet"],
         note="Quotation-office / bookkeeping beats."),
]


# Fallback used when a storyboard beat matches nothing: neutral, always safe.
DEFAULT_POSE = "think"


def parse_brief(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    beats = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"\s*ELLY ACTIVENESS:\s*(.+)", line)
            if m and not m.group(1).startswith("--"):
                beats.append(m.group(1).strip())
    return beats


def _stem(w: str) -> str:
    w = w.strip(".,;:!?").lower()
    return w[:-1] if len(w) > 4 and w.endswith("s") else w


SENSITIVE = ("solemn", "somber", "sober", "memorial", "no jokes", "sympathetic",
             "empathetic", "serious", "respectful", "grave", "human cost",
             "tragic", "suicide", "hardship", "breadline")


def route(beat: str, include_planned: bool = True) -> tuple[str, str]:
    """Pick the best pose for a storyboard beat. Returns (pose_id, why).

    Matching is word-level with light stemming so 'gestures' hits the 'gesture'
    tag. Planned poses participate so the routing doubles as a demand signal for
    what to generate next.
    """
    b = beat.lower()
    toks = {_stem(w) for w in re.split(r"[\s,;:\u2192\-/]+", b) if w}

    # Sensitive beats always get the solemn pose, never a comic one.
    if any(k in b for k in SENSITIVE):
        return "solemn_direct", "sensitive/respectful beat"

    best, best_score = None, 0
    for p in POSES:
        if p["source"] == "planned" and not include_planned:
            continue
        score = 0
        for tag in p["tags"]:
            parts = [_stem(t) for t in tag.split()]
            if len(tag) < 4 and tag not in toks:
                continue
            if tag in b:                          # multi-word phrase hit
                score += 10 + len(tag)
            elif any(t in toks for t in parts):   # single word hit
                score += 6 + len(tag)
        if score > best_score:
            best, best_score = p["id"], score
    return (best or DEFAULT_POSE), ("match" if best_score else "fallback -> neutral thinking")


def main() -> None:
    on_disk = {os.path.splitext(f)[0] for f in os.listdir(CUTOUTS)} if os.path.isdir(CUTOUTS) else set()

    for p in POSES:
        p["available"] = p["file"] in on_disk

    missing = [p["id"] for p in POSES if p["source"] != "planned" and not p["available"]]
    if missing:
        print("ERROR: pose listed as available but no cutout found:", missing, file=sys.stderr)
        sys.exit(1)

    beats = parse_brief(BRIEF)
    routed, unresolved = {}, []
    demand: dict[str, int] = {}
    for b in beats:
        pid, why = route(b)
        routed.setdefault(pid, []).append(b)
        demand[pid] = demand.get(pid, 0) + 1
        if why.startswith("fallback"):
            unresolved.append(b)

    # Generation priority: planned poses, most-demanded first.
    queue = sorted(
        ((pid, n) for pid, n in demand.items()
         if next(p for p in POSES if p["id"] == pid)["source"] == "planned"),
        key=lambda kv: -kv[1],
    )

    manifest = {
        "meta": {
            "episode": "EP015 - How Some People Got Rich During the Great Depression (1929)",
            "canvas": [1920, 1080],
            "fps": 30,
            "identity": {
                "species": "white fluffy bichon",
                "glasses": "round, black rimmed",
                "sweater": "navy blue with white stars and crescent moons",
                "scarf": "pink",
                "style": "2D cartoon, thick clean outlines, flat colour, soft shadows",
            },
            "rules": [
                "Never stretch, distort or crop a pose to fake a new action.",
                "Camera-safe: keep the right third clear in generated backgrounds.",
                "Elly 35-50% of frame height when present.",
                "No comedy poses on poverty, unemployment or the suicide reference.",
            ],
            "counts": {
                "total_poses": len(POSES),
                "available": sum(1 for p in POSES if p["available"]),
                "planned": sum(1 for p in POSES if p["source"] == "planned"),
                "storyboard_beats": len(beats),
                "unresolved_beats": len(unresolved),
            },
        },
        "poses": [
            {k: v for k, v in p.items() if k != "available"} | {"available": p["available"]}
            for p in POSES
        ],
        "demand": dict(sorted(demand.items(), key=lambda kv: -kv[1])),
        "generation_queue": [{"pose": pid, "beats": n} for pid, n in queue],
        "beat_routing": {k: sorted(v) for k, v in sorted(routed.items())},
        "unresolved_beats": sorted(set(unresolved)),
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    m = manifest["meta"]["counts"]
    print(f"poses.json: {m['available']}/{m['total_poses']} available, "
          f"{m['planned']} planned, {m['storyboard_beats']} storyboard beats "
          f"({m['unresolved_beats']} unresolved)")
    for pid, bs in sorted(routed.items(), key=lambda kv: -len(kv[1])):
        src = next(p["source"] for p in POSES if p["id"] == pid)
        print(f"  {pid:20s} {len(bs):3d} beats  [{src}]")
    if queue:
        print("\nnext to generate (most demanded first):")
        for pid, n in queue:
            print(f"  {pid:20s} {n:3d} beats")


if __name__ == "__main__":
    main()
