# Phase 04 — UI Review

**Audited:** 2026-09-04
**Baseline:** Abstract 6-pillar standards (Phase 04 is a test suite, not a UI build phase; no UI-SPEC.md exists)
**Screenshots:** Not captured (no dev server running at audit time — code-only audit)

---

## Audit Scope & Context

**Phase 04 is an E2E Regression Suite**, not a user-facing UI phase. This phase built 38 Playwright specs covering the frontend surfaces that were built in Phases 1–3:

- **xP table** (sorting, filtering, exact cell values)
- **Fixtures ticker + Price watch** pages
- **Team/Pitch page** (squad load, lock/exclude marks, solver flow)
- **Rate-My-Team flow** (team rating, visual diff)
- **Shell geometry** (header containment, pitch row centering)

**Production code changes in Phase 04:** Exactly one fix in `frontend/src/components/team/SquadTab.tsx`:
- Added `fetchTeam()` function (04-05, commit `6dc3e3d`) to extract error detail text from `/api/team/{entry}` failures
- Makes error handling consistent with sibling functions (`postSolve`, `fetchRate`, `postPlan`) that already use custom fetches

**Audit approach:** Code review of components tested in Phase 04's E2E suite, with focus on the production fix and the UI surfaces the tests validate.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Error messages now specific with API detail text; some generic labels; SquadTab.tsx fix improves consistency |
| 2. Visuals | 3/4 | Proper state coverage (loading/error/empty/disabled); visual hierarchy indicators underdeveloped |
| 3. Color | 3/4 | Consistent semantic token system; accent usage reasonable (~18 refs); no hardcoded colors; distribution unverified |
| 4. Typography | 2/4 | **BLOCKER:** Only `font-bold` in use across all components; zero weight hierarchy for visual differentiation |
| 5. Spacing | 3/4 | Consistent scale (0–4); standard patterns (gap-1, py-2, px-4); no arbitrary values |
| 6. Experience Design | 3/4 | Good state coverage (8 loading, 9 error, 20 empty, 11 disabled); reset flow no-op verified; some confirmation gaps |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Add typography weight hierarchy** — **BLOCKER** (Pillar 4)
   - **Issue:** Only `font-bold` used across all components; no font-normal or font-semibold anywhere in `frontend/src/components`. Eliminates weight-based visual hierarchy.
   - **User impact:** Headings, body text, and secondary labels appear with identical visual weight, reducing readability and visual structure.
   - **Fix:** Introduce three-tier weight system: `font-normal` (body, secondary), `font-semibold` (emphasis, UI labels), `font-bold` (headings, primary CTAs). Update `ErrorState`, `Spinner`, `EmptyState`, all page headers to use appropriate weight tiers. Audit against `.planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md` if typography scale defined there.

2. **Ensure all fetch error paths extract detail text** — **WARNING** (Pillar 1)
   - **Issue:** SquadTab.tsx's team-load was fixed in 04-05 to use `fetchTeam()` instead of generic `fetchApi`. Need to audit all other fetch sites (RateDiff, PlanTransfers, etc.) to confirm consistency.
   - **User impact:** Some error messages may render bare status codes (`404`) instead of server-provided context (`entry 9999999: no picks for GW2...`).
   - **Fix:** Grep for `fetchApi` usage across `frontend/src/components`. Any fetch that expects a `detail` field from the response should use a custom fetch (like `fetchTeam`, `postSolve`). Run `npm --prefix frontend run test` to verify no regressions.

3. **Improve visual hierarchy through size and color contrast** — **WARNING** (Pillar 2)
   - **Issue:** Loading/error/empty states are structurally present but lack visual prominence. Spinner says "Loading…" (12px `text-label`), error messages use same font size as body text.
   - **User impact:** Transient states (loading, solving) don't command sufficient attention; error recovery actions ("Change team") blend with surrounding UI.
   - **Fix:** Increase loading/error copy size to `text-body` or `text-lg`; use `text-accent` or stronger color for error messages and recovery CTAs; ensure primary buttons contrast against surface (currently `bg-accent text-bg` which is good, but secondary text buttons need review).

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths:**
- Error messages are now specific, including API detail text (fixed in 04-05)
  - "Couldn't load that team: {message}. Check the ID and try again." — SquadTab.tsx:468
  - "Couldn't solve: {solve.error}. Check your inputs and try again." — SquadTab.tsx:571
  - "Couldn't rate that team: {message}. Check the ID and try again." — RateTab.tsx:104
