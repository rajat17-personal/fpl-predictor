---
phase: quick-260909-elx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - config.py
  - backtest/walk_forward.py
  - backtest/benchmark_external.py
  - backtest/ep_next_provenance.py
  - tests/test_leakage.py
  - tests/test_experiments.py
  - IMPROVEMENTS.md
autonomous: true
requirements: [TODO-2026-09-09-ep-next-as-feature-minutes-signals]

estimate:
  tokens: 90000
  raw_tokens: 45000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A developer can read one section of IMPROVEMENTS.md and answer: does giving the xP model FPL's own ep_next figure close the played-only Spearman gap to it, and is that figure even safe to use?"
    - "The record states plainly that the todo's headline proposal — feed LAGGED ep_next — was already shipped before this task started (xp_fpl_r3/r5/r10/rall have been live model features via features/engineer.py ROLL_STATS), so the only genuinely new signals are the strict previous-fixture value and the same-fixture value."
    - "The decision-time provenance of same-fixture xp_fpl is settled by a measurement against a KNOWN-pre-deadline control (our own data/snapshots/*.parquet), not by assertion — and that verdict governs whether the same-fixture arm is adoptable at all."
    - "The availability half of the todo (chance_of_playing / status) is answered with the measured truth that no per-gameweek historical availability data exists anywhere in this repo, plus a dated forward path, rather than an invented feature."
    - "Every reported model+chips / multi_safe / Spearman delta is paired per season against a baseline measured on the SAME feature matrix, so no verdict rests on a published number today's pipeline can no longer reproduce."
    - "Nothing about the shipped product changed: every key in config.EXPERIMENTS is still False, and predict/, api/, web/, features/, data/ are untouched."
  artifacts:
    - backtest/ep_next_provenance.py
    - data/processed/experiments/ep_next_provenance.json
    - "data/processed/experiments/wf_ep_next_lag.csv and wf_ep_next_now.csv (tagged adoption runs)"
    - "data/processed/experiments/benchmark_ep_next_base.json, benchmark_ep_next_lag.json, benchmark_ep_next_now.json"
    - "IMPROVEMENTS.md '### Addendum (2026-09-09): ep_next as a model feature' section under Phase F"
  key_links:
    - "backtest.walk_forward.apply_experiment_feature_gating is the ONE place the flag acts — no features.parquet rebuild, no data/build_table.py change, exactly the ts_*/us_*/fm_* precedent"
    - "models.train._EXCLUDE keeps the literal xp_fpl out of feature_cols, so the flag must expose a DERIVED column under a new name; xp_fpl itself must stay in the frame because walk_forward and benchmark_external both score it as the FPL baseline"
    - "backtest.walk_forward._preds_for(df, T) is the ONLY prediction path for both the harness and the benchmark — never data/processed/test_predictions.parquet"
    - "data/snapshots/*.parquet is the only KNOWN-pre-deadline capture of FPL's ep_this/ep_next in this repo; data/raw/live/element_history.parquet supplies the realised minutes it is scored against"
---

<objective>
Settle whether feeding FPL's own expected-points figure (`xp_fpl`, i.e. its `ep_this` /
`ep_next` field) into the xP model closes the played-only ranking gap Phase 9 measured
(pooled Spearman 0.579 for FPL vs 0.383 for us), behind default-off flags, and record the
verdict as an IMPROVEMENTS.md Phase F addendum.

Purpose: Phase 9's external benchmark left this as its strongest measured lead. The todo
proposes exposing lagged `xp_fpl` plus availability signals as features and judging them
on the honest harness against the 2262 baseline with the >=2,280 D-05 bar and the D-07
mechanical verdict.

Output: `backtest/ep_next_provenance.py` (measurement-only), two default-off flags in
`config.EXPERIMENTS` with their single gating branch, a leakage regression test, tagged
adoption and benchmark runs, and an IMPROVEMENTS.md addendum inlining the decisive
numbers — the JSON/CSV artifacts live under gitignored `data/processed/`, so the
committed record must carry the numbers themselves (the 260909-5vx / 260909-dga
precedent).

Non-goal: this plan adopts nothing and flips no flag. Every key in `config.EXPERIMENTS`
stays `False` under EVERY outcome, including a positive one. If the numbers come out
pro-adoption, the addendum ends with a written case addressed to the user; adopting is
the user's decision, not this task's.
</objective>

<measured_facts>
Observations made at planning time by reading the code and querying the on-disk data.
Several of them redefine what this task must do versus what the todo proposed. Do not
re-derive them; verify them where a task says to.

