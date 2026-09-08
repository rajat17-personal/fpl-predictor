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
| capt_mc | capture improves ≥ +2 pts abs. over captain-by-mean | pending | pending | off |
| chips_v2 | no chip's isolated value regresses; WC value measured | pending | pending | off |
| team_strength | `tests/test_leakage.py` leakage assertion passes | pending | pending | off |
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

## Reference findings (why the priorities)

Levers that beat noise: model vs form baseline (+83..92/season), active transfers
(+~400), chips (+30–40, isolated), multi-GW (+40 leakage-safe). Levers that did NOT:
ranking loss (−55), clean-sheet sub-model (−50), set-piece/odds features (fixture
MAE better, season pts within noise). Full history in PLAN.md.
