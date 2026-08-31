# Testing Patterns

**Analysis Date:** 2026-08-31

## Test Framework

**Runner:**
- pytest
- Config: `pytest.ini` (see `/home/sraja/fpl/pytest.ini`)
- Plugins disabled: `addopts = -p no:playwright -p no:seleniumbase` (collides on `--browser` flag)

**Assertion Library:**
- pytest's built-in `assert` statements (no pytest-mock or other assertion libs needed)

**Run Commands:**
```bash
# Run all tests (from repo root)
python -m pytest

# With coverage (if coverage plugin installed)
python -m pytest --cov

# Specific test file
python -m pytest tests/test_legality.py

# Specific test function
python -m pytest tests/test_legality.py::test_pick_squad_legal
```

**Important:** Use the python314 conda environment:
```bash
/home/sraja/miniconda3/envs/python314/bin/python -m pytest
```

## Test File Organization

**Location:**
- All tests in `tests/` directory (see `pytest.ini:testpaths = tests`)
- Co-located with source code (tests are separate from source, not alongside)

**Naming:**
- Test modules: `test_*.py` (e.g., `test_legality.py`, `test_leakage.py`, `test_autosub.py`, `test_product.py`)
- Test functions: `test_*` (e.g., `test_pick_squad_legal`, `test_intervals_fit_apply_coverage`)
- Helper functions: `_*` prefix (e.g., `_pool()`, `_assert_legal_squad()`, `_idx()`, `_team()`)

**Structure:**
```
tests/
├── test_legality.py       # Property tests for optimizer legal outputs
├── test_leakage.py        # Feature leakage regression tests
├── test_autosub.py        # Autosub formation rule tests
└── test_product.py        # Product layer builders, intervals, snapshot, export
```

## Test Structure

**Suite Organization:**

```python
"""Module docstring: what this test suite covers and why.

Example from test_legality.py:
"""
import pytest
import config
from optimize.squad_ilp import pick_squad


def _pool(seed: int, n: int = 80) -> pd.DataFrame:
    """Helper: generate random test pool."""
    # Helper functions are inline, prefixed with _
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
- Fixtures (below) used sparingly

## Mocking

**Framework:** pytest fixtures (no mocking library like `unittest.mock` found)

**Patterns:**

```python
# Inline test data generators (from test_product.py)
def fake_boot(n_per_pos=(3, 7, 7, 5)) -> dict:
    """Bootstrap-static shaped enough for snapshot/export builders."""
    elements, code = [], 1000
    for etype, n in zip((1, 2, 3, 4), n_per_pos):
        for k in range(n):
            code += 1
            elements.append({
                "id": code - 900, "code": code, "web_name": f"P{code}",
                # ... populate fields
            })
    return {"elements": elements, "teams": TEAMS, ...}


def fake_pool(boot: dict) -> pd.DataFrame:
    """Convert bootstrap to player pool DataFrame."""
    rng = np.random.default_rng(0)
    # Deterministic seed for reproducible tests
    pos = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    rows = [{"player_code": el["code"], ...} for el in boot["elements"]]
    return pd.DataFrame(rows)
```

**What to Mock:**
- External data sources (fake_boot, fake_pool functions) — replace with deterministic test data
- Random generators: use seeded `np.random.default_rng(seed)` for reproducibility (see test_product.py:40, test_legality.py:16)
- Time-sensitive data: pass as parameters or use frozen fixtures

**What NOT to Mock:**
- Core business logic (optimizer, model, backtest engine)
- pandas/numpy operations
- Config constants
- Unit-tested helper functions (test them directly)

## Fixtures and Factories

**Test Data:**

```python
# From test_leakage.py: pytest fixture for expensive data
@pytest.fixture(scope="module")
def feat():
    return pd.read_parquet(FEATURES)

@needs_data
def test_first_appearance_has_no_rolling_features(feat):
    # feat is passed as argument, pytest injects it
    roll_cols = [c for c in feat.columns if any(c.endswith(sfx) for sfx in ("_r3", "_r5", "_r10", "_rall"))]
    first = (feat.sort_values(["season", "player_id", "kickoff_time"])
             .groupby(["season", "player_id"]).head(1))
    assert first[roll_cols].notna().any(axis=1).sum() == 0


# Conditional fixture using pytest.mark.skipif
FEATURES = config.PROCESSED_DIR / "features.parquet"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")
```

**Location:**
- Inline in test files (no separate `conftest.py`)
- Fixtures defined at module level, before test functions
- Scope can be `"function"` (default), `"module"` (expensive data), or `"session"`

## Coverage

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

## Test Types

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

**E2E Tests:**
- Not used (no Selenium, Playwright, or browser automation found)

## Common Patterns

**Async Testing:**
- Not used (no async code in project)

**Error Testing:**

```python
# From test_legality.py
def test_blank_gw_holding_needs_metadata():
    """B1: a held player missing from the pool must not be silently mislabeled."""
    pool = _pool(1)
    base = pick_squad(pool)["squad"]
    squad = dict(zip(base.player_code, base.price_m))
    gk = int(base[base.position == "GK"].iloc[0].player_code)
    shrunk = pool[pool.player_code != gk]           # the GK blanks this week
    
    # Test that error is raised without metadata
    with pytest.raises(ValueError):
        optimize_gw(shrunk, squad, bank=0.0, free_transfers=1)
    
    # Test that error is avoided with proper metadata
    meta = {gk: {"position": "GK", "team": "T0", "name": "held_gk"}}
    r = optimize_gw(shrunk, squad, bank=0.0, free_transfers=1, holdings_meta=meta)
    new = pool[pool.player_code.isin(r["squad"])]
    assert new.position.value_counts().to_dict() == config.POSITION_QUOTA
```

**Parametrized Tests:**

```python
# From test_legality.py
@pytest.mark.parametrize("seed", range(5))
def test_pick_squad_legal(seed):
    """Test across 5 different random seeds."""
    res = pick_squad(_pool(seed))
    _assert_legal_squad(res["squad"], config.BUDGET)


# From test_leakage.py
@needs_data
def test_minutes_r5_matches_independent_recompute(feat):
    """Verify rolling stat is computed correctly (leakage regression)."""
    raw = pd.read_parquet(RAW)
    season = "2023-24"
    pid = feat.loc[feat.season == season, "player_id"].value_counts().index[0]
    # Test against independent recompute
```

**Test Fixtures with Setup/Teardown:**
- Fixtures use `scope="module"` for expensive data loads (parquet files)
- No teardown needed (files are read-only)
- Fixtures marked with `@pytest.fixture` decorator

## Test Execution Tips

**Run specific test:**
```bash
python -m pytest tests/test_legality.py::test_pick_squad_legal -v
```

**Run tests matching a pattern:**
```bash
python -m pytest tests/ -k "legal" -v
```

**Show print statements:**
```bash
python -m pytest tests/ -s
```

**Stop on first failure:**
```bash
python -m pytest tests/ -x
```

**Debug with pdb on failure:**
```bash
python -m pytest tests/ --pdb
```

---

*Testing analysis: 2026-08-31*
