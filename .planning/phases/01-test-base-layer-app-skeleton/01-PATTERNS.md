# Phase 1: Test Base Layer & App Skeleton - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** 9 (3 backend new/modified, 6+ frontend greenfield scaffold files)
**Analogs found:** 3 / 9 (backend has strong analogs; frontend is greenfield — no in-repo analog exists, RESEARCH.md's verified Code Examples serve as the pattern source instead)

**IMPORTANT — repo tracking state:** This repository has no initial source commit. `git ls-files` shows only `.planning/**` tracked; `api/main.py`, `config.py`, `pytest.ini`, `tests/test_product.py`, `web/**` etc. are all untracked (`git status` shows them `??`). This is **not** a gitignored plugin-mirror situation (no `.gitignore` exists at all) — these files are the actual, canonical source on disk, simply not yet `git add`ed. There is no alternate tracked origin to substitute them with. Analog paths below are real, on-disk, working-tree paths; flag to the planner that Phase 1 (or an earlier housekeeping step) should `git add` these before/alongside this phase's changes so future phases don't repeat this discovery.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/main.py` (modify: add `_initial_state()`) | service/config (module globals factory) | request-response | `api/main.py:51-54` (itself — refactor of existing inline dict literal) | exact (self-refactor) |
| `tests/conftest.py` (new) | test (pytest fixture) | request-response | `tests/test_product.py` (fixture functions `fake_boot`/`fake_pool`, lines 17-50) | role-match (no conftest.py precedent exists; nearest analog is the fixture-style helpers already in test_product.py) |
| `tests/test_api.py` (new) | test (API integration) | request-response | `tests/test_product.py::test_api_solve_and_resolve` (lines 156-183) and `::test_free_transfer_accrual` (lines 186-199) | exact |
| `frontend/vite.config.ts` (new) | config | request-response (proxy) | none in-repo (greenfield); no analog — closest conceptual precedent is `web/assets/config.js` (site's own `API_BASE` detection concept) but different mechanism entirely | no analog |
| `frontend/src/main.tsx` (new) | provider/entry | request-response | none in-repo | no analog |
| `frontend/src/router.tsx` (new) | route | request-response | none in-repo | no analog |
| `frontend/src/lib/api.ts` (new) | utility (fetch wrapper) | request-response | `web/assets/app.js:9-28` (`detectApiBase()`, `loadJSON()`) — same *problem* (fetch `/data/*.json` and `/api/*`), different stack (vanilla JS vs TS/fetch-wrapper for React Query) | role-match (cross-stack) |
| `frontend/src/components/*.tsx` (Spinner, ErrorState, PlaceholderPage, NotFoundPage, PageShell) | component | request-response | none in-repo (no component-based frontend exists yet) | no analog |
| `frontend/src/routes/*.tsx` (8 placeholder route files) | component/route | request-response | none in-repo; conceptually mirrors `web/*.html` (8 static pages: index, team, fixtures, prices, league, scoreboard, differentials, methodology) for route-to-page mapping only, not code pattern | no analog (structural mapping only) |
| `.gitignore` (new, root) | config | file-I/O | none (doesn't exist yet) | no analog |

## Pattern Assignments

### `api/main.py` (config/module-globals factory, request-response) — the phase's only production-code edit

**Analog:** itself, `api/main.py:51-54` (current inline literal)

**Current code to refactor** (lines 51-54):
```python
_lock = threading.Lock()
_state: dict = {"artifact": None, "boot": None, "fixtures": None, "gw": None,
                "pools": {}, "loaded_at": 0.0}
_solve_cache: dict = {}
```

**Target pattern** (from RESEARCH.md Code Examples, verified against this exact file):
```python
_lock = threading.Lock()

def _initial_state() -> dict:
    """Factory for _state's pristine shape — single source of truth so tests
    (and _refresh's cold-start check) never hardcode the dict's keys."""
    return {"artifact": None, "boot": None, "fixtures": None, "gw": None,
            "pools": {}, "loaded_at": 0.0}

_state: dict = _initial_state()
_solve_cache: dict = {}
```

**Constraint:** Pure refactor — same dict shape, same keys, same defaults. Do not touch `_refresh()` (lines 57-68), `_pool()` (lines 77-87), or `_solve_cache` locking behavior (Pitfall 4 in RESEARCH.md: `_solve_cache` reads/writes are intentionally unlocked today — do not "fix" this as a drive-by).

**Docstring convention to preserve** (module-level, lines 1-20): design-notes block explaining entitlements stub and pool caching — do not remove when editing nearby code.

---

### `tests/conftest.py` (new — autouse fixture)

**Analog:** No existing `conftest.py` in the repo (`tests/` currently has only `test_*.py` files: `test_autosub.py`, `test_leakage.py`, `test_legality.py`, `test_product.py`). Pattern instead follows the project's existing test-file conventions read from `tests/test_product.py`:

**Header/docstring convention** (`tests/test_product.py:1-2`):
```python
"""Tests for the product layer: intervals, snapshot, export builders, price
model dataset, solver locks/excludes, the API, and the digest."""
from __future__ import annotations
```
→ apply the same `"""docstring"""` + `from __future__ import annotations` header to `conftest.py`.

**Target content** (from RESEARCH.md, verified against `api.main._state`/`_solve_cache` shape):
```python
"""Shared pytest fixtures for the API test suite."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_api_state():
    """Reset api.main's module-level globals before every test so test order
    never leaks state (APIT-03's required autouse reset)."""
    import api.main as m
    m._state = m._initial_state()
    m._solve_cache.clear()
    yield
    m._state = m._initial_state()
    m._solve_cache.clear()
```

**Import style:** local `import api.main as m` inside the fixture body (not top-of-file) — this matches the existing test pattern in `tests/test_product.py::test_api_solve_and_resolve` (line 158: `import api.main as m` inside the test function, not at module top), which keeps heavy imports (fastapi, pandas) out of collection time for tests that don't need them.

---

### `tests/test_api.py` (new — APIT-01/02/03)

**Analog:** `tests/test_product.py` — API section (lines 154-199) and fixture helpers (lines 17-50)

**Imports pattern** (`tests/test_product.py:1-10`):
```python
"""Tests for the product layer: ..."""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest
```
→ `test_api.py` needs a narrower version: `from __future__ import annotations`, then `import time` (for the concurrency test's `time.sleep`), `from concurrent.futures import ThreadPoolExecutor, as_completed`, `import responses` (or the monkeypatch fallback), plus reuse of `fake_boot`/`fake_pool` — **either import them from `tests/test_product.py` or duplicate the two small builder functions into `test_api.py`** (both are ~20-line pure functions with no external state; duplication avoids cross-test-file coupling, consistent with this repo not using a shared `conftest.py` fixture module for data builders today).

**Fixture-builder pattern** (`tests/test_product.py:14-36`, `fake_boot`):
```python
TEAMS = [{"id": i, "name": f"Club {i}", "short_name": f"C{i:02d}"} for i in range(1, 11)]

def fake_boot(n_per_pos=(3, 7, 7, 5)) -> dict:
    """Bootstrap-static shaped enough for snapshot/export builders."""
    elements, code = [], 1000
    for etype, n in zip((1, 2, 3, 4), n_per_pos):
        for k in range(n):
            code += 1
            elements.append({...})
    return {"elements": elements, "teams": TEAMS, "total_players": 1_000_000,
            "events": [{"id": 1, "is_next": True, "finished": False,
                        "deadline_time": "2026-09-04T17:30:00Z"}]}
```
and `fake_pool` (lines 39-50) — copy this pair verbatim (or import) as the deterministic pool/boot fixture for every `TestClient` test.

**Core `_pool`-monkeypatch pattern** (`tests/test_product.py:156-183`, `test_api_solve_and_resolve` — the established precedent for APIT-01's `/solve`):
```python
def test_api_solve_and_resolve(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as m
    boot = fake_boot()
    pool = fake_pool(boot)
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (pool, 1, boot))
    monkeypatch.delenv("FPL_API_KEYS", raising=False)
    c = TestClient(m.app)

    lock_name = pool.iloc[0]["name"]
    r = c.post("/api/solve", json={"locks": [lock_name]})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "squad" and len(body["squad"]) == 15
```
Extend this exact shape to `/team`, `/rate` (needs `responses` for `_fetch_team`'s two `requests.get` calls — see Pattern 3 below); extend the auth-gate assertion style (`assert c.post(...).status_code == 401`, line 183) for APIT-02.

**Auth stub test pattern** (`api/main.py:159-163`, `require_key`, exercised at `test_product.py:182-183`):
```python
def require_key(x_api_key: str | None = Header(default=None)) -> None:
    keys = {k.strip() for k in os.environ.get("FPL_API_KEYS", "").split(",")
            if k.strip()}
    if keys and x_api_key not in keys:
        raise HTTPException(401, "missing or invalid API key")
```
Three-mode test (open / valid key / invalid key) via `monkeypatch.setenv`/`delenv("FPL_API_KEYS", ...)` — no app restart needed since `require_key` reads `os.environ` at call time.

**`responses`-mocked FPL endpoint pattern** (for `/team`, `/rate` — `_fetch_team()` at `api/main.py:166-201`, `_free_transfers()` at `api/main.py:148-156`, both call `requests.get(f"{config.FPL_API}/entry/...")` directly, not through an importable seam):
```python
import responses
import config

@responses.activate
def test_team_endpoint(monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient
    boot, pool = fake_boot(), fake_pool(fake_boot())
    monkeypatch.setattr(m, "_pool", lambda horizon=1: (pool, 1, boot))
    responses.add(responses.GET, f"{config.FPL_API}/entry/12345/event/0/picks/",
                  json={"picks": [{"element": 1001}], "entry_history": {"bank": 5, "value": 1000}},
                  status=200)
    responses.add(responses.GET, f"{config.FPL_API}/entry/12345/",
                  json={"name": "Test FC", ...}, status=200)
    c = TestClient(m.app)
    r = c.get("/api/team/12345")
    assert r.status_code == 200 and r.json()["entry"] == 12345
```

**Concurrency race test pattern** (APIT-03 — real `ThreadPoolExecutor`, not a sequential loop):
```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def test_concurrent_refresh_and_solve(monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient
    boot, pool = fake_boot(), fake_pool(fake_boot())
    def slow_pool(horizon=1):
        time.sleep(0.05)
        return pool, 1, boot
    monkeypatch.setattr(m, "_pool", slow_pool)
    c = TestClient(m.app)

    def hit():
        return c.post("/api/solve", json={}).status_code

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(hit) for _ in range(20)]
        results = [f.result() for f in as_completed(futures)]

    assert all(status == 200 for status in results)
```
**Assertion discipline (Pitfall 4):** only assert "no exceptions, all 200s" — do NOT assert cache-hit-rate or identical response bodies across concurrent calls; `_solve_cache` is unlocked by design today (deferred fix is Phase 6 REL-05).

**Error handling pattern** (from `api/main.py:169-171`, `_fetch_team`):
```python
if r.status_code == 404:
    raise HTTPException(404, f"entry {entry}: no picks for GW{gw - 1} "
                             "(bad id, or the season hasn't started)")
r.raise_for_status()
```
→ Tests should assert on the specific status codes this pattern produces (404 for bad entry, 422 for unresolvable lock/exclude names via `_resolve()` at `api/main.py:204-224`, 401 for auth).

**Cold-start artifact stub (Pitfall 1)** — every test touching `/health` or `/meta` must stub `_state["artifact"]` to a non-`None` sentinel (the untracked `models/artifacts/xp_model.joblib` must never be loaded in tests):
```python
def test_health_and_meta(monkeypatch):
    import api.main as m
    from fastapi.testclient import TestClient
    boot, fixtures = fake_boot(), []
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, fixtures))
    m._state["artifact"] = object()   # non-None sentinel: skips joblib.load(xp_model.joblib)
    c = TestClient(m.app)
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True
```

---

### `frontend/` (Track B — greenfield, no in-repo analog)

No existing React/TypeScript/component-based frontend exists in this repo (`web/` is framework-free vanilla JS/HTML). All Track B files should follow RESEARCH.md's verified Code Examples section directly rather than an in-repo analog:

- `frontend/vite.config.ts` — proxy `/api` and `/data` to `http://localhost:8000` (RESEARCH.md Code Examples, verified against `api/main.py:402`'s `StaticFiles(directory=config.ROOT / "web", html=True)` mount point — proxy prefix must be `/data`, not `/web/data`, per Pitfall 3).
- `frontend/src/router.tsx` — `createBrowserRouter` from `react-router` (not `react-router-dom`), 8 routes + catch-all `*`, each wrapped by a shared `<PageShell>` with `errorElement={<ErrorState .../>}` per route group (RESEARCH.md Code Examples + `01-UI-SPEC.md` routes table).
- `frontend/src/main.tsx` — `createRoot` + `QueryClientProvider` + `RouterProvider` (RESEARCH.md Code Examples).
- `frontend/src/lib/api.ts` — thin fetch wrapper for `/data/*.json` and `/api/*`. **Cross-stack analog:** `web/assets/app.js:24-28` (`loadJSON`) shows the project's existing convention for this exact problem (fetch a relative JSON path, throw on non-ok status):
  ```javascript
  export async function loadJSON(name) {
    const r = await fetch(`data/${name}`);
    if (!r.ok) throw new Error(`${name}: ${r.status}`);
    return r.json();
  }
  ```
  Port the same "throw a descriptive Error on non-ok status" discipline into the TS/React Query version (`fetchJson`/`fetchApi` wrappers feeding `useQuery`'s `queryFn`), rather than swallowing errors — matches the project's existing error-surfacing convention (see also `web/assets/app.js:9-22`'s `detectApiBase()`, which tries/falls back rather than silently returning a broken value).
- `frontend/src/index.css` — Tailwind v4 CSS-first `@theme` block (RESEARCH.md Code Examples + `01-UI-SPEC.md` Color table) — no `tailwind.config.js`.
- `frontend/src/components/{PageShell,Spinner,ErrorState,PlaceholderPage,NotFoundPage}.tsx` and `frontend/src/routes/*.tsx` (8 files) — no code analog; structure and props contract are locked in `01-UI-SPEC.md` (App Shell Contract, Loading/Error component contract). Route-to-page mapping mirrors `web/*.html`'s existing 8 pages (`index.html`→XpTable, `team.html`→Team, `fixtures.html`→Fixtures, `prices.html`→Prices, `league.html`→League, `scoreboard.html`→Scoreboard, `differentials.html`→Differentials, `methodology.html`→Methodology) for naming/URL parity only, not code pattern (Phase 1 scope is `<PlaceholderPage title="…"/>` per route, per RESEARCH.md's Recommended Project Structure).

---

### `.gitignore` (new, root)

**Analog:** none — file doesn't exist. Minimum required entries per RESEARCH.md Environment Availability: `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`. No existing convention to follow; use standard Python + Node ignore patterns.

## Shared Patterns

### Backend: `_pool`-monkeypatch bypass (the load-bearing shared pattern for all of Track A)
**Source:** `tests/test_product.py:156-183`
**Apply to:** every `TestClient` test hitting `/solve`, `/team`, `/rate` (all call `_pool()` internally). Never let `_refresh()` run for real — it triggers `joblib.load()` on an untracked binary plus real FPL network calls.

### Backend: local (in-function) imports of `fastapi.testclient.TestClient` and `api.main`
**Source:** `tests/test_product.py:157-158`
```python
def test_api_solve_and_resolve(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as m
```
**Apply to:** all new tests in `tests/test_api.py` — matches existing project convention of deferring heavy/app-level imports to test-function scope rather than module top.

### Backend: `from __future__ import annotations` + module docstring header
**Source:** `tests/test_product.py:1-3`, `api/main.py:1-21`
**Apply to:** `tests/conftest.py`, `tests/test_api.py`, and the edited `api/main.py` (already has this header — preserve it).

### Frontend: descriptive-error-on-non-ok-fetch discipline
**Source:** `web/assets/app.js:24-28` (`loadJSON`)
**Apply to:** `frontend/src/lib/api.ts`'s `fetchJson`/`fetchApi` wrappers — throw with response status/URL context rather than swallowing, so React Query's `<ErrorState>` contract (per `01-UI-SPEC.md`) has a real message to render.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/vite.config.ts` | config | request-response | Greenfield — no build-tool config exists in repo; RESEARCH.md Code Examples is the source of truth |
| `frontend/src/main.tsx` | provider/entry | request-response | Greenfield — no React entry point exists |
| `frontend/src/router.tsx` | route | request-response | Greenfield — no client-side router exists (`web/` uses plain multi-page HTML) |
| `frontend/src/components/*.tsx` (5 files) | component | request-response | Greenfield — no component-based UI exists in repo |
| `frontend/src/routes/*.tsx` (8 files) | component/route | request-response | Greenfield — closest conceptual parallel is `web/*.html`'s 8 static pages, but no transferable code pattern (different rendering model entirely) |
| `.gitignore` | config | file-I/O | File does not exist yet anywhere in repo history |

## Metadata

**Analog search scope:** `api/main.py`, `tests/*.py`, `web/assets/*.js`, `web/*.html`, `config.py`, `pytest.ini` (all read in full or in relevant sections this session)
**Files scanned:** 9 target files against ~15 candidate analog files in `api/`, `tests/`, `web/`
**Pattern extraction date:** 2026-08-31
**Tracked-source note:** All analog paths cited above (`api/main.py`, `tests/test_product.py`, `web/assets/app.js`, `pytest.ini`) are currently untracked in git (`git status` shows `??`) — this is a pre-existing repo-hygiene gap (no `.gitignore`, no initial commit), not a gitignored-mirror substitution issue. The planner should ensure these files get `git add`ed as part of this phase's or an earlier housekeeping commit so the paths remain valid/trackable for downstream phases.
