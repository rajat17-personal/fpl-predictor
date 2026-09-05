---
phase: 02-data-layer-non-pitch-pages
plan: 07
subsystem: ui
tags: [css, oklch, design-tokens, dark-mode, vitest, ci-gate]

# Dependency graph
requires:
  - phase: 02-data-layer-non-pitch-pages
    provides: The dark-mode token palette shipped by plan 02-03 (the defect this plan fixes)
provides:
  - A dependency-free OKLCH token-budget gate (frontend/scripts/check-tokens.mjs) wired into
    the frontend test command
  - Rebalanced dark neutral tokens (bg/surface/surface-2/line) in both React and vanilla,
    kept in lockstep
  - Restored color-scheme (light/dark) and body paint parity with vanilla
  - Documented chroma budget rule in 02-UI-SPEC.md and lockstep decision in PARITY-DEVIATIONS.md
affects: [phase-07-cutover, ui-review, future-token-edits]

actuals:
  tokens: 4717
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Dependency-free Node gate script (node:fs/node:url only) for CSS token invariants that
       cannot be asserted from Vitest without a real Tailwind pipeline"
    - "Lockstep token edits: shared token values changed identically in both frontend/src/index.css
       and web/assets/style.css in a single commit, verified programmatically rather than by
       manual diff"

key-files:
  created:
    - frontend/scripts/check-tokens.mjs
  modified:
    - frontend/package.json
    - frontend/src/index.css
    - web/assets/style.css
    - .planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md
    - .planning/phases/02-data-layer-non-pitch-pages/02-UI-SPEC.md
    - .planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md

key-decisions:
  - "Lockstep over divergence for the palette fix: changed the four dark neutral hexes in both
     frontend/src/index.css and web/assets/style.css in one commit rather than diverging the
     React palette, per D-01/D-04 — the values were byte-identical before the fix, the change
     is token-value-only (reverts in one commit), and vanilla stays authoritative until CUT-01."
  - "A plain Node script (frontend/scripts/check-tokens.mjs) rather than a Vitest test for the
     token-budget gate — Vitest stubs CSS imports to empty strings by default, and reading the
     file with node:fs from inside src/ is blocked by tsconfig.app.json's vite/client-only types."
  - "0.0010 OKLCH chroma allowance on the budget, and a separate 0.6 lightness-lock tolerance,
     pinned to the pre-fix measured lightness values — stops a future 'just make it darker' edit
     from satisfying the chroma budget by moving the contrast ladder instead of removing chroma."

requirements-completed: [UIX-02]

coverage:
  - id: D1
    description: "Dark neutrals (bg/surface/surface-2/line) rebalanced so hue locks to the accent, chroma is cut to the light-theme budget, and lightness is unchanged"
    requirement: UIX-02
    verification:
      - kind: other
        ref: "npm --prefix frontend run check:tokens"
        status: pass
    human_judgment: true
    rationale: "The gate proves the OKLCH numbers are in budget, but whether the frame genuinely 'reads as dark' rather than green is a perceptual judgment G-02-1 originated from — the plan's own <verify> defers this to a <human-check> at end-of-phase per workflow.human_verify_mode=end-of-phase."
  - id: D2
    description: "color-scheme restored (light on :root, dark on .dark) and body painted from --color-bg/--color-ink, matching vanilla's parity behavior"
    requirement: UIX-02
    verification:
      - kind: other
        ref: "npm --prefix frontend run check:tokens (structure assertions)"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run test (171 Vitest tests, PageShell.test.tsx included)"
        status: pass
    human_judgment: false
  - id: D3
    description: "check-tokens.mjs gate wired into the standard frontend test command, dependency-free, and confirmed RED against the pre-fix palette / GREEN against the post-fix palette"
    requirement: UIX-02
    verification:
      - kind: other
        ref: "git log ab48ff1 (RED against old palette, named surface-2) and 746029c (GREEN + npm test wired)"
        status: pass
    human_judgment: false
  - id: D4
    description: "01-UI-SPEC.md, 02-UI-SPEC.md, and PARITY-DEVIATIONS.md updated to describe the palette that actually ships, with G-02-1 as the origin and the lockstep decision recorded"
    requirement: UIX-02
    verification:
      - kind: other
        ref: "grep checks for updated hexes, G-02-1 references, lockstep section, 8-row deviations table"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-02
status: complete
---

# Phase 02 Plan 07: Dark theme green-tint fix (UAT gap G-02-1) Summary

**Rebalanced the four dark-mode neutral tokens with a new dependency-free OKLCH budget gate (frontend/scripts/check-tokens.mjs) that fails the standard test command if the green tint ever comes back.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-02T01:18:43Z
- **Tasks:** 3
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- Built `frontend/scripts/check-tokens.mjs`, a zero-dependency Node script that converts sRGB
  hexes to OKLCH and asserts a chroma budget, hue lock, and lightness lock for the four dark
  neutral roles (bg, surface, surface-2, line), plus color-scheme/body structure checks and a
  lockstep check against `web/assets/style.css`. Confirmed RED against the shipped palette,
  naming all four over-budget roles with chroma numbers matching the diagnosis doc exactly.
