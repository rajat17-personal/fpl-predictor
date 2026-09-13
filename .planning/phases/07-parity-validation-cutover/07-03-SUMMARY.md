---
phase: 07-parity-validation-cutover
plan: 03
subsystem: ui
tags: [react, tailwind, accessibility, contrast, playwright, parity]

# Dependency graph
requires:
  - phase: 07-parity-validation-cutover/07-02
    provides: the eight-page scripted parity comparison tool (e2e/parity/parity-diff.mjs) and PARITY-REPORT.md's stage tables
provides:
  - "PARITY-REPORT.md's pre-deadline stage fully closed: 8 scripted page verdicts, the manual-eyeball verdict, and the D-08 same-session solver verdict, all traceable to a ledger number, a commit SHA, or a cron-green citation"
  - "Three React-only UI fixes: pitch-card stat-text contrast (WCAG AA against the pitch-1/pitch-2 gradient in both themes), a red dashed outline on the suggested-out player mirroring GhostCard's green idiom, and a header layout fix keeping the GW deadline pill and theme toggle on the same row as the nav tabs at desktop width"
  - "D-02 dogfooding handover: the React site is now the user's daily driver for the rest of GW4, vanilla standing by as reference"
affects: [07-04, 07-05, 07-06]

# Actuals (#2632)
actuals:
  tokens: 6900
  tasks: 1
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Theme-invariant CSS custom-property pair (--color-pitch-stat-bg/-ink) for text overlaid on a background that varies in luminance along a gradient, rather than trying to find one flat text color with adequate contrast against every gradient stop"
    - "Boolean prop threaded through a row-level component (PitchRow's onPitch) to distinguish 'same component, different background' cases, applied only to the branch that actually sits on the varying background (never to GhostCard's own internal PlayerCard, which always sits on a fixed accent-bg card)"

key-files:
  created: []
  modified:
    - frontend/src/components/pitch/PlayerCard.tsx
    - frontend/src/components/pitch/PlayerCard.test.tsx
    - frontend/src/components/pitch/Pitch.tsx
    - frontend/src/components/pitch/Pitch.test.tsx
    - frontend/src/index.css
    - frontend/src/components/PageShell.tsx
    - frontend/src/components/GwBanner.tsx
    - frontend/src/components/GwBanner.test.tsx
    - e2e/specs/smoke.spec.ts
    - .planning/phases/07-parity-validation-cutover/PARITY-REPORT.md

key-decisions:
  - "GwBanner's two-line text was reflowed (line 1 'GW{gw} · {absolute deadline}', line 2 '{countdown} · {freshness}') to close a ~200px desktop layout overflow, rather than shrinking fonts or widening the header's max-width past main/footer's shared 68rem cap (which would have reopened the G-01-3 stranded-nav alignment bug Phase 1 already fixed)."
  - "The three manual-pass defects (pitch contrast, outgoing outline, nav wrap) were fixed forward as plain React code changes, not new PARITY-DEVIATIONS.md ledger rows — they are UI bugs the user found by eyeball, not field-level React/vanilla behavioral divergences the scripted comparison tracks."
  - "PILL_CLASS's exact 'px-3 py-1.5' Tailwind classes were left untouched despite the general nav-spacing tightening, because e2e/parity/extract.mjs's React banner selector (header div[class*=\"px-3 py-1.5\"]) matches on that literal substring; changing it would have silently broken the scripted xP-table/Rate-my-team/etc. banner-field extraction."

patterns-established:
  - "Pattern: a dark semi-opaque backdrop token pair (bg + ink) for text overlaid on a photographic/gradient background, applied conditionally via a boolean prop threaded down only to the render branch that actually sits on that background."

requirements-completed: []  # CUT-01 is a phase-wide, multi-stage requirement (full gameweek cycle); this plan closes only its pre-deadline stage. See Deviation #4 -- do not mark CUT-01 complete until 07-06 (the cutover gate) finishes.

