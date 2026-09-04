---
phase: 04-e2e-regression-suite
verified: 2026-09-04T02:15:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "With FPL_FIXTURE_DIR unset, api/main.py behaves exactly as it does today (plan 04-01 must-have) — CR-01"
    - "The suggested incoming player renders as a ghost card in the same formation row as the outgoing player (plan 04-06 must-have) — ghost/bench-row placement"
  gaps_remaining: []
  regressions: []
---

# Phase 4: E2E Regression Suite Verification Report

**Phase Goal:** The critical user flows are protected by browser tests that pass or fail on code,
never on the calendar

**Verified:** 2026-09-04
**Status:** passed
**Re-verification:** Yes — after gap closure (plans 04-07, 04-08)

## Goal Achievement

### Observable Truths (Roadmap Success Criteria, E2E-01..05)

| # | Truth (ROADMAP.md SC) | Status | Evidence |
|---|------------------------|--------|----------|
| 1 | Frozen versioned JSON snapshots (normal, blank, double GW) plus a mocked FPL API back every test — no live-data dependence | ✓ VERIFIED | `python e2e/scripts/capture_fixtures.py --verify` re-run this session: `[verify] OK: gw=3, 6 pool files, xp_table non-empty, picks_event2.json has 15 picks, no upstream URLs`, exit 0. `e2e/fixtures/v1/**` tracked (41 files, previously confirmed not gitignored). CR-01's env-toggle leak (the thing that could have made fixture mode "stick" across an in-process reload, defeating the calendar-independence claim) is now closed — see truth 2. |
| 2 | Team/pitch + solver flow covered end to end: load squad, request solve, assert resulting XI and transfers | ✓ VERIFIED | `e2e/specs/team-solver.spec.ts` + `team-plan.spec.ts` unchanged by either gap-closure plan (not in `files_modified` of 04-07 or 04-08); backstopped explicitly in 04-07's `must_haves.truths` (verification: backstop) and re-confirmed by the full pytest suite (77 passed, includes `test_solve_transfers_response_is_a_legal_squad`, `test_plan_endpoint_returns_horizon_weeks` inside `tests/test_fixture_mode.py`, re-run this session). |
| 3 | The xP table and captains view are covered, asserting exact cell values and sort order rather than "a table rendered" | ✓ VERIFIED | `e2e/specs/xp-table.spec.ts` unchanged by either gap-closure plan; backstopped explicitly three times in 04-08's `must_haves.truths` (adjacency, empty, ordering edges — verification: backstop), consistent with the file not appearing in either plan's `files_modified`. |
| 4 | Rate-my-team flow covered end to end | ✓ VERIFIED | The specific defect that made this flow's own diff assertion false (ghost card landing in a different `role="group"` than the outgoing player for a benched sell) is fixed. `RateDiff.tsx`'s `resolveRateOverlay` now derives `ghost.row` from the matched sell row (`starting:false → "BENCH"`), and `Pitch.tsx`'s Bench `PitchRow` is wired with `{...rowGhost("BENCH")}` (both grepped directly in this session). Independently re-ran the isolated spec: `E2E_PYTHON=... E2E_VARIANTS=0 E2E_PORT=8140 npm --prefix e2e run test -- specs/rate-my-team.spec.ts --project=chromium` → **5 passed**, including the visual-diff test's Bench-group co-membership and cell-adjacency assertion (`ghostIdx === outIdx + 1`, grepped in `e2e/specs/rate-my-team.spec.ts:234-248`). |
| 5 | The fixtures and prices pages are covered | ✓ VERIFIED | `e2e/specs/fixtures-prices.spec.ts` + 4 variant specs under `e2e/specs/variants/` unchanged by either gap-closure plan; backstopped explicitly in 04-07's `must_haves.truths` (verification: backstop). |

