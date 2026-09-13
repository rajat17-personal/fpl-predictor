"""Leakage regression tests (frozen versions of the manual Phase-2 checks)."""
import numpy as np
import pandas as pd
import pytest

import config
from data import team_strength

FEATURES = config.PROCESSED_DIR / "features.parquet"
RAW = config.PROCESSED_DIR / "player_gw.parquet"
TEAM_STRENGTH = config.PROCESSED_DIR / "team_strength.parquet"
UNDERSTAT = config.PROCESSED_DIR / "understat.parquet"
FOTMOB = config.PROCESSED_DIR / "fotmob.parquet"
TRANSFERMARKT = config.DATA_DIR / "external" / "transfermarkt" / "injury_spells.csv"
needs_data = pytest.mark.skipif(not (FEATURES.exists() and RAW.exists()),
                                reason="run the data pipeline first")


@pytest.fixture(scope="module")
def feat():
    return pd.read_parquet(FEATURES)


@needs_data
def test_first_appearance_has_no_rolling_features(feat):
    roll_cols = [c for c in feat.columns
                 if any(c.endswith(sfx) for sfx in ("_r3", "_r5", "_r10", "_rall"))]
    first = (feat.sort_values(["season", "player_id", "kickoff_time"])
             .groupby(["season", "player_id"]).head(1))
    assert first[roll_cols].notna().any(axis=1).sum() == 0


@needs_data
def test_minutes_r5_matches_independent_recompute(feat):
    raw = pd.read_parquet(RAW)
    season = "2023-24"
    pid = feat.loc[feat.season == season, "player_id"].value_counts().index[0]
    got = (feat[(feat.season == season) & (feat.player_id == pid)]
           .sort_values("kickoff_time")["minutes_r5"])
    exp = (raw[(raw.season == season) & (raw.player_id == pid)]
           .sort_values("kickoff_time")["minutes"]
           .shift(1).rolling(5, min_periods=1).mean())
    assert np.allclose(got.fillna(-1).values, exp.fillna(-1).values)


@needs_data
def test_zero_minutes_never_scores_positive(feat):
    """A non-playing player cannot EARN points. (Exactly-zero is almost always
    true, but ~14 rows/253k are unused subs shown a card from the bench -> -1/-3.)"""
    zero = feat[feat.y_minutes == 0]
    assert (zero.y_points <= 0).all()
    assert (zero.y_points == 0).mean() > 0.999


@pytest.mark.skipif(not TEAM_STRENGTH.exists(),
                    reason="run `python -m data.team_strength` first")
def test_team_strength_ratings_reproducible_from_prior_matches():
    """D-06's explicit leakage requirement: a stored (season, gw, team) rating
    row must be exactly reproducible from an independently rebuilt match table
    truncated to matches strictly before that gameweek -- never from the whole
    season (Pitfall 2, 09-RESEARCH.md)."""
    ratings = pd.read_parquet(TEAM_STRENGTH)

    # One row per (season, gw, team_id), never per (season, team_id) -- a
    # season-level fit (Pitfall 2's own stated warning sign) would collapse
    # every gameweek in a season onto a single row and fail this.
    assert ratings.duplicated(["season", "gw", "team_id"]).sum() == 0

    raw = pd.read_parquet(RAW)
    matches = team_strength.build_matches(raw)

    season, gw = "2022-23", 20
    fitted = ratings[(ratings.season == season) & (ratings.gw == gw) & (~ratings.neutral)]
    assert not fitted.empty, f"no fitted (non-neutral) ratings stored for {season} GW{gw}"

    prior = matches[(matches.season == season) & (matches.gw < gw)]
    recomputed = team_strength.fit_ratings_as_of(prior)

    stored = fitted.set_index("team_id")
    common = stored.index.intersection(recomputed.index)
    assert len(common) == len(stored)
    # atol=1e-4 is still >10x tighter than the optimizer's own convergence
    # noise floor (observed: BLAS thread-count-dependent floating-point
    # reduction order gives ~1e-6 absolute jitter between two runs of the
    # identical fit) while remaining >1000x tighter than the attack/defence
    # scale (sd ~0.4) -- a real leakage bug (fitting on the whole season, or
    # on any match at/after gw) moves these values by orders of magnitude
    # more than this, not by optimizer noise.
    np.testing.assert_allclose(stored.loc[common, "attack"].to_numpy(),
                               recomputed.loc[common, "attack"].to_numpy(), atol=1e-4)
    np.testing.assert_allclose(stored.loc[common, "defence"].to_numpy(),
                               recomputed.loc[common, "defence"].to_numpy(), atol=1e-4)