coverage:
  - id: D1
    description: "PARITY-REPORT.md's pre-deadline stage fully closed: 8 scripted page rows (0 unexplained defects), the manual-eyeball row, and the D-08 solver-comparison row, each carrying the user's verbatim verdict or a fixing commit/ledger citation"
    requirement: "CUT-01"
    verification:
      - kind: other
        ref: "node e2e/parity/parity-diff.mjs --all --vanilla-origin http://127.0.0.1:8010 --react-origin http://127.0.0.1:8011 -> TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects, exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pitch-card stat-text contrast fix (price/xP and range-line text readable against the pitch-1/pitch-2 gradient, both themes) and the subbed-out red dashed outline"
    requirement: "CUT-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/pitch/PlayerCard.test.tsx#PlayerCard — pitch stat-line contrast (07-03 UAT G-07-1), PlayerCard — outgoing red dashed outline (07-03 UAT G-07-2)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/pitch/Pitch.test.tsx#Pitch — onPitch contrast threading (07-03 UAT G-07-1)"
        status: pass
      - kind: manual_procedural
        ref: "Live Playwright screenshot at 1280px, light+dark themes, http://127.0.0.1:8011/team?entry=6980093&tab=rate — confirms readable white-on-dark-chip stat text on every pitch row and the O'Reilly (red dashed) / Virgil (green dashed) swap pair"
        status: pass
    human_judgment: false
  - id: D3
    description: "Header layout fix: GW deadline pill and theme toggle stay on the same row as the nav tabs at desktop width (~1280px); mobile wrap unaffected"
    requirement: "CUT-01"
    verification:
      - kind: e2e
        ref: "e2e/specs/smoke.spec.ts (42/42 Playwright specs pass with updated frozen banner-text constants)"
        status: pass
      - kind: manual_procedural
        ref: "Live Playwright measurement at 1280px: header height 83px (one line) vs. 145px (wrapped) pre-fix, confirmed in both light and dark themes; 375px mobile still wraps by design"
        status: pass
    human_judgment: false

duration: 28min
completed: 2026-09-08
status: complete
---

# Phase 7 Plan 3: Pre-Deadline Parity Pass Summary

**Fixed three React-only UAT defects (pitch stat-text contrast, missing outgoing-player outline, desktop nav-row wrap) reported after the user's real GW4 manual pass, then closed out PARITY-REPORT.md's pre-deadline stage with the user's verbatim verdicts — 8/8 pages, manual eyeball, and D-08 solver comparison all clean.**

## Performance

