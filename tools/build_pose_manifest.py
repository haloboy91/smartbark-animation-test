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
POSES = [
    # ---- original Family Guy reference set (identity anchor) ----
    dict(id="shocked", file="01_Elly_Shocked_FamilyGuy", source="reference",
         tags=["shock", "shocked", "startled", "surprised", "surprise", "eyes widen",
               "stunned", "recoil", "jaw", "admiration", "startled jump"],
         note="Original master reference."),
    dict(id="ref03", file="03_Elly_Proud_PiggyBank_FamilyGuy", source="reference",
         tags=["proud", "worried"],
         note="LABEL UNVERIFIED - filename says proud/piggybank, kit README says this file is actually 'worried'. Needs visual confirmation."),
    dict(id="ref04", file="04_Elly_Worried_LoLang_FamilyGuy", source="reference",
         tags=["worried", "proud"],
         note="LABEL UNVERIFIED - filename says worried, kit README says this file is actually 'proud (piggy bank)'. Needs visual confirmation."),
    dict(id="confused", file="05_Elly_Calculator_Confused_FamilyGuy", source="reference",
         tags=["confused", "puzzled", "doubtful", "counting", "puzzled", "perplexed"],
         note="Original master reference with calculator prop."),
    dict(id="ref06", file="06_Elly_Excited_HaoHung_FamilyGuy", source="reference",
         tags=["excited", "waving", "energetic"],
         note="LABEL UNVERIFIED - filename says excited, kit README says this file is actually 'waving'."),
    dict(id="ref07", file="07_Elly_Sitting_Quiet_TinhLang_FamilyGuy", source="reference",
         tags=["sitting", "excited", "listening", "quiet"],
         note="LABEL UNVERIFIED - filename says sitting/quiet, kit README says this file is actually 'excited'."),
    dict(id="ref08", file="08_Elly_Welcome_Waving_FamilyGuy", source="reference",
         tags=["welcome", "waving", "sitting", "greeting"],
         note="LABEL UNVERIFIED - filename says welcome/waving, kit README says this file is actually 'sitting'. 1920x1280 source."),
    dict(id="think", file="09_Elly_Thinking_SuyNghi_FamilyGuy", source="reference",
         tags=["thinking", "thoughtful", "skeptical", "side-eye", "curious", "puzzled"],
         note="CONFIRMED - this is the master the client supplied for EP015."),
    dict(id="ref10", file="10_Elly_Crying_Buon_FamilyGuy", source="reference",
         tags=["crying", "sleepy", "sad"],
         note="LABEL UNVERIFIED - filename says crying, kit README says this file is actually 'sleepy'."),
    dict(id="angry", file="11_Elly_Angry_Mad_FamilyGuy", source="reference",
         tags=["angry", "mad", "firm", "precise", "emphatic", "insistent"],
         note="Original master reference."),
    dict(id="ref12", file="12_Elly_Sleepy_Sleep_FamilyGuy", source="reference",
         tags=["sleepy", "crying", "sad", "solemn"],
         note="LABEL UNVERIFIED - filename says sleepy, kit README says this file is actually 'crying'."),

    # ---- generated for EP015 (batch 1) ----
    dict(id="point_side", file="elly_point_side", source="generated",
         tags=["point", "pointing", "points", "indicate", "present", "tracks", "follows",
               "traces", "raises", "lowers paw", "paw", "at each", "toward", "direction"],
         note="Highest-demand gap: 'Elly points at...' occurs ~20x in the storyboard; the original 14 have no clean pointing pose."),
    dict(id="teach_pointer", file="elly_teach_pointer", source="generated",
         tags=["teacher", "explains", "explanatory", "classroom", "pointer", "lecture",
               "introducing", "introduces", "mechanism", "steps", "quadrants", "presentation"],
         note="Explainer chapters 1/3/5/7."),
    dict(id="count_paws", file="elly_count_paws", source="generated",
         tags=["counting", "counts", "tally", "numbers", "emphasizes", "repeated", "tally"],
         note="Short-selling worked example, margin math."),
    dict(id="alarmed_pawmouth", file="elly_alarmed_pawmouth", source="generated",
         tags=["alarmed", "gasps", "shocked", "paw to mouth"],
         note="Crash beats; distinct from the flat 'shocked' stare."),
    dict(id="wince", file="elly_wince", source="generated",
         tags=["wince", "winces", "flinch", "flinches", "grimace", "anxious", "distressed",
               "daydreams", "upward", "looks", "observes", "protective"],
         note="Crash + Livermore downfall."),
    dict(id="solemn_direct", file="elly_solemn_direct", source="generated",
         tags=["solemn", "somber", "sober", "serious", "direct-to-viewer", "respectful", "empathy",
               "sympathetic", "memorial", "concerned", "concern", "frown", "honest", "kind",
               "sincere", "quiet concern", "composed", "still", "listens"],
         note="MANDATORY for the suicide reference (Ch6) and all hardship beats - no gag, no comedy stinger."),
    dict(id="skeptical_brow", file="elly_skeptical_brow", source="generated",
         tags=["skeptical", "raised eyebrow", "side-eye", "doubtful", "intrigued", "wary",
               "smirk", "amused", "knowing", "half-smile", "incredulous", "recognition",
               "curious", "questions", "questioningly", "eyebrow", "brow"],
         note="Shoeshine-tale debunk, 'sounds familiar?' irony beats."),
    dict(id="deadpan", file="elly_deadpan", source="generated",
         tags=["deadpan", "dry", "eye-roll", "flat", "unimpressed", "matter-of-fact"],
         note="Comedy irony without a cartoon gag."),
    dict(id="relieved", file="elly_relieved", source="generated",
         tags=["relieved", "hopeful", "hope", "guarded optimism", "calm", "reassuring",
               "reassuring nod", "softens", "expression rises", "satisfied", "survive"],
         note="Chapter 5 liquidity + Chapter 7 recovery."),

    # ---- still to generate ----
    dict(id="magnifier", file="elly_magnifier", source="planned",
         tags=["investigative", "inspect", "magnifier", "examine", "investigative expression",
               "insight", "shifts", "distressed", "studies"],
         note="Ch3/Ch6 investigation beats."),
    dict(id="coin", file="elly_coin", source="planned",
         tags=["coin", "cash", "money", "liquid", "savings"],
         note="Ch5 'When Cash Becomes Power' hero prop."),
    dict(id="newspaper", file="elly_newspaper", source="planned",
         tags=["newspaper", "headline", "black thursday", "ticker"],
         note="Ch2 Black Thursday / Black Tuesday. No legible text in the art."),
    dict(id="umbrella", file="elly_umbrella", source="planned",
         tags=["umbrella", "storm", "protect", "shelter", "survive"],
         note="Ch7 'SURVIVE THE STORM' shot - capital protected under an umbrella."),
    dict(id="newsboy_hat", file="elly_newsboy_hat", source="planned",
         tags=["hat", "1920s", "era", "flapper", "period"],
         note="Client-approved era flourish: signature outfit + a 1920s newsboy cap."),
    dict(id="ledger", file="elly_ledger", source="planned",
         tags=["ledger", "notebook", "records", "books", "balances"],
         note="Quotation-office / bookkeeping beats."),
    dict(id="firm_headshake", file="elly_firm_headshake", source="planned",
         tags=["head-shake", "shakes head", "firm", "refuses", "corrects", "correction",
               "direct-to-camera", "emphasizes unchanged"],
         note="'A CRISIS IS NOT GOOD NEWS' + 'NOT ABOUT PREDICTION'."),
    dict(id="recoil", file="elly_recoil", source="planned",
         tags=["recoils", "pulls paw away", "wary", "steps back", "caution", "cautioning",
               "warns", "warning", "raises caution", "holds warning", "precise", "firm"],
         note="Margin-call / debt-chain danger beats."),
    dict(id="present_three", file="elly_present_three", source="planned",
         tags=["three", "three fingers", "three points", "lists"],
         note="Ch7 'three important differences' recurring motif."),
    dict(id="calm_nod", file="elly_calm_nod", source="planned",
         tags=["nod", "nods", "acknowledging", "composed", "listening", "approving",
               "measured", "satisfied", "calm", "presenting both"],
         note="Low-energy connective beats; keeps pose churn down in long shots."),
    dict(id="point_self", file="elly_point_self", source="planned",
         tags=["point self", "me", "direct address", "introduces"],
         note="Chapter-turn direct address."),
    dict(id="open_arms", file="elly_open_arms", source="planned",
         tags=["open arms", "explains", "presents", "both paws", "gestures", "gesture",
               "moderating", "compares", "comparing", "contrasts", "sides", "both",
               "presents both", "across", "left", "right", "switches", "two-paw"],
         note="Two-sided comparison shots (Investor A vs Investor B)."),
    dict(id="empathetic", file="elly_empathetic", source="planned",
         tags=["empathetic", "sympathetic", "kind", "soft", "breadline", "hardship"],
         note="Breadline / unemployment. Must not read as comic."),
    dict(id="peek_side", file="elly_peek_side", source="planned",
         tags=["half-smile", "smiling side-eye", "amused", "knowing", "smirk"],
         note="Light irony beats where deadpan is too flat."),
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
