---
phase: 02-data-layer-non-pitch-pages
fixed_at: 2026-09-01T15:59:00Z
review_path: .planning/phases/02-data-layer-non-pitch-pages/02-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-09-01T15:59:00Z
**Source review:** .planning/phases/02-data-layer-non-pitch-pages/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (fix_scope: critical_warning — 0 critical findings, 2 warnings; the
  3 Info findings in REVIEW.md were out of scope for this run)
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: Model-mode price note silently renders "NaN%"/"undefined" if optional fields are absent

**Files modified:** `frontend/src/routes/Prices.tsx`, `frontend/src/routes/Prices.test.tsx`
**Commit:** 6bfbe23
**Applied fix:** Guarded `w.val_moved_hit` in `ModeNote`'s model-mode branch the same way
`w.trained_utc` was already guarded — replaced the non-null assertion
(`w.val_moved_hit!`) with a `!= null` check that falls back to an en-dash (`–`), and
added `?? "unknown date"` to the `trained_utc` fallback for symmetry. Added a regression
test (`Prices.test.tsx`) that mocks a watchlist payload with both fields absent and
asserts the note renders "trained unknown date" / "hit-rate on actual movers – in
validation" instead of "NaN%"/"undefined". Verified via `npx vitest run
src/routes/Prices.test.tsx` (15/15 passed) and `npx tsc --noEmit -p tsconfig.app.json`
(clean).

### WR-02: Internal markdown link bypasses client-side routing

**Files modified:** `frontend/src/routes/Methodology.tsx`, `frontend/src/routes/Methodology.test.tsx`
**Commit:** 874a40f
**Applied fix:** Replaced `Methodology.tsx`'s `ReactMarkdown` `a` component override —
which previously rendered every link as a plain `<a>` — with one that detects a
root-relative `href` (starting with `/`) and renders react-router's `<Link>` instead,
falling back to a plain `<a>` for external/non-root-relative links. Added a regression
test (`Methodology.test.tsx`) that renders the page inside a two-route `MemoryRouter`
(with a `/scoreboard` stub route), fires a click on the "scoreboard" link, and asserts
the stub route's content replaces the methodology page in place — proving the link
performs a client-side transition rather than a full-page reload/navigation attempt.
Verified via `npx vitest run src/routes/Methodology.test.tsx` (8/8 passed) and `npx tsc
--noEmit -p tsconfig.app.json` (clean).

## Skipped Issues

None — both in-scope findings were fixed.

## Full-Suite Verification

All commands below were run inside the isolated review-fix worktree
(`.claude/worktrees/rf-02-152556-1788278050`, on temp branch
`gsd-reviewfix/02-152556`), after both fixes above were committed. `node_modules` for the
worktree was a symlink to the main checkout's `frontend/node_modules` (Linux — safe;
no reparse-point/junction risk here) since git worktrees do not carry
`node_modules`.

- `npm --prefix frontend run test` — **171/171 tests passed** (169 pre-existing + 2 new
  regression tests added by this fix pass), 22 test files.
- `npm --prefix frontend run typecheck` — clean, no errors.
- `bash scripts/verify_frontend_build.sh` — `BUILD PURITY OK` (production build
  succeeded; no `web/data/*.json` pipeline export leaked into `frontend/dist`).

These numbers were produced inside the review-fix worktree, not the main checkout — the
worktree is torn down (fast-forwarded into `master`, then removed) once this report is
written. They are reproducible by re-running the same three commands from `master` after
the fast-forward, since both fix commits (6bfbe23, 874a40f) carry forward unchanged.

## Not In Scope (Info findings, fix_scope=critical_warning)

For completeness, the following Info-tier findings from REVIEW.md were left untouched
per the requested `fix_scope`:

- **IN-01** — no runtime validation of fetched JSON in `frontend/src/lib/api.ts` /
  `frontend/src/routes/Scoreboard.tsx`.
- **IN-02** — `PriceTable` rows keyed on `r.name` in `frontend/src/routes/Prices.tsx:133`
  (no stable id in the `WatchlistRow` backend contract).
- **IN-03** — empty (but present) captains array renders empty table shell in
  `frontend/src/routes/XpTable.tsx:227-271`.

---

_Fixed: 2026-09-01T15:59:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
