"""Phase 6: multi-season walk-forward backtest with noise controls.

A single test season is too noisy to trust. This reduces noise three ways:
  1. MORE SEASONS      - expanding-window retrain + backtest over 6 seasons, so the
                         average has ~sqrt(6) tighter standard error.
  2. MULTIPLE TEAMS    - K jittered replicas of the model config per season (small
                         noise on xP -> different near-optimal squads) give a
                         WITHIN-season confidence band on realised points.
  3. ISOLATED CHIPS    - each chip's marginal value is measured on the SAME team
                         with vs without the chip that gameweek, stripping out the
                         path-dependence that made whole-season chip diffs unstable.

For each test season T: train on seasons before T-1, validate on T-1, simulate T.

Run:
  python -m backtest.walk_forward            # ~a few minutes
  python -m backtest.walk_forward --replicas 5
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import sys

import numpy as np
import pandas as pd
from scipy.stats import poisson, skellam, spearmanr

import config
from backtest.season import run_season
from data import team_strength as ts_mod
from models import captaincy
from models.train import load_features, predict_xp, train_predict
from ops.jsonio import read_json, write_json

# Schedule-derived context known ahead of time — safe to graft onto a frozen-form row.
# `opponent_team_id` is the future fixture's OPPONENT IDENTITY, which is knowable
# ahead (it is on the published fixture list) -- unlike a team-strength RATING,
# which is not (see leakage_safe_plan's team_strength graft). No `ts_*` name
# belongs in this list: a verify asserts their absence so nobody grafts a future
# gameweek's rating by accident (T-09-05-02).
FIXTURE_CTX = ["fdr_self", "fdr_opp", "was_home", "is_dgw", "gw", "days_rest",
              "opponent_team_id"]

DATA_SEASONS = config.SEASONS[:-1]                                  # drop 2026-27
TEST_SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
JITTER_FRAC = 0.05                                                  # 5% of xP sd


def resolve_scheduler(exp: dict[str, bool]) -> str:
    """Resolve `config.EXPERIMENTS`-shaped flags to exactly one of the three
    `backtest.season.run_season(scheduler=...)` values (D-02): "rl" when
    `rl_strategy` is on, else "v2" when `chips_v2` is on, else "v1". Enabling
    both `rl_strategy` and `chips_v2` is a `SystemExit` naming both -- the
    D-02 comparison requires the RL layer to beat the solver-scored scheduler
    on its own, not stacked on top of it. Pure logic, no data/model I/O --
    safe to unit test directly."""
    if exp["rl_strategy"] and exp["chips_v2"]:
        raise SystemExit(
            "rl_strategy and chips_v2 cannot both be enabled: the D-02 comparison "
            "requires the RL layer to beat the solver-scored (chips_v2) scheduler "
            "on its own, not stacked on top of it.")
    return "rl" if exp["rl_strategy"] else ("v2" if exp["chips_v2"] else "v1")


@functools.lru_cache(maxsize=1)
def _raw_opponent_key() -> pd.DataFrame:
    """(season, player_id, fixture_id) -> opponent_team_id, read once. Not a
    model feature -- features.parquet does not carry this column (only its
    derived fdr_self/fdr_opp do) -- needed solely so leakage_safe_plan's
    horizon graft can carry a future fixture's opponent IDENTITY forward."""
    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet")
    return raw[["season", "player_id", "fixture_id", "opponent_team_id"]].drop_duplicates()


def _attach_opponent_id(te: pd.DataFrame) -> pd.DataFrame:
    before = len(te)
    merged = te.merge(_raw_opponent_key(), on=["season", "player_id", "fixture_id"], how="left")
    if len(merged) != before:
        raise AssertionError(f"opponent_team_id merge changed row count {before} -> {len(merged)}")
    return merged


def _preds_for(df: pd.DataFrame, test_season: str):
    i = DATA_SEASONS.index(test_season)
    if i < 2:
        raise ValueError(f"{test_season}: need >=2 prior seasons")
    train, val = DATA_SEASONS[:i - 1], DATA_SEASONS[i - 1]
    # med = core selection objective; mean = captain-value model (the armband
    # doubles points, so the captain slot wants E[points], not the median).
    te, models, cols = train_predict(df, train, val, [test_season],
                                     objectives={"med": "regression_l1",
                                                 "mean": "regression"},
                                     calibrate=True)
    te = te.copy()
    te["xp_form"] = te["total_points_r5"].fillna(0)
    te = _attach_opponent_id(te)
    return te, models, cols


