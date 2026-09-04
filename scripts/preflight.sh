#!/usr/bin/env bash
# Local reproduction of the CI verification chain: runs the same gates
# .github/workflows/ci.yml's lint-build and test jobs run (hash-locked
# install, lint, frontend build + bundle guard, backend tests, frontend
# tests) plus the workflow-hygiene assertions this repo relies on before its
# first push, so a red pipeline is discovered here rather than on GitHub.
# Never installs into the developer's conda environment -- creates and
# removes its own venv.
#
# Usage: PREFLIGHT_PYTHON=/path/to/python3.14 bash scripts/preflight.sh
#   PREFLIGHT_PYTHON  interpreter used to create the ephemeral venv
#                      (default: python3 -- so this also works unmodified on
#                      a CI runner; set it to the conda 3.14 interpreter
#                      locally, the same seam convention E2E_PYTHON uses in
#                      e2e/playwright.config.ts)
set -euo pipefail
cd "$(dirname "$0")/.."

PREFLIGHT_PYTHON="${PREFLIGHT_PYTHON:-python3}"

GATE_NAMES=()
GATE_RESULTS=()

record() {
  GATE_NAMES+=("$1")
  GATE_RESULTS+=("$2")
}

announce() {
  echo "[preflight] $1"
}

fail() {
  echo "FAILED: [$1] $2"
  exit 1
}

# --- Gate 1/7: hash-locked environment ----------------------------------
announce "Gate 1/7: hash-locked environment (venv from PREFLIGHT_PYTHON=$PREFLIGHT_PYTHON)"
VENV_DIR="$(mktemp -d -t fpl-preflight-venv.XXXXXX)"
cleanup_venv() {
  rm -rf "$VENV_DIR"
}
trap cleanup_venv EXIT

if ! "$PREFLIGHT_PYTHON" -m venv "$VENV_DIR"; then
  fail "hash-locked environment" "'$PREFLIGHT_PYTHON -m venv' failed -- set PREFLIGHT_PYTHON to a valid Python 3.14 interpreter (e.g. the conda python314 env)."
fi

if ! "$VENV_DIR/bin/pip" install --require-hashes -r requirements.txt -r requirements-dev.txt; then
  fail "hash-locked environment" "pip install --require-hashes -r requirements.txt -r requirements-dev.txt failed -- see the pip output above."
fi
record "hash-locked environment" "PASS"
announce "Gate 1/7 OK"

# --- Gate 2/7: lint -------------------------------------------------------
announce "Gate 2/7: lint (ruff check .)"
if ! "$VENV_DIR/bin/ruff" check .; then
  fail "lint" "ruff check . reported violations -- fix them at the source (no ignore-list suppressions), or deliberately update ruff.toml's select/ignore if the rule set itself should change."
fi
record "lint" "PASS"
announce "Gate 2/7 OK"

# --- Gate 3/7: frontend build --------------------------------------------
announce "Gate 3/7: frontend build (npm --prefix frontend ci && npm --prefix frontend run build)"
if ! npm --prefix frontend ci; then
  fail "frontend build" "npm --prefix frontend ci failed -- see npm output above."
fi
if ! npm --prefix frontend run build; then
  fail "frontend build" "npm --prefix frontend run build failed -- see build output above."
fi
if [ ! -f frontend/dist/index.html ]; then
  fail "frontend build" "frontend/dist/index.html is missing after the build -- this is the exact bundle guard ci.yml's test job carries (RESEARCH.md Pitfall 5)."
fi
if [ ! -f frontend/dist/404.html ]; then
  fail "frontend build" "frontend/dist/404.html is missing after the build -- this is the exact bundle guard ci.yml's test job carries (RESEARCH.md Pitfall 5)."
fi
record "frontend build" "PASS"
announce "Gate 3/7 OK"

# --- Gate 4/7: backend tests ----------------------------------------------
announce "Gate 4/7: backend tests (python -m pytest)"
if ! "$VENV_DIR/bin/python" -m pytest; then
  fail "backend tests" "python -m pytest failed -- see pytest output above."
fi
record "backend tests" "PASS"
announce "Gate 4/7 OK"

# --- Gate 5/7: frontend tests ----------------------------------------------
announce "Gate 5/7: frontend tests (npm --prefix frontend test)"
if ! npm --prefix frontend test; then
  fail "frontend tests" "npm --prefix frontend test failed -- see vitest output above."
fi
record "frontend tests" "PASS"
announce "Gate 5/7 OK"