def _make_fixture_rows(season, fixture_id, gw, team_a=1, team_b=2, score_a=1, score_b=0):
    """Two rows (home + away) for one synthetic fixture -- the minimal shape
    `team_strength.build_matches` needs (a fixture's two sides reconstructed
    from the two distinct `opponent_team_id` values within its group)."""
    ts = pd.Timestamp(f"2020-01-{1 + (fixture_id % 27):02d}", tz="UTC")
    return [
        {"season": season, "fixture_id": fixture_id, "gw": gw, "kickoff_time": ts,
         "opponent_team_id": team_b, "was_home": True,
         "team_h_score": score_a, "team_a_score": score_b},
        {"season": season, "fixture_id": fixture_id, "gw": gw, "kickoff_time": ts,
         "opponent_team_id": team_a, "was_home": False,
         "team_h_score": score_a, "team_a_score": score_b},
    ]


def test_build_matches_tolerates_a_partial_current_season_but_not_a_partial_past_one():
    """Regression (Phase 8 plan 08-03 Task 3): player_gw.parquet now
    legitimately carries the in-progress current season for the first time
    (Phase 8's own capture). build_matches must not raise its
    systemic-reconstruction-failure alarm for a season that is simply not
    finished yet, while still raising it for a genuinely broken PAST
    (long-since-complete) season showing the exact same low fixture count."""
    rows = []
    for fid in range(1, 6):        # 5 fixtures -- far below MIN_FIXTURES_PER_SEASON
        rows += _make_fixture_rows(config.CURRENT_SEASON, fid, gw=1)
    for fid in range(101, 106):    # identical shortfall, but a PAST season
        rows += _make_fixture_rows("2019-20", fid, gw=1)
    df = pd.DataFrame(rows)

    current_only = df[df["season"] == config.CURRENT_SEASON]
    matches = team_strength.build_matches(current_only)
    assert set(matches["season"]) == {config.CURRENT_SEASON}
    assert len(matches) == 5

    with pytest.raises(AssertionError, match="systemic"):
        team_strength.build_matches(df[df["season"] == "2019-20"])


@pytest.mark.skipif(not (FEATURES.exists() and UNDERSTAT.exists()),
                    reason="run `python -m data.understat` then rebuild the pipeline first")
def test_understat_features_are_rolled_not_raw(feat):
    """09-08's leakage requirement: Understat's per-match npxG/involvement
    stats describe the MATCH THEY CAME FROM (a match outcome) -- they must
    reach the feature matrix only through the shift(1)-then-rolling path
    (config.UNDERSTAT_COLS registered in ROLL_STATS), never as bare pre-match
    context. Mirrors test_minutes_r5_matches_independent_recompute's own
    recompute-and-compare template."""
    bare = [c for c in config.UNDERSTAT_COLS if c in feat.columns]
    assert not bare, f"raw understat columns leaked into the feature matrix: {bare}"

    rolled = [c for c in feat.columns
             if c.startswith("us_") and c.split("_")[-1].startswith("r")]
    assert rolled, "no rolled understat feature columns found -- was the pipeline rebuilt?"

    raw = pd.read_parquet(RAW)
    season = "2023-24"
    pid = feat.loc[feat.season == season, "player_id"].value_counts().index[0]
    got = (feat[(feat.season == season) & (feat.player_id == pid)]
           .sort_values("kickoff_time")["us_npxg_r5"])
    exp = (raw[(raw.season == season) & (raw.player_id == pid)]
           .sort_values("kickoff_time")["us_npxg"]
           .shift(1).rolling(5, min_periods=1).mean())
    assert np.allclose(got.fillna(-1).values, exp.fillna(-1).values)


