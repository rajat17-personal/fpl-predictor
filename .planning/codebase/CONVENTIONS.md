---
last_mapped_commit: 382338e2c164a4433cd73cdbb12ffc9be2621493
---

# Coding Conventions

**Analysis Date:** 2026-09-11

## Naming Patterns

**Files:**
- Python: `snake_case.py` for modules (e.g., `data/ingest.py`, `models/train.py`, `optimize/squad_ilp.py`)
- TypeScript/React: PascalCase for components (e.g., `frontend/src/components/ThemeToggle.tsx`), camelCase for utilities (e.g., `frontend/src/lib/format.ts`)
- Test files: 
  - Python: `test_*.py` (e.g., `test_legality.py`, `test_leakage.py`, `test_bracket.py`, `test_availability.py`)
  - TypeScript/React: `*.test.ts`, `*.test.tsx` (e.g., `frontend/src/lib/format.test.ts`, `frontend/src/components/ThemeToggle.test.tsx`)
  - Playwright E2E: `*.spec.ts` (e.g., `e2e/specs/xp-table.spec.ts`, `e2e/specs/team-solver.spec.ts`)

**Functions:**
- Python:
  - Public: `snake_case` (e.g., `add_features()`, `train_predict()`, `fetch_vaastav_season()`)
  - Private/internal: `_snake_case` prefix (e.g., `_download()`, `_roll()`, `_pool()`, `_assert_legal_squad()`)
- TypeScript/React:
  - Public: `camelCase` (e.g., `resolveTheme()`, `readStoredChoice()`, `fetchJson()`)
  - React hooks: `useCamelCase` (e.g., `useTheme()`, `useSortable()`, `usePageMeta()`)
  - React components: `PascalCase` (e.g., `ThemeToggle`, `XpTable`, `PageShell`)
  - Private/internal: `camelCase` or `_camelCase` prefix (e.g., `getMediaQueryList()`, `applyResolvedTheme()`)
  - Playwright helpers: `camelCase` (e.g., `gotoReady()`, `watchOrigin()`, `openCardMenu()`)

**Variables:**
- Python: `snake_case` (e.g., `horizon_sum`, `sell_values`, `xp_med`, `total_points`)
- TypeScript/React: `camelCase` (e.g., `apiBase`, `numLeaves`, `stateKey`, `rows`, `selectedBy`)
- Constants:
  - Python ALL_CAPS: `BUDGET = 100.0`, `SQUAD_SIZE = 15`, `MAX_PER_CLUB = 3`, `SEASONS = [...]`
  - TypeScript/React PascalCase or ALL_CAPS: `THEME_STORAGE_KEY = "fpl-theme"`, `EN_DASH = "–"`, `NUMERIC_KEYS = new Set(...)`
  - Playwright constants: ALL_CAPS (e.g., `FROZEN_NOW`, `GW`, `ENTRY`, `BLANK_CLUBS = ["ARS", "AVL", ...]`)

**Types:**
- Python:
  - Use `from __future__ import annotations` for forward-compatible type hints (see `data/ingest.py:11`, `models/train.py:20`)
  - Type hints on function signatures: `def add_features(df: pd.DataFrame) -> pd.DataFrame:`
  - Union types use pipe syntax: `dict | None`, `list[str]`
- TypeScript/React:
  - Type definitions with `type` keyword (e.g., `type SortKey = "position" | "name" | "team_short"`)
  - Interface for objects (e.g., `interface CaptainRow { player_code: number; ... }`)
  - Exported types at module top: `export type ThemeChoice = "light" | "dark" | "system"`
  - Generic types: `Record<string, T>`, `{ [key: string]: value }`

## Code Style

**Formatting:**
- Python: 4-space indentation (standard Python), 100-character line length target (enforced by `ruff.toml`)
- TypeScript/React: 2-space indentation (enforced by Vite/Prettier)
- Playwright: 2-space indentation
- Line length: 100 characters target in Python (per `ruff.toml:line-length = 100`), 80-100 in TypeScript

**Linting:**
- Python: `ruff` configured in `ruff.toml` (not `pyproject.toml` — repo has no packaging metadata)
  - Target: Python 3.14
  - Rules: Explicit default selection `["E4", "E7", "E9", "F"]` (pycodestyle errors, Pyflakes)
  - Config: `ruff.toml` at repo root
  - Excludes: `data/raw`, `data/processed`, `data/snapshots`, `models/artifacts`, `frontend`, `web`, `.planning`, `e2e/node_modules`, `e2e/fixtures`, `e2e/playwright-report`, `e2e/test-results`
  - CI gate: `ruff check .` (see `.github/workflows/ci.yml`)
