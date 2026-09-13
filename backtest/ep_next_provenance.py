"""Quick task 260909-elx Task 1: provenance verdict for FPL's own ep_this/
ep_next figure (`xp_fpl` here -- config.py maps vaastav's `xP` column onto
it, per-gameweek, not a season constant, per planning-time fact F2).

The todo's proposal to feed `xp_fpl` into the model as a SAME-FIXTURE
feature is only safe if that value is genuinely decision-time-known (the FPL
API's live `ep_this`/`ep_next` figure as it stood before the deadline), not
a value that carries hindsight about who actually played. This module
answers that question with a measurement, not an assertion:

  1. Coverage census (F3) -- per season, from `player_gw.parquet`: the null
     share, the list of gameweeks where `xp_fpl` is 0.0 for EVERY row (an
     outage written as a zero, not a null), and the zero-share over the
     remaining ("non-outage") gameweeks.
  2. Historical conditional stats (F4) on non-outage gameweeks only, per
     season and pooled: P(played | xp_fpl==0), P(xp_fpl==0 | did not play),
     P(xp_fpl==0 | played). Read alone, a very low P(played | xp_fpl==0)
     looks like hindsight (a model that "knows" a zero-ep player really
     won't play) -- but genuine pre-deadline zeros also cluster around
     truly-unlikely-to-play players, so this number alone does not settle
     it.
  3. THE CONTROL (F5) -- the decisive test. `data/snapshots/*.parquet` is
     this repo's own daily cron capture of the live FPL API, taken at a KNOWN
     `ts_utc` strictly between gameweeks. Joining each snapshot's zero-`ep_this`
     rows (keyed by its own `next_gw`) to that gameweek's REALISED minutes
     (`data/raw/live/element_history.parquet`) gives a
     known-pre-deadline P(played | ep_this==0), with a Wilson-score 95%
     interval. If the historical column's estimate is materially LOWER than
     this control (i.e. the historical column is "too confident" a zero-ep
     player really won't play, more confident than a genuine pre-deadline
     snapshot could honestly be), the historical column behaves as if it
     knows the outcome -- consistent with hindsight.
  4. A verdict block stating whether the control's 95% interval overlaps the
     historical pooled estimate, honest about its own statistical power (a
     small control is reported as a small control, not implied to be more).

This module is measurement-only: it never trains, never writes into
models/artifacts/, and never mutates any committed data or pipeline
artifact. Output goes to stdout and
`config.EXPERIMENTS_DIR / "ep_next_provenance.json"` (gitignored).

Run:
  python -m backtest.ep_next_provenance
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import config
from ops.jsonio import write_json

# F3's outage-gameweek counts, verified at planning time by reading the
# on-disk data -- a disagreement here means the underlying data moved since
# the plan was written, and it must be RECORDED in the output, never
# silently overridden.
_EXPECTED_OUTAGE_COUNTS = {
    "2020-21": 1, "2021-22": 0, "2022-23": 2,
    "2023-24": 1, "2024-25": 3, "2025-26": 27,
}
_NULL_SEASONS = ["2016-17", "2017-18", "2018-19", "2019-20"]
_COVERAGE_SEASONS = ["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
_Z = 1.96  # 95% two-sided normal/Wilson


def wilson_interval(x: int, n: int, z: float = _Z) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion x/n. `n == 0` returns
    (0.0, 0.0) -- no data, not a claim of certainty."""
    if n == 0:
        return 0.0, 0.0
    phat = x / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = z * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return float(center - half), float(center + half)


def coverage_census() -> tuple[dict, pd.DataFrame]:
    """Per-season null share, outage gameweeks (`xp_fpl` == 0.0 for every
    row), and the zero-share over surviving (non-outage) gameweeks. Returns
    `(coverage_dict, non_outage_frame)` -- the frame feeds `historical_stats`.
    """
    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                          columns=["season", "player_id", "fixture_id", "gw",
                                   "xp_fpl", "minutes"])
    coverage: dict = {}
    non_outage_frames = []
    for season in _NULL_SEASONS + _COVERAGE_SEASONS:
        sub = raw[raw.season == season]
        null_share = float(sub["xp_fpl"].isna().mean()) if len(sub) else None
        if season in _NULL_SEASONS:
            coverage[season] = {
                "null_share": round(null_share, 4) if null_share is not None else None,
                "outage_gws": [], "zero_share_non_outage": None, "n_non_outage_rows": 0,
            }
            continue

        per_gw_all_zero = sub.groupby("gw")["xp_fpl"].apply(lambda s: bool((s == 0.0).all()))
        outage_gws = sorted(int(g) for g in per_gw_all_zero[per_gw_all_zero].index)
        non_outage = sub[~sub["gw"].isin(outage_gws)]
        zero_share = float((non_outage["xp_fpl"] == 0.0).mean()) if len(non_outage) else None
        coverage[season] = {
            "null_share": round(null_share, 4) if null_share is not None else None,
            "outage_gws": outage_gws,
            "zero_share_non_outage": round(zero_share, 4) if zero_share is not None else None,
            "n_non_outage_rows": int(len(non_outage)),
        }
        non_outage_frames.append(non_outage)

    disagreements = []
    for season, expected in _EXPECTED_OUTAGE_COUNTS.items():
        actual = len(coverage[season]["outage_gws"])
        if actual != expected:
            disagreements.append({"season": season, "expected": expected, "actual": actual})
    coverage["_verification"] = {
        "matches_planning_time_facts": not disagreements,
        "disagreements": disagreements,
    }

    pooled_non_outage = (pd.concat(non_outage_frames, ignore_index=True)
                         if non_outage_frames else pd.DataFrame(columns=raw.columns))
    return coverage, pooled_non_outage


