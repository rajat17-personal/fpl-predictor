---
phase: quick-260909-dga
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backtest/capt_ceiling_ci.py
  - tests/test_experiments.py
  - IMPROVEMENTS.md
autonomous: true
requirements: [TODO-2026-09-09-capt-ceiling-high-replica-rerun]

estimate:
  tokens: 70000
  raw_tokens: 35000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A developer can read one section of IMPROVEMENTS.md and answer: is capt_ceiling's +1.5pt capture reading real, or is it inside its own measurement noise?"
    - "Every reported capt_capture / model+chips / capt_mean delta carries a paired 95% interval computed from a stated resampling unit, so the verdict no longer rests on eyeballing a delta against an informally estimated SE (the exact weakness IMPROVEMENTS.md's 'What this phase did not resolve' section records)."
    - "The record states, with an empirical demonstration and not only a code-reading argument, whether raising --replicas can move capt_capture or model+chips at all."
    - "The re-measurement reproduces plan 09-03's published per-season numbers from wf_baseline_phase9.csv and wf_capt_ceiling_adopt.csv, or states in writing why it does not."
    - "Nothing about the shipped product changed: config.EXPERIMENTS['capt_ceiling'] is still False, config.py is byte-unchanged, and predict/, api/, web/, features/, data/ are untouched."
  artifacts:
    - backtest/capt_ceiling_ci.py
    - data/processed/experiments/capt_ceiling_ci.json
    - "data/processed/experiments/capt_ci_te_{season}.parquet (6 prediction cache files)"
    - "IMPROVEMENTS.md '### Addendum (2026-09-09): capt_ceiling paired intervals' section under Phase F"
  key_links:
    - "backtest.walk_forward._preds_for(df, T) is the ONLY prediction path — the same leakage-safe train/val/test split the real harness uses, never data/processed/test_predictions.parquet"
    - "models.captaincy.fit_ceiling_artifact(models, df, val_season, cols) is fit on DATA_SEASONS[index(T)-1], never the shipped 2025-26 intervals artifact (the 09-01 leakage rule)"
    - "backtest.season.run_season(..., capt_col=X) is the ONLY difference between the two arms — one shared `te` per season feeds both, because capt_ceiling gates no features"
    - "capt_capture is a RATIO OF SUMS (sum(capt_pts)/sum(best_pts), backtest/season.py:317), so every interval must resample and recompute the ratio, never average per-gameweek ratios"
---

<objective>
Settle whether capt_ceiling's +1.5pt capture reading (0.563→0.578) is a real effect or
measurement noise, by attaching proper paired confidence intervals to the adoption
comparison, and record the verdict as an IMPROVEMENTS.md Phase F addendum.

Purpose: Phase 9 REJECTED capt_ceiling on a +1.5pt capture delta against a ≥+2pt bar
(D-06), with model+chips +16 (2262→2278) alongside. Both readings were eyeballed
against an informally estimated SE≈16. The user wants this settled under Phase 9's own
ledger before capt_mc (models/simulate.py, still unbuilt) is gated on it permanently.

Output: `backtest/capt_ceiling_ci.py` (a reusable, cached, measurement-only module),
`data/processed/experiments/capt_ceiling_ci.json`, and an IMPROVEMENTS.md addendum
inlining the decisive numbers (the JSON lives under gitignored `data/processed/`, so
the committed record must carry the numbers themselves — the 260909-5vx precedent).

Non-goal: this plan adopts nothing and flips no flag. `config.EXPERIMENTS['capt_ceiling']`
stays `False` under EVERY outcome — including a positive one. If the intervals come out
pro-adoption, the addendum ends with a written case for the user to revise the D-06 bar;
revising the bar is the user's decision, not this task's.
</objective>

<measured_facts>
Observations made at planning time by reading the code and the on-disk Phase 9 results.
These are load-bearing: they redefine what this task must do versus what the todo
proposed. Do not re-derive them; verify them where a task says to.

**F1 — The todo's proposed method cannot work.** `--replicas` (walk_forward.py:241,
default 5) feeds exactly one thing: the `totals` list comprehension at
walk_forward.py:298-300, which produces `model_mean` and `model_std`. Every metric
`capt_ceiling` is capable of moving is computed from a SINGLE, UNJITTERED `run_season`
call:
  - `model+chips` ← `chips_df`, walk_forward.py:302-304 (one call, no jitter)
  - `capt_mean`, `capt_capture` ← `cdf`, walk_forward.py:306-308 (one call, no jitter)
