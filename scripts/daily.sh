#!/usr/bin/env bash
# Daily jobs (run every day, e.g. 02:30 UTC — after FPL's overnight price changes):
#   1. bootstrap snapshot   (price-model training data — the critical path)
#   2. price model training (no-op until enough days are collected)
#   3. watchlist refresh    (heuristic now, model once trained)
#   4. scoreboard update    (no-op unless a gameweek newly finished)
#
# Every step runs through run_step: a failure is announced on stderr, recorded
# to the alerts file (and the webhook, if configured), and does not abort the
# remaining independent steps — but the script itself still exits non-zero if
# anything failed, so a broken run can never look green.
#
# Cron line (WSL/VPS):
#   30 2 * * * /home/sraja/fpl/scripts/daily.sh >> /home/sraja/fpl/data/cron.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"

FAILED=()
NOTIFIED=0

# Runs COMMAND inside an if-condition, which `set -e` never fires for — a
# failing step is caught here instead of aborting the whole script.
run_step() {
  local name="$1"
  shift
  if "$@"; then
    echo "[daily] step $name OK"
  else
    local rc=$?
    echo "[daily] step $name FAILED rc=$rc" >&2
    FAILED+=("$name")
    NOTIFIED=$((NOTIFIED + 1))
    if ! "$PY" -m ops.notify --job daily --step "$name" --message "exit code $rc"; then
      echo "[daily] alerting failed for $name" >&2
    fi
  fi
}

trap 'rc=$?; if [ "$rc" -ne 0 ] && [ "$NOTIFIED" -eq 0 ]; then if ! "$PY" -m ops.notify --job daily --step unexpected --message "exit code $rc"; then echo "[daily] alerting failed for unexpected" >&2; fi; fi' EXIT

run_step data.snapshot "$PY" -m data.snapshot
run_step models.price-train "$PY" -m models.price --train
run_step models.price "$PY" -m models.price
run_step predict.scoreboard "$PY" -m predict.scoreboard

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "[daily] FAILED steps: ${FAILED[*]}" >&2
  exit 1
fi

echo "[daily] done $(date -u +%FT%TZ)"
