#!/usr/bin/env bash
# Boots two side-by-side uvicorn processes against the SAME live web/data
# export for Phase 7 parity validation (CUT-01, D-01/D-03): one plain
# (vanilla web/) and one with FPL_FRONTEND=react (built React app +
# live /data). On-demand sessions only -- nothing here runs 24/7; the
# daily/weekly cron keeps updating web/data/*.json regardless of whether
# either process is up.
#
# Never sets FPL_FIXTURE_DIR/FPL_FIXTURE_DATA_DIR on either process -- both
# uvicorns here always serve real, live pipeline output, never frozen E2E
# fixtures.
#
# Usage: bash scripts/dual_site.sh start|stop|status
#   DUAL_SITE_PYTHON         interpreter used to boot both uvicorn processes
#                            (default: /home/sraja/miniconda3/envs/python314/bin/python
#                            -- the project's conda interpreter, same seam
#                            convention as HARDENING_PYTHON/E2E_PYTHON)
#   DUAL_SITE_VANILLA_PORT   port the vanilla (unmodified web/) process binds
#                            (default: 8000 -- claimed ports: 8000 vanilla,
#                            8001 react per D-01, 8100-8102 E2E fixture
#                            variants, 8123 hardening, 8200 smoke)
#   DUAL_SITE_REACT_PORT     port the react (FPL_FRONTEND=react) process
#                            binds (default: 8001)
#   DUAL_SITE_PIDFILE        where both PIDs are recorded across start/stop
#                            (default: data/dual_site.pids)
set -euo pipefail
cd "$(dirname "$0")/.."

DUAL_SITE_PYTHON="${DUAL_SITE_PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"
DUAL_SITE_VANILLA_PORT="${DUAL_SITE_VANILLA_PORT:-8000}"
DUAL_SITE_REACT_PORT="${DUAL_SITE_REACT_PORT:-8001}"
DUAL_SITE_PIDFILE="${DUAL_SITE_PIDFILE:-data/dual_site.pids}"

LOOPBACK="127.0.0.1"
VANILLA_LOG="data/dual_site.vanilla.log"
REACT_LOG="data/dual_site.react.log"

usage() {
  echo "Usage: bash scripts/dual_site.sh start|stop|status"
}

# Loopback-only TCP connect probe -- true (0) when something is already
# listening on 127.0.0.1:<port>, false otherwise. No wildcard bind anywhere
# in this script; every uvicorn invocation below passes an explicit
# --host pinned to this same loopback address.
port_listening() {
  local port="$1"
  timeout 1 bash -c "echo >/dev/tcp/${LOOPBACK}/${port}" >/dev/null 2>&1
}

health_ok() {
  local port="$1"
  curl -fsS -m 2 "http://${LOOPBACK}:${port}/api/health" >/dev/null 2>&1
}

print_status_block() {
  if health_ok "$DUAL_SITE_VANILLA_PORT"; then
    echo "vanilla http://${LOOPBACK}:${DUAL_SITE_VANILLA_PORT} up"
  else
    echo "vanilla http://${LOOPBACK}:${DUAL_SITE_VANILLA_PORT} down"
  fi
  if health_ok "$DUAL_SITE_REACT_PORT"; then
    echo "react http://${LOOPBACK}:${DUAL_SITE_REACT_PORT} up"
  else
    echo "react http://${LOOPBACK}:${DUAL_SITE_REACT_PORT} down"
  fi
}

