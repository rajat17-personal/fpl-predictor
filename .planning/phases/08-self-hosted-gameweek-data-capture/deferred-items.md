# Phase 8 — Deferred Items

Out-of-scope issues discovered during execution, not fixed per the deviation scope
boundary (only issues directly caused by the current task's changes are auto-fixed).

## Plan 08-01

- **`tests/test_ci_cd_artifacts.py`: 3 pre-existing ruff F401 unused-import findings**
  (`pathlib`, `shutil`, `typing.Any`) at lines 16, 19, 22. Confirmed pre-existing by
  checking out the file at HEAD (commit `33067a7`, unrelated to this plan) before any
  08-01 change — `ruff check .` reports the same 3 findings against that unmodified
  copy. Not in this plan's `files_modified` list; left unfixed per the scope boundary.
  `ruff check .` naming `data/gw_capture.py` or `tests/test_gw_capture.py` (this plan's
  own gate) reports zero findings.
