---
phase: 01-test-base-layer-app-skeleton
verified: 2026-09-01T12:00:00Z
status: passed
score: 9/10 must-haves verified
behavior_unverified: 1
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 8/8 (roadmap-truth framing) — see must-have reframing below
  gaps_closed:
    - "G-01-3: header brand+nav are no longer full-bleed at wide viewports — contained at 68rem, centered, aligned with <main> and the footer, class-locked by a new PageShell.test.tsx"
  gaps_remaining: []
  regressions: []
behavior_unverified_items:

  - truth: "At viewports wider than 1088px the header brand+nav render inside a centered 68rem column instead of full-bleed (G-01-3 closed)"
    test: "Open the app at a maximized wide display (~1720px) and confirm the brand+nav sit in a centered column whose left/right edges line up with the page heading and footer disclaimer beneath/above them, with no large empty gutter beside the nav; then narrow to ~375px and confirm the nav still wraps without a hamburger."
    expected: "Header content visually aligns with <main> and footer content at every width; no full-bleed/stranded-nav regression."
    why_human: "jsdom (the test environment used by PageShell.test.tsx) has no layout engine — it can assert the correct Tailwind class tokens are present on the correct elements, which this re-verification independently confirmed, but it cannot measure actual rendered pixel geometry. That measurement requires a real browser and is formally handed to Phase 4's Playwright suite (E2E-01) per deferred-items.md and the ROADMAP Phase 4 research flags, both independently confirmed present in this re-verification."
human_verification:

  - test: "Final visual re-confirmation of G-01-3 at a wide viewport (~1720px), per plan 01-06 Task 1's own <human-check>"
    expected: "Brand+nav sit in a centered 68rem column aligned with the page heading and footer disclaimer; nav still wraps cleanly at ~375px."
    why_human: "Visual/geometric confirmation; jsdom cannot measure it. Automated evidence (class-token test, containment-count gate, code review) is strong and consistent, but no tool in this phase's toolchain can render pixels. Recorded as end-of-phase UAT per workflow.human_verify_mode=end-of-phase; not currently blocking further phase progress given the strength of the automated evidence, but the phase cannot claim the visual claim itself as mechanically VERIFIED."
  - test: "Package-legitimacy and PII sign-offs (recorded, listed for completeness — unchanged since prior verification)"
    expected: "N/A — already answered ('Approved') in 01-01-SUMMARY.md."
    why_human: "gate=\"blocking-human\" trust decisions, by protocol never auto-passable; carried forward unchanged from the prior VERIFICATION.md, independently re-confirmed via git/grep in this pass."
---

# Phase 1: Test Base Layer & App Skeleton Verification Report

