#!/usr/bin/env python3
"""Guard: no Elly artwork sourced from Google Drive may enter this project.

The client is explicit that Elly must be generated for EP015, not taken from the
Drive "Elly Behavior" masters or from Kit v2's knight-Elly set. Those files were
removed, but they are easy to reintroduce by accident (re-running fetch_kit.sh,
copying out of kit/, or anchoring a generation on them again).

This check fails the build if any of them come back:

  1. md5 blocklist  - fingerprints captured from the Drive files before deletion.
                      Catches a re-download even if the file is renamed.
  2. name patterns  - *FamilyGuy*, *elly_knight*, ELLY_KNIGHT*, *Elly_Behavior*
  3. location       - assets/elly/references/ must not exist
  4. git            - none of the above may be tracked in git history's index

Run as part of the pose pipeline, and in CI.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# md5 of every Drive-origin Elly image, captured before deletion.
#   assets/elly/references/  - the 11 "Elly Behavior" Family Guy masters
#   kit/.../elly_knight_*    - Kit v2's knight-Elly cutouts + pose sheet
BLOCKLIST_MD5 = {
    # "Elly Behavior" masters (Drive folder)
    "12ea65bab3d48d07d703ab275ef46fb9": "01_Elly_Shocked_FamilyGuy.jpg",
    "7f76a53f67acdd92f738c40d2297efce": "03_Elly_Proud_PiggyBank_FamilyGuy.jpg",
    "66388a8ee2f5a5232ec2155ca5dcb8ad": "04_Elly_Worried_LoLang_FamilyGuy.jpg",
    "90b52ac2139661cd038f3260be42ae3d": "05_Elly_Calculator_Confused_FamilyGuy.jpg",
    "d8345813ca375f3769edda21408257d4": "06_Elly_Excited_HaoHung_FamilyGuy.jpg",
    "8745db12365fbc52f5256edbad8e8c4e": "07_Elly_Sitting_Quiet_TinhLang_FamilyGuy.jpg",
    "057c8147cc65dc2b075bf2e043b54542": "08_Elly_Welcome_Waving_FamilyGuy.jpg",
    "e46cf28f3f50ee909f5ff530316ee3ae": "09_Elly_Thinking_SuyNghi_FamilyGuy.jpg",
    "09826c5663967766845a0526924ea570": "10_Elly_Crying_Buon_FamilyGuy.jpg",
    "02c5937e400b64b335eb3143f01c5b69": "11_Elly_Angry_Mad_FamilyGuy.jpg",
    "195d884f7da1b0a3051851ee57e3364d": "12_Elly_Sleepy_Sleep_FamilyGuy.jpg",
    # Kit v2 knight-Elly set
    "f4a8966fe4aaf3f31f5fc34dbc8f70ee": "ELLY_KNIGHT_POSES_SHEET.jpg",
    "cfb12893bb3e44fcb5d57638a012dea4": "elly_knight_cutouts/excited.png",
    "fac3f5b2a0b1382b13978ba7fed77c16": "elly_knight_cutouts/magnifier.png",
    "1afcd66d76b0a61a11cdc19841eaafd2": "elly_knight_cutouts/phone.png",
    "86d053af336fd3d0358082ea288365b1": "elly_knight_cutouts/point_self.png",
    "bfd8000a99627d0f94f31c364c313e9f": "elly_knight_cutouts/pointing.png",
    "d55d20f4b4d2e823f6951bf1e2226d15": "elly_knight_cutouts/proud.png",
    "ec96fdd20b457d0e291a2103fbeeb3ce": "elly_knight_cutouts/quill.png",
    "1c4b39d531607d5ba22b1c71c8479c7d": "elly_knight_cutouts/sad.png",
    "b0774aa540e4b6b10a3da2e35c73ce02": "elly_knight_cutouts/sitting.png",
    "6d17738eb115878a4956fe118ec1102b": "elly_knight_cutouts/surprised.png",
    "bf6e2551e7de57f50783cedfb9b0b263": "elly_knight_cutouts/thinking.png",
    "4c2a85ff720f331ac621bdab2503cbad": "elly_knight_cutouts/vip.png",
    "9552669edcae0d3f9ea701175a8d105e": "elly_knight_cutouts/welcome.png",
    "28ed89761cfc77b45e30dbf6941e7c04": "elly_knight_cutouts/worried.png",
}

BLOCKLIST_NAMES = ("familyguy", "elly_knight", "elly_behavior")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
# kit/ and google_drive/ are gitignored dependencies; they are allowed to hold
# the zip's contents, they just must never be tracked or copied into assets/.
SKIP_DIRS = {".git", "__pycache__", ".venv"}


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_images(base: Path):
    if base.name in SKIP_DIRS:
        return
    for p in sorted(base.iterdir()):
        if p.is_dir():
            if p.name in SKIP_DIRS:
                continue
            yield from walk_images(p)
        elif p.suffix.lower() in IMAGE_EXT:
            yield p


def main() -> int:
    problems: list[str] = []

    # 1 + 2: md5 blocklist and name patterns across the tracked project assets
    for scan_dir in ("assets", "docs"):
        d = ROOT / scan_dir
        if not d.exists():
            continue
        for p in walk_images(d):
            h = md5(p)
            if h in BLOCKLIST_MD5:
                problems.append(f"Drive image present: {p.relative_to(ROOT)} "
                                f"(matches {BLOCKLIST_MD5[h]})")
            low = p.name.lower()
            if any(n in low for n in BLOCKLIST_NAMES):
                problems.append(f"Drive-style filename: {p.relative_to(ROOT)}")

    # 3: the references folder must be gone
    if (ROOT / "assets" / "elly" / "references").exists():
        problems.append("assets/elly/references/ still exists (Drive masters live here)")

    # 4: nothing blocklisted may be tracked in git
    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout.split()
    except Exception:
        tracked = []
    for f in tracked:
        low = f.lower()
        if any(n in low for n in BLOCKLIST_NAMES) or "/references/" in f:
            problems.append(f"tracked in git: {f}")

    if problems:
        print("FAIL - Drive-sourced Elly artwork detected:")
        for p in problems:
            print(f"  - {p}")
        print("\nElly for EP015 must be generated, never taken from Drive.")
        return 1

    print("OK - no Drive-sourced Elly artwork in assets/, docs/ or git.")
    print(f"    {len(BLOCKLIST_MD5)} blocklisted fingerprints checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
