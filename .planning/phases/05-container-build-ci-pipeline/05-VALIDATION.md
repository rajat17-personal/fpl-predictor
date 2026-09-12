---
phase: "5"
slug: "container-build-ci-pipeline"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-09-04"
validated: "2026-09-12"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend/infra), vitest (frontend), Playwright (e2e) |
| **Config file** | `pytest.ini` (repo root; disables playwright/seleniumbase plugins) |
| **Quick run command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest tests/test_ci_cd_artifacts.py -q` |
| **Full suite command** | `/home/sraja/miniconda3/envs/python314/bin/python -m pytest -q` |
| **Estimated runtime** | ~1s quick · ~5–8 min full suite |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_ci_cd_artifacts.py -q`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~480 seconds (full suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | SEC-02 | — | Human approves uv/ruff package legitimacy before install | checkpoint | — (human decision gate) | — | ✅ resolved 2026-09-04 |
| 05-01-02 | 01 | 1 | SEC-02 | — | Locks fully hash-pinned; dev lock chains runtime lock | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k lock -q` | ✅ | ✅ green |
| 05-01-03 | 01 | 1 | CI-01 | — | ruff gate covers every tracked Python file, no suppressions | unit | `python -m pytest tests/test_reliability.py -k ruff -q` | ✅ | ✅ green |
| 05-02-01 | 02 | 1 | CI-03 | — | Two-stage Dockerfile: hashed install, libstdc++6+libgomp1, non-root, no secrets/model in image | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k dockerfile -q` | ✅ | ✅ green |
| 05-02-01b | 02 | 1 | CI-03 | — | .dockerignore excludes secret/model/data categories, re-includes frontend/dist only | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k dockerignore -q` | ✅ | ✅ green |
| 05-02-02 | 02 | 1 | CI-03 | — | smoke_test.sh valid, executable, ordered fail-fast guards | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k smoke -q` | ✅ | ✅ green |
| 05-03-01..03 | 03 | 2 | CI-01, CI-02, CI-04, CI-05 | — | ci.yml: 5-job needs chain, concurrency, least-privilege perms, main-only publish, 40-hex SHA pins, smoke-before-Trivy, single continue-on-error | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k ci_yml -q` | ✅ | ✅ green |
| 05-04-01 | 04 | 2 | SEC-04 | — | daily/weekly.yml dispatch-only, py3.14, hashed installs, SHA-pinned, github-actions[bot] identity | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k scheduler -q` | ✅ | ✅ green |
| 05-04-02 | 04 | 2 | SEC-04 | — | Chrome installer absent; .gitignore carries .gsd/.venv/venv/.docker rules; workflow secrets via `secrets.` expressions | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k "gitignore or installer" -q` + `tests/test_cron.py::test_workflow_secret_assignments_all_use_a_secrets_expression` | ✅ | ✅ green |
| 05-05-01 | 05 | 3 | CI-04 | — | preflight.sh valid, executable, mirrors CI chain | unit | `python -m pytest tests/test_ci_cd_artifacts.py -k preflight -q` | ✅ | ✅ green |
| 05-05-02 | 05 | 3 | CI-04, CI-05 | — | First real CI run green; GHCR image published; Trivy report-only findings visible | manual | — (see Manual-Only) | — | ✅ human-verified 2026-09-05 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. `tests/test_ci_cd_artifacts.py` (added retroactively by this validation audit, 32 tests) persists the plans' one-off `<verify>` gates as repeatable regression tests.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| uv/ruff package-legitimacy approval | SEC-02 | Blocking-human checkpoint by design (05-01 Task 1) | Resolved 2026-09-04 (verbatim: "approve-both") — no re-test needed |
| Real container build + smoke run | CI-03 | No container runtime in dev environment; CI's `image` job re-runs it on every push | `docker build -t local/fpl:smoke . && bash scripts/smoke_test.sh local/fpl:smoke` |
| First real CI run green, GHCR publish | CI-04 | Runs on developer's GitHub credential (D-14); agent has no gh CLI/remote | Verified 2026-09-05: PR run green on 3rd attempt (fixes `11cd68e`, `65cd2e7`); main run published to GHCR (Actions run 33950933101) |
| Trivy report-only findings visible in Security tab | CI-05 | Lives in GitHub Security tab, not queryable locally | Verified 2026-09-05: 187 report-only findings (triage deferred per D-10) |
| Branch protection on main requires ci.yml jobs (D-15) | CI-04 | Repo settings not queryable locally; **not yet explicitly confirmed** (05-05 coverage item D4) | Check Settings → Branches (or `gh api repos/:owner/:repo/branches/main/protection`) before Phase 6 closes CI-04 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (retroactive: `tests/test_ci_cd_artifacts.py`)
- [x] No watch-mode flags
- [x] Feedback latency < 480s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-12 (retroactive audit via /gsd-validate-phase)

---

## Validation Audit 2026-09-12

| Metric | Count |
|--------|-------|
| Gaps found | 6 |
| Resolved | 6 |
| Escalated | 0 |

Retroactive audit: phase 5's plans verified artifacts with one-off grep/YAML assertion commands that were never persisted. `tests/test_ci_cd_artifacts.py` (32 tests) now re-encodes those gates: lock hash-pinning (SEC-02), Dockerfile/.dockerignore invariants (CI-03), ci.yml job graph/SHA pins/Trivy ordering/publish gating (CI-01/02/04/05), scheduler modernization (SEC-04), and shell-script guards (CI-04). Full suite green after addition (360 passed, 1 skipped). Remaining manual-only items are inherently human-gated (checkpoints, real-infra CI run) — branch protection (D-15) is the one still-unconfirmed item, carried in Manual-Only.
