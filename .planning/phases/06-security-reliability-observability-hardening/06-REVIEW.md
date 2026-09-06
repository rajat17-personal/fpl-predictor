---
phase: 06-security-reliability-observability-hardening
reviewed: 2026-09-06T00:00:00Z
depth: standard
files_reviewed: 37
files_reviewed_list:
  - .env.example
  - .github/workflows/daily.yml
  - .github/workflows/weekly.yml
  - .gitignore
  - README.md
  - api/main.py
  - config.py
  - data/id_map.py
  - data/ingest.py
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
  - ruff.toml
  - scripts/daily.sh
  - scripts/preflight.sh
  - scripts/verify_hardening.sh
  - scripts/weekly.sh
  - tests/test_api.py
  - tests/test_api_hardening.py
  - tests/test_capture_fixtures.py
  - tests/test_cron.py
  - tests/test_fixture_mode.py
  - tests/test_obs.py
  - tests/test_payloads.py
  - tests/test_product.py
  - tests/test_reliability.py
findings:
  critical: 1
  warning: 7
  info: 3
  total: 11
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-09-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 37
**Status:** issues_found

## Summary

This is a re-review after gap-closure plan `06-06`. **CR-01 from the prior
`06-REVIEW.md` (`e2e/scripts/capture_fixtures.py` crashing with `NameError:
name 'json' is not defined` on its default action) is confirmed RESOLVED**:
`import json` is back in the module's stdlib import block (line 20),
`python -m pyflakes e2e/scripts/capture_fixtures.py` reports nothing, `ruff
check .` reports `All checks passed!` against all 54 tracked Python files
(the `ruff.toml` `exclude` list is now subtree-scoped, no longer hiding
`data/*.py` or `e2e/scripts/`), and the full suite passes locally
(`166 passed, 1 skipped`).

The four warnings and two info items left open in the prior review by
gap-closure plan `06-06` (explicitly deferred, not touched by that plan) are
**still open** — verified against the current source, not merely assumed
carried-over — and are re-listed below as WR-01 through WR-04 and IN-01/IN-02.

This pass also found one new, previously-undetected correctness defect in the
exact mechanism this phase's own commentary and `06-VERIFICATION.md` certify
as fixed: `api/main.py`'s solve-cache/`pool_version` invalidation guarantee
(REL-05) has a TOCTOU race between fetching a pool and tagging the cache
entry with the version that pool actually came from, in both `/api/solve` and
`/api/plan`. Three further warnings and one info item were found by tracing
edge cases through `predict/scoreboard.py`, `predict/digest.py`,
`ops/jsonlog.py`, and `api/main.py`'s new `/api/ready` probe.

## Critical Issues

### CR-01: `/api/solve` and `/api/plan` can cache a stale payload under a cache key that claims a newer pool version

