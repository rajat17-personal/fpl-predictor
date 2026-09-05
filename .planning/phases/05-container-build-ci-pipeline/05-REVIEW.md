---
phase: 05-container-build-ci-pipeline
reviewed: 2026-09-05T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - .dockerignore
  - .github/workflows/ci.yml
  - .github/workflows/daily.yml
  - .github/workflows/weekly.yml
  - .gitignore
  - Dockerfile
  - backtest/season.py
  - features/engineer.py
  - models/train.py
  - models/tune.py
  - optimize/chips.py
  - predict/export.py
  - requirements-dev.in
  - requirements-dev.txt
  - requirements.in
  - requirements.txt
  - ruff.toml
  - scripts/preflight.sh
  - scripts/smoke_test.sh
  - tests/test_product.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-09-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

This phase's actual payload is the CI/CD and container plumbing (`Dockerfile`, `.dockerignore`, `.github/workflows/*.yml`, `scripts/preflight.sh`, `scripts/smoke_test.sh`, `ruff.toml`, `requirements*.{in,txt}`); the seven Python files in the file list (`backtest/season.py`, `features/engineer.py`, `models/train.py`, `models/tune.py`, `optimize/chips.py`, `predict/export.py`, `tests/test_product.py`) received only mechanical ruff fixes (semicolon-joined statements split onto separate lines, unused `numpy` imports dropped, f-strings without placeholders de-f'd, one lambda-assignment turned into a `def`). I diffed each of those seven files against the pre-phase commit and confirmed no logic changed; `ruff check` on all seven passes cleanly today.

The infra deliverables are solid overall — every `uses:` line across the three workflows is a genuine 40-character commit SHA (verified by direct extraction, not just eyeballing), the Dockerfile's multi-stage/non-root/libstdc++6+libgomp1 reasoning is sound and matches how PuLP's bundled CBC binary and LightGBM's OpenMP dependency actually behave, and `.dockerignore`'s frontend-dist re-inclusion pattern is correctly ordered for Docker's (non-gitignore) pattern semantics. The findings below are the real gaps I could substantiate: two places where the "verified thing" and "shipped thing" can silently diverge (CI trigger coverage for forked PRs; the image that gets smoke-tested vs. the image that gets published), one workflow that will hard-crash if actually dispatched, one credential-scanner blind spot, and a few pre-existing (not introduced by this phase) code smells surfaced by reading the full files as required.

## Warnings

### WR-01: `ci.yml`'s pull_request trigger silently skips new commits on forked PRs

**File:** `.github/workflows/ci.yml:23-25`
**Issue:** `pull_request` is narrowed to `types: [opened, reopened, ready_for_review]`, on the stated rationale that a `push` to a branch with an open PR already fires a `push` event, so adding `synchronize` would double-run. That rationale only holds for PRs from branches **within this repository**. For a PR opened from a fork, subsequent commits pushed to the fork happen in the fork's own repo and never trigger this repo's `push` trigger — and with `synchronize` excluded from `pull_request`, those follow-up commits get **no CI run at all**. A contributor (or an attacker) could get an initial commit reviewed/approved, then push additional unverified commits to the same PR before merge.
**Fix:**
```yaml
pull_request:
  types: [opened, reopened, ready_for_review, synchronize]
```
If the double-run-on-same-repo-push concern still matters, keep the existing `concurrency` group (it already dedupes same-ref runs) rather than dropping `synchronize` outright.

### WR-02: The image that is smoke-tested/scanned is not the image that gets published

**File:** `.github/workflows/ci.yml:160-216` (image job) and `:217-258` (publish job); `Dockerfile:14,25,38`
**Issue:** The `image` job builds `local/fpl:ci` with `push: false, load: true`, runs `scripts/smoke_test.sh` and the Trivy scan against that build, then the `publish` job runs a **second, independent** `docker/build-push-action` invocation against the same Dockerfile/context and pushes *that* build to GHCR. The two builds share a GHA layer cache (`cache-from: type=gha`), so they're usually the same bits — but nothing guarantees it: `Dockerfile`'s `FROM python:3.14-slim` is a mutable tag (not pinned by digest), and `apt-get install -y libstdc++6 libgomp1` installs whatever versions are current in Debian's repos at build time (also unpinned). If either resolves differently between the two builds (minutes apart in the same run, or on a cache miss), the artifact pushed to `ghcr.io/${{ github.repository }}` is not provably the artifact that passed the smoke test and vulnerability scan.
**Fix:** Either (a) pin the base image by digest and the two apt packages by version so both builds are reproducible, or (b) restructure so `image` pushes to a scratch/staging tag first, and `publish` re-tags/pushes that same digest with `docker buildx imagetools create`/`docker tag` + `docker push` instead of rebuilding from source.

### WR-03: Dockerfile base image and apt packages are unpinned, undermining this phase's own hash-lock goal

**File:** `Dockerfile:14,25,38`
**Issue:** `requirements.txt`/`requirements-dev.txt` are hash-locked specifically so builds are reproducible (D-04), but `FROM python:3.14-slim` (both stages) and `apt-get install -y --no-install-recommends libstdc++6 libgomp1` have no version/digest pins. A future `python:3.14-slim` re-publish or a Debian security update to either package changes the shipped runtime silently, with no lockfile diff to signal it.
**Fix:** Pin the base image by digest (`FROM python:3.14-slim@sha256:...`) and consider pinning the two apt packages (`libstdc++6=<version> libgomp1=<version>`), refreshed deliberately alongside the Python lockfiles.

