"""FBref (StatsBomb) advanced stats — direct-URL scrape seam.

FBref sits behind Cloudflare, so soccerdata's scraper is unreliable (its season
enumeration breaks). Instead we drive Chrome directly via seleniumbase's UC mode,
fetch the player stat pages by URL, and parse the tables ourselves. Two-step:

  1. On a machine with Chrome:   python -m data.fbref --scrape
     -> writes data/processed/fbref.parquet (per-player-season per-90 rates).
  2. Anywhere: `python -m data.build_table` auto-joins the file if present
     (adds config.FBREF_COLS); without it, nothing changes.

Why FBref: per-season DEFENSIVE actions (tackles+interceptions, blocks, clearances)
feed FPL's defensive-contribution points, plus SCA/GCA and progressive passes.

NOTE: joined by normalised player name within season (FBref has no FPL id). Check
the printed coverage on first run and extend `_NAME_FIXUPS` for misses.
"""
from __future__ import annotations

import argparse
import io
import sys
import time

import pandas as pd

import config

_OUT = config.PROCESSED_DIR / "fbref.parquet"
_URL = "https://fbref.com/en/comps/9/{season}/{kind}/{season}-Premier-League-Stats"
_NAME_FIXUPS: dict[str, str] = {}   # FBref -> FPL full name (extend on first run)


def _norm(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.normalize("NFKD").str.encode("ascii", "ignore")
            .str.decode("ascii").str.lower().str.strip())


def _find(cols, *subs):
    for sub in subs:
        for c in cols:
            if sub.lower() in str(c).lower():
                return c
    return None


def _table(html: str, table_id: str) -> pd.DataFrame:
    """Parse one FBref stats table (they are hidden inside HTML comments).

    Mid-season movers appear once PER SQUAD; keep only the primary stint (most
    90s) so downstream merges stay 1 row per player (a 2-squad player in all
    three tables would otherwise blow up 2x2x2 on the name merges).
    """
    html = html.replace("<!--", "").replace("-->", "")
    t = pd.read_html(io.StringIO(html), attrs={"id": table_id})[0]
    t.columns = ["_".join(str(x) for x in c) if isinstance(c, tuple) else str(c)
                 for c in t.columns]
    pl = _find(t.columns, "Player")
    t = t[t[pl].ne("Player")].reset_index(drop=True)      # drop repeated header rows
    n90c = _find(t.columns, "90s")
    if n90c:
        t = (t.assign(_n90=pd.to_numeric(t[n90c], errors="coerce").fillna(0))
             .sort_values("_n90", ascending=False)
             .drop_duplicates(subset=[pl]).drop(columns="_n90").reset_index(drop=True))
    else:
        t = t.drop_duplicates(subset=[pl]).reset_index(drop=True)
    return t


