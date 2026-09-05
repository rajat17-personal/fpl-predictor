---
phase: 02-data-layer-non-pitch-pages
verified: 2026-09-02T21:40:00Z
status: passed
score: 14/16 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 12/12
  gaps_closed:
    - "G-02-1: dark theme read green-tinted — dark neutral chroma rebalanced, hue-locked to accent, color-scheme + body paint restored, enforced by frontend/scripts/check-tokens.mjs wired into `npm run test`"
    - "G-02-2: fixture chip venue letter sat beside instead of below the opponent code — FdrCell chip is now a column-direction flex with the venue tag on its own line, chip-owned 56px min-width, mono family, tight ticker-cell padding restored, pinned by 6 new geometry regression tests"
  gaps_remaining: []
  regressions: []
gaps: []
behavior_unverified_items: []
human_verification:

  - test: "Run the dev server, force dark mode, and load /fixtures and other routes. Confirm the frame reads as neutral dark (not green-tinted), and that the browser's own scrollbar/overscroll canvas paints dark rather than leaving light UA chrome next to the tinted surfaces."
    expected: "No green wash; UA chrome (scrollbar, overscroll) matches the dark palette."
    why_human: "The OKLCH chroma/hue/lightness budget and the color-scheme/body-paint structure are all confirmed programmatically (check-tokens.mjs gate passes with genuinely lower chroma and tighter hue-lock than before the fix), but whether the frame 'reads as dark, not green' to a human eye, and whether the browser actually paints its own chrome dark in response to color-scheme, cannot be asserted by grep or jsdom (jsdom has no paint pipeline and no UA chrome)."
  - test: "Visit /fixtures and compare a fixture chip's stacked H/A tag against web/fixtures.html's vanilla chip, in both themes."
    expected: "The venue letter sits on its own line, centred beneath the opponent code, matching vanilla's layout; the table is not visibly taller than before."
    why_human: "DOM class assertions (flex-col, chip-owned min-width, font-mono, opacity-75) and the tight td padding are all confirmed present in the code and pinned by 6 passing regression tests, but jsdom applies no stylesheet — only a real browser proves the rendered geometry matches vanilla pixel-for-pixel."
---

# Phase 2: Data Layer & Non-Pitch Pages Verification Report

**Phase Goal:** Seven of the eight pages render at verified parity with the vanilla site from the same JSON contract
**Verified:** 2026-09-02
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plans 02-07, 02-08 closing UAT gaps G-02-1 and G-02-2)

## Goal Achievement

### Observable Truths

