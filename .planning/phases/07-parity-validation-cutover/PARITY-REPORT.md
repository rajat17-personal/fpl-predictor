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

**Re-run after the manual-pass fixes (Task 3 close-out):** 2026-09-08 | GW4 | command:
`node e2e/parity/parity-diff.mjs --all --vanilla-origin http://127.0.0.1:8010 --react-origin http://127.0.0.1:8011`
→ `TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects`, exit 0 — proves the three
fix-forward commits closing G-07-1/G-07-2/G-07-3 (`a2839a8`, `86aba31`, `6a39d64`) introduced no
new scripted delta. The page table below is unchanged from the original run (field/delta counts
identical); this line is the re-verification citation for the "Cutover readiness" total below.

| Page | Verdict | Delta detail | Cron-green citation |
| --- | --- | --- | --- |
| xP table | 5 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent — no failure records to cite either way). `web/data` git history: commit `ac489ca` (2026-09-07) landed this stage's GW4 export, the first export commit since the initial tracking commit `1ee176a`. |
| Rate my team | 3 fields compared, 3 explained, 0 defects (re-compared after closing 2 defects, see below) | ledger #3, #9 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Fixture ticker | 4 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Price watch | 5 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| League table & leaders | 4 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Scoreboard | 5 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Differentials | 4 fields compared, 1 explained, 0 defects | ledger #3 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |
| Methodology | 4 fields compared, 2 explained, 0 defects (re-compared after closing 1 defect, see below) | ledger #3, #10 | No `data/cron.log` on this host as of 2026-09-07 (file absent). No `data/alerts.jsonl` on this host as of 2026-09-07 (file absent). `web/data` git history: commit `ac489ca` (2026-09-07). |

**Manual passes (D-05/D-08).** Both sites are up for the duration of this handover:
vanilla `http://127.0.0.1:8010`, react `http://127.0.0.1:8011` (override ports — port 8000 is
held by the same pre-existing, unrelated vanilla process, PID 2914). Entry **6980093** is the
D-08 comparison ID (numeric only — no manager name is recorded here or anywhere in this report).

| Item | Verdict |
| --- | --- |
| Manual eyeball pass (D-05, `PARITY-CHECKLIST.md` Part 1 — all 8 pages, desktop + mobile, light + dark) | Passed overall, per the user's verbatim report ("It overall matches, but a few issues to look into on the React site"), with 3 visual defects found on the Team page's pitch renderer and nav chrome. All 3 fixed forward on the React side (see "Defects found and how they were closed" below) — commits `a2839a8`, `86aba31`, `6a39d64`. Re-verified post-fix: `npm --prefix frontend run build`/`test` green (374/374), `npm --prefix e2e run test` green (42/42, including the frozen-fixture banner-text assertions updated for the G-07-3 fix), and a live Playwright measurement at 1280px/375px in both themes confirmed the header no longer wraps and the pitch stat text/outgoing outline render correctly (light and dark). |
| D-08 same-session solver comparison (`PARITY-CHECKLIST.md` Part 2 — entry 6980093, rate my team / one solve with identical locks / one two-gameweek plan, performed identically on both sites in one session) | Matched overall, per the user's verbatim report — no numeric or move discrepancy called out across rate my team, the one-solve comparison, or the two-gameweek plan for entry 6980093. |

