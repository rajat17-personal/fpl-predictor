---
phase: 09-xp-model-optimizer-improvement-experiments
reviewed: 2026-09-09T02:59:29Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - IMPROVEMENTS.md
  - backtest/benchmark_external.py
  - backtest/season.py
  - backtest/walk_forward.py
  - config.py
  - data/build_table.py
  - data/external/README.md
  - data/external/kiwi/ID_Dictionary.csv
  - data/external/kiwi/kiwi_projections_2021-22.csv
  - data/external/kiwi/kiwi_projections_2022-23.csv
  - data/external/kiwi/kiwi_projections_2023-24.csv
  - data/fotmob.py
  - data/id_crosswalk.py
  - data/team_strength.py
  - data/understat.py
  - features/engineer.py
  - models/captaincy.py
  - optimize/chips.py
  - optimize/rl_env.py
  - optimize/rl_train.py
  - requirements-rl.in
  - requirements-rl.txt
  - scripts/experiment_run.sh
  - tests/test_chips.py
  - tests/test_crosswalk.py
  - tests/test_experiments.py
  - tests/test_leakage.py
  - tests/test_product.py
  - tests/test_rl_env.py
  - web/data/captains.json
  - web/data/meta.json
  - web/data/squad.json
  - web/data/xp_table.json
findings:
  critical: 0
  warning: 6
  info: 3
  total: 9
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-09-09T02:59:29Z
**Depth:** standard
**Files Reviewed:** 27 source files (+4 generated JSON exports and 4 committed CSV/README data snapshots spot-checked, not line-by-line reviewed per instructions)
**Status:** issues_found

## Summary

This phase is an experiment-harness phase: eight opt-in flags (`config.EXPERIMENTS`), all default-off, plus three new data-enrichment sources (team_strength, understat, fotmob), a captaincy ceiling-EV column, an xP-scored chip scheduler, and a time-boxed RL policy trainer. All eight experiments were measured and rejected against their own pre-declared bars, and the code that implements them ships default-off and unused by the product path — which meaningfully limits the blast radius of anything found here (no adopted flag flips model behaviour in production today).

No BLOCKER-level defects were found: no injection vectors, no hardcoded secrets, no leakage introduced into the shipped default configuration (the new leakage-safety tests — `test_team_strength_ratings_reproducible_from_prior_matches`, `test_understat_features_are_rolled_not_raw`, `test_fotmob_features_are_rolled_not_raw` — correctly assert the shift(1)-then-rolling discipline this codebase depends on, and the code they test matches their claims). The findings below are WARNING/INFO-level robustness, contract-consistency, and maintainability issues, concentrated in the three new enrichment fetchers and the RL action-space constants.

## Warnings

### WR-01: `data/understat.py::fetch_season` can raise uncaught, breaking its own "never raises" contract

**File:** `data/understat.py:160`
**Issue:** The docstring for `fetch_season` states: "Returns None on total failure; never raises (optional enrichment must never break the pipeline)." The two upstream calls (`client.league(...).get_match_data(...)` and `.get_player_data(...)`) are correctly wrapped in `try/except Exception`, but the very next line —

```python
match_ids = {m["id"] for m in matches}
```

— sits **outside** that `try` block (line 160, after the `finally` at line 156). If `understatapi`'s response shape ever changes (a match dict missing `"id"`, or `matches` containing a non-dict entry), this raises an uncaught `KeyError`/`TypeError` straight out of `fetch_season()`, contradicting its documented contract. Compare with the sibling module `data/fotmob.py`, whose equivalent path (`_fetch_season_matches` → `_require(payload, ["fixtures", "allMatches"], list, what)`) is fully guarded and returns `None` on any shape mismatch — the two modules were built to the same D-11-style discipline but this one line was missed in `data/understat.py`.
**Fix:**
```python
try:
    match_ids = {m["id"] for m in matches}
except (TypeError, KeyError) as exc:
    print(f"  [miss] {season}: malformed match payload ({exc})")
    return None
```

### WR-02: Row-count-corruption guard in `attach()` is downgraded to a silently-loggable print in `build_table.py`

