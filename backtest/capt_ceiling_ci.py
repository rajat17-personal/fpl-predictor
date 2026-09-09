"""Quick task 260909-dga: paired confidence intervals for the capt_ceiling
adoption comparison (Phase 9 plan 09-03, IMPROVEMENTS.md Phase F).

Plan 09-03 measured capt_capture 0.563->0.578 (+1.5pt) and model+chips +16
(2262->2278) at the harness default of 5 replicas, and REJECTED capt_ceiling
against the >=+2pt D-06 bar by eyeballing both deltas against an informal
SE~=16. `--replicas` cannot settle this: it feeds ONLY the jittered
`model_mean`/`model_std` columns (backtest/walk_forward.py:298-300) --
`capt_capture`, `capt_mean` and `model+chips` all come from a single,
unjittered `run_season` call apiece, so a 25x replica re-run reproduces the
same two numbers already on disk (measured_facts F1/F2 at planning time, and
confirmed by the 25-replica demonstration this quick task's Task 2 runs
against the unmodified harness). This module answers the real question on a
different axis: does the delta survive a proper paired interval computed
across seasons (and, less strongly, across gameweeks)?

Per test season T, this module builds ONE shared frame (F6: capt_ceiling
gates no features, so the same predictions serve both arms) by reusing
`backtest.walk_forward`'s own `_preds_for` and `apply_experiment_feature_gating`
-- never a fork of the prediction path, never
`data/processed/test_predictions.parquet`. From that frame it runs the same
four `run_season` calls `backtest.walk_forward.main` runs (captaincy arm
off/on, chips arm off/on) and keeps each call's FULL per-gameweek log, not
just its season sum, so the gameweek-level bootstrap has real per-gameweek
rows to resample.

Two interval families are reported, both labelled with their resampling
unit and independence caveat (measured_facts F4/F5):
  - Season-clustered (n = number of seasons): a paired two-sided t-interval
    on the per-season deltas. This is the conservative, correctly-clustered
    reading and GOVERNS the verdict.
  - Gameweek-level paired cluster bootstrap (n ~= total gameweek pairs): a
    percentile interval from resampling (season, gameweek) pairs WITH
    REPLACEMENT, stratified within season, recomputing the ratio-of-sums (or
    sum, for non-ratio metrics) each draw. Reported as the higher-power but
    OPTIMISTIC reading, because gameweeks within a season are not
    independent -- squad state carries across gameweeks through transfers.

This is measurement-only: it never retrains into `models/artifacts/`, never
mutates the shipped 2025-26 intervals artifact, and never flips
`config.EXPERIMENTS['capt_ceiling']`.

Run:
  python -m backtest.capt_ceiling_ci                      # full 6 seasons
  python -m backtest.capt_ceiling_ci --seasons 2025-26     # one season (tracer)
  python -m backtest.capt_ceiling_ci --force               # rebuild caches
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

import config
from backtest.season import run_season
from backtest.walk_forward import (DATA_SEASONS, TEST_SEASONS, _preds_for,
                                   apply_experiment_feature_gating)
from models import captaincy
from models.train import load_features
from ops.jsonio import write_json

BOOTSTRAP_N = 10000
SEED = 0
ARMS = ("cap_off", "cap_on", "chips_off", "chips_on")
METRICS = ("capt_capture", "capt_mean", "model_chips")


def capture_ratio(capt_pts, best_pts) -> float:
    """Ratio-of-sums captaincy capture: sum(capt_pts) / max(sum(best_pts), 1).

    Mirrors backtest/season.py:317's definition and its zero-denominator
    guard exactly -- NEVER the mean of per-gameweek ratios, which is a
    different (and biased) statistic on unequal per-gameweek best_pts.
    """
    capt_pts = np.asarray(capt_pts, dtype=float)
    best_pts = np.asarray(best_pts, dtype=float)
    return float(capt_pts.sum() / max(float(best_pts.sum()), 1.0))


def paired_t_interval(deltas) -> dict:
    """Paired two-sided 95% t-interval on `deltas` (df = n - 1).

    Returns {n, mean, se, ci_lo, ci_hi}. `n < 2` returns a degenerate
    zero-width interval at the single delta (no spread to estimate).
    """
    deltas = np.asarray(deltas, dtype=float)
    n = len(deltas)
    mean = float(deltas.mean())
    if n < 2:
        return {"n": n, "mean": mean, "se": 0.0, "ci_lo": mean, "ci_hi": mean}
    std = float(deltas.std(ddof=1))
    se = std / np.sqrt(n)
    half = float(student_t.ppf(0.975, df=n - 1)) * se
    return {"n": n, "mean": mean, "se": se, "ci_lo": mean - half, "ci_hi": mean + half}


def paired_cluster_bootstrap(off_df: pd.DataFrame, on_df: pd.DataFrame,
                             value_cols: list[str], ratio: bool,
                             n_resamples: int, seed: int) -> dict:
    """Percentile bootstrap CI on the paired delta `on - off`, resampling
    (season, gameweek) pairs WITH REPLACEMENT, stratified within season (each
    season's own row count is preserved every draw; seasons are never mixed
    with each other's rows).

    `off_df`/`on_df` must carry a `season` column plus `value_cols`, aligned
    row-by-row on (season, gw) with `off_df`. When `ratio` is True,
    `value_cols` must be `[numerator, denominator]` and the recomputed
    quantity each draw is `numerator.sum() / max(denominator.sum(), 1)` for
    each arm (never a per-row ratio averaged after the fact -- the same
    ratio-of-sums discipline as `capture_ratio`). When `ratio` is False,
    `value_cols` must be a single column and the quantity is its sum.

    Degenerate property (not a distributional claim): if every row within a
    season is identical, resampling cannot change that season's sum/ratio,
    so the whole interval collapses to a point at the observed delta.
    """
    rng = np.random.default_rng(seed)
    seasons = sorted(off_df["season"].unique())
    n_cols = len(value_cols)
    off_total = np.zeros((n_resamples, n_cols))
    on_total = np.zeros((n_resamples, n_cols))
    n_total = 0
    for s in seasons:
        off_s = off_df.loc[off_df.season == s, value_cols].to_numpy()
        on_s = on_df.loc[on_df.season == s, value_cols].to_numpy()
        n_s = len(off_s)
        if n_s == 0:
            continue
        n_total += n_s
        idx = rng.integers(0, n_s, size=(n_resamples, n_s))
        off_total += off_s[idx].sum(axis=1)
        on_total += on_s[idx].sum(axis=1)

    if ratio:
        off_val = off_total[:, 0] / np.maximum(off_total[:, 1], 1.0)
        on_val = on_total[:, 0] / np.maximum(on_total[:, 1], 1.0)
    else:
        off_val = off_total[:, 0]
        on_val = on_total[:, 0]
    deltas = on_val - off_val

    return {
        "n_gw_pairs": int(n_total),
        "n_resamples": int(n_resamples),
        "ci_lo": float(np.percentile(deltas, 2.5)),
        "ci_hi": float(np.percentile(deltas, 97.5)),
    }


def frame_path(season: str):
    """`config.EXPERIMENTS_DIR / capt_ci_te_<season>.parquet` -- the cached,
    ceiling-EV-attached shared frame for one test season."""
    return config.EXPERIMENTS_DIR / f"capt_ci_te_{season}.parquet"


def build_shared_frame(df_ungated: pd.DataFrame, season: str, *, force: bool = False) -> pd.DataFrame:
    """The ONE frame both arms for `season` are scored from (F6): leakage-
    safe predictions via `_preds_for`, plus the `xp_capt_ceiling` column fit
    on the immediately-prior validation season (never the shipped 2025-26
    intervals artifact -- the same leakage rule `backtest.walk_forward.main`
    applies). Cached to `frame_path(season)` so re-slicing this module's
    output never retrains; pass `force=True` to rebuild.
    """
    path = frame_path(season)
    if path.exists() and not force:
        print(f"[capt_ci] cached {path.relative_to(config.ROOT)}")
        return pd.read_parquet(path)

    te, models, cols = _preds_for(df_ungated, season)
    val_season = DATA_SEASONS[DATA_SEASONS.index(season) - 1]
    artifact = captaincy.fit_ceiling_artifact(models, df_ungated, val_season, cols)
    te = captaincy.add_ceiling_ev(te, artifact, lam=config.CAPT_CEILING_LAMBDA)

    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    te.to_parquet(path, index=False)
    print(f"[capt_ci] built {path.relative_to(config.ROOT)} ({len(te):,} rows)")
    return te


def measure_season(df_ungated: pd.DataFrame, season: str, *, force: bool = False) -> pd.DataFrame:
    """Run the four arms for `season` off ONE shared frame and return their
    per-gameweek logs stacked with `season` and `arm` columns.

    Arms mirror backtest/walk_forward.py:298-308 exactly:
      cap_off    -- capt_col="xp_mean",           use_chips=False (the
                    capt_col_active-or-"xp_mean" default when the flag is off)
      cap_on     -- capt_col="xp_capt_ceiling",   use_chips=False
      chips_off  -- capt_col=None,                use_chips=True (scheduler v1)
      chips_on   -- capt_col="xp_capt_ceiling",   use_chips=True (scheduler v1)
    """
    te = build_shared_frame(df_ungated, season, force=force)

    runs = {
        "cap_off": run_season(te, "xp_med", capt_col="xp_mean", use_chips=False),
        "cap_on": run_season(te, "xp_med", capt_col="xp_capt_ceiling", use_chips=False),
        "chips_off": run_season(te, "xp_med", capt_col=None, use_chips=True),
        "chips_on": run_season(te, "xp_med", capt_col="xp_capt_ceiling", use_chips=True),
    }

    frames = []
    for arm, log in runs.items():
        d = log[["gw", "points", "capt_pts", "best_pts"]].copy()
        d["season"] = season
        d["arm"] = arm
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def measure_all(seasons: list[str], df_ungated: pd.DataFrame, *, force: bool = False,
                bootstrap_n: int = BOOTSTRAP_N, seed: int = SEED) -> dict:
    """Full measurement across `seasons`: per-season off/on values for
    capt_capture/capt_mean/model+chips, plus both interval families for each
    metric. Failed seasons are skipped and named in the returned dict's
    `failed_seasons` rather than aborting the whole run (a partial-season
    result is still usable if clearly labelled)."""
    per_season: dict[str, dict] = {}
    all_frames = []
    failed_seasons: list[dict] = []

    for season in seasons:
        try:
            log = measure_season(df_ungated, season, force=force)
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: record and continue
            print(f"[capt_ci] SEASON FAILED {season}: {exc}", file=sys.stderr)
            failed_seasons.append({"season": season, "error": str(exc)})
            continue
        all_frames.append(log)

        cap_off = log[log.arm == "cap_off"]
        cap_on = log[log.arm == "cap_on"]
        chips_off = log[log.arm == "chips_off"]
        chips_on = log[log.arm == "chips_on"]

        row = {
            "capt_capture_off": capture_ratio(cap_off.capt_pts, cap_off.best_pts),
            "capt_capture_on": capture_ratio(cap_on.capt_pts, cap_on.best_pts),
            "capt_mean_off": int(cap_off.points.sum()),
            "capt_mean_on": int(cap_on.points.sum()),
            "model_chips_off": int(chips_off.points.sum()),
            "model_chips_on": int(chips_on.points.sum()),
        }
        per_season[season] = row
        print(f"[capt_ci] {season}: capture {row['capt_capture_off']:.3f}->"
             f"{row['capt_capture_on']:.3f}  capt_mean {row['capt_mean_off']}->"
             f"{row['capt_mean_on']}  model+chips {row['model_chips_off']}->"
             f"{row['model_chips_on']}", flush=True)

    if not per_season:
        raise RuntimeError(f"every season failed: {failed_seasons}")

    done_seasons = list(per_season)
    full_log = pd.concat(all_frames, ignore_index=True)

    deltas = {
        "capt_capture": [per_season[s]["capt_capture_on"] - per_season[s]["capt_capture_off"]
                         for s in done_seasons],
        "capt_mean": [per_season[s]["capt_mean_on"] - per_season[s]["capt_mean_off"]
                     for s in done_seasons],
        "model_chips": [per_season[s]["model_chips_on"] - per_season[s]["model_chips_off"]
                       for s in done_seasons],
    }
    season_ci = {m: paired_t_interval(deltas[m]) for m in METRICS}

    cap_off_log = full_log[full_log.arm == "cap_off"]
    cap_on_log = full_log[full_log.arm == "cap_on"]
    chips_off_log = full_log[full_log.arm == "chips_off"]
    chips_on_log = full_log[full_log.arm == "chips_on"]

    gw_ci = {
        "capt_capture": paired_cluster_bootstrap(
            cap_off_log, cap_on_log, ["capt_pts", "best_pts"], True, bootstrap_n, seed),
        "capt_mean": paired_cluster_bootstrap(
            cap_off_log, cap_on_log, ["points"], False, bootstrap_n, seed),
        "model_chips": paired_cluster_bootstrap(
            chips_off_log, chips_on_log, ["points"], False, bootstrap_n, seed),
    }

    metrics = {}
    for m in METRICS:
        metrics[m] = {
            "n_seasons": season_ci[m]["n"],
            "mean_delta": round(season_ci[m]["mean"], 4),
            "season_se": round(season_ci[m]["se"], 4),
            "season_ci": [round(season_ci[m]["ci_lo"], 4), round(season_ci[m]["ci_hi"], 4)],
            "gw_bootstrap_ci": [round(gw_ci[m]["ci_lo"], 4), round(gw_ci[m]["ci_hi"], 4)],
            "gw_bootstrap_n_pairs": gw_ci[m]["n_gw_pairs"],
            "gw_bootstrap_resamples": gw_ci[m]["n_resamples"],
        }

    return {
        "seasons": done_seasons,
        "failed_seasons": failed_seasons,
        "resampling_units": {
            "season_clustered": (
                "Paired two-sided t-interval (df = n_seasons - 1) on the "
                "per-season on-minus-off deltas; n = number of seasons "
                "actually measured. The conservative, correctly-clustered "
                "reading -- GOVERNS the verdict."),
            "gameweek_bootstrap": (
                "Percentile interval from a paired cluster bootstrap: "
                "resample (season, gameweek) pairs WITH REPLACEMENT, "
                "stratified within season (each season's own row count is "
                "preserved every draw), recomputing the ratio-of-sums (or "
                "sum) each draw; n = total gameweek pairs across seasons. "
                "Higher-power but OPTIMISTIC -- gameweeks within a season "
                "are NOT independent (squad state carries across "
                "gameweeks through transfers), so this reading does not "
                "govern the verdict."),
        },
        "per_season": per_season,
        "metrics": metrics,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default=None,
                    help="comma-separated subset of walk_forward.TEST_SEASONS "
                         "(default: all 6)")
    ap.add_argument("--force", action="store_true",
                    help="rebuild the per-season cached frame even if already on disk")
    ap.add_argument("--bootstrap", type=int, default=BOOTSTRAP_N,
                    help="gameweek-level bootstrap resample count")
    ap.add_argument("--seed", type=int, default=SEED,
                    help="bootstrap RNG seed")
    args = ap.parse_args(argv)

    if args.seasons:
        seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
        unknown = [s for s in seasons if s not in TEST_SEASONS]
        if unknown:
            raise SystemExit(f"unknown season(s) {unknown} -- valid: {TEST_SEASONS}")
    else:
        seasons = list(TEST_SEASONS)

    # All experiment flags off (F6/F7): capt_ceiling gates no features, and
    # every other flag stays at its default-off state, matching the baseline
    # (wf_baseline_phase9.csv) and adoption (wf_capt_ceiling_adopt.csv) runs
    # this module's Task-1 reproduction check is checked against.
    df = load_features()
    df = apply_experiment_feature_gating(df, {})

    result = measure_all(seasons, df, force=args.force,
                         bootstrap_n=args.bootstrap, seed=args.seed)

    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.EXPERIMENTS_DIR / "capt_ceiling_ci.json"
    write_json(result, dest, indent=1)

    print(f"\n[capt_ci] seasons measured: {result['seasons']}")
    if result["failed_seasons"]:
        print(f"[capt_ci] FAILED seasons: {result['failed_seasons']}", file=sys.stderr)
    for m, stats in result["metrics"].items():
        print(f"[capt_ci] {m}: mean_delta={stats['mean_delta']} "
             f"season_ci={stats['season_ci']} (n={stats['n_seasons']})  "
             f"gw_bootstrap_ci={stats['gw_bootstrap_ci']} "
             f"(n={stats['gw_bootstrap_n_pairs']})")
    print(f"[capt_ci] saved {dest.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
