# Parity Deviation Ledger

This file lists every intentional difference between the React rebuild and the live vanilla
site (`web/`). Phase 7 (CUT-01) runs a side-by-side comparison of the two sites and treats every
entry in this ledger as an explained delta — and every difference it finds that is **not** listed
here as a defect to fix before cutover.

The parity model governing this phase is **behavioral parity, not pixel-level cloning** (D-01):
the rebuild must match vanilla's data, sort/filter/format semantics, and copy, but markup and
visuals are free to be React-idiomatic using the Phase 1 design tokens. All page copy (headlines,
explainers, footer disclaimer, Pro teaser) ports **verbatim** (D-03) — a copy rewrite is itself a
deviation and belongs in this ledger.

## Deviations

| # | Deviation | Reason | Introduced by |
|---|-----------|--------|----------------|
| 1 | Rich `ErrorState`/`EmptyState` (with a Retry affordance) instead of vanilla's silent blanks on a data-fetch failure | D-08, deliberate improvement | 02-01 |
| 2 | Accessible tap/click/keyboard status-flag tooltip instead of vanilla's desktop-only `title` attribute | D-09, deliberate improvement plus Phase 3 mobile-table preparation | 02-01 |
| 3 | The gameweek banner gains a "generated …" freshness line from `meta.json`'s `generated_utc` | D-20, deliberate trust-builder | 02-03 |
| 4 | The banner's deadline-passed state reads `GW{n} deadline passed` instead of vanilla's `· passed` suffix | D-21, clarity improvement | 02-03 |
| 5 | Price watchlist rows gain rise/fall trend icons vanilla does not have | UI-04 and D-17, deliberate small enhancement reusing existing dark-safe tokens | 02-04 |
| 6 | `PageShell`'s single unified footer replaces vanilla's per-page footer variants; the "How the model works" link is now sitewide and methodology's data-source credit line moves from the footer into the page body | Phase 1 shell simplification, logged retroactively now the ledger exists | 01-06 (Phase 1, retroactive) |
| 7 | Table header eyebrow text and other sub-14px vanilla chrome renders at the 14px Label token instead of vanilla's ~11px | Legibility improvement, respects the four-size typography contract | 02-01 |
| 8 | Scoreboard tile values render at the 28px Display token at weight 700 instead of vanilla's 24px weight 500 | The two-weight typography contract has no 500 | 02-05 |

## Appending an entry

While executing any plan in this phase, if you find yourself about to change vanilla behaviour
rather than port it — including "fixing" the counter-intuitive sort-arrow polarity, unifying the
two different `maxHi` formulas, or adding a `–` fallback to a column vanilla leaves un-guarded —
append a new numbered row here in the same commit as the change. A behavioural difference shipped
without a matching row is a parity defect, not a deviation.
