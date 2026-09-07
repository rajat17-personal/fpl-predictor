# Phase 7 Parity Report

**What this document is.** The evidence that CUT-01's second and third success criteria hold:
every page's output has been compared across a full gameweek cycle, and the daily/weekly cron
kept running green throughout. It is appended at each of the three D-07 cycle stages and cited
directly by the D-15 human cutover gate — nobody flips the seam's default without reading this
file first.

**Invariant.** No verdict may be recorded here that is not traceable to one of three things: a
`PARITY-DEVIATIONS.md` entry number, a fixing commit SHA, or a named cron-green citation. A
verdict written from memory is not evidence, and it does not go in this document.

## How a stage entry gets here

Boot the dual site, run the diff for that stage, and paste the emitted fragment into the
matching stage section below, replacing its empty template row-for-row:

```
bash scripts/dual_site.sh start
node e2e/parity/parity-diff.mjs --all --stage pre-deadline \
  --out .planning/phases/07-parity-validation-cutover/parity-fragment.md
# paste the appended fragment's table into the "Pre-deadline" section below,
# then delete the scratch fragment file
bash scripts/dual_site.sh stop
```

The emitted fragment's four columns (`Page | Verdict | Delta detail | Cron-green citation`)
match every stage table below exactly — it pastes in without editing the header row. The
`Cron-green citation` column is always empty in the emitted fragment; fill it in per the
checklist's cron-green step (`PARITY-CHECKLIST.md`) before treating the row as closed.

Each stage below is one of the three D-07 passes, in cycle order: **pre-deadline** (after the
Friday weekly export lands), **mid-gameweek** (matches live or settling), and **post-finish**
(after the gameweek closes and the scoreboard has run). A cycle must start at its pre-deadline
export — no joining mid-week (D-13).

### Pre-deadline

**This stage starts the cycle (D-13).** Validation gameweek: **GW4**, deadline_utc
`2026-09-12T12:30:00Z` (future at run time), export generated_utc `2026-09-07T16:04:03+00:00`
(landed via commit `ac489ca`, after `e2e/parity/`'s last tooling commit `81c4fca`,
2026-09-07T12:29:35Z — satisfying the pre-deadline precondition). No later pass in this cycle may
be run against a different gameweek.

**Run:** 2026-09-07T16:06:46.408Z | GW4 | generated_utc: 2026-09-07T16:04:03+00:00 | command:
`node e2e/parity/parity-diff.mjs --all --stage pre-deadline --out .planning/phases/07-parity-validation-cutover/PARITY-REPORT.md --vanilla-origin http://127.0.0.1:8010 --react-origin http://127.0.0.1:8011`
(override ports — port 8000 is held by a pre-existing, unrelated vanilla `uvicorn` process, PID
2914, documented in 07-01/07-02's SUMMARYs and left untouched)

| Page | Verdict | Delta detail | Cron-green citation |
| --- | --- | --- | --- |
| xP table | 5 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent — no failure records to cite either way). `web/data` git history: commit `ac489ca` (2026-09-07) landed this stage's GW4 export, the first export commit since the initial tracking commit `1ee176a`. |
| Rate my team | 3 fields compared, 1 explained, 2 defects | ledger #3; UNRESOLVED — 2 defect(s), needs a fixing commit SHA or a new PARITY-DEVIATIONS.md row | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Fixture ticker | 4 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Price watch | 5 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| League table & leaders | 4 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Scoreboard | 5 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Differentials | 4 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Methodology | 4 fields compared, 1 explained, 1 defects | ledger #3; UNRESOLVED — 1 defect(s), needs a fixing commit SHA or a new PARITY-DEVIATIONS.md row | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |

### Mid-gameweek

**Run:** _(not yet run)_ | GW _ | generated_utc: _ | command: _(paste the exact `parity-diff`
invocation that produced this stage's fragment)_

| Page | Verdict | Delta detail | Cron-green citation |
| --- | --- | --- | --- |
| xP table | | | |
| Rate my team | | | |
| Fixture ticker | | | |
| Price watch | | | |
| League table & leaders | | | |
| Scoreboard | | | |
| Differentials | | | |
| Methodology | | | |

### Post-finish

**Run:** _(not yet run)_ | GW _ | generated_utc: _ | command: _(paste the exact `parity-diff`
invocation that produced this stage's fragment)_

| Page | Verdict | Delta detail | Cron-green citation |
| --- | --- | --- | --- |
| xP table | | | |
| Rate my team | | | |
| Fixture ticker | | | |
| Price watch | | | |
| League table & leaders | | | |
| Scoreboard | | | |
| Differentials | | | |
| Methodology | | | |

## Defects found and how they were closed

D-14 is fix-forward: a defect closes by re-comparing the affected page at (or after) the stage
it was found, never by restarting the three-stage cycle. Every row here records that
re-comparison, not just the fix.

| Page | What was wrong | Disposition (fixed forward / new ledger row) | Commit SHA | Stage re-compared |
| --- | --- | --- | --- | --- |
| _(none recorded yet)_ | | | | |

## Cutover readiness

Read by the D-15 human gate before the flip is ever staged. Every figure here must be
computed from the stage tables and the defects table above — never estimated.

- Pages compared: pre-deadline **_**, mid-gameweek **_**, post-finish **_** (8 expected per stage)
- Total explained deltas (cite ledger #s): **_**
- Total defects found: **_**
- Total defects closed (see "Defects found and how they were closed" above): **_**
- **Remaining unexplained deltas: `_` — must read zero before the flip is staged.**

## Appending an entry

While running any validation pass in this phase, if a delta-fix commit changes React behaviour
to match vanilla (or to intentionally diverge from it), that commit must touch **this report**
and `PARITY-DEVIATIONS.md` in the same commit as the code change — never as a follow-up. Record
the new row in "Defects found and how they were closed" above with the commit SHA, and if the
fix is a deliberate divergence rather than a bug fix, add the matching numbered row to
`PARITY-DEVIATIONS.md` per that ledger's own "Appending an entry" section.

A verdict recorded here without one of the three citation kinds named in this document's
opening invariant — a ledger entry number, a fixing commit SHA, or a named cron-green citation
— is not evidence. It does not count toward "Cutover readiness" above, and the D-15 gate must
not be presented with it as settled.