**File:** `api/main.py:582-589` (`solve`), `api/main.py:647-652` (`plan`), root cause in `api/main.py:330-340` (`_pool`)
**Issue:** The whole point of `pool_version` (added by plan `06-04` for
REL-05, and described at length in `_initial_state`'s docstring: "a payload
computed against an older pool can never be served after a refresh — the
version bump... is what makes that unreachable") depends on the version
tagged into a cache key always describing the *same* pool generation the
payload was computed from. It does not, because the two are fetched in two
separate, non-atomic critical sections:

```python
@app.post("/api/solve", dependencies=[Depends(require_key)])
def solve(req: SolveRequest):
    pool, gw, boot = _pool(req.horizon)     # <- lock acquired+released inside _pool()
    with _lock:
        pool_version = _state["pool_version"]   # <- a SEPARATE, later lock acquisition
    key = hashlib.sha1(json.dumps({"gw": gw, "pool_version": pool_version,
                                  **req.model_dump()}, ...).hexdigest()
    ...
    _cache_put(key, out)
```

`_pool()` itself only holds `_lock` long enough to read `_state["pools"][key]`,
`_state["gw"]` and `_state["boot"]` and returns immediately after — it never
returns the version the returned pool corresponds to. If a `_refresh()` lands
on another thread between `_pool()`'s return and the handler's own
`with _lock: pool_version = ...` line (both a natural TTL-boundary refresh —
`POOL_TTL_S = 3600`, so this window recurs every hour in production — and any
future forced-refresh trigger), the handler computes `out` from the **old**
pool but tags it in the cache with the **new**, post-refresh
`_state["pool_version"]`. That payload is then indistinguishable from a
genuinely fresh one: any later request within the new version's lifetime that
hashes to the same key gets served the stale computation, for up to
`SOLVE_CACHE_TTL_S` (= `POOL_TTL_S`, another hour) or until the next natural
refresh clears the whole cache — silently, with no error and no way for a
caller to detect it. This is precisely the class of bug the module's own
`_cache_get`/`_cache_put` docstrings and `tests/test_api_hardening.py`'s
`test_payload_cached_before_a_refresh_is_unreachable_after_it` claim cannot
happen; that test only proves it for a payload keyed with the version known
*at store time*, not for the TOCTOU window between fetching the pool and
fetching the version tag, which no test drives (`test_concurrent_solve_and_refresh`
and `test_concurrent_solve_overlapping_refresh_stays_within_bound` both stub
`_pool` out entirely with a function that returns a fixed, version-independent
`DataFrame`, so neither exercises the real `_pool()` code path this bug lives
in). `06-04-PLAN.md` itself anticipated the safe alternative — "read
`_state['pool_version']` under the lock (**or return it from `_pool`, which
already holds the lock**)" — but the implementation took neither option
atomically: it re-enters the lock in a second, separate statement instead of
reading the version inside `_pool`'s own critical section.
`06-VERIFICATION.md` marks REL-05 "✓ SATISFIED... invalidation race fixed",
which is not accurate for this residual path. The `plan` endpoint has the
identical shape at lines 647-652 against `_gw_pools_meta`.
**Fix:** Make the pool fetch and the version tag one atomic read. Simplest
fix — return the version from `_pool`/`_gw_pools_meta` themselves, from
inside the same locked block that reads the pool:
```python
def _pool(horizon: int = 1):
    _refresh()
    with _lock:
        key = horizon
        if key not in _state["pools"]:
            ...
            _state["pools"][key] = _with_bands(...)
        return _state["pools"][key], _state["gw"], _state["boot"], _state["pool_version"]
```
and use that returned version directly in `solve`/`plan` instead of a second
`with _lock: pool_version = _state["pool_version"]` read. Apply the same
change to `_gw_pools_meta`/`_gw_pools`.

## Warnings

### WR-01: `predict/digest.py` — a genuinely 0%-owned player can never be flagged as the differential pick

**File:** `predict/digest.py:41` — **still open** (deferred by `06-06-PLAN.md`, not fixed)
**Issue:**
```python
diff = next((r for r in table
             if (r.get("ownership") or 100) < DIFFERENTIAL_MAX_OWN
             and r.get("status") == "a"), None)
```
`r.get("ownership") or 100` treats an ownership of exactly `0.0` as falsy and
substitutes `100`, excluding the most extreme possible differential from ever
being surfaced. Verified directly: `(0.0 or 100) < 10.0` is `False`.
**Fix:** Use an explicit `None` check instead of `or`:
```python
own = r.get("ownership")
diff = next((r for r in table
             if (r.get("ownership") if r.get("ownership") is not None else 100) < DIFFERENTIAL_MAX_OWN
             and r.get("status") == "a"), None)
```

### WR-02: `ops.jsonio.write_json` silently narrows every JSON artifact it writes to mode 0600

**File:** `ops/jsonio.py:47-65` — **still open** (deferred by `06-06-PLAN.md`, not fixed)
**Issue:** `tempfile.NamedTemporaryFile(..., delete=False, ...)` creates its
backing file at mode `0600` regardless of umask, and `os.replace` preserves
the source inode's bits, not the destination's previous ones. Every
`write_json` caller (`predict/export.py`, `predict/scoreboard.py`,
`models/price.py`, `models/intervals.py`, `e2e/scripts/capture_fixtures.py`)
now silently drops its output file to owner-only-readable on the next write,
breaking any reader running as a different OS user (reverse proxy, second
static-file process, backup agent).
**Fix:** Set an explicit conventional mode before or after the replace:
```python
os.chmod(tmp.name, 0o644)
os.replace(tmp.name, path)
```

### WR-03: `predict/scoreboard.py::score_gw` can raise an uncaught `IndexError` on an empty merge

**File:** `predict/scoreboard.py:39-63` — **still open** (deferred by `06-06-PLAN.md`, not fixed)
**Issue:** `pred = pd.DataFrame(frozen["players"]).merge(actuals, on="player_id", how="inner")`
followed by `.iloc[0]` (captain) and `.iloc[0]` (best player) will raise a
bare `IndexError` with no actionable message if the frozen file's
`player_id`s and the live actuals share zero rows (id_map drift, a corrupted
frozen file, mid-season element-id reassignment). `update()` has no
`try/except` around `score_gw`, so this crashes the post-GW cron step with a
traceback instead of the `PayloadError`-style message every other fail-loud
path in this phase produces.
**Fix:**
```python
if pred.empty:
    raise PayloadError(
        f"scoreboard: frozen gw{frozen['gw']} predictions share no player_id "
        "with the live actuals payload — check for an id_map/season drift"
    )
```

### WR-04: `require_key` compares the API key with a non-constant-time membership check

**File:** `api/main.py:424-428` — **still open** (deferred by `06-06-PLAN.md`, not fixed)
**Issue:** `x_api_key not in keys` is hash/`__eq__`-based set membership, not
a constant-time comparison, and is theoretically vulnerable to a timing
side-channel. Low cost to fix now, before real paid traffic depends on this
gate.
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

### WR-05: `predict/scoreboard.py::update()`'s bootstrap-static fetch has none of this phase's own retry/reliability treatment

**File:** `predict/scoreboard.py:81-82`
**Issue:**
```python
boot = requests.get(f"{config.FPL_API}/bootstrap-static/",
                    headers=_HEADERS, timeout=30).json()
```
No `raise_for_status()`, no retry/backoff. `data/snapshot.py::_fetch_bootstrap`
— the sibling call to the exact same endpoint, hardened by *this same phase*
(REL-02) — retries on 429/5xx with exponential backoff+jitter, distinguishes
retryable from non-retryable failures, and reports via `ops.notify` on final
failure. `predict/scoreboard.py::update()` is invoked from the identical
daily cron (`scripts/daily.sh`'s last step) but has none of that: a transient
5xx or a non-200 response with a non-JSON body raises either a raw
`requests.HTTPError`-free crash (status not checked at all) or an
uninformative `json.JSONDecodeError`, with no distinction from a genuine
schema problem. The failure is still visible (caught by `daily.sh`'s
`run_step` and reported via `ops.notify`), but the message an operator sees
names none of the specifics `_fetch_bootstrap`'s hardening was built to
surface, and a transient blip that `data.snapshot` would have silently
recovered from will instead abort `predict.scoreboard` outright.
**Fix:** Route this call through the same retry/backoff helper
`data/snapshot.py::_fetch_bootstrap` already implements (extract it to a
shared helper, e.g. `data/live_fetch.py`, and call it from both places), or
at minimum add `raise_for_status()` plus one retry pass.

### WR-06: `predict/digest.py` crashes with `KeyError` on `p10`/`p90` when the intervals artifact hasn't been trained yet

**File:** `predict/digest.py:55-56` (`to_text`), `predict/digest.py:86-87` (`to_html`); root cause in `predict/export.py:57-67` (`build_table`)
**Issue:** `build_table` only attaches `p10`/`p90` columns
`if art is not None` (`intervals.load_artifact()` returns `None` when
`models/artifacts/intervals.json` — gitignored, regenerable — doesn't exist
yet). When it's absent, the `cols` filter in `build_table` (`[c for c in
cols if c in t.columns]`) drops `p10`/`p90` from every row of
`xp_table.json` entirely — not `null`, simply absent. `predict/digest.py`'s
`to_text`/`to_html` then unconditionally do `r['p10']:.1f` / `r['p90']:.1f`
for every row in `d["top5"]`, raising `KeyError: 'p10'`. This is a real
cold-start path: `models.intervals` is documented in `README.md` as a
separate step ("fit p10/p90 bands... once per retrain"), distinct from the
`predict.export` → `predict.digest` chain `scripts/weekly.sh` runs — a fresh
deployment, a rebuilt model artifact directory, or an operator who has not
yet run `python -m models.intervals` will have `predict.digest` crash on its
very first invocation. Not caught by `tests/test_product.py::test_digest_render`,
whose fixture data always supplies `p10`/`p90` on every row.
**Fix:** Guard the format calls with a default, e.g.:
```python
p10 = f"{r['p10']:.1f}" if "p10" in r else "—"
p90 = f"{r['p90']:.1f}" if "p90" in r else "—"
```
applied consistently in both `to_text` and `to_html`.

### WR-07: `ops.jsonlog.redact` does not recurse into tuples, understating its own documented guarantee

**File:** `ops/jsonlog.py:41-54` (`_redact`); module docstring at `ops/jsonlog.py:7-8` claims "`redact` guarantees no secret value reaches a log line"
**Issue:**
```python
def _redact(value, secrets):
    if isinstance(value, dict):
        ...
    if isinstance(value, list):
        return [_redact(v, secrets) for v in value]
    if isinstance(value, str) and secrets and value in secrets:
        return "[redacted]"
    return value
```
Only `dict` and `list` are recursed into. A tuple value anywhere in a logged
field's structure (e.g. `extra={"detail": (401, "invalid key: <secret>")}`,
or any future call site that logs an exception's `.args` tuple, or a
`(status, headers)` pair) passes through the last `return value` branch
unexamined — a bare secret string nested inside a tuple is never checked
against `secrets` and never redacted, and a secret-shaped key inside a `dict`
nested inside a `tuple` is likewise skipped. No current call site in this
codebase logs a tuple-valued field, so there is no live leak today, but the
module's own docstring states an unconditional guarantee ("guarantees no
secret value reaches a log line") that the implementation does not actually
provide for this container type — the kind of gap that bites the next
engineer who trusts the docstring and logs a tuple.
**Fix:**
```python
if isinstance(value, (list, tuple)):
    result = [_redact(v, secrets) for v in value]
    return type(value)(result) if isinstance(value, tuple) else result
```

## Info

### IN-01: `models/price.py` — `CLASSES` dict is dead code

**File:** `models/price.py:38` — **still open** (deferred by `06-06-PLAN.md`, not fixed)
**Issue:** `CLASSES = {-1: "fall", 0: "hold", 1: "rise"}` is defined but never
referenced elsewhere in the file (`grep -n "CLASSES" models/price.py` — one
hit, the definition).
**Fix:** Remove it, or wire it in where `predict_proba(...)` output is
indexed positionally (`proba[:, 2]` / `proba[:, 0]`) to make that indexing
self-documenting.

### IN-02: `scripts/daily.sh` / `scripts/weekly.sh` — the "alerting failed" fallback branch is effectively unreachable

**File:** `scripts/daily.sh:34-36`, `scripts/weekly.sh:33-35` — **still open** (deferred by `06-06-PLAN.md`, not fixed)
**Issue:** `ops.notify.report()`'s CLI wrapper always returns `0`
regardless of whether the alert log write or webhook POST actually
succeeded (`report` never raises, by design), so
`if ! "$PY" -m ops.notify ...; then echo "alerting failed"...; fi` can only
fire on a Python process crash before `main()` runs, a much narrower
condition than the message implies.
**Fix:** Have `report`'s CLI wrapper propagate a success/failure signal, or
reword the shell message to describe the narrower actual failure mode.

### IN-03: `/api/ready`'s 503 body reports a nonsensical multi-billion-second `pool_age_s` before any pool has ever loaded

**File:** `api/main.py:537-549` (`ready`); the same value shape also affects the pre-existing `/api/health`
**Issue:** `_state["loaded_at"]` defaults to `0.0` (`_initial_state`). Before
the first successful `_refresh()`, both `/api/health` and the new
`/api/ready`'s 503 body compute `round(time.time() - _state["loaded_at"])`,
which is effectively the current Unix epoch time (~1.7 billion) rather than
a meaningful "pool age". `/api/health`'s version of this predates this
phase, but `/api/ready` is new here and inherits the same non-diagnostic
value in exactly the response an operator would read to debug a cold-start
failure.
**Fix:** Report `null`/omit `pool_age_s` when `_state["loaded_at"] == 0.0`
rather than emitting a value that looks like a real (if absurd) duration.

---

_Reviewed: 2026-09-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