cmd_start() {
  # Refuse to adopt a foreign process -- a developer's own server already
  # bound to either port must never silently become the "reference" side of
  # a parity comparison.
  if port_listening "$DUAL_SITE_VANILLA_PORT"; then
    echo "FAILED: port ${DUAL_SITE_VANILLA_PORT} is already listening -- refusing to adopt a foreign process as the vanilla reference. Stop whatever is bound there, or override DUAL_SITE_VANILLA_PORT."
    exit 1
  fi
  if port_listening "$DUAL_SITE_REACT_PORT"; then
    echo "FAILED: port ${DUAL_SITE_REACT_PORT} is already listening -- refusing to adopt a foreign process as the react server. Stop whatever is bound there, or override DUAL_SITE_REACT_PORT."
    exit 1
  fi

  echo "[dual_site] building frontend (npm --prefix frontend run build)"
  npm --prefix frontend run build

  echo "[dual_site] starting vanilla on ${LOOPBACK}:${DUAL_SITE_VANILLA_PORT}"
  "$DUAL_SITE_PYTHON" -m uvicorn api.main:app --host "$LOOPBACK" \
    --port "$DUAL_SITE_VANILLA_PORT" >"$VANILLA_LOG" 2>&1 &
  local vanilla_pid=$!

  echo "[dual_site] starting react on ${LOOPBACK}:${DUAL_SITE_REACT_PORT}"
  FPL_FRONTEND=react "$DUAL_SITE_PYTHON" -m uvicorn api.main:app --host "$LOOPBACK" \
    --port "$DUAL_SITE_REACT_PORT" >"$REACT_LOG" 2>&1 &
  local react_pid=$!

  printf '%s\n%s\n' "$vanilla_pid" "$react_pid" >"$DUAL_SITE_PIDFILE"

  local vanilla_ready=0 react_ready=0
  for _ in $(seq 1 30); do
    health_ok "$DUAL_SITE_VANILLA_PORT" && vanilla_ready=1
    health_ok "$DUAL_SITE_REACT_PORT" && react_ready=1
    if [ "$vanilla_ready" -eq 1 ] && [ "$react_ready" -eq 1 ]; then
      break
    fi
    sleep 1
  done

  if [ "$vanilla_ready" -ne 1 ]; then
    echo "FAILED: vanilla server on ${LOOPBACK}:${DUAL_SITE_VANILLA_PORT} did not answer /api/health within 30s"
    echo "--- ${VANILLA_LOG} (tail) ---"
    tail -n 40 "$VANILLA_LOG" || true
    exit 1
  fi
  if [ "$react_ready" -ne 1 ]; then
    echo "FAILED: react server on ${LOOPBACK}:${DUAL_SITE_REACT_PORT} did not answer /api/health within 30s"
    echo "--- ${REACT_LOG} (tail) ---"
    tail -n 40 "$REACT_LOG" || true
    exit 1
  fi

  print_status_block
}

cmd_stop() {
  if [ ! -f "$DUAL_SITE_PIDFILE" ]; then
    echo "[dual_site] no pidfile at ${DUAL_SITE_PIDFILE} -- nothing to stop"
    return 0
  fi

  while IFS= read -r pid; do
    [ -z "$pid" ] && continue
    # A stale pidfile must never be able to kill an unrelated process --
    # only signal a pid whose own /proc cmdline names uvicorn.
    if [ -r "/proc/${pid}/cmdline" ] && tr '\0' ' ' <"/proc/${pid}/cmdline" | grep -q 'uvicorn'; then
      kill "$pid" 2>/dev/null || true
    else
      echo "[dual_site] refusing to signal pid ${pid} -- /proc/${pid}/cmdline does not name uvicorn (stale pidfile?)"
    fi
  done <"$DUAL_SITE_PIDFILE"

  for _ in $(seq 1 10); do
    if ! port_listening "$DUAL_SITE_VANILLA_PORT" && ! port_listening "$DUAL_SITE_REACT_PORT"; then
      break
    fi
    sleep 1
  done

  rm -f "$DUAL_SITE_PIDFILE"

  local still=0
  if port_listening "$DUAL_SITE_VANILLA_PORT"; then
    echo "still listening: ${LOOPBACK}:${DUAL_SITE_VANILLA_PORT}"
    still=1
  fi
  if port_listening "$DUAL_SITE_REACT_PORT"; then
    echo "still listening: ${LOOPBACK}:${DUAL_SITE_REACT_PORT}"
    still=1
  fi
  if [ "$still" -eq 1 ]; then
    exit 1
  fi
  echo "[dual_site] stopped"
}

cmd_status() {
  print_status_block
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  status) cmd_status ;;
  *)
    usage
    exit 1
    ;;
esac
