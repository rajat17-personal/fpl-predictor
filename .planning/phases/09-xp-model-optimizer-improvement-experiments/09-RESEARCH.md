# Phase 9: xP Model & Optimizer Improvement Experiments - Research

**Researched:** 2026-09-08
**Domain:** Sports-analytics ML experimentation — xP model features, decision-layer optimization (captaincy EV, chip scheduling), reinforcement learning for strategy, external data enrichment — judged entirely by an existing offline walk-forward harness (no new user-facing surface).
**Confidence:** MEDIUM-HIGH on codebase integration points and package facts (verified this session); LOW on point-gain estimates for every experiment (inherent to the domain — see `.planning/research/XP-IMPROVEMENT-OPTIONS.md`'s own honesty framing, carried forward here).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Experiment sequencing & gates**
- D-01: Fixed order, run everything — all six experiments run in the recommended order regardless of intermediate results. The benchmark (1) still runs first but its outcome does NOT prune the feature-accuracy experiments (4, 6); it informs interpretation only.
- D-02: RL layer stays in-phase but hard-gated: it is built only after chip scheduler v2 (3) lands and is measured, and it must beat the solver-scored scheduler on the same honest harness to earn adoption.
- D-03: All three enrichment sources are in scope: Understat npxG/xGChain/xGBuildup (via theFPLkiwi's ready-made FPL↔fbref↔FFScout ID maps), FotMob per-match defensive stats, and FBref. All enter as **features only, never sub-models** (CS sub-model rejection stands). Name→FPL ID mapping is the shared prerequisite.
- D-04: FBref scrape host = local WSL Chrome/Chromium installed **outside the repo** (never committed — preserves Phase 5's repo hygiene). Scrapes run manually/cron on this machine only; no scraper Docker image this phase.

**Adoption bar & success criteria**
- D-05: Primary phase bar locked at mean core+chips season points ≥ **2,280** (current ≈2,256) across the 6-season walk-forward average — ≥ +25/season aggregate, outside the noise-band direction.
- D-06: Full per-experiment criteria set adopted from the research doc: captaincy capture ≥ +2 pts absolute over captain-by-mean; isolated WC value measured (currently unmeasured) and no chip's isolated value regresses its CI; `tests/test_leakage.py` extended for team-strength ratings (ratings at GW g reproducible from matches < g only); optimistic-vs-frozen A/B run for any horizon-touching change (the +337-vs-+40 discipline).
- D-07: Auto-adopt rule: each experiment pre-declares its criterion; when the adoption-deciding walk-forward run clears it outside the noise band, the flag flips default-on without a separate human sign-off. — Reversibility: reversible — a flag flip is one config change; the weekly product can revert to the prior default instantly.
- D-08: Failed experiments keep their code merged behind default-off flags, with numbers recorded in IMPROVEMENTS.md — the established rejected-with-numbers pattern. No code deletion.

**Dependencies & data acquisition**
- D-09: RL stack (torch, sb3-contrib, gymnasium, etc.) enters via a **separate dev-only lockfile** (e.g. `requirements-rl.in`/`.txt`, compiled with `uv --generate-hashes` per D-01 of Phase 5). It is never merged into the production lockfiles, Docker image, or CI install path — the weekly product stays torch-free.
- D-10: External benchmark data (theFPLkiwi historical projection CSVs, their ID maps, any OpenFPL outputs used) is **committed as a snapshot** with source URLs + license attribution, so the benchmark is reproducible forever — same philosophy as the frozen E2E fixtures. — Reversibility: costly — committed data vintages live in git history permanently; keep the snapshot small (CSVs only, no model binaries).
- D-11: FotMob acquisition = direct unofficial JSON endpoints, polite: conservative rate limiting, on-disk caching, and a kill-switch flag. Accept it may break upstream; no browser automation for FotMob.
- D-12: The blocking-human package-legitimacy gate stays for **every** new PyPI package this phase (torch, sb3-contrib, gymnasium, and anything else). No pre-approvals; registry-verified approval at install time, as in Phases 1–5.

**Compute budget & A/B protocol**
- D-13: A/B protocol = **independent + final combined**: each experiment A/Bs against the current default config independently; the winners then get one final combined walk-forward run, and that combined number is what the 2,280 bar (D-05) judges.
- D-14: Replica policy = fast iterate, full adopt: jitter replicas off (or minimal) during development iteration; every adoption-deciding run and the final combined run uses the full replica count for honest CIs.
- D-15: Compute runs on local WSL only; long runs (full-replica walk-forwards, RL training) launch as unattended overnight jobs with logs. No cloud spend.
- D-16: RL training is time-boxed with fixed seeds and pinned configs — a declared budget of a handful of overnight runs. If it hasn't beaten chip scheduler v2 on the honest harness within the box, it is recorded as rejected (per D-08); no open-ended tuning.

### Claude's Discretion
- Exact flag names, module layout for new code (e.g. `data/team_strength.py`, `backtest/benchmark_external.py`, `models/simulate.py`), and the hysteresis margin in chip scheduler v2.
- Quantile-first vs Monte-Carlo captaincy variant ordering (research doc suggests quantile first, MC only if quantiles move capture ≥ +2 pts — follow that unless evidence says otherwise).
- The concrete replica count constituting "full" (use the harness's existing default) and the exact RL time-box size within "a handful of overnight runs".
- Rate-limit values and cache layout for FotMob/Understat fetching.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (EO/rank-play modeling remains deferred from the research doc's option 7; it was never in this phase.)
</user_constraints>

---

## Project Constraints (from CLAUDE.md)

- Python 3.14, conda env `python314` at `/home/sraja/miniconda3/envs/python314/bin/python3.14` for all Python work — every new module (`data/team_strength.py`, `backtest/benchmark_external.py`, `models/simulate.py`, RL trainer) runs under this interpreter.
- `from __future__ import annotations` in every new module; type hints on signatures; `snake_case.py` modules, `snake_case` functions/variables, `_private()` prefix for internal helpers, `ALL_CAPS` module constants — match `data/fbref.py`/`optimize/chips.py` conventions exactly (this phase's closest analogues).
- Leakage-safe discipline is non-negotiable: every new rolling/derived feature follows the `shift(1)` pattern in `features/engineer.py::_roll()`; every new column gets a `tests/test_leakage.py` assertion (D-06 explicitly requires this for team-strength).
- No build step for Python: new modules are runnable via `python -m <module>`, `argparse` CLI, `main()` + `sys.exit(main())` bottom pattern (see every existing module in `data/`, `models/`, `backtest/`).
- Error handling conventions: `raise SystemExit(...)` for user-actionable missing-artifact errors (`features/engineer.py:110` style), `raise RuntimeError(...)` for solver-status failures (`optimize/multi_period.py` style), guarded `try/except Exception` for optional enrichment sources exactly like `data/fbref.py::attach()` and `data/build_table.py`'s odds/fbref try-blocks — this is the template for the new Understat/FotMob/team-strength joins.
- Print-based logging with module tags (`[fbref]`, `[odds]`, `[intervals]`) — no logger config; new modules should tag prints the same way (`[team_strength]`, `[fotmob]`, `[benchmark]`, `[rl]`).
- Package-legitimacy blocking-human gate (SEC-adjacent convention, Phases 1–5 precedent) applies to every new PyPI package — reconfirmed explicitly by D-12.
- `requirements.txt`/`requirements-dev.txt` are `uv pip compile --generate-hashes` locked (see exact command banners in both files); a new `requirements-rl.in`/`.txt` pair for the dev-only RL stack must follow the identical compile invocation, `-c requirements.txt` constraint per the dev lockfile's own header pattern, and must **never** appear in `Dockerfile` or any `pip install --require-hashes` line in `.github/workflows/*.yml` (verified today: `ci.yml`/`daily.yml`/`weekly.yml`/`Dockerfile` install only `requirements.txt`[+`requirements-dev.txt` in CI] — a new RL lockfile must not be added to any of these install lines).
- `.gitignore` currently excludes `data/raw/` and `data/processed/` wholesale (regenerable pipeline data) — D-10's committed benchmark snapshot **must live outside those two directories** (e.g. a new `data/external/` or `tests/fixtures/benchmark/` tracked path) or it will silently never be committed.

## Summary

This phase is not a typical feature-build phase: it runs six increasingly speculative ML/decision experiments against one fixed judge — `backtest/walk_forward.py`'s 6-season leakage-safe harness — with each experiment landing as an opt-in flag that only flips default-on if it clears its own pre-declared, harness-measured bar (D-07). The research below confirms every experiment has a concrete, low-risk integration seam already established by prior phases' patterns (odds join, FBref join, `capt_col` parameterization, causal chip scheduler), so the phase's real risk is not "can this be built" but "will the harness actually show a gain outside noise" — which per the project's own prior findings (odds: MAE better, season points within noise; multi-GW: +337 optimistic collapses to +40 honest) is the norm, not the exception, for point-estimate experiments in this codebase.

Two findings materially change how the planner should sequence this phase. First, **FBref (part of D-03/D-04) was already investigated and functionally abandoned as of 2026-08-22** (`IMPROVEMENTS.md` Phase E, `REQUIREMENTS.md` "Out of Scope"): the site's Cloudflare block is bypassable with Chrome, but the delivered HTML no longer carries the actual stat *values* — cells are empty (`class="iz"`) across all seasons and both headless/headed modes. A fresh `curl` against fbref.com today reproduces the 403 at the no-browser layer; nothing in the intervening ~2.5 weeks suggests the value-blanking issue has been fixed upstream. The planner should treat FBref as the lowest-priority, spike-first item in D-03/D-04 (verify the value-blanking is still present with a 5-minute Chrome check before investing in "host setup" — Chrome is in fact already installed on this machine at `/usr/bin/google-chrome-stable`, so the seam is ready to test immediately) rather than building fresh infrastructure around a known-dead source. Second, **the RL dependency stack is fully verifiable today**: `torch` is unexpectedly already installed ad-hoc in the `python314` conda env (`2.12.0+cu130`, real WSL2 CUDA GPU passthrough confirmed working — `torch.cuda.is_available() == True`), and `torch==2.14.0`/`gymnasium==1.3.0`/`sb3-contrib==2.9.0`/`stable-baselines3==2.9.0` all have `cp314`-compatible wheels confirmed downloadable today. This means D-16's "handful of overnight runs" budget can plausibly target GPU-accelerated training rather than CPU-only, which changes the realistic training-speed assumption the planner should bake into the RL task's time-box.

**Primary recommendation:** Sequence exactly as D-01 mandates (benchmark → captaincy EV → chip scheduler v2 → team-strength features → RL-gated-on-3 → enrichment sources ordered Understat → FotMob → FBref-last-with-a-spike-gate), reuse the `capt_col`/`xp_plan`/causal-scheduler/`data/fbref.py`-join patterns already proven in this codebase for every new module, and treat every point-estimate as provisionally noise until the full-replica adoption-deciding run says otherwise (D-14).

## Architectural Responsibility Map

This is a batch ML pipeline, not a web app — the standard Browser/API/DB tiers don't apply. The project's own layer taxonomy (`data/` → `features/` → `models/` → `optimize/` → `backtest/` → `predict/`) is the correct tier system for this phase; mapping each experiment onto it surfaces which layers each option touches and prevents (e.g.) accidentally putting decision logic in the feature layer or model logic in the optimizer.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| External-projection benchmark (Opt 6) | `backtest/` (new `benchmark_external.py`) | `data/` (snapshot loader) | Pure evaluation — no pipeline change; lives beside `walk_forward.py`, never touches `models/` |
| Captaincy/TC ceiling EV (Opt 1) | `optimize/` (`squad_ilp.py`/`transfers.py` `capt_col` seam) | `models/` (`intervals.py` supplies `xp_capt_ceiling`) | Decision-layer change consuming an existing model artifact — must NOT become a new sub-model (the CS-decomposition anti-pattern) |
| Chip scheduler v2 (Opt 3) | `optimize/` (`chips.py` rewrite) | `backtest/` (harness scores it; `season.py` chip application unchanged) | Pure decision-timing logic over existing xP — never touches `models/` or `features/` |
| RL-for-strategy layer (Opt 5, gated) | `optimize/`/new `models/simulate.py` boundary | `backtest/` (harness is still the judge) | RL chooses chip timing + transfer count (decision layer); the existing ILP still does player selection (D-02) — RL must not absorb the ILP's job |
| Team-strength Poisson/DC features (Opt 2) | `data/` (new `team_strength.py`, fit) | `features/`+`config.py` (declare columns), `backtest/walk_forward.py` (graft into horizon pools) | Feature-only per D-03/CS-rejection precedent — must feed the L1 regressor as input columns, never decompose points itself |
| Understat/FotMob/FBref enrichment (Opt 4/6 data) | `data/` (new source modules + shared ID crosswalk) | `data/build_table.py` (join), `features/engineer.py`+`config.py` (columns) | Same pattern as `data/fbref.py`/`data/odds.py` — optional, guarded, no-op-if-absent enrichment joins |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `scipy` | 1.17.1 installed / 1.18.1 latest [VERIFIED: pip index versions scipy, this session] | Dixon-Coles / Poisson team-strength fit via `scipy.optimize.minimize` on the match-result negative log-likelihood | Already a project dependency (`config.py` already uses it for Spearman); this is the standard hand-rolled approach used by the public Dixon-Coles tutorials this domain converges on — no dedicated PyPI package is idiomatic here [CITED: dashee87.github.io Dixon-Coles walkthrough; pena.lt/y (penaltyblog) Dixon-Coles walkthrough] |
| `gymnasium` | 1.3.0 [VERIFIED: pip index versions gymnasium + pip download --python-version 314 confirms `py3-none-any` wheel, this session] | Defines the RL environment (chip timing + transfer-count action space) that `sb3-contrib`'s MaskablePPO trains against | Successor to OpenAI Gym; the environment-interface standard every modern SB3-family algorithm expects [ASSUMED — package identity/purpose is training knowledge, registry existence verified this session] |
| `stable-baselines3` | 2.9.0 [VERIFIED: pip index versions + cp314-compatible pure-Python wheel confirmed, this session] | Base RL trainer package `sb3-contrib` extends | Reference-implementation RL library (DLR-RM), the de facto standard for PPO-family algorithms in Python [ASSUMED — package identity/purpose is training knowledge, registry existence verified this session] |
| `sb3-contrib` | 2.9.0 [VERIFIED: pip index versions + cp314-compatible pure-Python wheel confirmed, this session] | `MaskablePPO` — PPO variant with an `action_masks()` hook, needed because not every chip/transfer-count action is legal every gameweek (e.g. a chip already used) | This is the exact algorithm class ADnocap/FPL-RL uses and this phase's D-02 salvages the idea from [CITED: `.planning/research/XP-IMPROVEMENT-OPTIONS.md` FPL-RL audit; sb3-contrib.readthedocs.io Maskable PPO docs] |
| `torch` | 2.14.0 latest / 2.12.0+cu130 already ad-hoc-installed in `python314` env [VERIFIED: pip index versions + pip download --python-version 314 confirms real `cp314-cp314-manylinux` wheel downloads successfully, this session] | `stable-baselines3`'s neural-net backend | Required transitive dependency of SB3; no alternative backend is supported by the RL library the phase already committed to (D-09) [ASSUMED — package identity is training knowledge, wheel existence verified this session] |

**All four RL packages plus `torch` are entirely new to this project and are dev-only per D-09** — none belong in `requirements.in`/`requirements-dev.in`; they belong in a new `requirements-rl.in` compiled the same way (`uv pip compile requirements-rl.in --generate-hashes --python-version 3.14 -c requirements.txt -o requirements-rl.txt`, following the exact banner pattern already at the top of `requirements.txt`/`requirements-dev.txt`).

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `requests` | already a project dependency (`requirements.in`) | Direct unofficial FotMob JSON-endpoint fetches (D-11: no browser automation) | Every FotMob call — the same `requests.get()` + `raise_for_status()` pattern as `data/ingest.py` |
| `understatapi` | 0.7.1, already pinned exact in `requirements.in` [VERIFIED: requirements.in:10, requirements.txt] | Understat npxG/xGChain/xGBuildup scraping (Opt 5/D-03) | Already a dependency and already reachable (`curl understat.com` → 200 this session) — no new install needed, only new call sites in `data/ingest.py`-adjacent code |
| `pandas` | already a project dependency | theFPLkiwi CSV/ID-map loading, benchmark alignment | Standard — no new package needed for CSV ingestion |
| `seleniumbase` | already declared optional (per `data/fbref.py` docstring) | FBref scrape driver (D-04), if the value-blanking issue is confirmed fixed | Only if a fresh spike shows FBref now serves stat values again — see Common Pitfalls |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled Dixon-Coles via `scipy.optimize` | `penaltyblog` (PyPI package wrapping the same math) | Saves ~50 lines but adds a new dependency + package-legitimacy gate for something the codebase can implement in one small module using an already-approved dependency; hand-rolling also makes the leakage-safety of the expanding-window refit auditable in-repo (D-06 requires a `tests/test_leakage.py` assertion on it) |
| Direct FotMob JSON requests (D-11) | `fotmob-api` / `mobfot` PyPI wrapper packages | D-11 explicitly locks the direct-endpoint approach; a wrapper package adds a legitimacy-gate dependency for what is fundamentally a thin `requests.get()` around 1-2 endpoints — keep as a documented fallback only if direct endpoints prove unstable |
| `sb3-contrib` MaskablePPO | Hand-rolled tabular Q-learning over a small discretized chip/transfer state space | MaskablePPO is the salvaged, already-audited FPL-RL architecture (D-02); a hand-rolled tabular approach reinvents action-masking and loses the ability to condition on continuous xP-derived state features |

**Installation (dev-only RL stack; do NOT touch `requirements.in`/`requirements-dev.in`):**
```bash
# requirements-rl.in
torch==2.14.0
gymnasium==1.3.0
stable-baselines3==2.9.0
sb3-contrib==2.9.0

# compile (same invocation pattern as requirements.txt's own banner)
uv pip compile requirements-rl.in --generate-hashes --python-version 3.14 \
    -c requirements.txt -o requirements-rl.txt
```

**Version verification (this session):**
- `pip index versions gymnasium` → 1.3.0 latest; `pip index versions sb3-contrib` → 2.9.0 latest; `pip index versions stable-baselines3` → 2.9.0 latest; `pip index versions torch` → 2.14.0 latest (2.12.0 already installed ad-hoc in `python314`).
- `pip download <pkg>==<ver> --python-version 314 --only-binary=:all: --no-deps` succeeded for all four packages today — `torch-2.14.0-cp314-cp314-manylinux_2_28_x86_64.whl` (554.6 MB, CUDA-capable build available), `gymnasium-1.3.0-py3-none-any.whl`, `sb3_contrib-2.9.0-py3-none-any.whl`, `stable_baselines3-2.9.0-py3-none-any.whl`.
- The project's Python 3.14 pin (CLAUDE.md) is therefore **confirmed satisfiable** for the entire RL stack — no wheel-availability blocker.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| `gymnasium` | pypi | published 2026-04-22 [VERIFIED: package-legitimacy check] | unknown (checker could not retrieve) | farama.org (Farama Foundation) | SUS (`unknown-downloads`) | Flagged — well-known package (Farama Foundation, OpenAI Gym successor), but registry download-count lookup failed in this environment; planner must add `checkpoint:human-verify` before install per D-12 |
| `stable-baselines3` | pypi | unknown (checker returned no signal) | unknown | unknown (checker returned no signal) | SUS (`unknown-age`, `unknown-downloads`, `no-repository`) | Flagged — cross-verified independently via `pip index versions` (real version ladder 0.6.0→2.9.0 over years) and is the package the phase's own research doc names as the reference RL library; still requires the blocking-human gate per D-12 (no pre-approval) |
| `sb3-contrib` | pypi | unknown (checker returned no signal) | unknown | unknown (checker returned no signal) | SUS (same reasons) | Flagged — same cross-verification as stable-baselines3 (real version ladder 0.10.0→2.9.0); DLR-RM maintains both under the same GitHub org; still requires the blocking-human gate |
| `torch` | pypi | published 2026-09-02 [VERIFIED: package-legitimacy check] | unknown | pytorch.org | SUS (`too-new`, `unknown-downloads`) | Flagged — the "too-new" signal is on the **2.14.0 release date**, not the `torch` package itself (PyTorch is a 10-year-old, world's-most-downloaded ML package); `torch` is already ad-hoc-installed at 2.12.0 in this exact `python314` env, confirming legitimacy independently — still requires the blocking-human gate per D-12 (pin the version the planner actually selects, not necessarily bleeding-edge 2.14.0) |
| `understatapi` | pypi | already approved & pinned in `requirements.in` (Phase 2-3) | — | github.com/collinb9/understatAPI | Not re-audited — pre-existing dependency, no new install |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `gymnasium`, `stable-baselines3`, `sb3-contrib`, `torch` — all four are well-established, real ML/RL ecosystem packages; the SUS verdicts stem from this environment's package-legitimacy checker being unable to retrieve download-count/age telemetry for them (a known limitation for very-high-download-count packages whose registry metadata endpoints behave differently), not from any hallucination/slopsquat signal. Independently cross-verified this session via `pip index versions` (real, multi-year version ladders for all four) and `pip download --python-version 314` (real wheel bytes downloaded for all four). **D-12 still requires the blocking-human checkpoint before installing any of them** — this audit does not substitute for that gate, it only supplies the planner with the evidence to present at that checkpoint.

*No package in this phase resolves to `[SLOP]`. Every new package is dev-only (RL stack) or already-approved (understatapi); the planner should route torch/sb3-contrib/stable-baselines3/gymnasium through one `checkpoint:human-verify` task before the first `requirements-rl.in` install, presenting this table as the evidence.*

## Architecture Patterns

### System Architecture Diagram

```text
                    ┌─────────────────────────────────────────────────────┐
                    │   backtest/walk_forward.py  (THE JUDGE — unchanged)  │
                    │   6-season expanding retrain, jitter replicas,       │
                    │   isolated-chip harness, horizon pools               │
                    └───────────────────────┬───────────────────────────┘
                                             │ scores every experiment
        ┌───────────────┬───────────────────┼───────────────────┬─────────────────┐
        │                │                   │                   │                 │
        ▼                ▼                   ▼                   ▼                 ▼
 ┌─────────────┐  ┌──────────────┐   ┌───────────────┐   ┌───────────────┐  ┌─────────────┐
 │ Opt 6:       │  │ Opt 1:       │   │ Opt 3:         │   │ Opt 2:        │  │ Opt 5 (gated  │
 │ benchmark_   │  │ captaincy    │   │ chip scheduler │   │ team_strength │  │ on Opt 3):    │
 │ external.py  │  │ ceiling EV   │   │ v2 (chips.py)  │   │ .py features  │  │ RL strategy   │
 │ (new, eval   │  │ (intervals.  │   │                │   │               │  │ layer         │
 │ only)        │  │ py→capt_col) │   │                │   │               │  │               │
 └──────┬───────┘  └──────┬───────┘   └───────┬────────┘   └──────┬────────┘  └──────┬────────┘
        │                 │                    │                   │                   │
        │ reads           │ reads xp_med/      │ reads xp_med      │ new feature       │ reads xP +
        │ test_           │ xp_mean +          │ horizon pools     │ columns into      │ chip-scheduler-v2
        │ predictions.    │ intervals.json     │ (FIXTURE_CTX)     │ features.parquet  │ output as env state;
        │ parquet         │                    │                   │ (via build_table  │ ILP (squad_ilp/
        │                 │                    │                   │ join)             │ transfers) stays
        │                 │                    │                   │                   │ player-selection-only
        ▼                 ▼                    ▼                   ▼                   ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │  data/ layer: new enrichment sources (Opt 4/D-03)                                         │
 │  data/team_strength.py (Poisson/DC, expanding fit)                                        │
 │  data/understat_join.py or extended data/ingest.py (npxG/xGChain via understatapi)         │
 │  data/fotmob.py (direct JSON endpoints, D-11: rate-limited, cached, kill-switch)            │
 │  data/fbref.py (EXISTING — spike-verify value-blanking before any new work, see Pitfalls)  │
 │  shared: data/id_map.py extended with a name→FPL crosswalk (theFPLkiwi maps, D-03)          │
 │  → all joined in data/build_table.py exactly like the existing odds/fbref try/except blocks │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

A reader traces the primary use case (an experiment's honest score) by following: new/changed columns → `data/build_table.py` join → `features/engineer.py` columns → `models/train.py` retrain → `backtest/walk_forward.py` scoring → CSV/console output compared against the D-05 bar.

### Recommended Project Structure

```
data/
├── team_strength.py       # NEW (Opt 2) — Dixon-Coles/Poisson, expanding per-GW fit
├── fotmob.py               # NEW (Opt 4/D-11) — direct JSON endpoints, cache + rate limit + kill-switch
├── id_crosswalk.py         # NEW (D-03 shared prereq) — theFPLkiwi ID maps → player_code, one crosswalk for all enrichment sources
├── fbref.py                 # EXISTING — spike-verify before extending (see Pitfalls)
├── odds.py, ingest.py       # EXISTING — Understat calls likely extend ingest.py's per-season fetch pattern
backtest/
├── benchmark_external.py   # NEW (Opt 6) — evaluation-only, no pipeline mutation
├── walk_forward.py          # EXISTING — grows new A/B config branches per D-13, never restructured
models/
├── simulate.py               # NEW (Opt 1, only if MC variant is triggered) — small Monte-Carlo captaincy layer
├── intervals.py              # EXISTING — source of xp_capt_ceiling via existing p10/p90 artifact
optimize/
├── chips.py                  # REWRITTEN (Opt 3) — v2 solver-scored causal scheduler replaces the heuristic
├── rl_env.py                 # NEW (Opt 5, gated) — Gymnasium env: chip timing + transfer-count actions, ILP-selection stays external
├── rl_train.py                # NEW (Opt 5, gated) — MaskablePPO training entry point (python -m optimize.rl_train)
requirements-rl.in/.txt        # NEW (D-09) — dev-only, never in Docker/CI install lines
data/external/                 # NEW (D-10) — committed benchmark snapshot (kiwi CSVs), OUTSIDE .gitignore'd data/raw|processed
```

### Pattern 1: Guarded optional-enrichment join (the established template)

**What:** Every new data source (team-strength, Understat, FotMob, FBref) must join via a `try/except Exception` block in `data/build_table.py` that no-ops gracefully if the source is absent, exactly like the existing odds/fbref blocks.
**When to use:** All of D-03/D-03's three enrichment sources, and Opt 2's team-strength ratings.
**Example (existing code, the pattern to replicate):**
```python
# Source: data/build_table.py:142-146 (read this session)
    # Optional FBref advanced stats — no-op unless data/processed/fbref.parquet exists.
    try:
        full = fbref_mod.attach(full, id_map.load_id_map())
    except Exception as exc:
        print(f"  [fbref] skipped ({exc})")
```

### Pattern 2: Captain-value seam already exists — extend it, don't rebuild it

**What:** `optimize/squad_ilp.py::build_gw_pool` and `optimize/transfers.py::optimize_gw` already accept a `capt_col` parameter distinct from the XI-selection `xp_col` (this is how captain-by-mean was adopted in Phase C). The captaincy ceiling EV experiment (Opt 1) is a drop-in extension: compute a new column `xp_capt_ceiling` and pass it as `capt_col` instead of `xp_mean`.
**When to use:** Opt 1's quantile-first variant.
**Example:**
```python
# Source: optimize/squad_ilp.py:37-42 (read this session) — the existing seam
    agg = dict(xp=(xp_col, "sum"), price_m=("price_m", "first"),
               actual=("y_points", "sum"),
               # Captain value: the armband doubles points, so the optimal captain
               # is argmax MEAN points — pass e.g. capt_col="xp_mean" to captain by
               # the mean-objective model while still selecting the XI by xp_col.
               xp_capt=(capt_col or xp_col, "sum"))
```
```python
# NEW pattern for Opt 1 (quantile-first ceiling EV), threading through models/intervals.py's
# existing artifact — no new sub-model, no retraining:
from models.intervals import apply_intervals, load_artifact

def add_ceiling_ev(pool: pd.DataFrame, lam: float = 0.5) -> pd.DataFrame:
    """xp_capt_ceiling = xp_mean + lam * (p90 - xp_med), using the ALREADY-FIT
    held-out-residual intervals artifact (models/intervals.py) — zero new training."""
    art = load_artifact()
    pool = apply_intervals(pool.rename(columns={"xp_mean": "xp"}), art)
    pool["xp_capt_ceiling"] = pool["xp"] + lam * (pool["p90"] - pool["xp_med"])
    return pool.rename(columns={"xp": "xp_mean"})
```

### Pattern 3: Causal-scheduler rewrite — v2 keeps B3's visibility discipline

**What:** `optimize/chips.py::causal_schedule` already implements the "decision at GW g sees fixture structure only within g..g+visibility" discipline (the B3 fix). Chip scheduler v2 (Opt 3) must replace the *decision rule* (currently: fixed WC slot, biggest-visible-DGW/BGW heuristics) with an xP-scored comparison ("use now vs. best visible later window"), while keeping the exact same visibility-windowing structure — this is the single most important leakage-safety carryover.
**When to use:** Opt 3, entirely.
**Example (existing visibility-windowing to preserve, read this session):**
```python
# Source: optimize/chips.py:39-65 — the windowing discipline v2 MUST keep
def causal_schedule(preds: pd.DataFrame, xp_col: str = "xp_med",
                    visibility: int = 4) -> dict[int, str]:
    ...
    for g in half_gws:
        window = [w for w in half_gws if g <= w <= g + visibility]
        # v2 replaces what happens inside this loop (heuristic dgw/bgw comparisons)
        # with: score "play chip at g" vs "best score across `window`" using
        # backtest.walk_forward's horizon xP machinery (leakage_safe_plan's
        # frozen-form + future-fixture-context construction), fire on now >= best_later - hysteresis
```

### Pattern 4: MaskablePPO action-masking (Opt 5, gated on Opt 3)

**What:** The RL layer must expose `action_masks()` so illegal actions (e.g. an already-used chip, a transfer count exceeding free transfers + hit budget) are excluded from the policy's action distribution, not merely penalized in the reward.
**When to use:** Only after Opt 3 lands and is measured (D-02); the environment's reward signal at each step should be the REALIZED points from `backtest/season.py::run_season`-style scoring, with the ILP (`optimize/squad_ilp.py`/`optimize/transfers.py`) called as an external, un-learned player-selection step (D-02's hybrid split).
**Example:**
```python
# Source: sb3-contrib docs pattern (CITED: sb3-contrib.readthedocs.io Maskable PPO, PettingZoo SB3 tutorial)
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from sb3_contrib.common.maskable.policies import MaskableActorCriticPolicy

def mask_fn(env) -> np.ndarray:
    return env.unwrapped.action_masks()   # e.g. False for an already-used chip this half

env = ActionMasker(FplStrategyEnv(...), mask_fn)
model = MaskablePPO(MaskableActorCriticPolicy, env, verbose=1, seed=FIXED_SEED)  # D-16: fixed seeds
model.learn(total_timesteps=...)
```

### Anti-Patterns to Avoid

- **Re-deriving a clean-sheet / points-decomposition sub-model from team-strength ratings:** REJECTED with numbers already (−50/season, `IMPROVEMENTS.md` Phase C `ComponentModel`). Team-strength (Opt 2) ratings must enter as plain input *feature columns* to the existing L1 regressor — never as a `P(CS)×4 + residual` decomposition.
- **Fitting Dixon-Coles/Poisson ratings on the full season before use:** the sharpest leakage risk called out in the research doc — ratings for GW g must be fit on matches strictly < g (same expanding-window discipline as everything else). Add the `tests/test_leakage.py` assertion D-06 requires before considering Opt 2 done.
- **Letting the RL layer absorb player-selection:** D-02's whole premise is RL-for-strategy (chip timing, transfer count) with the ILP still doing selection — an RL action space that includes "which 15 players" reinvents the ILP badly and abandons its provably-optimal guarantee.
- **Treating a single-season or low-replica A/B as a verdict:** every one of this codebase's own precedents (odds, multi-GW, ranking loss) show single-season/low-replica point deltas that reverse or evaporate under the full 6-season/full-replica run. D-14's "fast iterate, full adopt" replica policy exists exactly to prevent premature adoption calls.
- **Re-scraping FBref without first re-confirming the value-blanking is fixed:** building fresh WSL-Chrome host infrastructure (D-04) is wasted effort if the site still serves empty stat cells, as it did 2.5 weeks ago. Spike first (5-minute manual page-source check), then decide whether to invest.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| PPO-style RL training with action masking | A custom policy-gradient loop | `sb3-contrib`'s `MaskablePPO` | Reference implementation with tested action-masking, GAE, clipping, and vectorized-env support — a hand-rolled RL trainer is a huge surface for silent bugs (reward scaling, advantage normalization, masking leaks) that would invalidate D-16's fixed-seed reproducibility requirement |
| Held-out prediction uncertainty for captaincy ceiling EV | A new quantile-regression model | `models/intervals.py`'s existing p10/p25/p75/p90 artifact | Already fit on genuinely held-out residuals per position×xp-bucket; a new model reopens a leakage-risk surface for zero benefit (D-01 discretion explicitly says quantile-first before any Monte-Carlo layer) |
| Dixon-Coles negative-log-likelihood optimization | A bespoke gradient-descent implementation | `scipy.optimize.minimize` (the standard approach in every public Dixon-Coles tutorial) | scipy is already an approved dependency; hand-rolling the optimizer (vs. hand-rolling the likelihood function, which IS appropriate here) adds numerical-stability risk for no benefit |
| Player name → FPL ID matching across Understat/FotMob/FBref | Three separate fuzzy-matching pipelines | theFPLkiwi's ready-made ID_Dictionary crosswalk (FPL↔fbref↔FFScout, per D-03) [CITED: github.com/theFPLkiwi/theFPLkiwi] extended with a manual `_NAME_FIXUPS`-style dict per `data/fbref.py`'s existing pattern for any Understat/FotMob names it doesn't cover | One shared crosswalk (D-03's explicit instruction) avoids three divergent, redundant, and individually-buggy name-matching implementations — `data/fbref.py`'s own history (a many-to-many join corrupted a whole walk-forward before being caught, `IMPROVEMENTS.md` Phase E) is the concrete cautionary precedent |

**Key insight:** every "don't hand-roll" item above already has an in-repo precedent of what happens when a shortcut is skipped — the CS sub-model's −50/season, the un-deduped FBref join's row-count corruption, or (for RL) FPL-RL's own audited in-sample inflation from getting the train/eval split subtly wrong. The phase's don't-hand-roll list is really "reuse the seam this codebase already paid to build correctly."

## Runtime State Inventory

Not applicable — this phase adds/extends data pipelines and decision logic behind opt-in flags; it is not a rename/refactor/migration phase. No existing runtime state (stored data keys, live service config, OS-registered state, secrets, build artifacts) is renamed or relocated by any of the six experiments.

## Common Pitfalls

### Pitfall 1: FBref's value-blanking may still be present — don't build host infra on a dead source
**What goes wrong:** Investing WSL-Chrome scraping infrastructure (D-04) for FBref, only to reproduce `IMPROVEMENTS.md`'s already-documented finding that stat *values* (not just access) are blocked at the source.
**Why it happens:** The Cloudflare-bypass problem (solved, `data/fbref.py` UC-mode Chrome driver) is a DIFFERENT problem from the value-blanking issue (found 2026-08-22, likely a StatsBomb→Opta provider-switch fallout per `IMPROVEMENTS.md`). Fixing/re-verifying access does not fix value delivery.
**How to avoid:** Before any new FBref work, run a 5-minute spike: `python -m data.fbref --scrape` for one season and inspect whether `fb_tkl_int_90` etc. come back non-null. Chrome is already present at `/usr/bin/google-chrome-stable` [VERIFIED: `command -v google-chrome-stable`, this session] — the spike costs nothing but time. `curl https://fbref.com/en/comps/9/Premier-League-Stats` still returns 403 without a browser [VERIFIED: curl output, this session], consistent with the Cloudflare block being unchanged; but that only re-confirms the access-layer problem, not the value-blanking one — the spike must use the actual Chrome driver, not curl.
**Warning signs:** Non-null row count in the scrape output but every `fb_*` column still empty/`NaN` after `attach()` — exactly the symptom `IMPROVEMENTS.md` documented.

### Pitfall 2: Team-strength ratings leaking via a season-level (not expanding) fit
**What goes wrong:** Fitting Dixon-Coles/Poisson parameters once per season using that season's full match results, then using the ratings for every GW in that season — this leaks future match outcomes into early-GW ratings.
**Why it happens:** It's the natural, simpler implementation (one fit per season vs. an expanding per-GW refit) and the bug is invisible in aggregate season-points backtests (the CS sub-model regression didn't come from this exact leak, but the same class of mistake — "fit on data the decision shouldn't have seen yet" — is the project's most-repeated failure mode: the +337-vs-+40 multi-GW leak, `IMPROVEMENTS.md`).
**How to avoid:** Expanding-window fit exactly like model training itself: ratings for GW g use matches strictly < g. Add the `tests/test_leakage.py` assertion D-06 explicitly requires ("ratings at GW g reproducible from matches < g only") before calling Opt 2 done.
**Warning signs:** Ratings artifact has one row per (season, team) instead of one row per (season, gw, team); no test asserting reproducibility from a truncated match history.

### Pitfall 3: FotMob's unofficial endpoints breaking without warning
**What goes wrong:** D-11 explicitly accepts "it may break upstream" — a silent break (endpoint 404s, schema changes, rate-limit block) would otherwise corrupt or NaN-out a feature column without any visible pipeline failure.
**Why it happens:** Unofficial/reverse-engineered APIs have no stability contract; FotMob has changed its API shape historically (per the wrapper packages' own changelogs, e.g. `fotmob-api`/`mobfot` on PyPI tracking breaking changes).
**How to avoid:** D-11's kill-switch flag + on-disk caching should be built with an explicit coverage-percentage print (like `data/fbref.py::attach()`'s `cov = merged["fb_tkl_int_90"].notna().mean()` pattern) so a silent break shows up as a coverage cliff in the pipeline's own printed output, not just NaN columns nobody looks at.
**Warning signs:** A sudden drop in `fotmob_*` column coverage between consecutive pipeline runs; HTTP 403/429 in fetch logs.

### Pitfall 4: RL reward/objective mismatch with the honest harness
**What goes wrong:** Training the RL policy on a reward that differs from what `backtest/walk_forward.py` ultimately measures (e.g. training on per-step xP instead of realized season points net of hits) produces a policy that looks good in training logs but loses to chip scheduler v2 on the actual adoption-deciding run — silently violating D-02's "must beat the solver-scored scheduler on the same honest harness" gate.
**Why it happens:** RL environments are commonly built around a dense, differentiable-feeling proxy reward (xP) because sparse realized-points rewards are noisier and slower to train against — exactly the same optimistic-vs-frozen trap the project's own multi-GW leakage finding (+337 optimistic → +40 honest) already demonstrated in a different subsystem.
**How to avoid:** The environment's `step()` reward should be realized points (net of transfer hits), computed the same way `backtest/season.py::run_season`'s per-GW scoring works, not raw xP; the training/eval split across the 6 test seasons must respect the same expanding-window discipline used everywhere else (no season used for RL training may also be used as its own eval season in the final walk-forward comparison).
**Warning signs:** RL training-curve reward climbing steadily while the periodic actual-harness eval score plateaus or declines — the ADnocap/FPL-RL audit's own smoking gun (in-sample training producing an inflated in-sample number) is the cautionary template here.

### Pitfall 5: Dev-only RL lockfile bleeding into production install paths
**What goes wrong:** `requirements-rl.txt` accidentally gets added to `Dockerfile`, `ci.yml`, or `daily.yml`/`weekly.yml`'s install lines, pulling a 554MB+ CUDA-capable `torch` wheel into the production image and cron runners — directly violating D-09 ("never merged into the production lockfiles, Docker image, or CI install path").
**Why it happens:** Easy copy-paste mistake when adding a new lockfile pair to a CI workflow that already has a `pip install --require-hashes -r requirements.txt -r requirements-dev.txt` pattern in two jobs.
**How to avoid:** Verified this session — current install lines are `Dockerfile:23` (`requirements.txt` only), `ci.yml:47,79` (`requirements.txt` + `requirements-dev.txt`), `ci.yml:119` (`requirements.txt` only), `daily.yml:21`/`weekly.yml:25` (`requirements.txt` only). None should gain a `requirements-rl.txt` reference; the RL training script's own `python -m` invocation should be run manually/via a separate ad-hoc `pip install -r requirements-rl.txt` on the dev machine only, never through these tracked workflow files.
**Warning signs:** `grep -rn requirements-rl .github/workflows/ Dockerfile` returning any hit.

## Code Examples

### Dixon-Coles / Poisson team-strength fit (Opt 2)
```python
# CITED: dashee87.github.io Dixon-Coles walkthrough (scipy.optimize.minimize pattern);
# adapted to this project's expanding-window discipline (NEW code, not yet in repo)
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

def dc_log_likelihood(params, home_goals, away_goals, home_team, away_team, teams):
    n = len(teams)
    attack = dict(zip(teams, params[:n]))
    defence = dict(zip(teams, params[n:2 * n]))
    home_adv, rho = params[-2], params[-1]
    ll = 0.0
    for hg, ag, h, a in zip(home_goals, away_goals, home_team, away_team):
        lam = np.exp(attack[h] + defence[a] + home_adv)
        mu = np.exp(attack[a] + defence[h])
        ll += poisson.logpmf(hg, lam) + poisson.logpmf(ag, mu)
        # rho correction only affects the 0-0/1-0/0-1/1-1 scorelines (Dixon & Coles 1997)
    return -ll

def fit_ratings_as_of(matches_before_gw: "pd.DataFrame") -> dict:
    """Ratings for GW g — call with matches strictly < g ONLY (leakage-safety
    per D-06's required test_leakage.py assertion)."""
    teams = sorted(set(matches_before_gw.home_team) | set(matches_before_gw.away_team))
    n = len(teams)
    x0 = np.concatenate([np.zeros(2 * n), [0.3, -0.1]])   # attack, defence, home_adv, rho
    res = minimize(dc_log_likelihood, x0, args=(
        matches_before_gw.home_goals, matches_before_gw.away_goals,
        matches_before_gw.home_team, matches_before_gw.away_team, teams),
        method="BFGS")
    attack, defence = res.x[:n], res.x[n:2 * n]
    return {t: {"attack": a, "defence": d} for t, a, d in zip(teams, attack, defence)}
```

### Captaincy ceiling EV threading through the existing intervals artifact (Opt 1)
```python
# Source pattern: models/intervals.py apply_intervals() (read this session, verbatim signature)
def apply_intervals(pool: pd.DataFrame, artifact: dict, xp_col: str = "xp") -> pd.DataFrame:
    ...  # attaches p10/p25/p75/p90 columns — reuse directly, do not refit
```
See Pattern 2 above for the `xp_capt_ceiling` column built on top of this.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| Heuristic chip scheduler (fixed WC slot, biggest-visible-DGW/BGW rules) | Solver-scored causal chip timing (Opt 3) | This phase, opt-in | Targets the codebase's own named weak spot ("WC fixed-slot timing is weak", `PLAN.md`); judged by the isolated-chip harness which currently shows FH +19.9±11.8, BB +12.4±7.6, TC +10.0±8.3, WC unmeasured [VERIFIED: `.planning/research/XP-IMPROVEMENT-OPTIONS.md`, itself citing `backtest/walk_forward.py`'s own isolated-chip output] |
| Captain-by-mean (`xp_mean` as `capt_col`) | Captaincy ceiling EV (`xp_mean + λ·(p90−xp_med)`) | This phase, opt-in, quantile-first | Captain-by-mean's own adoption number: **+16/season avg, noisy (-77..+125 per season), captaincy capture ≈57% both ways** [VERIFIED: `IMPROVEMENTS.md` Phase C, quoted verbatim] — ceiling EV's job is to move capture, not just mean |
| No public-benchmark comparison | External-projection benchmark (Opt 6) vs theFPLkiwi/OpenFPL on common played-only rows | This phase, first in sequence (D-01) | Calibrates whether remaining headroom is model-accuracy (promote Opt 2/5-data) or decision-layer (promote Opt 1/3) — informs interpretation only, does not gate per D-01 |

**Current verified baseline (the number every experiment must beat), per season, from the harness's own saved output:**

`data/processed/walk_forward_results.csv` [VERIFIED: read this session]:
```
season,model_mean,model_std,model+chips,capt_mean,capt_capture,multi_safe,form,hold
2020-21,2074,61,2091,2071,0.541,1967,2077,1517
2021-22,2119,47,2305,2123,0.583,2312,2174,1610
2022-23,2148,43,2380,2183,0.563,2269,2079,1835
2023-24,2191,68,2210,2086,0.483,2146,1960,1741
2024-25,2137,44,2417,2260,0.614,2101,2107,2230
2025-26,2122,21,2172,2174,0.595,2086,1797,1439
```
6-season averages (computed from the table above): `model_mean` ≈ 2132, `model+chips` ≈ 2263, `capt_capture` ≈ 56.3%. These are close to but not identical to CONTEXT.md's quoted "~2,105–2,256" / "current ≈2,256" range — likely from a slightly different run/replica-seed snapshot; the planner should re-run `python -m backtest.walk_forward` at phase start to get the exact current baseline the D-05 bar (≥2,280) will be judged against, rather than trusting either cached number.

**Deprecated/outdated:** none — this phase extends, it does not deprecate, any existing adopted component.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | `gymnasium`/`stable-baselines3`/`sb3-contrib`/`torch` package *identities and purposes* (RL ecosystem roles) are training knowledge, not sourced from an authoritative doc this session — only registry existence/wheel-availability was verified | Standard Stack, Package Legitimacy Audit | Low — these are extremely well-known packages; risk is limited to a version/API-detail being slightly stale, not the package being wrong or malicious |
| A2 | The Dixon-Coles hand-rolled `scipy.optimize.minimize` approach (no dedicated package) is "the standard" for this domain | Standard Stack, Code Examples | Low-medium — based on WebSearch of public tutorials (dashee87, penaltyblog blog posts), not an authoritative spec; a maintained package (`penaltyblog`) exists as an alternative if the hand-rolled fit proves numerically fragile |
| A3 | FBref's value-blanking issue (found 2026-08-22) is still present today (2026-09-08) | Summary, Pitfall 1 | Medium — only 2.5 weeks elapsed and no evidence of a fix, but this was not re-verified with an actual Chrome scrape this session (only the no-browser 403 was re-confirmed, which only reconfirms the access-layer block, not the value-blanking) — planner MUST spike-verify with the real Chrome driver before deciding FBref's priority |
| A4 | The FotMob "direct unofficial JSON endpoint" approach (D-11) will find working, undocumented endpoints for per-match defensive stats without needing a wrapper package | Standard Stack (Alternatives), Pitfall 3 | Medium — no specific FotMob endpoint URL/schema was verified this session (only that fotmob.com is network-reachable); the actual endpoint discovery is exploratory work the implementing plan must budget for, with `fotmob-api`/`mobfot` PyPI packages as a documented fallback |
| A5 | theFPLkiwi's ID_Dictionary crosswalk covers Understat player names, not just FPL/fbref/FFScout/FanTeam | Don't Hand-Roll, D-03 | Medium — WebSearch found the crosswalk explicitly named FPL/fbref/FFScout/FanTeam sources; Understat coverage was not independently confirmed. If absent, Understat names need the same `_NAME_FIXUPS`-style manual dict `data/fbref.py` already uses as a fallback |

**If this table is empty:** N/A — see entries above; all are LOW-MEDIUM risk and each has a documented fallback or verification step the planner can schedule as an early task.

## Open Questions

1. **What is the concrete hysteresis margin for chip scheduler v2's "fire now vs. wait" comparison?**
   - What we know: D-01's Claude's-Discretion section explicitly leaves this to implementation; the existing `causal_schedule` visibility window is 4 GWs.
   - What's unclear: no numeric hysteresis value is specified anywhere in prior research or context.
   - Recommendation: start with 0 (fire iff now ≥ best-later, no margin) for the first A/B pass, then sweep 1-3 pt margins if the zero-margin variant proves noisy — this is a cheap parameter sweep within the existing harness, not a new experiment.

2. **What real FotMob endpoint path/schema serves per-match defensive stats?**
   - What we know: FotMob has an unofficial JSON API (confirmed reachable this session; wrapper packages like `fotmob-api`/`mobfot` document some endpoint shapes).
   - What's unclear: the exact endpoint(s) and payload schema for per-player per-match defensive actions were not verified this session.
   - Recommendation: budget a short exploratory task (inspect `fotmob-api`'s source or the site's own network tab) before committing to a data-model shape for `data/fotmob.py`.

3. **Does theFPLkiwi's ID crosswalk include Understat player identifiers?**
   - What we know: the crosswalk explicitly covers FPL/fbref/FFScout/FanTeam (per WebSearch of the repo's README).
   - What's unclear: Understat-specific ID coverage.
   - Recommendation: inspect the actual `ID_Dictionary` file columns early in the D-03 shared-prerequisite task; fall back to name-normalization (`data/fbref.py::_norm()`'s existing pattern) plus a manual fixups dict if Understat IDs are absent.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `python314` conda env | All new code (CLAUDE.md mandate) | ✓ [VERIFIED this session] | Python 3.14.3 | — |
| `torch` cp314 wheel | RL stack (D-09) | ✓ [VERIFIED: `pip download torch==2.14.0 --python-version 314` succeeded this session; also already ad-hoc installed at 2.12.0+cu130] | 2.14.0 latest / 2.12.0 installed | — |
| NVIDIA GPU (WSL2 passthrough) | RL training speed (D-15/D-16 time-box) | ✓ [VERIFIED: `nvidia-smi` shows a real GPU; `torch.cuda.is_available()` returned `True` this session] | driver 610.57.01, CUDA 13.3 | CPU-only training if GPU proves unstable in an overnight unattended run |
| `gymnasium`/`sb3-contrib`/`stable-baselines3` cp314 wheels | RL stack (D-09) | ✓ [VERIFIED: `pip download --python-version 314` succeeded for all three this session] | 1.3.0 / 2.9.0 / 2.9.0 | — |
| Chrome/Chromium (for FBref scrape, D-04) | Opt 4/D-03 FBref enrichment | ✓ [VERIFIED: `/usr/bin/google-chrome-stable` present this session] | not version-checked | n/a — but see Pitfall 1: access ≠ usable data |
| `fbref.com` reachability | FBref scrape | ✗ direct (no-browser) [VERIFIED: `curl` returned 403 this session] | — | Chrome/`seleniumbase` UC-mode bypasses the 403 (existing `data/fbref.py` capability) — but see Pitfall 1 for the deeper value-blanking issue |
| `understat.com` reachability | Understat enrichment (Opt 5/D-03) | ✓ [VERIFIED: `curl` returned 200 this session] | — | — |
| `fotmob.com` API reachability | FotMob enrichment (D-11) | ✓ network-reachable [VERIFIED: `curl` on a guessed endpoint returned 404, i.e. reachable-but-wrong-path, not blocked] | — | Not a functional API verification — see Open Question 2 |
| `raw.githubusercontent.com/theFPLkiwi/theFPLkiwi` | External benchmark (Opt 6, D-10) | ✓ [VERIFIED: `curl` returned 200 this session] | — | — |
| `uv` (lockfile compiler, Phase 5 precedent) | `requirements-rl.txt` compile (D-09) | assumed present (used to build existing `requirements*.txt` banners) — not re-verified this session | — | `pip-compile` (pip-tools) as a fallback compiler if `uv` is unavailable |

**Missing dependencies with no fallback:** none identified.

**Missing dependencies with fallback:** FBref direct access (403) has an existing fallback (Chrome/seleniumbase, already built) — but see Pitfall 1 for why the fallback may not actually solve the real problem (value-blanking, not access-blocking).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x [VERIFIED: `requirements-dev.in:5`, `pytest>=8`] |
| Config file | `pytest.ini` (repo root) — `testpaths = tests`, disables playwright/seleniumbase pytest plugins to avoid CLI-flag collisions |
| Quick run command | `python -m pytest tests/test_leakage.py tests/test_legality.py -x` |
| Full suite command | `python -m pytest` (repo root, activates `pytest.ini`'s `testpaths = tests`) |

### Phase Requirements → Test Map

No formal requirement IDs are mapped to this phase (ROADMAP.md/REQUIREMENTS.md traceability table lists none for Phase 9 — this is a research/experiment phase judged by its own D-05/D-06 criteria, not the v1/v2 REQUIREMENTS.md list). The relevant "requirements" are D-05/D-06's adoption criteria themselves:

| Criterion (from D-05/D-06) | Behavior | Test Type | Automated Command | File Exists? |
|-----------------------------|----------|-----------|---------------------|--------------|
| D-06: team-strength leakage safety | Ratings at GW g reproducible from matches < g only | unit | `python -m pytest tests/test_leakage.py -k team_strength` | ❌ Wave 0 — new test to write alongside `data/team_strength.py` |
| D-06: optimistic-vs-frozen A/B discipline | Any horizon-touching change reports both an optimistic and leakage-safe number | integration | `python -m backtest.walk_forward` (manual comparison, existing `leakage_safe_plan` vs `_plan_col` split) | ✓ existing (`backtest/walk_forward.py:55-117`) |
| D-05: primary phase bar | Mean core+chips season points ≥ 2,280 across 6-season average | full-harness | `python -m backtest.walk_forward --replicas <full>` | ✓ existing |
| D-06: captaincy capture ≥ +2 pts absolute | `capt_capture` column improvement over the `capt_mean` baseline | full-harness | same `walk_forward` run, read `capt_capture` column | ✓ existing (already computed, see `walk_forward_results.csv`) |
| D-06: isolated chip regressions | No chip's isolated `delta` CI regresses | full-harness | same `walk_forward` run, isolated-chip block in stdout | ✓ existing (`backtest/walk_forward.py:181-187`) |
| RL vs chip-scheduler-v2 gate (D-02) | RL policy's harness score > chip-scheduler-v2's harness score | full-harness | manual comparison of two `walk_forward` runs (one config each) | ❌ Wave 0 — needs a config-flag seam to switch schedulers, and the RL trainer itself |
| Legality of any new ILP-adjacent code (RL-selected transfer counts, captain-ceiling changes) | Output remains a legal FPL squad | property | `python -m pytest tests/test_legality.py` | ✓ existing — should already cover any `capt_col`/pool-shape change since it fuzzes `pick_squad`/`optimize_gw` directly |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_leakage.py tests/test_legality.py tests/test_autosub.py` (fast, no full walk-forward)
- **Per experiment A/B (development iteration, D-14 "fast iterate"):** `python -m backtest.walk_forward --replicas 0` or a low replica count, jitter minimal
- **Per adoption-deciding run (D-14 "full adopt") and the final combined run (D-13):** `python -m backtest.walk_forward` at the harness's existing default replica count, full 6 seasons
- **Phase gate:** the D-05 bar (≥2,280) is judged on the final combined run only, per D-13

### Wave 0 Gaps

- [ ] `tests/test_leakage.py` extension for team-strength ratings (Opt 2) — no such test exists yet; must assert ratings at GW g reproduce from matches < g only (D-06 explicit requirement)
- [ ] A config-flag seam to run `backtest/walk_forward.py` with chip-scheduler-v2 vs. RL-strategy vs. the current heuristic scheduler, so the D-02 RL-vs-scheduler-v2 comparison is a repeatable one-flag toggle, not an ad-hoc script edit
- [ ] `requirements-rl.in`/`.txt` lockfile pair — does not exist yet (D-09)
- [ ] `data/external/` (or equivalent) tracked directory for the D-10 committed benchmark snapshot — does not exist yet; `.gitignore` currently excludes both `data/raw/` and `data/processed/` wholesale, so the snapshot needs a new path

*(No existing test infrastructure gap blocks Opt 1/3/6 directly — they reuse `test_legality.py`'s existing property-fuzz coverage and the harness's existing output columns.)*

## Security Domain

### Applicable ASVS Categories

This phase adds no new user-facing endpoints, auth surfaces, or externally-writable state — it is offline batch ML/data work. Most ASVS categories are not applicable; the relevant ones concern input handling for new external data sources and dependency supply-chain hygiene (SEC-02's existing pattern, reapplied).

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | No | No new auth surface |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes | External JSON/CSV payloads (FotMob JSON, theFPLkiwi CSVs, Understat responses) must be validated the same way `data/ingest.py`/existing `ops/jsonio.py` guard FPL API payloads — never assume shape, guard with `try/except` + explicit key checks, exactly like `data/fbref.py::attach()`'s guarded joins |
| V6 Cryptography | No | No new secrets/crypto surface introduced |
| V12/V14 Data Protection & Config | Yes | New PyPI dependencies (torch/gymnasium/sb3-contrib/stable-baselines3) go through the same package-legitimacy blocking-human gate as every prior phase (D-12); dev-only lockfile isolation (D-09) IS the security control here — it keeps a much larger, torch-bearing attack surface out of the production Docker image and CI install path entirely |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Unofficial FotMob endpoint returning attacker-influenced or malformed JSON (schema drift, unexpected types) silently corrupting a feature column | Tampering | Explicit schema/key validation on every FotMob response before use, coverage-percentage logging (Pitfall 3) so a corruption/drift shows up as a visible coverage cliff, never silently NaN-filled and forgotten |
| Dev-only RL dependency (`torch`, 554MB+ wheel) leaking into the production Docker image, inflating attack surface and image size | Tampering (of the deployed artifact) / supply-chain | D-09's isolation is the control — verified this session that no current `Dockerfile`/CI install line references anything but `requirements.txt`(+`requirements-dev.txt`); any new install line must be checked with `grep -rn requirements-rl .github/workflows/ Dockerfile` before merge |
| Committed benchmark CSV snapshot (D-10) containing unintended PII or license-incompatible redistribution of a third party's projection data | Information Disclosure / licensing risk | Attribute source URLs + license explicitly in the commit (D-10's own requirement); spot-check the CSVs for anything beyond player-name/projection columns before committing |

## Sources

### Primary (HIGH confidence)
- `.planning/research/XP-IMPROVEMENT-OPTIONS.md` — the phase's own canonical ranked-options research, read in full this session (ranked options table, per-option implementation notes, ADnocap/FPL-RL audit, success criteria)
- `IMPROVEMENTS.md` (repo root) — read in full this session (Phase A–E adopted/rejected history with numbers; FBref value-blanking finding; captaincy gap measurement)
- `PLAN.md` (repo root, relevant sections) — read this session (Refinements section: +337-optimistic-vs-+40-honest leakage finding; External data source assessment; "WC fixed-slot timing is weak")
- `backtest/walk_forward.py`, `models/intervals.py`, `optimize/chips.py`, `optimize/squad_ilp.py`, `optimize/transfers.py`, `backtest/season.py`, `optimize/multi_period.py`, `data/build_table.py`, `data/id_map.py`, `data/fbref.py`, `models/train.py`, `features/engineer.py`, `config.py`, `tests/test_legality.py`, `tests/test_leakage.py`, `requirements.in`, `requirements-dev.in`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `pytest.ini`, `.github/workflows/ci.yml`/`daily.yml`/`weekly.yml`, `Dockerfile` — all read in full or targeted this session
- `data/processed/walk_forward_results.csv` — read this session (actual current per-season baseline numbers)
- Direct tool verification this session: `pip index versions` (gymnasium, sb3-contrib, stable-baselines3, torch, scipy, understatapi), `pip download --python-version 314` (torch, gymnasium, sb3-contrib, stable-baselines3 — all confirmed cp314-compatible), `gsd_run query package-legitimacy check` (gymnasium, sb3-contrib, stable-baselines3, torch, understatapi), `nvidia-smi` + `python -c "import torch; torch.cuda.is_available()"` (GPU passthrough confirmed), `curl` reachability checks (fbref.com 403, understat.com 200, fotmob.com 404-but-reachable, raw.githubusercontent.com/theFPLkiwi 200), `command -v google-chrome-stable` (Chrome present)

### Secondary (MEDIUM confidence)
- sb3-contrib.readthedocs.io "Maskable PPO" docs + PettingZoo SB3 Connect Four tutorial (CITED, WebSearch this session) — `ActionMasker`/`action_masks()` pattern
- dashee87.github.io Dixon-Coles walkthrough; pena.lt/y (penaltyblog) Dixon-Coles walkthrough (CITED, WebSearch this session) — `scipy.optimize.minimize` NLL-fitting pattern
- github.com/theFPLkiwi/theFPLkiwi README (CITED, WebSearch this session) — ID_Dictionary crosswalk scope (FPL/fbref/FFScout/FanTeam), Old_Seasons historical projections folder

### Tertiary (LOW confidence)
- FotMob wrapper package existence (`fotmob-api`, `mobfot`) — WebSearch only, not independently installed/tested this session; flagged as a fallback option only, not a recommendation
- Package "identity/purpose" narrative for gymnasium/stable-baselines3/sb3-contrib/torch (what each package IS, beyond registry existence) — training knowledge per the provenance rule (see Assumption A1)

## Metadata

**Confidence breakdown:**
- Standard stack (RL packages): MEDIUM-HIGH — registry existence, version ladders, and cp314-wheel installability all independently verified this session; package *purpose/identity* narrative is training knowledge (LOW on that specific sub-claim, flagged as A1)
- Standard stack (Dixon-Coles/scipy): MEDIUM — approach is a WebSearch-sourced convention (public tutorials), not an authoritative spec, but scipy itself is an already-verified project dependency
- Architecture/integration points: HIGH — every seam (`capt_col`, `causal_schedule`'s visibility window, `data/build_table.py`'s guarded-join pattern, `models/intervals.py`'s artifact) was read directly from the current codebase this session, not inferred
- Pitfalls: HIGH for FBref (directly documented in `IMPROVEMENTS.md`, re-confirmed access-layer behavior this session), MEDIUM for RL/FotMob pitfalls (grounded in the project's own repeated leakage-pattern history plus general RL/scraping domain knowledge)
- Point-gain estimates for every experiment: LOW, by design — carried forward verbatim from `.planning/research/XP-IMPROVEMENT-OPTIONS.md`'s own explicit honesty framing; this phase's entire structure (opt-in flags, harness-judged adoption) exists because these estimates are not trustworthy in advance

**Research date:** 2026-09-08
**Valid until:** ~14 days for the FBref/FotMob/package-version specifics (fast-moving: unofficial APIs and bleeding-edge RL package versions drift quickly); ~30 days for the codebase-integration-pattern findings (stable — these are architectural seams already established across 8 prior phases)
