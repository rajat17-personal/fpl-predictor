---
status: complete
phase: 10-xp-experiment-follow-ups
source: [10-01-SUMMARY.md, 10-02-SUMMARY.md, 10-03-SUMMARY.md, 10-04-SUMMARY.md, 10-05-SUMMARY.md, 10-06-SUMMARY.md, 10-07-SUMMARY.md, 10-08-SUMMARY.md, 10-09-SUMMARY.md, 10-10-SUMMARY.md, 10-11-SUMMARY.md, 10-12-SUMMARY.md, 10-13-SUMMARY.md, 10-14-SUMMARY.md, 10-15-SUMMARY.md, 10-16-SUMMARY.md]
started: 2026-09-12T09:47:00Z
updated: 2026-09-12T09:51:24Z
---

## Current Test

[testing complete]

## Tests

### 1. Cron install confirmation (daily + @reboot catchup)
expected: Run `crontab -l` on this WSL machine. Both lines are present and correct: the 02:30 UTC daily line invoking scripts/daily.sh and the @reboot line invoking scripts/snapshot_catchup.sh. (Recorded verbatim in 10-03-SUMMARY.md when you installed them — confirm they are still installed and unmodified.)
result: pass
source: 10-03-SUMMARY.md D2 (human_judgment)

### 2. Transfermarkt backfill go/no-go decision (10-05 Task 3)
expected: The go/no-go decision on plan 10-07 Transfermarkt backfill scope: you answered "A" (full backfill) against the measured probe evidence and wall-clock projection recorded in 10-05-SUMMARY.md. Confirm this decision still stands and the recorded evidence matches what you saw.
result: pass
source: 10-05-SUMMARY.md D3 (human_judgment)

### 3. FPL-Core-Insights license posture decision (D-05 gate)
expected: The FPL-Core-Insights license posture decision (D-05 costly-reversibility gate): LICENSE/LICENSE.md 404, GitHub API license field null, README Using-The-Data clause quoted verbatim, main SHA pinned, and your decision "A" recorded BEFORE any data was committed. Confirm the recorded posture matches your intent (vendored CSVs stay in-repo under that reading).
result: pass
source: 10-06-SUMMARY.md D1 (validation_failed)

### 4. FBref tail-item closure decisions (IMPROVEMENTS.md)
expected: The FBref tail item: two human decisions recorded verbatim in IMPROVEMENTS.md — Task 1 answer "A" against the confirmed access reality and measured FotMob prior, then decision "C" closing it against the acquisition-format defect (Tkl+Int/Blocks/Clr columns 0/5454 populated). Confirm both recorded decisions and their reasoning reflect what you decided.
result: pass
source: 10-15-SUMMARY.md D1 (validation_failed)

### 5. [auto] 10-01 D1
expected: data/availability.py end-to-end: provider registry, gw_deadlines, resolve_as_of's two-boundary as-of-deadline selection, build/attach, wired through data/build_table.py -> features/engineer.py -> backtest/walk_forward.py's gate
result: pass
source: automated
coverage_id: D1 (10-01-SUMMARY.md)
verified_by: python -m data.availability --force (real GW1-3 FPL-Core-Insights probe data); python -m data.build_table (no [availability] skipped); python -m features.engineer (av_chance_pct present, no rolled variant); backtest/walk_forward.py --tag t1_av_off / t1_av_on -- opposite availability_flags states recorded, both produce a model+chips integer

### 6. [auto] 10-01 D2
expected: As-of-deadline leakage rule, D-10 NaN fallback, raw-not-rolled family classification, and the 11-key default-off flag registry, each locked by a named passing test
result: pass
source: automated
coverage_id: D2 (10-01-SUMMARY.md)
verified_by: tests/test_availability.py::test_every_source_row_predates_its_gw_deadline; tests/test_availability.py::test_missing_snapshot_degrades_to_nan_not_raise; tests/test_leakage.py::test_availability_features_are_raw_context_not_rolled; tests/test_experiments.py::test_experiments_registry_default_off

### 7. [auto] 10-01 D3
expected: data/snapshot.py captures chance_of_playing_this_round, news, news_added from today onward
result: pass
source: automated
coverage_id: D3 (10-01-SUMMARY.md)
verified_by: tests/test_availability.py::test_snapshot_frame_carries_new_availability_columns; tests/test_availability.py::test_take_snapshot_persists_new_columns_end_to_end

