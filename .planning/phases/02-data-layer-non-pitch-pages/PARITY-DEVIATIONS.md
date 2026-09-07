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
| 9 | `/team`'s default view is the Squad tab (model-squad pitch, `h1` "Model squad GW{n}"), not vanilla's rate-ID entry form (`h1` "Rate my team"); the page's "Load your own team" helper copy ("Your ID is in the URL…") differs from vanilla's rate-form helper accordingly, since it is SquadTab's own load-entry prompt, not a port of vanilla's Rate-my-team form text | Phase 3's view-only default Squad tab decision (03-01, STATE.md) — the loaded-team flow already covers vanilla's rate-ID interaction surface via a different tab, so the two sides' default landing content is intentionally not identical | 07-03 (structural divergence first flagged by 02-03, formally recorded here) |
| 10 | Methodology's data-source credit-line paragraph in the page body ends after "…football-data.co.uk odds." and does not repeat the "Not affiliated with the Premier League or the official Fantasy Premier League game." disclaimer sentence inline, unlike vanilla's single combined footer paragraph — PageShell's unified sitewide footer (entry 6) already carries that disclaimer once for every page, so restating it inside the Methodology body would duplicate it | Entry 6's unified-footer decision (01-06): one disclaimer instance sitewide instead of a per-page repeat | 01-06 (retroactive; specific text-match consequence recorded now by 07-03) |

## Palette changes made in lockstep

Changes to shared token values, applied identically to both sites in a single commit, are **not**
deviations — a lockstep change produces no React-versus-vanilla difference for Phase 7 to find. This
section records them so the rationale survives the phase without inflating the numbered table above.

**2026-09-01 — UAT gap G-02-1 (dark theme reads green-tinted).** The four dark-mode neutral tokens
(`--color-bg`/`--bg`, `--color-surface`/`--surface`, `--color-surface-2`/`--surface-2`,
`--color-line`/`--line`) were rebalanced in `frontend/src/index.css` and `web/assets/style.css`
together, in the same commit (02-07 Task 2):

| Token | Before | After |
|-------|--------|-------|
| bg | `#111815` | `#141715` |
| surface | `#18211c` | `#1b201c` |
| surface-2 | `#1f2a24` | `#222924` |
| line | `#2c3831` | `#2e3731` |

**Lockstep over divergence — the decision and its reasons (applied in Task 2, recorded here):**

1. The four hexes were byte-identical between React and vanilla before this fix. Diverging would
   have been the first palette divergence in this ledger, forcing Phase 7's side-by-side pass to
   eyeball-exempt every surface on every page — the highest-cost entry the ledger could carry.
2. The change is token-value-only: it cannot alter data, layout, sort/filter semantics, or copy,
   and it reverts in one `git revert` with no migration.
3. The vanilla site is what the user actually looks at today and stays authoritative until
   CUT-01 — diverging would ship the reported defect on the live site for a full season.

`frontend/scripts/check-tokens.mjs` asserts the two files' four dark hexes stay identical (the
"vanilla lockstep" checks), so Phase 7 can trust the invariant instead of re-checking it by eye.

**Regression fix, not a deviation.** The React port additionally restored the `color-scheme`
declarations (`:root { color-scheme: light }`, `.dark { color-scheme: dark }`) and the body paint
(`background`/`color` from the `--color-bg`/`--color-ink` tokens) that vanilla already had at
`web/assets/style.css:4`, `:29` and `:55`. This brings the React port back to parity with vanilla's
existing behavior — it is not a new difference between the two sites.

## Appending an entry

While executing any plan in this phase, if you find yourself about to change vanilla behaviour
rather than port it — including "fixing" the counter-intuitive sort-arrow polarity, unifying the
two different `maxHi` formulas, or adding a `–` fallback to a column vanilla leaves un-guarded —
append a new numbered row here in the same commit as the change. A behavioural difference shipped
without a matching row is a parity defect, not a deviation.
