---
phase: "4"
slug: "e2e-regression-suite"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-03"
validated: "2026-09-03"
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (API/backend) + @playwright/test 1.62.1 (E2E, Chromium) + Vitest (frontend units, pre-existing) |
| **Config file** | `pytest.ini`, `e2e/playwright.config.ts`, `frontend/vitest` config |
| **Quick run command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -x -q` |
| **Full suite command** | `E2E_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python npm --prefix e2e run test` (builds frontend, boots uvicorn in fixture mode, runs all 3 Playwright projects) |
| **Estimated runtime** | pytest ~3s · full E2E ~90s (build) + ~20s (42 tests) |

---

## Sampling Rate

- **After every task commit:** Run pytest quick command (~3s)
- **After every plan wave:** Run the full E2E suite command
- **Before `/gsd-verify-work`:** Full suite must be green — verified 2026-09-03: 42/42 Playwright, 363 Vitest, 76 pytest
- **Max feedback latency:** ~120 seconds (full E2E including frontend build)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-* | 01 | 1 | E2E-01 | — | No outbound HTTP / no artifact load in fixture mode | integration | `pytest tests/test_fixture_mode.py` (9 tests) + `python e2e/scripts/capture_fixtures.py --verify` | ✅ | ✅ green |
| 04-02-* | 02 | 2 | E2E-01 | T-04-SC | Closed 3-package install surface, exact-pinned | e2e | `playwright test specs/smoke.spec.ts specs/shell-geometry.spec.ts` | ✅ | ✅ green |
| 04-03-* | 03 | 3 | E2E-01, E2E-05 | — | Immutable v1 fixtures; variants additive only | e2e | `playwright test specs/fixtures-prices.spec.ts` + chromium-blank/chromium-dgw projects (4 variant specs) | ✅ | ✅ green |
| 04-04-* | 04 | 3 | E2E-03 | — | N/A | e2e | `playwright test specs/xp-table.spec.ts` (10 tests) | ✅ | ✅ green |
| 04-05-* | 05 | 3 | E2E-02 | — | Real ILP solve, no /api/* route mocking | e2e | `playwright test specs/team-solver.spec.ts specs/team-plan.spec.ts` (16 tests) | ✅ | ✅ green |
| 04-06-* | 06 | 3 | E2E-04 | — | Scrubbed manager-name fixture policy honored | e2e | `playwright test specs/rate-my-team.spec.ts` (5 tests) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Flake note (2026-09-03):** `shell-geometry.spec.ts` › "team page has no horizontal overflow at 390px (D-07)" failed once in a full-suite run, then passed in isolation and in a full-suite re-run (42/42). One occurrence — watch under CI (Phase 5); if it recurs, investigate cross-test state around the team page.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. (Playwright harness itself was Wave 2's deliverable, human-gated through three package checkpoints.)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual look-and-feel of rendered pages (beyond geometry assertions) | E2E-02..05 | Aesthetic judgment not assertable | Covered by end-of-phase UAT via /gsd-verify-work |

**Known fixture-data limitations (documented in 04-04/04-06 SUMMARYs, not coverage gaps):** null-value sort placement and non-"a" status-flag branches have no exercising rows in the immutable v1 capture; the `Pitch.tsx` ghost/bench-row placement gap is logged in `deferred-items.md` + `WINDOWS.md` for a future fix.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none)
- [x] No watch-mode flags (Playwright/pytest one-shot commands)
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-03

## Validation Audit 2026-09-03

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All five phase requirements (E2E-01..E2E-05) verified COVERED by green automated tests: 42 Playwright E2E tests across 3 projects (normal/blank/dgw), 9 fixture-mode pytest tests, plus the fixture coherence verifier. Full-suite state at audit: Playwright 42/42, Vitest 363/363, pytest 76/76.
