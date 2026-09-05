---
status: diagnosed
gap_id: G-03-1
mode: find_root_cause_only
bug_class: Bohrbug (fully deterministic — reproduces on every render for any even-cardinality row)
trigger: "when the team loads two strikers they are not central. and instead a drift a bit left. same when I load my team and 4 def and 4 mid are displayed."
created: 2026-09-03T00:00:00Z
updated: 2026-09-03T00:55:00Z
---

## Current Focus

hypothesis: CONFIRMED — `centeredStartColumn()` (Pitch.tsx L31-33) places every row on a single INTEGER CSS grid start column. Exact centring needs s = (C - n)/2 + 1, an integer only when card count `n` and column count `C` share parity. With C pinned at 5 (odd), every even-sized row (n=2, n=4) needs a half-integer start; `Math.floor` drops the 0.5 and shifts the whole row half a column-pitch LEFT.
test: (1) algebraic offset derivation for a C-track grid; (2) ran the real `centeredStartColumn` over n=1..6; (3) rendered the real <Pitch> against the real 3-5-2 fixture in jsdom and read the actual inline `gridColumn` off every cell; (4) grepped all CSS for counteracting justification/margins; (5) read Pitch.test.tsx for encoded expectations.
expecting: n=2 -> start 2 (cols 2-3, -0.5p); n=4 -> start 1 (cols 1-4, -0.5p); n=1/3/5 -> offset 0.
result: All five checks agree. Rendered DOM: FWD n=2 gridColumn=[2,3] offset=-0.5p; Bench n=4 gridColumn=[1,2,3,4] offset=-0.5p; GK/DEF/MID offset=0p. Alternatives eliminated (padding, CSS counteraction, test lock-in, environment, ghost path).
next_action: NONE — diagnose-only mode. Root cause is confirmed and documented; fix is owned by UAT gap-closure planning for G-03-1. No source file was modified (verified via `git status`).

## RCA Branching (categories checked)

- code: CONFIRMED ROOT CAUSE — integer-quantised grid placement cannot express the half-track offset an even row needs in an odd track set (Pitch.tsx L31-33, L106).
- config: ELIMINATED — Tailwind gap classes (`gap-1 min-[480px]:gap-2`) and the 480px breakpoint are symmetric; changing the gap scales the drift but does not create it.
- environment: ELIMINATED — grid line placement is integer by CSS spec, not implementation-defined; algebra and a headless jsdom render agree exactly.
- data: TRIGGER, NOT CAUSE — squad formation determines which rows are even-sized and therefore which rows visibly drift; the function is wrong for those inputs regardless.
- process/spec: CONTRIBUTING (prevention only) — 03-UI-SPEC.md L103-105 prescribes a mechanism (`justify-content: center` on 1fr tracks) that cannot work, which pushed the implementer to improvise the defective scheme.

and_gate: no — a single defect is sufficient to produce the failure. Row parity is an input condition, not an independent second cause. `root_cause` is therefore one cause, with one contributing process cause recorded for prevention.

## Symptoms

expected: Formation rows on the pitch renderer render horizontally centred regardless of row size. A 2-striker FWD row or a 4-player DEF/MID row sits centred on the pitch, aligned with the visual midline (centre circle / GK card). Pitch reads as an FPL-style pitch at desktop and 375px (UAT test 1).
actual: "when the team loads two strikers they are not central. and instead a drift a bit left. same when I load my team and 4 def and 4 mid are displayed." Rows with 2 or 4 cards sit left of the pitch midline; GK (1) and 3/5-card rows look correct.
errors: none (visual layout defect, no console errors)
reproduction: Open /team with a 3-5-2 model squad (2-card FWD row) or load an FPL entry in a 4-4-2 (4-card DEF and MID rows). Compare each row's visual centre against the SVG centre circle at cx=50 / the single GK card.
started: Discovered during UAT on 2026-09-03 (phase 03 pitch renderer). Present since the row layout was implemented.

## Eliminated

- hypothesis: "Asymmetric container padding / max-width / margin on the pitch surface pushes rows left."
  evidence: "Pitch surface uses symmetric `p-4` (Pitch.tsx L155); row wrapper is `relative flex flex-col gap-4` (L202) with no horizontal offset; no max-width anywhere in the pitch subtree. Also falsified by the fact that GK (n=1), 3-DEF and 5-MID rows are exactly centred in the SAME container — a container-level offset would shift every row equally."
  timestamp: 2026-09-03T00:30:00Z