def _cell_stats(df: pd.DataFrame) -> dict:
    n = len(df)
    if n == 0:
        return {"n": 0, "n_zero": 0, "p_played_given_zero": None,
                "p_played_given_zero_ci95": [None, None],
                "p_zero_given_played": None, "p_zero_given_notplayed": None}
    zero = df[df["xp_fpl"] == 0.0]
    played = df[df["minutes"] > 0]
    not_played = df[df["minutes"] == 0]
    x_played_given_zero = int((zero["minutes"] > 0).sum())
    n_zero = len(zero)
    p_played_given_zero = x_played_given_zero / n_zero if n_zero else None
    lo, hi = wilson_interval(x_played_given_zero, n_zero)
    p_zero_given_played = float((played["xp_fpl"] == 0.0).mean()) if len(played) else None
    p_zero_given_notplayed = (float((not_played["xp_fpl"] == 0.0).mean())
                              if len(not_played) else None)
    return {
        "n": n, "n_zero": n_zero,
        "p_played_given_zero": round(p_played_given_zero, 4) if p_played_given_zero is not None else None,
        "p_played_given_zero_ci95": [round(lo, 4), round(hi, 4)] if n_zero else [None, None],
        "p_zero_given_played": round(p_zero_given_played, 4) if p_zero_given_played is not None else None,
        "p_zero_given_notplayed": (round(p_zero_given_notplayed, 4)
                                   if p_zero_given_notplayed is not None else None),
    }


def historical_stats(non_outage: pd.DataFrame) -> dict:
    """P(played | xp_fpl==0), P(xp_fpl==0 | did not play), P(xp_fpl==0 |
    played) per season and pooled, on non-outage gameweeks only (F4)."""
    out = {"pooled": _cell_stats(non_outage)}
    for season in _COVERAGE_SEASONS:
        out[season] = _cell_stats(non_outage[non_outage["season"] == season])
    return out


def control_stats() -> dict:
    """P(played | ep_this==0) on each `data/snapshots/*.parquet` capture,
    joined to that gameweek's realised minutes from
    `data/raw/live/element_history.parquet` (F5). A snapshot whose gameweek
    has no realised minutes yet is reported `covered: False` and excluded
    from the pooled estimate."""
    snap_dir = config.DATA_DIR / "snapshots"
    eh_path = config.RAW_DIR / "live" / "element_history.parquet"
    if not eh_path.exists() or not snap_dir.exists():
        return {"snapshots": [], "pooled": {"n": 0, "note": "no snapshots or no "
                                            "element_history.parquet on disk"}}
    eh = pd.read_parquet(eh_path, columns=["player_id", "gw", "minutes"])

    per_snapshot = []
    pooled_zero_frames = []
    for path in sorted(snap_dir.glob("*.parquet")):
        snap = pd.read_parquet(path, columns=["player_id", "ep_this", "ep_next",
                                              "next_gw", "ts_utc"])
        next_gw = int(snap["next_gw"].iloc[0])
        ts_utc = str(snap["ts_utc"].iloc[0])
        realized = eh[eh["gw"] == next_gw]
        if realized.empty:
            per_snapshot.append({
                "file": path.name, "next_gw": next_gw, "ts_utc": ts_utc,
                "covered": False,
                "reason": f"no realised minutes yet for gw{next_gw}",
            })
            continue

        merged = snap.merge(realized, on="player_id", how="inner")
        zero = merged[merged["ep_this"] == 0.0]
        x = int((zero["minutes"] > 0).sum())
        n = len(zero)
        lo, hi = wilson_interval(x, n)
        per_snapshot.append({
            "file": path.name, "next_gw": next_gw, "ts_utc": ts_utc, "covered": True,
            "n_joined": len(merged), "n_zero_ep_this": n, "x_played_given_zero": x,
            "p_played_given_zero": round(x / n, 4) if n else None,
            "p_played_given_zero_ci95": [round(lo, 4), round(hi, 4)] if n else [None, None],
        })
        pooled_zero_frames.append(zero)

    if pooled_zero_frames:
        pooled_zero = pd.concat(pooled_zero_frames, ignore_index=True)
        x_pooled = int((pooled_zero["minutes"] > 0).sum())
        n_pooled = len(pooled_zero)
        lo, hi = wilson_interval(x_pooled, n_pooled)
        pooled = {
            "n": n_pooled, "x_played": x_pooled,
            "p_played_given_zero": round(x_pooled / n_pooled, 4) if n_pooled else None,
            "p_played_given_zero_ci95": [round(lo, 4), round(hi, 4)] if n_pooled else [None, None],
            "n_snapshots_covered": len(pooled_zero_frames),
        }
    else:
        pooled = {"n": 0, "note": "no covered snapshot has realised minutes yet"}

    return {"snapshots": per_snapshot, "pooled": pooled}


