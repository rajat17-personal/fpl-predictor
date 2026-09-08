"""Dixon-Coles / Poisson team attack and defence ratings, fit on an expanding
pre-gameweek window per season -> ordinary input feature columns for the
existing per-position LightGBM regressor.

Why: the adopted bookmaker-odds features (data/odds.py) have two verified
holes -- the `team` name column is 0% populated for 2016-17 through 2019-20
(so the odds join is null there too), and a manager's multi-gameweek horizon
has no posted odds for future fixtures. Ratings computed from results-to-date
fill both, keyed on the numeric (season, team_id) pair reconstructed from
`opponent_team_id` -- never on the club name column, which is exactly what
makes the 2016-19 seasons fillable.

NON-GOAL, stated explicitly: these ratings are inputs to the existing
per-position LightGBM regressor and NOTHING else. Re-deriving points as a
clean-sheet probability times four plus a residual is the `ComponentModel`
decomposition measured at -50 points/season and rejected (IMPROVEMENTS.md
Phase C). `ts_pcs` is a feature column; it is never combined arithmetically
into a predicted-points value here or anywhere downstream of this module.

LEAKAGE SAFETY: `fit_ratings_as_of()` must be called with matches strictly
before the target gameweek only -- fitting on a whole season is the sharpest
leakage risk in this option (09-RESEARCH.md Pitfall 2) and is exactly what
`tests/test_leakage.py::test_team_strength_ratings_reproducible_from_prior_matches`
guards against.

Run:
  python -m data.team_strength    # (re)build data/processed/team_strength.parquet
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson, skellam

import config

_OUT = config.PROCESSED_DIR / "team_strength.parquet"
MIN_MATCHES = 20   # below this, emit neutral (zero) ratings rather than fit on noise


def _fixture_side_map(df: pd.DataFrame) -> np.ndarray:
    """Each row's own numeric team id, reconstructed from the two distinct
    `opponent_team_id` values within its (season, fixture_id) group.

    The `team` name column is 0% populated for 2016-17 through 2019-20 (see
    module docstring), so a name-keyed reconstruction would inherit exactly
    the same hole this option exists to fill. Within a fixture, a row whose
    `opponent_team_id` is one of the two distinct values belongs to the other.
    """
    g = df.groupby(["season", "fixture_id"])["opponent_team_id"]
    lo = g.transform("min")
    hi = g.transform("max")
    return np.where(df["opponent_team_id"] == lo, hi, lo)


def build_matches(player_gw: pd.DataFrame) -> pd.DataFrame:
    """Collapse the player-fixture table to one row per (season, fixture_id):
    `season, gw, kickoff_time, home_id, away_id, home_goals, away_goals`.

    Drops individual fixtures that cannot be reconstructed (known vaastav
    data gaps -- e.g. a COVID-rescheduled 2019-20 fixture whose non-scoring
    side never got a backfilled row for the replayed gameweek, so it loses
    one of its two sides once rows without a recorded score are dropped) but
    RAISES if a season loses more than a handful of fixtures this way -- that
    scale of loss means a systemic reconstruction failure, not a one-off gap,
    and would otherwise silently yield half a league.
    """
    MIN_FIXTURES_PER_SEASON = 370   # tolerate a few known one-off data gaps, not a
                                    # systemic failure (full season is 380)

    need = ["season", "fixture_id", "gw", "kickoff_time", "opponent_team_id",
            "was_home", "team_h_score", "team_a_score"]
    df = player_gw[need].dropna(subset=need).copy()
    df["opponent_team_id"] = df["opponent_team_id"].astype(int)

    nsides = df.groupby(["season", "fixture_id"])["opponent_team_id"].transform("nunique")
    bad = df.loc[nsides != 2, ["season", "fixture_id"]].drop_duplicates()
    if len(bad):
        print(f"  [team_strength] dropping {len(bad)} fixture(s) missing one side "
              f"after requiring a recorded score (known data gap): "
              f"{bad.to_dict('records')}")
        df = df[nsides == 2]
    df["own_id"] = _fixture_side_map(df)

    home_side = (df[df["was_home"]]
                 .drop_duplicates(subset=["season", "fixture_id"])
                 [["season", "fixture_id", "gw", "kickoff_time", "own_id",
                   "team_h_score", "team_a_score"]]
                 .rename(columns={"own_id": "home_id"}))
    away_side = (df[~df["was_home"]]
                 .drop_duplicates(subset=["season", "fixture_id"])
                 [["season", "fixture_id", "own_id"]]
                 .rename(columns={"own_id": "away_id"}))
    matches = home_side.merge(away_side, on=["season", "fixture_id"], how="inner")

    matches["home_id"] = matches["home_id"].astype(int)
    matches["away_id"] = matches["away_id"].astype(int)
    matches["gw"] = matches["gw"].astype(int)
    matches["home_goals"] = matches.pop("team_h_score").astype(int)
    matches["away_goals"] = matches.pop("team_a_score").astype(int)

    counts = matches.groupby("season").size()
    systemic = counts[counts < MIN_FIXTURES_PER_SEASON]
    if len(systemic):
        raise AssertionError(
            f"season(s) with far fewer than 380 fixtures recovered -- a systemic "
            f"reconstruction failure, not a one-off data gap: {systemic.to_dict()}"
        )
    short = counts[(counts >= MIN_FIXTURES_PER_SEASON) & (counts < 380)]
    if len(short):
        print(f"  [team_strength] season(s) short of the full 380 fixtures "
              f"(known one-off data gaps): {short.to_dict()}")
    return matches.reset_index(drop=True)


def dc_log_likelihood(params: np.ndarray, home_idx: np.ndarray, away_idx: np.ndarray,
                      home_goals: np.ndarray, away_goals: np.ndarray, n_teams: int) -> float:
    """Dixon-Coles negative log-likelihood (Dixon and Coles 1997) over the
    given matches. `home_idx`/`away_idx` are 0-based indices into a fixed
    team ordering (not raw team ids) built by the caller.

    Minimised via `scipy.optimize.minimize` -- scipy is already a locked
    project dependency and hand-rolling the optimiser (vs. hand-rolling this
    likelihood, which is appropriate) adds numerical risk for no benefit.
    """
    attack = params[:n_teams]
    defence = params[n_teams:2 * n_teams]
    home_adv, rho = params[-2], params[-1]

    lam = np.exp(attack[home_idx] + defence[away_idx] + home_adv)
    mu = np.exp(attack[away_idx] + defence[home_idx])
    ll = poisson.logpmf(home_goals, lam) + poisson.logpmf(away_goals, mu)

    # Low-score correlation correction -- applies only to the 0-0, 1-0, 0-1
    # and 1-1 scorelines (Dixon and Coles 1997); every other scoreline keeps
    # tau == 1 (no correction).
    tau = np.ones_like(lam)
    m00 = (home_goals == 0) & (away_goals == 0)
    m01 = (home_goals == 0) & (away_goals == 1)
    m10 = (home_goals == 1) & (away_goals == 0)
    m11 = (home_goals == 1) & (away_goals == 1)
    tau = np.where(m00, 1 - lam * mu * rho, tau)
    tau = np.where(m01, 1 + lam * rho, tau)
    tau = np.where(m10, 1 + mu * rho, tau)
    tau = np.where(m11, 1 - rho, tau)
    tau = np.clip(tau, 1e-10, None)   # guard log() during mid-search excursions
    ll = ll + np.log(tau)
    return -ll.sum()


RIDGE = 0.1   # L2 shrinkage on attack/defence toward zero, applied only in
              # fit_ratings_as_of's wrapper objective (dc_log_likelihood itself
              # stays the pure, unregularized NLL). Measured need: an unregularized
              # BFGS fit at the MIN_MATCHES=20 floor (a 42-parameter model over just
              # 20 matches, i.e. 40 goal observations -- hopelessly underdetermined)
              # diverged to |attack|>1e3 and rho>1e9, overflowing exp() into inf/nan.
              # A Gaussian(0, 1/RIDGE) prior keeps thin-data fits well-posed and
              # shrinks toward zero (a neutral rating) exactly when data is thin --
              # the correct behaviour for an expanding-window fit that gets less
              # regularized, more data-driven, as the season accumulates matches.
_BOUNDS_BUFFER = 3.0   # attack/defence bound; exp(3)=20 is already a wildly
                       # improbable expected-goals multiplier, so this only
                       # stops runaway divergence, not realistic fits


def fit_ratings_as_of(matches_before_gw: pd.DataFrame) -> pd.DataFrame:
    """Fit Dixon-Coles attack/defence ratings from `matches_before_gw` ONLY.

    The caller is responsible for passing only matches strictly before the
    target gameweek -- fitting on a whole season (or on any match at or after
    the target gameweek) leaks a result the decision was never allowed to
    see. Returns one row per team (`attack`, `defence`, `home_adv`, `rho`),
    indexed by `team_id`.
    """
    teams = sorted(set(matches_before_gw["home_id"]) | set(matches_before_gw["away_id"]))
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    home_idx = matches_before_gw["home_id"].map(idx).to_numpy()
    away_idx = matches_before_gw["away_id"].map(idx).to_numpy()
    home_goals = matches_before_gw["home_goals"].to_numpy(dtype=float)
    away_goals = matches_before_gw["away_goals"].to_numpy(dtype=float)

    def _ridge_objective(p: np.ndarray) -> float:
        nll = dc_log_likelihood(p, home_idx, away_idx, home_goals, away_goals, n)
        return nll + 0.5 * RIDGE * float(np.sum(p[:2 * n] ** 2))

    x0 = np.concatenate([np.zeros(2 * n), [0.3, -0.1]])   # attack, defence, home_adv, rho
    bounds = ([(-_BOUNDS_BUFFER, _BOUNDS_BUFFER)] * (2 * n)
              + [(-2.0, 2.0), (-0.9, 0.9)])
    res = minimize(_ridge_objective, x0, method="L-BFGS-B", bounds=bounds)
    x = res.x
    attack, defence = x[:n], x[n:2 * n]
    home_adv, rho = float(x[-2]), float(x[-1])

    # attack/defence are identified only up to an additive shift (attack += c,
    # defence -= c leaves every lambda/mu unchanged) -- recentre to mean-zero
    # attack so successive per-gameweek fits stay comparable rather than
    # drifting along that flat likelihood direction.
    c = attack.mean()
    attack = attack - c
    defence = defence + c

    return pd.DataFrame({"team_id": teams, "attack": attack, "defence": defence,
                         "home_adv": home_adv, "rho": rho}).set_index("team_id")


def build() -> pd.DataFrame:
    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet")
    matches = build_matches(raw)
    print(f"[team_strength] matches: {len(matches):,} fixtures over "
          f"{matches['season'].nunique()} seasons")

    rows = []
    for season, smatches in matches.groupby("season", sort=False):
        smatches = smatches.sort_values(["gw", "kickoff_time"])
        teams = sorted(set(smatches["home_id"]) | set(smatches["away_id"]))
        gws = sorted(smatches["gw"].unique())
        n_neutral = 0
        for g in gws:
            prior = smatches[smatches["gw"] < g]
            if len(prior) < MIN_MATCHES:
                for t in teams:
                    rows.append({"season": season, "gw": int(g), "team_id": int(t),
                                "attack": 0.0, "defence": 0.0, "home_adv": 0.0,
                                "rho": 0.0, "neutral": True})
                n_neutral += len(teams)
                continue
            fit = fit_ratings_as_of(prior)
            for t, r in fit.iterrows():
                rows.append({"season": season, "gw": int(g), "team_id": int(t),
                            "attack": float(r["attack"]), "defence": float(r["defence"]),
                            "home_adv": float(r["home_adv"]), "rho": float(r["rho"]),
                            "neutral": False})
        print(f"  [team_strength] {season}: {len(gws)} gameweeks, {len(teams)} teams, "
              f"{n_neutral} neutral-filled rows")

    out = pd.DataFrame(rows)
    out.to_parquet(_OUT, index=False)
    return out


def ratings_as_of(season: str, gw: int) -> pd.DataFrame:
    """Per-team rating rows for exactly this (season, gw), indexed by
    `team_id`. The accessor the multi-gameweek horizon graft needs -- do not
    inline this into a join."""
    t = pd.read_parquet(_OUT)
    sub = t[(t["season"] == season) & (t["gw"] == gw)]
    return sub.set_index("team_id")


def attach(full: pd.DataFrame) -> pd.DataFrame:
    """Join team-strength ratings onto a player_gw-shaped frame, producing
    `config.TEAM_STRENGTH_COLS`. Asserts the join leaves the row count
    unchanged, exactly like `data/fbref.py::attach`. Returns `full` unchanged
    (no-op) when `data/processed/team_strength.parquet` is absent, matching
    every other optional enrichment source's contract."""
    if not _OUT.exists():
        return full
    ratings = pd.read_parquet(_OUT)

    need = ["season", "fixture_id", "opponent_team_id", "was_home", "gw"]
    missing = [c for c in need if c not in full.columns]
    if missing:
        raise AssertionError(f"attach(): full is missing required columns {missing}")

    nsides = full.groupby(["season", "fixture_id"])["opponent_team_id"].transform("nunique")
    has_fixture = full["fixture_id"].notna()
    if (nsides[has_fixture] != 2).any():
        raise AssertionError("attach(): a fixture does not have exactly two sides")

    tmp = full.copy()
    tmp["_own_id"] = _fixture_side_map(tmp)

    self_r = (ratings.rename(columns={"team_id": "_own_id", "attack": "ts_attack_self",
                                      "defence": "ts_defence_self"})
              [["season", "gw", "_own_id", "ts_attack_self", "ts_defence_self",
                "home_adv"]])
    opp_r = (ratings.rename(columns={"team_id": "opponent_team_id",
                                     "attack": "ts_attack_opp", "defence": "ts_defence_opp"})
             [["season", "gw", "opponent_team_id", "ts_attack_opp", "ts_defence_opp"]])

    before = len(tmp)
    merged = tmp.merge(self_r, on=["season", "gw", "_own_id"], how="left")
    merged = merged.merge(opp_r, on=["season", "gw", "opponent_team_id"], how="left")
    if len(merged) != before:   # a many-to-many join here corrupts every backtest
        raise AssertionError(f"team_strength join changed row count {before} -> {len(merged)}")

    is_home = merged["was_home"].fillna(False).astype(float)
    merged["ts_xg_for"] = np.exp(merged["ts_attack_self"] + merged["ts_defence_opp"]
                                 + merged["home_adv"] * is_home)
    merged["ts_xg_against"] = np.exp(merged["ts_attack_opp"] + merged["ts_defence_self"]
                                     + merged["home_adv"] * (1 - is_home))
    merged["ts_pwin"] = skellam.sf(0, merged["ts_xg_for"], merged["ts_xg_against"])
    merged["ts_pcs"] = poisson.pmf(0, merged["ts_xg_against"])

    merged = merged.drop(columns=["_own_id", "home_adv"])
    cov = merged["ts_attack_self"].notna().mean()
    print(f"  [team_strength] joined; coverage {cov:.1%}")
    return merged


def main() -> int:
    out = build()
    print(f"\nteam_strength: {len(out):,} rows over {out['season'].nunique()} seasons")
    summary = out.groupby("season").agg(gws=("gw", "nunique"), teams=("team_id", "nunique"),
                                        rows=("gw", "size"), neutral=("neutral", "sum"))
    print(summary.to_string())
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