### WR-04: `weekly.yml` will crash on a fresh dispatch — no model artifact is ever produced or fetched

**File:** `.github/workflows/weekly.yml:26-33`
**Issue:** The "Export predictions + digest" step runs `python -m predict.export`, which unconditionally executes `joblib.load(config.ROOT / "models" / "artifacts" / "xp_model.joblib")` (`predict/export.py:273`, also `predict/live.py:248`). `models/artifacts/` is gitignored and never committed (confirmed in `.gitignore:19` and `.dockerignore:41`), and this workflow has no step that trains a model or fetches one from elsewhere. If this dispatch-only workflow is ever actually run (its only trigger is `workflow_dispatch`), it will fail immediately with `FileNotFoundError`, after the preceding `data.live_history` step has already done its (wasted) work. The header comment acknowledges the model is "supplied at run time, never committed" but the workflow has no guard or clear failure message for this — a developer who dispatches it gets a raw Python traceback instead of an actionable error.
**Fix:** Either wire in a real model-delivery step (out of this phase's scope per D-12) or add an explicit guard step that fails fast with a clear message, e.g.:
```yaml
- name: Guard model artifact
  run: |
    test -f models/artifacts/xp_model.joblib || {
      echo "FAILED: models/artifacts/xp_model.joblib is not present. This workflow cannot export predictions until model delivery is wired up (see D-12)."; exit 1; }
```

### WR-05: `preflight.sh`'s credential scan only catches quoted secret literals

**File:** `scripts/preflight.sh:120`
**Issue:** `CRED_PATTERN`'s generic key/token clause is `(api|secret|access)[_-]?(key|token)["']?[[:space:]]*[:=][[:space:]]*["'][A-Za-z0-9_-]{16,}["']` — note the value is required to be wrapped in a quote character on **both** sides. A common real-world shape like an unquoted shell export (`export API_KEY=sk-abcdef1234567890abcdef`) or an unquoted `.env`-style line (`SECRET_TOKEN=abcdef1234567890`) will not match, so Gate 6 reports "PASS" while such a literal sits in a tracked file. The named-service patterns (AWS `AKIA...`, GitHub `gh[pousr]_...`, Slack `xox...`, PEM headers) are unaffected since they don't require surrounding quotes.
**Fix:** Make the quote requirement optional for the generic clause, e.g. drop the trailing/leading `["']` requirement or make it `["']?` on both ends (accepting the wider net of false positives that comes with it, which is the right trade-off for a warn-and-manually-review gate).

## Info

### IN-01: Duplicated `if chip == "wc"` block in `run_season` (pre-existing, not touched by this phase)

**File:** `backtest/season.py:178-180` and `:190-192`
**Issue:** Inside the `chip in ("wc", "fh")` branch, `squad, meta = _squad_from_pick(r); bank = round(budget - r["cost"], 1)` is executed once right after `r = pick_squad(...)`, then executed **again**, byte-for-byte, a few lines later after the Free Hit `chip_deltas` block. Both copies compute from the same unchanged `r`/`budget`, so it's currently harmless — but it's dead/duplicated logic that will silently drift if only one copy is edited in a future change.
**Fix:** Delete the second occurrence (lines 190-192); the first assignment already covers it.

### IN-02: `models/tune.py`'s result sort can raise `TypeError` on a tied score (pre-existing)

**File:** `models/tune.py:69`
**Issue:** `results.sort(reverse=True)` sorts `(spearman_score, combo_dict)` tuples. If two combos ever produce an exactly equal Spearman score, Python falls through to comparing the second tuple element (`dict < dict`), which raises `TypeError: '<' not supported between instances of 'dict' and 'dict'`. Low probability with floating-point scores, but a real latent crash path in a script meant to run unattended for `--iters N` trials.
**Fix:** `results.sort(key=lambda r: r[0], reverse=True)`.

### IN-03: `smoke_test.sh`'s solve request has no timeout

**File:** `scripts/smoke_test.sh:65-70`
**Issue:** `curl -fsS -X POST .../api/solve -d '{}'` has no `--max-time`/`--connect-timeout`. A hung or deadlocked server inside the freshly-built container (e.g. CBC subprocess wedged) would block this step until the surrounding CI job's own timeout fires, rather than failing fast with a clear "smoke test timed out" message.
**Fix:** `curl -fsS --max-time 30 -X POST ...`.

### IN-04: `daily.yml`/`weekly.yml` have no `concurrency` guard

**File:** `.github/workflows/daily.yml`, `.github/workflows/weekly.yml`
**Issue:** Unlike `ci.yml` (which sets a `concurrency` group with `cancel-in-progress`), these two dispatch-only workflows have none. Two manual dispatches in quick succession (or a dispatch retriggered while one is still running) could race on `git add`/`git commit`/`git push` against the same branch, producing a failed push (non-fast-forward) or, more concerning, an interleaved commit.
**Fix:** Add a `concurrency: { group: ${{ github.workflow }}, cancel-in-progress: false }` block so a second dispatch queues instead of racing.

---

_Reviewed: 2026-09-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
