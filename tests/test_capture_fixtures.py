"""Behavioural half of the CR-01 regression gate for
`e2e/scripts/capture_fixtures.py`.

The static half — the lint-coverage gate that makes ruff's `F` rule set (in
particular F821, undefined name) actually see this file — lives in
`tests/test_reliability.py`. This module proves the script actually imports
and that its read-only CLI path runs.

Neither half may invoke `_capture`: it issues live HTTP requests, loads
`models/artifacts/xp_model.joblib`, and rewrites the immutable v1 fixture
set (D-08).
"""
from __future__ import annotations

import dis
import importlib.util
import subprocess
import types
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PATH = _REPO_ROOT / "e2e" / "scripts" / "capture_fixtures.py"


@lru_cache(maxsize=1)
def _load_capture_fixtures_module():
    """Load `e2e/scripts/capture_fixtures.py` by file path, not by an
    `import` statement — `e2e/scripts/` is not a package (no
    `__init__.py`). Cached so the module import (which pulls in
    `predict.live`, not free) only happens once per session."""
    spec = importlib.util.spec_from_file_location(
        "_capture_fixtures_under_test", _SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capture_fixtures_module_imports():
    """Catches an import-time break — a removed stdlib import used at
    module level, a renamed `predict.export` symbol — that no other test in
    this repository covers today."""
    module = _load_capture_fixtures_module()
    assert callable(module.main)
    assert callable(module._capture)
    assert callable(module._verify)


def _load_global_names(code: types.CodeType) -> set[str]:
    """Every `LOAD_GLOBAL` argval reachable from `code`, recursing into any
    `co_consts` entry that is itself a code object — so a nested function
    (such as `_verify`'s `require_file`) is covered too."""
    names: set[str] = set()
    for instr in dis.get_instructions(code):
        if instr.opname == "LOAD_GLOBAL":
            names.add(instr.argval)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            names |= _load_global_names(const)
    return names


def test_capture_path_loads_no_undefined_global():
    """The ruff-independent backstop, and the direct runtime-object form of
    CR-01. `LOAD_GLOBAL` is the precise opcode here: function-local imports
    (`joblib`, `requests` inside `_capture`) compile to `LOAD_FAST`, and
    attribute names (`loads`, `to_json`, `relative_to`) never appear as
    `LOAD_GLOBAL` argvals, so this check has no false positives on the
    current source — it reported exactly `json` against the pre-fix file
    and exactly nothing against the fixed one."""
    import builtins

    module = _load_capture_fixtures_module()
    unresolved: dict[str, list[str]] = {}
    for fn_name in ("_capture", "_verify", "main"):
        fn = getattr(module, fn_name)
        names = _load_global_names(fn.__code__)
        missing = sorted(
            n for n in names
            if n not in module.__dict__ and not hasattr(builtins, n)
        )
        if missing:
            unresolved[fn_name] = missing
    assert unresolved == {}, (
        "undefined global name(s) on the capture path (function: names):\n"
        + "\n".join(
            f"  {fn}: {names}" for fn, names in sorted(unresolved.items())
        )
    )


def test_verify_path_returns_zero(capsys):
    """Exercises the argparse wiring and the whole read path against the
    committed v1 set."""
    module = _load_capture_fixtures_module()
    rc = module.main(["--verify"])
    captured = capsys.readouterr()
    assert rc == 0, captured.out
    assert "[verify] OK:" in captured.out


def test_the_gates_leave_the_frozen_fixture_set_untouched():
    """After the tests above, the immutable v1 fixture set must be
    byte-identical and gain no untracked file. `status --porcelain` (rather
    than `diff --quiet`) also catches an added untracked file under the
    fixture tree, which is the failure mode that would matter if someone
    later mistakenly wired the write path into a test."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "e2e/fixtures"],
        cwd=_REPO_ROOT, capture_output=True, text=True, check=True,
    )
    assert result.stdout == "", result.stdout
