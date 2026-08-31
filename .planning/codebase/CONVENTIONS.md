# Coding Conventions

**Analysis Date:** 2026-08-31

## Naming Patterns

**Files:**
- `snake_case.py` for modules (e.g., `data/ingest.py`, `models/train.py`, `optimize/squad_ilp.py`)
- Test files: `test_*.py` (e.g., `tests/test_legality.py`, `tests/test_leakage.py`)
- No file suffixes beyond `.py` for Python modules

**Functions:**
- `camelCase` for public functions in JavaScript modules (`detectApiBase()`, `loadJSON()`, `makeSortable()`)
- `snake_case` for Python functions: `add_features()`, `train_predict()`, `fetch_vaastav_season()`
- Private/internal functions: prefix with underscore (`_download()`, `_roll()`, `_pool()`, `_assert_legal_squad()`)

**Variables:**
- `snake_case` for all Python variables: `horizon_sum`, `sell_values`, `xp_med`, `total_points`
- `camelCase` for JavaScript variables: `apiBase`, `numLeaves`, `stateKey`
- Constants in ALL_CAPS in Python: `BUDGET = 100.0`, `SQUAD_SIZE = 15`, `MAX_PER_CLUB = 3`, `SEASONS = [...]`
- Local constants in ALL_CAPS: `HEADERS`, `TIMEOUT`, `ARTIFACTS`, `_EXCLUDE`

**Types:**
- Python: Use `from __future__ import annotations` for forward-compatible type hints (see `data/ingest.py:11`, `models/train.py:20`)
- Type hints on function signatures: `def add_features(df: pd.DataFrame) -> pd.DataFrame:`
- Union types use pipe syntax: `dict | None`, `list[str]`
- No type hints in JS (vanilla ES6 modules)

## Code Style

**Formatting:**
- Python: 4-space indentation (standard Python)
- JS: 2-space indentation (see `web/assets/app.js`)
- Line length: appears to be ~90-100 characters in Python
- No explicit linter/formatter config detected (no `.flake8`, `.pylintrc`, `pyproject.toml` config)

**Linting:**
- Not configured (no `.eslintrc`, `.flake8`, or linting config files present)
- Code follows implicit conventions: clean imports, type hints, docstrings

## Import Organization

**Order (Python):**
1. `from __future__ import annotations` (always first if present)
2. Standard library: `import sys`, `import json`, `import time`, `from pathlib import Path`
3. Third-party packages: `import pandas as pd`, `import numpy as np`, `import requests`, `from lightgbm import LGBMClassifier`
4. Project modules: `import config`, `from optimize.squad_ilp import pick_squad`

**Order (JavaScript):**
- `export` statements for public API at module level
- Helper functions and state below

**Path Aliases:**
- No path aliases configured; imports use relative paths within the project
- Implicit: `import config` works because `config.py` is at project root
- Submodules imported as: `from data.ingest import fetch_vaastav_season`, `from optimize.transfers import optimize_gw`

## Error Handling

**Patterns:**
- **HTTP errors:** `resp.raise_for_status()` to throw on non-2xx, then catch `requests.HTTPError` and `requests.RequestException` (see `data/ingest.py:28-44`)
- **Optional enrichment:** `try/except Exception` when a data source is optional (see `data/build_table.py` for odds/fbref)
- **Solver failures:** `raise RuntimeError(f"multi-period solve: {pulp.LpStatus[m.status]}")` (see `optimize/multi_period.py`)
- **Parameter validation:** `raise ValueError(f"objective '{objective}' unsupported...")` (see `models/train.py`)
- **User-facing CLI errors:** `raise SystemExit("Missing player_gw.parquet. Run `python -m data.build_table`.")` (see `features/engineer.py:110`)
- **Test assertions:** Direct `pytest.raises(ValueError)` for expected exceptions (see `tests/test_legality.py:92`)

## Logging

**Framework:** `print()` only — no logging library (no `logging` imports found)

**Patterns:**
- Print status/progress with context tags: `print(f"  saved    {dest.relative_to(config.ROOT)}")` (see `data/ingest.py:48`)
- Module-tagged info: `print(f"[price] {message}")`, `print(f"[odds] live fetch failed...")` (see `data/live_odds.py`, `models/price.py`)
- Structured reporting: `print("\n=== features summary ===")` followed by organized output (see `features/engineer.py:89-104`)
- Indented status for hierarchical info: `print(f"  cached   {dest.relative_to(config.ROOT)}")` (nested under parent operation)
- When to print: status messages, progress counters, warnings about optional data, final artifact paths

## Comments

**When to Comment:**
- Module-level docstring: Always. Explains purpose, design decisions, and usage (see every file)
- Function/class docstrings: Always. Single-line summary + details if complex (see `data/ingest.py:53-74`)
- Inline comments: Explain *why*, not what. Used sparingly (see `models/train.py:39` — "FPL's own prediction")
- Design notes: Multi-line at module top inside docstring (see `api/main.py:10-16`)

**JSDoc/TSDoc:**
- Not used. JavaScript uses inline comments only (see `web/assets/app.js:1-7`)
- Python docstrings explain algorithm/constraints inline (see `backtest/season.py`, `features/engineer.py:5-16`)

## Function Design

**Size:** 
- Functions range 10-50 lines typically
- Longer functions (50-100+) are algorithmic (e.g., optimizer MILP setup in `optimize/multi_period.py`)
- Private helpers extracted for reusability and clarity

**Parameters:**
- Named, typed: `def train_predict(df: pd.DataFrame, train_seasons, val_season, test_seasons, params: dict | None = None, objectives: dict | None = None, minutes_model: str = "binary", calibrate: bool = False):`
- Keyword-only args after `*` where they denote options: `def fetch_vaastav_season(season: str, *, force: bool = False)`
- Defaults for optional enrichment/behavior

**Return Values:**
- Single values for simple operations
- Dicts for complex results: `return {"squad": ..., "bank": ..., "transfers": ...}` (optimizer output)
- Dicts with optional fields: `{"p10": ..., "p90": ...}` (intervals)
- None for side-effect operations (e.g., `summarise()`)
- Tuple for multi-value return when order matters (rare)

## Module Design

**Exports:**
- Python: No explicit `__all__` found; public API inferred from function/class names (those not prefixed with `_`)
- JavaScript: `export` keyword for public API (see `web/assets/app.js:3,9,24,30,44,57,81,91`)

**Barrel Files:**
- Used minimally; most `__init__.py` are empty (e.g., `data/__init__.py`, `features/__init__.py`, `api/__init__.py`)
- No re-exports; submodules imported directly: `from data.ingest import ...`

## CLI Entry Points

**Pattern:**
- Modules are executable via `python -m module_name`
- Main function at module bottom: `def main() -> int:` (see `features/engineer.py:107-122`)
- Exit via `sys.exit(main())` or `if __name__ == "__main__": sys.exit(main())`
- Docstring at module top documents usage: `python -m data.ingest`, `python -m models.train` (see every module's docstring)
- argparse for CLI args: `ap = argparse.ArgumentParser()`, `ap.add_argument(...)` (see `predict/live.py`)

---

*Convention analysis: 2026-08-31*
