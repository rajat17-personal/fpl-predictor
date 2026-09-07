# Phase 7: Parity Validation & Cutover - Pattern Map

**Mapped:** 2026-09-07
**Files analyzed:** 8 (new/modified)
**Analogs found:** 8 / 8

This phase is mostly process + evidence artifacts (calendar-gated), but the one real
code change (the production serving seam) and its supporting scripts/tests/CI all have
strong, recent analogs already in the codebase — mostly Phase 4/5/6 work on the same
`api/main.py` mount-split and script conventions.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/main.py` (new `FPL_FRONTEND=react` branch, bottom of file) | config/route (StaticFiles mount seam) | request-response | `api/main.py`'s existing `_FIXTURE_ROOT` mount branch (same file, lines 69-80 + 766-776) | exact |
| `tests/test_fixture_mode.py` extension (or a sibling `tests/test_react_seam.py`) | test | request-response | `tests/test_fixture_mode.py` (whole file, 187 lines) | exact |
| `scripts/start_dual.sh` (or similar — start/stop both uvicorns) | utility (process orchestration) | batch | `scripts/verify_hardening.sh` (boot-a-real-uvicorn shape) + `scripts/smoke_test.sh` (docker boot/poll/cleanup shape) | role-match |
| `scripts/smoke_test.sh` (extended: react-mode assertion, D-04) | test/utility | request-response | itself, `scripts/smoke_test.sh` (82 lines, existing fixture-mode boot) | exact (in-place extension) |
| `.github/workflows/ci.yml` docker job (new react-mode smoke step) | config (CI) | batch | itself — existing docker job steps (lines ~168-190) that already run `scripts/smoke_test.sh local/fpl:ci` | exact |
| `e2e/parity/diff.spec.ts` (or `scripts/parity_diff.ts` — D-05 diff script) | test/utility (cross-site comparison) | transform | `e2e/specs/xp-table.spec.ts` (cell-value/sort-order extraction against a fixed fixture) + `e2e/helpers/page.ts` (`gotoReady`, frozen-clock navigation helper) | role-match |
| `e2e/playwright.config.ts` (new project/webServer entries for parity mode, if the diff script reuses the Playwright runner) | config | request-response | itself — existing multi-project `webServer` array (normal/blank/DGW variants, lines ~60-120) | exact |
| `frontend/scripts/check-tokens.mjs` (D-11: remove vanilla-lockstep assertions at the flip) | utility (build-time gate) | transform | itself — the "vanilla lockstep" section this phase deletes | exact |
| `PARITY-REPORT.md` (D-06 evidence artifact) | doc/config (not source code) | batch | `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` (ledger table + append-discipline structure) | exact |

## Pattern Assignments

### `api/main.py` — new production react-mode seam (D-01)

**Analog:** `api/main.py` itself — the existing `_FIXTURE_ROOT` env-seam pattern.

**Env-seam declaration pattern** (`api/main.py:60-80`):
```python
# --- E2E fixture-mode seam (Phase 4, E2E-01) --------------------------------
# FPL_FIXTURE_DIR points at a captured fixture set (see e2e/fixtures/v1/MANIFEST.md).
# When set, every outbound-network / model-artifact call site below branches to
# read committed JSON from disk instead...
_FIXTURE_ROOT = (Path(os.environ["FPL_FIXTURE_DIR"]).resolve()
                if os.environ.get("FPL_FIXTURE_DIR") else None)
...
if _FIXTURE_ROOT:
    print(f"[fixture-mode] FPL_FIXTURE_DIR={_FIXTURE_API} ... -- serving frozen fixtures, "
          "no live FPL API calls, no model artifact load. This must never be "
          "set in a production/deploy configuration.")
```
Copy this shape for `FPL_FRONTEND`: read the env var once near the top of the file next
to `_FIXTURE_ROOT`, print a one-line `[react-mode]`/`[frontend-seam]` announcement, and
keep the check as a plain truthy/enum comparison (e.g. `os.environ.get("FPL_FRONTEND") == "react"`).
Do NOT fold this into `_FIXTURE_ROOT` — CONTEXT.md's discretion note requires the two
seams to compose independently and the fixture branch to stay untouched.

**Mount-split pattern** (`api/main.py:759-776`):
```python
# Fixture mode (E2E-01): serve the built React app + the frozen /data set
# instead of vanilla web/. check_dir=False lets this server boot before the
# frontend build has finished...
# /data MUST be registered before the catch-all "/" mount below -- Starlette
# matches mounts in registration order, and the more general "/" mount would
# otherwise swallow JSON requests and answer them with 404.html.
if _FIXTURE_ROOT:
    app.mount("/data", StaticFiles(directory=_FIXTURE_DATA, check_dir=False),
              name="fixture-data")
    app.mount("/", StaticFiles(directory=config.ROOT / "frontend" / "dist",
                               html=True, check_dir=False), name="site")
