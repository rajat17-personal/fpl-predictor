---
phase: 10-xp-experiment-follow-ups
plan: 15
subsystem: xp-model-experiments
tags: [fbref, manual-acquisition, ledger, rl-reward-shaping, close-out]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "plan 10-14's closed model-class bracket and news_sentiment ledger entries (the two tail items this plan follows)"
provides:
  - "The D-04 manual-FBref-snapshot item closed: Task 1's Go decision executed (ten real downloads), a genuine acquisition-format defect discovered and root-caused (not assumed) before any code was written, and a second human decision (drop the join) recorded against that new evidence"
  - "data/external/fbref/README.md + the ten fbref_<season>_defense.csv files -- a permanent evidentiary snapshot, not joined into the pipeline"
  - "IMPROVEMENTS.md's '### fbref_v2: manual snapshot -- acquisition decision and outcome' and '### RL reward shaping: potential-based only' subsections -- both D-04 dead-tail items closed in the permanent record"
affects: [10-16 (final combined close-out; confirms Phase 10's config.EXPERIMENTS defaults -- this plan leaves fbref_v2 and rl_strategy both False, unchanged)]

# Actuals (#2632)
actuals:
  tokens: 127509
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Root-cause a surprising data finding against the live source itself (browser screenshot + incognito re-test) before deciding, rather than guessing at an export-tool bug and either silently working around it or silently dropping the item -- mirrors this phase's 'never dropped silently' discipline one level deeper: not just recording a Drop with reasoning, but verifying the reasoning is actually true before recording it."
    - "A second checkpoint fired mid-task (not scripted into the plan) when Task 2's own <read_first> investigation surfaced a fact the plan's Task 1 checkpoint could not have anticipated -- the executor stopped and asked rather than picking one of Task 1's three pre-declared options (A/B/C) as if it still applied unmodified."

key-files:
  created:
    - data/external/fbref/README.md
    - data/external/fbref/fbref_2016-17_defense.csv (..2025-26, ten files)
  modified:
    - IMPROVEMENTS.md

key-decisions:
  - "Task 1 verbatim decision: 'A' -- Go, all ten seasons (2016-17..2025-26), against the confirmed-dead automated-access evidence, the FotMob +1/season prior, and the fact that plans 10-01..10-14 (13 of 14 timed) consumed ~484 minutes (~8.1h) with no hard total-phase time budget ever declared."
  - "Acquisition succeeded (5,454 rows, 496 KB, ten files) but a second, unplanned finding emerged from Task 2's own <read_first> column-population check: config.FBREF_COLS's three source columns (Tkl+Int, Blocks, Clr) are 100% empty in every one of the 5,454 rows across all ten files -- confirmed not an export-tool artifact by a live browser screenshot of the FBref page itself plus an incognito re-test ('stil blank', verbatim). This is a third distinct FBref failure mode on record, different from both the 2026-08-22 value-blanking finding (Phase E) and Phase 9's access-layer-never-clears finding (fbref_v2, plan 09-09)."
  - "Second verbatim decision on that new finding: 'C' -- drop the join, record as an acquisition-format defect, explicitly distinct from declined-on-cost (the developer did complete the ten downloads; the source's currently-served data is what is deficient). No load_manual_snapshot, no reader/join code, no leakage test was written -- data/fbref.py, config.FBREF_COLS, and features/engineer.py are byte-identical to before this plan."
  - "The ten CSVs and their README are committed and retained (not deleted) as evidentiary artifacts, matching the plan's own 'artifacts... only on a Go or Partial decision' framing -- the acquisition itself was a Go, even though the resulting join was later dropped on new evidence discovered after acquisition."
  - "RL reward-shaping note written exactly as scoped: notes-only, no training, optimize/rl_env.py and optimize/rl_train.py untouched (git diff --stat confirms zero changes)."

requirements-completed: [TODO-FBREF-MANUAL, TODO-RL-SHAPING]

coverage:
  - id: D1
    description: "The FBref item is decided by a human against the confirmed access reality and the measured FotMob prior (Task 1: 'A'), then a second human decision closes it against a newly-discovered acquisition-format defect (Task 2 finding, decision 'C') -- both decisions recorded verbatim with their reasoning, never an unexplained absence"
    requirement: TODO-FBREF-MANUAL
    verification:
      - kind: other
        ref: "python -c reading IMPROVEMENTS.md for the required subsection headings and citations -- 'both tail subsections present'"
        status: pass
      - kind: other
        ref: "pandas non-null column counts over all ten CSVs (Tkl+Int/Blocks/Clr: 0/5454 populated; TklW/Int: fully populated) -- reproduced in this SUMMARY and IMPROVEMENTS.md"
        status: pass
    human_judgment: true
  - id: D2
    description: "No adoption number was fabricated against a defective/unusable data source -- the flag stays off, no code was written around all-NaN columns"
    requirement: TODO-FBREF-MANUAL
    verification:
      - kind: other
        ref: "config.EXPERIMENTS['fbref_v2'] is False; grep -c 'load_manual_snapshot' data/fbref.py -> 0 (not written); git diff --stat data/fbref.py features/engineer.py tests/test_leakage.py -> empty"
        status: pass
    human_judgment: false
  - id: D3
    description: "The RL item is notes-only: no training runs, neither optimize/rl_env.py nor optimize/rl_train.py changed"
    requirement: TODO-RL-SHAPING
    verification:
      - kind: other
        ref: "git diff --stat optimize/rl_env.py optimize/rl_train.py -> empty"
        status: pass
    human_judgment: false
  - id: D4
    description: "The potential-based-shaping correction (Ng, Harada and Russell 1999), the price-chasing failure mode, and the log-linear compute curve are on the record for any future revisit"
    requirement: TODO-RL-SHAPING
    verification:
      - kind: other
        ref: "python -c checking IMPROVEMENTS.md for 'Ng, Harada and Russell', 'optimize/rl_env.py', 'log-linear', 'potential-based', '1e-6', 'weight 1', 'D-16', 'skip' -- all present"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full repo test suite and lint stay green after the plan's edits"
    requirement: TODO-FBREF-MANUAL
    verification:
      - kind: integration
        ref: "python -m pytest -q -> 328 passed, 1 pre-existing skip, 279.73s"
        status: pass
      - kind: other
        ref: "ruff check . -> All checks passed!"
        status: pass
    human_judgment: false

duration: spanned two mid-plan human checkpoints (Task 1 decision, then an unplanned Task 2 finding requiring a second decision); wall-clock not separately timed
completed: 2026-09-11
status: complete
---

# Phase 10 Plan 15: Manual FBref Snapshot -- Acquisition-Format Defect Found and Closed; RL Reward-Shaping Notes Recorded Summary

**The developer completed all ten manual FBref downloads (Task 1: "A"), but Task 2's own read-first investigation found the acquired data does not contain the columns `config.FBREF_COLS` needs -- confirmed live on FBref's own page (not an export-tool bug) -- so the join was dropped on a second human decision ("C") and recorded as an acquisition-format defect, distinct from declined-on-cost; the RL reward-shaping notes (potential-based-only correction, Ng/Harada/Russell 1999, the log-linear compute curve) were recorded exactly as scoped, notes-only, with zero code changed.**

## Performance

- **Completed:** 2026-09-11
- **Tasks:** 3 of 3 resolved -- Task 1 (decision checkpoint, verbatim "A"), Task 2 (investigation surfaced a defect the plan could not have anticipated; resolved via a second human decision, verbatim "C", rather than the originally-planned reader/join code), Task 3 (ledger subsections written)
- **Files modified:** 12 (`IMPROVEMENTS.md`, `data/external/fbref/README.md`, ten `fbref_<season>_defense.csv` files)
- **Commits:** 2

## Accomplishments

- **Task 1: Go/no-go decision on the manual FBref snapshot.** Presented the confirmed-dead automated-access evidence (three real Chrome UC-mode attempts, `fbrapi.com` half-down 2026-09-09), the FotMob +1/season prior for the same signal family, and the time-remaining fact (plans 10-01..10-14, 13 of 14 timed, consumed ~484 minutes / ~8.1 hours with no hard total-phase time budget ever declared). **Verbatim decision: "A" -- Go, all ten seasons.**
- **The developer completed all ten downloads.** `data/external/fbref/fbref_<season>_defense.csv` for 2016-17 through 2025-26 -- 5,454 total player-season rows, 496 KB, real "Player Defensive Actions" export shape (grouped super-header + real column-name row, trailing `Matches`/hash columns) confirmed by the orchestrator's per-file verification before I began Task 2.
- **Task 2's `<read_first>` investigation surfaced a genuine, unplanned finding before any reader code was written.** Checking non-null coverage of every column across all ten files:

  | column | non-null (2025-26, n=551) | non-null (2016-17, n=543) |
  |---|---:|---:|
  | `90s`, `Player`, `Squad`, etc. | 551/551 | 543/543 |
  | `TklW` (tackles won) | 551/551 | 542/543 |
  | `Int` (interceptions) | 551/551 | 542/543 |
  | `Tkl` (total tackles) | **0/551** | **0/543** |
  | `Blocks` | **0/551** | **0/543** |
  | `Clr` (clearances) | **0/551** | **0/543** |
  | `Tkl+Int` | **0/551** | **0/543** |
  | `Def 3rd`/`Mid 3rd`/`Att 3rd`, Challenges block, `Sh`/`Pass`, `Err` | **0/551** | **0/543** |

  `config.FBREF_COLS`'s three columns derivable from this table (`fb_tkl_int_90` from `Tkl+Int`, `fb_blocks_90` from `Blocks`, `fb_clr_90` from `Clr`) are exactly the three that are universally blank, in every row of every season -- confirmed not sparse real missingness by checking known heavy tacklers (Idrissa Gueye 2016-17: `TklW=103, Int=77` populated, `Tkl`/`Blocks`/`Clr`/`Tkl+Int` blank; N'Golo Kanté: same pattern).
- **Root cause verified, not assumed, before any decision was made.** The initial hypothesis -- an export-widget artifact in FBref's "Get table as CSV" tool -- was tested and ruled out: the developer captured a live browser screenshot of `fbref.com/en/comps/9/2025-2026/defense/2025-2026-Premier-League-Stats#all_stats_defense` showing the *page itself* rendering the same columns blank, then re-tested in an incognito window with extensions disabled and reported, verbatim, **"stil blank."** Conclusion recorded in both `data/external/fbref/README.md` and `IMPROVEMENTS.md`: FBref is not currently serving these columns' data to logged-out visitors at all -- a site-side content change, not an access block or export-tool limitation this project's tooling could work around.
- **Second verbatim decision, on the new finding: "C" -- drop the join, record as an acquisition-format defect.** Explicitly distinct from declined-on-cost: the acquisition succeeded and the developer's effort was real; the *source's currently-served data* is what turned out to be deficient, discovered only after acquisition. Per this instruction: **no `load_manual_snapshot`, no reader/join code, and no `tests/test_leakage.py` addition were written.** `data/fbref.py`, `config.FBREF_COLS`, and `features/engineer.py`'s existing FBref wiring are byte-identical to before this plan (confirmed via `git diff --stat`).
- **The ten CSVs and the README are committed and retained** as a permanent evidentiary snapshot -- per the plan's own framing that the CSVs are an expected artifact "only on a Go or Partial decision" (the acquisition itself was a Go), and per this project's "never dropped silently" ledger discipline. A future revisit (e.g. if FBref restores column-serving, or via authenticated access) can compare a fresh single-season download's column-null pattern against this snapshot before re-attempting a join.
- **Task 3: wrote both required `## Phase G` ledger subsections.**
  - `### fbref_v2: manual snapshot -- acquisition decision and outcome (plan 10-15)` -- extends (does not replace) Phase 9's own `### fbref_v2:` entry; records both verbatim decisions ("A" then "C"), the carried-forward access evidence, the new acquisition-format-defect evidence (verbatim header row, the non-null table above, the live-browser + incognito re-test), and that no adoption number was measured.
  - `### RL reward shaping: potential-based only, recorded for any future revisit (plan 10-15)` -- all three points from the source todo, recorded as a correction of the developer's own stated instinct: (1) week-average baseline skip (action-independent, PPO's value function already does this), (2) team-value shaping must be potential-based only (`reward += gamma*Phi(s')-Phi(s)`, Ng/Harada/Russell 1999) never a raw additive bonus (price-chasing risk), naming `optimize/rl_env.py`'s reward function (lines 247-259, proven equal to `run_season`'s total to within 1e-6) as the code location any change would touch, and (3) the binding constraint was training budget not reward design, with the full v1->v2->v3 log-linear compute curve recorded and D-16's declare-before-training rule restated. Closed with the pure-realised-points adoption rule.