**F1 — The todo's part (a) is already shipped, and its premise is half wrong.** The todo
and models/train.py:41 both say `xp_fpl` is "evaluation baseline only, not a feature".
That is true only of the LITERAL column. `features/engineer.py:39` lists `"xp_fpl"` in
`ROLL_STATS`, so `features.parquet` already carries `xp_fpl_r3`, `xp_fpl_r5`,
`xp_fpl_r10` and `xp_fpl_rall` (confirmed by reading the parquet's columns), and
`models.train._EXCLUDE` names only `xp_fpl` — so those four lagged rolling means have
been live model features all along. "Feed LAGGED ep_next" therefore needs no work. The
only genuinely new signals available are (i) the strict previous-fixture value (a
shift(1), not a rolling mean) and (ii) the SAME-FIXTURE value.

**F2 — `xp_fpl` is exactly FPL's bootstrap `ep_this`, captured per gameweek.**
`config.py:254` maps vaastav's `xP` column onto `xp_fpl`. Comparing `merged_gw.csv`'s
final-gameweek `xP` against the end-of-season `players_raw.csv` bootstrap: `xP == ep_this`
for **100.0%** of players in 2022-23, 2023-24 and 2024-25, while GW1's `xP` matches that
same end-of-season `ep_this` for only 11–14%. So it is a per-gameweek capture of the live
`ep_this` field, not a season constant and not a post-hoc recomputation.

**F3 — Coverage is structurally broken, in two different ways.**
  - `xp_fpl` is **100% null for 2016-17, 2017-18, 2018-19 and 2019-20** — four of the
    eight `config.TRAIN_SEASONS`.
  - Whole gameweeks are captured as identically `0.0` across every row (a source/scrape
    failure written as a zero, not a null). Count of such gameweeks per season —
    2020-21: 1, 2021-22: 0, 2022-23: 2, 2023-24: 1, 2024-25: 3, **2025-26: 27 of 38**.
    The most recent test season is therefore mostly a fabricated zero if used raw.

**F4 — The zero mass on surviving gameweeks is consistent with a genuine pre-deadline
capture, not with hindsight.** On non-outage gameweeks the historical column shows a
29–42% share of exactly-zero rows, and among those zero rows only 1.5–2.9% of players went
on to play. Read alone that looks like hindsight. It is not: our OWN
`data/snapshots/*.parquet`, captured live by the daily cron at a known `ts_utc` strictly
between gameweeks (2026-08-31, `next_gw=3`, `ts_utc` 12:37 UTC; 2026-09-07, `next_gw=4`,
06:19 UTC), show `ep_this` zero-shares of **0.431 and 0.408** with means 1.410 / 1.425 —
squarely inside the historical 0.295–0.417 band. FPL genuinely publishes ep 0.0 for
roughly 40% of its ~626-player list before a deadline (unavailable plus fringe players,
plus 1-decimal rounding of anything under 0.05). `ep_this` and `ep_next` are near
identical in both snapshots (zero-shares 0.431/0.430 and 0.408/0.407), so between
gameweeks FPL serves essentially one figure under both names.

**F5 — The decisive provenance test is available and cheap, and Task 1 must run it.**
F4 settles the zero SHARE but not `P(played | ep == 0)`, which is the statistic that would
actually expose hindsight. That statistic can be computed on a KNOWN-pre-deadline capture
using only in-repo artifacts: join each snapshot's zero-`ep_this` rows (keyed by its own
`next_gw`) to that gameweek's realised minutes in
`data/raw/live/element_history.parquet` (1,890 rows, per-gameweek 2026-27 self-hosted
capture, carrying `player_id`, `gw`, `minutes`). If the known-pre-deadline
`P(played | ep == 0)` lands near the historical 1.5–2.9%, the historical column is
exonerated. If it is materially higher, the historical column carries hindsight and the
same-fixture arm is unadoptable whatever it scores.

**F6 — The availability half of the todo is not measurable, because the data does not
exist.** `chance_of_playing_this_round`, `chance_of_playing_next_round`, `status` and
`news` appear ONLY in `players_raw.csv`, which is a single end-of-season snapshot: rows ==
unique ids (713 for 2020-21, 865 for 2023-24, 841 for 2025-26). There is no per-gameweek
availability anywhere — not in `merged_gw.csv` (36 / 41 / 46 columns across the seasons
checked, none availability), not in the self-hosted
`data/raw/live/element_history.parquet` (21 columns, none availability). Using the
season-final value per gameweek would apply an end-of-season injury flag to every gameweek
of that season. This is the "missing information" constraint, not a difficulty judgement.
The forward path exists and has already started: `data/snapshots/*.parquet` carries
`status`, `chance_of_playing_next_round`, `ep_this`, `ep_next`, `next_gw` and `ts_utc` per
day from 2026-08-31 onward (2 files so far).

