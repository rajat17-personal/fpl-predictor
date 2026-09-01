---
status: diagnosed
trigger: "UAT gap G-01-3 (Phase 1): Nav link text adapts appropriately across screen sizes (remains proportionate/legible on large screens). User reported: 'The nav links text does not adapt based on screen size especially when screen size is bigger. rest work as expected'"
created: 2026-09-01T00:00:00Z
updated: 2026-09-01T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — see Resolution
test: n/a (diagnose-only session)
expecting: n/a
next_action: return ROOT CAUSE FOUND to caller (find_root_cause_only mode, no implementation edits)

## Symptoms

expected: Nav links look proportionate/legible relative to viewport at large desktop widths, same visual quality as mobile.
actual: On a ~1720px-wide desktop viewport, nav text renders small and left-clustered, stranded against a large empty right-hand gutter. Mobile (375-430px) wraps correctly onto two rows and looks fine.
errors: none (visual/layout issue, not a runtime error)
reproduction: Load app shell (PageShell) at a wide desktop viewport (~1720px); observe header brand+nav hugging the left edge with no width containment, while `<main>`/footer content is centered and capped at 68rem.
started: Phase 1 app-shell build (PageShell.tsx initial implementation)

## Eliminated

- hypothesis: `--text-label` token (14px, index.css:65-66) is the bug — nav font-size should scale up via responsive Tailwind breakpoints (md:/lg:/xl: text utilities).
  evidence: UI-SPEC Typography table (01-UI-SPEC.md, "Typography" section) defines Label as a single fixed 14px value with no breakpoint column. Vanilla parity source (web/assets/style.css:74, `nav.site a { font-size: 0.88rem }`) also uses one flat font-size at every viewport width — no media query changes it. Since the parity source itself never scales nav font-size and still looks correct at wide viewports (because it's contained inside `.wrap`), font-size is not the differentiator.
  timestamp: 2026-09-01T00:00:00Z

## Evidence

- timestamp: 2026-09-01T00:00:00Z
  checked: frontend/src/components/PageShell.tsx (full file)
  found: "<header>" (line 27) has classes `flex flex-wrap items-center gap-[18px] border-b border-line px-4 py-4` — no `max-w-[68rem]`/`mx-auto` constraint. "<main>" (line 53) has `mx-auto w-full max-w-[68rem]`. Footer's inner `<p>` (line 58) has `mx-auto max-w-[68rem]`. Header is the only chrome section missing the containment.
  implication: On viewports wider than 1088px (68rem), header content (brand + nav) is left-aligned inside a full-bleed row instead of being centered/capped like the rest of the shell — this is a containment omission, not a typography problem.

- timestamp: 2026-09-01T00:00:00Z
  checked: frontend/src/index.css (@theme block)
  found: `--text-label: 14px` / `--text-label--line-height: 1.4` (lines 65-66) — single fixed value, no responsive/clamp variant defined for any token in the type scale (Label/Body/Heading/Display).
  implication: The type-scale contract is intentionally fixed-px, not fluid — confirms font-size scaling is out of contract, not an oversight.

- timestamp: 2026-09-01T00:00:00Z
  checked: .planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md ("Layout frame" table, "Typography" table, Scope Note)
  found: "Content max-width | 68rem (1088px), centered | Carried from vanilla `.wrap { max-width: 68rem }` — parity" (line 66). "Header | Non-sticky, static flex row: brand + nav + (meta banner slot, empty this phase) | Carried from vanilla `header.site`" (line 68) — Header's own stated source is vanilla `header.site`. "Page horizontal padding ... per-page responsive scale-up is Phase 2 concern" (line 67) — only padding scale-up is deferred, not the base 68rem containment, which is a Phase-1-locked value per the Scope Note.
  implication: UI-SPEC requires header to carry over vanilla `header.site` behavior, which includes its containment (see next entry) — the 68rem cap is a Phase 1 deliverable already, not deferred.

- timestamp: 2026-09-01T00:00:00Z
  checked: web/index.html (lines 13-18) + web/assets/style.css (lines 59, 61-64, 72-78)
  found: Vanilla markup nests `<header class="site">` directly inside `<div class="wrap">` (`.wrap { max-width: 68rem; margin: 0 auto; ... }`). `nav.site` and its `a` children (font-size 0.88rem) inherit that containment — they are never wider than 1088px and are always centered within the viewport, regardless of screen width.
  implication: In vanilla, "proportionate at large screens" is achieved entirely through the 68rem containment (a narrow, centered column that reads correctly at any width) — not through responsive font-size. The React header dropped this containment, which is the actual regression relative to the stated parity source.

## Resolution

root_cause: |
  frontend/src/components/PageShell.tsx:27 — the `<header>` element is missing the `mx-auto max-w-[68rem]` width containment that the same component already applies to `<main>` (line 53) and the footer's `<p>` (line 58), and that the UI-SPEC's own cited parity source (`web/index.html:14-17` + `web/assets/style.css:59,62-64`, where `header.site` is nested inside `.wrap { max-width: 68rem; margin: 0 auto }`) applies to the header too. Because the header is the only chrome section rendered full-bleed, on viewports wider than 1088px the brand+nav content (fixed `text-label` = 14px, index.css:65-66) sits left-aligned against a large unconstrained empty gutter instead of being centered in a proportionate column — reading as "small, left-clustered" text. Mobile widths (375-430px) look correct only because there the unconstrained width happens to roughly equal the would-be-constrained width, masking the missing containment. This is a layout-containment omission, not a typography/token defect — vanilla's own nav font-size is a flat, non-responsive `0.88rem` at every breakpoint (web/assets/style.css:74) and still reads correctly at 1720px, because it's contained.
fix: NOT APPLIED (find_root_cause_only mode — no implementation files modified per task instructions)
verification: n/a — diagnose-only session
files_changed: []