- **Full repo suite green after all edits:** `python -m pytest -q` -> **328 passed, 1 pre-existing skip, 279.73s**; `ruff check .` -> **All checks passed!**

## Task Commits

1. **Task 1: Go/no-go decision checkpoint** -- no files changed (decision-only checkpoint), no commit
2. **Task 2: acquired-CSV investigation -> acquisition-format defect found -> second decision "C" -> evidentiary snapshot committed** -- `d466da9` (chore) -- ten CSVs + `data/external/fbref/README.md`
3. **Task 3: record the FBref outcome and the RL potential-based-shaping note** -- `2828413` (docs) -- `IMPROVEMENTS.md`

## Files Created/Modified

- `data/external/fbref/README.md` -- new: Source/Attribution/Regeneration/Reduction-applied/PII-spot-check sections plus an "Acquisition-format defect" section documenting the finding, the root-cause verification, and the outcome
- `data/external/fbref/fbref_2016-17_defense.csv` through `fbref_2025-26_defense.csv` -- new: the ten manually-downloaded CSVs, committed verbatim (496 KB total, no reduction applied)
- `IMPROVEMENTS.md` -- two new `## Phase G` subsections (`### fbref_v2: manual snapshot...` and `### RL reward shaping: potential-based only...`), inserted between the existing `### news_sentiment: adoption verdict (plan 10-12)` and `### Data provenance and access risk (Phase 10)` sections; no prior content reflowed or altered