**F7 — The published benchmark numbers cannot be reproduced today, so the re-score must
carry its own baseline.** `backtest.benchmark_external.score()` calls
`models.train.load_features()` and goes straight to `_preds_for` — it never calls
`apply_experiment_feature_gating`, so it scores whatever columns `features.parquet`
happens to hold. `benchmark_phase9.json` is dated 2026-09-08 08:12, while
`understat.parquet` (15:14), `fotmob.parquet` (21:59) and the `features.parquet` rebuild
(22:04) are all LATER the same day. The published pooled `xp_med` Spearman 0.383 was
measured on a smaller feature matrix than exists now. Any re-score must produce a fresh
all-flags-off baseline in the same run and compare against that, never against 0.383.

**F8 — The harness baseline this task is judged against.**
`data/processed/experiments/wf_baseline_phase9.csv` (all flags off, replicas=5):

| season | model+chips | multi_safe |
|---|---:|---:|
| 2020-21 | 2091 | 1967 |
| 2021-22 | 2305 | 2312 |
| 2022-23 | 2380 | 2269 |
| 2023-24 | 2210 | 2146 |
| 2024-25 | 2417 | 2101 |
| 2025-26 | 2172 | 2086 |
| **mean** | **2262** | **2147** |

D-05 adoption bar: model+chips >= 2,280. D-07 mechanical verdict: model+chips improves
AND multi_safe holds.

**F9 — Where the flag can act.** `apply_experiment_feature_gating`
(backtest/walk_forward.py:130) is called exactly once per harness run
(walk_forward.py:287) and is the single feature-selection gate. `xp_fpl` IS present in the
frame `load_features()` returns, but `models.train._EXCLUDE` keeps that literal name out
of `feature_cols`, and it must stay excluded because walk_forward and benchmark_external
both score it as the FPL baseline. So the gate must ADD a derived column under a new name
rather than drop one — the first branch in this function that adds instead of drops.
`tests/test_experiments.py:29` asserts `set(config.EXPERIMENTS) == _EXPERIMENT_KEYS`, so
that literal set must be updated when keys are added.

