---
phase: 02-data-layer-non-pitch-pages
verified: 2026-09-01T00:00:00Z
status: human_needed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Reload the app while `localStorage['fpl-theme']` is unset and the OS is in dark mode."
    expected: "No flash of the light theme before dark styling applies (the pre-mount head script in `frontend/index.html` should make the dark class present on `<html>` before first paint)."
    why_human: "jsdom (Vitest's test environment) has no paint pipeline; only a real browser can show whether a flash occurs. `theme.test.ts`/`ThemeToggle.test.tsx` prove the resolution logic is correct but not that the browser paints correctly before the flash window closes."
  - test: "Visit `/fixtures` in both light and dark theme and look at the 1-5 difficulty ramp and the legend row."
    expected: "The ramp reads unambiguously easy-to-hard at a glance in both themes. Note: the vanilla site's own ramp (and this port, which copies its hex values verbatim) is blue-to-red, not literal green-to-red — confirm this is what the ROADMAP's 'standard 1–5 green→red convention' phrase intended, since it does not literally match either the vanilla source or the port."
    why_human: "Color perception and 'does this read clearly as a difficulty ramp' cannot be asserted from a DOM class name; FdrCell.test.tsx only proves each difficulty level maps to a distinct token class, not that a human perceives the ramp as intended."
  - test: "Visit `/prices` in both themes and confirm the TrendingUp/TrendingDown icons on riser/faller rows are visually distinguishable at a glance."
    expected: "Riser (accent) and faller (destructive) icons read as clearly different colors/directions in both light and dark themes."
    why_human: "Prices.test.tsx proves the icons never cross tables and use distinct token classes, not that they are visually distinguishable to a human eye."
  - test: "Visit `/differentials` and drag the ownership slider across its full 1-25% range, especially near the low end."
    expected: "Band widths rescale sensibly; the `maxHi = Math.max(1, ...)` floor (R40) should visibly prevent the band track from filling the whole cell width when every qualifying player's p90/xp value is small."
    why_human: "Differentials.test.tsx proves the floor changes the scaling denominator mathematically, but only a human eye in a real browser can confirm the rendered result 'looks right' at low caps."
  - test: "With the dev proxy running and `web/data/scoreboard.json` genuinely absent (pre-season), visit `/scoreboard`."
    expected: "The pre-season zero-state (three backtest tiles + paragraph) renders — not an error state — proving the 404-vs-server-failure distinction works end-to-end through the real proxy, not just against a mocked `fetch`."
    why_human: "Scoreboard.test.tsx mocks `fetch` directly for the 404/500/network-failure cases; only a live proxy request against a genuinely missing file exercises the real HTTP path."
---

# Phase 2: Data Layer & Non-Pitch Pages Verification Report