- TypeScript/React: TypeScript compiler in strict mode (`tsc -b` with project references)
  - No ESLint config detected; code follows implicit conventions
- Playwright: No linting configured; code follows implicit conventions

## Import Organization

**Order (Python):**
1. `from __future__ import annotations` (always first if present)
2. Standard library: `import sys`, `import json`, `import time`, `from pathlib import Path`
3. Third-party packages: `import pandas as pd`, `import numpy as np`, `import requests`, `from lightgbm import LGBMClassifier`
4. Project modules: `import config`, `from optimize.squad_ilp import pick_squad`

**Order (TypeScript/React):**
1. React/framework imports: `import { useState } from "react"`, `import { useQuery } from "@tanstack/react-query"`
2. Local type imports: `import type { CaptainRow, XpRow } from "../lib/api"`
3. Component/utility imports: `import { fetchJson } from "../lib/api"`, `import { Spinner } from "../components/Spinner"`
4. Style imports (if any): `import "./index.css"`

**Order (Playwright):**
1. Framework imports: `import { test, expect, type Page } from "@playwright/test"`
2. Helper imports: `import { gotoReady, watchOrigin, FROZEN_NOW } from "../helpers/page"`
3. Test fixtures: `import fixtureData from "../fixtures/v1/normal/api/capture.json"`

**Path Aliases:**
- Python: No path aliases; imports use absolute from project root: `import config`, `from data.ingest import fetch_vaastav_season`
- TypeScript/React: Relative paths used (e.g., `import { fetchJson } from "../lib/api"`); no `jsconfig.json` path aliases
- Playwright: Relative paths with `..` navigation (e.g., `import { gotoReady } from "../helpers/page"`)

## Error Handling

**Python Patterns:**
- **HTTP errors:** `resp.raise_for_status()` to throw on non-2xx, then catch `requests.HTTPError` and `requests.RequestException` (see `data/ingest.py:28-44`)
- **Optional enrichment:** `try/except Exception` when a data source is optional (see `data/build_table.py` for odds/fbref)
- **Solver failures:** `raise RuntimeError(f"multi-period solve: {pulp.LpStatus[m.status]}")` (see `optimize/multi_period.py`)
- **Parameter validation:** `raise ValueError(f"objective '{objective}' unsupported...")` (see `models/train.py`)
- **User-facing CLI errors:** `raise SystemExit("Missing player_gw.parquet. Run `python -m data.build_table`.")` (see `features/engineer.py:110`)
- **Test assertions:** Direct `pytest.raises(ValueError)` for expected exceptions (see `tests/test_legality.py:92`)

**TypeScript/React Patterns:**
- **Promise errors:** `fetch()` with `.ok` check (see `frontend/src/routes/XpTable.test.tsx:25-30`)
- **Try/catch:** For localStorage access and optional features (see `frontend/src/lib/theme.ts:21-38`)
- **Graceful degradation:** Return null/undefined or default value on error; no throwing from event handlers (see `getMediaQueryList()` returns null on error)

**Playwright Patterns:**
- **Navigation errors:** Assertions on page state after navigation (no explicit error throws)
- **Timeout handling:** Playwright built-in timeout (30 seconds per test, 10 seconds per assertion)
- **Stale element retries:** Testing Library queries auto-retry; explicit `.toBeVisible()` checks for timing

## Logging

**Python:**
- Framework: `print()` only — no logging library (no `logging` imports found)
- Patterns:
  - Print status/progress with context tags: `print(f"  saved    {dest.relative_to(config.ROOT)}")` (see `data/ingest.py:48`)
  - Module-tagged info: `print(f"[price] {message}")`, `print(f"[odds] live fetch failed...")` (see `data/live_odds.py`, `models/price.py`)
  - Structured reporting: `print("\n=== features summary ===")` followed by organized output (see `features/engineer.py:89-104`)
  - Indented status for hierarchical info: `print(f"  cached   {dest.relative_to(config.ROOT)}")` (nested under parent operation)
  - When to print: status messages, progress counters, warnings about optional data, final artifact paths

**TypeScript/React:**
- Framework: `console` object (no logging library)
- Rarely used in component code (prefer error boundaries, test assertions)
- When used: `console.error()` for unrecoverable errors only; never `console.log()` in production code

**Playwright:**
- No logging in specs; use `--reporter=verbose` to see test execution details
- CLI output and exit codes convey all necessary info (`npx playwright test` or `npm run test` from `e2e/`)