**F10 — Environment.** 28 cores, load average 3.09. Three `optimize.rl_train` processes
alive (PIDs 802368 / 802371 / 802374, plus their three wrapper bash scripts) — leave them
alone, and launch no GPU work. `/usr/bin/taskset` is present. The working tree is clean
apart from untracked files, so `git diff --quiet` gates are usable. `data/processed/` is
gitignored, so no artifact under it is committed.
</measured_facts>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/todos/pending/2026-09-09-ep-next-as-feature-minutes-signals.md
@backtest/walk_forward.py
@backtest/benchmark_external.py
@features/engineer.py
@models/train.py
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Provenance verdict, default-off flags, and one season end to end</name>
  <files>backtest/ep_next_provenance.py, config.py, backtest/walk_forward.py, tests/test_leakage.py, tests/test_experiments.py</files>
  <read_first>
    backtest/enrichment_slices.py and backtest/capt_ceiling_ci.py — the 260909-5vx and
    260909-dga precedents for a measurement-only module under backtest/: how each reuses
    `_preds_for` and `apply_experiment_feature_gating`, its per-season parquet caching
    under `config.EXPERIMENTS_DIR`, its `--seasons` CLI shape, and its
    `ops.jsonio.write_json` output convention. Follow them rather than inventing a third
    style. `capt_ceiling_ci.py` also owns the paired-interval helpers Task 2 reuses — read
    their signatures now.
    backtest/walk_forward.py lines 130-157 — `apply_experiment_feature_gating`'s current
    drop-only body and its docstring contract, which this task extends.
    features/engineer.py lines 29-43 and 61-68 — `ROLL_STATS` (which already contains
    xp_fpl, per F1) and `_roll`'s shift-then-roll ordering, which the new previous-fixture
    column must match exactly.
    tests/test_leakage.py lines 94-146 — `test_understat_features_are_rolled_not_raw` and
    its fotmob twin: the recompute-and-compare template the new leakage test mirrors.
  </read_first>
  <behavior>
    Tests written before the code they cover.

    In tests/test_experiments.py, pure-function tests of the gating branch (build small
    in-memory frames; do not read parquet):
    - Flags off: the returned frame is column-identical to the input and carries neither
      derived column. Assert equality of the column list, not merely absence.
    - Previous-fixture flag on: the derived lag column appears, and for a two-player,
      four-fixture, kickoff-ordered frame its values equal each player's own prior-fixture
      xp_fpl, with each season's first appearance null. Players must not bleed into each
      other and seasons must not bleed into each other.
    - Outage masking: for a gameweek where every row's xp_fpl is 0.0, both derived columns
      are null for that gameweek rather than 0.0 — and a gameweek with a genuine mixture
      of zero and non-zero rows is NOT masked. Assert both halves; the second is what
      stops the mask eating F4's legitimate 40% zero mass.
    - Masking precedes lagging: a fixture whose previous fixture fell in an outage
      gameweek gets a null lag value, not 0.0.
    - The literal xp_fpl column survives gating unchanged under every flag combination
      (walk_forward and benchmark_external both still score it as the FPL baseline).
    - Registry: every key in config.EXPERIMENTS is False, and both new keys are present in
      the module's asserted key set.

    In tests/test_leakage.py, a decision-time test in the style of its understat/fotmob
    neighbours, skipped if features.parquet is absent: gate a real slice of the feature
    frame with the previous-fixture flag on, pick the most-frequent player of a season
    with intact coverage (2023-24 — F3 shows 2025-26 is 27/38 outage), and assert the
    derived lag column equals an independent kickoff-ordered shift of that player's masked
    xp_fpl. Also assert the same-fixture derived column is absent unless its own flag is
    on.
  </behavior>
  <action>
    Three pieces, in this order.

    (1) `backtest/ep_next_provenance.py`, a measurement-only module — it never trains,
    never writes into models/artifacts/, never mutates committed data. It answers one
    question: is the same-fixture xp_fpl decision-time-known? Report to stdout and write
    `config.EXPERIMENTS_DIR / "ep_next_provenance.json"` via `ops.jsonio.write_json`,
    containing:
      - Coverage census per season from player_gw.parquet: null share, the list of
        gameweeks where xp_fpl is 0.0 for every row, and the zero-share over the remaining
        gameweeks. Verify F3's counts (four fully-null seasons; 1/0/2/1/3/27 outage
        gameweeks) and record any disagreement rather than silently proceeding.
      - Historical conditional stats on non-outage gameweeks only, per season and pooled:
        P(played | xp_fpl == 0), P(xp_fpl == 0 | did not play), P(xp_fpl == 0 | played).
      - THE CONTROL, per F5. For each file in `data/snapshots/*.parquet`, take its
        `next_gw` and `ts_utc`, join its rows to that gameweek's realised minutes from
        `data/raw/live/element_history.parquet` on player_id, and compute the same
        P(played | ep_this == 0) on this known-pre-deadline capture, with n and a binomial
        confidence interval. Record `ts_utc` and `next_gw` beside each estimate so a
        reader can confirm the capture really preceded the deadline. If a snapshot's
        gameweek has no realised minutes yet, report it as uncovered rather than counting
        it.
      - A verdict block: whether the control's interval overlaps the historical pooled
        estimate, plus a boolean the addendum can quote. Keep this honest about its own
        power — two snapshots is a small control, so state n rather than implying more.

    (2) Two default-off flags in `config.EXPERIMENTS`, following the ts_*/us_*/fm_*
    precedent: one exposing the strict previous-fixture value and one exposing the
    same-fixture value. Keep them orthogonal and additive; both default False. Update
    tests/test_experiments.py's asserted key set (F9). Add a short comment block near
    EXPERIMENTS, in the style of the UNDERSTAT_COLS / FOTMOB_COLS notes, recording that
    the lagged ROLLING means already reach the model via ROLL_STATS (F1) so these flags
    cover only the two signals that were genuinely unavailable, and that the same-fixture
    flag is provenance-conditional on the module from piece (1).

    Then add the gating branch to `apply_experiment_feature_gating`. It stays the single
    feature-selection gate, but this is its first branch that adds a column rather than
    dropping one — update its docstring to say so and to say why (F9: the literal xp_fpl
    must stay both excluded from feature_cols and present in the frame as the scored FPL
    baseline). Requirements:
      - Build a masked series first: null out xp_fpl for every (season, gw) where it is
        0.0 or null across every row. Everything downstream derives from the masked
        series, so an outage gameweek can never enter the model as a confident zero.
      - The previous-fixture flag adds a column from a (season, player_id) grouping
        ordered by kickoff_time, shifted by one — the same ordering features/engineer.py
        uses. Return the frame in its original row order.
      - The same-fixture flag adds a column equal to the masked series.
      - With both flags off the returned frame must be unchanged, so an unflagged harness
        run still reproduces F8's baseline exactly.
      - Name the derived columns so `models.train.feature_cols` picks them up
        automatically and `_EXCLUDE` needs no edit. Do not edit models/train.py.

    (3) The tracer run: one season end to end through every layer this task touches —
    config flag, gating, `_preds_for` training on a frame that now contains the derived
    column, `run_season`, tagged CSV on disk. Use 2025-26 at one replica, deliberately: it
    is the worst-coverage season (F3), so it exercises the masking path hardest. Pin with
    `taskset -c 0-17` per F10, leave the rl_train processes alone, launch no GPU work. If
    the run needs backgrounding, detach it with a timestamped log under
    `data/processed/experiments/` and poll with a hard iteration cap — never an unbounded
    monitor.

    Do not run the full six-season comparison here; that is Task 2.
  </action>
  <verify>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_experiments.py tests/test_leakage.py -x -q</automated>
    <automated>taskset -c 0-17 /home/sraja/miniconda3/envs/python314/bin/python -m backtest.ep_next_provenance 2>&1 | tail -30</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "import json,pathlib,config; d=json.loads(pathlib.Path(config.EXPERIMENTS_DIR/'ep_next_provenance.json').read_text()); c=d['coverage']; assert len(c['2025-26']['outage_gws'])==27, c['2025-26']; assert c['2016-17']['null_share']==1.0, c['2016-17']; print('verdict:', d['verdict']); print('control:', d['control'])"</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "
