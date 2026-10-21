#!/usr/bin/env bash
# Re-fetch Smart Bark Kit v2 and the production scripts.
#
# curl cannot reach drive.google.com from the sandbox (TLS is blocked), so these
# must be pulled with the google_drive connector's download_file tool, which
# writes into google_drive/ inside the workspace. Both zips are gitignored.
#
# NOTE: this does NOT fetch Elly. Elly for EP015 is generated, never downloaded.
# The kit contains its own knight-Elly set and the Drive "Elly Behavior" masters
# exist too - neither may be copied into assets/. tools/check_no_drive_assets.py
# enforces that (md5 blocklist + filename patterns + git index scan).
set -euo pipefail

cat <<'EOS'
In the Arena chat, run (google_drive connector):

  download_file(file_id=1Myc8WX2GFenRmDUm_OUYtbkU8VCsZ57t)   # Kit v2 (34 MB)
  download_file(file_id=1EJkxPDJl8lR8H6HhzuAIa3uWyVdlrqTA)   # production scripts

Then:

  unzip -q -o google_drive/Smart_Bark_Kit_v2.zip -d kit/v2
  unzip -q -o google_drive/Smart_Bark_Production_Scripts.zip -d kit/production_scripts

Do not copy anything from kit/ into assets/elly/. Run the guard after any fetch:

  python3 tools/check_no_drive_assets.py
EOS
