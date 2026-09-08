# xP Improvement Options — Open-Source FPL Ecosystem Survey

**Researched:** 2026-09-08
**Researcher:** Claude (web survey + repo ground-truth audit)
**Ground truth audited:** `PLAN.md` (Refinements + External data sections), `IMPROVEMENTS.md` (Phases A–E), `backtest/walk_forward.py`, `optimize/multi_period.py`, `backtest/multi_period_season.py`, `models/train.py`
**Confidence:** MEDIUM-HIGH on ecosystem facts (cited), LOW on gain estimates (explicitly marked speculative — one honest season backtest has ±50–100 pts of path-dependence noise, per our own Phase 5/6 findings)

**Sources consulted:**

- vaastav dataset + tagged projects: <https://github.com/vaastav/Fantasy-Premier-League>
- sertalpbilal solver: <https://github.com/sertalpbilal/FPL-Optimization-Tools> (now redirects development to solioanalytics/open-fpl-solver; HiGHS-based multi-period MILP)
- Hindsight optimum: <https://alpscode.com/blog/hindsight-optimization/> + <https://github.com/sertalpbilal/fpl_hindsight_optimization>
- AIrsenal: <https://github.com/alan-turing-institute/AIrsenal> + <https://www.turing.ac.uk/news/airsenal> (Dixon-Coles Bayesian team model + player goal-involvement model)
- OpenFPL paper: <https://arxiv.org/abs/2508.09992> + <https://github.com/daniegr/OpenFPL>
- FPL Review methodology: <https://docs.fplreview.com/the-model/projections/massive-data-model/>, <https://docs.fplreview.com/articles/ultimate-truth/>, <https://fplreview.com/a-goalscoring-model-more-predictive-than-inferrences-from-bookmakers/>
- theFPLkiwi projections + ID maps: <https://github.com/theFPLkiwi/theFPLkiwi>
- Solver-in-the-wild live track record: <https://fpl.hashnode.dev/fpl-solver>
- High-claim backtests examined: <https://github.com/JoshuaPlacidi/Fantasy-Football-Team-Predictions>, <https://github.com/saheedniyi02/fpl-ai>, <https://github.com/solpaul/fpl-prediction>, <https://rittim.com/projects/ai-fpl-manager>, <https://arxiv.org/abs/2505.02170>
- FPL record totals context: goal.com ("how many points do you need to win FPL")

---

## Reality check: the 2,900-point claim

**We could not find a specific public project claiming a ~2,900 pts/season *average*.** We searched GitHub, arXiv, Medium, Reddit, and the vaastav tagged-projects list directly. What we did find, and what it implies:

**The arithmetic makes a 2,900 average essentially impossible for an honest system.**

- The highest points total *ever recorded by any human in FPL history* is **2,844** (2021/22) — most season winners land ~2,500–2,700 (goal.com). A system *averaging* 2,900 would beat every FPL champion ever, every season. No live-verified system does this.
- The theoretical perfect-hindsight ceiling (know every score in advance, unlimited −4 hits) is **4,984 for 2019-20** — but that took 145 transfer hits and 4 days of SAS MILP solve time (alpscode.com/blog/hindsight-optimization). With realistic transfer behavior the hindsight optimum is far lower; 2,900 sits in the band reachable only with *partial future knowledge*.
- FPL Review's "Ultimate Truth" analysis (docs.fplreview.com/articles/ultimate-truth) shows even a *perfect* probabilistic model has player-GW RMSE ~2.7–2.9 — real models (theirs included, RMSE 2.803) are within ~3% of the perfect model's error. The accuracy headroom is small; nobody's model is secretly 30% better.

**How ~2,900 claims are produced** (mechanisms we verified in the surveyed projects):

