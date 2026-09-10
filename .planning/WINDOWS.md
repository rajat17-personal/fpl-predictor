---
schema_version: 1
open_count: 3
waived_count: 0
fixed_count: 2
total_count: 5
last_updated: 2026-09-10T18:26:27.667Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | todo | frontend/package.json |  | npm run typecheck (tsc --noEmit against the solution tsconfig) type-checks 0 files; only 'npm run build' (tsc -b) actually catches type errors — fix before CI-01/CI-02 wire this script in | open |  | 2026-08-31T17:39:56.032Z |  |
| 2 | 04 | deviation | frontend/src/components/pitch/Pitch.tsx |  | Ghost card and outgoing label land in different pitch rows when the rating's best_move sells a benched (not starting) player -- see .planning/phases/04-e2e-regression-suite/deferred-items.md | fixed |  | 2026-09-04T02:36:58.055Z | 2026-09-04T05:54:57.907Z |
| 3 | 05 | deviation | .planning/phases/05-container-build-ci-pipeline/05-PATTERNS.md | 141 | Personal email <redacted-personal-email> present in a planning doc (quoted as historical/before-fix context, not live infra); out of this task's file scope (.gitignore, installer only) — left for a human decision before push (D-16), surfaced at the 05-05 push checkpoint. | fixed |  | 2026-09-04T13:46:43.491Z | 2026-09-04T14:27:53.257Z |
| 4 | 10 | deviation | models/bracket/gate.py |  | Plan 10-10 Task 3's <verify> checked run_gate's train_seasons against backtest.walk_forward.TEST_SEASONS (6 rolling walk-forward seasons), which legitimately overlaps config.TRAIN_SEASONS by design; implemented against config.TEST_SEASONS (the real held-out season) instead, per T-10-10-03's actual intent | open |  | 2026-09-10T18:26:20.716Z |  |
| 5 | 10 | deviation | requirements-experiments.txt |  | Executing this plan's literal install mechanism (uv pip sync requirements-experiments.txt --require-hashes) treated the WHOLE shared conda env python314 as its sync target and removed everything not in that one small lockfile -- including project-critical packages (torch, lightgbm, sklearn, fastapi, pulp) and unrelated non-project packages (jupyter/transformers/yt-dlp/wordcloud/etc). Recovered project deps via non-destructive uv pip install -r <file> --require-hashes against requirements.txt/requirements-dev.txt/requirements-rl.txt/requirements-experiments.txt plus one ad-hoc lxml reinstall; full pytest suite confirmed green after recovery. Non-project packages outside any lockfile are NOT recoverable to their exact prior versions. Future installs into this shared env must use 'uv pip install -r <file> --require-hashes', never '--sync'. | open |  | 2026-09-10T18:26:27.667Z |  |

````json
[
  {
    "id": 1,
    "kind": "todo",
    "phase": "01",
    "file": "frontend/package.json",
    "line": null,
    "description": "npm run typecheck (tsc --noEmit against the solution tsconfig) type-checks 0 files; only 'npm run build' (tsc -b) actually catches type errors — fix before CI-01/CI-02 wire this script in",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-31T17:39:56.032Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "04",
    "file": "frontend/src/components/pitch/Pitch.tsx",
    "line": null,
    "description": "Ghost card and outgoing label land in different pitch rows when the rating's best_move sells a benched (not starting) player -- see .planning/phases/04-e2e-regression-suite/deferred-items.md",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-04T02:36:58.055Z",
    "resolved_at": "2026-09-04T05:54:57.907Z"
  },
  {
    "id": 3,
    "kind": "deviation",
    "phase": "05",
    "file": ".planning/phases/05-container-build-ci-pipeline/05-PATTERNS.md",
    "line": 141,
    "description": "Personal email <redacted-personal-email> present in a planning doc (quoted as historical/before-fix context, not live infra); out of this task's file scope (.gitignore, installer only) — left for a human decision before push (D-16), surfaced at the 05-05 push checkpoint.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-04T13:46:43.491Z",
    "resolved_at": "2026-09-04T14:27:53.257Z"
  },
  {
    "id": 4,
    "kind": "deviation",
    "phase": "10",
    "file": "models/bracket/gate.py",
    "line": null,
    "description": "Plan 10-10 Task 3's <verify> checked run_gate's train_seasons against backtest.walk_forward.TEST_SEASONS (6 rolling walk-forward seasons), which legitimately overlaps config.TRAIN_SEASONS by design; implemented against config.TEST_SEASONS (the real held-out season) instead, per T-10-10-03's actual intent",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-10T18:26:20.716Z",
    "resolved_at": null
  },
  {
    "id": 5,
    "kind": "deviation",
    "phase": "10",
    "file": "requirements-experiments.txt",
    "line": null,
    "description": "Executing this plan's literal install mechanism (uv pip sync requirements-experiments.txt --require-hashes) treated the WHOLE shared conda env python314 as its sync target and removed everything not in that one small lockfile -- including project-critical packages (torch, lightgbm, sklearn, fastapi, pulp) and unrelated non-project packages (jupyter/transformers/yt-dlp/wordcloud/etc). Recovered project deps via non-destructive uv pip install -r <file> --require-hashes against requirements.txt/requirements-dev.txt/requirements-rl.txt/requirements-experiments.txt plus one ad-hoc lxml reinstall; full pytest suite confirmed green after recovery. Non-project packages outside any lockfile are NOT recoverable to their exact prior versions. Future installs into this shared env must use 'uv pip install -r <file> --require-hashes', never '--sync'.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-10T18:26:27.667Z",
    "resolved_at": null
  }
]
````