else:
    # Serve the static site from the same process, so a single
    #   uvicorn api.main:app --port 8000
    # runs everything at http://localhost:8000/ ...
    app.mount("/", StaticFiles(directory=config.ROOT / "web", html=True), name="site")
```
The new production react branch is a **third sibling branch** here, gated by
`_FIXTURE_ROOT` first (unchanged), then the new `_REACT_MODE` flag, else vanilla — e.g.:
```python
if _FIXTURE_ROOT:
    ...  # untouched
elif _REACT_MODE:
    app.mount("/data", StaticFiles(directory=config.ROOT / "web" / "data", check_dir=False),
              name="data")
    app.mount("/", StaticFiles(directory=config.ROOT / "frontend" / "dist",
                               html=True, check_dir=False), name="site")
else:
    app.mount("/", StaticFiles(directory=config.ROOT / "web", html=True), name="site")
```
Preserve registration order (`/data` before `/`) exactly as the fixture branch does —
same Starlette mount-matching hazard applies. Reuse `check_dir=False` since `frontend/dist`
may not exist yet at import time in dev.

**D-09 cutover flip** later just swaps the `else` branch's directory from `web` to
`frontend/dist` (or swaps which branch is the unconditional default) — same file, same
lines, no new pattern needed.

---

### `tests/test_fixture_mode.py` extension — seam test (D-01 test coverage)

**Analog:** `tests/test_fixture_mode.py` (whole file).

**Mount-count assertion pattern** (`tests/test_fixture_mode.py:153-165`):
```python
def test_unset_env_leaves_a_single_root_mount(monkeypatch):
    """The production default: with FPL_FIXTURE_DIR absent, api.main mounts
    exactly one path, "/" (vanilla web/), unchanged from before this seam."""
    from starlette.routing import Mount
    import api.main as m

    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    reloaded = importlib.reload(m)
    mounts = [route for route in reloaded.app.routes if isinstance(route, Mount)]
    assert len(mounts) == 1
    assert mounts[0].name == "site"
    importlib.reload(reloaded)
```
Copy this shape for the new seam: `monkeypatch.setenv("FPL_FRONTEND", "react")`, reload,
assert two mounts (`data`, `site`) in that order and that `site`'s directory resolves to
`frontend/dist`. Also add the inverse — with `FPL_FRONTEND` unset (or `=vanilla`), assert
the existing single-mount assertion still passes unchanged (guards that the fixture test
above, `test_unset_env_leaves_a_single_root_mount`, keeps passing with the new branch added).

**Reload/monkeypatch fixture pattern** (`tests/test_fixture_mode.py:35-55`):
```python
@pytest.fixture
def fixture_app(monkeypatch):
    import api.main as m
    monkeypatch.setenv("FPL_FIXTURE_DIR", str(FIXTURE_DIR))
    reloaded = importlib.reload(m)
    ...
    yield reloaded
    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    importlib.reload(reloaded)
```
Follow the same `importlib.reload` + teardown-reload discipline for any react-mode
fixture — module-level env branches in `api/main.py` only take effect on import/reload,
never on a live already-imported module.

---

### `scripts/start_dual.sh` (new) — start/stop both uvicorns (D-03)

**Analog A — port/cleanup conventions:** `scripts/smoke_test.sh` (82 lines).
```bash
SMOKE_PORT="${SMOKE_PORT:-8200}"
CONTAINER_NAME="fpl-smoke-$$"
cleanup() {
  "$SMOKE_DOCKER" rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT
```
**Analog B — real-uvicorn-boot + polling + interpreter seam:** `scripts/verify_hardening.sh` (lines 1-60):
```bash
# Usage: HARDENING_PYTHON=/path/to/python3.14 bash scripts/verify_hardening.sh
#   HARDENING_PYTHON  interpreter used to boot uvicorn and run inline python
#                      checks (default: python3 -- same seam convention as
#                      PREFLIGHT_PYTHON in scripts/preflight.sh and
#                      E2E_PYTHON in e2e/playwright.config.ts)
#   HARDENING_PORT    port the verification uvicorn process listens on
#                      (default: 8123 -- distinct from 8000/8100-8102/8200, ...)
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${HARDENING_PYTHON:-python3}"
HARDENING_PORT="${HARDENING_PORT:-8123}"
```
For the start/stop script: follow the same `set -euo pipefail`, `cd` to repo root,
env-var-with-default port/interpreter seam (e.g. `FPL_PY`, `REACT_PORT=8001`,
`VANILLA_PORT=8000` — D-01 already fixes these two exact ports), background both
`uvicorn` invocations (`FPL_FRONTEND=react ... &` / plain `...  &`), record PIDs to a
file for a stop command to `kill`, and `trap` cleanup on the start script's own exit only
if it's meant to be foreground/blocking — otherwise a separate `stop_dual.sh` reads the
PID file. Port choice must avoid 8000/8100-8102/8123/8200 (all already claimed per the
comments above) — 8001 is D-01's explicit choice and is free.

---

### `scripts/smoke_test.sh` extension — react-mode CI assertion (D-04)

**Analog:** itself (existing file, full 82 lines already read above).

Existing fixture-mode boot/poll/assert shape:
```bash
"$SMOKE_DOCKER" run -d --name "$CONTAINER_NAME" \
  -p "${SMOKE_PORT}:8000" \
  -e FPL_FIXTURE_DIR=/fixtures/v1/normal \
  -v "$(pwd)/e2e/fixtures:/fixtures:ro" \
  "$IMAGE_TAG" >/dev/null
...
for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:${SMOKE_PORT}/api/health" >/dev/null 2>&1; then
    HEALTH_OK=1
    break
  fi
  sleep 1
done
```
D-04 asks for one added assertion, not a new script: start a second container (or reuse
the smoke container with `-e FPL_FRONTEND=react` instead of the fixture env, same image)
and `curl -fsS http://localhost:${SMOKE_PORT}/ | grep -q '<div id="root"'` (or check
for a known `frontend/dist/index.html` marker string) to prove `index.html` is served
from `frontend/dist`, not `web/`. Reuse the same `cleanup`/`trap` and `FAILED:`-prefixed
error-message convention for consistency with the existing failure messages.

