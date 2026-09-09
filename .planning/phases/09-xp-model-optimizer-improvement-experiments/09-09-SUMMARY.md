---
phase: 09-xp-model-optimizer-improvement-experiments
plan: 09
subsystem: ml-experimentation
tags: [fotmob, fbref, defensive-actions, endpoint-discovery, walk-forward, feature-gating, leakage, cloudflare]

requires:
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-01's experiment spine (config.EXPERIMENTS, backtest/walk_forward.py --experiments/--seasons/--tag CLI, the tracked 6-season baseline in IMPROVEMENTS.md Phase F)"
  - phase: 09-xp-model-optimizer-improvement-experiments
    provides: "plan 09-08's data.id_crosswalk.resolve_by_name (the shared player-identity crosswalk this plan resolves FotMob names through) and apply_experiment_feature_gating(df, exp), the named helper this plan extends with a third family"
provides:
  - "data/fotmob.py -- cached, rate-limited, kill-switchable FotMob fetcher (two reverse-engineered direct JSON endpoints, discovered and verified live this plan), producing data/processed/fotmob.parquet (146,924 rows, 2016-17..2026-27)"
  - "config.FOTMOB_COLS registered in features/engineer.py's ROLL_STATS (never CONTEXT_COLS) -- leakage-tested"
  - "backtest/walk_forward.py::apply_experiment_feature_gating extended with an fm_* branch"
  - "D-07 adoption verdict for fotmob: REJECTED (model+chips +1, within noise), flag off, code merged"
  - "FBref settled by a real Chrome spike: three independent attempts confirm the site is still fully Cloudflare-gated in this environment (a harder failure than the prior value-blanking finding) -- recorded not-acquirable with evidence, no host infrastructure built"
  - "IMPROVEMENTS.md Phase F's enrichment section fully closed -- understat/fotmob/fbref_v2 rows all carry a number or an evidenced reason, none left `pending`"
affects: [09-10]

actuals:
  tokens: 8427
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Endpoint discovery via live response inspection (no wrapper package, D-11): probe candidate URL shapes with real HTTP requests, confirm structure, then hardcode the verified paths with a comment recording the verification date"
    - "Label-based (not internal-key-based) stat extraction from a nested per-block payload: match by the human-readable label FotMob itself displays, more stable than an internal key that can carry an unrelated-looking raw string (e.g. an apparent leaked i18n key for one stat)"
    - "NaN-not-zero on missing per-stat-block data: a coverage percentage only remains meaningful as a break signal if a truly absent stat is NaN, never silently defaulted to 0"

key-files:
  created:
    - data/fotmob.py
  modified:
    - config.py
    - data/build_table.py
    - features/engineer.py
    - backtest/walk_forward.py
    - tests/test_leakage.py
    - IMPROVEMENTS.md

key-decisions:
  - "Matched FotMob stat blocks by their on-page display label (\"Tackles\", \"Interceptions\", ...) rather than the payload's internal `key` field, after observing one stat's internal key looked like a raw, apparently-unintended i18n string (\"matchstats.headers.tackles\") while every label was stable and human-verifiable across players and matches"
  - "Treated three independent real-Chrome FBref spike attempts (5-6 minutes each, all hanging inside the existing UC-mode reconnect call) as sufficient, well-evidenced confirmation that FBref remains inaccessible in this environment -- verified with two control checks (a normal site loads instantly in the same driver; a non-UC driver against the same FBref URL loads in under a second but returns Cloudflare's interstitial) rather than assuming a fourth attempt would behave differently"
  - "REJECTED fotmob at adoption: model+chips moved +1/season (2262->2263), indistinguishable from the harness's own ~50-point season-to-season standard error -- far short of the >=2280 bar and not treated as a genuine signal despite real, leakage-tested data reaching the model"

requirements-completed: []

