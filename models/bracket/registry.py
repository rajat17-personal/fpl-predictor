"""Phase 10 plan 10-10: the stage-2 regressor swap registry (D-12).

`models/train.py::train_position`'s new `stage2` parameter calls through
`build_regressor` -- this is the ONE swap seam: the stage-1 P(play)
classifier, the calibration path, and the `ComponentModel` DEF/GK structure
are all untouched, and only the conditional-points regressor construction
is routed through here.

`CANDIDATES` now covers all seven `config.BRACKET_CANDIDATES` names (plan
10-10's `lgbm`/`ridge`/`xgb`/`catboost`, plan 10-11's `mlp`, and this plan's
`rnn`/`transformer`) -- `set(registry.CANDIDATES) == set(config.BRACKET_CANDIDATES)`.
The three deep-candidate factories (`mlp`/`rnn`/`transformer`) import their
owning module LAZILY, inside the factory function body rather than at this
module's top level: `models/bracket/deep.py`, `recurrent.py` and
`transformer.py` all import `torch` at module scope, which would make this
whole registry unimportable on a machine without torch installed if imported
eagerly here. `is_available` never triggers that import either -- it only
resolves `importlib.util.find_spec("torch")`, so it can answer False for a
missing package rather than raising.
"""
from __future__ import annotations

import importlib.util

from models.bracket import classical, gbdt


def _lgbm_factory(objective: str, params: dict):
    """The shipped candidate -- byte-equivalent to `models/train.py`'s own
    pre-bracket `LGBMRegressor(objective=objective, **params)` construction."""
    from lightgbm import LGBMRegressor
    return LGBMRegressor(objective=objective, **params)


def _mlp_factory(objective: str, params: dict):
    """Plan 10-11's tabular MLP candidate -- lazy import (see module docstring)."""
    from models.bracket import deep
    return deep.build_mlp(objective, params)


def _rnn_factory(objective: str, params: dict):
    """This plan's GRU sequence candidate -- lazy import (see module docstring)."""
    from models.bracket import recurrent
    return recurrent.build_gru(objective, params)


def _transformer_factory(objective: str, params: dict):
    """This plan's transformer sequence candidate -- lazy import (see module
    docstring)."""
    from models.bracket import transformer as transformer_mod
    return transformer_mod.build_transformer(objective, params)


# name -> (factory callable, module import name required for availability)
CANDIDATES = {
    "lgbm": (_lgbm_factory, "lightgbm"),
    "ridge": (classical.RidgeRegressorFactory(), "sklearn"),
    "xgb": (gbdt.XgbRegressorFactory(), "xgboost"),
    "catboost": (gbdt.CatBoostRegressorFactory(), "catboost"),
    "mlp": (_mlp_factory, "torch"),
    "rnn": (_rnn_factory, "torch"),
    "transformer": (_transformer_factory, "torch"),
}


def is_available(name: str) -> bool:
    """True iff `name` is a known candidate whose required package resolves
    in the current environment. Never raises for an unknown/unavailable
    name -- returns False instead, so `models/bracket/gate.py::run_gate` can
    skip a candidate cleanly (`"status": "unavailable"`) on a machine
    without the dev-only `requirements-experiments.txt` lockfile installed."""
    if name not in CANDIDATES:
        return False
    _, import_name = CANDIDATES[name]
    return importlib.util.find_spec(import_name) is not None


def build_regressor(name: str, objective: str, params: dict):
    """Return an unfitted stage-2 regressor for `name`, exposing sklearn's
    `fit`/`predict`. Raises `ValueError` naming the bad name and listing
    valid keys (`config.resolve_experiments`'s own error-message style) for
    an unrecognised name -- this is a programmer error (a typo'd candidate
    name), never an expected runtime state; an unavailable-but-known
    candidate is instead handled by `is_available`, not by this function."""
    if name not in CANDIDATES:
        raise ValueError(
            f"unknown bracket candidate '{name}' -- valid keys: {sorted(CANDIDATES)}")
    factory, _ = CANDIDATES[name]
    return factory(objective, params)