def _features_parquet_hash() -> str:
    """sha256 of the on-disk features.parquet -- the "vintage" a cached
    baseline is keyed against, so a rebuilt feature matrix (new source,
    fixed bug, extra season) invalidates a stale cache entry rather than
    silently comparing a fresh candidate against yesterday's numbers."""
    return hashlib.sha256((config.PROCESSED_DIR / "features.parquet").read_bytes()).hexdigest()


def _lgbm_played_spearman(df: pd.DataFrame, test_season: str) -> float:
    """In-process LightGBM played-only Spearman for `test_season`, via the
    identical `_preds_for` the real harness uses, filtered to `y_minutes > 0`
    and scored with the same `spearmanr(...).statistic` call form
    `backtest/benchmark_external.py::_stats_block` uses (one metric
    definition everywhere, never three near-identical ones) -- the baseline
    every Colab candidate's implausibility check is compared against.

    Cached to `config.EXPERIMENTS_DIR / "lgbm_played_spearman.json"`, keyed
    by BOTH season and `_features_parquet_hash()` -- comparing a fresh
    candidate against a stale baseline is exactly the kind of silent
    mismatch this whole check exists to catch, so a hash change forces a
    recompute even if the season's own key is already cached.
    """
    cache_path = config.EXPERIMENTS_DIR / "lgbm_played_spearman.json"
    h = _features_parquet_hash()
    cache = (read_json(cache_path, what="LightGBM played-only Spearman baseline cache")
             if cache_path.exists() else {})
    if not isinstance(cache, dict):
        cache = {}
    entry = cache.get(test_season)
    if isinstance(entry, dict) and entry.get("hash") == h and "spearman" in entry:
        return float(entry["spearman"])

    te, _models, _cols = _preds_for(df, test_season)
    played = te[te["y_minutes"] > 0]
    spearman = float(spearmanr(played["xp_med"], played["y_points"]).statistic)

    cache[test_season] = {"hash": h, "spearman": spearman}
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(cache, cache_path, indent=1)
    return spearman


# --- External prediction ingestion (D-14): score a Colab-trained bracket
# candidate through the exact same run_season/_preds_for-shaped path an
# in-process LightGBM run uses, so the local harness stays the sole judge.
# See 10-RESEARCH.md Pitfall 6 (a schema-valid but leakage-corrupt artifact)
# and Open Question 4 (ground truth is always re-attached locally, never
# trusted from the artifact).

# The artifact contract is deliberately minimal: (season, gw, player_code,
# fixture_id, xp_med, xp_mean). `fixture_id` is required, not optional --
# this project's model granularity is the individual FIXTURE, not the
# gameweek (features/engineer.py's own ID_COLS says so explicitly), so a
# gameweek-level artifact could not be scored through run_season without
# inventing a double-gameweek split rule. Do not "simplify" this contract to
# gameweek-level in a future Colab notebook.
_EXTERNAL_PRED_COLS = ["season", "gw", "player_code", "fixture_id", "xp_med", "xp_mean"]

# With the LightGBM baseline at 0.383 pooled played-only Spearman
# (IMPROVEMENTS.md's own "Benchmark: our xP vs theFPLkiwi" figure) and FPL's
# own ep_next (which sees genuine pre-deadline news we do not have) at 0.579,
# a candidate trained on the same features clearing ~0.53 is far likelier to
# be leakage (test-season contamination in the external training loop) than
# a genuine modelling breakthrough. This is a WARNING, not a rejection -- the
# number still gets recorded, with the flag raised, exactly how Phase 9
# handled its own +337-optimistic-vs-+40-honest finding.
_MAX_PLAUSIBLE_SPEARMAN_JUMP = 0.15

_GROUND_TRUTH_COLS = {"y_points", "y_minutes", "y_played", "y_started", "y_clean_sheets"}