coverage:
  - id: D1
    description: "FotMob's unofficial JSON endpoints discovered, verified live, and wrapped in a rate-limited, cached, kill-switchable fetcher with explicit response-shape validation"
    verification:
      - kind: other
        ref: "python -c module-surface check (Task 1 <verify>): FOTMOB_ENABLED, _MIN_INTERVAL_S+sleep, _ENDPOINTS, coverage print all present"
        status: pass
      - kind: unit
        ref: "kill-switch no-op assertion (FOTMOB_ENABLED=False -> attach() returns input unchanged, same columns)"
        status: pass
      - kind: integration
        ref: "python -m data.fotmob (146,924 rows across 11 seasons; cache-warm rerun touches zero network calls)"
        status: pass
    human_judgment: false
  - id: D2
    description: "FotMob defensive-action counts reach the model only through shift(1)-then-rolling windows, never as raw pre-match context; pipeline rebuild leaves player_gw.parquet row count unchanged"
    verification:
      - kind: unit
        ref: "tests/test_leakage.py#test_fotmob_features_are_rolled_not_raw"
        status: pass
      - kind: integration
        ref: "python -m data.build_table && python -m features.engineer (player_gw.parquet 253,509 rows unchanged; features.parquet gained 24 rolled fm_* columns at 40.4% coverage)"
        status: pass
    human_judgment: false
  - id: D3
    description: "apply_experiment_feature_gating(df, exp) extended with a third fm_* branch alongside ts_*/us_*, no new ad-hoc gating path"
    verification:
      - kind: integration
        ref: "full pytest suite green (215 passed, 1 skipped) after the extension; existing team_strength/understat gating behaviour unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "FotMob A/B measured on season points; D-07 adoption verdict recorded as REJECTED"
    verification:
      - kind: integration
        ref: "data/processed/experiments/wf_fotmob_adopt.json (6 seasons, 5 replicas, fotmob=true; model+chips 2263 vs baseline 2262)"
        status: pass
    human_judgment: true
    rationale: "The REJECT verdict rests on judging a +1 model+chips delta as within the harness's own noise band (SE~50) rather than a hard coded threshold -- the same judgment shape as this phase's other adoption verdicts (capt_ceiling, understat). A human should confirm this reasoning stands before treating the flag as permanently settled."
  - id: D5
    description: "FBref settled by a real Chrome spike: three independent attempts confirm the Cloudflare access block is still fully in effect (a harder failure than the prior documented value-blanking), with no new scraping-host infrastructure built"
    verification:
      - kind: other
        ref: "three real-Chrome spike attempts (data.fbref.scrape_to_cache(seasons=['2025-26']), 2026-09-08), each hanging 5-6 minutes inside driver.uc_open_with_reconnect(); control checks confirmed Chrome/network otherwise functional and a plain driver still receives Cloudflare's \"Just a moment...\" interstitial for the same URL"
        status: pass
    human_judgment: true
    rationale: "Concluding \"confirmed dead\" from a hang (rather than an explicit error or explicit empty result) is an environmental/reproducibility judgment, not a mechanically-checked assertion -- a human should sanity-check that three consistent hangs is sufficient evidence rather than, e.g., a transient network issue specific to this session."
  - id: D6
    description: "IMPROVEMENTS.md Phase F's enrichment section closed -- understat/fotmob/fbref_v2 rows all carry a number or an evidenced reason, none `pending`"
    verification:
      - kind: other
        ref: "python -c row-content check (Task 3 <verify>): no 'pending' in any of the three rows; fbref_v2's row carries qualifying evidence keywords; config.EXPERIMENTS retains exactly its 8 pre-declared keys"
        status: pass
    human_judgment: false

duration: 6h 29min
completed: 2026-09-09
status: complete
---

# Phase 9 Plan 9: FotMob Endpoint Discovery + FBref Access Spike Summary

**Reverse-engineered two live FotMob JSON endpoints, built a cached/rate-limited/kill-switchable fetcher, rolled 146,924 rows of per-match defensive-action data into the feature matrix behind a leakage test, REJECTED adoption after a +1/season move indistinguishable from noise, and settled FBref with three real-Chrome spike attempts that all confirm the Cloudflare block is still fully in effect — closing every enrichment row in Phase F's results table.**

## Performance

