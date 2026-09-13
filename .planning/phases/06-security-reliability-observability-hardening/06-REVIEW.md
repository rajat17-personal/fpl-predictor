---
phase: 06-security-reliability-observability-hardening
reviewed: 2026-09-06T00:00:00Z
depth: standard
files_reviewed: 36
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
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-09-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 36
**Status:** issues_found

## Summary

This review re-examines the full current state of Phase 6 (plans 06-01 through 06-07,
including the REL-05 gap-closure commit `aae7503`), superseding the prior 06-REVIEW.md.

The REL-05 TOCTOU fix in `api/main.py` (`PoolSnapshot`/`GwPoolsSnapshot`, `_pool()`,
`_gw_pools_meta()`/`_gw_pools_locked()`, the bounded `_solve_cache` LRU+TTL) is sound:
every consumer of the pool/version pair reads all four fields (`pool`, `gw`, `boot`,
`pool_version`) inside a single `with _lock:` block, `solve()`/`plan()`/`team()`/`rate()`
never re-acquire `_lock` or subscript `_state` afterward, and
`tests/test_api_hardening.py`'s stub-free, real-interleaving regression tests (in
particular `test_solve_never_serves_a_pre_refresh_payload_under_a_post_refresh_key` and
the AST-based structural gate `test_snapshot_consumers_hold_no_lock_and_touch_no_state_dict`)
genuinely exercise the race this fix closes, not a stubbed-out approximation of it. The
CORS allowlist (SEC-01), structured request logging + secret redaction (OBS-01),
liveness/readiness split (OBS-02), fail-loud JSON I/O (REL-01/REL-04), and pydantic
payload validation (REL-03) are all implemented as documented and are backed by
tests that actually drive the failure paths (not just the happy path).

The one finding that changes the ship/no-ship call is in
`.github/workflows/weekly.yml`: removing the `|| true` cron-suppression from the
"Commit outputs" step (done correctly and deliberately elsewhere in this same phase)
left behind a `git add data/raw/live` line that targets a directory unconditionally
excluded by `.gitignore` — this now fails the entire step (and job) every time the
workflow reaches it, which is the opposite of the reliability goal that change was
making. See CR-01 below.

## Critical Issues

### CR-01: `weekly.yml`'s "Commit outputs" step always fails — `git add` targets a gitignored directory

**File:** `.github/workflows/weekly.yml:35`
**Issue:**
The "Commit outputs" step runs:
```yaml
git add web/data data/raw/live
if ! git diff --cached --quiet; then
  git commit -m "weekly: GW export $(date -u +%F)"
fi
git push
```
`data/raw/` (and therefore `data/raw/live/`) is unconditionally listed in `.gitignore`
(`.gitignore:14`), with no negation rule the way `data/snapshots/` gets
(`!data/snapshots/` / `!data/snapshots/**`). `git add` on an explicitly-named,
gitignored path prints `"The following paths are ignored by one of your .gitignore
files"` and **exits 1** rather than silently no-opping (verified directly: `git add
<gitignored-dir>` → exit code 1). GitHub Actions' default shell for `run:` steps on
Linux runners is `bash --noprofile --norc -eo pipefail {0}` (errexit), so this
`git add`'s non-zero exit aborts the step — and, with no `continue-on-error`, the
whole `weekly` job — before `git commit`/`git push` ever run.

This is a regression introduced by this phase, not a pre-existing bug: the prior
version of this line was `git add web/data data/raw/live || true` (see
`git diff 2840bbac06e9b74ab96f562a8392c5cf8ebbe1c3^..HEAD -- .github/workflows/weekly.yml`),
and the `|| true` suppression was removed as part of this phase's REL-02/OBS-03
"no shell OR-suppression in a cron script or workflow" hardening (the exact
pattern `scripts/preflight.sh` Gate 6 now greps for). The equivalent line in
`daily.yml` was fixed correctly in the same phase: it *dropped* the other
gitignored path it used to carry (`models/artifacts/price_model.joblib`) instead of
just stripping the `|| true`. `weekly.yml`'s `data/raw/live` was never given the
same treatment.

Reproduced directly:
```
$ git init /tmp/gittest && cd /tmp/gittest
$ mkdir -p data/raw/live && echo x > data/raw/live/foo.txt
$ echo "data/raw/" > .gitignore && git add .gitignore && git commit -q -m init
$ git add data/raw/live; echo "exit=$?"
The following paths are ignored by one of your .gitignore files:
data/raw
hint: Use -f if you really want to add them.
exit=1
```