### 8. [auto] 10-01 D4
expected: Every Phase 10 adoption criterion, including D-02's exact Spearman trigger, written to IMPROVEMENTS.md before any adoption-deciding run
result: pass
source: automated
coverage_id: D4 (10-01-SUMMARY.md)
verified_by: grep -c 'Phase G' IMPROVEMENTS.md; token-presence + pending-count script (see plan 10-01 Task 3 verify block)

### 9. [auto] 10-02 D1
expected: Top-100 overall-league consensus ownership fetcher (data/fpl_standings.py) -- paginated FPL standings fetch, per-manager picks fetch with graceful 404 degradation, aggregation to player_id owner counts with zero manager identity persisted
result: pass
source: automated
coverage_id: D1 (10-02-SUMMARY.md)
verified_by: tests/test_scoreboard.py::test_consensus_ownership_counts_distinct_owners_never_double_counting -- pass; tests/test_scoreboard.py::test_fetch_standings_stops_on_empty_page -- pass; tests/test_scoreboard.py::test_fetch_entry_picks_one_unavailable_manager_does_not_kill_the_others -- pass; tests/test_scoreboard.py::test_build_writes_parquet_and_load_consensus_returns_it -- pass; python -m data.fpl_standings --gw 1 --force (real live FPL API run, 103s wall clock, 103 requests)

### 10. [auto] 10-02 D2
expected: fplreview manual-capture slot: validating CSV reader (data/fplreview.py) with zero HTTP-client imports (the code-level ToS mitigation), and a six-section committed README documenting the weekly manual workflow
result: pass
source: automated
coverage_id: D2 (10-02-SUMMARY.md)
verified_by: tests/test_scoreboard.py::test_validate_raises_naming_all_missing_columns_at_once -- pass; tests/test_scoreboard.py::test_validate_raises_when_proj_pts_entirely_non_numeric -- pass; tests/test_scoreboard.py::test_load_gw_resolves_names_and_drops_unresolved -- pass; tests/test_scoreboard.py::test_load_gw_duplicate_player_names_raises -- pass; grep -cE http-client-import data/fplreview.py == 0

### 11. [auto] 10-02 D3
expected: Both benchmarks scored in predict/scoreboard.py::score_gw/running_summary as independently-optional additive blocks; both-absent entry is byte-identical to today's key set
result: pass
source: automated
coverage_id: D3 (10-02-SUMMARY.md)
verified_by: tests/test_scoreboard.py::test_score_gw_both_absent_reproduces_todays_key_set -- pass; tests/test_scoreboard.py::test_score_gw_adds_consensus_keys_when_present -- pass; tests/test_scoreboard.py::test_score_gw_adds_fplreview_keys_on_played_rows_only -- pass; tests/test_scoreboard.py::test_running_summary_averages_each_new_key_only_over_carrying_entries -- pass; tests/test_scoreboard.py::test_rescore_with_force_gains_new_keys_without_losing_existing -- pass; tests/test_product.py -- pass (export-contract regression, product surface untouched)

### 12. [auto] 10-03 D1
expected: scripts/snapshot_catchup.sh captures today's snapshot when missing, is a no-op when present, and prints its own crontab lines via --print-cron
result: pass
source: automated
coverage_id: D1 (10-03-SUMMARY.md)
verified_by: tests/test_cron.py#test_catchup_script_is_syntactically_valid; tests/test_cron.py#test_catchup_reports_missing_days_without_capturing; tests/test_cron.py#test_catchup_is_a_noop_when_today_exists

### 13. [auto] 10-03 D3
expected: daily.sh's data.snapshot-gap-report step reports the archive gap into data/cron.log on every daily run
result: pass
source: automated
coverage_id: D3 (10-03-SUMMARY.md)
verified_by: tests/test_cron.py#test_daily_sh_gap_report_step_runs_after_snapshot_before_price_train

### 14. [auto] 10-04 D1
expected: "config.AVAILABILITY_COLS grown to the full eight-column
result: pass
source: automated
coverage_id: D1 (10-04-SUMMARY.md)
verified_by: python -m data.availability --force (real 2025-26 GW1-3 fpl_core_insights probe); python -m data.build_table && python -m features.engineer (all 8 av_ columns reach features.parquet raw, zero rolled variants); tests/test_availability.py::test_status_one_hot_covers_every_fpl_code; tests/test_availability.py::test_snapshot_age_days_is_deadline_minus_snapshot_ts; tests/test_availability.py::test_unknown_status_code_raises_not_silently_dropped; tests/test_availability.py::test_news_added_postdating_deadline_raises_naming_the_row

