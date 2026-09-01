---
status: diagnosed
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
  root_cause: "Dark-mode neutral tokens in frontend/src/index.css .dark (lines 87-93) are green-family with up to 2.3x the chroma of their light-theme counterparts and sit within ~5-13 degrees of the brand accent hue (~154deg OKLCH), so the whole frame reads as a green wash. Values are byte-identical to vanilla web/assets/style.css:30-35 (not a port defect). Amplified by two dropped vanilla parity details: no color-scheme declaration and unpainted <body> (vanilla style.css:4,29,55)."
  artifacts:
    - path: "frontend/src/index.css"
      issue: "lines 87-93: over-chromatic, accent-colliding dark neutrals (--color-bg #111815, --color-surface #18211c, --color-surface-2 #1f2a24, --color-line #2c3831)"
    - path: "frontend/index.html"
      issue: "line 28: body unpainted, no color-scheme declaration"
    - path: "frontend/src/components/PageShell.tsx"
      issue: "line 40: bg-bg on inner div where vanilla painted body"
    - path: "web/assets/style.css"
      issue: "lines 30-35: upstream origin of identical values — change in lockstep or log divergence in PARITY-DEVIATIONS.md"
  missing:
    - "Re-balance dark neutrals: lock hue to accent (~154deg), hold lightness, cut chroma to light theme's per-role budget (illustrative: bg #141715, surface #1b201c, surface-2 #222924, line #2e3731)"
    - "Add color-scheme: light/dark declarations and paint body with --color-bg (straight parity regression fix)"
    - "Document chosen chroma budget in UI-SPEC Color table; decide lockstep-vs-diverge for vanilla and log in PARITY-DEVIATIONS.md"
  debug_session: .planning/debug/dark-theme-green-tint.md

- gap_id: G-02-2
  truth: "Fixture ticker cells present opponent and venue legibly; venue (H/A) label placement looks intentional, not awkward"
  status: failed
  reason: "User reported: only issue I see is that the A, H lable looks a bit akward can it come belwo the team instead of next to it"
  severity: cosmetic
  test: 2
  root_cause: "Parity regression, not new design: vanilla already stacks H/A below the opponent code (.fdr small { display: block } at web/assets/style.css:155 on an inline-block, text-centered chip), but FdrCell.tsx:61 ports the chip as a row-direction flex (inline-flex items-center gap-0.5), pinning the <small> beside the code. Markup is identical to vanilla; only the CSS diverged. UI-SPEC specified chip content but not internal layout; existing tests assert text only, not geometry."
  artifacts:
    - path: "frontend/src/components/FdrCell.tsx"
      issue: "line 61: row flex chip; line 64: <small> venue tag; line 56: min-w-[56px] misplaced on wrapper instead of chip (line 48 blank-cell branch already puts it on the chip)"
    - path: "frontend/src/routes/Fixtures.tsx"
      issue: "line 95: generic px-3 py-2 cell padding, missing vanilla's fixtures-specific tight cellpad (3px 4px, style.css:154) that absorbs the taller 2-line chip"
    - path: "frontend/src/components/FdrCell.test.tsx"
      issue: "7 tests, none assert layout geometry — cannot catch this regression class"
  missing:
    - "Swap chip to column stack (inline-flex flex-col items-center, drop gap-0.5) in FdrCell.tsx:61"
    - "Move min-w-[56px] from wrapper onto the chip so both branches match and columns stay aligned"
    - "Restore vanilla's tight fixtures cell padding on Fixtures.tsx:95 to cancel most of the ~14px/row growth"
    - "Optionally close adjacent font drift (font-mono, smaller size, opacity 0.75 on venue tag)"
    - "Add geometry regression test asserting column-direction class and min-width on the chip"
  debug_session: .planning/debug/fixture-venue-label-placement.md
