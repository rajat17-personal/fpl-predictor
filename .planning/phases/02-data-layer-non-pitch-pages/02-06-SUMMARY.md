---
phase: 02-data-layer-non-pitch-pages
plan: 06
subsystem: ui
tags: [react, tanstack-query, react-markdown, vitest, parity, differentials, methodology]

# Dependency graph
requires:
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-01's shared parity utilities (lib/bandCell.ts + components/BandCell.tsx, lib/statusFlag.tsx, lib/format.ts primitives) and the full web/data/*.json TypeScript contract in lib/api.ts"
  - phase: 02-data-layer-non-pitch-pages
    provides: "02-02's human-approved react-markdown@10.1.0 install and the PARITY-DEVIATIONS.md ledger (entry 6 pre-seeded for this plan's footer-placement decision)"
provides:
  - "Real, fully-ported /differentials route: ownership slider (min 1/max 25/step 1, default 10), R39 filter+slice, R40's maxHi floor of 1 kept structurally distinct from the xP table's own un-floored maxHi (R11), R41's un-guarded Own %"
  - "Real, fully-ported /methodology route: verbatim vanilla prose bundled at build time via frontend/src/content/methodology.md, rendered through react-markdown with no raw-HTML sink anywhere in frontend/src"
  - "frontend/src/vite-env.d.ts — the Vite client types reference every future ?raw/?url import in this project can now rely on"
affects: [07]

# Actuals (#2632)
actuals:
  tokens: 6350
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Differentials shares the xP table's exact TanStack Query key (['xp_table']) so the two routes read one cache entry — a second visit to either page after the first triggers no additional fetch"
    - "diffOwnershipCell() is exported specifically so R41's null-ownership 'no en-dash fallback' case (which the page's own filter always excludes from the rendered set) stays directly unit-testable without contriving an unreachable render path"
    - "Methodology is the one route in the phase with zero query/loading/error state — content arrives via a Vite ?raw import resolved at build time, so its route component is a pure render with no useQuery call at all"
    - "react-markdown's components prop maps h1/h2/p/ul/li/a/strong onto the existing four-role typography tokens, keeping the markdown-to-token mapping in one place rather than scattering token classes across a wrapper's CSS cascade"

key-files:
  created:
    - frontend/src/routes/Differentials.test.tsx
    - frontend/src/routes/Methodology.test.tsx
    - frontend/src/content/methodology.md
    - frontend/src/vite-env.d.ts
  modified:
    - frontend/src/routes/Differentials.tsx
    - frontend/src/routes/Methodology.tsx

key-decisions:
  - "Exported diffOwnershipCell(ownership) as a standalone, directly-testable function rather than inlining the un-guarded String(ownership?.toFixed(1)) expression — the null-ownership case it covers (R41) can never appear in the page's own rendered output (the R39 filter excludes it at every cap), so the acceptance criterion is proven against the function in isolation instead of a rendered row."
  - "Styled react-markdown's output via its components prop (an explicit tag->token-class map) rather than a wrapper CSS-cascade class, so the markdown-to-typography-token mapping is declared once in Methodology.tsx and does not depend on an untracked global stylesheet rule."

patterns-established: []

requirements-completed: [UI-05]