- **Duration:** ~28 min (this continuation session, from checkpoint resume to sign-off). The scripted Tasks 1–2 and the Task 3 handover setup ran ~10 min in the prior session before the checkpoint pause.
- **Started:** 2026-09-08T06:44:00Z (dual-site servers already running per the checkpoint handover)
- **Completed:** 2026-09-08T07:12:09Z
- **Tasks:** 1 (closing out Task 3's checkpoint: fix reported defects, record verdicts)
- **Files modified:** 10

## Accomplishments

- Fixed pitch-card stat-text contrast (UAT G-07-1): price/xP and range-line text now render on a dark semi-opaque backdrop with white text, readable against both pitch-1/pitch-2 gradient stops in both themes — applied only to real cards on a grass row (GK/DEF/MID/FWD), never Bench or a GhostCard's own accent-bg card.
- Gave the suggested-out player the same dashed-outline idiom as the incoming ghost card, in the `bad` (red) token instead of `accent` (green), so a suggested swap reads as one out/in pair at a glance (UAT G-07-2).
- Closed the desktop-width nav-row wrap (UAT G-07-3): tightened header spacing and reflowed GwBanner's two lines, cutting the row from ~1289px to comfortably under its 1088px (68rem) container cap — confirmed live via Playwright (header 83px tall, single line, at 1280px, both themes).
- Re-ran the full 8-page scripted parity pass post-fix: `TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects`, exit 0 — the three fixes introduced no new scripted delta.
- Recorded the user's verbatim manual-pass and D-08 same-session solver-comparison verdicts in `PARITY-REPORT.md`, computed the "Cutover readiness" totals (8 pages, 11 explained deltas, 5 defects found/closed, 0 remaining unexplained), and confirmed D-02 dogfooding continues on the React site for the rest of GW4.

## Task Commits

Prior session (before the checkpoint pause):
1. **Baseline: Land pre-deadline GW4 weekly export snapshot** - `ac489ca` (chore)
2. **Task 1: Pre-deadline scripted pass across all eight pages** - `fab419c` (feat)
3. **Task 2: Close every pre-deadline defect by new ledger row** - `ff42e75` (feat)
4. **Task 3 (setup): Hand over the manual pass and D-08 solver comparison** - `556f141` (feat)

This continuation session:
5. **Fix: pitch-card stat-text contrast + outgoing red dashed outline** - `a2839a8` (fix)
6. **Fix: keep GW deadline/theme toggle on the nav row at desktop width** - `86aba31` (fix)
7. **Fix: close remaining ~30px gap in the nav-row wrap fix** - `6a39d64` (fix)
8. **Docs: record the manual-pass and D-08 handover verdicts** - `ed71841` (docs)

**Plan metadata:** this SUMMARY's own commit (below)

## Files Created/Modified

- `frontend/src/components/pitch/PlayerCard.tsx` - Added `onPitch` prop; pitch-stat backdrop classes on the price/xP and range-line spans; red dashed outline wrapper for `diff="out"`
- `frontend/src/components/pitch/PlayerCard.test.tsx` - New tests for the contrast fix and the outgoing dashed outline
- `frontend/src/components/pitch/Pitch.tsx` - Threaded `onPitch` through `PitchRow` to the real (non-ghost) `PlayerCard` on GK/DEF/MID/FWD rows only
- `frontend/src/components/pitch/Pitch.test.tsx` - New tests confirming `onPitch` reaches grass-row cards but not Bench or GhostCard
- `frontend/src/index.css` - Added `--color-pitch-stat-bg`/`-ink` tokens
- `frontend/src/components/PageShell.tsx` - Tightened header section/nav-link spacing to close the desktop wrap
- `frontend/src/components/GwBanner.tsx` - Reflowed the two-line pill text (dropped "deadline:" label, redistributed content)
- `frontend/src/components/GwBanner.test.tsx` - Updated banner-text regex assertions for the new line 1/line 2 split
- `e2e/specs/smoke.spec.ts` - Updated the frozen `BANNER_LINE_1`/`BANNER_LINE_2` constants to match GwBanner's new text
- `.planning/phases/07-parity-validation-cutover/PARITY-REPORT.md` - Filled the manual-eyeball and D-08 verdict rows, added the three defect rows, computed Cutover readiness totals

## Decisions Made

- Reflowed `GwBanner`'s copy (dropped the literal "deadline:" label; redistributed the absolute deadline, countdown, and freshness text across the same two lines) instead of shrinking fonts or widening the header past its shared 68rem cap. This field's deltas are already blanket-explained by `PARITY-DEVIATIONS.md` #3/#4 (`extract.mjs`'s `BANNER_FIELD.knownDeviations`), so reflowing its wording introduces no new parity defect — confirmed by the post-fix scripted re-run still reporting the banner delta as `explained (ledger #3)` on every page.
- Left `PILL_CLASS`'s exact `px-3 py-1.5` untouched even while tightening every other spacing value in the header, because `e2e/parity/extract.mjs`'s React banner selector matches on that literal class substring — changing it would have silently broken the scripted comparison's ability to find the banner field at all.
- Treated all three manual-pass defects as plain React code fixes (not new `PARITY-DEVIATIONS.md` ledger rows), per Task 2's own closure discipline: they are visual/UX bugs the user found by eyeball, not deliberate React/vanilla behavioral divergences the ledger tracks.
- Verified the actual required layout-width reduction via a live Playwright measurement (not hand arithmetic) after an initial character-width estimate undershot by ~30px and still wrapped by half a pixel — real font metrics (IBM Plex Sans/Mono, Chromium) don't match a flat per-character estimate closely enough to trust without measuring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed low-contrast pitch-card stat text (UAT G-07-1)**
- **Found during:** Task 3 (user's manual pass)
- **Issue:** `PlayerCard`'s price/xP and range-line spans used `--color-ink-2` directly on the green `pitch-1`/`pitch-2` gradient, failing WCAG AA against both gradient stops in either theme (computed contrast ratios 2.81:1–3.02:1 against the two worst-case combinations, both well under the 4.5:1 threshold for 14px text).
- **Fix:** Added theme-invariant `--color-pitch-stat-bg`/`-ink` tokens (dark backdrop + white text, computed worst-case contrast ~9.6:1) applied only to real cards on a grass row.
- **Files modified:** `frontend/src/index.css`, `frontend/src/components/pitch/PlayerCard.tsx`, `frontend/src/components/pitch/Pitch.tsx`
- **Verification:** New unit tests in `PlayerCard.test.tsx`/`Pitch.test.tsx`; live Playwright screenshot at 1280px, light+dark.
- **Committed in:** `a2839a8`

**2. [Rule 1 - Bug] Added the missing outgoing-player red dashed outline (UAT G-07-2)**
- **Found during:** Task 3 (user's manual pass)
- **Issue:** The suggested-out player in a best-XI swap carried only `opacity-50` and an `sr-only` label — no visible marking matching the incoming ghost card's green dashed outline.
- **Fix:** `diff="out"` now gets the same dashed-outline idiom as `GhostCard`, in the `bad` (red) token.
- **Files modified:** `frontend/src/components/pitch/PlayerCard.tsx`
- **Verification:** New unit test in `PlayerCard.test.tsx`; live Playwright screenshot of the O'Reilly → Virgil swap.
- **Committed in:** `a2839a8`

**3. [Rule 1 - Bug] Fixed the desktop-width nav-row wrap (UAT G-07-3)**
- **Found during:** Task 3 (user's manual pass)
- **Issue:** The GW deadline pill and theme toggle wrapped onto a second header row below the nav tabs at any desktop viewport ≥ ~1120px — the header's inner container is capped at 68rem/1088px regardless of viewport, and the un-tightened row's natural content width measured ~1289px.
- **Fix:** Tightened header section/nav-link spacing and reflowed `GwBanner`'s two lines (see Decisions above). First tightening pass left the row within 0.5px of the container width and still wrapped; a second, Playwright-measured pass (nav padding `px-2`→`px-1.5`, nav gap→0, outer gap→`gap-1`) closed the remaining gap with real margin (measured natural width ~1000px against the 1088px cap).
- **Files modified:** `frontend/src/components/PageShell.tsx`, `frontend/src/components/GwBanner.tsx`, `frontend/src/components/GwBanner.test.tsx`, `e2e/specs/smoke.spec.ts`
- **Verification:** Full frontend suite (374/374) and e2e Playwright suite (42/42, including updated frozen banner-text assertions) both green; live Playwright measurement confirms one-line header at 1280px (both themes), 375px mobile unaffected.
- **Committed in:** `86aba31`, `6a39d64`

**4. [Rule 1 - Bug] Reverted a premature CUT-01 requirement completion**
- **Found during:** the state_updates step
- **Issue:** All six 07-0X plans (`07-01` through `07-06`) name `requirements: [CUT-01]` in their frontmatter, since CUT-01 is a single phase-wide, multi-stage requirement ("the React site completes a full gameweek cycle (deadline → live → finished) side-by-side with verified parity"). Running `gsd_run query requirements.mark-complete CUT-01` per the standard state_updates step flipped `REQUIREMENTS.md`'s CUT-01 checkbox and traceability-table row to Complete after only this plan's pre-deadline stage — before the mid-gameweek/post-finish stages (07-04/07-05) or the D-15 cutover gate (07-06) have run. That would have misrepresented CUT-01 as satisfied to any later gate (`/gsd-ship`, the D-15 human cutover checkpoint) that reads `REQUIREMENTS.md` for the milestone's true state.
- **Fix:** Reverted `REQUIREMENTS.md` via `git checkout` before it was committed (the change was uncommitted at the time). Left CUT-01 as `[ ] Pending` for this SUMMARY's metadata commit. The correct plan to mark it complete is `07-06` (the cutover gate), once the full cycle and its verification actually finish.
- **Files modified:** `.planning/REQUIREMENTS.md` (reverted, not committed)
- **Verification:** `grep CUT-01 .planning/REQUIREMENTS.md` shows `[ ]` / `Pending` after the revert.
- **Committed in:** N/A — this is a revert of an uncommitted, over-eager automatic step; no commit carries the premature completion.

---

**Total deviations:** 4 auto-fixed (3 Rule 1 visual/contrast bugs from the manual UAT pass; 1 Rule 1 revert of a premature requirement-completion side effect). No scope creep.
**Impact on plan:** All three UI fixes were essential to close the manual-eyeball row with a genuine "passed" verdict rather than a deferred defect. The requirements-completion revert is corrective, not additive — it prevents this plan's state_updates step from misrepresenting a later-plan gate as already satisfied. No architectural changes; no new dependencies; no ledger rows (plain React code fixes).

## Issues Encountered

- The first layout-tightening pass for UAT G-07-3 was based on a per-character width estimate (IBM Plex Sans/Mono average glyph width) and undershot the real required reduction: the row still wrapped by roughly half a pixel even after cutting ~230px of estimated width. Resolved by measuring the actual rendered DOM via a headless Playwright script (`row.style.flexWrap = "nowrap"` + `getBoundingClientRect()`) instead of continuing to estimate, which revealed the true natural width (1088.5px) and let a second, smaller tightening pass close the gap with real margin (confirmed final natural width ~1000px).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 7's pre-deadline stage is fully closed: 8/8 scripted pages clean, manual eyeball passed (after 3 fixes), D-08 solver comparison matched. `PARITY-REPORT.md`'s Cutover readiness section now carries real, non-placeholder totals for this stage.
- Dual-site servers (`http://127.0.0.1:8010` vanilla, `http://127.0.0.1:8011` react) are left running per D-02's dogfooding handover — the user continues using the React site as their daily driver for the rest of GW4, with vanilla standing by as reference.
- Mid-gameweek and post-finish stages (07-04/07-05, per the D-07 three-pass cycle) remain to be run once the gameweek reaches those states — this plan's job (pre-deadline) is done.
- No blockers. The three fixes were narrowly scoped (pitch-card contrast, outgoing outline, header spacing) and did not touch any pipeline, vanilla, or frozen-fixture file.

---
*Phase: 07-parity-validation-cutover*
*Completed: 2026-09-08*
