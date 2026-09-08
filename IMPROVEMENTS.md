# Improvements plan

From the 2026-08-21 code review. Work top-to-bottom; each item states impact and
where it lands. Status: ☐ todo · ☑ done · ◪ partial.

## Phase A — Bug fixes (correctness first)  — ALL DONE 2026-08-21

- ☑ **B1 Blank-GW padding corrupts positions (live `--entry`)** — `optimize/transfers.py`
  `_extend_pool` hardcodes `position="MID"` for held players missing from the pool.
  Backtest pre-pads correctly; the live entry path does not. Fix: `optimize_gw`
  accepts holdings metadata (position/team/name); error rather than silently
  mislabel. Live builds that metadata from the bootstrap.
- ☑ **B2 Autosubs can produce illegal formations** — `backtest/season.py::_autosub`
  enforces position maxima only; FPL also enforces minima (≥3 DEF, ≥2 MID, ≥1 FWD).
  Fix: per-slot rule matching real FPL — a blank starter may be replaced by the
  same position, or another position only if the blank's position stays ≥ its
  minimum; otherwise the slot goes UNFILLED (never fixed with a wrong position).
  Removes a small optimistic bias from every backtest config.
- ☑ **B3 Chip scheduling look-ahead in backtest** — `optimize/chips.py` reads the
  season's final fixture list, but doubles are created mid-season. Fix: causal
  scheduler — the decision at GW g only sees fixture structure within g..g+K
  (default K=4, matching real announcement lead time). Live already causal.
