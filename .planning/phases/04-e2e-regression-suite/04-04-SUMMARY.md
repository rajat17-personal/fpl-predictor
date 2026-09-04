---
phase: 04-e2e-regression-suite
plan: 04
subsystem: testing
tags: [e2e, playwright, xp-table, sort-order, captains, parity, tie-stability]

requires:
  - phase: 04-e2e-regression-suite (plan 02)
    provides: "e2e/helpers/page.ts's gotoReady, the isolated e2e/ npm project, and the chromium project's testIgnore that excludes specs/variants/** (this plan's spec runs on the normal fixture set only)"
  - phase: 04-e2e-regression-suite (plan 01)
    provides: "e2e/fixtures/v1/normal/web-data/{xp_table,captains}.json -- the immutable capture every literal in this plan's spec is hand-derived from"

provides:
  - "e2e/specs/xp-table.spec.ts: full E2E-03 coverage of the flagship xP table + Captain picks sub-table -- exact cell values and row order (10 tests total across 3 describe blocks)"
  - "Hand-derived literal reference for Phase 7's parity pass: rows 1-3, row 50 (Verbruggen), captain row 1 (Haaland), all four position-filter counts (GK=12, DEF=10, MID=22, FWD=6), two independent tie groups (price_m=4.5, ownership=0.6), and the full 12-name GK-filtered/price-sorted order"

affects: [e2e-suite-wave-3, ci-02, cutover]

actuals:
  tokens: 4213
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Column-index locators (table.locator('tbody tr td:nth-child(N)')) read as .allTextContents() to assert an exact ordered-name array after a sort/filter action, rather than walking individual row locators -- keeps a 50-row full-order assertion to one line instead of 50"
    - "Tie-stability proof: pick a real tied-key pair from the frozen data (never invent one), assert their relative order is unchanged across both sort directions -- proves the comparator returns 0 for equal keys and the underlying sort is stable, without ever calling the comparator from the spec"
    - "Band cell assertions use toContainText on the whole <td> rather than locating individual inner <span> elements -- BandCell.tsx's outer wrapping span's own textContent concatenates every descendant span's text with no separator, so `.locator('span').first()` resolves to the wrapper (all text glued together), not the innermost xp-number span"

key-files:
  created:
    - e2e/specs/xp-table.spec.ts
  modified: []

key-decisions:
  - "[Task 1, documented in-file] Two of the plan's conditional must_haves are not exercisable against the immutable v1 capture: (a) the captains sub-table's literal 'undefined' ownership fallback (R18) -- none of the 10 rows in captains.json, let alone the 5 rendered, has a null ownership; (b) the flagged-player status flag -- the top 50 rows all have status='a' (the nearest non-'a' row is index 201 of 651, far outside the slice). Both are skipped per the plan's own 'if no such player/row exists, skip only that assertion, record it' instruction -- not silently dropped, and the fixture is NOT mutated to force either case (D-08's immutability rule)."
  - "[Task 2, documented in-file] Searched the FULL 651-row frozen xp_table.json (not just the top 50) for any null price_m/ownership/xp_capt: zero exist anywhere in the committed fixture. The plan's flagged-assumption fallback ('cover the tie/null cases through a position filter that narrows to rows that do') presumes a null is reachable by filtering; since none exists ANYWHERE in the JSON, no filter can manufacture one without mutating v1. The null-key sort-placement assertion is therefore skipped, documented in the spec's own comment block rather than silently omitted. Every other required assertion (both glyphs, both directions, tie stability on two independent numeric columns, a text-column sort) is fully covered."
  - "[Task 3] 'Man City' chosen as the full-club-name search term (9 of 50 top rows, team_short=MCI) -- neither the full name nor the short code is a substring of the other, and the full name is never rendered in any cell on this page, so a passing search can only be exercising the r.team match branch (R13)."

