---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 2
total_count: 3
last_updated: 2026-09-04T14:27:53.257Z
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
  }
]
````