- hypothesis: "A CSS rule (justify-content / justify-items / place-content / auto margin) partially counteracts or compounds the placement."
  evidence: "Grepped all of frontend/src: the row container's complete class list is `grid gap-1 min-[480px]:gap-2` (Pitch.tsx L100). No justification or margin utility is applied to it. Every other `justify-center` hit is an unrelated flex container inside PlayerCard/FdrCell/ChipTimeline/etc."
  timestamp: 2026-09-03T00:30:00Z

- hypothesis: "The existing unit tests encode the buggy start columns, so the bug was 'locked in' by an assertion."
  evidence: "Read Pitch.test.tsx in full (111 lines). Zero assertions on gridColumn/gridTemplateColumns/start. The ghost test asserts only relative child ORDER (L93: `ghostCellIdx === odegaardCellIdx + 1`), which is invariant to start column. The tests never test centring at all — an absence of coverage, not a wrong expectation."
  timestamp: 2026-09-03T00:35:00Z

- hypothesis: "Environment/browser-specific CSS grid behaviour (drift only in the user's browser)."
  evidence: "Grid line placement is integer by CSS spec, not implementation-defined. Algebraic derivation and a jsdom render of the real component agree exactly on the start columns. The offset is deterministic and reproduces in a headless render with no browser involved."
  timestamp: 2026-09-03T00:50:00Z

- hypothesis: "Bench alignment or the ghost-card 6-column growth path contributes."
  evidence: "The ghost path is CORRECT: n=6 grows the grid to columns=6, same parity, offset=0p. The bench is not a separate cause but an additional VICTIM of the same defect (n=4, offset=-0.5p) — confirmed in the DOM probe. Neither is an independent contributing cause."
  timestamp: 2026-09-03T00:50:00Z

## Evidence

- timestamp: 2026-09-03T00:05:00Z
  checked: "`.planning/debug/knowledge-base.md` (Phase 0 known-pattern check). MemPalace not available in this session."
  found: "No knowledge base file exists yet (three unrelated active sessions: dark-theme-green-tint, fixture-venue-label-placement, nav-text-not-responsive — none touch pitch row layout)."
  implication: "No prior-pattern shortcut. Investigate from first principles."

- timestamp: 2026-09-03T00:10:00Z
  checked: "frontend/src/components/pitch/Pitch.tsx lines 31-33 and 95-106 — the entire row-placement mechanism."
  found: |
    function centeredStartColumn(count: number, columns: number): number {   // L31
      return Math.max(1, Math.floor((columns - count) / 2) + 1);             // L32
    }
    const slots = buildRowSlots(players, ghostPlayer, ghostAfterCode);       // L95
    const columns = Math.max(5, slots.length);                              // L96
    const start = centeredStartColumn(slots.length, columns);               // L97
    <div className="grid gap-1 min-[480px]:gap-2"                            // L100
      style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}> // L101
      ...<div style={{ gridColumn: start + i }}>                             // L106
    Every cell is placed on an INTEGER grid column line. There is exactly one
    start value per row, applied to all cells sequentially.
  implication: "Row position is fully determined by one integer, `start`. CSS grid lines are integers — a row can only ever begin at a whole track. Half-track placement is impossible by construction."

- timestamp: 2026-09-03T00:15:00Z
  checked: "Derived the exact centring offset algebraically for a grid of C equal `minmax(0,1fr)` tracks with C-1 gaps. Let p = track_width + gap (the column pitch). Container content width W = C*p - gap. A row of n cards starting at column s spans [(s-1)p, (s+n-1)p - gap], so its centre is ((2s+n-2)p - gap)/2. Grid centre is (C*p - gap)/2. offset = p*(2s + n - 2 - C)/2."
  found: "Perfect centring requires 2s + n - 2 - C = 0, i.e. s = (C - n)/2 + 1. That is an integer ONLY when (C - n) is even, i.e. when n and C share parity. The code computes s = floor((C-n)/2) + 1, so whenever (C-n) is odd the floor discards exactly 0.5, leaving offset = -p/2 (half a column pitch to the LEFT)."
  implication: "Parity mismatch is the mechanism. With the fixed C=5 (odd), every EVEN-sized row is off-centre by half a column pitch, always leftward. Every ODD-sized row is exact."

