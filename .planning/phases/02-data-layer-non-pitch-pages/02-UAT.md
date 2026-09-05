---
status: complete
phase: 02-data-layer-non-pitch-pages
source: [02-VERIFICATION.md]
started: 2026-09-01T21:40:00Z
updated: 2026-09-02T00:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Dark-mode frame reads as dark, not green
expected: In forced dark mode, /fixtures (and other routes) read as a dark neutral frame with green accents — not a green-tinted wash. UA chrome (scrollbars, form controls, overscroll canvas) paints dark. Matches web/fixtures.html side-by-side.
result: pass

### 2. Stacked fixture chip matches vanilla at a glance
expected: On /fixtures, every fixture chip shows the venue letter (H/A) on its own line, centred beneath the opponent code, in mono type — matching web/fixtures.html. Ticker columns stay aligned (blank and populated chips share the same minimum width) and the table has not visibly inflated in height.
result: pass

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
