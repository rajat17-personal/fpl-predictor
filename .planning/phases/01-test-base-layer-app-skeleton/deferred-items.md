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

## Visual assertion for G-01-3 header containment — handed to Phase 4 (E2E-01)

- **Found during:** 01-06 Task 2, closing UAT gap `G-01-3` (nav brand+nav rendering full-bleed
  on wide desktop viewports instead of contained at 68rem like `<main>` and the footer).
- **Root cause:** `frontend/src/components/PageShell.tsx`'s header was the only chrome section
  missing the `mx-auto max-w-[68rem]` containment `<main>` and the footer already had — see the
  full diagnosis at `.planning/debug/nav-text-not-responsive.md`.
- **Impact:** The fix shipped in plan 01-06 — the header now nests brand+nav+meta-slot inside a
  `mx-auto w-full max-w-[68rem] px-4` wrapper, and the footer's paragraph gained the matching
  `w-full px-4` — and is regression-locked at the class-token level by
  `frontend/src/components/PageShell.test.tsx`. What that test **cannot** prove is real pixel
  geometry: jsdom has no layout engine, so it can assert the right Tailwind classes are present
  but not that the rendered header is actually ≤1088px wide and horizontally centered at a wide
  viewport. Only a real browser can measure that.
- **Not fixed here:** out of scope for a vitest/jsdom unit test — this requires Phase 4's
  Playwright suite (`E2E-01`), which runs in a real browser with a layout engine.
- **Suggested follow-up:** Phase 4 (E2E-01) must set a 1720px-wide viewport and assert: (1) the
  header's inner content wrapper's bounding-box width is at most 1088px (68rem), (2) that
  wrapper is horizontally centered in the viewport, and (3) its bounding-box x-range matches the
  `<main>` element's content box x-range. References: gap `G-01-3` and the full diagnosis at
  `.planning/debug/nav-text-not-responsive.md`.
