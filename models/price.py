"""Price-change predictor (Tier-2 engagement: the nightly watchlist).

FPL prices move on hidden transfer-momentum thresholds. The API serves only the
current moment, so training data is the daily snapshot archive (data/snapshot.py)
— consecutive-day pairs where day d's momentum features predict whether the price
moved by day d+1.

Until the archive is deep enough (MIN_DAYS) the watchlist falls back to the
community-standard heuristic — net event transfers scaled by ownership — and says
so in the JSON (`mode: "heuristic"`); the page must show that label. Once trained,
the model's hit-rate belongs on the scoreboard like everything else.

Run:
  python -m models.price --train        # train when >= MIN_DAYS of snapshots
  python -m models.price                # emit web/data/watchlist.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys

import joblib
import numpy as np
import pandas as pd

import config
from data.snapshot import load_snapshots
from ops.jsonio import write_json

ARTIFACT = config.ROOT / "models" / "artifacts" / "price_model.joblib"
WATCHLIST = config.ROOT / "web" / "data" / "watchlist.json"
MIN_DAYS = 14
FEATURES = ["net_per_owner", "net_transfers", "ownership", "price_m",
            "transfers_in_event", "transfers_out_event", "form",
            "cost_change_event", "cost_change_start", "net_momentum_3d",
            "is_flagged"]
CLASSES = {-1: "fall", 0: "hold", 1: "rise"}


def _featurize(snaps: pd.DataFrame) -> pd.DataFrame:
    """Per (player, day) features from the raw snapshot columns."""
    df = snaps.sort_values(["player_id", "date"]).copy()
    owners = (df.selected_by_percent / 100.0 * df.total_players).clip(lower=1.0)
    df["net_transfers"] = df.transfers_in_event - df.transfers_out_event
    # transfers_*_event are cumulative within a gameweek — the signal is the
    # DAILY delta. Day one of a window falls back to the cumulative figure.
    daily = df.groupby("player_id")["net_transfers"].diff()
    df["net_daily"] = daily.where(daily.notna() & (daily.abs() <= df.net_transfers.abs() * 2),
                                  df.net_transfers)
    df["net_per_owner"] = df.net_daily / owners
    df["ownership"] = df.selected_by_percent
    df["is_flagged"] = (df.status != "a").astype(int)
    df["net_momentum_3d"] = (df.groupby("player_id")["net_per_owner"]
                             .transform(lambda s: s.rolling(3, min_periods=1).mean()))
    return df


def build_dataset(snaps: pd.DataFrame) -> pd.DataFrame:
    """Consecutive-day pairs: features at day d, label = price move by day d+1."""
    df = _featurize(snaps)
    df["next_price"] = df.groupby("player_id")["price_m"].shift(-1)
    df["next_date"] = df.groupby("player_id")["date"].shift(-1)
    gap = (pd.to_datetime(df.next_date) - pd.to_datetime(df.date)).dt.days
    df = df[gap == 1].copy()                      # only true consecutive days
    df["label"] = np.sign(df.next_price - df.price_m).astype(int)
    return df


def train() -> dict | None:
    snaps = load_snapshots()
    n_days = snaps.date.nunique() if len(snaps) else 0
    if n_days < MIN_DAYS:
        print(f"[price] {n_days}/{MIN_DAYS} snapshot days collected — keep the "
              "daily cron running; training will unlock automatically.")
        return None
    import lightgbm as lgb
    ds = build_dataset(snaps)
    days = sorted(ds.date.unique())
    split = days[int(len(days) * 0.8)]
    tr, va = ds[ds.date < split], ds[ds.date >= split]
    clf = lgb.LGBMClassifier(objective="multiclass", num_class=3,
                             n_estimators=500, learning_rate=0.05,
                             num_leaves=31, verbose=-1)
    clf.fit(tr[FEATURES], tr.label + 1,
            eval_set=[(va[FEATURES], va.label + 1)],
            callbacks=[lgb.early_stopping(50, verbose=False)])
    acc = float((clf.predict(va[FEATURES]) == va.label + 1).mean())
    moved = va[va.label != 0]
    hit = (float((clf.predict(moved[FEATURES]) == moved.label + 1).mean())
           if len(moved) else float("nan"))
    art = {"clf": clf, "features": FEATURES,
           "trained_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "val_accuracy": acc, "val_moved_hit": hit, "n_days": n_days}
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(art, ARTIFACT)
    print(f"[price] trained on {n_days} days; val acc={acc:.3f}, "
          f"hit-rate on actual movers={hit:.3f}")
    return art


# Heuristic calibration: FPL's hidden thresholds scale with ownership, so net
# transfers PER OWNER is the comparable signal. ~3%/day of a player's owners as
# net flow is treated as "at the threshold" (progress 100%) until the trained
# model replaces this with real probabilities.
NPO_AT_THRESHOLD = 0.03


def _status(progress: float, prob: float | None) -> str:
    x = prob if prob is not None else min(abs(progress), 1.5) / 1.5
    if x >= 0.65:
        return "very likely"
    if x >= 0.35:
        return "likely"
    return "monitoring"


def _entry(r: pd.Series, prob: float | None) -> dict:
    progress = float(r.net_per_owner) / NPO_AT_THRESHOLD
    e = {"name": r["name"], "team": r.team, "position": r.position,
         "price_m": float(r.price_m), "ownership": float(r.ownership),
         "net_per_owner": round(float(r.net_per_owner), 4),
         "net_transfers": int(r.net_transfers),
         "progress": round(min(abs(progress), 1.5), 2),
         "status": _status(progress, prob)}
    if prob is not None:
        e["prob"] = round(float(prob), 3)
    return e


def _official_status(likelihood: float, percent: float) -> str:
    """FPL's -5..+5 likelihood bands -> label (±4/±5 is the site's 'very
    likely'; >100% progress means the threshold is already passed)."""
    a = abs(likelihood) if pd.notna(likelihood) else 0
    if abs(percent) >= 100 or a >= 4:
        return "very likely tonight"
    if a == 3:
        return "likely"
    return "monitoring"