def compute_verdict(historical: dict, control: dict) -> dict:
    """Whether the control's 95% interval overlaps the historical pooled
    estimate. Honest about its own power -- states n rather than implying
    more (F5's explicit requirement)."""
    h = historical["pooled"]
    c = control["pooled"]
    if c.get("n", 0) == 0 or h.get("n_zero", 0) == 0:
        return {
            "exonerated": None,
            "historical_pooled_p": h.get("p_played_given_zero"),
            "control_pooled_p": c.get("p_played_given_zero"),
            "reason": "insufficient data on one or both sides for a control comparison",
        }
    h_lo, h_hi = h["p_played_given_zero_ci95"]
    c_lo, c_hi = c["p_played_given_zero_ci95"]
    overlap = not (c_lo > h_hi or c_hi < h_lo)
    return {
        "exonerated": bool(overlap),
        "historical_pooled_p": h["p_played_given_zero"],
        "historical_pooled_ci95": h["p_played_given_zero_ci95"],
        "historical_pooled_n_zero": h["n_zero"],
        "control_pooled_p": c["p_played_given_zero"],
        "control_pooled_ci95": c["p_played_given_zero_ci95"],
        "control_pooled_n_zero": c["n"],
        "control_n_snapshots_covered": c.get("n_snapshots_covered", 0),
        "reason": (
            "control's 95% interval overlaps the historical pooled estimate -- "
            "consistent with a genuine pre-deadline capture; the same-fixture "
            "arm is not disqualified by this test"
            if overlap else
            "control's P(played | ep==0) is materially HIGHER than the "
            "historical pooled estimate, with non-overlapping 95% intervals -- "
            "the historical column is more confident a zero-ep player truly "
            "will not play than a genuine pre-deadline snapshot could honestly "
            "be, consistent with hindsight contamination. The same-fixture "
            "arm (ep_next_now) is a diagnostic upper bound only and must not "
            "be adopted whatever it scores."
        ),
        "power_caveat": (
            f"control is n={c.get('n', 0)} zero-ep rows from "
            f"{c.get('n_snapshots_covered', 0)} covered snapshot(s) -- a small "
            f"control; stated as such, not implied to be more."
        ),
    }


def main() -> int:
    coverage, non_outage = coverage_census()
    historical = historical_stats(non_outage)
    control = control_stats()
    verdict = compute_verdict(historical, control)

    out = {"coverage": coverage, "historical": historical, "control": control,
           "verdict": verdict}
    config.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.EXPERIMENTS_DIR / "ep_next_provenance.json"
    write_json(out, dest, indent=1)

    print("=== ep_next provenance (quick 260909-elx) ===")
    for season in _NULL_SEASONS:
        print(f"  {season}: null_share={coverage[season]['null_share']} (fully null)")
    for season in _COVERAGE_SEASONS:
        c = coverage[season]
        print(f"  {season}: null_share={c['null_share']} outage_gws={c['outage_gws']} "
              f"zero_share_non_outage={c['zero_share_non_outage']}")
    v = coverage["_verification"]
    print(f"  verification vs planning-time facts: matches={v['matches_planning_time_facts']} "
          f"disagreements={v['disagreements']}")

    hp = historical["pooled"]
    print(f"\nhistorical pooled (non-outage gws): P(played|xp_fpl==0)="
          f"{hp['p_played_given_zero']} CI95={hp['p_played_given_zero_ci95']} n_zero={hp['n_zero']}")

    for s in control["snapshots"]:
        if s["covered"]:
            print(f"  control {s['file']} (next_gw={s['next_gw']}, ts_utc={s['ts_utc']}): "
                  f"P(played|ep_this==0)={s['p_played_given_zero']} "
                  f"CI95={s['p_played_given_zero_ci95']} n={s['n_zero_ep_this']}")
        else:
            print(f"  control {s['file']}: UNCOVERED ({s['reason']})")
    cp = control["pooled"]
    print(f"  control pooled: n={cp.get('n')} P(played|ep_this==0)={cp.get('p_played_given_zero')} "
          f"CI95={cp.get('p_played_given_zero_ci95')} "
          f"(from {cp.get('n_snapshots_covered', 0)} covered snapshot(s))")

    print(f"\nverdict: exonerated={verdict['exonerated']}")
    print(f"  {verdict['reason']}")
    if "power_caveat" in verdict:
        print(f"  {verdict['power_caveat']}")
    print(f"\nsaved {dest.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
