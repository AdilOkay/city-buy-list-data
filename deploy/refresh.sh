#!/usr/bin/env bash
# City Buy List - VPS price-data refresh (option A backend).
# Rebuilds the 4 volatile datasets from AODP and pushes them to this repo, so the
# app launcher pulls fresh averages on start. Runs on a small VPS via cron (every
# 4h). A dedicated VPS IP at this pace serves AODP cleanly (verified); do NOT drop
# the 2s pacing inside the scripts or you will hit AODP's global rate limit.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1                 # repo root (this script lives in deploy/)
LOG="deploy/refresh.log"
echo "==== $(date -u +%FT%TZ) refresh start ====" >> "$LOG"

git pull --quiet --rebase 2>>"$LOG" || echo "git pull warning" >> "$LOG"
for s in build_baseline build_materials build_toptraded build_routes; do
  python3 "scripts/$s.py" >> "$LOG" 2>&1 || echo "$s FAILED" >> "$LOG"
done

git add docs/data/baseline.json docs/data/materials.json docs/data/toptraded.json docs/data/routes.json
if git diff --cached --quiet; then
  echo "no data changes, nothing to commit" >> "$LOG"
else
  git commit -q -m "chore: scheduled price data refresh (VPS)" >> "$LOG" 2>&1
  git push -q >> "$LOG" 2>&1 && echo "pushed OK" >> "$LOG" || echo "PUSH FAILED - check the deploy key" >> "$LOG"
fi
echo "==== $(date -u +%FT%TZ) refresh end ====" >> "$LOG"