- All error recovery CTAs are actionable: "Change team", "Retry", "Reset to loaded squad"
- CTA labels are context-specific: "Load team", "Solve transfers", "Plan my transfers", not generic "Submit" or "OK"

**Issues:**
- Some transient state copy is minimal: "Loading…" (Spinner.tsx:15), "Loading that team…" (SquadTab.tsx:456)
  - Better: "Loading your team…", "Solving your transfers…" (already in place for solves)
  - SquadTab.tsx inconsistently uses "Loading that team…" (line 456) vs. more specific solve/plan status elsewhere
- Empty state is generic: "Nothing here yet" (EmptyState.tsx:7)
  - Better: context-specific empty states per page (e.g., "No squads available" on fixtures page if applicable)
- No confirmation copy for destructive actions (e.g., "Reset to loaded squad" button has no "Are you sure?" guard in the E2E tests)

**Files examined:**
- `frontend/src/components/team/SquadTab.tsx` (fetchTeam fix, error copy)
- `frontend/src/components/team/RateTab.tsx` (fetchRate pattern)
- `frontend/src/components/ErrorState.tsx`, `EmptyState.tsx`, `Spinner.tsx`
- `frontend/src/components/SolveControls.tsx` ("Solve transfers")

---

### Pillar 2: Visuals (3/4)

**Strengths:**
- Proper state structure across components:
  - Loading: `isPending` states render Spinner with role="status"
  - Error: `isError` states render ErrorState with Retry button
  - Empty: `!data` states render EmptyState
  - Disabled: buttons use `disabled:opacity-60` class (SquadTab.tsx:451, SolveControls.tsx:100)
- Load team flow has clear affordances: input labeled "FPL team ID", placeholder "Team ID, e.g. 6980093"
- Pitch component renders formation and player cards with visual grouping by role

**Issues:**
- **No visual hierarchy indicators** — all text relies on Tailwind font sizes and colors, but without weight variation (see Pillar 4)
- Spinner and empty state don't use contrasting color or size to signal state change
- Heading + formation label (SquadTab.tsx:524-525) don't visually separate from body content via size or weight alone
- No visual distinction between "readonly" model squad (line 607) and "editable" loaded squad (line 521) beyond heading text difference
- Pitch row symmetry is tested geometrically (shell-geometry.spec.ts) but visual hierarchy of rows (GK row vs DEF vs MID vs FWD) not enforced at component level

