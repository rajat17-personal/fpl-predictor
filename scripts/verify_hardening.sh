#!/usr/bin/env bash
# Phase 6 runtime proof: boots one real uvicorn process against the frozen
# v1 fixture set and asserts the six guarantees that only exist as
# properties of a real booted process with real middleware ordering and real
# environment resolution -- the CORS trust boundary, the liveness/readiness
# split, the structured request trail, secret redaction, and an actionable
# read failure. Plans 06-01 through 06-04 already prove their behavior
# against a `TestClient`; this script is the one place those same guarantees
# are re-proven against a genuinely running process (see 06-05-PLAN.md
# objective -- Phase 5 learned the hard way that this gap is where real bugs
# hide: a bare `pytest` missing the CWD on `sys.path`, a missing shared
# library for LightGBM).
#
# Never contacts the live FPL API and never loads a model artifact --
# FPL_FIXTURE_DIR is set unconditionally below, so this always boots in
# fixture mode against the committed e2e/fixtures/v1/normal set.
#
# Usage: HARDENING_PYTHON=/path/to/python3.14 bash scripts/verify_hardening.sh
#   HARDENING_PYTHON  interpreter used to boot uvicorn and run inline python
#                      checks (default: python3 -- same seam convention as
#                      PREFLIGHT_PYTHON in scripts/preflight.sh and
#                      E2E_PYTHON in e2e/playwright.config.ts)
#   HARDENING_PORT    port the verification uvicorn process listens on
#                      (default: 8123 -- distinct from 8000/8100-8102/8200,
#                      the ports the dev server, E2E servers and the
#                      container smoke test already claim)
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${HARDENING_PYTHON:-python3}"
HARDENING_PORT="${HARDENING_PORT:-8123}"

GATE_NAMES=()
GATE_RESULTS=()

record() {
  GATE_NAMES+=("$1")
  GATE_RESULTS+=("$2")
}

announce() {
  echo "[verify_hardening] $1"
}

fail() {
  echo "FAILED: [$1] $2"
  exit 1
}

# --- Sentinel configuration --------------------------------------------
# A key/origin this script owns outright, never the operator's real values --
# so a leak into the capture file is unambiguous and a real .env's
# FPL_API_KEYS/FPL_CORS_ORIGINS can never accidentally satisfy (or corrupt)
# these assertions (T-06-05-02, T-06-05-04).
SENTINEL_KEY="hardening-sentinel-key-do-not-log"
ALLOWED_ORIGIN="https://fpl.example.com"
DENIED_ORIGIN="https://evil.example.net"

CAPTURE_FILE="$(mktemp -t fpl-hardening-capture.XXXXXX)"
ALERT_LOG_FILE="$(mktemp -t fpl-hardening-alerts.XXXXXX)"
HEADERS_FILE="$(mktemp -t fpl-hardening-headers.XXXXXX)"
HEALTH_BODY_FILE="$(mktemp -t fpl-hardening-health.XXXXXX)"
READY_BODY_FILE="$(mktemp -t fpl-hardening-ready.XXXXXX)"

SERVER_PID=""

# EXIT trap: kills the background uvicorn process by PID and removes every
# temp file, so an assertion failure part-way through still tears everything
# down (T-06-05-03) -- this must be installed before the server is started.
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -f "$CAPTURE_FILE" "$ALERT_LOG_FILE" "$HEADERS_FILE" \
        "$HEALTH_BODY_FILE" "$READY_BODY_FILE"
}
trap cleanup EXIT

# --- Boot one real uvicorn process against the frozen fixture set --------
announce "booting uvicorn on 127.0.0.1:${HARDENING_PORT} (FPL_FIXTURE_DIR=e2e/fixtures/v1/normal)"
FPL_FIXTURE_DIR="e2e/fixtures/v1/normal" \
FPL_CORS_ORIGINS="$ALLOWED_ORIGIN" \
FPL_API_KEYS="$SENTINEL_KEY" \
FPL_ALERT_LOG="$ALERT_LOG_FILE" \
  "$PY" -m uvicorn api.main:app --host 127.0.0.1 --port "$HARDENING_PORT" \
  >"$CAPTURE_FILE" 2>&1 &
