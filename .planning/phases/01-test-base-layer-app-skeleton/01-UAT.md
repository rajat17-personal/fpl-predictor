---
status: testing
phase: 01-test-base-layer-app-skeleton
source: [01-VERIFICATION.md]
started: 2026-09-01T05:40:00Z
updated: 2026-09-01T05:40:00Z
---

## Current Test

number: 1
name: api/main.py diff is a pure refactor
expected: |
  Same six _state keys, same defaults, same order; no change to _refresh, _pool,
  _solve_cache, or CORSMiddleware. (Verifier pre-checked via `git show 7313446 -- api/main.py` —
  diff is confined to the _initial_state() extraction; your read confirms it.)
awaiting: user response

## Tests

### 1. api/main.py diff is a pure refactor
expected: Same six `_state` keys, same defaults, same order; no change to `_refresh`, `_pool`, `_solve_cache`, or `CORSMiddleware`. Read `git show 7313446 -- api/main.py`.
result: [pending]

### 2. No third-party manager PII in tests/test_api.py responses fixtures
expected: All manager/team/entry identities are synthetic — only "Test FC", "Test Manager", entry 12345, keys k1/k2/nope. Skim the `responses.add` bodies in tests/test_api.py.
result: [pending]

### 3. App shell visual conformance and live error recovery
expected: With uvicorn (port 8000) and `npm --prefix frontend run dev` running — nav highlights the active link; nav wraps without a hamburger at 375px; footer reads the exact three-sentence disclaimer; stopping uvicorn shows ErrorState on xP page, restarting and clicking Retry recovers without a full reload.
result: [pending]

### 4. Package legitimacy sign-off scope
expected: Human reviewed and approved the 13 [SUS]-flagged packages before any install ran. Already answered "Approved" (recorded verbatim in 01-01-SUMMARY.md) — confirm the recorded scope matches what you intended to approve.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