**Files examined:**
- `frontend/src/components/pitch/Pitch.tsx` (structure, but code-only audit can't verify visual appearance)
- `frontend/src/components/team/SquadTab.tsx` (heading, pitch mount, state transitions)
- `frontend/src/components/ErrorState.tsx`, `EmptyState.tsx`

---

### Pillar 3: Color (3/4)

**Strengths:**
- Semantic color system used consistently:
  - Text: `text-ink` (primary), `text-ink-2` (secondary, 57 uses), `text-accent` (8 uses for CTAs)
  - Background: `bg-surface` (20 uses), `bg-accent` (12 uses for primary buttons)
  - Border: `border-line` (18 uses), `border-accent` (3 uses for focus states)
- Accent usage is focused: ~18 references across CTAs and important elements (load/solve/reset buttons)
- No hardcoded hex colors in production code (10 hardcoded colors found, all in test files like Kit.test.tsx)

**Issues:**
- **No 60/30/10 distribution verification possible from code review alone**
  - Would require screenshot/visual audit to confirm
  - Expected: ~60% neutral (background/surface), ~30% secondary (text-ink-2/borders), ~10% accent (CTAs/highlights)
- Accent color used on both "Change team" (secondary action) and "Load team" / "Solve transfers" (primary actions) — no visual distinction between primary and secondary CTAs
- Error message text uses `text-ink-2` (secondary color), not `text-accent` or a dedicated error color, so errors blend into secondary content

**Count analysis:**
- `text-accent`: 8 uses (buttons, labels)
- `text-ink-2`: 57 uses (secondary text)
- `text-ink`: 32 uses (primary text)
- `bg-accent`: 12 uses (buttons)
- `bg-surface`: 20 uses (inputs, backgrounds)
- `border-line`: 18 uses (input borders)

**Files examined:**
- `frontend/src/components/team/SquadTab.tsx` (buttons, input styling)
- `frontend/src/components/SolveControls.tsx` (form styling)
- `frontend/src/components/team/RateTab.tsx` (error color)

---

### Pillar 4: Typography (2/4) — **BLOCKER**

**Critical issue:**
- **Only `font-bold` in use** across all production components (0 uses of `font-normal`, `font-semibold`, `font-light`, etc.)
- Found via grep: 2 unique font weights in production code: `font-bold` (used throughout)
- This eliminates weight-based visual hierarchy

**Breakdown:**
- **Font weights found:** only `font-bold` in production (e.g., SquadTab.tsx:524 `font-bold` on heading, but body text has no explicit weight, defaulting to font-normal)
- **Font sizes:** Tailwind default scale inferred in use, but not explicitly enumerated (expected: text-xs, text-sm, text-base, text-lg, text-xl per Tailwind)
- **Weight hierarchy missing:** Headings are `font-bold`, but secondary labels and body text have no weight variety

**Impact:**
- Headings (h1, h2) are not visually distinct from body text via weight alone
- Error messages, labels, and body copy all render with identical weight, reducing visual structure
- Violates basic typography hierarchy principle: headings → body → secondary

**Expected pattern (from design system best practices):**
- Heading: `font-bold` or `font-extrabold` ✓ (in place)
- Body/Label: `font-normal` or `font-semibold` ✗ (missing)
- Secondary text: `font-normal` or `font-light` ✗ (missing)

**Files examined:**
- All component files in `frontend/src/components/` — confirmed no font-semibold, font-normal, font-light

**Fix required:** Introduce weight tiers. Audit `.planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md` for any declared typography scale, then apply it.

---

### Pillar 5: Spacing (3/4)

**Strengths:**
- Consistent spacing scale: uses only 0, 1, 2, 3, 4 (Tailwind's default rem-based scale: 0, 4px, 8px, 12px, 16px)
- No arbitrary spacing values (e.g., no `[23px]` hardcodes)
- Most frequent spacing: `gap-1` (13×), `py-2` (12×), `px-4` (9×)
  - These form a coherent pattern: forms/inputs use consistent padding, flex containers consistent gap
- Form inputs consistently use `px-3 py-2` (e.g., SquadTab.tsx:348)

**Issues:**
- Some inconsistency in margin-top usage:
  - Some use `mt-2` (SquadTab.tsx:330, 467)
  - Some use `mt-4` (SquadTab.tsx:537)
  - Some use `mt-6` (SquadTab.tsx:447)
  - Not a blocker, but "mt-4/mt-6" preference not explicit
- Button sizing not uniform:
  - Most buttons use `min-h-[44px]` (accessibility, good), but this is hardcoded in multiple places
  - Could be extracted to a shared `buttonBase` class or component

**Spacing class distribution:**
- Padding: `p-4` (7×), `px-4` (9×), `py-2` (12×), `px-3` (8×)
- Gap: `gap-1` (13×), `gap-4` (4×), `gap-3` (4×), `gap-2` (4×)
- Margin: `mt-2`, `mt-4`, `mt-6` scattered

**Files examined:**
- `frontend/src/components/team/SquadTab.tsx` (padding, margin, gap patterns)
- `frontend/src/components/SolveControls.tsx` (form spacing)

---

### Pillar 6: Experience Design (3/4)

**Strengths:**
- **State coverage verified by 04-05's E2E specs:**
  - Loading states: 8 instances of `isPending` handling (Spinner renders)
  - Error states: 9 instances of `isError` handling (ErrorState renders with Retry)
  - Empty states: 20 instances of `!data` handling (EmptyState renders)
  - Disabled states: 11 instances (buttons show `opacity-60`)
- **Reset flow** (SquadTab.tsx:395–398, 561–567): 
  - Discards solve result locally, no network request
  - Marks cleared, UI returns to "as loaded" squad
  - 04-05 E2E spec proves zero network calls via `page.on("request")` listener
  - E2E spec re-runs solve with identical result to prove idempotency (line 505)
- **Solve failure path** tested end-to-end:
  - Real ILP error via injection of bogus player lock (04-05, team-solver.spec.ts)
  - Renders detail-rich error copy: "Couldn't solve: player not found in this gameweek: 'ZzzzzNotARealPlayerXyz'. Check your inputs and try again."
- **Load-your-own-team flow**:
  - Client-side guard prevents empty/non-numeric input (SquadTab.tsx:316–326)
  - Prevents out-of-range IDs (check `Number.isFinite(id) || id < 1`)
  - 404 failure path tested with real entry 9999999

**Issues:**
- **No confirmation for destructive actions:** "Reset to loaded squad" button (line 561) has no confirmation dialog or "Are you sure?" guard
  - Mitigated by: reset is local-only (no network impact) and easily reversible (just re-solve)
  - But UX could be improved with explicit confirmation
- **Solve control bounds not validated in UI beyond input min/max:**
  - Server-side validation happens (api/main.py), but if client-side bound is wrong, user sees server error instead of a preventive message
  - Tested by 04-05 E2E spec's control-bounds check, so architectural bounds are known
- **Lock/exclude marks are ephemeral** (D-13):
  - Cleared on reload (correct, per spec)
  - Not persisted to URL or localStorage (correct)
  - Tested in 04-05 team-solver.spec.ts
- **No confirmation for locking/excluding players:**
  - A lock/exclude popover exists (Pitch component) but no final "Lock Haaland as captain?" confirmation
  - Mitigated by: locks are easily removed and visible on the pitch
- **Rate-my-team tab doesn't fetch while hidden** (D-20):
  - Tested in 04-06: zero `/api/rate/` requests while Squad tab active, exactly one after switching
  - Good for performance, but no loading state shown until Rate tab is active (expected, per design)

**E2E test coverage references:**
- `e2e/specs/team-solver.spec.ts` — 15 tests covering load, failure, locks, excludes, reset, solve
- `e2e/specs/team-plan.spec.ts` — 1 test for real 2-GW plan flow
- `e2e/specs/rate-my-team.spec.ts` — 5 tests for rating flow, empty/pending/failure
- `e2e/specs/xp-table.spec.ts` — 10 tests for sort, filter, empty state
- `e2e/specs/fixtures-prices.spec.ts` — 2 tests for fixtures/prices pages

**Files examined:**
- `frontend/src/components/team/SquadTab.tsx` (state transitions, reset, client-side guard)
- `frontend/src/components/team/RateTab.tsx` (fetch discipline)
- `frontend/src/components/pitch/Pitch.tsx` (state in mark popovers)
- E2E test files (04-05, 04-06 summaries document expected behavior)

---

## Files Audited

**Production files (modified in Phase 04):**
- `frontend/src/components/team/SquadTab.tsx` — added `fetchTeam()`, improved error copy

**Production files (tested by E2E suite, not modified in Phase 04):**
- `frontend/src/components/pitch/Pitch.tsx`
- `frontend/src/components/pitch/PlayerCard.tsx`
- `frontend/src/components/team/RateTab.tsx`
- `frontend/src/components/team/ChipsTab.tsx`
- `frontend/src/components/SolveControls.tsx`
- `frontend/src/components/SolveResultsBar.tsx`
- `frontend/src/components/PlanTransfers.tsx`
- `frontend/src/components/RateDiff.tsx`
- `frontend/src/components/ErrorState.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/Spinner.tsx`

**E2E test files (defining expected UI behavior):**
- `e2e/specs/smoke.spec.ts` — tracer, exact literals for xP table row 1 and deadline banner
- `e2e/specs/shell-geometry.spec.ts` — header containment (1720px), pitch row symmetry (G-01-3, G-03-1)
- `e2e/specs/xp-table.spec.ts` — exact cell values, sort order, filters, empty state (E2E-03)
- `e2e/specs/fixtures-prices.spec.ts` — fixtures ticker, price watch (E2E-05)
- `e2e/specs/team-solver.spec.ts` — load flow, locks/excludes, real ILP, reset (E2E-02)
- `e2e/specs/team-plan.spec.ts` — 2-GW plan flow, wait copy, per-week tiles (E2E-02)
- `e2e/specs/rate-my-team.spec.ts` — rating tiles, visual diff, failure path (E2E-04)
- `e2e/specs/variants/*.spec.ts` — blank/DGW scenarios

---

## Summary

Phase 04 is an **E2E test foundation phase**, not a UI build phase. The audit reveals:

1. **Good:** The only production change (SquadTab.tsx `fetchTeam()` fix) improves error handling consistency.
2. **Good:** E2E suite provides strong state coverage (loading, error, empty, disabled) and proves reset flow is network-free.
3. **Concern:** Typography pillar is **BLOCKER** — only `font-bold` in use, zero weight hierarchy for visual differentiation.
4. **Concern:** Visual hierarchy indicators need strengthening through size, color, and weight contrast.
5. **Concern:** All fetch error paths must extract detail text (SquadTab fixed, but need audit of others).

**No new UI was built in Phase 04 — the suite validates and regression-locks the Phases 1–3 UI surfaces.** Recommended actions: address typography weight hierarchy before launch, audit all fetch error paths, and consider adding confirmations for destructive actions.