@pytest.mark.skipif(not (FEATURES.exists() and FOTMOB.exists()),
                    reason="run `python -m data.fotmob` then rebuild the pipeline first")
def test_fotmob_features_are_rolled_not_raw(feat):
    """09-09's leakage requirement: FotMob's per-match defensive-action counts
    describe the MATCH THEY CAME FROM (a match outcome) -- they must reach the
    feature matrix only through the shift(1)-then-rolling path
    (config.FOTMOB_COLS registered in ROLL_STATS), never as bare pre-match
    context. Mirrors test_understat_features_are_rolled_not_raw's own
    recompute-and-compare template."""
    bare = [c for c in config.FOTMOB_COLS if c in feat.columns]
    assert not bare, f"raw fotmob columns leaked into the feature matrix: {bare}"

    rolled = [c for c in feat.columns
             if c.startswith("fm_") and c.split("_")[-1].startswith("r")]
    assert rolled, "no rolled fotmob feature columns found -- was the pipeline rebuilt?"

    raw = pd.read_parquet(RAW)
    season = "2023-24"
    pid = feat.loc[feat.season == season, "player_id"].value_counts().index[0]
    got = (feat[(feat.season == season) & (feat.player_id == pid)]
           .sort_values("kickoff_time")["fm_tackles_r5"])
    exp = (raw[(raw.season == season) & (raw.player_id == pid)]
           .sort_values("kickoff_time")["fm_tackles"]
           .shift(1).rolling(5, min_periods=1).mean())
    assert np.allclose(got.fillna(-1).values, exp.fillna(-1).values)


@needs_data
def test_availability_features_are_raw_context_not_rolled(feat):
    """Phase 10 plan 10-01's leakage requirement -- the opposite
    classification from test_understat_features_are_rolled_not_raw's: a
    point-in-time availability figure resolved as of the gameweek deadline
    (data/availability.py::resolve_as_of) is ALREADY leakage-safe on its own
    terms, so it must reach the feature matrix RAW, as pre-match context
    (config.AVAILABILITY_COLS registered in CONTEXT_COLS), never rolled --
    the regression gate against a future edit "helpfully" moving the family
    into ROLL_STATS."""
    assert "av_chance_pct" in feat.columns, \
        "av_chance_pct missing -- was the pipeline rebuilt after data.availability?"

    rolled = [c for c in feat.columns
             if c.startswith("av_") and any(
                 c.endswith(sfx) for sfx in ("_r3", "_r5", "_r10", "_rall"))]
    assert not rolled, f"availability columns must never be rolled: found {rolled}"


@needs_data
def test_ep_next_lag_gate_matches_independent_masked_shift(feat):
    """Quick task 260909-elx's decision-time leakage requirement: the
    previous-fixture (`ep_next_lag`) gate must equal an independently
    recomputed masked-then-shift(1) series of `xp_fpl` for a real player, and
    the same-fixture derived column (`xp_fpl_now`) must be absent unless its
    own flag is on -- mirrors test_understat_features_are_rolled_not_raw's
    own recompute-and-compare template."""
    from backtest.walk_forward import apply_experiment_feature_gating
    from models.train import load_features

    df = load_features()
    season = "2023-24"  # F3: intact coverage (only 1 of 38 gameweeks is an outage)
    pid = df.loc[df.season == season, "player_id"].value_counts().index[0]

    gated_lag = apply_experiment_feature_gating(df, {"ep_next_lag": True})
    assert "xp_fpl_now" not in gated_lag.columns, \
        "same-fixture column must not appear when only ep_next_lag is on"
    assert "xp_fpl_lag1" in gated_lag.columns

    got = (gated_lag[(gated_lag.season == season) & (gated_lag.player_id == pid)]
           .sort_values("kickoff_time")["xp_fpl_lag1"]
           .reset_index(drop=True))

    raw = pd.read_parquet(RAW, columns=["season", "player_id", "gw", "kickoff_time", "xp_fpl"])
    season_all = raw[raw.season == season]
    all_zero_gw = season_all.groupby("gw")["xp_fpl"].apply(lambda s: bool((s == 0.0).all()))
    outage_gws = set(all_zero_gw[all_zero_gw].index)

    raw_sub = (raw[(raw.season == season) & (raw.player_id == pid)]
              .sort_values("kickoff_time").reset_index(drop=True))
    masked = raw_sub["xp_fpl"].mask(raw_sub["gw"].isin(outage_gws))
    exp = masked.shift(1)

    assert np.allclose(got.fillna(-1).values, exp.fillna(-1).values)


