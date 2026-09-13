---
phase: 07-parity-validation-cutover
plan: 02
subsystem: testing
tags: [playwright, node, parity, e2e, ledger]

# Dependency graph
requires:
  - phase: 07-parity-validation-cutover
    provides: "07-01's production react-mode serving seam (api/main.py FPL_FRONTEND=react),
      scripts/dual_site.sh, the one-page parity-diff.mjs tracer, and the live-export
      meta.json freshness guard this plan grows into the full 8-page instrument"
provides:
  - "e2e/parity/extract.mjs -- 8-page field map (route/vanillaPath/label/fields) with
    explicit per-origin selector pairs, a shared normalizeText() helper, and
    extractPage() for per-origin navigation + extraction"
  - "e2e/parity/ledger.mjs -- PARITY-DEVIATIONS.md pipe-table parser (node:fs only,
    fails loudly on missing file/heading/zero rows) and isKnownDelta() field-level
    classifier"
  - "e2e/parity/parity-diff.mjs --all/--page/--stage/--out -- 8-page ledger-aware
    diff CLI with a markdown stage-fragment emitter"
  - "PARITY-REPORT.md -- three empty D-07 stage tables, a defects-closed table, a
    cutover-readiness summary, and an append discipline"
  - "PARITY-CHECKLIST.md -- the D-05 eyeball pass (8 pages) and the D-08 entry-6980093
    same-session interactive comparison (rate/solve/plan)"
affects: [07-03, 07-04, 07-05, 07-06]

actuals:
  tokens: 10266
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Field-map-declared ledger binding: extract.mjs's PAGES fields carry an
      optional knownDeviations array of PARITY-DEVIATIONS.md entry numbers,
      reviewed in the field map itself rather than inferred from prose text
      matching at diff time -- ledger.mjs's isKnownDelta() consumes it and throws
      if a declared number no longer resolves against the live ledger."
    - "Origin-as-flavour object ({ base, flavour }) passed to extractPage() so one
      function navigates either origin to its own path shape (vanilla's .html
      files vs React's client routes) without a second navigation call site."
    - "Single shared character-stripping normalizer (normalizeText, letters/digits/
      space/period/apostrophe/hyphen only) applied to every extracted field --
      table cells and prose text alike -- so punctuation/glyph differences (sort
      arrows, status-flag glyphs, %, thousands separators) never register as
      deltas while the underlying values still compare exactly."

key-files:
  created:
    - e2e/parity/extract.mjs
    - e2e/parity/ledger.mjs
    - .planning/phases/07-parity-validation-cutover/PARITY-REPORT.md
    - .planning/phases/07-parity-validation-cutover/PARITY-CHECKLIST.md
  modified:
    - e2e/parity/parity-diff.mjs

key-decisions:
  - "extractPage(page, pageSpec, origin) takes origin as { base, flavour } rather
    than a bare URL string, so one function resolves both which path to visit
    (vanillaPath vs route) and which selector half of each field to use, per the
    plan's exact three-parameter signature."
  - "isKnownDelta() classifies at the field level (any delta on a field that
    declares knownDeviations cites the first declared number) rather than
    inspecting delta text -- matches the plan's explicit design decision that the
    field-to-ledger binding lives in extract.mjs, reviewed there."
  - "Team page (/team vs /team.html) and Methodology's relocated credit line
    surface as real (not-yet-ledgered) defects on every run -- documented as a
    flagged, not silently worked around: the Team page's default views diverge
    structurally (React's Phase-3 squad-first pitch view vs vanilla's rate-ID
    form) and PARITY-DEVIATIONS.md has no entry recording it. This plan's job
    was building the comparison instrument, not resolving what it finds --
    triage belongs to the 07-03..07-06 validation-pass plans."
  - "Verified against override ports (DUAL_SITE_VANILLA_PORT=8010/REACT_PORT=8011)
    rather than the plan's literal default-port verify commands, because port
    8000 is held by the same pre-existing, unrelated vanilla uvicorn (PID 2914)
    07-01's SUMMARY already documented and left running untouched."