# --- Gate 6/7: workflow hygiene --------------------------------------------
announce "Gate 6/7: workflow hygiene (SHA pins, no schedule trigger, no personal email/credential literal)"

USES_TOTAL=$(grep -rhE '^[[:space:]]*-?[[:space:]]*uses:' .github/workflows/ | wc -l | tr -d ' ')
USES_PINNED=$(grep -rhE '^[[:space:]]*-?[[:space:]]*uses:[[:space:]]*[^[:space:]]+@[0-9a-f]{40}([[:space:]]|$)' .github/workflows/ | wc -l | tr -d ' ')
announce "uses=$USES_TOTAL sha_pinned=$USES_PINNED"
if [ "$USES_TOTAL" -eq 0 ] || [ "$USES_TOTAL" != "$USES_PINNED" ]; then
  fail "workflow hygiene" "$USES_PINNED/$USES_TOTAL uses: lines are SHA-pinned across .github/workflows/ -- every action must be pinned to a 40-character commit SHA (CI-04)."
fi

if grep -rlE '^[[:space:]]*schedule:' .github/workflows/ >/dev/null 2>&1; then
  fail "workflow hygiene" "a workflow carries a schedule: trigger -- D-12 requires workflow_dispatch-only until model delivery is settled next milestone."
fi

TRACKED_FILE_COUNT=$(git ls-files | wc -l | tr -d ' ')
announce "SCANNED $TRACKED_FILE_COUNT TRACKED FILES for personal email/credential-shaped literals"

# Email-shaped literal, plus a handful of common credential shapes (private
# key headers, AWS access keys, GitHub/Slack tokens, generic
# api/secret/access key-or-token assignments). Deliberately excludes the
# github-actions[bot] noreply address (D-11's own mandated commit identity)
# and doc-placeholder domains, which are not personal emails.
EMAIL_PATTERN='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
CRED_PATTERN='-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|(api|secret|access)[_-]?(key|token)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9_-]{16,}["'"'"']'
SAFE_ALLOWLIST='@users\.noreply\.github\.com|@example\.(com|org)'

HITS=$(git grep -InE "${EMAIL_PATTERN}|${CRED_PATTERN}" -- . 2>/dev/null | grep -viE "$SAFE_ALLOWLIST" || true)
if [ -n "$HITS" ]; then
  echo "--- tracked-file scan hits (personal email / credential-shaped literal) ---"
  printf '%s\n' "$HITS"
  fail "workflow hygiene" "a tracked file contains a personal email address or a credential-shaped literal (see hits above). This is a decision for the developer -- redact, or explicitly accept the risk for a private repo -- not something this script auto-fixes (D-16)."
fi

record "workflow hygiene" "PASS"
announce "Gate 6/7 OK"

# --- Gate 7/7: container ----------------------------------------------------
CONTAINER_CLI=""
if command -v docker >/dev/null 2>&1; then
  CONTAINER_CLI="docker"
elif command -v podman >/dev/null 2>&1; then
  CONTAINER_CLI="podman"
fi

if [ -z "$CONTAINER_CLI" ]; then
  announce "Gate 7/7 SKIPPED: container build + smoke test -- no container runtime (docker/podman) found on this machine. This gate is exercised by the CI image job instead."
  record "container build + smoke test" "SKIPPED"
else
  announce "Gate 7/7: container build + smoke test (using $CONTAINER_CLI)"
  if ! "$CONTAINER_CLI" build -t local/fpl:preflight .; then
    fail "container build + smoke test" "$CONTAINER_CLI build -t local/fpl:preflight . failed -- see build output above."
  fi
  if ! SMOKE_DOCKER="$CONTAINER_CLI" bash scripts/smoke_test.sh local/fpl:preflight; then
    fail "container build + smoke test" "scripts/smoke_test.sh local/fpl:preflight failed -- see smoke-test output above."
  fi
  record "container build + smoke test" "PASS"
  announce "Gate 7/7 OK"
fi

# --- Summary -----------------------------------------------------------
RAN=0
SKIPPED=0
echo ""
announce "==================== SUMMARY ===================="
for i in "${!GATE_NAMES[@]}"; do
  printf '[preflight]   %-32s %s\n' "${GATE_NAMES[$i]}" "${GATE_RESULTS[$i]}"
  if [ "${GATE_RESULTS[$i]}" = "SKIPPED" ]; then
    SKIPPED=$((SKIPPED + 1))
  else
    RAN=$((RAN + 1))
  fi
done
announce "$RAN gate(s) ran, $SKIPPED gate(s) skipped"
echo "PREFLIGHT PASSED"