@pytest.mark.skipif(not (TRANSFERMARKT.exists() and RAW.exists()),
                    reason="run `python -m data.transfermarkt --build` and the data pipeline first")
def test_transfermarkt_injury_dates_precede_kickoff():
    """The todo's own explicit leakage requirement
    (.planning/todos/pending/2026-09-10-transfermarkt-injury-history.md):
    "extend tests/test_leakage.py to assert injury-spell dates precede
    fixture kickoff". Run against the REAL committed spell table joined to
    the REAL player_gw.parquet -- never synthetic data. Every gameweek where
    `injury_status_as_of` reports an active spell must have that spell's
    contributing `from_date` strictly before BOTH `deadline_ts` (the bound
    the join itself uses) AND every kickoff in that gameweek
    (`kickoff_max` -- `gw_deadlines()`'s own docstring records the
    postponement caveat that makes this the harder bound, and the one the
    todo names)."""
    import data.transfermarkt as tm
    from data.availability import gw_deadlines

    spells = tm.load_transfermarkt()
    assert spells is not None and not spells.empty, \
        "committed spell table exists but failed to load or is empty"
    spells = spells.dropna(subset=["player_code", "from_date"]).copy()
    spells["player_code"] = spells["player_code"].astype("Int64")
    spells["from_date"] = pd.to_datetime(spells["from_date"], utc=True)
    spells["until_date"] = pd.to_datetime(spells["until_date"], utc=True)

    deadlines = gw_deadlines()
    raw = pd.read_parquet(RAW, columns=["season", "gw", "player_code", "kickoff_time"])
    raw = raw.dropna(subset=["kickoff_time"])
    kickoff_max = (raw.groupby(["season", "gw"], sort=False)["kickoff_time"].max()
                   .reset_index(name="kickoff_max"))

    covered_codes = set(spells["player_code"].unique())
    keyed = (raw[["season", "gw", "player_code"]].drop_duplicates())
    keyed = keyed[keyed["player_code"].astype("Int64").isin(covered_codes)]
    keyed = (keyed.merge(deadlines[["season", "gw", "deadline_ts"]],
                         on=["season", "gw"], how="inner")
             .merge(kickoff_max, on=["season", "gw"], how="inner"))
    assert not keyed.empty, "no player-gw rows overlap the committed spell table's players"

    checked = 0
    offenders = []
    for row in keyed.itertuples(index=False):
        deadline_ts = pd.Timestamp(row.deadline_ts)
        if deadline_ts.tzinfo is None:
            deadline_ts = deadline_ts.tz_localize("UTC")
        kickoff_ts = pd.Timestamp(row.kickoff_max)
        if kickoff_ts.tzinfo is None:
            kickoff_ts = kickoff_ts.tz_localize("UTC")

        sp = spells[spells["player_code"] == row.player_code]
        status = tm.injury_status_as_of(sp, row.player_code, deadline_ts)
        if not status["injured"]:
            continue
        checked += 1

        active = sp[(sp["from_date"] <= deadline_ts)
                    & (sp["until_date"].isna() | (sp["until_date"] >= deadline_ts))]
        worst_from = active["from_date"].max()
        if not (worst_from < deadline_ts):
            offenders.append((int(row.player_code), row.season, int(row.gw),
                              "deadline_ts", str(worst_from)))
        if not (worst_from < kickoff_ts):
            offenders.append((int(row.player_code), row.season, int(row.gw),
                              "kickoff_max", str(worst_from)))

    assert checked > 0, "no active-spell player-gws found -- cannot exercise the assertion"
    assert not offenders, f"spell from_date does not precede bound: {offenders[:10]}"