**Phase Goal:** The API has a real test safety net, and a React app talks to it through a proven runtime seam.
**Verified:** 2026-09-01T12:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap-closure plan 01-06 (UAT gap G-01-3) executed.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | pytest exercises /solve, /rate, /team, /health, /meta against a mocked FPL API, fails on contract/error regressions | ✓ VERIFIED | Independently re-ran `python -m pytest -q`: **67 passed**, 0 failed, 2.63s. Unchanged since prior verification. |
| 2 | require_key() covered in open/valid/invalid modes | ✓ VERIFIED | Included in the 67-passing backend suite; `api/main.py`'s `require_key()` untouched since commit `7313446` (confirmed via `git log --oneline --all -- api/main.py`, still only one touching commit). |
| 3 | Concurrent solve + pool-refresh test runs green, race is observable | ✓ VERIFIED | Included in the 67-passing backend suite; no code touching `api/main.py`'s concurrency path was modified by plan 01-06. |
| 4 (UI-01) | React/Vite scaffold proves dev-proxy seam, all 8 routes render with error isolation, vanilla web/ untouched | ✓ VERIFIED | `npm --prefix frontend run test`: **5 files / 9 tests passing** (was 4/7 before 01-06; +2 new PageShell tests). `npm --prefix frontend run build` succeeds (`tsc -b && vite build`, 740ms, `dist/` produced). `git status --porcelain web/` still empty — vanilla untouched. |
| 5 | At viewports wider than 1088px the header brand+nav render inside a centered 68rem column instead of full-bleed — closes G-01-3 | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED (class-token level ✓ VERIFIED) | `PageShell.tsx` read directly: outer `<header>` now `border-b border-line py-4` (no cap/gutter); a new inner `<div className="mx-auto flex w-full max-w-[68rem] flex-wrap items-center gap-[18px] px-4">` wraps brand+nav+meta-slot. `PageShell.test.tsx` independently re-run (`npx vitest run src/components/PageShell.test.tsx` equivalent via full suite): both new tests pass, asserting the exact containment token set on header-wrapper/main/footer-paragraph via `Set`-based comparison (not substring). This proves the *class tokens* are correct; it cannot prove rendered pixel geometry — jsdom has no layout engine. See `behavior_unverified_items`. |
| 6 | Header, main and footer content share one containment geometry | ✓ VERIFIED | Source read confirms identical token set `mx-auto w-full max-w-[68rem] px-4` on header's inner wrapper (L32), `<main>` (L59, plus `flex-1`), and footer's `<p>` (L64). Test 1 in `PageShell.test.tsx` asserts this three-way. |
| 7 | Nav label typography stays fixed 14px Label token — no breakpoint-scaled font size introduced | ✓ VERIFIED | `grep -E '(sm|md|lg|xl|2xl):text-' frontend/src/components/PageShell.tsx` → no matches. Nav `NavLink` className still carries `font-label text-label` unconditionally (L43). |
| 8 | Header and footer borders stay full-bleed edge to edge — only content is capped | ✓ VERIFIED | Outer `<header>` = `border-b border-line py-4`, outer `<footer>` = `border-t border-line py-4 text-label text-ink-2` — neither carries `max-w-` or `px-` tokens (independently confirmed by source read and by `PageShell.test.tsx` Test 2's negative assertions). |
| 9 | The existing frontend suite still passes and `npm --prefix frontend run build` still succeeds | ✓ VERIFIED | Independently re-ran both: 5 files/9 tests passing, build succeeds. No pre-existing test file (`routeIsolation.test.tsx`, `harness.test.tsx`, `ErrorState.test.tsx`, `Spinner.test.tsx`) required modification — confirmed via `git log --oneline --all -- <path>` showing only their original 01-04/01-05 commits. |
| 10 | Phase 4's Playwright work carries a findable instruction to assert header containment at a 1720px viewport | ✓ VERIFIED | `grep -c "G-01-3" .planning/ROADMAP.md` → 2 (Phase 1 plan-list entry + Phase 4 research-flag sentence, as designed). Phase 4's `**Research flags**:` line reads: "...Gap `G-01-3` handoff: at a 1720px viewport, assert the header's inner content wrapper is ≤1088px wide, horizontally centered, and shares the `<main>` element's content x-range (see `.planning/phases/.../deferred-items.md`)." `deferred-items.md` independently read: contains a full handoff section naming G-01-3, 1720, E2E-01, and `PageShell.test.tsx`. |

**Score:** 9/10 truths verified (1 present + wired, pixel geometry not exercisable in this toolchain — see Human Verification).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/PageShell.tsx` | Header/footer inner containment wrapper matching `<main>`'s geometry | ✓ VERIFIED | Read directly; matches SUMMARY's before/after claims exactly (diffed against commit `06b70d8`). |
| `frontend/src/components/PageShell.test.tsx` | Containment-parity regression test (2 tests) | ✓ VERIFIED | Exists, 2 describe/it blocks, both pass, asserts via `Set` token comparison (not substring), asserts negative full-bleed constraint on outer header/footer. |
| `.planning/phases/01-test-base-layer-app-skeleton/deferred-items.md` | Phase 4 visual-assert handoff entry | ✓ VERIFIED | New section present, names G-01-3, 1720px, E2E-01, `PageShell.test.tsx`, and the debug session path. |
| `.planning/ROADMAP.md` | Phase 4 research-flag carrying the same handoff, scoped to one line | ✓ VERIFIED | `G-01-3` appears exactly twice total in the file; Phase 4's research-flags sentence carries both `G-01-3` and `1720`; no other phase section (checked Phase 3 and Phase 5 boundaries) mentions it. |
| `tests/test_api.py`, `api/main.py` (`_initial_state()`), `tests/conftest.py` | Backend test safety net (unchanged from prior verification) | ✓ VERIFIED | Unmodified by plan 01-06 (`git log --oneline --all -- api/main.py` still shows only `7313446`); 67/67 passing on independent re-run. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `frontend/src/components/PageShell.test.tsx` | `frontend/src/components/PageShell.tsx` | Reads live `className` tokens off the rendered DOM | ✓ WIRED | Confirmed by independent test re-run — passes against the current file, fails (per SUMMARY's documented RED output) against the pre-fix version. |
| Header inner wrapper | `<main>` element | Identical class token set (`mx-auto w-full max-w-[68rem] px-4`) | ✓ WIRED | Source-diffed directly; confirmed identical modulo `main`'s additional `flex-1`. |
| `deferred-items.md` + ROADMAP Phase 4 | Phase 4's future Playwright suite | Explicit, findable written instruction naming G-01-3 and 1720px | ✓ WIRED | Both artifacts independently grepped and read in full; content is specific and actionable (bounding-box width ≤1088px, horizontal centering, x-range match with `<main>`). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend full suite still green post-gap-closure | `python -m pytest -q` | 67 passed, 0 failed, 2.63s | ✓ PASS |
| Frontend full suite green, includes 2 new PageShell tests | `npm --prefix frontend run test -- --reporter=verbose` | 5 files / 9 tests, all pass | ✓ PASS |
| Frontend build still succeeds after the containment fix | `npm --prefix frontend run build` | `tsc -b && vite build` — success, `dist/` produced, 740ms | ✓ PASS |
| No breakpoint-scaled font-size utility introduced | `grep -E '(sm\|md\|lg\|xl\|2xl):text-' PageShell.tsx` | no matches | ✓ PASS |
| ROADMAP handoff is exactly-scoped (2 occurrences, both in Phase 1/Phase 4 sections) | `grep -c "G-01-3" .planning/ROADMAP.md` | 2 | ✓ PASS |
| No dependency drift from this gap-closure plan | (source read) `frontend/package.json`/`package-lock.json` absent from 01-06's `files_modified` and commit diffs | confirmed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| APIT-01 | 01-01, 01-02, 01-03 | TestClient contract tests for /solve, /rate, /team, /health, /meta with mocked FPL API | ✓ SATISFIED | 67 passing tests, unchanged, all 5 endpoints covered, zero network egress. REQUIREMENTS.md marks `[x]` and Phase 1 = Complete. |
| APIT-02 | 01-03 | require_key covered open/valid/invalid | ✓ SATISFIED | Unchanged, included in 67-passing suite. REQUIREMENTS.md marks `[x]`. |
| APIT-03 | 01-03 | Concurrency test with autouse state-reset fixture | ✓ SATISFIED | Unchanged, included in 67-passing suite. REQUIREMENTS.md marks `[x]`. |
| UI-01 | 01-01, 01-04, 01-05, 01-06 | React/Vite app, 8 routes, dev proxy, runtime-fetched JSON, plus this gap-closure's chrome-containment correction | ✓ SATISFIED | All 8 routes + catch-all registered; dev-proxy proven live in prior pass (unchanged); build purity confirmed; G-01-3 closed at the class-token/test level. REQUIREMENTS.md marks `[x]`; `01-06-SUMMARY.md` frontmatter lists `requirements-completed: [UI-01]`. |

No orphaned requirements: REQUIREMENTS.md's traceability table maps exactly APIT-01, APIT-02, APIT-03, UI-01 to Phase 1 (all marked Complete), matching every plan's `requirements:` frontmatter field, including 01-06.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/PageShell.tsx:32,59,64` + `PageShell.test.tsx:12` | — | The literal containment token string `mx-auto w-full max-w-[68rem] px-4` is duplicated across 4 independent sites (header wrapper, main, footer paragraph, test's `CONTAINMENT` const) rather than derived from one shared constant (flagged in the incremental `01-REVIEW.md` for plan 01-06) | ℹ️ Info (non-blocking) | The new regression test mitigates the immediate risk — it will catch a future edit that updates only 1-2 of the 3 JSX sites. But a deliberate width change (e.g. `68rem` → `72rem`) still needs 4 manual, uncoordinated edits. Same defect class that produced G-01-3 originally; not elevated to Warning because the test now guards it. Not a phase-blocking issue. |

No 🛑 Blocker-severity anti-patterns found. No unreferenced TBD/FIXME/XXX markers in any file touched by plan 01-06. The three pre-existing Warning-level findings (WR-01 unchecked cast, WR-02 vitest.config.ts tsconfig exclusion, WR-03 now independently resolved) and the typecheck-no-op Advisory Finding remain unchanged from the prior verification and are already routed to Phase 2/Phase 5 — not re-litigated here.

## Human Verification Required

### 1. Final visual re-confirmation of G-01-3 at a wide viewport

**Test:** Run `npm --prefix frontend run dev`, open the app maximized on a wide display (~1720px). Confirm brand+nav now sit in a centered column whose left edge lines up with the page heading beneath it and whose right edge lines up with the end of the footer disclaimer — no large empty gutter beside the nav. Then narrow to ~375px and confirm the nav still wraps onto a second row with no hamburger and unchanged side padding.
**Expected:** Header/main/footer content edges visually align at every width; no full-bleed/stranded-nav regression from the original G-01-3 report.
**Why human:** jsdom (the environment `PageShell.test.tsx` runs in) has no layout engine — it proves the correct Tailwind class tokens are on the correct elements (independently re-confirmed above) but cannot measure rendered pixel geometry. That real-browser proof is formally and traceably handed to Phase 4's Playwright suite (`E2E-01`) via `deferred-items.md` and the ROADMAP Phase 4 research flags, both independently confirmed present and correctly scoped in this re-verification. This item is recorded per `workflow.human_verify_mode=end-of-phase`; the strength and specificity of the automated evidence (structurally-sound class-token fix, independently reviewed by `01-REVIEW.md`'s incremental pass, negative full-bleed assertions, code diff matching SUMMARY exactly) means it is not treated as a blocking gap, but it cannot be marked mechanically VERIFIED either.

### 2. Package-legitimacy and PII sign-offs (recorded, listed for completeness — carried forward unchanged)

**Test:** No action needed — already answered.
**Expected:** N/A.
**Why human:** Unchanged since the prior verification pass. Both items carry `verification: judgment` and a recorded "Approved" answer in `01-01-SUMMARY.md`, independently re-corroborated via git/grep in this pass. Listed per protocol for completeness of the human-verification ledger.

## Gaps Summary

No blocking gaps. UAT gap **G-01-3** (header/nav full-bleed at wide viewports) is closed at the level this phase's toolchain can mechanically prove: `PageShell.tsx`'s header and footer now share the exact same containment class-token set as `<main>` (`mx-auto w-full max-w-[68rem] px-4`), locked by a new `PageShell.test.tsx` that fails if any of the three chrome sections drifts, verified independently via source read, a fresh test run (5 files/9 tests green), a fresh build (succeeds), and an independent grep of the negative full-bleed/typography-scaling constraints. The incremental `01-REVIEW.md` pass for plan 01-06 independently reached the same "structurally-sound fix" conclusion and found no critical or blocking issues, only a non-blocking Info-level duplication note.

The one thing that remains genuinely unprovable in Phase 1's environment is real rendered pixel geometry — jsdom has no layout engine. This has been explicitly and traceably deferred to Phase 4 (`E2E-01`) via two independent, cross-checked artifacts (`deferred-items.md` and the ROADMAP Phase 4 research flags), both confirmed present and correctly scoped by this re-verification (exactly 2 occurrences of `G-01-3` in `ROADMAP.md`, no leakage into Phase 3 or Phase 5). Per this project's `workflow.human_verify_mode=end-of-phase`, a lightweight final visual confirmation of the fix is recorded as a human-verification item rather than a blocking gap, given the strength and specificity of the automated evidence already gathered.

The phase resolves to `human_needed` rather than `passed` for the same structural reason as the prior verification pass: a visual/geometric claim exists that cannot be mechanically proven in this toolchain. This is not a defect discovered by this re-verification — it is the expected, correctly-scoped boundary between what a jsdom-based unit test can prove and what only a real-browser E2E suite (Phase 4) can prove.

---

_Verified: 2026-09-01T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