**Score:** 5/5 roadmap success criteria verified. Both previously-failing plan-level must-haves
(CR-01's restore path, the ghost/bench-row placement) are independently re-confirmed fixed —
see Gaps Closed below.

### Gaps Closed (from prior VERIFICATION.md, commit 119040c)

| # | Prior Gap | Fix Plan | Independent Re-Verification |
|---|-----------|----------|------------------------------|
| 1 | CR-01: `api/main.py`'s fixture seam never restored `predict.live._gw_pool` on an env-unset reload after fixture mode had been entered — falsified plan 04-01's must-have | 04-07 | Re-ran the exact CR-01 repro script from the plan's own `<verify>` block in-process this session: `RESTORE OK` printed, confirming `predict.live._gw_pool`, `api.main._gw_pool`, and `api.main._load_live` are all restored to the original production objects (object identity) after a set→reload→unset→reload cycle. Read the fix directly in `api/main.py` (capture-once `hasattr(live, "_gw_pool_production")` guard placed ahead of the `if _FIXTURE_ROOT:` branch, explicit `else:` restoring all three bindings). `tests/test_fixture_mode.py` now carries `_ORIGINAL_GW_POOL` (discriminated by `__module__`), a teardown identity assertion, and a dedicated `test_unset_env_restores_the_production_gw_pool` — grepped, all present. Full pytest suite re-run: **77 passed** (up from 76 baseline). |
| 2 | Ghost card rendered in a different `role="group"` than the outgoing player for the real capture's own benched sell target (Mateta) — falsified plan 04-06's must-have | 04-08 | Grepped `"BENCH"` directly into `Pitch.tsx` (union member + `rowGhost("BENCH")` wiring on the Bench row) and `RateDiff.tsx` (`resolveRateOverlay`'s ordered row-derivation rule). Independently re-ran `e2e/specs/rate-my-team.spec.ts` in isolation against a fresh build + fixture-mode server this session: **5 passed**, including the adjacency proof (`ghostIdx === outIdx + 1` inside the Bench `role="group"`). `WINDOWS.md` id=2 confirmed `status: fixed` with a `resolved_at` timestamp via `gsd-tools windows status` (`open_count: 1`, `fixed_count: 1`); id=1 (unrelated Phase 1 typecheck no-op) untouched. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/main.py` fixture seam | Restores all three bindings when `FPL_FIXTURE_DIR` is unset | ✓ VERIFIED | Capture-once guard + explicit `else:` restore, read directly; CR-01 repro script prints `RESTORE OK` |
| `tests/test_fixture_mode.py` | Proves the restore, not just the fixture-mode-ON path | ✓ VERIFIED | 10/10 passed (re-run this session); `_ORIGINAL_GW_POOL`, teardown identity assertion, dedicated regression test all present |
| `frontend/src/components/pitch/Pitch.tsx` | Ghost mechanism keyed off sell target's actual row (incl. bench) | ✓ VERIFIED | `"BENCH"` union member + `rowGhost("BENCH")` on the Bench row, grepped |
| `frontend/src/components/RateDiff.tsx` | `resolveRateOverlay` derives ghost row from the matched sell row | ✓ VERIFIED | Ordered rule (bench sell → BENCH, starter → own row, unresolved → buy fallback), grepped |
| `e2e/specs/rate-my-team.spec.ts` | Asserts same-group + adjacency for the real bench-sell capture | ✓ VERIFIED | 5/5 passed in isolated re-run; adjacency assertion present |
| `.planning/WINDOWS.md` | id=2 fixed | ✓ VERIFIED | `gsd-tools windows status`: `open_count: 1`, `fixed_count: 1`, id=2 `status: fixed` with `resolved_at` |
| `e2e/fixtures/v1/**` | Byte-identical, untouched by gap closure | ✓ VERIFIED | `capture_fixtures.py --verify` exits 0 with the same GW/counts as the original phase run |
| All 8 phase `SUMMARY.md` files | Present | ✓ VERIFIED | `ls` confirms 04-01 through 04-08 SUMMARY.md all present |

### Full Test Suite Re-Runs (this session)

| Suite | Command | Result | Status |
|-------|---------|--------|--------|
| Python (full) | `python -m pytest -q` | `77 passed` | ✓ PASS |
| Python (fixture-mode only) | `python -m pytest tests/test_fixture_mode.py -q` | `10 passed` | ✓ PASS |
| CR-01 repro | in-process set→reload→unset→reload identity check | `RESTORE OK` | ✓ PASS |
| Frontend (Vitest, full) | `npx vitest run` (in `frontend/`) | `368 passed` (38 files) | ✓ PASS |
| E2E (rate-my-team, isolated) | `E2E_PYTHON=... E2E_VARIANTS=0 E2E_PORT=8140 npm --prefix e2e run test -- specs/rate-my-team.spec.ts --project=chromium` | `5 passed` | ✓ PASS |
| Fixture coherence | `python e2e/scripts/capture_fixtures.py --verify` | `[verify] OK: gw=3, 6 pool files, ...` | ✓ PASS |
| WINDOWS ledger | `gsd-tools windows status` | `open_count: 1, fixed_count: 1` | ✓ PASS |

Full 3-project (normal/blank/dgw) Playwright suite (42 specs) was not re-run in full this session
— per the task's environment notes, a full run takes several minutes and both SUMMARY.md (04-08)
and the prior verification session already recorded 42/42 green after these exact changes. The
one spec directly implicated by the closed gaps (`rate-my-team.spec.ts`) was re-run in isolation
above and passed 5/5, which is the targeted evidence that actually discriminates the fix from the
prior failure.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| E2E-01 | 04-01, 04-02, 04-03, 04-07 | Fixture strategy — frozen normal/blank/dgw + no live-data dependence, including the env-unset restore path | ✓ SATISFIED | Fixture `--verify` re-run green; CR-01 restore re-verified in-process |
| E2E-02 | 04-05 | Team/pitch + solver flow regression test | ✓ SATISFIED | Unchanged by gap closure; backstopped explicitly, pytest suite green |
| E2E-03 | 04-04 | xP table + captains rendering/sorting regression test | ✓ SATISFIED | Unchanged by gap closure; backstopped explicitly (3 edges) |
| E2E-04 | 04-06, 04-08 | Rate-my-team flow regression test, including the same-row/adjacency ghost fix | ✓ SATISFIED | `rate-my-team.spec.ts` re-run 5/5 in isolation this session; WINDOWS.md id=2 fixed |
| E2E-05 | 04-03 | Fixtures and prices pages regression tests | ✓ SATISFIED | Unchanged by gap closure; backstopped explicitly |

No orphaned requirements: REQUIREMENTS.md's traceability table maps exactly E2E-01..05 to Phase 4,
and all five appear in a plan's `requirements:` frontmatter field (including the two gap-closure
plans 04-07 `[E2E-01]` and 04-08 `[E2E-04]`).

**Note:** `.planning/REQUIREMENTS.md`'s traceability table (as of this session) still shows
E2E-02/03/05 as "Gaps Found" — that reflects the prior (pre-gap-closure) verification pass and
should be updated to "Complete" alongside this report; those three requirements were never
actually gapped (the prior VERIFICATION.md's two gaps were plan 04-01's and 04-06's must-haves,
mapping to E2E-01 and E2E-04 respectively, not E2E-02/03/05).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_fixture_mode.py` | SPA-fallback test (`test_client_side_route_falls_back_to_the_spa_shell_not_json`) | Implicit dependency on an out-of-band, gitignored `frontend/dist/` build with no `skipif` guard (04-REVIEW.md, updated 2026-09-04, "Critical Issues" — WR-04 lineage) | ⚠️ Warning (advisory, pre-existing, explicitly out of scope for both gap-closure plans) | A clean checkout without a prior `npm run build`/Playwright run will 500 on this one pytest test; does not affect any Playwright E2E spec (the harness always builds the frontend itself via `webServer.command`) and does not touch the phase's calendar-independence goal. Confirmed `frontend/dist/index.html` exists in this environment (built during this session's E2E run) so the test currently passes here; the fragility is environmental, not a regression from this phase's work. |
| `api/main.py`, `e2e/scripts/capture_fixtures.py` | multiple | Bare `open(...)` without context manager (04-REVIEW.md WR-01) | ⚠️ Warning (advisory, unchanged) | Resource-leak/robustness; not fixed by either gap-closure plan (explicitly out of scope, matching 04-07's task boundary) |

No `TBD`/`FIXME`/`XXX` debt markers found in any file touched by the gap-closure plans (`api/main.py`,
`tests/test_fixture_mode.py`, `frontend/src/components/pitch/Pitch.tsx`, `frontend/src/components/RateDiff.tsx`,
`frontend/src/components/pitch/Pitch.test.tsx`, `frontend/src/components/RateDiff.test.tsx`,
`e2e/specs/rate-my-team.spec.ts`) — grepped directly this session, zero hits. The debt-marker gate
does not fire.

Both warnings above are pre-existing, already documented in 04-REVIEW.md, and were deliberately
left out of scope by both gap-closure plans' `<action>` sections ("Do NOT convert the bare
`open(...)` calls..."). They do not block the phase goal — E2E-01..05 are all satisfied by real,
passing, non-mocked browser tests, and neither warning is a debt marker or a failure of any stated
must-have.

### Human Verification Required

None. Both previously open gaps were independently re-verified against the actual codebase this
session (source inspection + fresh test/spec runs, not SUMMARY.md claims), and no new human-only
concern (visual, real-time, external-service) was introduced by either gap-closure plan.

### Gaps Summary

No gaps remain. Both must-haves that failed in the prior verification pass (119040c) are now
independently confirmed fixed against the actual codebase:

1. **CR-01 (api/main.py restore path):** re-ran the plan's own repro script in-process this
   session — `RESTORE OK`. Full pytest suite green at 77/77 (up from 76).
2. **Ghost/bench-row placement (Pitch.tsx / RateDiff.tsx):** re-ran `e2e/specs/rate-my-team.spec.ts`
   in isolation against a real fixture-mode server this session — 5/5 passed, including the
   adjacency proof. `WINDOWS.md` id=2 closed.

All five roadmap Success Criteria for Phase 4 hold: frozen fixtures with no live-data dependence,
the team/pitch + solver flow, the xP table/captains view, the rate-my-team flow, and the
fixtures/prices pages are all covered by real, passing, non-mocked Playwright tests against a real
FastAPI process and a real ILP solve. Two pre-existing advisory warnings (SPA-fallback test's
implicit `frontend/dist` dependency; bare `open()` calls) remain open but are explicitly
out-of-scope items, not blockers, and were flagged again for visibility rather than silently
dropped.

---

_Verified: 2026-09-04_
_Verifier: Claude (gsd-verifier)_