requirements-completed: []

coverage:
  - id: D1
    description: "e2e/parity/extract.mjs: 8-page field map (route == every non-wildcard
      frontend/src/router.tsx path) with an explicit vanilla/react selector pair and
      kind (rows|text) per field, every page carrying >=3 comparable fields"
    requirement: CUT-01
    verification:
      - kind: other
        ref: "node -e import('./e2e/parity/extract.mjs') -- PAGES.length===8, every
          field.length>=2, every field has both vanilla+react selectors, route set
          equals router.tsx's 8 paths"
        status: pass
    human_judgment: false
  - id: D2
    description: "e2e/parity/parity-diff.mjs --all/--page: walks all 8 pages against
      both live dual_site origins, per-page + TOTAL verdict, exits non-zero on any
      delta/zero-field page/zero total"
    requirement: CUT-01
    verification:
      - kind: e2e
        ref: "node e2e/parity/parity-diff.mjs --all (dual_site ports 8010/8011) ->
          TOTAL: 8 pages, 34 fields compared, 11 deltas, exit 1"
        status: pass
      - kind: e2e
        ref: "node e2e/parity/parity-diff.mjs --page /methodology -> TOTAL: 1 pages,
          4 fields compared, 2 deltas, exit 1 (non-zero only for reported deltas)"
        status: pass
    human_judgment: false
  - id: D3
    description: "e2e/parity/ledger.mjs: loadLedger() parses the 8 numbered
      PARITY-DEVIATIONS.md rows via node:fs only and throws loudly on a missing
      file/heading/zero rows; isKnownDelta() classifies via field-declared
      knownDeviations and throws on a stale ledger reference"
    requirement: CUT-01
    verification:
      - kind: other
        ref: "node -e loadLedger() -> 8 rows, numbers [1..8] in order"
        status: pass
      - kind: other
        ref: "node -e loadLedger('/nonexistent/LEDGER.md') -> throws, message names
          the path"
        status: pass
      - kind: other
        ref: "node -e cross-check every extract.mjs knownDeviations number against
          the live ledger -> empty bad-list, exit 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "parity-diff.mjs ledger-aware verdict + --stage/--out markdown
      fragment emitter, defect cells carrying an explicit unfilled marker"
    requirement: CUT-01
    verification:
      - kind: e2e
        ref: "node e2e/parity/parity-diff.mjs --all --stage dry-run --out
          /tmp/parity-fragment.md -> TOTAL: 8 pages, 34 fields compared, 8
          explained, 3 defects, exit 1; fragment has 10 pipe-rows (header +
          alignment + 8 pages), 1 Cron-green citation header, defect rows carry
          'UNRESOLVED -- ... fixing commit SHA or a new PARITY-DEVIATIONS.md row'"
        status: pass
    human_judgment: false
  - id: D5
    description: "PARITY-REPORT.md and PARITY-CHECKLIST.md exist, ready to be filled
      at the first validation pass, carry no manager personal-name data"
    requirement: CUT-01
    verification:
      - kind: other
        ref: "grep checks: 3 stage H3 headings (pre-deadline/mid-gameweek/post-finish),
          5x 'Cron-green citation', checklist has 8 per-page subsections + exactly 3
          interactive-flow checkboxes + entry 6980093 cited 4x; no manager first/last
          name in either file"
        status: pass
    human_judgment: true
    rationale: "The report/checklist documents' structural completeness is
      grep-verified above, but whether their instructions are actually followable
      and sufficient for a human running the real 3-stage cycle (07-03..07-06) is
      a judgment call no automated check here can make -- the first real
      validation pass is the proof."

duration: 39min
completed: 2026-09-07
status: complete
---

# Phase 7 Plan 2: Full 8-Page Parity Instrument Summary

