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

`encode_availability` (plan 10-04) is a pure derivation on top of
`resolve_as_of`'s output -- status one-hot, chance%, news recency, and the
staleness of the resolved snapshot itself (`av_snapshot_age_days`) -- and
adds no new time-travel surface of its own.

Run:
  python -m data.availability            # (re)build data/processed/availability.parquet
  python -m data.availability --force    # ignore the cache, rebuild
  python -m data.availability --report   # read-only per-season/per-source coverage report
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

import pandas as pd

import config
from data import id_map
from ops.jsonio import write_json

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

# Carried through by whichever provider(s) actually supply them (currently
# fpl_core_insights for news_added; daily_snapshot gained these columns in
# data/snapshot.py from 2026-09-10, so older captured .parquet files under
# data/snapshots/ won't have them yet). load_sources()/resolve_as_of() treat
# these as pass-through: present when available, NaN otherwise -- never
# required (T-10-04's Task 1 grows the family from Task 1's own
# encode_availability, not from a schema requirement on every provider).
_OPTIONAL_SOURCE_COLS = ["news_added", "chance_of_playing_this_round"]

_RESOLVED_COLS = ["season", "gw", "player_code", "status",
                  "chance_of_playing_next_round", "source", "snapshot_ts",
                  "deadline_ts", "news_added", "chance_of_playing_this_round"]

# FPL's own per-player availability codes: a=available, d=doubtful,
# i=injured, s=suspended, u=unavailable -- config.AVAILABILITY_COLS's five
# av_status_* one-hot columns are a CLOSED set over exactly these five.
_STATUS_CODES = ("a", "d", "i", "s", "u")

# 'n' ("ineligible" -- e.g. a player who transferred out of the Premier
# League mid-season but remains in the FPL element list as a historic
# record) is a real code seen in the vendored fpl_core_insights probe data
# (2025-26 GW2/GW3: Nkunku/N.Jackson/Isak/Wissa, all mid-window-transfer
# players with chance_of_playing_next_round == 0.0) that predates this
# plan's five-code assumption. predict/live.py:130 already groups it with
# i/s/u as functionally unavailable ("injured/suspended/unavailable/
# ineligible") -- normalised here to 'u' for that same reason, rather than
# growing _STATUS_CODES to six: the one-hot family stays the exact eight
# columns config.AVAILABILITY_COLS declares, and a code this alias map does
# NOT cover still raises (T-10-04-01) rather than being silently folded in.
_STATUS_ALIASES = {"n": "u"}


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
    base_cols = ["player_code", "ts_utc", "status", "chance_of_playing_next_round"]
    optional = [c for c in _OPTIONAL_SOURCE_COLS if c in snaps.columns]
    out = snaps[base_cols + optional].copy()
    out["snapshot_ts"] = pd.to_datetime(out.pop("ts_utc"), utc=True)
    out["season"] = config.CURRENT_SEASON
    out["source"] = "daily_snapshot"
    return out[_REQUIRED_SOURCE_COLS + optional]


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
            df = pd.read_csv(csv_path, usecols=lambda c: c in (
                {"id", "status", "chance_of_playing_next_round"} | set(_OPTIONAL_SOURCE_COLS)))
            _require_columns(df, ["id", "status", "chance_of_playing_next_round"],
                             f"fpl_core_insights {csv_path.relative_to(base.parent)}")
            df = df.rename(columns={"id": "player_id"})
            merged = df.merge(id_map_df[id_map_df["season"] == season],
                              on="player_id", how="left")
            merged["snapshot_ts"] = kickoff_max_by_gw.loc[key]
            merged["season"] = season
            merged["source"] = "fpl_core_insights"
            optional = [c for c in _OPTIONAL_SOURCE_COLS if c in merged.columns]
            frames.append(merged[_REQUIRED_SOURCE_COLS + optional])
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
        optional = [c for c in _OPTIONAL_SOURCE_COLS if c in df.columns]
        frames.append(df[_REQUIRED_SOURCE_COLS + optional])
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
            # Pass-through, not a change to the selection rule above: Task
            # 10-04-01 needs each resolved row's own gw deadline_ts to derive
            # av_days_since_news/av_snapshot_age_days. Which row wins (the
            # two-condition cutoff + latest-per-player dedup immediately
            # above) is unchanged from plan 10-01.
            latest["deadline_ts"] = row["deadline_ts"]
            results.append(latest)
    if not results:
        return pd.DataFrame(columns=_RESOLVED_COLS)
    out = pd.concat(results, ignore_index=True)
    for col in _OPTIONAL_SOURCE_COLS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[_RESOLVED_COLS]


