# Deferred Items — quick-260913-1ds

Out-of-scope discoveries found while executing this plan. Per the executor's
scope boundary, these are documented, not fixed, since they are pre-existing
and unrelated to the three files this plan is scoped to
(`tests/test_rl_env.py`, `tests/test_bracket.py`, `tests/test_bracket_deep.py`).

## 1. Pre-existing ruff F401 failures in tests/test_ci_cd_artifacts.py

**Found during:** Direction C verification (`ruff check .`)

**Issue:** `tests/test_ci_cd_artifacts.py` has 3 unused imports (`pathlib`,
`shutil`, `typing.Any`) that fail ruff's F401 check. Confirmed pre-existing
by running `ruff check` against the file's content at `HEAD~2` (before this
plan's two commits) — identical 3 errors present.

**Impact:** `.github/workflows/ci.yml`'s lint job runs the bare `ruff check .`
command, so this file is already failing CI's lint gate today, independent
of this plan's collection-error fix.

**Not fixed here:** Out of this plan's scope guard (only the three named test
files may be modified). Needs a separate quick task or plan to remove the
three unused imports from `tests/test_ci_cd_artifacts.py`.

**RESOLVED by orchestrator at close-out:** commit `1d5e5f1` removed the three
unused imports (ruff --fix; `ruff check .` now clean repo-wide; the file's 32
tests still pass). No separate task needed.
