# Phase 9: xP Model & Optimizer Improvement Experiments - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-08
**Phase:** 09-xp-model-optimizer-improvement-experiments
**Areas discussed:** Experiment sequencing & gates, Adoption bar & success criteria, Dependencies & data acquisition, Compute budget & A/B protocol

---

## Experiment sequencing & gates

| Option | Description | Selected |
|--------|-------------|----------|
| Decision-gated (Recommended) | Benchmark runs first; accuracy parity deprioritizes feature work toward decision-layer work | |
| Fixed order, run everything | All experiments run in recommended order regardless of intermediate results | ✓ |
| Decisions-first, skip benchmark | Skip benchmark; only captaincy + chip work | |

**User's choice:** Fixed order, run everything

| Option | Description | Selected |
|--------|-------------|----------|
| In-phase, gated (Recommended) | RL built in Phase 9 only after chip scheduler v2 is measured; must beat it on the honest harness | ✓ |
| Defer to its own phase | Phase 9 ends at chip scheduler v2; RL becomes a Phase 10 candidate | |
| Drop RL entirely | Chip scheduler v2 captures the value without RL complexity | |

**User's choice:** In-phase, gated

| Option | Description | Selected |
|--------|-------------|----------|
| Understat only (Recommended) | Only the derisked source (existing dep + kiwi ID maps) | |
| Understat + FotMob | Also the FotMob defensive-stats scraper | |
| All three incl. FBref prep | Full goal item 6 including a Chrome-capable scrape host | ✓ |
| None this phase | Skip enrichment entirely | |

**User's choice:** All three incl. FBref prep

| Option | Description | Selected |
|--------|-------------|----------|
| Local WSL Chrome (Recommended) | Chrome installed outside the repo; scrapes run on this machine only | ✓ |
| Dockerized scraper | Separate Chrome-bearing image kept out of the production image | |
| Prep only, no scraping | Prove the host + one fetch; join deferred | |

**User's choice:** Local WSL Chrome

---

## Adoption bar & success criteria

| Option | Description | Selected |
|--------|-------------|----------|
| Lock 2,280 (Recommended) | ≥ +25/season aggregate, outside noise band, per research doc | ✓ |
| Raise to 2,300 | Match the ROADMAP frontier language | |
| No aggregate bar | Per-experiment metrics only | |

**User's choice:** Lock 2,280

| Option | Description | Selected |
|--------|-------------|----------|
| Clears criterion, auto-adopt (Recommended) | Pre-declared criterion cleared outside noise band → flag flips default-on | ✓ |
| You review each at phase end | Nothing flips without explicit sign-off | |
| Any positive mean | Adopt anything positive even inside the noise band | |

**User's choice:** Clears criterion, auto-adopt

| Option | Description | Selected |
|--------|-------------|----------|
| Keep code behind flag (Recommended) | Merged, default-off, numbers in IMPROVEMENTS.md | ✓ |
| Delete code, keep findings | Only measurement survives | |
| Case by case | Heavy stacks deleted, cheap ones kept | |

**User's choice:** Keep code behind flag

| Option | Description | Selected |
|--------|-------------|----------|
| Adopt full set (Recommended) | Captaincy capture +2pts; WC value measured + no chip CI regression; leakage tests extended; optimistic-vs-frozen A/B | ✓ |
| Adopt, tweak numbers | Structure kept, thresholds adjusted | |
| Aggregate bar only | Only 2,280 gates | |

**User's choice:** Adopt full set

---

## Dependencies & data acquisition

| Option | Description | Selected |
|--------|-------------|----------|
| Separate dev-only lock (Recommended) | requirements-rl compiled with uv --generate-hashes, never in production locks/image | ✓ |
| Main lockfile | torch in main hash-locked requirements | |
| Conda-only, no lock | Ad-hoc install, nothing tracked | |

**User's choice:** Separate dev-only lock

| Option | Description | Selected |
|--------|-------------|----------|
| Commit snapshot (Recommended) | Commit kiwi CSV vintages + ID maps with attribution — frozen-fixtures philosophy | ✓ |
| Fetch script + gitignored cache | Lean repo, breakable benchmark | |
| You decide | Per-file by size and license | |

**User's choice:** Commit snapshot

| Option | Description | Selected |
|--------|-------------|----------|
| Unofficial JSON, polite (Recommended) | Rate-limited JSON endpoints, on-disk caching, kill-switch flag | ✓ |
| Best-effort spike first | Time-boxed spike before any pipeline work | |
| Skip FotMob | Drop despite the goal text | |

**User's choice:** Unofficial JSON, polite

| Option | Description | Selected |
|--------|-------------|----------|
| Keep blocking gate (Recommended) | Every package stops for registry-verified approval at install time | ✓ |
| Pre-approve RL set now | torch/sb3-contrib/gymnasium approved in this discussion | |

**User's choice:** Keep blocking gate

---

## Compute budget & A/B protocol

| Option | Description | Selected |
|--------|-------------|----------|
| Independent + final combined (Recommended) | Independent A/Bs vs current default; winners get one final combined run that the 2,280 bar judges | ✓ |
| Cumulative stacking | Each experiment builds on prior winners | |
| Full factorial where cheap | Independent + pairwise interaction runs | |

**User's choice:** Independent + final combined

| Option | Description | Selected |
|--------|-------------|----------|
| Fast iterate, full adopt (Recommended) | Replicas off during development; full replicas for adoption-deciding + final runs | ✓ |
| Full replicas always | Every run with full replicas | |
| You decide | Per-experiment by metric noise | |

**User's choice:** Fast iterate, full adopt

| Option | Description | Selected |
|--------|-------------|----------|
| Local WSL, overnight OK (Recommended) | Unattended overnight jobs with logs; no cloud spend | ✓ |
| Local, working-hours only | No unattended runs | |
| Cloud burst allowed | Rent a box/GPU for heavy runs | |

**User's choice:** Local WSL, overnight OK

| Option | Description | Selected |
|--------|-------------|----------|
| Time-boxed, fixed seeds (Recommended) | Declared budget of a handful of overnight runs; no win in the box → rejected | ✓ |
| Proof-of-concept only | Only prove env/mask wiring; serious training is a future phase | |
| Open-ended until verdict | Train until clear win or loss | |

**User's choice:** Time-boxed, fixed seeds

---

## Claude's Discretion

- Flag names and module layout for new code (`data/team_strength.py`, `backtest/benchmark_external.py`, `models/simulate.py`, etc.)
- Quantile-first vs Monte-Carlo captaincy ordering (research doc default: quantile first)
- Concrete "full" replica count and exact RL time-box size
- Rate-limit values and cache layout for FotMob/Understat

## Deferred Ideas

None — discussion stayed within phase scope.
