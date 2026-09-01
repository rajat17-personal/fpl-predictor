---
status: diagnosed
phase: 01-test-base-layer-app-skeleton
source: [01-VERIFICATION.md]
started: 2026-09-01T05:40:00Z
updated: 2026-09-01T06:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. api/main.py diff is a pure refactor
expected: Same six `_state` keys, same defaults, same order; no change to `_refresh`, `_pool`, `_solve_cache`, or `CORSMiddleware`. Read `git show 7313446 -- api/main.py`.
result: pass

### 2. No third-party manager PII in tests/test_api.py responses fixtures
expected: All manager/team/entry identities are synthetic — only "Test FC", "Test Manager", entry 12345, keys k1/k2/nope. Skim the `responses.add` bodies in tests/test_api.py.
result: pass

### 3. App shell visual conformance and live error recovery
expected: With uvicorn (port 8000) and `npm --prefix frontend run dev` running — nav highlights the active link; nav wraps without a hamburger at 375px; footer reads the exact three-sentence disclaimer; stopping uvicorn shows ErrorState on xP page, restarting and clicking Retry recovers without a full reload.
result: issue
reported: "The nav links text does not adapt based on screen size especially when screen size is bigger. rest work as expected"
severity: cosmetic
notes: Screenshots confirm active-state highlight, mobile wrap without hamburger (430px), and exact footer disclaimer; ErrorState/Retry confirmed working by user.

### 4. Package legitimacy sign-off scope
expected: Human reviewed and approved the 13 [SUS]-flagged packages before any install ran. Already answered "Approved" (recorded verbatim in 01-01-SUMMARY.md) — confirm the recorded scope matches what you intended to approve.
result: pass

## Summary

total: 4
passed: 3
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-01-3
  truth: "Nav link text adapts appropriately across screen sizes (remains proportionate/legible on large screens)"
  status: failed
  reason: "User reported: The nav links text does not adapt based on screen size especially when screen size is bigger. rest work as expected"
  severity: cosmetic
  test: 3
  root_cause: "PageShell.tsx:27 header is the only chrome section missing the mx-auto max-w-[68rem] containment that main (L53) and footer (L58) apply; on >1088px viewports the header renders full-bleed so the fixed 14px nav text reads stranded/undersized. Layout-containment omission vs the UI-SPEC 68rem parity contract — not a typography defect (vanilla nav font never scales either; its .wrap containment is what makes it look right)."
  artifacts:
    - path: "frontend/src/components/PageShell.tsx"
      issue: "header (line 27) lacks mx-auto max-w-[68rem] inner containment"
  missing:
    - "Wrap header brand+nav in an inner mx-auto w-full max-w-[68rem] container (keep border/padding full-bleed on outer header)"
    - "Do NOT add responsive font-size utilities — fixed 14px Label token is the UI-SPEC contract"
    - "Playwright note for Phase 4 (E2E-01): assert header inner wrapper width matches main (≤1088px, centered) at 1720px viewport"
  debug_session: ".planning/debug/nav-text-not-responsive.md" 
