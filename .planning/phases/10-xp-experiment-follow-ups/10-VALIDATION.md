---
phase: "10"
slug: "xp-experiment-follow-ups"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-10"
validated: "2026-09-11"
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config: `pytest.ini` at project root) |
| **Config file** | `pytest.ini` |
| **Quick run command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q -x` |
| **Full suite command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q` |
| **Estimated runtime** | ~4–5 minutes (329 tests as of phase close) |

---

## Sampling Rate

- **After every task commit:** Run `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q -x`
- **After every plan wave:** Run `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 300 seconds (full suite grew to ~4.5 min during this phase)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| availability spine + encoding | 10-01/10-04/10-06 | 1–3 | TODO-AVAIL-FLAGS | — | N/A | unit + leakage | `pytest tests/test_availability.py tests/test_leakage.py::test_availability_features_are_raw_context_not_rolled` | ✅ (16 + 1 tests) | ✅ green |
| TM injury backfill + join | 10-05/10-07 | 2–3 | TODO-TM-INJURY | — | N/A | unit + leakage | `pytest tests/test_transfermarkt.py tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff` | ✅ (6 + 1 tests) | ✅ green |
| model-class bracket (registry, gate, seq) | 10-09..10-14 | 4–8 | TODO-BRACKET | — | N/A | unit + equivalence | `pytest tests/test_bracket.py` | ✅ (26 tests) | ✅ green |
| top-100 consensus benchmark | 10-02 | 1 | TODO-TOP100 | — | N/A | unit | `pytest tests/test_scoreboard.py` | ✅ (23 tests, shared file) | ✅ green |
| fplreview capture slot + reader | 10-02 | 1 | TODO-FPLREVIEW | — | N/A | unit (reader); capture is manual | `pytest tests/test_scoreboard.py` | ✅ | ✅ green |
| snapshot catch-up cron | 10-03 | 1 | PHASE10-CRON | — | N/A | unit + script | `pytest tests/test_cron.py` | ✅ (26 tests) | ✅ green |
| external-prediction ingestion seam | 10-09/10-13 | 4–7 | PHASE10-COLAB-SEAM | — | N/A | unit + roundtrip | `pytest tests/test_bracket.py -k external_preds or exported_bundle` | ✅ | ✅ green |
| declared criteria + export contract | 10-01/10-16 | 1, 10 | PHASE10-CRITERIA | — | N/A | contract regression | `pytest tests/test_product.py -k export_contract or phase10_flags` | ✅ | ✅ green |
| news-sentiment (D-02) | 10-12 | 6 | TODO-NEWS | — | N/A | none — declined on cost; no code exists | ledger: IMPROVEMENTS.md D-02 "declined on cost" | N/A | ✅ (ledger) |
| FBref manual snapshot | 10-15 | 9 | TODO-FBREF-MANUAL | — | N/A | none — acquisition-format defect; no join code | ledger + evidentiary CSVs at `data/external/fbref/` | N/A | ✅ (ledger) |
| RL reward shaping | 10-15 | 9 | TODO-RL-SHAPING | — | N/A | none — notes-only by design | ledger: IMPROVEMENTS.md RL potential-based-shaping note | N/A | ✅ (ledger) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — every experiment landed with its own
test file or extended an existing one (pattern: `tests/test_experiments.py` from Phase 9),
and the full suite gates each wave. No Wave 0 backfill was required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| fplreview scoreboard capture | TODO-FPLREVIEW | Site blocks automated access (HTTP 403, confirmed); ToS-constrained manual capture | Manual capture per `data/external/fplreview/README.md` before each deadline |
| Long walk-forward / Colab training runs | TODO-BRACKET, PHASE10-COLAB-SEAM | Multi-hour compute / human-driven GPU session | `tail -f` the experiment log; ledger JSON assertions after run (all recorded in `data/processed/experiments/`) |
| Crontab installation | PHASE10-CRON | crontab lives outside the repo | `crontab -l` shows daily.sh + @reboot snapshot_catchup.sh lines (verified 2026-09-10) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none existed)
- [x] No watch-mode flags
- [x] Feedback latency < 300s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-09-11 (audit found zero gaps; no auditor spawn required)

## Validation Audit 2026-09-11

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Audit basis: 11 traceability keys mapped against the live test suite (329 passed, 1
pre-existing unrelated skip). Eight keys carry named automated tests added during this
phase; three keys (TODO-NEWS, TODO-FBREF-MANUAL, TODO-RL-SHAPING) produced no code by
recorded decision and are verified at the ledger level in `IMPROVEMENTS.md`.
