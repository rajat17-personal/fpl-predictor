#!/usr/bin/env bash
# Weekly export (run before the gameweek deadline, e.g. Fridays 08:00 UTC):
#   1. refresh current-season per-player history (rolling form features)
#   2. export predictions + site JSON (xp table, captains, squad, ticker, chips)
#   3. render the email digest
#
# Cron line (WSL/VPS):
#   0 8 * * fri /home/sraja/fpl/scripts/weekly.sh >> /home/sraja/fpl/data/cron.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"

$PY -m data.live_history
$PY -m predict.export
$PY -m models.price          # watchlist alongside fresh table
$PY -m predict.digest
echo "[weekly] done $(date -u +%FT%TZ)"