patterns-established:
  - "For a future fixture cut (v2) that needs to exercise a null-valued cell or a flagged-status player, hand-pick source rows for the capture explicitly rather than hoping a real gameweek's data happens to include one -- v1's real capture has neither anywhere in its 651 rows."

requirements-completed: [E2E-03]

coverage:
  - id: D1
    description: "xP table + Captain picks sub-table: exact frozen cell strings, exact row counts/order, sort polarity with tie stability, position/search filters, empty-result state, and filter-then-sort composition -- all against the immutable v1 normal capture"
    requirement: "E2E-03"
    verification:
      - kind: e2e
        ref: "E2E_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python E2E_VARIANTS=0 npm --prefix e2e run test -- specs/xp-table.spec.ts --project=chromium (10 passed)"
        status: pass
      - kind: e2e
        ref: "E2E_VARIANTS=0 npm --prefix e2e run test -- --project=chromium (full non-variant suite, 18 passed: 2 smoke + 4 shell-geometry + 2 fixtures-prices + 10 xp-table)"
        status: pass
      - kind: other
        ref: "node coverage-grep gates: TABLE SCOPING OK (no frontend/src import, both aria-labels present), SORT CONTRACT ASSERTED (both glyphs, no spec-side .sort()), FILTER COVERAGE OK (No players match + all four position labels); (cd e2e && npx tsc --noEmit -p tsconfig.json) exits 0"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-09-04
status: complete
---

# Phase 4 Plan 04: xP Table + Captain Picks Exact-Value Coverage Summary

**Locked the flagship xP table's 41-rule parity contract into a real-browser Playwright spec — exact cell strings for the first three and last of the frozen top 50, the Captain picks sub-table's full-club-name/no-en-dash divergence, both sort-arrow directions with two independently-verified stable ties, all four position-filter counts summing to 50, a full-club-name search, the no-match empty state, and one filter-then-sort composition — 10 tests, zero re-implementation of the formatting/sorting code under test.**

## Performance
- **Duration:** ~35min active work
- **Started:** 2026-09-04 (immediately following 04-03)
- **Completed:** 2026-09-04
- **Tasks:** 3 (all `type="auto"`, no checkpoints)
- **Files modified:** 1 (new)

## Accomplishments

