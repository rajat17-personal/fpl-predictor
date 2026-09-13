# Phase 10: xP Experiment Follow-ups - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Pursue the remaining measured leads from Phase 9's research sweep under the same honest-harness discipline (pre-declared criteria, default-off flags, ledger verdicts in IMPROVEMENTS.md), judged against the measured 2,262 model+chips 6-season baseline with the ≥2,280 adoption bar where full coverage applies.

**Already closed before this discussion** (do not re-plan): ep_next feature flags (quick 260909-elx, both rejected), per-position/covered-rows enrichment re-measurement (quick 260909-5vx), high-replica capt_ceiling re-run (quick 260909-dga, rejection confirmed), RL v2/v3 bigger-timestep runs (9h box declared 2026-09-09, evaluated 2026-09-10: beats chips_v2 on 2025-26 but −97 vs shipped heuristic, rejected, log-linear compute curve recorded).

**Live scope = the 8 pending todos** (all `resolves_phase: 10`), sequenced: Tier 3 benchmarks first (top-100 consensus, fplreview weekly capture — deadline-gated data accumulation), then Tier 1 (FPL availability flags into P(play), Transfermarkt injury history), then Tier 2 (model-class bracket — unconditional; Guardian/GDELT news sentiment — conditional on a pre-declared trigger), with the manual FBref snapshot and RL reward-shaping notes at the dead tail.

Depends on Phase 9 (experiment framework, flag registry, crosswalk, harness baselines).

</domain>

<decisions>
## Implementation Decisions

### Sequencing & kill conditions
- **D-01:** Execution order: Tier-3 benchmarks land FIRST (near-zero cost; fplreview capture is deadline-gated so every missed GW is data permanently lost), then Tier 1 → Tier 2.
- **D-02:** News sentiment (Guardian/GDELT) build trigger is a pre-declared Spearman threshold, not vibes: if after BOTH Tier-1 experiments the benchmark Spearman vs ep_next is still below ~0.50 (roughly half the 0.383→0.579 gap closed — planner locks the exact number before any Tier-1 run), sentiment gets built; otherwise recorded as not-triggered in the ledger (capt_mc precedent).
- **D-03:** Model-class bracket runs UNCONDITIONALLY (Phase 9 D-01 precedent: run everything, results inform interpretation only) — it answers a different question (model class vs input signal) than the availability work.
- **D-04:** Manual FBref snapshot + RL reward-shaping notes both stay in scope, sequenced dead last. FBref happens only if everything else lands with time to spare and the user is willing to do the manual CSV downloads. RL item is notes-only (IMPROVEMENTS.md addendum), no training.

### Availability data & backfill
- **D-05:** FPL-Core-Insights 2025-26 per-GW backfill: vendor + verify first. Gate the commit on a verification pass spot-checking their frozen GW folders against our own 2026-08-31/2026-09-07 snapshots for schema and value agreement. Then commit as a one-time snapshot (theFPLkiwi pattern: README, retrieval date/URL, attribution). Leakage rule: use GW N−1's frozen folder for GW N (their folders freeze at GW end). — **Reversibility:** costly — committed data vintages live in git history permanently; keep it small (CSVs only).
- **D-06:** Transfermarkt injury backfill depth: ALL training seasons 2016-17+ — the whole point of this source is reaching where FPL flags can't; fetcher runs as a background killable job (rate-limit-bound wall clock accepted). A/B on the full 6-season walk-forward.
- **D-07:** Transfermarkt storage: committed snapshot — the normalized injury-spell table (CSV/parquet + README with retrieval date), like the kiwi data; weeks of fetching must never need redoing. Raw page cache may stay uncommitted. — **Reversibility:** costly — same git-history permanence as D-05.
- **D-08:** Snapshot cron gap fix is IN SCOPE: anacron-style catch-up — on boot/first-run-of-day, if today's snapshot is missing, capture it (data/snapshot.py is already idempotent per UTC day). Context: only 2 of 10 days captured since 2026-08-31 (2026-08-31, 2026-09-07) because WSL cron doesn't fire when the machine is off.