---

### `.github/workflows/ci.yml` — react-mode smoke step (D-04)

**Analog:** itself — existing docker job (lines ~168-190):
```yaml
- uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e   # v4.3.0
- ... download frontend-dist artifact to frontend/dist
- uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a   # v7.3.0
- run: bash scripts/smoke_test.sh local/fpl:ci
```
Add the react-mode assertion as an additional `run: bash scripts/smoke_test.sh local/fpl:ci`
invocation with an env var flag (e.g. `SMOKE_REACT_MODE=1`) or a second explicit step
calling a `--react` flag on the same script — follow the existing pattern of pinning
third-party actions by commit SHA with a version comment, already used throughout this job.

---

### `e2e/parity/*` — the diff script (D-05)

**Analog A — page-visit + cell-extraction shape:** `e2e/specs/xp-table.spec.ts` (352 lines).
Key pattern: navigate with the frozen-clock helper, locate tables by ARIA role/name, read
`allTextContents()` per column for comparison:
```typescript
const table = page.getByRole("table", { name: "xP table" });
const names = () => table.locator("tbody tr td:nth-child(2)").allTextContents();
```
The diff script should reuse this exact `getByRole("table", {name})` + `allTextContents()`
extraction idiom against BOTH origins (`:8000` vanilla and `:8001` react), rather than
inventing a new selector strategy.

**Analog B — navigation/frozen-clock helper:** `e2e/helpers/page.ts` (81 lines):
```typescript
export async function gotoReady(page: Page, path: string, opts: GotoReadyOptions = {}): Promise<void> {
  if (opts.viewport) { await page.setViewportSize(opts.viewport); }
  await page.clock.setFixedTime(FROZEN_NOW);
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
}
```
For live-data parity passes (not fixture-frozen), the diff script should NOT pin
`FROZEN_NOW` — the whole point is comparing two processes against the *same live*
`web/data/*.json` at the same instant. Reuse `gotoReady`'s font-wait pattern only, drop
the clock pin, and instead pin a comparison timestamp by fetching both origins within
the same script invocation (sequential `page.goto` calls close in wall-clock time).

**Analog C — config/webServer multi-project shape:** `e2e/playwright.config.ts` (lines 39-120):
```typescript
const PYTHON = process.env.E2E_PYTHON ?? "python";
// Deliberately NOT 8000: a developer's own `uvicorn api.main:app --port 8000` ...
const webServer = [
  { command: `${PYTHON} -m uvicorn api.main:app --port ${NORMAL_PORT}`, ... env: { FPL_FIXTURE_DIR: FIXTURE_NORMAL_DIR } },
];
```
If the parity diff script is wired into Playwright's config (rather than a standalone
node script), it should NOT declare its own `webServer` entries — D-03's start/stop
script already boots :8000/:8001 against live data; a parity Playwright project should
set `baseURL` per-project and skip the `webServer` array entirely (or point it at a
no-op check), since booting a THIRD/FOURTH uvicorn from Playwright would fight the
long-running dual-server session the validation week depends on.

