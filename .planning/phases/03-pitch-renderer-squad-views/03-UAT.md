---
status: testing
phase: 03-pitch-renderer-squad-views
source: [03-VERIFICATION.md]
started: 2026-09-03T07:00:00Z
updated: 2026-09-03T07:00:00Z
---

## Current Test

number: 1
name: Pitch visual rendering and mobile responsiveness (UI-07, PITCH-02)
expected: |
  Pitch reads as an FPL-style pitch at both desktop and 375px width; no horizontal
  overflow; kit colours/patterns legible; exactly one C badge and at most one V badge
  visible; dark mode keeps text legible against the pitch tokens.
awaiting: user response

## Tests

### 1. Pitch visual rendering and mobile responsiveness (UI-07, PITCH-02)
expected: Open /team (no ?entry=) at desktop and 375px viewport. Green gradient surface with white decorative markings, formation rows top-to-bottom (GK/DEF/MID/FWD), bench in its own non-green strip. Cards shrink without the 5-column grid reflowing; name ellipsis works; price/xP never hidden; no horizontal overflow; dark mode legible.
result: [pending]

### 2. Rate-tab diff styling and post-solve badges (PITCH-03, PITCH-04)
expected: With an entry loaded, the Rate tab's out card is visually dimmed/marked distinct; the ghost card (dashed border, reduced opacity) sits in the correct formation row; Squad tab post-solve IN badges visible and placed per UI-SPEC; solve results bar and plan-transfers per-week blocks wrap correctly at phone width.
result: [pending]

### 3. Trademark posture sign-off (PITCH-01)
expected: Read docs/decisions/pitch-kit-sourcing.md in full. The neutral-SVG-kit posture (no crest/sponsor/CDN imagery, non-legal-opinion caveat) reads as sound and sufficient without formal legal review at this stage — something you are willing to stand behind at a future payment-gateway review.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
