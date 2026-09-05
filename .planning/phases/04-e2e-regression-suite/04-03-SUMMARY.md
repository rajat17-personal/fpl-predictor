---
phase: 04-e2e-regression-suite
plan: 03
subsystem: testing
tags: [e2e, playwright, fixture-synthesis, fixtures-page, prices-page, chip-timeline, blank-gameweek, double-gameweek]

requires:
  - phase: 04-e2e-regression-suite (plan 01)
    provides: "The immutable e2e/fixtures/v1/normal/ capture (GW3) this plan's synthesis script reads and never writes to"
  - phase: 04-e2e-regression-suite (plan 02)
    provides: "e2e/playwright.config.ts's E2E_VARIANTS-gated chromium-blank/chromium-dgw servers+projects, e2e/helpers/page.ts's gotoReady/GW, and the isolated e2e/ npm project (@playwright/test@1.62.1, typescript@6.0.3, @types/node@26.4.1) this plan installs no new package into"
provides:
  - "e2e/scripts/synthesize-variants.mjs: a zero-dependency Node transform deriving blank/ and dgw/ web-data sets from the immutable normal capture (D-06), reproducible byte-for-byte on re-run"
  - "e2e/fixtures/v1/blank/web-data/ and e2e/fixtures/v1/dgw/web-data/: two committed, immutable variant fixture sets sharing normal's real player names/prices"
  - "e2e/fixtures/v1/MANIFEST.md's Synthesis rules section: the selection rule, both club-code lists, the per-file transform/non-transform list, and the determinism guarantee"
  - "e2e/specs/fixtures-prices.spec.ts: full E2E-05 coverage of the fixtures ticker and price watch pages against the normal fixture set"
  - "e2e/specs/variants/{blank-fixtures,blank-xp-table,dgw-fixtures,dgw-chips}.spec.ts: targeted specs exercising the blank/double-gameweek scenarios on the exact surfaces they change (E2E-01's second/third fixture sets)"
affects: [e2e-suite-wave-4, ci-02, cutover]

actuals:
  tokens: 109400
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One deterministic transform script derives all non-normal fixture scenarios from the single real capture (D-06) -- selection is a plain lexicographic sort on the club `short` code (Array.prototype.sort() with no comparator), never object/iteration order and never randomness, so a second run reproduces byte-identical output"
    - "Variant servers reuse normal/api/ through FPL_FIXTURE_DATA_DIR (wired in 04-02) -- blank/dgw fixture sets need only a web-data/ directory since every surface they change (fixtures ticker, xP table, chip timeline) is a pure /data renderer that never calls the API"
    - "Row/cell locators scope to the specific table cell under test (e.g. cells.nth(3).getByLabel(...)) rather than a page-wide getByLabel/getByText query -- the same opponent code and difficulty can legitimately recur across gameweek columns or other clubs' rows, so an unscoped query is a strict-mode-violation trap, not a passing assertion"
    - "getByText() is case-insensitive substring matching by default in Playwright -- a short legend label like \"Easy\"/\"Hard\" needs { exact: true } or it silently matches an unrelated lowercase occurrence of the same word elsewhere on the page"

key-files:
  created:
    - e2e/scripts/synthesize-variants.mjs
    - e2e/fixtures/v1/blank/web-data/captains.json
    - e2e/fixtures/v1/blank/web-data/chips.json
    - e2e/fixtures/v1/blank/web-data/fixtures.json
    - e2e/fixtures/v1/blank/web-data/leaders.json
    - e2e/fixtures/v1/blank/web-data/meta.json
    - e2e/fixtures/v1/blank/web-data/squad.json
    - e2e/fixtures/v1/blank/web-data/standings.json
    - e2e/fixtures/v1/blank/web-data/watchlist.json
    - e2e/fixtures/v1/blank/web-data/xp_table.json
    - e2e/fixtures/v1/dgw/web-data/captains.json
    - e2e/fixtures/v1/dgw/web-data/chips.json
    - e2e/fixtures/v1/dgw/web-data/fixtures.json
    - e2e/fixtures/v1/dgw/web-data/leaders.json
    - e2e/fixtures/v1/dgw/web-data/meta.json
    - e2e/fixtures/v1/dgw/web-data/squad.json
    - e2e/fixtures/v1/dgw/web-data/standings.json
    - e2e/fixtures/v1/dgw/web-data/watchlist.json
    - e2e/fixtures/v1/dgw/web-data/xp_table.json
    - e2e/specs/fixtures-prices.spec.ts
    - e2e/specs/variants/blank-fixtures.spec.ts
    - e2e/specs/variants/blank-xp-table.spec.ts
    - e2e/specs/variants/dgw-fixtures.spec.ts
    - e2e/specs/variants/dgw-chips.spec.ts
  modified:
    - e2e/fixtures/v1/MANIFEST.md

