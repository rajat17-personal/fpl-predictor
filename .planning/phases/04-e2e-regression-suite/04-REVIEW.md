---
phase: 04-e2e-regression-suite
reviewed: 2026-09-03T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - .gitignore
  - api/main.py
  - e2e/helpers/page.ts
  - e2e/package.json
  - e2e/playwright.config.ts
  - e2e/scripts/capture_fixtures.py
  - e2e/scripts/synthesize-variants.mjs
  - e2e/specs/fixtures-prices.spec.ts
  - e2e/specs/rate-my-team.spec.ts
  - e2e/specs/shell-geometry.spec.ts
  - e2e/specs/smoke.spec.ts
  - e2e/specs/team-plan.spec.ts
  - e2e/specs/team-solver.spec.ts
  - e2e/specs/variants/blank-fixtures.spec.ts
  - e2e/specs/variants/blank-xp-table.spec.ts
  - e2e/specs/variants/dgw-chips.spec.ts
  - e2e/specs/variants/dgw-fixtures.spec.ts
  - e2e/specs/xp-table.spec.ts
  - e2e/tsconfig.json
  - frontend/package.json
  - frontend/src/components/team/SquadTab.tsx
  - tests/test_fixture_mode.py
findings:
  critical: 1
  warning: 4
  info: 1
  total: 6
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-09-03
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Reviewed the Phase 4 fixture-mode seam in `api/main.py`, the `capture_fixtures.py` /
`synthesize-variants.mjs` fixture pipeline, the Playwright harness (`e2e/`), and the
`SquadTab.tsx` `fetchTeam` fix. Most of the seam is careful and well-documented — the
production `else` branches (static-site mount, `require_key`, request/response shapes)
are untouched, and `tests/test_fixture_mode.py` correctly proves no `requests.get`/
`joblib.load` call happens while `FPL_FIXTURE_DIR` is set.

However, one **verified, reproducible** bug undermines the phase's own core promise
("Production ... is untouched by any of this"): `api/main.py`'s fixture-mode branch
monkeypatches `predict.live`'s module-level `_gw_pool` global, but never un-patches it
when fixture mode is subsequently disabled in the same process. I reproduced a crash of
`/api/solve` (and, by the same code path, `/api/team`, `/api/rate`, `/api/plan`) in
"production" configuration after a single prior fixture-mode `importlib.reload` cycle —
exactly the cycle `tests/test_fixture_mode.py`'s own fixture performs at teardown. See
CR-01 for the full repro.

Also flagged: several `open()` calls without a context manager across the fixture
capture/serving code (resource-leak/robustness), a documented "scrub-names" privacy
guarantee that has no automated regression check, a permanently-committed real FPL
entry ID + team name despite the "scrub" branding, and a `pytest` test that silently
depends on `frontend/dist/` already being built.

## Critical Issues

### CR-01: `predict.live._gw_pool` fixture-mode monkeypatch is never restored — production `/api/solve`, `/api/team`, `/api/rate`, `/api/plan` crash after any prior fixture-mode reload in-process

**File:** `api/main.py:114-121`

**Issue:**

```python
if _FIXTURE_ROOT:
    _load_live = _load_live_fixture
    # build_pool/build_horizon_pool resolve `_gw_pool` from predict.live's own
    # module globals at call time, so rebinding only api.main's imported name
    # would not affect them — both bindings must be rebound (RESEARCH.md
    # Pattern 1, Pitfall 1).
    _gw_pool = _gw_pool_fixture
    live._gw_pool = _gw_pool_fixture
```

This correctly rebinds *both* `api.main._gw_pool` and `predict.live._gw_pool` when
`FPL_FIXTURE_DIR` is set — but there is no `else` branch that restores
`live._gw_pool` when the env var is *not* set. `api.main._gw_pool` "self-heals" on a
later reload only because it is re-imported fresh from `predict.live` each time
(`from predict.live import (_gw_pool, ...)`) — but that re-import now pulls the
**already-polluted** value, because `predict.live` itself is a long-lived module that
is never reloaded. The pollution is therefore permanent for the remainder of the
process once fixture mode has been entered even once.

This is not a hypothetical: `tests/test_fixture_mode.py`'s own `fixture_app` fixture
performs exactly this cycle at teardown (`monkeypatch.delenv(...); importlib.reload(reloaded)`)
and its docstring explicitly (and incorrectly) claims this "reload[s] back to the
unset-env module ... so the rest of the suite ... never sees the fixture-mode module."
I reproduced the crash directly:

