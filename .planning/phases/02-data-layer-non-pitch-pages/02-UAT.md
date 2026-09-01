---
status: testing
phase: 02-data-layer-non-pitch-pages
source: [02-VERIFICATION.md]
started: 2026-09-01T11:30:00Z
updated: 2026-09-01T11:30:00Z
---

## Current Test

number: 1
name: No flash of wrong theme on reload
expected: |
  With `localStorage['fpl-theme']` unset and the OS in dark mode, hard-reload the app:
  no flash of the light theme before dark styling applies (the pre-mount head script in
  `frontend/index.html` puts the dark class on `<html>` before first paint).
awaiting: user response

## Tests

### 1. No flash of wrong theme on reload
expected: With `localStorage['fpl-theme']` unset and the OS in dark mode, hard-reload the app — no flash of the light theme before dark styling applies. Repeat after choosing Light and after choosing Dark from the toggle.
result: [pending]

### 2. FDR ramp reads easy-to-hard in both themes
expected: On `/fixtures`, the 1–5 difficulty ramp and legend read unambiguously easy-to-hard at a glance in light and dark themes. Note: the port copies vanilla's hex values verbatim, which are blue-to-red rather than literal green-to-red — confirm this is what the ROADMAP's "standard 1–5 green→red convention" intended.
result: [pending]

### 3. Price trend icons distinguishable
expected: On `/prices` in both themes, the TrendingUp (accent) and TrendingDown (destructive) icons on riser/faller rows are visually distinguishable at a glance.
result: [pending]

### 4. Differentials band scaling at low caps
expected: On `/differentials`, dragging the ownership slider across its 1–25% range (especially near the low end) rescales band widths sensibly; the `maxHi = Math.max(1, ...)` floor visibly prevents the band track from filling the whole cell when all qualifying p90/xp values are small.
result: [pending]

### 5. Scoreboard 404-vs-error through the real proxy
expected: With the dev proxy running and `web/data/scoreboard.json` genuinely absent (pre-season), `/scoreboard` renders the pre-season zero-state (three backtest tiles + paragraph), not an error state — proving the 404-vs-server-failure distinction end-to-end.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
