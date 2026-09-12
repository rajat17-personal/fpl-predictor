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

**Same validation gameweek as stage one (D-13 check).** Pre-deadline run header fixed **GW4**;
this run's export (`web/data/meta.json`) also names **gw: 4** — confirmed by the precondition
check below before anything was recorded. No later pass in this cycle may be run against a
different gameweek.

**Precondition check (run before booting anything):**
```
/home/sraja/miniconda3/envs/python314/bin/python -c "import json,os,datetime as dt; m=json.load(open('web/data/meta.json')); d=dt.datetime.fromisoformat(m['deadline_utc'].replace('Z','+00:00')); now=dt.datetime.now(dt.timezone.utc); sb=os.path.exists('web/data/scoreboard.json'); print('gw',m['gw'],'deadline_passed',d<now,'scoreboard_file',sb)"
-> gw 4 deadline_passed True scoreboard_file True
```
`web/data/scoreboard.json` exists but its only entry is `{"gw": 3, ...}` — GW4 has not been
scored yet. **Observed data state: deadline passed, scoreboard not yet run for GW4 — the
gameweek is in flight (matches live or settling), not finished.**

**Run:** 2026-09-12T13:15:38.357Z | GW4 | generated_utc: 2026-09-12T10:35:47+00:00 | command:
`node e2e/parity/parity-diff.mjs --all --stage mid-gameweek --out .planning/phases/07-parity-validation-cutover/PARITY-REPORT.md --vanilla-origin http://127.0.0.1:8010 --react-origin http://127.0.0.1:8011`
(override ports — port 8000 is held by a pre-existing, unrelated vanilla `uvicorn` process, PID
209850, same convention 07-01/07-02/07-03 already documented and left untouched)

Before this run, the live `web/data` working tree was committed as a baseline snapshot
(`chore(07-04): land mid-gameweek GW4 weekly export snapshot`, `0756b34`) so the
`git diff --quiet -- scripts/daily.sh scripts/weekly.sh web/data` acceptance check has something
clean to assert against — the files themselves were untouched by this task, only landed.