### Adoption criteria (P(play) / partial-coverage experiments)
- **D-09:** FPL availability-flags experiment is judged on a DUAL criterion, both must hold: (a) covered-season (2025-26) walk-forward model+chips improves ≥ +25 points, AND (b) benchmark Spearman vs ep_next improves ≥ +0.03 over the 0.383 baseline. Transfermarkt (full coverage) keeps the standard 6-season protocol.
- **D-10:** D-07 auto-adopt stands for availability flags, but with a mandatory safe fallback: when no fresh pre-deadline snapshot exists, availability features go NaN and the prediction degrades to today's behavior — asserted by a test before the flag can flip.
- **D-11:** Final combined run (Phase 9 D-13 pattern) uses SPLIT VERDICTS: the combined 6-season run includes only full-coverage winners, judged on ≥2,280; availability flags carry their own dual-criterion verdict recorded separately in the ledger. No forced apples-to-oranges combination.

### Model-class bracket
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

### Folded Todos

All 8 pending todos fold into this phase (each is tagged `resolves_phase: 10` and enumerated in the ROADMAP phase description):
- **Availability flags into P(play)** (2026-09-10, major) — ranking gap is a minutes/availability problem; own snapshots + vendored 2025-26 backfill → Tier 1.
- **Transfermarkt injury history** (2026-09-10, major) — all-season backfillable P(play) signal → Tier 1.
- **Model-class bracket** (2026-09-10, minor) — LightGBM never challenged; six-family bracket → Tier 2, unconditional.
- **Guardian/GDELT news sentiment** (2026-09-10, minor) — conditional on D-02's trigger → Tier 2.
- **Top-100 consensus benchmark** (2026-09-10, minor) — scoreboard diagnostic → Tier 3, first.
- **fplreview scoreboard benchmark** (2026-09-10, minor) — manual-assisted weekly capture → Tier 3, first.
- **Manual FBref CSV snapshot** (2026-09-09, minor, deprioritized) — dead-tail, only with spare time + user willingness (D-04).
- **RL reward-shaping notes** (2026-09-09, minor) — notes-only IMPROVEMENTS.md addendum at the tail (D-04).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope (the todos ARE the spec)
- `.planning/todos/pending/2026-09-10-availability-flags-pplay.md` — Tier 1: own-snapshot columns to add, backfill source + leakage caveat, OpenFPL encoding to mine
- `.planning/todos/pending/2026-09-10-transfermarkt-injury-history.md` — Tier 1: fetcher conventions, features, leakage test requirement
- `.planning/todos/pending/2026-09-10-model-class-bracket.md` — Tier 2: candidate rationale, two-stage gate design
- `.planning/todos/pending/2026-09-10-news-sentiment-conditional.md` — Tier 2 conditional: GDELT/Guardian method, mlpremier repo to mine (arXiv 2405.02412)
- `.planning/todos/pending/2026-09-10-top100-consensus-benchmark.md` — Tier 3: FPL standings/entry endpoints, scoreboard column
- `.planning/todos/pending/2026-09-10-fplreview-scoreboard-benchmark.md` — Tier 3: manual capture, ToS constraints (diagnostic only, never a feature)
- `.planning/todos/pending/2026-09-09-manual-fbref-snapshot.md` — tail item: kiwi snapshot pattern, fbrapi.com re-probe option
- `.planning/todos/pending/2026-09-09-rl-reward-shaping-revisit.md` — tail item: the potential-based-shaping note to record (Ng et al. 1999)

### Prior ground truth & discipline
- `IMPROVEMENTS.md` (repo root) — Phase F ledger: every Phase 9/quick-task verdict with numbers (capt_ceiling +1.5 < +2 bar; chips_v2 −48; team_strength −2; understat +16 < bar; fotmob +1; rl v1–v3 rejections + compute curve; ep_next flag rejections); where every Phase 10 verdict gets recorded
- `.planning/phases/09-xp-model-optimizer-improvement-experiments/09-CONTEXT.md` — inherited decisions D-05..D-16 (bar, auto-adopt, dev-only lockfiles, polite fetchers, package gate, A/B protocol, replica policy)
- `.planning/research/XP-IMPROVEMENT-OPTIONS.md` — success-criteria set and leakage-risk notes Phase 9 adopted; still the criteria template
- `data/external/README.md` + `data/external/kiwi/` — the committed-snapshot pattern D-05/D-07 replicate

