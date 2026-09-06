"""Repository-wide regression gate for REL-01 (file-handle leaks) and REL-04
(actionable JSON-load failures).

The scanner is a plain module-level function so it can be driven both by the
real gate (against every tracked `.py` file) and by synthetic positive/negative
control snippets — a gate only ever exercised against a clean tree is a gate
that can silently stop working.

Note on this file's own wording: the scanner works on raw source TEXT (not an
AST), so any literal occurrence of the builtin call spelled out contiguously
in a comment, docstring or string constant would be indistinguishable from a
real violation and would flag this file against itself. Anywhere this module
needs to talk ABOUT that call shape, it is built via string concatenation
(`_OPEN_CALL`) rather than spelled out directly, so this file's own source
text never contains the literal 5-character trigger sequence.

Run:
  python -m pytest tests/test_reliability.py -q
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# The builtin call this gate hunts for, built via concatenation so this
# module's own source text never contains the trigger sequence contiguously.
_OPEN_CALL = "open" + "("
_READ_JSON_CALL = "read_json" + "("
_WHAT_KWARG = "what" + "="

# Matches a call to the builtin open function whose preceding character is
# either the start of the line or a character outside [A-Za-z0-9_.] — so an
# identifier merely *ending* in the word "open" (e.g. an FPL API test named
# "..._stay_open(") never matches, because the character right before the
# call there is "_", which IS in the excluded set.
_OPEN_CALL_RE = re.compile(r"(?:^|[^A-Za-z0-9_.])(" + re.escape(_OPEN_CALL) + r")")


def _find_bare_open_columns(line: str) -> list[int]:
    """0-based column offsets of bare (non-context-manager) open-call sites in
    `line`. A call is bare unless immediately preceded by the literal `with `
    (the `with` keyword plus a single space)."""
    cols = []
    for m in _OPEN_CALL_RE.finditer(line):
        start = m.start(1)  # index of the 'o' in the open call
        if line[max(0, start - 5):start] == "with ":
            continue
        cols.append(start)
    return cols


def scan_for_bare_file_handles(files: dict[str, str]) -> list[tuple[str, int, str]]:
    """`files`: mapping of path (str) -> full file text.

    Returns `(path, lineno, stripped_line)` findings for every bare open-call
    site, sorted by `(path, lineno)` so two runs over the same tree produce
    byte-identical output.
    """
    findings: list[tuple[str, int, str]] = []
    for path, text in files.items():
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _find_bare_open_columns(line):
                findings.append((path, lineno, line.strip()))
    findings.sort(key=lambda f: (f[0], f[1]))
    return findings


def _tracked_python_files() -> dict[str, str]:
    """Every `git ls-files '*.py'` path (relative to repo root) mapped to its
    on-disk text, read via a context manager (this scanner does not itself
    leak a handle while checking for leaks elsewhere)."""
    out = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=_REPO_ROOT,
        capture_output=True, text=True, check=True,
    )
    paths = [p for p in out.stdout.splitlines() if p]
    files: dict[str, str] = {}
    for rel in paths:
        with open(_REPO_ROOT / rel, encoding="utf-8") as f:
            files[rel] = f.read()
    return files


def _ruff(*args: str) -> subprocess.CompletedProcess:
    """Run ruff as a module of the currently-running interpreter (never a
    bare `ruff` resolved off `PATH`), scoped explicitly to this repository's
    own `ruff.toml` so a control file living outside the repository tree
    still evaluates under this project's `select` list."""
    return subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache",
         "--output-format", "concise",
         "--config", str(_REPO_ROOT / "ruff.toml"), *args],
        cwd=_REPO_ROOT, capture_output=True, text=True, check=False,
    )


def _ruff_inspected_python_files(*extra: str) -> list[str]:
    """Every `.py` path ruff actually inspects under the current exclusion
    configuration (plus any `extra` args), relative to `_REPO_ROOT`, sorted.

    `--show-files` also prints `ruff.toml` itself (a config artifact, not a
    linted Python file), so results are filtered to paths ending in `.py`.
    """
    result = _ruff("--show-files", *extra, ".")
    files = []
    for line in result.stdout.splitlines():
        if not line.endswith(".py"):
            continue
        files.append(str(Path(line).resolve().relative_to(_REPO_ROOT)))
    return sorted(files)


# --------------------------------------------------------------- positive/negative controls

def test_scanner_flags_a_bare_open_call():
    """Positive control: a synthetic snippet with a genuine violation yields
    exactly one finding — the gate is not vacuously passing."""
    snippet = {"synthetic/violation.py":
               f"def f():\n    data = json.load({_OPEN_CALL}path))\n"}
    findings = scan_for_bare_file_handles(snippet)
    assert len(findings) == 1, findings
    assert findings[0][0] == "synthetic/violation.py"
    assert findings[0][1] == 2


