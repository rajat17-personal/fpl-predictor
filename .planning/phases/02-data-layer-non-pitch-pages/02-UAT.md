---
status: complete
phase: 02-data-layer-non-pitch-pages
source: [02-VERIFICATION.md]
started: 2026-09-01T11:30:00Z
updated: 2026-09-01T12:55:00Z
---

## Current Test

[testing complete]

## Tests

### 1. No flash of wrong theme on reload
expected: With `localStorage['fpl-theme']` unset and the OS in dark mode, hard-reload the app — no flash of the light theme before dark styling applies. Repeat after choosing Light and after choosing Dark from the toggle.
result: issue
reported: "dark mode looks okay although the colour looks a bit green"
severity: cosmetic

### 2. FDR ramp reads easy-to-hard in both themes
expected: On `/fixtures`, the 1–5 difficulty ramp and legend read unambiguously easy-to-hard at a glance in light and dark themes. Note: the port copies vanilla's hex values verbatim, which are blue-to-red rather than literal green-to-red — confirm this is what the ROADMAP's "standard 1–5 green→red convention" intended.
result: issue
reported: "only issue I see is that the A, H lable looks a bit akward can it come belwo the team instead of next to it"
severity: cosmetic

### 3. Price trend icons distinguishable
expected: On `/prices` in both themes, the TrendingUp (accent) and TrendingDown (destructive) icons on riser/faller rows are visually distinguishable at a glance.
result: pass

### 4. Differentials band scaling at low caps
expected: On `/differentials`, dragging the ownership slider across its 1–25% range (especially near the low end) rescales band widths sensibly; the `maxHi = Math.max(1, ...)` floor visibly prevents the band track from filling the whole cell when all qualifying p90/xp values are small.
result: pass

### 5. Scoreboard 404-vs-error through the real proxy
expected: With the dev proxy running and `web/data/scoreboard.json` genuinely absent (pre-season), `/scoreboard` renders the pre-season zero-state (three backtest tiles + paragraph), not an error state — proving the 404-vs-server-failure distinction end-to-end.
result: pass

## Summary

total: 5
passed: 3
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-02-1
  truth: "With OS dark mode and no stored theme, hard reload shows dark styling with correct dark palette colors from first paint"
  status: failed
  reason: "User reported: dark mode looks okay although the colour looks a bit green"
  severity: cosmetic
  test: 1
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-02-2
  truth: "Fixture ticker cells present opponent and venue legibly; venue (H/A) label placement looks intentional, not awkward"
  status: failed
  reason: "User reported: only issue I see is that the A, H lable looks a bit akward can it come belwo the team instead of next to it"
  severity: cosmetic
  test: 2
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis
