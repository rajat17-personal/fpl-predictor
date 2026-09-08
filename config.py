"""Project constants and paths (Phase 0)."""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

# --- Paths ------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"          # cached downloads (vaastav CSVs, FPL API JSON)
PROCESSED_DIR = DATA_DIR / "processed"  # canonical parquet tables
EXPERIMENTS_DIR = PROCESSED_DIR / "experiments"  # Phase 9 tagged walk-forward run artifacts

for _d in (RAW_DIR, PROCESSED_DIR, EXPERIMENTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def load_dotenv(path: Path | None = None) -> int:
    """Populate `os.environ` from a `KEY=VALUE` `.env` file (SEC-03).

    Reads `path` (default `ROOT / ".env"`) if it exists; blank lines and
    lines whose first non-space character is `#` are skipped. A value may be
    wrapped in one layer of matching single or double quotes, which is
    stripped. A key already present in `os.environ` is never overwritten —
    an exported shell variable, a container, or a CI runner always wins over
    the file, so a deployment can override without editing anything.

    Never raises: a malformed line is skipped with a one-line stderr warning
    naming the line number; an unreadable file is a warning, not a failure —
    the process must still start. When the file exists with permission bits
    other than 0o600, prints an unmissable (but non-blocking) stderr warning.

    Returns the number of keys this call actually set.
    """
    target = Path(path) if path is not None else (ROOT / ".env")
    if not target.exists():
        return 0

    try:
        mode = stat.S_IMODE(target.stat().st_mode)
        if mode != 0o600:
            print(
                f"[config] {target} has mode {oct(mode)}, expected 0o600 "
                f"(secrets are readable by more than the owner) -- run `chmod 600 .env`",
                file=sys.stderr,
            )
    except OSError as exc:
        print(f"[config] could not stat {target}: {exc}", file=sys.stderr)

    try:
        with open(target, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as exc:
        print(f"[config] could not read {target}: {exc}", file=sys.stderr)
        return 0

    count = 0
    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key:
            print(f"[config] {target}:{lineno}: malformed line, skipping", file=sys.stderr)
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key in os.environ:
            continue
        os.environ[key] = value
        count += 1
    return count


load_dotenv()

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

# Team attack/defence strength ratings from an expanding pre-gameweek
# Dixon-Coles fit (data/team_strength.py) — OPTIONAL enrichment, computed
# UNCONDITIONALLY (independent of EXPERIMENTS["team_strength"] below): the
# pipeline no-ops without data/processed/team_strength.parquet, matching every
# other optional source here, but once it exists the join always runs so
# player_gw.parquet/features.parquet stay stable across an A/B run — the
# feature-selection gate lives in backtest/walk_forward.py instead, so
# flipping the experiment flag is never a pipeline rebuild. Fills the two
# verified odds holes: ODDS_COLS is null for the whole 2016-19 training
# window (bookmaker CSVs join on the `team` name column, which is 0%
# populated those seasons), and a multi-gameweek horizon has no posted odds
# for future fixtures either — ratings computed from results-to-date cover
# both.
TEAM_STRENGTH_COLS = ["ts_attack_self", "ts_defence_self", "ts_attack_opp",
                      "ts_defence_opp", "ts_xg_for", "ts_xg_against",
                      "ts_pwin", "ts_pcs"]

# --- Modelling (Phase 3): strict time-based split, never random ------------
# Train on earlier seasons, hold out the most recent complete season as test.
TRAIN_SEASONS = ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
                 "2021-22", "2022-23", "2023-24"]
VAL_SEASON = "2024-25"     # chronological validation (early stopping)
TEST_SEASONS = ["2025-26"]  # untouched during training

# --- Phase 9: xP model & optimizer improvement experiments ------------------
# Every experiment lands opt-in behind a flag, defaulted off (D-07/D-08): an
# unflagged `backtest/walk_forward.py` run reproduces the pre-phase-9 baseline
# exactly. A later plan adds an experiment by adding one key here and one
# branch in `backtest/walk_forward.py::main` -- never a bespoke ad-hoc switch.
EXPERIMENTS: dict[str, bool] = {
    "capt_ceiling": False,
    "capt_mc": False,
    "chips_v2": False,
    "team_strength": False,
    "rl_strategy": False,
    "understat": False,
    "fotmob": False,
    "fbref_v2": False,
}

CAPT_CEILING_LAMBDA = 0.5       # captaincy ceiling-EV upside weight (models/captaincy.py);
# swept over {0.0, 0.25, 0.5, 0.75, 1.0} in tags capt_lam_0.0..1.0 (2026-09-08,
# 6 seasons/1 replica); 0.5 measured the highest 6-season-mean capt_capture
# (0.578, vs 0.576/0.25, 0.572/0.75, 0.547/1.0, 0.563/0.0 control)
CHIPS_V2_HYSTERESIS = 0.0       # chip scheduler v2 fire-now-vs-wait margin (optimize/chips.py);
# swept over {0, 1, 2, 3} in tags chips_hys_0..3 (2026-09-08, 6 seasons/1 replica);
# 0 measured the highest 6-season-mean model+chips (2214, vs 2205/1, 2198/2, 2169/3)


def resolve_experiments(spec: str | None = None) -> dict[str, bool]:
    """Resolve a flag spec into a fresh copy of `EXPERIMENTS` with named flags forced on.

    `spec` is a comma-separated list of flag names (whitespace around commas is
    tolerated). `None` falls back to the `FPL_EXPERIMENTS` environment variable
    (also unset -> every flag stays at its `EXPERIMENTS` default, i.e. off). The
    token "none" forces every flag off; the token "all" forces every flag on.
    Any other unrecognised token raises `ValueError` naming the bad token and
    listing the valid keys. The module-level `EXPERIMENTS` dict is never mutated
    -- callers always get back a fresh copy.
    """
    if spec is None:
        spec = os.environ.get("FPL_EXPERIMENTS")
    result = dict(EXPERIMENTS)
    tokens = [t.strip() for t in spec.split(",")] if spec else []
    tokens = [t for t in tokens if t]
    if not tokens:
        return result
    if "none" in tokens:
        return {k: False for k in result}
    if "all" in tokens:
        return {k: True for k in result}
    for t in tokens:
        if t not in result:
            raise ValueError(f"unknown experiment flag '{t}' -- valid keys: {sorted(result)}")
        result[t] = True
    return result


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