## Decisions Made

See `key-decisions` in frontmatter. Two verbatim human decisions this plan, not one: Task 1's "A" (go, all ten seasons) against the pre-acquisition evidence, and a second, plan-unanticipated decision "C" (drop the join, record as a defect) against evidence that only emerged from Task 2's own read-first investigation after the acquisition had already succeeded.

## Deviations from Plan

### Auto-fixed Issues

None -- no bugs, missing functionality, or blocking issues in code were found or fixed (no code was written this plan).

### Scope Change (human-directed, not a Rule 1-3 auto-fix)

**1. Task 2 executed as an investigation-then-decline rather than the planned reader/join implementation**
- **Found during:** Task 2's own `<read_first>` step, before any implementation code was written
- **Issue:** The plan's Task 2 assumed the acquired CSVs would contain `config.FBREF_COLS`'s three defensive-action columns (`Tkl+Int`, `Blocks`, `Clr`) once a Go/Partial decision authorised acquisition. Column-population analysis of the real acquired files found those three columns 100% empty in all 5,454 rows across all ten seasons -- a finding the plan's Task 1 checkpoint (which only weighed cost/benefit of *acquiring* the data) could not have anticipated, since it depends on the acquired data's actual content.
- **Resolution:** Presented the finding to the coordinator/human as a three-way choice (re-export / proceed with a reduced+renamed column set / drop and record as a defect) rather than guessing. Root-caused the finding first (ruled out an export-tool artifact via a live page screenshot and an incognito re-test) so the choice was made against a verified fact, not a hypothesis. Human selected "C" (drop, record as a defect).
- **Files affected:** `data/fbref.py`, `tests/test_leakage.py` -- neither was touched (the plan's `files_modified` listed both; this plan's actual `files_modified` is `IMPROVEMENTS.md`, `data/external/fbref/README.md`, and the ten CSVs).
- **Verification:** `git diff --stat data/fbref.py tests/test_leakage.py features/engineer.py` against the pre-plan commit is empty; `config.EXPERIMENTS['fbref_v2']` confirmed `False`.
- **Committed in:** `d466da9` (the CSV+README evidentiary commit) and `2828413` (the ledger entry recording both decisions and the finding).

