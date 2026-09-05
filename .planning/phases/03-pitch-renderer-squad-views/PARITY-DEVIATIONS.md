# Parity Deviation Ledger — Phase 3

This file continues the numbering of `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md`
and follows its exact preamble intent: it lists every intentional difference between the React
rebuild and the live vanilla site (`web/`) introduced during Phase 3 (Pitch Renderer & Squad
Views). Phase 7 (CUT-01) runs a side-by-side comparison of the two sites and treats every entry
in this ledger as an explained delta — and every difference it finds that is **not** listed here
as a defect to fix before cutover.

Unlike Phase 2, most of Phase 3 is **new UI design, not parity porting** — vanilla has no pitch
(`03-CONTEXT.md`'s "Critical framing"). Only the rate/plan flows (`web/team.html`) carry vanilla
behavior and copy to preserve verbatim (D-19); everything pitch-shaped is this phase's own design.
This ledger therefore records the deltas at the seams where Phase 3 touches shared, previously-
parity-ported chrome (`PageShell`'s nav/footer, `usePageMeta`'s route table) or deliberately
replaces a vanilla rendering approach the earlier phases preserved.

## Deviations

| # | Deviation | Reason | Introduced by |
|---|-----------|--------|----------------|
| 9 | `/team` nav label renamed from "Rate my team" to "My team" | D-12 — the page outgrew its vanilla name once it hosts the pitch, solver, rate, and chips | 03-01 |
| 10 | Footer disclaimer gains one sentence about generic kit imagery ("Player kit colors shown are generic illustrations, not licensed team imagery.") | PITCH-01 success criterion 1 + D-03/D-04 | 03-01 |
| 11 | Vanilla's `squadCards()` list rendering (Best-XI and per-week plan squads) replaced by the new `<Pitch>` component | D-19 — explicitly authorized; "the pitch diff is the new centerpiece, nothing users had disappears" | 03-03 |
| 12 | `/team`'s page title changes from "Rate my team — FPL ML" to "My team — FPL ML"; description broadens from the vanilla single-purpose copy to the three-tab scope | Follows the D-12 nav rename for consistency | 03-01 |
| 13 | Chip timeline reports DGW/BGW **club counts** (integers), not club names, because `web/data/chips.json`'s `structure[].dgw_clubs`/`.bgw_clubs` are integer counts (`predict/export.py:197-198`), not arrays of club names as `03-RESEARCH.md`/`03-UI-SPEC.md` originally described — the UI-SPEC's "reveals the affected clubs" wording is explained by this row rather than silently diverged from | 03-02 |

## Appending an entry

While executing any plan in this phase, if you find yourself about to change vanilla behaviour
rather than port it — including replacing a vanilla list/table rendering with the new pitch
component, changing copy that D-19 requires to carry over verbatim, or diverging from a data
contract's actual shape — append a new numbered row here in the same commit as the change. A
behavioural difference shipped without a matching row is a parity defect, not a deviation.