key-decisions:
  - "Selection rule executed exactly as specified: sort fixtures.json's 20 ticker rows ascending by `short`; first six = BLANK clubs (ARS, AVL, BHA, BOU, BRE, CHE), first four = DOUBLE clubs (ARS, AVL, BHA, BOU) -- recorded verbatim in MANIFEST.md and hardcoded identically in every Task 3 spec."
  - "Synthesised chips.json note strings copied byte-for-byte from predict/live.py's _chip_note wording: blank = \"GW3 has 6 blank clubs — consider Free Hit.\"; double = \"GW3 is a DOUBLE for 4 clubs — consider Bench Boost / Triple Captain.\" -- verified against the live function source, not guessed."
  - "Double-club cycle wraps ARS→AVL→BHA→BOU→ARS (each club's synthetic second fixture opponent is the next club in the sorted list, last wraps to first) -- produces a closed loop with no dangling reference to a club outside the double set."

requirements-completed: [E2E-01, E2E-05]

coverage:
  - id: D1
    description: "Deterministic synthesis script + two committed, reproducible blank/dgw variant fixture sets (E2E-01's second and third fixture sets)"
    requirement: "E2E-01"
    verification:
      - kind: integration
        ref: "node e2e/scripts/synthesize-variants.mjs && git status --porcelain e2e/fixtures/v1 (empty) && git diff --quiet -- e2e/fixtures/v1/normal (clean)"
        status: pass
      - kind: other
        ref: "node one-shot VARIANT SHAPES OK check: 6 blank rows with empty gw3 fixtures + bgw_clubs=6; 4 double rows with 2 gw3 fixture entries + dgw_clubs=4; ZERO DEPENDENCY SCRIPT check (only node: imports)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fixtures ticker + price watch pages, exact frozen values, data-derived gw column count, zero interactive cells (E2E-05)"
    requirement: "E2E-05"
    verification:
      - kind: e2e
        ref: "E2E_VARIANTS=0 npm --prefix e2e run test -- specs/fixtures-prices.spec.ts --project=chromium (2 passed)"
        status: pass
      - kind: other
        ref: "node coverage-grep over fixtures-prices.spec.ts (FIXTURES PRICES COVERAGE OK: difficulty/Likely risers/Likely fallers/data as of present, gws-derived column count confirmed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Targeted blank/double-gameweek specs on the exact surfaces those scenarios change (fixtures ticker, xP table, chip timeline), full three-project suite green in one invocation"
    requirement: "E2E-01"
    verification:
      - kind: e2e
        ref: "npm --prefix e2e run test -- --project=chromium-blank --project=chromium-dgw (4 passed); full npm --prefix e2e run test, all three projects (12 passed)"
        status: pass
      - kind: other
        ref: "grep gate confirms no e2e/specs/variants/* file names a host/port (VARIANT SPECS USE BASEURL); (cd e2e && npx tsc --noEmit -p tsconfig.json) exits 0"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-04
status: complete
---

# Phase 4 Plan 03: Fixture Synthesis + Fixtures/Prices Coverage + Blank/DGW Variants Summary

**Derived the blank and double-gameweek E2E fixture sets from the immutable normal capture with one deterministic, dependency-free Node script, then covered the fixtures ticker and price watch pages end to end and proved the two new scenarios exercise the exact surfaces they change (empty-fixtures em-dash chip, opposite-venue double chips, chip-timeline DGW marker + tooltip) in a real browser.**