`capt_col_active` (walk_forward.py:270) is passed only to those two calls. Therefore
re-running at `--replicas 25` produces byte-identical `capt_capture` and `model+chips`
to the `--replicas 5` run already on disk. A 25×2-arm re-run would burn ~50-70 min to
reprint the same two numbers.

**F2 — F1 is already corroborated on disk.** Comparing the two committed Phase 9 result
CSVs row-for-row:
  - `data/processed/experiments/wf_baseline_phase9.csv` (all flags off, replicas=5)
  - `data/processed/experiments/wf_capt_ceiling_adopt.csv` (capt_ceiling, replicas=5)
their `model_mean`, `model_std`, `multi_safe`, `form`, `hold` columns are identical in
all six seasons (2074/2119/2148/2191/2137/2122 etc.) — `capt_ceiling` cannot touch them.
Separately, `wf_capt_lam_0.0.json` was run at `replicas=1` and reports the same
`multi_safe` 2147 / `form` 2032 / `hold` 1729 as the `replicas=5` runs, while its
`model_mean` (2107) and `model_std` (59) differ from theirs (2132/38) — replicas move
the jittered columns and nothing else.

**F3 — The per-season paired deltas are already computable, and are not significant.**
From the two CSVs above (capt_ceiling minus baseline, per season):
  - `capt_capture`: [+0.026, −0.014, −0.012, +0.008, +0.056, +0.024]
  - `model+chips` : [+56, −28, −30, −8, −18, +121]
  - `capt_mean`   : [+47, −82, −76, +4, +29, +11]
Paired two-sided t intervals at n=6 seasons (computed at planning time, to be
reproduced by the module):
  | metric | mean Δ | SE | 95% CI | excludes 0 |
  |---|---:|---:|---|---|
  | capt_capture | +0.0147 | 0.0108 | [−0.0131, +0.0424] | no |
  | model+chips  | +15.5   | 24.77  | [−48.2, +79.2]     | no |
  | capt_mean    | −11.2   | 22.32  | [−68.5, +46.2]     | no |
Note `capt_mean` — the captaincy arm's own season points — is NEGATIVE in the mean.

**F4 — Per-gameweek detail exists in memory but is discarded.** `run_season`'s returned
log carries one row per gameweek with `gw`, `points`, `capt_pts`, `best_pts`
(backtest/season.py:220-223 for the opening gameweek, 282-285 for the rest).
walk_forward.py:308 collapses it to a single ratio and walk_forward.py:317 rounds that
to 3 decimals before it reaches the CSV — a ~1.5% relative rounding error on a ~0.015
effect. Recovering the unrounded per-gameweek rows is what makes a higher-n interval
possible at all.

**F5 — The pairing is tight but not squad-identical.** `capt_col` reaches the ILP as
the `xp_capt` column (optimize/squad_ilp.py:42) and is consumed in the objective
(optimize/squad_ilp.py:63), so the two arms select DIFFERENT squads, not merely a
different armband on one squad. The pairing unit is therefore (season, gameweek), not
(season, gameweek, squad). Say so in the addendum; do not overclaim.

**F6 — One `te` per season serves both arms.** `capt_ceiling` gates no features, so
`apply_experiment_feature_gating` returns the same frame either way, and the ceiling
column is added on top of the same predictions (walk_forward.py:291-296). The module
must exploit this: train once per season, run both arms off the shared frame. Training
is the expensive step; the arm runs are cheap.