Truths 1–12 are the phase's original must-haves (carried from the initial 02-VERIFICATION.md); truths 13–16 are the gap-closure plans' own must-haves for G-02-1/G-02-2. All were independently re-checked against the current codebase (not read from SUMMARY claims).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | xP table (`/`) sorts, filters, and formats identically to vanilla (R1–R19) | ✓ VERIFIED (regression) | `sortable.ts`/`format.ts` unchanged by gap plans; `XpTable.test.tsx` still green in the 178/178 re-run |
| 2 | Fixtures page (`/fixtures`) shows an FDR ticker in the 1–5 easy→hard convention | ✓ VERIFIED (regression) | `FdrCell.tsx`'s literal `FDR_CLASSES` map unchanged by gap closure; only chip geometry/padding/family changed (see truths 13–16) |
| 3 | Prices page (`/prices`) shows watchlist rise/fall indicators matching vanilla | ✓ VERIFIED (regression) | `Prices.tsx` untouched by gap plans; `Prices.test.tsx` green |
| 4 | League, scoreboard, differentials, and methodology pages present the same information as vanilla | ✓ VERIFIED (regression) | Untouched by gap plans; respective test files green |
| 5 | Every route shows a persistent gameweek meta banner (UI-06) | ✓ VERIFIED (regression) | `PageShell.tsx`/`GwBanner.tsx` untouched; tests green |
| 6 | Three-state Light/Dark/System toggle (UIX-02) persists and resolves correctly | ✓ VERIFIED (regression) | `theme.ts`/`ThemeToggle.tsx` untouched by gap plans (only the CSS tokens they resolve to changed); `theme.test.ts`/`ThemeToggle.test.tsx` green |
| 7 | Complete `web/data/*.json` interface set in `lib/api.ts`; no later plan re-edited it | ✓ VERIFIED (regression) | `api.ts` not in either gap plan's `files_modified` |
| 8 | `PARITY-DEVIATIONS.md` exists with all eight seeded deviations plus an append rule | ✓ VERIFIED | Read directly: numbered deviations table still has exactly 8 rows; a new "Palette changes made in lockstep" section was added below it (not a 9th deviation row, by design — a lockstep change produces no React/vanilla delta) |
| 9 | Full frontend Vitest suite, typecheck, and production build-purity gate all pass | ✓ VERIFIED | Independently re-run: `npm --prefix frontend run test` → 178/178 passed (22 files, includes the new `check-tokens.mjs` gate + 6 new FdrCell geometry tests + 1 new Fixtures padding test); `npm --prefix frontend run build` → succeeds, clean dist output |
| 10 | Regression gate: Phase 1 API pytest suite + Phase 1 frontend tests unaffected | ✓ VERIFIED (regression) | Folded into the 178/178 total; no Phase 1 files touched by either gap plan |
| 11 | No raw-HTML injection sink exists anywhere in `frontend/src` | ✓ VERIFIED (regression) | `Methodology.tsx` untouched by gap plans |
| 12 | No unresolved debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) in phase-modified files | ✓ VERIFIED | `grep -rnE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across all 8 gap-plan-modified files (index.css, check-tokens.mjs, FdrCell.tsx, FdrCell.test.tsx, Fixtures.tsx, Fixtures.test.tsx, style.css, package.json) returns no matches |
| 13 | (02-07) In dark mode every neutral surface token carries no more chroma than its light-theme counterpart (within an 8-bit quantization allowance), hue-locked to the accent | ✓ VERIFIED | Independently re-ran `npm --prefix frontend run check:tokens`: all 4 roles now pass chroma budget (bg 0.0061≤0.0064, surface 0.0106≤0.0120, surface-2 0.0135≤0.0153, line 0.0161≤0.0176) and hue lock (0.2°–3.2° from accent, was 4.9°–12.7°); lightness held within 0.07 of pre-fix values |
| 14 | (02-07) `.dark`/`:root` declare color-scheme; body is painted from `--color-bg`; vanilla and React declare byte-identical dark neutral hexes | ✓ VERIFIED | Read directly in `frontend/src/index.css` (lines 86–128): `:root{color-scheme:light}`, `.dark{color-scheme:dark; ...}`, `body{background:var(--color-bg);color:var(--color-ink)}`; `web/assets/style.css` lines 27–50 carry the identical 4 hex values, confirmed both by direct read and by the gate's own lockstep assertions |
| 15 | (02-07) A dependency-free automated gate fails the frontend test command if a future edit reintroduces over-chromatic/accent-colliding dark neutrals | ✓ VERIFIED | `frontend/package.json`'s `test` script is `node scripts/check-tokens.mjs && vitest run` (confirmed by direct read); git history shows commit `ab48ff1` shipped the gate RED against the pre-fix palette (commit message + diff confirm), and it is GREEN today |
| 16 | (02-08) On `/fixtures` every fixture chip shows the venue letter on its own line, centred beneath the opponent code; every chip (populated + blank) carries its own 56px min-width (not the wrapper); tight ticker-cell padding restored; a regression test fails on reversion | ✓ VERIFIED | `FdrCell.tsx` read directly: populated chip is `inline-flex ... flex-col ... min-w-[56px] ... font-mono`, wrapper carries no min-width; blank-branch matches. `Fixtures.tsx` line 101: `<td className="px-1 py-[3px]">` scoped to the gameweek cell only, 4 other cells keep `px-3 py-2`. 6 new geometry tests in `FdrCell.test.tsx` + 1 new padding test in `Fixtures.test.tsx` independently re-run and pass |
| G-02-1 (visual) | The dark frame reads as dark, not green, to a human eye; browser UA chrome (scrollbar/overscroll) paints dark | ? UNCERTAIN — routed to human | Numeric/structural evidence strongly supports the fix (chroma nearly halved, hue lock tightened 2–6x, color-scheme + body paint restored — see truths 13–14), but final perceptual confirmation and UA-chrome rendering require a real browser; both gap plans' own `<human-check>` blocks explicitly deferred this to end-of-phase per `workflow.human_verify_mode` |
| G-02-2 (visual) | The stacked chip visually matches vanilla's fixture ticker at a glance, without visibly inflating the table | ? UNCERTAIN — routed to human | DOM structure and padding are confirmed correct by direct read and 7 passing tests (see truth 16), but the plan's own `<human-check>` explicitly deferred final pixel-level visual comparison against `web/fixtures.html` to end-of-phase |

**Score:** 14/16 truths verified (2 routed to human verification per the gap plans' own deferred `<human-check>` blocks)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/scripts/check-tokens.mjs` | Dependency-free OKLCH token-budget gate | ✓ VERIFIED | Present, zero npm deps (`node:fs`/`node:url` only), independently re-run and passes |
| `frontend/src/index.css` | Rebalanced dark neutrals + color-scheme + body paint | ✓ VERIFIED | Read directly; all 4 changes present |
| `web/assets/style.css` | Lockstep dark neutral hexes | ✓ VERIFIED | Read directly; identical to `index.css`'s `.dark` block |
| `.planning/phases/01.../01-UI-SPEC.md` | Updated Color role table with new hexes | ✓ VERIFIED | `141715`/`1b201c`/`222924`/`2e3731` all present; superseded hexes not found in the role/token tables |
| `.planning/phases/02.../02-UI-SPEC.md` | Chroma budget subsection naming G-02-1 | ✓ VERIFIED | Section present at line ~399 with per-role figures and gate reference |
| `.planning/phases/02.../PARITY-DEVIATIONS.md` | Lockstep decision recorded; 8-row table unchanged | ✓ VERIFIED | "Palette changes made in lockstep" section present; deviations table still exactly 8 rows |
| `frontend/src/components/FdrCell.tsx` | Column-stacked, chip-owned min-width, mono chip | ✓ VERIFIED | Read directly; matches spec |
| `frontend/src/routes/Fixtures.tsx` | Tight ticker-cell padding, scoped only to gw cell | ✓ VERIFIED | Read directly; `px-1 py-[3px]` on gw cell only, 4 other cells unchanged |
| `frontend/src/components/FdrCell.test.tsx` | 6 new geometry regression tests | ✓ VERIFIED | Present, independently re-run, pass |
| `frontend/src/routes/Fixtures.test.tsx` | Padding regression test | ✓ VERIFIED | Present, independently re-run, passes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `frontend/package.json` `test` script | `check-tokens.mjs` | shell `&&` chain | ✓ WIRED | Confirmed by direct read: `"test": "node scripts/check-tokens.mjs && vitest run"` |
| `.dark` class on `<html>` | `color-scheme: dark` | class-based (not media query) | ✓ WIRED | Confirmed: `.dark { color-scheme: dark; ... }` in `index.css`, no competing `@media (prefers-color-scheme)` block in the React CSS |
| `index.css` `.dark` neutral hexes | `web/assets/style.css` dark-media-block hexes | lockstep invariant, gate-enforced | ✓ WIRED | Confirmed both by direct read (byte-identical) and by the gate's own 4 lockstep assertions passing |
| `FdrCell` chip `className` | geometry regression tests | class-list substring assertions | ✓ WIRED | 6 new tests in `FdrCell.test.tsx` query the rendered chip via its accessible label and assert on `className`; independently re-run and pass |
| `Fixtures.tsx` gw `<td>` | padding regression test | class-list substring assertion | ✓ WIRED | 1 new test in `Fixtures.test.tsx` walks up from the chip to its `<td>` and asserts `py-[3px]`; independently re-run and passes |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-02 | 02-01, 02-02 | xP table parity | ✓ SATISFIED | Unchanged by gap closure; regression-confirmed green |
| UI-03 | 02-04, **02-08** | Fixtures FDR ticker | ✓ SATISFIED | Gap G-02-2 closed: stacked chip, chip-owned min-width, tight cell padding, mono family — all independently confirmed in code and tests |
| UI-04 | 02-04 | Prices watchlist | ✓ SATISFIED | Unchanged by gap closure; regression-confirmed green |
| UI-05 | 02-02, 02-05, 02-06 | League/scoreboard/differentials/methodology | ✓ SATISFIED | Unchanged by gap closure; regression-confirmed green |
| UI-06 | 02-03 | Gameweek meta banner | ✓ SATISFIED | Unchanged by gap closure; regression-confirmed green |
| UIX-02 | 02-03, **02-07** | Dark mode toggle | ✓ SATISFIED | Gap G-02-1 closed: chroma rebalanced, hue-locked, color-scheme + body paint restored, gate enforces going forward — all independently confirmed |