Note: today this failure is additionally masked by an earlier one — the preceding
"Export predictions + digest" step (`bash scripts/weekly.sh`) itself has no
mechanism to supply the gitignored, never-committed
`models/artifacts/xp_model.joblib` that `predict.export` requires, so that step
fails first and the job stops before even reaching "Commit outputs" (see WR-01).
That does not make this line correct — it only means the two gaps currently hide
each other, and fixing one without the other still leaves `weekly.yml` non-functional
end to end.

**Fix:** Either stop trying to track `data/raw/live` (it is explicitly documented in
`.gitignore` as "regenerable pipeline data" that every run re-fetches, so there is no
real recovery/audit value in committing it), or carve out an explicit negation rule
for it the same way `data/snapshots/` gets one:
```diff
- git add web/data data/raw/live
+ git add web/data
```
or, if the intent genuinely is to persist it:
```diff
# .gitignore
+ !data/raw/live/
+ !data/raw/live/**
```
Either way, add a regression test analogous to
`tests/test_cron.py::test_env_example_is_tracked_and_env_is_ignored` that runs
`git add --dry-run` (or `git check-ignore`) over every path either workflow's
"Commit outputs" step names, so a future re-introduction of this exact class of bug
fails CI instead of only ever being caught by a real dispatch.

## Warnings

### WR-01: `weekly.yml` has no mechanism to supply the model artifact it depends on

**File:** `.github/workflows/weekly.yml:26-30`
**Issue:** `predict.export.export()` (invoked via `scripts/weekly.sh` →
`python -m predict.export`) does `joblib.load(config.ROOT / "models" / "artifacts" /
"xp_model.joblib")` unconditionally. `models/artifacts/` is gitignored and is never
populated by anything in this workflow (no cache restore, no artifact download, no
secrets-backed fetch) — only a comment claims "The trained model is supplied at run
time, never committed to the repo." On a fresh `actions/checkout`, this `joblib.load`
raises `FileNotFoundError`, `scripts/weekly.sh`'s `run_step` catches it, alerts, and
lets the two independent remaining steps run, but the script still exits 1 at the end
— so the "Export predictions + digest" step, and therefore the whole job, fails on
every dispatch as currently wired.
**Fix:** Either wire an actual supply mechanism (e.g. `actions/download-artifact`
from a companion "train" workflow, or a repository/environment secret + `curl`/`aws
s3 cp` step before "Export predictions + digest"), or make the dormant/manual nature
of this workflow explicit in a pre-flight check with an actionable error (e.g. a
`test -f models/artifacts/xp_model.joblib || { echo "::error::place a trained model
at models/artifacts/xp_model.joblib before dispatching this workflow"; exit 1; }`
step) so a future operator gets a clear message instead of a `FileNotFoundError`
traceback three steps deep.

### WR-02: `predict/scoreboard.py` skipped this phase's cron-reliability hardening

**File:** `predict/scoreboard.py:81-83`
**Issue:**
```python
boot = requests.get(f"{config.FPL_API}/bootstrap-static/",
                    headers=_HEADERS, timeout=30).json()
```
and `fetch_actuals()` (`predict/scoreboard.py:29-36`) call the FPL API with no
`raise_for_status()`, no retry/backoff, and no `ops.notify.report()` alerting. Every
other cron-invoked live-network call site this phase touched
(`data/snapshot.py::_fetch_bootstrap`) now has bounded retry + exponential backoff +
`report()` alerting on final failure (REL-02). `predict/scoreboard.py` is invoked from
the same `scripts/daily.sh` (`run_step predict.scoreboard ...`) but was left on the
pre-hardening pattern: a transient 5xx/network blip surfaces as an uncaught
`requests.exceptions.*` (best case) or a `KeyError`/`json.JSONDecodeError` against an
HTML error page (worst case) instead of the structured, alerted failure the rest of
this phase standardized on. `run_step` in `daily.sh` still catches and reports the
exit code either way, but the *message* alerted is a bare "exit code 1", not the
actionable "bootstrap-static fetch failed after N attempts: ..." the rest of the
phase produces.
**Fix:** Route `predict/scoreboard.py`'s bootstrap fetch through the same
retry/backoff/`report()` helper `data/snapshot.py::_fetch_bootstrap` uses (factor it
into a small shared helper if duplicating the retry loop is undesirable), and add
`raise_for_status()` before `.json()` on both `update()`'s bootstrap fetch and
`fetch_actuals()`.

### WR-03: `ops.notify.report()`'s "never raises" contract is fragile against a reserved `LogRecord` field name

