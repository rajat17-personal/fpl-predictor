---
phase: "9"
slug: "xp-model-optimizer-improvement-experiments"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-08"
validated: "2026-09-12"
---

# Phase 9 — Validation Strategy

> Per-phase validation contract. Retroactively audited and completed by /gsd-validate-phase on 2026-09-12.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config: `pytest.ini`, `testpaths = tests`) |
| **Config file** | `pytest.ini` |
| **Quick run command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_experiments.py tests/test_chips.py tests/test_crosswalk.py tests/test_rl_isolation.py -q` |
| **Full suite command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q` |
| **Estimated runtime** | ~300 seconds (full suite, 378 tests) |

Lint gate: `/home/sraja/miniconda3/envs/python314/bin/ruff check .`

---

## Sampling Rate

- **After every task commit:** Run the quick run command above
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~300 seconds

---

## Per-Task Verification Map

Phase 9 carries no REQ-IDs (ROADMAP records `Requirements: TBD`; every plan has `requirements: []`). The requirement column below therefore names each plan's coverage deliverables (Dx) from its SUMMARY frontmatter. All statuses verified green on 2026-09-12 (full suite 361→378 passed, 1 skipped).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | D1/D3: flag registry + captaincy ceiling column | T-09-01-01 | bad `FPL_EXPERIMENTS` token raises ValueError, never eval'd | unit | `pytest tests/test_experiments.py -q` (registry + ceiling-EV tests) | ✅ | ✅ green |
| 09-01-02 | 01 | 1 | D4: unattended launcher | T-09-01-02 | args quoted, dev-only local tool | unit | `pytest tests/test_experiments.py -q` (`test_experiment_run_sh_*`, added 2026-09-12) | ✅ | ✅ green |
| 09-01-03 | 01 | 1 | D2/D5: harness CLI + measured 6-season baseline | T-09-01-04 | baseline JSON records resolved flag dict; default-off protected by test | measurement | manual-only (see below) + `test_experiments_registry_default_off` | ✅ | ✅ green |
| 09-02-01 | 02 | 2 | D1: committed kiwi snapshot + attribution | — | PII spot-check recorded in data/external/README.md | unit | `pytest tests/test_crosswalk.py -q` (`test_kiwi_*`, 4 tests added 2026-09-12) | ✅ | ✅ green |
| 09-02-02 | 02 | 2 | D2: player-identity crosswalk | — | player_code uniqueness asserted (anti join-corruption) | unit | `pytest tests/test_crosswalk.py -q` (6 tests) | ✅ | ✅ green |
| 09-02-03 | 02 | 2 | D3: external benchmark reading | — | no-network default mode | measurement | manual-only (see below) | ✅ | ✅ green |
| 09-03-01..03 | 03 | 3 | D1–D4: lambda sweep, adoption verdict, capt_mc gate | — | flag stays off per verdict | unit + measurement | `test_capt_ceiling_and_capt_mc_flags_stay_off`; runs manual-only | ✅ | ✅ green |
| 09-04-01 | 04 | 3 | D1: scored_schedule (chips_v2) | — | provably blind to realised points / beyond visibility window | unit | `pytest tests/test_chips.py -q` (7 tests) | ✅ | ✅ green |
| 09-04-02 | 04 | 3 | D2: WC isolated delta | — | v1 season total behaviour-preserving | unit | `test_wc_chip_delta_recorded_against_zero_transfer_hold` | ✅ | ✅ green |
| 09-04-03 | 04 | 3 | D3: hysteresis sweep + verdict | — | flag stays off per verdict | measurement | manual-only (see below) | ✅ | ✅ green |
| 09-05-01 | 05 | 4 | D1: Dixon-Coles ratings leakage-safe | — | expanding-window fit, no future matches | unit | `test_team_strength_ratings_reproducible_from_prior_matches` | ✅ | ✅ green |
| 09-05-02 | 05 | 4 | D2: pipeline join row-preserving | — | unconditional compute, harness-side gating | integration | `pytest tests/test_leakage.py -q` | ✅ | ✅ green |
| 09-05-03 | 05 | 4 | D3: decision-time horizon graft, no ts_* in FIXTURE_CTX | — | future ratings never carried forward | unit | `test_fixture_ctx_no_ts_columns` (added 2026-09-12) | ✅ | ✅ green |
| 09-06-01 | 06 | 5 | D1: package-legitimacy gate | supply-chain (D-12) | human approval recorded verbatim | human gate | manual-only (see below) | ✅ | ✅ green |
| 09-06-02 | 06 | 5 | D2: RL lockfile production isolation | supply-chain (D-09) | requirements-rl unreachable from Dockerfile/CI | unit | `pytest tests/test_rl_isolation.py -q` (3 tests, added 2026-09-12) | ✅ | ✅ green |
| 09-06-03 | 06 | 5 | D3: FplStrategyEnv + reward equivalence | — | reward reuses backtest.season scoring, anti-Pitfall-4 proof | unit | `pytest tests/test_rl_env.py -q` (6 tests) | ✅ | ✅ green |
| 09-07-01 | 07 | 5 | D1: three-way v1/v2/rl scheduler toggle | — | rl+chips_v2 together hard-exits naming both | unit | 5 `resolve_scheduler`/`run_season` tests in test_experiments.py | ✅ | ✅ green |
| 09-07-02 | 07 | 5 | D2: MaskablePPO trainer, train-before-evaluate split | — | no future season in training set | unit | `test_train_seasons_for_*` (3 tests, added 2026-09-12) | ✅ | ✅ green |
| 09-07-03 | 07 | 5 | D3: D-02 gate spent, RL rejected | — | flag stays off per verdict | measurement | manual-only (see below) | ✅ | ✅ green |
| 09-08-01 | 08 | 6 | D1: Understat fetcher + crosswalk tier | T-09-08-05 | whole-token fixup rule (anti-spoofing); kill switch | unit | `test_understat_kill_switch_no_op_when_disabled` (added 2026-09-12) + test_crosswalk.py | ✅ | ✅ green |
| 09-08-02 | 08 | 6 | D2: us_* rolled-not-raw leakage | — | shift(1)-then-roll only | unit | `test_understat_features_are_rolled_not_raw` | ✅ | ✅ green |
| 09-08-03 | 08 | 6 | D3/D4: gating helper + adoption verdict | — | flag stays off per verdict | unit + measurement | 3 gating tests; adoption run manual-only | ✅ | ✅ green |
| 09-09-01 | 09 | 6 | D1: FotMob fetcher + kill switch | — | shape validation raises named-key error; NaN-not-zero | unit | `test_fotmob_kill_switch_no_op_when_disabled` (added 2026-09-12) | ✅ | ✅ green |
| 09-09-02 | 09 | 6 | D2/D3: fm_* leakage + gating branch | — | shift(1)-then-roll only | unit | `test_fotmob_features_are_rolled_not_raw`; `test_feature_gating_{drops,keeps}_fm_family_*` (added 2026-09-12) | ✅ | ✅ green |
| 09-09-03 | 09 | 6 | D4–D6: fotmob verdict, FBref spike, ledger close | — | no new scraping-host infra (D-04) | measurement + human | manual-only (see below) | ✅ | ✅ green |
| 09-10-01 | 10 | 7 | D1: final combined run vs D-05 bar | — | shipped default config unchanged | measurement | manual-only (see below) | ✅ | ✅ green |
| 09-10-02 | 10 | 7 | D2/D3: export contract + no-wiring invariant | T-09-10-01 | schema drift fails by name | unit | `test_export_contract_file_set_and_key_sets`, `test_no_adopted_experiment_flags_needed_product_wiring` | ✅ | ✅ green |
| 09-10-03 | 10 | 7 | D4: Phase F ledger closed | — | — | docs check | manual-only (see below) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 stubs needed — pytest/ruff were in place before the phase; every gap found by the 2026-09-12 audit was filled directly (see audit trail).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 6-season baseline + all adoption/sweep walk-forward runs | 09-01 D5, 09-02 D3, 09-03 D1/D3, 09-04 D3, 09-05 D3 (adoption), 09-07 D3, 09-08 D4, 09-09 D4, 09-10 D1 | Multi-minute-to-hour harness measurements; plan 09-01 explicitly forbids shelling full walk-forward runs into the unit suite; result artifacts live under gitignored `data/processed/experiments/` | `scripts/experiment_run.sh <tag> [--seasons CSV] [--experiments SPEC]`, poll the printed log for `[wf] tag=<tag>`, read `data/processed/experiments/wf_<tag>.json`; judged numbers are recorded in IMPROVEMENTS.md Phase F |
| RL package-legitimacy gate | 09-06 D1 | D-12 requires a genuine human supply-chain decision (gate=blocking-human by design); decision "Approve all four (Recommended)" recorded in SUMMARY + STATE.md | Re-run `pip index versions` + PyPI JSON cross-check if pins ever change; require fresh human approval |
| Understat/FotMob adoption noise-band judgments | 09-08 D4, 09-09 D4 | Verdicts rest on judging small deltas (+16, +1) against the harness's ~50-point SE — human judgment per the summaries' own `human_judgment: true` flags | Review IMPROVEMENTS.md Phase F rows; re-run adoption tags if the baseline moves |
| FBref access spike | 09-09 D5 | Environmental browser-based conclusion (3 consistent Chrome hangs + 2 control checks); not mechanically checkable | `python -m data.fbref --scrape` restricted to one season; compare against the 2026-09-08 evidence in IMPROVEMENTS.md before investing further |
| Phase F ledger closure | 09-09 D6, 09-10 D4 | One-off docs assertions over IMPROVEMENTS.md (no `pending` cells, D-01..D-16 audit present); brittle as a permanent test | `grep -c pending` the Phase F table; confirm Decisions audit + "What this phase did not resolve" sections present |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none remained after audit)
- [x] No watch-mode flags
- [x] Feedback latency < 300s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-12

---

## Validation Audit 2026-09-12

| Metric | Count |
|--------|-------|
| Gaps found | 8 |
| Resolved | 8 |
| Escalated | 0 |

Gaps resolved by 17 new regression tests (all green; full suite 378 passed, 1 skipped after fill):

1. `fm_*` feature-gating branch — `tests/test_experiments.py` (2 tests)
2. Understat kill-switch no-op — `tests/test_experiments.py` (1 test)
3. FotMob kill-switch no-op — `tests/test_experiments.py` (1 test)
4. RL lockfile production isolation (D-09) — `tests/test_rl_isolation.py` (new file, 3 tests)
5. `FIXTURE_CTX` contains no `ts_*` column (leakage guard) — `tests/test_leakage.py` (1 test)
6. `train_seasons_for` train-before-evaluate split — `tests/test_rl_env.py` (3 tests)
7. `experiment_run.sh` launcher contract — `tests/test_experiments.py` (2 tests)
8. Committed kiwi snapshot presence + 8-column schema — `tests/test_crosswalk.py` (4 tests)

Note: 3 pre-existing ruff F401/F811-class errors in `tests/test_ci_cd_artifacts.py` (unmodified by this audit) were observed and left untouched — they predate this validation pass and belong to later-milestone work.
