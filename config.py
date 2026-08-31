"""Project constants and paths (Phase 0)."""
from __future__ import annotations

from pathlib import Path

# --- Paths ------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"          # cached downloads (vaastav CSVs, FPL API JSON)
PROCESSED_DIR = DATA_DIR / "processed"  # canonical parquet tables

for _d in (RAW_DIR, PROCESSED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Data sources -----------------------------------------------------------
VAASTAV_RAW = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
FPL_API = "https://fantasy.premierleague.com/api"

# Seasons to ingest for training. Recent seasons carry the expected_* (xG/xA)
# columns; extend backwards if you want more history (features will be NaN where
# a column did not exist that season).
SEASONS = ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22",
           "2022-23", "2023-24", "2024-25", "2025-26", "2026-27"]
CURRENT_SEASON = "2026-27"
# Note: seasons before 2022-23 lack native xG/xA columns (NaN); LightGBM handles it.

# --- FPL rules (2026/27) ----------------------------------------------------
BUDGET = 100.0                 # £m initial squad budget
SQUAD_SIZE = 15
POSITION_QUOTA = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}   # full 15-man squad
FORMATION_MIN = {"GK": 1, "DEF": 3, "MID": 2, "FWD": 1}     # min in starting XI
MAX_PER_CLUB = 3
MAX_FREE_TRANSFERS = 5
TRANSFER_HIT = 4               # points lost per extra transfer
SELL_ON_FEE = 0.5             # 50% of profit on price rises

# --- Feature engineering (Phase 2) -----------------------------------------
# Rolling windows in games; "all" = season-to-date. Multiple horizons let the
# model choose which matters (covers the 3 / 10 / all-previous-games request).
WINDOWS = [3, 5, 10, "all"]

POSITIONS = ["GK", "DEF", "MID", "FWD"]

# Set-piece / penalty taker order (1 = first-choice taker; NaN = not a taker).
# From players_raw snapshots (2022-23+) and the live bootstrap. Strong point-ceiling
# signal, especially penalties. Season-level static per player.
SET_PIECE_COLS = ["penalties_order", "direct_freekicks_order",
                  "corners_and_indirect_freekicks_order"]

# Bookmaker-implied probabilities (de-overrounded) from football-data.co.uk, per
# fixture, team perspective. Strong clean-sheet / goals priors, esp. for defenders.
ODDS_COLS = ["odds_pwin", "odds_pdraw", "odds_plose", "odds_pover25"]

# FBref (StatsBomb) per-90 advanced stats — OPTIONAL enrichment (see data/fbref.py).
# Only present if you run the offline scrape on a browser machine; the pipeline
# no-ops without it. Defensive actions feed FPL's defensive-contribution points.
FBREF_COLS = ["fb_tkl_int_90", "fb_blocks_90", "fb_clr_90",
              "fb_sca_90", "fb_gca_90", "fb_prog_90"]

# --- Modelling (Phase 3): strict time-based split, never random ------------
# Train on earlier seasons, hold out the most recent complete season as test.
TRAIN_SEASONS = ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
                 "2021-22", "2022-23", "2023-24"]
VAL_SEASON = "2024-25"     # chronological validation (early stopping)
TEST_SEASONS = ["2025-26"]  # untouched during training

# --- Canonical player_gw schema --------------------------------------------
# Columns pulled from vaastav merged_gw.csv (renamed on the right where useful).
# Kept deliberately explicit so schema drift across seasons is visible.
MERGED_GW_COLUMNS = {
    "GW": "gw",
    "element": "player_id",
    "name": "name",
    "position": "position",
    "team": "team",
    "opponent_team": "opponent_team_id",
    "was_home": "was_home",
    "kickoff_time": "kickoff_time",
    "fixture": "fixture_id",
    "minutes": "minutes",
    "starts": "starts",
    "total_points": "total_points",
    "xP": "xp_fpl",                 # FPL's own expected points (baseline to beat)
    "goals_scored": "goals_scored",
    "assists": "assists",
    "clean_sheets": "clean_sheets",
    "goals_conceded": "goals_conceded",
    "own_goals": "own_goals",
    "penalties_missed": "penalties_missed",
    "penalties_saved": "penalties_saved",
    "saves": "saves",
    "yellow_cards": "yellow_cards",
    "red_cards": "red_cards",
    "bonus": "bonus",
    "bps": "bps",
    "expected_goals": "xg",
    "expected_assists": "xa",
    "expected_goal_involvements": "xgi",
    "expected_goals_conceded": "xgc",
    "influence": "influence",
    "creativity": "creativity",
    "threat": "threat",
    "ict_index": "ict_index",
    "value": "value",               # price * 10 (e.g. 55 == £5.5m)
    "selected": "selected",
    "transfers_in": "transfers_in",
    "transfers_out": "transfers_out",
    "transfers_balance": "transfers_balance",
    "team_h_score": "team_h_score",
    "team_a_score": "team_a_score",
}
