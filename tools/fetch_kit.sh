#!/usr/bin/env bash
# Re-fetch Smart Bark Kit v2, the production scripts, and the original Elly
# references.
#
# curl cannot reach drive.google.com from the sandbox (TLS is blocked), so these
# must be pulled with the google_drive connector's download_file tool, which
# writes into google_drive/ inside the workspace. Every ID below has been used
# successfully; the zips are gitignored, this script records how to get them.
set -euo pipefail

cat <<'EOS'
Kit v2 (34 MB) ................ download_file(file_id=1Myc8WX2GFenRmDUm_OUYtbkU8VCsZ57t)
Production scripts (17 KB) .... download_file(file_id=1EJkxPDJl8lR8H6HhzuAIa3uWyVdlrqTA)

Original Elly "Behavior" references (already committed to
assets/elly/references/ - only re-fetch if lost):

  01_Elly_Shocked_FamilyGuy .......... 1eXvfN3JWEXlplp4x28RR_6j6jUQif9Os
  03_Elly_Proud_PiggyBank_FamilyGuy .. 125zCTkGlQTS_Ko_XY-VAxB6MVvH-s8DW
  04_Elly_Worried_LoLang_FamilyGuy ... 1g5kajRZu9dzE9lGsoEiVkRkf5rdSTkTN
  05_Elly_Calculator_Confused ........ 10z2RymunGZTKf_oLyTmAoeszc8Xp_QBn
  06_Elly_Excited_HaoHung_FamilyGuy .. 1PFWU_jBcLUQoJRJgPmD2gERUkHTNYRQz
  07_Elly_Sitting_Quiet_FamilyGuy .... 1EXmIzzHONIY5zKSgNW8C7WBPiXCEdYuh
  08_Elly_Welcome_Waving_FamilyGuy ... 1nz8pkWqeZNs_4Uh5m2uDIVZgdeSNMGDg
  09_Elly_Thinking_SuyNghi_FamilyGuy . 1xQhHglFLzjFzPyoCFfQlWb1SJGmO0ygJ
  10_Elly_Crying_Buon_FamilyGuy ...... 1XJFdMNauWVTWvnBnn498cno6Qif6Wto9
  11_Elly_Angry_Mad_FamilyGuy ........ 1zk5jZJ2qM6Zrk51MWY7oCjU0415YbLGD
  12_Elly_Sleepy_Sleep_FamilyGuy ..... 1yOvIptjuJryMMNP0lulwgtElGUcGiekN

To find the containing folder again: search_files for name contains 'Elly'.

Then:
  unzip -q -o google_drive/Smart_Bark_Kit_v2.zip -d kit/v2
  unzip -q -o google_drive/Smart_Bark_Production_Scripts.zip -d kit/production_scripts
EOS
