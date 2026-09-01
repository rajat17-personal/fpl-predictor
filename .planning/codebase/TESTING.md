# Testing Patterns

**Analysis Date:** 2026-09-01

## Test Framework

### Python (Backend)

**Runner:**
- pytest (Python testing framework)
- Config: `pytest.ini` (`addopts = -p no:playwright -p no:seleniumbase` disables colliding plugins)
- Runs: 6 test files in `tests/` directory

**Assertion Library:**
- pytest's built-in `assert` statements
- `pytest.raises()` for exception testing

**Run Commands:**
```bash
# All Python tests (from repo root, uses python314 conda env)
/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/

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

## Test File Organization

### Python

**Location:**
- All tests in `tests/` directory (configured in `pytest.ini:testpaths = tests`)
- Separate from source code (not co-located)

**Naming:**
- Test modules: `test_*.py` (e.g., `test_legality.py`, `test_leakage.py`, `test_autosub.py`, `test_api.py`, `test_product.py`)
- Test functions: `test_*` (e.g., `test_pick_squad_legal`, `test_intervals_fit_apply_coverage`)
- Helper functions: `_*` prefix (e.g., `_pool()`, `_assert_legal_squad()`, `_idx()`, `_team()`)

**Structure:**
```
tests/
├── conftest.py          # Shared fixtures (resets api.main module state)
├── test_legality.py     # Squad legality property tests
├── test_leakage.py      # Feature engineering leakage regression tests
├── test_autosub.py      # Formation rule autosub tests
├── test_api.py          # FastAPI contract tests (mocking FPL API)
└── test_product.py      # Product layer builders, snapshots, exports
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

## Test Structure

### Python

**Suite Organization:**

```python
"""Module docstring: what this test suite covers and why.

Example from test_legality.py: Property tests for optimizer output legality.
"""
from __future__ import annotations

import pytest
import config
from optimize.squad_ilp import pick_squad


def _pool(seed: int, n: int = 80) -> pd.DataFrame:
    """Helper: generate random test pool."""
    # Inline helper functions, prefixed with _
    # Reused across multiple tests in the suite

def _assert_legal_squad(s: pd.DataFrame, budget: float):
    """Reusable assertion for squad legality."""
    assert len(s) == config.SQUAD_SIZE
    # Multiple asserts bundled into a helper for readability


@pytest.mark.parametrize("seed", range(5))
def test_pick_squad_legal(seed):
    """Test that optimizer always outputs a legal squad."""
    res = pick_squad(_pool(seed))
    _assert_legal_squad(res["squad"], config.BUDGET)
```

**Patterns:**
- Imports at top: config, modules under test, pytest, pandas/numpy if needed
- Helper functions immediately after imports
- Test functions below helpers
- Fixtures used sparingly (defined in conftest.py or inline)
- Docstrings explain what is being tested and WHY

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

  it("renders known-row cell text with vanilla number formats, including – fallbacks", async () => {
    mockFetchOnce(rows);
    renderXpTable();

    expect(await screen.findByText("Haaland")).toBeInTheDocument();
    const haalandRow = screen.getByText("Haaland").closest("tr")!;
    expect(within(haalandRow).getByText("15.5")).toBeInTheDocument();
  });
});
```

**Patterns:**
- Helper functions (mocks, renderers) at top
- `describe()` blocks organize related tests
- `it()` blocks are independent test cases
- `beforeEach()` / `afterEach()` for setup/cleanup (global state, mocks)
- Comments explain WHY (especially for concurrent operations, edge cases)
- Assertions use Testing Library queries (screen, within, fireEvent)

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
```

**Location:**
- Inline in test files or in `conftest.py` (shared)
- Fixtures defined at module level, before test functions
- Scope: `"function"` (default), `"module"` (expensive data loads), `"session"` (rare)

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
- Scope: Verify API endpoint responses match contract (from test_api.py)
- Approach: Mock FPL API, verify FastAPI routes return expected shapes
- Example: `test_health_and_meta_contract`, `test_solve_endpoint_response`

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

---

*Testing analysis: 2026-09-01*
