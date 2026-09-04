---
phase: 04-e2e-regression-suite
verified: 2026-09-03T18:30:00Z
status: gaps_found
score: 5/7 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "With FPL_FIXTURE_DIR unset, api/main.py behaves exactly as it does today (plan 04-01 must-have)"
    status: partial
    reason: >
      Verified FALSE under a reproducible, in-process module-reload cycle. api/main.py's
      fixture-mode branch does `live._gw_pool = _gw_pool_fixture` when FPL_FIXTURE_DIR is set,
      but has no `else` branch restoring `predict.live._gw_pool` when the var is unset and the
      module reloaded. `predict.live` is never reloaded (only `api.main` is), so the pollution
      of its module-global is permanent for the rest of the process once fixture mode has been
      entered even once. Independently reproduced in this verification session (see Evidence).
      This is CR-01 from 04-REVIEW.md (severity: critical), filed 2026-09-03, and remains
      unfixed in the current codebase — confirmed by direct source inspection and a live repro.
      It is not logged in .planning/WINDOWS.md and carries no override.
      Note: a freshly-started uvicorn process with the env var simply unset for its whole
      lifetime never touches the vulnerable code path — the bug requires an in-process
      env-toggle-and-reload cycle. But `tests/test_fixture_mode.py`'s own fixture teardown
      performs exactly that cycle, and its docstring's claim that this "restores the unset-env
      module" is itself false, meaning the pytest suite's own safety net has a documented-wrong
      assumption baked in.
    artifacts:
      - path: "api/main.py"
        issue: "Lines ~114-121: `if _FIXTURE_ROOT: ... live._gw_pool = _gw_pool_fixture` has no else-branch restoring live._gw_pool; the production function reference is never captured before it can be polluted."
      - path: "tests/test_fixture_mode.py"
        issue: "fixture_app fixture's teardown docstring/comment claims the reload 'restores the unset-env module' — verified false."
    missing:
      - "Capture predict.live._gw_pool's true original function once (e.g. live._gw_pool_production = live._gw_pool, guarded by hasattr) before any fixture-mode branch can run, and restore from that captured reference in an explicit else-branch when FPL_FIXTURE_DIR is unset."
      - "Correct test_fixture_mode.py's docstring/comment and add a regression assertion (e.g. predict.live._gw_pool is <original> after teardown, or a real build_pool-path smoke call) that would catch this class of regression."
  - truth: "The suggested incoming player renders as a ghost card in the same formation row as the outgoing player (plan 04-06 must-have)"
    status: partial
    reason: >
      FALSE for the real, immutable v1 capture's own best_move: it sells Mateta, a BENCHED
      (non-starting) player. Pitch.tsx's ghost-insertion mechanism keys the ghost's row purely
      off the BUY's position (always a GK/DEF/MID/FWD formation row), never off the SELL
      target's actual row — so when the sell target is on the bench, the ghost card (Forwards
      row) and the dimmed/labelled outgoing card (Bench row) land in two different
      role="group" containers. This is pre-existing Phase 3 code (Pitch.tsx), correctly
      discovered and NOT masked by plan 04-06's spec (it asserts the real observed two-row
      behavior), and is already logged as an open item: .planning/WINDOWS.md id=2 (kind:
      deviation, status: open) and .planning/phases/04-e2e-regression-suite/deferred-items.md.
      Surfaced here because it is a still-open, unresolved falsification of a plan-declared
      must-have, not because the E2E suite itself is deficient — the suite did exactly its job
      by catching it.
    artifacts:
      - path: "frontend/src/components/pitch/Pitch.tsx"
        issue: "Ghost slot is always inserted into the row matching the incoming player's position, never the outgoing player's actual (possibly bench) row."
    missing:
      - "Extend Pitch.tsx's ghost mechanism to key off the sell target's actual row (including Bench) rather than the buy's position, per deferred-items.md's suggested follow-up — or explicitly waive WINDOWS.md id=2 with a reason before shipping."
---

# Phase 4: E2E Regression Suite Verification Report

**Phase Goal:** A hermetic Playwright E2E suite over frozen fixtures proving the whole stack
(React build → FastAPI fixture mode → real ILP) end to end, covering the xP table,
fixtures/prices pages, team/pitch + solver flow, rate-my-team flow, and blank/double-gameweek
variants.

**Verified:** 2026-09-03
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria, E2E-01..05)

