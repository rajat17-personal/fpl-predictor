---
status: issues-found
phase: "04"
depth: standard
files_reviewed: 25
findings:
  critical: 1
  warning: 1
  info: 0
  total: 2
reviewed: 2026-09-04T00:00:00Z
---

# Code Review — Phase 4 (e2e-regression-suite)

## Scope and method

Reviewed the 25 files listed in the workflow's `files` config at standard depth: the
`api/main.py` fixture-mode seam (and its restore path, CR-01 from the prior review),
`tests/test_fixture_mode.py`, the full Playwright E2E harness (`e2e/helpers`,
`e2e/scripts`, `e2e/specs/**`, `e2e/playwright.config.ts`, package/tsconfig files), and
the three frontend files touched by the ghost-row fix (`Pitch.tsx`, `RateDiff.tsx`,
`SquadTab.tsx`) plus their test files. Frozen fixture JSON payloads under
`e2e/fixtures/v1/**` were excluded per the review's config (data captures, not code),
though `MANIFEST.md`'s prose was read.

Verification performed, not just read-through:
- Re-derived `git diff 79f3aa79cd457654ae9356e429075ef9f5c651b5^..HEAD` for every file in
  scope and reviewed the actual diff hunks against the full file bodies, to avoid
  re-litigating pre-existing (out-of-phase) code such as `_resolve()`'s name-matching
  logic in `api/main.py`, which is unchanged by this phase.
- Ran `pytest tests/test_fixture_mode.py` and `pytest tests/ -k "api or fixture"` — both
  green with `frontend/dist/` present.
- Reproduced a failure by temporarily moving `frontend/dist/` aside and re-running
  `tests/test_fixture_mode.py` — confirmed the crash described in CR-01 below (1 failed,
  9 passed), then restored the directory.
- Ran `vitest run` on `RateDiff.test.tsx` + `Pitch.test.tsx` (32/32 passed) and `tsc
  --noEmit` in both `frontend/` and `e2e/` (no type errors).
- Ran a quick-depth grep sweep (secrets, `eval`, `innerHTML`, empty catch, debug
  artifacts) across every file in scope — no hits besides an intentional CLI
  `console.log` in `synthesize-variants.mjs`.

## Prior-review fix verification

**CR-01 (fixture-mode `_gw_pool` teardown leak) — holds.** Traced the capture-once
guard (`if not hasattr(live, "_gw_pool_production")`, `api/main.py:123-124`) and the
three-way restore in the `else` branch (`api/main.py:140-143`) against
`tests/test_fixture_mode.py`'s `fixture_app` fixture and the two dedicated regression
tests (`test_unset_env_restores_the_production_gw_pool`,
`test_unset_env_leaves_a_single_root_mount`). The guard correctly captures the real
`predict.live._gw_pool` reference exactly once (before the fixture branch below it ever
runs) and the env-unset path restores all three bindings (`api.main._gw_pool`,
`predict.live._gw_pool`, `api.main._load_live`) by object identity. Confirmed by test
run: all identity assertions pass.

