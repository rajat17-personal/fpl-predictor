"""Repository-wide regression gate for REL-01 (file-handle leaks) and REL-04
(actionable JSON-load failures).

The scanner is a plain module-level function so it can be driven both by the
real gate (against every tracked `.py` file) and by synthetic positive/negative
control snippets — a gate only ever exercised against a clean tree is a gate
that can silently stop working.

Run:
  python -m pytest tests/test_reliability.py -q
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Matches a call to the builtin `open(` whose preceding character is either the
# start of the line or a character outside [A-Za-z0-9_.] — so an identifier
# merely *ending* in the word "open" (e.g. `..._stay_open(`) never matches,
# because the character right before "open(" there is "_", which IS in the
# excluded set.
_OPEN_CALL_RE = re.compile(r"(?:^|[^A-Za-z0-9_.])(open\()")


def _find_bare_open_columns(line: str) -> list[int]:
    """0-based column offsets of bare (non-context-manager) `open(` calls in
    `line`. A call is bare unless immediately preceded by the literal `with `
    (the `with` keyword plus a single space)."""
    cols = []
    for m in _OPEN_CALL_RE.finditer(line):
        start = m.start(1)  # index of the 'o' in 'open('
        if line[max(0, start - 5):start] == "with ":
            continue
        cols.append(start)
    return cols


def scan_for_bare_file_handles(files: dict[str, str]) -> list[tuple[str, int, str]]:
    """`files`: mapping of path (str) -> full file text.

    Returns `(path, lineno, stripped_line)` findings for every bare `open(`
    call, sorted by `(path, lineno)` so two runs over the same tree produce
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


# --------------------------------------------------------------- positive/negative controls

def test_scanner_flags_a_bare_open_call():
    """Positive control: a synthetic snippet with a genuine violation yields
    exactly one finding — the gate is not vacuously passing."""
    snippet = {"synthetic/violation.py": "def f():\n    data = json.load(open(path))\n"}
    findings = scan_for_bare_file_handles(snippet)
    assert len(findings) == 1, findings
    assert findings[0][0] == "synthetic/violation.py"
    assert findings[0][1] == 2


def test_scanner_ignores_identifier_ending_in_open():
    """Negative control: an identifier that merely ends in the word 'open'
    (the live `tests/test_api.py::test_unauthenticated_endpoints_stay_open`
    example) must never be flagged, nor must an already-guarded `with open(`."""
    snippet = {
        "synthetic/clean.py": (
            "def test_unauthenticated_endpoints_stay_open(monkeypatch, header):\n"
            "    pass\n"
            "\n"
            "def g(path):\n"
            "    with open(path) as f:\n"
            "        return f.read()\n"
        )
    }
    findings = scan_for_bare_file_handles(snippet)
    assert findings == [], findings


def test_scanner_sorts_findings_by_path_then_lineno():
    """Findings come back sorted by (path, lineno), regardless of dict
    insertion order — required for byte-identical output across runs."""
    snippet = {
        "z_second.py": "x = open(a)\ny = open(b)\n",
        "a_first.py": "x = open(a)\n",
    }
    findings = scan_for_bare_file_handles(snippet)
    assert [(p, ln) for p, ln, _ in findings] == [
        ("a_first.py", 1),
        ("z_second.py", 1),
        ("z_second.py", 2),
    ]


# --------------------------------------------------------------- the real gate

def test_no_bare_file_handles_in_tracked_python():
    """The repository-wide gate: zero bare `open(` calls anywhere in tracked
    Python. Prints the full sorted findings list on failure so a future
    violation is named, not merely counted."""
    findings = scan_for_bare_file_handles(_tracked_python_files())
    assert findings == [], (
        "bare file handle(s) found (path, lineno, line):\n"
        + "\n".join(f"  {p}:{ln}: {code}" for p, ln, code in findings)
    )


def test_every_tracked_read_json_call_has_a_what_label():
    """Every `read_json(` CALL site in tracked Python passes a `what=` label,
    so no PayloadError message can be anonymous (REL-04).

    Excludes the function's own definition line (`def read_json(path, *, what:
    str, ...)`, in `ops/jsonio.py`) — that line names its `what` PARAMETER,
    which has no default (`what: str`, not `what=...`), so it is not a call
    site the requirement targets and must not be flagged as one.
    """
    missing: list[tuple[str, int, str]] = []
    for path, text in sorted(_tracked_python_files().items()):
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("def "):
                continue
            if "read_json(" in line and "what=" not in line:
                missing.append((path, lineno, stripped))
    assert missing == [], (
        "read_json( call(s) missing a what= label (path, lineno, line):\n"
        + "\n".join(f"  {p}:{ln}: {code}" for p, ln, code in missing)
    )