**File:** `data/build_table.py:154-180` (team_strength/understat/fotmob join blocks); mirrors `data/team_strength.py:288-289`, `data/understat.py:279-281`, `data/fotmob.py:312-314`
**Issue:** `team_strength.attach()`, `understat.attach()`, and `fotmob.attach()` each carry an explicit `AssertionError` guard ("a many-to-many join here corrupts every backtest") added specifically because a name-join once silently multiplied `player_gw` rows up to 16x and corrupted a whole walk-forward run before being caught (documented in `IMPROVEMENTS.md` Phase E and repeated in each module's own comments). `data/build_table.py` wraps every one of these three `attach()` calls in a bare `except Exception as exc: print(...)`, which — while it does not let corrupted data through (the exception fires before `attach()` returns, so `full` is never reassigned) — reduces a designed hard-stop safety net to a `print()` line that is easy to miss in an unattended cron log (`scripts/daily.sh`/`weekly.sh`). This is consistent with this codebase's existing "optional enrichment must never break the pipeline" convention (already applied the same way to `odds`/`fbref`), but it means a *second* occurrence of the exact corruption class this project has already suffered once would again surface only as an easily-overlooked log line, not a failed CI run or a loud alert.
**Fix:** Not necessarily a code change to `build_table.py` itself (the optional-enrichment convention is deliberate project policy per CLAUDE.md) — but consider distinguishing `AssertionError` from ordinary `Exception` at these three call sites so a row-count-corruption assertion propagates (or is logged at a visibly higher severity / written to a `data/cron.log`-monitored sentinel) rather than being caught by the same generic branch as "source unreachable":
```python
except AssertionError:
    raise   # data corruption is not an "optional source missing" case
except Exception as exc:
    print(f"  [team_strength] skipped ({exc})")
```

### WR-03: `optimize/rl_env.py` `TRANSFER_CAPS` magic-number offset is decoupled from `HIT_BUDGET`

**File:** `optimize/rl_env.py:46-48`
**Issue:**
```python
CHIPS_ORDER = ("-", "wc", "fh", "bb", "tc")
TRANSFER_CAPS = tuple(range(0, config.MAX_FREE_TRANSFERS + 3))    # 0..7: FTs + a 2-hit budget
HIT_BUDGET = 2           # extra hits beyond free transfers a legal action may take
```
`TRANSFER_CAPS`'s upper bound (`MAX_FREE_TRANSFERS + 3` = 8, i.e. values 0..7) is only correct because `HIT_BUDGET` happens to be 2 (`max_ft(5) + hit_budget(2) + 1` for range's exclusive end = 8). `HIT_BUDGET` is declared *after* `TRANSFER_CAPS` and the "+3" is a bare literal with no reference to `HIT_BUDGET`. `build_action_mask` separately computes `ft_cap = free_transfers + HIT_BUDGET` (line 112) and masks any `cap > ft_cap`. If `HIT_BUDGET` is ever tuned (e.g. to 3) without also updating the "+3" literal, `build_action_mask` would compute a legal `ft_cap` of 8 for `free_transfers=5`, but `TRANSFER_CAPS` would not contain the value 8 at all — the policy's action space would silently lose its top legal transfer count with no error anywhere, and nothing in `tests/test_rl_env.py` would catch the mismatch (its budget test only checks `free_transfers=1`, i.e. `ft_cap=3`, well inside either bound).
**Fix:** Reorder so `TRANSFER_CAPS` is derived from `HIT_BUDGET` directly:
```python
HIT_BUDGET = 2
TRANSFER_CAPS = tuple(range(0, config.MAX_FREE_TRANSFERS + HIT_BUDGET + 1))
```

### WR-04: RL observation's "horizon" signal reuses the *current* gameweek's xP for every future fixture instead of that fixture's own prediction

