#!/usr/bin/env bash
# Weekly export (run before the gameweek deadline, e.g. Fridays 08:00 UTC):
#   1. refresh current-season per-player history (rolling form features)
#   2. export predictions + site JSON (xp table, captains, squad, ticker, chips)
#   3. render the email digest
#
# Every step runs through run_step: a failure is announced on stderr, recorded
# to the alerts file (and the webhook, if configured), and does not abort the
# remaining independent steps — but the script itself still exits non-zero if
# anything failed, so a broken run can never look green.
#
# Cron line (WSL/VPS):
#   0 8 * * fri /home/sraja/fpl/scripts/weekly.sh >> /home/sraja/fpl/data/cron.log 2>&1
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
    echo "[weekly] step $name OK"
  else
    local rc=$?
    echo "[weekly] step $name FAILED rc=$rc" >&2
    FAILED+=("$name")
    NOTIFIED=$((NOTIFIED + 1))
    if ! "$PY" -m ops.notify --job weekly --step "$name" --message "exit code $rc"; then
      echo "[weekly] alerting failed for $name" >&2
    fi
  fi
}

trap 'rc=$?; if [ "$rc" -ne 0 ] && [ "$NOTIFIED" -eq 0 ]; then if ! "$PY" -m ops.notify --job weekly --step unexpected --message "exit code $rc"; then echo "[weekly] alerting failed for unexpected" >&2; fi; fi' EXIT

run_step data.live_history "$PY" -m data.live_history
run_step predict.export "$PY" -m predict.export
run_step models.price "$PY" -m models.price
run_step predict.digest "$PY" -m predict.digest

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "[weekly] FAILED steps: ${FAILED[*]}" >&2
  exit 1
fi

echo "[weekly] done $(date -u +%FT%TZ)"