@needs_data
def test_sequence_features_no_future_gw_leakage():
    """D-21's named gate for models/bracket/sequence.py (Phase 10 plan
    10-11): for at least 200 real target fixtures spread across seasons,
    independently recompute the expected prior-fixture set directly from
    player_gw.parquet (never trusting the builder's own bookkeeping) and
    assert the sequence builder's timesteps match it exactly, and that every
    included kickoff_time is strictly less than the target's own. Mirrors
    test_minutes_r5_matches_independent_recompute's own recompute-and-compare
    template."""
    from models.bracket import sequence as seq_mod

    raw = pd.read_parquet(RAW)
    feat_df = pd.read_parquet(FEATURES)

    rng = np.random.RandomState(0)
    seasons = sorted(feat_df.season.unique())
    sample_seasons = list(rng.choice(seasons, min(4, len(seasons)), replace=False))

    checked = 0
    for season in sample_seasons:
        gws = sorted(feat_df.loc[feat_df.season == season, "gw"].unique())
        sample_gws = list(rng.choice(gws, min(6, len(gws)), replace=False))
        for gw in sample_gws:
            gw = int(gw)
            bundle = seq_mod.build_sequences(season, gw, raw=raw, feat=feat_df)
            targets = (feat_df[(feat_df.season == season) & (feat_df.gw == gw)]
                      .sort_values(["player_id", "kickoff_time"]).reset_index(drop=True))
            assert len(targets) == len(bundle.ids)
            seq_stats = seq_mod.SEQ_STATS

            for i, row in targets.iterrows():
                pid, kt = row.player_id, row.kickoff_time
                # Independent recompute -- a fresh expression against
                # player_gw.parquet, not a call into the builder's own code.
                hist = (raw[(raw.season == season) & (raw.player_id == pid)
                            & (raw.kickoff_time < kt)]
                        .sort_values("kickoff_time"))
                expected = hist.tail(seq_mod.SEQ_WINDOW)[seq_stats].to_numpy(dtype="float32")
                n_real = len(expected)

                got_mask = bundle.mask[i].numpy()
                n_got_real = int((~got_mask).sum())
                assert n_got_real == n_real, (season, gw, pid, n_got_real, n_real)
                if n_real:
                    got_seq = bundle.x_seq[i][~got_mask].numpy()
                    assert np.allclose(got_seq, expected, atol=1e-4, equal_nan=True), \
                        (season, gw, pid)
                    assert (hist.tail(n_real)["kickoff_time"] < kt).all()

                checked += 1
            if checked >= 200:
                break
        if checked >= 200:
            break

    assert checked >= 200, f"only checked {checked} fixtures, need >=200"


@needs_data
def test_transfermarkt_injury_features_are_raw_context_not_rolled(feat):
    """Task 3's second required regression, mirroring
    test_availability_features_are_raw_context_not_rolled's own template: the
    tm_ family (config.INJURY_COLS) is raw pre-match context
    (features/engineer.py's CONTEXT_COLS), never rolled -- a regression gate
    against a future edit "helpfully" moving the family into ROLL_STATS.
    Holds trivially before plan 10-08's build_table.py wiring lands (no tm_
    columns exist in features.parquet yet), and stays true afterward."""
    rolled = [c for c in feat.columns
             if c.startswith("tm_") and any(
                 c.endswith(sfx) for sfx in ("_r3", "_r5", "_r10", "_rall"))]
    assert not rolled, f"injury columns must never be rolled: found {rolled}"


def test_fixture_ctx_no_ts_columns():
    """Plan 09-05 D3: FIXTURE_CTX must carry no ts_* columns.

    The decision-time horizon graft re-derives team-strength ratings from the
    decision gameweek's own snapshot (ratings_as_of(g)), never from the future
    gameweek's own (leaky). Only the OPPONENT IDENTITY carries forward; the
    ratings themselves are re-derived. This guard prevents an accidental
    ts_*column from being frozen into a future row, which would leak future
    team-strength knowledge into a current-gameweek decision."""
    from backtest.walk_forward import FIXTURE_CTX

    ts_cols_found = [c for c in FIXTURE_CTX if c.startswith("ts_")]
    assert not ts_cols_found, (
        f"FIXTURE_CTX must not carry ts_* columns (leakage risk); found: {ts_cols_found}"
    )