---

**Total deviations:** 1 (a plan-unanticipated data-content finding requiring a second human decision, not a code bug)
**Impact on plan:** The plan's stated `must_haves.artifacts` entry "`data/fbref.py` — `load_manual_snapshot`" was not produced, because the human-directed outcome of the mid-plan finding was to drop the join entirely. This is a correct execution of the plan's own governing principle -- "a Drop is a decision with reasoning, never an unexplained absence" -- applied one step later than Task 1 anticipated, but applied faithfully: the decision is recorded with its reasoning (an acquisition-format defect, root-caused and evidenced) in both `data/external/fbref/README.md` and `IMPROVEMENTS.md`.

## Issues Encountered

- The RL note's citation (`Ng, Harada and Russell, 1999`) initially wrapped across a Markdown line break, splitting the literal substring `Ng, Harada and Russell` the Task 3 `<verify>` command checks for and causing a first-pass verify failure. Reflowed the paragraph so the citation stays on one line; re-ran the verify command, confirmed passing. No content change, formatting only.

## User Setup Required

None further -- the manual acquisition `user_setup` step (ten browser downloads) was already completed by the developer as part of Task 1's "A" decision, before Task 2 began.

## Next Phase Readiness

- **Both D-04 dead-tail items are closed** in `IMPROVEMENTS.md`'s `## Phase G` section: the FBref manual snapshot (acquired, then dropped on a verified acquisition-format defect) and the RL reward-shaping notes (recorded, no training).
- **`config.EXPERIMENTS['fbref_v2']` and `['rl_strategy']` both stay `False`** -- confirmed no default flipped anywhere this plan (`assert not any(config.EXPERIMENTS.values())` passes).
- **`optimize/rl_env.py` and `optimize/rl_train.py` are byte-identical to before this plan** (`git diff --stat` empty) -- the RL item stayed genuinely notes-only.
- **`data/fbref.py`, `config.FBREF_COLS`, and `features/engineer.py`'s FBref wiring are unchanged** -- the scrape-side path (`attach()`, `_NAME_FIXUPS`, `scrape_to_cache`) this plan's Task 2 would have extended is exactly as Phase 9 left it.
- **A permanent evidentiary snapshot exists at `data/external/fbref/`** (README + ten CSVs) for any future revisit to check against before re-attempting a manual acquisition.
- No blockers for plan 10-16 (the final combined close-out run) -- this was the last plan besides 10-16 in Phase 10's sequence, and both items it owned are closed with recorded reasoning either way.

