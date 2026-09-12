---
phase: "10"
slug: "xp-experiment-follow-ups"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-12"
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| FPL API / GitHub raw / api.github.com → `data/raw/`, `data/snapshots/` | untrusted third-party JSON/CSV enters the pipeline (bootstrap-static, FPL-Core-Insights, standings/picks) | public player metadata, prices, availability fields |
| Transfermarkt HTML → `data/external/transfermarkt/` derived CSV | scraped injury-history pages parsed into an 8-column derived table; raw HTML never committed | public injury spells, tm player ids |
| `data/processed/*.parquet` → `features.parquet` → model training | a wrong value or wrong timestamp here silently corrupts every downstream prediction (leakage boundary) | engineered features, as-of-deadline availability |
| Local repo → Colab bundle (`colab/`, `*_tensors.npz`) | external GPU trainer handoff for deep bracket candidates | sequence tensors, join keys, split labels |
| Pipeline → `web/data/*.json` product contract | experiment features must never leak into the shipped product surface | xp table, squad, captains JSON |
| cron (`scripts/daily.sh`, `scripts/snapshot_catchup.sh`) → live data dirs | unattended writes to real snapshots/artifacts; failures must be loud and idempotent | daily snapshots, cron log, webhook alerts |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-10-01-01 | Tampering | `data/availability.py` provider registry | high | mitigate | `_require_columns` raises `ValueError` naming the absent column, so an upstream schema change fails loudly instead of producing an all-NaN … | closed |
| T-10-01-02 | Tampering | `resolve_as_of` time boundary | critical | mitigate | selection requires BOTH `snapshot_ts < deadline_ts` AND `snapshot_ts < min(kickoff_time)`; asserted for every registered `source` by `tests… | closed |
| T-10-01-03 | Denial of Service | `data/build_table.py` availability block | medium | mitigate | wrapped in the same `try/except Exception` + `[availability] skipped` print as the three existing optional-enrichment blocks — an availabil… | closed |
| T-10-01-04 | Information Disclosure | `news` free-text captured into `data/snapshots/*.parquet` (… | low | accept | FPL's `news` field is public editorial copy about publicly-known players ("Knock - 75% chance of playing"), not third-party personal data; … | closed |
| T-10-01-05 | Repudiation | pre-declared criteria written after a measurement | high | mitigate | Task 3 writes the criteria block in wave 1; plan 10-08 (the first adoption run) carries a `<precondition>` asserting the block exists, so n… | closed |
| T-10-01-06 | Tampering | test isolation vs the irreplaceable `data/snapshots/` archi… | high | mitigate | `tests/test_availability.py`'s autouse fixture monkeypatches `data.snapshot.SNAP_DIR` to `tmp_path`, matching `tests/test_cron.py`'s existi… | closed |
| T-10-02-01 | Information Disclosure | top-100 managers' `player_name`/`entry_name` from the stand… | high | mitigate | `consensus_ownership` aggregates to `player_id` counts only; no manager identifier, team name or entry id is written to any parquet or to `… | closed |
| T-10-02-02 | Tampering | a mis-pasted fplreview CSV silently entering the published … | high | mitigate | `data/fplreview.py::validate` raises on missing columns and on an all-non-numeric projection column; duplicate `player_code` within a gamew… | closed |
| T-10-02-03 | Legal/compliance | fplreview ToS forbids ingestion and redistribution | high | mitigate | zero `requests` references in `data/fplreview.py` (verify-enforced), no `config.EXPERIMENTS` flag and no `*_COLS` constant references the d… | closed |
| T-10-02-04 | Denial of Service | scoreboard cron blocked by a slow or failing standings fetch | medium | mitigate | `fetch_entry_picks` returns `[]` on `requests.RequestException`; `load_consensus`/`load_gw` return `None` when absent, so both blocks skip … | closed |
| T-10-02-05 | Spoofing | wrong league id yields a "top 100" that is an arbitrary lea… | medium | mitigate | `OVERALL_LEAGUE_ID` is a single named constant, the first real run prints the top-3 entries for a human eyeball, and the SUMMARY records th… | closed |
| T-10-03-01 | Tampering | `data/snapshots/` overwrite or deletion by the catch-up scr… | critical | mitigate | the script only ever invokes `python -m data.snapshot` with no `--force`, so `take_snapshot`'s own `out.exists() and not force` guard makes… | closed |
| T-10-03-02 | Tampering | a test writing into the real archive | high | mitigate | the `FPL_SNAPSHOT_DIR` override plus `tests/test_cron.py`'s existing `SNAP_DIR` monkeypatch fixture keep every test in `tmp_path`; the head… | closed |
| T-10-03-03 | Repudiation | a silent capture failure on boot | high | mitigate | failure alerts through the same `ops.notify` path `daily.sh` uses, whose never-raise + redaction contract is already tested; the script exi… | closed |
| T-10-03-04 | Information Disclosure | secrets in the alert message or in `data/cron.log` | low | mitigate | the message is a literal `exit code $rc` with no payload; `ops.jsonlog.redact()` already covers the notify path and has direct unit tests f… | closed |
| T-10-03-05 | Denial of Service | repeated `@reboot` invocations hammering the FPL API on a r… | low | accept | one bootstrap-static GET per UTC day maximum by construction (the idempotency guard); a reboot loop would produce at most one additional re… | closed |
| T-10-04-01 | Tampering | status one-hot on an unrecognised code | high | mitigate | distinct codes validated against `_STATUS_CODES` first; an unknown code raises `ValueError` naming it and its row count, because an all-zer… | closed |
| T-10-04-02 | Tampering | partial family fill making absence look like availability | high | mitigate | `attach`'s left merge yields whole-family NaN; `test_whole_family_is_nan_when_no_snapshot_qualifies` asserts all eight together, and the ve… | closed |
| T-10-04-03 | Tampering | a `news_added` value postdating the deadline | high | mitigate | `encode_availability` raises `AssertionError` naming the offending `(season, gw, player_code)` rather than clipping — it is an escape-hatch… | closed |
| T-10-04-04 | Information Disclosure | FPL `news` free text in a tracked artifact | low | accept | public editorial copy about public players, already visible in every FPL client; only its timestamp is encoded as a feature, and `av_days_s… | closed |
| T-10-04-05 | Tampering | a coverage report mutating the artifact under judgement | medium | mitigate | `--report` is read-only and the verify asserts the parquet's sha256 is unchanged across a report run | closed |
| T-10-05-01 | Tampering | an anti-bot challenge page parsed as an empty injury table | critical | mitigate | `parse_injury_table` scans for `Just a moment`, `DataDome`, `captcha-delivery`, `Attention Required` and raises `ValueError` naming the mar… | closed |
| T-10-05-02 | Tampering | wrong-footballer id from the search endpoint | high | mitigate | the probe records the resolved `(name, tm_player_id)` pair per row for human eyeball at the checkpoint, and name resolution goes through `d… | closed |
| T-10-05-03 | Tampering | schema drift in the injury table's columns | high | mitigate | `parse_injury_table` returns a fixed six-column contract; the checkpoint requires the verbatim served headers to be compared against 10-RES… | closed |
| T-10-05-04 | Denial of Service | our request rate getting this IP blocked | medium | mitigate | `_MIN_INTERVAL_S = 3.0` (double `data/fotmob.py`'s), the probe is capped at 8 pages, and every page is cached under `data/raw/transfermarkt… | closed |
| T-10-05-05 | Legal/compliance | committing scraped content whose ToS forbids redistribution | high | mitigate | this plan commits no scraped page (`data/raw/` is gitignored); the D-07 committed artifact is a derived, normalized spell table decided in … | closed |
| T-10-05-06 | Repudiation | building a fetcher on an unconfirmed source and calling the… | high | mitigate | the go/no-go checkpoint is blocking-human and 10-07 depends on this plan; decision D produces a recorded `not acquirable` verdict rather th… | closed |
| T-10-06-01 | Tampering | folder-freeze mis-dating (treating a gameweek-N folder as g… | critical | mitigate | the provider assigns `snapshot_ts = max(kickoff_time over (season, N))`, so the shared resolver can only ever admit it for a later gameweek… | closed |
| T-10-06-02 | Tampering | vendor schema drift silently producing an all-NaN availabil… | high | mitigate | `_reduce_gw_csv` raises `ValueError` naming every missing `_KEEP_COLS` member and the gameweek, per 10-RESEARCH.md Pitfall 2 | closed |
| T-10-06-03 | Tampering | a vendor value disagreeing with reality, adopted unchecked | high | mitigate | `--verify` compares `status` and `chance_of_playing_next_round` against our own captures on the two overlapping days and prints an explicit… | closed |
| T-10-06-04 | Legal/compliance | committing content whose license forbids redistribution | high | mitigate | blocking-human license checkpoint before any bulk fetch, decision recorded verbatim, posture written into the README's `## Attribution` | closed |
| T-10-06-05 | Information Disclosure | third-party manager/entry identity inside the vendor's files | medium | mitigate | `_KEEP_COLS` is an allowlist, not a denylist, so any unexpected column is dropped by construction; the README's `## PII spot-check` records… | closed |
| T-10-06-06 | Denial of Service | repository bloat from an oversized committed vintage | medium | mitigate | a hard `du -sk` verify gate at 20 MB, CSVs only, one season only, availability columns only | closed |
| T-10-07-01 | Tampering | wrong-footballer id resolution corrupting an unrelated play… | high | mitigate | ids resolve through `data.id_crosswalk.resolve_by_name` only (whole-token verification, mononym exclusion — the crosswalk's own discipline)… | closed |
| T-10-07-02 | Tampering | a challenge page or parse failure silently becoming "no inj… | critical | mitigate | `parse_injury_table` (plan 10-05) raises on the four challenge markers; `build` counts and reports failures per player, and an unresolvable… | closed |
| T-10-07-03 | Tampering | an unparsed `from_date` entering a date-range comparison as… | high | mitigate | `build` coerces with an explicit format check and drops unparsable rows with a counted printed warning; the verify asserts `from_date.notna… | closed |
| T-10-07-04 | Tampering | future-dated spell information leaking into gameweek g | critical | mitigate | features are computed against `deadline_ts` from the single shared `data.availability.gw_deadlines()`, and `tests/test_leakage.py::test_tra… | closed |
| T-10-07-05 | Tampering | a resumed run double-counting spells | medium | mitigate | deduplication on `(player_code, from_date)` before every incremental write, asserted on the committed table | closed |
| T-10-07-06 | Legal/compliance | committing scraped page content | high | mitigate | only the derived eight-column normalized table is committed; raw HTML stays under gitignored `data/raw/transfermarkt/`, verify-enforced by … | closed |
| T-10-07-07 | Denial of Service | a multi-hour run dying on one bad page | medium | mitigate | per-player try/except with a failure counter, incremental appends, and `--resume` skipping cached players, so a kill or a crash costs at mo… | closed |
| T-10-08-01 | Repudiation | a verdict back-fitted to the number that came out | high | mitigate | the criteria were written in plan 10-01 Task 3 in wave 1; this plan's verify prints each delta beside its pre-declared bar, and the action … | closed |
| T-10-08-02 | Tampering | comparing two runs trained on different feature matrices | high | mitigate | Task 1 records `features.parquet`'s sha256; Task 2 carries a `<precondition>` asserting it is unchanged, and every A/B uses a freshly measu… | closed |
| T-10-08-03 | Repudiation | reporting a partial-coverage result as if it were full-cove… | high | mitigate | the availability verdict must cite the measured 2025-26 coverage in the same paragraph as the verdict, and the D-02 record must state that … | closed |
| T-10-08-04 | Repudiation | citing an unverifiable paper as corroborating evidence | medium | mitigate | the injury verdict states the A1 caveat explicitly; the D-02 record cites mlpremier's negative finding rather than only the todo's optimist… | closed |
| T-10-08-05 | Denial of Service | availability or injury attach failure breaking the daily pi… | medium | mitigate | the fifth `data/build_table.py` block uses the same `try/except Exception` + skip print as the four existing ones | closed |
| T-10-09-01 | Tampering | a schema-valid but leakage-corrupt external artifact (test … | critical | mitigate | season-set equality check raises on a multi-season dump; the vintage-keyed implausibility check flags a Spearman jump over 0.15 with a name… | closed |
| T-10-09-02 | Tampering | ground truth supplied by the artifact rather than re-attach… | critical | mitigate | `_EXTERNAL_PRED_COLS` is an allowlist; any `y_*` column present is dropped with a named warning and truth is re-joined from `features.parqu… | closed |
| T-10-09-03 | Tampering | a fan-out join inflating the scored row set | high | mitigate | row-count assert naming both counts, in `_attach_opponent_id`'s established form, plus a printed join-coverage percentage | closed |
| T-10-09-04 | Repudiation | reporting a `multi_safe` figure that describes a different … | high | mitigate | `--external-preds` records `multi_safe` as `None` with a printed note rather than substituting a locally-trained model's `models`/`cols`; t… | closed |
| T-10-09-05 | Tampering | comparing a fresh candidate against a stale baseline | medium | mitigate | the baseline cache is keyed by `features.parquet`'s sha256 and recomputes on a change | closed |
| T-10-10-SC | Tampering | pip installs of xgboost and catboost (both SUS in the audit) | high | mitigate | blocking-human package-legitimacy checkpoint (Task 1), live-registry re-verification of both pins immediately before install with drift rep… | closed |
| T-10-10-01 | Tampering | the experiments stack leaking into the production image | high | mitigate | `grep -rl "requirements-experiments" Dockerfile .github/workflows/` must return zero, and `git diff --stat` on the production/dev locks mus… | closed |
| T-10-10-02 | Tampering | the stage-2 parameterization silently changing the shipped … | high | mitigate | a `stage2="lgbm"` prediction-equivalence test to 1e-9, plus a full walk-forward run reproducing plan 10-08's baseline | closed |
| T-10-10-03 | Tampering | a gate run training on a test season | critical | mitigate | `run_gate` asserts no `TEST_SEASONS` member is in its training seasons and raises; `test_gate_never_trains_on_a_test_season` re-checks the … | closed |
| T-10-10-04 | Repudiation | an optimistic in-sample gate figure quoted as if comparable… | high | mitigate | every gate JSON carries an explicit `eval_split` label and the docstring states the non-comparability | closed |
| T-10-10-05 | Tampering | median imputation destroying the information-bearing missin… | medium | mitigate | `SimpleImputer(add_indicator=True)` retains it, verify-enforced by grep, with the reasoning in a comment naming `test_first_appearance_has_… | closed |
| T-10-11-01 | Tampering | a same-double-gameweek fixture admitted as a prior timestep | critical | mitigate | the prior-fixture selection uses a strict `kickoff_time` bound rather than a `gw` integer bound, with the reasoning in a comment, and `test… | closed |
| T-10-11-02 | Tampering | right-padding making padding look like recent form | high | mitigate | left-padding so the most recent gameweek is always the last index, with an explicit `src_key_padding_mask`-convention boolean mask; asserte… | closed |
| T-10-11-03 | Tampering | re-feeding rolled features and calling it a test of learned… | high | mitigate | `SEQ_STATS` derives from `ROLL_STATS`'s raw members; a build-time assert plus a test reject any `_r3`/`_r5`/`_r10`/`_rall` member in either… | closed |
| T-10-11-04 | Tampering | a predict-time scaler refit causing train/serve skew | high | mitigate | the imputer and scaler are fitted on train only and reused in `predict`; the adapter test asserts finite predictions on NaN-containing input | closed |
| T-10-11-05 | Tampering | first-appearance rows silently dropped, changing the evalua… | medium | mitigate | they are retained as all-padded rows and a verify asserts at least one exists for a gameweek-1 target | closed |
| T-10-11-06 | Information Disclosure | large model checkpoints committed to the repository | medium | mitigate | checkpoints write under the already-gitignored `config.RL_POLICY_DIR`; `git status --porcelain models/artifacts` must be empty | closed |
| T-10-11-07 | Repudiation | a search quietly exceeding the declared budget | medium | mitigate | `SEARCH_BUDGET = 12` hard-stops, both search logs are asserted to be within budget, and the action forbids extending on a promising trend | closed |
| T-10-12-01 | Information Disclosure | `GUARDIAN_API_KEY` in a print, a cache path or a traceback | high | mitigate | read via `os.environ` after `config.load_dotenv()` (the `ODDS_API_KEY` precedent, mode-600 `.env`, never committed); cache slugs are built … | closed |
| T-10-12-02 | Tampering | an article published after the deadline entering a pre-matc… | critical | mitigate | the request window itself is the primary bound (`startdatetime`/`enddatetime`, `from-date`/`to-date` anchored to `data.availability.gw_dead… | closed |
| T-10-12-03 | Tampering | GDELT or Guardian schema drift silently producing NaN featu… | high | mitigate | `_require` explicit-shape validation raising `ValueError` naming the absent key, the same T-09-09-01 discipline `data/fotmob.py` established | closed |
| T-10-12-04 | Tampering | a mononym or short-name query matching unrelated news | high | mitigate | entity resolution goes through `data.id_crosswalk.resolve_by_name` only, inheriting its whole-token verification and mononym exclusion; no … | closed |
| T-10-12-05 | Denial of Service | a news outage breaking the daily pipeline | medium | mitigate | `attach` is an optional-enrichment path guarded the same way the four existing ones are; `load_news()` returns `None` when absent; a missin… | closed |
| T-10-12-06 | Repudiation | building an experiment the pre-declared trigger did not aut… | high | mitigate | Task 1's blocking decision checkpoint reads the number from `benchmark_tier1.json` and preserves the not-triggered / declined-on-cost disti… | closed |
| T-10-13-01 | Tampering | a model attending to padded timesteps and producing a plaus… | critical | mitigate | `src_key_padding_mask` on the encoder, last-non-padded-state selection in the GRU, no `pack_padded_sequence` against a left-padded layout, … | closed |
| T-10-13-02 | Tampering | a notebook deriving its own splits and leaking the test sea… | critical | mitigate | `manifest.json` carries the per-test-season split triples computed by `_preds_for`'s own rule, the README states the split contract as a pr… | closed |
| T-10-13-03 | Tampering | notebook model classes drifting from the repository's own | high | mitigate | the notebook's copied classes are labelled as copies in a comment stating that a divergence invalidates the comparison; the manifest's `fea… | closed |
| T-10-13-04 | Information Disclosure | credentials or local paths embedded in a notebook that gets… | high | mitigate | a verify greps the notebook JSON for credential names and local absolute paths and fails on any hit; the bundle carries no `y_*` ground tru… | closed |
| T-10-13-05 | Repudiation | an unrun candidate silently absent from the comparison | high | mitigate | an unrun candidate must still get a gate file with `status: not_run_compute_exhausted` and the remaining balance; the verify asserts all se… | closed |
| T-10-13-06 | Repudiation | an unrecorded compute spend making D-13's hard stop unenfor… | medium | mitigate | units consumed and remaining are recorded per candidate in the checkpoint response and the SUMMARY, and the action forbids starting a run t… | open — below high threshold (non-blocking) |
| T-10-14-SC | Tampering | the conditional `onnxruntime` install (SUS in the audit) | high | mitigate | blocking-human approval with live-registry re-verification and drift reporting, hash-locked into the experiments lockfile only, installed v… | closed |
| T-10-14-01 | Tampering | an ONNX graph diverging numerically from its torch original | high | mitigate | `verify_parity` on at least 1,000 real rows at a 1e-4 tolerance, raising with the maximum deviation named; `torch.onnx.export` used rather … | closed |
| T-10-14-02 | Tampering | torch reaching the production path through a module-scope i… | high | mitigate | a subprocess test imports `OnnxRegressor` with torch blocked in `sys.meta_path` and must succeed — the actual proof of D-17's guarantee | closed |
| T-10-14-03 | Repudiation | an inert experiment flag producing a no-op run recorded as … | critical | mitigate | Task 1 requires verifying the flag actually selects the candidate before running, and reporting an inert flag as a blocking gap rather than… | closed |
| T-10-14-04 | Repudiation | a single-season figure judged against the six-season bar | high | mitigate | the action forbids the comparison explicitly and the ledger entry must label the figure single-season with the reason and the unit cost of … | closed |
| T-10-14-05 | Repudiation | a candidate's result lost from the record | high | mitigate | the verify asserts all seven gate files exist and that the 6-season run set equals the mechanically-computed advance set exactly; the resul… | closed |
| T-10-15-01 | Tampering | a season-aggregate per-90 figure used as if it were pre-mat… | high | mitigate | the limitation is stated in a code comment, in a dedicated `## Leakage limitation` README section (verify-enforced, including the literal `… | closed |
| T-10-15-02 | Tampering | a guessed FBref export header mapping producing wrong-colum… | high | mitigate | `_MANUAL_KEEP_COLS` is derived from a real downloaded file's verbatim header row and recorded in the SUMMARY; a missing source column raise… | closed |
| T-10-15-03 | Tampering | name-match false positives attributing another player's def… | high | mitigate | resolution goes through `data.id_crosswalk.resolve_by_name` only (its `fbref_key` tier exists for exactly this source), a duplicate `(seaso… | closed |
| T-10-15-04 | Legal/compliance | committing FBref-derived content | medium | mitigate | the README records the source, the manual export method and Sports Reference's terms on manual export; only the reduced per-90 columns are … | closed |
| T-10-15-05 | Repudiation | a dropped item left as an unexplained absence | medium | mitigate | a Drop is recorded as a declined-on-cost decision with the FotMob +1/season prior quoted, following the `capt_mc` recorded-non-decision pre… | closed |
| T-10-15-06 | Repudiation | an RL revisit repeating the rejected raw-additive shaping d… | medium | mitigate | the note records the correction explicitly (potential-based only, net points keep weight 1) with the Ng et al. 1999 guarantee and the price… | closed |
| T-10-16-01 | Repudiation | mixing a one-season signal into a six-season average and re… | high | mitigate | D-11's split rule is enforced by a verify asserting `availability_flags` is absent from the combined run's flag set, whatever its own verdi… | closed |
| T-10-16-02 | Tampering | a default flipped without its pre-declared criterion being … | critical | mitigate | the adopting set is derived from the recorded ledger verdicts; every flipped flag must be named in the updated `test_experiments_registry_d… | closed |
| T-10-16-03 | Tampering | flipping `availability_flags` without D-10's safe fallback … | critical | mitigate | the fallback test is run as this task's first verify and the action forbids the flip without it | closed |
| T-10-16-04 | Tampering | a training-time feature key leaking into the public product… | high | mitigate | a verify greps every `web/data/*.json` payload for `av_`/`tm_`/`nw_`/`bracket_` keys and fails on any hit; `tests/test_product.py` locks it… | closed |
| T-10-16-05 | Repudiation | an adopted flag that is silently inert | high | mitigate | a real `python -m predict.export` run plus a `git diff --stat web/data` check: an adoption whose exported values do not move is reported as… | closed |
| T-10-16-06 | Repudiation | a decision or todo left with no recorded outcome | high | mitigate | verifies assert a row for every D-01..D-21 and a named resolution for every one of the eight `resolves_phase: 10` todos, plus a zero unfill… | closed |
| T-10-16-07 | Tampering | a scoped ledger edit destroying a prior phase's record | high | mitigate | a verify asserts every Phase A-F anchor still exists, including Phase 9's own decisions-audit and did-not-resolve headings | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Open threat detail

- **T-10-13-06 (medium, non-blocking):** "units consumed and remaining are recorded per candidate" was never satisfied — `bracket_gate_rnn.json` and `bracket_gate_transformer.json` carry `colab_units_consumed: null` / `colab_units_remaining: null`; the human's Colab session did not surface the figure, so D-13's 200-unit hard stop is not reconcilable from the record. Partially compensated: the absence is explicitly recorded as "not reported" (never assumed zero) in IMPROVEMENTS.md's D-13 compute-accounting paragraph and 10-14-SUMMARY.md, with per-candidate GPU wall clock (3.3s / 19.5s) showing the budget was never near-binding.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-10-01 | T-10-01-04 | `elements[].news` is public FPL editorial copy — no PII/confidentiality exposure in snapshotting it | plan 10-01 threat register (developer) | 2026-09-10 |
| AR-10-02 | T-10-03-05 | catchup re-run bounded to one bootstrap GET per UTC day by the snapshot idempotency guard — DoS surface negligible | plan 10-03 threat register (developer) | 2026-09-10 |
| AR-10-03 | T-10-04-04 | availability coverage report discloses only aggregate counts of public data | plan 10-04 threat register (developer) | 2026-09-10 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Flags (carried forward — no threat ID covers these yet)

Recorded by the 2026-09-12 audit; register these before the next phase that touches the named surface:

1. **Colab bundle exports ground truth for the test season.** `models/bracket/registry.py:152,161-168` writes `y=`/`minutes=` into `<season>_tensors.npz` for the union of every split season — including 2025-26 — so the bundle leaves the machine carrying real `y_points` (T-10-13-04 assumed the opposite). Contained today (ingest strips and re-joins truth locally per T-10-09-02; implausibility gate T-10-09-01 fires on contamination; data is public FPL scoring), but any future external-trainer handoff inherits a live test-season-label leakage surface.
2. **A test writes to the live experiments directory.** `tests/test_bracket.py::test_granularity_bracket_writes_gate_schema` runs `run_granularity_bracket` without monkeypatching `config.EXPERIMENTS_DIR`, so every `pytest -q` overwrites the real `bracket_gate_mlp.json` and both `bracket_search_mlp_*.json` with a toy `max_epochs=1` result (documented in 10-13-SUMMARY.md and WINDOWS.md, deliberately unfixed). Same class as T-10-01-06 / T-10-03-02, which the register does cover for `data/snapshots/`.
3. **10-15's declared mitigations were never built.** T-10-15-01/02/03 closed by vector absence (no FBref manual join exists, `fbref_v2` off) — not by the named artifacts (no `## Leakage limitation` README section, no `_MANUAL_KEEP_COLS`, no duplicate-`(season, player_code)` guard). Any future plan reviving the FBref manual join inherits three unmitigated high-severity threats and must build these first.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-12 | 94 | 93 | 1 (medium, non-blocking) | gsd-security-auditor (opus), ASVS L1, block_on high — verified against post-code-review-fix tree (commits 2f27a7a..11e7e6b); 85 targeted tests executed |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed (T-10-13-06 open below the `high` block threshold)
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-12