def test_scanner_ignores_identifier_ending_in_open():
    """Negative control: an identifier that merely ends in the word 'open'
    (the live `tests/test_api.py::test_unauthenticated_endpoints_stay_open`
    example) must never be flagged, nor must an already-guarded context-manager
    call."""
    snippet = {
        "synthetic/clean.py": (
            "def test_unauthenticated_endpoints_stay_open(monkeypatch, header):\n"
            "    pass\n"
            "\n"
            "def g(path):\n"
            f"    with {_OPEN_CALL}path) as f:\n"
            "        return f.read()\n"
        )
    }
    findings = scan_for_bare_file_handles(snippet)
    assert findings == [], findings


def test_scanner_sorts_findings_by_path_then_lineno():
    """Findings come back sorted by (path, lineno), regardless of dict
    insertion order — required for byte-identical output across runs."""
    snippet = {
        "z_second.py": f"x = {_OPEN_CALL}a)\ny = {_OPEN_CALL}b)\n",
        "a_first.py": f"x = {_OPEN_CALL}a)\n",
    }
    findings = scan_for_bare_file_handles(snippet)
    assert [(p, ln) for p, ln, _ in findings] == [
        ("a_first.py", 1),
        ("z_second.py", 1),
        ("z_second.py", 2),
    ]


# --------------------------------------------------------------- the real gate

def test_no_bare_file_handles_in_tracked_python():
    """The repository-wide gate: zero bare open-call sites anywhere in tracked
    Python. Prints the full sorted findings list on failure so a future
    violation is named, not merely counted."""
    findings = scan_for_bare_file_handles(_tracked_python_files())
    assert findings == [], (
        "bare file handle(s) found (path, lineno, line):\n"
        + "\n".join(f"  {p}:{ln}: {code}" for p, ln, code in findings)
    )


def test_every_tracked_read_json_call_has_a_what_label():
    """Every ops.jsonio read call site in tracked Python passes a `what`
    label, so no PayloadError message can be anonymous (REL-04).

    Excludes the reader's own definition line in `ops/jsonio.py` — that line
    names the `what` parameter itself (a required keyword-only argument with
    no default), so it has no `=` after the parameter name and is not a call
    site the requirement targets.
    """
    missing: list[tuple[str, int, str]] = []
    for path, text in sorted(_tracked_python_files().items()):
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("def "):
                continue
            if _READ_JSON_CALL in line and _WHAT_KWARG not in line:
                missing.append((path, lineno, stripped))
    assert missing == [], (
        "read_json call(s) missing a what label (path, lineno, line):\n"
        + "\n".join(f"  {p}:{ln}: {code}" for p, ln, code in missing)
    )


# ------------------------------------------------------------- lint-coverage gate (CR-01)

def test_ruff_detects_an_undefined_name(tmp_path):
    """Positive control for the *rule*: the configured `select` list really
    does report the CR-01 defect class (a name used without ever being
    imported) as F821, rather than the coverage gate below passing because
    ruff never found anything to say."""
    target = tmp_path / "undefined_name.py"
    target.write_text("def f():\n    return json.dumps({})\n")
    result = _ruff(str(target))
    assert result.returncode != 0, result.stdout
    assert "F821" in result.stdout, result.stdout


def test_ruff_reports_nothing_for_a_clean_module(tmp_path):
    """Negative control: the same module with the missing import restored
    exits 0 and reports no finding."""
    target = tmp_path / "clean_module.py"
    target.write_text("import json\n\n\ndef f():\n    return json.dumps({})\n")
    result = _ruff(str(target))
    assert result.returncode == 0, result.stdout
    assert "F821" not in result.stdout, result.stdout


def test_ruff_check_covers_every_tracked_python_file():
    """The real gate: ruff's inspected file set must exactly equal the
    tracked Python file set. Both collections must be non-empty first — an
    empty scan set would otherwise pass this comparison vacuously."""
    inspected = set(_ruff_inspected_python_files())
    tracked = set(_tracked_python_files().keys())
    assert inspected, "ruff inspected zero python files — vacuous gate"
    assert tracked, "git ls-files '*.py' returned zero files — vacuous gate"
    missing_from_lint = sorted(tracked - inspected)
    extra_in_lint = sorted(inspected - tracked)
    assert inspected == tracked, (
        "lint gate coverage mismatch:\n"
        f"  tracked but invisible to the lint gate: {missing_from_lint}\n"
        f"  inspected by the lint gate but untracked: {extra_in_lint}"
    )


def test_coverage_gate_notices_a_reinstated_blanket_exclude():
    """Positive control for the *gate*: passing --exclude e2e must remove
    e2e/scripts/capture_fixtures.py from the inspected set, proving the
    coverage gate reads a real exclusion rather than returning a constant —
    so it will actually fire if someone re-adds a blanket entry to
    ruff.toml."""
    with_exclude = _ruff_inspected_python_files("--exclude", "e2e")
    without_exclude = _ruff_inspected_python_files()
    assert "e2e/scripts/capture_fixtures.py" not in with_exclude
    assert "e2e/scripts/capture_fixtures.py" in without_exclude