**Ledger-filtering logic (D-05):** parse `PARITY-DEVIATIONS.md`'s table
(`.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md:16-25`) — a simple
markdown pipe-table — to build a known-deltas allowlist the diff script filters against
before reporting a mismatch as new. No existing script parses this table yet; a small
regex/split on `|` per row is sufficient (mirrors `frontend/scripts/check-tokens.mjs`'s
own dependency-free `node:fs`-only style, no npm markdown parser needed).

---

### `frontend/scripts/check-tokens.mjs` — remove vanilla-lockstep assertions (D-11)

**Analog:** itself — the section this phase deletes at the flip:
```javascript
// ... Reading the file with node:fs from inside src is closed off too ...
const vanillaCssUrl = new URL("../../web/assets/style.css", import.meta.url);
```
At cutover, remove the `vanillaCssUrl` read and the "vanilla lockstep" comparison
assertions (the four dark-hex-identity checks referenced in
`PARITY-DEVIATIONS.md:55-56`), leaving the OKLCH chroma-budget checks against
`frontend/src/index.css` alone intact. This is a deletion, not a new pattern — no new
code style needed, just remove the vanilla-comparison half of the existing checks and
update the file's own module docstring (lines 1-16) to drop the "stays in lockstep with
the React palette" clause.

---

### `PARITY-REPORT.md` (D-06 evidence artifact)

**Analog:** `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` (71 lines) —
table structure + append-discipline section:
```markdown
| # | Deviation | Reason | Introduced by |
|---|-----------|--------|----------------|
| 1 | ... | ... | ... |

## Appending an entry

While executing any plan in this phase, if you find yourself about to change vanilla
behaviour rather than port it ... append a new numbered row here in the same commit as
the change.
```
`PARITY-REPORT.md` should mirror this table-plus-append-discipline shape but keyed by
cycle stage × page rather than by deviation number — e.g. one table per D-07 stage
(pre-deadline / mid-GW / post-finish) with columns `Page | Verdict | Delta (ledger # /
fixing commit / new ledger row) | Cron-green citation (D-16)`. The doc's closing section
mirrors this ledger's "Appending an entry" discipline: instructions for what a future
delta-fix commit must also touch (this report + `PARITY-DEVIATIONS.md` in the same commit).

## Shared Patterns

### Env-var seam convention (applies to `api/main.py`, `smoke_test.sh`, `verify_hardening.sh`, `playwright.config.ts`)
**Source:** `api/main.py:69-80`, `scripts/verify_hardening.sh:18-31`, `e2e/playwright.config.ts:33-42`
Every port/interpreter/mode knob in this codebase is `ENV_VAR:-default` with a comment
explaining *why* that default port is safe (never collides with another script's claimed
port). New scripts/tests in this phase must declare their env vars the same way and
extend the "claimed ports" comment trail (8000 vanilla, 8001 react per D-01, 8100-8102
E2E variants, 8123 hardening, 8200 smoke) rather than picking an arbitrary free port.

### Mount registration order (`/data` before `/`)
**Source:** `api/main.py:759-765` comment block.
Any new StaticFiles mount for `/data` must be registered before the catch-all `/`
mount in the same branch — Starlette matches mounts in registration order.

### `set -euo pipefail` + `cd "$(dirname "$0")/.."` + `trap cleanup EXIT`
**Source:** `scripts/smoke_test.sh:15-37`, `scripts/verify_hardening.sh:27-28`
Apply to any new shell script in this phase (start/stop script, extended smoke test).

### Reload-to-apply-env-branch discipline
**Source:** `tests/test_fixture_mode.py:35-55` (fixture) and `:168-187` (restore proof)
Any pytest covering the new `FPL_FRONTEND` seam must `importlib.reload(api.main)` after
`monkeypatch.setenv`/`delenv` — module-level `os.environ.get(...)` branches only take
effect at import time.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Manual same-session checklist (D-08, entry 6980093 solve/rate/plan comparison) | doc/process | request-response | No prior manual-comparison checklist exists in the repo (Phase 4's E2E suite is fully scripted); this is a plain markdown checklist authored fresh, not code — no code pattern applies. |
| Cron-green citation logic (D-16) | doc/process | event-driven | Not a new script — `data/cron.log` + `ops.notify` (Phase 6) already exist and are simply cited by hand in `PARITY-REPORT.md`; no new integration code. |

## Metadata

**Analog search scope:** `api/main.py`, `tests/test_fixture_mode.py`, `scripts/` (smoke_test.sh, verify_hardening.sh, daily.sh, weekly.sh), `.github/workflows/ci.yml`, `e2e/` (playwright.config.ts, specs/, helpers/), `frontend/scripts/check-tokens.mjs`, `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md`
**Files scanned:** ~15 read/grepped directly, plus directory listings of `e2e/specs/`
**Pattern extraction date:** 2026-09-07
