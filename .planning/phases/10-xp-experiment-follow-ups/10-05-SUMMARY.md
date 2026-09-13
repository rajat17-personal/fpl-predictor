---
phase: 10-xp-experiment-follow-ups
plan: 05
subsystem: data
tags: [scraping, requests, pandas-read-html, transfermarkt, access-probe, figshare]

# Dependency graph
requires:
  - phase: 10-xp-experiment-follow-ups
    provides: "10-01's IMPROVEMENTS.md Phase 10 provenance table skeleton (this plan fills its Transfermarkt row)"
provides:
  - "data/transfermarkt.py: figshare shortcut check + a bounded 8-page real access probe + one-page injury-table parser"
  - "A measured, evidenced go/no-go decision authorising plan 10-07's full 2016-17+ backfill scope"
  - "IMPROVEMENTS.md Phase 10 provenance table's Transfermarkt and figshare rows, now measured facts not assumptions"
affects: [10-07, transfermarkt_injury experiment, data/id_crosswalk]

# Actuals (#2632)
actuals:
  tokens: 7148
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bounded access-probe-before-build discipline (Phase 9 fbref_v2 precedent), applied to a second unofficial source"
    - "Anti-bot interstitial detection raises ValueError naming the marker rather than parsing to a misleadingly-empty frame"

key-files:
  created:
    - data/transfermarkt.py
    - tests/test_transfermarkt.py
  modified:
    - IMPROVEMENTS.md

key-decisions:
  - "Figshare pre-scraped injury dataset verdict: INSUFFICIENT — absent from figshare's own search API (only 2 unrelated hits); every ndownloader download WAF-challenged (HTTP 202, x-amzn-waf-action: challenge)"
  - "Real 8-page Transfermarkt probe: 7/8 ok, 0 challenged, 1 id_unresolved (name-resolution gap, not an access block) — access is mostly-open, measured not assumed"
  - "Developer go/no-go decision (verbatim): A — full backfill (D-06 as written), all seasons 2016-17+, background killable job"

patterns-established:
  - "Two-plan spike-first contract for unofficial scraping sources: probe module ships alone first, bulk build only after a blocking-human checkpoint authorises scope"

requirements-completed: [TODO-TM-INJURY]

coverage:
  - id: D1
    description: "Figshare pre-scraped injury dataset checked via its public search API before any scraper code was written; verdict INSUFFICIENT recorded with evidence"
    requirement: TODO-TM-INJURY
    verification:
      - kind: unit
        ref: "python -m data.transfermarkt --figshare-check"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real 8-page probe against transfermarkt.com from this machine; anti-bot interstitial detection provably raises instead of parsing to an empty frame"
    requirement: TODO-TM-INJURY
    verification:
      - kind: unit
        ref: "tests/test_transfermarkt.py::test_parse_injury_table_on_saved_fixture, test_parse_injury_table_raises_on_challenge_page, test_probe_records_verdict_per_page_without_raising"
        status: pass
      - kind: integration
        ref: "python -m data.transfermarkt --probe --n 8 (real run, 7/8 ok)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Go/no-go decision on plan 10-07's Transfermarkt backfill scope, made against measured evidence and a computed wall-clock projection"
    requirement: TODO-TM-INJURY
    verification:
      - kind: manual_procedural
        ref: "checkpoint:decision Task 3, developer answered verbatim 'A'"
        status: pass
    human_judgment: true
    rationale: "Blocking-human decision by design (gate=blocking-human) — the choice among full backfill / reduced-season / figshare substitute / not-acquirable requires the developer's own judgment on wall-clock cost vs. value, not something automation can resolve"

duration: 17min
completed: 2026-09-10
status: complete
---

# Phase 10 Plan 05: Transfermarkt Access Probe Summary

**Measured (not assumed) that Transfermarkt's injury pages are mostly reachable with plain `requests` (7/8 real pages parsed), ruled out the figshare pre-scraped alternative as INSUFFICIENT, and got a blocking-human go decision (Option A) authorising plan 10-07's full 2016-17+ backfill.**

## Performance

- **Duration:** 17 min (bed178e to 64b0a8f)
- **Started:** 2026-09-10T13:09:19Z
- **Completed:** 2026-09-10T13:26:31Z
- **Tasks:** 3
- **Files modified:** 3 (`data/transfermarkt.py`, `tests/test_transfermarkt.py`, `IMPROVEMENTS.md`)

## Accomplishments

