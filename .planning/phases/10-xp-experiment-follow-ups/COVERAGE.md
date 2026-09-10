# Phase 10 — External API Coverage Matrix

**Decided:** 2026-09-10 (plan time)
**Rule:** `INTEGRATE` is the default. This table is the *subtraction record* — every
`OPT-OUT` carries a one-line reason. A second integration against the same need
re-starts from full coverage.

This phase integrates six external surfaces: the official FPL API (new endpoints),
FPL-Core-Insights (GitHub raw CSVs), Transfermarkt (injury history), figshare (a
possible pre-scraped substitute), GDELT DOC 2.0 + Guardian Open Platform
(D-02-conditional), and fplreview (manual-only, ToS-constrained).

## FPL API — `https://fantasy.premierleague.com/api`

| capability | decision | reason |
|---|---|---|
| `leagues-classic/{id}/standings/?page_standings=N` | INTEGRATE | top-100 consensus benchmark (plan 10-02) |
| `entry/{id}/event/{gw}/picks/` | INTEGRATE | per-manager picks → consensus ownership ranking (plan 10-02) |
| `bootstrap-static/` `elements[].status` | INTEGRATE | already captured by `data/snapshot.py::_ELEMENT_COLS` |
| `bootstrap-static/` `elements[].chance_of_playing_next_round` | INTEGRATE | already captured; the tracer's first availability feature |
| `bootstrap-static/` `elements[].chance_of_playing_this_round` | INTEGRATE | added to `_ELEMENT_COLS` in plan 10-01 |
| `bootstrap-static/` `elements[].news` | INTEGRATE | added to `_ELEMENT_COLS` in plan 10-01 (days-since-news feature) |
| `bootstrap-static/` `elements[].news_added` | INTEGRATE | added to `_ELEMENT_COLS` in plan 10-01 (news recency timestamp) |
| `bootstrap-static/` `events[].deadline_time` | OPT-OUT | not needed — deadlines derive offline from `player_gw.parquet`'s own `kickoff_time` (first kickoff − 90 min), keeping the availability build network-free |
| `event/{gw}/live/` | INTEGRATE | already integrated (`predict/scoreboard.py::fetch_actuals`) |
| `entry/{id}/history/` | OPT-OUT | not needed — consensus ownership needs per-GW picks, not a manager's season history |
| `element-summary/{id}/` | OPT-OUT | not needed here — already covered by `data/live_history.py` |
| `fixtures/` | OPT-OUT | not needed — kickoff times already live in `player_gw.parquet` |
| `my-team/{id}/`, `transfers/`, any authenticated endpoint | OPT-OUT | explicitly out of scope — this phase adds no user-authenticated surface |

## FPL-Core-Insights — `raw.githubusercontent.com/olbauday/FPL-Core-Insights`

| capability | decision | reason |
|---|---|---|
| `LICENSE` / `LICENSE.md` root file | INTEGRATE | RESEARCH Open Question 1 — license posture gates the commit (plan 10-06) |
| per-GW playerstats CSV, season `2025-2026` | INTEGRATE | the D-05 vendored historical availability provider (plan 10-06) |
| GitHub contents API directory listing | INTEGRATE | needed to enumerate the per-GW folders (mirrors `benchmark_external.py::_list_gw_files`) |
| cumulative season-level playerstats table | OPT-OUT | not needed — only the per-GW frozen folders carry the as-of semantics the leakage rule requires |
| season dirs `2024-2025`, `2026-2027` | OPT-OUT | explicitly out of scope — D-05 scopes the backfill to 2025-26 only |
| any non-playerstats table in the repo (fixtures, teams, understat mirrors) | OPT-OUT | not needed — the availability columns are the whole point of this vendoring |

## Transfermarkt — `https://www.transfermarkt.com`

