"""Phase 10 plan 10-11: the leakage-safe padded/masked sequence builder (D-20).

The sequence-model hypothesis (plan 10-13's LSTM/GRU and transformer
candidates, this plan's shared infrastructure) is explicitly "can a network
learn better temporal aggregation than our hand-rolled `_r3`/`_r5`/`_r10`/
`_rall` rolling windows" -- which only means anything if the network sees
RAW per-gameweek history rather than the engineered rolled means. That makes
this module a brand-new leakage surface (D-21): every timestep feeding a
GW-g prediction must come from a strictly earlier `kickoff_time`, proven on
real data by `tests/test_leakage.py::test_sequence_features_no_future_gw_leakage`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

import config
from features.engineer import CONTEXT_COLS, ROLL_STATS

# D-20's stated ~8-10 gameweek band, locked at its top per 10-01-PLAN.md's
# decision table. Lives HERE, not config.py, for two reasons: it is a
# bracket-internal representation choice rather than a pipeline-wide feature
# declaration, and config.py belongs to plan 10-10's file set in an earlier
# wave.
SEQ_WINDOW = 10


def _parquet_columns(path: Path) -> set[str]:
    """Column names of an on-disk parquet file's schema only (no row data
    read) -- returns an empty set if the file doesn't exist yet, so this
    module's import never breaks a fresh clone that hasn't run the pipeline."""
    if not path.exists():
        return set()
    return set(pq.ParquetFile(path).schema.names)


_RAW_COLUMNS = _parquet_columns(config.PROCESSED_DIR / "player_gw.parquet")
_FEAT_COLUMNS = _parquet_columns(config.PROCESSED_DIR / "features.parquet")

# The raw per-gameweek stats each timestep carries. Taken from
# `features/engineer.py::ROLL_STATS`, restricted to those actually present
# in `player_gw.parquet` (mirrors `add_features`'s own "skip a ROLL_STATS
# entry absent from df" contract), falling back to the full declared list
# when the parquet doesn't exist yet (e.g. a fresh clone). This is
# deliberately the UNROLLED series -- D-20's hypothesis is that a network
# can learn its own temporal aggregation, which is only under test if it
# sees the raw series `_roll` would otherwise have shift(1)-then-averaged.
# Feeding `*_r3`/`*_r5` back in would test nothing.
SEQ_STATS: list[str] = ([s for s in ROLL_STATS if s in _RAW_COLUMNS]
                        if _RAW_COLUMNS else list(ROLL_STATS))

# The pre-match context for the target fixture, taken from
# `features/engineer.py::CONTEXT_COLS` restricted to columns actually
# present in `features.parquet`. Asserted below (at module-load / "build"
# time) to never carry a rolled column -- CONTEXT_COLS never does by
# construction, but this guards a future edit that "helpfully" moves a
# rolled family in here.
STATIC_COLS: list[str] = ([c for c in CONTEXT_COLS if c in _FEAT_COLUMNS]
                          if _FEAT_COLUMNS else list(CONTEXT_COLS))

_bad_static = [c for c in STATIC_COLS if c.endswith(("_r3", "_r5", "_r10", "_rall"))]
assert not _bad_static, f"STATIC_COLS must never carry a rolled column: {_bad_static}"


@dataclass
class SequenceBundle:
    """One row per target fixture. `x_seq`/`mask` share the `(n_rows,
    window)` leading shape; `mask` follows the `src_key_padding_mask`
    convention `nn.TransformerEncoder`/`nn.LSTM` expect: True = padded."""

    x_seq: torch.Tensor        # (n_rows, window, n_stats) float32
    mask: torch.Tensor         # (n_rows, window) bool -- True = padded
    x_static: torch.Tensor     # (n_rows, n_static) float32
    y: torch.Tensor            # (n_rows,) float32 -- y_points
    minutes: torch.Tensor      # (n_rows,) float32 -- y_minutes
    ids: pd.DataFrame          # season, gw, player_code, fixture_id (parallel frame)


def _pad_and_mask(per_player_arrays: list[np.ndarray], window: int,
                  n_stats: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Left-pad a list of `(n_i, n_stats)` arrays (`n_i <= window`, most
    recent row last) to `(len(arrays), window, n_stats)` via
    `torch.nn.utils.rnn.pad_sequence`, plus an explicit boolean mask (True =
    padded). Left-padding (not `pad_sequence`'s own right-padding default)
    keeps the most recent gameweek always at the LAST index regardless of
    history length -- a recurrent/attention model reading a right-padded
    batch would attend to padding as if it were recent form.

    `pad_sequence` pads to the BATCH's own max length, which can be shorter
    than `window` when every row in this call has a short history (e.g. an
    early-season gameweek) -- a dummy all-zero length-`window` sequence is
    prepended to force the padded output to exactly `window` timesteps, then
    dropped. This is a minimal, documented use of the standard idiom, not a
    hand-rolled fixed-length padder.
    """
    seqs = [torch.as_tensor(a, dtype=torch.float32) for a in per_player_arrays]
    dummy = torch.zeros(window, n_stats, dtype=torch.float32)
    reversed_seqs = [dummy] + [s.flip(0) for s in seqs]
    padded_rev = torch.nn.utils.rnn.pad_sequence(reversed_seqs, batch_first=True)[1:]
    x = padded_rev.flip(1)

    lengths = torch.tensor([len(a) for a in per_player_arrays], dtype=torch.long)
    idx = torch.arange(window).unsqueeze(0)
    mask = idx < (window - lengths).unsqueeze(1)   # True = padded position
    return x, mask