- **Duration:** 6h 29min (dominated by an ~85-minute unattended FotMob historical fetch — interrupted once mid-run by a session restart, resumed from its own on-disk cache in ~20 minutes — and three bounded, ultimately unsuccessful FBref Chrome spike attempts)
- **Started:** 2026-09-08T19:55:08Z (Task 1 commit)
- **Completed:** 2026-09-09T02:24:13Z (Task 3 commit)
- **Tasks:** 3
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- `data/fotmob.py` (new) — `FOTMOB_ENABLED` kill switch, `HEADERS`/`TIMEOUT`, `_MIN_INTERVAL_S = 1.5`, `_ENDPOINTS` (two reverse-engineered direct JSON paths verified live 2026-09-08: `GET /api/data/leagues?id=47&season={YYYY/YYYY}` for a season's fixture/match-id list, `GET /api/data/matchDetails?matchId={id}` for per-player match stats), `_require()` (explicit shape validation raising a named-key error rather than propagating a schema change as NaN), `build()`, `attach()`. Matches stat blocks by their **display label** ("Tackles", "Interceptions", "Blocks", "Clearances", "Recoveries", "Duels won") rather than FotMob's internal `key` field, after finding one internal key looked like a raw, unstable-seeming i18n string while every label was stable across players and matches. A missing label yields NaN, never a silently-wrong zero — the distinction the coverage-percentage print depends on to catch a future silent break (Pitfall 3). Full historical build: **146,924 player-match rows across 11 seasons** (2016-17 through the in-progress 2026-27), zero network calls on a cache-warm rerun.
- **Discovery was itself bounded and evidence-based**, per the plan's own instruction: live response inspection (not a wrapper package, D-11) found the endpoints moved from a guessed `/api/leagues` (404) to the real `/api/data/leagues` base; a coverage probe across all 6 walk-forward test seasons (2020-21..2025-26, 6 matches sampled each) found the needed stat labels present in every sample, while pre-2020 seasons frequently lack them (FotMob's own coverage tier drops from `xG` to `ratings`/`lower` — treated as ordinary missing data, not an error).
- `config.FOTMOB_COLS` (`fm_tackles`, `fm_interceptions`, `fm_blocks`, `fm_clearances`, `fm_recoveries`, `fm_duels_won`) registered in `features/engineer.py`'s `ROLL_STATS` (never `CONTEXT_COLS`) — every value reaches the model only through `_roll`'s `shift(1)`-then-rolling windows, since these describe the match they came from (a match outcome), matching plan 09-08's Understat precedent exactly. `tests/test_leakage.py::test_fotmob_features_are_rolled_not_raw` asserts no bare `fm_*` column survives in `features.parquet` and independently recomputes `fm_tackles_r5`. `data/build_table.py` gained a guarded fotmob join after the understat block, computed unconditionally. Rebuild: `player_gw.parquet` unchanged at **253,509 rows**; `features.parquet` gained 24 rolled `fm_*` columns at **40.4% row-level coverage** (via plan 09-08's shared `data.id_crosswalk` name resolver — no new crosswalk work needed).
- `backtest/walk_forward.py::apply_experiment_feature_gating(df, exp)` extended with a third `fm_*` branch alongside the existing `ts_*`/`us_*` families — no new ad-hoc gating path added, matching the plan's explicit instruction.
- **Adoption-deciding run** (6 seasons, 5 replicas) against the plan 09-01 baseline: `model+chips` 2262 → **2263** (**+1/season**, well inside the harness's own ~50-point season-to-season standard error). **D-07 verdict: REJECTED** — `config.EXPERIMENTS['fotmob']` stays `False`; all code stays merged (D-08).
- **FBref spiked three times with a real Chrome driver, all inconclusive in the same way.** Each attempt (`data.fbref.scrape_to_cache(seasons=['2025-26'])`, equivalent to `python -m data.fbref --scrape` restricted to one season, run 2026-09-08) hung indefinitely inside `driver.uc_open_with_reconnect()` for 5-6 minutes before being killed, never returning a page — 0 rows scraped in every attempt. Two control checks isolate the cause: (1) the same UC driver loaded a normal site (`example.com`) instantly, confirming Chrome and the network stack otherwise work fine in this session; (2) a **plain, non-UC** Chrome driver loaded the same FBref URL in under a second but received Cloudflare's own `"Just a moment..."` interstitial page (`challenges.cloudflare.com` script present) rather than the stats table — i.e. the site is still fully Cloudflare-gated, and the UC-mode bypass technique `data/fbref.py` relies on does not clear that challenge within a many-minutes window here. This is a **different, more severe** failure mode than the 2026-08-22 finding recorded in `IMPROVEMENTS.md` Phase E (which got PAST Cloudflare and received a real page with empty stat cells — value-blanking); today the access layer itself does not resolve. **Verdict: not acquirable this session.** `config.EXPERIMENTS['fbref_v2']` stays `False`; no new scraping-host infrastructure or scraper container image was built (D-04), matching Pitfall 1's explicit warning.
- **IMPROVEMENTS.md Phase F's enrichment section fully closed** — the `understat`/`fotmob`/`fbref_v2` rows in the results table and their own detailed subsections all carry a number or an evidenced reason; a closing prose summary ties the three sources together against plan 09-02's external-benchmark reading.

## Task Commits

Each task was committed atomically:

1. **Task 1: Discover FotMob's endpoints and build a polite, killable fetcher** - `5b001e3` (feat)
2. **Task 2: Join FotMob as rolled features and A/B it** - `c9b8abe` (feat)
3. **Task 3: Settle FBref with a real Chrome spike, and close every enrichment row** - `00f7fc1` (docs)

_No separate plan-metadata commit — this file plus STATE.md/ROADMAP.md are committed together as the close-out commit._

## Files Created/Modified

- `data/fotmob.py` (new) - `FOTMOB_ENABLED`, `_MIN_INTERVAL_S`, `_ENDPOINTS`, `_require()`, `_fetch()`, `build()`, `attach()`
- `config.py` - `FOTMOB_COLS`
- `data/build_table.py` - guarded fotmob join
- `features/engineer.py` - `FOTMOB_COLS` in `ROLL_STATS`
- `backtest/walk_forward.py` - `apply_experiment_feature_gating`'s third `fm_*` branch
- `tests/test_leakage.py` - `test_fotmob_features_are_rolled_not_raw`
- `IMPROVEMENTS.md` - `fotmob`/`fbref_v2` Phase F rows and detailed subsections filled (no pending cells), closing enrichment summary added

## Decisions Made

- Matched FotMob stat blocks by their on-page display label rather than the payload's internal `key` field, after observing one stat's internal key looked like a raw, unintended i18n string while every label was stable and human-verifiable across players and matches — labels are what the site itself shows, and are less likely to silently change without someone noticing.
- Treated three independent, consistent real-Chrome FBref hangs (with two isolating control checks) as sufficient evidence that the source is inaccessible this session, rather than continuing to retry — matching the plan's own cost-conscious framing (Pitfall 1: don't invest further in a source that may not deliver even if access were fixed).
- REJECTED `fotmob` at adoption: the +1 `model+chips` move is indistinguishable from the harness's own noise band, consistent with the pattern already seen for every other feature-accuracy experiment this phase (odds, understat, team_strength).