| # | Truth (ROADMAP.md SC) | Status | Evidence |
|---|------------------------|--------|----------|
| 1 | Frozen versioned JSON snapshots (normal, blank, double GW) back every test — no live-data dependence | ✓ VERIFIED | `e2e/fixtures/v1/{normal,blank,dgw}/` committed (41 tracked files, not gitignored); `capture_fixtures.py --verify` exits 0 (`[verify] OK: gw=3, 6 pool files, xp_table non-empty, picks_event2.json has 15 picks, no upstream URLs` — reproduced independently this session); no spec mocks `/api/*` (grepped, zero `page.route(` hits); `watchOrigin` proves zero cross-origin requests in smoke.spec.ts |
| 2 | Team/pitch + solver flow covered end to end: load squad, request solve, assert resulting XI and transfers | ✓ VERIFIED | `e2e/specs/team-solver.spec.ts` (15 tests) + `team-plan.spec.ts` (1 test): real `/api/solve` calls, 5 legality invariants asserted against the live response, one pinned golden XI/moves/bank, real 2-GW `/api/plan` flow |
| 3 | xP table and captains view covered — exact cell values and sort order, not "a table rendered" | ✓ VERIFIED | `e2e/specs/xp-table.spec.ts` (10 tests): exact cell literals for rows 1-3 and row 50, both sort directions with 2 independent tie-stability proofs, 4 position-filter counts summing to 50, full-club-name search, empty-result state |
| 4 | Rate-my-team flow covered end to end | ⚠️ PARTIAL — see gap | `e2e/specs/rate-my-team.spec.ts` (5 tests) covers all 4 tiles, empty/pending/failure states, and the single-pitch diff — but the diff's own must-have ("ghost in the same row as outgoing") is verified FALSE against the real captured data; the spec correctly asserts the real (two-row) behavior rather than masking it. See gaps. |
| 5 | Fixtures and prices pages covered | ✓ VERIFIED | `e2e/specs/fixtures-prices.spec.ts` (2 tests) + 4 targeted variant specs under `e2e/specs/variants/`: data-derived GW-column count, exact ticker/price literals, zero interactive cells, blank em-dash chips for all 6 blanked clubs, double-chip pairs for all 4 doubled clubs, DGW timeline marker + tooltip |

**Score:** 5/7 must-haves verified (4 roadmap SCs fully clean + the fixture-strategy SC; 2
plan-level must-haves — one from 04-01, one from 04-06 — fail on independently-verified
evidence). See Gaps.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `e2e/fixtures/v1/normal/**` | Immutable GW3 capture (api + web-data) | ✓ VERIFIED | 41 tracked files under `e2e/fixtures/v1`; `--verify` exits 0 |
| `e2e/fixtures/v1/blank/web-data/`, `dgw/web-data/` | Deterministic variants | ✓ VERIFIED | 9 files each, present; synthesis script re-run leaves `git status --porcelain` clean per 04-03-SUMMARY |
| `e2e/scripts/capture_fixtures.py` | Capture/verify tool | ✓ VERIFIED | Ran `--verify` independently this session, exit 0 |
| `e2e/scripts/synthesize-variants.mjs` | Zero-dep transform | ✓ VERIFIED (by summary + code review, not re-run) | Reviewed by 04-REVIEW.md, no findings against it |
| `api/main.py` fixture seam | `_FIXTURE_ROOT`/`_FIXTURE_API`/`_FIXTURE_DATA`, branch at every network/artifact site | ⚠️ VERIFIED WITH KNOWN BUG | Present and wired for the fixture-mode-ON path; the OFF-path restoration is broken (CR-01, reproduced independently) |
| `tests/test_fixture_mode.py` | In-process proof of network/artifact isolation | ✓ VERIFIED (but its own reload-safety claim is false) | 9 tests pass (`pytest -q`: 76 passed, confirmed this session); the file's docstring about reload restoring production is incorrect (CR-01) |
| `e2e/playwright.config.ts`, `e2e/helpers/page.ts` | Harness, clock/locale pinning, 3-project port block | ✓ VERIFIED | Present, `timezoneId: UTC`, `locale: en-GB`, Chromium-only (per 04-02-SUMMARY grep gates) |
| `e2e/specs/*.spec.ts` (7 files) + `e2e/specs/variants/*.spec.ts` (4 files) | All required spec coverage | ✓ VERIFIED | All 11 files present on disk (confirmed via `ls`), matching every plan's declared artifact |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `playwright.config.ts` webServer | `frontend/dist` + fixture-mode uvicorn | chained build command | ✓ WIRED | Per 04-02-SUMMARY; `bash scripts/verify_frontend_build.sh` green, `dist/404.html` byte-identical to `dist/index.html` |
| `build_pool`/`build_horizon_pool` | frozen per-gw pools | `predict.live._gw_pool` rebind | ⚠️ WIRED BUT LEAKS | Correctly wired ON; the rebind is never undone OFF (CR-01) |
| React app | `/api/*` (real FastAPI) | no route mocking anywhere | ✓ WIRED | Grepped all spec files, zero `page.route(` calls |
| Rate tab swap line | Best-move tile | same `/api/rate` response | ✓ WIRED | 04-06-SUMMARY: both asserted against the same captured response |
| Blank/DGW servers | `normal/api/` via `FPL_FIXTURE_DATA_DIR` | shared API capture, distinct `/data` | ✓ WIRED | Confirmed in 04-02/04-03 config and specs |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| E2E-01 | 04-01, 04-02, 04-03 | Fixture strategy — frozen normal/blank/dgw + no live-data dependence | ✓ SATISFIED | Fixture sets committed and independently re-verified; harness proven network-isolated |
| E2E-02 | 04-05 | Team/pitch + solver flow regression test | ✓ SATISFIED | `team-solver.spec.ts` + `team-plan.spec.ts`, real ILP, legality invariants, pinned golden |
| E2E-03 | 04-04 | xP table + captains rendering/sorting regression test | ✓ SATISFIED | `xp-table.spec.ts`, exact literals + sort/filter contract |
| E2E-04 | 04-06 | Rate-my-team flow regression test | ⚠️ SATISFIED WITH A KNOWN OPEN DEFECT | Flow is covered end to end; the diff's ghost-row must-have fails against real data (tracked, WINDOWS.md id=2) |
| E2E-05 | 04-03 | Fixtures and prices pages regression tests | ✓ SATISFIED | `fixtures-prices.spec.ts` |

