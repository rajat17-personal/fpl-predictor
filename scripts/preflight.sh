#!/usr/bin/env bash
# Local reproduction of the CI verification chain: runs the same gates
# .github/workflows/ci.yml's lint-build and test jobs run (hash-locked
# install, lint, frontend build + bundle guard, backend tests, frontend
# tests) plus the workflow-hygiene and Phase 6 hardening assertions this
# repo relies on before its first push, so a red pipeline is discovered here
# rather than on GitHub. Never installs into the developer's conda
# environment -- creates and removes its own venv.
#
# The Phase 6 pytest modules (tests/test_reliability.py, tests/test_cron.py,
# tests/test_api_hardening.py, tests/test_obs.py) need no dedicated gate of
# their own here: Gate 4's `python -m pytest` run already collects and runs
# them, and .github/workflows/ci.yml's `test` job runs the identical
# `python -m pytest` on every push -- no CI workflow change is needed or
# wanted for them.
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

# --- Gate 1/8: hash-locked environment ----------------------------------
announce "Gate 1/8: hash-locked environment (venv from PREFLIGHT_PYTHON=$PREFLIGHT_PYTHON)"
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
announce "Gate 1/8 OK"

# --- Gate 2/8: lint -------------------------------------------------------
announce "Gate 2/8: lint (ruff check .)"
if ! "$VENV_DIR/bin/ruff" check .; then
  fail "lint" "ruff check . reported violations -- fix them at the source (no ignore-list suppressions), or deliberately update ruff.toml's select/ignore if the rule set itself should change."
fi
record "lint" "PASS"
announce "Gate 2/8 OK"

# --- Gate 3/8: frontend build --------------------------------------------
announce "Gate 3/8: frontend build (npm --prefix frontend ci && npm --prefix frontend run build)"
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
announce "Gate 3/8 OK"

# --- Gate 4/8: backend tests ----------------------------------------------
announce "Gate 4/8: backend tests (python -m pytest)"
if ! "$VENV_DIR/bin/python" -m pytest; then
  fail "backend tests" "python -m pytest failed -- see pytest output above."
fi
record "backend tests" "PASS"
announce "Gate 4/8 OK"

# --- Gate 5/8: frontend tests ----------------------------------------------
announce "Gate 5/8: frontend tests (npm --prefix frontend test)"
if ! npm --prefix frontend test; then
  fail "frontend tests" "npm --prefix frontend test failed -- see vitest output above."
fi
record "frontend tests" "PASS"
announce "Gate 5/8 OK"

# --- Gate 6/8: workflow hygiene --------------------------------------------
announce "Gate 6/8: workflow hygiene (SHA pins, no schedule trigger, no personal email/credential literal)"

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
announce "Gate 6/8 OK"

# --- Gate 7/8: phase 6 hardening (file handles, cron suppression, CORS, secrets, runtime) ---
announce "Gate 7/8: phase 6 hardening (file handles, cron suppression, CORS, secrets, runtime)"

# 1. File handles (REL-01) -- no tracked Python file opens a file outside a
# context manager. The scanned-file count is printed with its own announce
# line so a vacuous pass (an empty file list) is visible in the output --
# never omitted, never counted as a pass (T-06-05-01).
PY_FILES=$(git ls-files '*.py')
PY_FILE_COUNT=$(printf '%s\n' "$PY_FILES" | grep -c . || true)
announce "SCANNED $PY_FILE_COUNT TRACKED PYTHON FILES for bare file handles"
BARE_OPEN_HITS=$(printf '%s\n' "$PY_FILES" | xargs grep -nE '(^|[^A-Za-z0-9_.])open\(' 2>/dev/null | grep -v 'with open(' || true)
if [ -n "$BARE_OPEN_HITS" ]; then
  echo "--- bare file-handle hits ---"
  printf '%s\n' "$BARE_OPEN_HITS"
  fail "phase 6 hardening" "a tracked Python file opens a file outside a context manager (see hits above) -- route it through ops.jsonio.read_json/write_json instead (REL-01)."
fi

# 2. Cron suppression (REL-02/OBS-03) -- no shell OR-suppression operator in
# a non-comment line of either cron script or GitHub Actions workflow.
# Comment lines are filtered before counting so a comment mentioning '||'
# cannot fail its own gate.
CRON_SUPPRESSION_HITS=$(grep -vE '^[[:space:]]*#' scripts/daily.sh scripts/weekly.sh \
  .github/workflows/daily.yml .github/workflows/weekly.yml | grep -F '||' || true)
if [ -n "$CRON_SUPPRESSION_HITS" ]; then
  echo "--- shell-suppression hits ---"
  printf '%s\n' "$CRON_SUPPRESSION_HITS"
  fail "phase 6 hardening" "a shell OR-suppression operator (||) appears in a non-comment line of a cron script or workflow (see hits above) -- REL-02/OBS-03 require every step's real exit code to surface, not be silently swallowed."
fi