- ☑ **B4 (part) Live `days_rest`** — top-importance feature for DEF/GK missing at
  live inference. Compute from the live fixtures list (team's previous kickoff).
  (Rolling form + live odds are Phase B/C.)
- ☑ **B5 FBref scrape loses progress** — writes parquet only at the end (lost the
  killed run's season). Fix: append per season, skip cached seasons on restart.
- ☑ **B6 Entry-mode selling prices** — public API lacks purchase prices; current
  price used instead (sell-on fee ignored). Fix: `--purchase-prices file.json`
  (web_name → purchase £m) override; document the approximation otherwise.
- ☑ **B7 Budget tolerance leaks money** — solver may spend +£0.049 and the bank is
  then clamped at 0, gifting cash weekly. Fix: carry the true (possibly slightly
  negative) bank; tolerance stays only as MILP rounding guard.
- ☑ **B8 Spearman inflated by non-players** — ~60% of rows are 0-minute rows.
  Fix: report played-only metrics alongside in `models/train.py`.

- ☑ **B9 Club cap not grandfathered** (found by the calibrated walk-forward run):
  a January window move can leave a legally-built squad holding 4 of one club
  (2020-21 GW20: 4x Arsenal) — FPL only enforces <=3 at transfer time, but our ILP
  applied it as a hard invariant -> infeasible under `max_transfers=0`. Fix: per-club
  cap = max(3, currently-held count); regression test added. (Also fixed a `cap`
  variable shadowing introduced by the first attempt — caught by the test suite.)

## Phase A2 — Tests (locks the fixes in; currently zero tests)

- ☑ `tests/test_legality.py` — property test: random pools → `pick_squad` /
  `optimize_gw` output always legal (2/5/5/3, ≤3 club, budget, formation, 1 captain).
  Would have caught B1/B2.
- ☑ `tests/test_leakage.py` — first-appearance rows have all-NaN rolling features;
  `minutes_r5` equals independent shift+roll recompute (freeze the manual checks).
- ☑ `tests/test_autosub.py` — formation-minimum scenarios (blank DEF → bench DEF
  in, never a 4th MID that breaks minima; GK only replaced by GK).
- ☑ Doctests: `pytest --doctest-modules optimize/pricing.py`.
- ☑ Calibration check (`models/calibration.py`, test season): MID/GK well calibrated
  (ECE 0.011/0.009); **DEF under-confident (ECE 0.028**, says 35% -> 47% play) — a
  cheap stage-1 isotonic recalibration is a Phase-C candidate.
- ☑ Backtest metrics: captaincy hit-rate 18% / capture 57% (gap ~4.8 pts/GW — the
  biggest single-decision gap; motivates the Phase-C Monte-Carlo captaincy). Mid-season
  entry robust (`backtest.season --start-gw 10`: 60.0/GW vs 56.6 full season).

## Phase B — Live/serve parity (biggest live-quality win)

- ☑ Current-season rolling form at inference (`data/live_history.py`): fetch + cache
  element-summary per player, compute form-as-of-now (guarding against the API's
  pre-created zero rows for unplayed fixtures), auto-merged in `predict.live`.
- ☑ Live forward odds seam (`data/live_odds.py`): fills ODDS_COLS at inference when
  `ODDS_API_KEY` is set (the-odds-api.com free tier); graceful NaN without a key.
  NOTE: untested against the real API until a key is provided.
- ☑ Horizon metrics (`backtest/horizons.py`): Spearman 0.736 / 0.699 / 0.675 at
  1/2/3 GWs ahead (~0.03/week decay) — frozen form stays useful 2-3 GWs out,
  validating the multi-GW planner's inputs.

## Phase C — Model upgrades

- ☑ 3-state minutes model (`minutes_model="3state"`): TESTED, REJECTED — MAE
  0.874 vs 0.871, Spearman 0.734 vs 0.736, season sim no better. The regressor
  already absorbs cameo/start via minutes-form features. Opt-in only.
- ☑ **Stage-1 isotonic recalibration ADOPTED as default** (`calibrate=True`):
  strictly better fixture metrics (MAE 0.868), deployed ECE improved for every
  position (DEF 0.028→0.020). Walk-forward confirmation run queued.
- ☑ **Captain-by-mean ADOPTED** (attacks the 4.8 pts/GW captaincy gap without
  simulation): the armband doubles points, so the captain slot should maximise
  E[points] — select XI by xp_med, captain by xp_mean (`capt_col`/`xp_capt`
  through squad_ilp, transfers, season, live). 6-season walk-forward: **2150 vs
  core 2134 (+16/season avg)** — but noisy per season (-77..+125, wins 3/6 with
  two ties); capture ~57% both ways on average. Adopted because it is
  theoretically correct and free at inference; expect small average gain, not the
  single-season +57.
- ☐ Full Monte-Carlo layer (chip timing error bars, EO/variance-aware
  differentials for RANK play) — deferred; captain-by-mean covers the points case.
- ☐ Price-change model from transfer momentum (team-value growth).

## Phase D — Optimization upgrades

- ☑ True multi-period MILP TESTED, NOT ADOPTED (`optimize/multi_period.py` +
  `backtest/multi_period_season.py`): transfers/FT-banking/hits as variables over
  a rolling 3-GW horizon (receding-horizon, execute week 0), frozen-form future
  pools, candidate pruning (held + top-150), grandfathered club caps. 2025-26:
  **2167 vs myopic capt-mean 2174 — a tie**, while taking 9 hits (transfer-happy).
  Consistent with multi-GW value collapsing to +13 after calibration. Kept as
  opt-in; not worth 6-season compute unless the 1-GW model's edge grows.
- ☐ Robust variant: hedge vs prediction error (arXiv 2505.02170-style).

## Phase E — Data

- ☑ FBref scrape — **BLOCKED at the source, abandoned (2026-08-22)**: the scrape
  works (Cloudflare bypassed, 11 seasons, ~6k player-seasons of names) but FBref
  no longer serves the advanced stat VALUES — every Tkl+Int/blocks/clearances/
  SCA/GCA cell is empty (`class="iz"`) in the delivered HTML, headless AND headed,
  across all seasons; only a few metrics (e.g. interceptions) survive. Likely
  fallout of the StatsBomb→Opta provider switch. The seam stays (`data/fbref.py`)
  with hardening added while diagnosing: season-LAGGED join (same-season
  aggregates were leakage), per-table primary-stint dedupe (mid-season movers
  appear once per squad → 2x2x2 merge blowup), `_key` dedupe + row-count assert
  in `attach()` (a many-to-many name join silently duplicated player_gw rows up
  to 16x and corrupted a whole walk-forward before being caught).
- ☐ Injury/press-conference feed earlier than `chance_of_playing`.
- ☐ Understat npxG/xGChain via soccerdata cache (low priority; FPL xG covers most).

## Phase F — xP model & optimizer improvement experiments (Phase 9)

### Baseline (measured 2026-09-08, all experiment flags off)

Command: `scripts/experiment_run.sh baseline_phase9` → `python -m backtest.walk_forward
--tag baseline_phase9` (6 seasons, 5 replicas, `--experiments` unset → all-off).
Result: `data/processed/experiments/wf_baseline_phase9.json`.

| season | model_mean | model_std | model+chips | capt_mean | capt_capture | multi_safe | form | hold |
|--------|-----------:|----------:|------------:|----------:|-------------:|-----------:|-----:|-----:|
| 2020-21 | 2074 | 61 | 2091 | 2071 | 0.541 | 1967 | 2077 | 1517 |
| 2021-22 | 2119 | 47 | 2305 | 2123 | 0.583 | 2312 | 2174 | 1610 |
| 2022-23 | 2148 | 43 | 2380 | 2183 | 0.563 | 2269 | 2079 | 1835 |
| 2023-24 | 2191 | 68 | 2210 | 2086 | 0.483 | 2146 | 1960 | 1741 |
| 2024-25 | 2137 | 44 | 2417 | 2260 | 0.614 | 2101 | 2107 | 2230 |
| 2025-26 | 2122 | 21 | 2172 | 2174 | 0.595 | 2086 | 1797 | 1439 |

6-season averages: `model_mean` = 2132, `model+chips` = **2262**, `capt_mean` = 2150,
`capt_capture` = 0.563 (56.3%), `multi_safe` = 2147, `form` = 2032, `hold` = 1729.

This measured `model+chips` average (2262) agrees closely with both prior estimates:
D-05's quoted "current ≈2,256" (off by 6 points) and 09-RESEARCH.md's ≈2,263 computed
from the then-cached `walk_forward_results.csv` (off by 1 point) — well within the
noise this harness already reports (season-to-season std ≈38-68, SE ≈16). **2,262 is
the reference number the D-05 ≥2,280 bar is judged against for this phase**, measured
fresh on this machine rather than inherited from either cached figure.

### Adoption criteria (D-05/D-06, pre-declared)

- **Primary bar:** mean core+chips season points ≥ **2,280** across the 6-season average.
- **Captaincy:** capture % (armband points ÷ best-possible armband) improves ≥ +2 pts
  absolute over captain-by-mean, averaged over seasons.
- **Chips:** isolated WC value measured and no chip's isolated value regresses (see the
  isolated-chip table below); FH/BB/TC stay within their CIs.
- **Team-strength:** ratings covered by a `tests/test_leakage.py` assertion (ratings at
  GW g must reproduce from matches < g only).
- **Multi-GW / horizon:** any horizon-touching change gets an optimistic-vs-frozen A/B.
- **RL:** must beat chip scheduler v2 on the same harness (D-02).

Isolated chip value observed in this baseline run (same team, with vs without —
`data/processed/experiments/wf_baseline_phase9.csv`):

| chip | mean | std | count |
|------|-----:|----:|------:|
| bb | 10.1 | 8.3 | 9 |
| fh | 20.8 | 16.1 | 10 |
| tc | 7.2 | 6.3 | 10 |

WC's isolated value is not separately recorded by the harness (it triggers a full
squad rebuild, not a same-team-with/without comparison); this baseline table is
therefore the "currently unmeasured" state the adoption criteria call out for WC.

### Benchmark: our xP vs theFPLkiwi (external-projection benchmark, D-01 experiment 1)

Command: `python -m backtest.benchmark_external --tag phase9` (no network access;
reads only the committed `data/external/kiwi/` snapshot plus
`data/processed/features.parquet`). Result:
`data/processed/experiments/benchmark_phase9.json`. Scored on played-only
common rows (`y_minutes > 0`) at GW level (fixtures summed per player-GW so
DGWs line up with theFPLkiwi's one-row-per-gameweek shape), joined on
`(season, player_id == fpl_id, gw)`.

2023-24 is explicitly **skipped, not silently dropped**: theFPLkiwi's committed
snapshot for that season only carries 4 gameweeks (GW1/GW3/GW4/GW18) —
too thin to score.

| season | n rows (pre-join) | n common | join coverage | n played-only | MAE `xp_med` | Spearman `xp_med` | MAE `xp_mean` | Spearman `xp_mean` | MAE `xp_fpl` (FPL) | Spearman `xp_fpl` | MAE `proj_pts` (kiwi) | Spearman `proj_pts` |
|--------|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021-22 | 23,230 | 19,603 | 84.4% | 9,772 | 2.064 | 0.380 | 2.090 | 0.380 | 2.107 | 0.591 | 2.114 | 0.380 |
| 2022-23 | 24,957 | 14,342 | 57.5% | 7,716 | 1.869 | 0.386 | 1.928 | 0.390 | 1.808 | 0.558 | 1.988 | 0.389 |
| **pooled (played-only)** | — | — | — | **17,488** | **1.978** | **0.383** | **2.018** | **0.386** | **1.975** | **0.579** | **2.059** | **0.383** |

**Interpretation.** On these two historical seasons, our xP (`xp_med`/`xp_mean`)
and theFPLkiwi's published pre-deadline projections (`proj_pts`) land in the
same MAE/Spearman neighbourhood — neither model clearly beats the other on
played-only common rows (pooled Spearman 0.383 vs 0.383, MAE 1.978 vs 2.059).
The more striking part of this reading is that FPL's own `xp_fpl` baseline
ranks players noticeably better than either of us here (pooled Spearman 0.579
vs 0.383) despite a comparable MAE (1.975 vs 1.978) — on 2021-22/2022-23
specifically, no candidate is dominant on both axes at once, and FPL's own
official expected-points figure is the strongest ranker of the three. **Per
D-01, this reading prunes nothing**: all six experiments in this phase still
run in the fixed order regardless of this number — it is context for
interpreting them (e.g. a later feature-accuracy experiment closing the
ranking gap to `xp_fpl` on this same played-only basis would itself be a
useful confirmation signal), not a gate on any of them.

### Experiment results

| flag | criterion | measured | verdict | default |
|------|-----------|----------|---------|---------|
| capt_ceiling | capture improves ≥ +2 pts abs. over captain-by-mean | +1.5 pts abs. (0.563→0.578); model+chips +16 (2262→2278) | rejected | off |
| capt_mc | capture improves ≥ +2 pts abs. over captain-by-mean | not run — gated on capt_ceiling capture delta of +0.015, below the +0.02 trigger | not triggered | off |
| chips_v2 | model+chips improves over current default; no chip's isolated value regresses; WC value measured | model+chips −48 (2262→2214); bb regressed outside its CI (10.0→8.5); Wildcard measured for the first time (14.2±9.0/gw, n=4, `wf_wc_measure`) | rejected | off |
| team_strength | `tests/test_leakage.py` leakage assertion passes; D-07: model+chips improves over the current default and multi_safe does not regress | leakage test passes; model+chips −2/season (2262→2260); multi_safe −12/season (2147→2135) | rejected | off |
| rl_strategy | beats chips_v2 on the same harness (D-02) | pending | pending | off |
| understat | model+chips contribution measured via the harness | pending | pending | off |
| fotmob | model+chips contribution measured via the harness | pending | pending | off |
| fbref_v2 | model+chips contribution measured via the harness | pending | pending | off |

Every row starts `pending`; later plans in this phase fill their own row as they
measure it. Plan 09-10 finalises this table. A failed experiment keeps its code
merged behind a default-off flag with its number recorded here — never deleted (D-08).

### capt_ceiling: lambda sweep and adoption verdict (plan 09-03)

- ☑ **Lambda sweep, TESTED, REJECTED at adoption.** `--capt-lambda` swept over
  {0.0, 0.25, 0.5, 0.75, 1.0} at 6 seasons/1 replica (`wf_capt_lam_<value>`,
  2026-09-08). Lambda 0.0 reproduced the captain-by-mean control exactly
  (`capt_capture` 0.563, matching the baseline to within noise), confirming the
  ceiling column is wired through the correct seam:

  | lambda | capt_capture | model+chips |
  |-------:|-------------:|------------:|
  | 0.0 (control) | 0.563 | 2264 |
  | 0.25 | 0.576 | 2283 |
  | **0.5 (winner)** | **0.578** | 2278 |
  | 0.75 | 0.572 | 2272 |
  | 1.0 | 0.547 | 2270 |

  Lambda 0.5 measured the highest 6-season-mean `capt_capture` and was pinned
  to `config.CAPT_CEILING_LAMBDA`.
- ☑ **Adoption-deciding run** (`scripts/experiment_run.sh capt_ceiling_adopt
  --experiments capt_ceiling`, 6 seasons at the harness's default 5 replicas,
  `wf_capt_ceiling_adopt.json`): `capt_capture` 0.578 vs the plan 09-01
  baseline's 0.563 — a **+1.5 percentage-point** absolute move, and
  `model+chips` 2278 vs baseline 2262 (**+16/season**, no regression). D-06's
  criterion requires **≥ +2 pts absolute**; +1.5 does not clear it.
- **D-07 auto-adopt verdict: REJECTED.** `config.EXPERIMENTS['capt_ceiling']`
  stays `False` (D-08: the code stays merged, nothing deleted). No change to
  `tests/test_experiments.py`'s all-flags-default-off assertion was needed
  since the default set did not change.

### capt_mc: Monte-Carlo variant not triggered (plan 09-03)

- ☐ **Not built — gated on the quantile variant's own number.** The research
  doc's sequencing rule (`.planning/research/XP-IMPROVEMENT-OPTIONS.md`
  option 1) is that the Monte-Carlo captaincy layer is only worth its
  machinery once the cheap quantile variant (`capt_ceiling`) has shown the
  ceiling direction pays. The measured `capt_ceiling` capture delta is
  **+0.015** (1.5 percentage points), below the **+0.02** trigger this plan
  pre-declared for building `models/simulate.py`. Per Branch B of this plan's
  Task 3: `models/simulate.py` was left uncreated, `config.EXPERIMENTS
  ['capt_mc']` stays `False`, and this is a recorded, numbered decision in the
  D-08 tradition — not a silent omission. Since `capt_mc` is a
  variant-ordering rule inside experiment 2 (not a seventh experiment), this
  does not affect D-01's fixed six-experiment sequence.

### chips_v2: xP-scored causal scheduler — hysteresis sweep and adoption verdict (plan 09-04)

- ☑ **Wildcard's isolated value measured for the first time.** `backtest/season.py`
  now records a `wc` `chip_deltas` entry (same-gameweek isolation vs a
  zero-transfer hold, the same construction FH already used) — previously
  unmeasured. On the `wf_wc_measure` run (2024-25/2025-26, 1 replica):
  **wc = +14.2±9.0 pts/gw (n=4)**, roughly in the same neighbourhood as TC
  (+9.8±9.0) and below FH (+27.3±26.1). This is a same-gameweek reading only —
  a wildcard's larger real value is the multi-gameweek squad it leaves behind,
  which shows up in the whole-season `model+chips` figure, not this delta.
- ☑ **Hysteresis sweep, TESTED.** `--chips-hysteresis` swept over {0, 1, 2, 3}
  at 6 seasons/1 replica each (`wf_chips_hys_<value>`, 2026-09-08), `chips_v2`
  forced on:

  | hysteresis | model+chips |
  |-----------:|------------:|
  | **0 (winner)** | **2214** |
  | 1 | 2205 |
  | 2 | 2198 |
  | 3 | 2169 |

  Hysteresis 0 measured the highest 6-season-mean `model+chips`, strictly
  above the other three swept values (no tie-break needed) — matching
  09-RESEARCH.md's own recommendation to start at 0. Pinned to
  `config.CHIPS_V2_HYSTERESIS` (already 0.0 by default; comment updated to
  name the sweep).
- ☑ **Adoption-deciding run** (`python -m backtest.walk_forward --experiments
  chips_v2` at the harness's default 6 seasons / 5 replicas,
  `wf_chips_v2_adopt.json`): `model+chips` **2214** vs the plan 09-01
  baseline's **2262** — a **−48/season regression**, not an improvement.
  D-06/D-07's first condition (model+chips improves over the current default)
  fails outright. The second condition (no chip's isolated value regresses
  outside its own confidence interval, checked against `wf_wc_measure`'s
  per-chip table) also fails: `bb` regressed from 10.0±0.0 (v1, n=2) to 8.5±6.5
  (v2, n=12) — below `baseline_mean − baseline_std` = 10.0.

  | chip | v1 mean (± std, n) — `wf_wc_measure` | v2 mean (± std, n) — `wf_chips_v2_adopt` | regressed outside v1 CI? |
  |------|----------------------------:|----------------------------:|:---:|
  | bb | 10.0 ± 0.0 (2) | 8.5 ± 6.5 (12) | **yes** |
  | fh | 27.3 ± 26.1 (3) | 13.6 ± 17.6 (7) | no (within CI) |
  | tc | 9.8 ± 9.0 (4) | 8.0 ± 6.3 (12) | no (within CI) |
  | wc | 14.2 ± 9.0 (4) | 11.7 ± 23.1 (12) | no (within CI) |

- **D-07 auto-adopt verdict: REJECTED.** `config.EXPERIMENTS['chips_v2']` stays
  `False` (D-08: the code — `scored_schedule`, the `scheduler` keyword, the
  `--chips-hysteresis` flag, the wc isolated-value measurement — stays merged,
  nothing deleted). No change to `tests/test_experiments.py`'s all-flags-
  default-off assertion was needed since the default set did not change. The
  heuristic v1 scheduler (`causal_schedule`) remains the shipped default.

### team_strength: expanding-window Dixon-Coles ratings — leakage evidence, horizon graft, and adoption verdict (plan 09-05)

- ☑ **Ratings cover every season including 2016-19, the seasons this option
  exists to fix.** `data/team_strength.py::build_matches()` reconstructs each
  fixture's numeric `(season, team_id)` sides from the two distinct
  `opponent_team_id` values within it — the `team` name column (the odds join
  key) is 0% populated for 2016-17 through 2019-20, so a name-keyed
  reconstruction would inherit exactly the same hole. `data/build_table.py`'s
  guarded join reports **100.0% `ts_attack_self` coverage across every
  season**, including all four 2016-19 seasons, vs `odds_pwin`'s 64.3%
  6-season-plus coverage (0% for 2016-19). `player_gw.parquet` stayed at
  253,509 rows and `features.parquet` gained the 8 declared `ts_*` columns —
  the join did not multiply or drop a single row.
- ☑ **Leakage-safety, TESTED.** An unregularized fit at the 20-match minimum
  diverged (`|attack|>1e3`, `rho>1e9`, overflowing `exp()` into inf/nan) — a
  42-parameter fit over 20 matches (40 goal observations) is hopelessly
  underdetermined. Fixed with a small L2 ridge shrinkage
  (`data/team_strength.py::RIDGE`) toward zero, the correct behaviour for an
  expanding-window fit that should get less regularized as the season
  accumulates matches. `tests/test_leakage.py::test_team_strength_ratings_reproducible_from_prior_matches`
  independently rebuilds the match table, refits GW20 2022-23's ratings from
  matches `gw < 20` only, and reproduces the stored parquet row within
  `atol=1e-4` (observed optimizer noise floor ≈1e-6, itself from BLAS
  thread-count-dependent floating-point reduction order — not a leakage bug);
  a second assertion confirms one row per `(season, gw, team_id)`, not per
  `(season, team_id)` (Pitfall 2's own stated warning sign).
- ☑ **Decision-time horizon graft, TESTED.** `backtest/walk_forward.py`'s
  `leakage_safe_plan()` grafts the future fixture's **opponent identity**
  (`opponent_team_id`, added to `FIXTURE_CTX` — knowable ahead, it is on the
  published fixture list) but re-derives `ts_attack_opp`/`ts_defence_opp`/
  `ts_xg_for`/`ts_xg_against`/`ts_pwin`/`ts_pcs` from
  `team_strength.ratings_as_of(season, g)` — the ratings **as of the decision
  gameweek g**, never the future gameweek's own rating row (which is fit on
  matches up to `g+k-1`, results the decision-maker at `g` has not seen). No
  `ts_*` name is in `FIXTURE_CTX` (verified) so nobody can graft one by
  accident (T-09-05-02).
- ☑ **Optimistic-vs-frozen A/B, D-06.** `--optimistic-plan` added; both arms
  reported side by side on the adoption-deciding run
  (`wf_team_strength_adopt.json`, 6 seasons/5 replicas, `team_strength` on):

  | | multi_safe (honest) | multi_optimistic (peeks at future form) | gap |
  |---|---:|---:|---:|
  | 6-season mean | 2135 | 2527 | +392 |

  The gap (+392) lands in the same neighbourhood as the project's own
  previously-documented +337-optimistic-vs-+40-honest multi-GW leakage
  finding (`PLAN.md` Refinements) — expected, not new: it is the same
  structural trap (future-form-peeking looks far better than a frozen-form
  plan can ever honestly claim), reproduced here on purpose rather than
  assumed away, exactly as D-06 requires for any horizon-touching change.