**D-02 handover.** For the rest of GW4, the React site (`http://127.0.0.1:8011`, or the
production `FPL_FRONTEND=react` seam once deployed) is the daily driver for the user's real FPL
week, with vanilla (`http://127.0.0.1:8010`) standing by as the reference. Dogfooding continues
through the remainder of GW4; any further finding is recorded exactly like a scripted finding — a
defect row in "Defects found and how they were closed" below with a fixing commit SHA or a new
`PARITY-DEVIATIONS.md` ledger row — never from memory.

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
| Rate my team | `heading`/`formHelper` deltas: `/team`'s default Squad tab ("Model squad GW4") shows the Load-your-own-team helper copy, not vanilla's rate-ID form ("Rate my team" / "Enter your FPL team ID…") | New ledger row — deliberate default-view difference, Phase 3's 03-01 view-only Squad tab decision | New ledger row — `PARITY-DEVIATIONS.md` #9 (this commit) | pre-deadline (`node e2e/parity/parity-diff.mjs --page /team` → 3 fields, 3 explained, 0 defects) |
| Methodology | `creditLine` delta: the body credit-line paragraph ends after "…odds." and does not repeat the "Not affiliated…" disclaimer sentence vanilla's single combined footer paragraph carries | New ledger row — PageShell's unified sitewide footer (entry 6) already states the disclaimer once for every page; restating it in the body would duplicate it | New ledger row — `PARITY-DEVIATIONS.md` #10 (this commit) | pre-deadline (`node e2e/parity/parity-diff.mjs --page /methodology` → 4 fields, 2 explained, 0 defects) |
| Team (pitch renderer, manual pass G-07-1) | `PlayerCard`'s price/xP and range-line text rendered `--color-ink-2` (grey) directly on the pitch-1/pitch-2 green gradient — fails WCAG AA against both gradient stops in either theme; user reported "the xP score text is grey on the green pitch background and is hard to read" | Fixed forward — added theme-invariant `--color-pitch-stat-bg`/`-ink` tokens (dark backdrop + white text), applied only to real cards on a grass row (GK/DEF/MID/FWD), never Bench or a GhostCard | `a2839a8` | pre-deadline (full 374/374 frontend suite green; live Playwright screenshot at 1280px, light+dark, confirms readable stat chips on every pitch row) |
| Team (pitch renderer, manual pass G-07-2) | The suggested-out player in a best-XI swap carried no visible marking (opacity-50 only) while the incoming player got a green dashed outline — user asked for a matching red dashed outline on the outgoing card, "mirrors the existing green-dashed idiom" | Fixed forward — `diff="out"` now gets the same dashed-outline idiom as `GhostCard`, in the `bad` (red) token instead of `accent` (green) | `a2839a8` | pre-deadline (full 374/374 frontend suite green; live Playwright screenshot of the O'Reilly → Virgil swap confirms the red/green dashed pair) |
| Team / sitewide nav (manual pass G-07-3) | The GW deadline pill and theme toggle wrapped onto a second header row below the nav tabs at desktop width (~1280px) — a real layout defect, not viewport-specific: natural row content measured ~1289px against the 68rem/1088px inner cap, which never grows past that regardless of viewport | Fixed forward — tightened header spacing (18px section gaps → 4-8px, nav-link `px-3`→`px-1.5`) and re-split `GwBanner`'s two lines (line 1 `GW{gw} · {absolute deadline}`, line 2 `{countdown} · {freshness}`, nothing dropped); `PILL_CLASS`'s `px-3 py-1.5` substring left untouched since `extract.mjs`'s React banner selector matches on it | `86aba31`, `6a39d64` | pre-deadline (full 374/374 frontend suite green, 42/42 e2e suite green after updating `smoke.spec.ts`'s frozen banner-text constants; live Playwright measurement confirms one-line header at 1280px, 83px tall vs. 145px wrapped, in both themes; mobile 375px unaffected) |

## Cutover readiness

Read by the D-15 human gate before the flip is ever staged. Every figure here must be
computed from the stage tables and the defects table above — never estimated.

- Pages compared: pre-deadline **8**, mid-gameweek **0**, post-finish **0** (8 expected per stage)
- Total explained deltas (cite ledger #s): **11** — the final scripted re-run (`node e2e/parity/parity-diff.mjs --all`, 2026-09-08) reports `TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects`, all cited to ledger #3 (banner, 8 occurrences), #9 (heading/formHelper, 2 occurrences) and #10 (creditLine, 1 occurrence)
- Total defects found: **5** — 2 scripted (Task 1: Rate my team `heading`/`formHelper`, Methodology `creditLine`, both closed via new ledger rows in Task 2) + 3 manual (Task 3: pitch stat-text contrast G-07-1, missing outgoing outline G-07-2, nav-row desktop wrap G-07-3, all closed fix-forward in React code)
- Total defects closed (see "Defects found and how they were closed" above): **5**
- **Remaining unexplained deltas: `0` — reads zero; the pre-deadline stage is clean.**

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