SERVER_PID=$!

HEALTH_READY=0
for _ in $(seq 1 30); do
  if curl -sS -o /dev/null "http://127.0.0.1:${HARDENING_PORT}/api/health" 2>/dev/null; then
    HEALTH_READY=1
    break
  fi
  sleep 1
done

if [ "$HEALTH_READY" -ne 1 ]; then
  echo "--- captured server output ---"
  cat "$CAPTURE_FILE" 2>/dev/null || true
  fail "boot" "http://127.0.0.1:${HARDENING_PORT}/api/health did not respond within 30s"
fi
announce "boot OK"

# --- Gate 1/6: SEC-01 denied origin --------------------------------------
announce "Gate 1/6: SEC-01 denied origin"
curl -sS -D "$HEADERS_FILE" -o /dev/null \
  -H "Origin: ${DENIED_ORIGIN}" \
  "http://127.0.0.1:${HARDENING_PORT}/api/health"
if grep -qi '^access-control-allow-origin:' "$HEADERS_FILE"; then
  fail "SEC-01 denied origin" "a request carrying Origin: ${DENIED_ORIGIN} received an access-control-allow-origin header -- FPL_CORS_ORIGINS is not restricting the trust boundary"
fi
record "SEC-01 denied origin" "PASS"
announce "Gate 1/6 OK"

# --- Gate 2/6: SEC-01 allowed origin --------------------------------------
# Also carries the sentinel X-API-Key header -- this is one of "the requests
# above" Gate 5 (SEC-03) asserts never leaked it, and a CORS preflight OPTIONS
# request never reaches a route handler, so this adds no solve-path cost.
announce "Gate 2/6: SEC-01 allowed origin"
curl -sS -D "$HEADERS_FILE" -o /dev/null -X OPTIONS \
  -H "Origin: ${ALLOWED_ORIGIN}" \
  -H "Access-Control-Request-Method: POST" \
  -H "X-API-Key: ${SENTINEL_KEY}" \
  "http://127.0.0.1:${HARDENING_PORT}/api/solve"
ALLOW_ORIGIN_LINE=$(grep -i '^access-control-allow-origin:' "$HEADERS_FILE" | tr -d '\r' || true)
ALLOW_ORIGIN_VALUE="${ALLOW_ORIGIN_LINE#*: }"
if [ "$ALLOW_ORIGIN_VALUE" != "$ALLOWED_ORIGIN" ]; then
  fail "SEC-01 allowed origin" "expected access-control-allow-origin: ${ALLOWED_ORIGIN}, got: ${ALLOW_ORIGIN_VALUE:-<absent>}"
fi
record "SEC-01 allowed origin" "PASS"
announce "Gate 2/6 OK"

# --- Gate 3/6: OBS-02 liveness and readiness ------------------------------
announce "Gate 3/6: OBS-02 liveness and readiness"
HEALTH_STATUS=$(curl -sS -D "$HEADERS_FILE" -o "$HEALTH_BODY_FILE" \
  -w '%{http_code}' "http://127.0.0.1:${HARDENING_PORT}/api/health")
if [ "$HEALTH_STATUS" != "200" ]; then
  fail "OBS-02 liveness and readiness" "/api/health returned HTTP ${HEALTH_STATUS}, expected 200"
fi
if ! grep -qi '^x-request-id:' "$HEADERS_FILE"; then
  fail "OBS-01 structured request log" "the /api/health response carried no X-Request-ID header"
fi

READY_STATUS=$(curl -sS -o "$READY_BODY_FILE" -w '%{http_code}' \
  "http://127.0.0.1:${HARDENING_PORT}/api/ready")
if [ "$READY_STATUS" != "200" ] && [ "$READY_STATUS" != "503" ]; then
  fail "OBS-02 liveness and readiness" "/api/ready returned unexpected HTTP status ${READY_STATUS}"
fi