coverage:
  - id: D1
    description: "/differentials renders from /data/xp_table.json using the same TanStack Query key as the xP table (no second export file, shared cache entry), filtered by R39's (ownership ?? 100) <= cap && status === 'a' predicate and sliced to 30 rows."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#at cap 10, includes an ownership-8 available player and excludes an ownership-12 player and an ownership-8 unavailable player"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#excludes a row with null ownership even at the maximum cap of 25"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#renders exactly 30 rows from a 40-row qualifying source (R39 slice)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The ownership slider (min 1/max 25/step 1, default 10) re-filters synchronously against already-loaded data with no additional fetch, and its live label reflects the current cap as a percentage."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#renders the range input with min=1 max=25 step=1 and an initial value of 10"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#moving the slider from 10 to 25 widens the rendered set with no additional fetch"
        status: pass
    human_judgment: false
  - id: D3
    description: "maxHi = Math.max(1, ...rows.map(r => r.p90 ?? r.xp)) — the floor of 1 is structurally distinct from the xP table's own un-floored maxHi (R11); verified both by the grep-level source-distinctness gate and by a rendering assertion that proves the floor actually changes the band's scaling denominator."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#scales the band point marker against a maxHi floor of 1 when every qualifying row's p90 is below 1 (R40)"
        status: pass
      - kind: other
        ref: "grep -q 'Math.max(1' frontend/src/routes/Differentials.tsx && ! grep -q 'Math.max(1' frontend/src/routes/XpTable.tsx (plan Task 1 automated verify: MAXHI FORMULAS STAY DISTINCT)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Own % renders to one decimal with no en-dash fallback (R41), matching the Captains sub-table and diverging from the xP table's own Own % column; the differentials table has no interactive elements (not sortable)."
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "frontend/src/routes/Differentials.test.tsx#diffOwnershipCell — renders the literal 'undefined' text for a null ownership / renders one decimal place for a real ownership value"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#has no interactive elements within the differentials table (not sortable)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A cap that matches zero rows renders the page-specific 'No players under {cap}% ownership right now' heading with 'Try raising the slider.' body, distinct from the shared EmptyState (which still covers a genuinely zero-row source)."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#renders the page-specific zero-match heading and body when the cap matches nothing"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Differentials.test.tsx#renders the shared EmptyState for a zero-row source (distinct from the cap zero-match heading)"
        status: pass
    human_judgment: false
  - id: D6
    description: "/methodology renders its content from frontend/src/content/methodology.md, imported at build time via Vite's ?raw suffix — no runtime fetch, no loading or error state, no Spinner or Retry control under any condition."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Methodology.test.tsx#renders no spinner and no Retry control on this page under any condition"
        status: pass
    human_judgment: false
  - id: D7
    description: "The markdown renders through react-markdown into real React elements in the documented section order (Prediction, Uncertainty, Selection, The receipts, Honesty policy), with the four receipt figures and their source captions intact and the honesty policy as a three-item bullet list."
    requirement: "UI-05"
    verification:
      - kind: integration
        ref: "frontend/src/routes/Methodology.test.tsx#renders the five h2 sections in the documented order"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Methodology.test.tsx#renders the four receipt figures with their exact strings and source captions"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Methodology.test.tsx#renders the honesty policy as exactly three list items"
        status: pass
      - kind: other
        ref: "grep -q '0.87 vs FPL 1.07' && grep -q '0.74 vs FPL 0.30' && grep -q '2260' && grep -q '+102' frontend/src/content/methodology.md (plan Task 2 automated verify: RECEIPTS INTACT)"
        status: pass
    human_judgment: false
  - id: D8
    description: "No raw-HTML injection path exists anywhere in frontend/src (no React raw-markup escape-hatch prop, no rehype-raw plugin); script-shaped markdown text renders as escaped visible text, never as a live element; the data-source credit line is the final paragraph of the page body while the shared PageShell footer wording is unchanged."
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "! grep -rq 'SetInnerHTML' frontend/src (plan Task 2 automated verify: NO RAW HTML SINK)"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Methodology.test.tsx#renders script-shaped markdown text as escaped visible text, never as a live element"
        status: pass
      - kind: integration
        ref: "frontend/src/routes/Methodology.test.tsx#renders the data-source credit line as the final paragraph of the page body, leaving the PageShell footer unchanged"
        status: pass
    human_judgment: false
  - id: D9
    description: "Full frontend Vitest suite, typecheck, and the production build-purity gate all pass with this plan's changes in place — all seven ported pages in the phase are now green together."
    verification:
      - kind: other
        ref: "npm --prefix frontend run test (169/169 passed)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run typecheck (exit 0)"
        status: pass
      - kind: other
        ref: "bash scripts/verify_frontend_build.sh (BUILD PURITY OK)"
        status: pass
    human_judgment: false
  - id: D10
    description: "Manual spot check: visiting /differentials and dragging the slider across its full range shows the band widths rescale sensibly at low caps where the floor bites."
    verification: []
    human_judgment: true
    rationale: "The plan's <verification> step 5 is an explicit non-gating manual spot check — Vitest's jsdom environment has no layout/paint pipeline to assert the band track visually rescales sensibly; the underlying scaling math is proven correct by the automated maxHi-floor test (D3), but only a human eye can confirm it reads well at low caps in a real browser."