def load_external_predictions(path, test_season: str, *, df: pd.DataFrame | None = None,
                              baseline_spearman: float | None = None) -> pd.DataFrame:
    """Ingest an externally-produced (e.g. Colab) per-fixture prediction
    parquet and validate + score it through the identical shape `_preds_for`
    returns, so it feeds `backtest.season.run_season` (and every consumer of
    `main`'s season loop) exactly like an in-process LightGBM run.

    Validated on four axes (D-14/10-RESEARCH.md Pitfall 6):
      1. schema       -- every column in `_EXTERNAL_PRED_COLS` must be present.
      2. season       -- the artifact's own `season` column must equal exactly
         `{test_season}` (catches a notebook that trained one global model
         and dumped every season into one file).
      3. ground truth -- any `y_*` column present is DROPPED and warned
         about; truth is always re-attached locally from `features.parquet`
         (Open Question 4), never trusted from the artifact.
      4. row count    -- the join onto the local feature frame must never
         increase the row count (a fan-out join).

    On top of validation, the played-only Spearman of the artifact's own
    `xp_med` against real `y_points` is compared to a vintage-keyed
    in-process LightGBM baseline (`_lgbm_played_spearman`, always available
    -- computed on arrival if not already cached); a jump over
    `_MAX_PLAUSIBLE_SPEARMAN_JUMP` is flagged loudly (printed, and on the
    returned frame's `.attrs["implausible"]`) but the number is still
    recorded -- see the constant's own comment. `baseline_spearman` lets a
    caller who already has a figure in hand skip that (expensive) run.
    """
    artifact = pd.read_parquet(path)
    missing = [c for c in _EXTERNAL_PRED_COLS if c not in artifact.columns]
    if missing:
        raise ValueError(
            f"external prediction artifact {path} missing required column(s): {missing} "
            f"(the contract is {_EXTERNAL_PRED_COLS})")

    artifact_seasons = set(artifact["season"].unique())
    if artifact_seasons != {test_season}:
        raise ValueError(
            f"external prediction artifact {path} season set {sorted(artifact_seasons)} "
            f"!= expected {{{test_season!r}}} -- a candidate that trained one global "
            "model and dumped every season into one file would fail this check "
            "(10-RESEARCH.md Pitfall 6)")

    dropped_gt = [c for c in artifact.columns if c in _GROUND_TRUTH_COLS]
    for c in dropped_gt:
        print(f"[external] WARNING: artifact carried ground-truth column {c!r} -- "
              "dropped, re-attached locally from features.parquet (the artifact "
              "is never the source of truth for what happened)")

    base = load_features() if df is None else df
    local = base[base["season"] == test_season].copy()
    before = len(local)
    artifact_join = artifact[["season", "player_code", "fixture_id", "xp_med", "xp_mean"]]
    te = local.merge(artifact_join, on=["season", "player_code", "fixture_id"], how="inner")
    if len(te) > before:
        raise AssertionError(
            f"external prediction join increased row count {before} -> {len(te)} for "
            f"{test_season} -- the artifact has more than one row per "
            "(player_code, fixture_id)")
    coverage = len(te) / before if before else 0.0
    print(f"[external] {test_season}: joined {len(te):,}/{before:,} local rows "
          f"(coverage {coverage:.1%})")

    te["xp_form"] = te["total_points_r5"].fillna(0)
    te = _attach_opponent_id(te)

    if baseline_spearman is None:
        baseline_spearman = _lgbm_played_spearman(base, test_season)

    played = te[te["y_minutes"] > 0]
    ext_spearman = float(spearmanr(played["xp_med"], played["y_points"]).statistic)
    jump = ext_spearman - baseline_spearman
    implausible = jump > _MAX_PLAUSIBLE_SPEARMAN_JUMP
    te.attrs["implausible"] = implausible
    if implausible:
        print(f"[external] IMPLAUSIBLE: external xp_med played-only Spearman "
              f"{ext_spearman:.4f} exceeds the in-process LightGBM baseline "
              f"{baseline_spearman:.4f} by {jump:.4f} (> {_MAX_PLAUSIBLE_SPEARMAN_JUMP:.2f}). "
              "The likeliest cause is test-season contamination in the external "
              "training loop, not a modelling breakthrough -- see 10-RESEARCH.md "
              "Pitfall 6. The number below is recorded WITH this flag raised.")
    return te


def _plan_col(preds: pd.DataFrame, horizon: int = 4, decay: float = 0.84) -> pd.DataFrame:
    """Add `xp_plan` = horizon-discounted forward sum of xp_med, for multi-GW
    transfer planning. Drives WHICH players to hold over an upcoming fixture run;
    scoring still uses actual points.

    Backtest caveat: this peeks at future GWs' predictions (which embed future
    form), so it is an OPTIMISTIC upper bound on multi-GW value. The leakage-safe
    live version rebuilds future xP from current form + known fixtures.
    """
    pg = (preds.groupby(["player_code", "gw"])["xp_med"].sum()
          .reset_index(name="pg").sort_values(["player_code", "gw"]))

    def fdec(a):
        a = a.values
        n = len(a)
        out = np.zeros(n)
        for k in range(horizon):
            if n - k <= 0:
                break
            out[:n - k] += (decay ** k) * a[k:]
        return out

    pg["xp_plan"] = pg.groupby("player_code")["pg"].transform(fdec)
    m = preds.merge(pg[["player_code", "gw", "xp_plan"]], on=["player_code", "gw"], how="left")
    nfix = m.groupby(["player_code", "gw"])["xp_med"].transform("size")   # split over DGW rows
    m["xp_plan"] = m["xp_plan"] / nfix
    return m


