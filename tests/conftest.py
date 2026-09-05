"""Shared pytest fixtures for the API test suite."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_api_state():
    """Reset api.main's module-level globals before and after every test so
    test order never leaks state, and seed a non-None artifact sentinel so
    _refresh's cold-start guard never reaches joblib.load(models/artifacts/
    xp_model.joblib) — that file is untracked and absent on a clean checkout.
    """
    import api.main as m
    m._state = m._initial_state()
    m._state["artifact"] = object()
    m._solve_cache.clear()
    yield
    m._state = m._initial_state()
    m._state["artifact"] = object()
    m._solve_cache.clear()