duration: 25min
completed: 2026-09-01
status: complete
---

# Phase 2 Plan 6: Differentials & Methodology Parity Summary

**Ports `/differentials` (ownership slider, R39-R41's filter/slice/floor/no-fallback rules, sharing the xP table's query cache) and `/methodology` (verbatim vanilla prose bundled at build time via a `?raw` markdown import, rendered through `react-markdown` with no raw-HTML sink anywhere in the app), closing out UI-05 and the seven-page scope of this phase.**

## Performance

- **Duration:** 25 min (approx.)
- **Started:** 2026-09-01T15:00:00Z (approx.)
- **Completed:** 2026-09-01T15:25:00Z (approx.)
- **Tasks:** 2 (both `tdd="true"`)
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- Replaced the `/differentials` placeholder with a real route: the ownership slider (min 1/max 25/step 1, default 10) drives a synchronous local re-filter over the xP table's shared TanStack Query cache entry, applying R39's `(ownership ?? 100) <= cap && status === "a"` predicate and a 30-row slice
- Kept R40's `maxHi = Math.max(1, ...)` floor of 1 structurally distinct from the xP table's own un-floored `maxHi` (R11) — verified both by a source-level grep gate and a rendering test that proves the floor actually changes the band's scaling denominator
- Ported R41's un-guarded Own % (`diffOwnershipCell`, no en-dash fallback), matching the Captains sub-table and diverging from the xP table's own Own % column
- Replaced the `/methodology` placeholder with a real route: `frontend/src/content/methodology.md` is a verbatim port of `web/methodology.html` lines 30-77, imported at build time via Vite's `?raw` suffix and rendered through `react-markdown`'s default component (no `dangerouslySetInnerHTML`, no `rehype-raw` plugin) — the one page in the phase with no runtime fetch, no loading/error state
- All four published accuracy figures (Fixture MAE 0.87 vs FPL 1.07, Rank correlation 0.74 vs FPL 0.30, Season points ~2260, Edge over form-picking +102) survived the port character for character, each with its source caption
- Relocated the data-source credit line into the page body as the final paragraph (ledger entry 6), leaving Phase 1's unified `PageShell` footer untouched
- Added `frontend/src/vite-env.d.ts` (Vite client types reference) so the `?raw` import — and any future Vite-specific import in this project — resolves under `tsc -b` build mode

## Task Commits

