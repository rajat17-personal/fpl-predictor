---
last_mapped_commit: 382338e2c164a4433cd73cdbb12ffc9be2621493
---

# Testing Patterns

**Analysis Date:** 2026-09-11

## Test Framework

### Python (Backend)

**Runner:**
- pytest (Python testing framework)
- Config: `pytest.ini` (`addopts = -p no:playwright -p no:seleniumbase` disables colliding plugins)
- Runs: 22 test files in `tests/` directory

**Assertion Library:**
- pytest's built-in `assert` statements
- `pytest.raises()` for exception testing

**Run Commands:**
```bash
# All Python tests (from repo root, uses python314 conda env)
python -m pytest tests/

# Specific test file
python -m pytest tests/test_legality.py

# Specific test function
python -m pytest tests/test_legality.py::test_pick_squad_legal

# Watch mode (if pytest-watch installed)
ptw tests/

# With verbose output
python -m pytest -v
```

### TypeScript/React (Frontend)

**Runner:**
- Vitest 4.1.11 (Vite-native test runner)
- Config: `frontend/vitest.config.ts` (jsdom environment, globals enabled, setupFiles pointing to `src/test/setup.ts`)
- Runs: 22 test files in `frontend/src/` (co-located with source)

**Assertion Library:**
- Vitest's built-in `expect()` statements
- `@testing-library/jest-dom` matchers (e.g., `.toBeInTheDocument()`, `.toHaveAttribute()`)

**Run Commands:**
```bash
# All frontend tests
cd frontend && npm run test

# Watch mode (default for vitest during development)
cd frontend && npm test -- --watch

# Specific test file
npm run test -- src/lib/format.test.ts

# Specific test suite
npm run test -- --reporter=verbose src/routes/

# Coverage (if configured)
npm run test -- --coverage
```

### Playwright (E2E)

**Runner:**
- Playwright Test 1.62.1
- Config: `e2e/playwright.config.ts` (sophisticated multi-server fixture-mode setup)
- Runs: 7 base spec files + 4 variant specs in `e2e/specs/` and `e2e/specs/variants/`

**Key Setup:**
- Builds React frontend once before any test runs (chained in `webServer.command` via `&&`)
- Boots up to 3 concurrent uvicorn servers in fixture mode:
  - `localhost:8100` (normal fixtures, default variant)
  - `localhost:8101` (blank fixtures — 6 clubs with no GW fixtures)
  - `localhost:8102` (dgw fixtures — double gameweek variant)
- All servers serve the same pre-built `frontend/dist/` SPA from `check_dir=False` mount
- Locale fixed to `en-GB`, timezone to `UTC` (mandatory for consistent deadline rendering across developer machines and CI)
- Browser: Chromium only (no Firefox/Safari/WebKit variants in Phase 5)

**Run Commands:**
```bash
# All specs with all variants (3 servers, full run)
cd e2e && npm run test

# Fast local run (normal variant only, single server)
E2E_VARIANTS=0 npm run test

# Specific spec file
npm run test -- specs/xp-table.spec.ts

# Specific test within a spec
npm run test -- specs/xp-table.spec.ts -g "renders the frozen top 50"

# Verbose reporter
npm run test -- --reporter=verbose

# Install Chromium (only needed first time)
npm run install:browser

# View HTML report after run
npx playwright show-report
```

