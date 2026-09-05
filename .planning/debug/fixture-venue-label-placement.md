---
status: diagnosed
trigger: "only issue I see is that the A, H lable looks a bit akward can it come belwo the team instead of next to it"
created: 2026-09-01T13:05:00Z
updated: 2026-09-01T13:32:00Z
---

## Current Focus
<!-- OVERWRITE on each update - reflects NOW -->

bug_class: Bohrbug (deterministic — static markup/CSS, reproduces on every render)

hypothesis: The inline H/A is a PARITY REGRESSION, not a design choice. Vanilla
  web/assets/style.css:155 sets `.fdr small { display: block }`, which already
  stacks H/A BELOW the opponent code. FdrCell.tsx:61 wraps the chip in
  `inline-flex items-center`, which blockifies the <small> into a flex ITEM on
  the main (row) axis — `display:block` has no stacking effect inside a flex
  row. The user is asking for vanilla's actual behaviour to be restored.
test: compare vanilla .fdr/.fdr small CSS against FdrCell.tsx chip classes
expecting: vanilla stacks (display:block), React does not (flex row) -> confirmed
next_action: check 02-UI-SPEC.md + PARITY-DEVIATIONS.md to confirm stacked layout
  was never recorded as an intentional deviation

reasoning_checkpoint:
  hypothesis: "FdrCell.tsx:61's `inline-flex items-center gap-0.5` on the chip
    forces the venue <small> onto the same row as the opponent code, dropping
    vanilla's `.fdr small { display: block }` stacking (style.css:155)."
  confirming_evidence:
    - "web/assets/style.css:155 — `.fdr small { display: block; font-size: 0.62rem; opacity: 0.75; }`"
    - "web/assets/style.css:152 — `.fdr { display: inline-block; text-align: center; ... }` (centers the stacked pair)"
    - "frontend/src/components/FdrCell.tsx:61 — chip is `inline-flex items-center gap-0.5`, a ROW flex container"
    - "frontend/src/components/FdrCell.tsx:64 — `<small className=\"text-[0.7em]\">` carries no display/opacity rule of its own"
    - "web/fixtures.html:74-75 — vanilla markup is `${f.opp}<small>...</small>`, structurally identical to the port; only the CSS differs"
  falsification_test: "If vanilla /fixtures rendered H/A inline beside the code,
    the port would be faithful and this would be a pure design change. Refuted:
    display:block on the <small> puts it on its own line in vanilla."
  fix_rationale: "Not applicable — diagnose-only mode. Direction: make the chip a
    column flex (or drop flex entirely for vanilla's inline-block + text-align:center)."
  blind_spots: "Not visually confirmed in a running browser — inferred from CSS
    cascade semantics. Have not measured resulting row-height delta empirically."
  candidate_causes:
    - "code: chip container uses row-direction flex, blockifying the <small> into a row item (CONFIRMED)"
    - "config: Tailwind v4 has no utility that reproduces `display:block on a child` from the parent — the port had to restructure, and restructured to a row (contributing)"
    - "data: none — f.home/f.opp values are correct; layout only"
  and_gate: "no — the single flex-direction choice at FdrCell.tsx:61 is sufficient
    to produce the symptom. The Tailwind-idiom cause is an explanation of WHY the
    port drifted, not a second necessary condition."

## Symptoms
<!-- Written during gathering, then IMMUTABLE -->

expected: Fixture ticker cells present the opponent code and venue (H/A) in a layout that reads clean and intentional.
actual: "only issue I see is that the A, H lable looks a bit akward can it come belwo the team instead of next to it" — the superscript-style H/A next to the code reads awkward; user wants it below the opponent code.
errors: None reported
reproduction: Test 2 in UAT — open /fixtures (dev server: npm --prefix /home/sraja/fpl/frontend run dev, backend on port 8000) and look at any GW cell chip.
started: Discovered during UAT of Phase 02 (data layer + non-pitch pages)

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-09-01T13:05:00Z
  checked: knowledge base .planning/debug/knowledge-base.md
  found: does not exist (no prior resolved sessions indexed)
  implication: no known-pattern shortcut; investigate from scratch

- timestamp: 2026-09-01T13:05:00Z
  checked: .planning/phases/02-data-layer-non-pitch-pages/02-UAT.md
  found: gap G-02-2 recorded, severity cosmetic, test 2, truth = "venue (H/A) label placement looks intentional, not awkward"
  implication: initially framed as a design-change request — REVISED below, it is a parity regression

- timestamp: 2026-09-01T13:12:00Z
  checked: frontend/src/components/FdrCell.tsx lines 55-66 (the populated-cell branch)
  found: |
    Chip = `inline-flex items-center gap-0.5 rounded px-2 py-1 font-label text-label`
    Children = bare text node {f.opp} then <small className="text-[0.7em]">H|A</small>.
    A row-direction flex container BLOCKIFIES every child into a flex item laid
    out along the main axis — so the <small> can never start a new line here,
    regardless of any display value it carries.
  implication: the inline H/A is produced by the chip's flex-direction (row), line 61

- timestamp: 2026-09-01T13:14:00Z
  checked: web/fixtures.html lines 73-76 (vanilla markup the port claims to copy)
  found: |
    `<span class="fdr fdr${f.fdr}" title="...">${f.opp}<small>${f.home?"H":"A"}</small></span>`
    Structurally IDENTICAL to the React port — same element order, same nesting.
  implication: the markup was ported faithfully; the divergence is entirely in CSS

- timestamp: 2026-09-01T13:16:00Z
  checked: web/assets/style.css lines 152-155 (vanilla .fdr chip styling)
  found: |
    152: .fdr { display: inline-block; text-align: center;
             font-family: "IBM Plex Mono", monospace; font-size: 0.76rem;
             padding: 6px 8px; border-radius: 6px; min-width: 58px; }
    154: td.cellpad { padding: 3px 4px; border-top: 1px solid var(--line); }
    155: .fdr small { display: block; font-size: 0.62rem; opacity: 0.75; }
  implication: |
    DECISIVE. Vanilla ALREADY renders H/A stacked BELOW the opponent code
    (display:block on the <small>), horizontally centred (text-align:center on
    an inline-block chip). The user is not requesting a new design — they are
    describing vanilla's existing behaviour, which the port silently dropped.
    Vanilla also pairs the taller 2-line chip with a FIXTURES-SPECIFIC tighter
    cell padding (td.cellpad 3px/4px) to stop rows bloating.

- timestamp: 2026-09-01T13:18:00Z
  checked: web/assets/style.css line 129 (vanilla generic td) vs Fixtures.tsx:95
  found: |
    Vanilla generic `td { padding: 8px 12px }` == the port's `px-3 py-2`.
    Vanilla overrides fixture cells to `td.cellpad { padding: 3px 4px }`.
    Fixtures.tsx:95 renders `<td className="px-3 py-2">` — the GENERIC padding;
    the cellpad override was never ported.
  implication: |
    Both halves of vanilla's ticker-cell design were dropped together (stacked
    chip + tight cell padding). That is why the port looks "different but not
    broken" rather than obviously wrong.