Each task was committed atomically (both `tdd="true"`; both wrote passing tests on first implementation, so no separate RED-only commit was needed beyond the single feat commit per task — same judgment call plan 02-04's SUMMARY documents for this phase):

1. **Task 1: Differentials page with the ownership slider and its distinct band scale** - `0e27a7a` (feat)
2. **Task 2: Methodology page from bundled markdown** - `093ff16` (feat)

## Files Created/Modified
- `frontend/src/routes/Differentials.tsx` - Real, fully-ported differentials route (ownership slider, R39-R41)
- `frontend/src/routes/Differentials.test.tsx` - Full behavioral test suite (13 tests)
- `frontend/src/routes/Methodology.tsx` - Real, fully-ported methodology route (bundled markdown, react-markdown)
- `frontend/src/routes/Methodology.test.tsx` - Full behavioral test suite (7 tests)
- `frontend/src/content/methodology.md` - Verbatim markdown port of `web/methodology.html` lines 30-77
- `frontend/src/vite-env.d.ts` - New: Vite client types reference

## Decisions Made
- Exported `diffOwnershipCell(ownership)` as a standalone, directly-testable function rather than inlining the un-guarded `String(ownership?.toFixed(1))` expression — the null-ownership case it covers (R41) can never appear in the page's own rendered output (the R39 filter always excludes it), so the acceptance criterion is proven against the function in isolation instead of a rendered row, per the task's own read_first guidance.
- Styled `react-markdown`'s output via its `components` prop (an explicit tag-to-token-class map for h1/h2/p/ul/li/a/strong) rather than a wrapper CSS-cascade class, keeping the markdown-to-typography mapping declared once in `Methodology.tsx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `Differentials.test.tsx`'s untyped fetch mock broke the stricter `tsc -b` build-mode typecheck**
- **Found during:** Task 2, running `bash scripts/verify_frontend_build.sh` as part of Task 2's own full-suite verify block
- **Issue:** `npm run typecheck` (`tsc --noEmit`, a no-op check against the root project's empty `files: []`) passed trivially, but the build's `tsc -b` step failed on `Differentials.test.tsx` with `error TS2493: Tuple type '[]' of length '0' has no element at index '0'` — `mockFetchOnce`'s `vi.fn(() => ...)` had no declared parameter, so TypeScript inferred `fetchMock.mock.calls` as an array of empty tuples, and the "no additional fetch" test's `.filter(([url]) => ...)` destructure had no element to bind.
- **Fix:** Declared the mock function's parameter explicitly (`vi.fn((_path: string) => ...)`), matching the existing pattern in `XpTable.test.tsx`'s own fetch mock (which already types its `path` parameter for the same reason).
- **Files modified:** frontend/src/routes/Differentials.test.tsx
- **Verification:** `npm --prefix frontend run typecheck` and `bash scripts/verify_frontend_build.sh` (`BUILD PURITY OK`) both pass; the same stricter-build-mode failure mode plans 02-04 and 02-05's SUMMARYs document independently for this phase.
- **Committed in:** 093ff16 (Task 2 commit — bundled with Task 2's own changes since it was caught by Task 2's verify block, not Task 1's)

**2. [Rule 1 - Bug] `Methodology.tsx`'s own doc comment tripped the phase's `SetInnerHTML` negative-grep gate**
- **Found during:** Task 2, running `! grep -rq 'SetInnerHTML' frontend/src`
- **Issue:** A doc comment explaining the raw-HTML-sink threat mitigation used the literal word `dangerouslySetInnerHTML`, which matched the same case-sensitive substring the gate scans for — a false positive from documentation, not an actual sink, but one the gate cannot distinguish.
- **Fix:** Reworded the comment to describe the same fact ("no React raw-markup escape-hatch prop") without spelling out the literal API name.
- **Files modified:** frontend/src/routes/Methodology.tsx
- **Verification:** `! grep -rq 'SetInnerHTML' frontend/src` prints `NO RAW HTML SINK`.
- **Committed in:** 093ff16 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking type-inference fix, 1 Rule 1 self-inflicted grep-gate false positive)
**Impact on plan:** Both were necessary consequences of implementing the plan's own verify blocks exactly as written. No scope creep, no architectural change.

## Issues Encountered
None beyond the deviations documented above.

## Threat Model Notes

Per this plan's `<threat_model>`: T-02-12 (Tampering, mitigate) — confirmed `react-markdown` parses to real React elements and exposes no raw-markup sink by design; the repo-wide `! grep -rq 'SetInnerHTML' frontend/src` gate passes, and `Methodology.test.tsx`'s dedicated test confirms script-shaped markdown text renders as escaped visible text (`window.__pwned = true` as a string, never a live `<script>` element). T-02-13 (Information Disclosure, mitigate) — `Differentials.tsx` reuses the Phase 1 `ErrorState`, passing only the `resource` label; the thrown fetch error goes to `console.error` only, confirmed by the dedicated fetch-failure test.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All seven ported pages in this phase (xP table, fixtures, prices, league, scoreboard, differentials, methodology) are now real, fully-tested routes; `/team` remains the Phase 3 placeholder by design.
- `PARITY-DEVIATIONS.md`'s entry 6 (footer-placement decision) is now implemented exactly as pre-seeded — confirmed via `Methodology.test.tsx`'s footer-unchanged assertion. No new ledger entries were needed; this plan introduced no new intentional deviations from vanilla.
- `frontend/src/vite-env.d.ts` is now available for any future Vite-specific import (`?raw`, `?url`, etc.) in this project.
- No blockers for Phase 3 (pitch UI + `/team`) or Phase 7 (CUT-01 side-by-side comparison).

## Self-Check: PASSED

All 6 created/modified files verified present on disk; both task commit hashes (`0e27a7a`, `093ff16`) verified present in `git log`. Full frontend suite (169/169), typecheck, and the production build-purity gate (`BUILD PURITY OK`) all re-confirmed green immediately before writing this summary. The `MAXHI FORMULAS STAY DISTINCT`, `NO RAW HTML SINK`, and `RECEIPTS INTACT` source-level gates all re-confirmed passing.

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-01*