## Deviations from Plan

None — plan executed exactly as written. (See "Issues Encountered" below for an operational interruption during execution, not a deviation from the plan's own instructions.)

## Issues Encountered

- **Mid-plan session interruption during the FotMob historical fetch.** The orchestrating session was restarted partway through the ~85-minute unattended `python -m data.fotmob` background fetch (after 8 of 11 seasons had completed and their raw JSON payloads were cached to disk). On resume, the uncommitted Task 2 code diff was verified intact and correct against the plan's spec before proceeding; the fetch was relaunched via `setsid` (fully detached from the controlling session, unlike the original `nohup`+`disown`, which did not survive the interruption) and completed the remaining ~20 minutes of work by reusing the already-cached seasons from disk — no data was re-fetched unnecessarily, and no code was lost or needed to be redone.
- **The first two FBref spike attempts ran without unbuffered/granular logging**, so their eventual timeout/kill produced no diagnostic trail; the third attempt added print statements around each step (Chrome launch, navigation) which, combined with the two control checks (a normal site load, a plain-driver load of the same FBref URL), pinpointed the exact hang location and its cause (Cloudflare's challenge not resolving) rather than leaving it as an unexplained timeout.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Experiment 6 (D-01's enrichment-data option) is now fully closed for all three sources: Understat (REJECTED, +16/season), FotMob (REJECTED, +1/season), FBref (not acquirable, confirmed dead with evidence). No `pending` cell remains anywhere in Phase F.
- `data/fotmob.py`'s endpoint-discovery pattern (live response inspection, verified-date comments, label-based extraction) is available for any future FotMob work without repeating the discovery step.
- `predict/live.py` and `predict/export.py` remain untouched — the weekly product surface is unaffected, matching this plan's own success criteria.
- Plan 09-10 (the final combined run per D-13) has all three enrichment verdicts available to fold into its cross-experiment reading; none of the three flags need to be included since all stayed default-off.
- No blockers.

---
*Phase: 09-xp-model-optimizer-improvement-experiments*
*Completed: 2026-09-09*

## Self-Check: PASSED

All key files (data/fotmob.py, config.py, data/build_table.py, features/engineer.py,
backtest/walk_forward.py, tests/test_leakage.py, IMPROVEMENTS.md) exist on disk; all
three task commits (5b001e3, c9b8abe, 00f7fc1) found in `git log`; full pytest suite
(215 passed, 1 skipped) and `ruff check .` both green; `data/processed/fotmob.parquet`
(146,924 rows) and `data/processed/experiments/wf_fotmob_fast.json`/`wf_fotmob_adopt.json`
all present with the expected shape; `player_gw.parquet` confirmed at 253,509 rows,
matching the pre-plan baseline.