```
$ python -c "
import os, importlib
import api.main as m
os.environ['FPL_FIXTURE_DIR'] = str(m.config.ROOT / 'e2e/fixtures/v1/normal')
m = importlib.reload(m)
del os.environ['FPL_FIXTURE_DIR']
m = importlib.reload(m)          # <-- 'restores' production per the code's own comment
from fastapi.testclient import TestClient
c = TestClient(m.app)
r = c.post('/api/solve', json={})
"
...
File ".../predict/live.py", line 166, in build_pool
    pool = _gw_pool(boot, fixtures, gw, artifact)
File ".../api/main.py", line 107, in _gw_pool_fixture
    path = _FIXTURE_API / "pools" / f"gw{gw}.json"
TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'
```

`_gw_pool_fixture`'s closure still reads `_FIXTURE_API` from api.main's module globals
(the same dict `importlib.reload` mutates in place), and after the second reload that
global is `None` — so the leaked binding doesn't even degrade to "still serving stale
fixtures," it hard-crashes any endpoint that reaches `build_pool`/`build_horizon_pool`
(`/api/solve`, `/api/team`, `/api/rate`, `/api/plan`) with a 500.

The existing test suite does not currently catch this only because
`tests/test_product.py::test_api_solve_and_resolve` (the one other test file that hits
`/api/solve`, and which runs after `test_fixture_mode.py` alphabetically) monkeypatches
`api.main._pool` directly and never goes through the real `build_pool`/`_gw_pool` path.
Any future test that exercises the real solve path in "production" mode — or any other
process that toggles `FPL_FIXTURE_DIR` via `importlib.reload` (dev tooling, notebooks,
a future hot-reload harness) — will hit this.

**Fix:** Capture the true production function exactly once, before it can ever be
polluted, and always restore from that captured reference rather than from
`predict.live`'s current (possibly already-polluted) attribute:

```python
if not hasattr(live, "_gw_pool_production"):
    live._gw_pool_production = live._gw_pool  # captured once, never re-captured

if _FIXTURE_ROOT:
    _load_live = _load_live_fixture
    _gw_pool = _gw_pool_fixture
    live._gw_pool = _gw_pool_fixture
else:
    _gw_pool = live._gw_pool_production
    live._gw_pool = live._gw_pool_production
```

Also correct `tests/test_fixture_mode.py`'s `fixture_app` docstring/teardown claim, and
add an assertion (e.g. a smoke call to `/api/solve` with a monkeypatched `_pool`-free
path, or a direct `predict.live._gw_pool is <original>` check) that would have caught
this regression.

## Warnings

### WR-01: Fixture-mode file I/O never closes file handles (`open()` without `with`)

**File:** `api/main.py:73, 111, 236, 269, 287`; `e2e/scripts/capture_fixtures.py:103-105, 113-114, 123, 142-157, 228-231, 243, 252, 258`; `tests/test_fixture_mode.py:16`

**Issue:** Every fixture-mode read/write in this phase uses a bare `open(...)` passed
directly into `json.load`/`json.dump` (e.g. `api/main.py:73`
`json.load(open(_FIXTURE_API.joinpath(*parts)))`, `capture_fixtures.py:105`
`json.dump(payload, open(path, "w"), indent=1)`). None of these close the resulting
file object — on CPython, the handle is only released whenever the GC happens to
collect it, not deterministically at the end of the operation. This is called out
explicitly in this project's own Python conventions/review checklist ("missing `with`
for file operations") and is exactly the kind of pattern that turns into a real bug
under PyPy, in a long-running process that opens many fixture files per request (every
`/api/solve`/`/api/team`/`/api/rate`/`/api/plan` call in fixture mode opens 1-4 files),
or when a test suite runs thousands of iterations.

**Fix:**

```python
def _fixture_json(*parts: str):
    with open(_FIXTURE_API.joinpath(*parts)) as f:
        return json.load(f)
```

Apply the same `with open(...) as f:` pattern to every other bare-`open()` call site
listed above.

### WR-02: The "scrub-names" privacy guarantee has no automated check

**File:** `e2e/scripts/capture_fixtures.py:83-91` (`_trim_summary`), `197-280` (`_verify`)

