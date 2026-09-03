---
status: testing
phase: 03-pitch-renderer-squad-views
source: [03-VERIFICATION.md]
started: 2026-09-03T07:00:00Z
updated: 2026-09-03T07:45:00Z
---

## Current Test

number: 4
name: Visual re-check of pitch row centering after 03-05 fix (G-03-1)
expected: |
  Open /team at desktop and 375px viewport, light and dark mode, on the 3-5-2 model
  squad and a loaded 4-4-2 entry. Every formation row and the bench read as
  horizontally centered on the pitch midline — including the 2-card FWD row and
  4-card DEF/MID/bench rows — with no horizontal overflow and name ellipsis intact.
awaiting: user response

## Tests

### 1. Pitch visual rendering and mobile responsiveness (UI-07, PITCH-02)
expected: Open /team (no ?entry=) at desktop and 375px viewport. Green gradient surface with white decorative markings, formation rows top-to-bottom (GK/DEF/MID/FWD), bench in its own non-green strip. Cards shrink without the 5-column grid reflowing; name ellipsis works; price/xP never hidden; no horizontal overflow; dark mode legible.
result: issue
reported: "when the team loads two strikers they are not central. and instead a drift a bit left. same when I load my team and 4 def and 4 mid are displayed."
severity: cosmetic

### 2. Rate-tab diff styling and post-solve badges (PITCH-03, PITCH-04)
expected: With an entry loaded, the Rate tab's out card is visually dimmed/marked distinct; the ghost card (dashed border, reduced opacity) sits in the correct formation row; Squad tab post-solve IN badges visible and placed per UI-SPEC; solve results bar and plan-transfers per-week blocks wrap correctly at phone width.
result: pass
note: "User confirmed ghost card okay; asked about 5-DEF edge case (verified handled — Pitch.tsx row grows to 6 columns) and suggested in-place replacement design (captured as deferred follow-up)"

### 3. Trademark posture sign-off (PITCH-01)
expected: Read docs/decisions/pitch-kit-sourcing.md in full. The neutral-SVG-kit posture (no crest/sponsor/CDN imagery, non-legal-opinion caveat) reads as sound and sufficient without formal legal review at this stage — something you are willing to stand behind at a future payment-gateway review.
result: pass

### 4. Visual re-check of pitch row centering after 03-05 fix (G-03-1)
expected: Open /team at desktop and 375px viewport, light and dark mode, on the 3-5-2 model squad and a loaded 4-4-2 entry. Every formation row and the bench read as horizontally centered on the pitch midline — including the 2-card FWD row and 4-card DEF/MID/bench rows — with no horizontal overflow and name ellipsis intact.
result: [pending]

## Summary

total: 4
passed: 2
issues: 1
pending: 1
skipped: 0
blocked: 0

## Deferred Follow-Ups

- test: 2
  idea: "Is there a better way of showing the transferred player? maybe replace the transferred player and small warning/or other label to indicate the change (instead of ghost card)"
  deferred_at: 2026-09-03

## Gaps

- gap_id: G-03-1
  truth: "Formation rows render centered on the pitch regardless of row size — a 2-striker row or 4-player DEF/MID row sits horizontally centered, matching the 5-column grid's visual midline"
  status: fix_shipped
  closed_by: 03-05 (commits 25a7244, 4e83899; awaiting visual confirmation — test 4)
  reason: "User reported: when the team loads two strikers they are not central. and instead a drift a bit left. same when I load my team and 4 def and 4 mid are displayed."
  severity: cosmetic
  test: 1
  root_cause: "centeredStartColumn() in Pitch.tsx (L31-33) centers rows by integer CSS grid start column in a fixed 5-column grid; even card counts (2, 4) need a half-integer start, Math.floor drops the 0.5, shifting the row half a column-pitch left (~61px desktop, ~32px at 375px). Odd rows (1/3/5) center exactly, matching the report. Bench (n=4) affected too. UI-SPEC L103-105 prescribed a no-op mechanism (justify-content:center on 1fr tracks), so the implementer improvised the defective integer scheme."
  artifacts:
    - path: "frontend/src/components/pitch/Pitch.tsx"
      issue: "L31-33 centeredStartColumn integer-only centering; L96-97 columns/start; L100-101 row container; L106 per-cell gridColumn — one shared PitchRow serves GK/DEF/MID/FWD and bench, so one fix corrects all"
    - path: "frontend/src/components/pitch/Pitch.test.tsx"
      issue: "no positional/centering assertions — coverage hole that let a pure integer function ship wrong"
    - path: ".planning/phases/03-pitch-renderer-squad-views/03-UI-SPEC.md"
      issue: "L103-105 prescribes justify-content:center on minmax(0,1fr) tracks, a no-op — spec itself is wrong"
  missing:
    - "Swap PitchRow to display:flex justify-content:center with fixed basis calc((100% - (cols-1)*var(--pitch-gap))/cols), cols = max(5, slots.length) — continuous centering, D-07 no-reflow invariant holds, ghost row still divides by 6"
    - "Lift responsive gap to a custom property (--pitch-gap 4px/8px) so it survives inside the calc"
    - "Correct 03-UI-SPEC.md L103-105 so the broken mechanism isn't re-derived"
    - "Add symmetry regression test over n in {1,2,3,4,5,6} including odd controls (n=3, n=5)"
  debug_session: .planning/debug/pitch-row-centering-drift.md