**Ghost-row fix (Pitch.tsx / RateDiff.tsx, "BENCH" row) — holds.** `Pitch.tsx`'s
`PitchGhost.row` union now includes `"BENCH"`, the Bench `PitchRow` is wired with
`{...rowGhost("BENCH")}`, and `RateDiff.tsx`'s `resolveRateOverlay` keys the ghost's row
off the *sell* target's own row (bench included) rather than the buy's position, exactly
as documented. Verified against both the unit tests (`Pitch.test.tsx`'s
"keeps the ghost-holding Bench row … exactly centered" and RateDiff's "keys the ghost
row off the sell target's own row: BENCH for a benched sell") and the new E2E coverage
(`rate-my-team.spec.ts`'s "one pitch carries the rating's XI, the outgoing/ghost cards…"
test, which asserts ghost/out-card adjacency inside the same `role="group"` Bench
container against a real fixture-mode server response). All pass.

## Critical Issues

### CR-01 — `tests/test_fixture_mode.py`'s SPA-fallback test crashes with an unhandled 500 on a clean checkout (no pre-built `frontend/dist`)

**File:** `tests/test_fixture_mode.py:144-149` (test), root cause in `api/main.py:546-550`
**Issue:** `test_client_side_route_falls_back_to_the_spa_shell_not_json` asserts that
`GET /team` returns `text/html` (the SPA's `index.html`/`404.html` fallback). This
depends on `api/main.py`'s fixture-mode `"/"` mount:
```python
app.mount("/", StaticFiles(directory=config.ROOT / "frontend" / "dist",
                           html=True, check_dir=False), name="site")
```
`check_dir=False` only skips Starlette's directory-existence check at **mount time**
(so the three parallel uvicorn servers in `playwright.config.ts` can boot before the
frontend build finishes). Starlette's `StaticFiles.check_config()` still runs lazily on
the **first request** routed through that mount, and if the directory genuinely does
not exist at that point, it raises `RuntimeError("StaticFiles directory '…dist' does
not exist.")`, which FastAPI surfaces as an unhandled 500 with a JSON body — not the
`text/html` SPA shell the test expects.

`frontend/dist/` is gitignored (`.gitignore:9`) and nothing in the Python test path
builds it: `tests/conftest.py` has no such fixture, and the only place that runs
`npm --prefix frontend run build` is `e2e/playwright.config.ts`'s `webServer.command`
(the Playwright harness, a separate npm-driven process). A plain `pytest
tests/test_fixture_mode.py` — the natural way to run the Python API test suite, and
almost certainly how a CI job for `tests/` would invoke it — has no dependency that
builds the frontend first.

Reproduced directly:
```
$ mv frontend/dist frontend/dist.bak
$ pytest tests/test_fixture_mode.py -q
...
FAILED tests/test_fixture_mode.py::test_client_side_route_falls_back_to_the_spa_shell_not_json
1 failed, 9 passed in 0.98s
$ mv frontend/dist.bak frontend/dist
$ pytest tests/test_fixture_mode.py -q
10 passed in 1.47s
```
The test only passes today because a Playwright run (or a manual `npm run build`)
happened to leave `frontend/dist/` on disk from a previous session — an environmental
side effect, not something the test itself guarantees. On a fresh clone, in a Docker
build stage, or on a CI runner whose Python test job doesn't also run the frontend
build first, this test fails every time, for a reason that has nothing to do with the
fixture-mode behavior it's meant to verify.

**Why it matters:** This is exactly the class of defect the phase exists to close out —
a regression test that isn't actually reproducible outside one developer's machine
state. It will intermittently (in practice: reliably, on CI) turn green/red based on
unrelated build ordering, eroding trust in the whole `tests/test_fixture_mode.py` file
and blocking CI adoption of `pytest` as a gate.

**Suggested fix:** Make the test's dependency on a built frontend explicit instead of
implicit. Either:
1. Skip loudly when the precondition isn't met:
```python
import pytest

FRONTEND_DIST = config.ROOT / "frontend" / "dist"

@pytest.mark.skipif(
    not FRONTEND_DIST.is_dir(),
    reason="frontend/dist not built — run `npm --prefix frontend run build` first",
)
def test_client_side_route_falls_back_to_the_spa_shell_not_json(fixture_app):
    ...
```
2. Or make it self-sufficient — a session-scoped fixture that runs
   `npm --prefix frontend run build` once if `dist/` is missing (mirrors what
   `e2e/playwright.config.ts` already does for the same reason).
3. Or, more defensively, make the production code degrade instead of crash: catch the
   missing-directory case in `api/main.py`'s fixture-mode mount setup and serve a
   deliberate 404/503 rather than letting Starlette's `RuntimeError` propagate as an
   unhandled 500 — this protects the real fixture-mode server too, not just the test.

Any of the three closes the gap; (1) is the smallest change and makes the failure mode
self-documenting instead of a mysterious CI flake.

## Warnings

### WR-01 — New fixture-mode file reads never use `with`, across `api/main.py` and `e2e/scripts/capture_fixtures.py`

**File:** `api/main.py:73` (`_fixture_json`), `api/main.py:111` (`_gw_pool_fixture`),
`api/main.py:258` (`_fetch_entry_history`), `api/main.py:291` (`_fetch_entry_picks`),
`api/main.py:309` (`_fetch_entry_summary`); `e2e/scripts/capture_fixtures.py:105`
(`_write_json`), `e2e/scripts/capture_fixtures.py:113-114` (`_capture`)
**Issue:** Every new fixture-mode read/write path opens files with a bare `open(...)`
passed straight into `json.load`/`json.dump`, e.g.:
```python
def _fixture_json(*parts: str):
    return json.load(open(_FIXTURE_API.joinpath(*parts)))
```
rather than a `with open(...) as f:` block. This is called out explicitly in this
project's own documented conventions (`## Error Handling` / Python style: "missing
`with` for file operations" is a named anti-pattern to catch). In CPython the handle is
closed promptly by refcounting once the expression's value is consumed, so this is not
an active resource leak today, but it's the same defect class the project's own
`data/ingest.py`, `models/train.py`, etc. otherwise avoid throughout the codebase, is
not safe on non-refcounted Python implementations, and — more concretely — leaves the
file handle open for the duration of any exception raised while parsing (e.g. a
truncated/corrupt fixture JSON never closes the handle before propagating).

**Why it matters:** Consistency with the codebase's own stated convention, and
resilience under partially-written or corrupt fixture files (a real risk here, since
these are hand-edited/regenerated JSON captures under active development in this same
phase).

**Suggested fix:**
```python
def _fixture_json(*parts: str):
    with open(_FIXTURE_API.joinpath(*parts)) as f:
        return json.load(f)
```
and equivalently for the other six call sites listed above.

---

_Reviewed: 2026-09-04T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
