#!/usr/bin/env bash
# Daily jobs (run every day, e.g. 02:30 UTC — after FPL's overnight price changes):
#   1. bootstrap snapshot   (price-model training data — the critical path)
#   2. price model training (no-op until enough days are collected)
#   3. watchlist refresh    (heuristic now, model once trained)
#   4. scoreboard update    (no-op unless a gameweek newly finished)
#
# Cron line (WSL/VPS):
#   30 2 * * * /home/sraja/fpl/scripts/daily.sh >> /home/sraja/fpl/data/cron.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"

$PY -m data.snapshot
$PY -m models.price --train || true
$PY -m models.price
$PY -m predict.scoreboard
echo "[daily] done $(date -u +%FT%TZ)"
