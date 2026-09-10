---
phase: "10"
slug: "xp-experiment-follow-ups"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-10"
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
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q -x`
- **After every plan wave:** Run `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD — filled by planner | — | — | TBD | — | N/A | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] TBD — planner to enumerate per-experiment regression tests (pattern: `tests/test_experiments.py`, `tests/test_crosswalk.py` from Phase 9)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| fplreview scoreboard capture | TBD | Site blocks automated access (HTTP 403, confirmed) | Manual capture per todo design |
| Long walk-forward / RL training runs | TBD | Multi-hour compute; validated via ledger JSON assertions after run | `tail -f` the experiment log, then run ledger assertion commands |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