import pandas as pd, config
from models.train import load_features, feature_cols
from backtest.walk_forward import apply_experiment_feature_gating as gate
df = load_features()
off = gate(df, {})
assert list(off.columns) == list(df.columns), 'flags-off changed the frame'
on = gate(df, {k: True for k in config.EXPERIMENTS})
new = [c for c in on.columns if c not in df.columns]
assert len(new) == 2, new
assert 'xp_fpl' in on.columns, 'FPL baseline column was consumed by the gate'
assert set(new) <= set(feature_cols(on)), 'derived columns are not reaching feature_cols'
assert not set(new) & set(feature_cols(off)), 'derived columns leak when flags are off'
print('gate adds', new, '| feature count off/on:', len(feature_cols(off)), len(feature_cols(on)))"</automated>
  </verify>
  <done>
    The unit and leakage tests pass. `ep_next_provenance.json` exists with the coverage
    census reproducing F3's outage counts, the historical conditional stats, and the
    known-pre-deadline control with its n, interval, `ts_utc` and `next_gw`, plus a stated
    verdict on whether same-fixture xp_fpl behaves like a pre-deadline capture. Both new
    flags exist and are False. The gate is a no-op with flags off and adds exactly two
    columns with flags on, both reaching `feature_cols` while `xp_fpl` itself survives
    untouched. A tagged single-season 2025-26 run is on disk, proving the flag trains and
    scores end to end on the worst-coverage season. All three rl_train processes are still
    alive.
  </done>
</task>