### 15. [auto] 10-04 D2
expected: "Whole-family NaN fallback: a player-gameweek absent from
result: pass
source: automated
coverage_id: D2 (10-04-SUMMARY.md)
verified_by: tests/test_availability.py::test_whole_family_is_nan_when_no_snapshot_qualifies; tests/test_availability.py::test_availability_family_present_and_not_rolled_in_features; apply_experiment_feature_gating: flag off drops all 8 av_ columns, flag on keeps all 8 (verified against real load_features()); tests/test_leakage.py::test_availability_features_are_raw_context_not_rolled

### 16. [auto] 10-04 D3
expected: "Read-only per-season/per-source coverage + snapshot-staleness
result: pass
source: automated
coverage_id: D3 (10-04-SUMMARY.md)
verified_by: python -m data.availability --report (real data: prints per-source and per-season lines, WARNING for sub-50% seasons); sha256(availability.parquet) unchanged across a --report run; data/processed/experiments/availability_coverage.json contains per_season/per_source top-level keys

### 17. [auto] 10-05 D1
expected: Figshare pre-scraped injury dataset checked via its public search API before any scraper code was written; verdict INSUFFICIENT recorded with evidence
result: pass
source: automated
coverage_id: D1 (10-05-SUMMARY.md)
verified_by: python -m data.transfermarkt --figshare-check

### 18. [auto] 10-05 D2
expected: Real 8-page probe against transfermarkt.com from this machine; anti-bot interstitial detection provably raises instead of parsing to an empty frame
result: pass
source: automated
coverage_id: D2 (10-05-SUMMARY.md)
verified_by: tests/test_transfermarkt.py::test_parse_injury_table_on_saved_fixture, test_parse_injury_table_raises_on_challenge_page, test_probe_records_verdict_per_page_without_raising; python -m data.transfermarkt --probe --n 8 (real run, 7/8 ok)

### 19. [auto] 10-06 D2
expected: All 38 available 2025-26 gameweeks fetched, reduced to the approved six-column footprint, and committed under 20 MB
result: pass
source: automated
coverage_id: D2 (10-06-SUMMARY.md)
verified_by: python -m data.fpl_core_insights --fetch (real network run, 38/38 gameweeks written); du -sk data/external/fpl_core_insights -> 1,028 KB (well under 20,000)

### 20. [auto] 10-06 D3
expected: Vendored snapshot verified against our own captures with a real, printed agreement rate
result: pass
source: automated
coverage_id: D3 (10-06-SUMMARY.md)
verified_by: python -m data.fpl_core_insights --verify -> data/processed/experiments/fpl_core_insights_verify.json (status_agreement, chance_agreement, per_gw present)

### 21. [auto] 10-06 D4
expected: N-1 leakage offset proven on synthetic data, plus the missing-column raise
result: pass
source: automated
coverage_id: D4 (10-06-SUMMARY.md)
verified_by: tests/test_availability.py::test_vendored_provider_uses_prior_gw_folder; tests/test_availability.py::test_reduce_gw_csv_raises_on_missing_availability_column

### 22. [auto] 10-06 D5
expected: 2025-26 availability coverage measurably non-zero and improved after vendoring
result: pass
source: automated
coverage_id: D5 (10-06-SUMMARY.md)
verified_by: python -m data.availability --report: 2025-26 coverage 92.2% -> 92.7% (27,195/29,338 rows)