def _masked_xp_fpl(df: pd.DataFrame) -> pd.Series:
    """`xp_fpl` with every (season, gw) group nulled out where it is 0.0 or
    null for EVERY row in that group -- an outage gameweek captured as a
    false zero (or an entirely-null training season, F3) must never enter the
    model as a confident zero. A gameweek with a genuine MIXTURE of zero and
    non-zero rows is left untouched, so this does not eat F4's legitimate
    ~40% pre-deadline zero mass."""
    is_zero_or_null = df["xp_fpl"].isna() | (df["xp_fpl"] == 0.0)
    all_masked = is_zero_or_null.groupby([df["season"], df["gw"]]).transform("all")
    return df["xp_fpl"].where(~all_masked)


def _prev_fixture_lag(df: pd.DataFrame, masked: pd.Series) -> pd.Series:
    """Strict previous-fixture value of `masked` (a shift(1), never a rolling
    mean) within (season, player_id), ordered by kickoff_time -- the same
    ordering features/engineer.py's `_roll` uses. Operates on the ALREADY-
    masked series, so an outage gameweek's null propagates forward as a null
    lag rather than a confident zero (T-elx-02). Returns a Series aligned to
    `df`'s original row order/index regardless of `df`'s own row order."""
    tmp = pd.DataFrame({"season": df["season"].to_numpy(),
                        "player_id": df["player_id"].to_numpy(),
                        "kickoff_time": df["kickoff_time"].to_numpy(),
                        "masked": masked.to_numpy()}, index=df.index)
    order = tmp.sort_values(["season", "player_id", "kickoff_time"]).index
    lagged = tmp.loc[order].groupby(["season", "player_id"])["masked"].shift(1)
    return lagged.reindex(df.index)


def apply_experiment_feature_gating(df: pd.DataFrame, exp: dict) -> pd.DataFrame:
    """Drop or add an experiment-gated feature from `df` depending on its flag.

    `ts_*` (config.TEAM_STRENGTH_COLS), rolled `us_*` (config.UNDERSTAT_COLS
    -> ROLL_STATS), rolled `fm_*` (config.FOTMOB_COLS -> ROLL_STATS),
    `av_*` (config.AVAILABILITY_COLS -> CONTEXT_COLS) and `tm_*`
    (config.INJURY_COLS -> CONTEXT_COLS) are all computed UNCONDITIONALLY by
    the pipeline (see config.py's own comments on those five constants) so an
    experiment toggle never forces a data/build_table.py + features/engineer.py
    rebuild -- the feature-selection gate lives here instead, in exactly one
    place, so a future enrichment family adds one branch here rather than
    growing a sixth ad-hoc inline drop expression.

    Extracted from plan 09-05's inline team_strength-only gating (D-13), then
    extended by plan 09-08 (understat), 09-09 (fotmob), 10-01
    (availability_flags) and 10-07 (transfermarkt_injury); each existing
    branch's behaviour is unchanged from what its own plan measured.

    `ep_next_lag`/`ep_next_now` (quick task 260909-elx) are this function's
    first branch that ADDS a column rather than dropping one. `xp_fpl` (FPL's
    own per-fixture xP, models.train.load_features()'s merged-in evaluation
    baseline) must stay OUT of `feature_cols` (models/train.py's `_EXCLUDE`
    keeps it there) while staying IN the frame, because walk_forward and
    benchmark_external both score it as the FPL baseline -- so these two
    flags expose DERIVED columns (`xp_fpl_lag1`, `xp_fpl_now`) under new
    names, never rename or consume the literal `xp_fpl` column itself.

    `exp` needs only `.get()` -- callers may pass any dict-like subset of
    `config.EXPERIMENTS`'s keys (tests pass a plain two-key dict directly).
    """
    drop: list[str] = []
    if not exp.get("team_strength", False):
        drop += [c for c in config.TEAM_STRENGTH_COLS if c in df.columns]
    if not exp.get("understat", False):
        drop += [c for c in df.columns if c.startswith("us_")]
    if not exp.get("fotmob", False):
        drop += [c for c in df.columns if c.startswith("fm_")]
    if not exp.get("availability_flags", False):
        drop += [c for c in df.columns if c.startswith("av_")]
    if not exp.get("transfermarkt_injury", False):
        drop += [c for c in df.columns if c.startswith("tm_")]
    out = df.drop(columns=drop) if drop else df

    add_lag = exp.get("ep_next_lag", False)
    add_now = exp.get("ep_next_now", False)
    if add_lag or add_now:
        if "xp_fpl" not in df.columns:
            raise AssertionError(
                "ep_next_lag/ep_next_now require 'xp_fpl' in the frame -- "
                "models.train.load_features() must have merged it in")
        if out is df:
            out = out.copy()
        masked = _masked_xp_fpl(df)
        if add_lag:
            out["xp_fpl_lag1"] = _prev_fixture_lag(df, masked)
        if add_now:
            out["xp_fpl_now"] = masked
    return out