- timestamp: 2026-09-03T00:20:00Z
  checked: "Ran the real `centeredStartColumn` implementation over n=1..6 with the real `columns = Math.max(5, n)` rule and scored each with the offset formula."
  found: |
    n=1 cols=5 start=3 occupies 3..3 offset= 0.0p CENTRED
    n=2 cols=5 start=2 occupies 2..3 offset=-0.5p DRIFT LEFT
    n=3 cols=5 start=2 occupies 2..4 offset= 0.0p CENTRED
    n=4 cols=5 start=1 occupies 1..4 offset=-0.5p DRIFT LEFT
    n=5 cols=5 start=1 occupies 1..5 offset= 0.0p CENTRED
    n=6 cols=6 start=1 occupies 1..6 offset= 0.0p CENTRED  (ghost row grows to 6, same parity)
  implication: "Exactly matches the user report: 2-FWD drifts left, 4-DEF and 4-MID drift left, while GK (1), 3-DEF and 5-MID look correct. n=4 is the more visible case — cols 1-4 filled, col 5 conspicuously empty."

- timestamp: 2026-09-03T00:25:00Z
  checked: "Magnitude of the -0.5p drift at both UAT viewports. p = track + gap, track = (W - (C-1)*gap)/C."
  found: "Desktop, pitch inner width W~600px with gap-2 (8px): track=113.6px, p=121.6px, drift=~61px left (over half a card width). At 375px, W~311px with gap-1 (4px): track=59px, p=63px, drift=~32px left."
  implication: "Drift is large and clearly visible at both viewports — consistent with 'drift a bit left' being reported by eye against the SVG centre circle (cx=50, Pitch.tsx L176) and the single GK card, both of which ARE exactly centred."

- timestamp: 2026-09-03T00:30:00Z
  checked: "Ruled out counteracting/contributing CSS. Grepped all of frontend/src for justify-center / justify-items / place-content / grid-column / margin-auto on the row container."
  found: "The row container's full class list is `grid gap-1 min-[480px]:gap-2` (Pitch.tsx L100) — no justify-content, no justify-items, no auto margins, no max-width. The only other grid-related hits are unrelated flex `justify-center` inside PlayerCard/FdrCell/etc. The pitch surface uses symmetric `p-4` (L155) and the rows sit in `relative flex flex-col gap-4` (L202) — a block-level column with no horizontal offset."
  implication: "Nothing counteracts or adds to the offset. Padding is symmetric so the grid container itself is centred on the pitch; the drift originates solely from the integer start column. Single root cause, no compounding factor."

- timestamp: 2026-09-03T00:35:00Z
  checked: "frontend/src/components/pitch/Pitch.test.tsx (all 111 lines) for assertions on column placement."
  found: "Zero assertions on `gridColumn`, `start`, `gridTemplateColumns`, or any positional property. The ghost test (L87-93) asserts only RELATIVE DOM child ORDER (`ghostCellIdx === odegaardCellIdx + 1`), which is invariant to the start column. `centeredStartColumn` is never called directly by any test."
  implication: "The tests do NOT encode the buggy expectation — they simply never test centring at all. This is the gate gap that let the defect ship: a pure-arithmetic, fully unit-testable function has no unit test. A fix will not have to fight an existing assertion."