**F7 — Environment.** 28 cores, load average 3.0, three `optimize.rl_train` processes
alive (PIDs 802368/802371/802374) — leave them alone. `/usr/bin/taskset` is present.
`data/processed/` is gitignored, so no result artifact under it is committed.
</measured_facts>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/todos/pending/2026-09-09-capt-ceiling-high-replica-rerun.md
@backtest/walk_forward.py
@backtest/season.py
@backtest/enrichment_slices.py
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: End-to-end paired-interval measurement on one season</name>
  <files>backtest/capt_ceiling_ci.py, tests/test_experiments.py</files>
  <read_first>
    backtest/enrichment_slices.py — the 260909-5vx precedent for a measurement-only
    module in backtest/: how it reuses `_preds_for`, how it caches per-season
    predictions to parquet under `config.EXPERIMENTS_DIR`, its CLI shape, and its
    `ops.jsonio.write_json` output convention. Follow it rather than inventing a
    second style.
    backtest/walk_forward.py lines 286-330 — the exact call sequence this module must
    mirror per season (`_preds_for`, the capt_ceiling artifact fit on the prior
    validation season, the `cdf` captaincy arm, the `chips_df` chips arm).
    backtest/season.py lines 150-160 and 310-320 — `run_season`'s signature and the
    ratio-of-sums definition of capture.
  </read_first>
  <behavior>
    Pure-function unit tests in tests/test_experiments.py, written before the
    statistics helpers they cover:
    - Ratio-of-sums capture: given per-gameweek capt_pts/best_pts arrays, the helper
      returns sum(capt)/sum(best), NOT the mean of per-gameweek ratios — assert the two
      differ on a fixture where they must (e.g. best_pts varying across gameweeks) and
      that the helper matches the former.
    - Zero-denominator guard: an all-zero best_pts input returns a finite value rather
      than raising or emitting inf/nan (mirror walk_forward.py:308's max(...,1) guard).
    - Paired t interval: on the six capt_capture deltas from F3, the helper reproduces
      mean +0.0147 and a 95% CI of [-0.0131, +0.0424] to 4 decimal places.
    - Paired cluster bootstrap: with a fixed seed and clusters that are exact copies of
      one another, the returned interval collapses to a point at the observed delta
      (a degenerate-input sanity property, not a distributional assertion).
  </behavior>
  <action>
    Create `backtest/capt_ceiling_ci.py`, a measurement-only module. It must import and
    reuse `backtest.walk_forward`'s own `_preds_for`, `apply_experiment_feature_gating`,
    `DATA_SEASONS`, `TEST_SEASONS`, plus `models.captaincy` and
    `backtest.season.run_season` — do not fork or reimplement the prediction path, and
    do not read `data/processed/test_predictions.parquet`.

    Per season T: build the shared frame once per F6 — `load_features`, gate with an
    all-flags-off experiment dict, `_preds_for(df, T)` for `(te, models, cols)`, then
    fit the ceiling artifact on `DATA_SEASONS[DATA_SEASONS.index(T) - 1]` via
    `captaincy.fit_ceiling_artifact` and add the ceiling column with
    `captaincy.add_ceiling_ev(te, artifact, lam=config.CAPT_CEILING_LAMBDA)`. Cache the
    resulting frame to `config.EXPERIMENTS_DIR / f"capt_ci_te_{season}.parquet"` and
    reuse it on later invocations so re-slicing never retrains — the 5vx caching rule.
    Expose a flag to force a rebuild.

    From that one frame run four `run_season` calls per season and keep each call's
    FULL returned per-gameweek log, not just its sum:
      - captaincy arm OFF: capt_col="xp_mean", use_chips=False
      - captaincy arm ON : capt_col="xp_capt_ceiling", use_chips=False
      - chips arm OFF    : capt_col=None, use_chips=True
      - chips arm ON     : capt_col="xp_capt_ceiling", use_chips=True
    These mirror walk_forward.py:302-306 exactly; the OFF captaincy arm's "xp_mean"
    default is what walk_forward.py:306's `capt_col_active or "xp_mean"` resolves to
    when the flag is off. Retain gw, points, capt_pts, best_pts per row per arm.

    Compute two interval families over the paired arms, and label both in the output:
      - Season-clustered (n=6): the conservative, correctly-clustered reading. Paired
        two-sided t interval on the per-season deltas of capt_capture, capt_mean
        (captaincy-arm season points), and model+chips (chips-arm season points).
        This family GOVERNS the verdict.
      - Gameweek-level paired cluster bootstrap (n≈228 gameweek pairs, fixed seed,
        >=10000 resamples, percentile interval): resample gameweek pairs with
        replacement stratified within season and recompute the ratio of sums each draw
        per the key_links rule. Report as the higher-power but optimistic reading,
        because gameweeks within a season are not independent — squad state carries
        across gameweeks through transfers.
    Record the resampling unit and the season-vs-gameweek independence caveat as
    fields in the output JSON so the addendum cannot quote an interval without it.

    Write `config.EXPERIMENTS_DIR / "capt_ceiling_ci.json"` via `ops.jsonio.write_json`
    with, per metric: n, mean delta, both intervals, and the per-season off/on values
    for reproduction. Give the module a `--seasons` CLI argument accepting a
    comma-separated subset (default: all of TEST_SEASONS), matching walk_forward's own
    flag, so this task can run one season and Task 2 can run six.

    This task's tracer path is the single season 2025-26 end to end: shared frame →
    four arms → both interval families → JSON on disk. Do not add per-position or
    per-chip slicing; that is not this task's scope.
  </action>
  <verify>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_experiments.py -x -q</automated>
    <automated>taskset -c 0-17 /home/sraja/miniconda3/envs/python314/bin/python -m backtest.capt_ceiling_ci --seasons 2025-26 2>&1 | tail -30</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "import json,pathlib,config; d=json.loads(pathlib.Path(config.EXPERIMENTS_DIR/'capt_ceiling_ci.json').read_text()); s=d['per_season']['2025-26']; assert abs(s['capt_capture_off']-0.595)<0.0006, s; assert abs(s['capt_capture_on']-0.619)<0.0006, s; assert s['model_chips_off']==2172, s; assert s['model_chips_on']==2293, s; print('2025-26 reproduces wf CSVs:', s)"</automated>
  </verify>
  <done>
    The unit tests pass. A single-season run writes capt_ceiling_ci.json whose 2025-26
    off/on values reproduce the committed Phase 9 CSV rows — capt_capture 0.595/0.619
    (within the CSV's own 3dp rounding) and model+chips 2172/2293 exactly. Both
    interval families and their stated resampling units are present in the JSON. The
    per-season prediction cache parquet exists, and a second invocation of the same
    command is visibly faster because it does not retrain.
  </done>
</task>

<task type="auto">
  <name>Task 2: Full six-season run plus the replica-invariance demonstration</name>
  <files>data/processed/experiments/capt_ceiling_ci.json</files>
  <action>
    Two independent measurements. Run them sequentially, both pinned with
    `taskset -c 0-17` per F7, both launched detached with output to a timestamped log
    under `data/processed/experiments/`. Do not kill or disturb the three
    `optimize.rl_train` processes, and do not launch GPU work.

    (a) Full six-season run of `backtest.capt_ceiling_ci` over all of TEST_SEASONS,
    overwriting the single-season JSON from Task 1 with the complete result. Five of
    the six seasons must train, so expect this to dominate the wall clock.

    (b) The replica-invariance demonstration, which is what converts F1 from a
    code-reading argument into an observed fact — the addendum's central claim depends
    on it. Using the UNMODIFIED committed harness, run both arms at 25 replicas over a
    single season:
      python -m backtest.walk_forward --seasons 2025-26 --replicas 25 --tag base_r25
      python -m backtest.walk_forward --seasons 2025-26 --replicas 25 --tag capt_r25 --experiments capt_ceiling
    Then compare each tagged CSV's 2025-26 row against the corresponding row of the
    existing 5-replica results. Expected and to be confirmed: `model+chips`,
    `capt_mean` and `capt_capture` are identical to wf_baseline_phase9.csv
    (2172 / 2174 / 0.595) and wf_capt_ceiling_adopt.csv (2293 / 2185 / 0.619)
    respectively, while `model_mean` and `model_std` — the only replica-averaged
    columns — do shift. Record the observed `model_mean`/`model_std` values for both
    replica counts; that contrast is the demonstration.

    One season at 25 replicas is sufficient and is the deliberate choice here: the
    metrics are deterministic, so a single season exhibits the mechanism completely,
    and spending 50-70 minutes on six seasons × two arms to reprint numbers F1 shows
    cannot change would be the exact waste this plan exists to avoid. State that
    reasoning in the SUMMARY.

    Launch pattern: write a sentinel file on completion and poll for it with a hard
    iteration cap, never an unbounded monitor. If a poll budget expires with the run
    still alive, report the log's current tail and keep polling in a fresh bounded
    loop — do not assume failure and do not relaunch a run that is still alive.

    If a season fails to train, record which one and why in the SUMMARY and let the
    remaining seasons complete; a five-season interval clearly labelled as such is a
    usable result, a silently truncated six-season claim is not.
  </action>
  <verify>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "import json,pathlib,config; d=json.loads(pathlib.Path(config.EXPERIMENTS_DIR/'capt_ceiling_ci.json').read_text()); ps=d['per_season']; print('seasons:',sorted(ps)); assert len(ps)>=5, ps; [print(m, d['metrics'][m]['mean_delta'], d['metrics'][m]['season_ci']) for m in d['metrics']]"</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "
import pandas as pd, config
E=config.EXPERIMENTS_DIR
for tag,ref,cols in [('base_r25','wf_baseline_phase9',None),('capt_r25','wf_capt_ceiling_adopt',None)]:
    a=pd.read_csv(E/f'wf_{tag}.csv').set_index('season').loc['2025-26']
    b=pd.read_csv(E/f'wf_{ref}.csv').set_index('season').loc['2025-26']
    for c in ['model+chips','capt_mean','capt_capture']:
        assert a[c]==b[c], (tag,c,a[c],b[c])
    print(tag,'invariant on capt/chips metrics; model_mean r25=',a['model_mean'],'vs r5=',b['model_mean'],'model_std r25=',a['model_std'],'vs r5=',b['model_std'])
"</automated>
  </verify>
  <done>
    capt_ceiling_ci.json covers at least five seasons with both interval families
    populated for capt_capture, capt_mean and model+chips. The 25-replica runs are on
    disk for both arms and the comparison confirms model+chips, capt_mean and
    capt_capture are unchanged from the 5-replica results while model_mean/model_std
    are not — the observed demonstration of F1. Every command ran under taskset -c 0-17
    and all three rl_train processes are still alive.
  </done>
</task>

<task type="auto">
  <name>Task 3: Record the Phase F addendum and guard the untouched flag</name>
  <files>IMPROVEMENTS.md, tests/test_experiments.py</files>
  <read_first>
    IMPROVEMENTS.md line 989 onward — the '### Addendum (2026-09-09): per-position and
    covered-row re-measurement' section from quick task 260909-5vx. Match its style:
    inlined markdown tables carrying the numbers themselves, an explicit plainly-stated
    verdict, a caveat paragraph about what the measurement does and does not license,
    and a closing tie-back to the phase's own recorded open weakness.
    IMPROVEMENTS.md line 899 onward — 'What this phase did not resolve', which records
    that every Phase 9 verdict rested on eyeballing a delta against an informal SE.
    IMPROVEMENTS.md line 225 onward — '### capt_ceiling: lambda sweep and adoption
    verdict (plan 09-03)', the section this addendum extends.
  </read_first>
  <action>
    Add a new section to IMPROVEMENTS.md under Phase F, after the 5vx addendum, titled
    as a 2026-09-09 addendum on capt_ceiling paired intervals and naming plan 09-03 as
    the section it extends. Because data/processed/ is gitignored (F7), inline every
    decisive number — a reader with no access to the JSON must be able to check the
    verdict.

    Cover, in this order:
      1. What plan 09-03 concluded and on what evidence (capture 0.563→0.578 against a
         ≥+2pt D-06 bar, model+chips 2262→2278, both at 5 replicas, both eyeballed
         against an informal SE≈16).
      2. The replica finding. State plainly that raising --replicas cannot move either
         number, cite the mechanism (replicas feed only the jittered `totals` list, so
         only model_mean/model_std are replica-averaged; every metric capt_ceiling
         touches comes from a single unjittered run_season call), and give the Task 2
         observation as the demonstration — the r=25 vs r=5 table showing model+chips,
         capt_mean and capt_capture identical while model_mean/model_std move. This is
         the correction to the todo's own proposed method and should be readable as
         such: the 25× re-run was run, and it is the reason the answer had to come from
         a different axis.
      3. The paired intervals table: per-season off/on values for capt_capture,
         capt_mean and model+chips, then mean delta with both the season-clustered
         (n=6, governing) and gameweek-bootstrap (n≈228, optimistic) 95% intervals.
      4. The verdict, stated plainly against the pre-declared D-06 bar, driven by the
         season-clustered family. Include capt_mean's own sign — the captaincy arm's
         season points, which F3 measured as negative in the mean — because a capture
         gain that does not convert into points is the reading a bar revision would
         have to survive.
      5. The caveats: gameweeks within a season are not independent so the bootstrap
         interval is optimistic and does not govern; and per F5 the two arms select
         different squads rather than differing only in the armband, so these deltas
         measure the whole capt_col-in-the-ILP-objective change, not an isolated
         captain pick.
      6. The closing tie-back: this is the second instalment (after 5vx) on the
         'What this phase did not resolve' gap, and unlike 5vx it tests the
         season-points metric the adoption bar is actually written against.

    Then branch on the season-clustered result, and make the branch you took explicit
    in both the addendum and the SUMMARY:
      - If the capt_capture interval EXCLUDES zero and neither capt_mean nor
        model+chips shows a regression: close the section with a clearly-headed block
        presenting the case for revising the D-06 bar, addressed to the user as a
        decision they must make. State what the revised bar would need to be, and that
        capt_mc (models/simulate.py) becomes worth building only if the user accepts it.
      - Otherwise: record the rejection as confirmed, now on a stated statistical test
        rather than an eyeballed delta, and note that capt_mc stays ungated.
    Under EITHER branch `config.EXPERIMENTS['capt_ceiling']` stays False and config.py
    stays byte-unchanged. Do not edit config.py in this task for any reason.

    Add one regression test to tests/test_experiments.py asserting that the two
    captaincy experiment flags in config.EXPERIMENTS are both False, so a future change
    that silently adopts either one fails a test rather than shipping quietly.

    Move the todo file from .planning/todos/pending/ to the completed location this
    repo's convention uses, or if no such convention exists leave it in place and say
    so in the SUMMARY.
  </action>
  <verify>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_experiments.py -x -q</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -c "import config; assert config.EXPERIMENTS['capt_ceiling'] is False; assert config.CAPT_CEILING_LAMBDA==0.5; print('flag off, lambda pinned')" && git diff --quiet -- config.py && echo "config.py byte-unchanged"</automated>
    <automated>git diff --name-only && test -z "$(git diff --name-only -- predict api web features data)" && echo "no product surface touched"</automated>
    <automated>/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_leakage.py tests/test_legality.py -q</automated>
  </verify>
  <done>
    IMPROVEMENTS.md carries a Phase F addendum whose inlined tables let a reader check
    the verdict without the gitignored JSON, covering all six required points including
    the replica-invariance demonstration and the explicit branch taken. The captaincy
    flags are asserted off by a test, config.py is byte-unchanged, and no file under
    predict/, api/, web/, features/ or data/ is modified. The pre-existing leakage and
    legality suites still pass.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo → committed record | IMPROVEMENTS.md becomes the permanent, citable verdict on capt_ceiling; a number that cannot be checked from the committed text is unfalsifiable once data/processed/ is cleared |
| measurement → shipped default | config.EXPERIMENTS is the single switch between a measurement and a product change |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-dga-01 | Tampering | config.py EXPERIMENTS / CAPT_CEILING_LAMBDA | high | mitigate | Task 3 asserts the captaincy flags are False and `git diff --quiet -- config.py` passes; a new test pins both flags off permanently |
| T-dga-02 | Information disclosure | IMPROVEMENTS.md addendum | low | mitigate | Numbers only — no paths outside the repo, no personal identifiers (the Phase 05-04 precedent); addendum inlines results rather than linking gitignored artifacts |
| T-dga-03 | Denial of service | host CPU shared with 3 live rl_train processes | medium | mitigate | Every harness invocation pinned with `taskset -c 0-17` of 28 cores; runs launched detached and polled with a hard iteration cap; no GPU work launched |
| T-dga-04 | Repudiation | the verdict itself | medium | mitigate | Task 1 reproduces plan 09-03's published per-season numbers exactly before any new interval is trusted; resampling unit and independence caveat are recorded as JSON fields, not left to prose |
| T-dga-SC | Tampering | npm/pip/cargo installs | high | mitigate | No packages installed — numpy/pandas/scipy/pytest are already project dependencies, so the package-legitimacy gate has no surface here |
</threat_model>

<verification>
- Task 1's reproduction gate passed before any new interval was believed: 2025-26
  off/on values match wf_baseline_phase9.csv and wf_capt_ceiling_adopt.csv.
- The 25-replica runs exist for both arms and demonstrate replica-invariance of
  capt_capture / capt_mean / model+chips, with model_mean/model_std moving as the
  contrast.
- Both interval families are reported with their resampling unit named, and the
  season-clustered family governs the verdict.
- config.py is byte-unchanged and both captaincy flags are asserted off by a test.
- tests/test_leakage.py and tests/test_legality.py still pass.
- All three optimize.rl_train processes survived the task.
</verification>

<success_criteria>
A developer reading IMPROVEMENTS.md can answer, from inlined numbers alone, whether
capt_ceiling's +1.5pt capture reading survives a stated statistical test — and can see
why the replica count was never the axis that could answer it. Nothing about the
shipped product changed.
</success_criteria>

<output>
Create `.planning/quick/260909-dga-high-replica-25x-capt-ceiling-adoption-r/260909-dga-SUMMARY.md` when done
</output>
