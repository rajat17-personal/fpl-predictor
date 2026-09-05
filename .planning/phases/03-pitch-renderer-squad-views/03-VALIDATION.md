---
phase: "3"
slug: "pitch-renderer-squad-views"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: false
wave_0_complete: true
created: "2026-09-02"
validated: "2026-09-03"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest (backend) |
| **Config file** | `frontend/vitest.config.ts`, `pytest.ini` |
| **Quick run command** | `cd frontend && npx vitest run <file>` |
| **Full suite command** | `cd frontend && npx vitest run` + `python -m pytest -x -q` (conda env python314) |
| **Estimated runtime** | ~25s frontend (357 tests), ~3s backend (67 tests) |

---

## Sampling Rate

- **After every task commit:** targeted `vitest run` on touched test files + `npm run typecheck`
- **After every plan wave:** full `vitest run` + `bash scripts/verify_frontend_build.sh` + root pytest
- **Before `/gsd-verify-work`:** Full suite must be green — confirmed 2026-09-03 (357/357 frontend, 67/67 backend)
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | PITCH-02 | — | N/A | unit | `npx vitest run src/lib/formation.test.ts src/lib/squadJoin.test.ts src/components/pitch/Pitch.test.tsx src/routes/Team.test.tsx` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | PITCH-02, UIX-01 | — | N/A | unit | `npx vitest run src/components/pitch/PlayerCard.test.tsx src/components/pitch/Kit.test.tsx src/components/pitch/kitMap.test.ts` | ✅ | ✅ green |
| 03-01-03 | 01 | 1 | PITCH-01, UI-07 | — | non-affiliation disclaimer present | unit | `npx vitest run src/components/PageShell.test.tsx` | ✅ | ✅ green |
| 03-02-01 | 02 | 2 | PITCH-03, UIX-03 | — | no persistence of entry IDs | unit | `npx vitest run src/routes/Team.test.tsx src/components/team/SquadTab.test.tsx` | ✅ | ✅ green |
| 03-02-02 | 02 | 2 | UIX-03 | — | Chips tab fires zero /api/ requests | unit | `npx vitest run src/components/team/ChipsTab.test.tsx src/components/ChipTimeline.test.tsx` | ✅ | ✅ green |
| 03-02-03 | 02 | 2 | PITCH-03 | — | N/A | unit | `npx vitest run src/components/team/RateTab.test.tsx src/lib/pairMoves.test.ts` | ✅ | ✅ green |
| 03-03-01 | 03 | 3 | PITCH-04 | — | N/A | unit | `npx vitest run src/components/RateDiff.test.tsx` | ✅ | ✅ green |
| 03-03-02 | 03 | 3 | PITCH-04 | — | vanilla error copy, no silent retries | unit | `npx vitest run src/components/PlanTransfers.test.tsx` | ✅ | ✅ green |
| 03-03-03 | 03 | 3 | PITCH-04 | — | N/A | unit | `npx vitest run src/components/team/RateTab.test.tsx` | ✅ | ✅ green |
| 03-04-01 | 04 | 3 | PITCH-03 | — | lock/exclude ephemeral, never persisted | unit | `npx vitest run src/components/team/SquadTab.test.tsx` | ✅ | ✅ green |
| 03-04-02 | 04 | 3 | PITCH-03 | — | solve request bounds mirror server | unit | `npx vitest run src/components/SolveControls.test.tsx` | ✅ | ✅ green |
| 03-04-03 | 04 | 3 | PITCH-03 | — | ordering-safe solve lifecycle | unit | `npx vitest run src/components/SolveResultsBar.test.tsx src/components/team/SquadTab.test.tsx` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. (vitest + testing-library harness pre-dated the phase; no Wave 0 installs needed.)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile-responsive pitch and tables render correctly at narrow widths | UI-07 | Layout/reflow is a visual property; jsdom has no real layout engine, so an automated assertion would only restate CSS classes | Open `/team` at 375px width (devtools device toolbar): formation rows wrap without horizontal scroll, cards stay legible, bench row visible; check xP/League tables scroll inside their own containers |
| Pitch/card visual appearance matches UI-SPEC (colors, badges, spacing) | PITCH-02 | Visual fidelity check deferred to end-of-phase UAT per `workflow.human_verify_mode` | `/gsd-verify-work 3` walks through the queued human-checks from 03-01 |
| Trademark posture: neutral kits + non-affiliation disclaimer read as intended | PITCH-01 | Legal-adjacent judgment call, not a DOM assertion | Review footer disclaimer and `docs/decisions/pitch-kit-sourcing.md` during UAT |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none)
- [x] No watch-mode flags (`vitest run` one-shot everywhere)
- [x] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter — withheld: UI-07 + two visual checks are manual-only by nature

**Approval:** validated 2026-09-03 (partial — 12 automated task verifications green, 3 manual-only items routed to UAT)

## Validation Audit 2026-09-03

| Metric | Count |
|--------|-------|
| Gaps found | 1 (UI-07 automated coverage) |
| Resolved | 0 |
| Escalated | 1 (manual-only — visual/layout, not automatable in jsdom) |