def _emit_official(latest: pd.DataFrame, top: int) -> dict:
    """Watchlist straight from FPL's official predictor fields (2026/27+)."""
    live = latest[latest.price_change_percent.notna()].copy()
    locked = live.price_change_locked_until.notna() & \
        (live.price_change_locked_until != "")
    live = live[~locked]
    def rows(frame):
        return [{
            "name": r["name"], "team": r.team, "position": r.position,
            "price_m": float(r.price_m), "ownership": float(r.ownership),
            "net_transfers": int(r.net_transfers),
            "progress": round(float(r.price_change_percent) / 100, 2),
            "proj_tonight": (round(float(r.proj0_percent) / 100, 2)
                             if pd.notna(r.proj0_percent) else None),
            "status": _official_status(r.proj0_likelihood,
                                       r.price_change_percent),
        } for _, r in frame.iterrows()]
    risers = live[live.price_change_percent > 0] \
        .nlargest(top, "price_change_percent")
    fallers = live[live.price_change_percent < 0] \
        .nsmallest(top, "price_change_percent")
    return {"mode": "official", "locked_players": int(locked.sum()),
            "risers": rows(risers), "fallers": rows(fallers)}


def emit_watchlist(top: int = 15) -> dict:
    """web/data/watchlist.json from the latest snapshot.

    Source priority: FPL's official predictor fields (present since 2026/27)
    -> our trained model -> the net-transfers heuristic.
    """
    snaps = load_snapshots()
    if not len(snaps):
        raise SystemExit("[price] no snapshots yet — run python -m data.snapshot")
    latest = _featurize(snaps[snaps.date == snaps.date.max()].copy())
    if ("price_change_percent" in latest.columns
            and latest.price_change_percent.notna().any()):
        out = _emit_official(latest, top)
        out["date"] = str(snaps.date.max())
        WATCHLIST.parent.mkdir(parents=True, exist_ok=True)
        write_json(out, WATCHLIST)
        print(f"[price] watchlist (official predictor) -> {WATCHLIST}")
        return out
    art = joblib.load(ARTIFACT) if ARTIFACT.exists() else None
    if art is not None:
        proba = art["clf"].predict_proba(latest[art["features"]])
        latest["p_rise"], latest["p_fall"] = proba[:, 2], proba[:, 0]
        risers = latest.sort_values("p_rise", ascending=False).head(top)
        fallers = latest.sort_values("p_fall", ascending=False).head(top)
        out = {"mode": "model", "trained_utc": art["trained_utc"],
               "val_moved_hit": art["val_moved_hit"],
               "risers": [_entry(r, r.p_rise) for _, r in risers.iterrows()],
               "fallers": [_entry(r, r.p_fall) for _, r in fallers.iterrows()]}
    else:
        # Per-owner ratios explode at near-zero ownership; the heuristic list is
        # only meaningful for players enough people actually hold.
        ranked = latest[latest.ownership >= 0.5].sort_values("net_per_owner")
        out = {"mode": "heuristic",
               "note": "net event transfers per owner — model trains itself once "
                       f"{MIN_DAYS} days of snapshots exist",
               "risers": [_entry(r, None) for _, r in ranked.tail(top).iloc[::-1].iterrows()],
               "fallers": [_entry(r, None) for _, r in ranked.head(top).iterrows()]}
    out["date"] = str(snaps.date.max())
    WATCHLIST.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, WATCHLIST)
    print(f"[price] watchlist ({out['mode']}) -> {WATCHLIST}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", action="store_true")
    args = ap.parse_args(argv)
    if args.train:
        train()
    else:
        emit_watchlist()
    return 0


if __name__ == "__main__":
    sys.exit(main())