<task type="auto">
  <name>Task 2: Six-season adoption measurement and the gated benchmark re-score</name>
  <files>backtest/benchmark_external.py, tests/test_experiments.py</files>
  <read_first>
    backtest/benchmark_external.py lines 249-315 — `score()` and `main()`, where the
    `--experiments` option and the gating call must land (F7).
    backtest/capt_ceiling_ci.py — its paired-t interval helper and its output JSON shape.
    Reuse the helper; do not reimplement a second paired interval in this repo.
  </read_first>
  <action>
    Two measurements plus one small code change. Every harness invocation pinned with
    `taskset -c 0-17` per F10, launched detached with output to a timestamped log under
    `data/processed/experiments/`, polled with a hard iteration cap and never an unbounded
    monitor. Do not disturb the three rl_train processes and launch no GPU work. If a poll
    budget expires with a run still alive, report the log tail and keep polling in a fresh
    bounded loop — do not assume failure and do not relaunch a live run.

    (a) Adoption runs, six seasons, harness defaults (five replicas), against F8's
    baseline. Two arms:
      - previous-fixture flag only — the arm that is adoptable regardless of Task 1's
        provenance verdict, because a strict shift is decision-time-known by construction.
      - previous-fixture plus same-fixture flags — the upper-bound arm.
    Write each to its own `--tag`. Then compute, reusing capt_ceiling_ci's helper, the
    per-season paired deltas and a paired two-sided 95% t interval at n=6 for model+chips
    and multi_safe, each arm against F8's baseline rows. State the resampling unit
    (season) in the output, as the 5vx/dga addenda do.

    Report the D-07 mechanical verdict per arm against the pre-declared criteria: the
    >=2,280 D-05 bar on mean model+chips, and multi_safe holding against 2147. Apply the
    rule mechanically; do not soften a miss or hunt for a slice that passes.

    (b) The EXP-1 style re-score. Add an `--experiments` option to
    `backtest/benchmark_external.py` that resolves flags with `config.resolve_experiments`
    and passes the frame through `apply_experiment_feature_gating` before
    `_our_preds_gw_level` — closing the F7 gap that the benchmark has never gated at all.
    Keep the default (no flag) behaviour identical to today's so the change is additive.
    Then run three scores, each with its own `--tag`: an all-flags-off fresh baseline, the
    previous-fixture arm, and the previous-fixture-plus-same-fixture arm. All three read
    the same committed theFPLkiwi snapshot and score the same two seasons the module
    already selects.

    The comparison that matters is within-run: does our pooled played-only Spearman move
    toward the `xp_fpl` figure measured in the SAME run? Per F7 the published 0.383 and
    0.579 are not reproducible today, so record the fresh baseline's own numbers and treat
    those as the reference; note the discrepancy against the published pair explicitly
    rather than quietly substituting one for the other.

    Add one regression test to tests/test_experiments.py pinning the new benchmark option:
    with no flags the resolved experiment dict is all-False, so the default scoring path is
    unchanged.

    If a season fails to train, record which and why in the SUMMARY and let the rest
    complete — a five-season interval clearly labelled as such is usable, a silently
    truncated six-season claim is not.
  </action>
  <verify>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "
import pandas as pd, config
E = config.EXPERIMENTS_DIR
base = pd.read_csv(E/'wf_baseline_phase9.csv').set_index('season')
for tag in ['ep_next_lag','ep_next_now']:
    a = pd.read_csv(E/f'wf_{tag}.csv').set_index('season')
    assert len(a) >= 5, (tag, len(a))
    common = base.index.intersection(a.index)
    for col in ['model+chips','multi_safe']:
        d = (a.loc[common, col] - base.loc[common, col])
        print(tag, col, 'arm mean=%.1f base mean=%.1f delta mean=%+.1f per-season=%s'
              % (a.loc[common,col].mean(), base.loc[common,col].mean(), d.mean(), list(d)))"</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "
import json, pathlib, config
for tag in ['ep_next_base','ep_next_lag','ep_next_now']:
    d = json.loads(pathlib.Path(config.EXPERIMENTS_DIR/f'benchmark_{tag}.json').read_text())
    p = d['pooled']
    print(tag, 'n=%d' % p['n_rows'],
          'spearman xp_med=%.4f xp_mean=%.4f xp_fpl=%.4f'
          % (p['spearman_xp_med'], p['spearman_xp_mean'], p['spearman_xp_fpl']))"</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_experiments.py -x -q</automated>
    <automated>ps -p 802368,802371,802374 -o pid=,comm= && echo "rl_train processes intact"</automated>
  </verify>
  <done>
    Both tagged six-season adoption CSVs are on disk covering at least five seasons each,
    with per-season paired deltas and season-clustered 95% intervals computed against F8's
    baseline for model+chips and multi_safe, and a mechanical D-05/D-07 verdict recorded
    per arm. `benchmark_external.py` accepts an experiments option, defaults to today's
    ungated behaviour, and three tagged benchmark JSONs exist — a fresh all-off baseline
    plus both arms — so the played-only Spearman movement is read within-run rather than
    against the unreproducible published 0.383/0.579. Every run was pinned with
    `taskset -c 0-17` and all three rl_train processes survived.
  </done>
</task>