| capability | decision | reason |
|---|---|---|
| player injury-history page `/…/verletzungen/spieler/{tm_id}` | INTEGRATE | the D-06 injury-spell source (plans 10-05, 10-07) |
| player search / ID resolution (name → `tm_player_id`) | INTEGRATE | needed once per `player_code`, then cached (RESEARCH Pattern 3) |
| suspensions / bans page | OPT-OUT | not needed yet — D-06 scopes this source to injury spells |
| transfer history / market value / squad pages | OPT-OUT | explicitly out of scope — no valuation or transfer feature in this phase |
| any POST / authenticated surface | OPT-OUT | explicitly out of scope — read-only public pages only |

## figshare — pre-scraped Transfermarkt injuries dataset

| capability | decision | reason |
|---|---|---|
| dataset landing page + download link probe | INTEGRATE | RESEARCH Open Question 2 — a bounded check that could remove the scraper entirely (plan 10-05 Task 1) |
| figshare public API (`api.figshare.com/v2/articles/{id}`) | INTEGRATE | fallback path for the same check when the download link 403s |
| any other figshare dataset | OPT-OUT | not needed — one specific dataset is being checked |

## GDELT DOC 2.0 — `https://api.gdeltproject.org/api/v2/doc/doc` (D-02-conditional)

| capability | decision | reason |
|---|---|---|
| `mode=artlist` (article list + timestamps + doc counts) | INTEGRATE | doc-count feature + the article-timestamp leakage assertion (plan 10-12) |
| `mode=timelinetone` (pre-computed tone series) | INTEGRATE | the mean-tone feature — no sentiment model needed (todo's own scoping) |
| `mode=tonechart` | OPT-OUT | not needed — `timelinetone` already yields the per-window mean the feature uses |
| GDELT GKG v2 / BigQuery export | OPT-OUT | not needed — DOC 2.0's tone is already pre-computed server-side and keyless |
| `gdeltdoc` pip client | OPT-OUT | not needed — plain `requests` matches this project's no-wrapper fetcher convention and avoids a new dependency + package gate |

## Guardian Open Platform — `https://content.guardianapis.com` (D-02-conditional)

| capability | decision | reason |
|---|---|---|
| `/search` (query, `from-date`/`to-date`, `webPublicationDate`) | INTEGRATE | second sentiment source + timestamp-leakage proof (plan 10-12) |
| API-key auth via `.env` (`GUARDIAN_API_KEY`) | INTEGRATE | free developer key; loaded through the existing `config.load_dotenv()` pattern |
| `show-fields=body` (full article text) | OPT-OUT | not needed — D-02's method is doc-count + tone aggregation, never a text model |
| `/tags`, `/sections`, `/editions` | OPT-OUT | not needed — player-name search is the only entity path used |
| Guardian Content "Content API" paid tier | OPT-OUT | explicitly out of scope — solo dev, no new spend (CLAUDE.md budget constraint) |

## fplreview — `https://app.fplreview.com`

| capability | decision | reason |
|---|---|---|
| manual free-model projection table export (human download → `data/external/fplreview/`) | INTEGRATE | the Tier-3 diagnostic benchmark (plan 10-02) |
| automated projection fetch / scrape | OPT-OUT | explicitly out of scope — confirmed HTTP 403 to automated access (RESEARCH Pitfall 5) and their ToS blocks ingestion; manual capture only |
| redistribution of captured projections | OPT-OUT | explicitly out of scope — ToS forbids it; committed CSVs stay local-diagnostic and are never republished or fed to a model |
| fplreview paid tiers / API | OPT-OUT | explicitly out of scope — no new spend |

## fbrapi.com (FBref proxy, tail item)

| capability | decision | reason |
|---|---|---|
| liveness re-probe before the manual FBref path | OPT-OUT | not needed yet — probed 2026-09-09 and found half-down (TLS chain fails, no HTTP response); D-04 fixes acquisition as manual, so a re-probe buys nothing this phase |
| any FBref automated scrape | OPT-OUT | explicitly out of scope — Phase 9 recorded `fbref_v2` as not-acquirable after three real Chrome spikes; D-04 forbids new scraping infrastructure |
