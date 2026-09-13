#!/usr/bin/env bash
# Phase 9 (D-15): unattended experiment launcher. Detaches a
# `backtest.walk_forward` run so a long harness run survives a shell
# disconnect, with both stdout and stderr captured to a per-run log under
# data/processed/experiments/. Local WSL only, no cloud (D-15) -- this
# launcher is a developer-only tool, never invoked by CI, cron, or the API.
#
# Usage: scripts/experiment_run.sh <tag> [extra args passed to backtest.walk_forward]
#   scripts/experiment_run.sh baseline_phase9
#   scripts/experiment_run.sh capt_ceiling_lam03 --experiments capt_ceiling --seasons 2025-26
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"

if [ "$#" -lt 1 ]; then
  echo "[experiment] usage: scripts/experiment_run.sh <tag> [extra backtest.walk_forward args]" >&2
  exit 1
fi

TAG="$1"
shift

mkdir -p data/processed/experiments

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="data/processed/experiments/${TAG}-${TS}.log"

nohup "$PY" -m backtest.walk_forward --tag "$TAG" "$@" >"$LOG" 2>&1 &
PID=$!
disown "$PID" 2>/dev/null || true

echo "[experiment] tag=$TAG pid=$PID log=$LOG"