**Issue:** `_trim_summary`'s `scrub_names` branch blanks `player_first_name`/
`player_last_name` and is documented as a "Task 1 checkpoint decision" that "the two
free-text manager name fields never enter git history." This guarantee is enforced
solely by the fact that `_capture()` happens to hardcode `scrub_names=True` at its one
call site (`capture_fixtures.py:152`) — there is no corresponding assertion in
`_verify()` that `entries/{ENTRY}/summary.json`'s `player_first_name`/
`player_last_name` are actually empty. `_verify()` does check for the literal string
`fantasy.premierleague.com` leaking into any committed file, but performs no equivalent
check for the specific PII field this whole code path exists to protect. A future edit
to `_trim_summary` (e.g. dropping the `scrub_names` parameter, or a future v2 capture
script copy-pasted without it) would silently commit a real name to git history with
`--verify` reporting success.

**Fix:** Add to `_verify()`:

```python
summary = json.load(open(API_DIR / "entries" / str(ENTRY) / "summary.json"))
if summary.get("player_first_name") or summary.get("player_last_name"):
    errors.append("entries/.../summary.json: player_first_name/player_last_name "
                  "must be scrubbed to empty strings")
```

### WR-03: A real FPL account's entry ID and team name are permanently committed to git

**File:** `e2e/scripts/capture_fixtures.py:34` (`ENTRY = 6980093`), `83-91` (`_trim_summary`)

**Issue:** `_trim_summary` deliberately keeps `name` (the FPL team name, "rajat" per
the specs' own comments) and every numeric season figure verbatim, scrubbing only the
two separate first/last-name fields. That is a documented, reviewed decision — but the
net effect is that a real, working FPL entry ID (`6980093`) tied to a real team name is
now permanently committed to this repository's git history, in a project whose own
CLAUDE.md frames this milestone as "production hardening ... ahead of monetization."
Team name + a live entry ID is enough to look the account up on the public FPL site.
This is flagged here for a final sign-off pass before the repository is made public or
handed to other contributors — not asserted as a bug in the scrub logic itself (the
scrub does exactly what its own comment claims).

**Fix:** If this repository will ever go public, either use a disposable/test FPL
entry for the frozen capture instead of the maintainer's real account, or additionally
scrub/replace the `name` field with a synthetic value (and re-derive the handful of
hardcoded `"rajat"` literals in `smoke.spec.ts`, `rate-my-team.spec.ts`, etc.
accordingly).

### WR-04: `tests/test_fixture_mode.py`'s SPA-fallback test silently depends on an out-of-band `frontend/dist/` build

**File:** `tests/test_fixture_mode.py:129-135`

**Issue:** `test_client_side_route_falls_back_to_the_spa_shell_not_json` mounts
`config.ROOT / "frontend" / "dist"` (via the reloaded `api.main` module) and asserts
`GET /team` returns `text/html`. Nothing in this pytest file (or in `tests/conftest.py`)
builds the frontend, checks that `frontend/dist/` exists, or skips the test when it is
absent. `frontend/dist/` is gitignored and only produced by `npm --prefix frontend run
build` — a step the Playwright harness chains explicitly (`playwright.config.ts`'s
`webServer.command`) but this Python test file does not. On a fresh clone, or any CI
runner that runs `pytest` before the frontend build step exists (Phase 5), this test
will fail with a mount/500 error whose message won't obviously point at "you forgot to
build the frontend."

**Fix:** Either `pytest.skip(...)` when `frontend/dist/index.html` doesn't exist, or
have this test (or a session-scoped fixture) invoke the frontend build itself before
asserting against it, so the failure mode is legible.

## Info

### IN-01: `fetchTeam`'s error-detail extraction duplicates `postSolve`'s (and other files') identical logic

**File:** `frontend/src/components/team/SquadTab.tsx:92-105` vs `112-129`

**Issue:** The new `fetchTeam` helper and the existing `postSolve` helper in the same
file contain byte-for-byte identical `try { detail = (await res.json()).detail } catch
{ }` / `throw new Error(detail || String(res.status))` blocks. Per this file's own
comments, `RateTab.tsx`'s `fetchRate` and `PlanTransfers.tsx`'s `postSolve`/`postPlan`
repeat the same pattern again — four-plus copies of one 10-line block.

**Fix:** Extract one shared helper into `lib/api.ts`, e.g.:

```ts
export async function fetchWithDetail<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: string | undefined;
    try {
      detail = ((await res.json()) as { detail?: string })?.detail;
    } catch {
      // not JSON — fall back to status code
    }
    throw new Error(detail || String(res.status));
  }
  return (await res.json()) as T;
}
```

and have `fetchTeam`, `postSolve`, `fetchRate`, `postPlan` call
`fetchWithDetail(await fetch(...))`.

---

_Reviewed: 2026-09-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
