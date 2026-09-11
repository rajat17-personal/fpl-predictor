---
phase: quick-260911-8as
plan: 01
subsystem: infra
tags: [uv, pip-compile, lxml, beautifulsoup4, html5lib, certifi, pandas, read_html, pytest]

requires: []
provides:
  - "Direct requirements.in pins for lxml, beautifulsoup4, html5lib, certifi (the pandas.read_html scraping stack for data/transfermarkt.py and data/fbref.py)"
  - "Recompiled, hash-locked requirements.txt and requirements-dev.txt with a purely additive diff"
  - "A CI-visible pytest gate (tests/test_transfermarkt.py) proving both pandas.read_html parser legs (lxml, bs4+html5lib) and the requests-to-certifi CA bundle link"
affects: [data-pipeline, ci, transfermarkt-scraping, fbref-scraping]

actuals:
  tokens: 10318
  tasks: 3
  commits: 2

tech-stack:
  added: [lxml, beautifulsoup4, html5lib]
  patterns: ["Direct-pin packages reached only through a third-party library's internal dispatch (pandas.read_html flavor resolution), not imported by name anywhere in the repo, with a heavy explanatory comment block in requirements.in warning against removal-as-unused"]

key-files:
  created: []
  modified:
    - requirements.in
    - requirements.txt
    - requirements-dev.txt
    - tests/test_transfermarkt.py

key-decisions:
  - "Human approved all four packages (verbatim: \"approve all four\") via the Task 1 blocking-human package-legitimacy gate; live-registry re-verification found zero drift from the installed versions (lxml 6.1.3, beautifulsoup4 4.15.0, html5lib 1.1, certifi 2025.11.12)."
  - "Placed all four pins in requirements.in (not requirements-dev.in) because data/transfermarkt.py and data/fbref.py are production data-pipeline modules, module-level-imported by data/build_table.py."
  - "Used version ranges (lxml>=6.1,<7, beautifulsoup4>=4.13, html5lib>=1.1, certifi>=2025.11.12) matching the surrounding production dependencies' style, not exact pins."
  - "requirements-rl.txt and requirements-experiments.txt deliberately NOT recompiled (their .in files carry no -r requirements.in line), verified safe via the lockfile-layering invariant check (0 conflicts in shared pins across all four locks)."

requirements-completed: [DEPLOCK-01]

coverage:
  - id: D1
    description: "Four direct pins (lxml, beautifulsoup4, html5lib, certifi) added to requirements.in with explanatory comments, human-approved via package-legitimacy gate"
    requirement: DEPLOCK-01
    verification:
      - kind: unit
        ref: "git diff requirements.in shows only the new documented section"
        status: pass
    human_judgment: false
  - id: D2
    description: "requirements.txt and requirements-dev.txt recompiled with hashes, additive diff only (zero non-comment line removals)"
    requirement: DEPLOCK-01
    verification:
      - kind: unit
        ref: "Task 2 Gate A (additive-only diff check) + Gate B (hash presence check)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dockerfile's compiler-free builder stage can still install lxml as a prebuilt cp314 manylinux wheel"
    requirement: DEPLOCK-01
    verification:
      - kind: unit
        ref: "Task 2 Gate C (pip download --only-binary=:all: for lxml==6.1.3 on manylinux_2_28_x86_64)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both pandas.read_html parser legs (lxml, bs4+html5lib) and the requests-to-certifi CA bundle link work end-to-end against a from-lockfile install, including the real data.transfermarkt.parse_injury_table call site"
    requirement: DEPLOCK-01
    verification:
      - kind: unit
        ref: "Task 2 Gate E (end-to-end script)"
        status: pass
      - kind: unit
        ref: "tests/test_transfermarkt.py#test_read_html_lxml_flavor_is_installed"
        status: pass
      - kind: unit
        ref: "tests/test_transfermarkt.py#test_read_html_bs4_flavor_is_installed"
        status: pass
      - kind: unit
        ref: "tests/test_transfermarkt.py#test_requests_ca_bundle_resolves_to_certifi"
        status: pass
    human_judgment: false
  - id: D5
    description: "The bs4 parser-leg gate is a real regression test, demonstrated to fail when html5lib is missing (RED-proof)"
    requirement: DEPLOCK-01
    verification:
      - kind: unit
        ref: "RED-proof script (sys.modules['html5lib'] = None, pd.read_html(flavor='bs4') raises ImportError)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full test suite green, lockfile layering invariant holds across all four lockfiles"
    requirement: DEPLOCK-01
    verification:
      - kind: unit
        ref: "python -m pytest (326 passed, 1 skipped, pre-existing)"
        status: pass
      - kind: unit
        ref: "Task 3 Gate C (lockfile layering invariant script)"
        status: pass
    human_judgment: false

