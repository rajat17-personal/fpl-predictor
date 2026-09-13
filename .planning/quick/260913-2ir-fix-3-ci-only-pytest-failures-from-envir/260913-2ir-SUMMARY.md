---
status: complete
task: 260913-2ir
one-liner: Fixed 3 CI-only pytest failures caused by test-side environment coupling (a developer-specific interpreter path, an untriggered lru_cache fallback tier, and an under-specified skip guard) — proven with a faithful clean-checkout CI simulation, not by pushing and waiting.
files-modified:
  - tests/test_cron.py
  - tests/test_crosswalk.py
  - tests/test_leakage.py
actuals:
  tokens: 9500
  tasks: 2
  commits: 3
---

# Quick Task 260913-2ir: Fix 3 CI-only pytest failures from environment coupling

## Accomplishments

- Reproduced the exact 3 CI-only failures locally via a detached-worktree CI simulation, proving harness fidelity before touching any test.
- Fixed `tests/test_cron.py`'s `test_daily_sh_failure_is_non_zero_notifies_once_and_lets_later_steps_run`: the stub interpreter's `real_python` local was hardcoded to a developer-specific conda path (`/home/sraja/miniconda3/envs/python314/bin/python`) that does not exist on CI runners. Rebound to `sys.executable`, added `import sys`, and double-quoted the interpolated value in the generated bash `exec` line.
- Fixed `tests/test_crosswalk.py`'s `test_resolve_by_name_returns_na_for_unknown_name`: an unresolvable name fell through both fast crosswalk tiers into `_fpl_name_index()`, which loads the full historical id map and needs season files absent on a clean checkout, raising `ValueError: No objects to concatenate`. Added a `monkeypatch` stand-in replacing `_fpl_name_index` with a zero-arg lambda returning an empty `pd.Series(dtype="Int64")` — mapping against an empty index still yields NA for every key, keeping the test running (not skipped) and fully offline.
- Fixed `tests/test_leakage.py`'s `test_transfermarkt_injury_dates_precede_kickoff`: its `skipif` guarded only on the committed spell table (which exists in CI), so the test ran and died inside `gw_deadlines()`, which reads the uncommitted `player_gw.parquet` build artifact. Widened the guard to require both the spell table and `RAW`, matching the file's existing two-condition `needs_data` idiom.

## Task-Commit Table

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (C1) | Fix cron stub interpreter path | `cb9e16c` | tests/test_cron.py |
| 1 (C2) | Stub crosswalk historical-registry tier | `61a70dc` | tests/test_crosswalk.py |
| 1 (C3) | Widen leakage skip guard | `b3c7fe6` | tests/test_leakage.py |

## Deviations from Plan

### Harness fidelity correction (not a Rule 1-4 code deviation — a test-methodology correction made during Step B, before any fix was applied)

The plan's measured fact named an existing `block_rl.py` blocker script at the scratchpad path, instructing it be copied into the worktree root and run from there. Doing so literally produced **4** failures, not 3:

1. An extra `FAILED tests/test_reliability.py::test_ruff_check_covers_every_tracked_python_file` — caused by `block_rl.py` itself becoming an untracked `.py` file inside the worktree, which `test_reliability.py`'s tracked-vs-inspected file-set comparison correctly flagged as an artifact of *my own simulation*, not a real repo defect.
2. An extra `FAILED tests/test_fixture_mode.py::test_client_side_route_falls_back_to_the_spa_shell_not_json` — caused by the clean worktree checkout legitimately lacking `frontend/dist` (gitignored). Reading `.github/workflows/ci.yml` confirmed this is expected and already handled in real CI: the `lint-build` job builds the frontend and uploads it as an artifact that the `test` job downloads *before* running pytest — a two-job handoff this single-process simulation does not have.
3. **Missing** the real 3rd failure: `tests/test_cron.py`'s test did not fail at all when run on this machine, even from the clean-checkout worktree, because the "developer-specific" interpreter path hardcoded in the test (`/home/sraja/miniconda3/envs/python314/bin/python`) *is this machine's own interpreter* — it exists locally regardless of git-checkout state. The bug is specifically "does not exist on the CI runner," which a same-machine worktree checkout cannot reproduce on its own.