<task type="auto">
  <name>Task 3: Record the Phase F addendum and guard the untouched flags</name>
  <files>IMPROVEMENTS.md, tests/test_experiments.py</files>
  <read_first>
    IMPROVEMENTS.md line 989 onward — the 260909-5vx addendum — and line 1102 onward — the
    260909-dga addendum. Match their style: inlined markdown tables carrying the numbers
    themselves, a plainly stated verdict, a caveats paragraph on what the measurement does
    and does not license, and a closing tie-back to the phase's own recorded open weakness.
    IMPROVEMENTS.md line 172 onward — the benchmark section whose 0.383 / 0.579 reading
    this addendum revisits — and line 899 onward, 'What this phase did not resolve'.
  </read_first>
  <action>
    Add a new section to IMPROVEMENTS.md under Phase F, after the dga addendum, titled as a
    2026-09-09 addendum on ep_next as a model feature and naming the benchmark section it
    extends. Because data/processed/ is gitignored (F10), inline every decisive number — a
    reader with no access to the JSON or CSVs must be able to check the verdict.

    Cover, in this order:
      1. The correction to the todo's own premise (F1): the lagged rolling means of
         FPL's expected points have been live model features via ROLL_STATS all along, so
         "feed lagged ep_next" was already shipped. Name the four columns. State that this
         reframes the experiment onto the two signals that genuinely were unavailable.
      2. What the column actually is and how good the data is: F2's exact-match evidence
         that it is FPL's per-gameweek `ep_this`, then F3's coverage census — four fully
         null training seasons and the per-season outage-gameweek counts, with 2025-26 at
         27 of 38 called out as the headline coverage problem. Explain the masking rule the
         gate applies and why an outage zero is more dangerous than a null.
      3. The provenance verdict from Task 1, with the historical conditional stats beside
         the known-pre-deadline control from our own snapshots (n, interval, `ts_utc`,
         `next_gw`), and a plain statement of what it licenses. If the control exonerates
         the column, say so and say the same-fixture arm is a legitimate reading; if it
         does not, say the same-fixture arm is a diagnostic upper bound that must never be
         adopted whatever it scored.
      4. The adoption table: per-season model+chips and multi_safe for the baseline and
         both arms, then mean deltas with season-clustered 95% intervals, then the
         mechanical D-05/D-07 verdict per arm.
      5. The benchmark re-score: the fresh all-off baseline's pooled played-only Spearman
         beside both arms and beside `xp_fpl`'s own figure from the same run — the direct
         answer to whether the ranking gap closes. Record F7 explicitly: the published
         0.383/0.579 predate the understat/fotmob feature-matrix rebuild and are not
         reproducible, so this addendum's baseline supersedes them for comparison
         purposes. Note the phase's known trap by name — a feature can improve
         fixture-level MAE or Spearman while season points stay inside the noise band —
         and state which side of it this result landed on.
      6. The availability half, scoped down honestly per F6. State the measured fact that
         per-gameweek availability does not exist in this repo for any past season, name
         the three artifacts checked and what each does and does not carry, and state that
         this is missing data rather than a judgement about difficulty. Then give the dated
         forward path: `data/snapshots/*.parquet` has captured status,
         chance_of_playing_next_round, ep_this, ep_next, next_gw and ts_utc daily since
         2026-08-31, so roughly one 2026-27 season of accumulation makes a per-gameweek
         availability panel constructible, and the daily cron is the thing that must keep
         running for that to happen. Do not invent a feature or a number for this half.
      7. The caveats and the closing tie-back: the season-clustered intervals are the
         governing family at n=6, the benchmark scores only the two seasons theFPLkiwi
         covers, and this is the third instalment on the 'What this phase did not resolve'
         gap after 5vx and dga.

    Then branch on the season-clustered model+chips result, and make the branch explicit in
    both the addendum and the SUMMARY:
      - If an arm clears the >=2,280 D-05 bar with multi_safe holding, AND that arm is
        provenance-clean per Task 1: close with a clearly-headed block presenting the case
        for adoption, addressed to the user as their decision, stating what flipping the
        flag would change downstream.
      - Otherwise: record the rejection mechanically against the pre-declared bar, in the
        style of the phase's other REJECTED entries.
    Under EITHER branch every key in `config.EXPERIMENTS` stays False.

    Add one regression test to tests/test_experiments.py asserting both new flags are
    False, so a future change that silently adopts either fails a test rather than shipping
    quietly.

    Move the todo file out of `.planning/todos/pending/` to whatever completed location
    this repo's convention uses; if no such convention exists, leave it and say so in the
    SUMMARY.
  </action>
  <verify>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_experiments.py tests/test_leakage.py tests/test_legality.py -q</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "import config; assert not any(config.EXPERIMENTS.values()), config.EXPERIMENTS; print('all experiment flags off:', sorted(config.EXPERIMENTS))"</automated>
    <automated>test -z "$(git status --porcelain -- predict api web features data)" && echo "no product surface touched"</automated>
    <automated>taskset -c 0-17 /home/sraja/miniconda3/envs/python314/bin/python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag elx_default_check 2>&1 | tail -15</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "
import pandas as pd, config
a = pd.read_csv(config.EXPERIMENTS_DIR/'wf_elx_default_check.csv').set_index('season').loc['2025-26']
b = pd.read_csv(config.EXPERIMENTS_DIR/'wf_baseline_phase9.csv').set_index('season').loc['2025-26']
for col in ['model+chips','multi_safe','capt_capture']:
    assert a[col] == b[col], (col, a[col], b[col])