- Rebalanced the dark neutrals in lockstep: bg `#111815`→`#141715`, surface `#18211c`→`#1b201c`,
  surface-2 `#1f2a24`→`#222924`, line `#2c3831`→`#2e3731`, in both `frontend/src/index.css` and
  `web/assets/style.css` in the same commit. Hue now locks within 0.2–3.2 degrees of the accent
  (was 4.9–12.7), chroma sits at or under budget on all four roles, and lightness held within
  0.07 of the pre-fix values.
- Restored `color-scheme: light` on `:root`, `color-scheme: dark` on `.dark`, and a `body` rule
  painting `background`/`color` from the bg/ink tokens — the two parity regressions the diagnosis
  identified as amplifiers (light UA chrome, unpainted overscroll canvas).
- Wired `check:tokens` into the frontend's standard `test` script so a future edit that
  reintroduces the defect fails `npm run test`, not just a separate lint step.
- Updated `01-UI-SPEC.md`'s Color role table and carried-forward token table, added a
  Dark-neutral chroma budget subsection to `02-UI-SPEC.md` naming G-02-1 as the origin, and
  recorded the lockstep decision (with its three reasons) in `PARITY-DEVIATIONS.md` without
  adding a row to the numbered deviations table — a lockstep change produces no React/vanilla
  delta for Phase 7 to find.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a dependency-free OKLCH token-budget gate that fails against today's palette** - `ab48ff1` (test)
2. **Task 2: Rebalance the dark neutrals in lockstep and restore color-scheme plus body paint** - `746029c` (fix)
3. **Task 3: Record the chroma budget in the UI-SPECs and the lockstep decision in the ledger** - `5bf56c9` (docs)

## Files Created/Modified

- `frontend/scripts/check-tokens.mjs` - New OKLCH token-budget gate (chroma/hue/lightness/structure/lockstep assertions)
- `frontend/package.json` - Added `check:tokens` script; `test` now runs the gate before `vitest run`
- `frontend/src/index.css` - Rebalanced `.dark` neutral hexes; added `:root`/`.dark` `color-scheme`; added `body` background/color rule
- `web/assets/style.css` - Rebalanced the same four dark neutral hexes inside the `prefers-color-scheme: dark` media block (lockstep)
- `.planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md` - Updated Color role table and carried-forward token table to the new dark hexes
- `.planning/phases/02-data-layer-non-pitch-pages/02-UI-SPEC.md` - Added Dark-neutral chroma budget subsection under Color
- `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` - Added "Palette changes made in lockstep" section

## Decisions Made

- **Lockstep over divergence** for the palette values (see key-decisions in frontmatter and the
  Task 2 rationale in PARITY-DEVIATIONS.md) — no ledger row added since it produces no
  React/vanilla delta.
- **Plain Node script over Vitest test** for the gate, per the plan's closed-off-alternatives
  rationale (Vitest's default CSS stubbing, and tsconfig.app.json's lack of node types for a
  src-based node:fs test).
- **0.0010 chroma allowance / 0.6 lightness tolerance**, both pinned with in-code comments
  explaining the quantization-floor and contrast-ladder rationale respectively, so a future
  editor does not need to re-derive them.

## Deviations from Plan

None - plan executed exactly as written. All four gap-coverage-audit items (rebalance dark
neutrals, restore color-scheme/body paint, document the chroma budget, decide and record
lockstep-vs-diverge) were delivered by the tasks the plan assigned them to.

## Issues Encountered

None. The gate's measured chroma/hue numbers matched the diagnosis doc's figures on the first
run (bg 0.0121, surface 0.0161, surface-2 0.0189, line 0.0202 pre-fix; 0.0061/0.0106/0.0135/0.0161
post-fix), confirming the OKLCH conversion was implemented correctly without iteration.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The dark-neutral chroma budget is now enforced automatically (`npm run test` runs
  `check:tokens` first) — no manual re-verification needed on future palette edits.
- `01-UI-SPEC.md`/`02-UI-SPEC.md`/`PARITY-DEVIATIONS.md` describe the palette that actually
  ships, so Phase 7 (CUT-01)'s side-by-side comparison has an accurate reference.
- Human visual confirmation of the fix on `/fixtures` in dark mode (the plan's `<human-check>`)
  is deferred to the end-of-phase UAT batch per `workflow.human_verify_mode: end-of-phase` — not
  yet performed by this executor run.
- `--color-ink`/`--color-ink-2` and `--color-fdr3-bg`, both also measured as green-family by the
  diagnosis, remain unchanged — explicitly out of scope per this plan's gap-coverage audit (text
  glyphs cover too little viewport area to wash, and the FDR ramp is a validated diverging scale
  whose contrast issue is resolved by the surface-2 fix, not by retinting the chip itself).

---
*Phase: 02-data-layer-non-pitch-pages*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: frontend/scripts/check-tokens.mjs
- FOUND: .planning/phases/02-data-layer-non-pitch-pages/02-07-SUMMARY.md
- FOUND: commit ab48ff1 (Task 1)
- FOUND: commit 746029c (Task 2)
- FOUND: commit 5bf56c9 (Task 3)
- Re-ran `npm --prefix frontend run test` (gate + 171 Vitest tests) and `npm --prefix frontend run build`: both green.
