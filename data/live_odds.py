"""Live forward odds for UPCOMING fixtures (optional; needs an API key).

Backtests get odds from football-data.co.uk, but that only covers completed
matches — at live inference the ODDS_COLS (top-3 features for DEF) were NaN.
This seam fills them from the-odds-api.com when a key is available:

  export ODDS_API_KEY=...     # free tier: https://the-odds-api.com (~500 req/mo)
  python -m predict.live      # picks the odds up automatically

Without the key everything degrades gracefully to NaN (previous behaviour).
De-overrounding matches data/odds.py so live values share the training scale.
"""
from __future__ import annotations

import os

import pandas as pd
import requests

_URL = ("https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
        "?regions=eu&markets=h2h,totals&oddsFormat=decimal&apiKey={key}")

# the-odds-api team names -> FPL short names (extend as clubs change).
_NAME_MAP = {
    "Manchester City": "Man City", "Manchester United": "Man Utd",
    "Tottenham Hotspur": "Spurs", "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield Utd", "Wolverhampton Wanderers": "Wolves",
    "Brighton and Hove Albion": "Brighton", "West Ham United": "West Ham",
    "Newcastle United": "Newcastle", "Leeds United": "Leeds",
    "Leicester City": "Leicester", "Ipswich Town": "Ipswich",
    "Luton Town": "Luton", "West Bromwich Albion": "West Brom",
    "AFC Bournemouth": "Bournemouth",
}


def _implied(prices: list[float]) -> list[float]:
    inv = [1 / p for p in prices]
    s = sum(inv)
    return [x / s for x in inv]


def fetch_live_odds() -> pd.DataFrame | None:
    """Team-perspective implied probabilities for upcoming fixtures, or None."""
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        return None
    try:
        r = requests.get(_URL.format(key=key), timeout=20)
        r.raise_for_status()
        events = r.json()
    except requests.RequestException as exc:
        print(f"  [odds] live fetch failed ({exc}) — continuing without")
        return None

    rows = []
    for ev in events:
        home = _NAME_MAP.get(ev["home_team"], ev["home_team"])
        away = _NAME_MAP.get(ev["away_team"], ev["away_team"])
        h2h = tot = None
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                if mk["key"] == "h2h" and h2h is None and len(mk["outcomes"]) == 3:
                    prices = {o["name"]: o["price"] for o in mk["outcomes"]}
                    if ev["home_team"] in prices and ev["away_team"] in prices:
                        ph, pd_, pa = _implied([prices[ev["home_team"]],
                                                prices["Draw"],
                                                prices[ev["away_team"]]])
                        h2h = (ph, pd_, pa)
                if (mk["key"] == "totals" and tot is None
                        and any(o.get("point") == 2.5 for o in mk["outcomes"])):
                    over = next(o["price"] for o in mk["outcomes"]
                                if o["name"] == "Over" and o.get("point") == 2.5)
                    under = next(o["price"] for o in mk["outcomes"]
                                 if o["name"] == "Under" and o.get("point") == 2.5)
                    tot = _implied([over, under])[0]
        if h2h is None:
            continue
        ph, pd_, pa = h2h
        rows.append({"team": home, "was_home": True, "odds_pwin": ph,
                     "odds_pdraw": pd_, "odds_plose": pa, "odds_pover25": tot})
        rows.append({"team": away, "was_home": False, "odds_pwin": pa,
                     "odds_pdraw": pd_, "odds_plose": ph, "odds_pover25": tot})
    if not rows:
        return None
    # A team can appear in several upcoming fixtures; keep the earliest listed.
    return pd.DataFrame(rows).drop_duplicates(["team", "was_home"], keep="first")