**CI Integration (see `.github/workflows/ci.yml`):**
- Chained after Python + TypeScript tests (all must pass before E2E runs)
- Full 3-server variant run (no `E2E_VARIANTS=0` narrowing)
- Retries: 1 (CI only; local runs don't retry)
- Python via `setup-python@v7.0.0` action (python on PATH is what uvicorn uses, no E2E_PYTHON env var)
- Node via `setup-node@v7.0.0` action (cache includes both frontend/ and e2e/ package-lock.json)

## Test File Organization

### Python

**Location:**
- All tests in `tests/` directory (configured in `pytest.ini:testpaths = tests`)
- Separate from source code (not co-located)

**Naming:**
- Test modules: `test_*.py` (e.g., `test_legality.py`, `test_leakage.py`, `test_bracket.py`, `test_availability.py`, `test_api.py`, `test_product.py`, `test_cron.py`)
- Test functions: `test_*` (e.g., `test_pick_squad_legal`, `test_external_preds_rejects_missing_required_column`)
- Helper functions: `_*` prefix (e.g., `_pool()`, `_assert_legal_squad()`, `_idx()`, `_team()`)

**Structure:**
```
tests/
├── conftest.py              # Shared fixtures (resets api.main module state)
├── test_legality.py         # Squad legality property tests
├── test_leakage.py          # Feature engineering leakage regression tests
├── test_bracket.py          # External prediction ingestion validation (Phase 10-09)
├── test_availability.py     # Player availability fixture tests
├── test_api.py              # FastAPI contract tests (mocking FPL API)
├── test_api_hardening.py    # API resilience and error path tests
├── test_product.py          # Product layer builders, snapshots, exports
├── test_cron.py             # Daily/weekly pipeline orchestration
├── test_experiments.py      # Training/backtest experiments
├── test_scoreboard.py       # Post-GW accuracy evaluation
├── test_payloads.py         # Data payload schema validation
├── test_fixture_mode.py     # Fixture-mode API behavior (static mount SPA fallback)
├── test_chips.py            # Chip timing optimization
├── test_obs.py              # Observability and logging
├── test_reliability.py      # Retry logic and resilience
├── test_react_seam.py       # Frontend integration seams
├── test_crosswalk.py        # Player ID mapping
├── test_capture_fixtures.py # Fixture capture/generation tooling
├── test_rl_env.py           # RL environment validation
└── test_transfermarkt.py    # Transfermarkt injury scraper tests
```

### TypeScript/React

**Location:**
- Co-located with source: `frontend/src/**/*.test.ts` and `frontend/src/**/*.test.tsx`
- Test fixtures in `frontend/src/test/fixtures/` (JSON files matching API contract)

**Naming:**
- Test files: `*.test.ts` or `*.test.tsx` (e.g., `XpTable.test.tsx`, `format.test.ts`)
- Test suites: `describe("ComponentName")` or `describe("functionName (description)")`
- Test cases: `it("does X when Y")` (descriptive statements)

**Structure:**
```
frontend/src/
├── test/
│   ├── setup.ts           # Vitest globals setup (cleanup after each test)
│   └── fixtures/          # JSON test data matching API contracts
│       ├── xp_table.json
│       ├── captains.json
│       ├── meta.json
│       ├── fixtures.json
│       └── ... (more fixtures)
├── lib/
│   ├── format.ts
│   ├── format.test.ts
│   ├── theme.ts
│   ├── theme.test.ts
│   └── ... (more utilities with tests)
├── routes/
│   ├── XpTable.tsx
│   ├── XpTable.test.tsx
│   └── ... (more pages with tests)
└── components/
    ├── ThemeToggle.tsx
    ├── ThemeToggle.test.tsx
    └── ... (more components with tests)
```

### Playwright (E2E)

**Location:**
- Spec files in `e2e/specs/` (normal tests)
- Variant specs in `e2e/specs/variants/` (blank-*.spec.ts, dgw-*.spec.ts)
- Helpers in `e2e/helpers/page.ts` (reusable navigation and fixture utilities)
- Fixtures in `e2e/fixtures/v1/{normal,blank,dgw}/{api,web-data}/` (frozen JSON snapshots)

**Naming:**
- Spec files: `*.spec.ts` (e.g., `xp-table.spec.ts`, `team-solver.spec.ts`, `smoke.spec.ts`)
- Variant specs: `{blank,dgw}-*.spec.ts` (e.g., `blank-xp-table.spec.ts`, `dgw-chips.spec.ts`)
- Helper functions: `camelCase` (e.g., `gotoReady()`, `openCardMenu()`, `rowCount()`)
- Test suites: `test.describe("Feature — what it validates")`
- Test cases: `test("renders X correctly")`

**Structure:**
```
e2e/
├── playwright.config.ts       # Full server lifecycle, 3 fixture variants, browser setup
├── helpers/
│   └── page.ts               # Shared navigation, fixture constants, observers
├── specs/
│   ├── xp-table.spec.ts       # xP table (flagship page, E2E-03)
│   ├── team-solver.spec.ts    # Team page — Squad tab solver (E2E-02)
│   ├── team-plan.spec.ts      # Team page — Plan Transfers tab
│   ├── rate-my-team.spec.ts   # Rate My Team utility
│   ├── fixtures-prices.spec.ts # Fixtures & Prices page
│   ├── shell-geometry.spec.ts  # Page shell layout & responsive behavior
│   └── smoke.spec.ts          # Smoke test (one path through full stack)
└── specs/variants/
    ├── blank-xp-table.spec.ts     # xP table under blank-club variant
    ├── blank-fixtures.spec.ts     # Fixtures page under blank-club variant
    ├── dgw-chips.spec.ts          # Chip timing under DGW variant
    └── dgw-fixtures.spec.ts       # Fixtures page under DGW variant
```

## Test Structure

### Python

**Suite Organization:**

```python
"""Module docstring: what this test suite covers and why.

Example from test_bracket.py: External prediction ingestion validation.
"""
from __future__ import annotations

import pytest
import config
from optimize.squad_ilp import pick_squad

# Module-scoped fixture for expensive data (shared across all tests in suite)
@pytest.fixture(scope="module")
def df_full():
    return load_features()

def _pool(seed: int, n: int = 80) -> pd.DataFrame:
    """Helper: generate random test pool."""
    # Inline helper functions, prefixed with _
    # Reused across multiple tests in the suite

def _assert_legal_squad(s: pd.DataFrame, budget: float):
    """Reusable assertion for squad legality."""
    assert len(s) == config.SQUAD_SIZE
    # Multiple asserts bundled into a helper for readability

# Conditional fixture: skip entire test if data not present
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")

@needs_data
@pytest.mark.parametrize("seed", range(5))
def test_pick_squad_legal(seed):
    """Test that optimizer always outputs a legal squad."""
    res = pick_squad(_pool(seed))
    _assert_legal_squad(res["squad"], config.BUDGET)
```

**Patterns:**
- Imports at top: config, modules under test, pytest, pandas/numpy if needed
- Module-level docstring explaining scope and dependencies
- Helper functions immediately after imports (private, prefixed with `_`)
- Fixtures (pytest and module-scoped) below helpers
- Test functions below fixtures
- Docstrings explain WHAT is tested and WHY it matters
- Conditional skips (`@needs_data`) for expensive data dependencies

### TypeScript/React

**Suite Organization:**

```typescript
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import XpTable from "./XpTable";
import fixtureRows from "../test/fixtures/xp_table.json";

const rows = fixtureRows as XpRow[];

/* Comment explaining why mocking is structured this way.
 * Routes fire concurrent queries, so mocking must route by URL not call order.
 */
function mockFetchOnce(xpTableBody: unknown, captainsBody: unknown = []) {
  globalThis.fetch = vi.fn((path: string) => {
    const body = path === "/data/captains.json" ? captainsBody : xpTableBody;
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    });
  }) as unknown as typeof fetch;
}

function renderXpTable() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <QueryClientProvider client={queryClient}>
        <XpTable />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("XpTable (Task 1 — end-to-end slice)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders known-row cell text with vanilla number formats", async () => {
    mockFetchOnce(rows);
    renderXpTable();

    expect(await screen.findByText("Haaland")).toBeInTheDocument();
    const haalandRow = screen.getByText("Haaland").closest("tr")!;
    expect(within(haalandRow).getByText("15.5")).toBeInTheDocument();
  });
});
```

**Patterns:**
- Helper functions (mocks, renderers) at top, above test suites
- `describe()` blocks organize related tests
- `it()` blocks are independent test cases
- `beforeEach()` / `afterEach()` for setup/cleanup (global state, mocks)
- Comments explain WHY (especially for concurrent operations, edge cases)
- Assertions use Testing Library queries (screen, within, fireEvent)
- Fixtures imported as constants with TypeScript type casting

### Playwright

**Suite Organization:**

```typescript
import { test, expect, type Page } from "@playwright/test";
import { gotoReady, watchOrigin, ENTRY, GW, PICKS_EVENT } from "../helpers/page";

/*
 * Team page — Squad tab (E2E-02). Every navigation uses gotoReady (clock
 * pinned before nav, fonts settled after) per the suite-wide convention.
 * `[aria-label$=" actions"]` (PlayerCard.tsx's `{name} actions` trigger) is
 * this file's card-count/name-set proxy for an interactive (loaded/solved)
 * pitch; the default model-squad pitch and the plan-flow pitch (team-plan.
 * spec.ts) render no such trigger at all (no `onMark` passed — 03-01's
 * view-only default and PlanTransfers.tsx's read-only per-week pitch), so
 * counting the five `role="group"` rows' direct children is this file's
 * card-count proxy for those.
 *
 * Every solve below is a genuine POST to /api/solve, run by the real
 * PuLP/CBC ILP over the frozen prediction pool (D-10) — no Playwright
 * route-mock interception anywhere in this file.
 */

const MAX_FREE_TRANSFERS = 5;
const BUDGET = 100.0;

async function openCardMenu(page: Page, name: string) {
  await page.getByRole("button", { name: `${name} actions` }).click();
  return page.getByRole("menu", { name: `${name} actions` });
}

async function rowCount(
  page: Page,
  label: "Goalkeeper" | "Defenders" | "Midfielders" | "Forwards" | "Bench",
): Promise<number> {
  return page.getByRole("group", { name: label }).locator("> div").count();
}

test.describe("Squad tab: default view (no entry)", () => {
  test("renders the model squad view-only, with no team auto-submitted", async ({
    page,
  }) => {
    await gotoReady(page, "/team");

    await expect(page.getByRole("heading", { level: 1 }))
      .toHaveText(`Model squad · GW${GW}`);
    await expect(page.getByText("3-5-2", { exact: true })).toBeVisible();
  });
});
```

**Patterns:**
- Multi-line doc comment at spec top: Explain WHAT the spec validates, WHY it matters, key assumptions/fixtures
- Hand-derived expected values documented (e.g., "row 1 from e2e/fixtures/v1/normal/web-data/xp_table.json")
- Helper functions (async, accepting `page: Page`) below imports, above test suites
- Constants for test data (MAX_FREE_TRANSFERS, BUDGET, BLANK_CLUBS)
- `test.describe()` groups related tests
- `test()` blocks are independent (no cross-test state sharing via page)
- All navigation via `gotoReady()` helper (clock pinned before, fonts settled after)
- Assertions query by accessible role/text (preferred) not CSS selectors
- Timeouts: 30 sec per test, 10 sec per assertion (from playwright.config.ts)

## Mocking

### Python

**Framework:** pytest fixtures + `monkeypatch` for dependency injection; `responses` library for HTTP stubbing

**Patterns:**

```python
# Inline test data generators (from test_api.py)
def fake_boot(n_per_pos=(3, 7, 7, 5)) -> dict:
    """Bootstrap-static shaped enough for snapshot/export builders."""
    elements, code = [], 1000
    for etype, n in zip((1, 2, 3, 4), n_per_pos):
        for k in range(n):
            code += 1
            elements.append({
                "id": code - 900, "code": code, "web_name": f"P{code}",
                "team": (code % 10) + 1, "element_type": etype, "status": "a",
                # ... populate fields matching FPL API bootstrap-static
            })
    return {"elements": elements, "teams": TEAMS, ...}

# Module state reset via autouse fixture (from conftest.py)
@pytest.fixture(autouse=True)
def _reset_api_state():
    """Reset api.main's module-level globals before and after every test."""
    import api.main as m
    m._state = m._initial_state()
    m._state["artifact"] = object()  # Prevent joblib.load() during tests
    m._solve_cache.clear()
    yield
    m._state = m._initial_state()
    m._solve_cache.clear()

# Monkeypatching external calls
def test_health_and_meta_contract(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as m
    
    boot = fake_boot()
    monkeypatch.setattr(m, "_load_live", lambda force=True: (boot, []))
    # Now _load_live returns fake data instead of hitting FPL API
```

**What to Mock:**
- External data sources (use `fake_boot()`, `fake_pool()` functions for deterministic test data)
- Random generators: seed with `np.random.default_rng(seed)` for reproducibility
- Time-sensitive data: pass as parameters or use frozen fixtures
- Module state: use `monkeypatch` to override (e.g., `_load_live`, config values)
- HTTP calls: use `responses` library to intercept and respond without network (see test_api.py)

**What NOT to Mock:**
- Core business logic (optimizer, model, backtest engine) — test directly
- pandas/numpy operations
- Config constants
- Unit-tested helper functions — test them directly or via their parent

### TypeScript/React

**Framework:** Vitest's `vi` (Sinon-like mocking); `@testing-library/react` for component testing

**Patterns:**

```typescript
// Global fetch mocking (from XpTable.test.tsx)
function mockFetchOnce(xpTableBody: unknown, captainsBody: unknown = []) {
  globalThis.fetch = vi.fn((path: string) => {
    const body = path === "/data/captains.json" ? captainsBody : xpTableBody;
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    });
  }) as unknown as typeof fetch;
}

// Global stubbing (from ThemeToggle.test.tsx)
function installMatchMediaStub(initialMatches: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: initialMatches,
      media: "(prefers-color-scheme: dark)",
      addEventListener: () => {},
      removeEventListener: () => {},
    })),
  );
}

// Cleanup after each test
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// React component rendering with providers
function renderXpTable() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <QueryClientProvider client={queryClient}>
        <XpTable />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
```

**What to Mock:**
- Fetch calls: use `vi.fn()` to return resolved promises with test fixture JSON
- Global APIs: `matchMedia`, `localStorage`, `window` features — use `vi.stubGlobal()`
- React Router: use `MemoryRouter` with test routes
- React Query: use `QueryClient` with `retry: false` to avoid test delays
- TanStack Query calls: route mocks by URL to handle concurrent queries

**What NOT to Mock:**
- React component rendering (test real components)
- React hooks behavior (test real hooks via custom hook test patterns)
- User interactions (use `fireEvent` or `userEvent` for real clicks)
- localStorage when testing theme persistence (may use real localStorage in jsdom)

### Playwright

**Framework:** Native Playwright route interception; `@playwright/test` fixture system

**Patterns (NOT used in e2e specs):**

```typescript
// Playwright HAS route interception capabilities, but the e2e suite
// deliberately does NOT mock network calls. Instead:
// - All fixtures are pre-baked as frozen JSON in e2e/fixtures/v1/{normal,blank,dgw}/
// - uvicorn boots in fixture-mode (FPL_FIXTURE_DIR env var switches data source)
// - Specs drive real API calls against fixture data (D-10)
// - No route.abort(), no route.continue({ response }), no vi.fn()

// Instead, every spec uses gotoReady() helper to pin clock/fonts before nav
export async function gotoReady(page: Page, path: string): Promise<void> {
  await page.clock.setFixedTime(FROZEN_NOW);
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
}

// And watchOrigin() observer to verify no foreign requests:
export function watchOrigin(page: Page): OriginWatch {
  const foreign: string[] = [];
  let testOrigin: string | null = null;
  page.on("request", (request) => {
    const requestOrigin = new URL(request.url()).origin;
    if (testOrigin === null && request.isNavigationRequest()) {
      testOrigin = requestOrigin;
    } else if (requestOrigin !== testOrigin) {
      foreign.push(request.url());
    }
  });
  return { getForeignRequests: () => foreign };
}

// Test usage:
test("no foreign requests fired", async ({ page }) => {
  const origin = watchOrigin(page);
  await gotoReady(page, "/");
  expect(origin.getForeignRequests()).toEqual([]);
});
```

**Why No Mocking:**
- Fixture-mode uvicorn (booted by playwright.config.ts) is the system under test
- Mocking network calls would skip testing the full request/response cycle
- Pre-baked frozen fixtures guarantee deterministic test data across all runs
- Clock pinning (via `setFixedTime()`) replaces need for time mocks — exact time is known in advance

**What IS Controlled:**
- Browser locale (`en-GB`) and timezone (`UTC`) — mandatory for deadline string consistency
- Viewport size (when `opts.viewport` passed to `gotoReady()`)
- Fixture set (via `E2E_VARIANTS=0` env var or `webServer.env` FPL_FIXTURE_DIR)

## Fixtures and Factories

### Python

**Test Data:**

```python
# From conftest.py: pytest fixture for expensive data
@pytest.fixture(scope="module")
def feat():
    return pd.read_parquet(FEATURES)

@needs_data
def test_first_appearance_has_no_rolling_features(feat):
    roll_cols = [c for c in feat.columns
                 if any(c.endswith(sfx) for sfx in ("_r3", "_r5", "_r10", "_rall"))]
    first = (feat.sort_values(["season", "player_id", "kickoff_time"])
             .groupby(["season", "player_id"]).head(1))
    assert first[roll_cols].notna().any(axis=1).sum() == 0


# Conditional fixture using pytest.mark.skipif
FEATURES = config.PROCESSED_DIR / "features.parquet"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")

# Module-scoped fixture: expensive, shared across test suite
@pytest.fixture(scope="module")
def te_2025(df_full):
    """A real in-process LightGBM run's own `_preds_for` output for the
    2025-26 test season -- the known-good input the round-trip test writes
    to a parquet and reads back through the new seam."""
    te, _models, _cols = _preds_for(df_full, "2025-26")
    return te
```

**Location:**
- Inline in test files or in `conftest.py` (shared)
- Fixtures defined at module level, before test functions
- Scope: `"function"` (default), `"module"` (expensive data loads), `"session"` (rare)
- Module-scoped fixtures are preferred for expensive operations (training models, loading large parquets)

### TypeScript/React

**Test Data:**

```typescript
// Fixture JSON files in src/test/fixtures/
// Example: xp_table.json (imported as const rows)
import fixtureRows from "../test/fixtures/xp_table.json";

const rows = fixtureRows as XpRow[];

// Used directly in tests:
it("renders known rows", () => {
  mockFetchOnce(rows);  // Pass fixture to mock
  renderXpTable();
  expect(screen.getByText("Haaland")).toBeInTheDocument();
});
```

**Location:**
- JSON fixtures in `frontend/src/test/fixtures/` (one file per API endpoint/contract)
- Imported in tests as TypeScript constants with type casting
- No factory functions; fixtures are static JSON matching exact API contracts

### Playwright

**Test Data:**

```typescript
// Frozen snapshots in e2e/fixtures/v1/{normal,blank,dgw}/{api,web-data}/
// Example: e2e/fixtures/v1/normal/api/capture.json (shared constant source)
import capture from "../fixtures/v1/normal/api/capture.json" with { type: "json" };

export const FROZEN_NOW = new Date(capture.frozen_now_utc);
export const GW = capture.gw;
export const ENTRY = capture.entry;
export const PICKS_EVENT = capture.picks_event;

// Used throughout all specs:
test("renders the deadline banner", async ({ page }) => {
  await gotoReady(page, "/");
  // Frozen clock knows the exact deadline from capture.json
  // Spec never hardcodes a second copy of GW, ENTRY, etc.
});
```

**Location:**
- Frozen JSON snapshots in `e2e/fixtures/v1/{normal,blank,dgw}/` (immutable test data)
- API captures (e.g., `capture.json`) shared via helpers (`e2e/helpers/page.ts`)
- Web-data exports (e.g., `xp_table.json`, `captains.json`) matching `web/data/*.json` contract
- Expected values hardcoded (hand-derived once from fixtures, never recomputed at test time)

**Fixture Variants:**
- **normal:** Default set (all 20 clubs have GW fixtures)
- **blank:** 6 clubs with no fixtures that GW (ARS, AVL, BHA, BOU, BRE, CHE)
- **dgw:** Double-gameweek set (some clubs with 2 fixtures, some with 0)

## Coverage

### Python

**Requirements:** No coverage target enforced (no `.coveragerc` or similar config)

**View Coverage:**
```bash
# Install coverage if not present
pip install pytest-cov

# Run tests with coverage report
python -m pytest --cov=. --cov-report=html

# View in browser
open htmlcov/index.html
```

### TypeScript/React

**Requirements:** No coverage target configured

**View Coverage:**
```bash
# If coverage plugin installed
npm run test -- --coverage

# View in browser (if HTML output generated)
open coverage/index.html
```

### Playwright

**Requirements:** No coverage target configured (E2E tests don't measure code coverage)

**Run & Report:**
```bash
# Run all specs and generate HTML report
npm run test

# View report in browser
npx playwright show-report
```

## Test Types

### Python

**Unit Tests:**
- Scope: Single function or class (e.g., `test_pick_squad_legal` tests `pick_squad()`)
- Approach: Inline test data (`_pool()` functions), direct assertions
- Example: `test_pick_squad_legal`, `test_optimize_gw_legal`, `test_intervals_fit_apply_coverage`

**Integration Tests:**
- Scope: Multiple components working together (e.g., squad picking + transfer optimization + autosubs)
- Approach: Use realistic data (small synthetic pools), test end-to-end behavior
- Example: `test_grandfathered_club_cap` (holds state across optimize steps), `test_snapshot_frame_shape` (data pipeline)

**Regression Tests:**
- Scope: Protect against known bugs (prefixed with B1, B2, etc. in docstrings)
- Approach: Narrow tests for specific edge cases
- Example: `test_blank_gw_holding_needs_metadata` (B1: blank GW position corruption), `test_autosub_*` (B2: formation rules)

**Contract Tests:**
- Scope: Verify API endpoint responses match contract (from test_api.py, test_api_hardening.py)
- Approach: Mock FPL API, verify FastAPI routes return expected shapes
- Example: `test_health_and_meta_contract`, `test_solve_endpoint_response`

**Validation Tests:**
- Scope: Verify data pipeline outputs (schema, constraints, leakage) — see test_bracket.py, test_leakage.py
- Approach: Load real/external predictions, apply schema/validation gates
- Example: `test_external_preds_rejects_missing_required_column`, `test_no_future_leakage`

### TypeScript/React

**Component Tests:**
- Scope: Render component with required providers, test UI behavior
- Approach: Use `render()` from Testing Library, query by accessible role/text
- Example: `XpTable.test.tsx`, `ThemeToggle.test.tsx`

**Hook Tests:**
- Scope: Test React hook logic (form state, data fetching)
- Approach: Render a test component using the hook, assert state changes
- Example: `useTheme()` tested via `ThemeToggle` component

**Integration Tests:**
- Scope: Full page render with routing, data fetching, all providers
- Approach: Mock fetch, render full route tree, test user flows
- Example: `XpTable` with `QueryClientProvider`, `MemoryRouter`, fetch mocks

**Smoke Tests:**
- Scope: Verify test harness itself (jsdom, TypeScript, Testing Library)
- Approach: Minimal render of a component
- Example: `harness.test.tsx` (proves jsdom present, JSX compiles, matchers registered)

### Playwright

**Smoke Test (Full Stack):**
- Scope: One path through every layer (build → fixture-mode uvicorn → real API → real solver → Chromium rendering)
- Approach: Navigate to `/`, pin clock, verify exact expected values
- File: `e2e/specs/smoke.spec.ts`
- Example: Verify banner text "GW{gw} · {deadline}" matches frozen capture

**UI Contract Tests:**
- Scope: Render specific pages, verify structure/content against frozen fixtures
- Approach: Query by accessible role/text, assert cell values, row counts, formations
- Example: `xp-table.spec.ts` (top 50 rows), `team-solver.spec.ts` (squad pitch)

**Interaction Tests:**
- Scope: Form submissions, navigation, state changes via user actions
- Approach: Fill inputs, click buttons, verify URL changes and UI updates
- Example: Team solver form (entry load, free transfer slider, solve button)

**Layout & Geometry Tests:**
- Scope: Responsive breakpoints, bounding boxes, viewport-specific rendering
- Approach: Set viewport size, measure element positions/sizes after font load
- File: `e2e/specs/shell-geometry.spec.ts`

**Variant Tests:**
- Scope: Behavior under different fixture sets (blank clubs, DGW)
- Approach: Run same test logic against different `webServer` (different port/env)
- Files: `e2e/specs/variants/{blank,dgw}-*.spec.ts`
- Example: `blank-xp-table.spec.ts` verifies no blanked-club rows appear in the table

**Network Isolation Tests:**
- Scope: Verify no external requests (e.g., to fantasy.premierleague.com)
- Approach: Use `watchOrigin()` helper, collect foreign URLs, assert empty
- Example: `smoke.spec.ts` calls `expect(origin.getForeignRequests()).toEqual([])`

## Common Patterns

### Python

**Parametrized Tests:**

```python
@pytest.mark.parametrize("seed", range(5))
def test_pick_squad_legal(seed):
    """Test across 5 different random seeds."""
    res = pick_squad(_pool(seed))
    _assert_legal_squad(res["squad"], config.BUDGET)
```

**Error Testing:**

```python
with pytest.raises(ValueError):
    optimize_gw(shrunk, squad, bank=0.0, free_transfers=1)
```

**Fixture Injection:**

```python
def test_minutes_r5_matches_independent_recompute(feat):
    # feat is injected by pytest
    got = feat[...]["minutes_r5"]
    exp = raw[...]["minutes"].shift(1).rolling(5, min_periods=1).mean()
    assert np.allclose(got.fillna(-1).values, exp.fillna(-1).values)
```

### TypeScript/React

**Async Queries:**

```typescript
it("renders after async query resolves", async () => {
  mockFetchOnce(rows);
  renderXpTable();
  // Wait for element to appear (query triggers fetch, resolves, re-render)
  expect(await screen.findByText("Haaland")).toBeInTheDocument();
});
```

**User Interactions:**

```typescript
it("updates state on click", () => {
  render(<ThemeToggle />);
  fireEvent.click(screen.getByRole("button", { name: "Dark theme" }));
  expect(screen.getByRole("button", { name: "Dark theme" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
```

**Accessible Queries:**

```typescript
// Query by accessible role (preferred)
screen.getByRole("table", { name: "xP table" })

// Query by text
screen.getByText("Haaland")

// Query by label
screen.getByLabelText("Player name")

// Scoped queries (within a subtree)
within(haalandRow).getByText("15.5")
```

### Playwright

**Clock Pinning & Font Wait:**

```typescript
test("renders deadline banner with exact time", async ({ page }) => {
  await gotoReady(page, "/");  // Clock pinned BEFORE nav, fonts settled AFTER
  // FROZEN_NOW is known from capture.json; banner renders predictable string
  await expect(page.getByText("Fri 4 Sept, 17:30")).toBeVisible();
});
```

**Network Observation:**

```typescript
test("no foreign requests fired", async ({ page }) => {
  const origin = watchOrigin(page);
  await gotoReady(page, "/team?entry=6980093");
  expect(origin.getForeignRequests()).toEqual([]);
});
```

**Hand-Derived Expectations:**

```typescript
// Every expected value is hardcoded once, never recomputed at test time
const BANNER_LINE_1 = "GW3 · Fri 4 Sept, 17:30";
const BANNER_LINE_2 = "in 1d 1h · generated just now";

test("renders banner lines exactly", async ({ page }) => {
  await gotoReady(page, "/");
  await expect(page.getByText(BANNER_LINE_1, { exact: true })).toBeVisible();
  await expect(page.getByText(BANNER_LINE_2, { exact: true })).toBeVisible();
});
```

**Multi-Server Variants:**

```typescript
// This spec runs in the chromium-blank project only (see playwright.config.ts)
// It verifies the blank-fixtures variant (6 clubs with no GW fixtures)
test.describe("blank set xP table", () => {
  test("no visible row belongs to a blanked club", async ({ page }) => {
    await gotoReady(page, "/");
    const teams = await page.locator("table tbody td:nth-child(3)").allTextContents();
    expect(teams).not.toContain("ARS");  // Arsenal is blanked
    expect(teams).not.toContain("AVL");  // Aston Villa is blanked
    // etc.
  });
});
```

## Test Execution Tips

### Python

```bash
# Run specific test
python -m pytest tests/test_legality.py::test_pick_squad_legal -v

# Run tests matching a pattern
python -m pytest tests/ -k "legal" -v

# Show print statements
python -m pytest tests/ -s

# Stop on first failure
python -m pytest tests/ -x

# Debug with pdb on failure
python -m pytest tests/ --pdb

# From CI (full run with pytest output)
python -m pytest
```

### TypeScript/React

```bash
cd frontend

# Run all tests once
npm run test

# Watch mode (default, re-runs on file changes)
npm run test -- --watch

# Specific file
npm run test -- src/lib/format.test.ts

# Specific test name
npm run test -- --grep "formats to exactly one decimal place"

# Debug mode (runs in single thread)
npm run test -- --inspect-brk

# Show test tree (helpful for understanding structure)
npm run test -- --reporter=verbose
```

### Playwright

```bash
cd e2e

# Full suite with all variants (3 servers)
npm run test

# Fast local run (normal variant only, 1 server)
E2E_VARIANTS=0 npm run test

# Specific spec file
npm run test -- specs/xp-table.spec.ts

# Specific test within spec
npm run test -- specs/xp-table.spec.ts -g "renders the frozen top 50"

# Verbose reporter
npm run test -- --reporter=verbose

# Debug mode (headed browser, inspects)
npm run test -- --debug

# View results from last run
npx playwright show-report

# Install Chromium (required first time)
npm run install:browser

# From CI (full run as it would be in CI)
npm run test
```

## CI Test Chain

The `.github/workflows/ci.yml` runs tests in a strict linear sequence:

1. **lint-build** (ubuntu-latest)
   - Lint Python code with `ruff check .`
   - Build React frontend: `npm --prefix frontend run build`
   - Upload `frontend/dist/` as artifact

2. **test** (needs lint-build)
   - Download `frontend/dist/` artifact
   - Run Python tests: `python -m pytest`
   - Run TypeScript tests: `npm --prefix frontend test`

3. **e2e** (needs test)
   - Rebuild frontend (owned by playwright.config.ts, not artifact-based)
   - Boot 3 uvicorn fixture-mode servers
   - Run Playwright specs: `npm --prefix e2e run test`

This linear chain ensures:
- Frontend is built once and verified before any test uses it
- Python tests pass before E2E runs (E2E depends on Python API working)
- E2E runs against the exact bundle Python tests verified
- A broken lint/test stage never wastes time building an image

---

*Testing analysis: 2026-09-11*