1. **In-sample / same-season evaluation.** JoshuaPlacidi/Fantasy-Football-Team-Predictions reports 1,518 pts over GW4–29 of 2019/20 (≈2,220 pace) from a *linear regression* — evaluated on a season the rolling-window pipeline had exposure to. Honest for what it is, but the genre routinely tests on data the model saw.
2. **Rolling features computed over the full season then split** — the same leakage class we caught ourselves: our optimistic multi-GW backtest showed **+337/season, of which 88% was leakage; the honest number was +40** (`PLAN.md` Refinements). Any repo that doesn't explicitly freeze form at decision time should be assumed leaky.
3. **Hindsight EV scoring** — scoring the recommended team on *realized* points with knowledge of who blanked (autosubs/captains resolved favorably), or hand-picking the best of several simulated seasons.
4. **Single lucky season presented as typical.** Our own Phase 5 finding: one season swings ±50–100 pts on path-dependence alone.

**Best *verified* public performances for calibration:**

- fpl.hashnode.dev MILP solver: **98.8th percentile live** by GW29 of one season (~2,400–2,500-pt pace territory) — the author explicitly avoids over-claiming from one season.
- OpenFPL (arXiv 2508.09992): the only *prospectively evaluated* open model — accuracy comparable to FPL Review on 2024-25, no season-points claim at all (accuracy ≠ decisions).
- AIrsenal runs live every season; no elite-finish claims.

**Bottom line:** our leakage-safe 2,105–2,128 core (+chips ≈ 2,256) is *not* embarrassingly behind the field — it is in the honest range. The realistic frontier for a fully-automated system is roughly 2,300–2,500/season (top-50k → top-5k territory depending on year); claims above ~2,700 average should be presumed leaky until proven live. *(The 2,300–2,500 frontier estimate is speculative, triangulated from the hashnode live result and elite human totals.)*

**Ecosystem risk note (verified):** the vaastav dataset **stopped weekly updates after 2024-25** — only 3 updates/season now (season start, post-January, season end). Our pipeline already leans on the live FPL API + `data/live_history.py` for the current season, but any future re-ingest of "historical" current-season data must not assume vaastav freshness.

### Post-publication audit: the specific project found (ADnocap/FPL-RL)

