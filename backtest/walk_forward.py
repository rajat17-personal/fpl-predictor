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
import sys

import numpy as np
import pandas as pd
from scipy.stats import poisson, skellam

import config
from backtest.season import run_season
from data import team_strength as ts_mod
from models import captaincy
from models.train import load_features, predict_xp, train_predict
from ops.jsonio import write_json

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
    ap.add_argument("--optimistic-plan", action="store_true",
                    help="also compute the OPTIMISTIC multi-GW plan (_plan_col, which "
                         "peeks at future GWs' own predictions) and report it as "
                         "multi_optimistic beside the honest multi_safe (D-06) -- the "
                         "gap between the two is the project's own repeated "
                         "+337-optimistic-vs-+40-honest failure mode, made visible "
                         "rather than assumed away for any horizon-touching change")
    args = ap.parse_args(argv)

    exp = config.resolve_experiments(args.experiments)
    capt_col_active = "xp_capt_ceiling" if exp["capt_ceiling"] else None
    capt_lambda = (config.CAPT_CEILING_LAMBDA if args.capt_lambda is None
                   else args.capt_lambda)
    chips_hysteresis = (config.CHIPS_V2_HYSTERESIS if args.chips_hysteresis is None
                        else args.chips_hysteresis)

    if args.seasons:
        seasons = [s.strip() for s in args.seasons.split(",") if s.strip()]
        unknown = [s for s in seasons if s not in TEST_SEASONS]
        if unknown:
            raise SystemExit(f"unknown season(s) {unknown} -- valid: {TEST_SEASONS}")
    else:
        seasons = list(TEST_SEASONS)

    df = load_features()
    rows, chip_recs = [], []
    for T in seasons:
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
                              capt_col=capt_col_active,
                              scheduler="v2" if exp["chips_v2"] else "v1",
                              chips_hysteresis=chips_hysteresis)
        chip_recs.extend({"season": T, **d} for d in chips_df.attrs["chip_deltas"])
        cdf = run_season(te, "xp_med", capt_col=capt_col_active or "xp_mean", use_chips=False)
        capt_mean = int(cdf.points.sum())
        capt_capture = cdf.capt_pts.sum() / max(cdf.best_pts.sum(), 1)
        m_safe = int(run_season(leakage_safe_plan(te, models, cols,
                                                  team_strength=exp["team_strength"]),
                                "xp_plan", use_chips=False).points.sum())     # leakage-safe
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
    gm = res.mean().round(0).astype(int)
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
    print(f"  multi-GW (SAFE)  : {gm['multi_safe']}   -> vs myopic core "
          f"{gm['multi_safe']-gm['model_mean']:+d} (leakage-free, honest)")
    if args.optimistic_plan:
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
            "capt_lambda": capt_lambda,
            "chips_hysteresis": chips_hysteresis,
            "model_mean": int(gm["model_mean"]),
            "model_std": int(season_std),
            "model+chips": int(gm["model+chips"]),
            "capt_mean": int(gm["capt_mean"]),
            "capt_capture": capt_capture_avg,
            "multi_safe": int(gm["multi_safe"]),
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
          f"experiments={','.join(active_flags) or 'none'} capt_lambda={capt_lambda} "
          f"chips_hysteresis={chips_hysteresis} "
          f"model_mean={gm['model_mean']} "
          f"model+chips={gm['model+chips']} capt_capture={capt_capture_avg}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