def export_sequence_bundle(seasons: list[str], out_dir):
    """Serialize `models/bracket/sequence.py::SequenceBundle` tensors plus
    the identity frame for the Colab handoff (D-13's GRU/transformer
    candidates), writing a `manifest.json` that is the notebook's SPLIT
    AUTHORITY -- the anti-Pitfall-6 device (10-RESEARCH.md): the notebook
    reads its splits from here, it never derives its own.

    `seasons` is the list of TEST seasons the caller wants a Colab run for
    (e.g. `["2025-26"]`). For each one, the exact `(train_seasons,
    val_season, test_season)` triple is computed by the IDENTICAL
    expanding-window rule `backtest.walk_forward._preds_for` uses, and
    recorded under `manifest["splits"][test_season]`. The tensor files
    written to `out_dir` cover the UNION of every season any requested test
    season's split triple touches (its train seasons, its val season, and
    itself) -- a real Colab training loop needs all of them, not just the
    test season's own rows, and `models/bracket/sequence.py` builds each
    season's history from that season alone (never crossing a season
    boundary), so one exported file per needed season is sufficient; no
    season is ever exported twice even if two requested test seasons share
    training seasons.

    Never trusted as an artifact CONSUMED back into this repo without going
    through `backtest.walk_forward.load_external_predictions` -- this
    function only produces the notebook's INPUT.
    """
    import hashlib
    from pathlib import Path

    import numpy as np
    import pandas as pd
    import torch

    import config
    from backtest.walk_forward import DATA_SEASONS
    from models.bracket import sequence as bracket_sequence
    from models.train import load_features
    from ops.jsonio import write_json

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    feat = load_features()
    raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet")
    features_sha256 = hashlib.sha256(
        (config.PROCESSED_DIR / "features.parquet").read_bytes()).hexdigest()

    splits: dict = {}
    needed_seasons: set[str] = set()
    for test_season in seasons:
        i = DATA_SEASONS.index(test_season)
        if i < 2:
            raise ValueError(
                f"{test_season}: need >=2 prior seasons (same rule "
                "backtest.walk_forward._preds_for enforces)")
        train_seasons, val_season = DATA_SEASONS[:i - 1], DATA_SEASONS[i - 1]
        splits[test_season] = {
            "train_seasons": list(train_seasons),
            "val_season": val_season,
            "test_season": test_season,
        }
        needed_seasons |= set(train_seasons) | {val_season, test_season}

    for season in sorted(needed_seasons):
        gws = sorted(feat.loc[feat.season == season, "gw"].unique().tolist())
        bundles = [bracket_sequence.build_sequences(season, int(gw), raw=raw, feat=feat)
                  for gw in gws]
        x_seq = torch.cat([b.x_seq for b in bundles], dim=0)
        mask = torch.cat([b.mask for b in bundles], dim=0)
        x_static = torch.cat([b.x_static for b in bundles], dim=0)
        y = torch.cat([b.y for b in bundles], dim=0)
        minutes = torch.cat([b.minutes for b in bundles], dim=0)
        ids = pd.concat([b.ids for b in bundles], ignore_index=True)

        safe = season.replace("/", "-")
        np.savez(out_dir / f"{safe}_tensors.npz",
                 x_seq=x_seq.numpy(), mask=mask.numpy(), x_static=x_static.numpy(),
                 y=y.numpy(), minutes=minutes.numpy())
        ids.to_parquet(out_dir / f"{safe}_ids.parquet", index=False)

    manifest = {
        "seq_window": bracket_sequence.SEQ_WINDOW,
        "seq_stats": list(bracket_sequence.SEQ_STATS),
        "static_cols": list(bracket_sequence.STATIC_COLS),
        "shapes": {
            "x_seq": [None, bracket_sequence.SEQ_WINDOW, len(bracket_sequence.SEQ_STATS)],
            "mask": [None, bracket_sequence.SEQ_WINDOW],
            "x_static": [None, len(bracket_sequence.STATIC_COLS)],
        },
        "dtypes": {"x_seq": "float32", "mask": "bool", "x_static": "float32",
                   "y": "float32", "minutes": "float32"},
        "features_sha256": features_sha256,
        "seasons_exported": sorted(needed_seasons),
        "splits": splits,
    }
    write_json(manifest, out_dir / "manifest.json", indent=1)
    return out_dir
