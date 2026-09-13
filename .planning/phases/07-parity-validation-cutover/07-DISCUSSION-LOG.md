# Phase 7: Parity Validation & Cutover - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-07
**Phase:** 7-Parity Validation & Cutover
**Areas discussed:** Side-by-side topology, Comparison method & evidence, Cutover mechanics & rollback, Cycle timing & failure policy

---

## Side-by-side topology

| Option | Description | Selected |
|--------|-------------|----------|
| Two processes, env seam | New production env seam (e.g. FPL_FRONTEND=react) mounts frontend/dist at / and web/data at /data; second uvicorn on :8001; vanilla untouched on :8000 | ✓ |
| One process, React at /beta | Mount dist under /beta in the :8000 process; requires Vite base + Router basename rework reverted at cutover | |
| One process, React at /, vanilla at /legacy | Flip authority before validation passes — inverts the vanilla-authoritative invariant | |

**User's choice:** Two processes, env seam (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| React as daily driver | Real weekly FPL usage on :8001, vanilla for verification | ✓ |
| Vanilla as daily driver | React only visited during comparison sessions | |
| Strict parallel use | Every action performed on both sites | |

**User's choice:** React as daily driver (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| On-demand sessions | Start/stop script boots both uvicorns when needed; cron updates exports regardless | ✓ |
| Continuous via cron @reboot | Both processes 24/7 for the cycle | |

**User's choice:** On-demand sessions (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Extend container smoke test | CI asserts react-mode env serves index.html from frontend/dist | ✓ |
| Local only, container next milestone | Verify the container flip when hosting exists | |

**User's choice:** Extend container smoke test (Recommended)

---

## Comparison method & evidence

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid: script + eyeball | Playwright script diffs normalized page data filtering ledger deltas; visuals/flows manual checklist | ✓ |
| Manual checklist only | Per-page eyeball checklist at each stage | |
| Full scripted diff | Script everything including solver flows | |

**User's choice:** Hybrid: script + eyeball (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| PARITY-REPORT.md per stage | Committed report appended per cycle stage; cutover decision cites it | ✓ |
| Report + raw captures | Also archive extracted JSON snapshots | |
| Verification notes only | Fold into VERIFICATION.md at the end | |

**User's choice:** PARITY-REPORT.md per stage (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| 3 full passes | Full 8-page pass at pre-deadline export, live, and finished stages | ✓ |
| 2 full + live spot-check | Full at deadline and finished; spot-check live | |
| Continuous (every daily cron) | Diff after every daily cron | |

**User's choice:** 3 full passes (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Manual same-input session | Entry 6980093 on both sites same session: rate, one solve with identical locks, one 2-GW plan | ✓ |
| Scripted flow diff too | Drive both solver flows scripted and diff | |
| Trust E2E, skip flow comparison | No vanilla-vs-React flow comparison | |

**User's choice:** Manual same-input session (Recommended)

---

## Cutover mechanics & rollback

| Option | Description | Selected |
|--------|-------------|----------|
| Flip default, keep assets | Default serves frontend/dist; web/ assets frozen in repo as env-flip rollback; delete later | ✓ |
| Flip default + delete assets | Delete vanilla site assets in the same phase | |
| Keep vanilla at /legacy | Vanilla reachable at a subpath indefinitely | |

**User's choice:** Flip default, keep assets (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Data-wrong only, 1 GW window | Rollback only for wrong data / blocked weekly action; escape hatch live one further GW | ✓ |
| Any defect, until next milestone | Flip back for any regression; vanilla flip-able until deploy milestone | |
| No formal window | Keep the env var with no stated policy | |

**User's choice:** Data-wrong only, 1 GW window (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Both close at flip | Vanilla frozen; check-tokens lockstep assertions removed; ledger gets closing entry | ✓ |
| Lockstep ends, ledger stays open | Keep appending to the ledger post-cutover | |
| Keep both until deletion | Maintain both disciplines until assets deleted | |

**User's choice:** Both close at flip (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both this phase | Image keeps COPYing web/ and frontend/dist; only serving default flips | ✓ |
| Drop vanilla from image at flip | Remove web/ site assets from image (keep web/data) | |

**User's choice:** Keep both this phase (Recommended)

---

## Cycle timing & failure policy

| Option | Description | Selected |
|--------|-------------|----------|
| First full GW after build | Cycle = first GW whose pre-deadline Friday export lands after seam/script/report work is done (likely GW5) | ✓ |
| Target GW5 explicitly | Commit to GW5 dates now | |
| Whenever, even mid-GW | Count a partial week | |

**User's choice:** First full GW after build (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Fix forward, re-verify page | Fix immediately, re-compare affected pages, continue the cycle | ✓ |
| Any defect restarts the cycle | One unexplained delta invalidates the gameweek | |
| Severity-based restart | Data-wrong restarts; cosmetic fixes forward | |

**User's choice:** Fix forward, re-verify page (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Human gate on the report | Claude assembles PARITY-REPORT.md and stages the flip commit; user reviews and approves | ✓ |
| Auto-flip on clean report | Flip lands without separate approval | |

**User's choice:** Human gate on the report (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Cron green log in report | Each stage entry cites green daily/weekly cron runs (cron.log + no ops.notify alerts) | ✓ |
| Implicit — alerts would fire | Rely on Phase 6 alerting alone | |
| Extra pipeline checks | New monitoring around the cron | |

**User's choice:** Cron green log in report (Recommended)

## Claude's Discretion

- Env var name/values, port numbers, start/stop script shape and location
- Diff script internals: fields extracted per page, normalization, ledger-delta encoding, location
- Manual checklist contents and PARITY-REPORT.md layout
- How the seam composes with the fixture-mode branch (fixture mode must keep working unchanged)
- Whether the flip commit also updates README/docs references

## Deferred Ideas

- Deleting vanilla site assets — after the 1-GW rollback window, likely next milestone
- Slimming the Docker image to React-only — deploy milestone
- Arming Actions schedulers / model delivery to CI — next milestone (carried from Phase 5 D-12)