The user later identified the ~2,900 project: **github.com/ADnocap/FPL-RL** (MaskablePPO chip/transfer-count strategy over a PuLP/CBC MILP selector, LightGBM 86-feature xP model, vaastav+Understat+FBref+FotMob+odds data). Its README claims **2,918 pts on a "2024-25 holdout season"** at 1 transfer/GW (3,171 at 5/GW; oracle 3,713), plus "0.787 per-GW correlation with actuals". Audit verdict (from the repo's own code, fetched 2026-09-08):

- **The 2,918 is in-sample — mechanism 1 above, confirmed.** `scripts/oracle_comparison.py` feeds the optimizer genuine LightGBM *predictions* (not oracle points), loaded from `models/point_predictor` — the "model of record". But `scripts/train_predictor.py` shows **every configuration trains on 2024-25**: the EVAL model trains 2016-17→2024-25 (validation = last 8 GWs *of 2024-25*), and the PROD "model of record" trains on all 10 seasons through 2025-26. The replayed season is inside the training window either way; the only genuinely held-out season (2025-26) has no published headline number.
- **The honest-looking parts corroborate this reading:** its no-transfer GW1-squad baseline scores 1,950 — consistent with our honest range — and the implausible **+968 from a single transfer/GW** is precisely the in-sample signature (cf. our own +337 optimistic → +40 honest multi-GW finding).
- **The 0.787 correlation is Pearson over all players with recorded targets per GW** (`np.corrcoef` on non-NaN rows, per-GW `g["pred"].corr(g["target"])`), so the predictable mass of zero-minute players inflates it; it is not comparable to rank metrics among starters.
- Repo maturity: 1 star, 41 commits, no published live results ("now running live for the 2026-27 season" — unverified).

**Salvageable ideas from FPL-RL** (independent of its headline number): the hybrid architecture — RL for *strategy* (chip timing, transfer count) atop a MILP for *selection* — is a legitimate framing of our Option 3 (solver-scored chip scheduler); its FotMob per-match defensive stats are a fourth enrichment source we had not catalogued (same caveat as FBref: name→FPL mapping). Neither changes the ranked options below.

---

## Ranked options table

Ranked by expected-honest-gain ÷ effort, *after* excluding everything already TESTED/REJECTED in `PLAN.md`/`IMPROVEMENTS.md` (ranking loss −55, clean-sheet sub-model −50, 3-state minutes model no-better, true multi-period MILP tie-with-9-hits, FBref blocked at source).

| # | Option | Used by | Expected honest gain | Effort | Leakage risk | Conflicts with prior tests? |
|---|--------|---------|---------------------|--------|--------------|------------------------------|
| 1 | Captaincy/TC ceiling EV (variance-aware armband) | FPL Review sims; our own gap analysis | +15–40/season (speculative; gap is measured at ~4.8/GW) | S–M | Low | No — extends adopted captain-by-mean; MC layer is an open TODO |
| 2 | Team-strength Poisson/Dixon-Coles priors as *features* | AIrsenal, FPL Review, OpenFPL | +0–25/season (speculative; fills real input gaps) | M | Medium (fit strictly pre-GW) | Must be features, NOT a sub-model (CS sub-model REJECTED) |
| 3 | Chip scheduler v2: solver-scored causal timing | sertalpbilal tools, fpl.hashnode.dev | +10–30/season (bounded by isolated chip values 10–20 each; WC timing known-weak) | M | Medium (must stay causal, B3-style) | No — heuristic scheduler is the named anti-pattern |
| 4 | Earlier/richer availability inputs (xMins *inputs*, not model class) | FPL Review, theFPLkiwi | live-only quality; backtest-invisible (speculative) | M | Low | Complements REJECTED 3-state finding: info was the bottleneck, not model class |
| 5 | Understat npxG/xGChain/deep-completion features | OpenFPL (rivals FPL Review on FPL+Understat only) | +0–15/season (speculative; ICT/odds overlap) | M | Low (existing shift(1) pattern) | Listed low-priority in IMPROVEMENTS Phase E — OpenFPL evidence upgrades it slightly |
| 6 | External-projection benchmark + optional blend | theFPLkiwi (historical projections in repo), OpenFPL weights | +0–10/season; main value is calibration/benchmarking | S | Low | No |
| 7 | Effective-ownership / differential modeling | FPL Review rank sims | ~0 for points-max product | M–L | Low | Deferred in IMPROVEMENTS ("EO/variance for RANK play") — skip for now |

S = days, M = ~1–2 weeks part-time, L = multi-week.

---

## Option details

### 1. Captaincy/TC ceiling EV — variance-aware armband and Triple Captain

**What it is.** Pick the captain (and the TC week) by expected *doubled* value including upside, not just mean xP: either (a) quantile-based — score candidates by `xp_mean + λ·(p90 − xp_med)` using the existing intervals artifact, or (b) a small Monte-Carlo layer — sample per-player point distributions (haul probabilities), simulate the armband, pick max-EV with a variance knob. TC timing then falls out as "the GW where the best captain's distribution is fattest" instead of the current DGW-or-best-captain fallback.

**Who uses it.** FPL Review's Massive Data model explicitly weights every scoring event by probability and exposes EV + simulation tooling (docs.fplreview.com massive-data-model); their planner community treats captaincy as a distribution problem. Our own `IMPROVEMENTS.md` Phase C measured the gap: **captaincy hit-rate 18%, capture 57%, ~4.8 pts/GW gap — "the biggest single-decision gap"** — and captain-by-mean recovered only +16/season of it.

**Expected honest gain.** Speculative. The theoretical pool is ~180/season (4.8 × 38), but most is irreducible variance. Captain-by-mean's +16 suggests each further refinement claws small amounts; +15–40/season is a hopeful-but-plausible band. Judge on captaincy *capture %* as a lower-noise intermediate metric, season points as the final judge.

**Implementation.** `models/intervals.py` (already fits p10/p90 per position×xp-bucket) → thread a `xp_capt_ceiling` column through `models/train.py`/`predict_xp`, `optimize/squad_ilp.py` + `optimize/transfers.py` (captain objective already parameterized via `capt_col`), `optimize/chips.py` (TC trigger), `backtest/season.py` + `backtest/walk_forward.py` (A/B config). The MC variant adds a new small module (e.g. `models/simulate.py`).

**Leakage risk.** Low — intervals are fit on held-out residuals from prior seasons; nothing new peeks.

**Conflicts.** None. Extends the ADOPTED captain-by-mean; the Monte-Carlo layer is an explicit open TODO in IMPROVEMENTS Phase C. Do NOT re-derive it as a component/decomposed points model (that pattern lost twice: CS sub-model −50, ranking loss −55).

### 2. Team-strength ratings (Poisson / Dixon-Coles) as features

**What it is.** Fit a lightweight team attack/defence strength model (Dixon-Coles 1997 bivariate Poisson, or plain Poisson GLM, or even Elo) on match results strictly *before* each GW, and emit per-fixture features: expected goals for/against, P(clean sheet), P(win). AIrsenal's entire team layer is exactly this — "every team has two latent abilities, α attack and β defence, plus home advantage γ" (Turing/AIrsenal README).

**Why it adds anything given odds are DONE.** Our odds features (KEPT — top-3 for DEF conditional points) have two verified holes: (a) **2016-19 training seasons have NaN odds** (`PLAN.md`: "2016-19 lack `team` so NaN there — training only"), and (b) **future GWs in the multi-GW horizon have no posted odds** — `xp_plan`/horizon pools graft only `FIXTURE_CTX` (fdr, home, dgw, rest; `backtest/walk_forward.py`), so the planner sees FDR but not a calibrated strength signal for weeks t+2..t+H. A DC model computed from results-to-date fills both, and updates mid-season as teams change (FDR is static-ish).

**Who uses it.** AIrsenal (Bayesian DC via bpl), FPL Review ("team strength & style" is a named model input), OpenFPL (team-form features).

**Expected honest gain.** +0–25/season, speculative. Odds already cover the next-GW case well, so the marginal value is concentrated in horizon planning and old-season training rows. Note our own precedent: odds improved fixture MAE to a best-ever 0.871 yet moved season points *within noise* — expect the same shape here; judge on horizon Spearman (`backtest/horizons.py`) + DEF/GK MAE, with season points as a guard, not the sole judge.

**Implementation.** New `data/team_strength.py` (fit per season, expanding, per GW — cache a parquet of per-(season,gw,team) ratings), join in `data/build_table.py`, feature columns in `features/engineer.py` + `config.py`, and graft the *future-fixture* ratings into horizon pools in `backtest/walk_forward.py::_plan_col`/`leakage_safe_plan` and `predict/live.py --horizon`. scipy is already a dependency; no new packages needed for a Poisson GLM.

**Leakage risk.** MEDIUM — the classic mistake is fitting ratings on the full season. Ratings for GW g must use matches < g only (same expanding discipline as everything else); add a test in `tests/test_leakage.py`.

**Conflicts.** Yes, one sharp edge: the clean-sheet **sub-model** was TESTED, REJECTED (−50/season). This option must feed ratings as *input features to the existing L1 regressor*, never as a P(CS)×4 decomposition. Framed that way, it's the same pattern as the adopted odds columns.

### 3. Chip scheduler v2 — solver-scored, causal

**What it is.** Replace the fixture-structure heuristic (`optimize/chips.py`: BB→biggest DGW, TC→DGW fallback, FH→biggest BGW, WC→fixed slot) with an xP-scored decision: at each GW, for each unused chip, evaluate "use now vs. best visible later window" using the horizon xP machinery (frozen form + known future fixtures — the same causal construction as `leakage_safe_plan`), and fire when now ≥ best-later minus a hysteresis margin. WC timing specifically: score a hypothetical re-pick at each candidate GW over the following ~4 GWs of xp_plan.

**Who uses it.** sertalpbilal's tools embed chips directly in the MILP with allowed-chip-GW settings; the fpl.hashnode.dev solver author reports solver-found chip sequences worth **"30+ more expected points"** than community-consensus timing, live at the 98.8th percentile. Our own `PLAN.md` names the weakness: "WC fixed-slot timing is weak"; TC times well.

**Expected honest gain.** +10–30/season, semi-grounded: our isolated chip values are FH +19.9±11.8, BB +12.4±7.6, TC +10.0±8.3 — better timing can only harvest a fraction of these plus the WC upside; the hashnode 30+ figure is expected-points, not realized. The **isolated-chip harness in `backtest/walk_forward.py` is the perfect judge** — same team with/without chip, noise-controlled.

**Implementation.** `optimize/chips.py` (rewrite decision rule), reuse `backtest/walk_forward.py` horizon pools, `backtest/season.py` (chip application unchanged), `predict/live.py` (chip note). Careful to keep the B3 fix: decisions at GW g see fixture structure only within g..g+K.

**Leakage risk.** MEDIUM — scoring candidate chip windows must use frozen-form horizon xP, not realized points or future-fitted predictions. The B3 causal-scheduler fix is precedent for how this goes wrong.

**Conflicts.** None; the heuristic scheduler is the codebase's own named anti-pattern. It does NOT require re-adopting the multi-period MILP (which tied) — scenario scoring over the existing myopic pipeline is enough.

### 4. Availability inputs — earlier/richer team news (xMins *inputs*)

**What it is.** Improve *what the minutes stage sees*, not its architecture: press-conference/injury news earlier than the FPL API's `chance_of_playing` (which often updates late), predicted-lineup signals, manager rotation patterns, days-since-return-from-injury, cup-fixture congestion. The 3-state model rejection (`IMPROVEMENTS.md`: MAE 0.874 vs 0.871, "the regressor already absorbs cameo/start via minutes-form features") is evidence the bottleneck is information, not model class.

**Who uses it.** FPL Review's model is fed "temporary factors like penalty takers/rotation" and data recency (docs); theFPLkiwi's projections revolve around expected minutes (their README: even "the probability of the 3rd sub coming on" matters). Every commercial EV service treats xMins as the #1 lever. *(That xMins is the top lever is community consensus; no controlled public measurement exists — speculative.)*

**Expected honest gain.** Honest answer: **unmeasurable in our backtest** — historical press-conference data isn't in vaastav, so the walk-forward can't score it. This is a *live-quality* investment (our live path already applies `chance_of_playing`; earlier news mainly wins the 24–48h before deadline). Free structured sources are scarce; scraping news sites adds fragility. Rank it by product value (user trust at the deadline), not backtest points.

**Implementation.** `predict/live.py` (availability override hook already exists via flags), possibly a small `data/news.py` feed adapter; zero changes to training. Listed as open TODO in IMPROVEMENTS Phase E ("Injury/press-conference feed earlier than chance_of_playing").

**Leakage risk.** Low (live-only).

**Conflicts.** None, but respect the 3-state rejection: don't rebuild the model class, feed the existing one better.

### 5. Understat npxG / xGChain / deep-involvement features

**What it is.** Join Understat shot-level aggregates (npxG, xGChain, xGBuildup) per player-match, roll them with the existing leakage-safe windows. We already carry FPL-API xG/xA (`features/engineer.py` rolls `xg`, `xa`, `xgi`, `xgc`); Understat adds non-penalty separation and *involvement-in-move* chain metrics FPL's feed lacks.

**Who uses it.** **OpenFPL is the headline evidence**: position-specific ensembles trained on *only* FPL + Understat data (2020-21→2023-24), prospectively matching FPL Review's accuracy on 2024-25 and beating it on high-return (>2 pt) players (arXiv 2508.09992). AIrsenal and most serious repos in the vaastav tagged list also consume Understat or FPL xG.

**Expected honest gain.** +0–15/season, speculative — our precedent (odds, set-piece) is that better fixture MAE ≠ resolvable season points; and ICT/odds already overlap heavily with xG signal. IMPROVEMENTS Phase E already marks this "low priority; FPL xG covers most" — the OpenFPL result is the reason to keep it on the list at all, since it bounds what FPL+Understat *can* achieve.

**Implementation.** `data/ingest.py` (understatapi is already a dependency), name→FPL ID mapping — **shortcut: theFPLkiwi's repo ships ready-made FPL↔fbref↔FFScout ID maps** (github.com/theFPLkiwi/theFPLkiwi), plus `data/build_table.py` join and `features/engineer.py` columns. The FBref hardening lessons (season-lagged join, primary-stint dedupe, row-count asserts in `data/fbref.py`) transfer directly.

**Leakage risk.** Low-medium — same-match join must follow the existing shift(1) discipline; the FBref same-season-aggregate leak already bitten-and-fixed is the template for what to avoid.

**Conflicts.** None (FBref is blocked at source; Understat is a different, working source).

### 6. External-projection benchmark (and optional blend)

**What it is.** Score our xP against a public projection set on identical player-GWs — theFPLkiwi's repo contains historical season projections (`Old_Seasons/`), OpenFPL publishes models + inference code for reproducible forecasts. Then optionally blend (simple convex weight tuned on validation season). Also: FPL's own `ep_next` is already in our feature set, but not as a benchmark.

**Who uses it.** OpenFPL's whole paper is this benchmark exercise; FPL Review's Ultimate Truth compares 6 models on common predictions.

**Expected honest gain.** +0–10/season from blending (speculative; blends of decorrelated models usually help accuracy a little). The real value is **calibration of our roadmap**: if our MAE/Spearman already matches kiwi/OpenFPL on common rows, the model is not the constraint and effort should go to decisions (options 1/3); if it doesn't, feature work (options 2/5) gets promoted. Cheap, high-information.

**Implementation.** A standalone `backtest/benchmark_external.py` (new, small): load kiwi CSVs / run OpenFPL inference, align IDs via kiwi maps, report MAE/Spearman side-by-side on played-only rows (per the B8 fix). No pipeline changes.

**Leakage risk.** None (evaluation only). For *blending*, ensure the external projections were genuinely pre-deadline vintages (kiwi's historical files are as-published; OpenFPL inference on our features is fine).

**Conflicts.** None.

### 7. Effective-ownership / differential modeling — SKIP for now

**What it is.** Model EO and pick differentials to maximize *rank* rather than points (variance-seeking when behind). Used by FPL Review's rank sims and most elite human strategy.

**Why skip.** Our product contract is best-expected-points recommendations; rank-vs-field optimization changes the objective and needs an ownership forecast model. IMPROVEMENTS already defers it ("EO/variance-aware differentials for RANK play"). Revisit at monetization if users ask for mini-league mode. Effort M–L for ~0 points-EV gain.

---

## Recommended phase scope

A single GSD research/experiment phase — "xP decision-layer upgrades" — bundling the options that (a) don't conflict with prior rejections, (b) are judged by the existing harness, and (c) attack the two *measured* gaps (captaincy 4.8/GW; WC timing weak):

1. **External benchmark first (option 6)** — half a day; decides whether model-accuracy work (2, 5) even matters this phase.
2. **Captaincy ceiling EV (option 1)** — quantile variant first (intervals already exist), MC variant only if quantiles move captaincy capture ≥ +2 pts.
3. **Chip scheduler v2 (option 3)** — WC timing is the known-weak slot; judge with the isolated-chip harness.
4. **Team-strength features (option 2)** — feature-only DC/Poisson ratings, prioritized for horizon pools and pre-2019 training rows; drop the sub-phase if the option-6 benchmark shows accuracy parity with OpenFPL/kiwi.
5. *(stretch)* **Understat npxG join (option 5)** — only if the kiwi ID-map shortcut proves clean in a spike.

**Success criteria (all judged by `backtest/walk_forward.py`, 6 test seasons, replicas on):**

- Primary: mean core+chips season points ≥ **2,280** (current ≈2,256) across the 6-season average — i.e. ≥ +25/season aggregate, outside the SE-31 band direction.
- Captaincy: capture % (armband points ÷ best-possible armband) improves ≥ +2 pts absolute over captain-by-mean, averaged over seasons.
- Chips: isolated WC value measured (currently unmeasured) and no chip's isolated value regresses; FH/BB/TC stay within their CIs.
- No leakage regressions: `tests/test_leakage.py` extended for team-strength ratings (ratings at GW g must reproduce from matches < g only); optimistic-vs-frozen A/B run for any horizon-touching change (the +337-vs-+40 discipline).
- Every experiment lands opt-in behind a flag with default unchanged until the walk-forward average clears its criterion (the established pattern: ranking loss, CS model, 3-state, MILP all stayed opt-in).

**Explicitly out of scope:** re-testing ranking loss, clean-sheet decomposition, 3-state minutes, always-on multi-period MILP (all REJECTED with numbers); FBref (blocked at source); EO/rank modeling (deferred); anything claiming to close the gap to 2,900 — that number is not real.
