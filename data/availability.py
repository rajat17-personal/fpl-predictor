"""Point-in-time player availability -- a THIRD leakage-safe feature family.

Neither `ROLL_STATS`'s shift-then-roll (a MATCH OUTCOME, rolled) nor
`CONTEXT_COLS`'s static-per-fixture join (known at fixture-build time, no
"as of when" question) fits an injury/status signal: "will this player play?"
changes hour to hour, and the only honest value to feed a gameweek g's
decision is whatever was KNOWN as of g's deadline -- never a later value, and
never one derived by walking backward from an outcome. This module is that
third family: a provider registry of long (player_code, snapshot_ts, ...)
frames, an as-of-deadline resolver applied UNIFORMLY across every provider,
and a single derived column, `av_chance_pct`.

Two source providers, matching data/fotmob.py's five-function optional-
enrichment shape:

  - "daily_snapshot" -- data.snapshot.load_snapshots(), our own daily FPL
    bootstrap capture (data/snapshots/*.parquet). Tagged with
    `season = config.CURRENT_SEASON` -- a snapshot only ever describes the
    live season at capture time.
  - "fpl_core_insights" -- per-gameweek `playerstats.csv` CSVs (columns
    verified live 2026-09-10 against
    https://api.github.com/repos/olbauday/FPL-Core-Insights, GW1-3 of
    2025-2026: `id, status, chance_of_playing_next_round,
    chance_of_playing_this_round, ..., news, news_added, gw, ...` -- `id` is
    the FPL element id for that season, cross-checked against
    data/processed/id_map.parquet (id=1 == Raya, season 2025-26)). Per D-05
    these folders freeze at gameweek END: a folder covering gameweek N is
    stamped `snapshot_ts = max(kickoff_time over (season, N))` -- the moment
    it froze -- so `resolve_as_of` naturally offers gameweek N's frozen file
    only to gameweek N+1 onward (the N-1 offset D-05 describes, with no
    special-cased arithmetic anywhere in this module). Looked for under
    `config.DATA_DIR / "external" / "fpl_core_insights"` (10-06's committed,
    license-gated, all-38-gameweek vendoring), falling back to
    `config.RAW_DIR / "fpl_core_insights"` (this plan's uncommitted,
    gitignored probe of GW1-3 only) when the committed directory is absent.
    Directory layout (this module's own choice, since 10-06 has not run yet):
    `<base>/<season-as-in-source-repo>/GW<n>_playerstats.csv`, flat -- no
    need to mirror the source repo's full "By Gameweek/GW<n>/" tree since
    only `playerstats.csv` is used.

Leakage rule (`resolve_as_of`): a source row is eligible for gameweek g only
if `snapshot_ts` is STRICTLY BEFORE both `deadline_ts` (derived,
`min(kickoff_time) - 90min`) AND every kickoff in g (`kickoff_max`). The
second condition exists because a postponed first fixture pushes
`min(kickoff_time)` -- and therefore `deadline_ts` -- later, making the
derived deadline permissive; requiring predates-every-kickoff-too closes that
hole regardless of `deadline_ts`'s own accuracy. Never falls forward to a
later snapshot: a (season, gw, player_code) with no qualifying row is simply
absent from the resolved output (D-10) -- `attach`'s left merge turns that
absence into NaN, never a raise, never a stale carry-forward.

Run:
  python -m data.availability            # (re)build data/processed/availability.parquet
  python -m data.availability --force    # ignore the cache, rebuild
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

import pandas as pd

import config
from data import id_map

# Module-level kill switch (09-PATTERNS.md convention, matching
# data/fotmob.py::FOTMOB_ENABLED): flipping this to False makes every public
# entry point below a no-op without touching a call site.
AVAILABILITY_ENABLED = True

_OUT = config.PROCESSED_DIR / "availability.parquet"
_DEADLINE_LEAD = pd.Timedelta(minutes=90)   # FPL deadlines are exactly 90 min
                                            # before a gameweek's first fixture

# Every provider in SOURCES must return at least these columns (V5 / T-10-01-01):
# an upstream schema change must fail loudly (_require_columns), never
# silently produce an all-NaN feature the model trusts unquestioned.
_REQUIRED_SOURCE_COLS = ["season", "player_code", "snapshot_ts", "status",
                         "chance_of_playing_next_round", "source"]

_RESOLVED_COLS = ["season", "gw", "player_code", "status",
                  "chance_of_playing_next_round", "source", "snapshot_ts"]


def _require_columns(df: pd.DataFrame, cols: list[str], what: str) -> None:
    """Raise `ValueError` naming the first missing column(s) rather than
    letting an upstream schema change propagate as a silent all-NaN feature
    (the data/fotmob.py `_require()` precedent, T-09-09-01 / T-10-01-01)."""
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{what}: missing required column(s) {missing}")


def gw_deadlines() -> pd.DataFrame:
    """One row per (season, gw): `deadline_ts = min(kickoff_time) - 90min`
    and `kickoff_max = max(kickoff_time)` (the second boundary
    `resolve_as_of` requires). Derived offline from
    `data/processed/player_gw.parquet` -- no network.

    Postponement caveat: if a gameweek's first fixture is postponed,
    `min(kickoff_time)` moves later and the derived `deadline_ts` becomes
    permissive (later than the real FPL deadline would have been) -- this is
    why `resolve_as_of` ALSO requires the source row to predate every
    kickoff in that gameweek (`kickoff_max`), not just the derived deadline.
    """
    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                          columns=["season", "gw", "kickoff_time"])
    raw = raw.dropna(subset=["kickoff_time"])
    g = raw.groupby(["season", "gw"], sort=False)["kickoff_time"]
    out = g.agg(kickoff_min="min", kickoff_max="max").reset_index()
    out["deadline_ts"] = out["kickoff_min"] - _DEADLINE_LEAD
    return out[["season", "gw", "deadline_ts", "kickoff_max"]]


def _daily_snapshot_source() -> pd.DataFrame:
    """Our own daily FPL bootstrap capture (data/snapshot.py). A snapshot
    only ever describes the live season at capture time -- tagged
    `season = config.CURRENT_SEASON`. Returns an empty frame (never raises)
    when no snapshots exist yet, matching every other optional source's
    contract."""
    from data import snapshot as snapshot_mod

    snaps = snapshot_mod.load_snapshots()
    if snaps.empty:
        return pd.DataFrame(columns=_REQUIRED_SOURCE_COLS)
    _require_columns(snaps, ["player_code", "ts_utc", "status",
                             "chance_of_playing_next_round"],
                     "daily_snapshot provider")
    out = snaps[["player_code", "ts_utc", "status",
                "chance_of_playing_next_round"]].copy()
    out["snapshot_ts"] = pd.to_datetime(out.pop("ts_utc"), utc=True)
    out["season"] = config.CURRENT_SEASON
    out["source"] = "daily_snapshot"
    return out[_REQUIRED_SOURCE_COLS]


def _fci_season_label(dirname: str) -> str:
    """FPL-Core-Insights' own season folder naming ('2025-2026') -> this
    project's convention ('2025-26'). A directory that already looks like a
    project-format season ('2025-26', e.g. a future 10-06 layout) passes
    through unchanged."""
    if len(dirname) == 9 and dirname[4] == "-" and dirname[:4].isdigit() and dirname[5:].isdigit():
        return f"{dirname[:4]}-{dirname[7:]}"
    return dirname


def _fpl_core_insights_source() -> pd.DataFrame:
    """Per-gameweek `playerstats.csv` CSVs -- committed home
    (`config.DATA_DIR / "external" / "fpl_core_insights"`, 10-06) falling
    back to the uncommitted probe (`config.RAW_DIR / "fpl_core_insights"`,
    this plan). Returns an empty frame (never raises) when neither directory
    exists, matching every other optional source's contract.

    Per D-05, a folder labelled gameweek N freezes at gameweek N's END:
    `snapshot_ts = max(kickoff_time over (season, N))`, from
    `player_gw.parquet` -- the moment it froze. `resolve_as_of` then performs
    the N-1 offset arithmetic for free (a GW-N file is only ever eligible for
    GW N+1 onward, since it postdates GW N's own deadline), with no special
    case anywhere in this module.
    """
    base = config.DATA_DIR / "external" / "fpl_core_insights"
    if not base.exists():
        base = config.RAW_DIR / "fpl_core_insights"
    if not base.exists():
        return pd.DataFrame(columns=_REQUIRED_SOURCE_COLS)

    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                          columns=["season", "gw", "kickoff_time"]).dropna(subset=["kickoff_time"])
    kickoff_max_by_gw = raw.groupby(["season", "gw"], sort=False)["kickoff_time"].max()
    id_map_df = id_map.load_id_map()[["season", "player_id", "player_code"]]

    frames = []
    for season_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        season = _fci_season_label(season_dir.name)
        for csv_path in sorted(season_dir.glob("GW*_playerstats.csv")):
            gw_token = csv_path.stem.split("_")[0]   # "GW1_playerstats" -> "GW1"
            if not gw_token.startswith("GW") or not gw_token[2:].isdigit():
                continue
            gw = int(gw_token[2:])
            key = (season, gw)
            if key not in kickoff_max_by_gw.index:
                # No deadline info for this (season, gw) -- e.g. player_gw.parquet
                # has no rows for this season yet. Skip silently: absent, never raise.
                continue
            df = pd.read_csv(csv_path, usecols=lambda c: c in {
                "id", "status", "chance_of_playing_next_round"})
            _require_columns(df, ["id", "status", "chance_of_playing_next_round"],
                             f"fpl_core_insights {csv_path.relative_to(base.parent)}")
            df = df.rename(columns={"id": "player_id"})
            merged = df.merge(id_map_df[id_map_df["season"] == season],
                              on="player_id", how="left")
            merged["snapshot_ts"] = kickoff_max_by_gw.loc[key]
            merged["season"] = season
            merged["source"] = "fpl_core_insights"
            frames.append(merged[_REQUIRED_SOURCE_COLS])
    if not frames:
        return pd.DataFrame(columns=_REQUIRED_SOURCE_COLS)
    return pd.concat(frames, ignore_index=True)


# Provider registry: source name -> zero-argument callable returning a long
# frame carrying at least `_REQUIRED_SOURCE_COLS`. A provider whose directory
# or files are absent returns an empty frame, never raises.
SOURCES: dict[str, Callable[[], pd.DataFrame]] = {
    "daily_snapshot": _daily_snapshot_source,
    "fpl_core_insights": _fpl_core_insights_source,
}


def load_sources() -> pd.DataFrame:
    """Run every registered provider and concatenate the results into one
    long frame. Each provider's output is validated by `_require_columns`
    before concatenation -- a provider cannot bypass the schema contract by
    returning an unexpected shape."""
    frames = []
    for name, fn in SOURCES.items():
        df = fn()
        if df is None or df.empty:
            continue
        _require_columns(df, _REQUIRED_SOURCE_COLS, f"provider '{name}'")
        frames.append(df[_REQUIRED_SOURCE_COLS])
    if not frames:
        return pd.DataFrame(columns=_REQUIRED_SOURCE_COLS)
    return pd.concat(frames, ignore_index=True)


def resolve_as_of(snaps: pd.DataFrame, deadlines: pd.DataFrame) -> pd.DataFrame:
    """For each (season, gw, player_code), select the source row with the
    maximum `snapshot_ts` satisfying BOTH `snapshot_ts < deadline_ts` AND
    `snapshot_ts < kickoff_max` (== `min(kickoff_time)` over that gameweek --
    the postponement guard). No qualifying row means that player-gameweek is
    simply absent from the output (D-10) -- never a raise, never a forward
    fill to a later snapshot.

    Asserted for EVERY registered `source` value by
    `tests/test_availability.py::test_every_source_row_predates_its_gw_deadline`,
    so a newly registered provider cannot bypass this rule (T-10-01-02).
    """
    _require_columns(snaps, ["season", "player_code", "snapshot_ts", "status",
                             "chance_of_playing_next_round", "source"],
                     "resolve_as_of: snaps")
    _require_columns(deadlines, ["season", "gw", "deadline_ts", "kickoff_max"],
                     "resolve_as_of: deadlines")
    if snaps.empty or deadlines.empty:
        return pd.DataFrame(columns=_RESOLVED_COLS)

    snaps = snaps.dropna(subset=["player_code", "snapshot_ts"]).copy()
    snaps["snapshot_ts"] = pd.to_datetime(snaps["snapshot_ts"], utc=True)

    results = []
    for season, dl in deadlines.groupby("season", sort=False):
        s = snaps[snaps["season"] == season]
        if s.empty:
            continue
        for _, row in dl.iterrows():
            # BOTH conditions at once: snapshot_ts must predate the derived
            # deadline AND predate every kickoff that gameweek (min of the two).
            cutoff = min(row["deadline_ts"], row["kickoff_max"])
            elig = s[s["snapshot_ts"] < cutoff]
            if elig.empty:
                continue
            latest = (elig.sort_values("snapshot_ts")
                     .groupby("player_code", as_index=False, sort=False).last())
            latest["season"] = season
            latest["gw"] = int(row["gw"])
            results.append(latest)
    if not results:
        return pd.DataFrame(columns=_RESOLVED_COLS)
    out = pd.concat(results, ignore_index=True)
    return out[_RESOLVED_COLS]


def build(*, force: bool = False) -> pd.DataFrame:
    """Fetch every registered source, resolve as-of-deadline, derive
    `av_chance_pct`, and write `data/processed/availability.parquet`. Prints
    the same `[availability] joined; coverage {pct}` line `attach()` prints,
    computed against `player_gw.parquet`'s own (season, gw, player_code)
    keys, so this CLI demonstrates real join coverage without requiring
    `data.build_table` to run first."""
    if not AVAILABILITY_ENABLED:
        print("  [availability] disabled (AVAILABILITY_ENABLED=False)")
        return pd.DataFrame(columns=["season", "gw", "player_code", "av_chance_pct"])
    if _OUT.exists() and not force:
        print(f"  [availability] {_OUT.name} exists (use --force to rebuild)")
        return pd.read_parquet(_OUT)

    deadlines = gw_deadlines()
    snaps = load_sources()
    resolved = resolve_as_of(snaps, deadlines)
    if resolved.empty:
        out = pd.DataFrame(columns=["season", "gw", "player_code", "av_chance_pct"])
    else:
        out = resolved[["season", "gw", "player_code"]].copy()
        out["av_chance_pct"] = pd.to_numeric(
            resolved["chance_of_playing_next_round"], errors="coerce") / 100.0
    out.to_parquet(_OUT, index=False)

    n_sources = resolved["source"].nunique() if not resolved.empty else 0
    print(f"  [availability] built {len(out):,} rows from {n_sources} source(s)")

    keys = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                           columns=["season", "gw", "player_code"]).drop_duplicates()
    joined = keys.merge(out, on=["season", "gw", "player_code"], how="left")
    cov = joined["av_chance_pct"].notna().mean() if len(joined) else 0.0
    print(f"  [availability] joined; coverage {cov:.1%}")
    return out


def load_availability() -> pd.DataFrame | None:
    """Return the cached table, or None when absent -- matching
    `data/fotmob.py::load_fotmob`'s no-op-if-absent contract."""
    return pd.read_parquet(_OUT) if _OUT.exists() else None


def attach(full: pd.DataFrame) -> pd.DataFrame:
    """Left-merge cached availability onto a player_gw-shaped frame on
    `["season", "gw", "player_code"]`. No-op if the kill switch is off or the
    cache is absent -- optional enrichment must never break the pipeline.
    Raises `AssertionError` if the join changes `full`'s row count (a
    many-to-many join here would corrupt every backtest)."""
    if not AVAILABILITY_ENABLED:
        return full
    avail = load_availability()
    if avail is None:
        return full

    need = ["season", "gw", "player_code"]
    missing = [c for c in need if c not in full.columns]
    if missing:
        raise AssertionError(f"attach(): full is missing required columns {missing}")

    before = len(full)
    merged = full.merge(avail[["season", "gw", "player_code", "av_chance_pct"]],
                        on=["season", "gw", "player_code"], how="left")
    if len(merged) != before:
        raise AssertionError(
            f"availability join changed row count {before} -> {len(merged)}")
    cov = merged["av_chance_pct"].notna().mean()
    print(f"  [availability] joined; coverage {cov:.1%}")
    return merged


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore the cache, rebuild")
    args = ap.parse_args(argv)

    if not AVAILABILITY_ENABLED:
        print("[availability] disabled (AVAILABILITY_ENABLED=False)")
        return 0
    out = build(force=args.force)
    print(f"availability: {len(out):,} rows")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