No orphaned requirements: REQUIREMENTS.md's traceability table maps exactly E2E-01..05 to
Phase 4, and all five appear in a plan's `requirements:` frontmatter field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/main.py` | ~114-121 | Monkeypatch of `predict.live._gw_pool` with no restoring else-branch | 🛑 Blocker | Verified reproducible: production behavior after any prior in-process fixture-mode toggle is permanently corrupted (crashes `/api/solve`, `/api/team`, `/api/rate`, `/api/plan`). Falsifies plan 04-01's stated must-have. Not logged in WINDOWS.md. |
| `frontend/src/components/pitch/Pitch.tsx` | n/a | Ghost card keyed off buy position, not sell target's actual row | ⚠️ Warning (already tracked) | Falsifies plan 04-06's ghost-same-row must-have for a benched sell target; open in WINDOWS.md id=2 and deferred-items.md — pre-existing Phase 3 code, correctly surfaced not masked |
| `api/main.py`, `e2e/scripts/capture_fixtures.py`, `tests/test_fixture_mode.py` | multiple (per 04-REVIEW.md WR-01) | Bare `open(...)` without context manager | ⚠️ Warning | Resource-leak/robustness; flagged by code review, not fixed; no debt marker (TBD/FIXME/XXX), so does not trip the debt-marker gate |
| `e2e/scripts/capture_fixtures.py` | `_verify()` | Scrub-names PII policy has no automated regression check (04-REVIEW.md WR-02) | ⚠️ Warning | A future edit could silently re-commit a real name with `--verify` still reporting success |
| `e2e/scripts/capture_fixtures.py` | `ENTRY = 6980093` | Real FPL entry ID + team name permanently committed (04-REVIEW.md WR-03) | ⚠️ Warning (accepted, flagged for a pre-public sign-off) | Deliberate per Task 1's checkpoint decision; flagged again here per the review's own recommendation |
| `tests/test_fixture_mode.py` | SPA-fallback test | Implicit dependency on an out-of-band `frontend/dist/` build, no skip guard (04-REVIEW.md WR-04) | ⚠️ Warning | Will fail confusingly in a CI stage that runs pytest before the frontend build exists |

No `TBD`/`FIXME`/`XXX` debt markers found in any file this phase modified (grepped
`api/main.py`, `e2e/scripts/*.py`, `e2e/scripts/*.mjs`, `SquadTab.tsx`,
`tests/test_fixture_mode.py`) — the debt-marker gate does not fire.

