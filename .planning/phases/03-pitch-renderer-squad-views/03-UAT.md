---
status: complete
phase: 03-pitch-renderer-squad-views
source: [03-VERIFICATION.md]
started: 2026-09-03T07:00:00Z
updated: 2026-09-03T09:00:00Z
---

## Current Test

[testing complete]

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

## Summary

total: 3
passed: 2
issues: 1
pending: 0
skipped: 0
blocked: 0

## Deferred Follow-Ups

- test: 2
  idea: "Is there a better way of showing the transferred player? maybe replace the transferred player and small warning/or other label to indicate the change (instead of ghost card)"
  deferred_at: 2026-09-03

## Gaps

- gap_id: G-03-1
  truth: "Formation rows render centered on the pitch regardless of row size — a 2-striker row or 4-player DEF/MID row sits horizontally centered, matching the 5-column grid's visual midline"
  status: failed
  reason: "User reported: when the team loads two strikers they are not central. and instead a drift a bit left. same when I load my team and 4 def and 4 mid are displayed."
  severity: cosmetic
  test: 1
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis
