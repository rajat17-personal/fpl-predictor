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
| rl_strategy | beats chips_v2 on the same harness (D-02) | seed-mean model+chips 2020 (1847/2069/2144, spread 297) vs chips_v2's 2192 on the same 5 seasons — a −172/season regression, not an improvement | rejected | off |
| understat | model+chips improves ≥2,280 primary bar (D-05/D-06), outside noise (D-07) | model+chips +16 (2262→2278, 2 short of the 2,280 bar); multi_safe +33 (2147→2180); fixture-level MAE/Spearman flat-to-slightly-worse (1.8751→1.8761 / 0.3620→0.3599); join coverage 19.9%→41.2% row-level (94.7% of distinct names) after closing a crosswalk gap + 78 fixups | rejected | off |
| fotmob | model+chips contribution measured via the harness | model+chips +1 (2262→2263, within noise); join coverage 40.4% row-level via the shared crosswalk | rejected | off |
| fbref_v2 | model+chips contribution measured via the harness | not acquirable this session — real UC-mode Chrome navigation to fbref.com never completed (3 attempts, 5-6 min each) despite Chrome/network working fine against a control site; a non-UC driver confirms the page is still Cloudflare-gated (`Just a moment...` challenge). 0 rows scraped, no `fb_tkl_int_90` coverage | not acquirable | off |

Every row started `pending`; each plan in this phase filled its own row as it
measured it, and plan 09-10 confirms none remain — every cell above carries a
number or an evidenced reason. A failed experiment keeps its code merged
behind a default-off flag with its number recorded here — never deleted (D-08).

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

- ☑ **Box spent as declared.** All 15 policies (5 trainable seasons x 3 seeds)
  hit the 30-minute wall-clock cap (`capped: true` in every sidecar JSON) —
  none converged early on `--timesteps 200000`, confirming the cap, not the
  timestep count, was the real budget enforcement (D-16):

  | test season | seed 0 timesteps | seed 1 timesteps | seed 2 timesteps |
  |---|---:|---:|---:|
  | 2021-22 | 8373 | 8161 | 8361 |
  | 2022-23 | 4588 | 4516 | 4662 |
  | 2023-24 | 6934 | 6695 | 6920 |
  | 2024-25 | 13645 | 13502 | 14093 |
  | 2025-26 | 13079 | 12775 | 13339 |

  Total spend: 15 x 30 min = 450 policy-minutes, executed as 3 parallel
  per-seed runs (~2.5 real-clock hours, not the ~9-hour worst case of running
  all 15 sequentially).
- ☑ **5-season comparison, not 6 — apples-to-apples.** Both `chips_v2` and
  `rl_strategy` were re-measured on the same 5 seasons this experiment can
  train on (2021-22 through 2025-26, 5 replicas each), not the previously
  recorded 6-season `chips_v2` figure (2214, which includes the untrainable
  2020-21): `wf_chips_v2_5season.json` -> **`model+chips` 2192** (vs the
  matching 5-season v1 baseline `wf_baseline_5season.json` -> 2272, an
  internally consistent −80/season chips_v2 regression, the same direction
  plan 09-04 already found over 6 seasons).
- **Adoption-deciding runs, one per seed** (`wf_rl_adopt_seed{0,1,2}.json`,
  5 seasons x 5 replicas, `rl_strategy` on, `chips_v2` off, `scheduler: rl`
  confirmed in every summary):

  | seed | model+chips |
  |---:|---:|
  | 0 | 1847 |
  | 1 | 2069 |
  | 2 | 2144 |
  | **mean** | **2020** |
  | spread (max−min) | 297 |

  Seed-mean **2020** vs the same-5-season `chips_v2` figure **2192** — a
  **−172/season regression**, not an improvement, and every individual seed
  (even the best, 2144) already falls short of 2192. D-02's bar (beat the
  solver-scored scheduler) is not met by any seed, let alone the mean.
- ☑ **Isolated-chip comparison** (same 5-season basis; `chips_v2_5season`
  vs the three `rl_adopt_seed*` runs):

  | chip | chips_v2 (mean±std, n) | rl seed0 | rl seed1 | rl seed2 |
  |------|----------------------------:|---:|---:|---:|
  | bb | 8.7±6.6 (10) | — | — | 8.5±9.2 (2) |
  | fh | 1.2±8.9 (6) | — | −5.5±19.1 (2) | 78.0 (1) |
  | tc | 8.8±5.7 (10) | — | — | — |
  | wc | 9.6±19.5 (10) | 20.0±28.3 (2) | −22.0±8.5 (2) | 7.5±0.7 (2) |

  The RL policy plays far fewer chips overall than either heuristic scheduler
  (most halves end with an unused chip rather than the v1/v2 end-of-half
  forcing rule triggering, since the policy under-explores the chip actions
  within its short training budget) — the sparse, noisy per-chip counts above
  are a symptom of that, not a like-for-like isolated-value comparison; the
  whole-season `model+chips` figures above are the decision-relevant number.
- ☑ **Training-vs-held-out curve: no Pitfall-4 divergence observed.** Across
  all 15 runs the training-episode reward was flat-to-slightly-declining
  over the capped window (e.g. seed 0 / 2025-26: 2212 -> 2156 from t=1024 to
  t=12288) while the held-out score stayed noisy around the same level
  (2194 -> 2086, no monotonic trend either way) — the classic FPL-RL audit
  smoking gun (training reward climbing while the held-out/harness score
  plateaus or falls) did **not** appear. The honest reading is simpler and
  less exotic: in a 30-minute, 2-4-training-season budget the policy did not
  learn a materially better strategy than a random or heuristic one, and the
  masked action space (chip x transfer-count) with dozens of legal actions
  per gameweek needs far more experience than ~5,000-14,000 timesteps to
  move meaningfully off its initialization.
- **D-07/D-16 verdict: REJECTED.** `config.EXPERIMENTS['rl_strategy']` stays
  `False` (already the default; no flip, so no change needed to
  `tests/test_experiments.py`'s all-flags-default-off assertion). Per D-08
  and D-16's stop rule, the box is exhausted and the code stays merged
  behind the default-off flag — `optimize/rl_env.py` and
  `optimize/rl_train.py` remain in the repository, nothing deleted, and no
  additional seeds, extended timestep budget, or further tuning were spent
  chasing this result. One explicit note per this plan's own instruction:
  the audited FPL-RL project's headline 2,918-point figure was in-sample
  (judged by a different, optimistic signal than an honest walk-forward
  harness measures) and was never this experiment's target — this
  experiment's own honest, leakage-safe number (seed-mean 2020, well below
  both v1's 2272 and chips_v2's 2192 on the same 5 seasons) is the answer to
  a different, harder question than that headline was ever measuring.

### understat: non-penalty xG + involvement-chain metrics — crosswalk gap found, fixture-level accuracy flat, adoption verdict (plan 09-08)

- ☑ **Join built and cached.** `data/understat.py` fetches per-player match
  histories via `understatapi` (the real API has no single per-league-season
  endpoint — `fetch_season()` combines the league's fixture-id list with
  every roster player's whole career history, filtered to that season's
  fixture ids) and writes `data/processed/understat.parquet`
  (109,592 player-match rows, 2016-17 through 2026-27, cached under
  `data/raw/understat/`, zero network calls on a cache-warm rerun).
- ☑ **Crosswalk gap found and closed, TESTED — a real assumption delta.**
  The first real join measured only **19.9% row-level coverage**
  (413/1,980 distinct Understat names resolved) through
  `data.id_crosswalk.resolve_by_name`'s existing tiers alone. Root cause:
  theFPLkiwi's `ID_Dictionary.csv` (plan 09-02's crosswalk source) is a
  **current-squad-only snapshot** (~454 rows) — it structurally cannot
  resolve a historically-departed player (Harry Kane, Sergio Agüero, Diego
  Costa, …) no matter how many name-spelling fixups are added, since the
  player is simply absent from that source, not misspelled in it. Fixed by
  extending `resolve_by_name` with a third tier,
  `id_crosswalk._fpl_name_index()`, matching against **every** historical
  `player_code` `data/id_map.py` has ever recorded (2,737+ codes, not
  theFPLkiwi's ~454) — raising coverage to 1,730/1,980 distinct names
  (row-level 39.8%). A second, smaller bug (Understat's JSON leaves
  apostrophes HTML-entity-escaped, e.g. `"N&#039;Golo Kanté"`) was fixed
  with `html.unescape()` in `data/understat.py`. 78 additional
  `_NAME_FIXUPS` entries (74 multi-token nickname↔full-legal-name mappings,
  verified by requiring both Understat tokens to appear as **whole** tokens
  in exactly one `id_map` candidate — never a coincidental substring — plus
  4 individually football-knowledge-verified mononyms) closed the final gap
  for well-known nickname/full-name mismatches (Diego Costa, David Luiz,
  Cristiano Ronaldo, Rúben Neves, …). **Final coverage: 1,875/1,980 distinct
  names (94.7%), 41.2% row-level** — the remaining ~105 names are
  deliberately unresolved common mononyms (e.g. "Fred", "Jonny") where a
  second real same-era EPL player shares the identical display name and no
  season/team context is available to disambiguate safely (T-09-08-05); see
  `data/id_crosswalk.py`'s `_NAME_FIXUPS` comment for the specific
  Fred/Jonny false-positive this plan caught and declined to guess.
- ☑ **Leakage-safety, TESTED.** `config.UNDERSTAT_COLS` registered in
  `features/engineer.py::ROLL_STATS` (never `CONTEXT_COLS`) — every value
  reaches the model only through `_roll`'s `shift(1)`-then-rolling windows.
  `tests/test_leakage.py::test_understat_features_are_rolled_not_raw`
  asserts no bare `us_*` column survives in `features.parquet` and
  independently recomputes one player's `us_npxg_r5` from the raw table.
  `player_gw.parquet` stayed at 253,509 rows after the rebuild.
- ☑ **Feature-selection gate generalised.** Extracted plan 09-05's inline
  `team_strength`-only gating into a named, tested helper,
  `backtest/walk_forward.py::apply_experiment_feature_gating(df, exp)`,
  routing both `ts_*` (team_strength) and rolled `us_*` (understat) through
  one place — re-running one of plan 09-05's own tagged configurations
  (`ts_fast`) through the new helper reproduced its stored numbers exactly
  (`model+chips` 2256, `multi_safe` 2100, `multi_optimistic` 2437 — bit-for-bit
  identical), confirming the refactor changed no team_strength behaviour.
- ☑ **Fixture-level accuracy measured separately from season points, D-01's
  own stated expectation.** Reusing `backtest/benchmark_external.py`'s
  `_stats_block` MAE/Spearman helper (temporarily pointed at our own
  understat-off vs understat-on `xp_med` columns rather than theFPLkiwi's,
  no second MAE implementation written), pooled over all 6 test seasons at
  fixture level (played-only, n=66,665):

  | | MAE (`xp_med`) | Spearman (`xp_med`) |
  |---|---:|---:|
  | understat off | 1.8751 | 0.3620 |
  | understat on | 1.8761 | 0.3599 |

  Fixture-level accuracy did **not** improve — both MAE and Spearman moved
  very slightly in the wrong direction. Per-season detail in
  `data/processed/experiments/understat_mae_comparison.json`.
- **Adoption-deciding run** (`scripts/experiment_run.sh understat_adopt
  --experiments understat`, the harness's default 6 seasons/5 replicas,
  `wf_understat_adopt.json`) against the plan 09-01 baseline
  (`wf_baseline_phase9.json`):

  | metric | baseline | understat on | delta |
  |--------|---------:|--------------:|------:|
  | model+chips | 2262 | 2278 | +16 |
  | multi_safe (honest horizon) | 2147 | 2180 | +33 |

  `model+chips` moved up but stayed **2 points short of the pre-declared
  ≥2,280 primary bar** (D-05/D-06), and the identical +16 delta was already
  seen — and separately judged inconclusive — for `capt_ceiling`'s own
  adoption run in this same phase. Combined with the fixture-level MAE/
  Spearman reading directly above (essentially flat, slightly worse), the
  honest read is that this move is consistent with the harness's own
  season-to-season noise, not a genuine accuracy-driven gain — exactly the
  "better fixture MAE, season points move within noise" shape this plan's
  own objective flagged as the expected outcome (the odds-join precedent).
- **D-07 auto-adopt verdict: REJECTED.** `config.EXPERIMENTS['understat']`
  stays `False` (already the default; no flip, so no change needed to
  `tests/test_experiments.py`'s all-flags-default-off assertion). Per D-08
  all new code (`data/understat.py`, the `id_crosswalk` historical-fallback
  tier and its 78 fixups, the guarded `build_table.py`/`features/engineer.py`
  joins, `apply_experiment_feature_gating`) stays merged, nothing deleted —
  the columns are computed unconditionally and simply unused as model
  features by default.

### fotmob: per-match defensive-action counts — endpoint discovery, leakage evidence, and adoption verdict (plan 09-09)

- ☑ **Endpoints discovered and verified live, TESTED.** No FotMob endpoint
  path or schema was known before this plan (09-RESEARCH.md Open Question 2,
  assumption A4). A bounded discovery pass found two direct, unofficial JSON
  endpoints (verified 2026-09-08, no wrapper package per D-11):
  `GET /api/data/leagues?id=47&season={YYYY/YYYY}` (Premier League fixture
  list → match ids) and `GET /api/data/matchDetails?matchId={id}` (per-match
  player stats, including labelled `Tackles`/`Interceptions`/`Blocks`/
  `Clearances`/`Recoveries`/`Duels won` stat blocks). Sampled coverage check:
  all 6 sampled matches in each of the 6 walk-forward test seasons
  (2020-21..2025-26) carried these labels; pre-2020 seasons frequently do not
  (FotMob's own coverage tier drops from `xG` to `ratings`/`lower`).
- ☑ **Fetcher built matching plan 09-08's conventions.** `data/fotmob.py`:
  `FOTMOB_ENABLED` kill switch, 1.5s rate limit, on-disk cache under
  `data/raw/fotmob/`, explicit shape validation (`_require`) raising on a
  missing/mis-typed key rather than silently propagating a schema change as
  NaN (T-09-09-01). Full historical build: **146,924 player-match rows across
  11 seasons** (2016-17 through the in-progress 2026-27), cached so a re-run
  touches the network zero times.
- ☑ **Leakage-safety, TESTED.** `config.FOTMOB_COLS` registered in
  `features/engineer.py::ROLL_STATS` (never `CONTEXT_COLS`) — every value
  reaches the model only through `_roll`'s `shift(1)`-then-rolling windows.
  `tests/test_leakage.py::test_fotmob_features_are_rolled_not_raw` asserts no
  bare `fm_*` column survives in `features.parquet` and independently
  recomputes one player's `fm_tackles_r5`. `player_gw.parquet` stayed at
  253,509 rows after the rebuild; join coverage 40.4% row-level (via the
  shared `data.id_crosswalk` name resolver plan 09-08 built).
- ☑ **Feature-selection gate extended.** `backtest/walk_forward.py::apply_experiment_feature_gating`
  gained a third `fm_*` branch alongside `ts_*`/`us_*` — no new ad-hoc gating
  path added.
- ☑ **Adoption-deciding run** (`scripts/experiment_run.sh fotmob_adopt
  --experiments fotmob`, the harness's default 6 seasons/5 replicas,
  `wf_fotmob_adopt.json`) against the plan 09-01 baseline
  (`wf_baseline_phase9.json`): `model+chips` **2262 → 2263** (**+1/season**,
  well inside the harness's own season-to-season noise band, SE≈50) —
  nowhere near D-05's ≥2,280 primary bar.
- **D-07 auto-adopt verdict: REJECTED.** `config.EXPERIMENTS['fotmob']` stays
  `False` (already the default; no flip, so no change needed to
  `tests/test_experiments.py`'s all-flags-default-off assertion). Per D-08
  all new code (`data/fotmob.py`, the guarded `build_table.py`/
  `features/engineer.py` joins, the `apply_experiment_feature_gating`
  branch) stays merged, nothing deleted — the columns are computed
  unconditionally and simply unused as model features by default.

### fbref_v2: real Chrome spike — access still blocked, no new infrastructure built (plan 09-09)

- ☐ **Spiked, CONFIRMED DEAD (access failure).** Per D-04/Pitfall 1, ran a
  bounded spike before any new work: `data.fbref.scrape_to_cache(seasons=['2025-26'])`
  (equivalent to `python -m data.fbref --scrape` restricted to one season)
  against the real Chrome driver at `/usr/bin/google-chrome-stable`, on
  2026-09-08. **Three independent attempts, each run for 5-6 minutes, all
  hung indefinitely inside `driver.uc_open_with_reconnect()`** and never
  returned a page — 0 rows scraped, no `fb_tkl_int_90` coverage to report.
  A control check confirmed Chrome and the network stack work fine in this
  session (`driver.get('https://example.com')` returned instantly); a
  second control check using a *plain* (non-UC) Chrome driver against the
  same FBref URL loaded in <1s but returned Cloudflare's own
  `"Just a moment..."` interstitial (`challenges.cloudflare.com` script
  present in the page source) rather than the stats table — i.e. the site
  is still fully Cloudflare-gated, and the UC-mode bypass `data/fbref.py`
  relies on does not clear that challenge within a many-minutes window in
  this environment.
- **This is a different, and more severe, failure mode than the
  2026-08-22 finding** (`IMPROVEMENTS.md` Phase E), which got PAST
  Cloudflare and received a real page with empty stat cells (value-blanking).
  Today's access layer itself does not resolve — re-confirming
  09-RESEARCH.md's plain `curl` 403 (assumption A3 was correctly flagged as
  unverified; it does not hold, but not in the direction hoped for).
- **No new scraping-host infrastructure and no scraper container image were
  built** (D-04) — three short, bounded spike attempts is the full extent of
  the investment, per Pitfall 1's explicit warning against building
  infrastructure around a source that may not deliver values even if access
  were fixed.
- **Verdict: not acquirable this session.** `config.EXPERIMENTS['fbref_v2']`
  stays `False` (already the default; no flip, no `tests/test_experiments.py`
  change needed). Nothing in `data/fbref.py`, `config.FBREF_COLS`, or
  `features/engineer.py`'s existing wiring changed — there was nothing to
  build, only to run, and running it did not succeed.

### Enrichment experiment summary (Understat / FotMob / FBref, plan 09-09)

Of the three D-03 enrichment sources, one (Understat) produced real,
leakage-tested data that moved `model+chips` +16/season (2 short of the
D-05 bar, REJECTED); one (FotMob) required genuine endpoint-discovery work
this plan completed, produced real data across 11 seasons, and moved
`model+chips` +1/season (indistinguishable from noise, REJECTED); one
(FBref) never got past its own access layer despite three real attempts and
is recorded not-acquirable with evidence, per D-08's "never dropped
silently" rule. Read against plan 09-02's external-benchmark finding (our
`xp_med`/`xp_mean` and theFPLkiwi's projections land in the same MAE/Spearman
neighbourhood, with FPL's own `xp_fpl` ranking players better than either),
the combined picture across this phase's whole enrichment-data lever is
consistent: two real, cleanly-joined, leakage-safe feature families
(Understat, FotMob) each moved the harness by an amount indistinguishable
from its own noise floor, and the phase's honest accuracy frontier is not
gated on any single missing data source — it is gated on the model/decision
layer, exactly as this phase's other experiments (capt_ceiling, chips_v2,
team_strength, rl_strategy) also found.

### Final combined run (plan 09-10, D-13)

Command: `scripts/experiment_run.sh final_combined` → `python -m backtest.walk_forward
--tag final_combined` (6 seasons, 5 replicas — the harness's own defaults — with
`--experiments` deliberately **not** passed, so this measures the shipped default
`config.EXPERIMENTS`, never a forced flag combination). Result:
`data/processed/experiments/wf_final_combined.json`/`.csv`.

**Adopted flag set at phase close: none.** All eight flags (`capt_ceiling`,
`capt_mc`, `chips_v2`, `team_strength`, `rl_strategy`, `understat`, `fotmob`,
`fbref_v2`) stayed default-off — every experiment this phase ran was measured
and REJECTED against its own pre-declared criterion (`capt_mc` was never
triggered and `fbref_v2` was never acquirable, per their own rows above). D-13's
"the winners get one final combined run" therefore has zero winners to combine:
the final combined configuration is, by construction, identical to the phase's
opening baseline. Per this task's own instruction, that is recorded as a
legitimate and informative phase outcome, not skipped.

| season | model_mean | model+chips | capt_mean | capt_capture | multi_safe | form | hold |
|--------|-----------:|------------:|----------:|-------------:|-----------:|-----:|-----:|
| 2020-21 | 2074 | 2091 | 2071 | 0.541 | 1967 | 2077 | 1517 |
| 2021-22 | 2119 | 2305 | 2123 | 0.583 | 2312 | 2174 | 1610 |
| 2022-23 | 2148 | 2380 | 2183 | 0.563 | 2269 | 2079 | 1835 |
| 2023-24 | 2191 | 2210 | 2086 | 0.483 | 2146 | 1960 | 1741 |
| 2024-25 | 2137 | 2417 | 2260 | 0.614 | 2101 | 2107 | 2230 |
| 2025-26 | 2122 | 2172 | 2174 | 0.595 | 2086 | 1797 | 1439 |

6-season means: `model_mean` = 2132, **`model+chips` = 2262**, `capt_mean` = 2150,
`capt_capture` = 0.563, `multi_safe` = 2147, `form` = 2032, `hold` = 1729 — every
figure bit-for-bit identical to plan 09-01's `wf_baseline_phase9.json`, exactly
as expected when the config that ships after this phase and the config that
shipped before it are the same dict (`assert f['experiments'] ==
config.EXPERIMENTS` in this task's own verify).

**D-05 verdict, judged arithmetically:**

| comparator | model+chips | delta vs. final combined |
|---|---:|---:|
| measured plan 09-01 baseline (`wf_baseline_phase9.json`) | 2262 | 0 |
| D-05's quoted "current ≈2,256" | 2256 | +6 |
| D-05 primary bar | 2280 | −18 |
| **final combined (this run, `wf_final_combined.json`)** | **2262** | — |

The final combined run measures **2262 — 18 points short of the ≥2,280 primary
bar** — and, as expected, matches the measured phase baseline exactly (delta 0)
since no flag changed between the two runs. Per-season deltas against the
2,280 bar range from −70 (2023-24: 2210) to +137 (2024-25: 2417); three of the
six seasons individually clear 2,280 on their own (2021-22 2305, 2022-23 2380,
2024-25 2417) and three fall short (2020-21 2091, 2023-24 2210, 2025-26 2172)
— exactly the shape of "noisy per-season, judged on the 6-season mean" rather
than a directional signal either way.

Reading the −18 shortfall against the harness's own season-to-season spread on
`model+chips` (mean 2262, sample std ≈126, SE ≈52 over n=6 — noticeably wider
than `model_mean`'s own ±38/SE 16, since `model+chips` folds in the isolated
per-season chip-play variance on top of model noise): **the shortfall is well
inside one standard error**, and the +6 delta against D-05's quoted ≈2,256
estimate is smaller still. The honest reading is "unchanged, not regressed" —
not "close but for bad luck." No flag was adjusted to chase the bar: every
experiment's D-07 verdict was already recorded and committed by the plan that
ran it (09-03 through 09-09); this task's run only measures the configuration
those verdicts left in place.

**This phase's honest walk-forward frontier at close is the same 2,262 it
measured at open.** Every one of the six ranked experiments in
`.planning/research/XP-IMPROVEMENT-OPTIONS.md` (captaincy ceiling EV, chip
scheduler v2, team-strength ratings, RL-for-strategy, and the three enrichment
sources bundled as the sixth) was built, measured on the honest leakage-safe
6-season harness, and rejected against its own pre-declared criterion — none
moved `model+chips` outside the harness's own noise band in the improving
direction, and two (`chips_v2`, `rl_strategy`) moved it backward outside that
band. That is not a failure of this phase's own discipline: D-01 through D-16's
mechanical, pre-declared, noise-aware adoption rule did exactly its job of
refusing six real, honestly-measured negative-or-noise-band results, matching
the project's own prior history (odds and set-piece features that improved
fixture-level MAE without moving season points; the +337-optimistic-vs-+40-
honest multi-GW leakage trap) that the 2,280 bar exists to guard against, not
promise past.

### Decisions audit (plan 09-10, D-01 through D-16)

Walking `.planning/phases/09-xp-model-optimizer-improvement-experiments/09-CONTEXT.md`'s
sixteen implementation decisions in order, stating in one line how this phase
honoured each and where the evidence sits. An audit that only records
agreement is not an audit — two entries below (D-01, D-12) are honoured in
spirit rather than to the letter, and say so plainly.

- **D-01 (fixed order, run everything) — honoured in spirit, not literally.**
  The declared order is benchmark → captaincy → chips → team-strength → RL
  (gated) → enrichment. Plan 09-01 built the shared experiment spine
  (`config.EXPERIMENTS`, the harness's `--experiments`/`--seasons`/`--tag`
  CLI) **and** rode the cheapest captaincy quantile variant through it as a
  tracer, before plan 09-02 formally ran the benchmark — so that every later
  experiment had a flag and a seam to ride from day one, rather than plan
  09-01 shipping infrastructure nobody could yet use. Once that tracer
  landed, the six experiments ran in the declared order exactly (09-02
  benchmark, 09-03 captaincy, 09-04 chips, 09-05 team-strength, 09-06/09-07
  RL gated on 09-04, 09-08/09-09 enrichment), and the benchmark's own reading
  (our `xp_med`/`xp_mean` in the same MAE/Spearman neighbourhood as
  theFPLkiwi's projections) pruned nothing, per D-01's own instruction — it
  is cited as interpretive context in 09-08/09-09's summaries, never as a
  gate.
- **D-02 (RL hard-gated on chips v2) — honoured literally.** `optimize/rl_env.py`
  (09-06) was built only after 09-04 measured `chips_v2`; 09-07's adoption
  verdict required RL to beat the solver-scored scheduler on the identical
  harness (a freshly re-measured 5-season `chips_v2` figure of 2192, matching
  the seasons RL could actually train on) and it did not on any seed
  (seed-mean 2020, −172/season) — REJECTED.
- **D-03 (three enrichment sources, features only, shared crosswalk) —
  honoured literally.** Understat (09-08) and FotMob (09-09) both register
  their columns in `features/engineer.py::ROLL_STATS` (never `CONTEXT_COLS`,
  never a new sub-model); FBref (09-09) stayed a spike with no model
  integration since it never became acquirable. All three route foreign
  player names through the single `data.id_crosswalk.resolve_by_name` built
  in 09-02, extended (not replaced) by 09-08's historical-registry fallback
  tier.
- **D-04 (FBref host = local WSL Chrome outside the repo, no scraper image) —
  honoured literally.** 09-09's spike ran the pre-existing `data/fbref.py`
  against the local Chrome binary already used by earlier phases; no new
  infrastructure, container, or committed browser binary was added.
- **D-05 (primary bar ≥2,280) — honoured literally.** Measured fresh in 09-01
  (2262, not either inherited ~2,256/~2,263 estimate) and re-confirmed
  byte-for-byte by this plan's final combined run (2262) — the bar was judged
  arithmetically against the actual shipped configuration, not an estimate.
- **D-06 (full per-experiment criteria set) — honoured literally, per
  experiment.** Captaincy capture bar (09-03: +1.5pt < +2pt, rejected);
  Wildcard's isolated value measured for the first time (09-04, +14.2±9.0
  pts/gw) and no chip's isolated value allowed to regress unnoticed (bb's did,
  in 09-04's own `chips_v2` reading, contributing to that rejection);
  `tests/test_leakage.py` extended for team-strength ratings (09-05, passes);
  optimistic-vs-frozen A/B run for team-strength's horizon-touching change
  (09-05, gap +392, matching the project's own prior +337 finding) and the
  same `--optimistic-plan` capability reused by this plan's final run.
- **D-07 (mechanical auto-adopt rule) — honoured literally, six times.**
  `capt_ceiling` (09-03), `chips_v2` (09-04), `team_strength` (09-05),
  `rl_strategy` (09-07), `understat` (09-08), and `fotmob` (09-09) were each
  measured against their own pre-declared criterion and REJECTED without a
  separate human sign-off being sought — the rule's whole point (a
  mechanical flip, not a debate) held six times in a row because none
  cleared its bar.
- **D-08 (no code deletion, numbers recorded) — honoured literally.** Every
  rejected experiment's module stays in the repository (verified by this
  plan's own module-import check below); every row in the results table
  above carries a number or an evidenced reason, never a silent drop.
- **D-09 (RL stack isolated in a dev-only lockfile) — honoured literally.**
  09-06 proved (not merely asserted) that `requirements-rl.txt` is referenced
  by nothing in `Dockerfile` or any `.github/workflows/*.yml`, and that those
  files are byte-identical to before the plan.
- **D-10 (external benchmark data committed as a snapshot) — honoured
  literally.** `data/external/kiwi/` (ID map + three seasons of projection
  CSVs) plus `data/external/README.md` (source URLs, license attribution)
  landed in 09-02, reproducible with zero network access.
- **D-11 (FotMob = direct JSON endpoints, no wrapper package) — honoured
  literally.** 09-09 discovered and verified two direct, unofficial JSON
  endpoints live against the real API; no third-party FotMob client package
  was installed.
- **D-12 (blocking-human package-legitimacy gate for every new package) —
  honoured literally for new installs, correctly not re-triggered for an
  existing pin.** 09-06's four RL packages (torch, gymnasium,
  stable-baselines3, sb3-contrib) each went through the blocking-human gate
  (STATE.md: "Approve all four (Recommended)"). 09-08 needed
  `understatapi==0.7.1`, already pinned exactly in `requirements.txt` since
  an earlier phase but missing from the active conda environment — installing
  an already-approved, already-hash-locked pin is a Rule 1 bug fix
  (environment drift), not a new-package decision, so no gate was raised for
  it; this is the one place this audit calls out a literal-vs-spirit
  distinction on D-12 itself, and 09-08's own SUMMARY documents the
  reasoning explicitly rather than silently skipping the gate.
- **D-13 (independent A/Bs + one final combined run) — honoured literally.**
  Every experiment (09-03 through 09-09) ran its own independent
  adoption-deciding measurement against the plan 09-01 baseline; this plan
  (09-10) ran the single final combined measurement D-13 specifies, and the
  D-05 bar was judged against that one number, not any individual
  experiment's own reading.
- **D-14 (fast iterate, full adopt) — honoured literally.** Every sweep
  (`--capt-lambda`, `--chips-hysteresis`) ran at reduced replicas/seasons for
  speed; every adoption-deciding run and this plan's final combined run used
  the harness's full default (6 seasons, 5 replicas).
- **D-15 (local WSL only, unattended long runs with logs) — honoured
  literally.** `scripts/experiment_run.sh` (09-01) launched the great
  majority of this phase's multi-minute-to-multi-hour runs, including this
  plan's own `final_combined` run
  (`data/processed/experiments/final_combined-<timestamp>.log`). No cloud
  compute was used anywhere in this phase.
- **D-16 (RL time-boxed, fixed seeds, pinned config, declared budget) —
  honoured literally.** 09-07 declared the box (3 seeds, 30-minute
  per-policy wall-clock cap, GPU) in `IMPROVEMENTS.md` **before** launching
  any training, spent it in full (all 15 policies hit the cap), and stopped
  exactly per the pre-declared stop rule once the REJECTED verdict landed —
  no extra seeds, no extended timestep budget, no further tuning.

### What this phase did not resolve

- **The primary D-05 bar (≥2,280) was not cleared.** The phase closes at the
  same 2,262 `model+chips` it opened at (this plan's final combined run,
  above). Whether a genuinely different lever — not one of this phase's
  eight flags — could clear it is an open question for a future phase, not
  one this phase's own experiment menu was designed to answer.
- **`capt_mc` (the Monte-Carlo captaincy variant) was gated off before it was
  ever built.** Its own separate question — does full Monte-Carlo layering
  beat the cheap quantile ceiling once the ceiling direction is proven to pay
  — remains untested, since the quantile variant's own capture delta
  (+0.015) never crossed the +0.02 trigger this phase pre-declared for
  building `models/simulate.py`.
- **FBref (`fbref_v2`) remains genuinely unacquired**, and this session's
  failure mode is harder than Phase E's (a Cloudflare-gated hang, not a
  value-blanked page that got past the gate). Whether a different
  browser-automation approach — a longer timeout, a different UC-mode
  configuration, or a paid anti-bot bypass service — would succeed is
  untested and was explicitly out of this phase's budget (Pitfall 1: don't
  build infrastructure around a source that may not deliver values even if
  access were fixed).
- **`rl_strategy`'s ceiling under a materially larger compute/time budget is
  unknown.** The training-vs-held-out curves showed no divergence (no
  overfitting smoking gun) — the honest reading is that ~5,000–14,000
  timesteps over 2–4 training seasons simply wasn't enough experience for
  the policy to learn much, not that the approach is fundamentally broken.
  Whether a much larger box would let it beat `chips_v2` (itself already
  rejected) is untested and outside D-16's declared box.
- **Every REJECTED verdict this phase reached rests on judging a small
  `model+chips` delta as "within the harness's own noise band" by eye
  (comparing against an informally-estimated SE), not a pre-registered
  statistical test.** 09-08 and 09-09 both flag this explicitly in their own
  SUMMARY coverage blocks (`human_judgment: true`) for exactly this reason. A
  future phase could tighten this with a real paired significance test
  (e.g. a bootstrap over the 6 season-level observations) rather than an
  eyeballed SE comparison.
- **The external benchmark's own puzzle (09-02) is unexplained.** FPL's
  official `xp_fpl` ranks players noticeably better than our own
  `xp_med`/`xp_mean` on the same played-only common rows (pooled Spearman
  0.579 vs 0.383) despite comparable MAE. Per D-01 this informs
  interpretation only and prunes nothing — but *why* FPL's own figure ranks
  better was never investigated this phase and stays open.
- **No experiment this phase touched the model's core selection objective,
  the two-stage hurdle architecture, or feature engineering beyond three
  enrichment column families.** This phase's own repeated finding — echoed
  across 09-03 (capture, not points), 09-04/09-07 (chip/strategy layer
  regressions), 09-05/09-08/09-09 (feature-accuracy moves indistinguishable
  from noise) — is that the honest accuracy frontier is gated on the
  model/decision layer itself, not on any single missing lever this phase
  tried. No specific alternative model or decision-layer redesign was
  attempted or ruled out; that is the natural next question for a future
  phase, not an answer this one produced.

### This phase in the project's continuous history (Phases A–E)

This phase's results extend or qualify five earlier entries rather than
existing in isolation:

- **Phase C's captain-by-mean adoption** (+16/season, noisy per-season, "wins
  3/6 with two ties") is directly echoed by `capt_ceiling`'s own
  adoption-run reading this phase — the identical **+16/season** figure
  recurred at a completely different lever (upside-weighted armband value
  instead of mean-value armband). The same number showing up twice from two
  different mechanisms is itself evidence that +16 is more likely this
  harness's own noise-band width than a genuine, mechanism-specific signal —
  not a coincidence to explain away.
- **Phase C's clean-sheet sub-model rejection** (−50/season) established the
  "no new sub-model, ride the existing pipeline" discipline this phase's own
  module docstrings cite by name: `models/captaincy.py`'s post-hoc quantile
  column (09-01) and every enrichment source's `shift(1)`-then-rolled feature
  column (09-08, 09-09) both explicitly followed it rather than repeating
  that mistake.
- **Phase C's ranking-loss rejection** (−55/season) and **Phase D's true
  multi-period MILP tie** both established that added machinery does not
  reliably beat the existing myopic/pointwise setup on this harness. This
  phase found the same shape twice more at a different layer: `chips_v2`'s
  actual regression (−48/season) and `rl_strategy`'s larger one
  (−172/season) are "more sophisticated scheduling/strategy" losing to the
  simpler heuristic it tried to replace, exactly like ranking loss and the
  multi-period MILP did before it.
- **Phase E's FBref finding** (accessible but value-blanked, 2026-08-22) is
  *qualified*, not repeated, by this phase's harder failure (09-09):
  inaccessible at all this session, Cloudflare-gated even for a real
  UC-mode Chrome session that previously got through. The site's defenses
  tightened between the two attempts, not loosened.
- **Phase E's own deferred note** ("Understat npxG… low priority") is the
  option this phase actually spent real engineering effort on (09-08) and
  closed with a number (+16/season, 2 short of the D-05 bar) rather than
  leaving it deferred indefinitely.

### Addendum (2026-09-09): per-position and covered-row re-measurement of understat / fotmob accuracy

- **Why this re-measurement exists.** 09-08/09-09 measured both enrichment
  sources' fixture-level accuracy pooled over ALL positions and ALL rows.
  The model is per-position and the enrichment join is partial, so a real
  positional gain could have been diluted twice over and rejected as noise.
  `understat` was the phase's closest miss (`model+chips` 2278 vs the
  2,280 bar) — worth one cheap re-slice before the lead is closed
  permanently. Built by `backtest/enrichment_slices.py`; the full 50-cell
  grid (2 sources × 5 position slices × 5 coverage slices) is written to
  the gitignored `data/processed/experiments/enrichment_position_coverage.json`
  — the numbers below are the committed record, since the JSON itself is
  not tracked.
- **A correction to the premise, stated plainly — sharper than expected.**
  09-08's own reported raw per-match join coverage (~41% understat, ~40%
  fotmob) is measured over the WHOLE `player_gw.parquet` table, including
  every bench/unused/injured row with zero match involvement — rows
  Understat and FotMob structurally cannot have data for, since both
  sources only record players who actually featured. Restricted to the
  played-only rows this measurement (and 09-08's own MAE comparison)
  actually scores (n=66,665, identical row set), that raw per-match join
  figure is **96.2%** (understat) / **94.9%** (fotmob) — not ~41%/~40%.
  Separately, the ROLLED feature the model actually consumes
  (`us_npxg_r5`/`fm_tackles_r5`, cumulative over `shift(1)`-then-rolling
  prior matches) is present on **89.2%** (understat) / **88.1%** (fotmob)
  of the same played rows — per position: understat GK 90.8%, DEF 88.9%,
  MID 89.0%, FWD 89.4%; fotmob GK 89.2%, DEF 87.6%, MID 88.0%, FWD 88.8%.
  Two coverage definitions are reported below (`row_joined`: this exact
  fixture's own raw value is present; `feat_present`: the rolled feature is
  non-null) because they measure different things and disagree in both
  directions — a row can be `feat_present` without being `row_joined`
  (a prior match had data, this one's own raw value is missing), and here
  `row_joined` is actually the LARGER population on played rows, since the
  rolling window only looks at matches strictly before the current one and
  therefore excludes a player's own first-ever covered appearance. Net
  effect: on the population that actually gets scored, the original todo's
  "~60% of rows carry empty enrichment features" dilution concern does not
  hold at either definition — coverage on played rows is 88–96%, not ~40%.
- **The method, in three sentences.** Same leakage-safe `_preds_for` split
  as the real harness, same `apply_experiment_feature_gating` gate,
  played-only fixture rows (n=66,665, identical to 09-08's pooled row set),
  pooled across the 6 test seasons (2020-21..2025-26). Every delta carries
  a paired 95% interval: a normal interval on the per-row absolute-error
  difference for MAE, a 200-resample paired bootstrap for Spearman. The
  pre-declared signal rule: a cell counts as a real gain only when the MAE
  delta's upper bound is below zero AND the Spearman delta's lower bound is
  above zero — both axes must clear their own interval, not just move in
  the right direction.
- **The reproduction check.** The pooled understat `ALL`/`all` cell
  reproduces 09-08's published numbers exactly: MAE 1.8751 (off) / 1.8761
  (on), Spearman 0.3620 (off) / 0.3599 (on) — `n=66,665` in both, absolute
  difference 0.0000 on all four figures. `features.parquet` has been
  rebuilt since 09-08 (09-09 added the `fm_*` family), but that changes
  nothing about the `off` feature set `apply_experiment_feature_gating`
  produces, and the exact reproduction confirms it.
- **The results, `row_joined` (covered-rows-only) slice:**

  **understat** (n=66,665 played rows; `row_joined` = this fixture's own
  raw `us_npxg` is present)

  | position | n | MAE off | MAE on | ΔMAE [95% CI] | ΔSpearman [95% CI] |
  |---|---:|---:|---:|---:|---:|
  | GK | 4,522 | 2.1422 | 2.1444 | +0.0022 [-0.0047, 0.0091] | +0.0154 [-0.0022, 0.0357] |
  | DEF | 21,681 | 2.0713 | 2.0723 | +0.0011 [-0.0017, 0.0038] | -0.0058 [-0.0088, -0.0023] |
  | MID | 29,814 | 1.6777 | 1.6776 | -0.0002 [-0.0017, 0.0014] | +0.0025 [0.0003, 0.0045] |
  | FWD | 8,124 | 1.9779 | 1.9810 | +0.0032 [-0.0017, 0.0080] | -0.0031 [-0.0092, 0.0014] |
  | ALL | 64,141 | 1.8815 | 1.8823 | +0.0008 [-0.0006, 0.0022] | -0.0019 [-0.0037, -0.0001] |

  **fotmob** (n=66,665 played rows; `row_joined` = this fixture's own raw
  `fm_tackles` is present)

  | position | n | MAE off | MAE on | ΔMAE [95% CI] | ΔSpearman [95% CI] |
  |---|---:|---:|---:|---:|---:|
  | GK | 4,434 | 2.1443 | 2.1551 | +0.0108 [0.0044, 0.0171] | -0.0080 [-0.0232, 0.0086] |
  | DEF | 21,314 | 2.0734 | 2.0752 | +0.0019 [-0.0006, 0.0044] | +0.0015 [-0.0014, 0.0043] |
  | MID | 29,448 | 1.6884 | 1.6886 | +0.0002 [-0.0013, 0.0017] | -0.0001 [-0.0020, 0.0021] |
  | FWD | 8,063 | 1.9873 | 1.9892 | +0.0019 [-0.0029, 0.0068] | -0.0035 [-0.0084, 0.0017] |
  | ALL | 63,259 | 1.8881 | 1.8899 | +0.0017 [0.0004, 0.0031] | -0.0004 [-0.0022, 0.0012] |

  `feat_present` headline (rolled feature actually consumed by the model):
  understat pooled `ALL` n=59,453, MAE 1.8927→1.8936 (ΔMAE +0.0009
  [-0.0006, 0.0024]), Spearman ΔSpearman -0.0021 [-0.0040, -0.0001];
  fotmob pooled `ALL` n=58,703, MAE 1.8996→1.9013 (ΔMAE +0.0017 [0.0003,
  0.0032]), Spearman ΔSpearman -0.0007 [-0.0028, 0.0014]. Same shape as
  `row_joined`: small, mixed-sign deltas, no position clears the bar.
- **The verdict: no cell reached signal.** Across the full 50-cell grid (2
  sources × 5 position slices × 5 coverage slices), zero cells satisfy
  `d_mae_hi < 0.0 AND d_spearman_lo > 0.0`. The closest thing to a
  positional lean is understat's MID/`row_joined` cell (ΔMAE -0.0002,
  interval [-0.0017, 0.0014] — crosses zero) and fotmob has no position
  with a negative ΔMAE at all in `row_joined` (every position's on-column
  is flat-to-worse). This is a real null result, reported plainly, not a
  failure of the measurement: the per-position, per-coverage re-slice
  motivates no follow-up flag variant. `config.EXPERIMENTS['understat']`
  and `config.EXPERIMENTS['fotmob']` both stay `False` — this addendum
  adopts nothing.
- **The multiple-comparison caveat.** 50 cells were tested at 95%, so
  roughly 2–3 cells would be expected to reach "signal" by chance alone
  even if neither source had any real per-position effect. Zero cells
  reaching signal here is therefore a stronger null than "no signal found"
  would be on a single test — it is below the chance-alone expectation.
  Any single flagged cell in a future re-run of this kind would still be a
  lead to re-test on the season-points harness, never a result on its own.
- **Tying this to the phase's own open weakness.** IMPROVEMENTS.md's "What
  this phase did not resolve" section (above) records that every Phase 9
  REJECTED verdict rested on eyeballing a delta against an informally
  estimated SE rather than a pre-registered statistical test. These paired
  intervals are a first, narrow instalment on that gap — narrow because
  they test fixture-level accuracy (MAE/Spearman on `xp_med`), not the
  season-points metric (`model+chips`) the ≥2,280 adoption bar is actually
  written against. A pre-registered test on the season-points metric itself
  remains the larger, unaddressed version of that gap.

### Addendum (2026-09-09): capt_ceiling paired intervals — high-replica re-run settled on a different axis (extends plan 09-03)

- **What plan 09-03 concluded, and on what evidence.** The adoption run
  measured `capt_capture` 0.563 → 0.578 (a **+1.5 percentage-point** absolute
  move) and `model+chips` 2262 → 2278 (**+16/season**), both at the harness's
  default of 5 replicas, both judged against an **informally estimated
  SE≈16** rather than a computed one. D-06's criterion (**≥+2pt absolute**
  capture) was not cleared, and the verdict was REJECTED.
- **The replica finding: `--replicas` cannot settle this, and the 25×
  re-run proves it.** `--replicas` (`backtest/walk_forward.py:241`, default
  5) feeds exactly one thing — the jittered `totals` list comprehension at
  `walk_forward.py:298-300`, which produces only `model_mean`/`model_std`.
  Every metric `capt_ceiling` is capable of moving comes from a single,
  UNJITTERED `run_season` call: `model+chips` from the `chips_df` call
  (`walk_forward.py:302-304`), `capt_mean`/`capt_capture` from the `cdf` call
  (`walk_forward.py:306-308`). Raising `--replicas` therefore cannot move
  either number — it was never the axis that could answer this question.
  This is not a code-reading claim left untested: both arms were re-run at
  `--replicas 25` against the unmodified harness (2025-26, `wf_base_r25`
  / `wf_capt_r25`) and compared to the existing 5-replica results:

  | metric | r=5 (baseline / adopt) | r=25 (baseline / adopt) | moved? |
  |---|---|---|---|
  | `model+chips`  | 2172 / 2293 | 2172 / 2293 | no |
  | `capt_mean`    | 2174 / 2185 | 2174 / 2185 | no |
  | `capt_capture` | 0.595 / 0.619 | 0.595 / 0.619 | no |
  | `model_mean`   | 2122 / 2122 | 2112 / 2112 | **yes** |
  | `model_std`    | 21 / 21 | 68 / 68 | **yes** |

  `model+chips`, `capt_mean` and `capt_capture` are byte-identical between 5
  and 25 replicas for both arms, exactly as F1 predicted; only the two
  replica-averaged columns move. This is the correction to the originating
  todo's own proposed method (a 25×, 6-season, 2-arm re-run) — that re-run
  was executed on one season specifically to demonstrate the mechanism, not
  spent six-fold chasing numbers F1 shows cannot change. The real answer had
  to come from a different axis: a paired interval over the season-level
  deltas already sitting in the two committed Phase 9 result CSVs.
- **The paired intervals, computed by `backtest/capt_ceiling_ci.py` over all
  six test seasons** (reproducing plan 09-03's published `wf_baseline_phase9.csv`
  / `wf_capt_ceiling_adopt.csv` rows exactly before any new interval was
  trusted):

  | season | capture off | capture on | capt_mean off | capt_mean on | model+chips off | model+chips on |
  |---|---:|---:|---:|---:|---:|---:|
  | 2020-21 | 0.541 | 0.567 | 2071 | 2118 | 2091 | 2147 |
  | 2021-22 | 0.583 | 0.569 | 2123 | 2041 | 2305 | 2277 |
  | 2022-23 | 0.563 | 0.551 | 2183 | 2107 | 2380 | 2350 |
  | 2023-24 | 0.483 | 0.491 | 2086 | 2090 | 2210 | 2202 |
  | 2024-25 | 0.614 | 0.670 | 2260 | 2289 | 2417 | 2399 |
  | 2025-26 | 0.595 | 0.619 | 2174 | 2185 | 2172 | 2293 |

  | metric | mean Δ | season-clustered 95% CI (n=6, GOVERNS) | gameweek-bootstrap 95% CI (n=227, optimistic) | excludes 0? |
  |---|---:|---|---|---|
  | capt_capture | +0.0146 | [−0.0131, +0.0423] | [−0.0090, +0.0412] | no |
  | capt_mean | −11.2 | [−68.5, +46.2] | [−235.0, +98.0] | no |
  | model+chips | +15.5 | [−48.2, +79.2] | [−250.0, +433.0] | no |

  The season-clustered family is a paired two-sided t-interval (df = 5) on
  the six per-season on-minus-off deltas; the gameweek family is a
  percentile interval from a paired cluster bootstrap resampling
  (season, gameweek) pairs WITH REPLACEMENT, stratified within season,
  recomputing the ratio-of-sums (for `capt_capture`) or the sum (for
  `capt_mean`/`model+chips`) each of 10,000 draws — never a per-gameweek
  ratio averaged after the fact.
- **The verdict, driven by the season-clustered family: REJECTION CONFIRMED,
  now on a stated statistical test.** `capt_capture`'s 95% CI
  [−0.0131, +0.0423] straddles zero, so the +1.5pt reading is not
  distinguishable from measurement noise at this sample size — it does not
  even clear the much weaker "excludes zero" bar, let alone D-06's ≥+2pt
  threshold. `model+chips`'s CI [−48.2, +79.2] also straddles zero. Most
  tellingly, `capt_mean` — the captaincy arm's OWN season points, not a
  proxy — has a **negative** mean delta (−11.2/season): the capture-ratio
  gain the arm shows does not convert into more points on the metric that
  actually pays a manager. A capture gain riding alongside a points loss is
  exactly the reading a bar revision would have to survive, and it does not
  survive here. `config.EXPERIMENTS['capt_ceiling']` stays `False`;
  `capt_mc` (`models/simulate.py`, still unbuilt) stays ungated — plan
  09-03's Branch B non-decision stands.
- **Caveats.** (1) Gameweeks within a season are NOT independent — squad
  state carries across gameweeks through transfers — so the gameweek-level
  bootstrap interval is the higher-power but OPTIMISTIC reading and does not
  govern; it is reported for context only. (2) `capt_col` reaches the ILP as
  the `xp_capt` objective column (`optimize/squad_ilp.py:42,63`), so the two
  arms select DIFFERENT squads, not merely a different armband on one squad
  — the pairing unit is (season, gameweek), not (season, gameweek, squad).
  These deltas measure the whole capt_col-in-the-ILP-objective change, not
  an isolated captain pick; do not read them as an isolated armband effect.
- **Tying this back.** This is the second instalment (after the 2026-09-09
  understat/fotmob addendum above) on "What this phase did not resolve"'s
  recorded gap that every REJECTED verdict rested on an eyeballed delta
  against an informal SE. Unlike that instalment — which tested
  fixture-level MAE/Spearman — this one tests the season-points metric
  (`capt_capture`, `capt_mean`, `model+chips`) the ≥+2pt D-06 bar is
  actually written against, and reaches the same REJECTED verdict on a
  stated statistical test rather than an eyeballed one.

### Addendum (2026-09-09): rl_strategy v2 — 4x training budget, still rejected, with a dose-response reading (extends plan 09-07)

- **Declared before training** (todo `2026-09-09-rl-v2-bigger-timestep-run.md`, committed
  `da8227a` prior to launch, D-16 discipline): same 3 seeds (0/1/2), same 5 trainable
  seasons, same pure realised-points reward, per-policy wall-clock cap raised 30 → **120
  minutes**, outputs isolated in `data/processed/experiments/rl_v2_policies/` so plan
  09-07's recorded v1 policies were never overwritten (restored to `models/artifacts/`
  after the eval).
- **Box spent as declared.** All 15 policies hit the 120-min cap (`capped: true` in every
  sidecar); later-season timesteps reached ~51-53k vs v1's 13-14k — the intended ~4x
  experience. Training logs: `rl_v2_train_seed{0,1,2}.log`.
- **Adoption-deciding runs** (`wf_rl_v2_adopt_seed{0,1,2}.json`, 5 seasons x 5 replicas,
  `--experiments rl_strategy --rl-seed N`, eval log `rl_v2_eval-20260909T153101Z.log`):

  | arm | model+chips |
  |---|---:|
  | rl v2 seed 0 | 2140 |
  | rl v2 seed 1 | 2087 |
  | rl v2 seed 2 | 2065 |
  | **rl v2 seed-mean** | **2097** |
  | rl v1 seed-mean (30-min box, plan 09-07) | 2020 |
  | chips_v2 same-5-season reference (`wf_chips_v2_5season`) | 2192 |
  | v1 heuristic same-5-season baseline (`wf_baseline_5season`) | 2272 |

- **Verdict: REJECTED (D-02 bar not met).** Every v2 seed individually loses to the
  solver-scored scheduler (best seed 2140 vs 2192, seed-mean gap −95/season), and all
  remain far below the v1 heuristic baseline (2272). `config.EXPERIMENTS['rl_strategy']`
  stays `False`; no product or config change.
- **The honest dose-response reading.** Quadrupling the training budget moved the
  seed-mean +77 (2020 → 2097) and tightened the seed spread (297 → 75) — the policy is
  genuinely learning, not stuck at initialization as v1's reading suggested. But linear
  extrapolation of that slope (~+77 per 4x budget, with diminishing returns expected)
  puts break-even with the solver several more quadruplings away (multi-day GPU runs per
  policy), for a scheduler that would at best match a solver we already have. This
  addendum therefore settles the RL-for-strategy direction more firmly than plan 09-07
  could: the constraint is not merely budget, it is the exchange rate between compute
  and points. The reward-shaping notes todo (potential-based shaping) remains on file
  for any future revisit, but no further RL time-boxes are recommended this milestone.

### Addendum (2026-09-09): ep_next as a model feature — provenance-tainted, both arms rejected (extends the benchmark section above)

- **The todo's own premise was half wrong.** The todo and `models/train.py`'s own
  `_EXCLUDE` comment both say `xp_fpl` (FPL's `ep_this`/`ep_next` field, mapped in
  `config.py`) is "evaluation baseline only, not a feature". That is true only of the
  LITERAL column. `features/engineer.py` has listed `"xp_fpl"` in `ROLL_STATS` since
  before this task, so `features.parquet` already carries `xp_fpl_r3`, `xp_fpl_r5`,
  `xp_fpl_r10` and `xp_fpl_rall` — four lagged rolling means of FPL's own expected-points
  figure have been live model features all along. **"Feed lagged ep_next" needed no new
  work.** The only genuinely new signals this task could add were (a) the strict
  previous-fixture value (a `shift(1)`, not a rolling mean) and (b) the SAME-FIXTURE
  value — exposed behind two new default-off flags, `ep_next_lag` and `ep_next_now`
  (`config.EXPERIMENTS`), added by `backtest/walk_forward.py`'s
  `apply_experiment_feature_gating` as derived columns `xp_fpl_lag1`/`xp_fpl_now`.
- **What the column is, and how much of it exists.** Comparing vaastav's final-gameweek
  `xP` column against the end-of-season bootstrap's `ep_this`: exact match for **100.0%**
  of players in 2022-23/2023-24/2024-25 (vs 11–14% at GW1) — this is a genuine
  per-gameweek capture of FPL's live `ep_this` field, not a season constant. Coverage is
  broken in two ways: `xp_fpl` is **100% null for 2016-17 through 2019-20** (four of the
  eight training seasons), and whole gameweeks are captured as an identical `0.0` across
  every row — an outage written as a false zero, not a null:

  | season | outage gameweeks (all-zero) | zero-share (non-outage gws) |
  |---|---:|---:|
  | 2020-21 | 1 (gw35) | 0.295 |
  | 2021-22 | 0 | 0.308 |
  | 2022-23 | 2 (gw12, gw36) | 0.364 |
  | 2023-24 | 1 (gw26) | 0.417 |
  | 2024-25 | 3 (gw22, gw32, gw34) | 0.379 |
  | 2025-26 | **27 of 38** | 0.386 |

  2025-26 — the most recent test season — is mostly a fabricated zero if used raw. The
  gate (`backtest/ep_next_provenance.py`'s coverage census, reproduced exactly by
  `apply_experiment_feature_gating`) nulls out any (season, gw) group that is 0.0/null
  for EVERY row before deriving either signal, so an outage gameweek can never enter the
  model as a confident zero — a mixed zero/non-zero gameweek (the genuine ~30-42%
  pre-deadline zero mass) is left untouched.
- **The provenance verdict — the decisive test, and it does NOT exonerate the column.**
  A low `P(played | xp_fpl==0)` on its own looks like hindsight, but genuine pre-deadline
  zeros also cluster on truly-unlikely-to-play players, so that number alone does not
  settle it. `backtest/ep_next_provenance.py` instead compares the historical figure
  against a KNOWN-pre-deadline control: this repo's own `data/snapshots/*.parquet` (the
  daily cron, captured at a known `ts_utc` strictly between gameweeks), joined to that
  gameweek's realised minutes in `data/raw/live/element_history.parquet`.

  | | P(played \| ep==0) | 95% CI (Wilson) | n |
  |---|---:|---|---:|
  | historical, pooled non-outage gws (2020-21..2025-26) | 0.0229 | [0.0216, 0.0243] | 48,671 zero-ep rows |
  | control: `data/snapshots/2026-08-31.parquet` (next_gw=3, ts_utc 12:37 UTC) | 0.0815 | [0.0544, 0.1203] | 270 zero-ep rows |

  The control's interval sits entirely ABOVE the historical pooled interval — no
  overlap. A genuine pre-deadline capture is materially LESS certain a zero-ep player
  will actually not play (8.15%) than the historical column claims to be (2.29%): the
  historical column is more confident than an honest forward-looking snapshot could be,
  consistent with hindsight contamination. **Verdict: NOT exonerated.** (The second
  snapshot, `2026-09-07.parquet`, next_gw=4, is honestly reported as `covered: False` —
  gw4 has no realised minutes yet — rather than dropped silently; the control is
  therefore n=270 from ONE covered snapshot, a small control, stated as such.) Per the
  pre-declared rule (T-elx-01), this makes the same-fixture arm (`ep_next_now`) a
  diagnostic upper bound only, never an adoption case, regardless of what it scores
  below.
- **The adoption run (6 seasons, 5 replicas, `data/processed/experiments/wf_ep_next_lag.csv`
  / `wf_ep_next_now.csv`, paired intervals via `backtest.capt_ceiling_ci.paired_t_interval`,
  reused rather than reimplemented):**

  | season | model+chips base | +lag | +lag+now | multi_safe base | +lag | +lag+now |
  |---|---:|---:|---:|---:|---:|---:|
  | 2020-21 | 2091 | 2091 | 2091 | 1967 | 1967 | 1967 |
  | 2021-22 | 2305 | 2305 | 2305 | 2312 | 2312 | 2312 |
  | 2022-23 | 2380 | 2316 | 3395 | 2269 | 2054 | 3316 |
  | 2023-24 | 2210 | 2110 | 3971 | 2146 | 2143 | 3791 |
  | 2024-25 | 2417 | 2370 | 3906 | 2101 | 2243 | 3552 |
  | 2025-26 | 2172 | 2147 | 2627 | 2086 | 2158 | 2488 |
  | **mean** | **2262** | **2223** | **3049** | **2147** | **2146** | **2905** |

  | arm | metric | mean Δ | season-clustered 95% CI (n=6, GOVERNS) | clears own zero? |
  |---|---|---:|---|---|
  | ep_next_lag | model+chips | −39.3 | [−80.4, +1.7] | no |
  | ep_next_lag | multi_safe | −0.7 | [−126.2, +124.9] | no |
  | ep_next_now | model+chips | +786.7 | [−4.6, +1577.9] | no (barely) |
  | ep_next_now | multi_safe | +757.5 | [−3.1, +1518.1] | no (barely) |

  2020-21 and 2021-22 show an EXACT zero delta on every arm: for those two test seasons
  `_preds_for`'s own train window (`DATA_SEASONS[:i-1]`) is entirely the four fully-null
  seasons, so LightGBM never sees a single non-null value of either derived column during
  training and cannot split on it — this is the masking/lag gate behaving correctly, not
  a bug. The moment the train window first includes a season with real coverage
  (2020-21, for test season 2022-23 onward), `ep_next_now`'s effect explodes: model+chips
  triples the baseline gap size on 2023-24 alone (2210→3971). This magnitude — not a
  modest edge, a near-doubling of realistic season points — is itself corroborating
  evidence for the provenance verdict above, not a separate finding to weigh against it.
- **Verdict, applied mechanically (D-05/D-07), THEN gated by provenance (T-elx-01):**
  - `ep_next_lag` (decision-time-safe by construction — a strict `shift(1)`): mean
    model+chips 2223 **does not clear** the ≥2,280 D-05 bar, and D-07 fails outright
    (model+chips regresses, multi_safe is flat). **REJECTED** — the safe half of the
    todo's ask genuinely does not help. `config.EXPERIMENTS['ep_next_lag']` stays `False`.
  - `ep_next_now` (same-fixture): mean model+chips 3049 mechanically CLEARS the ≥2,280
    D-05 bar by a wide margin, and multi_safe also "holds" (2905 vs 2147) — read
    naively, this is the best single-flag result recorded anywhere in this phase. It is
    rejected anyway, because the provenance test above found the very feature driving
    this result behaves as if it knows the outcome before it happens. A number this
    large, appearing only once the training window contains real (leakage-consistent)
    data, is the signature of exactly the failure this task's threat register was written
    to catch (T-elx-01), not a genuine model improvement. **REJECTED — unadoptable
    regardless of the mechanical bar.** `config.EXPERIMENTS['ep_next_now']` stays `False`.
- **The benchmark re-score** (`backtest/benchmark_external.py`'s new `--experiments`
  option, closing F7's gap that this module never gated at all; played-only pooled rows
  over the two seasons theFPLkiwi covers, 2021-22/2022-23, n=17,488 in every run):

  | run | xp_med MAE | xp_med Spearman | xp_fpl Spearman (same run) |
  |---|---:|---:|---:|
  | fresh all-off baseline (`--experiments none`) | 1.978 | 0.383 | 0.579 |
  | +ep_next_lag | 1.976 | 0.383 | 0.579 |
  | +ep_next_lag+ep_next_now | 1.753 | 0.516 | 0.579 |

  The fresh all-off baseline reproduces the originally published 0.383/0.579 pooled pair
  exactly, per season and pooled — a useful confirmation, though F7's own caution stands
  for any future rebuild that changes `features.parquet` again: this run, not the
  original 09-02 one, is what a later re-score should compare against. `ep_next_lag`
  moves the ranking metric by 0.000 pooled — consistent with the season-points reading
  above, this signal simply is not there once training only sees decision-time-known
  values. `ep_next_now` moves pooled Spearman from 0.383 to 0.516 — real movement toward
  `xp_fpl`'s own 0.579, but the per-season breakdown shows why it does not count as
  closing the gap: 2022-23 alone jumps from 0.386 to **0.688**, SURPASSING `xp_fpl`'s own
  0.558 figure for that season. A derived feature outranking the very column it was
  copied from, on the one test season where the training window first contains real
  coverage, is the same leakage signature as the season-points result — not the model
  becoming a better forecaster than FPL's own team.