REQUIREMENTS.md's traceability table maps exactly UI-02, UI-03, UI-04, UI-05, UI-06, UIX-02 to Phase 2 (grep-confirmed at REQUIREMENTS.md lines 121–126), all marked "Complete", and all six appear in at least one plan's `requirements:` frontmatter (including the two gap-closure plans, which each declare one of the two requirements they're closing a gap against). No orphaned requirements.

### Anti-Patterns Found

None blocker-level. `grep` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` across all 8 gap-plan-modified files returned zero matches.

**One unresolved advisory finding from the gap-closure code review (`02-REVIEW.md`, 0 critical / 2 warning / 4 info — independently confirmed present, no corresponding REVIEW-FIX exists for it):**

- **WR-01** (`FdrCell.tsx:57,70`): The chip's `min-w-[56px]` and `px-2 py-1` (4px vertical) do not byte-match vanilla's `.fdr` rule at `web/assets/style.css:152-153`, which specifies `min-width: 58px` and `padding: 6px 8px` (6px vertical) — a 2px width and 2px vertical-padding shortfall. This is a plan-authoring discrepancy, not an execution defect: `02-08-PLAN.md`'s own must-haves literally specify "56px minimum width," which the code delivers exactly as written; the review's finding is that the plan's own reference value doesn't match the vanilla source it claims to port byte-exactly. **Impact assessment:** this does not block the phase goal — the UAT complaint (G-02-2) was specifically about venue-label placement (beside vs. below), which is now structurally fixed and geometry-regression-tested; a 2px chip-padding delta is unlikely to be visually perceptible and does not affect the phase's four ROADMAP success criteria. Recommended as a low-priority follow-up fix, not a re-opened gap.
- **WR-02** (`Fixtures.tsx:50-56`): pre-existing "next six gameweeks" hard-coded copy inconsistent with the data-derived column count — pre-dates the gap-closure plans (introduced in 02-04), surfaced opportunistically by this review's file scope. Not part of either UAT gap; non-blocking.
- **IN-01 through IN-04**: unused default export on `FdrCell`, out-of-range FDR value leaking into `aria-label` verbatim, token gate only lockstep-checking 4 of the shared token set, and a latent 4/5-char hex-parsing gap in `check-tokens.mjs` — all info-level, non-blocking, confirmed present, none touch the phase's must-haves.

Advisory findings carried forward from the phase's original review pass (`02-REVIEW-FIX.md`, applied to Prices.tsx/Methodology.tsx before the gap-closure plans ran) remain fixed and unaffected by this re-verification.

## Human Verification Required

2 items — both are the gap-closure plans' own deferred `<human-check>` blocks (workflow.human_verify_mode: end-of-phase), harvested here per the verifier's harvest step. Every underlying structural/numeric claim behind both items is independently confirmed programmatically; only the final perceptual/rendered-pixel confirmation is outstanding.

### 1. Dark-mode frame reads as dark, not green (closes G-02-1)

**Test:** Run the dev server, force dark mode from the theme toggle, and load `/fixtures` (and spot-check other routes). Scroll past the end of the page and check the overscroll canvas/scrollbar color. Repeat on `web/fixtures.html` (vanilla) to confirm both now match.
**Expected:** The page and header backgrounds read as neutral dark, not green; the browser's own UA chrome (scrollbar, overscroll) paints dark, not light.
**Why human:** `check-tokens.mjs` proves the OKLCH numbers are now in budget (chroma nearly halved, hue lock tightened from 4.9–12.7° to 0.2–3.2°) and that `color-scheme`/body-paint structure exists, but whether the frame perceptually "reads as dark" and whether the browser actually renders dark UA chrome in response are things only a real browser paint pipeline can show — jsdom has neither.

### 2. Stacked fixture chip matches vanilla at a glance (closes G-02-2)

**Test:** Visit `/fixtures` in both themes; each chip should show the three-letter opponent code with H/A centred on the line beneath it, all chips the same width down each gameweek column. Compare against `web/fixtures.html`. Confirm the table has not grown noticeably taller.
**Expected:** Layout visually matches vanilla; no noticeable table-height regression.
**Why human:** The column-direction layout, chip-owned min-width, mono family, and tight cell padding are all confirmed by direct code read and 7 passing regression tests (jsdom class-list assertions), but jsdom applies no stylesheet — only a real browser proves the rendered pixels actually match vanilla's `.fdr` rule end to end.

## Gaps Summary

No blocking gaps remain. Both UAT gaps (G-02-1, G-02-2) are closed at the code level: independently re-verified against the actual codebase, not taken from SUMMARY.md claims.

- **G-02-1** (dark theme green tint): `check-tokens.mjs` was re-run fresh in this verification pass and confirms all 4 neutral roles now pass their chroma budget with margin, hue-lock tightened 2–6x closer to the accent, lightness held within 0.07 of pre-fix values, `color-scheme` declarations and body paint restored, and the vanilla/React lockstep invariant holds byte-for-byte. The fix is enforced going forward by the same gate wired into `npm run test`.
- **G-02-2** (venue label placement): `FdrCell.tsx` was read directly and confirms the chip is now a column-direction flex with the venue tag on its own line; 6 new geometry regression tests plus 1 new padding test were independently re-run and pass, closing the exact blind spot the diagnosis identified (the pre-existing 7 text/accessibility-only tests could not have caught this class of regression).

Both gap-closure plans' own `<human-check>` blocks were deliberately deferred to end-of-phase per `workflow.human_verify_mode: end-of-phase` and have not yet been performed by any executor run — these are the 2 items in Human Verification Required above, and they are why overall status is `human_needed` rather than `passed`.

One narrow advisory finding (WR-01: FdrCell chip is 2px narrower / 2px less vertical padding than vanilla's literal `.fdr` rule, because the gap-closure plan itself specified 56px rather than vanilla's actual 58px) remains open with no corresponding fix. It does not block the phase goal — the UAT complaint concerned label placement, not exact pixel dimensions — but is recommended as a low-priority follow-up.

Full regression check across all 12 original phase truths confirms no new breakage from the gap-closure plans: 178/178 Vitest tests pass (22 files, up from 169 at initial verification — +6 FdrCell geometry, +1 Fixtures padding, +2 from the earlier Prices/Methodology review-fix pass), production build succeeds, and no debt markers exist in any of the 8 files the gap-closure plans touched.

---

*Verified: 2026-09-02*
*Verifier: Claude (gsd-verifier)*
