# Phase 10: xP Experiment Follow-ups - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 10-xp-experiment-follow-ups
**Areas discussed:** Sequencing & kill conditions, Availability data & backfill, Adoption bar for P(play) work, Model-bracket compute & scope

---

## Sequencing & kill conditions

| Option | Description | Selected |
|--------|-------------|----------|
| Benchmarks first | Tier-3 scoreboard benchmarks land first (near-zero cost, deadline-gated data accumulation), then Tier 1 → Tier 2 | ✓ |
| Strict tier order 1→2→3 | Research-derived priority exactly | |
| Tier 1 + benchmarks in parallel | Benchmarks alongside Tier 1 in one wave | |

**User's choice:** Benchmarks first (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Spearman threshold | Pre-declare: build sentiment only if post-Tier-1 benchmark Spearman < ~0.50 | ✓ |
| Both Tier-1 rejected | Build only if both Tier-1 experiments fail adoption | |
| Defer to next phase | Record trigger, build later phase | |

**User's choice:** Spearman threshold (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Notes yes, FBref drop | Write RL addendum, drop FBref | |
| Both at the tail | Keep both, sequenced dead last; FBref only with spare time + user willingness | ✓ |
| Drop both | Close RL via existing addendum, drop FBref | |

**User's choice:** Both at the tail

| Option | Description | Selected |
|--------|-------------|----------|
| Unconditional | D-01 precedent: run the bracket regardless | ✓ |
| After Tier 1 lands | Bracket runs on best available feature matrix | |
| Gate on Tier-1 failure | Bracket as fallback lever only | |

**User's choice:** Unconditional (Recommended)

---

## Availability data & backfill

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, vendor 2025-26 | Commit FPL-Core-Insights per-GW playerstats directly | |
| No, own data only | Live 2026-27 tracking only | |
| Vendor + verify first | Gate commit on spot-check vs own 2026-08-31/09-07 snapshots | ✓ |

**User's choice:** Vendor + verify first

| Option | Description | Selected |
|--------|-------------|----------|
| All seasons 2016-17+ | Full training-window Transfermarkt backfill | ✓ |
| Test seasons only (2020-21+) | Half the fetch time, null features before | |
| One season pilot first | 2025-26 pilot, expand if signal | |

**User's choice:** All seasons 2016-17+ (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Committed snapshot | Normalized injury-spell table committed like kiwi data | ✓ |
| Cache only | Uncommitted data/raw/ cache like fotmob | |
| Cache + committed summary | Raw cached, derived feature table committed | |

**User's choice:** Committed snapshot (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Anacron-style catch-up | On boot/first-run-of-day, capture missing daily snapshot | ✓ |
| Deadline-day guard only | Pre-deadline existence check only | |
| Out of scope | Accept sparse snapshots | |

**User's choice:** Anacron-style catch-up (Recommended)
**Notes:** Finding surfaced during discussion: only 2 of 10 days captured since 2026-08-31 (WSL cron silent on machine-off days).

---

## Adoption bar for P(play) work

| Option | Description | Selected |
|--------|-------------|----------|
| Dual criterion | Covered-season points AND Spearman must both improve | ✓ |
| Spearman only | Judge purely on ranking improvement | |
| Points on covered season | Consistent single-metric protocol | |

**User's choice:** Dual criterion (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-adopt + safe fallback | D-07 stands; NaN-fallback on missing snapshot, asserted by test | ✓ |
| Shadow 2-3 GWs first | Side-by-side export before flipping | |
| Strict D-07, no extras | Flag flips, nothing extra | |

**User's choice:** Auto-adopt + safe fallback (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Points +25 / Spearman +0.03 | Conservative dual margins | ✓ |
| Points positive / Spearman +0.05 | Spearman-led margins | |
| Let the researcher propose | Derive margins from measured harness noise | |

**User's choice:** Points +25 / Spearman +0.03 (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Split verdicts | Combined 6-season run for full-coverage winners only; flags verdict separate | ✓ |
| Combined incl. flags | NaN-history combined run | |
| No combined this phase | Individual verdicts only | |