# 3. CORS (SEC-01) -- no wildcard in the allow-origins/methods/headers
# middleware arguments, and the boundary is configurable via FPL_CORS_ORIGINS
# rather than hardcoded.
CORS_WILDCARD_HITS=$(grep -nE 'allow_(origins|methods|headers)' api/main.py | grep -F '*' || true)
if [ -n "$CORS_WILDCARD_HITS" ]; then
  echo "--- CORS wildcard hits ---"
  printf '%s\n' "$CORS_WILDCARD_HITS"
  fail "phase 6 hardening" "a CORS middleware argument in api/main.py contains a wildcard (see hits above) -- SEC-01 requires an explicit origin/method/header allowlist."
fi
if ! grep -q 'FPL_CORS_ORIGINS' api/main.py; then
  fail "phase 6 hardening" "api/main.py does not reference FPL_CORS_ORIGINS -- the CORS trust boundary must be configurable via environment, not hardcoded (SEC-01)."
fi

# 4. Secrets (SEC-03) -- a tracked, valueless .env.example naming every
# variable; a real .env is git-ignored and can never be committed.
if [ ! -f .env.example ] || ! git ls-files --error-unmatch .env.example >/dev/null 2>&1; then
  fail "phase 6 hardening" ".env.example is missing or not tracked -- SEC-03 requires a committed, valueless template naming every project env var."
fi
if ! git check-ignore -q .env; then
  fail "phase 6 hardening" ".env is not git-ignored -- a real .env must never be committable (SEC-03)."
fi
ENV_EXAMPLE_BAD_LINES=$(grep -vE '^[[:space:]]*(#.*)?$' .env.example | grep -vE '^[A-Z][A-Z0-9_]*=$' || true)
if [ -n "$ENV_EXAMPLE_BAD_LINES" ]; then
  echo "--- .env.example non-conforming lines ---"
  printf '%s\n' "$ENV_EXAMPLE_BAD_LINES"
  fail "phase 6 hardening" ".env.example contains a line that is not an uppercase KEY= with no assigned value (see hits above) -- a real value there would leak a secret into a tracked file (SEC-03)."
fi

# 5. Secret file mode (SEC-03) -- when a real .env exists on this machine,
# its permission bits must be exactly 600. When it does not exist, this
# sub-check is recorded as SKIPPED by name rather than silently passed
# (T-06-05-01) -- a gate that silently skips is worse than no gate.
if [ -f .env ]; then
  ENV_MODE=$(stat -c '%a' .env 2>/dev/null || stat -f '%Lp' .env 2>/dev/null || echo '')
  if [ "$ENV_MODE" != "600" ]; then
    fail "phase 6 hardening" ".env exists but is mode $ENV_MODE, not 600 -- run 'chmod 600 .env' (SEC-03)."
  fi
  record ".env file mode" "PASS"
else
  # Lowercase "skipped" here deliberately -- the summary table row below is
  # the single, canonical place this sub-check's SKIPPED status is recorded
  # by name (uppercase), so a `grep -c SKIPPED` over this script's whole
  # output counts each real skip exactly once, not once per mention.
  announce "no .env on this machine -- .env file mode sub-check recorded as skipped, not silently passed"
  record ".env file mode" "SKIPPED"
fi

# 6. Runtime proof -- the five static checks above cannot see a real CORS
# response header, a real structured log line, or a real secret-redaction
# failure; scripts/verify_hardening.sh boots a genuine uvicorn process
# against the frozen fixture set and proves those. Runs inside this script's
# own hash-locked ephemeral venv, never the developer's conda environment.
if ! HARDENING_PYTHON="$VENV_DIR/bin/python" bash scripts/verify_hardening.sh; then
  fail "phase 6 hardening" "scripts/verify_hardening.sh failed -- see its own output above."
fi

record "phase 6 hardening" "PASS"
announce "Gate 7/8 OK"

# --- Gate 8/8: container ----------------------------------------------------
CONTAINER_CLI=""
if command -v docker >/dev/null 2>&1; then
  CONTAINER_CLI="docker"
elif command -v podman >/dev/null 2>&1; then
  CONTAINER_CLI="podman"
fi

if [ -z "$CONTAINER_CLI" ]; then
  # Lowercase "skipped" for the same reason as the .env-mode sub-check above
  # -- the summary table row is the single canonical SKIPPED-by-name record.
  announce "Gate 8/8 skipped: container build + smoke test -- no container runtime (docker/podman) found on this machine. This gate is exercised by the CI image job instead."
  record "container build + smoke test" "SKIPPED"
else
  announce "Gate 8/8: container build + smoke test (using $CONTAINER_CLI)"
  if ! "$CONTAINER_CLI" build -t local/fpl:preflight .; then
    fail "container build + smoke test" "$CONTAINER_CLI build -t local/fpl:preflight . failed -- see build output above."
  fi
  if ! SMOKE_DOCKER="$CONTAINER_CLI" bash scripts/smoke_test.sh local/fpl:preflight; then
    fail "container build + smoke test" "scripts/smoke_test.sh local/fpl:preflight failed -- see smoke-test output above."
  fi
  record "container build + smoke test" "PASS"
  announce "Gate 8/8 OK"
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
