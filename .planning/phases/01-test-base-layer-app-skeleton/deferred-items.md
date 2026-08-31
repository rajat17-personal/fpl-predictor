# Deferred Items — Phase 01

Items observed during execution that are out of scope for the plan that found them
(scope boundary: only auto-fix issues directly caused by the current task's changes).

## `npm --prefix frontend run typecheck` does not type-check anything

- **Found during:** 01-05 Task 3, while fixing a real `tsc -b`-only error (`process` used
  without `@types/node` in scope) that `npm run typecheck` did not catch.
- **Root cause:** `frontend/tsconfig.json` is a TypeScript "solution" file (`"files": []`,
  only `references`). Plain `tsc --noEmit` against a solution file with `files: []` and no
  own `include` type-checks zero files and exits 0 trivially — it does not traverse
  `references` the way `tsc -b` does. Only `npm run build`'s `tsc -b && vite build` step
  actually type-checks `src/**` today.
- **Impact:** `npm run typecheck` (used as a fast acceptance-criteria gate throughout this
  phase's plans, including this one) currently gives a false "all clear" for real type
  errors that only surface at `npm run build`. This plan's own `process`-typing bug is a
  concrete instance — it silently passed `typecheck` and only failed at `build`.
- **Not fixed here:** predates this plan (present since 01-04, which also relied on
  `npm run typecheck`), and correcting it means either changing `package.json`'s
  `"typecheck"` script to `tsc -b --noEmit` (a build-cache/behavior change beyond this
  plan's file list) or restructuring the tsconfig solution — both out of this plan's scope.
- **Suggested follow-up:** Phase 5 (`CI-01`/`CI-02`, which inherits these `npm --prefix
  frontend` commands verbatim per 01-04's SUMMARY) should change the `typecheck` script to
  actually traverse references (e.g. `tsc -b --noEmit` or an explicit `-p tsconfig.app.json`)
  before wiring it into CI, or every future plan's "typecheck exits 0" acceptance criterion
  is unknowingly a no-op.
