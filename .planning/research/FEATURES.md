# Feature Research

**Domain:** FPL (Fantasy Premier League) prediction/optimization web product — team/pitch views, stat tables, and the production-readiness bar for a small paid API
**Researched:** 2026-08-31
**Confidence:** MEDIUM (competitor feature sets corroborated across multiple independent listings/app-store descriptions; exact FPL shirt-CDN URL pattern is LOW-confidence/unverified — see Gaps; production-readiness and CI practices are well-established industry consensus, MEDIUM-HIGH)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist on any FPL tool site in 2026. Missing these makes the product feel unfinished next to FFScout, LiveFPL, FPL Review, and Fantasy Football Fix, or feel un-FPL-like next to the official app.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Pitch view with formation layout (GK back, then DEF/MID/FWD rows, bench below) | Every FPL tool and the official app render the squad this way; it's the domain's universal mental model | MEDIUM | Formation is data-driven (e.g. 3-4-3, 4-4-2) — layout must recompute rows from squad composition, not hardcode 11 slots |
| Captain (C) and vice-captain (VC) badges on player cards in pitch view | Doubling/vice-fallback is core FPL scoring; every tool marks this visually (small circular badge, top-right or corner of shirt) | LOW | Existing `squad.json`/`captains.json` already carry this data — purely a rendering concern |
| Player price + predicted points (xP) shown on/near each pitch card | FFScout's pitch-first "Today"/"My Team" screens rate the team by xP and fixture difficulty directly on the pitch; users expect price and points at a glance without a click | LOW-MEDIUM | Your `xp_table.json` already has price_m + xp; needs a compact card layout (name, price, xP, form badge) |
| Official-look shirts (not generic dots/initials) | The official app and every polished third-party tool use real kit imagery; generic placeholder icons read as "unfinished MVP" | MEDIUM | See licensing note below — use PL's own kit images or neutral generated kits, never redrawn crests |
| Sortable, filterable player/stat tables (by position, team, price, xP, ownership, form) | This is the single most-used feature across FFScout, LiveFPL, FPL Review, Fantasy Football Fix — the "big table" is the product for power users | MEDIUM | Existing vanilla site's xP table already does this; React rebuild must preserve column sort + filter chips, not regress |
| Fixture Difficulty Rating (FDR) ticker, color-coded 1–5 (green→red) | Universal convention (FFScout, premierfantasytools, fpl.page, fplcopilot, fpltactics) — a team-rows × GW-columns grid, each cell colored by difficulty and labeled opponent + H/A | LOW-MEDIUM | You already emit `fixtures.json` for a 6-GW ticker; must match the standard green/grey/orange/red convention users already recognize |
| Mobile responsiveness for pitch + tables | FFScout's own tool is "pitch-first" specifically because most usage is mobile around deadline time; official app is mobile-first | MEDIUM | Pitch view is the harder responsive case (needs to reflow shirts without overlap on narrow screens); tables need horizontal scroll or column priority collapse |
| Rate-my-team view (squad xP vs optimal, suggested swaps) | FPL Review, Fantasy Football Fix ("Fix Rivals"), FFScout, and your own `/api/rate` endpoint all treat this as core, not a bonus | MEDIUM | Already implemented server-side (`/api/rate/{entry}`); the React rebuild's job is a good visual diff of "your team" vs "optimal" |
| Price-change watchlist / predictor | Fantasy Football Fix's Price Change Predictor and FFScout's Price Predictions page are both flagship, high-traffic features; your `models/price.py` already produces this data | LOW | Mostly a table/badge UI on top of existing watchlist output — rising/falling arrows, "predicted tonight/tomorrow/later this week" granularity is the current bar to match |
| Deadline countdown / next-GW meta banner | Every FPL tool surfaces "GW N deadline in Xh" prominently — it's the anxiety-driven return trigger | LOW | `meta.json` already has gameweek/deadline; needs a persistent header component |

### Differentiators (Competitive Advantage)

