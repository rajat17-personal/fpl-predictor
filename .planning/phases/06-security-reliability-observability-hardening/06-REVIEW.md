---
phase: 06-security-reliability-observability-hardening
reviewed: 2026-09-05T00:00:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - .env.example
  - .github/workflows/daily.yml
  - .github/workflows/weekly.yml
  - .gitignore
  - README.md
  - api/main.py
  - config.py
  - data/id_map.py
  - data/live_history.py
  - data/snapshot.py
  - e2e/scripts/capture_fixtures.py
  - models/intervals.py
  - models/price.py
  - ops/__init__.py
  - ops/jsonio.py
  - ops/jsonlog.py
  - ops/notify.py
  - ops/payloads.py
  - predict/digest.py
  - predict/export.py
  - predict/live.py
  - predict/scoreboard.py
  - scripts/daily.sh
  - scripts/preflight.sh
  - scripts/verify_hardening.sh
  - scripts/weekly.sh
  - tests/test_api.py
  - tests/test_api_hardening.py
  - tests/test_cron.py
  - tests/test_fixture_mode.py
  - tests/test_obs.py
  - tests/test_payloads.py
  - tests/test_product.py
  - tests/test_reliability.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-09-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found

## Summary

Phase 6's `ops/` package (fail-loud JSON I/O, structured logging with secret
redaction, alerting), the CORS allowlist, the bounded LRU+TTL solve cache, and
the cron retry/backoff + `.env` hardening are all internally consistent and
well covered by `tests/test_reliability.py`, `tests/test_cron.py`,
`tests/test_api_hardening.py`, `tests/test_obs.py` and `tests/test_payloads.py`
— the concurrency, TTL, redaction and CORS-wildcard-refusal claims made in
those tests were traced against the implementation and hold up.

One outright crash was found in a script this milestone did not add pytest
coverage for (`e2e/scripts/capture_fixtures.py`), confirmed independently with
`pyflakes` and a manual read: `_capture()` uses `json.loads(...)` but the
module never imports `json`, so the fixture-capture path (the tool's entire
purpose, per its own docstring/`Run:` block) raises `NameError` on every
invocation that isn't `--verify`. Several other, smaller correctness and
robustness gaps were found by tracing edge cases through `predict/digest.py`,
`predict/scoreboard.py`, and the new `ops.jsonio.write_json` atomic-write path
(which silently changes on-disk file permissions for every JSON artifact it
touches, a side effect of `tempfile`'s default mode that is easy to miss
because the currently-committed `web/data/*.json` files predate this code
path and still show their old, git-checkout permissions).

## Critical Issues

### CR-01: `capture_fixtures.py` crashes on every capture run — `json` is used but never imported

**File:** `e2e/scripts/capture_fixtures.py:133`
**Issue:** `_capture()` calls `json.loads(pool.to_json(orient="records"))`, but
the module's import block (lines 16–32) imports only `argparse`, `datetime`,
`shutil`, `sys`, `pathlib.Path`, `config`, `ops.jsonio`, and symbols from
`predict.export`/`predict.live` — never `json`. Running the script exactly as
documented in its own module docstring (`python e2e/scripts/capture_fixtures.py`,
i.e. the default, non-`--verify` action) raises `NameError: name 'json' is not
defined` and aborts before any fixture file is written. Confirmed independently
with `python -m pyflakes e2e/scripts/capture_fixtures.py`:
```
e2e/scripts/capture_fixtures.py:133:19: undefined name 'json'
```
This is the tool that produces/refreshes the immutable v1 E2E fixture set the
Playwright suite and `tests/test_fixture_mode.py`/`tests/test_payloads.py`
depend on — it currently cannot be re-run to capture a v2 set or repair v1
without first fixing this import.
**Fix:**
```python
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path
```

## Warnings

### WR-01: `predict/digest.py` — a genuinely 0%-owned player can never be flagged as the differential pick

