"""Phase 10 plan 10-10: the D-12 model-class bracket.

`registry` is the single seam `models/train.py::train_position` calls
through to swap the stage-2 (conditional-points) regressor by name; `gate`
is the D-15 cheap validation-split gate that decides which candidate earns
a full 6-season walk-forward. See `registry.py`'s module docstring for the
one-swap-seam contract.
"""
from __future__ import annotations