**Ledger entry 4 exercised for the first time.** Every page's `banner` delta now carries both
the freshness line (ledger #3, present since pre-deadline) *and* the deadline-passed wording
difference (ledger #4: react renders `GW4 deadline passed`, vanilla renders `· passed`) —
visible in the raw tool output, e.g. `vanilla=(GW4 deadline Sat Sep 12 0830 AM passed)
react=(GW4 deadline passedgenerated 2h ago)`. `extract.mjs`'s `deltaDetailCell()` cites only the
first declared ledger number per field (`declared[0]`, always `#3` for this field, per
`ledger.mjs`), so the table's "Delta detail" column below reads `ledger #3` even where entry #4
also explains the same delta — both numbers are declared on the `banner` field's
`knownDeviations: [3, 4]` list, so no *unlisted* delta exists here; the tool's citation format is
simply single-number-per-field, not a defect. No delta was found anywhere else on the banner, the
league/leaders page, or the Rate-my-team (squad) page beyond what pre-deadline already recorded.

| Page | Verdict | Delta detail | Cron-green citation |
| --- | --- | --- | --- |
| xP table | 5 fields compared, 1 explained, 0 defects | ledger #3 (banner delta also covered by #4 — see note above) | See "Cron-green citation" note below the table (shared across all eight rows). |
| Rate my team | 3 fields compared, 3 explained, 0 defects | ledger #3 (banner, also #4), #9 | See note below. |
| Fixture ticker | 4 fields compared, 1 explained, 0 defects | ledger #3 (also #4) | See note below. |
| Price watch | 5 fields compared, 1 explained, 0 defects | ledger #3 (also #4) | See note below. |
| League table & leaders | 4 fields compared, 1 explained, 0 defects | ledger #3 (also #4) | See note below. |
| Scoreboard | 5 fields compared, 1 explained, 0 defects | ledger #3 (also #4) | See note below. |
| Differentials | 4 fields compared, 1 explained, 0 defects | ledger #3 (also #4) | See note below. |
| Methodology | 4 fields compared, 2 explained, 0 defects | ledger #3 (also #4), #10 | See note below. |

**TOTAL (from the tool's own summary line): 8 pages, 34 fields compared, 11 explained, 0
defects, exit 0.** No page was carried forward from the pre-deadline stage under D-14's single
exception (that stage's own table shows 0 remaining defects after its Task 2/Task 3 closures),
so there is nothing to close here.

**Cron-green citation (D-16, shared across all eight rows above — same evidence covers every
page since the comparison ran once for all of them):**

1. **`data/cron.log`** exists on this host. Since the pre-deadline pass (2026-09-08), it shows
   two full `[daily]` runs, every step `OK`: `2026-09-11T06:30:05Z` (`data.snapshot OK`,
   `data.snapshot-gap-report OK`, `models.price-train OK`, `models.price OK`,
   `predict.scoreboard OK` — `scored GWs [3]`) and `2026-09-12T06:30:06Z` (same five steps `OK`,
   `predict.scoreboard` — `scored GWs none`, consistent with GW4 not yet finished). No
   `[weekly]` lines appear in this window because no Friday fell between 2026-09-08 and this run
   (2026-09-12) — GW4's weekly export already landed pre-deadline (`ac489ca`); a fresh weekly
   run isn't due until GW5's cycle, outside this stage's scope.
2. **`data/alerts.jsonl`** does not exist on this host as of 2026-09-12 (file absent — no
   failure records to cite either way, consistent with both daily runs reporting every step OK).
3. **`web/data` git history** since the pre-deadline pass's `ac489ca`: `6bdfbb9` (2026-09-08,
   Phase 9 export-contract lock test, ran `python -m predict.export` end to end and refreshed
   captains/meta/squad/xp_table for GW4), `f715aab` (2026-09-11, Phase 10 export-contract lock
   test, same refresh), and this stage's own baseline `0756b34` (2026-09-12, the mid-gameweek
   snapshot landed immediately before this run) — confirming the export kept moving throughout
   the window this stage covers.

**Observation, not a defect of this stage (out of scope to fix — cron lines are read-only for
the whole phase, T-07-04-05):** `crontab -l` on this host currently lists only the
`30 2 * * * .../daily.sh` and `@reboot .../snapshot_catchup.sh` lines. The
`0 8 * * fri .../weekly.sh` line documented as required setup in `06-USER-SETUP.md`/
`06-05-SUMMARY.md` is absent. This has not affected GW4's cycle — its one required weekly
export already landed pre-deadline via a manual `python -m predict.export` run (`ac489ca`),
and no further weekly run is due until GW5 — but it is worth the user reinstalling that line
before GW5's Friday export is due. Recorded for visibility, not auto-installed (this plan's
threat model forbids touching cron lines).

**Manual eyeball pass (D-05, `PARITY-CHECKLIST.md` Part 1) — deferred to end-of-phase UAT.**
`workflow.human_verify_mode` is `end-of-phase` (`.planning/config.json`); this task's own
`<verify>` block's `<human-check>` item is an automated-task human-check, not a
`type="checkpoint:*"` gate, so per the standard checkpoint protocol it is harvested into the
end-of-phase UAT pass rather than pausing here. (D-08's same-session interactive comparison is
not re-required at this stage — `PARITY-CHECKLIST.md` Part 2 calls for it once per cycle, and it
was already completed and recorded in the pre-deadline stage above.)

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

- Pages compared: pre-deadline **8**, mid-gameweek **8**, post-finish **0** (8 expected per stage)
- Total explained deltas (cite ledger #s): pre-deadline **11**; mid-gameweek **11** — `node e2e/parity/parity-diff.mjs --all --stage mid-gameweek`, 2026-09-12, reports `TOTAL: 8 pages, 34 fields compared, 11 explained, 0 defects`, all cited to ledger #3 (banner, 8 occurrences — every one of which is now also explained by #4, the deadline-passed-copy entry this stage first exercises), #9 (heading/formHelper, 2 occurrences) and #10 (creditLine, 1 occurrence)
- Total defects found: pre-deadline **5** (2 scripted + 3 manual, all closed — see table above); mid-gameweek **0**
- Total defects closed: pre-deadline **5**; mid-gameweek **0 found, 0 to close**
- **Remaining unexplained deltas: `0` after both stages run so far — pre-deadline and mid-gameweek are both clean. Post-finish remains to be run once GW4's scoreboard has scored.**

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