**File:** `predict/digest.py:41`
**Issue:**
```python
diff = next((r for r in table
             if (r.get("ownership") or 100) < DIFFERENTIAL_MAX_OWN
             and r.get("status") == "a"), None)
```
`r.get("ownership") or 100` treats an ownership of exactly `0.0` (a brand-new
or newly-promoted player nobody has picked yet — the *most* extreme possible
differential) as falsy and substitutes `100`, which then fails the
`< DIFFERENTIAL_MAX_OWN` (10.0) test. Such a player is silently excluded from
ever being the week's "Differential" callout, which is precisely the class of
player that feature exists to surface. Verified directly:
```python
>>> r = {"ownership": 0.0, "status": "a"}
>>> (r.get("ownership") or 100) < 10.0
False
```
Not caught by `tests/test_product.py::test_digest_render` because its fixture
data uses ownership values `5.0..12.0`, never `0.0`.
**Fix:** Use an explicit `None`-check instead of `or`:
```python
diff = next((r for r in table
             if (r.get("ownership") if r.get("ownership") is not None else 100) < DIFFERENTIAL_MAX_OWN
             and r.get("status") == "a"), None)
```

### WR-02: `ops.jsonio.write_json` silently narrows every JSON artifact it writes to mode 0600

**File:** `ops/jsonio.py:47-65`
**Issue:** `write_json` writes via `tempfile.NamedTemporaryFile(..., delete=False, ...)`
and then `os.replace`s it into place. `tempfile.NamedTemporaryFile` creates its
backing file with mode `0600` regardless of the process umask (verified on
this box: `oct(os.stat(...).st_mode) == '0o100600'` even with umask `022`), and
`os.replace` preserves the *source* inode's permission bits, not the
destination path's previous ones. Every caller of `write_json` — including
`predict/export.py` (`web/data/{meta,xp_table,captains,squad,fixtures,chips,
standings,leaders}.json`, `web/data/history/gw{N}.json`), `predict/scoreboard.py`
(`web/data/scoreboard.json`), `models/price.py` (`web/data/watchlist.json`),
`models/intervals.py` (`models/artifacts/intervals.json`), and
`e2e/scripts/capture_fixtures.py` — now produces files world-unreadable to any
process running as a different OS user, silently. The currently-committed
`web/data/*.json` files still show `rw-r--r--` (644) only because they were
last written before this atomic-write path existed / were restored by a plain
`git checkout`, which does not track this permission bit; the very next
`predict.export`/`predict.scoreboard`/`models.price` run on this box will drop
them to `rw-------`. Today this is masked because the API and the cron both
run as the same OS user (per README, "one process serves both the site and
the API"), but it silently breaks the moment any other reader (a reverse
proxy, a separate static-file server per README's documented two-process
alternative, a backup/log-shipping agent, a different deploy user) reads these
files directly off disk instead of through the FastAPI process that wrote
them.
**Fix:** Set an explicit, conventional mode on the temp file before the
replace (or `os.chmod` after it):
```python
tmp = tempfile.NamedTemporaryFile(
    mode="w", dir=path.parent, delete=False, suffix=".tmp", encoding="utf-8"
)
try:
    with tmp:
        json.dump(obj, tmp, indent=indent)
    os.chmod(tmp.name, 0o644)
    os.replace(tmp.name, path)
except Exception:
    ...
```

### WR-03: `predict/scoreboard.py::score_gw` can raise an uncaught `IndexError` on an empty merge

**File:** `predict/scoreboard.py:39-63`
**Issue:**
```python
pred = pd.DataFrame(frozen["players"]).merge(actuals, on="player_id", how="inner")
...
cap = pred.sort_values("xp_capt", ascending=False).iloc[0]
...
best = pred.sort_values("actual", ascending=False).iloc[0]
```
If the frozen prediction file's `player_id`s and the live `/event/{gw}/live/`
actuals share zero rows after the inner merge (e.g. an `id_map`/season
transition, a corrupted/edited frozen file, or FPL reassigning element ids
between the export and the score run), `pred` is empty and both `.iloc[0]`
calls raise `IndexError`. `update()` in the same module has no `try/except`
around `score_gw`, so this propagates straight out of the post-GW cron
(`predict.scoreboard`, run from `scripts/daily.sh`), and — unlike every other
fail-loud path this phase added — surfaces as a bare Python traceback with no
`PayloadError`-style actionable message naming the mismatched gameweek.
**Fix:** Guard the empty case explicitly before computing the entry, e.g.:
```python
if pred.empty:
    raise PayloadError(
        f"scoreboard: frozen gw{frozen['gw']} predictions share no player_id "
        "with the live actuals payload — check for an id_map/season drift"
    )
```