### Key code seams
- `config.py` — EXPERIMENTS flag registry (10 flags, all False) + per-source column declarations; new flags land here
- `data/snapshot.py` — `_ELEMENT_COLS` (already captures status, chance_of_playing_next_round, ep_this/ep_next); add news/news_added/chance_of_playing_this_round; per-day parquet under data/snapshots/
- `data/id_crosswalk.py` — 3-tier name→player_code resolution (87.4% coverage) for Transfermarkt/news-entity joins
- `data/fotmob.py` / `data/understat.py` — the polite-fetcher conventions (kill switch, on-disk cache, coverage print) Transfermarkt mirrors
- `backtest/walk_forward.py` — the sole judge; enrichment_preds_* artifact-scoring path is the template for Colab-produced prediction files
- `predict/scoreboard.py` — where both Tier-3 benchmark columns land
- `tests/test_leakage.py` — extended per D-21 and for Transfermarkt spell dates

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.EXPERIMENTS` dict + walk_forward's feature-selection gating: flipping a flag is never a pipeline rebuild — new experiments reuse this exactly.
- `data/snapshot.py` is idempotent per UTC day with `--backfill`-friendly structure; the anacron fix (D-08) is a wrapper/cron change, not new capture logic.
- Phase 9's `data/processed/experiments/` artifact conventions (tagged logs, benchmark_*.json, per-season preds parquets) — Colab outputs must match to be scoreable.
- `scipy.stats.spearmanr` benchmark scoring in predict/scoreboard.py and the EXP-1 benchmark files (benchmark_ep_next_*.json) — the Spearman-vs-ep_next measurement basis for D-02/D-09 already exists.
- theFPLkiwi vendored-snapshot precedent (README + attribution + retrieval date) for D-05/D-07.

### Established Patterns
- Leakage-safe shift(1)-then-roll in features/engineer.py; every new feature column gets a tests/test_leakage.py assertion.
- Rejected-with-numbers: code merged behind default-off flags, verdict in IMPROVEMENTS.md — every Phase 10 experiment ends this way or adopts.
- Blocking-human package-legitimacy gate at install time (Phases 1–9, zero drift record).
- Snapshot cron: WSL cron is the sole scheduler; machine-off days silently skip (the D-08 motivation).

### Integration Points
- `data/build_table.py` joins new sources into player_gw; `features/engineer.py` + `config.py` declare columns; `models/train.py` P(play) classifier consumes availability features.
- `predict/live.py` / `predict/export.py` — weekly product surface; untouched unless a flag flips default-on (then D-10's fallback test gates the flip).
- `scripts/daily.sh` / crontab — where the anacron-style catch-up lands.

</code_context>

<specifics>
## Specific Ideas

- Mine OpenFPL's availability-feature encoding (arXiv:2508.09992) before designing the P(play) features — it closed most of the ep_next gap with only categorical chance_of_playing flags.
- Transfermarkt endpoints: reimplement worldfootballR's documented endpoints in Python; do not depend on the R package.
- fplreview data is ToS-restricted: never redistributed, never a model input — scoreboard diagnostic only.
- The user wants the bracket structured around per-candidate Colab-vs-local time-benefit assessment, with candidates divided across both machines in parallel even at speed parity — total wall clock is the constraint being optimized.
- Sequence-model hypothesis is explicitly "can a network learn better temporal aggregation than our hand-rolled rolling windows" — hence raw per-GW inputs (D-20), not re-fed engineered features.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (The two lowest-priority items — FBref manual snapshot, RL shaping notes — stay in-phase at the tail per D-04 rather than deferring.)

</deferred>

---

*Phase: 10-xp-experiment-follow-ups*
*Context gathered: 2026-09-10*
