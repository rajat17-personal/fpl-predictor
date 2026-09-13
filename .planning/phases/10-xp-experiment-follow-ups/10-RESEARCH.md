# Phase 10: xP Experiment Follow-ups - Research

**Researched:** 2026-09-10
**Domain:** ML data-engineering experiments (availability/injury/sentiment features, model-class bracket, external benchmarks) inside an existing honest walk-forward harness
**Confidence:** MEDIUM — the harness/flag/fetcher conventions are HIGH confidence (read directly from the codebase); several external sources (Transfermarkt access risk, FPL-Core-Insights exact schema, the IJCSS 2025 paper's actual claims) are MEDIUM/LOW and flagged individually below.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Sequencing & kill conditions**
- **D-01:** Execution order: Tier-3 benchmarks land FIRST (near-zero cost; fplreview capture is deadline-gated so every missed GW is data permanently lost), then Tier 1 → Tier 2.
- **D-02:** News sentiment (Guardian/GDELT) build trigger is a pre-declared Spearman threshold, not vibes: if after BOTH Tier-1 experiments the benchmark Spearman vs ep_next is still below ~0.50 (roughly half the 0.383→0.579 gap closed — planner locks the exact number before any Tier-1 run), sentiment gets built; otherwise recorded as not-triggered in the ledger (capt_mc precedent).
- **D-03:** Model-class bracket runs UNCONDITIONALLY (Phase 9 D-01 precedent: run everything, results inform interpretation only) — it answers a different question (model class vs input signal) than the availability work.
- **D-04:** Manual FBref snapshot + RL reward-shaping notes both stay in scope, sequenced dead last. FBref happens only if everything else lands with time to spare and the user is willing to do the manual CSV downloads. RL item is notes-only (IMPROVEMENTS.md addendum), no training.

**Availability data & backfill**
- **D-05:** FPL-Core-Insights 2025-26 per-GW backfill: vendor + verify first. Gate the commit on a verification pass spot-checking their frozen GW folders against our own 2026-08-31/2026-09-07 snapshots for schema and value agreement. Then commit as a one-time snapshot (theFPLkiwi pattern: README, retrieval date/URL, attribution). Leakage rule: use GW N−1's frozen folder for GW N (their folders freeze at GW end). — **Reversibility:** costly — committed data vintages live in git history permanently; keep it small (CSVs only).
- **D-06:** Transfermarkt injury backfill depth: ALL training seasons 2016-17+ — the whole point of this source is reaching where FPL flags can't; fetcher runs as a background killable job (rate-limit-bound wall clock accepted). A/B on the full 6-season walk-forward.
- **D-07:** Transfermarkt storage: committed snapshot — the normalized injury-spell table (CSV/parquet + README with retrieval date), like the kiwi data; weeks of fetching must never need redoing. Raw page cache may stay uncommitted. — **Reversibility:** costly — same git-history permanence as D-05.
- **D-08:** Snapshot cron gap fix is IN SCOPE: anacron-style catch-up — on boot/first-run-of-day, if today's snapshot is missing, capture it (data/snapshot.py is already idempotent per UTC day). Context: only 2 of 10 days captured since 2026-08-31 (2026-08-31, 2026-09-07) because WSL cron doesn't fire when the machine is off.

**Adoption criteria (P(play) / partial-coverage experiments)**
- **D-09:** FPL availability-flags experiment is judged on a DUAL criterion, both must hold: (a) covered-season (2025-26) walk-forward model+chips improves ≥ +25 points, AND (b) benchmark Spearman vs ep_next improves ≥ +0.03 over the 0.383 baseline. Transfermarkt (full coverage) keeps the standard 6-season protocol.
- **D-10:** D-07 auto-adopt stands for availability flags, but with a mandatory safe fallback: when no fresh pre-deadline snapshot exists, availability features go NaN and the prediction degrades to today's behavior — asserted by a test before the flag can flip.
- **D-11:** Final combined run (Phase 9 D-13 pattern) uses SPLIT VERDICTS: the combined 6-season run includes only full-coverage winners, judged on ≥2,280; availability flags carry their own dual-criterion verdict recorded separately in the ledger. No forced apples-to-oranges combination.

**Model-class bracket**
- **D-12:** Candidate roster — six families, all replacing only the E[pts|played] regressor (LightGBM keeps the P(play) stage): Ridge/ElasticNet, XGBoost, CatBoost, small MLP, one recurrent (LSTM or GRU, not both), and a small transformer encoder (user explicitly added). LambdaRank/ranking loss excluded (already rejected with numbers).
- **D-13:** Compute is HYBRID, superseding Phase 9's D-15 for this bracket only: the user has Colab Pro with 200 compute units (no new spend). For each candidate, assess whether Colab training gives a wall-clock benefit and assign accordingly; even at speed parity, divide candidates across local WSL and Colab to parallelize the bracket. Budget: all 200 units + open-ended local overnights; hard stop at unit exhaustion, recorded per D-16 discipline.
- **D-14:** Colab↔local handoff: Colab runs the full per-season expanding-window walk-forward retrain loop for its candidates (features/sequence data uploaded, pinned seeds/configs), producing frozen per-season test-prediction files committed back; the local harness scores those artifacts exactly like Phase 9's enrichment_preds_* parquets. The local harness remains the sole judge.
- **D-15:** Two-stage gate: stage-1 cheap gate advances a candidate only if val-split played-only Spearman ≥ LightGBM + 0.01 (MAE recorded as diagnostic, never a gate); only gate-winners get the full 6-season walk-forward on the ≥2,280 bar.
- **D-16:** New packages (xgboost, catboost, any transformer helper) enter a dev-only hash-locked experiments lockfile (extend requirements-rl.txt or a new requirements-experiments.txt), never Dockerfile/CI (D-09 Phase 9 pattern), each through the blocking-human D-12 package-legitimacy gate.
- **D-17:** If a torch-based candidate clears the bar: adopt via runtime-free inference — export weights to ONNX (onnxruntime as a small CPU dep) or a numpy forward pass; torch stays dev-only. Production image never carries torch. — **Reversibility:** reversible — the export path is additive; the LightGBM default remains one flag away.
- **D-18:** Granularity: deep candidates (MLP, recurrent, transformer) run BOTH pooled-with-position-feature and per-position variants; each candidate's better validation variant enters the cheap gate. Classical/GBDT candidates stay per-position, mirroring LightGBM.
- **D-19:** Tuning budget is asymmetric: XGBoost/CatBoost get sensible defaults (LightGBM-adjacent, low expected delta); deep candidates get the real declared search budget. All searches logged like models/tune.py.
- **D-20:** Sequence-model inputs: raw per-GW stats for the last ~10 GWs (padded/masked) PLUS a static side-vector (position, price, current-GW fixture context) concatenated after the encoder — the network learns its own temporal aggregation (the hypothesis under test).
- **D-21:** The new sequence builder is a fresh leakage surface: tests/test_leakage.py gets explicit new assertions that every timestep feeding a GW-g prediction comes from GWs < g, proven on real data (Phase 9 team-strength discipline).

### Claude's Discretion
- Exact flag names in config.EXPERIMENTS, module layout for new code (e.g. data/transfermarkt.py, models/bracket/, predict/benchmarks.py), sequence window length within ~8–10 GWs, transformer size budget, exact Colab notebook structure and artifact naming, rate-limit values and cache layout for Transfermarkt/Guardian/GDELT, and the exact Spearman threshold value for D-02 (declared in the plan before any Tier-1 run).
- fplreview weekly capture workflow details (where the manual download/paste step lives) — design for minimal user friction; the todo allows dropping it if the manual step proves annoying.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (The two lowest-priority items — FBref manual snapshot, RL shaping notes — stay in-phase at the tail per D-04 rather than deferring.)
</user_constraints>

<phase_requirements>
## Phase Requirements

Phase 10 is **not** mapped in `.planning/REQUIREMENTS.md`'s v1/v2 traceability table — it is an experiment-tracking phase whose spec is the 8 pending todos (`resolves_phase: 10`), not formal REQ-IDs. The table below maps each todo to the research support in this document so the planner can trace coverage the same way it would trace a REQ-ID.

| Todo (spec) | Tier | Research Support |
|----|------|------------------|
| `2026-09-10-top100-consensus-benchmark.md` | 3 | FPL standings/entry endpoint shapes, throttling convention — see Standard Stack / Code Examples |
| `2026-09-10-fplreview-scoreboard-benchmark.md` | 3 | Confirmed live 403 to automated access; manual-capture pattern — see Pitfalls, Architecture Patterns |
| `2026-09-10-availability-flags-pplay.md` | 1 | OpenFPL encoding precedent, FPL status-code table, snapshot-join design, leakage caveat — see Architecture Patterns, Code Examples, Pitfalls |
| `2026-09-10-transfermarkt-injury-history.md` | 1 | URL pattern, ID-resolution gap, DataDome/Cloudflare access risk, figshare pre-scraped alternative — see Pitfalls, Open Questions |
| `2026-09-10-model-class-bracket.md` | 2 | Package audit, Colab handoff design gap, two-stage gate reuse, sequence-leakage test pattern — see Standard Stack, Package Legitimacy Audit, Architecture Patterns |
| `2026-09-10-news-sentiment-conditional.md` | 2 (conditional) | GDELT/Guardian API specifics, mlpremier's own **negative** finding — see State of the Art, Pitfalls |
| `2026-09-09-manual-fbref-snapshot.md` | tail | No new research needed — kiwi pattern reused verbatim per the todo |
| `2026-09-09-rl-reward-shaping-revisit.md` | tail | No new research needed — notes-only, Ng et al. 1999 potential-based shaping already cited by the todo |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.14, conda env `python314` at `/home/sraja/miniconda3/envs/python314/bin/python3.14` for all Python work — confirmed active this session (`python --version` → 3.14.3).
- `snake_case.py` modules, `snake_case` functions/vars, `ALL_CAPS` constants, `from __future__ import annotations`, type hints on signatures, `dict | None` union syntax.
- Print-based status/progress logging with module tags (`[fotmob]`, `[snapshot]`) — no logging framework. New fetchers must follow this.
- Error handling: `raise SystemExit(...)` for user-facing CLI failures, `try/except Exception` guarding *optional* enrichment, `ValueError` for parameter validation, HTTP errors via `resp.raise_for_status()`.
- No build step; every module runs via `python -m package.module`.
- `Model/decision-quality improvements` are listed **Out of Scope** in `.planning/REQUIREMENTS.md` for the *v1 production-hardening milestone* — Phase 10 is explicitly the exception the user carved out post-v1 (ROADMAP evolution entry), not a contradiction; no plan should treat this phase as blocked by that v1 line.
- This is a **solo dev, pre-revenue** project — every new dependency, scraper, or cloud spend must stay free-tier / no-new-spend (Guardian free key, GDELT keyless, Colab Pro already owned, no new API purchases).

## Summary

Phase 9 closed with every one of its 8 experiment flags rejected and measured `model+chips` (2,262) unchanged from baseline. Its own diagnostic run (`backtest/benchmark_external.py`) found the real gap is not season points but **ranking accuracy**: our `xp_med`/`xp_mean` land at pooled Spearman 0.383 against FPL's own `ep_next`'s 0.579 on played-only rows. Phase 10 chases that specific gap (availability/injury signal Tier 1, unconditional model-class bracket Tier 2) plus two low-cost diagnostic benchmarks (Tier 3), inside the same pre-declared-criteria / default-off-flag / ledger-verdict discipline Phase 9 built. CONTEXT.md has already locked almost every implementation decision (D-01 through D-21); this document supplies the missing *technical* facts those decisions assume — exact endpoints, package versions, encoding schemes, access-risk evidence, and one significant code-seam correction.

**The single most important correction this research makes:** CONTEXT.md's canonical_refs describe `backtest/walk_forward.py`'s "enrichment_preds_* artifact-scoring path" as an existing template for scoring Colab-produced prediction files. **No such path exists yet** — grepped and confirmed absent. The actual existing precedent is `backtest/benchmark_external.py` (loads an external per-season CSV/parquet, computes fixture-level MAE/Spearman against `y_points`) plus `models/train.py`'s `test_predictions.parquet` shape (`season, gw, player_code, player_id, name, team, position, price_m, y_points, y_minutes, xp_med, xp_mean, xp_form, xp_fpl`). Neither one currently feeds Colab-produced predictions into `backtest/season.py::run_season` for a whole-season `model+chips` score — that ingestion path (load an externally-supplied `xp_med`/`xp_mean` parquet in place of an in-process-trained model's predictions, at the exact `_preds_for()` seam) is **new infrastructure this phase must build**, not reuse.