### WR-04: `require_key` compares the API key with a non-constant-time membership check

**File:** `api/main.py:424-428`
**Issue:**
```python
def require_key(x_api_key: str | None = Header(default=None)) -> None:
    keys = {k.strip() for k in os.environ.get("FPL_API_KEYS", "").split(",")
            if k.strip()}
    if keys and x_api_key not in keys:
        raise HTTPException(401, "missing or invalid API key")
```
`x_api_key not in keys` is a hash-based set-membership test, not a
constant-time string comparison — CPython's string `__eq__`/hashing does not
guarantee timing independence from the input's byte content, so this is
theoretically vulnerable to a timing side-channel that could help an attacker
guess a valid key byte-by-byte given enough requests. The module's own
docstring and `README.md`'s "Secrets and configuration" section already flag
`require_key` as "a stub, upgradeable to Supabase JWT... single choke point by
design", so the fix cost is low and worth taking now rather than after real
paid traffic depends on this gate.
**Fix:**
```python
import hmac

def require_key(x_api_key: str | None = Header(default=None)) -> None:
    keys = {k.strip() for k in os.environ.get("FPL_API_KEYS", "").split(",")
            if k.strip()}
    if keys and not any(
        x_api_key is not None and hmac.compare_digest(x_api_key, k) for k in keys
    ):
        raise HTTPException(401, "missing or invalid API key")
```

## Info

### IN-01: `models/price.py` — `CLASSES` dict is dead code

**File:** `models/price.py:38`
**Issue:** `CLASSES = {-1: "fall", 0: "hold", 1: "rise"}` is defined at module
level but never referenced anywhere else in the file (verified via `grep -n
"CLASSES" models/price.py`, one hit — the definition itself). Label mapping
for the trained classifier's 3 classes is done inline elsewhere (`clf.fit(...,
tr.label + 1, ...)` / `CLASSES` is never used to decode predictions back to a
string).
**Fix:** Remove it, or wire it in where `art["clf"].predict_proba(...)` output
is currently indexed by raw class position (`proba[:, 2]`/`proba[:, 0]`) if the
intent was to make that indexing self-documenting.

### IN-02: `scripts/daily.sh` / `scripts/weekly.sh` — the "alerting failed" fallback branch is unreachable

**File:** `scripts/daily.sh:34-36`, `scripts/weekly.sh:33-35`
**Issue:**
```bash
if ! "$PY" -m ops.notify --job daily --step "$name" --message "exit code $rc"; then
  echo "[daily] alerting failed for $name" >&2
fi
```
`ops.notify.report()` (the function the CLI's `main()` calls) is explicitly
documented ("Never raises: this function's entire body is guarded...") and
tested (`tests/test_cron.py::test_report_never_raises_even_when_everything_is_broken`)
to swallow every internal failure (webhook errors, disk errors, even a broken
`redact`) and always return `None`. Its `main()` therefore always `return 0`
regardless of whether the alert log write or the webhook POST actually
succeeded. Verified empirically: `python -m ops.notify --job x --step y
--message test` exits `0` even when pointed at conditions that make the inner
webhook/log path fail. The shell's `if !` branch can only fire on a Python
process crash before `main()` runs (e.g. a missing interpreter, a
`PYTHONPATH` misconfiguration causing an import error) — a real but much
narrower failure mode than "alerting failed" suggests, and the comment/message
wording gives a false impression that a swallowed webhook/log failure would be
surfaced here.
**Fix:** Either have `ops.notify.report`'s CLI wrapper return non-zero when it
detects a downstream failure (e.g. have `report` return a success/failure flag
that `main()` propagates, rather than always `None`), or reword the shell
comment/echo to describe the actual (narrower) failure mode it guards against.

---

_Reviewed: 2026-09-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
