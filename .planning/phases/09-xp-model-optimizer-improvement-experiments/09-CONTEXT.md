# Phase 9: xP Model & Optimizer Improvement Experiments - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Raise honest walk-forward season points from the current ~2,105–2,256 core toward ~2,300+, judged **exclusively** by the existing leakage-safe 6-season harness (`backtest/walk_forward.py`). The phase runs the full ranked experiment bundle from `.planning/research/XP-IMPROVEMENT-OPTIONS.md` in its recommended order: (1) external-projection benchmark, (2) captaincy/TC ceiling EV, (3) solver-scored chip scheduler v2, (4) Dixon-Coles/Poisson team-strength features, (5) RL-for-strategy layer (gated on 3), (6) enrichment data sources (Understat, FotMob, FBref). Everything already tested-and-rejected with numbers (ranking loss, CS sub-model, 3-state minutes, always-on multi-period MILP) is excluded. Every experiment lands opt-in behind a flag; defaults change only when the harness clears the experiment's pre-declared criterion.

Depends on Phase 8 (self-hosted gameweek data capture) per ROADMAP.md.

</domain>

<decisions>
## Implementation Decisions

### Experiment sequencing & gates
- **D-01:** Fixed order, run everything — all six experiments run in the recommended order regardless of intermediate results. The benchmark (1) still runs first but its outcome does NOT prune the feature-accuracy experiments (4, 6); it informs interpretation only.
- **D-02:** RL layer stays in-phase but hard-gated: it is built only after chip scheduler v2 (3) lands and is measured, and it must beat the solver-scored scheduler on the same honest harness to earn adoption.
- **D-03:** All three enrichment sources are in scope: Understat npxG/xGChain/xGBuildup (via theFPLkiwi's ready-made FPL↔fbref↔FFScout ID maps), FotMob per-match defensive stats, and FBref. All enter as **features only, never sub-models** (CS sub-model rejection stands). Name→FPL ID mapping is the shared prerequisite.
- **D-04:** FBref scrape host = local WSL Chrome/Chromium installed **outside the repo** (never committed — preserves Phase 5's repo hygiene). Scrapes run manually/cron on this machine only; no scraper Docker image this phase.

### Adoption bar & success criteria
- **D-05:** Primary phase bar locked at mean core+chips season points ≥ **2,280** (current ≈2,256) across the 6-season walk-forward average — ≥ +25/season aggregate, outside the noise-band direction.
- **D-06:** Full per-experiment criteria set adopted from the research doc: captaincy capture ≥ +2 pts absolute over captain-by-mean; isolated WC value measured (currently unmeasured) and no chip's isolated value regresses its CI; `tests/test_leakage.py` extended for team-strength ratings (ratings at GW g reproducible from matches < g only); optimistic-vs-frozen A/B run for any horizon-touching change (the +337-vs-+40 discipline).
- **D-07:** Auto-adopt rule: each experiment pre-declares its criterion; when the adoption-deciding walk-forward run clears it outside the noise band, the flag flips default-on without a separate human sign-off. — **Reversibility:** reversible — a flag flip is one config change; the weekly product can revert to the prior default instantly.
- **D-08:** Failed experiments keep their code merged behind default-off flags, with numbers recorded in IMPROVEMENTS.md — the established rejected-with-numbers pattern. No code deletion.

### Dependencies & data acquisition
- **D-09:** RL stack (torch, sb3-contrib, gymnasium, etc.) enters via a **separate dev-only lockfile** (e.g. `requirements-rl.in`/`.txt`, compiled with `uv --generate-hashes` per D-01 of Phase 5). It is never merged into the production lockfiles, Docker image, or CI install path — the weekly product stays torch-free.
- **D-10:** External benchmark data (theFPLkiwi historical projection CSVs, their ID maps, any OpenFPL outputs used) is **committed as a snapshot** with source URLs + license attribution, so the benchmark is reproducible forever — same philosophy as the frozen E2E fixtures. — **Reversibility:** costly — committed data vintages live in git history permanently; keep the snapshot small (CSVs only, no model binaries).
- **D-11:** FotMob acquisition = direct unofficial JSON endpoints, polite: conservative rate limiting, on-disk caching, and a kill-switch flag. Accept it may break upstream; no browser automation for FotMob.
- **D-12:** The blocking-human package-legitimacy gate stays for **every** new PyPI package this phase (torch, sb3-contrib, gymnasium, and anything else). No pre-approvals; registry-verified approval at install time, as in Phases 1–5.

### Compute budget & A/B protocol
- **D-13:** A/B protocol = **independent + final combined**: each experiment A/Bs against the current default config independently; the winners then get one final combined walk-forward run, and that combined number is what the 2,280 bar (D-05) judges.
- **D-14:** Replica policy = fast iterate, full adopt: jitter replicas off (or minimal) during development iteration; every adoption-deciding run and the final combined run uses the full replica count for honest CIs.
- **D-15:** Compute runs on local WSL only; long runs (full-replica walk-forwards, RL training) launch as unattended overnight jobs with logs. No cloud spend.
- **D-16:** RL training is time-boxed with fixed seeds and pinned configs — a declared budget of a handful of overnight runs. If it hasn't beaten chip scheduler v2 on the honest harness within the box, it is recorded as rejected (per D-08); no open-ended tuning.

### Claude's Discretion
- Exact flag names, module layout for new code (e.g. `data/team_strength.py`, `backtest/benchmark_external.py`, `models/simulate.py`), and the hysteresis margin in chip scheduler v2.
- Quantile-first vs Monte-Carlo captaincy variant ordering (research doc suggests quantile first, MC only if quantiles move capture ≥ +2 pts — follow that unless evidence says otherwise).
- The concrete replica count constituting "full" (use the harness's existing default) and the exact RL time-box size within "a handful of overnight runs".
- Rate-limit values and cache layout for FotMob/Understat fetching.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Experiment menu, audit, and criteria
- `.planning/research/XP-IMPROVEMENT-OPTIONS.md` — the ranked options table, per-option implementation notes, leakage risks, the ADnocap/FPL-RL audit (2,918 is in-sample), and the success-criteria set this phase adopts verbatim (D-05/D-06).

### Prior tested/rejected ground truth
- `PLAN.md` (repo root) — Refinements + External data sections: the +337-optimistic-vs-+40-honest leakage finding, odds/set-piece adoption history, "WC fixed-slot timing is weak".
- `IMPROVEMENTS.md` (repo root) — Phases A–E adopted/rejected list with numbers (ranking loss −55, CS sub-model −50, 3-state minutes, MILP tie); captaincy gap measurement (hit-rate 18%, capture 57%, ~4.8 pts/GW); where this phase's new results get recorded.

### Dependency phase
- `.planning/research/DATA-SOURCE-RESILIENCE.md` — Phase 8 research (vaastav stall, self-hosted GW capture); Phase 9 depends on Phase 8's data layer being in place.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backtest/walk_forward.py` — the sole judge: 6-season expanding-window retrain, jitter replicas, isolated-chip evaluation, horizon pools (`_plan_col`/`leakage_safe_plan`). Chip scheduler v2 and RL are scored here.
- `models/intervals.py` — p10/p90 bands per position×xp-bucket already fit on held-out residuals; the captaincy ceiling EV threads `xp_capt_ceiling` from these.
- `optimize/squad_ilp.py` / `optimize/transfers.py` — captain objective already parameterized via `capt_col` (captain-by-mean precedent); ceiling EV is a new column through the same seam.
- `optimize/chips.py` — the heuristic scheduler being replaced (BB→biggest DGW, TC→DGW fallback, FH→biggest BGW, WC→fixed slot); chip application in `backtest/season.py` stays unchanged.
- `data/fbref.py` hardening lessons (season-lagged join, primary-stint dedupe, row-count asserts) transfer directly to the Understat/FotMob joins.
- `understatapi` is already a dependency; `scipy` covers Poisson GLM needs — team-strength modeling needs no new packages.

### Established Patterns
- Leakage-safe shift(1)-then-roll discipline in `features/engineer.py`; every new feature column follows it and gets a `tests/test_leakage.py` assertion.
- Opt-in flags with defaults unchanged until the harness clears the criterion (ranking loss, CS model, 3-state, MILP all stayed opt-in) — this phase's D-07/D-08 formalize it.
- B3 causal-scheduler fix precedent: chip decisions at GW g may see fixture structure only within g..g+K; frozen-form horizon xP only, never realized points.
- Package-legitimacy blocking gate + uv hash-locked installs (Phase 5 D-01/D-02).

### Integration Points
- `data/build_table.py` joins new sources into the canonical player_gw table; `features/engineer.py` + `config.py` declare new feature columns.
- Horizon pools graft in `backtest/walk_forward.py` and `predict/live.py --horizon` — where Dixon-Coles future-fixture ratings enter.
- `predict/live.py` / `predict/export.py` — weekly product surface; nothing here changes until a flag flips default-on.

</code_context>

<specifics>
## Specific Ideas

- The salvageable FPL-RL ideas are exactly two: the hybrid split (RL chooses chip timing + transfer count; the existing ILP keeps player selection) and FotMob as an enrichment source. Its 2,918 headline is in-sample and is not a target — "anything claiming to close the gap to 2,900" is explicitly out of scope.
- theFPLkiwi's ready-made ID maps are the intended shortcut for all name→FPL ID mapping; build one shared crosswalk, not per-source mappings.
- Benchmark comparisons run on played-only common rows (per the B8 fix) with MAE/Spearman side-by-side.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (EO/rank-play modeling remains deferred from the research doc's option 7; it was never in this phase.)

</deferred>

---

*Phase: 09-xp-model-optimizer-improvement-experiments*
*Context gathered: 2026-09-08*
