---
status: testing
phase: 02-data-layer-non-pitch-pages
source: [02-VERIFICATION.md]
started: 2026-09-01T21:40:00Z
updated: 2026-09-01T21:40:00Z
---

## Current Test

number: 1
name: Dark-mode frame reads as dark, not green
expected: |
  In forced dark mode (OS dark or the app's Dark toggle), visit /fixtures and a couple of other
  routes. The frame — background, cards, scrollbars, overscroll area — reads as dark neutral with
  a green accent on it, not as a green wash. Side-by-side with web/fixtures.html the dark palette
  looks identical (the two sites declare byte-identical dark hexes).
awaiting: user response

## Tests

### 1. Dark-mode frame reads as dark, not green
expected: In forced dark mode, /fixtures (and other routes) read as a dark neutral frame with green accents — not a green-tinted wash. UA chrome (scrollbars, form controls, overscroll canvas) paints dark. Matches web/fixtures.html side-by-side.
result: [pending]

### 2. Stacked fixture chip matches vanilla at a glance
expected: On /fixtures, every fixture chip shows the venue letter (H/A) on its own line, centred beneath the opponent code, in mono type — matching web/fixtures.html. Ticker columns stay aligned (blank and populated chips share the same minimum width) and the table has not visibly inflated in height.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