## Performance
- **Duration:** ~20min active work
- **Started:** 2026-09-03 (immediately following 04-02)
- **Completed:** 2026-09-04T01:37:13Z
- **Tasks:** 3 (all `type="auto"`, no checkpoints)
- **Files modified:** 24 (23 new, 1 modified — MANIFEST.md's Synthesis rules section)

## Accomplishments

- **Task 1 — Fixture synthesis.** Wrote `e2e/scripts/synthesize-variants.mjs` (plain `node:fs`/`node:path`/`node:url`, zero npm dependencies, matching `frontend/scripts/check-tokens.mjs`'s convention). Selection rule: sort `normal/web-data/fixtures.json`'s 20 ticker rows ascending by `short`; first six (`ARS`, `AVL`, `BHA`, `BOU`, `BRE`, `CHE`) are the BLANK clubs, first four (`ARS`, `AVL`, `BHA`, `BOU`) are the DOUBLE clubs. Blank set: current-GW fixtures emptied for the six blank clubs, `chips.json`'s `bgw_clubs` set to 6 with `_chip_note`'s exact wording, blanked clubs dropped from `xp_table.json`/`captains.json`. Double set: each double club's current-GW `fixtures` array gains a second entry (venue-inverted, `opp` = next club in the cycle `ARS→AVL→BHA→BOU→ARS`, same `fdr`), `chips.json`'s `dgw_clubs` set to 4 with `_chip_note`'s exact wording; `xp_table.json`/`captains.json` left untransformed (documented — a real double week would raise xP, but no double-set spec asserts it). Verified determinism by running the script twice and diffing output directories (byte-identical) and by confirming `git status --porcelain e2e/fixtures/v1` stays empty after a third run on the committed state. Filled MANIFEST.md's previously-empty "Synthesis rules" section with the full rule set, both club lists, and the determinism guarantee.
- **Task 2 — Fixtures + Prices coverage.** `e2e/specs/fixtures-prices.spec.ts` asserts, on the normal fixture set: the fixtures ticker's exact first row (Crystal Palace, xg_next 1.45, xgc_next 1.62, ease 3.33), the header's gameweek column count and labels derived from the committed fixture's own `gws.length` (never hardcoded, per R20), one known chip's full accessible-name wording ("Away vs FUL, difficulty 3"), the difficulty legend, and zero buttons in the table; and on the price watch page: the exact single matching mode note (official, with the 48-locked-players sentence since `locked_players` is truthy), the frozen first riser row (De Cuyper, progress label "114% → 128% tonight") and first faller row (Sánchez, "111% → 120% tonight"), and zero buttons in both price tables.
- **Task 3 — Targeted variant specs.** `blank-fixtures.spec.ts`: all six blank clubs render the `Blank gameweek` em-dash chip on their current-GW cell; a control club (Crystal Palace) still renders its normal fixture chip. `blank-xp-table.spec.ts`: no visible row's team column shows a blanked club code, the top-50 slice still applies, and the blank set's own first row (unaffected — B.Fernandes/MUN is not a blanked club) asserts correctly. `dgw-fixtures.spec.ts`: all four doubled clubs render exactly two opposite-venue chips; the control club still renders exactly one. `dgw-chips.spec.ts`: the `Why GW3` heading, the exact double-week note wording, the current-GW timeline marker's `... double gameweek` accessible name and `DGW` caption, and the click-revealed `4 clubs affected` tooltip. Full three-project suite (12 tests: 2 smoke + 4 shell-geometry + 2 fixtures-prices on `chromium`, 2 on `chromium-blank`, 2 on `chromium-dgw`) passes in one `npm --prefix e2e run test` invocation.
- Re-ran `npm --prefix frontend run test` (363 passed, including the token-budget gate) and the full pytest suite (76 passed) after all three commits — neither regressed.

## Task Commits
1. **Task 1: Synthesise the blank and double-gameweek fixture sets** — `157726a` (feat)
2. **Task 2: Cover the fixtures ticker and price watch pages on the normal set** — `5b59bfa` (test)
3. **Task 3: Targeted blank and double-gameweek specs** — `4643b3d` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `e2e/scripts/synthesize-variants.mjs` — the deterministic transform (see Accomplishments)
- `e2e/fixtures/v1/blank/web-data/*.json` (9 files) — blank variant set
- `e2e/fixtures/v1/dgw/web-data/*.json` (9 files) — double-gameweek variant set
- `e2e/fixtures/v1/MANIFEST.md` — Synthesis rules section filled in
- `e2e/specs/fixtures-prices.spec.ts` — normal-set fixtures/prices coverage (2 tests)
- `e2e/specs/variants/blank-fixtures.spec.ts`, `blank-xp-table.spec.ts`, `dgw-fixtures.spec.ts`, `dgw-chips.spec.ts` — targeted variant specs (4 tests)

## Decisions Made
See `key-decisions` in frontmatter — the selection rule's resulting club lists and the exact synthesised note strings are the load-bearing facts every Task 3 spec hardcodes.

## Deviations from Plan

**1. [Rule 1 - bug in own draft, fixed before commit] `page.getByLabel(...)` and unscoped `page.getByText(...)` calls were ambiguous across repeated content**
- **Found during:** Task 2, first test run of `fixtures-prices.spec.ts`.
- **Issue:** `page.getByLabel("Away vs FUL, difficulty 3")` matched 3 elements (Crystal Palace's GW3 cell plus two unrelated future-gameweek cells for other clubs that also happen to face Fulham at difficulty 3), triggering a Playwright strict-mode violation. Separately, `page.getByText("Easy")`/`"Hard"` matched the fixtures page's own intro paragraph (which contains lowercase "easy"/"hard" as prose) because Playwright's text matcher is case-insensitive substring by default.
- **Fix:** Scoped the chip assertion to the specific first-row/current-gw `<td>` (`cells.nth(3).getByLabel(...)`) instead of a page-wide query, and added `{ exact: true }` to the legend label assertions.
- **Files modified:** `e2e/specs/fixtures-prices.spec.ts` (spec-only, no production code touched)
- **Verification:** re-ran the spec — both tests pass
- **Commit:** `5b59bfa` (fixed before the commit was made; no separate corrective commit needed)

**Total deviations:** 1 (spec-authoring correction, caught and fixed during the same task's verification loop, before any commit).
**Impact:** None on production code or the fixture contract — both fixes are locator-specificity corrections within the test file itself.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None. Local runs need `E2E_PYTHON` set to the conda interpreter, exactly as established in 04-02 — no new environment requirement introduced by this plan.

## Next Phase Readiness

E2E-01 (all three fixture sets: normal, blank, double) and E2E-05 (fixtures + prices pages) are now fully closed. `e2e/fixtures/v1/blank/` and `e2e/fixtures/v1/dgw/` are immutable from this point forward — any future contract change cuts a `v2` set alongside `v1`, never edits these in place. Remaining phase scope (per `04-CONTEXT.md`): E2E-02 (team/pitch + solver flow), E2E-03 (xP table + captains with sort order), E2E-04 (rate-my-team end to end), each their own later plan/wave. No blockers.

## Self-Check: PASSED

- `e2e/scripts/synthesize-variants.mjs` — FOUND
- `e2e/fixtures/v1/blank/web-data/*.json` (9 files) — FOUND
- `e2e/fixtures/v1/dgw/web-data/*.json` (9 files) — FOUND
- `e2e/specs/fixtures-prices.spec.ts` — FOUND
- `e2e/specs/variants/{blank-fixtures,blank-xp-table,dgw-fixtures,dgw-chips}.spec.ts` — FOUND
- `git log --oneline --all --grep="04-03"` — commits `157726a`, `5b59bfa`, `4643b3d` all carry a `(04-03)` scope and are present in `git log --oneline -5`
- Re-ran all acceptance criteria for Tasks 1-3: all pass (determinism gate empty diff, VARIANT SHAPES OK, ZERO DEPENDENCY SCRIPT, FIXTURES PRICES COVERAGE OK, VARIANT SPECS USE BASEURL, `(cd e2e && npx tsc --noEmit -p tsconfig.json)` exits 0)
- Re-ran plan-level `<verification>`: `node e2e/scripts/synthesize-variants.mjs` leaves the tree clean and `normal/` untouched; full `npm --prefix e2e run test` (all three projects) green — 12 passed; no spec under `e2e/specs/variants/` names a host or port; `npm --prefix frontend run test` unaffected (363 passed); full pytest suite unaffected (76 passed)
