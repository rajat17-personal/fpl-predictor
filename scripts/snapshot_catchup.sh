#!/usr/bin/env bash
# Anacron-style catch-up for the daily FPL bootstrap snapshot (D-08).
#
# WSL cron only fires while the machine is actually running -- it does not
# wake the machine, and it does not replay missed jobs. scripts/daily.sh's
# `30 2 * * *` cron line is therefore silently skipped on any day the machine
# is off at that moment. Since 2026-08-31, only 2 of 10 days were captured
# this way. Because data/snapshot.py::take_snapshot is already idempotent
# per UTC day (its `out.exists() and not force` guard), this script is a
# *scheduling* fix, not new capture logic: it is safe to invoke arbitrarily
# often -- on `@reboot`, on shell login, and from daily.sh's own gap-report
# step -- and only ever does real capture work on the first invocation of a
# given UTC day. It never modifies data/snapshot.py.
#
# Usage:
#   scripts/snapshot_catchup.sh                # capture today's snapshot if missing
#   scripts/snapshot_catchup.sh --report-only   # print the archive gap only, never capture
#   scripts/snapshot_catchup.sh --print-cron    # print the two crontab lines to install, nothing else
#
# On failure, alerts through the same ops.notify path scripts/daily.sh uses
# (FPL_ALERT_WEBHOOK, if configured) and exits with the real captured exit
# code -- a broken run can never look green.
#
# FPL_SNAPSHOT_DIR overrides the archive directory. It exists for tests
# ONLY -- production invocations (cron, boot, daily.sh) must pass nothing
# and use the real data/snapshots directory.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"
SNAP_DIR="${FPL_SNAPSHOT_DIR:-data/snapshots}"

print_cron() {
  echo "30 2 * * * /home/sraja/fpl/scripts/daily.sh >> /home/sraja/fpl/data/cron.log 2>&1"
  echo "@reboot /home/sraja/fpl/scripts/snapshot_catchup.sh >> /home/sraja/fpl/data/cron.log 2>&1"
}

# Always-on visibility (D-08): print how many snapshot days are missing from
# the archive so a growing gap is visible the day it starts, not months later.
gap_report() {
  local files_arr=() files earliest today_epoch earliest_epoch span_days missing_days
  shopt -s nullglob
  files_arr=("$SNAP_DIR"/*.parquet)
  shopt -u nullglob
  files=${#files_arr[@]}
  if [ "$files" -eq 0 ]; then
    echo "[catchup] archive: 0 files spanning 0 days (0 days missing)"
    return 0
  fi
  earliest=$(printf '%s\n' "${files_arr[@]}" | xargs -n1 basename | sed 's/\.parquet$//' | sort | head -n1)
  today_epoch=$(date -u -d "$TODAY" +%s)
  earliest_epoch=$(date -u -d "$earliest" +%s)
  span_days=$(( (today_epoch - earliest_epoch) / 86400 + 1 ))
  missing_days=$(( span_days - files ))
  echo "[catchup] archive: ${files} files spanning ${span_days} days (${missing_days} days missing)"
}

if [ "${1:-}" = "--print-cron" ]; then
  print_cron
  exit 0
fi

REPORT_ONLY=0
if [ "${1:-}" = "--report-only" ]; then
  REPORT_ONLY=1
fi

mkdir -p "$SNAP_DIR"
TODAY="$(date -u +%F)"
OUT="${SNAP_DIR}/${TODAY}.parquet"

if [ "$REPORT_ONLY" -eq 1 ]; then
  gap_report
  exit 0
fi

if [ -f "$OUT" ]; then
  echo "[catchup] ${TODAY}.parquet already present -- nothing to do"
  gap_report
  exit 0
fi

rc=0
if "$PY" -m data.snapshot; then
  echo "[catchup] captured ${TODAY}.parquet"
else
  rc=$?
  echo "[catchup] capture failed rc=$rc" >&2
  if "$PY" -m ops.notify --job catchup --step data.snapshot --message "exit code $rc"; then
    :
  else
    echo "[catchup] alerting failed" >&2
  fi
fi

gap_report

if [ "$rc" -ne 0 ]; then
  exit "$rc"
fi
exit 0