**File:** `optimize/rl_env.py:78-84`
**Issue:**
```python
horizon_xp = 0.0
for code in squad:
    base = float(by_code.get(code, 0.0))     # <- fixed at the CURRENT gw only
    fixture_gws = gws_by_code.get(code, set())
    for k in range(HORIZON):
        if gw + k in fixture_gws:
            horizon_xp += (DECAY ** k) * base
```
`by_code` is built from `cur = preds[preds.gw == gw]` — i.e. `base` is always the player's predicted points **for the current gameweek**, not for gameweek `gw + k`. The loop then adds this same current-week value, decayed, for every future gameweek the player has a fixture in, rather than that future gameweek's own predicted value. The intent (per the module docstring, "gameweeks of decay-forward own form horizon signal") appears to be a genuine forward-looking value signal; as implemented it only encodes "does this player have upcoming fixtures soon" weighted by *this week's* form, not next week's. This does not cause any leakage (no future outcome is read), but it is a real modelling bug in the policy's own input features, which — given `rl_strategy` was independently rejected on its own harness numbers — may partly explain why the trained policy under-performed (a materially weaker observation than intended). Low product risk today since `rl_strategy` defaults off and is not used anywhere else, but worth fixing before this signal is ever revisited.
**Fix:** Look up each future gameweek's own predicted value instead of reusing `base`:
```python
horizon_xp = 0.0
for code in squad:
    fixture_gws = gws_by_code.get(code, set())
    for k in range(HORIZON):
        fut_gw = gw + k
        if fut_gw in fixture_gws:
            fut_by_code = preds[preds.gw == fut_gw].groupby("player_code")[XP_COL].sum()
            horizon_xp += (DECAY ** k) * float(fut_by_code.get(code, 0.0))
```
(or precompute a `gw -> Series` map once outside the per-step call for efficiency).

### WR-05: `data/id_crosswalk.py::resolve_by_name` docstring describes fixups as a last-resort tier, but the code applies them first, to every input

**File:** `data/id_crosswalk.py:235-264`
**Issue:** The docstring says fixups are tried "then, `_NAME_FIXUPS` (applied to the raw name before normalising, for a source's persistent misses across ALL three tiers)" — implying fixups are a fallback applied only after the three name-key tiers have already failed. The actual code:
```python
def resolve_by_name(names: pd.Series) -> pd.Series:
    fixed = names.replace(_NAME_FIXUPS)   # applied to EVERY name, up front
    keys = _norm(fixed)
    ...
```
rewrites every input name via `_NAME_FIXUPS` unconditionally, *before* any tier is attempted, not after all three tiers fail. In practice this is probably harmless for the curated entries in `_NAME_FIXUPS` (their replacement targets are specifically chosen to resolve via tier 3, `_fpl_name_index()`), but it means a name that would have resolved correctly and more specifically via tier 1 (theFPLkiwi's own `name_key`) under its original spelling is silently redirected before tier 1 ever sees it, if that name happens to also be a `_NAME_FIXUPS` key. This is a documentation/implementation mismatch that could mislead a future maintainer debugging a wrong-player join.
**Fix:** Either update the docstring to describe the actual (upfront, universal) behaviour, or change the implementation to apply `_NAME_FIXUPS` only to names that fail all three tiers, matching the documented contract.

### WR-06: `understat.py`/`fotmob.py` join key collapses on same-day double-fixtures and NaT dates

**File:** `data/understat.py:266-276`, `data/fotmob.py:299-309`
**Issue:** Both `attach()` implementations build a join key as `season|player_code|match_date` (calendar date only, no time). If a player's two fixtures in the same gameweek (or, for fotmob, in general) happen to fall on the same calendar date — or if `kickoff_time`/`match_date` fails to parse and becomes `"NaT"` on both sides for the same player+season — the join key collapses two distinct fixtures onto one key. Because the enrichment-side table is de-duplicated on this key before merging (`drop_duplicates(subset="_key")`), the row-count assertion (`if len(merged) != len(full): raise AssertionError`) is **not** tripped (the left join still returns exactly `len(full)` rows), but both of the colliding player-fixture rows on the `full` side would silently receive the *same* enrichment values, which is a correctness bug the row-count guard cannot catch by construction. Low real-world frequency (same-day PL doubles are rare), but the guard's blind spot is worth documenting since this is precisely the failure class this codebase has been burned by before.
**Fix:** Include `fixture_id` in the join key where available instead of (or in addition to) the calendar date, since `full` already carries `fixture_id` and it uniquely identifies each match:
```python
full["_key"] = (full["season"].astype(str) + "|"
                + full["player_code"].astype("Int64").astype(str)
                + "|" + full["fixture_id"].astype("Int64").astype(str))
```
(would require carrying a comparable match identifier through from the Understat/FotMob side, e.g. joining fixture-level date ranges once to resolve `fixture_id`, or at minimum asserting no `(season, player_code, match_date)` collisions exist within `full` before relying on this key.)

## Info

### IN-01: `backtest/season.py::_pick_lists`/`_score` redefine `capt_code`/`captain` inconsistently across branches (readability)

**File:** `backtest/season.py:239-240, 259, 268-269`
**Issue:** In the `wc`/`fh` branch, `capt_code = captain` is set immediately after `captain` is unpacked from `_pick_lists(r)` — a redundant alias (both names refer to the same value for the rest of that branch) that exists only because the non-chip branch further down uses the name `capt_code = r["captain_code"]` from a different result dict shape (`optimize_gw`'s `"captain_code"` vs `pick_squad`'s `is_captain==1` row). This isn't a bug, but the duplicate naming across branches is a minor readability hazard for future edits (easy to update one branch's `captain`/`capt_code` and miss the other).
**Fix:** No functional change needed; consider a short comment noting `capt_code` and `captain` are intentionally the same value in the wc/fh branch, to save a future reader the trace.