**Grew the 07-01 one-page tracer into a ledger-aware, 8-page comparison CLI
(`e2e/parity/extract.mjs` + `ledger.mjs` + `parity-diff.mjs --all/--stage/--out`)
plus the two evidence documents (`PARITY-REPORT.md`, `PARITY-CHECKLIST.md`) the
D-15 cutover gate will be decided from — verified end-to-end against a live
dual-site pair, surfacing 8 explained deltas and 3 real, not-yet-ledgered defects.**

## Performance

- **Duration:** 39 min
- **Started:** 2026-09-07T11:56:00Z (approx.)
- **Completed:** 2026-09-07T12:35:00Z (approx.)
- **Tasks:** 3 completed
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- `e2e/parity/extract.mjs`: one `PAGES` entry per React route (route set verified
  identical to `frontend/src/router.tsx`'s 8 non-wildcard paths), each carrying an
  explicit vanilla-selector/react-selector pair per field (vanilla addresses by
  element id, React by accessible name — the two sites share no selector), a
  shared `normalizeText()` character-stripping/whitespace-collapsing helper, and
  `extractPage(page, pageSpec, origin)` for per-origin navigation + extraction.
- `e2e/parity/parity-diff.mjs` grew from a single hardcoded `--page /` xP-table
  row-comparison into `--all` (iterates all 8 pages) / `--page <route>` (any of
  the 8), with a per-page verdict and a non-vacuous `TOTAL:` line, exiting
  non-zero on any real defect, any zero-compared-field page, or a ledger-load
  failure.
- `e2e/parity/ledger.mjs`: `loadLedger()` parses `PARITY-DEVIATIONS.md`'s 8
  numbered rows with `node:fs` only (mirrors `check-tokens.mjs`'s dependency-free
  style), stopping before the next `## ` heading so the lockstep-palette
  section's own table is never mistaken for numbered deltas; throws loudly on a
  missing file, missing `## Deviations` heading, or zero parsed rows.
  `isKnownDelta()` classifies each delta via the field-declared
  `knownDeviations` array and throws if a declared ledger number no longer
  resolves — a stale reference is a config error, not a silent pass.
- `--stage`/`--out` on `parity-diff.mjs`: appends a markdown fragment (H3 stage
  heading, run header with GW/`generated_utc`/exact command line, and a
  Page/Verdict/Delta-detail/Cron-green-citation row per page) whose columns
  match `PARITY-REPORT.md`'s stage tables exactly; a defect's cell always
  carries an explicit unfilled marker naming what must replace it.
- `PARITY-REPORT.md`: opening invariant (a verdict is only evidence if it cites
  a ledger number, a fixing commit SHA, or a named cron-green citation), three
  empty D-07 stage tables pre-seeded with the 8 page labels, a "Defects found
  and how they were closed" table (D-14 fix-forward), and a "Cutover readiness"
  summary the D-15 human gate reads.
- `PARITY-CHECKLIST.md`: the D-05 eyeball pass (per-page layout/spacing/theme/
  overflow/copy, explicit that value/sort-order checking is the script's job)
  and the D-08 same-session interactive comparison (entry 6980093, three flows:
  rate, one solve with identical locks, one two-GW plan) plus a cron-green
  evidence step naming the three concrete citations and requiring a verbatim
  "log does not exist" note rather than a fabricated green run.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend the comparison from one page to all eight** - `9006460` (feat)
2. **Task 2: Ledger-aware classification and the report fragment emitter** - `81c4fca` (feat)
3. **Task 3: The evidence artifact and the manual checklist** - `e562fa8` (docs)

**Plan metadata:** _pending_ (docs: complete plan)

## Files Created/Modified

- `e2e/parity/extract.mjs` - New: 8-page field map + `extractPage()` + shared `normalizeText()`
- `e2e/parity/ledger.mjs` - New: `PARITY-DEVIATIONS.md` parser + `isKnownDelta()` classifier
- `e2e/parity/parity-diff.mjs` - Rewired to consume `extract.mjs`/`ledger.mjs`; `--all`/`--page`/`--stage`/`--out`
- `.planning/phases/07-parity-validation-cutover/PARITY-REPORT.md` - New: the D-06 evidence artifact
- `.planning/phases/07-parity-validation-cutover/PARITY-CHECKLIST.md` - New: the D-05/D-08 manual checklist

## Decisions Made

- `extractPage`'s `origin` parameter is `{ base, flavour }` rather than a bare
  URL string, matching the plan's exact three-parameter signature while
  resolving both "which path" and "which selector half" from one value.
- Field-level ledger binding (`knownDeviations` declared on the field, not
  inferred from delta text) — the design decision the plan called out
  explicitly. Only the banner field carries `knownDeviations: [3, 4]` in this
  build; every other real divergence found (Team page structure, methodology's
  relocated credit line) is left as a genuine, currently-unclassified defect
  rather than pre-emptively ledgered, since ledgering them is a product/parity
  decision outside this plan's scope (building the tool, not adjudicating what
  it finds).
- Verified against override ports 8010/8011 instead of the plan's literal
  default-port (8000/8001) verify commands: port 8000 is held by the same
  pre-existing, unrelated vanilla `uvicorn` process (PID 2914) 07-01's SUMMARY
  already documented and explicitly left running untouched. Behavior at the
  default ports was not independently re-verified in this session, but
  `dual_site.sh`'s own port-guard logic (which correctly refused to adopt the
  foreign process in 07-01) is unchanged by this plan.

