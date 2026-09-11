---
phase: 10-xp-experiment-follow-ups
verified: 2026-09-11T16:20:00Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: No — initial verification
---

# Phase 10: xP Experiment Follow-ups Verification Report

**Phase Goal:** Act on the eight `resolves_phase: 10` todos plus three infrastructure items
carried from Phase 9's experiment program: run the Tier-1 availability/injury experiments
against pre-declared criteria, open and close the D-03 model-class bracket, evaluate the D-02
news-sentiment trigger, close the D-04 dead-tail items (FBref manual snapshot, RL shaping
note), fix the snapshot capture gap, and add the diagnostic benchmark columns — every verdict
recorded in IMPROVEMENTS.md, the weekly product contract unchanged.

**Verified:** 2026-09-11
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `availability_flags` (TODO-AVAIL-FLAGS): built, measured against the pre-declared D-09 dual criterion, REJECTED and recorded | ✓ VERIFIED | `data/processed/experiments/wf_avail_base_2526.json`/`wf_avail_on_2526.json` and `benchmark_tier1_base.json`/`benchmark_tier1_avail.json` on disk show byte-identical model+chips (2172) and Spearman (0.3832) between off/on — matches IMPROVEMENTS.md's stated "neither leg moved at all" verdict exactly, not merely narrated |
| 2 | `transfermarkt_injury` (TODO-TM-INJURY): built, measured on the standard 6-season protocol, REJECTED (-20) and recorded | ✓ VERIFIED | `data/processed/experiments/wf_tm_base6.json` (2262) / `wf_tm_on6.json` (2242) present; `data/external/transfermarkt/injury_spells.csv` (12,503 spells) and `tm_id_map.csv` committed; leakage test `tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff` independently recomputes from real `player_gw.parquet`, passes |
| 3 | D-03 model-class bracket (TODO-BRACKET): opened, 7 candidates (lgbm baseline + ridge/xgb/catboost/mlp/rnn/transformer) gated mechanically, closed at 0/7 advance | ✓ VERIFIED | All 7 `bracket_gate_<candidate>.json` files exist with real measured `spearman_xp_med` values (checked `bracket_gate_mlp.json` directly: 0.3942, pooled); `tests/test_bracket.py::test_gate_advance_rule_is_mechanical_over_the_seven_recorded_candidates` asserts HOLD against the live gate files, not synthetic data — passes |
| 4 | D-02 news-sentiment trigger (TODO-NEWS): evaluated against the locked 0.500 threshold, fired (0.3874), routed to a human checkpoint, DECLINED ON COST recorded distinctly from not-triggered | ✓ VERIFIED | `data/processed/experiments/benchmark_tier1.json` exists (0.3874); `data/news.py`/`tests/test_news.py` correctly absent (never built, per the DECLINE decision) — matches plan 10-12's own "declined, not not-triggered" ledger distinction |
| 5 | D-04 dead-tail 1, FBref manual snapshot (TODO-FBREF-MANUAL): acquired (all 10 seasons) then dropped on a verified acquisition-format defect, evidence retained | ✓ VERIFIED | `data/external/fbref/README.md` plus CSVs committed; `data/fbref.py` has no `load_manual_snapshot`/join code (correctly absent — no adoption number was ever attempted against the defective source per the ledger) |
| 6 | D-04 dead-tail 2, RL reward shaping (TODO-RL-SHAPING): notes-only, no training | ✓ VERIFIED | `git log` shows no commit touching `optimize/rl_env.py`/`optimize/rl_train.py` in plan 10-15's range; IMPROVEMENTS.md's potential-based-shaping note present with the Ng et al. 1999 citation |
| 7 | Snapshot capture gap fixed (PHASE10-CRON) | ✓ VERIFIED | `scripts/snapshot_catchup.sh` is a real, substantive idempotent catch-up script (not a stub); `crontab -l` on this machine shows both the `30 2 * * *` daily.sh line AND the `@reboot` catch-up line actually installed, matching D-08's "installed and verified live" claim |
| 8 | Diagnostic benchmark columns (TODO-TOP100, TODO-FPLREVIEW) added, diagnostic-only | ✓ VERIFIED | `data/fpl_standings.py`/`data/fplreview.py` exist and are genuinely wired into `predict/scoreboard.py` (`import data.fpl_standings`/`import data.fplreview`, `mae_fplreview`/`spearman_fplreview` columns added conditionally) |
| 9 | PHASE10-COLAB-SEAM: external-prediction ingestion seam built and validated before any Colab candidate existed | ✓ VERIFIED | `backtest/walk_forward.py::load_external_predictions` performs real schema/season/ground-truth-drop/row-count/implausibility validation (read directly, not narrated); successfully consumed by `wf_bracket_rnn_2526.json`/`wf_bracket_transformer_2526.json` |
| 10 | PHASE10-CRITERIA: every Phase 10 adoption criterion declared in IMPROVEMENTS.md before any adoption-deciding run | ✓ VERIFIED | `git log` shows `f417eaa docs(10-01): declare Phase 10 adoption criteria before any measuring run` predates every adoption-run commit (10-04 through 10-14); IMPROVEMENTS.md's "Declared criteria" section carries the 2026-09-10 date |
| 11 | Every verdict recorded in IMPROVEMENTS.md; all eight `resolves_phase: 10` todos named with a resolution; no unfilled cell remains | ✓ VERIFIED | IMPROVEMENTS.md's "## Phase G" section (lines 1449-2107) contains the full 9-row results table (no `pending` cells), the "Todos resolved" table naming all 8 by file stem, and the D-01..D-21 decisions audit table with 21 rows, each with an outcome and evidence citation |
| 12 | Weekly product contract unchanged | ✓ VERIFIED | Direct `grep` of the real, currently-on-disk `web/data/*.json` files for `"av_`/`"tm_`/`"nw_`/`"bracket_` prefixes returns zero matches; `tests/test_product.py::test_phase10_flags_default_off_leaves_export_contract_unchanged` performs the identical check as an automated regression and passes in the full suite run |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/availability.py` + `tests/test_availability.py` | as-of-deadline availability spine | ✓ VERIFIED | Exists, substantive; D-10 safe-fallback test (`test_missing_snapshot_degrades_to_nan_not_raise`) is a real assertion, not a stub |
| `data/transfermarkt.py` + `data/external/transfermarkt/injury_spells.csv`/`tm_id_map.csv` | injury backfill + committed snapshot | ✓ VERIFIED | Present; 12,503 real spells committed |
| `models/bracket/{registry,classical,gbdt,gate,deep,sequence,recurrent,transformer}.py` | 6-candidate bracket infrastructure | ✓ VERIFIED | All present; `registry.CANDIDATES` covers all 7 `config.BRACKET_CANDIDATES` names |
| `models/bracket/export.py` | ONNX export (D-17), only if a torch candidate adopted | ✓ VERIFIED (correctly absent) | No torch candidate cleared `GATE_MARGIN`; absence matches the ledger's "D-17 correctly NOT triggered" |
| `colab/bracket_deep.ipynb`, `colab/README.md` | D-13/D-14 Colab handoff | ✓ VERIFIED | Present |
| `data/fpl_core_insights.py` + `data/external/fpl_core_insights/README.md` | D-05 vendored 2025-26 backfill | ✓ VERIFIED | Present |
| `data/fpl_standings.py`, `data/fplreview.py` + `data/external/fplreview/README.md` | Tier-3 diagnostics | ✓ VERIFIED | Present, wired into `predict/scoreboard.py` |
| `scripts/snapshot_catchup.sh` + `tests/test_cron.py` | PHASE10-CRON | ✓ VERIFIED | Present, substantive, installed live in this machine's crontab |
| `data/news.py`, `tests/test_news.py` | only if D-02 build path taken | ✓ VERIFIED (correctly absent) | DECLINED ON COST — never built, matches the ledger |
| `data/fbref.py` (manual snapshot loader) | only if FBref acquisition adopted | ✓ VERIFIED (correctly absent join code) | CSVs acquired and committed as evidence; no join/adoption code, matching the "Drop — acquisition-format defect" decision |
| `data/processed/experiments/wf_combined_phase10.json` | final combined run | ✓ VERIFIED | `model+chips` = 2262, `experiments` all-False — bit-identical to the ledger's claimed numbers |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `data/transfermarkt.py::attach` | `data/build_table.py` | inline call in `build()` | ⚠️ WIRED, with a correctness bug (see Anti-Patterns) | Wired and functioning for the frozen-features-parquet measurement path used by every adoption run; CR-01 (code review) identifies a staleness bug specific to the live incremental-rebuild path — does not affect this phase's measured verdicts or the default-off product contract |
| `config.EXPERIMENTS` | `backtest/walk_forward.py::apply_experiment_feature_gating` | flag-gated column dropping | ✓ WIRED | `tests/test_experiments.py::test_feature_gating_drops_tm_family_when_off` / `..._keeps_tm_family_when_on` pass |
| `crontab @reboot` | `scripts/snapshot_catchup.sh` | installed cron line | ✓ WIRED | Confirmed live via `crontab -l` on this machine |
| Colab-exported parquet | `backtest/walk_forward.py::load_external_predictions` | `--external-preds` CLI flag | ✓ WIRED | Consumed for both `wf_bracket_rnn_2526.json` and `wf_bracket_transformer_2526.json` |
| `predict/scoreboard.py` | `data/fpl_standings.py` / `data/fplreview.py` | direct import + conditional column write | ✓ WIRED | Confirmed via source read |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| TODO-AVAIL-FLAGS | 10-01/10-04/10-06/10-08 | Availability flags into P(play) | ✓ SATISFIED | REJECTED, D-09 dual criterion — recorded |
| TODO-TM-INJURY | 10-05/10-07/10-08 | Transfermarkt injury history flag | ✓ SATISFIED | REJECTED (-20) — recorded |
| TODO-BRACKET | 10-09..10-14 | Model-class bracket | ✓ SATISFIED | 0/7 advance, closed with numbers |
| TODO-NEWS | 10-08/10-12 | Conditional news-sentiment | ✓ SATISFIED | Trigger fired, DECLINED ON COST |
| TODO-TOP100 | 10-02 | Top-100 consensus benchmark | ✓ SATISFIED | Built, diagnostic-only, wired |
| TODO-FPLREVIEW | 10-02 | fplreview scoreboard benchmark | ✓ SATISFIED | Built, manual-assisted, wired |
| TODO-FBREF-MANUAL | 10-15 | Manual FBref snapshot | ✓ SATISFIED | Acquired then dropped (defect), evidence committed |
| TODO-RL-SHAPING | 10-15 | RL reward-shaping revisit | ✓ SATISFIED | Notes-only, recorded |
| PHASE10-CRON | 10-03 | Snapshot capture gap | ✓ SATISFIED | Built, tested, installed live |
| PHASE10-COLAB-SEAM | 10-09/10-13 | External-prediction ingestion seam | ✓ SATISFIED | Built, validated, round-trip-proven, used |
| PHASE10-CRITERIA | 10-01 | Pre-declared adoption criteria | ✓ SATISFIED | Committed before any adoption run (commit-order confirmed) |

Per the prompt's own framing, none of these 11 keys are mapped in `.planning/REQUIREMENTS.md` — confirmed by direct grep (zero hits). This is the phase's declared, deliberate traceability shape (its spec is the ROADMAP.md phase entry plus the 16 plans' own `requirements:` frontmatter), not a gap.

### Behavioral Spot-Checks / Independent Reproduction

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Full test suite | `python -m pytest -q` | `329 passed, 1 skipped, ... in 276.51s`, exit 0 | ✓ PASS — independently re-run in this verification session (not merely trusted from context), matches the pre-verified figure exactly |
| Product contract, real files | `grep '"av_\|"tm_\|"nw_\|"bracket_' web/data/*.json` | zero matches | ✓ PASS |
| `wf_combined_phase10.json` model+chips | direct JSON read | `2262`, all `experiments` False | ✓ PASS — matches ledger exactly |
| `bracket_gate_mlp.json` | direct JSON read | `spearman_xp_med: 0.3942`, `granularity: pooled` | ✓ PASS — matches ledger exactly |
| Crontab installation | `crontab -l` | both lines present | ✓ PASS |
| Debt-marker scan | `grep -nE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across 20 phase-10-touched files | zero matches | ✓ PASS |
| requirements-experiments isolation | `grep -rl requirements-experiments .github/workflows/` | zero matches | ✓ PASS — matches D-16's claim |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `data/build_table.py:204-207`, `data/transfermarkt.py:619-671`, `data/availability.py:130-148` | CR-01 (10-REVIEW.md) | `tm_mod.attach()` is called inline mid-build against the in-memory `full` frame, but internally re-reads `gw_deadlines()` from the *on-disk* (stale, previous-run) `player_gw.parquet` — the newest gameweek's `tm_injured` baseline is unconditionally set to 0.0 ("not injured") before the deadline-resolvability check, so a genuinely injured player in the most-recent gameweek can be reported not-injured | ⚠️ Warning (advisory, not a phase-goal blocker) | Does not affect any of this phase's 9 measured adoption verdicts (those ran against a frozen `features.parquet`, not the live incremental-rebuild path) and does not affect the live weekly product contract (`transfermarkt_injury` stays default-off, so these columns are computed but never consumed as model features). It is a real correctness bug that will surface the moment the flag is ever flipped on, or if any future diagnostic reads `tm_*` columns directly — confirmed independently by re-reading the cited source lines, not merely trusting 10-REVIEW.md's narrative. Recommend a follow-up fix (thread `raw=full` through `gw_deadlines`, as 10-REVIEW.md's own fix proposes) before ever adopting the flag. |
| `config.py:265-270` | stale comment | Comment on `bracket_mlp`/`bracket_rnn`/`bracket_transformer` still says "reserved for a future plan... not yet constructible" even though plans 10-11/10-13 built and gated all three this phase | ℹ️ Info | Cosmetic doc staleness only; `models/bracket/registry.py`'s own docstring correctly states all 7 candidates are now covered — no functional impact |
| `config.py:306-332` | WR-02 (10-REVIEW.md) | `resolve_experiments()` silently drops named flags when combined with `"none"`/`"all"` tokens | ℹ️ Info | Pre-existing experiment-CLI ergonomics issue, not introduced to serve this phase's goal claims; carried forward from 10-REVIEW.md for completeness |

No 🛑 Blocker anti-patterns found. No unreferenced `TBD`/`FIXME`/`XXX` debt markers in any phase-10-touched file.

### Human Verification Required

None. All truths resolved to VERIFIED via direct artifact inspection, independent test re-execution, and live-machine state checks (crontab). No behavior-dependent state-transition truths in this phase's scope required a runtime behavioral test beyond what the existing, independently-re-run test suite already exercises.

### Gaps Summary

No gaps block phase-goal achievement. All eight `resolves_phase: 10` todos and all three infrastructure requirement keys (PHASE10-CRON, PHASE10-COLAB-SEAM, PHASE10-CRITERIA) are genuinely resolved in the codebase — not merely narrated in IMPROVEMENTS.md. Every number the ledger cites was independently cross-checked against the actual on-disk artifact that produced it (`wf_combined_phase10.json`, `wf_tm_base6.json`/`wf_tm_on6.json`, `benchmark_tier1*.json`, `bracket_gate_*.json`) and matched exactly. The weekly product contract is provably unchanged, confirmed both by the automated regression test and by a direct grep of the real, currently-served `web/data/*.json` payloads. The full pytest suite (329 tests) was independently re-run in this verification session (not merely trusted from prior context) and passed with exit code 0, matching the previously-reported figure exactly.

One genuine code-quality finding from 10-REVIEW.md (CR-01, a Transfermarkt-injury staleness bug in the live incremental-rebuild path) is carried forward here as a Warning. It does not invalidate any of this phase's measured verdicts (which ran against a frozen features snapshot) or the product-contract truth (the flag stays default-off), so it does not block this phase's goal achievement — but it is a real bug worth a small follow-up fix before `transfermarkt_injury` is ever reconsidered for adoption.

---

_Verified: 2026-09-11_
_Verifier: Claude (gsd-verifier)_
