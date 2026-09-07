"""Mount-branch coverage for all three api.main serving modes (Phase 7,
CUT-01): production react (FPL_FRONTEND=react), the untouched production
default (FPL_FRONTEND absent or "vanilla"), and precedence against the
existing E2E fixture-mode branch (FPL_FIXTURE_DIR set). Sibling to
tests/test_fixture_mode.py -- copies its importlib.reload + monkeypatch +
teardown-reload discipline verbatim (each test performs its own setup and
teardown reload inline, mirroring test_unset_env_leaves_a_single_root_mount);
does not modify that file."""
from __future__ import annotations

import importlib
from pathlib import Path

from starlette.routing import Mount

import config

FIXTURE_DIR = config.ROOT / "e2e" / "fixtures" / "v1" / "normal"


def _mount_names(app) -> list[str]:
    return [route.name for route in app.routes if isinstance(route, Mount)]


def _mount_directory(app, name: str) -> Path:
    """The resolved on-disk directory a named Mount serves. Asserting this,
    not just the mount's name, is what catches the react branch pointing at
    the wrong directory -- the single most consequential mistake this seam
    can make."""
    for route in app.routes:
        if isinstance(route, Mount) and route.name == name:
            return Path(route.app.directory)
    raise AssertionError(f"no mount named {name!r} in {app.routes!r}")


def test_react_mode_mounts_live_data_then_dist(monkeypatch):
    """FPL_FRONTEND=react, no fixture var: two Mounts, "data" then "site" in
    registration order; "site" resolves to frontend/dist and "data" to the
    live web/data directory."""
    import api.main as m

    monkeypatch.setenv("FPL_FRONTEND", "react")
    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    reloaded = importlib.reload(m)

    assert _mount_names(reloaded.app) == ["data", "site"]
    assert _mount_directory(reloaded.app, "data") == config.ROOT / "web" / "data"
    assert _mount_directory(reloaded.app, "site") == config.ROOT / "frontend" / "dist"

    monkeypatch.delenv("FPL_FRONTEND", raising=False)
    importlib.reload(reloaded)


def test_unset_frontend_env_leaves_the_production_default(monkeypatch):
    """FPL_FRONTEND absent: exactly one Mount, "site", serving web/ -- the
    pre-existing production default, unchanged by this seam."""
    import api.main as m

    monkeypatch.delenv("FPL_FRONTEND", raising=False)
    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    reloaded = importlib.reload(m)

    assert _mount_names(reloaded.app) == ["site"]
    assert _mount_directory(reloaded.app, "site") == config.ROOT / "web"

    importlib.reload(reloaded)


def test_vanilla_literal_value_behaves_identically_to_unset(monkeypatch):
    """Only the literal value "react" activates the branch -- FPL_FRONTEND=
    vanilla must behave exactly like the unset default."""
    import api.main as m

    monkeypatch.setenv("FPL_FRONTEND", "vanilla")
    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    reloaded = importlib.reload(m)

    assert _mount_names(reloaded.app) == ["site"]
    assert _mount_directory(reloaded.app, "site") == config.ROOT / "web"

    monkeypatch.delenv("FPL_FRONTEND", raising=False)
    importlib.reload(reloaded)


def test_fixture_mode_wins_over_react_mode(monkeypatch):
    """With both FPL_FIXTURE_DIR and FPL_FRONTEND=react set, the fixture
    branch wins -- two mounts named "fixture-data" then "site", and the live
    /data mount never appears. Regression guard keeping the E2E suite's
    topology intact."""
    import api.main as m

    monkeypatch.setenv("FPL_FIXTURE_DIR", str(FIXTURE_DIR))
    monkeypatch.setenv("FPL_FRONTEND", "react")
    reloaded = importlib.reload(m)

    assert _mount_names(reloaded.app) == ["fixture-data", "site"]
    assert "data" not in _mount_names(reloaded.app)

    monkeypatch.delenv("FPL_FIXTURE_DIR", raising=False)
    monkeypatch.delenv("FPL_FRONTEND", raising=False)
    importlib.reload(reloaded)