duration: ~20min (Tasks 2-3; Task 1's gate was resolved in a prior session)
completed: 2026-09-11
status: complete
---

# Quick Task 260911-8as: Lock the Transfermarkt/FBref scraping stack Summary

**Direct requirements.in pins for lxml/beautifulsoup4/html5lib/certifi, recompiled hash-locked requirements.txt+requirements-dev.txt (additive-only diff), and a CI-visible pytest gate proving both pandas.read_html parser legs plus the requests-to-certifi CA bundle link — closing the exact crash sequence recorded in WINDOWS.md entries 4-5.**

## Performance

- **Tasks:** 3/3 complete (Task 1 was a blocking-human gate resolved before this continuation)
- **Files modified:** 4 (requirements.in, requirements.txt, requirements-dev.txt, tests/test_transfermarkt.py)
- **Commits:** 2 (Task 1 produced no file changes — its only output is the recorded approval below)

## Task 1: Package-legitimacy gate

**Verbatim human approval:** "approve all four" — all four packages (lxml, beautifulsoup4, html5lib, certifi) approved as direct pins in requirements.in, entering the shipped Docker image per the plan.

**Registry re-verification (done in the prior session, reused here per resume instructions — not re-fetched):**
- `lxml` 6.1.3 — PyPI latest matches installed version.
- `beautifulsoup4` 4.15.0 — matches installed version; the `bs4` import-name mismatch was explicitly called out as the legitimate, decades-old case (not a typosquat).
- `html5lib` 1.1 — matches installed version; dormant-but-official project.
- `certifi` — installed 2025.11.12; live PyPI latest was 2026.7.22 at plan time. The floor pin `>=2025.11.12` resolves to the newer version at compile time — expected and not drift from the approved package identity, only its version.

No file changes in Task 1 itself — it is a pure decision gate. The approval is recorded here and in STATE.md's Decisions section per the standard package-legitimacy-gate pattern (Phase 01, 02, 05, 09, 10 precedent).

## Task 2: Pin the four packages and recompile both affected lockfiles

**Commit:** `7628f43` (feat)

- Added a new documented section to `requirements.in`: `lxml>=6.1,<7`, `beautifulsoup4>=4.13`, `html5lib>=1.1`, `certifi>=2025.11.12`, with a comment block explaining the pandas.read_html dispatch mechanism, the WINDOWS.md incident this closes, and a do-not-remove-as-unused warning.
- Recompiled `requirements.txt` via `uv pip compile requirements.in --generate-hashes --python-version 3.14 -o requirements.txt`. Diff: **199 added lines, 0 non-comment removed lines** (Gate A — additive-only, no existing pin moved).
- Recompiled `requirements-dev.txt` via `uv pip compile requirements-dev.in --generate-hashes --python-version 3.14 -c requirements.txt -o requirements-dev.txt`. Diff: **207 added lines, 0 non-comment removed lines**.
- Gate B: `lxml`, `beautifulsoup4`, `html5lib`, `certifi`, `soupsieve`, `webencodings` all present and hash-locked in both files.
- Gate C: a prebuilt `lxml-6.1.3-cp314-cp314-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl` downloads successfully via `pip download --only-binary=:all:` targeting the Docker builder's platform (`manylinux_2_28_x86_64`, cp314) — Dockerfile's compiler-free builder stage (D-03) stays valid.
- Gate D: installed non-destructively via `uv pip install --require-hashes -r <file> --python <conda-env-python>` (one file per invocation — the `uv pip sync` verb that caused the WINDOWS-5 incident was never used). Both installs reported "Checked N packages" with nothing new to fetch (already-installed versions matched the recompiled pins exactly).
- Gate E (end-to-end): `pd.read_html(..., flavor="lxml")` and `flavor="bs4"` both parsed a 1x2 table correctly; `requests.certs.where() == certifi.where()` and the bundle is >100KB; `data.transfermarkt.parse_injury_table` parsed a real injury table end-to-end. All against the from-lockfile install.

## Task 3: Permanent CI gate + full suite

**Commit:** `b56b728` (test)

- Extended `tests/test_transfermarkt.py` with three new tests: `test_read_html_lxml_flavor_is_installed`, `test_read_html_bs4_flavor_is_installed`, `test_requests_ca_bundle_resolves_to_certifi`. Reworded the module docstring (it previously claimed "All three tests run with zero network access," which is now stale given six tests).
- **RED-proof observed:** hiding `html5lib` from `sys.modules` and calling `pd.read_html(..., flavor="bs4")` raised:
  > `` `Import html5lib` failed.  Use pip or conda to install the html5lib package. ``
  This confirms the bs4-leg test is a genuine regression gate, not a test that would pass regardless of whether html5lib is installed.
- Lockfile layering invariant (Gate C): checked shared pins across all four lockfiles against `requirements.txt` — `requirements-dev.txt` (38 shared, 0 conflicts), `requirements-rl.txt` (3 shared, 0 conflicts), `requirements-experiments.txt` (6 shared, 0 conflicts). Confirms `requirements-rl.txt` and `requirements-experiments.txt` remain valid uncompiled.
- Full suite (Gate D): `python -m pytest` → **326 passed, 1 skipped** (pre-existing skip, unrelated to this change), 283.85s.
- `git diff` confirms `Dockerfile` and every `.github/workflows/*.yml` file are byte-identical to before this task (unmodified, as required).

## Task Commits

1. **Task 1: Package-legitimacy gate** — no commit (pure decision gate; approval recorded above and in STATE.md)
2. **Task 2: Pin the four packages and recompile both affected lockfiles** — `7628f43` (feat)
3. **Task 3: Make both parser legs a permanent CI gate, then prove the suite and the lock layering** — `b56b728` (test)

## Files Created/Modified

- `requirements.in` — added a documented section with the four new direct pins
- `requirements.txt` — recompiled, hash-locked, additive diff (+199/-0 non-comment lines)
- `requirements-dev.txt` — recompiled, hash-locked, additive diff (+207/-0 non-comment lines)
- `tests/test_transfermarkt.py` — three new dependency-availability regression tests + reworded docstring

## Decisions Made

- All four packages approved via the blocking-human package-legitimacy gate, verbatim answer "approve all four" — see key-decisions and Task 1 section above.
- Pins placed in `requirements.in`, not `requirements-dev.in` — the affected modules (`data/transfermarkt.py`, `data/fbref.py`) are production data-pipeline code, module-level-imported by `data/build_table.py`.
- `requirements-rl.txt` and `requirements-experiments.txt` were NOT recompiled — their `.in` files have no `-r requirements.in` line, so they cannot gain these packages; the lockfile-layering invariant check confirms this leaves them valid.

## Deviations from Plan

**One minor Rule 1 fix, not present in the plan's literal verify command:**

**1. [Rule 1 - Bug] `pd.read_html` raised `FileNotFoundError` on a bare HTML string in the new tests**

- **Found during:** Task 3, first test run
- **Issue:** pandas 3.0.5's `read_html` treats a bare string argument as a filesystem path/URL if it doesn't look like a `file`-like object, raising `FileNotFoundError: [Errno 2] No such file or directory: <table>...` instead of parsing it as literal HTML. This differs from the plan's own Task 2 Gate E verify script, which already wrapped its HTML in `io.StringIO(...)`.
- **Fix:** Wrapped `_ONE_ROW_TABLE_HTML` in `io.StringIO(...)` at each `pd.read_html` call site in the two new tests, matching the pattern the plan itself used in Task 2's verify block.
- **Files modified:** `tests/test_transfermarkt.py`
- **Verification:** Both tests pass; full suite green.
- **Committed in:** `b56b728` (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial — a two-line fix consistent with the plan's own verify-script convention. No scope creep.

## WINDOWS.md ledger note

Per the plan's `<output>` instructions: this plan closes the *lockfile-gap* half of the WINDOWS.md entry 5 incident (the ad-hoc installs — certifi, html5lib, beautifulsoup4, lxml — now have a permanent home in `requirements.in`/`requirements.txt`/`requirements-dev.txt`, and a CI gate proves both parser legs stay installable from a lockfile-only rebuild). It does **not** close the *standing rule* half — "never run `uv pip sync` against the shared conda env" remains a live operational rule independent of this plan, since a future developer could still run `sync` against a different lockfile and strip the env again. Left as a developer decision whether to mark WINDOWS.md entry 5 as `fixed` or leave it `open` pending some future guard (e.g., a wrapper script or CI check that forbids `sync`).

## Issues Encountered

None beyond the one documented deviation above.

## Next Phase Readiness

- The Transfermarkt scraping stack (and FBref's shared `read_html` call site) is now fully covered by the project lockfiles and by a CI-visible regression test — a repeat of the WINDOWS.md entries 4-5 incident is not possible from a from-lockfile-only rebuild.
- No blockers introduced. `requirements-rl.txt` and `requirements-experiments.txt` remain untouched and valid.
- The daily/weekly cron pipeline, Docker builder stage, and every GitHub Actions workflow continue to install `requirements.txt`/`requirements-dev.txt` unchanged — this plan required zero edits to `Dockerfile` or `.github/workflows/*.yml`.

## Self-Check: PASSED

All modified/created files verified present on disk; both task commit hashes (`7628f43`, `b56b728`) verified present in `git log --oneline --all`.

---
*Phase: quick-260911-8as*
*Completed: 2026-09-11*
