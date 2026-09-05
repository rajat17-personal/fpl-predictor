#!/usr/bin/env bash
# Proves the Vite dev-server proxy seam end to end:
#   1. start uvicorn (the real backend) on :8000
#   2. start the Vite dev server on :5173
#   3. through port 5173 only, assert /data/meta.json, /api/health, and / all resolve
#      the way they would in production (StaticFiles mount + FastAPI routes)
#
# Usage: bash scripts/verify_dev_proxy.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-/home/sraja/miniconda3/envs/python314/bin/python}"

UVICORN_PID=""
VITE_PID=""

cleanup() {
  if [ -n "$VITE_PID" ] && kill -0 "$VITE_PID" 2>/dev/null; then
    kill "$VITE_PID" 2>/dev/null || true
    wait "$VITE_PID" 2>/dev/null || true
  fi
  if [ -n "$UVICORN_PID" ] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
  fi
  # `npm run dev` spawns vite as a child process of npm itself, so killing the
  # tracked $VITE_PID (npm) alone can leave the real vite listener orphaned on
  # port 5173. Belt-and-suspenders: kill anything still bound to either port.
  for port in 8000 5173; do
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      # shellcheck disable=SC2086
      kill $pids 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

echo "[verify_dev_proxy] starting uvicorn on :8000"
"$PY" -m uvicorn api.main:app --host 127.0.0.1 --port 8000 >/tmp/verify_dev_proxy_uvicorn.log 2>&1 &
UVICORN_PID=$!

echo "[verify_dev_proxy] starting vite dev server on :5173"
npm --prefix frontend run dev -- --port 5173 --strictPort >/tmp/verify_dev_proxy_vite.log 2>&1 &
VITE_PID=$!

wait_for() {
  local url="$1" label="$2" tries=60
  for ((i = 0; i < tries; i++)); do
    if node -e "fetch(process.argv[1]).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" "$url" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "FAILED: $label did not answer within ${tries}s ($url)"
  echo "--- uvicorn log ---"; cat /tmp/verify_dev_proxy_uvicorn.log 2>/dev/null || true
  echo "--- vite log ---"; cat /tmp/verify_dev_proxy_vite.log 2>/dev/null || true
  return 1
}

wait_for "http://127.0.0.1:8000/api/health" "uvicorn"
wait_for "http://localhost:5173/" "vite dev server"

echo "[verify_dev_proxy] asserting through port 5173 only"

META_JSON=$(node -e "
fetch('http://localhost:5173/data/meta.json').then(async r => {
  if (!r.ok) { console.error('status ' + r.status); process.exit(1); }
  const body = await r.json();
  if (typeof body.gw !== 'number') { console.error('gw is not numeric: ' + JSON.stringify(body.gw)); process.exit(1); }
  console.log(JSON.stringify(body));
}).catch(e => { console.error(String(e)); process.exit(1); });
") || { echo "FAILED: GET /data/meta.json — $META_JSON"; exit 1; }
echo "  /data/meta.json OK: $META_JSON"

HEALTH_JSON=$(node -e "
fetch('http://localhost:5173/api/health').then(async r => {
  if (!r.ok) { console.error('status ' + r.status); process.exit(1); }
  const body = await r.json();
  if (body.ok !== true) { console.error('ok is not true: ' + JSON.stringify(body.ok)); process.exit(1); }
  console.log(JSON.stringify(body));
}).catch(e => { console.error(String(e)); process.exit(1); });
") || { echo "FAILED: GET /api/health — $HEALTH_JSON"; exit 1; }
echo "  /api/health OK: $HEALTH_JSON"

ROOT_HTML=$(node -e "
fetch('http://localhost:5173/').then(async r => {
  if (!r.ok) { console.error('status ' + r.status); process.exit(1); }
  const body = await r.text();
  if (!/id=\"root\"/.test(body)) { console.error('no root mount element found'); process.exit(1); }
  console.log('has-root-element');
}).catch(e => { console.error(String(e)); process.exit(1); });
") || { echo "FAILED: GET / — $ROOT_HTML"; exit 1; }
echo "  / OK: root mount element present"

echo "DEV PROXY OK"