def encode_availability(resolved: pd.DataFrame) -> pd.DataFrame:
    """Derive the full OpenFPL-style eight-column availability family
    (arXiv:2508.09992 -- categorical availability tags, no proprietary xMins
    sub-model needed) from `resolve_as_of`'s output. A PURE function of the
    resolver's already leakage-safe frame: every column below is derived only
    from rows `resolve_as_of` already admitted, so this function adds no new
    time-travel surface of its own (T-10-04's own must_have).

    Returns exactly `config.AVAILABILITY_COLS` (in that order) plus the three
    join keys (season, gw, player_code) -- nothing else. A player-gameweek
    absent from `resolved` is simply absent from this function's output too;
    turning that absence into a whole-family NaN row is `attach()`'s left
    merge, not this function's job (D-10).
    """
    join_keys = ["season", "gw", "player_code"]
    _require_columns(
        resolved,
        join_keys + ["snapshot_ts", "deadline_ts", "status", "chance_of_playing_next_round"],
        "encode_availability",
    )
    if resolved.empty:
        return pd.DataFrame(columns=join_keys + config.AVAILABILITY_COLS)

    out = resolved[join_keys].copy()

    # av_chance_pct -- resolved as of a gameweek's deadline, "next round" IS
    # that gameweek, so chance_of_playing_next_round is the right field.
    # chance_of_playing_this_round describes whichever gameweek was CURRENT
    # when the snapshot was taken -- for a pre-deadline snapshot that is the
    # PREVIOUS gameweek, a different reference frame; captured (carried
    # through resolve_as_of) but deliberately left unencoded here.
    out["av_chance_pct"] = pd.to_numeric(
        resolved["chance_of_playing_next_round"], errors="coerce") / 100.0

    # Status one-hot: normalise known aliases (_STATUS_ALIASES), THEN
    # validate the remaining distinct codes against _STATUS_CODES. An
    # unrecognised code raises ValueError naming it and its row count
    # (T-10-04-01) -- an all-zeros one-hot would be indistinguishable from a
    # missing row and would hide a genuine upstream schema change.
    status_raw = resolved["status"].astype(str).str.strip().str.lower()
    status = status_raw.replace(_STATUS_ALIASES)
    unknown = sorted(set(status.unique()) - set(_STATUS_CODES))
    if unknown:
        counts = status.value_counts()
        detail = ", ".join(f"{code!r} ({int(counts.get(code, 0))} row(s))" for code in unknown)
        raise ValueError(
            f"encode_availability: unrecognised status code(s) not in "
            f"{_STATUS_CODES} (aliases: {_STATUS_ALIASES}): {detail}")
    for code in _STATUS_CODES:
        out[f"av_status_{code}"] = (status == code).astype(float)

    # av_days_since_news -- deadline_ts minus news_added, in whole days, NaN
    # when news_added is null. A news_added that POSTDATES the deadline means
    # resolve_as_of admitted a row it should have excluded (T-10-01-02's own
    # escape hatch) -- raise naming the offending key, never clip.
    deadline_ts = pd.to_datetime(resolved["deadline_ts"], utc=True)
    news_added = pd.to_datetime(resolved.get("news_added"), utc=True, errors="coerce")
    delta_news_days = (deadline_ts - news_added).dt.total_seconds() / 86400.0
    bad = delta_news_days < 0
    if bad.any():
        offenders = ", ".join(
            f"({r.season}, {r.gw}, {r.player_code})"
            for r in resolved.loc[bad, join_keys].itertuples(index=False)
        )
        raise AssertionError(
            f"encode_availability: news_added postdates the gw deadline for "
            f"{offenders} -- resolve_as_of should already have excluded these rows")
    out["av_days_since_news"] = delta_news_days

    # av_snapshot_age_days -- the staleness signal: how long before the
    # deadline the resolved snapshot was actually taken. Always strictly
    # positive because resolve_as_of only ever admits snapshot_ts < deadline_ts.
    snapshot_ts = pd.to_datetime(resolved["snapshot_ts"], utc=True)
    out["av_snapshot_age_days"] = (deadline_ts - snapshot_ts).dt.total_seconds() / 86400.0

    return out[join_keys + config.AVAILABILITY_COLS]