## Comments

**Python:**
- Module-level docstring: Always. Explains purpose, design decisions, and usage (see every file)
- Function/class docstrings: Always. Single-line summary + details if complex (see `data/ingest.py:53-74`)
- Inline comments: Explain *why*, not what. Used sparingly (see `models/train.py:39` — "FPL's own prediction")
- Design notes: Multi-line at module top inside docstring (see `api/main.py:10-16`)

**TypeScript/React:**
- Module-level comment: Explain design decisions and constraints (see `frontend/src/lib/format.ts:1-12`)
- Function comments: Explain subtle behavior or non-obvious decisions (see `frontend/src/lib/theme.ts:13`, `frontend/src/lib/theme.ts:41`, `frontend/src/lib/theme.ts:68-69`)
- Inline comments: Short, explain edge cases (see `frontend/src/lib/theme.ts:85-89`)
- Comments document the coupling between files (e.g., frontend/src/lib/theme.ts mirrors frontend/index.html's inline script)
- No JSDoc/TSDoc; vanilla comments suffice

**Playwright:**
- Multi-line docstring (comment block) at test top: Explain WHY the test matters, what it validates, and fixture/data dependencies (see `e2e/specs/xp-table.spec.ts:4-33`)
- Hand-derived expected values: Always explain WHERE the literal string/number came from (e.g., "row 1 hand-derived from e2e/fixtures/v1/normal/web-data/xp_table.json")
- Inline comments: Explain timing/sequencing rules and concurrent operation safeguards (see `e2e/helpers/page.ts:20-31`)
- Never comment what code does (e.g., `// click the button` — Playwright method name says it all); comment WHY ordering matters

## Function Design

**Python:**
- Size: Functions range 10-50 lines typically; longer functions (50-100+) are algorithmic (e.g., optimizer MILP setup in `optimize/multi_period.py`)
- Parameters: Named, typed; keyword-only args after `*` for options (e.g., `def fetch_vaastav_season(season: str, *, force: bool = False)`)
- Return values: Single values for simple ops, dicts for complex results (`{"squad": ..., "bank": ..., "transfers": ...}`), None for side-effect operations

**TypeScript/React:**
- Hooks: Small, focused (under 50 lines); composed via `useCallback`, `useState`, `useEffect`
- Components: Stateless when possible; state lifted to hooks or context
- Functions: Pure functions for utilities (see `format.ts` formatting helpers, `sortable.ts` sorting logic)
- Return types: Always annotated (e.g., `function resolveTheme(...): ResolvedTheme { ... }`)
- Parameters: Destructured when passing multiple related values (e.g., React component props)

**Playwright:**
- Helper functions: Reusable across specs (e.g., `gotoReady()`, `openCardMenu()`, `cardActionsNames()`)
- Async/await: All navigation and query functions are async; always `await` before assertion
- Test structure: Describe blocks group related tests; each `it()` is independent (no cross-test state)

## Module Design

**Python:**
- Exports: No explicit `__all__`; public API inferred from function/class names (those not prefixed with `_`)
- Barrel files: Used minimally; most `__init__.py` are empty (e.g., `data/__init__.py`, `features/__init__.py`, `api/__init__.py`)
- No re-exports; submodules imported directly: `from data.ingest import ...`

**TypeScript/React:**
- Exports: `export` keyword for public API (functions, components, types)
- Each file exports one component or one utility module
- No barrel files (`index.ts` re-exports); imports use explicit paths: `import { fetchJson } from "../lib/api"` not `from "../lib"`
- Types exported alongside functions: `export type XpRow = { ... }; export function fetchXpTable(...) { ... }`

**Playwright:**
- Helpers as utility modules: `e2e/helpers/page.ts` exports reusable functions (`gotoReady`, `watchOrigin`, constants `FROZEN_NOW`, `GW`)
- No barrel files; specs import directly from helpers
- Fixtures as JSON files: `e2e/fixtures/v1/{normal,blank,dgw}/` directory structure mirrors API contract structure

## CLI Entry Points (Python Only)

**Pattern:**
- Modules are executable via `python -m module_name`
- Main function at module bottom: `def main() -> int:` (see `features/engineer.py:107-122`)
- Exit via `sys.exit(main())` or `if __name__ == "__main__": sys.exit(main())`
- Docstring at module top documents usage: `python -m data.ingest`, `python -m models.train` (see every module's docstring)
- argparse for CLI args: `ap = argparse.ArgumentParser()`, `ap.add_argument(...)` (see `predict/live.py`)

---

*Convention analysis: 2026-09-11*