- timestamp: 2026-09-03T00:40:00Z
  checked: "03-UI-SPEC.md lines 97-111 (Layout — CSS Grid, verified 5-column ceiling, D-07) vs the implementation, and 03-01-SUMMARY.md line 29 for the recorded pattern decision."
  found: |
    UI-SPEC L103-105: "rows with fewer than 5 starters (e.g. a 3-DEF row) center their
    cards within the row via `justify-content: center` on the row container, not by
    changing `grid-template-columns`."
    03-01-SUMMARY.md L29 records the implementer's deliberate substitution:
    "Pitch row centering via computed grid-column start offset (never justify-content
    on 1fr tracks), preserving the fixed 5-column grid at every viewport width"
  implication: |
    The implementer was RIGHT to reject the spec's prescription — `justify-content:
    center` is a no-op on `minmax(0,1fr)` tracks because 1fr consumes all free space,
    so there is nothing left to distribute. But the replacement (integer grid-column
    start) silently traded one broken centring mechanism for another that only works
    at odd cardinalities. The spec itself is defective here; the fix must correct BOTH
    the code and UI-SPEC L103-105, or the next implementer re-derives the same bug.

- timestamp: 2026-09-03T00:45:00Z
  checked: "Scope of affected rows beyond the two the user named. splitPitchRows (frontend/src/lib/formation.ts L39-50) yields gk/def/mid/fwd/bench; bench is always 15-11 = 4 cards (UI-SPEC L108)."
  found: "The bench row uses the identical PitchRow component (Pitch.tsx L248-256) with n=4 and columns=5, so it drifts left by the same -0.5p. Every legal FPL formation has an even-sized row: 3-4-3 (4 MID), 4-4-2 (4 DEF, 4 MID, 2 FWD), 3-5-2 (2 FWD), 4-5-1 (4 DEF), 5-4-1 (4 MID), 5-3-2 (2 FWD), 4-3-3 (4 DEF), 3-4-3 (4 MID)."
  implication: "The defect is not formation-specific — it is present in every squad view including the bench, on every page that renders <Pitch>. Fix scope is the single shared PitchRow, so one change corrects all of them."

- timestamp: 2026-09-03T00:50:00Z
  checked: "EMPIRICAL CONFIRMATION. Rendered the real <Pitch> against the real 3-5-2 test fixture (src/test/fixtures/squad.json — DEF 3 / MID 5 / FWD 2 / GK 1 / bench 4, i.e. exactly the user's reported case) in jsdom via a throwaway vitest probe, and read the actual inline `gridColumn` off every rendered cell. Probe file deleted afterwards; `git status` confirms no source file was modified."
  found: |
    Goalkeeper   tracks="repeat(5, minmax(0, 1fr))" n=1 gridColumn=[3]         offset= 0.0p CENTRED
    Defenders    tracks="repeat(5, minmax(0, 1fr))" n=3 gridColumn=[2,3,4]     offset= 0.0p CENTRED
    Midfielders  tracks="repeat(5, minmax(0, 1fr))" n=5 gridColumn=[1,2,3,4,5] offset= 0.0p CENTRED
    Forwards     tracks="repeat(5, minmax(0, 1fr))" n=2 gridColumn=[2,3]       offset=-0.5p DRIFT LEFT
    Bench        tracks="repeat(5, minmax(0, 1fr))" n=4 gridColumn=[1,2,3,4]   offset=-0.5p DRIFT LEFT
  implication: |
    Root cause CONFIRMED by direct observation, not inference. The 2-FWD row is
    placed on columns 2-3, so its visual centre lands on the line BETWEEN track 2
    and track 3 — while the grid's true centre is the MIDDLE of track 3. That is a
    half-column-pitch leftward drift, exactly the reported symptom. The bench shows
    the identical fault at n=4. All odd-cardinality rows are exact, which is why the
    user perceived the drift as specific to "two strikers" and "4 def and 4 mid".

## Resolution

root_cause: |
  `centeredStartColumn()` (frontend/src/components/pitch/Pitch.tsx L31-33) centres a
  formation row by choosing a single INTEGER CSS grid start column:

      Math.max(1, Math.floor((columns - count) / 2) + 1)

  and every cell in the row is then placed at `gridColumn: start + i` (L106) inside a
  fixed `repeat(columns, minmax(0,1fr))` track set (L101) where `columns = Math.max(5,
  slots.length)` (L96).

  True centring requires the start column s = (C - n)/2 + 1, which is an integer ONLY
  when the row's card count `n` and the column count `C` share parity. Because C is
  pinned at 5 (odd) for every non-ghost row, every EVEN-sized row (n = 2 or 4) needs a
  half-integer start column, which CSS grid cannot express. `Math.floor` discards that
  0.5 and the whole row is placed half a column-pitch (track width + gap) to the LEFT
  of the pitch midline — ~61px at desktop, ~32px at 375px.

  This is a single defect in one shared function; row cardinality (2-FWD, 4-DEF, 4-MID,
  4-bench) is the data-dependent TRIGGER, not a co-cause. AND-gate: no — no second
  simultaneous condition is required, the function is simply wrong for even n.

  Contributing cause (prevention only, not required for the failure): 03-UI-SPEC.md
  L103-105 prescribes centring "via `justify-content: center` on the row container",
  which is a no-op against `minmax(0,1fr)` tracks because 1fr absorbs all free space.
  The implementer correctly rejected it (recorded in 03-01-SUMMARY.md L29) and
  improvised the integer-start-column scheme, trading one broken mechanism for another
  that only happens to work at odd cardinalities. The spec must be corrected alongside
  the code or the next implementer re-derives the same class of bug.

fix: "NOT APPLIED — this session ran in find_root_cause_only mode. Fix is owned by UAT gap-closure planning for G-03-1."

fix_direction: |
  Both options below preserve D-07 (fixed column measure, cards shrink rather than
  reflow) and the ghost row's growth to a 6-card measure.

  RECOMMENDED — Option B, flex row with a grid-derived card measure:
    Replace the row's `display:grid` + per-cell `gridColumn` with
    `display:flex; justify-content:center` and give each cell a fixed basis equal to
    one track of the SAME `cols = Math.max(5, slots.length)` measure:
      flex: 0 0 calc((100% - (cols - 1) * var(--pitch-gap)) / cols)
    Flex centring is continuous, not integer-quantised, so it is exact for every n with
    no parity condition. Card width still derives from the 5-column measure, so the
    no-reflow invariant is unchanged, and the ghost row still divides by 6. The existing
    responsive gap survives unchanged if the gap is lifted to a custom property
    (e.g. `[--pitch-gap:4px] min-[480px]:[--pitch-gap:8px]` with `gap-[var(--pitch-gap)]`),
    replacing the current `gap-1 min-[480px]:gap-2`. No gap surgery, smallest diff.

  ALTERNATIVE — Option A, doubled 10-column grid (half-track granularity):
    `repeat(2 * cols, minmax(0,1fr))`, each card spanning 2 columns starting at
    `gridColumn: (cols - n + 1) / span 2`. Integer-valued for every n (n=2 -> start 4,
    n=4 -> start 2), so centring becomes exact. Costs more: the grid `gap` must drop to
    0 (otherwise a gap appears down the middle of each 2-column card) and the visual gap
    must be reintroduced as per-cell horizontal padding, which perturbs each card's inner
    content width. Only prefer this if a grid-specific behaviour must be retained.

  ALSO REQUIRED:
    1. Correct 03-UI-SPEC.md L103-105 — `justify-content: center` on `1fr` tracks is a
       no-op; document the chosen mechanism so it is not re-derived incorrectly.
    2. Add the regression test that does not exist today (see recurrence_guard).
    3. Apply the fix once in the shared PitchRow — it corrects GK/DEF/MID/FWD and the
       bench in every view that renders <Pitch>.

verification: "N/A — no fix applied in this session."

files_changed: []

affected_surface: |
  frontend/src/components/pitch/Pitch.tsx — L31-33 (centeredStartColumn), L96-97
  (columns/start), L100-101 (row container + track definition), L106 (per-cell
  gridColumn). One shared PitchRow serves GK/DEF/MID/FWD (L203-242) and the bench
  (L248-256), so every even-sized row in every squad view is affected. Every legal FPL
  formation contains at least one even row (3-4-3, 4-4-2, 3-5-2, 4-5-1, 5-4-1, 5-3-2,
  4-3-3), and the 4-card bench is always affected.

oracle_type: derived (contract/model — a row's centre of mass must equal the container's centre; asserted on the placement model, since jsdom has no layout engine to measure real pixel centres)

why_not_caught: |
  Unit tests. `centeredStartColumn` is a pure integer function — trivially unit-testable
  — but Pitch.test.tsx asserts only badges, ghost ORDER, and prop threading; it makes
  zero positional assertions. The UI review (03-UI-REVIEW.md) confirmed the presence of
  the decorative markings but not row alignment against them. The defect was therefore
  only reachable by eye, which is exactly what happened at UAT.

recurrence_guard: |
  frontend/src/components/pitch/Pitch.test.tsx — an implementation-agnostic symmetry
  test over the row-placement result: for n in {1,2,3,4,5,6} assert leading free space
  === trailing free space (equivalently `2s + n - 2 - C === 0` for the grid form, or
  `justify-content: center` plus a `max(5,n)` basis divisor for the flex form).
  Boundary neighbours chosen deliberately: n=1 (min), n=2 and n=4 (the even cases that
  fail today), n=3 (odd control that passes today, guards against an over-correction
  that breaks odd rows), n=5 (max, zero free space), n=6 (ghost overflow, grid grows
  to 6). The n=3 and n=5 controls matter — a naive fix that shifts everything right by
  half a track would fix the even rows and silently break the odd ones.