The second major finding: **Transfermarkt access risk is unresolved and should be spiked, not assumed** — mixed 2025/2026 evidence exists for both "simple `requests` + headers still work" and "DataDome/Cloudflare blocks it," and `worldfootballR` (the reference implementation the todo cites) has been **archived** (read-only, no further maintenance) since 2025-09-18. This is the same access-risk shape that burned three real spike attempts on FBref in Phase 9 (D-04's own precedent). A bounded spike (5-10 real player pages, plain `requests`) before committing to a 6-season fetcher build is strongly recommended, mirroring Phase 9's own FBref discipline — and a pre-scraped injury dataset on figshare (unconfirmed, 403'd on direct fetch) is worth a 10-minute check first since it could make the fetcher unnecessary entirely.

Third: **mlpremier (arXiv 2405.02412), the repo D-02's news-sentiment todo explicitly cites to mine, is itself a *negative* result for exactly this feature** — its own Guardian-based sentiment transfer-learning experiment "did not identify a strong predictive signal in natural language news texts," underperforming both its CNN and its Ridge/LightGBM baselines. This does not block D-02's conditional trigger (which is correctly gated on a measured Spearman shortfall, not on this prior), but it is directly relevant prior evidence the plan and the eventual ledger entry should cite.

**Primary recommendation:** Tier 3 first (near-zero cost, deadline-gated — exactly as D-01 orders it), building the FPL top-100 standings/consensus fetcher and the fplreview manual-capture workflow into `predict/scoreboard.py`. Before starting Tier 1's Transfermarkt work, spend one bounded session (mirroring the FBref spike) confirming real page access; do not build the full fetcher infrastructure until that access is confirmed. Before Tier 2's Colab handoff, build and land the "score an externally-supplied prediction parquet through `run_season`" seam as its own small task — every Colab-trained candidate's adoption verdict depends on it existing and being tested first.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FPL availability-flag capture (status/news/chance_of_playing) | Data Ingest (`data/snapshot.py`) | Feature Engineer | Already-running daily cron; only needs new `_ELEMENT_COLS` entries — a pure data-capture concern, not a feature-engineering one |
| Availability-feature join (pre-deadline snapshot → player-GW) | Feature Engineer (new code, `features/engineer.py` or a sibling module) | — | This is genuinely pre-match CONTEXT (like `ODDS_COLS`), not a rolled per-match outcome (like `ROLL_STATS`) — a new join family, not a `ROLL_STATS` extension |
| Transfermarkt injury fetch + normalize | Data Ingest (new `data/transfermarkt.py`) | — | Mirrors `data/fotmob.py`/`data/understat.py` exactly: kill switch, cache, throttle, crosswalk join |
| Injury-spell → player-GW feature | Feature Engineer | — | Pre-match context (was this player injured as of kickoff), joined by date-range overlap — a new join pattern, closer to the availability join than to `ROLL_STATS` |
| Model-class bracket (candidate regressors) | Model Training (`models/train.py` + new `models/bracket/`) | Backtest (scoring) | Six new regressor implementations behind the existing per-position E[pts\|played] seam; `backtest/walk_forward.py` stays the sole judge |
| Colab-trained candidate scoring | Backtest (`backtest/walk_forward.py`, new ingestion function) | — | New code: load an externally-produced per-season prediction parquet and route it through the same `run_season`/chip-scoring path `_preds_for()` currently feeds |
| News sentiment (GDELT/Guardian, conditional) | Data Ingest (new `data/news.py` or similar) | Feature Engineer | Same shape as Transfermarkt: fetch → normalize → crosswalk-join → pre-match feature |
| Top-100 consensus benchmark | Predict/Product (`predict/scoreboard.py`) | Data Ingest (FPL standings fetch) | Diagnostic-only, scoreboard-internal — never touches `predict/live.py`/`predict/export.py` per the phase's own default-off/no-product-wiring discipline |
| fplreview weekly benchmark | Predict/Product (`predict/scoreboard.py`) | Data External snapshot (`data/external/fplreview/`) | Manual-assisted capture + committed small CSVs, scored the same way as the FPL consensus column |
| Anacron-style snapshot catch-up (D-08) | Ops/Scheduling (`scripts/daily.sh` or `data/snapshot.py`'s own entry point) | — | A scheduling/idempotency fix, not a data-shape change — `data/snapshot.py::take_snapshot` is already idempotent per UTC day |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | (already a project dep) | All new fetchers (Transfermarkt, GDELT, Guardian, FPL standings) | Matches every existing fetcher (`data/fotmob.py`, `data/understat.py`, `data/snapshot.py`) — no wrapper packages per Phase 9's D-11 precedent |
| xgboost | **3.4.1** latest on PyPI [VERIFIED: pypi via `pip index versions`, 2026-09-10] — env currently has 3.2.0 installed ad hoc, **not** in any requirements file | Model-class bracket candidate (D-12) | GBDT sibling to LightGBM; cheap, sensible-defaults tuning per D-19 |
| catboost | **1.2.10** latest on PyPI [VERIFIED: pypi] | Model-class bracket candidate (D-12) | Second GBDT sibling; ordered boosting handles categoricals differently from LightGBM/XGBoost, useful as a diversity check |
| scikit-learn | already project dep (1.4+) | Ridge/ElasticNet classical-floor candidate (D-12) | Already installed for isotonic calibration — `sklearn.linear_model.Ridge`/`ElasticNet` need zero new packages |
| torch | **2.12.0** [VERIFIED: 09-CONTEXT.md D-06 package-legitimacy audit, Phase 9, human-approved] — already pinned in `requirements-rl.txt`, `torch.cuda.is_available()` confirmed `True` this env | MLP / LSTM-GRU / transformer-encoder candidates (D-12, D-20) | Already installed, GPU-proven (RL training used it); `nn.LSTM`/`nn.GRU`/`nn.TransformerEncoder` cover every deep candidate with zero new packages |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| onnxruntime | **1.29.0** latest [VERIFIED: pypi] | D-17's runtime-free inference export, IF a torch candidate clears the adoption bar | **Defer this install** until a torch candidate actually wins — do not add it speculatively; it may never be exercised |
| gdeltdoc | **1.12.0** latest [VERIFIED: pypi] — third-party client (alex9smith/gdelt-doc-api) for the keyless GDELT DOC 2.0 API | D-02-conditional news sentiment, GDELT half | Optional convenience wrapper; the raw `doc?query=...&mode=ToneChart` HTTP endpoint is also trivially callable with plain `requests`, matching the "no wrapper package" convention more closely |
| — (no package) | — | Guardian Open Platform API | Plain `requests` against `https://content.guardianapis.com/search?api-key=...` — no maintained lightweight Python client package was found; matches the project's own "thin requests wrapper" convention better than adopting a new dependency |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| torch-based MLP | `sklearn.neural_network.MLPRegressor` | Zero new deps, CPU-only, no GPU benefit for D-13's Colab-time-benefit assessment — the plan should still assess it (per candidate roster, an MLP is required) but torch is the more consistent choice given the transformer/recurrent candidates already require it |
| skorch (sklearn wrapper around torch) | Raw torch training loop | `optimize/rl_train.py` already establishes the project's own raw-torch-training-loop convention (no `skorch`/`pytorch-lightning`); adding a wrapper package for 3 candidates when the project already has a working from-scratch pattern is unnecessary dependency surface |
| Custom Transfermarkt scraper (`data/transfermarkt.py`, D-06/D-07's stated path) | The figshare "Injuries from Transfermarkt.com" pre-scraped dataset (unconfirmed coverage/license — 403'd on direct fetch this session) | **Worth a 10-minute check before writing any scraper** — if it covers EPL 2016-17+ with an open license, it could satisfy D-06/D-07 with zero scraping infrastructure; document as a discovery task at the top of the Tier-1 Transfermarkt plan, not skipped |
| Direct GDELT `doc` HTTP calls | `gdeltdoc` pip package | Either works; `gdeltdoc` saves writing the tone-chart query-string builder but is one more (small, low-risk) new dependency |

**Installation (only if/when each tier is reached — do not install speculatively):**
```bash
# Tier 2, model-class bracket (add to a new requirements-experiments.txt, -c requirements-rl.txt -c requirements.txt)
pip install xgboost==3.4.1 catboost==1.2.10

# Tier 2, ONLY if a torch candidate clears the adoption bar (D-17)
pip install onnxruntime==1.29.0

# Tier 2, conditional (D-02), GDELT half only if the plain-requests approach is not preferred
pip install gdeltdoc==1.12.0
```

**Version verification:** Confirmed live via `pip index versions <pkg>` in the project's own conda env (`python314`) on 2026-09-10. `xgboost` was found **already installed ad hoc (3.2.0)** in this environment but absent from every `requirements*.txt`/`.in` file — the planner should not assume it is "already available" for CI/fresh-environment purposes; it must still go through the D-16 lockfile + package-legitimacy gate like every other new dependency.

## Package Legitimacy Audit

Ecosystem: PyPI. Checked via `gsd-tools query package-legitimacy check --ecosystem pypi xgboost catboost onnxruntime skorch` (2026-09-10).

| Package | Registry | Age / publishedAt (latest ver.) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| xgboost | PyPI | 2026-08-xx (latest release) | unknown (seam reports null) | none surfaced by the seam (well-known: github.com/dmlc/xgboost) | **SUS** — reasons: `too-new`, `unknown-downloads`, `no-repository` | Flagged — planner must add `checkpoint:human-verify` before install (long-established package; SUS verdict is a seam limitation — see note below) |
| catboost | PyPI | 2026-02-18 (latest release) | unknown | `catboost.ai` (surfaced) | **SUS** — reason: `unknown-downloads` | Flagged — planner must add `checkpoint:human-verify` before install |
| onnxruntime | PyPI | 2026-08-17 (latest release) | unknown | `onnxruntime.ai` (surfaced) | **SUS** — reasons: `too-new`, `unknown-downloads` | Flagged — planner must add `checkpoint:human-verify` before install (only if/when D-17 triggers) |
| skorch | PyPI | 2026-05-14 (latest release) | unknown | none surfaced | **SUS** — reasons: `unknown-downloads`, `no-repository` | **Not recommended for use at all** (see Alternatives Considered — raw torch loops already established) — no install needed |

**Reading these SUS verdicts:** the seam's `too-new`/`unknown-downloads` signals are triggered by each package's *most recent version's* publish date and a download-count lookup that returned null in this environment — not evidence of a hallucinated or newly-created package. All four are long-established, widely-used ML libraries (xgboost: ~9 years on PyPI; catboost: Yandex-maintained since 2017; onnxruntime: Microsoft-maintained since 2018) — this is a known seam limitation for fast-releasing, actively-maintained packages, exactly the same shape as Phase 9's own `uv`/`ruff` SUS-but-approved precedent (Phase 05-01). **Disposition: none removed (no SLOP verdicts)**; xgboost, catboost, and (conditionally) onnxruntime should proceed through the standard blocking-human D-12 checkpoint with this context, matching Phase 9's precedent for `torch`/`gymnasium`/`stable-baselines3`/`sb3-contrib` (all approved after a human review despite thin seam signal).

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** xgboost, catboost, onnxruntime — each needs a `checkpoint:human-verify` task in the plan before its first install, per protocol; skorch is simply not recommended (excluded from the plan's package list entirely, not merely gated).

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │            Tier 3 (near-zero cost, first)     │
                    │                                               │
  FPL standings API ─┤→ predict/scoreboard.py: top-100 consensus col │
  fplreview (manual)─┤→ data/external/fplreview/*.csv (committed)   │
                    │        → predict/scoreboard.py: MAE/Spearman │
                    └───────────────────┬───────────────────────────┘
                                        │ (diagnostic only, never a feature)
                    ┌───────────────────▼───────────────────────────┐
                    │       Tier 1 (availability / injury signal)    │
  data/snapshot.py  │                                               │
   (daily cron,     │→ new _ELEMENT_COLS (news, news_added,         │
   already running) │   chance_of_playing_this_round)                │
                    │                                               │
  FPL-Core-Insights │→ one-time vendored 2025-26 backfill            │
   (vendor+verify)  │   (data/external/fpl_core_insights/)           │
                    │        ↓                                       │
                    │  NEW join: pre-deadline snapshot → player-GW   │
                    │  (features/engineer.py sibling, NOT ROLL_STATS)│
                    │        ↓                                       │
  Transfermarkt     │→ data/transfermarkt.py (spike access FIRST)    │
   (injury spells)  │   → injury-spell table (committed, D-07)       │
                    │        ↓                                       │
                    │  NEW join: date-range overlap → player-GW      │
                    │        ↓                                       │
                    │  models/train.py P(play) stage ONLY            │
                    │        ↓                                       │
                    │  backtest/walk_forward.py: dual-criterion       │
                    │  adoption (D-09), safe-fallback test (D-10)    │
                    └───────────────────┬───────────────────────────┘
                                        │ (Spearman-gap check, D-02)
                    ┌───────────────────▼───────────────────────────┐
                    │       Tier 2 (model class, unconditional;       │
                    │        news sentiment, conditional on D-02)     │
                    │                                               │
  features.parquet ─┤→ 6 candidate regressors (Ridge/XGB/CatBoost/   │
   (same matrix,    │   MLP/LSTM-GRU/transformer), stage-1 cheap gate│
   same splits)     │   (D-15) on local val-split Spearman           │
                    │        ↓ (gate winners only)                   │
  Colab Pro (GPU-   │→ full 6-season walk-forward retrain loop       │
   bound candidates)│   → frozen per-season prediction parquet        │
                    │   → committed back to the repo                 │
                    │        ↓                                       │
                    │  NEW backtest/walk_forward.py ingestion path:  │
                    │  score an externally-produced prediction       │
                    │  parquet through run_season exactly like       │
                    │  _preds_for()'s in-process output (MUST BE     │
                    │  BUILT — no existing "enrichment_preds_*"      │
                    │  path found in the codebase)                   │
                    │        ↓                                       │
                    │  ≥2,280 bar, same as every Phase 9 experiment  │
                    └───────────────────────────────────────────────┘
```

### Recommended Project Structure
```
data/
├── snapshot.py                    # extend _ELEMENT_COLS (Tier 1a)
├── transfermarkt.py                # NEW — mirrors fotmob.py's shape exactly
├── news.py                         # NEW (conditional, D-02) — GDELT + Guardian
├── external/
│   ├── fpl_core_insights/          # NEW — vendored 2025-26 per-GW snapshot (D-05)
│   ├── transfermarkt/              # NEW — committed injury-spell table (D-07)
│   └── fplreview/                  # NEW — weekly manual-capture CSVs (Tier 3)
features/
├── engineer.py                     # extend: new pre-match join family for
│                                    #   availability/injury (NOT ROLL_STATS)
models/
├── train.py                        # unchanged interface; new regressor classes
├── bracket/                        # NEW — one module per candidate family
│   ├── ridge.py / xgb.py / catboost_model.py / mlp.py / rnn.py / transformer.py
backtest/
├── walk_forward.py                 # extend apply_experiment_feature_gating;
│                                    #   NEW: load_external_predictions() seam
├── benchmark_external.py           # reused as-is for the D-02 Spearman gate
predict/
├── scoreboard.py                   # extend: top-100 consensus col, fplreview col
scripts/
├── daily.sh                        # extend for D-08 anacron-style catch-up
colab/                              # NEW — notebook(s) + artifact-naming convention (D-14)
```

### Pattern 1: The fetcher convention (mirror for Transfermarkt/news)
**What:** Every optional-enrichment fetcher in this codebase (`data/fotmob.py`, `data/understat.py`) follows the identical shape: a module-level `<NAME>_ENABLED` kill switch, a `_throttle()` rate limiter, an on-disk JSON cache via `ops.jsonio`, a `_require()` explicit-shape validator (never silent NaN on a schema break), a `build(force=False)` that writes one tidy parquet, a `load_<name>()` that returns `None` if the cache is absent, and an `attach(full)` that joins by the shared `data.id_crosswalk.resolve_by_name` and asserts the row count is unchanged.
**When to use:** Every new Tier 1/2 fetcher (`data/transfermarkt.py`, `data/news.py`) should follow this exactly — it is the established, security-reviewed pattern (T-09-09-01's explicit-shape-validation rationale applies identically to an unofficial/undocumented Transfermarkt page or a GDELT schema change).
**Example:**
```python
# Source: data/fotmob.py (this codebase), the direct template
FOTMOB_ENABLED = True
_MIN_INTERVAL_S = 1.5

def _throttle() -> None: ...          # sleep until _MIN_INTERVAL_S has elapsed
def _require(payload, path, expected_type, what): ...  # explicit shape check
def build(*, force: bool = False) -> pd.DataFrame: ...  # fetch all, cache, write parquet
def load_fotmob() -> pd.DataFrame | None: ...            # None if absent, never raises
def attach(full: pd.DataFrame) -> pd.DataFrame: ...       # crosswalk join, row-count assert, coverage print
```

### Pattern 2: Experiment flag + feature-selection gate (config.py + walk_forward.py)
**What:** Every experiment gets one `config.EXPERIMENTS` key (default `False`), and one branch in `backtest/walk_forward.py::apply_experiment_feature_gating`. Data is computed **unconditionally** by the pipeline (join always runs if the source parquet exists); the flag only controls whether `walk_forward` drops/adds the columns before training — so toggling an experiment is never a `data/build_table.py` + `features/engineer.py` rebuild.
**When to use:** `availability_flags`, `transfermarkt_injury`, `news_sentiment` (D-02-conditional), and each of the six `bracket_*` candidates all need their own key.
**Example:**
```python
# Source: config.py (this codebase)
EXPERIMENTS: dict[str, bool] = {
    "capt_ceiling": False, "capt_mc": False, "chips_v2": False,
    "team_strength": False, "rl_strategy": False, "understat": False,
    "fotmob": False, "fbref_v2": False, "ep_next_lag": False, "ep_next_now": False,
    # Phase 10 additions (Claude's discretion for exact names):
    "availability_flags": False, "transfermarkt_injury": False,
    "news_sentiment": False,
    "bracket_ridge": False, "bracket_xgb": False, "bracket_catboost": False,
    "bracket_mlp": False, "bracket_rnn": False, "bracket_transformer": False,
}
```

### Pattern 3: The crosswalk join (identity resolution across sources)
**What:** `data/id_crosswalk.py::resolve_by_name` is the ONE shared name→`player_code` resolver — three tiers (theFPLkiwi `name_key`, `fbref_key`, then `_fpl_name_index()` over every historical `player_code` `data/id_map.py` has ever seen), plus a manual `_NAME_FIXUPS` dict for persistent misses. Transfermarkt and any news source join through this exact function — **never** a second, competing name matcher (the explicit lesson from the FBref many-to-many join corruption in Phase 9/Phase E).
**When to use:** Every new source in this phase that only carries a display name, no FPL id.
**Note:** Transfermarkt profile pages are keyed by a **Transfermarkt player ID**, not a name — resolving FPL player → Transfermarkt ID is itself a name-matching problem the crosswalk should be extended to cover (store the resolved `tm_player_id` once per `player_code`, cached, rather than re-searching Transfermarkt's search endpoint on every fetch).

### Pattern 4: Leakage-safe feature families — THREE distinct patterns now exist, not one
This phase must not force Tier 1's new availability/injury features through the existing `ROLL_STATS` shift-then-roll machinery — that path is specifically for **match outcomes** (stats describing the fixture that already happened, e.g. `fm_tackles`, `us_npxg`). Availability status and injury state are **pre-match context known before kickoff** (like `ODDS_COLS`/`TEAM_STRENGTH_COLS`), but unlike those two, they come from a **point-in-time snapshot table**, not a per-fixture join key — a genuinely new pattern:

| Family | Existing example | Join key | Leakage rule |
|---|---|---|---|
| Match-outcome, rolled | `us_npxg`, `fm_tackles` (`ROLL_STATS`) | `(season, player_code, match_date)` | `shift(1)` then rolling window — never raw |
| Fixture context, static-per-fixture | `odds_pwin`, `ts_attack_self` (`CONTEXT_COLS`) | `(season, fixture_id)` or team-level rating as-of gw | Known before kickoff by construction (published odds/ratings) — used raw |
| **NEW: point-in-time snapshot, as-of-deadline** | availability flags, injury status | `(player_code, nearest snapshot date < gw deadline)` | Must use the **latest snapshot/record strictly BEFORE the gameweek's deadline_time** — not the fixture's own kickoff, and critically not any record dated during/after the gameweek (the FPL-Core-Insights "frozen at GW end" trap D-05 already names) |

**Example (the snapshot-join leakage rule, to encode as a `tests/test_leakage.py` assertion per D-10's safe-fallback requirement):**
```python
# Conceptual pattern for features/engineer.py's new availability join —
# not existing code; this phase must write it.
# 1. Get each gw's deadline_time from the FPL events endpoint / a cached copy.
# 2. For each (season, player_code, gw), select the snapshot with the
#    MAX(date) such that snapshot.date < deadline_time(season, gw).
# 3. If no such snapshot exists (D-10's fallback case): NaN, not an error —
#    LightGBM handles NaN natively; a test must assert this degrades
#    gracefully rather than raising or silently using a future snapshot.
```

### Anti-Patterns to Avoid
- **Treating FPL-Core-Insights' per-GW folder as "state as of that GW's deadline":** D-05 is explicit that these folders freeze at GW **end** (after the deadline, after news arrives during the week) — the correct leakage-safe join uses GW **N−1**'s folder as the proxy for "known before GW N's deadline." Confirm this by spot-checking the folder's own `snapshot_date`/`updated_at` metadata against known deadline times before trusting the offset-by-one rule blindly.
- **Building the Transfermarkt fetcher before confirming access:** Phase 9's FBref experience (3 real spike attempts, all failed against Cloudflare, "not acquirable" recorded honestly in IMPROVEMENTS.md) is the direct precedent for treating access confirmation as its own gated step, not an assumption baked into the plan.
- **Reusing `ROLL_STATS`/`shift(1)` for availability or injury features:** these are not match outcomes; shifting them by one fixture would use the WRONG lookback horizon (a player's availability status two fixtures ago is not "the most recent known status" once a DGW or postponement has occurred) — the correct join is date-based against the deadline, described above.
- **Assuming `enrichment_preds_*` already exists:** it does not (confirmed by grep on this session's codebase read) — build and test the external-prediction ingestion seam as an explicit Tier-2 task before any Colab candidate is scored, not as an afterthought once Colab artifacts start arriving.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Name→player identity resolution for Transfermarkt/news sources | A second name-matcher dict | `data.id_crosswalk.resolve_by_name` (extend `_NAME_FIXUPS`) | The exact lesson of the FBref many-to-many join corruption this project has already paid for once |
| Guardian/GDELT sentiment scoring | A custom LLM/transformer sentiment classifier | GDELT's own built-in `Tone`/`ToneAbs` score (no model needed, per the todo's own scoping) and simple doc-count aggregation | The todo explicitly scopes this as "no sentiment model needed" — GDELT's tone score is pre-computed server-side |
| ONNX export of a torch model (D-17, if triggered) | A hand-written numpy forward pass for every candidate architecture | `torch.onnx.export` + `onnxruntime.InferenceSession` | Standard, well-tested export path; a hand-rolled forward pass duplicates the framework's own graph tracing and risks silent numerical drift between train/inference |
| Two-stage gate Spearman computation | A new metrics helper | `models/train.py::_report`'s existing `spearman` computation pattern (played-only, `pd.Series.corr(method="spearman")`) | Already the exact metric definition D-15's "played-only fixture-level Spearman" refers to |
| Sequence-model padding/masking for the last ~8-10 GWs (D-20) | A custom padding scheme | `torch.nn.utils.rnn.pad_sequence` + an explicit boolean mask fed to `nn.LSTM`/`nn.GRU`/`nn.TransformerEncoder`'s `src_key_padding_mask` | Standard PyTorch idiom; a hand-rolled padding scheme is exactly the kind of "deceptively complex" problem (variable-length early-season sequences, DGW double-counting) this rule exists for |

**Key insight:** every fetcher, join, and identity-resolution problem in this phase has a directly analogous, already-built-and-tested precedent somewhere in `data/` or `backtest/` from Phase 9 — the discipline that keeps this phase safe is reusing those exact shapes rather than inventing parallel ones, especially given Phase 9's own hard-won lesson (the FBref/id_map many-to-many join corruption) about what happens when a second ad-hoc matcher is grown instead.

## Common Pitfalls

### Pitfall 1: Transfermarkt access is genuinely uncertain, not merely "scrape it"
**What goes wrong:** Building the full D-06/D-07 fetcher (6 seasons, ~all-player backfill) before confirming basic page access works, only to discover mid-build that DataDome/Cloudflare blocks plain `requests` — repeating Phase 9's FBref failure mode almost exactly.
**Why it happens:** Search results are genuinely mixed: some 2025/2026 guides claim Transfermarkt "is relatively straightforward to scrape with Python" using plain `requests` + a `User-Agent` header; others describe DataDome protection with JA3/HTTP-2 fingerprinting specifically noted as blocking bare `requests`. The reference implementation the todo cites, `worldfootballR`, was **archived (read-only)** on 2025-09-18 — no further maintenance if Transfermarkt's HTML/anti-bot posture changes.
**How to avoid:** Spike first (mirroring Phase 9's D-04 FBref discipline): fetch 5-10 real player injury-history pages with plain `requests` + a realistic `User-Agent`, log pass/fail, before writing any caching/throttling/normalization infrastructure. Also spend 10 minutes checking the figshare "Injuries from Transfermarkt.com" pre-scraped dataset (this session's WebFetch got a 403 — could not confirm coverage/license/EPL inclusion) as a possible shortcut that avoids scraping entirely.
**Warning signs:** A 403/429 on the very first real page, or a response body containing a DataDome/Cloudflare challenge script rather than the injury table HTML — treat exactly like Phase 9's "not acquirable" verdict shape if it recurs after a real attempt, not as a transient error to retry indefinitely.

### Pitfall 2: FPL-Core-Insights' exact per-GW CSV schema is unconfirmed
**What goes wrong:** Designing the D-05 verification-and-commit pipeline against an assumed column layout that doesn't match the actual repo.
**Why it happens:** This session's research could confirm the repo exists, is actively maintained (2026/27 season coverage), and has a season-keyed `data/` directory (`2024-2025`, `2025-2026`, `2026-2027`) with both a cumulative "playerstats" table and a derived "per-gameweek" table (delta-computed) — but could **not** retrieve the actual column list, per-GW subfolder naming, or license from a directory-listing fetch.
**How to avoid:** The first Tier-1 availability-flags plan task should be a direct `curl`/`requests` fetch of one real per-GW CSV from `raw.githubusercontent.com/olbauday/FPL-Core-Insights/...` and a `LICENSE` file check — mirroring `data/external/README.md`'s existing "PII spot-check" and "Reduction applied" discipline for the kiwi snapshot — **before** designing the join, not assumed from this research.
**Warning signs:** Column names that don't match `status`/`chance_of_playing_next_round`/`news`/`news_added` 1:1 — the join code should validate this explicitly (`_require`-style) rather than silently producing NaN columns.

### Pitfall 3: mlpremier is a *negative* prior for D-02's own cited feature
**What goes wrong:** Treating `danielfrees/mlpremier` (arXiv 2405.02412) as validating evidence for building the Guardian/GDELT sentiment feature, when its own published result is the opposite.
**Why it happens:** The todo cites this repo as "related... to mine" without characterizing its finding. This session's research confirms: the paper's Guardian-based news-sentiment transfer-learning experiment **did not identify a strong predictive signal**, underperforming both the paper's own CNN and its Ridge/LightGBM baselines.
**How to avoid:** This does not block D-02 (which is correctly triggered by a measured Spearman shortfall, not by prior literature), but the plan and ledger entry should cite this as a directly relevant negative prior — it lowers the expected-value prior for this experiment even if D-02's trigger condition fires, and should inform how much effort/tuning budget to allocate if it is built.
**Warning signs:** None specific — this is a framing correction for interpretation, not a code risk.

### Pitfall 4: the IJCSS 2025 paper (10.2478/ijcss-2025-0008) could not be independently verified this session
**What goes wrong:** Treating the Tier-1 todos' claimed findings from this paper ("clearest wins were on the will-play classification task," "regression gains cherry-pick flavored but classification gains directionally consistent") as confirmed research when this session's web search could not locate the actual paper by DOI.
**Why it happens:** The DOI did not resolve in web search (searches returned unrelated NFL fantasy-football injury content); this may be a very-recent/low-visibility publication, a DOI typo in the todo, or a paywalled journal not indexed by the search tool used this session.
**How to avoid:** Treat every specific numeric/qualitative claim attributed to this paper in the CONTEXT.md/todos as `[ASSUMED]` (see Assumptions Log below) until the planner or an execution-time task independently retrieves and confirms it — do not cite it as settled evidence in the eventual ledger entry without that confirmation.
**Warning signs:** None code-related — a documentation/citation integrity risk only.

### Pitfall 5: fplreview.com actively blocks automated access — confirmed, not assumed
**What goes wrong:** Attempting to automate the fplreview capture (defeating the todo's own explicit "manual-assisted" scoping) and hitting a wall late.
**Why it happens / confirmed this session:** A direct `WebFetch` of `fplreview.com/terms-of-service/` returned **HTTP 403 Forbidden** in this research session — directly corroborating the todo's own claim ("their site 403s scrapers"). The Free Model's actual projection-table access mechanism (CSV? web app table? login-gated?) could not be determined from documentation alone.
**How to avoid:** Design the capture as genuinely manual from the start (a documented step: user visits `app.fplreview.com/free`, copies/exports the current week's table, drops it under `data/external/fplreview/`) — do not spend planning or execution budget on scraper attempts against this specific target. D-04/the todo already permit dropping this item entirely if the manual step proves annoying.
**Warning signs:** N/A — this is a confirmed access constraint, not a risk to monitor.

### Pitfall 6: the Colab↔local prediction-scoring seam does not exist and is a new leakage surface
**What goes wrong:** Assuming any externally-produced parquet with `xp_med`/`xp_mean` columns is automatically leakage-safe because it "looks like" `test_predictions.parquet`.
**Why it happens:** A Colab notebook training its own expanding-window walk-forward loop is re-implementing `models/train.py::train_predict`'s train/val/test season split logic from scratch — any drift (e.g. accidentally including the test season in training, or using the full dataset for a single global fit instead of D-14's per-test-season expanding window) produces a file that is schema-valid but leakage-corrupt, and the local harness has no way to detect this from the parquet alone.
**How to avoid:** The new `backtest/walk_forward.py` ingestion function (Pattern 4 above) should validate, not just load: assert the predicted seasons match `TEST_SEASONS`, and — where feasible — spot-check one candidate's Colab-produced predictions against a same-config LightGBM run's own `_preds_for()` output shape/row-count as a sanity check before trusting the walk-forward score.
**Warning signs:** A Colab candidate's fixture-level Spearman implausibly far above LightGBM's 0.383 on the SAME played-only benchmark (`backtest/benchmark_external.py`'s own methodology, reused for D-15's cheap gate) — a large, suspicious jump is the same "smells like leakage" signal that caught the multi-GW `+337-optimistic-vs-+40-honest` finding in Phase 9.

## Code Examples

### FPL top-100 standings fetch (Tier 3)
```python
# Conceptual — FPL API, unauthenticated, matches this project's existing
# requests + _HEADERS convention (predict/scoreboard.py, data/snapshot.py).
# League id 314 = the global "Overall" classic league (verified via community
# documentation this session; not independently re-verified against a live
# response in this research pass — spot-check the shape on the first real run).
import requests
_HEADERS = {"User-Agent": "fpl-ml-project/0.1"}

def fetch_top100(gw: int) -> list[dict]:
    rows = []
    for page in (1, 2, 3):   # ~50/page; 3 pages covers >=100 with margin for ties
        r = requests.get(
            "https://fantasy.premierleague.com/api/leagues-classic/314/standings/",
            params={"page_standings": page}, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        results = r.json()["standings"]["results"]
        if not results:
            break
        rows.extend(results)
    return rows[:100]
```

### Injury-spell overlap join (Tier 1, Transfermarkt)
```python
# Conceptual pattern for the player-GW injury feature.
# injuries: columns [player_code, from_date, until_date] (or until_date is
# null/NaT for an ongoing injury as of the retrieval date).
def injury_status_as_of(injuries: pd.DataFrame, player_code: int, as_of) -> dict:
    spells = injuries[injuries.player_code == player_code]
    active = spells[(spells.from_date <= as_of)
                    & (spells.until_date.isna() | (spells.until_date >= as_of))]
    if active.empty:
        return {"injured": False, "days_out_so_far": 0}
    row = active.iloc[0]
    return {"injured": True,
            "days_out_so_far": (as_of - row.from_date).days}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Proprietary "expected minutes" models (commercial services like FPL Review) | Categorical FPL API availability tags (`status`, `chance_of_playing_next_round`) as direct model features, no xMins sub-model | OpenFPL, arXiv:2508.09992 (Aug 2025) | Directly validates the Tier-1 availability-flags todo's approach: no need to build a proprietary xMins estimator first — consume FPL's own categorical tags |
| Assuming news/sentiment features help EPL player-performance forecasting | mlpremier's own transfer-learning experiment on Guardian news text found **no strong predictive signal**, underperforming simpler baselines | arXiv 2405.02412 (May 2024) | Lowers the expected value of D-02's conditional sentiment build even if its Spearman trigger fires; still worth the conditional test per the pre-declared-criteria discipline, but budget/tuning expectations should be modest |
| `worldfootballR` as the maintained reference for Transfermarkt scraping conventions | Repository **archived** (read-only) 2025-09-18 — no further endpoint-drift fixes upstream | 2025-09-18 | The todo's own instruction ("reimplement worldfootballR's documented endpoints... do not depend on the R package") already anticipated not depending on the package itself, but this also means there is no active upstream to consult if Transfermarkt's HTML changes after this phase ships |

**Deprecated/outdated:**
- The assumption that "Transfermarkt is easy to scrape with plain requests" (still repeated in some 2026 guides) should be treated with caution — it coexists with credible reports of DataDome-based anti-bot protection on the same site; resolve empirically (Pitfall 1), not from either single source.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The IJCSS 2025 paper (10.2478/ijcss-2025-0008) exists and supports the todos' specific claims about injury-history/will-play classification gains | Tier-1 todos (transfermarkt-injury-history.md, news-sentiment-conditional.md) | Could not verify this session (DOI did not resolve). If the paper's actual findings differ from what the todos summarize, D-06's expected-value case for the full 6-season backfill effort is weaker than stated |
| A2 | FPL-Core-Insights' per-GW CSV schema includes columns directly analogous to `status`/`chance_of_playing_next_round`/`news`/`news_added` | availability-flags-pplay.md, Pitfall 2 | If the actual schema differs, D-05's verification-spot-check design needs rework before the first commit |
| A3 | League id 314 is the correct/current FPL "Overall" global classic league id for top-100 consensus | top100-consensus-benchmark.md, Code Examples | If wrong or changed, the fetched "top 100" would be a random/wrong league — must be spot-checked against a known top overall manager on the first real run |
| A4 | Transfermarkt's injury-history page structure (`/verletzungen/spieler/{id}`) and its columns (season, injury type, from, until, days, games missed) remain stable and accessible via plain `requests` in this session's timeframe | transfermarkt-injury-history.md, Pitfall 1 | Directly gates whether D-06/D-07 can be executed as scoped at all — a spike is required before trusting this |
| A5 | The figshare "Injuries from Transfermarkt.com" dataset covers EPL, sufficient seasons, and has a usable license | Alternatives Considered | Could not confirm (403 on direct fetch) — if it doesn't cover EPL/is license-restricted, it's a dead end and the fetcher path is the only option |
| A6 | GDELT DOC 2.0's `Tone`/`ToneAbs` score, applied to player-name-mention doc counts, is a meaningful pre-match availability/sentiment signal for FPL purposes specifically (as opposed to general news sentiment) | news-sentiment-conditional.md | If not, the D-02-conditional build (even if triggered) may show no signal regardless of correct implementation — consistent with mlpremier's own negative finding (Pitfall 3) |

**If this table is empty:** N/A — six assumptions logged above, all flow from external-source claims this session could not independently and fully verify.

## Open Questions

1. **What is the FPL-Core-Insights repository's exact license?**
   - What we know: repository exists, actively maintained through 2026/27; a directory listing was retrievable.
   - What's unclear: LICENSE file contents — could not be fetched this session.
   - Recommendation: check `LICENSE`/`LICENSE.md` at the repo root as the very first Tier-1 execution step, mirroring `data/external/README.md`'s existing no-explicit-licence handling for theFPLkiwi (small research snapshot with attribution, not a redistribution under stated terms) — apply the same posture if this repo is similarly unlicensed, or a stricter one if it carries an explicit restrictive license.

2. **Does the figshare pre-scraped Transfermarkt injury dataset make the D-06/D-07 fetcher unnecessary?**
   - What we know: a dataset exists (~107k injuries, ~18,500 players, multi-league) per search-result summaries; could not be directly fetched (403) to confirm EPL coverage, season range, or license.
   - What's unclear: whether it actually satisfies "ALL training seasons 2016-17+" coverage for EPL specifically, and its license terms for a committed derivative.
   - Recommendation: a 10-minute check (try a direct download link, or the figshare API) at the very start of the Tier-1 Transfermarkt plan, before committing to building `data/transfermarkt.py` at all.

3. **Does Transfermarkt block programmatic access with `requests` in practice, right now, from this environment?**
   - What we know: mixed 2025/2026 evidence both ways; `worldfootballR` (the reference implementation) is archived.
   - What's unclear: the actual current behavior — genuinely untested this session (no live network probe was attempted against transfermarkt.com directly, since this research pass focused on documentation).
   - Recommendation: the bounded spike described in Pitfall 1, run as the literal first task of the Tier-1 Transfermarkt plan (mirroring Phase 9's D-04 FBref spike-first discipline), with its own go/no-go checkpoint before any fetcher infrastructure is built.

4. **What exact column shape should the new Colab-prediction ingestion function require?**
   - What we know: `models/train.py`'s `test_predictions.parquet` shape (`season, gw, player_code, player_id, name, team, position, price_m, y_points, y_minutes, xp_med, xp_mean, xp_form, xp_fpl`) is the closest existing analog; `backtest/benchmark_external.py` shows the pattern for scoring an external per-season file.
   - What's unclear: whether `y_points`/`y_minutes` (ground truth) should be re-attached locally (safer — Colab never touches ground truth beyond training) or trusted from the Colab artifact.
   - Recommendation: re-attach `y_points`/`y_minutes`/all `ID_COLS` locally after loading the Colab-produced `xp_med`/`xp_mean` predictions, joined on `(season, gw, player_code)` — Colab's artifact should carry predictions only, never re-derive ground truth, closing an entire class of accidental-leakage risk at the seam boundary.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| conda env `python314` | All Python work | ✓ | 3.14.3 | — |
| torch + CUDA | MLP/LSTM/transformer candidates (D-12/D-20), local half of D-13's split | ✓ [VERIFIED: 09-CONTEXT.md — `torch.cuda.is_available()` confirmed `True`, RTX 4080] | 2.12.0+cu130 | CPU-only training (slower; Colab GPU covers the gap per D-13) |
| xgboost / catboost | Model-class bracket | ✗ (not in any requirements file; ad-hoc 3.2.0 present but untracked) | — | Must be added to a new/extended requirements-experiments.txt per D-16 |
| Google Colab Pro | GPU-bound bracket candidates (D-13) | Assumed ✓ (user-stated, not independently verified this session) | 200 compute units, per D-13 | Local WSL overnight runs, per D-13's own fallback text |
| Guardian Open Platform API key | D-02-conditional news sentiment | Unknown — free key not yet obtained | — | GDELT alone (keyless) covers the "no build needed" half of D-02 if Guardian signup is deferred |
| GDELT DOC 2.0 API | D-02-conditional news sentiment | ✓ (keyless, no signup) [CITED: blog.gdeltproject.org] | n/a | — |
| Network access to transfermarkt.com from execution environment | Tier-1 Transfermarkt fetcher | **Unverified this session** (documentation research only, no live probe attempted against the actual site) | — | figshare pre-scraped dataset (Open Question 2), or defer/drop per Pitfall 1's spike-first gate |
| Network access to fplreview.com | Tier-3 fplreview benchmark | **Confirmed blocked for automated fetch** (403 observed this session) | — | Manual capture only, exactly as the todo scopes it |

**Missing dependencies with no fallback:**
- None outright-blocking — every Tier 1/2 external dependency has either a documented fallback (Guardian→GDELT-only, Transfermarkt→figshare-or-drop) or is explicitly gated behind a spike/verification step before commitment.

**Missing dependencies with fallback:**
- xgboost/catboost (not yet installed — straightforward pip install once package-legitimacy checkpoint clears)
- Guardian API key (GDELT alone can carry the conditional sentiment experiment if Guardian signup is skipped)
- Confirmed Transfermarkt access (figshare dataset or the drop-if-blocked precedent from Phase 9's FBref item)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest [VERIFIED: `pytest.ini` read this session, `testpaths = tests`] |
| Config file | `pytest.ini` (repo root) |
| Quick run command | `python -m pytest tests/test_leakage.py tests/test_experiments.py -x` |
| Full suite command | `python -m pytest` |

### Phase Requirements → Test Map
| Todo | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| availability-flags | Snapshot-join leakage: only a snapshot dated strictly before the gw deadline is used | unit | `pytest tests/test_leakage.py::test_availability_flags_use_only_pre_deadline_snapshot -x` | ❌ Wave 0 — new test needed |
| availability-flags | D-10 safe fallback: missing snapshot degrades to NaN, never raises, never uses a future snapshot | unit | `pytest tests/test_experiments.py::test_availability_flags_safe_fallback_on_missing_snapshot -x` | ❌ Wave 0 |
| transfermarkt-injury-history | Injury-spell dates strictly precede fixture kickoff | unit | `pytest tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff -x` | ❌ Wave 0 |
| model-class-bracket | Sequence builder: every timestep feeding a GW-g prediction comes from GWs < g (D-21) | unit | `pytest tests/test_leakage.py::test_sequence_features_no_future_gw_leakage -x` | ❌ Wave 0 |
| model-class-bracket | Two-stage gate Spearman computation matches `models/train.py::_report`'s definition | unit | `pytest tests/test_bracket.py::test_gate_spearman_matches_report_helper -x` | ❌ Wave 0 |
| top100-consensus-benchmark | Consensus fetch shape validation (standings response has expected keys) | unit | `pytest tests/test_scoreboard.py::test_top100_fetch_shape -x` | ❌ Wave 0 (no `tests/test_scoreboard.py` currently exists) |
| Colab ingestion seam | External prediction parquet validated (correct seasons, ID_COLS reattached, row-count assert) | unit | `pytest tests/test_experiments.py::test_load_external_predictions_validates_schema -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_leakage.py tests/test_experiments.py -x`
- **Per wave merge:** `python -m pytest`
- **Phase gate:** Full suite green before any adoption-deciding `backtest.walk_forward` run, matching Phase 9's own discipline (`tests/test_experiments.py`'s all-flags-default-off assertion must be re-verified whenever a new flag is added)

### Wave 0 Gaps
- [ ] `tests/test_leakage.py` — new assertions for availability-snapshot join, Transfermarkt injury-date ordering, and sequence-builder GW-ordering (D-21) — none exist yet
- [ ] `tests/test_bracket.py` — new file for model-class-bracket gate/scoring logic
- [ ] `tests/test_scoreboard.py` — new file; `predict/scoreboard.py` currently has no dedicated test file at all (confirmed via `ls tests/`)
- [ ] Framework install: none needed — pytest already fully configured

## Security Domain

`security_enforcement: true`, ASVS level 1, block on `high` [VERIFIED: `.planning/config.json`, this session].

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase adds no user-facing auth surface — all new code is offline data pipeline/experiment code |
| V3 Session Management | No | Same as above |
| V4 Access Control | No | No new API endpoints or access boundaries |
| V5 Input Validation | Yes | Every new fetcher's `_require()`-style explicit shape validation (Pattern 1) — an unofficial/scraped source's schema drift must raise, never silently propagate as NaN or (worse) a wrong-column value |
| V6 Cryptography | No | No new secrets/crypto surface beyond the existing `.env`/`load_dotenv()` pattern (mode-600 enforcement already exists) |
| V7 Error Handling / Logging | Yes | New fetchers must follow the existing `try/except requests.RequestException` + module-tagged print convention — never let a Transfermarkt/GDELT/Guardian outage crash the daily pipeline (matches `data/odds.py`'s "optional enrichment must never break the pipeline" contract) |
| V12 File & Resources | Yes | Guardian API key must load via `config.load_dotenv()`'s existing `.env` pattern (mode 600), never hardcoded — matches `ODDS_API_KEY`'s existing precedent exactly |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Scraped-page schema drift silently corrupting features (an unofficial Transfermarkt/GDELT/Guardian response shape changes) | Tampering (of trust, not malicious) | `_require()`-style explicit shape validation, matching `data/fotmob.py`'s existing T-09-09-01 precedent — raise, don't silently NaN |
| API key leakage in logs/commits (Guardian key) | Information Disclosure | `.env` file, mode 600, never committed — `config.load_dotenv()` already enforces the pattern; a new fetcher must read the key via `os.environ`, never hardcode or print it |
| Injury/name-matching false positives corrupting an unrelated player's P(play) prediction | Tampering | The crosswalk's own existing discipline (Pattern 3): whole-token verification, mononym exclusion, never a coincidental substring match — apply identically to Transfermarkt ID resolution |
| Committing a scraped dataset whose license/ToS forbids redistribution (Transfermarkt injury table, FPL-Core-Insights CSVs) | Legal/compliance (not STRIDE, but explicitly flagged by D-05/D-07's "costly reversibility" note) | Mirror `data/external/README.md`'s existing attribution + retrieval-date + "no explicit licence, treated as small research snapshot" posture — check each new source's actual license/ToS before committing, per Open Question 1 |

## Sources

### Primary (HIGH confidence)
- This codebase, read directly this session: `config.py`, `data/snapshot.py`, `data/fotmob.py`, `data/id_crosswalk.py`, `features/engineer.py`, `models/train.py`, `backtest/walk_forward.py`, `backtest/benchmark_external.py`, `predict/scoreboard.py`, `tests/test_leakage.py`, `data/external/README.md`, `.planning/config.json`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `IMPROVEMENTS.md`, `.planning/phases/10-xp-experiment-follow-ups/10-CONTEXT.md`, all 8 pending todo files
- `gsd-tools query package-legitimacy check` — xgboost/catboost/onnxruntime/skorch verdicts
- `pip index versions` — live PyPI version checks for xgboost, catboost, onnxruntime, skorch, gdeltdoc, theguardian-api-python (not found)

### Secondary (MEDIUM confidence)
- [OpenFPL paper (arXiv:2508.09992)](https://arxiv.org/abs/2508.09992) and [GitHub repo](https://github.com/daniegr/OpenFPL) — availability-tag approach, WebSearch-confirmed, aligns with `.planning/research/XP-IMPROVEMENT-OPTIONS.md`'s own prior citation
- [mlpremier paper (arXiv 2405.02412)](https://arxiv.org/abs/2405.02412) and [GitHub repo](https://github.com/danielfrees/mlpremier) — negative sentiment finding, WebSearch-confirmed
- [GDELT DOC 2.0 API blog announcement](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) and [gdelt-doc-api client](https://github.com/alex9smith/gdelt-doc-api)
- [Guardian Open Platform documentation](https://open-platform.theguardian.com/documentation/) — free-tier rate limits, historical archive since 1999
- [worldfootballR injury-history issue #58](https://github.com/JaseZiv/worldfootballR/issues/58) — URL pattern, archived-repo status
- [FPL-Core-Insights repository](https://github.com/olbauday/FPL-Core-Insights) — directory structure only, schema unconfirmed
- fplreview.com ToS — **directly observed 403 this session** via WebFetch (not merely cited secondhand)
- FPL API endpoint community documentation (Medium/cheatography-derived summaries) for `leagues-classic/{id}/standings/` and `entry/{id}/event/{gw}/picks/`

### Tertiary (LOW confidence)
- IJCSS 2025 paper (10.2478/ijcss-2025-0008) — **could not be located/verified this session**; every claim attributed to it in the todos is `[ASSUMED]` (Assumptions Log A1)
- figshare "Injuries from Transfermarkt.com" dataset — **403'd on direct fetch**, coverage/license unconfirmed (Assumptions Log A5)
- General "is Transfermarkt scrapeable" WebSearch results — mixed, contradictory, not resolved by a live probe this session (Assumptions Log A4, Open Question 3)

## Metadata

**Confidence breakdown:**
- Codebase patterns (fetcher convention, experiment flags, crosswalk, leakage tests, harness shape): HIGH — read directly from source this session
- FPL top-100/standings endpoint shapes: MEDIUM — community-documented, not independently probed against a live response this session
- Transfermarkt access risk: LOW/unresolved — genuinely contradictory secondary evidence; explicitly gated behind a required spike
- OpenFPL/mlpremier findings: MEDIUM-HIGH — WebSearch-confirmed against the papers' own abstracts/summaries, not full-text-verified line by line
- IJCSS 2025 paper claims: LOW — unverified, could not locate the source this session
- Package versions (xgboost/catboost/onnxruntime/gdeltdoc): HIGH — live `pip index versions` this session

**Research date:** 2026-09-10
**Valid until:** ~14 days for the fast-moving external-access items (Transfermarkt anti-bot posture, fplreview ToS enforcement); ~30 days for the codebase-pattern and package-version findings (stable, versioned artifacts)
