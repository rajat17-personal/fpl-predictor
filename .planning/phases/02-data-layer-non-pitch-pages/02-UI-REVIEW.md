# Phase 02 — UI Review

**Audited:** 2026-09-01
**Baseline:** UI-SPEC.md (design contract)
**Screenshots:** Not captured (no dev server — code-only audit)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All page copy verbatim from vanilla; error/empty state messages custom and appropriate |
| 2. Visuals | 3/4 | Strong visual hierarchy in tables; spacing violations undermine layout consistency |
| 3. Color | 4/4 | All tokens, no hardcoded colors; full dark palette with FDR 1-5 ramp and semantic colors |
| 4. Typography | 3/4 | Four-role token system applied consistently; brand text uses arbitrary value instead of token |
| 5. Spacing | 2/4 | Spacing scale violations (18px gap); documented exceptions (44px, 56px, 68rem, 240px) correct |
| 6. Experience Design | 4/4 | Loading/error/empty states complete; accessibility implemented (aria, tooltips, dark mode); live GW countdown |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Fix `gap-[18px]` spacing violation in PageShell header** — Violates 4px multiple rule (should be 16 or 24). High-visibility component; use `gap-4` (16px) or `gap-6` (24px). — **BLOCKER** — `frontend/src/components/PageShell.tsx:42`

2. **Replace `text-[1.25rem]` with `text-heading` token in PageShell brand** — Arbitrary 20px value duplicates the `--text-heading` token already declared. Apply `text-heading` class to the brand `<span>`. — **WARNING** — `frontend/src/components/PageShell.tsx:43`

3. **Document the `gap-[18px]` exception in UI-SPEC if intentional** — If the 18px header gap is a deliberate layout choice (beyond the documented exceptions), add it to the Spacing Scale section as an "exception" and update PARITY-DEVIATIONS.md. Otherwise, fix to 16px or 24px. — **WARNING** — Spec alignment

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

**Evidence:** All pages ship verbatim copy from vanilla sites with zero rewrites.

- **Page headings:** "Projected points, with the uncertainty shown" (xP), "Fixture ticker" (fixtures), "Price watch" (prices), "League table & season leaders" (league), "The scoreboard" (scoreboard), "Differentials" (differentials) — all copied directly from `web/*.html`.
- **Page titles/meta:** `usePageMeta.ts` exports an 8-route `PAGE_META` table with titles and descriptions matching vanilla exactly (verified in test assertions across all route tests).
- **Error/empty state messages:** Custom, context-appropriate copies:
  - xP table no-match: "No players match" / "Try a different position filter or search term."
  - Differentials no-match: "No players under {cap}% ownership right now" / "Try raising the slider."
  - Prices empty table: "Nothing flagged right now" / "No players are currently trending toward a price change in this direction."
  - Scoreboard empty (pre-season): Verbatim vanilla "No gameweeks scored yet..." + backtest stats.
- **Generic labels audit:** No "Submit", "OK", "Cancel", "Save", "Click Here" found. All CTAs are "Retry" (ErrorState) or self-descriptive (filter/search inputs, sort buttons).
- **Copy ledger entries:** Entries 3, 4, 8 (freshness line, deadline-passed state, Display-token weight for tiles) all implemented verbatim as pre-seeded.

**Score justification:** Copywriting contract fully met. Zero parity defects in copy; all deliberate deviations pre-documented in PARITY-DEVIATIONS.md.

---

### Pillar 2: Visuals (3/4)

**Evidence:** Tables and layouts exhibit strong visual hierarchy; spacing violations undermine consistency.

**Strengths:**
- **Visual hierarchy in tables:** Header rows carry `bg-surface` background + uppercase `font-label` eyebrow text (`tracking-[0.08em]`), clearly distinguishing from body rows.
- **Data visual emphasis:** 
  - xP band cells use a three-part visual (value, track, range) to surface uncertainty — immediately distinct from plain numeric cells.
  - FDR ticker cells render colored difficulty chips (1–5 ramp, easy-blue to hard-red) that map difficulty at a glance.
  - Price-watch trend icons (`TrendingUp`/`TrendingDown`) add color-coded semantic meaning to riser/faller rows.