### Behavioral Spot-Checks / Independent Re-Verification

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Fixture coherence | `python e2e/scripts/capture_fixtures.py --verify` | `[verify] OK: gw=3, 6 pool files, xp_table non-empty, picks_event2.json has 15 picks, no upstream URLs`, exit 0 | ✓ PASS |
| Full pytest suite | `python -m pytest -q` | `76 passed` | ✓ PASS |
| CR-01 repro | in-process `FPL_FIXTURE_DIR` set → reload → unset → reload → inspect `predict.live._gw_pool` | `live._gw_pool` remains bound to `_gw_pool_fixture` after the env var is unset and the module reloaded | ✗ FAIL (confirms 04-REVIEW.md CR-01, independently reproduced) |
| Fixture set tracked, not ignored | `git ls-files e2e/fixtures/v1 \| wc -l` (41), `git check-ignore -q e2e/fixtures` (exit 1) | 41 files tracked; not ignored | ✓ PASS |
| Full E2E suite (42/42), Vitest (363/363) | orchestrator-verified this session (not independently re-run in this pass — expensive; environment context states pass) | 42/42, 363/363 | ✓ PASS (relied on session-verified fact) |

### Human Verification Required

None required to determine phase status — both gaps below are objectively verifiable from the
codebase and were independently reproduced or confirmed by static inspection during this
verification. They are presented as gaps (not human-verification items) because they resolve
to FAILED, not UNCERTAIN. A human decision IS needed on disposition (fix now vs. explicitly
waive), which is exactly what the gaps section and the open WINDOWS.md entry are for.

### Gaps Summary

Two must-haves declared in this phase's own plans do not hold against the actual codebase:

1. **CR-01 (new, untracked, critical):** `api/main.py`'s fixture-mode seam never restores
   `predict.live._gw_pool` when `FPL_FIXTURE_DIR` is unset after having been set earlier in
   the same process. This directly falsifies plan 04-01's must-have that "with FPL_FIXTURE_DIR
   unset, api/main.py behaves exactly as it does today." A fresh, single-lifetime uvicorn
   process is unaffected, but `tests/test_fixture_mode.py`'s own teardown performs exactly the
   toggle-and-reload sequence that triggers it, and its docstring's claim to the contrary is
   itself wrong. This was already flagged CRITICAL by 04-REVIEW.md's CR-01 with a full repro
   and suggested fix; it remains unfixed and is not present in `.planning/WINDOWS.md`.
   **This is the primary reason for `gaps_found`.**

2. **Pitch.tsx ghost/bench-row placement (already tracked):** plan 04-06's must-have that the
   ghost card renders "in the same formation row" as the outgoing player is false for the real
   captured data (a benched sell target). This was correctly discovered and documented rather
   than concealed — `deferred-items.md` and `WINDOWS.md` (id=2, open) already track it as a
   pre-existing Phase 3 defect outside this phase's file scope. It is listed here because it is
   a still-open falsification of a stated must-have, not a new finding, and the developer should
   either fix `Pitch.tsx` or explicitly waive WINDOWS.md id=2 with a reason before `/gsd-ship`
   (which is already blocked by `windows_enforce` for this reason independent of this report).

Everything else — the fixture strategy (E2E-01), the solver flow (E2E-02), the xP table
(E2E-03), the fixtures/prices pages (E2E-05), and the rest of the rate-my-team flow (E2E-04) —
is genuinely covered by real, passing, non-mocked browser tests against a real ILP and a real
FastAPI process, independently re-verified in this session (fixture `--verify`, full pytest
suite, and direct source inspection of every plan's declared artifacts and key links).

**This looks like it could be accepted via override for item 2**, given it is a pre-existing,
already-ledgered, correctly-surfaced Phase 3 defect that Phase 4's own testing infrastructure
was working as designed to catch. If the developer wants to accept it as-is for this phase,
add to this file's frontmatter:

```yaml
overrides:
  - must_have: "the suggested incoming player rendered as a ghost card in the same formation row"
    reason: "Pre-existing Phase 3 Pitch.tsx defect, correctly discovered (not masked) by 04-06's spec against real captured data; tracked in WINDOWS.md id=2 (open) and deferred-items.md for a dedicated future fix; out of Phase 4's file-modification scope."
    accepted_by: "<name>"
    accepted_at: "<ISO timestamp>"
```

Item 1 (CR-01) is a genuine, unresolved, untracked regression risk in code this phase itself
wrote — it should be fixed rather than overridden before this phase is considered closed.

---

_Verified: 2026-09-03_
_Verifier: Claude (gsd-verifier)_