Features that set this product apart. Should align with Core Value (trustworthy, always-on weekly recommendations from a real ML model, not a heuristic).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| ILP-solved squad/transfer optimizer with explicit constraints (locks, excludes, chip mode, multi-GW horizon) | Most competitors (FPL Review, Fantasy Football Fix) use heuristics or simpler greedy/LP models advertised as "leading predicted points model" without transparency; a real two-stage hurdle model + PuLP ILP with p10/p90 intervals is a genuine technical edge worth surfacing in the UI (e.g. "why this pick" explanations, confidence bands) | HIGH (already built server-side) | UI work: expose intervals (p10/p90) as a range/error-bar on player cards or captain picks — most competitor UIs show a single point estimate, not a distribution |
| Scoreboard / accuracy transparency page (MAE + rank vs FPL's own ep_next, historical) | Nobody in the competitor set publicly grades their own predictions against reality gameweek-by-gameweek; this builds trust that xP is calibrated, not marketing copy | LOW-MEDIUM | Already exists (`predict/scoreboard.py`, "scoreboard" page) — worth promoting as a differentiator in copy/positioning, not hiding it as a minor page |
| Differentials view with ownership-aware xP delta | LiveFPL has effective-ownership analysis; a differentials page ranking high-xP/low-ownership players is a known valued niche feature but not universal — you already have it | LOW (exists) | Preserve in rebuild; consider adding "rank-swing potential" framing to match LiveFPL's EO-based positioning |
| Chip timing recommendation (WC/FH/BB/TC) with DGW/BGW awareness | LiveFPL and FFScout both offer chip planners; yours is heuristic-driven off fixture structure — reasonable parity feature, could differentiate if paired with the multi-period ILP lookahead already in `optimize/multi_period.py` | MEDIUM | Already partially built; UI should visualize "why this GW" (DGW/BGW callout) rather than just a date |
| Email digest (weekly plain-text + HTML) | Not a common feature among the big four competitors, who are web/app-first; a low-cost owned channel (no app-store dependency, no push notification permission friction) is a real retention differentiator for a solo-dev product | LOW (exists) | Keep as differentiator messaging: "get your team news without opening an app" |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Custom-drawn/generic kit graphics per club, or scraped/redrawn club crests | Looks "more branded," seems easy to theme | PL club crests and kit designs are trademarked; unlicensed reproduction of crests/branding is a legal risk for a paid product, and hand-drawn "close enough" kits look cheap next to competitors using real kit art | Use the official FPL shirt-image resources (as the official app and FFScout-adjacent tools do) for player cards, and keep club identification to name/short-code text or the officially-sourced kit image only — do not recreate crests as custom logos |
| Real-time in-match live score ticker / live points during matches | LiveFPL and the official app do this and it's flashy | High complexity (websocket or polling infra, live FPL bonus-point provisional logic, autosub prediction during play) for a solo dev; this milestone's scope is explicitly a weekly/daily batch pipeline, not a real-time system — building this now risks destabilizing the "keep the pipeline reliable" core value | Ship the deadline countdown + post-GW scoreboard (batch) now; revisit live in-match tracking as a distinct future milestone only if there's demonstrated demand, decoupled from the daily/weekly cron architecture |
| Social/community features (mini-league chat, comments, forums) | Competitors like FFScout have large community/content sides | Massive scope creep for a solo-dev, pre-revenue product; moderation burden; distracts from the core value (reliable weekly recommendations) | Keep scope to personal team tools; if community demand emerges, link out to existing communities (Reddit r/FantasyPL, Discord) instead of building your own |
| Full historical "all seasons ever" browsable stats explorer in v1 of the React rebuild | Feels like "more data = more value" | Big surface area, most of it low-traffic; risks delaying the actual milestone goal (parity rebuild + hardening) for a feature nobody asked for yet | Preserve the existing scoreboard/history JSON contract (`history/gw{N}.json`) so it's available to build later, but don't add new historical UI in this milestone |
| Building a bespoke rate-limiting/auth system beyond the planned Supabase JWT swap point | Tempting to "just add it now" while touching the API | Explicitly out of scope this milestone (blocked on payment gateway decision); building it prematurely risks throwaway work if the auth model changes when Supabase JWT lands | Keep `require_key()` as the single swap point; for this milestone, add framework-level rate limiting (e.g. `slowapi`) by IP as a stopgap production-hardening item, not a full auth/subscription system |

## Feature Dependencies

```
[Pitch view formation layout]
    └──requires──> [Squad/XI JSON with formation-derived positions] (exists: squad.json)
                       └──requires──> [Player card component: shirt + name + price + xP]
                                          └──requires──> [Shirt image sourcing decision] (FPL CDN vs neutral kits)

[Captain/vice badges] ──enhances──> [Pitch view formation layout]

[Rate-my-team view] ──requires──> [Pitch view formation layout] (shows "your team")
                     ──requires──> [Sortable stat table] (shows "optimal swaps")

[FDR ticker] ──enhances──> [Sortable stat table] (fixture-run column)
[FDR ticker] ──enhances──> [Pitch view] (fixture difficulty overlay per player, per FFScout convention)

[Price-change watchlist] ──requires──> [models/price.py output] (exists, 14-day lockout already noted in PROJECT.md)

[API rate limiting] ──requires──> [Structured logging] (need request context to rate-limit sensibly and audit abuse)
[Health/readiness endpoints] ──enhances──> [CI Docker image publish step] (a real health check makes the published image verifiable, not just buildable)
[Schema validation on FPL payloads] ──requires──> [pydantic models for bootstrap-static / fixtures responses]
[API integration tests] ──requires──> [Schema validation] (tests are far more useful once responses are typed/validated, not ad hoc dict access)

[Playwright E2E: team/pitch + solver flow] ──requires──> [React pitch view] (can't E2E-test a UI that doesn't exist yet)
[Playwright E2E] ──enhances──> [FastAPI integration tests] (E2E catches integration gaps unit/API tests miss, but should not substitute for them — API tests are the missing base layer per PROJECT.md)
```

### Dependency Notes

- **Pitch view requires shirt image sourcing decision first:** This is a blocking design decision (per PROJECT.md, "resolve during UI design") — the formation-layout component and the player-card component both consume whatever image contract is chosen (official CDN URL per team+kit-type, or neutral SVG-generated kit). Resolve before building pitch-view components, not after.
- **Captain/vice badges enhance rather than block pitch view:** They're a rendering detail on top of the same player-card component; can be added in the same pass or a fast follow without re-architecting.
- **API rate limiting requires structured logging:** Rate-limiting decisions (per-IP vs per-key, threshold tuning) are much easier to validate and debug with structured request logs already in place — build logging first, or at minimum in the same phase.
- **Schema validation blocks meaningful API tests:** Testing against raw dict/JSON responses from FPL's API is brittle; typed pydantic response/request models make both the "graceful JSON-load failure" hardening item and the API test suite meaningfully easier — sequence schema validation before or alongside the API test suite phase, not after.
- **Playwright E2E depends on the React pitch view existing:** This is an ordering constraint already implicit in PROJECT.md's phase list — E2E for "team/pitch + solver flow" cannot be planned in detail until the pitch view's DOM/component structure is decided.

## MVP Definition

Given this is a brownfield **parity rebuild + hardening** milestone (not a net-new product), "MVP" here means the minimum slice needed to hit full parity plus the specific hardening asks in PROJECT.md — not a trimmed-down feature set.

### Launch With (v1 of this milestone)

- [ ] Pitch view with formation layout, shirts (official CDN or neutral kits — decision resolved first), captain/vice badges, price+xP overlay — table stakes, and it's an explicit Active requirement
- [ ] All 8 pages at parity (xP table, team, fixtures, prices, league, scoreboard, differentials, methodology) — explicit full-parity requirement, avoids maintaining two frontends
- [ ] Sortable/filterable stat tables preserved from the vanilla site — regression risk otherwise
- [ ] FDR ticker preserved with standard green→red convention — existing `fixtures.json` contract, just needs faithful rendering
- [ ] Mobile-responsive pitch + tables — table stakes for an FPL audience that checks teams on mobile before deadlines
- [ ] FastAPI integration test suite (`/solve`, `/rate`, `/team`, auth stub, cache, error responses) — explicitly called out as the missing base layer
- [ ] Playwright E2E for team/pitch + solver, xP table + captains, rate-my-team, fixtures/prices — explicit requirement
- [ ] CI: lint, pytest, API tests, Playwright, Docker build+publish (GHCR) — explicit requirement, no live deploy
- [ ] Security/config hardening: CORS restriction, pinned deps, `.env` secrets, repo hygiene — explicit requirement
- [ ] Reliability: fix file-handle leaks, remove `|| true` cron swallowing, add FPL schema validation, graceful JSON-load failure, solve-cache LRU/invalidation — explicit requirement
- [ ] Observability: structured logging, health/readiness endpoints, cron/FPL-outage alerting — explicit requirement
- [ ] Basic rate limiting (e.g. `slowapi`, per-IP) — currently "not implemented" per ARCHITECTURE.md; table stakes for a soon-to-be-paid API even pre-auth

### Add After Validation (v1.x — post this milestone, pre/at paid launch)

- [ ] Prediction interval (p10/p90) visualization on player/captain cards — differentiator, but not needed for parity; add once the base pitch view is solid
- [ ] Chip timing "why this GW" DGW/BGW explanatory UI — enhances existing heuristic feature
- [ ] Supabase JWT auth + payment webhooks — explicitly deferred, `require_key()` stays the swap point
- [ ] Live deploy automation (Cloudflare Pages / Hetzner) — explicitly out of scope this milestone

### Future Consideration (v2+)

- [ ] Real-time in-match live tracking (live points, provisional bonus during play) — explicit anti-feature for now, high infra complexity, revisit only with demonstrated demand
- [ ] Full historical multi-season stats explorer UI — data contract exists, UI deferred
- [ ] Community/social features — explicit anti-feature, scope creep for a solo dev

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Pitch view (formation, shirts, C/VC badges, price/xP) | HIGH | HIGH | P1 |
| 8-page parity rebuild in React | HIGH | HIGH | P1 |
| Sortable/filterable tables | HIGH | MEDIUM | P1 |
| FDR ticker | HIGH | LOW | P1 |
| Mobile responsiveness | HIGH | MEDIUM | P1 |
| API integration test suite | HIGH (trust/safety net) | MEDIUM | P1 |
| Playwright E2E suite | MEDIUM-HIGH | MEDIUM | P1 |
| CI (lint/test/Docker publish) | HIGH | MEDIUM | P1 |
| Security/config hardening (CORS, pinned deps, secrets) | HIGH | LOW-MEDIUM | P1 |
| Reliability fixes (leaks, cron traps, schema validation, cache LRU) | HIGH | MEDIUM | P1 |
| Structured logging + health endpoints | HIGH | LOW-MEDIUM | P1 |
| Basic rate limiting | MEDIUM-HIGH | LOW | P1 |
| Prediction intervals in UI | MEDIUM | LOW-MEDIUM | P2 |
| Price-change watchlist UI polish | MEDIUM | LOW | P2 |
| Chip-timing explanatory UI | LOW-MEDIUM | LOW | P2 |
| Docker image vulnerability scan (Trivy) in CI | MEDIUM (security posture, cheap to add) | LOW | P2 |
| Dark mode | LOW-MEDIUM (nice-to-have polish, not called out as a requirement) | LOW-MEDIUM | P2 |
| Live in-match tracking | MEDIUM (long-term) | HIGH | P3 |
| Historical stats explorer UI | LOW-MEDIUM | MEDIUM | P3 |
| Community/social features | LOW (not aligned with core value) | HIGH | P3 |

## Competitor Feature Analysis

| Feature | FFScout (Plan FPL) | LiveFPL | FPL Review | Fantasy Football Fix | Official FPL App | Our Approach |
|---------|--------------------|---------|------------|-----------------------|-------------------|--------------|
| Pitch view | Pitch-first Today/My Team screens; live points, captain impact, provisional bonus, predicted autosubs | Not primary focus (rank/live-battle focused) | Table/planner-focused, less pitch-centric | Live team reveals, "Fix Rivals" squad comparisons | Canonical pitch view (source of the convention) | Pitch view as primary team/solver surface, matching official conventions (formation rows, C/VC badges) |
| Fixture ticker (FDR) | Yes, integrated into Transfer Planner | Yes, ticker + planner | Yes | Not primary but referenced alongside price tools | Basic FDR in "Fixtures" tab | Preserve existing `fixtures.json`-driven ticker, standard green→red scale |
| Transfer/squad optimizer | Predicted-points-driven planner, not a full ILP | Chip/rotation planner, not disclosed as ILP | "Leading predicted points model" + LP-style solver (per third-party descriptions) | Draft planner (up to 5 team drafts) + chip strategy | None (manual only) | Real two-stage hurdle model + PuLP ILP with p10/p90 intervals — genuine technical differentiator, worth surfacing transparently |
| Rate-my-team / rival comparison | Implicit via pitch rating | "Live Battle" vs rivals/leagues | Rate My FPL Team (via ecosystem, e.g. FPL Copilot) | "Fix Rivals" detailed comparisons | None | `/api/rate/{entry}` — already built; needs a clear visual diff UI |
| Price-change prediction | Price Predictions page | Price-change predictions ("best accuracy in market" — marketing claim, unverified) | Referenced as a differentiator by others | Flagship feature, push notifications, granular timing (tonight/tomorrow/later) | Basic transfer-value info only | `models/price.py` watchlist exists; match Fix's granularity bar (rising/falling + rough timing) in UI, no push notifications needed for v1 |
| Prediction transparency / scoreboard | Not publicly emphasized | Not publicly emphasized | Marketing claims "leading" without public grading shown | Not publicly emphasized | N/A | Public scoreboard (MAE + rank vs FPL's own ep_next) — differentiator none of the big four visibly do |
| Email/owned channel | Unclear (app + web focus) | App-focused | Web-focused | App-focused, push notifications | N/A | Weekly digest email — low-cost differentiator, no app-store gatekeeping |
| Live in-match tracking | Yes (live points/bonus/autosubs) | Yes, core feature (live rank) | Not primary | Yes (live team reveals) | Yes (native) | Deliberately deferred (anti-feature for this milestone) — batch pipeline architecture doesn't support it without new real-time infra |

## Production-Readiness Checklist (Small Paid API Product)

Distinct from user-facing features, this is the non-negotiable engineering bar for a small paid FastAPI product, synthesized from current industry practice (2026) and cross-referenced against the existing `CONCERNS.md`/`ARCHITECTURE.md` gaps:

| Item | Table Stakes? | Current State (per ARCHITECTURE.md) | Complexity |
|------|----------------|--------------------------------------|------------|
| Liveness + readiness health endpoints (distinct semantics: liveness = process up; readiness = dependencies OK, e.g. model loaded, FPL API reachable) | Yes | `GET /api/health` exists but check whether it distinguishes liveness vs readiness — likely needs upgrade to return 503 when pool/model isn't ready | LOW-MEDIUM |
| Structured (JSON) logging with request/correlation IDs | Yes | Currently `print()` statements only, no library logger — explicit gap | MEDIUM |
| Config validation via pydantic-settings (fail fast on missing/malformed env vars) | Yes | Not mentioned as existing; `.env` pattern is planned but validation layer isn't specified | LOW-MEDIUM |
| Rate limiting (per-IP or per-key) | Yes, even pre-auth (protects against scraping/abuse of a compute-heavy `/solve` endpoint) | Explicitly "not implemented" | LOW (e.g. `slowapi` middleware) |
| Schema validation on external API payloads (FPL bootstrap-static/fixtures) | Yes | Explicit gap in CONCERNS.md — "no schema validation on FPL payloads" | MEDIUM (pydantic models for the FPL response shapes) |
| CORS restricted to known origins | Yes | Explicit gap — "wide-open CORS" | LOW |
| Pinned/locked dependencies | Yes | Explicit gap — "unpinned deps" | LOW |
| Secrets via `.env`, never committed | Yes | Planned | LOW |
| Bounded/LRU cache with invalidation (not unbounded growth) | Yes | Explicit gap — "unbounded solve cache" | MEDIUM |
| Graceful degradation on load/parse failure (no silent crash, no silent bad data) | Yes | Explicit gap — "graceful JSON-load failures" needed | LOW-MEDIUM |
| Monitoring/alerting for cron failures and FPL API outages | Yes | Explicit gap — "no monitoring"; cron currently swallows errors via `\|\| true` | MEDIUM |
| Container image vulnerability scanning (e.g. Trivy) in CI | Yes, cheap insurance | Not yet built (CI is new this milestone) | LOW (single CI step, free tier via GitHub Actions) |
| API integration test coverage (auth stub, caching, concurrency, error paths) | Yes | Explicit gap — zero coverage today | MEDIUM-HIGH |

## Sources

- [Members Benefits - Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/benefits)
- [How to use the Members Area - Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/how-to-use-the-members-area)
- [Get the new and upgraded Fantasy Football Scout app](https://www.fantasyfootballscout.co.uk/2026/07/24/get-the-new-and-upgraded-fantasy-football-scout-app-today)
- [LiveFPL Rank](https://www.livefpl.net/)
- [LiveFPL Transfer Planner](https://plan.livefpl.net/ticker)
- [Best FPL Tools for 2026/27 - FPL Pulse](https://www.fplpulse.com/blog/best-fpl-tools)
- [FPL Fixture Difficulty Ticker (FDR) 2026/27 - Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl/ticker)
- [How the Fixture Difficulty Ratings help FPL managers - Premier League](https://www.premierleague.com/en/news/68553)
- [FPL Review - Projections, Planner & Solver](https://fplreview.com/)
- [Fantasy Premier League toolbox - Fantasy Football Fix](https://www.fantasyfootballfix.com/web_features/)
- [FPL Price Change Predictor Announced for 2026/27 - Fantasy Football Fix](https://www.fantasyfootballfix.com/blog-index/fpl-2026-27-player-price-changes/)
- [What is an FPL captain and how do I choose one? - Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2025/07/21/what-is-an-fpl-captain-and-how-do-i-choose-one)
- [FPL basics explained: Managing your team - Premier League](https://www.premierleague.com/en/news/2174899/fpl-basics-managing-your-team)
- [New Year, New FPL team badge! - Premier League](https://www.premierleague.com/en/news/4362141/whats-new-in-202526-fantasy-team-badges)
- [Building Production-Ready APIs with FastAPI in 2026 - DEV Community](https://dev.to/apaksh/building-production-ready-apis-with-fastapi-in-2026-the-complete-playbook-5hlb)
- [How to Build Production-Ready FastAPI Applications - OneUptime](https://oneuptime.com/blog/post/2026-01-26-fastapi-production-ready/view)
- [Production-Grade Logging for FastAPI Applications - Medium](https://medium.com/@laxsuryavanshi.dev/production-grade-logging-for-fastapi-applications-a-complete-guide-f384d4b8f43b)
- [FastAPI production deployment best practices - Render](https://render.com/articles/fastapi-production-deployment-best-practices)
- [Setting up the Docker image scan GitHub Action - Snyk](https://snyk.io/blog/docker-image-scan-github-action/)
- [How to Set Up Container Scanning in GitHub Actions - OneUptime](https://oneuptime.com/blog/post/2025-12-20-container-scanning-github-actions/view)
- [Container Security: GitHub Actions Image Scanning Tools - Medium](https://medium.com/@anshumaansingh10jan/container-security-a-complete-overview-of-github-actions-integrated-image-scanning-tools-832e6406ec23)
- Internal: `/home/sraja/fpl/.planning/PROJECT.md`, `/home/sraja/fpl/.planning/codebase/ARCHITECTURE.md` (existing product surface, JSON export contract, CONCERNS.md gap list referenced therein)

**Gap note (LOW confidence):** The exact CDN URL pattern the official FPL app uses for shirt images (e.g. a `resources.premierleague.com/.../shirts/...png` path with kit-type/team-code parameters) could not be confirmed via web search — only that the official app and FFScout's tooling source shirt imagery from Premier League-hosted resources rather than custom art, and that away kits are explicitly made public by the PL for this purpose. **Resolve this with direct inspection of the official FPL app's/site's network requests (view-source or devtools on fantasy.premierleague.com's My Team page) before committing to a shirt-image strategy in the UI design phase** — do not build against a guessed URL pattern.

---
*Feature research for: FPL prediction/optimization web product (team/pitch views, stat tables, production-readiness bar)*
*Researched: 2026-08-31*
