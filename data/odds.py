"""Bookmaker match odds from football-data.co.uk -> per-fixture implied probabilities.

Free historical CSVs (one per season). We de-overround the 1X2 and over/under 2.5
markets into probabilities and expand each match into two team-perspective rows so
it joins to player_gw on (season, date, team, was_home) — no opponent name needed.

Signal: opponent win prob ~ clean-sheet difficulty (defenders/GK); over-2.5 prob ~
attacking environment (attackers). Markets price these very well.

Run:
  python -m data.odds        # (re)build data/processed/odds.parquet
"""
from __future__ import annotations

import sys

import pandas as pd
import requests

import config

_OUT = config.PROCESSED_DIR / "odds.parquet"
_FD_URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"
FD_TO_FPL = {"Man United": "Man Utd", "Tottenham": "Spurs",
             "Sheffield United": "Sheffield Utd"}


def _season_code(season: str) -> str:
    a, b = season.split("-")            # "2022-23" -> "2223"
    return a[2:] + b


def _first_cols(df: pd.DataFrame, *options):
    for cols in options:
        if all(c in df.columns for c in cols):
            return cols
    return None


def _download(season: str, *, force: bool = False) -> pd.DataFrame | None:
    path = config.RAW_DIR / "odds" / f"{season}.csv"
    if not path.exists() or force:
        try:
            r = requests.get(_FD_URL.format(code=_season_code(season)), timeout=30)
            r.raise_for_status()
        except requests.RequestException as exc:
            print(f"  [miss] {season}: {exc}")
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")


def _season_odds(season: str, force: bool = False) -> pd.DataFrame | None:
    df = _download(season, force=force)
    if df is None:
        return None
    h, d, a = _first_cols(df, ["AvgH", "AvgD", "AvgA"], ["B365H", "B365D", "B365A"]) or (None,) * 3
    if h is None:
        print(f"  [skip] {season}: no 1X2 odds columns")
        return None
    ou = _first_cols(df, ["B365>2.5", "B365<2.5"], ["Avg>2.5", "Avg<2.5"])

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce").dt.date
    out["home"] = df["HomeTeam"].replace(FD_TO_FPL)
    out["away"] = df["AwayTeam"].replace(FD_TO_FPL)
    inv = 1 / df[[h, d, a]].astype(float)
    norm = inv.sum(axis=1)
    out["pH"], out["pD"], out["pA"] = (inv[h] / norm, inv[d] / norm, inv[a] / norm)
    if ou:
        io = 1 / df[ou[0]].astype(float)
        iu = 1 / df[ou[1]].astype(float)
        out["pover"] = io / (io + iu)
    else:
        out["pover"] = pd.NA
    out = out.dropna(subset=["date"])

    # Expand to team-perspective rows.
    home = out.rename(columns={"home": "team"}).assign(
        was_home=True, odds_pwin=out.pH, odds_pdraw=out.pD, odds_plose=out.pA,
        odds_pover25=out.pover)
    away = out.rename(columns={"away": "team"}).assign(
        was_home=False, odds_pwin=out.pA, odds_pdraw=out.pD, odds_plose=out.pH,
        odds_pover25=out.pover)
    keep = ["date", "team", "was_home"] + config.ODDS_COLS
    both = pd.concat([home[keep], away[keep]], ignore_index=True)
    both.insert(0, "season", season)
    return both


def load_odds(rebuild: bool = False) -> pd.DataFrame:
    if _OUT.exists() and not rebuild:
        return pd.read_parquet(_OUT)
    frames = [x for s in config.SEASONS if (x := _season_odds(s)) is not None]
    odds = pd.concat(frames, ignore_index=True)
    odds.to_parquet(_OUT, index=False)
    return odds


def main() -> int:
    odds = load_odds(rebuild=True)
    print(f"odds: {len(odds):,} team-fixtures over "
          f"{odds.season.nunique()} seasons; cols={config.ODDS_COLS}")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