**File:** `ops/notify.py:55-56`
**Issue:**
```python
log_fields = {k: v for k, v in record.items() if k != "message"}
log_event(_logger, "alert", alert_message=record["message"], **log_fields)
```
`log_event` passes `extra={"event": event, **fields}` into `logger.log(...)`. If any
caller of `report(job, step, message, **fields)` ever passes a `fields` key that
collides with a reserved `logging.LogRecord` attribute (e.g. `module`, `process`,
`args`, `msg`, `filename`), `logger.log()` raises
`KeyError: "Attempt to overwrite 'X' in LogRecord"`. Because that call happens
*before* the on-disk JSONL append and the webhook POST inside `report()`'s single
`try` block, the exception is swallowed by the outer `except Exception` — which logs
only an `alert.failed` event — and the alert is **never written to disk or POSTed**,
silently defeating the module's own documented guarantee ("a broken alerting path can
never abort the run it observes... every failure inside `report` itself is caught,
logged, and swallowed" — the intent is clearly "the alert always lands somewhere",
not "the alert can vanish"). No current call site (`data/snapshot.py`,
`ops/notify.main`) passes a colliding field name, so this is latent, not currently
triggered.
**Fix:** Prefix caller-supplied extra fields before handing them to `log_event`
(e.g. `log_event(_logger, "alert", alert_message=record["message"],
**{f"alert_{k}": v for k, v in log_fields.items()})`), or move the on-disk
write/webhook POST ahead of the `log_event` call so a future reserved-name collision
degrades to a missing log line rather than a missing alert record.

### WR-04: REL-05's atomic critical section still holds the global lock for the full pool build

**File:** `api/main.py:360-372` (`_pool`), `374-392` (`_gw_pools_locked`)
**Issue:** This is pre-existing behavior (unchanged by the REL-05 fix itself — only
the return shape changed), but the fix's own framing ("all four read inside the SAME
critical section... consume this as one value, never split across two lock
acquisitions") makes the design explicit rather than incidental, so it is worth
calling out now: `_pool()`/`_gw_pools_locked()` call `build_pool`/`build_horizon_pool`/
`_gw_pool` (LightGBM inference + pandas aggregation, potentially seconds on a
cold/refreshed pool) *while holding* `_lock`. Every other request touching `_pool()`,
`_gw_pools_meta()`, `_cache_get()`, or `_cache_put()` — i.e. every `/api/solve`,
`/api/plan`, `/api/team`, `/api/rate` request, and even `_refresh()` itself — blocks
for that entire duration. The module's own header docstring ("Solves are computed in
parallel (thread-safe ILP)") and `_pool()`'s own inline comment ("Deadline-hour
traffic hits the cache") both imply a level of concurrency this lock shape does not
provide on a cache miss.
**Fix:** Out of scope for a mechanical fix in this review, but worth a follow-up: build
the pool outside the lock (accepting that two threads might redundantly build the
same cache-miss pool once), then take the lock only to publish the result and read
`pool_version` atomically — trading a rare duplicated computation for shorter lock
hold times during exactly the deadline-hour traffic spike the docstring calls out.

## Info

### IN-01: `ruff.toml`'s `line-length = 100` is dead configuration under the configured rule set

**File:** `ruff.toml:13,33`
**Issue:** `line-length = 100` is set, but `[lint] select = ["E4", "E7", "E9", "F"]`
does not include `E501` (line-too-long) or any other line-length-sensitive rule in
that explicit set, so `ruff check` currently never consults `line-length` for
anything. This isn't a functional bug (nothing relies on it firing), but it reads as
an enforced 100-column limit that Gate 2 (`ruff check .`) does not actually enforce.
**Fix:** Either add `"E501"` to `select` (and confirm the existing tree is under 100
columns everywhere, or add per-file `ignore` entries), or drop the `line-length`
setting and note in the comment block that column length is a style preference the
lint gate does not police.

### IN-02: `.env.example` could not be independently read for this review

**File:** `.env.example`
**Issue:** This file is blocked by the current sandbox's read/bash permission rules
(both the `Read` tool and `cat` were denied), so its contents were not directly
inspected here. `tests/test_cron.py` (`test_env_example_lines_are_keys_with_no_
assigned_value`, `test_env_example_names_every_expected_key`,
`test_env_example_is_tracked_and_env_is_ignored`) exercise its shape and give
reasonable confidence it is a valueless, tracked template naming
`FPL_API_KEYS`/`ODDS_API_KEY`/`FPL_CORS_ORIGINS`/`FPL_ALERT_WEBHOOK`/`FPL_ALERT_LOG`/
`FPL_FIXTURE_DIR`/`FPL_FIXTURE_DATA_DIR`, and `scripts/preflight.sh` Gate 7 sub-check
4 independently re-verifies the same shape at CI/preflight time — but neither
substitutes for a direct read. Flagging so a human reviewer (who has filesystem
access this environment does not) gives it a final look before sign-off.
**Fix:** N/A — informational; re-run this review (or eyeball the file manually) in an
environment where `.env.example` is readable if full confidence is required.

---

_Reviewed: 2026-09-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
