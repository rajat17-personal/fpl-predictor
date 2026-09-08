"""One shared player-identity crosswalk keyed on `player_code` (D-03).

Problem: this phase introduces three foreign identity namespaces at once
(Understat, FotMob, FBref) on top of the existing FPL-internal identity in
`data/id_map.py`. Without a shared crosswalk, each enrichment source would
grow its own divergent name matcher -- exactly the kind of many-to-many join
that once silently corrupted a whole backtest in `data/fbref.py` (see
IMPROVEMENTS.md Phase E).

`data/id_map.py` stays the sole authority for FPL identity; `player_code`
remains the canonical join key everywhere. This module is an *alias table*
keyed by `player_code`, built from theFPLkiwi's committed `ID_Dictionary.csv`
(`data/external/kiwi/ID_Dictionary.csv`, see `data/external/README.md`) --
not a competing identity model.

IMPORTANT: the committed `ID_Dictionary.csv` carries NO Understat identifier
column (verified 2026-09-08 against the live upstream repository; this
settles 09-RESEARCH.md's Open Question 3 and assumption A5 in the negative --
no Understat IDs exist upstream). `resolve_by_name()` -- normalised-name
matching, with a manual `_NAME_FIXUPS` override for misses -- is therefore
the REQUIRED fallback path for resolving Understat player names to
`player_code`, and for any other source without a direct id column.

Run:
  python -m data.id_crosswalk        # (re)build data/processed/id_crosswalk.parquet
"""
from __future__ import annotations

import sys

import pandas as pd

import config

_SRC = config.ROOT / "data" / "external" / "kiwi" / "ID_Dictionary.csv"
_OUT = config.PROCESSED_DIR / "id_crosswalk.parquet"

# Source name -> theFPLkiwi FPL name, for resolve_by_name() misses (extend as
# later plans discover them -- same manual-override convention as
# data/fbref.py's _NAME_FIXUPS).
_NAME_FIXUPS: dict[str, str] = {}

_RENAME = {
    "FPL code": "player_code",
    "FPL ID": "kiwi_fpl_id",
    "FPL name": "fpl_name",
    "fbref": "fbref_name",
    "fbref ID": "fbref_id",
    "Name": "kiwi_name",
    "FPL pos": "position",
    "Team": "team",
    "DOB": "dob",
}
_COLS = ["player_code", "kiwi_fpl_id", "fpl_name", "fbref_name", "fbref_id",
         "kiwi_name", "position", "team", "dob", "name_key", "fbref_key"]


def _norm(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.normalize("NFKD").str.encode("ascii", "ignore")
            .str.decode("ascii").str.lower().str.strip())


def build() -> pd.DataFrame:
    """Build the player_code-keyed alias table from the committed ID dictionary.

    `drop_duplicates(subset="player_code")` plus the trailing uniqueness
    assertion make a many-to-many join structurally impossible downstream --
    the same discipline that stopped a repeat of the fbref join corruption
    (IMPROVEMENTS.md Phase E).
    """
    raw = pd.read_csv(_SRC, encoding="latin-1")
    df = raw.rename(columns=_RENAME)
    df["player_code"] = pd.to_numeric(df["player_code"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["player_code"])
    df["name_key"] = _norm(df["fpl_name"])
    df["fbref_key"] = _norm(df["fbref_name"])
    df = df.drop_duplicates(subset="player_code", keep="first").reset_index(drop=True)
    if not df["player_code"].is_unique:
        raise AssertionError(
            "id_crosswalk.build(): duplicate player_code would multiply rows "
            "in every downstream merge")
    return df[_COLS]


def load_crosswalk() -> pd.DataFrame | None:
    """Return the cached crosswalk, or None when absent -- matching
    `data/fbref.py::load_fbref`'s no-op-if-absent contract so downstream
    joins can stay inside a guarded try/except."""
    return pd.read_parquet(_OUT) if _OUT.exists() else None


def resolve_by_name(names: pd.Series) -> pd.Series:
    """Map arbitrary source names to `player_code`.

    Tries, in order: `_norm` against `name_key` (theFPLkiwi's own FPL name),
    then `_norm` against `fbref_key`, then `_NAME_FIXUPS` (applied to the raw
    name before normalising, for a source's persistent misses). Returns
    `pd.NA` for names that resolve nowhere.
    """
    cw = load_crosswalk()
    if cw is None:
        return pd.Series(pd.NA, index=names.index, dtype="Int64")
    fixed = names.replace(_NAME_FIXUPS)
    keys = _norm(fixed)
    by_name = (cw.dropna(subset=["name_key"]).drop_duplicates("name_key")
               .set_index("name_key")["player_code"])
    by_fbref = (cw.dropna(subset=["fbref_key"]).drop_duplicates("fbref_key")
                .set_index("fbref_key")["player_code"])
    out = keys.map(by_name)
    missing = out.isna()
    if missing.any():
        out.loc[missing] = keys[missing].map(by_fbref)
    return out.astype("Int64")


def main() -> int:
    from data.id_map import load_id_map

    cw = build()
    cw.to_parquet(_OUT, index=False)

    idm_codes = set(load_id_map()["player_code"].dropna().unique())
    cw_codes = set(cw["player_code"].dropna().unique())
    covered = len(idm_codes & cw_codes)
    pct = covered / len(idm_codes) if idm_codes else 0.0
    print(f"[crosswalk] {len(cw):,} rows; covers {pct:.1%} of id_map.parquet's "
          f"{len(idm_codes):,} distinct player_code values")
    print(f"wrote {_OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