- timestamp: 2026-09-01T13:20:00Z
  checked: .planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md (D-04 ledger)
  found: only one fixtures-adjacent entry (#5, price watchlist trend icons). NO entry for the FDR chip layout, venue-label stacking, or the dropped cellpad padding.
  implication: the inline layout was never an APPROVED deviation — it is undocumented drift, so restoring vanilla's stacked layout needs no ledger reversal

- timestamp: 2026-09-01T13:22:00Z
  checked: .planning/phases/02-data-layer-non-pitch-pages/02-UI-SPEC.md lines 212-214, 349
  found: |
    L213: "for each fixture in the cell: opponent code + small H/A tag" — the
      spec says WHAT renders but never WHERE; stacked-vs-inline is unspecified.
    L349: "FDR ticker cell: min-width: 56px (rounded from vanilla's 58px)" —
      specifies the value but not WHICH element carries it.
  implication: |
    ROOT-CAUSE-OF-THE-ROOT-CAUSE. The UI-SPEC under-specified chip internal
    layout, so the implementer chose a reasonable-looking inline flex row. No
    gate could have caught it: no test, review, or typecheck asserts geometry.

- timestamp: 2026-09-01T13:24:00Z
  checked: min-w-[56px] placement across FdrCell.tsx and Fixtures.tsx
  found: |
    FdrCell.tsx:48  blank/em-dash chip  -> min-w-[56px] ON THE CHIP (+ justify-center)
    FdrCell.tsx:56  populated wrapper   -> min-w-[56px] ON THE WRAPPER
    FdrCell.tsx:61  populated chip      -> NO min-width, NO centring
    Fixtures.tsx:73 the <th>            -> min-w-[56px]
    Vanilla .fdr    EVERY chip          -> min-width:58px + text-align:center
  implication: |
    Pre-existing inconsistency that the stacked fix MUST reconcile. Today an
    inline chip is ~5ch wide ("FUL"+gap+"A") so it roughly fills the 56px
    wrapper by accident. Stacked, its intrinsic width collapses to ~3ch ("FUL")
    and the coloured chip would visibly shrink and left-align inside the
    wrapper, breaking column rhythm — unless min-width moves onto the chip
    (line 61) as vanilla has it, and centring is added.

- timestamp: 2026-09-01T13:26:00Z
  checked: FdrCell.test.tsx (7 tests) and Fixtures.test.tsx for layout assertions
  found: |
    No test asserts flex direction, chip geometry, or H/A position. The venue
    assertions are text queries only — getByText("H") line 22, getByText("A")
    line 30 — which pass identically under a stacked layout.
  implication: the fix is test-safe (zero rewrites); but nothing guards the layout, hence the need for a new regression assertion

- timestamp: 2026-09-01T13:28:00Z
  checked: typography tokens — vanilla .fdr vs the port's `font-label text-label`
  found: |
    Vanilla chip: IBM Plex MONO @ 0.76rem (12.16px), small @ 0.62rem + opacity .75
    Port chip:    --font-label = IBM Plex SANS @ --text-label = 14px,
                  small @ text-[0.7em] (9.8px), no opacity reduction
    A --font-mono token already exists at index.css:75 (added in plan 02-03).
  implication: |
    Adjacent undocumented drift. Relevant to the stacked fix because 14px sans
    stacks ~13.7px taller per chip than 12.16px mono, and mono is what gives
    vanilla's ticker its column alignment. Token is already available.

- timestamp: 2026-09-01T13:30:00Z
  checked: row-height impact of a naive flex-col flip (computed from current tokens)
  found: |
    Now:     py-1(8) + code line(14*1.4=19.6)                    = ~27.6px chip
             + td py-2(16)                                       = ~43.6px row
    Stacked: py-1(8) + code(19.6) + small(9.8*1.4=13.7)          = ~41.3px chip
             + td py-2(16)                                       = ~57.3px row
    Delta ~ +13.7px/row; x20 clubs = ~275px taller table.
    Restoring vanilla's cellpad (py-2 -> ~3px) puts the row at ~47.3px,
    only ~+3.7px vs today.
  implication: the height cost is real but is almost entirely cancelled by also porting vanilla's fixtures-specific tight cell padding — the two changes belong together

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  PARITY REGRESSION, not a design-change request. Vanilla already stacks the
  venue letter below the opponent code; the React port lost it in the CSS
  translation.

  Primary (sufficient) cause — frontend/src/components/FdrCell.tsx:61:
    the chip is `inline-flex items-center gap-0.5`, a ROW-direction flex
    container. Flex blockifies its children as flex items along the main axis,
    so the <small> venue tag (line 64) is pinned beside the opponent code and
    can never begin a new line.

  What it should have reproduced — web/assets/style.css:155:
    `.fdr small { display: block; font-size: 0.62rem; opacity: 0.75; }`
    on an `inline-block; text-align: center` chip (style.css:152) — i.e. venue
    on its own line, centred under the code. Vanilla's markup
    (web/fixtures.html:74-75) is byte-for-byte the same shape as the port's,
    so ONLY the CSS diverged.

  Why it drifted (blameless): 02-UI-SPEC.md:213 specifies the chip's CONTENT
  ("opponent code + small H/A tag") but never its internal LAYOUT. Tailwind has
  no utility that expresses "make my child display:block", so the port had to
  restructure the chip, and restructured it into a row. No gate could catch it:
  no test asserts geometry, and the deviation was never entered in the D-04
  PARITY-DEVIATIONS ledger.

  Three coupled sub-deviations the fix must handle together (all undocumented):
   1. Fixtures.tsx:95 uses generic `px-3 py-2` (== vanilla's generic
      `td {padding:8px 12px}`) instead of vanilla's fixtures-specific
      `td.cellpad {padding:3px 4px}` (style.css:154) which exists precisely to
      absorb the taller 2-line chip.
   2. `min-w-[56px]` sits on the WRAPPER (FdrCell.tsx:56), not on each chip;
      vanilla puts `min-width:58px` on EVERY `.fdr`. Stacking collapses a chip's
      intrinsic width from ~5ch to ~3ch, so without moving it the coloured chip
      shrinks and column rhythm breaks. Note FdrCell.tsx:48 (blank cell) already
      puts min-w + justify-center on the chip — the two branches disagree.
   3. Chip font is `font-label` (IBM Plex Sans, 14px) vs vanilla's IBM Plex Mono
      @0.76rem; `--font-mono` already exists at index.css:75.

fix: [not applied — diagnose-only mode]
verification: [n/a — diagnose-only mode]
files_changed: []