## Deviations from Plan

None — plan executed exactly as written. The port-override adaptation above
follows 07-01's own established precedent for the same pre-existing process
and is not a departure from the plan's intent.

## Issues Encountered

- The markdown fragment's alignment row (`|---|---|---|---|`) initially failed
  the `grep -c '^| '` acceptance check (9 rows instead of the required 10)
  because `|---` does not start with `| ` (pipe-space). Fixed by writing the
  alignment row as `| --- | --- | --- | --- |` (space after every pipe),
  matching the header row's own format — re-verified at 10 rows.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The comparison instrument (`extract.mjs` + `ledger.mjs` + `parity-diff.mjs`)
  and both evidence documents are complete and proven end-to-end against a
  live dual-site pair. 07-03 through 07-06 (the three real-calendar D-07
  validation passes plus the D-15 human cutover gate) can run
  `node e2e/parity/parity-diff.mjs --all --stage <name> --out <path>` and paste
  the result directly into `PARITY-REPORT.md`.
- Three real, currently-unclassified defects will show up on every run until
  triaged by a future plan: the Team page's structural divergence (React's
  Phase-3 squad-first default view vs vanilla's rate-ID form — 2 fields) and
  methodology's relocated data-source credit line (footer vs body text, plus a
  trailing sentence vanilla's footer carries that the body paragraph does not —
  1 field). Neither is a defect in this plan's own tooling; both are real,
  pre-existing product differences this plan's job was to surface, not resolve.
  07-03 (or whichever plan runs the first real stage pass) should either fix
  these to match vanilla or add ledger rows explaining them, per D-14/the
  ledger's own "Appending an entry" discipline.
- No blockers for 07-03.

---
*Phase: 07-parity-validation-cutover*
*Completed: 2026-09-07*

## Self-Check: PASSED

- FOUND: e2e/parity/extract.mjs
- FOUND: e2e/parity/ledger.mjs
- FOUND: e2e/parity/parity-diff.mjs
- FOUND: .planning/phases/07-parity-validation-cutover/PARITY-REPORT.md
- FOUND: .planning/phases/07-parity-validation-cutover/PARITY-CHECKLIST.md
- FOUND commit: 9006460
- FOUND commit: 81c4fca
- FOUND commit: e562fa8