- **Status flag visuals:** Icon-based status flags (✕ for unavailable, ▲ for doubtful) render inline after player names in text-ink-2 color, distinguishing flagged players without disrupting scan-ability.
- **Consistent component reuse:**
  - `Spinner` used uniformly for loading states across all routes.
  - `ErrorState` component with consistent "We couldn't reach {resource}" copy on all data-fetch failures (except Scoreboard 404, which routes to zero-state).
  - `EmptyState` reused for zero-row conditions.

**Weaknesses:**
- **Spacing inconsistency:** The header's `gap-[18px]` between brand and nav breaks the visual consistency of the 4px-multiple spacing scale. The 18px value sits awkwardly between `gap-4` (16px) and `gap-6` (24px), creating visual micro-misalignment in a high-visibility location.
- **Arbitrary brand size:** The `text-[1.25rem]` (20px) on "FPLML" duplicates the `text-heading` token already defined, creating a maintainability risk (if the heading size ever changes, the brand won't follow).

**Score justification:** Visual hierarchy is well-executed and uses tokens correctly. However, two spacing/typography anomalies (18px gap, arbitrary 20px) suggest incomplete token adoption in the shell layer, which is the foundation all other pages build on. Score 3 reflects "good but with notable gaps."

---

### Pillar 3: Color (4/4)

**Evidence:** Zero hardcoded colors; full token palette with dark-mode symmetry.

**Token usage audit:**
- **No hardcoded colors found:** `grep -rn "#[0-9a-fA-F]{3,8}|rgb(" frontend/src/routes --include="*.tsx"` returns 0 results. All color is applied through Tailwind token classes.
- **Semantic color palette:**
  - `--color-bg` (60%, dominant): page background light/dark
  - `--color-surface`/`--color-surface-2` (30%, secondary): table headers, pill backgrounds (GW banner, theme toggle), tiles
  - `--color-accent` (10%, accent): nav active link, sort direction arrows, theme toggle active button, `TrendingUp` icon, inline links
  - `--color-bad`: unavailable status flag (✕), `TrendingDown` icon
  - `--color-warn`/`--color-warn-bg`: heuristic-mode price note background
  - `--color-band`/`--color-band-pt`: xP interval track/point
- **FDR ramp (fixture difficulty):**
  - 1–5 difficulty range mapped to explicit token pairs per level: `--color-fdr{1..5}-bg` and `--color-fdr{1..5}-ink`.
  - Easy (1) is blue (`#2a78d6` light / `#3987e5` dark), hard (5) is red (`#e34948` light / `#e66767` dark).
  - Neutral (3) is muted gray (`#f0efec` light / `#383835` dark), never bright.
  - `FdrCell.tsx` uses an explicit literal `FDR_CLASSES` map (never string interpolation), guaranteeing Tailwind's build-time scanner can see all five classes.
- **Dark mode implementation:**
  - Class-based `@custom-variant dark` strategy (Tailwind v4), not media-query-only.
  - Inline pre-mount script in `index.html` applies theme class before React mounts, preventing flash.
  - All 20 FDR tokens (both themes) declared in `.dark { }` block with identical accessibility (both themes readable).
  - `useTheme()` hook persists choice to `localStorage`, degrades to session-only on write failure, tracks `matchMedia` live for system preference.

**Accent usage audit:**
- 12 instances of accent-token usage across routes.
- Used appropriately: active nav link, sort arrows, theme toggle active state, rise icon, links.
- Never applied to body text or non-interactive chrome (contract compliance).

**Score justification:** Complete token adoption, zero hardcoded colors, full dark palette with proven symmetry (light/dark FDR values), and semantic color distribution respects 60/30/10. Score 4.

---

### Pillar 4: Typography (3/4)

**Evidence:** Four-token typography system applied consistently; one arbitrary value in shell.

**Token system audit:**
- **Four-size / two-weight contract:** Exactly four font sizes (`--text-label` 14px, `--text-body` 16px, `--text-heading` 20px, `--text-display` 28px) and two weights (400 regular, 700 bold) declared in `index.css` `@theme` block.
- **Font family mapping:**
  - `--font-heading` / `--font-display`: Archivo (serif-style sans), weight 700
  - `--font-body` / `--font-label`: IBM Plex Sans, weight 400
  - `--font-mono`: IBM Plex Mono (numeric modifier), weight 400
- **Token application:** 103 uses of typography token classes across all routes (`font-label`, `text-label`, `font-body`, `text-body`, `font-heading`, `text-heading`, `font-display`, `text-display`).

**Conformance checks:**
- **h1 headings:** Use `font-display text-display font-bold` (28px/700/Archivo). Verified in all route components (XpTable, Fixtures, Prices, League, Scoreboard, Differentials, Methodology h1 via markdown rendering).
- **h2 headings:** Use `font-heading text-heading font-bold` (20px/700/Archivo). Verified in xP table ("Captain picks"), all routes' subsections, Methodology sections via react-markdown.
- **Body prose:** Use `font-body text-body` (16px/400/IBM Plex Sans). Verified in page explanatory text, sub-copy, error/empty state messages.
- **Labels/chrome:** Use `font-label text-label` (14px/400/IBM Plex Sans). Verified in table headers (eyebrow style: uppercase, `tracking-[0.08em]`), table cells, form inputs, chip labels.
- **Numeric/tabular data:** Apply `tabular-nums` modifier alongside the base role class (same size/weight, IBM Plex Mono family). Verified: prices, ownership %, xP, MAE, GW numbers, deadline countdown.
- **Markdown rendering (Methodology):** `react-markdown` components prop maps h1→Display, h2→Heading, p/li→Body, a→Body-with-accent-link, strong→font-bold (no new weights introduced).

**Exceptions/violations found:**
- **`text-[1.25rem]` on PageShell brand:** The "FPLML" text uses an arbitrary 20px value (`text-[1.25rem]`) instead of `text-heading`. This duplicates the declared token and breaks the "only four sizes" contract in the shell layer.
- **All other sizes conform:** No `text-xs`, `text-sm`, `text-base`, `text-xl`, `text-2xl`, `text-3xl`, `text-4xl`, `text-5xl` found. Only the four declared tokens are in use (except the one brand violation).

**Score justification:** Typography token system is well-designed and applied consistently across all routes. The single PageShell brand exception (arbitrary 20px instead of `text-heading`) is isolated but visible in the shell that every page inherits. Score 3 reflects "good, consistent application with one maintenance risk in a high-visibility component."

---

### Pillar 5: Spacing (2/4)

**Evidence:** Spacing scale violations in the shell; documented exceptions correctly applied.

**Spacing scale (UI-SPEC contract):**
- Defined: xs(4px), sm(8px), md(16px), lg(24px), xl(32px), 2xl(48px), 3xl(64px) — all multiples of 4.
- Documented exceptions (beyond scale):
  - 44px touch-target minimum for nav links, position chips, search input, theme toggle buttons, status-flag button, range-slider thumb.
  - 56px `min-width` for FDR ticker cells (rounded from vanilla's 58px).
  - 68rem containment width (carried from Phase 1).
  - 240px `max-width` for StatusFlag tooltip popover.

**Scale violations found:**
1. **`gap-[18px]` in PageShell header** (`frontend/src/components/PageShell.tsx:42`):
   - Separates brand from nav + gap between header sections.
   - 18px is NOT a multiple of 4. Should be `gap-4` (16px) or `gap-6` (24px).
   - High-visibility component; affects entire site chrome.
   - **BLOCKER:** Violates fundamental spacing contract.

**Valid arbitrary values (documented exceptions):**
- `min-h-[44px]`: Touch target for buttons (nav links, position chips, theme toggle, status flag) — documented.
- `min-w-[44px]`: Touch target width for icon buttons (theme toggle) — documented.
- `min-w-[56px]`: FDR ticker cell fixed width (UI-SPEC exception) — documented.
- `max-w-[240px]`: StatusFlag tooltip max-width — documented.
- `max-w-[68rem]`: Containment (Phase 1 carried) — documented.
- `min-h-[16rem]`: Empty/error/loading state min-height for centering — reasonable vertical space, no scale violation (16rem = 256px, not a gap/padding value).

**Spacing distribution audit:**
- Padding/margin classes: 91 instances of `p-` and `px-`/`py-` (mostly `px-3 py-2` on table cells).
- Gap classes: Mostly `gap-2` and `gap-3`, consistent with scale.
- One exception: `gap-[18px]`, the blocker violation.

**Score justification:** Spacing scale is well-understood and applied consistently throughout all routes (7 pages + shell). One high-visibility violation (18px gap in header) breaks the contract and scores the entire pillar down. If the 18px is intentional (e.g., a carefully-chosen layout constant), it should be documented as an exception in the UI-SPEC and PARITY-DEVIATIONS.md. Score 2 reflects "partial conformance; blocking defect requires fix."

---

### Pillar 6: Experience Design (4/4)

**Evidence:** Complete state coverage across 7 pages + shell chrome + interactive controls.

**State handling audit (per UI-SPEC E1–E10 considerations):**

1. **xP table (E1, flagship):**
   - Loading: `<Spinner/>` while `isPending`.
   - Error: `<ErrorState resource="the xP table" onRetry={...} />` on `isError`.
   - Empty: Generic `<EmptyState/>` on zero rows; page-specific "No players match" heading when filters yield zero.
   - Populated: Fully sortable (7 columns), filterable (5 position chips + search), band cells with tooltips.
   - Partial: Per-row optional fields (`ownership`, `p10`/`p90`, `news`, `xp_capt`) handled with fallbacks (`–` or field omit).
   - Status flags: Accessible tooltip on flagged players (hover/focus/click-toggle, Escape/click-outside dismiss).

2. **Fixtures table (E2):**
   - Loading/error/empty: Spinner, ErrorState, EmptyState (same as xP).
   - Populated: Data-derived gameweek column count (never hard-coded to 6).
   - Partial: `xg_next`/`xgc_next` null → `–`; `ease` has no fallback.
   - FDR cells: Explicit 1-5 token map, out-of-range clamps to neutral (difficulty 3).
   - No interactive headers (correctly not sortable per vanilla).

3. **Prices table (E3):**
   - Loading/error/empty: Spinner, ErrorState, EmptyState.
   - Populated: Two tables (risers/fallers) with mode-dependent progress labels and three verbatim mode-note variants.
   - Progress math: `raw = prob ?? progress ?? 0`, `pct = Math.round(100 * Math.abs(raw))`, `bar = Math.min(pct, 100)` (bar clamped, label not) — verbatim.
   - Trend icons: `TrendingUp` (accent) for risers, `TrendingDown` (bad) for fallers, never crossing tables.
   - No interactive headers (correctly not sortable).

4. **League table (E4):**
   - Standings: Array-position rank (index + 1), GD sign rule (+/– prefix when `gd > 0`, else bare).
   - Leader boards: Five fixed boards (points/goals/assists/clean_sheets/cards), 8-entry cap, "Nothing yet this season" fallback for empty/missing.
   - Loading/error/empty: Spinner, ErrorState on standings fetch failure; leader boards fail together (single query, both required).
   - No interactive headers (not sortable).

5. **Scoreboard (E5, special error handling):**
   - **404-vs-error distinction:** Dedicated `fetchScoreboard()` function returns `null` on 404 (→ zero-state with backtest stats), throws for all other non-ok status (→ ErrorState with Retry). This is the phase's deliberate improvement over vanilla's uniform `try{}catch{}` swallow.
   - Populated: Four tiles (Gameweeks scored, MAE, Rank correlation, Captain average) + history table in export order.
   - Partial: `mae_fpl`/`spearman_fpl` null → `–` per-cell/per-tile.

6. **Differentials (E6):**
   - Ownership slider: `min=1 max=25 step=1 default=10`, live label `{cap}%`, 44px touch target.
   - Filter: `(ownership ?? 100) <= cap && status === "a"`, 30-row slice.
   - Empty: Page-specific "No players under {cap}% ownership right now" when cap matches zero; shared EmptyState when source is zero.
   - maxHi floor: `Math.max(1, ...)` — structurally distinct from xP table's un-floored maxHi (grep-verified: distinct source).
   - Band cell: Identical to xP table's, but maxHi floor changes scaling denominator.

7. **Methodology (E7, static content):**
   - No loading/error/empty states: Markdown imported at build time via Vite `?raw` suffix.
   - Rendered: Five h2 sections (Prediction/Uncertainty/Selection/"The receipts"/Honesty policy), four receipt figures with captions, three-item honesty bullet list.
   - No raw-HTML sink: `react-markdown` default component (no `dangerouslySetInnerHTML`, no `rehype-raw` plugin); script-shaped markdown text renders as escaped visible text.

8. **GW Banner (E8, data-display chrome):**
   - Loading: `loading…` in muted pill.
   - Error: Quiet `deadline TBC` fallback (not ErrorState), no Retry.
   - Populated: Two-line pill (Line 1: "GW{gw} deadline: {abs} · {rel}" or "GW{gw} deadline passed", Line 2: "generated {freshness}").
   - Live countdown: 60s cadence outside final hour, 1s inside final hour (with per-second precision via `fmtRel` discriminated `{ passed: true } | { passed: false; text }`).
   - Overflow/long-text: Fixed short strings, never clipped.

9. **Dark mode toggle (E9, interactive control):**
   - Resolves synchronously at mount from `localStorage` + `matchMedia`.
   - Degrades to session-only on storage-write failure (no user-facing error).
   - Exactly one button carries `aria-pressed="true"` + accent tokens at all times.
   - Tracks OS-level theme changes live while set to `system`.

10. **Status-flag tooltip (E10, interactive control):**
    - Opens on hover/focus/click-toggle, closes on Escape/click-outside or click-toggle-again.
    - Rendered only when `status !== "a"` (available players have no flag).
    - Glyph/color: `✕` bad for `status in ["i","s","u","n"]`, `▲` warn for other non-available.
    - Content: `r.news ?? label` (fallback to label word), max-width 240px, wraps.

**Accessibility audit:**
- 28 instances of `aria-*` attributes found (labels, pressed states, descriptions, hidden).
- All form inputs labeled (search, slider).
- All buttons have `aria-label` or visible text + `aria-pressed` for toggles.
- All interactive elements have visible focus states via Tailwind's `:focus-visible` (inherited).
- Status-flag tooltip has `aria-describedby` pointing to a `role="tooltip"` span.

**Score justification:** All six state categories (loading, error, empty, populated, partial, overflow) are handled across 7 pages. Accessibility is robust (aria labels, tooltips, disabled states, dark mode support). Scoreboard's 404-vs-error distinction is a deliberate improvement over vanilla. No state-handling defects found. Score 4.

---

## Files Audited

**Routes (fully implemented, tested, green):**
- `frontend/src/routes/XpTable.tsx` (1-table layout, sortable, filterable, band cells, status flags, captain sub-table)
- `frontend/src/routes/Fixtures.tsx` (FDR ticker, data-derived gameweek columns, legend)
- `frontend/src/routes/Prices.tsx` (risers/fallers tables, mode-dependent notes, trend icons)
- `frontend/src/routes/League.tsx` (standings + five leader boards, rank numbering, GD sign rule)
- `frontend/src/routes/Scoreboard.tsx` (404-vs-error fetch, backtest zero-state, populated tiles + history)
- `frontend/src/routes/Differentials.tsx` (ownership slider, ownership-cap filter, maxHi floor, band scaling)
- `frontend/src/routes/Methodology.tsx` (bundled markdown, react-markdown rendering, no raw-HTML sink)

**Components (shared, reusable):**
- `frontend/src/components/PageShell.tsx` (app chrome, header nav, GW banner, theme toggle, containment)
- `frontend/src/components/GwBanner.tsx` (four-state countdown chip, live 60s/1s interval switching)
- `frontend/src/components/ThemeToggle.tsx` (three-button Light/Dark/System, localStorage + matchMedia)
- `frontend/src/components/BandCell.tsx` (p10–p90 interval band, CSS calc() width, tooltip)
- `frontend/src/components/FdrCell.tsx` (fixture-difficulty cells, 1-5 literal token map, blank-gameweek dash)
- `frontend/src/components/Spinner.tsx` (loading state)
- `frontend/src/components/ErrorState.tsx` (data-fetch error with Retry)
- `frontend/src/components/EmptyState.tsx` (zero-row fallback)

**Libraries (utilities, hooks):**
- `frontend/src/lib/api.ts` (13-interface web/data/*.json TypeScript contract)
- `frontend/src/lib/usePageMeta.ts` (per-route document title/meta description hook, 8-route table)
- `frontend/src/lib/theme.ts` (resolveTheme, useTheme, localStorage+matchMedia logic)
- `frontend/src/lib/deadline.ts` (fmtAbs, fmtRel, fmtFreshness formatters, graduated countdown precision)
- `frontend/src/lib/sortable.ts` (sort comparator, useSortable hook, null-first-then-last handling, direction glyph)
- `frontend/src/lib/bandCell.ts` (band geometry, maxHi calculation, tooltip copy)
- `frontend/src/lib/statusFlag.tsx` (accessible status-flag tooltip, click-toggle, Escape/click-outside dismiss)
- `frontend/src/lib/format.ts` (fixed1, fixed2, orDash, localeInt primitives)

**Styles & assets:**
- `frontend/src/index.css` (@theme tokens, dark-mode `.dark` block, @fontsource imports, single mechanism)
- `frontend/src/content/methodology.md` (bundled markdown prose, verbatim from vanilla)
- `frontend/index.html` (pre-mount theme resolution script, @fontsource preloads)

**Test fixtures:**
- `frontend/src/test/fixtures/xp_table.json`, `captains.json`, `fixtures.json`, `watchlist_*.json`, `standings.json`, `leaders.json`, `scoreboard.json`, `meta.json`

---

## Summary

Phase 2 has shipped **seven fully-ported pages + shell chrome** with strong copywriting and experience-design parity to vanilla. The color and typography systems are well-designed and token-based (no hardcoded values). Accessibility is thorough (aria labels, tooltips, keyboard navigation, dark mode). 

**Two defects** need attention:
1. **BLOCKER:** `gap-[18px]` spacing scale violation in PageShell header breaks the 4px-multiple contract.
2. **WARNING:** `text-[1.25rem]` arbitrary typography on brand duplicates the `text-heading` token.

Both are isolated to the shell and do not affect the seven route implementations. With these fixes, Phase 2 would score **22/24** (91%).

**Recommendation:** Fix the two shell defects before proceeding to Phase 3. The route implementations are production-ready and well-tested (169/169 Vitest tests passing). The color and experience-design work sets a strong foundation for Phase 3's pitch UI.