**Phase Goal:** Seven of the eight pages render at verified parity with the vanilla site from the same JSON contract
**Verified:** 2026-09-01
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | xP table (`/`) sorts, filters, and formats identically to vanilla, checked against an enumerated rule inventory (R1–R19), not by eyeball | ✓ VERIFIED | `frontend/src/lib/sortable.ts`'s comparator is a byte-for-byte port of `web/assets/app.js:71-75` (`dir * ((y ?? -1e9) - (x ?? -1e9))` numeric, `dir * String(y ?? "").localeCompare(String(x ?? ""))` string) — independently diffed against the vanilla source in this review. `format.ts`'s `fixed1`/`fixed2`/`orDash`/`localeInt` match the exact per-call-site precision (`toFixed(1)`/`toFixed(2)`) verified against `web/index.html`. `XpTable.test.tsx` (27 tests) exercises sort polarity, position/search filter AND-composition, the top-50 slice-not-resort, band-cell fallbacks, and the Captain picks divergent-fallback sub-table. |
| 2 | Fixtures page (`/fixtures`) shows an FDR ticker in the 1–5 easy→hard convention | ✓ VERIFIED | `FdrCell.tsx` uses an explicit literal 1–5 token map (`FDR_CLASSES`), never string-interpolated class names; blank-gameweek em-dash with neutral difficulty-3 styling; gameweek column count is data-derived (`data[0].gws.map(...)`), not hard-coded to six. Colors are ported verbatim from `web/assets/style.css`'s `--fdr{1-5}-bg/-ink` hex values (confirmed identical in `index.css`). `FdrCell.test.tsx` + `Fixtures.test.tsx` assert five distinct classes and the dynamic column count. |
| 3 | Prices page (`/prices`) shows watchlist rise/fall indicators matching vanilla's calls | ✓ VERIFIED | `computeProgress()` in `Prices.tsx` ports vanilla's `raw`/`pct`/`bar` math verbatim (bar clamped at 100%, label not); `TrendingUp`/`TrendingDown` icons render on riser/faller rows respectively (ledger entry 5). `Prices.test.tsx` covers the 114%-clamped case, all three mode notes, and icon separation. One narrow gap: `ModeNote`'s "model" branch force-unwraps `w.val_moved_hit!` without a null guard — see code-review WR-01 below (currently unreachable in production since the pipeline only emits `official` mode). |
| 4 | League, scoreboard, differentials, and methodology pages present the same information as their vanilla counterparts from the same JSON files | ✓ VERIFIED | `League.tsx`: array-position rank (`i + 1`), vanilla GD sign rule (`gd > 0 ? "+"+gd : String(gd)`), five fixed leader boards with 8-entry cap + `Nothing yet this season` fallback — all match `web/league.html`. `Scoreboard.tsx`: dedicated `fetchScoreboard()` distinguishing 404 (zero-state) from any other failure (ErrorState) — verified more discriminating than vanilla's blanket `try/catch`, by design (D-08). `Differentials.tsx`: `(ownership ?? 100) <= cap && status === "a"` filter, 30-row slice, `Math.max(1, ...)` floor kept structurally distinct from the xP table's un-floored `maxHi`. `Methodology.tsx`: verbatim markdown bundled via `?raw` import, rendered through `react-markdown` with no raw-HTML sink (grep-verified: `! grep -rq 'SetInnerHTML' frontend/src` passes). |
| 5 | Every route shows a persistent gameweek meta banner (UI-06) fed by one shell-owned `meta.json` query | ✓ VERIFIED | `PageShell.tsx` owns the single `["meta"]` query and passes it to `GwBanner`; four states (loading/future/passed/failed) implemented in `GwBanner.tsx`/`deadline.ts`, tested in `GwBanner.test.tsx`/`deadline.test.ts` (22 tests total). |
| 6 | Three-state Light/Dark/System toggle (UIX-02) persists and resolves correctly | ✓ VERIFIED | `theme.ts`'s `resolveTheme`/`useTheme` and `ThemeToggle.tsx` match the UI-SPEC contract: localStorage persistence with try/catch degrade-to-session-only, live `matchMedia` tracking while `system`, idempotent class application. 15 tests across `theme.test.ts`/`ThemeToggle.test.tsx`. The pre-mount `index.html` head script and `useTheme` read the identical storage key with identical unknown-value coercion, so they cannot disagree. |
| 7 | Complete `web/data/*.json` TypeScript interface set exists in `lib/api.ts`; no later plan re-edited it | ✓ VERIFIED | 13 interfaces landed in plan 02-01; `git log` shows only 02-04/02-05 made narrow, justified field-optionality widenings (`WatchlistRow.prob`/`proj_tonight`, `ScoreboardSummary.mae_fpl`/`spearman_fpl`) after cross-checking `models/price.py`/`predict/scoreboard.py` directly — no structural re-edit. |
| 8 | `PARITY-DEVIATIONS.md` exists with all eight seeded deviations plus an append rule | ✓ VERIFIED | File present at the D-04 path with 8 numbered rows (deviation/reason/introducing-plan) and a stated "Appending an entry" rule; read directly, contents match the seed table. |
| 9 | Full frontend Vitest suite, typecheck, and production build-purity gate all pass | ✓ VERIFIED | Independently re-run (not taken from SUMMARY claims): `npm --prefix frontend run test` → 169/169 passed (22 test files); `npm --prefix frontend run typecheck` → clean, no `error TS` lines; `bash scripts/verify_frontend_build.sh` → prints `BUILD PURITY OK`. |
| 10 | Regression gate: Phase 1 API pytest suite + Phase 1 frontend tests unaffected | ✓ VERIFIED | Independently re-run: `pytest tests/ -k "api or test_api"` → 42 passed, 0 failed (Phase 1 `test_api.py` contract, auth-stub, and concurrency tests all still pass). Frontend regression is folded into the 169/169 total above (`PageShell.test.tsx`, `Spinner.test.tsx`, `ErrorState.test.tsx`, `routeIsolation.test.tsx`, `harness.test.tsx` all present and green). |
| 11 | No raw-HTML injection sink exists anywhere in `frontend/src` | ✓ VERIFIED | `! grep -rq 'SetInnerHTML' frontend/src` passes; `Methodology.tsx` uses `react-markdown`'s default (escaping) renderer with a `components` override that adds only token classes, never a raw-markup escape hatch. `Methodology.test.tsx` asserts script-shaped markdown text renders as escaped visible text. |
| 12 | No unresolved debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) in phase-modified files | ✓ VERIFIED | `grep -rnE "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` across `frontend/src/{routes,components,lib}` (excluding test files) returns no matches. |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/api.ts` | 13-interface `web/data/*.json` TypeScript contract | ✓ VERIFIED | Present, typechecks, consumed unchanged by all 6 route files |
| `frontend/src/lib/sortable.ts` / `.test.ts` | Ported comparator + hook | ✓ VERIFIED | Matches vanilla byte-for-byte; tests pass |
| `frontend/src/lib/bandCell.ts`, `components/BandCell.tsx` | Band geometry/tooltip + component | ✓ VERIFIED | CSS `calc()` width (not pre-subtracted number); reused by XpTable + Differentials |
| `frontend/src/lib/format.ts` | fixed1/fixed2/orDash/localeInt primitives | ✓ VERIFIED | Matches vanilla per-call-site precision |
| `frontend/src/lib/statusFlag.tsx` | Accessible status-flag tooltip | ✓ VERIFIED | Reused by XpTable and Differentials with identical trigger/mapping |
| `frontend/src/lib/usePageMeta.ts` | 8-route title/description table | ✓ VERIFIED | grep-gated to exactly 8 `description:` entries |
| `frontend/src/lib/theme.ts`, `components/ThemeToggle.tsx` | Dark-mode hook + control | ✓ VERIFIED | Class-based single mechanism, complete dark palette |
| `frontend/src/lib/deadline.ts`, `components/GwBanner.tsx` | Countdown/freshness formatters + chip | ✓ VERIFIED | Four-state chip, live countdown, graceful degradation |
| `frontend/src/components/FdrCell.tsx` | FDR difficulty cell | ✓ VERIFIED | Literal 1-5 token map, blank-gameweek handling |
| `frontend/src/routes/{XpTable,Fixtures,Prices,League,Scoreboard,Differentials,Methodology}.tsx` | 7 fully-ported routes | ✓ VERIFIED | All read directly; each matches its vanilla source's cited line ranges |
| `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` | 8-entry deviation ledger | ✓ VERIFIED | Present, 8 rows + append rule |
| `frontend/src/content/methodology.md` | Verbatim markdown port | ✓ VERIFIED | All four receipt figures present (`0.87 vs FPL 1.07`, `0.74 vs FPL 0.30`, `2260`, `+102`), matching `web/methodology.html` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `/data/xp_table.json` | rendered rows | `fetchJson` → `slice(0,50)` → filter → `sortRows` → `BandCell` | ✓ WIRED | Confirmed in `XpTable.tsx`; slice happens before sort per R10 |
| `/data/xp_table.json` | Differentials rows | same `["xp_table"]` query key → local filter/slice | ✓ WIRED | Confirmed shared cache key in `Differentials.tsx` |
| `frontend/index.html` head script | `<html class="dark">` | `localStorage` read + `matchMedia` | ✓ WIRED | Confirmed same storage key/coercion as `useTheme` |
| `/data/meta.json` | `GwBanner` | single `PageShell`-owned query | ✓ WIRED | Confirmed in `PageShell.tsx` — one query, passed as props |
| `/data/watchlist.json` `mode` | `ModeNote` branch + progress label branch | shared `w.mode` field | ✓ WIRED | Confirmed both branches keyed on the same field in `Prices.tsx` |
| `/data/fixtures.json` | `FdrCell` | `FixtureTickerTeam[]` → per-gw `<FdrCell gw={g}>` | ✓ WIRED | Confirmed in `Fixtures.tsx` |
| `/data/scoreboard.json` 404 | pre-season zero-state | dedicated `fetchScoreboard()` status branch | ✓ WIRED | Confirmed `res.status === 404` → `null` → zero-state; all other non-ok → thrown Error → ErrorState |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-02 | 02-01, 02-02 | xP table parity | ✓ SATISFIED | Sort/filter/format/captain-picks all ported and tested |
| UI-03 | 02-04 | Fixtures FDR ticker | ✓ SATISFIED | Data-derived columns, literal token map, blank-gw handling |
| UI-04 | 02-04 | Prices watchlist | ✓ SATISFIED | Progress math, mode notes, trend icons (WR-01 narrow edge-case noted below) |
| UI-05 | 02-02, 02-05, 02-06 | League/scoreboard/differentials/methodology | ✓ SATISFIED | All four routes ported and tested |
| UI-06 | 02-03 | Gameweek meta banner | ✓ SATISFIED | Shell-owned single query, 4-state chip |
| UIX-02 | 02-03 | Dark mode toggle | ✓ SATISFIED | Class-based, persisted, complete palette |

No orphaned requirements: REQUIREMENTS.md's traceability table maps exactly UI-02, UI-03, UI-04, UI-05, UI-06, UIX-02 to Phase 2, and all six appear in at least one plan's `requirements:` frontmatter.

### Anti-Patterns Found

None (blocker-level). `grep` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and for stub/coming-soon copy across `frontend/src/{routes,components,lib}` (excluding tests) returned zero matches.

**Advisory findings carried forward from `02-REVIEW.md` (0 critical / 2 warning / 3 info) — none block the roadmap success criteria, all independently confirmed present in the code during this verification:**

- **WR-01** (`Prices.tsx:92`): The "model"-mode price note force-unwraps `w.val_moved_hit!` without a null guard (its sibling field `trained_utc` is safely optional-chained). If a `model`-mode payload ever omits `val_moved_hit`, this silently renders `"NaN%"` instead of failing loudly or falling back. Currently unreachable — the live pipeline only ever emits `official` mode — but the type declares the field optional, so the guard gap is real. Confirmed present at the cited line.
- **WR-02** (`Methodology.tsx:41`): The markdown renderer's `a` component override renders a plain `<a href="/scoreboard">` instead of react-router's `<Link>`, so the one internal link on the methodology page triggers a full page reload rather than a client-side transition — inconsistent with every other internal link in the phase. Confirmed present at the cited line.
- **IN-01/IN-02/IN-03**: no-runtime-validation-on-fetch, name-keyed (not id-keyed) price table rows, and an empty-but-present captains array rendering an empty table shell rather than a fallback message — all info-level, non-blocking, confirmed present.

**UI-REVIEW.md (20/24) findings — shell-layer polish, not goal-blocking:**

- `frontend/src/components/PageShell.tsx:42` — `gap-[18px]` is not a multiple of 4 (violates the UI-SPEC's own 4px spacing-scale contract; UI-REVIEW's internal severity scale calls this "BLOCKER" against that contract, but it does not block any of the four ROADMAP success criteria — the header still renders and functions correctly). Confirmed present.
- `frontend/src/components/PageShell.tsx:43` — `text-[1.25rem]` duplicates the already-declared `text-heading` token instead of using it. Confirmed present.

Neither shell-layer finding affects data correctness, sort/filter/format parity, or page content — they are visual-consistency debt in the header chrome, appropriately scored down by the UI reviewer but not phase-goal-blocking.

## Human Verification Required

5 items — all visual-appearance or live-browser checks that the plans themselves flagged as non-gating manual spot checks (`human_judgment: true` in each SUMMARY's coverage table) and that cannot be proven by grep or jsdom-based Vitest assertions. Automated coverage of the underlying logic for each of these is green; only the final visual/live-network confirmation is outstanding.

### 1. Dark-mode flash-free reload

**Test:** Reload the app with no stored theme preference and the OS set to dark mode.
**Expected:** No flash of the light theme before dark styling applies.
**Why human:** jsdom has no paint pipeline; `theme.test.ts` proves the resolution logic is correct, not that the browser paints correctly before the flash window closes.

### 2. FDR ticker color-ramp readability

**Test:** Visit `/fixtures` in both light and dark themes; look at the 1–5 difficulty ramp and legend.
**Expected:** The ramp reads unambiguously easy-to-hard at a glance. Note the vanilla source (and this verbatim port) uses a blue→red ramp, not literal green→red — confirm this matches the intent behind the ROADMAP phrase "standard 1–5 green→red convention."
**Why human:** Color perception cannot be asserted from a DOM class name.

### 3. Price-watch trend-icon distinguishability

**Test:** Visit `/prices` in both themes; check the TrendingUp/TrendingDown icons on riser/faller rows.
**Expected:** Riser and faller icons read as clearly distinct at a glance in both themes.
**Why human:** Tests prove the icons never cross tables and use distinct token classes, not that they are visually distinguishable.

### 4. Differentials band-scale visual sanity at low ownership caps

**Test:** Visit `/differentials` and drag the ownership slider across its full range, especially near the low end.
**Expected:** Band widths rescale sensibly; the `Math.max(1, ...)` floor should visibly prevent bands from over-filling when all qualifying players have small xP values.
**Why human:** The math is proven correct by an automated test; only a human eye in a real browser can confirm it "looks right."

### 5. Scoreboard 404-vs-error distinction against the real dev proxy

**Test:** With the dev proxy running and `web/data/scoreboard.json` genuinely absent (pre-season), visit `/scoreboard`.
**Expected:** The pre-season zero-state renders (not an error).
**Why human:** Vitest mocks `fetch` directly; only a live proxy request against a truly missing file exercises the real HTTP path end to end.

## Gaps Summary

No blocking gaps. All 12 observable truths derived from the phase's four ROADMAP success criteria plus its two requirement-driven cross-cutting features (UI-06, UIX-02) are verified against the actual codebase — independently re-run test suite (169/169), typecheck (clean), build-purity gate (`BUILD PURITY OK`), and the Phase 1 regression gate (42/42 API tests) all confirmed fresh, not taken from SUMMARY claims. Source code for all seven ported routes plus the shared sort/format/band/status-flag utilities was read directly and cross-diffed against the vanilla `web/` source for the highest-risk parity rules (sort comparator polarity, number-format precision, FDR token mapping, watchlist progress math) and found to match exactly.

The phase carries five inherently-visual or live-network items that no static analysis or jsdom test can settle — these were already self-flagged by the executor as non-gating manual spot checks in each plan's own `<verification>` section, and are surfaced here for an explicit human pass before the phase is considered fully closed out. Two advisory code-review warnings (an un-guarded field in an as-yet-unreachable watchlist mode, and an internal link that bypasses client-side routing) and two UI-review spacing/typography findings in the shell header are real but narrow, do not block any of the four ROADMAP success criteria, and are recommended (not required) fixes.

---

*Verified: 2026-09-01*
*Verifier: Claude (gsd-verifier)*