def scrape_to_cache(seasons=None) -> pd.DataFrame:
    from seleniumbase import Driver  # lazy: only needed for scraping

    seasons = seasons or [s for s in config.SEASONS if s <= config.CURRENT_SEASON]
    # Incremental: keep already-cached seasons, only fetch the missing ones, and
    # write the parquet after EVERY season so a killed run loses nothing.
    cached = load_fbref()
    done = set(cached.season.unique()) if cached is not None else set()
    seasons = [s for s in seasons if s not in done]
    if done:
        print(f"  [cache] {len(done)} seasons already cached, fetching {len(seasons)} more")
    if not seasons:
        return cached
    driver = Driver(uc=True, headless=True)

    def fbref_code(s):                       # "2025-26" -> FBref URL form "2025-2026"
        return f"{s[:4]}-20{s[5:7]}"

    def fetch(season, kind):
        driver.uc_open_with_reconnect(
            _URL.format(season=fbref_code(season), kind=kind), reconnect_time=6)
        time.sleep(4)
        return driver.get_page_source()

    def num(df, col):
        return pd.to_numeric(df[col], errors="coerce") if col else pd.Series(dtype=float)

    frames = []
    try:
        for s in seasons:
            try:
                dfn = _table(fetch(s, "defense"), "stats_defense")
                gca = _table(fetch(s, "gca"), "stats_gca")
                pas = _table(fetch(s, "passing"), "stats_passing")
            except Exception as exc:
                print(f"  [skip] {s}: {exc}")
                continue
            n90 = num(dfn, _find(dfn.columns, "90s"))
            n90p = num(pas, _find(pas.columns, "90s")).clip(lower=0.5)
            base = pd.DataFrame({
                "season": s,
                "player": dfn[_find(dfn.columns, "Player")],
                "team": dfn[_find(dfn.columns, "Squad")],
                "fb_tkl_int_90": num(dfn, _find(dfn.columns, "Tkl+Int")) / n90.clip(lower=0.5),
                "fb_blocks_90": num(dfn, _find(dfn.columns, "Blocks_Blocks", "Blocks")) / n90.clip(lower=0.5),
                "fb_clr_90": num(dfn, _find(dfn.columns, "Clr")) / n90.clip(lower=0.5),
            })
            gkey = _find(gca.columns, "Player")
            base = base.merge(pd.DataFrame({
                "player": gca[gkey],
                "fb_sca_90": num(gca, _find(gca.columns, "SCA_SCA90", "SCA90")),
                "fb_gca_90": num(gca, _find(gca.columns, "GCA_GCA90", "GCA90")),
            }), on="player", how="left")
            base = base.merge(pd.DataFrame({
                "player": pas[_find(pas.columns, "Player")],
                "fb_prog_90": num(pas, _find(pas.columns, "PrgP", "Progressive")) / n90p,
            }), on="player", how="left")
            frames.append(base)
            # Persist incrementally: append this season to the cache right away.
            keep = ["season", "player", "team"] + config.FBREF_COLS
            partial = pd.concat(([cached] if cached is not None else []) + frames,
                                ignore_index=True)[keep]
            partial.to_parquet(_OUT, index=False)
            print(f"  [ok]   {s}: {len(base)} players (cache now {len(partial):,} rows)")
    finally:
        driver.quit()

    out = load_fbref()
    print(f"wrote {_OUT.relative_to(config.ROOT)} ({len(out):,} player-seasons)")
    return out


def load_fbref() -> pd.DataFrame | None:
    return pd.read_parquet(_OUT) if _OUT.exists() else None


def _next_season(s: str) -> str:
    """'2017-18' -> '2018-19'."""
    y = int(s[:4]) + 1
    return f"{y}-{(y + 1) % 100:02d}"


def attach(full: pd.DataFrame, id_map: pd.DataFrame) -> pd.DataFrame:
    """Join cached FBref per-90s onto player_gw by normalised name, LAGGED one
    season: season-s aggregates describe the player entering season s+1. Joining
    same-season would leak end-of-season rates into early gameweeks, and live
    inference could never have the current season's aggregate anyway.

    `id_map` supplies FPL first/second names per (season, player_id). No-op if the
    cache is absent. Guarded so a bad/low-coverage join never breaks the pipeline.
    """
    fb = load_fbref()
    if fb is None:
        return full
    fb = fb.copy()
    fb["season"] = fb["season"].map(_next_season)
    fb["_key"] = fb["season"] + "|" + _norm(fb["player"].replace(_NAME_FIXUPS))
    fb = fb.drop_duplicates(subset="_key")   # never let the join multiply rows

    names = id_map[["season", "player_id", "first_name", "second_name"]].copy()
    names["_key"] = names["season"] + "|" + _norm(
        names["first_name"].fillna("") + " " + names["second_name"].fillna(""))
    key = names[["season", "player_id", "_key"]].drop_duplicates()

    merged = full.merge(key, on=["season", "player_id"], how="left").merge(
        fb[["_key"] + config.FBREF_COLS], on="_key", how="left").drop(columns=["_key"])
    if len(merged) != len(full):   # a many-to-many join here corrupts every backtest
        raise AssertionError(f"fbref join changed row count {len(full)} -> {len(merged)}")
    cov = merged["fb_tkl_int_90"].notna().mean()
    print(f"  [fbref] joined; coverage {cov:.1%}"
          + ("  (low -> extend _NAME_FIXUPS)" if cov < 0.5 else ""))
    return merged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scrape", action="store_true", help="scrape FBref (needs Chrome)")
    args = ap.parse_args(argv)
    if args.scrape:
        scrape_to_cache()
    else:
        fb = load_fbref()
        print("no cache — run with --scrape on a machine with Chrome"
              if fb is None else f"cache present: {len(fb):,} player-seasons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