def _graft_team_strength_ratings(synth: pd.DataFrame, ratings_g: pd.DataFrame) -> None:
    """Overwrite `synth`'s ts_* columns in place with the DECISION-TIME rating
    (`ratings_g` == `team_strength.ratings_as_of(season, g)`) crossed with the
    future fixture's opponent IDENTITY (already grafted via FIXTURE_CTX) --
    never with the future gameweek's own rating row, which is fit on matches
    up to g+k-1 and would leak results the decision-maker at g has not seen.

    Self-side ratings need no change: `form`'s own ts_attack_self/ts_defence_self
    were already fit as-of g when features.parquet was built (attach() fits
    every stored row on matches strictly before its own gw).
    """
    opp_id = synth["opponent_team_id"]
    synth["ts_attack_opp"] = opp_id.map(ratings_g["attack"]).to_numpy()
    synth["ts_defence_opp"] = opp_id.map(ratings_g["defence"]).to_numpy()
    home_adv = float(ratings_g["home_adv"].iloc[0]) if len(ratings_g) else 0.0
    is_home = synth["was_home"].fillna(False).astype(float)
    synth["ts_xg_for"] = np.exp(synth["ts_attack_self"] + synth["ts_defence_opp"]
                                + home_adv * is_home)
    synth["ts_xg_against"] = np.exp(synth["ts_attack_opp"] + synth["ts_defence_self"]
                                    + home_adv * (1 - is_home))
    synth["ts_pwin"] = skellam.sf(0, synth["ts_xg_for"], synth["ts_xg_against"])
    synth["ts_pcs"] = poisson.pmf(0, synth["ts_xg_against"])


def leakage_safe_plan(te: pd.DataFrame, models: dict, cols: list, *,
                      horizon: int = 4, decay: float = 0.84,
                      team_strength: bool = False) -> pd.DataFrame:
    """LEAKAGE-SAFE multi-GW plan value.

    At decision GW g, predict each future GW g+k using the player's form AS OF g
    (their GW-g feature row already only sees data through g-1) with GW g+k's real
    FIXTURE context grafted in (opponent/home/FDR/DGW — knowable ahead). No future
    form is used, so this is an honest estimate of multi-GW planning value.

    `team_strength=True` additionally re-derives the ts_* columns from the
    DECISION-TIME ratings (`ratings_as_of(season, g)`) and the future
    fixture's opponent identity, rather than letting FIXTURE_CTX graft
    through a future gameweek's own (not-yet-knowable) rating row.
    """
    by_gw = {g: te[te.gw == g] for g in te.gw.unique()}
    records = []
    for g, cur in by_gw.items():
        form = cur.drop_duplicates("player_code").set_index("player_code")  # frozen-form snapshot
        ratings_g = (ts_mod.ratings_as_of(cur["season"].iloc[0], g)
                    if team_strength else None)
        plan = pd.Series(0.0, index=form.index)
        for k in range(horizon):
            fut = by_gw.get(g + k)
            if fut is None:
                continue
            fut = fut[fut.player_code.isin(form.index)]
            if fut.empty:
                continue
            synth = form.loc[fut.player_code].reset_index()   # repeat form per future fixture (DGW ok)
            for c in FIXTURE_CTX:
                synth[c] = fut[c].values                       # graft the future fixture context
            if team_strength:
                _graft_team_strength_ratings(synth, ratings_g)
            pred = predict_xp(models, synth, cols, "med").clip(lower=0).values
            s = pd.Series(pred, index=fut.player_code.values).groupby(level=0).sum()
            plan = plan.add(s.mul(decay ** k), fill_value=0.0)
        records += [{"gw": g, "player_code": pc, "pg": v} for pc, v in plan.items()]

    pg = pd.DataFrame(records)
    m = te.merge(pg, on=["gw", "player_code"], how="left")
    nfix = m.groupby(["gw", "player_code"])["xp_med"].transform("size")
    m["xp_plan"] = (m["pg"] / nfix).fillna(0.0)
    return m