def build(*, force: bool = False) -> pd.DataFrame:
    """Fetch every registered source, resolve as-of-deadline, encode the full
    availability family (`encode_availability`), and write
    `data/processed/availability.parquet`. Prints the same
    `[availability] joined; coverage {pct}` line `attach()` prints, computed
    against `player_gw.parquet`'s own (season, gw, player_code) keys, so this
    CLI demonstrates real join coverage without requiring `data.build_table`
    to run first."""
    if not AVAILABILITY_ENABLED:
        print("  [availability] disabled (AVAILABILITY_ENABLED=False)")
        return pd.DataFrame(columns=["season", "gw", "player_code"] + config.AVAILABILITY_COLS)
    if _OUT.exists() and not force:
        print(f"  [availability] {_OUT.name} exists (use --force to rebuild)")
        return pd.read_parquet(_OUT)

    deadlines = gw_deadlines()
    snaps = load_sources()
    resolved = resolve_as_of(snaps, deadlines)
    out = encode_availability(resolved)
    # `source` is on-disk-only provenance for `--report`'s per-(season,
    # source) breakdown -- never part of config.AVAILABILITY_COLS, so
    # attach()'s merge (which selects only AVAILABILITY_COLS members) never
    # lets it reach player_gw.parquet/features.parquet.
    out["source"] = resolved["source"] if not resolved.empty else pd.Series(dtype="object")
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
    many-to-many join here would corrupt every backtest).

    Joins whichever `config.AVAILABILITY_COLS` members are actually present
    on the cached `avail` frame (a pre-Task-1 cache built by an older
    `data.availability` would only carry `av_chance_pct`; a fresh `--force`
    rebuild carries all eight). A left merge means a player-gameweek absent
    from `avail` gets NaN across every joined column TOGETHER -- never a
    partial fill (T-10-04-02) -- since a single merged row either matches one
    `avail` row (all present columns populated, `av_days_since_news`
    possibly still NaN if that row's own `news_added` was null) or matches
    nothing (every joined column NaN).
    """
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
    cols = need + [c for c in config.AVAILABILITY_COLS if c in avail.columns]
    merged = full.merge(avail[cols], on=need, how="left")
    if len(merged) != before:
        raise AssertionError(
            f"availability join changed row count {before} -> {len(merged)}")
    cov = merged["av_chance_pct"].notna().mean()
    print(f"  [availability] joined; coverage {cov:.1%}")
    return merged


_COVERAGE_OUT = config.EXPERIMENTS_DIR / "availability_coverage.json"


def report() -> dict:
    """Read-only per-season, per-source coverage + snapshot-staleness report.

    Loads the EXISTING `availability.parquet` (never rebuilds it -- no
    network access, no write to `_OUT`) and prints, per (season, source):
    row count, distinct players, distinct gameweeks, `av_chance_pct`
    non-null rate, and the median/95th-percentile `av_snapshot_age_days`.
    Then, per season: the fraction of that season's `player_gw.parquet` rows
    (deduplicated on the join key, matching `build()`'s own coverage calc)
    carrying a non-null `av_chance_pct` -- the number D-09's "covered
    season" language refers to -- with a loud `WARNING ... below 50%` line
    (mirroring `backtest/benchmark_external.py::score`'s own sub-50% warning)
    for any season under that bar, so a thin join can never be quietly
    reported as a result.

    Writes the same figures to `config.EXPERIMENTS_DIR /
    "availability_coverage.json"` (via `ops.jsonio.write_json`) so plan 10-08
    can cite exact numbers instead of re-deriving them from a printed table.

    T-10-04-05: this function is READ-ONLY. It must never call `build()` or
    write to `_OUT` -- a coverage check during an adoption run must never be
    able to perturb the artifact being judged.
    """
    if not _OUT.exists():
        print(f"  [availability] {_OUT.name} does not exist -- run "
              f"`python -m data.availability` (or --force) first")
        payload = {"per_season": {}, "per_source": {}}
        write_json(payload, _COVERAGE_OUT, indent=2)
        return payload

    d = pd.read_parquet(_OUT)
    keys = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet",
                           columns=["season", "gw", "player_code"]).drop_duplicates()

    per_source: dict = {}
    if not d.empty and "source" in d.columns:
        for (season, source), sub in d.groupby(["season", "source"], sort=True):
            ages = sub["av_snapshot_age_days"].dropna()
            row = {
                "n_rows": int(len(sub)),
                "n_players": int(sub["player_code"].nunique()),
                "n_gws": int(sub["gw"].nunique()),
                "chance_pct_non_null_rate": float(sub["av_chance_pct"].notna().mean()),
                "snapshot_age_days_median": float(ages.median()) if len(ages) else None,
                "snapshot_age_days_p95": float(ages.quantile(0.95)) if len(ages) else None,
            }
            per_source[f"{season}|{source}"] = row
            print(f"  [availability] {season} / {source}: n={row['n_rows']:,} "
                  f"players={row['n_players']} gws={row['n_gws']} "
                  f"chance_pct_non_null={row['chance_pct_non_null_rate']:.1%} "
                  f"snapshot_age_days median={row['snapshot_age_days_median']} "
                  f"p95={row['snapshot_age_days_p95']}")

    per_season: dict = {}
    for season, keys_season in keys.groupby("season", sort=True):
        if d.empty or "av_chance_pct" not in d.columns:
            joined = keys_season.assign(av_chance_pct=pd.NA)
        else:
            joined = keys_season.merge(
                d[["season", "gw", "player_code", "av_chance_pct"]],
                on=["season", "gw", "player_code"], how="left")
        n = len(joined)
        n_covered = int(joined["av_chance_pct"].notna().sum())
        cov = float(n_covered / n) if n else 0.0
        per_season[season] = {"n_rows": n, "n_covered": n_covered, "coverage": cov}
        print(f"  [availability] season {season}: coverage {cov:.1%} "
              f"({n_covered:,}/{n:,} rows)")
        if cov < 0.5:
            print(f"[availability] WARNING {season}: coverage {cov:.1%} below 50%")

    payload = {"per_season": per_season, "per_source": per_source}
    write_json(payload, _COVERAGE_OUT, indent=2)
    print(f"  [availability] wrote {_COVERAGE_OUT.relative_to(config.ROOT)}")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore the cache, rebuild")
    ap.add_argument(
        "--report", action="store_true",
        help="READ-ONLY: print + write per-season/per-source coverage and "
             "snapshot-staleness percentiles from the EXISTING "
             "availability.parquet cache -- never rebuilds it, never touches "
             "the network")
    args = ap.parse_args(argv)

    if not AVAILABILITY_ENABLED:
        print("[availability] disabled (AVAILABILITY_ENABLED=False)")
        return 0

    if args.report:
        report()
        return 0

    out = build(force=args.force)
    print(f"availability: {len(out):,} rows")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