print('unflagged run still reproduces the phase-9 baseline row exactly')"</automated>
  </verify>
  <done>
    IMPROVEMENTS.md carries a Phase F addendum whose inlined tables let a reader check
    every verdict without the gitignored artifacts, covering all seven required points —
    including the F1 correction to the todo's premise, the provenance verdict with its
    known-pre-deadline control, the coverage census, the within-run benchmark comparison
    with F7 stated, the honestly scoped-down availability half with its dated forward path,
    and the explicit branch taken. Both new flags are asserted False by a test, an
    unflagged single-season run still reproduces the phase-9 baseline row exactly, no file
    under predict/, api/, web/, features/ or data/ is modified, and the leakage and
    legality suites still pass.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| historical source data -> model features | vaastav's `xP` column is a third-party per-gameweek capture whose exact capture time is unverifiable; if it carries hindsight, every downstream number in this task is fiction |
| measurement -> shipped default | config.EXPERIMENTS is the single switch between a measurement and a product change |
| repo -> committed record | IMPROVEMENTS.md becomes the permanent citable verdict; a number not checkable from committed text is unfalsifiable once data/processed/ is cleared |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-elx-01 | Tampering | same-fixture xp_fpl as a model feature | critical | mitigate | Task 1's provenance module scores P(played given ep==0) against a KNOWN-pre-deadline control from our own snapshots before any adoption reading is trusted; Task 3 must state the verdict and mark the arm a diagnostic upper bound if the control fails |
| T-elx-02 | Spoofing | outage gameweeks written as 0.0 | high | mitigate | The gate masks any gameweek whose xp_fpl is 0.0 across every row to null before deriving either column, with a unit test proving a mixed-zero gameweek is NOT masked; 2025-26's 27 outage gameweeks are named in the addendum |
| T-elx-03 | Tampering | config.EXPERIMENTS defaults | high | mitigate | Task 3 asserts every key is False and re-runs an unflagged season proving it reproduces the phase-9 baseline row exactly; a new test pins both added flags off |
| T-elx-04 | Repudiation | the verdict itself | medium | mitigate | Every delta is paired per season against a baseline measured on the same feature matrix; F7's unreproducible published numbers are called out rather than silently substituted; resampling unit recorded with each interval |
| T-elx-05 | Denial of service | host CPU shared with 3 live rl_train processes | medium | mitigate | Every harness invocation pinned with `taskset -c 0-17` of 28 cores, launched detached and polled with a hard iteration cap; no GPU work; rl_train PIDs re-checked in Task 2's verify |
| T-elx-06 | Information disclosure | IMPROVEMENTS.md addendum | low | mitigate | Numbers only, no paths outside the repo and no personal identifiers (the Phase 05-04 precedent) |
| T-elx-SC | Tampering | npm/pip/cargo installs | high | mitigate | No packages installed — pandas/numpy/scipy/pytest are already project dependencies, so the package-legitimacy gate has no surface here |
</threat_model>

<verification>
- The provenance control ran and is reported with its n, interval, `ts_utc` and `next_gw`,
  and its verdict governs how the same-fixture arm is characterised in the addendum.
- The gate is a proven no-op with flags off: an unflagged 2025-26 run reproduces
  wf_baseline_phase9.csv's row exactly on model+chips, multi_safe and capt_capture.
- Outage masking is tested in both directions — an all-zero gameweek is masked, a
  mixed-zero gameweek is not.
- Both adoption arms are judged mechanically against the pre-declared >=2,280 D-05 bar and
  the D-07 multi_safe condition, with season-clustered intervals.
- The benchmark re-score carries its own all-off baseline and states F7 rather than
  comparing against the unreproducible published 0.383/0.579.
- The availability half is recorded as measured-absent with a dated forward path, not
  invented.
- Every key in config.EXPERIMENTS is False; predict/, api/, web/, features/ and data/ are
  unmodified; leakage and legality suites pass.
- All three optimize.rl_train processes survived the task.
</verification>

<success_criteria>
A developer reading IMPROVEMENTS.md can answer, from inlined numbers alone: whether FPL's
own expected-points figure is safe to feed the model, whether feeding it closes the
played-only ranking gap, whether it moves season points past the pre-declared bar, and why
the availability half of the idea could not be measured at all. Nothing about the shipped
product changed.
</success_criteria>

<output>
Create `.planning/quick/260909-elx-experiment-feed-lagged-ep-next-xp-fpl-av/260909-elx-SUMMARY.md` when done
</output>