- **Task 1 — Exact cell values and row order.** Before writing any assertions, scripted an inspection of the committed `e2e/fixtures/v1/normal/web-data/{xp_table,captains}.json` to hand-derive every literal (D-15): confirmed `xp_table.json`'s 651 rows are already sorted descending by `xp` (the pipeline's own pre-sort, R10) so the top-50 slice is rows 1-50 unchanged. Hardcoded the header row (7 labels, exact order), rows 1-3 (B.Fernandes/Haaland/Cherki, every cell including the band's `lo–hi` and `xp` numbers with real `toFixed` rounding — e.g. `p90=10.55` renders as `10.6`), row 50 (Verbruggen, pinning the slice boundary), the two page-copy paragraphs, and the Captain picks sub-table's row 1 (Haaland/Man City, full club name in the Team column vs. the main table's short code). Discovered during fixture inspection (not during test-writing) that the frozen capture has **zero** rows with a non-`"a"` status in the top 50 and **zero** null-ownership rows among the five rendered captains — both conditional must-haves from the plan's own text are consequently not exercisable against this immutable fixture; documented in-file and here rather than silently dropped or worked around by mutating v1.
- **Task 2 — Sort semantics, ties and null keys.** Locked `sortRows`' counter-intuitive polarity (fresh click = ascending + nulls-top, glyph `▼`; repeat click = descending + nulls-bottom, glyph `▲`) on both a numeric column (`£m`) and a text column (`Player`), asserting the exact ordered name list in both directions. Proved stability with **two independent real tied-key pairs** found by scripting the fixture (not invented): `price_m=4.5` (a five-way tie — Dedić/Petrović/Leno/Ajer/Verbruggen, the minimum price in the top 50, landing as the first 5 names ascending and the last 5 descending, same relative order both times) and `ownership=0.6` (Ndoye/Janelt, same proof on an independent column). Searched the **entire 651-row** frozen capture (not just the visible top 50) for any null `price_m`/`ownership`/`xp_capt` — found zero anywhere — so the null-key-placement assertion the plan's flagged-assumption fallback anticipated (narrow via a position filter to find one) has no fixture data to exercise even after filtering; documented and skipped rather than mutating the immutable v1 set.
- **Task 3 — Filters, empty state, filter/sort interaction.** Verified all five position chips (`All` pressed by default) and the exact per-chip row count for the frozen top 50 (GK=12, DEF=10, MID=22, FWD=6, summing to 50 — proving filters run on the already-sliced 50, R12). Chose `"Man City"` as the full-club-name search term (9 of 50 rows, team_short `MCI`) to prove the `r.team` match branch (R13) since the full name is never rendered in any cell. Asserted the `No players match` block for an unmatched search, explicitly distinct from the page-level `EmptyState`'s `Nothing here yet` heading (queried and asserted absent), with the chips/search box still present for recovery, then cleared the search and confirmed all 50 rows return. Closed with a filter-then-sort composition test (GK filter + ascending `£m` sort) asserting the full 12-name literal order, proving the sort ran over the filtered 12-row subset rather than the unfiltered 50.
- Re-ran the full non-variant Playwright suite after each task (culminating in 18 passed: 2 smoke + 4 shell-geometry + 2 fixtures-prices + 10 xp-table), `npm --prefix frontend run test` (363 passed), and the full pytest suite (76 passed) — none regressed.

## Task Commits
1. **Task 1: Exact cell values and row order for both tables** — `18bb6f0` (test) — `e2e/specs/xp-table.spec.ts`
2. **Task 2: Sort semantics, ties and null keys** — `cd33ccd` (test) — `e2e/specs/xp-table.spec.ts`
3. **Task 3: Filters, the empty state, and filter/sort interaction** — `76b658c` (test) — `e2e/specs/xp-table.spec.ts`

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `e2e/specs/xp-table.spec.ts` (new, 351 lines, 10 tests across 3 `describe` blocks) — the complete E2E-03 spec: exact cell values/row order, sort semantics with tie/null coverage, and filters/empty-state/composition.

## Decisions Made
See `key-decisions` in frontmatter — the two documented fixture-data gaps (no null captain ownership, no flagged status player, no null anywhere in the numeric columns) are the load-bearing facts for anyone extending this spec or cutting a v2 fixture.

## Deviations from Plan

**1. [Fixture-data gap, documented per the plan's own escape hatch — no code change] Captains table's literal-`"undefined"` ownership fallback (R18) has no exercisable row in the frozen capture**
- **Found during:** Task 1, while deriving literals from `captains.json`.
- **Issue:** The plan's `<action>` text makes this assertion conditional ("If any of the five frozen captain rows has a null ownership, assert the literal string `undefined`..."). None of `captains.json`'s 10 rows (nor the 5 rendered) has a null `ownership`.
- **Fix:** Skipped this one assertion; documented in the spec's own header comment and here. The underlying code path (`String(r.ownership?.toFixed(1))`, PARITY-DEVIATIONS.md's R18 entry) is unaffected and still correct — only this spec's proof of it is deferred to a future fixture cut.
- **Files modified:** none (documentation only, within the same file's comments)
- **Verification:** confirmed via scripted inspection (`node -e "..."` over `captains.json`) that all 10 rows have non-null `ownership`
- **Commit:** `18bb6f0`

**2. [Fixture-data gap, documented per the plan's own escape hatch — no code change] No flagged-status player exists within the top 50**
- **Found during:** Task 1, while checking `xp_table.json` for a non-`"a"` status.
- **Issue:** The plan makes the status-flag assertion conditional on the frozen capture containing such a player. It does not, within the top 50 (the nearest non-`"a"` row is index 201 of 651).
- **Fix:** Skipped, per the plan's own "if no such player exists in the capture, record that in the SUMMARY and skip only that assertion" instruction.
- **Files modified:** none
- **Verification:** scripted inspection of all 651 rows in `xp_table.json` confirmed only rows beyond index 200 have a non-`"a"` status
- **Commit:** `18bb6f0`

**3. [Fixture-data gap beyond the plan's anticipated fallback, documented — no code change] No null numeric value anywhere in the 651-row frozen capture, so the null-key sort-placement assertion cannot be exercised even via the plan's suggested position-filter fallback**
- **Found during:** Task 2, while deriving the null-key test case.
- **Issue:** The plan's flagged assumption anticipates that if the top 50 lacks a null, "cover the tie/null cases through a position filter that narrows to rows that do." Scripted inspection of the FULL 651-row `xp_table.json` (not just the top 50) found zero rows with a null `price_m`, `ownership`, or `xp_capt` anywhere — so no filter, however narrow, can surface one without mutating the immutable v1 fixture.
- **Fix:** Skipped the null-key placement assertion; documented prominently in the spec's own comment block (not silently dropped). Every other Task 2 requirement (both glyphs, both directions on a numeric column, tie stability on two independent tied-key pairs, a full text-column sort) is fully implemented and passing.
- **Files modified:** none
- **Verification:** scripted inspection (`node -e "..."`) of all 651 rows, all three numeric fields
- **Commit:** `cd33ccd`

**Total deviations:** 3, all the same category (a plan-anticipated fixture-data condition that this specific frozen capture does not satisfy) — none required a code change, a checkpoint, or an architectural decision. Each is documented in-file (so the spec's own comments carry the explanation forward) and here, per the plan's explicit "record it in the SUMMARY, do not mutate the immutable fixture" instruction.
**Impact:** None on production code. Three specific rendered-DOM assertions (captains null-ownership literal, status-flag reveal, null-key sort placement) are deferred to a future `v2` fixture cut that deliberately includes rows exercising those paths — everything else the plan required is implemented and green.

## Issues Encountered

None beyond the three documented fixture-data gaps above.

## User Setup Required

None. Local runs need `E2E_PYTHON` set to the conda interpreter, exactly as established in 04-02 — no new environment requirement introduced by this plan.

## Next Phase Readiness

E2E-03 (xP table + captain picks with exact values and sort order) is now closed. The hand-derived literals recorded in this SUMMARY and in the spec's own header comment (rows 1-3, row 50, captain row 1, all four position counts, both tie groups, the full GK-filtered/price-sorted order) are available for Phase 7's parity pass to reuse without re-deriving them. Remaining phase scope per `04-CONTEXT.md`: E2E-02 (team/pitch + solver flow) and E2E-04 (rate-my-team end to end), each their own later plan/wave. The three documented fixture-data gaps (no null anywhere in `xp_table.json`, no flagged player in the top 50, no null captain ownership among the first 5) are worth keeping in mind if a future plan needs one of those conditions — they are not present in v1 and D-08 forbids mutating it in place; a v2 cut would need to deliberately include such rows. No blockers.

## Self-Check: PASSED

- `e2e/specs/xp-table.spec.ts` — FOUND on disk (351 lines)
- `git log --oneline --all --grep="04-04"` — commits `18bb6f0`, `cd33ccd`, `76b658c` all present in `git log --oneline -5` with a `test(04-04): ...` message
- Re-ran all three tasks' acceptance criteria: all pass (10/10 tests in `xp-table.spec.ts`; `TABLE SCOPING OK`; `SORT CONTRACT ASSERTED`; `FILTER COVERAGE OK`; `(cd e2e && npx tsc --noEmit -p tsconfig.json)` exits 0)
- Re-ran plan-level `<verification>`: `npm --prefix e2e run test -- --project=chromium` (full non-variant suite) green — 18 passed; spec contains no import from `frontend/src` (confirmed by the same grep gate); `npm --prefix frontend run test` unaffected (363 passed); full pytest suite unaffected (76 passed)