def _jitter(te: pd.DataFrame, xp_col: str, seed: int) -> pd.DataFrame:
    """Perturb xP to pick a different near-optimal team (replica 0 = true optimum)."""
    if seed == 0:
        return te
    rng = np.random.default_rng(seed)
    t = te.copy()
    t[xp_col] = t[xp_col] + rng.normal(0, JITTER_FRAC * t[xp_col].std(), len(t))
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", type=int, default=5, help="jittered teams per season")
    ap.add_argument("--experiments", default=None,
                    help="comma-separated experiment flags to force on (see config.EXPERIMENTS); "
                         "falls back to $FPL_EXPERIMENTS, then all-off")
    ap.add_argument("--seasons", default=None,
                    help="comma-separated subset of TEST_SEASONS to run (default: all 6)")
    ap.add_argument("--tag", default=None,
                    help="write a tagged data/processed/experiments/wf_<tag>.csv/.json result "
                         "instead of overwriting walk_forward_results.csv")
    ap.add_argument("--capt-lambda", type=float, default=None,
                    help="override config.CAPT_CEILING_LAMBDA for this run "
                         "(only affects the capt_ceiling experiment)")
    ap.add_argument("--chips-hysteresis", type=float, default=None,
                    help="override config.CHIPS_V2_HYSTERESIS for this run "
                         "(only affects the chips_v2 experiment)")
    ap.add_argument("--rl-seed", type=int, default=None,
                    help="which config.RL_SEEDS entry's trained policy to load "
                         "(only affects the rl_strategy experiment; default: "
                         "config.RL_SEEDS[0])")
    ap.add_argument("--optimistic-plan", action="store_true",
                    help="also compute the OPTIMISTIC multi-GW plan (_plan_col, which "
                         "peeks at future GWs' own predictions) and report it as "
                         "multi_optimistic beside the honest multi_safe (D-06) -- the "
                         "gap between the two is the project's own repeated "
                         "+337-optimistic-vs-+40-honest failure mode, made visible "
                         "rather than assumed away for any horizon-touching change")
    ap.add_argument("--external-preds", default=None,
                    help="path to an externally-produced (e.g. Colab) per-fixture "
                         "prediction parquet (see load_external_predictions's "
                         "_EXTERNAL_PRED_COLS contract), scored through the season "
                         "loop in place of an in-process LightGBM run for each "
                         "selected season -- D-14's seam for judging a Colab bracket "
                         "candidate. Cannot combine with --experiments capt_ceiling "
                         "(captaincy needs a real models/cols pair a frozen artifact "
                         "does not carry); multi_safe is always recorded as None for "
                         "these seasons, with a printed note, rather than substituting "
                         "a locally-trained model's models/cols")
    args = ap.parse_args(argv)

    exp = config.resolve_experiments(args.experiments)
    if args.external_preds and exp["capt_ceiling"]:
        raise SystemExit(
            "--external-preds cannot be combined with --experiments capt_ceiling: "
            "capt_ceiling needs a real models/cols pair (captaincy.fit_ceiling_artifact) "
            "that a frozen external prediction artifact does not carry -- substituting "
            "a locally-trained model's models/cols would report a multi_safe/capt_ceiling "
            "figure that describes a different model than the one under test.")
    capt_col_active = "xp_capt_ceiling" if exp["capt_ceiling"] else None
    capt_lambda = (config.CAPT_CEILING_LAMBDA if args.capt_lambda is None
                   else args.capt_lambda)
    chips_hysteresis = (config.CHIPS_V2_HYSTERESIS if args.chips_hysteresis is None
                        else args.chips_hysteresis)
    rl_seed = config.RL_SEEDS[0] if args.rl_seed is None else args.rl_seed
    scheduler = resolve_scheduler(exp)   # D-02: resolved exactly once, before the season loop

    if args.seasons:
        seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
        unknown = [s for s in seasons if s not in TEST_SEASONS]
        if unknown:
            raise SystemExit(f"unknown season(s) {unknown} -- valid: {TEST_SEASONS}")
    else:
        seasons = list(TEST_SEASONS)

    df = load_features()
    df = apply_experiment_feature_gating(df, exp)
    rows, chip_recs = [], []
    for T in seasons:
        if args.external_preds:
            # D-14 seam: score a frozen, externally-produced artifact through
            # the identical harness path instead of training in-process.
            # models/cols are unavailable for a frozen artifact -- callers
            # needing captaincy.fit_ceiling_artifact are refused above.
            te, models, cols = load_external_predictions(args.external_preds, T), None, None
        else:
            te, models, cols = _preds_for(df, T)
            if exp["capt_ceiling"]:
                # Leakage-safe: fit the ceiling artifact on the validation season
                # immediately prior to T, never on the shipped 2025-26 artifact.
                val_season = DATA_SEASONS[DATA_SEASONS.index(T) - 1]
                artifact = captaincy.fit_ceiling_artifact(models, df, val_season, cols)
                te = captaincy.add_ceiling_ev(te, artifact, lam=capt_lambda)
        # Multiple teams: jittered replicas of the core model config.
        totals = [int(run_season(_jitter(te, "xp_med", s), "xp_med",
                                 use_chips=False).points.sum())
                  for s in range(args.replicas)]
        # Full system (chips) — replica 0, and harvest isolated chip values.
        chips_df = run_season(te, "xp_med", use_chips=True, record_chips=True,
                              capt_col=capt_col_active, scheduler=scheduler,
                              chips_hysteresis=chips_hysteresis, rl_seed=rl_seed)
        chip_recs.extend({"season": T, **d} for d in chips_df.attrs["chip_deltas"])
        cdf = run_season(te, "xp_med", capt_col=capt_col_active or "xp_mean", use_chips=False)
        capt_mean = int(cdf.points.sum())
        capt_capture = cdf.capt_pts.sum() / max(cdf.best_pts.sum(), 1)
        if args.external_preds:
            # A frozen artifact carries no models/cols, so leakage_safe_plan
            # (which needs predict_xp(models, ...)) cannot run -- record an
            # honest None rather than substituting a locally-trained model's
            # models/cols, which would describe a different model than the
            # one under test (T-10-09-04).
            m_safe = None
            print(f"[wf] {T}: multi_safe skipped -- --external-preds artifacts carry "
                  "no models/cols to compute leakage_safe_plan")
        else:
            m_safe = int(run_season(leakage_safe_plan(te, models, cols,
                                                      team_strength=exp["team_strength"]),
                                    "xp_plan", use_chips=False).points.sum())  # leakage-safe
        form = int(run_season(te, "xp_form", use_chips=False).points.sum())
        hold = int(run_season(te, "xp_med", use_chips=False, max_transfers=0).points.sum())

        row = {"season": T, "model_mean": int(np.mean(totals)),
              "model_std": int(np.std(totals)), "model+chips": int(chips_df.points.sum()),
              "capt_mean": capt_mean, "capt_capture": round(capt_capture, 3),
              "multi_safe": m_safe, "form": form, "hold": hold}
        line = (f"[{T}] model={int(np.mean(totals))}±{int(np.std(totals))} "
               f"captMean={capt_mean}(cap{capt_capture:.0%}) multiGW={m_safe} "
               f"chips={int(chips_df.points.sum())} form={form} hold={hold}")
        if args.optimistic_plan:
            m_optimistic = int(run_season(_plan_col(te), "xp_plan",
                                          use_chips=False).points.sum())      # optimistic
            row["multi_optimistic"] = m_optimistic
            line += f" multiGW_optimistic={m_optimistic}"
        rows.append(row)
        print(line, flush=True)

    res = pd.DataFrame(rows).set_index("season")
    print("\n=== Walk-forward season totals ===")
    print(res.to_string())

    n = len(seasons)
    # A plain `res.mean().round(0).astype(int)` blows up if any column is
    # all-NaN (multi_safe is always None/NaN for --external-preds seasons,
    # T-10-09-04) -- astype(int) cannot hold NaN. Kept as a plain dict rather
    # than a Series so a None stays a real None (not a fabricated int).
    gm = {c: (None if res[c].isna().all() else int(round(float(res[c].mean()))))
          for c in res.columns}
    # pandas' default ddof=1 std is NaN for a single-row Series (n=1) -- a real
    # possibility now that --seasons can select a subset for fast iteration
    # (D-14). 0.0 is the honest answer: there is no season-to-season spread to
    # report from one season.
    season_std = float(res["model_mean"].std()) if n > 1 else 0.0
    se_model = season_std / np.sqrt(n)
    print(f"\nAveraged over {n} seasons (season-to-season std in brackets):")
    print(f"  model (core, L1) : {gm['model_mean']}  "
          f"(±{int(season_std)}/season, SE {se_model:.0f})")
    print(f"  capt-by-mean     : {gm['capt_mean']}   -> vs core "
          f"{gm['capt_mean']-gm['model_mean']:+d} (captain slot uses E[pts])")
    if gm["multi_safe"] is None:
        print("  multi-GW (SAFE)  : n/a  (skipped -- --external-preds artifacts carry no "
              "models/cols to compute leakage_safe_plan)")
    else:
        print(f"  multi-GW (SAFE)  : {gm['multi_safe']}   -> vs myopic core "
              f"{gm['multi_safe']-gm['model_mean']:+d} (leakage-free, honest)")
    if args.optimistic_plan:
        if gm["multi_safe"] is None:
            print(f"  multi-GW (OPTIMISTIC) : {gm['multi_optimistic']}   -> vs SAFE "
                  "n/a (multi_safe unavailable for --external-preds seasons)")
        else:
            print(f"  multi-GW (OPTIMISTIC) : {gm['multi_optimistic']}   -> vs SAFE "
                  f"{gm['multi_optimistic']-gm['multi_safe']:+d} (peeks at future form -- "
                  f"the honest-vs-flattering gap, not a number to plan against)")
    print(f"  model + chips    : {gm['model+chips']}")
    print(f"  form baseline    : {gm['form']}   -> model edge +{gm['model_mean']-gm['form']}")
    print(f"  hold (no xfers)  : {gm['hold']}   -> active mgmt +{gm['model_mean']-gm['hold']}")
    print(f"  within-season team spread (jitter): ~±{int(res['model_std'].mean())} pts")

    # Isolated chip value across all instances (fh/bb/tc: same team scored
    # with vs without the chip; wc: same team vs a zero-transfer hold).
    cr = pd.DataFrame(chip_recs)
    chip_deltas_summary: dict[str, dict[str, float]] = {}
    if len(cr):
        print("\n=== Isolated chip value (same team, with vs without) ===")
        agg = cr.groupby("chip")["delta"].agg(["mean", "std", "count"]).round(1)
        print(agg.to_string())
        print("(positive = the chip added points on the week it was played)")
        # ddof=1 std is NaN for a single-observation chip (e.g. one WC per
        # season/replica) -- 0.0 is the honest answer, same guard as model_std.
        chip_deltas_summary = {
            str(chip): {"mean": float(row["mean"]),
                        "std": float(row["std"]) if pd.notna(row["std"]) else 0.0,
                        "count": int(row["count"])}
            for chip, row in agg.iterrows()
        }

    active_flags = sorted(k for k, v in exp.items() if v)
    capt_capture_avg = round(float(res["capt_capture"].mean()), 3)
    if args.tag:
        config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        res.to_csv(config.EXPERIMENTS_DIR / f"wf_{args.tag}.csv")
        summary = {
            "tag": args.tag,
            "seasons": seasons,
            "replicas": args.replicas,
            "experiments": exp,
            "scheduler": scheduler,
            "capt_lambda": capt_lambda,
            "chips_hysteresis": chips_hysteresis,
            "rl_seed": rl_seed,
            "model_mean": int(gm["model_mean"]),
            "model_std": int(season_std),
            "model+chips": int(gm["model+chips"]),
            "capt_mean": int(gm["capt_mean"]),
            "capt_capture": capt_capture_avg,
            "multi_safe": gm["multi_safe"],  # None for --external-preds seasons (T-10-09-04)
            "form": int(gm["form"]),
            "hold": int(gm["hold"]),
            "chip_deltas": chip_deltas_summary,
        }
        if args.optimistic_plan:
            summary["multi_optimistic"] = int(gm["multi_optimistic"])
        write_json(summary, config.EXPERIMENTS_DIR / f"wf_{args.tag}.json", indent=1)
        print(f"\nsaved data/processed/experiments/wf_{args.tag}.csv/.json")
    else:
        res.to_csv(config.PROCESSED_DIR / "walk_forward_results.csv")
        print("\nsaved data/processed/walk_forward_results.csv")

    print(f"[wf] tag={args.tag or 'none'} seasons={len(seasons)} replicas={args.replicas} "
          f"experiments={','.join(active_flags) or 'none'} scheduler={scheduler} "
          f"capt_lambda={capt_lambda} chips_hysteresis={chips_hysteresis} rl_seed={rl_seed} "
          f"model_mean={gm['model_mean']} "
          f"model+chips={gm['model+chips']} capt_capture={capt_capture_avg}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
