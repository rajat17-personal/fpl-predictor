---
phase: "02"
slug: "data-layer-non-pitch-pages"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-01"
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) / pytest (backend, existing) |
| **Config file** | frontend/vitest.config.ts |
| **Quick run command** | `npm --prefix frontend run test` |
| **Full suite command** | `npm --prefix frontend run test && npm --prefix frontend run typecheck && bash scripts/verify_frontend_build.sh` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm --prefix frontend run test`
- **After every plan wave:** Run `npm --prefix frontend run test && npm --prefix frontend run typecheck && bash scripts/verify_frontend_build.sh`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T1 (tracer) | 02-01 | 1 | UI-02 | T-02-01, T-02-02, T-02-03 | Ported vanilla template strings render as auto-escaped JSX text; fetch-error detail reaches console only; the 50-row slice bounds render cost | unit + component | `npm --prefix frontend run test -- src/routes/XpTable.test.tsx src/lib/sortable.test.ts src/lib/bandCell.test.ts src/lib/format.test.ts` | created by this task | ⬜ pending |
| T2 | 02-01 | 1 | UI-02 | T-02-01 | Search input is a comparison predicate only, never echoed as markup | unit + component | `npm --prefix frontend run test -- src/routes/XpTable.test.tsx src/lib/usePageMeta.test.tsx` | created by this task | ⬜ pending |
| T3 | 02-01 | 1 | UI-02 | T-02-01 | Injury `news` text renders as escaped children in the tooltip, not as an attribute-injected string | unit + component | `npm --prefix frontend run test -- src/lib/statusFlag.test.tsx src/routes/XpTable.test.tsx` | created by this task | ⬜ pending |
| T1 (checkpoint) | 02-02 | 1 | UI-05 | T-02-SC | Blocking human approval before any dependency enters the tree | manual | MISSING — blocking human gate, no runnable check exists | n/a | ⬜ pending |
| T2 | 02-02 | 1 | UI-05 | T-02-SC | Exact version pins, so the lockfile records precisely what was reviewed | script + suite | `node --input-type=module -e "…exact-pin check…"` then `npm --prefix frontend run test && npm --prefix frontend run typecheck` | n/a (inline script) | ⬜ pending |
| T3 | 02-02 | 1 | UI-02 | T-02-04 | Every intentional deviation is recorded with its reason and originating plan | script | `test -f …/PARITY-DEVIATIONS.md && grep -v '^ *#' … \| grep -cE '^\| *[1-8] *\|' \| grep -qx 8` | created by this task | ⬜ pending |
| T1 | 02-03 | 2 | UIX-02 | T-02-06 | No third-party font request; single dark-mode mechanism | script | `grep -q '@custom-variant dark' … && ! grep -q '@media (prefers' … && ! grep -q 'fonts.googleapis.com' frontend/index.html` plus `bash scripts/verify_frontend_build.sh` | n/a (source gates) | ⬜ pending |
| T2 | 02-03 | 2 | UIX-02 | T-02-05 | A tampered storage value degrades to the operating-system default rather than reaching any evaluation path | unit + component | `npm --prefix frontend run test -- src/lib/theme.test.ts src/components/ThemeToggle.test.tsx` | created by this task | ⬜ pending |
| T3 | 02-03 | 2 | UI-06 | T-02-07 | `meta.json` fields render as escaped children; a failed fetch shows a fixed literal, never the response | unit + component | `npm --prefix frontend run test -- src/lib/deadline.test.ts src/components/GwBanner.test.tsx src/components/PageShell.test.tsx` | created by this task | ⬜ pending |
| T1 | 02-04 | 2 | UI-03 | T-02-08 | Difficulty selects a class from a literal 1–5 map; out-of-range clamps to neutral | component | `npm --prefix frontend run test -- src/components/FdrCell.test.tsx src/routes/Fixtures.test.tsx` | created by this task | ⬜ pending |
| T2 | 02-04 | 2 | UI-04 | T-02-09 | The qualifying mode note renders in the same pass as the numbers it qualifies | component | `npm --prefix frontend run test -- src/routes/Prices.test.tsx` | created by this task | ⬜ pending |
| T1 | 02-05 | 2 | UI-05 | T-02-11 | Fetch-error detail reaches console only | component | `npm --prefix frontend run test -- src/routes/League.test.tsx` | created by this task | ⬜ pending |
| T2 | 02-05 | 2 | UI-05 | T-02-10 | A server failure cannot be presented as "no gameweeks scored yet" | component | `npm --prefix frontend run test -- src/routes/Scoreboard.test.tsx` | created by this task | ⬜ pending |
| T1 | 02-06 | 2 | UI-05 | T-02-13 | Fetch-error detail reaches console only | component | `npm --prefix frontend run test -- src/routes/Differentials.test.tsx` | created by this task | ⬜ pending |
| T2 | 02-06 | 2 | UI-05 | T-02-12 | Markdown renders to real React elements; no raw-markup sink anywhere in the source tree | component + repo gate | `npm --prefix frontend run test -- src/routes/Methodology.test.tsx` and `! grep -rq 'SetInnerHTML' frontend/src` | created by this task | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No separate Wave 0 test-scaffolding pass is needed. The framework gap is already closed: Vitest
4.1.11, @testing-library/react 16.3.3, @testing-library/jest-dom 7.0.1 and jsdom 30.0.1 are
installed and proven by the existing Phase 1 suites (`PageShell.test.tsx`, `ErrorState.test.tsx`,
`Spinner.test.tsx`, `routeIsolation.test.tsx`, `harness.test.tsx`), and `src/test/setup.ts` already
registers `afterEach(cleanup)` plus the jest-dom matchers.

Every test file and every parity fixture this phase's `<automated>` commands reference is created
by the task that runs the command, before that command runs — there is no task whose verify points
at a file no task authors:

- [x] `frontend/src/lib/sortable.test.ts`, `bandCell.test.ts`, `format.test.ts`, `frontend/src/routes/XpTable.test.tsx`, `frontend/src/test/fixtures/xp_table.json` — 02-01 T1
- [x] `frontend/src/lib/usePageMeta.test.tsx` — 02-01 T2
- [x] `frontend/src/lib/statusFlag.test.tsx`, `frontend/src/test/fixtures/captains.json` — 02-01 T3
- [x] `frontend/src/lib/theme.test.ts`, `frontend/src/components/ThemeToggle.test.tsx` — 02-03 T2
- [x] `frontend/src/lib/deadline.test.ts`, `frontend/src/components/GwBanner.test.tsx`, `frontend/src/test/fixtures/meta.json` — 02-03 T3
- [x] `frontend/src/components/FdrCell.test.tsx`, `frontend/src/routes/Fixtures.test.tsx`, `frontend/src/test/fixtures/fixtures.json` — 02-04 T1
- [x] `frontend/src/routes/Prices.test.tsx`, `frontend/src/test/fixtures/watchlist_{official,heuristic,model}.json` — 02-04 T2
- [x] `frontend/src/routes/League.test.tsx`, `frontend/src/test/fixtures/{standings,leaders}.json` — 02-05 T1
- [x] `frontend/src/routes/Scoreboard.test.tsx`, `frontend/src/test/fixtures/scoreboard.json` — 02-05 T2
- [x] `frontend/src/routes/Differentials.test.tsx` — 02-06 T1
- [x] `frontend/src/routes/Methodology.test.tsx` — 02-06 T2

Two fixture shapes are synthesised rather than copied from live data, because the pipeline cannot
produce them yet: the populated `scoreboard.json` (the file does not exist pre-season) and the
`heuristic` / `model` watchlist modes (the export has only ever emitted `official`). Both are
authored against the emitting Python source (`predict/scoreboard.py`, `models/price.py`) rather
than guessed, and the plans make that cross-check an explicit read-first obligation.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Package-legitimacy approval for the four new npm dependencies | UI-05 | A supply-chain trust decision is a human judgement, not a runnable assertion; the gate is deliberately not auto-approvable | Review the audit table in `02-RESEARCH.md`, spot-check any package at `npmjs.com/package/<name>`, and answer approve or reject at plan 02-02 Task 1 |
| No flash of the wrong theme on reload | UIX-02 | The flash happens between the head script and first paint; jsdom has no paint phase and no real reload | With the OS in dark mode and no stored preference, hard-reload the dev server and watch the first frame; repeat after choosing Light and after choosing Dark |
| Dark-theme legibility of the FDR ramp, price trend icons and status flags | UI-03, UI-04, UIX-02 | Colour distinguishability is a perceptual judgement; jsdom computes no colour | Load `/fixtures` and `/prices` with the theme set to Dark and confirm the difficulty ramp still reads easy-to-hard and the rise/fall icons stay distinguishable from each other |
| Pixel geometry of the header containment at wide viewports | UI-06 | jsdom has no layout engine; already handed forward to Phase 4 as gap G-01-3 | Deferred to Phase 4 Playwright per `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or a stated human-gate exemption
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (the only MISSING is the human approval gate, which has no runnable form)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending — set to validated by `/gsd-validate-phase` after execution.
