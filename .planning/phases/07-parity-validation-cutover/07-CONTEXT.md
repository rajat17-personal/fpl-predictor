# Phase 7: Parity Validation & Cutover - Context

**Gathered:** 2026-09-07
**Status:** Ready for planning

<domain>
## Phase Boundary

The React site becomes the live site without breaking a single weekly recommendation cycle (CUT-01). Three things must become TRUE: (1) React and vanilla run side by side through one complete gameweek cycle — deadline → live → finished — serving the same live JSON exports; (2) every page's output is compared across that cycle, with each difference either matched to `PARITY-DEVIATIONS.md` or fixed, leaving zero unexplained deltas; (3) vanilla is retired only after the cycle passes, with the weekly recommendations flowing uninterrupted throughout.

The only real code change in this phase is the **production serving seam**: today a plain `uvicorn api.main:app` serves vanilla `web/` at `/`, and the React build (`frontend/dist`) is only servable in fixture mode — which also swaps to frozen data and so cannot be the side-by-side vehicle. Phase 5's D-06 promised cutover as "a config/env flip"; this phase builds that flip. Everything else is comparison tooling, process, and real calendar time — the roadmap flags this as an execution checklist gated on a full gameweek, not a research problem.

Invariant: `web/data/` is the pipeline↔site export contract and survives forever. "Retiring vanilla" means only the vanilla site *assets* (`web/*.html`, `web/assets/`), never the data directory.

Out of this phase: live deployment/hosting (next milestone), auth/payments, any new site features. The local WSL cron (daily 02:30, weekly Fri 08:00 UTC) is production and must not be disturbed.

</domain>

<decisions>
## Implementation Decisions

