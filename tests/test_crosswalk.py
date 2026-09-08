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


def test_resolve_by_name_returns_na_for_unknown_name(crosswalk_parquet):
    result = crosswalk.resolve_by_name(pd.Series(["Zzzznonexistent Qqqqplayer"]))
    assert pd.isna(result.iloc[0])


def test_merge_against_crosswalk_preserves_row_count(crosswalk_parquet):
    codes = crosswalk_parquet["player_code"].head(100).tolist()
    synthetic = pd.DataFrame({"player_code": codes, "x": range(len(codes))})
    merged = synthetic.merge(crosswalk.load_crosswalk(), on="player_code", how="left")
    assert len(merged) == len(synthetic)
