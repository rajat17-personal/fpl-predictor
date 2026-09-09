"""Quick task 260909-5vx: per-position, per-coverage re-measurement of the
understat and fotmob enrichment sources' effect on `xp_med` accuracy.

Phase 9 (09-08/09-09) measured both sources pooled over ALL positions and ALL
rows. The model is per-position and the enrichment join is partial, so a real
positional gain could have been diluted twice over. This module re-slices the
same leakage-safe predictions by position (GK/DEF/MID/FWD/ALL) and by two
distinct coverage definitions:

  - `row_joined` / `row_unjoined`: whether the enrichment source's RAW value
    joined onto that exact player-match at all (the ~40% figure Phase 9
    reported for the per-match join).
  - `feat_present` / `feat_absent`: whether the ROLLED feature the model
    actually consumes (`us_npxg_r5`, `fm_tackles_r5`) was non-null for that
    row (~89%). A row can be `feat_present` while not `row_joined`, because
    the rolling windows are cumulative over prior matches -- one historical
    join makes every later row non-null.

Every delta between the "on" and "off" configs carries a paired 95% interval:
a normal interval on the per-row absolute-error difference for MAE, a
200-resample paired bootstrap for Spearman. This is measurement-only: it
never retrains into `models/artifacts/`, never mutates any pipeline artifact,
and never writes outside `config.EXPERIMENTS_DIR`.

Run:
  python -m backtest.enrichment_slices                       # full 6 seasons
  python -m backtest.enrichment_slices --seasons 2025-26      # one season (smoke)
  python -m backtest.enrichment_slices --force                # rebuild caches
  python -m backtest.enrichment_slices --out-name my_run.json
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import config
from backtest.walk_forward import TEST_SEASONS, _preds_for, apply_experiment_feature_gating
from models.train import load_features
from ops.jsonio import write_json

# Passed straight to apply_experiment_feature_gating(); its .get(..., False)
# contract makes an absent key mean off.
CONFIGS = {"off": {}, "understat": {"understat": True}, "fotmob": {"fotmob": True}}
POSITION_SLICES = ["ALL", "GK", "DEF", "MID", "FWD"]
COVERAGE_SLICES = ["all", "row_joined", "row_unjoined", "feat_present", "feat_absent"]
# Maps each enrichment source to the column-name prefix used by its raw /
# rolled columns (data/build_table.py, features/engineer.py).
_SRC_PREFIX = {"understat": "us", "fotmob": "fm"}
PRED_COLS = ["season", "player_id", "fixture_id", "gw", "position",
            "y_points", "y_minutes", "xp_med", "xp_mean"]
KEY = ["season", "player_id", "fixture_id"]
BOOTSTRAP_N = 200
SEED = 0
MIN_CELL_N = 200

_PUBLISHED_UNDERSTAT_POOLED = {
    "mae_off": 1.8751, "mae_on": 1.8761,
    "spearman_off": 0.3620, "spearman_on": 0.3599,
}


def preds_path(cfg: str, season: str):
    """`config.EXPERIMENTS_DIR / enrichment_preds_<cfg>_<season>.parquet`."""
    return config.EXPERIMENTS_DIR / f"enrichment_preds_{cfg}_{season}.parquet"


def build_preds(df_ungated: pd.DataFrame, cfg: str, season: str, force: bool = False) -> pd.DataFrame:
    """Leakage-safe predictions for `(cfg, season)`, cached on disk so a
    re-slice never retrains. `cfg` is a key of `CONFIGS`."""
    path = preds_path(cfg, season)
    if path.exists() and not force:
        print(f"[slices] cached {path.relative_to(config.ROOT)}")
        return pd.read_parquet(path)

    gated = apply_experiment_feature_gating(df_ungated, CONFIGS[cfg])
    te, _models, _cols = _preds_for(gated, season)
    out = te[PRED_COLS].copy()
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path, index=False)
    print(f"[slices] built {path.relative_to(config.ROOT)} ({len(out):,} rows)")
    return out


def coverage_flags() -> pd.DataFrame:
    """Per-(season, player_id, fixture_id) coverage flags for both enrichment
    sources, at two distinct definitions.

    `us_row_joined`/`fm_row_joined` mark whether the enrichment source's raw
    per-match value (`us_npxg`, `fm_tackles` in player_gw.parquet) actually
    joined for that fixture -- the ~40% figure Phase 9 reported.
    `us_feat_present`/`fm_feat_present` mark whether the ROLLED feature the
    model actually consumes (`us_npxg_r5`, `fm_tackles_r5` in
    features.parquet) was non-null for that row -- ~89%, because the rolling
    windows are cumulative over prior matches, so one historical join makes
    every later row non-null even when that exact fixture never joined.
    """
    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                          columns=KEY + ["us_npxg", "fm_tackles"])
    feat = pd.read_parquet(config.PROCESSED_DIR / "features.parquet",
                           columns=KEY + ["us_npxg_r5", "fm_tackles_r5"])
    merged = raw.merge(feat, on=KEY, how="left")
    if len(merged) != len(raw):
        raise AssertionError(
            f"coverage_flags merge changed row count {len(raw)} -> {len(merged)}")

    merged["us_row_joined"] = merged["us_npxg"].notna()
    merged["fm_row_joined"] = merged["fm_tackles"].notna()
    merged["us_feat_present"] = merged["us_npxg_r5"].notna()
    merged["fm_feat_present"] = merged["fm_tackles_r5"].notna()
    return merged[KEY + ["us_row_joined", "fm_row_joined", "us_feat_present", "fm_feat_present"]]


def _safe_spearman(a: np.ndarray, b: np.ndarray) -> tuple[float, bool]:
    """spearmanr(a, b).statistic, tolerating a degenerate constant column
    (non-finite correlation) by treating it as 0.0."""
    val = spearmanr(a, b).statistic
    if not np.isfinite(val):
        return 0.0, True
    return float(val), False


def cell_stats(off, on, y, rng: np.random.Generator, bootstrap_n: int = BOOTSTRAP_N) -> dict:
    """Paired MAE + Spearman comparison of `on` vs `off` against `y`, with a
    95% interval on each delta.

    `off`, `on`, `y` are aligned 1-D arrays (same rows, same order). The MAE
    delta's interval is a paired normal interval on the per-row absolute-
    error difference `d = abs(on - y) - abs(off - y)`. The Spearman delta's
    interval is a `bootstrap_n`-resample paired bootstrap over row indices
    drawn from `rng`. `signal` is True only when `d_mae_hi < 0.0` AND
    `d_spearman_lo > 0.0` -- i.e. both axes improved beyond their own
    interval. Guards `n < MIN_CELL_N` and `n == 0` by returning the full key
    set with `signal` False and a `note` naming the small-sample reason,
    skipping the bootstrap entirely.
    """
    off = np.asarray(off, dtype=float)
    on = np.asarray(on, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(y)

    if n < MIN_CELL_N:
        return {
            "n": n, "mae_off": None, "mae_on": None,
            "d_mae": None, "d_mae_lo": None, "d_mae_hi": None,
            "spearman_off": None, "spearman_on": None,
            "d_spearman": None, "d_spearman_lo": None, "d_spearman_hi": None,
            "signal": False,
            "note": f"n={n} < MIN_CELL_N={MIN_CELL_N}: skipped bootstrap (small-sample guard)",
        }

    abs_off = np.abs(off - y)
    abs_on = np.abs(on - y)
    mae_off = float(abs_off.mean())
    mae_on = float(abs_on.mean())

    d = abs_on - abs_off
    d_mean = float(d.mean())
    d_std = float(d.std(ddof=1)) if n > 1 else 0.0
    half = 1.96 * d_std / np.sqrt(n)
    d_mae_lo = d_mean - half
    d_mae_hi = d_mean + half

    spearman_off, off_degenerate = _safe_spearman(off, y)
    spearman_on, on_degenerate = _safe_spearman(on, y)
    d_spearman = spearman_on - spearman_off

    deltas = np.empty(bootstrap_n)
    for i in range(bootstrap_n):
        idx = rng.integers(0, n, size=n)
        so, _ = _safe_spearman(off[idx], y[idx])
        sn, _ = _safe_spearman(on[idx], y[idx])
        deltas[i] = sn - so
    d_spearman_lo = float(np.percentile(deltas, 2.5))
    d_spearman_hi = float(np.percentile(deltas, 97.5))

    signal = bool(d_mae_hi < 0.0 and d_spearman_lo > 0.0)
    note = ("degenerate constant column treated as spearman=0.0"
           if (off_degenerate or on_degenerate) else "")

    return {
        "n": n,
        "mae_off": round(mae_off, 4), "mae_on": round(mae_on, 4),
        "d_mae": round(d_mean, 4), "d_mae_lo": round(d_mae_lo, 4), "d_mae_hi": round(d_mae_hi, 4),
        "spearman_off": round(spearman_off, 4), "spearman_on": round(spearman_on, 4),
        "d_spearman": round(d_spearman, 4),
        "d_spearman_lo": round(d_spearman_lo, 4), "d_spearman_hi": round(d_spearman_hi, 4),
        "signal": signal, "note": note,
    }


def slice_all(seasons: list[str], bootstrap_n: int = BOOTSTRAP_N) -> dict:
    """Position x coverage cell_stats grid for both enrichment sources, read
    from the on-disk prediction caches (must already exist for every
    `(config, season)` pair in `seasons`)."""
    rng = np.random.default_rng(SEED)
    coverage = coverage_flags()

    cells: dict = {}
    for source in ("understat", "fotmob"):
        off_frames = [pd.read_parquet(preds_path("off", s)) for s in seasons]
        on_frames = [pd.read_parquet(preds_path(source, s)) for s in seasons]
        off_df = pd.concat(off_frames, ignore_index=True)
        on_df = pd.concat(on_frames, ignore_index=True)

        merged = off_df.merge(on_df[KEY + ["xp_med"]], on=KEY, how="inner",
                              suffixes=("_off", "_on"))
        if len(merged) != len(off_df):
            raise AssertionError(
                f"{source}: off/on merge changed row count {len(off_df)} -> {len(merged)}")

        merged = merged.merge(coverage, on=KEY, how="left")
        played = merged[merged.y_minutes > 0].reset_index(drop=True)

        prefix = _SRC_PREFIX[source]
        row_joined_col = f"{prefix}_row_joined"
        feat_present_col = f"{prefix}_feat_present"

        cells[source] = {}
        for pos in POSITION_SLICES:
            pos_df = played if pos == "ALL" else played[played.position == pos]
            cells[source][pos] = {}
            for cov in COVERAGE_SLICES:
                if cov == "all":
                    cov_df = pos_df
                elif cov == "row_joined":
                    cov_df = pos_df[pos_df[row_joined_col]]
                elif cov == "row_unjoined":
                    cov_df = pos_df[~pos_df[row_joined_col].astype(bool)]
                elif cov == "feat_present":
                    cov_df = pos_df[pos_df[feat_present_col]]
                else:  # feat_absent
                    cov_df = pos_df[~pos_df[feat_present_col].astype(bool)]
                cells[source][pos][cov] = cell_stats(
                    cov_df["xp_med_off"].to_numpy(), cov_df["xp_med_on"].to_numpy(),
                    cov_df["y_points"].to_numpy(), rng, bootstrap_n=bootstrap_n)

    understat_pooled = cells["understat"]["ALL"]["all"]
    observed = {k: understat_pooled[k] for k in
               ("mae_off", "mae_on", "spearman_off", "spearman_on")}
    abs_diff = {k: (round(abs(observed[k] - _PUBLISHED_UNDERSTAT_POOLED[k]), 4)
                   if observed[k] is not None else None)
               for k in observed}

    return {
        "seasons": seasons,
        "bootstrap_n": bootstrap_n,
        "seed": SEED,
        "min_cell_n": MIN_CELL_N,
        "coverage_definitions": {
            "row_joined": "the enrichment source's RAW per-match value "
                         "(us_npxg / fm_tackles in player_gw.parquet) joined for "
                         "this exact fixture -- Phase 9's original ~40% figure.",
            "feat_present": "the ROLLED feature the model actually consumes "
                            "(us_npxg_r5 / fm_tackles_r5 in features.parquet) was "
                            "non-null for this row -- ~89%, since rolling windows are "
                            "cumulative over prior matches (one historical join makes "
                            "every later row non-null even without a same-fixture join).",
        },
        "reproduction_check": {
            "published": _PUBLISHED_UNDERSTAT_POOLED,
            "observed": observed,
            "abs_diff": abs_diff,
        },
        "cells": cells,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default=None,
                    help="comma-separated subset of walk_forward.TEST_SEASONS "
                         "(default: all 6)")
    ap.add_argument("--force", action="store_true",
                    help="rebuild prediction caches even if already on disk")
    ap.add_argument("--bootstrap", type=int, default=BOOTSTRAP_N,
                    help="Spearman-delta bootstrap resample count")
    ap.add_argument("--out-name", default="enrichment_position_coverage.json",
                    help="bare filename under config.EXPERIMENTS_DIR (no path "
                         "separators or parent-directory references)")
    args = ap.parse_args(argv)

    if args.seasons:
        seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
        unknown = [s for s in seasons if s not in TEST_SEASONS]
        if unknown:
            raise SystemExit(f"unknown season(s) {unknown} -- valid: {TEST_SEASONS}")
    else:
        seasons = list(TEST_SEASONS)

    out_name = args.out_name
    if "/" in out_name or "\\" in out_name or ".." in out_name:
        raise SystemExit(
            f"--out-name must be a bare filename with no path separators or "
            f"parent-directory references, got {out_name!r}")

    df = load_features()
    for cfg in CONFIGS:
        for season in seasons:
            build_preds(df, cfg, season, force=args.force)

    summary = slice_all(seasons, bootstrap_n=args.bootstrap)
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.EXPERIMENTS_DIR / out_name
    write_json(summary, dest, indent=1)

    for source in ("understat", "fotmob"):
        allall = summary["cells"][source]["ALL"]["all"]
        print(f"[slices] {source} ALL/all: n={allall['n']} "
             f"mae_off={allall['mae_off']} mae_on={allall['mae_on']} d_mae={allall['d_mae']} "
             f"[{allall['d_mae_lo']}, {allall['d_mae_hi']}]")
        any_signal = False
        for pos, covs in summary["cells"][source].items():
            for cov, c in covs.items():
                if c.get("signal"):
                    any_signal = True
                    print(f"[slices]   SIGNAL {source}/{pos}/{cov}: n={c['n']} "
                         f"d_mae={c['d_mae']} [{c['d_mae_lo']}, {c['d_mae_hi']}] "
                         f"d_spearman={c['d_spearman']} [{c['d_spearman_lo']}, {c['d_spearman_hi']}]")
        if not any_signal:
            print(f"[slices]   no cell reached signal for {source}")

    rc = summary["reproduction_check"]
    print(f"[slices] reproduction check (understat pooled ALL/all): "
         f"observed={rc['observed']} published={rc['published']} abs_diff={rc['abs_diff']}")
    print(f"[slices] saved {dest.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