### Side-by-side topology
- **D-01:** **Production env seam + two processes.** Add a small env seam in `api/main.py` (e.g. `FPL_FRONTEND=react`) that, in *production* mode (no fixture vars), mounts `frontend/dist` at `/` and live `web/data` at `/data`. Run a second uvicorn on :8001 with it; vanilla stays untouched on :8000. Rejected: subpath mount at `/beta` (requires Vite `base` + Router `basename` rework the E2E suite doesn't expect) and flipping `/` to React before validation (inverts the vanilla-is-authoritative invariant). — **Reversibility:** reversible — the seam is additive; default behavior unchanged until the cutover flip.
- **D-02:** **React is the daily driver during the validation week.** The user does their real FPL week (xP, captains, rate, transfers) on :8001, dropping to :8000 vanilla to verify. Dogfooding surfaces real-usage defects; vanilla remains authoritative if anything looks off.
- **D-03:** **On-demand sessions, not 24/7.** A small start/stop script boots both uvicorns for usage/comparison sessions. Cron updates the JSON exports regardless of server uptime, so nothing is lost while they're down.
- **D-04:** **The seam is proven in the Docker image this phase.** Extend the CI container smoke test with one assertion: a container started with the react-mode env serves `index.html` from `frontend/dist`. The deploy milestone inherits a proven flip, not an assumed one.

### Comparison method & evidence
- **D-05:** **Hybrid comparison: script + eyeball.** A Playwright script visits both sites and extracts normalized page data — table cell values, sort order, banner/copy text, key figures — and diffs it, filtering deltas already recorded in `PARITY-DEVIATIONS.md`. Layout, visuals, and interactive flows get a manual checklist pass. Full scripted flow-diffing rejected (throwaway build cost; E2E already pins solver rendering); manual-only rejected (8 pages × 3 passes by eye misses subtle value/sort drift).
- **D-06:** **`PARITY-REPORT.md` is the evidence artifact**, committed in the phase dir and appended at each cycle stage: date, GW state, per-page verdict, and every delta found → ledger # / fixing commit / new ledger entry. The cutover decision cites this document; the phase verification consumes it.
- **D-07:** **Three full 8-page passes**, one per cycle stage: after the pre-deadline Friday export, mid-gameweek while matches are live/settling, and after the GW finishes and the scoreboard runs. Each stage exercises a different data state (deadline banner, in-flight scores, final standings).
- **D-08:** **Interactive flows get one manual same-input session:** entry **6980093** loaded on both sites in the same session — rate, one solve with identical locks, one 2-GW plan — tiles/transfers/XI compared and recorded in the report. Both processes share the same model and pool, so same-session results should be identical; a cross-site mismatch is a defect.

### Cutover mechanics & rollback
- **D-09:** **Retirement = flip the seam's default.** After the cycle passes, a plain `uvicorn api.main:app` serves `frontend/dist` at `/`; vanilla's site assets stay in the repo, frozen and unmaintained, still servable via the env var as an instant rollback. Deleting `web/` site assets is a later cleanup, not this phase. — **Reversibility:** reversible by design — rollback is the same env flip.
- **D-10:** **Rollback policy: data-wrong only, 1-GW window.** Flip back to vanilla only if the React site shows wrong data or blocks a weekly action; cosmetic bugs are fixed forward. The escape hatch is considered live for one further gameweek after cutover, then vanilla is dead weight awaiting deletion.
- **D-11:** **Lockstep and the ledger both close at the flip.** Vanilla is frozen (no further edits), the `check-tokens.mjs` vanilla-lockstep assertions are removed, and `PARITY-DEVIATIONS.md` gets a closing entry marking cutover — it becomes a historical record, no longer a gate. — **Reversibility:** costly — resurrecting the lockstep discipline after post-cutover React-only changes would require re-porting them to vanilla; the rollback window (D-10) is why vanilla stays *frozen* rather than *maintained*.
- **D-12:** **Docker image keeps both frontends this phase.** Only the serving default flips; the Dockerfile keeps COPYing `web/` and `frontend/dist`. Slimming the image is deploy-milestone work.

### Cycle timing & failure policy
- **D-13:** **The validation cycle is the first full gameweek whose pre-deadline Friday export lands after the build work is done** (seam, diff script, report scaffolding) — likely GW5. A cycle must start at its export; no joining mid-week. No fixed calendar commitment — a build slip moves the cycle, it doesn't fail the phase.
- **D-14:** **Defects fix forward, never restart the cycle.** An unexplained delta is fixed immediately, the affected page(s) re-compared, and the cycle continues — the bar is "zero unexplained deltas by cycle end". Only a fix that lands too late to re-observe its data state extends validation into the next GW *for that page*.
- **D-15:** **Cutover is a human gate** (Phase 5 D-14 style `checkpoint:human`): Claude assembles the completed `PARITY-REPORT.md` and stages the flip commit; the user reviews the report and personally approves the flip. Never auto-flip.
- **D-16:** **Criterion-3 evidence is cron-green citations:** each `PARITY-REPORT.md` stage entry records that the daily/weekly cron runs since the last pass completed green (`data/cron.log` + absence of `ops.notify` alerts). No new pipeline machinery — Phase 6's alerting spine is the watcher.

### Claude's Discretion
- Exact env var name/values for the seam, port numbers, and the start/stop script's shape and location.
- The diff script's internals: which fields per page are extracted, normalization rules, how ledger-known deltas are encoded/filtered, where it lives (likely `e2e/` or `scripts/`).
- The manual checklist's contents and the `PARITY-REPORT.md` layout.
- How the seam composes with the existing fixture-mode branch in `api/main.py` (fixture mode must keep working unchanged — the E2E suite depends on it).
- Whether the flip commit also updates README/docs references to the vanilla site.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The parity contract (what "explained delta" means)
- `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` — the ledger: 8 numbered intentional deltas, the lockstep-palette record, and the append discipline. This phase treats every listed entry as explained and every unlisted difference as a defect; D-11 closes it at the flip.
- `.planning/ROADMAP.md` §Phase 7 — goal, the three success criteria, "execution checklist gated on real calendar time"
- `.planning/REQUIREMENTS.md` — CUT-01 text

### The serving seam (where the only production code change lands)
- `api/main.py` — the mount split at the bottom of the file: production catch-all serves `web/`; the `_FIXTURE_ROOT` branch serves `frontend/dist` + frozen `/data` (registration order matters — `/data` before `/`). The new seam is a third, production-mode branch beside these; the fixture branch must be untouched.
- `tests/test_fixture_mode.py` — the unset-env assertion guarding today's default mount; extend for the new seam.
- `.planning/phases/04-e2e-regression-suite/04-CONTEXT.md` — D-02: the mount-switch decision this phase's cutover was designed to reuse; D-01/D-03 fixture topology that must keep working.

### Cutover inheritance from CI/Docker
- `.planning/phases/05-container-build-ci-pipeline/05-CONTEXT.md` — D-06 (both frontends baked into the image; cutover = env flip, no image rework), D-07 (smoke-test shape D-04 extends), D-14 (human push gate pattern D-15 mirrors)
- `Dockerfile` + the smoke-test wiring in `.github/workflows/ci.yml` — where the react-mode smoke assertion (D-04) lands
- `frontend/scripts/check-tokens.mjs` — the vanilla-lockstep assertions D-11 removes at the flip

### The weekly cycle being protected
- `scripts/weekly.sh`, `scripts/daily.sh` — the cron jobs whose green runs are criterion-3 evidence (D-16); `run_step` + `ops.notify` alerting is the existing watcher
- `web/data/` — the live export contract both sites serve; must be consumed unchanged

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The fixture-mode mount branch in `api/main.py` is the exact pattern for the new seam (StaticFiles mounts, registration order, `check_dir` semantics) — the production react branch is a sibling, not a modification
- `e2e/playwright.config.ts` + the Phase 4 Playwright toolchain — the diff script (D-05) can reuse the installed `@playwright/test` runner and browser; no new packages expected (package-legitimacy gate applies if any are)
- `scripts/verify_hardening.sh` — precedent for boot-a-real-uvicorn-and-assert scripts; the start/stop script (D-03) and any seam verification can follow its shape
- `scripts/smoke_test.sh` + CI docker job — the place D-04's react-mode assertion extends
- Phase 6's `ops.notify` + `data/cron.log` per-step accounting — criterion-3 evidence already exists, just needs citing (D-16)

### Established Patterns
- `checkpoint:human` gates for actions only the user performs (Phase 5 D-14: pushes; here D-15: the cutover flip)
- Deviation-ledger discipline: any React behavior change made while fixing a delta must either match vanilla or get a ledger row in the same commit — until D-11 closes the ledger
- `web/data/*.json` fetched at runtime, never bundled — the react-mode mount must serve `/data` from the live directory, mirroring what the dev proxy and fixture mode already do
- Conda env `python314` for all Python; `npm --prefix frontend run build` (`tsc -b`) is the real typecheck

### Integration Points
- `api/main.py` bottom-of-file mount logic — the seam (D-01) and later the default flip (D-09)
- `.github/workflows/ci.yml` docker job — react-mode smoke assertion (D-04)
- `frontend/scripts/check-tokens.mjs` — lockstep assertions removed at flip (D-11)
- `.planning/phases/07-parity-validation-cutover/PARITY-REPORT.md` — new evidence artifact (D-06), consumed by phase verification and the D-15 human gate
- Next milestone inherits: a proven env flip in the container, a frozen vanilla awaiting deletion, and the closed ledger as the historical parity record

</code_context>

<specifics>
## Specific Ideas

- The React site should earn cutover by being *used*, not just inspected — the user runs their real FPL week on it (D-02), with vanilla as the reference standing by
- "Zero unexplained deltas" is provable, not remembered: every claim in the cutover decision traces to a `PARITY-REPORT.md` line citing a ledger #, a fixing commit, or a green cron run
- Same-session solver comparison uses the user's real team, entry **6980093** (never entry 1, per PROJECT.md)
- The phase is calendar-gated by design; plans should model the waiting (build wave → validation passes spread across the gameweek → human-gated flip), not pretend it can compress

</specifics>

<deferred>
## Deferred Ideas

- **Deleting vanilla site assets (`web/*.html`, `web/assets/`)** — after the 1-GW rollback window (D-10), likely next milestone's cleanup
- **Slimming the Docker image to React-only** — deploy milestone, alongside hosting (D-12)
- **Arming Actions schedulers / model delivery to CI** — next milestone (carried from Phase 5 D-12)

</deferred>

---

*Phase: 7-Parity Validation & Cutover*
*Context gathered: 2026-09-07*
