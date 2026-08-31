---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-08-31T17:39:56.032Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | todo | frontend/package.json |  | npm run typecheck (tsc --noEmit against the solution tsconfig) type-checks 0 files; only 'npm run build' (tsc -b) actually catches type errors — fix before CI-01/CI-02 wire this script in | open |  | 2026-08-31T17:39:56.032Z |  |

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
  }
]
````