- **Figshare shortcut checked before any scraper code was written.** `--figshare-check` searched figshare's public API for the "Injuries from Transfermarkt.com" dataset 10-RESEARCH.md A5 cites: it does not exist there (only 2 unrelated hits), and every `ndownloader.figshare.com` file download attempted returned HTTP 202 with an `x-amzn-waf-action: challenge` header (an AWS WAF JS challenge plain `requests` cannot clear). Verdict: **INSUFFICIENT**. An earlier false `USABLE` reading during development was caught and fixed as a Rule-1 bug before the Task 1 commit (bed178e).
- **A real 8-page access probe ran against transfermarkt.com from this machine** (plain `requests` + a Chrome `User-Agent`, `_MIN_INTERVAL_S=3.0`): **7/8 pages `ok`** (HTTP 200, 1-15 real injury-spell rows parsed per page), 0 `challenge`, 0 `http_error`, 0 `parse_error`, 1 `id_unresolved` (B.Fernandes — FPL's abbreviated display name fails Transfermarkt's own search endpoint; a name-resolution gap for 10-07 to fix, not an access block). The verbatim served column headers — `Season, Injury, from, until, Days, Games missed` — exactly confirm 10-RESEARCH.md's Assumption A4.
- **An anti-bot interstitial provably raises rather than parsing to a misleading empty frame** (`T-10-05-01` mitigation): `parse_injury_table` scans for `Just a moment`, `DataDome`, `captcha-delivery`, `Attention Required` and raises `ValueError` naming the detected marker, proven by a dedicated offline test.
- **The projected full-scope backfill wall clock was computed explicitly**, not estimated: **2,623 distinct `player_code` values** across seasons 2016-17..2025-26 in `data/processed/player_gw.parquet`, one profile-page fetch per player at `_MIN_INTERVAL_S=3.0`s ≈ **2.19h**, plus one search-endpoint fetch per player for `tm_player_id` resolution ≈ 2.19h more — **≈4.4h total**, rate-limit-bound wall clock for a background killable job.
- **Developer go/no-go decision recorded verbatim: "A"** — Option A, full backfill (D-06 as written): all seasons 2016-17+, background killable job. Plan 10-07 is authorised to build at this full scope; Option B (reduced seasons) and Option C (figshare substitute, unavailable since the figshare verdict was INSUFFICIENT not USABLE) do not apply.
- IMPROVEMENTS.md's Phase 10 provenance table now carries measured facts (not "unverified") for both Transfermarkt and the figshare dataset, plus a new `### transfermarkt_injury: go/no-go decision` subsection recording the full evidence chain and the verbatim decision for 10-07 to read directly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Check figshare pre-scraped dataset before writing any scraper** - `bed178e` (feat)
2. **Task 2: Bounded real-page access probe and one-page parser** - `c00797a` (feat)
3. **Task 3: Go/no-go on the Transfermarkt backfill (checkpoint:decision, resolved)** - `64b0a8f` (docs)

**Plan metadata:** (this commit) - `docs: complete plan`

## Files Created/Modified

- `data/transfermarkt.py` - Module constants (`TRANSFERMARKT_ENABLED`, `HEADERS`, `TIMEOUT`, `_MIN_INTERVAL_S=3.0`, `_RAW_DIR`, `_OUT`), `_throttle`, `--figshare-check` (Task 1), `_fetch_page`, `parse_injury_table`, `probe`, `--probe`/`--n` (Task 2). No `build()`, no bulk loop, no `attach()` — that is 10-07's, only if authorised (it now is).
- `tests/test_transfermarkt.py` - Three offline tests: parse on a saved fixture, raise on a challenge-page body, and probe-never-raises under a total-block monkeypatch.
- `IMPROVEMENTS.md` - Phase 10 provenance table's Transfermarkt row (measured mostly-open access) and figshare row (corrected to INSUFFICIENT, superseding the earlier Phase 9 "403" reading); new `### transfermarkt_injury: go/no-go decision — Option A, full backfill authorised` subsection with the full evidence chain and the verbatim developer decision.

## Decisions Made

- **Figshare verdict: INSUFFICIENT** (not USABLE, not UNREACHABLE) — the dataset itself is absent from figshare's search API; the WAF-challenge behavior is a separate, secondary finding on top of that absence.
- **Access verdict: mostly-open** — 7/8 real pages parsed with real data; the one failure (`id_unresolved`) is a name-matching gap in this probe's ad-hoc Transfermarkt-search lookup, not a block, and is explicitly flagged for 10-07 to address (likely via a `_NAME_FIXUPS`-style override, following `data/id_crosswalk.py`'s existing three-tier pattern).
- **Go/no-go: A — full backfill, all seasons 2016-17+**, per the developer's verbatim answer. The computed ≈4.4h wall clock was judged acceptable as a background killable job.

## Deviations from Plan

None - plan executed exactly as written. (Tasks 1-2's own deviations, including the figshare false-`USABLE` Rule-1 bug fix, were already documented in their respective task commits by the prior executor session; no new deviations occurred in Task 3.)

## Issues Encountered

None in Task 3. The one substantive finding from Task 2 — the `id_unresolved` case for abbreviated FPL display names (e.g., "B.Fernandes") against Transfermarkt's search endpoint — is not a bug in this plan's scope; it is explicitly named in IMPROVEMENTS.md as a task for plan 10-07's own id-resolution work.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 10-07 is authorised to build the full 2016-17+ Transfermarkt injury backfill: fetcher/cache/normalization/join, using `data/transfermarkt.py`'s `_fetch_page`/`parse_injury_table` as its foundation, resolving the B.Fernandes-style name gap through `data.id_crosswalk.resolve_by_name` (never a second matcher), and budgeting ≈4.4h of rate-limit-bound wall clock as a background killable job.
- `data/transfermarkt.py` still has zero `build()`/bulk-loop/`attach()` code — 10-07 builds that, not this plan.
- No blockers for 10-07 beyond the id-resolution gap already flagged.

## Self-Check: PASSED

All claimed files and commits verified present:
- `data/transfermarkt.py`, `tests/test_transfermarkt.py`, `10-05-SUMMARY.md`, `data/processed/experiments/transfermarkt_probe.json` — FOUND
- Commits `bed178e`, `c00797a`, `64b0a8f` — FOUND in git log

---
*Phase: 10-xp-experiment-follow-ups*
*Completed: 2026-09-10*