- **The availability half of the todo is not measurable — this is a measured absence, not
  a judgement call.** `chance_of_playing_this_round`, `chance_of_playing_next_round`,
  `status` and `news` appear ONLY in `players_raw.csv`, a single END-OF-SEASON snapshot
  (rows == unique player ids). Two other candidate sources were checked and neither
  carries it: `merged_gw.csv` (36–46 columns across the seasons checked, none
  availability) and this repo's own self-hosted `data/raw/live/element_history.parquet`
  (21 columns, none availability). There is no per-gameweek availability signal for any
  past season anywhere in this repo; using the season-final value per gameweek would
  apply an end-of-season injury flag retroactively to every gameweek of that season, which
  is worse than no feature. **The forward path already exists and has started:**
  `data/snapshots/*.parquet` has captured `status`, `chance_of_playing_next_round`,
  `ep_this`, `ep_next`, `next_gw` and `ts_utc` daily since 2026-08-31 (2 files so far —
  the same snapshots this addendum's own provenance control used). Roughly one 2026-27
  season of accumulation makes a per-gameweek availability panel constructible; the daily
  cron (Phase 6) is the thing that must keep running for that to happen. No feature or
  number is invented for this half.
- **Caveats.** (1) The season-clustered t-interval (n=6) is the governing family, per the
  260909-dga addendum's own precedent — both arms' intervals technically straddle zero at
  95% despite `ep_next_now`'s huge point estimate, because 2020-21/2021-22 contribute an
  exact-zero delta each (diluting the mean and widening the interval) for the structural
  reason explained above, not because the signal is weak once it actually engages. (2)
  The benchmark re-score covers only the two seasons theFPLkiwi's committed snapshot
  covers (2021-22, 2022-23) — 2022-23 is also the FIRST test season where `ep_next_now`'s
  training window includes real coverage, so this 2-season read is not independent
  confirmation of the season-points result; it shares the same root cause. (3) This is
  the third instalment on "What this phase did not resolve"'s recorded external-benchmark
  puzzle (why does `xp_fpl` rank players better than our own model) — after this
  addendum, the honest answer is still "unexplained by a safe feature", since the only
  candidate that moved the gap turned out to be leakage.
- **Closing.** Both `config.EXPERIMENTS['ep_next_lag']` and `['ep_next_now']` stay
  `False` under every reading above — there is no adoption case here, mechanical bar or
  not, and none is being presented to the user. If a future daily-cron accumulation
  (12+ months) produces a large enough known-pre-deadline control to narrow the
  provenance interval, this verdict is the one to revisit first.

### Declared time-box (2026-09-09, written before training): rl_strategy v3 single-season overnight extension

User-directed extension of the v2 dose-response reading: **one season (2025-26), 3 seeds
(0/1/2) in parallel, 540 minutes (9h) per policy, `--timesteps 400000`** (raised so the
wall-clock box stays the binding budget), same pure realised-points reward, outputs in
`data/processed/experiments/rl_v3_policies/` (v1/v2 artifacts untouched). Stop rule:
when the box is spent, evaluate as-is on the same-season adoption comparison
(`wf_rl_v3_adopt_2025-26_seed{N}`) against the season's recorded v2 seed scores and the
solver reference; no extension, no extra seeds. Purpose: extend the measured
compute→points curve (30min→v1, 120min→v2, 540min→v3) by one more point on the
best-covered season.

### Addendum (2026-09-10): rl_strategy v3 — 9h single-season run: beats the solver scheduler, still loses to the shipped heuristic

Box spent exactly as declared above (3 seeds x 540 min on 2025-26, all `capped: true`,
~237-248k timesteps each — ~5x v2's per-policy experience). Adoption evals
`wf_rl_v3_adopt_2025-26_seed{0,1,2}.json` (1 season x 5 replicas each); all 2025-26
references from the same harness:

| arm (2025-26 only) | model+chips |
|---|---:|
| v1 heuristic scheduler (shipped default, `wf_baseline_5season`) | **2237** |
| **rl v3 seed-mean (540-min box)** | **2140** (2116 / 2187 / 2117) |
| chips_v2 solver-scored scheduler (`wf_chips_v2_5season`) | 2101 |
| rl v2 seed-mean (120-min box) | 2059 (2046 / 2117 / 2014) |
| rl v1 seed-mean (30-min box) | 1985 (1898 / 1898 / 2160) |

- **The notable crossing:** every v3 seed individually beats the solver-scored
  scheduler on this season (worst seed 2116 vs 2101) — the literal D-02 bar
  ("beat chips_v2") is met for the first time, on this one season. But chips_v2 was
  itself rejected for losing to the v1 heuristic, and v3 still trails that shipped
  default by **−97** (2140 vs 2237), so nothing is adoptable: replacing the v1
  scheduler with the v3 policy would cost points.
- **The compute→points curve, third point (2025-26 seed-means):** 30 min → 1985,
  120 min → 2059 (+74), 540 min → 2140 (+81). Strikingly log-linear: each ~4.5x
  compute multiplication buys roughly +75-80 points. Extrapolating the SAME rate
  (optimistic — diminishing returns are the norm), closing the remaining −97 to the
  v1 heuristic needs one to two more quadruplings: ~40 hours to multiple days of GPU
  per policy, to at best MATCH a zero-cost heuristic. Single-season caveats apply
  (n=1 season, season std ≈55, seed spread 71).
- **Verdict: still REJECTED for adoption** (`config.EXPERIMENTS['rl_strategy']`
  stays `False`), but the finding is upgraded from "RL loses" to "RL learns on a
  clean log-linear curve whose exchange rate is uneconomical." If GPU-hours ever
  become free-tier abundant, this curve is the business case to re-open — and the
  measured crossing over chips_v2 means the policy's ceiling is not obviously below
  solver-level scheduling. v1/v2/v3 policy artifacts all preserved
  (`models/artifacts/` + `rl_v2_policies/` + `rl_v3_policies/`; v1's 2025-26 pair
  restored from `rl_v1_2025-26_backup`).

## Phase G — xP experiment follow-ups (Phase 10)

Phase 10 pursues Phase 9's own measured leads under the same honest-harness
discipline: every experiment lands opt-in behind a `config.EXPERIMENTS` flag,
defaulted off, judged by `backtest/walk_forward.py`'s unflagged-reproduces-
baseline contract — never a bespoke ad-hoc switch. This section locks every
Phase 10 adoption criterion in writing before any run in this phase measures
anything against them (T-10-01-05).

### Declared criteria (2026-09-10, written before any Phase 10 adoption run)

- **Primary bar (unchanged):** 6-season mean `model+chips` >= **2,280** against
  the measured **2,262** Phase F baseline.
- **D-09 availability dual criterion, BOTH required:** (a) 2025-26 walk-forward
  `model+chips` improves by >= **+25** points; (b) pooled played-only
  `spearman_xp_med` on `backtest.benchmark_external`'s EXP-1 basis improves by
  >= **+0.03** over the **0.383** baseline. The 2025-26 coverage this criterion
  is judged on comes from the D-05 vendored FPL-Core-Insights backfill, **not**
  from our own daily snapshots — those start in season 2026-27 and
  `backtest/walk_forward.py::DATA_SEASONS` drops 2026-27 entirely, so our own
  captured snapshots have zero walk-forward coverage on their own.
- **D-02 news-sentiment trigger:** after BOTH Tier-1 experiments, if pooled
  played-only `spearman_xp_med` is **< 0.500** the news-sentiment experiment
  gets built; if **>= 0.500** it is recorded not-triggered (the `capt_mc`
  precedent — a numbered, evidenced non-decision, not a silent skip). The
  0.383 -> 0.579 arithmetic midpoint (the two pooled Spearman figures already
  on record in this file's Phase F benchmark table) is **0.481**; the binding
  number is **0.500** — D-02's own stated figure, made exact.
- **D-15 bracket cheap gate:** a model-class-bracket candidate advances only if
  its val-split played-only Spearman >= LightGBM's own on the same split **+
  0.010**; MAE is recorded as a diagnostic alongside it and is never itself a
  gate.
- **D-11 split verdicts:** the final combined run (10-16) includes only
  full-coverage winners and is judged on >= 2,280; the availability
  experiment carries its own dual-criterion verdict (D-09, above) recorded
  separately — no apples-to-oranges combination of the two.
- **D-13 compute budget:** 200 Colab Pro units total plus open-ended local
  overnights; recurrent and transformer candidates run on Colab,
  Ridge/XGBoost/CatBoost/MLP run local (WSL); hard stop at unit exhaustion,
  consumption recorded per candidate.
- **D-19 tuning budget:** 12 configs per deep candidate per granularity
  variant, hard stop, logged like `models/tune.py`; XGBoost/CatBoost get
  sensible LightGBM-adjacent defaults only (asymmetric per D-19).
- **D-10:** no availability flag may be flipped default-on until the
  missing-snapshot NaN fallback is asserted by a passing test —
  `tests/test_availability.py::test_missing_snapshot_degrades_to_nan_not_raise`
  (plan 10-01, this phase).

### Experiment results (Phase 10)

| flag | criterion | measured | verdict | default |
|------|-----------|----------|---------|---------|
| availability_flags | D-09 dual criterion: 2025-26 model+chips +25, pooled played-only Spearman +0.03 over 0.383 | 2025-26 model+chips 2172->2172 (+0, need +25); pooled Spearman 0.3832->0.3832 (+0.0000, need +0.03) | REJECTED (dual criterion, neither leg met) | off |
| transfermarkt_injury | model+chips contribution measured via the harness | 6-season model+chips 2262->2242 (-20, need >=2280) | REJECTED | off |
| news_sentiment | D-02 conditional build; if built, model+chips contribution measured via the harness | pending | pending | off |
| bracket_ridge | D-15 cheap gate: val played-only Spearman >= LightGBM + 0.010 | pending | pending | off |
| bracket_xgb | D-15 cheap gate: val played-only Spearman >= LightGBM + 0.010 | pending | pending | off |
| bracket_catboost | D-15 cheap gate: val played-only Spearman >= LightGBM + 0.010 | pending | pending | off |
| bracket_mlp | D-15 cheap gate: val played-only Spearman >= LightGBM + 0.010 | pending | pending | off |
| bracket_rnn | D-15 cheap gate: val played-only Spearman >= LightGBM + 0.010 | pending | pending | off |
| bracket_transformer | D-15 cheap gate: val played-only Spearman >= LightGBM + 0.010 | pending | pending | off |

Every row starts `pending`; each plan in this phase fills its own row as it
measures it, and plan 10-16 confirms none remain — matching the Phase F
table's own closing discipline.

### availability_flags: dual-criterion adoption verdict (plan 10-08)

- **Commands run.** `scripts/experiment_run.sh avail_base_2526 --seasons 2025-26 --replicas 5`
  and `scripts/experiment_run.sh avail_on_2526 --seasons 2025-26 --replicas 5 --experiments availability_flags`
  (artifacts `data/processed/experiments/wf_avail_base_2526.json` /
  `wf_avail_on_2526.json`); `python -m backtest.benchmark_external --experiments none --tag tier1_base`
  and `--experiments availability_flags --tag tier1_avail` (artifacts
  `benchmark_tier1_base.json` / `benchmark_tier1_avail.json`). All four run
  against the frozen `features.parquet` Task 1 recorded
  (sha256 `ae809b5b6169ee776363e543fd6c50e78017cf1f36e1c3742807feb16336dc3f`,
  253,509 rows x 172 columns) — verified unchanged (byte-identical hash) at
  measurement time.
- **D-09 dual criterion, BOTH required:**

  | leg | base | flag on | delta | bar | met? |
  |---|---:|---:|---:|---:|:--:|
  | (a) 2025-26 `model+chips` | 2172 | 2172 | +0 | >= +25 | NO |
  | (b) pooled played-only `spearman_xp_med` (2021-22, 2022-23, n=17,488) | 0.3832 | 0.3832 | +0.0000 | >= +0.03 over 0.383 | NO |

  Neither leg moved at all — the flag-on and flag-off runs produced
  byte-identical `model+chips` and identical pooled Spearman to four decimal
  places. **D-07 auto-adopt verdict: REJECTED** (dual criterion needs both;
  zero of two are met). `config.EXPERIMENTS['availability_flags']` stays
  `False` (already the default; no flip). Per D-08 all code stays merged —
  `data/availability.py`, the `av_*` feature family, and the
  `apply_experiment_feature_gating` branch are computed unconditionally and
  simply unused as model features by default.
- **This is not a thin-join verdict.** 2025-26 availability coverage is
  **92.7%** (10-06-SUMMARY.md, up from the pre-vendoring 92.2%) — a
  well-covered season, not a sparse probe. The flat reading is a real
  measurement against real coverage, not an artifact of missing data.
- **D-09(b)'s flat reading has a structural explanation, stated plainly
  rather than left implicit.** `backtest.benchmark_external`'s scoreable
  seasons are **2021-22 and 2022-23** (the only seasons theFPLkiwi's
  committed snapshot carries enough gameweeks to score) — and
  `availability_flags` has **zero coverage in either season**
  (`data/availability.py`'s providers only cover 2025-26 onward). The
  `tier1_base` and `tier1_avail` pooled blocks are therefore numerically
  identical on every stat column to four decimal places by construction,
  not because the flag has no value anywhere — D-09(b)'s own pre-declared
  basis simply cannot see 2025-26 at all. The rule is still applied
  mechanically against the number D-09(b) actually names.
- **Phase F's own figure, for comparison.** 10-01-SUMMARY.md's tracer run
  (`wf_t1_av_off` / `wf_t1_av_on`, single-replica) already recorded
  2025-26 `model+chips = 2172` for both the off and on states. This plan's
  fresh, 5-replica, full-coverage (92.7%, not 10-01's 10.8% probe) re-run
  reproduced the **identical 2172** for both arms — Task 1's rebuild (which
  added the `tm_*` injury family to `features.parquet`, always stripped by
  gating when the flag driving this A/B is off) did not move this
  particular number, contrary to the plan's own anticipation that it might.

### transfermarkt_injury: 6-season adoption verdict (plan 10-08)

- **Commands run.** `scripts/experiment_run.sh tm_base6 --replicas 5` and
  `scripts/experiment_run.sh tm_on6 --replicas 5 --experiments transfermarkt_injury`
  (artifacts `data/processed/experiments/wf_tm_base6.json` /
  `wf_tm_on6.json`), against the same frozen `features.parquet`.
- **Standard 6-season protocol, primary bar:**

  | metric | fresh base (6-season) | flag on | delta | bar | met? |
  |---|---:|---:|---:|---:|:--:|
  | `model+chips` | 2262 | 2242 | **-20** | >= 2,280 | NO |

  Not merely short of the bar — a genuine **regression** against its own
  contemporaneous control. **D-07 auto-adopt verdict: REJECTED.**
  `config.EXPERIMENTS['transfermarkt_injury']` stays `False` (already the
  default; no flip). Per D-08 all code stays merged — `data/transfermarkt.py`,
  `config.INJURY_COLS`, and the `apply_experiment_feature_gating` branch are
  computed unconditionally and simply unused as model features by default.
- **Coverage, measured live against the completed backfill** (2026-09-11,
  via `data.transfermarkt.attach()` on the real `player_gw.parquet`, all
  2,623 distinct `player_code` values in scope): **id-resolved coverage
  79.7%** row-level (`tm_days_out_so_far` non-null share), **82.6%**
  player-level (2,166/2,623 `player_code` values resolved a Transfermarkt
  id), **active-spell rate 11.0%** among id-resolved rows. The backfill
  itself is complete: 12,503 injury spells across 1,697 players in
  `data/external/transfermarkt/injury_spells.csv`; the remaining 926
  id-resolved players (2,623 total id-map entries minus 1,697 with recorded
  spells) legitimately have zero injury-history rows (mostly youth players
  with no Transfermarkt injury table), not a resolution failure — matching
  10-07-SUMMARY.md's own resolved-vs-unresolved distinction
  (`_covered_player_codes()`).
- **Unverified-prior caveat (A1).** The IJCSS 2025 paper
  (`10.2478/ijcss-2025-0008`) the original todo cites for this source's
  expected value could not be located or verified this session (recorded in
  "Unverified prior evidence" below) — this measured -20-point regression
  stands on its own honest harness result, not as a confirmation or
  refutation of that unverified prior.

### D-02 news-sentiment trigger evaluation (plan 10-08)

- **Locked threshold:** pooled played-only `spearman_xp_med` **< 0.500**
  triggers building the news-sentiment experiment; **>= 0.500** records it
  not-triggered (IMPROVEMENTS.md "Declared criteria", plan 10-01).
- **Command run:** `python -m backtest.benchmark_external --experiments availability_flags,transfermarkt_injury --tag tier1`
  (artifact `data/processed/experiments/benchmark_tier1.json`).
- **Measured:** pooled played-only `spearman_xp_med` = **0.3874**
  (seasons 2021-22, 2022-23, n=17,488).
- **Mechanical outcome: 0.3874 < 0.500 → BUILD.** Plan 10-12 is required to
  build the news-sentiment experiment per D-02's own pre-declared rule.
- **Structural caveat, stated per the plan's own requirement.** These two
  benchmark seasons carry **zero `availability_flags` coverage** —
  `benchmark_tier1_base.json` (both flags off, 0.3832) and
  `benchmark_tier1_avail.json` (availability only, 0.3832) are numerically
  identical to four decimal places on every column, confirming the
  availability family contributed nothing measurable to this particular
  number. The entire movement from the fresh base (0.3832) to the combined
  Tier-1 run (0.3874, **+0.0042**) is attributable to `transfermarkt_injury`
  alone, which does have real (if modest) coverage in 2021-22/2022-23. This
  does not change D-02's mechanical outcome — the trigger measures whether
  the ranking gap is still open, not which experiment moved it, and it is
  still well short of 0.500 either way.
- **Prior evidence for tuning budget.** `danielfrees/mlpremier` (arXiv
  2405.02412) published a **negative** result for Guardian-based news
  sentiment — it underperformed both its own CNN and its Ridge/LightGBM
  baselines in that paper's own reported comparison. Plan 10-12 should treat
  this as the governing prior on how much tuning budget the sentiment
  experiment deserves once built, not assume a positive result is likely.

### Data provenance and access risk (Phase 10)

| source | access status | committed? | license/ToS posture | evidence |
|--------|---------------|------------|----------------------|----------|
| FPL API | open, no auth | not committed (fetched live) | public API, standard ToS | already the project's primary data source |
| FPL-Core-Insights | reachable — probed live 2026-09-10 (GW1-3 `playerstats.csv`, columns confirmed) | commit pending 10-06's license check | license unconfirmed at plan time (10-RESEARCH.md Pitfall) — verify before committing | `data/raw/fpl_core_insights/2025-2026/` (gitignored probe, this plan) |
| Transfermarkt | **mostly-open — measured 2026-09-10.** Real 8-page probe (plain `requests` + Chrome User-Agent, `_MIN_INTERVAL_S=3.0`): 7/8 pages `ok` (200, real injury rows parsed, 1-15 rows/page), 0 `challenge`, 0 `http_error`, 0 `parse_error`, 1 `id_unresolved` (B.Fernandes — FPL's abbreviated display name fails Transfermarkt's search endpoint; a name-resolution gap for 10-07, not an access block). Served column headers confirmed verbatim: `Season, Injury, from, until, Days, Games missed` (10-RESEARCH.md A4 exact match) | not committed (raw pages gitignored under `data/raw/transfermarkt/`); **go/no-go decision: A — full backfill authorised**, all seasons 2016-17+, background killable job (10-05 checkpoint, verbatim developer answer "A") | unofficial source, ToS unclear; committed artifact is a derived, normalized spell table decided in 10-07, never the raw scraped page | 8-page real probe (`data/processed/experiments/transfermarkt_probe.json`), this plan |
| figshare pre-scraped dataset | **INSUFFICIENT — measured 2026-09-10.** The ~107k-injury "Injuries from Transfermarkt.com" dataset 10-RESEARCH.md A5 cites does not exist on figshare's public API (`articles/search` for "Injuries from Transfermarkt" returned only 2 unrelated hits); every `ndownloader.figshare.com` download attempted returned HTTP 202 with `x-amzn-waf-action: challenge` (AWS WAF JS challenge, not clearable by plain `requests`) | not committed | unknown (never reached — WAF-blocked) | `--figshare-check` run, this plan; supersedes the earlier Phase 9 "403 on direct fetch" reading |
| GDELT DOC 2.0 | keyless, not yet probed | not committed, conditional on D-02's trigger firing | public API | plain `requests`, no `gdeltdoc` package (locked decision, this plan) |
| Guardian | free key needed, not yet probed | not committed, conditional on D-02's trigger firing | Open Platform ToS | plain `requests` client (locked decision, this plan) |
| fplreview | **403 to automated access — manual capture only** | never redistributed, never a model input | manual, non-redistributable | 10-RESEARCH.md / plan 10-02 |
| fbrapi.com | half-down 2026-09-09, **not re-probed per D-04** | not committed | unknown | 09-RESEARCH.md Phase 9 finding (Cloudflare-gated) |

### transfermarkt_injury: go/no-go decision — Option A, full backfill authorised (plan 10-05)

Two bounded checks ran before any backfill infrastructure was built, per the
Phase 9 `fbref_v2` precedent (spend the probe before the spend). Figshare
verdict: **INSUFFICIENT** (dataset absent from figshare's own search API;
every download attempt WAF-challenged). Real 8-page Transfermarkt probe:
**7/8 pages parsed cleanly**, 0 challenged, 1 `id_unresolved` (a name-lookup
gap, not an access block) — full per-page evidence in
`data/processed/experiments/transfermarkt_probe.json`.

Projected full-scope wall clock, computed explicitly per the checkpoint's own
instructions: **2,623 distinct `player_code` values** across seasons
2016-17..2025-26 (`data/processed/player_gw.parquet`), one profile-page fetch
per player at `_MIN_INTERVAL_S = 3.0`s ≈ **2.19h**, plus one search-endpoint
fetch per player for `tm_player_id` resolution ≈ 2.19h more — **≈4.4h total**
rate-limit-bound wall clock for a background killable job.

**Developer decision (verbatim): "A"** — Option A, full backfill (D-06 as
written): all seasons 2016-17+, background killable job. Plan 10-07 is
authorised to build the 6-season backfill fetcher, cache, and normalized
join at this full scope; no season-scope reduction (Option B) and no
figshare substitute (Option C, unavailable — figshare verdict was
INSUFFICIENT, not USABLE) apply.

### Unverified prior evidence (Phase 10)

- The IJCSS 2025 paper (`10.2478/ijcss-2025-0008`) could not be located this
  session. Every claim the Tier-1 todos attribute to it is **[ASSUMED]** —
  cited as provenance, not verified fact, in any later plan's writeup.
- `danielfrees/mlpremier` (arXiv 2405.02412) — the repo D-02's todo cites to
  mine for a news-sentiment approach — published a **negative** result for
  Guardian-based news sentiment: it underperformed both its own CNN and its
  Ridge/LightGBM baselines in that paper's own reported comparison.
- Neither note changes any pre-declared trigger above; both are context the
  eventual ledger entries for `news_sentiment` (and any Tier-1 experiment
  drawing on the IJCSS claims) must cite rather than omit.

## Reference findings (why the priorities)

Levers that beat noise: model vs form baseline (+83..92/season), active transfers
(+~400), chips (+30–40, isolated), multi-GW (+40 leakage-safe). Levers that did NOT:
ranking loss (−55), clean-sheet sub-model (−50), set-piece/odds features (fixture
MAE better, season pts within noise). Full history in PLAN.md.