- **Adoption-deciding run** (`python -m backtest.walk_forward --experiments
  team_strength --optimistic-plan`, the harness's default 6 seasons/5
  replicas, `wf_team_strength_adopt.json`) against the plan 09-01 baseline
  (`wf_baseline_phase9.json`):

  | metric | baseline | team_strength on | delta |
  |--------|---------:|------------------:|------:|
  | model+chips | 2262 | 2260 | −2 |
  | multi_safe (honest horizon) | 2147 | 2135 | −12 |

  Both pre-declared D-07 conditions fail: `model+chips` did not improve (it
  moved slightly down, well within the harness's own season-to-season noise
  band, SE≈40) and `multi_safe` regressed rather than held. The leakage-test
  criterion (D-06's own stated bar for this specific option) passes, but D-07's
  mechanical model+chips/multi_safe rule — applied against the current default
  configuration exactly as plan 09-03/09-04 applied it — does not.
- **D-07 auto-adopt verdict: REJECTED.** `config.EXPERIMENTS['team_strength']`
  stays `False` (already the default; no flip, so no change needed to
  `tests/test_experiments.py`'s all-flags-default-off assertion). Per D-08 all
  new code (`data/team_strength.py`, the guarded `build_table.py`/
  `features/engineer.py` joins, the `leakage_safe_plan` decision-time graft,
  `--optimistic-plan`) stays merged, nothing deleted — the columns are computed
  unconditionally and simply unused as model features by default.

### rl_strategy: time-boxed MaskablePPO policy vs the solver-scored chip scheduler (plan 09-07)

**Declared time-box (written before any training was launched, per D-16):**

- **Seeds:** 3 fixed seeds (0, 1, 2), pinned in `config.RL_SEEDS`.
- **Policies:** one per test season per seed, trained only on seasons strictly
  before that test season.
- **Per-policy wall-clock cap:** 30 minutes, enforced inside `optimize/rl_train.py`'s
  `_TimeBoxCallback`, not by hoping `--timesteps` happens to fit.
- **Hardware:** GPU-accelerated (RTX 4080, `torch.cuda.is_available()` confirmed
  `True` this session, `torch==2.12.0+cu130`).
- **Stop rule:** if the box is exhausted without beating plan 09-04's recorded
  `chips_v2` `model+chips` figure, the experiment is recorded as rejected with
  its numbers. No additional seeds, no extended timestep budget, no further
  tuning.

**Discovered constraint, declared before training started: 2020-21 is excluded.**
`train_seasons_for(T)` can only train on seasons that are themselves
`TEST_SEASONS` members (the only seasons with a squad pool `build_gw_pool`/
`pick_squad` can actually build) — `features.parquet`'s `team` column
[VERIFIED empirically, this session] is 100% null for 2016-17 through 2019-20
and 0% null from 2020-21 onward, exactly why `backtest.walk_forward.TEST_SEASONS`
has always started at 2020-21 rather than `DATA_SEASONS`' own 2016-17 floor —
a pre-existing, structural property of the whole walk-forward pipeline, not
something this plan introduces. **2020-21 is `TEST_SEASONS`' own earliest
member, so by construction it has no earlier `TEST_SEASONS` entry to train a
policy on at all.** The time-box therefore trains policies for the **5**
seasons that do have >=1 earlier `TEST_SEASONS` member (2021-22 through
2025-26) — **15 policies (5 seasons x 3 seeds), not 18** — and the D-02
adoption comparison runs over those same 5 seasons on both sides (`rl_strategy`
and a freshly-measured 5-season `chips_v2` figure), so the comparison stays
apples-to-apples rather than comparing a 5-season RL number against the
previously-recorded 6-season `chips_v2` figure (2214, which includes 2020-21).
`optimize/rl_env.py::load_policy` raises a `SystemExit` naming the training
command if `scheduler="rl"` is ever requested for 2020-21 specifically — this
is a permanent, structural constraint, not a bug to silently work around.

<!-- rl_strategy: results filled by the training + adoption run below -->

## Reference findings (why the priorities)

Levers that beat noise: model vs form baseline (+83..92/season), active transfers
(+~400), chips (+30–40, isolated), multi-GW (+40 leakage-safe). Levers that did NOT:
ranking loss (−55), clean-sheet sub-model (−50), set-piece/odds features (fixture
MAE better, season pts within noise). Full history in PLAN.md.
