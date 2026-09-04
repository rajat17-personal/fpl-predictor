#!/usr/bin/env bash
# CI-03 container smoke test: proves a real integer program runs through the
# CBC binary bundled inside the built image, not merely that `import pulp`
# succeeds. Boots the image in fixture mode (FPL_FIXTURE_DIR, no model
# artifact needed -- D-05/D-07), asserts /api/health, then POSTs a genuine
# from-scratch /api/solve and counts the 15 squad slots the ILP must produce.
#
# Usage: bash scripts/smoke_test.sh <image-tag>
#   SMOKE_DOCKER  container CLI to use (default: docker)
#   SMOKE_PORT    host port to publish (default: 8200 -- never 8000, a
#                 developer's own `uvicorn api.main:app --port 8000` serving
#                 live data would be silently adopted otherwise, the same
#                 trap e2e/playwright.config.ts documents for its own port
#                 choice)
set -euo pipefail
cd "$(dirname "$0")/.."

SMOKE_DOCKER="${SMOKE_DOCKER:-docker}"
SMOKE_PORT="${SMOKE_PORT:-8200}"

if [ "$#" -lt 1 ]; then
  echo "FAILED: no image tag given. Usage: bash scripts/smoke_test.sh <image-tag>"
  exit 1
fi
IMAGE_TAG="$1"

if ! command -v "$SMOKE_DOCKER" >/dev/null 2>&1; then
  echo "FAILED: container runtime '$SMOKE_DOCKER' not found (selected via SMOKE_DOCKER=$SMOKE_DOCKER). Override with SMOKE_DOCKER=<cli> if your runtime isn't named 'docker' (e.g. podman)."
  exit 1
fi

CONTAINER_NAME="fpl-smoke-$$"

cleanup() {
  "$SMOKE_DOCKER" rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[smoke_test] starting $IMAGE_TAG as $CONTAINER_NAME on port $SMOKE_PORT"
"$SMOKE_DOCKER" run -d --name "$CONTAINER_NAME" \
  -p "${SMOKE_PORT}:8000" \
  -e FPL_FIXTURE_DIR=/fixtures/v1/normal \
  -v "$(pwd)/e2e/fixtures:/fixtures:ro" \
  "$IMAGE_TAG" >/dev/null

echo "[smoke_test] polling /api/health"
HEALTH_OK=0
for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:${SMOKE_PORT}/api/health" >/dev/null 2>&1; then
    HEALTH_OK=1
    break
  fi
  sleep 1
done

if [ "$HEALTH_OK" -ne 1 ]; then
  echo "FAILED: http://localhost:${SMOKE_PORT}/api/health did not respond within 30s"
  echo "--- container logs ---"
  "$SMOKE_DOCKER" logs "$CONTAINER_NAME" || true
  exit 1
fi
echo "[smoke_test] health OK"

echo "[smoke_test] POSTing /api/solve (from-scratch squad, real CBC solve)"
SOLVE_BODY=$(curl -fsS -X POST "http://localhost:${SMOKE_PORT}/api/solve" \
  -H 'Content-Type: application/json' -d '{}') || {
  echo "FAILED: POST /api/solve did not return a successful response"
  "$SMOKE_DOCKER" logs "$CONTAINER_NAME" || true
  exit 1
}

PLAYER_CODE_COUNT=$(printf '%s' "$SOLVE_BODY" | grep -o '"player_code"' | wc -l | tr -d ' ')

if [ "$PLAYER_CODE_COUNT" -ne 15 ]; then
  echo "FAILED: expected 15 player_code entries in /api/solve response, got $PLAYER_CODE_COUNT"
  echo "--- response body ---"
  printf '%s\n' "$SOLVE_BODY"
  exit 1
fi
echo "[smoke_test] solve OK -- 15 squad slots confirmed via a real CBC solve"

echo "SMOKE TEST PASSED"