## Self-Check: PASSED

- `data/external/fbref/README.md` and all ten `fbref_<season>_defense.csv` files -- FOUND (`ls data/external/fbref/`)
- Commits `d466da9`, `2828413` -- FOUND in `git log --oneline`
- `IMPROVEMENTS.md` contains `### fbref_v2: manual snapshot — acquisition decision and outcome` and `### RL reward shaping: potential-based only` -- FOUND
- `IMPROVEMENTS.md` contains `Ng, Harada and Russell`, `optimize/rl_env.py`, `log-linear`, `potential-based`, `fbrapi.com` -- FOUND
- `IMPROVEMENTS.md`'s RL subsection contains `skip`, `1e-6`, `weight 1`, `D-16` -- FOUND
- All five prior Phase F/G anchor headings intact (`### fbref_v2: real Chrome spike`, `### rl_strategy: time-boxed MaskablePPO policy`, `### Addendum (2026-09-10): rl_strategy v3`, `## Phase F`, `## Reference findings`) -- CONFIRMED
- `config.EXPERIMENTS['rl_strategy']` and `['fbref_v2']` both `False`; no flag anywhere `True` -- CONFIRMED
- `git diff --stat optimize/rl_env.py optimize/rl_train.py` against the pre-plan commit -- empty, CONFIRMED
- Re-ran `python -m pytest -q`: 328 passed, 1 pre-existing skip, 279.73s
- Re-ran `ruff check .`: all checks passed

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-11*