**Correction applied (harness only, zero production/test-file changes from this step):**
- Ran `block_rl.py` from its original scratchpad location (outside the worktree) instead of copying it in, with `PYTHONPATH` pointed at the worktree root for import resolution — this avoids the untracked-file lint-coverage false positive while still resolving `import config` to the worktree's own module.
- Copied the already-built `frontend/dist/` (gitignored, present on this dev machine) into the sim worktree, mirroring the artifact-download step `ci.yml`'s `test` job performs before running pytest.
- To reproduce the interpreter-path failure faithfully without touching the real filesystem, used an unprivileged Linux mount namespace (`unshare --mount --map-root-user`) to bind-mount the real interpreter to a shadow path (used to run pytest itself) and bind-mount `/dev/null` over the *original* hardcoded path only inside that private mount namespace — invisible to, and with zero effect on, the rest of the system (confirmed: `python --version` outside the namespace was unaffected throughout).

With this correction, Step B's pre-fix run reproduced **exactly** the 3 named failures and no others — see Verification below.

None of the three landed fixes changed as a result of this correction; it only affected how the *simulation* was constructed, in service of the plan's own instruction to "STOP and report" if the harness were not faithful. All corrections were scoped to the throwaway `/tmp` worktree and scratchpad tooling — no repo file outside the three named test files was touched.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema changes were introduced. The threat register's three `mitigate` items (interpolate only `sys.executable`, quote it, remove the developer-path disclosure, keep the crosswalk stand-in fully offline) were all applied as specified.

## Verification

**Pre-fix CI-sim (faithful clean-checkout simulation, harness fidelity proven):**
```
FAILED tests/test_cron.py::test_daily_sh_failure_is_non_zero_notifies_once_and_lets_later_steps_run
FAILED tests/test_crosswalk.py::test_resolve_by_name_returns_na_for_unknown_name
FAILED tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff
3 failed, 376 passed, 32 skipped, 392 warnings in 4.36s
```
Exactly the 3 failures named in the plan, and no others.

**Post-fix CI-sim (same worktree, refreshed to post-fix HEAD `b3c7fe6`):**
```
378 passed, 33 skipped, 368 warnings in 4.65s
```
0 failed. The `32 -> 33` skipped and `376 -> 378` passed changes are exactly the 3 fixed tests moving out of `failed` (2 now run and pass; the leakage test now correctly skips, since `RAW` is legitimately absent on a clean checkout).

**Explicit outcome of the 3 targeted tests inside the post-fix sim (verbose, not inferred from the summary line):**
```
tests/test_cron.py::test_daily_sh_failure_is_non_zero_notifies_once_and_lets_later_steps_run PASSED [ 33%]
tests/test_crosswalk.py::test_resolve_by_name_returns_na_for_unknown_name PASSED [ 66%]
tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff SKIPPED [100%]
2 passed, 1 skipped in 0.97s
```
The cron test is explicitly PASSED (not skipped) in the simulation, as required.

**Local full suite baseline (measured fresh, before any edits):**
```
427 passed, 1 skipped, 1242 warnings in 292.89s (0:04:52)
```
(Single unrelated skip: `tests/test_cron.py:431` — `test_real_dotenv_if_present_is_mode_0600`, "no .env at repo root".)

**Local full suite (post-fix, same machine):**
```
427 passed, 1 skipped, 1242 warnings in 268.49s (0:04:28)
```
Pass count unchanged from baseline — no local regression.

**Targeted local run of the 3 fixed test files:**
```
48 passed, 1 skipped in 155.09s (0:02:35)
```
(The 1 skip is `test_leakage.py`'s unrelated `test_understat_features_are_rolled_not_raw` / other pipeline-artifact-gated tests being satisfied locally — all 3 target tests themselves RAN and PASSED, confirmed individually above and via the file-scoped run.)

**Ruff:**
```
$ ruff check .
All checks passed!
```

**Scope guard:**
```
$ grep -rn "envs/python314" tests/ | wc -l
0
$ git log --oneline -3 -- tests/ | wc -l
3
$ git status --porcelain -- data/ api/ models/ optimize/ predict/ features/ ops/ requirements*.txt .github/ | wc -l
4   # pre-existing untracked data/snapshots/*.parquet files, present before this task started, unrelated to it
```

**Worktree teardown:**
```
$ git worktree remove --force <sim-path>
$ git worktree list | wc -l
1
```

## Self-Check: PASSED

- FOUND: tests/test_cron.py (modified, committed `cb9e16c`)
- FOUND: tests/test_crosswalk.py (modified, committed `61a70dc`)
- FOUND: tests/test_leakage.py (modified, committed `b3c7fe6`)
- FOUND: cb9e16c in `git log --oneline --all`
- FOUND: 61a70dc in `git log --oneline --all`
- FOUND: b3c7fe6 in `git log --oneline --all`
- Worktree list confirmed back to 1 entry (`/home/sraja/fpl`)