**User's choice:** Split verdicts (Recommended)

---

## Model-bracket compute & scope

| Option | Description | Selected |
|--------|-------------|----------|
| Local WSL only | Keep D-15 intact | initially ✓, then revised |
| Colab free tier for seq models | Narrow amendment | |
| Colab incl. paid units | Use held units freely | |

**User's choice:** Initially "Local WSL only", REVISED by free-text on the next question: per-candidate Colab-vs-local time-benefit assessment; divide candidates across both machines in parallel even at speed parity. Confirmed: user has Colab Pro with 200 compute units (no new spend).

| Option | Description | Selected |
|--------|-------------|----------|
| Full roster as written | Ridge/ElasticNet, XGBoost, CatBoost, MLP, LSTM/GRU | |
| Drop the GBDT siblings | Three candidates only | |
| Add a transformer too | Extend with a tiny attention encoder | ✓ (via free text) |

**User's choice:** All five families PLUS a small transformer encoder — six candidates total ("does this five include transformer arch as well? include if not").

| Option | Description | Selected |
|--------|-------------|----------|
| ~100 units + 3 nights | Half units in reserve | |
| All 200 units, open nights | Full balance, hard stop at exhaustion | ✓ |
| Minimal probe first | One night per family, no tuning | |

**User's choice:** All 200 units, open nights

| Option | Description | Selected |
|--------|-------------|----------|
| Dev lockfile + D-12 gate | Hash-locked experiments lockfile, never Dockerfile/CI, blocking-human gate | ✓ |
| Main lockfile if adopted | Migration path planned upfront | |
| Skip the gate this phase | Well-known packages, no ceremony | |

**User's choice:** Dev lockfile + D-12 gate (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Colab runs walk-forward too | Full per-season retrain loop on Colab, frozen preds committed back, local harness scores | ✓ |
| Colab tunes, local retrains | Colab only for hyperparameter search | |
| Cheap gate only on Colab | Smallest Colab surface | |

**User's choice:** Colab runs walk-forward too (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Beat by margin +0.01 | Val Spearman ≥ LightGBM + 0.01 to advance | ✓ |
| Any strict beat | Any decimal above | |
| Top-2 always advance | Best two regardless | |

**User's choice:** Beat by margin +0.01 (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Export weights, no torch | ONNX/numpy inference; torch stays dev-only | ✓ |
| Amend D-09, ship torch | Graduate torch into production | |
| Evidence only, defer | Productionize in a later phase | |

**User's choice:** Export weights, no torch (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Match per-position | All candidates mirror shipped 4-regressor structure | |
| Pooled + position feature | Deep pooled, classical per-position | |
| Both for deep models | Deep candidates run both variants; better one enters gate | ✓ |

**User's choice:** Both for deep models

| Option | Description | Selected |
|--------|-------------|----------|
| Small fixed budget each | Equal ~20-30-config random search per candidate | |
| Sensible defaults only | Fastest bracket | |
| Tune GBDTs less, deep more | Defaults for XGB/CatBoost; real budget for deep | ✓ |

**User's choice:** Tune GBDTs less, deep more

| Option | Description | Selected |
|--------|-------------|----------|
| Raw per-GW stats | Network learns its own temporal aggregation | |
| Engineered features per step | Reuse tested leakage-safe columns | |
| Raw + static context | Raw sequence + static side-vector after encoder | ✓ |

**User's choice:** Raw + static context

| Option | Description | Selected |
|--------|-------------|----------|
| Extend test_leakage.py | Explicit new timestep < g assertions on real data | ✓ |
| Reuse shifted columns only | Structural constraint via existing columns | |
| Both | Belt and braces | |

**User's choice:** Extend test_leakage.py (Recommended)

---

## Claude's Discretion

- Exact flag names, module layout, sequence window length (~8–10 GWs), transformer size budget, Colab notebook structure/artifact naming, fetcher rate limits and cache layout, exact D-02 Spearman threshold value (declared in plan before Tier-1 runs), fplreview capture workflow design.

## Deferred Ideas

None — discussion stayed within phase scope.
