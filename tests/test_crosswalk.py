"""Regression tests for the shared player-identity crosswalk (D-03).

Only `data/external/kiwi/ID_Dictionary.csv` (committed, tracked) is needed --
no `needs_data` guard applies here, unlike tests reading the regenerable
data/processed/ pipeline outputs."""
from __future__ import annotations

import pandas as pd
import pytest

from data import id_crosswalk as crosswalk


@pytest.fixture(scope="module")
def crosswalk_df() -> pd.DataFrame:
    return crosswalk.build()


@pytest.fixture
def crosswalk_parquet(crosswalk_df, tmp_path, monkeypatch):
    """Write a real crosswalk parquet and point the module at it, so
    resolve_by_name()/load_crosswalk() are exercised without depending on
    `python -m data.id_crosswalk` having already run in this session."""
    dest = tmp_path / "id_crosswalk.parquet"
    crosswalk_df.to_parquet(dest, index=False)
    monkeypatch.setattr(crosswalk, "_OUT", dest)
    return crosswalk_df


def test_norm_strips_accents_and_lowercases():
    out = crosswalk._norm(pd.Series(["Guéhi"]))
    assert out.iloc[0] == "guehi"


def test_build_returns_unique_player_code(crosswalk_df):
    assert crosswalk_df["player_code"].is_unique


def test_build_produces_name_key_and_fbref_key_columns(crosswalk_df):
    assert "name_key" in crosswalk_df.columns
    assert "fbref_key" in crosswalk_df.columns


def test_resolve_by_name_maps_known_fpl_name_to_its_own_player_code(crosswalk_parquet):
    known = crosswalk_parquet.dropna(subset=["fpl_name"]).iloc[0]
    result = crosswalk.resolve_by_name(pd.Series([known["fpl_name"]]))
    assert int(result.iloc[0]) == int(known["player_code"])


def test_resolve_by_name_returns_na_for_unknown_name(crosswalk_parquet, monkeypatch):
    """An unresolvable name falls through both crosswalk tiers into the
    historical-registry tier (`_fpl_name_index`), which loads the full id map
    and needs season files a clean checkout does not have. Stand in a
    zero-arg lambda returning an empty Int64 Series in its place -- mapping
    against an empty index still yields NA for every key, so the assertion
    stays meaningful while the test remains offline and deterministic.
    `monkeypatch.setattr` on the module attribute supersedes the
    `functools.lru_cache` wrapper wholesale, so no cached call ever fires."""
    monkeypatch.setattr(crosswalk, "_fpl_name_index", lambda: pd.Series(dtype="Int64"))
    result = crosswalk.resolve_by_name(pd.Series(["Zzzznonexistent Qqqqplayer"]))
    assert pd.isna(result.iloc[0])


def test_merge_against_crosswalk_preserves_row_count(crosswalk_parquet):
    codes = crosswalk_parquet["player_code"].head(100).tolist()
    synthetic = pd.DataFrame({"player_code": codes, "x": range(len(codes))})
    merged = synthetic.merge(crosswalk.load_crosswalk(), on="player_code", how="left")
    assert len(merged) == len(synthetic)


# --- data/external/kiwi/ (plan 09-02 D1) --

def test_kiwi_id_dictionary_exists():
    """Plan 09-02 D1: committed snapshot files must exist."""
    from pathlib import Path
    id_dict = Path(__file__).parent.parent / "data" / "external" / "kiwi" / "ID_Dictionary.csv"
    assert id_dict.exists(), f"Kiwi ID_Dictionary.csv not found at {id_dict}"


def test_kiwi_projection_csvs_exist():
    """Plan 09-02 D1: all three seasons' projection CSVs must be present."""
    from pathlib import Path
    kiwi_dir = Path(__file__).parent.parent / "data" / "external" / "kiwi"
    for season in ["2021-22", "2022-23", "2023-24"]:
        path = kiwi_dir / f"kiwi_projections_{season}.csv"
        assert path.exists(), f"Kiwi projections CSV not found: {path}"


def test_kiwi_projections_have_exactly_8_tidy_columns():
    """Plan 09-02 D1: each projection CSV must have exactly the 8 tidy columns
    declared in data/external/README.md: season, gw, fpl_id, name, pos, team,
    price, proj_pts."""
    from pathlib import Path
    expected_cols = {"season", "gw", "fpl_id", "name", "pos", "team", "price", "proj_pts"}
    kiwi_dir = Path(__file__).parent.parent / "data" / "external" / "kiwi"

    for season in ["2021-22", "2022-23", "2023-24"]:
        path = kiwi_dir / f"kiwi_projections_{season}.csv"
        df = pd.read_csv(path)
        assert set(df.columns) == expected_cols, (
            f"{season}: columns {set(df.columns)} != expected {expected_cols}"
        )


def test_kiwi_projections_no_fpl_id_zero_placeholder():
    """Plan 09-02 D1: no row with fpl_id==0 should survive reduction.
    fpl_id==0 rows are theFPLkiwi's own placeholders for not-yet-signed players."""
    from pathlib import Path
    kiwi_dir = Path(__file__).parent.parent / "data" / "external" / "kiwi"

    for season in ["2021-22", "2022-23", "2023-24"]:
        path = kiwi_dir / f"kiwi_projections_{season}.csv"
        df = pd.read_csv(path)
        zero_rows = df[df["fpl_id"] == 0]
        assert len(zero_rows) == 0, (
            f"{season}: found {len(zero_rows)} rows with fpl_id==0 "
            "(should have been dropped during reduction)"
        )