### IN-02: `benchmark_external.py::_reduce_projection_csv` positional column assumption has no independent regression test

**File:** `backtest/benchmark_external.py:98-140`
**Issue:** The reduction of theFPLkiwi's wide per-gameweek CSV to 8 tidy columns relies entirely on *positional* column indexing (`cols[label_idx[11] + 1]`), guarded only by a length assertion (`len(label_idx) < 12`). This is explicitly documented as fragile-by-necessity (column names repeat across blocks), but there is no unit test in `tests/` pinning this behaviour against a small synthetic CSV fixture — the only verification is the `--fetch` step's own printed summary and the eventual downstream MAE numbers in `IMPROVEMENTS.md`, which would not clearly localise a silent off-by-one in the column selection (it would just look like slightly worse MAE, easy to misattribute to something else).
**Fix:** Add a small unit test constructing a minimal synthetic CSV matching the documented 13-column layout (and the 12-column early-season variant) and asserting `_reduce_projection_csv` extracts the correct `proj_pts` value, so a future upstream layout change or edit to this function is caught immediately rather than silently degrading benchmark accuracy.

### IN-03: `optimize/rl_train.py::_TimeBoxCallback._held_out_score` runs a full-season replay on every eval tick without limiting overhead awareness

**File:** `optimize/rl_train.py:203-212`
**Issue:** `maybe_log()` is gated by `eval_every_steps` (once per PPO policy update, `n_steps=1024`), and each invocation replays an entire season gameweek-by-gameweek through `FplStrategyEnv` (itself calling the ILP solver every step). This is a deliberate, documented design choice (the anti-Pitfall-4 diagnostic) and not a bug, but it is worth flagging as a maintainability/cost note for anyone raising `--timesteps` well above the current wall-clock-capped regime (per `HYPERPARAMS`, an eval fires roughly every 1024 timesteps) — the eval overhead could become a non-trivial fraction of the time-box budget itself if `n_steps` is later reduced without revisiting `eval_every_steps`. Out of this review's correctness scope (performance is explicitly out of scope for v1), noted only because it interacts with D-16's wall-clock cap being the stated "real budget enforcement."
**Fix:** No action required now; if `HYPERPARAMS["n_steps"]` is ever lowered, consider decoupling `eval_every_steps` from it explicitly so eval overhead doesn't eat into the trained-policy budget the D-16 time-box is meant to protect.

---

_Reviewed: 2026-09-09T02:59:29Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