def _player_histories(raw: pd.DataFrame, season: str, seq_stats: list[str],
                      player_ids) -> dict:
    """`player_id -> (kickoff_time ndarray asc, stats ndarray asc)` for every
    id in `player_ids`, restricted to `season` -- rolling/sequence features
    reset at a season boundary in this codebase (`features/engineer.py`'s
    own `groupby(["season", "player_id"])`), so history never crosses a
    season."""
    sub = raw[(raw.season == season) & (raw.player_id.isin(set(player_ids)))]
    sub = sub.sort_values(["player_id", "kickoff_time"])
    out: dict = {}
    for pid, g in sub.groupby("player_id", sort=False):
        out[pid] = (g["kickoff_time"].to_numpy(),
                    g[seq_stats].to_numpy(dtype="float32"))
    return out


def build_sequences(season: str, gw: int, *, window: int = SEQ_WINDOW,
                    raw: pd.DataFrame | None = None,
                    feat: pd.DataFrame | None = None) -> SequenceBundle:
    """For every player with a fixture in `(season, gw)`, build a `(window,
    n_stats)` raw-history tensor drawn only from gameweeks strictly before
    it, plus a static side-vector for the target fixture itself.

    Selection uses the last `window` rows for `(season, player_id)` whose
    `kickoff_time` is strictly earlier than the target fixture's own
    `kickoff_time` -- a `kickoff_time` bound, NOT a `gw < g` integer bound: a
    gameweek-integer comparison would admit an earlier fixture of the SAME
    double gameweek that had not yet been played at decision time. This is
    the single subtlest correctness point in this file.

    A double gameweek's earlier fixture contributes as its own timestep
    (never summed) -- `raw`/`player_gw.parquet` is already fixture-level, so
    this falls out of the selection rule above for free. A player with zero
    prior gameweeks (a first appearance) yields an all-padded row with an
    all-True mask -- it is NOT dropped; first appearances are a real and
    information-bearing case.
    """
    if raw is None:
        raw = pd.read_parquet(config.PROCESSED_DIR / "player_gw.parquet")
    if feat is None:
        feat = pd.read_parquet(config.PROCESSED_DIR / "features.parquet")

    raw = raw.sort_values(["season", "player_id", "kickoff_time"])
    seq_stats = [s for s in SEQ_STATS if s in raw.columns]
    static_cols = [c for c in STATIC_COLS if c in feat.columns]
    n_stats = len(seq_stats)

    targets = (feat[(feat.season == season) & (feat.gw == gw)]
              .sort_values(["player_id", "kickoff_time"]).reset_index(drop=True))

    histories = _player_histories(raw, season, seq_stats, targets.player_id.unique())

    per_player_arrays: list[np.ndarray] = []
    for row in targets.itertuples(index=False):
        kts, stats = histories.get(row.player_id, (np.array([]), np.zeros((0, n_stats), dtype="float32")))
        # kts is ascending; searchsorted(side="left") gives the count of
        # entries strictly less than the target's own kickoff_time.
        idx = int(np.searchsorted(kts, row.kickoff_time, side="left"))
        start = max(0, idx - window)
        per_player_arrays.append(stats[start:idx])

    x_seq, mask = _pad_and_mask(per_player_arrays, window, n_stats)
    x_static = torch.as_tensor(targets[static_cols].to_numpy(dtype="float32"))
    y = torch.as_tensor(targets["y_points"].to_numpy(dtype="float32"))
    minutes = torch.as_tensor(targets["y_minutes"].to_numpy(dtype="float32"))
    ids = targets[["season", "gw", "player_code", "fixture_id"]].reset_index(drop=True)

    return SequenceBundle(x_seq=x_seq, mask=mask, x_static=x_static,
                          y=y, minutes=minutes, ids=ids)