KEYS_CHECK=$("$PY" - "$HEALTH_BODY_FILE" "$READY_BODY_FILE" <<'PYEOF'
import json
import sys

health_path, ready_path = sys.argv[1], sys.argv[2]
with open(health_path, encoding="utf-8") as f:
    health = json.load(f)
with open(ready_path, encoding="utf-8") as f:
    ready = json.load(f)

health_keys = set(health.keys())
ready_keys = set(ready.keys())
ok = (
    health_keys == {"ok", "gw", "pool_age_s"}
    and "ready" in ready_keys
    and health_keys != ready_keys
)
print("OK" if ok else f"BAD health_keys={sorted(health_keys)} ready_keys={sorted(ready_keys)}")
PYEOF
)
if [ "$KEYS_CHECK" != "OK" ]; then
  fail "OBS-02 liveness and readiness" "unexpected response body keys: ${KEYS_CHECK}"
fi
record "OBS-02 liveness and readiness" "PASS"
announce "Gate 3/6 OK"

# --- Gate 4/6: OBS-01 structured request log ------------------------------
announce "Gate 4/6: OBS-01 structured request log"
JSON_LOG_CHECK=$("$PY" - "$CAPTURE_FILE" <<'PYEOF'
import json
import sys

path = sys.argv[1]
found = False
with open(path, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        if (
            rec.get("event") == "http.request"
            and "request_id" in rec
            and "status" in rec
            and "duration_ms" in rec
        ):
            found = True
            break
print("FOUND" if found else "NOT_FOUND")
PYEOF
)
if [ "$JSON_LOG_CHECK" != "FOUND" ]; then
  fail "OBS-01 structured request log" "no captured stderr line parsed as a JSON object with event=http.request carrying request_id, status and duration_ms"
fi
record "OBS-01 structured request log" "PASS"
announce "Gate 4/6 OK"

# --- Gate 5/6: SEC-03 no secret in the trail ------------------------------
announce "Gate 5/6: SEC-03 no secret in the trail"
SECRET_CHECK=$("$PY" - "$CAPTURE_FILE" "$SENTINEL_KEY" <<'PYEOF'
import sys

path, secret = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8", errors="replace") as f:
    content = f.read()
print("LEAKED" if secret in content else "CLEAN")
PYEOF
)
if [ "$SECRET_CHECK" != "CLEAN" ]; then
  fail "SEC-03 no secret in the trail" "the sentinel X-API-Key value appears in the captured server output"
fi
record "SEC-03 no secret in the trail" "PASS"
announce "Gate 5/6 OK"

# --- Gate 6/6: REL-04 actionable read failure -----------------------------
announce "Gate 6/6: REL-04 actionable read failure"
MISSING_PATH="/tmp/fpl-hardening-does-not-exist-$$.json"
READ_JSON_CHECK=$("$PY" - "$MISSING_PATH" <<'PYEOF'
import sys

sys.path.insert(0, "")
from ops.jsonio import PayloadError, read_json

path = sys.argv[1]
try:
    read_json(path, what="hardening verification probe")
except PayloadError as exc:
    print("OK" if path in str(exc) else f"BAD_MESSAGE:{exc}")
except Exception as exc:  # noqa: BLE001 -- any other exception type is the failure
    print(f"WRONG_TYPE:{type(exc).__name__}: {exc}")
else:
    print("DID_NOT_RAISE")
PYEOF
)
if [ "$READ_JSON_CHECK" != "OK" ]; then
  fail "REL-04 actionable read failure" "ops.jsonio.read_json on a non-existent path did not raise an actionable PayloadError naming the path (${READ_JSON_CHECK})"
fi
record "REL-04 actionable read failure" "PASS"
announce "Gate 6/6 OK"

# --- Summary ---------------------------------------------------------------
RAN=0
SKIPPED=0
echo ""
announce "==================== SUMMARY ===================="
for i in "${!GATE_NAMES[@]}"; do
  printf '[verify_hardening]   %-32s %s\n' "${GATE_NAMES[$i]}" "${GATE_RESULTS[$i]}"
  if [ "${GATE_RESULTS[$i]}" = "SKIPPED" ]; then
    SKIPPED=$((SKIPPED + 1))
  else
    RAN=$((RAN + 1))
  fi
done
announce "$RAN gate(s) ran, $SKIPPED gate(s) skipped"
echo "HARDENING VERIFIED"