### 23. [auto] 10-07 D1
expected: resolve_tm_id resolves a name to a Transfermarkt id exactly once per player_code (via data.id_crosswalk.tm_id_cache), and a second call for the same player issues zero HTTP requests
result: pass
source: automated
coverage_id: D1 (10-07-SUMMARY.md)
verified_by: python -c '...resolve_tm_id(...) twice...' -- first call 0.01s (cached search HTML from plan 10-05's probe), second call 0.001s (id-cache hit, zero HTTP)

### 24. [auto] 10-07 D2
expected: build() is resumable and killable: a real kill-and-restart cycle during this plan's own execution proved the second run picked up exactly where the first left off (player 21/2623), never re-processing the first 20 players
result: pass
source: automated
coverage_id: D2 (10-07-SUMMARY.md)
verified_by: live kill (SIGTERM, PID 191523) after 20 players processed/flushed, then a fresh `python -u -m data.transfermarkt --build` process started at player 21 -- observed directly in the log

### 25. [auto] 10-07 D3
expected: injury_status_as_of's overlap semantics match the three hand-computed cases (mid-spell, post-spell, ongoing spell) exactly, and the vectorized attach() agrees with the scalar reference implementation
result: pass
source: automated
coverage_id: D3 (10-07-SUMMARY.md)
verified_by: python -c '...injury_status_as_of(...)...' -- a=14 days mid-spell, b=not-injured post-spell, c=injured on an ongoing (until_date=null) spell; attach() on a synthetic id-map+spell-table fixture against a real 2000-row player_gw slice -- tm_injured/tm_days_out_so_far/tm_spells_prior_365d/tm_days_out_prior_365d all matched hand-verified expectations across the spell's active/inactive gameweeks

### 26. [auto] 10-07 D4
expected: The todo's own explicit leakage requirement -- every spell contributing to a gameweek's injury features has from_date strictly before both the deadline and the kickoff -- asserted against the REAL committed (partial) spell table, not synthetic data
result: pass
source: automated
coverage_id: D4 (10-07-SUMMARY.md)
verified_by: tests/test_leakage.py::test_transfermarkt_injury_dates_precede_kickoff

### 27. [auto] 10-07 D5
expected: config.EXPERIMENTS['transfermarkt_injury'] defaults False and apply_experiment_feature_gating drops every tm_ column when off, keeps all four when on -- proven against real data via data.transfermarkt.attach() + models.train.load_features(), since data/build_table.py's own wiring is deferred to plan 10-08
result: pass
source: automated
coverage_id: D5 (10-07-SUMMARY.md)
verified_by: tests/test_experiments.py::test_transfermarkt_injury_gate_drops_or_keeps_all_four_on_real_attach; python -m pytest -q (repo-wide: 289 passed, 1 unrelated pre-existing skip)

### 28. [auto] 10-08 D1
expected: Both Tier-1 feature families (availability, injury) reach features.parquet through the standard optional-enrichment path; the frozen matrix every measurement in this plan shares is recorded by hash and verified unchanged across all runs
result: pass
source: automated
coverage_id: D1 (10-08-SUMMARY.md)
verified_by: features.parquet sha256 ae809b5b6169ee776363e543fd6c50e78017cf1f36e1c3742807feb16336dc3f (253,509 rows x 172 columns) -- verified identical at Task 1 commit time and again before every Task 2 measurement; python -m pytest -q -- 323 passed, 1 skipped (pre-existing .env-gated cron test), 0 failed

### 29. [auto] 10-08 D2
expected: availability_flags measured against D-09's dual criterion (2025-26 model+chips +25 AND pooled played-only Spearman +0.03 over 0.383), both legs on record, REJECTED (neither leg met, coverage 92.7% not thin)
result: pass
source: automated
coverage_id: D2 (10-08-SUMMARY.md)
verified_by: data/processed/experiments/wf_avail_base_2526.json / wf_avail_on_2526.json -- 2025-26 model+chips 2172 -> 2172 (+0, need +25); data/processed/experiments/benchmark_tier1_base.json / benchmark_tier1_avail.json -- pooled played-only spearman_xp_med 0.3832 -> 0.3832 (+0.0000, need +0.03)

### 30. [auto] 10-08 D3
expected: transfermarkt_injury measured against the standard 6-season >=2,280 bar, REJECTED (2262 -> 2242, a -20 regression against its own fresh control)
result: pass
source: automated
coverage_id: D3 (10-08-SUMMARY.md)
verified_by: data/processed/experiments/wf_tm_base6.json / wf_tm_on6.json -- 6-season model+chips 2262 -> 2242

### 31. [auto] 10-08 D4
expected: D-02 news-sentiment trigger evaluated against the locked 0.500 threshold using the measured post-Tier-1 pooled Spearman; outcome (BUILD) recorded before plan 10-12 acts on it, with the two-scoreable-seasons/zero-availability-coverage structural caveat stated explicitly
result: pass
source: automated
coverage_id: D4 (10-08-SUMMARY.md)
verified_by: data/processed/experiments/benchmark_tier1.json -- pooled played-only spearman_xp_med 0.3874 < 0.500 -> BUILD

### 32. [auto] 10-08 D5
expected: Both verdicts recorded in IMPROVEMENTS.md's Phase 10 results table with numbers, each flag stays default-off; seven remaining rows (news_sentiment + 6 bracket flags) still pending; all Phase A-F anchors intact
result: pass
source: automated
coverage_id: D5 (10-08-SUMMARY.md)
verified_by: python -c '...' -- both Tier-1 rows filled, non-pending; bracket-row pending count >= 14 (measured 15, includes one prose occurrence); all named Phase A-F headings present; config.EXPERIMENTS all False

### 33. [auto] 10-09 D1
expected: An externally-produced per-season prediction parquet scores through the exact same run_season/_preds_for path an in-process LightGBM run uses -- proven by exact round-trip equivalence (both totals 2133 for 2025-26, 100% join coverage)
result: pass
source: automated
coverage_id: D1 (10-09-SUMMARY.md)
verified_by: tests/test_bracket.py::test_external_preds_roundtrip_matches_in_process_run

### 34. [auto] 10-09 D2
expected: load_external_predictions VALIDATES rather than merely loads: missing-column, wrong-season-set, row-count-fan-out, and ground-truth-column rejections all fire with the required named-in-error-message detail
result: pass
source: automated
coverage_id: D2 (10-09-SUMMARY.md)
verified_by: tests/test_bracket.py::test_external_preds_rejects_missing_required_column; tests/test_bracket.py::test_external_preds_rejects_wrong_season_set; tests/test_bracket.py::test_external_preds_rejects_row_count_increase; tests/test_bracket.py::test_external_preds_ignores_ground_truth_columns_in_the_artifact

### 35. [auto] 10-09 D3
expected: A leakage-corrupt candidate (xp_med literally copied from real y_points) is flagged IMPLAUSIBLE against a vintage-keyed in-process LightGBM baseline (2025-26 measured 0.3464 played-only Spearman); a legitimate round-tripped artifact is NOT flagged -- the check fires on a real leak and stays quiet on a real candidate
result: pass
source: automated
coverage_id: D3 (10-09-SUMMARY.md)
verified_by: tests/test_bracket.py::test_external_preds_flags_implausible_spearman_jump; tests/test_bracket.py::test_external_preds_legitimate_roundtrip_not_flagged_implausible; python -c '...hashlib.sha256(features.parquet)... assert h in json.dumps(cache entry)...' -- confirms lgbm_played_spearman.json's cache entry is keyed by the feature-matrix hash, not just the season

### 36. [auto] 10-09 D4
expected: The seam is built and proven before any Colab candidate exists (--external-preds refuses --experiments capt_ceiling with a named reason; multi_safe recorded as None with a printed note rather than a fabricated number; the plain unflagged walk_forward path runs unchanged)
result: pass
source: automated
coverage_id: D4 (10-09-SUMMARY.md)
verified_by: python -m backtest.walk_forward --external-preds /nonexistent.parquet --experiments capt_ceiling --seasons 2025-26 -- non-zero exit, 'capt_ceiling' named in stderr; python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag seam_regression -- [2025-26] model= line printed, wf_seam_regression.csv/.json written

### 37. [auto] 10-10 D1
expected: xgboost/catboost installed only after the blocking-human package gate, at re-verified pins, into a dev-only hash-locked lockfile provably isolated from Docker/CI (zero grep hits, production/dev locks byte-identical)
result: pass
source: automated
coverage_id: D1 (10-10-SUMMARY.md)
verified_by: grep -rl requirements-experiments Dockerfile .github/workflows/ -> 0 hits; git diff --stat requirements.txt requirements-dev.txt requirements.in requirements-dev.in -> empty

### 38. [auto] 10-10 D2
expected: train_position(..., stage2='lgbm') is byte-equivalent to the pre-bracket shipped path -- only the conditional-points regressor is swappable; the stage-1 P(play) classifier and ComponentModel structure are untouched
result: pass
source: automated
coverage_id: D2 (10-10-SUMMARY.md)
verified_by: tests/test_experiments.py::test_stage2_lgbm_default_matches_explicit_prediction_equivalence; tests/test_experiments.py::test_stage2_ridge_swaps_only_the_conditional_points_regressor; tests/test_experiments.py::test_stage2_ridge_def_component_path_swaps_only_residual_regressor; python -m backtest.walk_forward --seasons 2025-26 --replicas 1 --tag bracket_seam_regression -- model+chips=2172, identical to the pre-change wf_seam_regression.json baseline

### 39. [auto] 10-10 D3
expected: Ridge, XGBoost and CatBoost each have a measured, recorded, same-split D-15 gate result (Spearman, MAE, delta, ADVANCE/HOLD verdict), gate provably never trains on the model's real held-out test season
result: pass
source: automated
coverage_id: D3 (10-10-SUMMARY.md)
verified_by: tests/test_bracket.py::test_gate_never_trains_on_a_test_season; tests/test_bracket.py::test_gate_spearman_matches_benchmark_external_definition; python -m models.bracket.gate --candidate lgbm --candidate ridge --candidate xgb --candidate catboost -- four bracket_gate_<candidate>.json files written, all HOLD

### 40. [auto] 10-11 D1
expected: The sequence builder (models/bracket/sequence.py) honours D-20's raw-input specification (SEQ_STATS/STATIC_COLS never carry a rolled _r3/_r5/_r10/_rall column) and passes D-21's leakage assertion by independent recompute on 200+ real sampled fixtures spread across seasons
result: pass
source: automated
coverage_id: D1 (10-11-SUMMARY.md)
verified_by: tests/test_leakage.py::test_sequence_features_no_future_gw_leakage; tests/test_bracket.py::test_sequence_window_is_padded_and_masked; tests/test_bracket.py::test_sequence_uses_raw_stats_not_rolled_features; grep -c pad_sequence models/bracket/sequence.py -> 4 (non-zero, standard torch idiom used, not hand-rolled)

### 41. [auto] 10-11 D2
expected: The shared raw-torch training loop (train_torch_regressor) and TorchRegressorAdapter follow optimize/rl_train.py's own convention, restore best-epoch weights (never the last epoch), fit the imputer/scaler on train only, and drop into models/train.py's stage-2 slot unchanged (sklearn fit/predict contract, tolerates LightGBM-only kwargs)
result: pass
source: automated
coverage_id: D2 (10-11-SUMMARY.md)
verified_by: tests/test_bracket.py::test_torch_adapter_matches_sklearn_predict_contract; git status --porcelain models/artifacts -> empty (checkpoints land in the already-gitignored dir); grep -cE '(import|from) (skorch|pytorch_lightning|lightning)' models/bracket/deep.py -> 0

### 42. [auto] 10-11 D3
expected: The MLP is measured at both D-18 granularities (per_position, pooled) within D-19's declared 12-config search budget per variant, and the better variant's gate result is written to data/processed/experiments/bracket_gate_mlp.json in the schema every later plan reads (key-superset of bracket_gate_lgbm.json, plus granularity + granularity_scores)
result: pass
source: automated
coverage_id: D3 (10-11-SUMMARY.md)
verified_by: tests/test_bracket.py::test_mlp_search_respects_budget; tests/test_bracket.py::test_granularity_bracket_writes_gate_schema; python -m models.bracket.deep (via run_granularity_bracket('mlp')) -- real 8-season train / 2024-25 val run, per_position=0.3924, pooled=0.3942, winner=pooled, delta vs lgbm baseline (0.3900) = +0.0042 < GATE_MARGIN(0.010) -> HOLD

### 43. [auto] 10-12 D1
expected: D-02 trigger read from the measured artifact (0.3874 < 0.500 -> fired) and the mechanical BUILD outcome stated, before any override is applied
result: pass
source: automated
coverage_id: D1 (10-12-SUMMARY.md)
verified_by: data/processed/experiments/benchmark_tier1.json pooled.spearman_xp_med = 0.3874, read live via python -c, quoted in the checkpoint and in IMPROVEMENTS.md

### 44. [auto] 10-12 D2
expected: Projected build wall clock computed live from features.parquet (not estimated from memory): 244,425 distinct (season,gw,player_code) windows at full config.SEASONS scope (~339.5h / 14.1 days) and 156,075 at the 6-season measurement scope (~216.8h / 9.0 days), both at the locked _GDELT_MIN_INTERVAL_S=5.0
result: pass
source: automated
coverage_id: D2 (10-12-SUMMARY.md)
verified_by: python -c pandas query against data/processed/features.parquet, counted distinct (season,gw,player_code) triples for config.SEASONS and for the 6-season protocol subset; both figures quoted verbatim in the checkpoint and in IMPROVEMENTS.md's declined-on-cost entry

### 45. [auto] 10-12 D3
expected: The verbatim DECLINE answer is recorded in IMPROVEMENTS.md's D-02 section as 'declined on cost', explicitly distinguished from a 'not triggered' outcome, and the Phase 10 results table's news_sentiment row reflects DECLINED ON COST rather than pending or REJECTED
result: pass
source: automated
coverage_id: D3 (10-12-SUMMARY.md)
verified_by: IMPROVEMENTS.md new '### D-02 news-sentiment: declined on cost, NOT not-triggered (plan 10-12)' subsection, commit e243e66; results-table news_sentiment row updated in the same commit

### 46. [auto] 10-13 D1
expected: Both sequence candidates (GRU, transformer) provably ignore padded timesteps and concatenate the static vector after the encoder, never as an extra timestep
result: pass
source: automated
coverage_id: D1 (10-13-SUMMARY.md)
verified_by: tests/test_bracket.py::test_sequence_regressors_consume_the_padding_mask; tests/test_bracket.py::test_transformer_size_matches_locked_budget

### 47. [auto] 10-13 D2
expected: All seven config.BRACKET_CANDIDATES entries resolve through models/bracket/registry.py with lazy torch imports (is_available answers False, never raises, for an absent package)
result: pass
source: automated
coverage_id: D2 (10-13-SUMMARY.md)
verified_by: tests/test_bracket.py::test_registry_covers_all_seven_bracket_candidates; tests/test_bracket.py::test_registry_is_available_never_raises_for_deep_candidates

### 48. [auto] 10-13 D3
expected: The Colab handoff (export_sequence_bundle, manifest.json, colab/bracket_deep.ipynb, colab/README.md) makes the manifest the notebook's split authority, proven to match backtest.walk_forward's own expanding-window rule
result: pass
source: automated
coverage_id: D3 (10-13-SUMMARY.md)
verified_by: tests/test_bracket.py::test_exported_bundle_roundtrips_to_the_same_tensors

### 49. [auto] 10-13 D4
expected: Both Colab-trained frozen artifacts (colab_rnn_2025-26.parquet, colab_transformer_2025-26.parquet) score through backtest.walk_forward.load_external_predictions -- 100% join coverage, correct schema, single season, no ground-truth column, no fan-out -- and both HOLD against the LightGBM baseline at GATE_MARGIN=0.010 with no [external] IMPLAUSIBLE warning fired
result: pass
source: automated
coverage_id: D4 (10-13-SUMMARY.md)
verified_by: python -m backtest.walk_forward --external-preds data/processed/experiments/colab/colab_rnn_2025-26.parquet --seasons 2025-26 --replicas 5 --tag bracket_rnn_2526 -- [external] 2025-26: joined 29,747/29,747 (100.0%), model+chips=863, multi_safe=None; python -m backtest.walk_forward --external-preds data/processed/experiments/colab/colab_transformer_2025-26.parquet --seasons 2025-26 --replicas 5 --tag bracket_transformer_2526 -- [external] 2025-26: joined 29,747/29,747 (100.0%), model+chips=1619, multi_safe=None

### 50. [auto] 10-13 D5
expected: Every one of the seven candidates has a bracket_gate_<candidate>.json file (none missing/unrun) -- D-13's compute budget was never exhausted, so no candidate carries status: not_run_compute_exhausted
result: pass
source: automated
coverage_id: D5 (10-13-SUMMARY.md)
verified_by: ls data/processed/experiments/bracket_gate_{lgbm,ridge,xgb,catboost,mlp,rnn,transformer}.json -- all 7 present, all status: ok

### 51. [auto] 10-14 D1
expected: The D-15 advance rule applied mechanically to all seven recorded bracket_gate_<candidate>.json files: 7/7 HOLD, 0 ADVANCE, no candidate silently dropped from the comparison
result: pass
source: automated
coverage_id: D1 (10-14-SUMMARY.md)
verified_by: tests/test_bracket.py::test_gate_advance_rule_is_mechanical; tests/test_bracket.py::test_gate_advance_rule_is_mechanical_over_the_seven_recorded_candidates; python -c one-liner reading all seven bracket_gate_*.json and computing ADVANCE set -- ADVANCE: none (reproduced verbatim in this SUMMARY and in IMPROVEMENTS.md)

### 52. [auto] 10-14 D2
expected: D-17's conditional onnxruntime/export path correctly did not trigger (no torch candidate advanced) -- nothing installed, no code created, recorded as a non-decision
result: pass
source: automated
coverage_id: D2 (10-14-SUMMARY.md)
verified_by: grep -c onnxruntime requirements.in requirements-dev.in -> 0/0; grep -rl onnxruntime|requirements-experiments Dockerfile .github/workflows/ -> 0 hits; models/bracket/export.py does not exist

### 53. [auto] 10-14 D3
expected: IMPROVEMENTS.md's Phase 10 results table reaches zero pending cells (9/9 flag rows filled) and both required ## Phase G subsections (bracket verdict, news_sentiment verdict) exist with commands, artifact paths, and mechanical verdicts, without disturbing any prior anchor heading
result: pass
source: automated
coverage_id: D3 (10-14-SUMMARY.md)
verified_by: python -c checks against IMPROVEMENTS.md: zero pending cells, both verdict-section headings present, all five prior anchor headings intact (## Phase F, availability_flags/D-02/capt_mc subsections, ## Reference findings)

### 54. [auto] 10-14 D4
expected: Full repo test suite and lint stay green after the plan's edits -- no regression introduced by the new tests or the ledger write
result: pass
source: automated
coverage_id: D4 (10-14-SUMMARY.md)
verified_by: python -m pytest -q -> 328 passed, 1 pre-existing skip, 284.44s; ruff check . -> All checks passed!

### 55. [auto] 10-15 D2
expected: No adoption number was fabricated against a defective/unusable data source -- the flag stays off, no code was written around all-NaN columns
result: pass
source: automated
coverage_id: D2 (10-15-SUMMARY.md)
verified_by: config.EXPERIMENTS['fbref_v2'] is False; grep -c 'load_manual_snapshot' data/fbref.py -> 0 (not written); git diff --stat data/fbref.py features/engineer.py tests/test_leakage.py -> empty

### 56. [auto] 10-15 D3
expected: The RL item is notes-only: no training runs, neither optimize/rl_env.py nor optimize/rl_train.py changed
result: pass
source: automated
coverage_id: D3 (10-15-SUMMARY.md)
verified_by: git diff --stat optimize/rl_env.py optimize/rl_train.py -> empty

### 57. [auto] 10-15 D4
expected: The potential-based-shaping correction (Ng, Harada and Russell 1999), the price-chasing failure mode, and the log-linear compute curve are on the record for any future revisit
result: pass
source: automated
coverage_id: D4 (10-15-SUMMARY.md)
verified_by: python -c checking IMPROVEMENTS.md for 'Ng, Harada and Russell', 'optimize/rl_env.py', 'log-linear', 'potential-based', '1e-6', 'weight 1', 'D-16', 'skip' -- all present

### 58. [auto] 10-15 D5
expected: Full repo test suite and lint stay green after the plan's edits
result: pass
source: automated
coverage_id: D5 (10-15-SUMMARY.md)
verified_by: python -m pytest -q -> 328 passed, 1 pre-existing skip, 279.73s; ruff check . -> All checks passed!

### 59. [auto] 10-16 D1
expected: The D-11 split-verdict combined run: full-coverage winner set mechanically derived as empty from the ledger, run launched with no --experiments flag, model+chips=2262 measured and reconciled against the 2,262 baseline and 2,280 bar, availability_flags verified absent from the combined flag set
result: pass
source: automated
coverage_id: D1 (10-16-SUMMARY.md)
verified_by: data/processed/experiments/wf_combined_phase10.json -- replicas=5, seasons=6, model+chips=2262, availability_flags not in enabled flag set (all False); python -m pytest tests/test_availability.py::test_missing_snapshot_degrades_to_nan_not_raise -q -- 1 passed (D-10 gate)

### 60. [auto] 10-16 D2
expected: Single reviewable default-change commit: config.py byte-identical before/after (zero flags adopted), tests/test_experiments.py left untouched, verified programmatically that every flag flipped True is named in the registry test (vacuously true here since zero flags flipped)
result: pass
source: automated
coverage_id: D2 (10-16-SUMMARY.md)
verified_by: git diff --stat config.py -- empty; python -m pytest tests/test_experiments.py -q -- 49 passed

### 61. [auto] 10-16 D3
expected: Product surface proven unchanged: new test_phase10_flags_default_off_leaves_export_contract_unchanged greps every real web/data/*.json payload for av_/tm_/nw_/bracket_ keys (none found); real python -m predict.export run completed; git diff --stat web/data classified as key-stable value-refresh (5 files changed, single-line JSON rewrites, key sets byte-identical before/after per a scripted key-set diff)
result: pass
source: automated
coverage_id: D3 (10-16-SUMMARY.md)
verified_by: tests/test_product.py::test_phase10_flags_default_off_leaves_export_contract_unchanged -- 1 passed; python -m predict.export -- real run, GW4, 656 players; git diff --stat web/data -- captains/meta/squad/xp_table.json changed (2 chars each, single-line rewrites), fixtures/chips/leaders/standings unchanged

### 62. [auto] 10-16 D4
expected: Every D-01 through D-21 decision audited with an outcome and evidence citation; all eight resolves_phase:10 todos named by file stem with their resolution; Phase 10 results table has zero unfilled cells; all Phase A-F anchors (incl. Phase 9's own decisions-audit and did-not-resolve headings) intact
result: pass
source: automated
coverage_id: D4 (10-16-SUMMARY.md)
verified_by: python -c checks against IMPROVEMENTS.md -- all 21 D-NN tokens present in the Decisions audit section; all 8 todo stems named in Phase G; results table has zero pending cells; five prior anchor headings intact

### 63. [auto] 10-16 D5
expected: Full repo test suite stays green after every edit this plan made
result: pass
source: automated
coverage_id: D5 (10-16-SUMMARY.md)
verified_by: python -m pytest -q -- 329 passed, 1 pre-existing skip, 0 failed (297.90s)

## Summary

total: 63
passed: 63
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
