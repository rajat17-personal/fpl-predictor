# Phase 2: Data Layer & Non-Pitch Pages - Research

**Researched:** 2026-09-01
**Domain:** React port of a hand-built vanilla JS site (7 pages) to behavioral parity — sort/filter/format semantics, cross-page chrome (GW banner, dark mode), zero-dependency parity verification
**Confidence:** HIGH (this phase's core risk is *not* an unfamiliar technology — it's silently porting a subtly-behaving vanilla algorithm wrong. Every claim below that concerns vanilla behavior was verified by reading the source or executing it, not by inference.)

## Summary

This phase has almost no "new technology" risk — React 19, React Router 7, TanStack Query 5, Tailwind 4, and the Phase 1 scaffold (`PageShell`, `ErrorState`/`EmptyState`/`Spinner`) are already installed and proven. The entire risk surface is **porting `web/assets/app.js` and seven inline `<script type="module">` blocks into React without changing their observable behavior** — sort comparators, `.toFixed()` calls, `??`/`?.` fallback chains, and conditional CSS classes that were never written down as a spec until now.

The single highest-value finding of this research: **`makeSortable`'s sort direction is inverted from what its own UI arrow implies.** A fresh click on any sortable header (`state.dir = -1`) sorts the column **ascending** (small→large, nulls at the top) and displays a **▼ (down)** arrow; a second click (`state.dir = +1`) sorts **descending** (large→small, nulls at the bottom) and displays **▲ (up)**. This was verified by executing the exact comparator in Node (not by reading the UI-SPEC's prose description of it, which states the opposite polarity — see Pitfall 1). Any Vitest test written against the UI-SPEC's stated "fresh click = descending" claim will encode the wrong behavior. The planner and executor must use the verified polarity below, not the UI-SPEC's page-contract prose.

Beyond that: the JSON contract (`web/data/*.json`) was read directly (not assumed) to confirm field shapes, nullability, and the one page (`scoreboard.json`) that currently **does not exist on disk** (pre-season) — meaning the empty-state path is the only one exercisable against live data today, and the populated-state path needs a synthetic fixture. Three new npm packages (`react-markdown`, three `@fontsource/*` packages) were checked against the package-legitimacy gate and the live npm registry: all four verdict `OK`.

**Primary recommendation:** Treat this phase as a port, not a build. Extract `makeSortable`, `statusFlag`, `bandCell`, and `fmtDeadline`'s verified-correct pieces into small, directly-testable TypeScript utilities (one per vanilla helper), write one Vitest assertion per enumerated rule below (satisfying D-05), and resist any urge to "fix" a vanilla quirk (inverted arrow, inconsistent `?? "–"` fallbacks between pages) without a `PARITY-DEVIATIONS.md` entry — D-01 is behavioral parity, not a corrected reimplementation.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-02 | xP table page at parity — sortable/filterable, exact sort/format semantics | Full `makeSortable`/`statusFlag`/`bandCell` inventory below (Parity Rule Inventory, Pitfall 1); verified sort-direction polarity via Node execution |
| UI-03 | Fixtures page with FDR ticker in the standard 1–5 green→red convention | Fixtures cell-logic inventory below; FDR tokens already declared in `frontend/src/index.css` (this phase activates them) |
| UI-04 | Prices page with watchlist rise/fall indicators | Watchlist mode-note/progress-bar inventory below; new `TrendingUp`/`TrendingDown` icons per UI-SPEC (ledger entry 5) |
| UI-05 | League, scoreboard, differentials, and methodology pages at parity | Per-page inventory below for all four; scoreboard's empty-vs-error `try{}catch{}` distinction flagged as Pitfall 2 |
| UI-06 | Persistent gameweek meta banner with deadline countdown | `fmtDeadline` verified inventory + UI-SPEC's upgraded `{rel}`/`{freshness}` format tables; `meta.json` schema confirmed live |
| UIX-02 | Dark mode toggle | Tailwind v4 `@custom-variant dark` class-strategy confirmed via web search against official-pattern docs; `frontend/src/index.css` already declares both light and (media-query) dark token blocks to migrate |
</phase_requirements>

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Parity model**
- D-01: Behavioral parity, not visual cloning — same data, same sort/filter/format semantics verified against an enumerated inventory of the vanilla rules; markup and visuals are React-idiomatic using the Phase 1 design tokens. Phase 7 compares information + behavior, not pixels.
- D-02: The xP table keeps the vanilla top-50 "free preview" cap and the Pro-tier teaser copy. The full table stays behind the future paid tier.
- D-03: All page copy (headlines, explainers, footer disclaimer, Pro teaser) ports verbatim. Any rewrite is a ledger entry.
- D-04: Every intentional deviation from vanilla is logged as a one-line entry in a deviation ledger: `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md`. Phase 7's side-by-side comparison treats this ledger as the list of explained deltas. Reversibility: costly.
- D-05: Parity is verified by unit tests per inventoried rule — each `.sort()`, `.toFixed()`, secondary sort key, and conditional class from the vanilla inventory becomes a Vitest assertion against fixture JSON. The inventory survives as executable regression coverage that Phase 4 E2E builds on.
- D-06: The xP table is the flagship — it gets the deepest test coverage (sorting, filtering, band rendering).

**Interaction & degradation behavior**
- D-07: Table sort/filter state is ephemeral component state — resets on reload/navigation exactly like vanilla. No URL params, no localStorage persistence.
- D-08: Data-load failures show rich error states using the Phase 1 ErrorState/EmptyState components with actionable per-page messages (deliberate improvement over vanilla's silent blanks; ledger entry).
- D-09: Status-flag injury news gets an accessible tooltip (tap/click-friendly, keyboard-accessible popover or inline reveal) instead of vanilla's desktop-only `title` attribute (ledger entry; also pre-work for Phase 3's mobile-usable tables).

**Rendering & assets**
- D-10: Pure CSR for all pages this phase. No prerender/SSG machinery; data stays runtime-fetched so prerendering remains addable later without rework.
- D-11: Per-page titles and meta descriptions handled by a small route helper (e.g., a `usePageMeta` hook reading a per-route table), porting vanilla's values verbatim. No helmet-style dependency.
- D-12: Fonts (Archivo, IBM Plex Sans/Mono) are self-hosted (woff2 via Fontsource or static files) — no Google Fonts CDN request. Reversibility: reversible, but any new npm package must pass the package-legitimacy gate.
- D-13: The methodology page is markdown-sourced — content lives in a `.md` file rendered through a markdown pipeline (renderer choice is planner's; package-legitimacy gate applies).

**Dark mode (UIX-02)**
- D-14: Default theme is system preference (`prefers-color-scheme`); an explicit user choice overrides it.
- D-15: The toggle is three-state: Light / Dark / System.
- D-16: Persistence via localStorage plus an inline head script in `index.html` that applies the theme class before React mounts — no flash of wrong theme on reload.
- D-17: Build the full dark token palette this phase — surfaces, text, borders, plus dark-safe variants of the semantic colors (FDR 1–5 green→red scale, price rise/fall indicators, status flags, band cells). Phase 3's pitch UI inherits this palette. Reversibility: costly.

**GW meta banner (UI-06)**
- D-18: Placement: the upgraded header chip — vanilla's deadline chip location in PageShell, now showing GW number, countdown, and data freshness. Not a separate banner bar.
- D-19: Countdown ticks per minute (per-second inside the final hour if cheap). Genuinely live, satisfies UI-06's "live deadline countdown".
- D-20: The banner includes a "generated …" freshness line from `meta.json`'s `generated_utc` — a deliberate improvement (ledger entry).
- D-21: When the deadline passes mid-session, the chip flips to a clear "GW{n} deadline passed" state. No speculative refetching.
- D-22: If `meta.json` fails to load, the chip shows a quiet "deadline TBC" fallback and pages render normally (matches vanilla's graceful degradation; D-08's rich-error-state rule applies to page data, not the banner).

### Claude's Discretion
- Markdown renderer choice for the methodology page (D-13) — subject to the package-legitimacy approval gate.
- Font delivery mechanism (Fontsource packages vs. self-hosted static woff2 files) — same gate applies.
- Tooltip implementation for D-09 (popover vs. inline reveal) — pick the cheapest accessible pattern.
- TanStack Query caching/refetch policy for the JSON files — not discussed; standard sensible defaults.
- Per-second ticking inside the final hour (D-19) — include only if it falls out naturally.

### Deferred Ideas (OUT OF SCOPE)
- Pre-launch SEO pass — prerender the shell of methodology/scoreboard/differentials, plus `sitemap.xml` and `robots.txt`. Deferred to a later milestone; CSR-with-runtime-data keeps it addable without rework.
</user_constraints>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sort / filter / format (xP table, Differentials, price watch) | Browser / Client | — | Pure client-side state in vanilla (`makeSortable`, filter closures); ported as ephemeral React component state per D-07 — no server round trip |
| JSON contract fetch (`/data/*.json`) | Browser / Client | API / Backend (static file mount) | TanStack Query fetches at runtime (D-10); FastAPI's `StaticFiles` mount at `/` is the read-only serving tier — already built, out of scope this phase, contract consumed unchanged |
| GW meta banner countdown | Browser / Client | — | `setInterval`-driven relative-time computation from `meta.json`'s `deadline_utc`; no server push, no websocket |
| Dark mode resolution + persistence | Browser / Client | — | `localStorage` + inline `<head>` script + `matchMedia` listener; no server-side preference storage this phase |
| Methodology content | Frontend build (Vite `?raw` import) | — | Bundled at build time, not runtime-fetched — a distinct tier from every other page's data source (explicitly not a violation of D-10, per UI-SPEC's own reasoning) |
| FDR / status-flag / price rise-fall color coding | Browser / Client | — | Pure presentational mapping over already-fetched JSON fields; no computation happens server-side |
| CSS dark-token selector strategy | Browser / Client (build-time CSS) | — | Tailwind v4 `@custom-variant dark` compiles to a CSS class selector; runtime toggle is a `classList` operation, no JS-computed styles |

## Standard Stack

### Core (already installed, Phase 1)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^19.2.8 | UI runtime | Already pinned, no change this phase |
| react-router | 7.18.3 | Routing, `NavLink`, data router `errorElement` | Already pinned; `RouteErrorBoundary` pattern established in Phase 1 |
| @tanstack/react-query | 5.102.8 | Data fetching/caching for every `/data/*.json` and `meta.json` | Already pinned; established `useQuery` pattern in `XpTable.tsx` |
| lucide-react | 1.38.0 | Icons — `Sun`/`Moon`/`Monitor` (theme toggle), `TrendingUp`/`TrendingDown` (price) | Already installed in Phase 1, **activated for the first time this phase** |
| tailwindcss / @tailwindcss/vite | 4.3.3 | Styling, design tokens | Already pinned; CSS-first `@theme`/`@custom-variant` config (v4 paradigm) |
| typescript | 6.0.3 | Type safety | Already pinned (deliberate downgrade from a broken newer release per Phase 1's SUMMARY) |

### New this phase

| Library | Registry-verified version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `react-markdown` | **10.1.0** `[VERIFIED: npm registry via package-legitimacy check + npm view, 2026-09-01]` | Renders `frontend/src/content/methodology.md` (D-13) | No `dangerouslySetInnerHTML` — parses via `remark`/`rehype` into real React elements; 33.7M weekly downloads; MIT; matches D-13's discretion note |
| `@fontsource/archivo` | **5.3.0** `[VERIFIED: npm registry, 2026-09-01]` | Self-hosted Archivo (headings, 700) woff2 | D-12 — replaces Phase 1's Google Fonts `<link>` |
| `@fontsource/ibm-plex-sans` | **5.3.0** `[VERIFIED: npm registry, 2026-09-01]` | Self-hosted IBM Plex Sans (body/UI, 400) woff2 | D-12 |
| `@fontsource/ibm-plex-mono` | **5.3.0** `[VERIFIED: npm registry, 2026-09-01]` | Self-hosted IBM Plex Mono (numeric/tabular, 400) woff2 | D-12 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `react-markdown` | `marked` / `markdown-it` + `dangerouslySetInnerHTML` | Faster to wire but reintroduces an XSS-shaped sink for zero benefit — methodology content is developer-authored today, but the sink itself is the risk, not today's content. `react-markdown` avoids it entirely at negligible bundle cost (content is 4 short sections). |
| Hand-rolled `{rel}`/`{freshness}` countdown math | `date-fns` / `dayjs` / `luxon` | **Rejected — do not add.** D-19's format table is 2–3 branches of `Math.floor`/`%` arithmetic, the same idiom vanilla's own `fmtDeadline` already uses. A date library is a real dependency (bundle size, another package-legitimacy review) for a problem vanilla already solved in 6 lines. Matches CLAUDE.md's "boring, maintainable choices" budget constraint. |
| `@fontsource/*` packages | Manually downloaded/subsetted `.woff2` files in `public/fonts/` | Fontsource ships pre-built, correctly-licensed woff2 + ready CSS `@font-face` imports for exactly the two weights (400/700) this project uses — no manual subsetting or license-file bookkeeping. Recommended. |

**Installation:**
```bash
cd frontend
npm install --save-exact react-markdown@10.1.0 @fontsource/archivo@5.3.0 @fontsource/ibm-plex-sans@5.3.0 @fontsource/ibm-plex-mono@5.3.0
```

**Version verification:** All four versions above were verified live against the npm registry on 2026-09-01 via `npm view <pkg> version` from `frontend/` (matches the project's existing package pinning discipline — `--save-exact`, re-verify immediately before install per Phase 1's established pattern).

## Package Legitimacy Audit

| Package | Registry | Published | Weekly Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----------|-------------------|--------------|---------|-------------|
| react-markdown | npm | 2025-03-07 | 33,678,442 | github.com/remarkjs/react-markdown | OK | Approved |
| @fontsource/archivo | npm | 2026-07-19 | 115,882 | github.com/fontsource/font-files | OK | Approved |
| @fontsource/ibm-plex-sans | npm | 2026-07-19 | 540,876 | github.com/fontsource/font-files | OK | Approved |
| @fontsource/ibm-plex-mono | npm | 2026-07-19 | 1,313,717 | github.com/fontsource/font-files | OK | Approved |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none — all four verdicts `OK` from `gsd-tools query package-legitimacy check --ecosystem npm`, cross-verified against the live npm registry (`npm view <pkg> version`) with zero drift, and `npm view react-markdown scripts.postinstall` returned empty (no postinstall script).

*Despite the clean `OK` verdicts, these are still new dependencies discovered via the seam's registry lookup rather than pre-approved in a prior phase's human gate — the planner should route the actual `npm install` through the same human-approval step Phase 1 used for its package list, per this project's established package-legitimacy discipline (see STATE.md's Phase 01 "Human approved full 13-package … install set" precedent).*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (React SPA, client-side routed)                             │
│                                                                        │
│  PageShell (header: brand + nav + GW-chip + theme-toggle)            │
│   │                                                                    │
│   ├─ meta.json ──▶ useQuery("meta") ──▶ GwBanner (D-18..D-22)        │
│   │                                      countdown tick (setInterval) │
│   │                                                                    │
│   ├─ localStorage["fpl-theme"] ──▶ useTheme() ──▶ <html class="dark">│
│   │    (inline <head> script pre-mount, D-16)                        │
│   │                                                                    │
│   └─ <Outlet/> — per-route page component                            │
│        │                                                               │
│        ├─ /            xp_table.json + captains.json                 │
│        │                 fetch → slice(0,50) → filter(pos,search)     │
│        │                 → sort(makeSortable-ported) → render rows    │
│        │                 → bandCell (p10/p90 track+dot)               │
│        │                                                               │
│        ├─ /fixtures    fixtures.json (not sortable)                  │
│        │                 fetch → render 6-GW FDR cells (fdr1..5)      │
│        │                                                               │
│        ├─ /prices      watchlist.json (not sortable)                 │
│        │                 fetch → mode-branch copy → progress bars     │
│        │                 → TrendingUp/Down icon (new, UI-04)          │
│        │                                                               │
│        ├─ /league      standings.json + leaders.json (not sortable)  │
│        │                                                               │
│        ├─ /scoreboard  scoreboard.json (try/catch → empty | 5xx →    │
│        │                 ErrorState; 404 → empty; special-cased)      │
│        │                                                               │
│        ├─ /differentials  xp_table.json (client re-filtered,         │
│        │                    ownership slider + status==="a")          │
│        │                                                               │
│        └─ /methodology  frontend/src/content/methodology.md           │
│                           (Vite ?raw import, build-time — no fetch)   │
└─────────────────────────────────────────────────────────────────────┘
                              │  GET /data/*.json  (relative to origin,
                              │  root-relative — NOT relative to route)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Dev: Vite proxy /data,/api → localhost:8000                         │
│  Prod: FastAPI StaticFiles mount serving web/data/*.json + web/ built │
│  (out of scope this phase — contract consumed unchanged)             │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
frontend/src/
├── lib/
│   ├── api.ts                 # existing — fetchJson/fetchApi, add per-JSON TS interfaces here
│   ├── sortable.ts             # NEW — ported makeSortable as a hook: useSortableRows()
│   ├── format.ts               # NEW — toFixed/toLocaleString wrappers matching vanilla exactly
│   ├── bandCell.ts             # NEW — p10/p90 track math (maxHi, pct, calc() string builder)
│   ├── statusFlag.tsx          # NEW — accessible tooltip StatusFlag component (D-09)
│   ├── deadline.ts             # NEW — fmtDeadline's {abs} port + D-19's upgraded {rel}/{freshness}
│   └── theme.ts                # NEW — useTheme() hook: localStorage + matchMedia + class toggle
├── content/
│   └── methodology.md          # NEW — verbatim port of web/methodology.html lines 30-77
├── components/
│   ├── GwBanner.tsx             # NEW — mounts in PageShell's ml-auto slot (D-18)
│   ├── ThemeToggle.tsx          # NEW — 3-state Light/Dark/System segmented control
│   ├── FdrCell.tsx              # NEW — shared by Fixtures
│   └── BandCell.tsx             # NEW — shared by xP table + Differentials
└── routes/
    ├── XpTable.tsx              # replace placeholder — flagship (D-06)
    ├── Fixtures.tsx
    ├── Prices.tsx
    ├── League.tsx
    ├── Scoreboard.tsx
    ├── Differentials.tsx
    └── Methodology.tsx
```

### Pattern 1: Ported sort comparator as a typed hook

**What:** `makeSortable`'s exact comparator, extracted so its verified (non-obvious) polarity lives in one tested place instead of being re-derived per page.
**When to use:** The xP table is the only sortable table this phase (see Parity Rule Inventory below) — but the hook should be written generically since Phase 3 will need it again.
**Example (verified polarity, see Pitfall 1):**
```typescript
// Source: ported from web/assets/app.js:57-79 (verified via Node execution, 2026-09-01)
type SortState<K extends string> = { key: K | null; dir: 1 | -1 };

function compareNumeric(a: number | null | undefined, b: number | null | undefined, dir: 1 | -1) {
  return dir * ((b ?? -1e9) - (a ?? -1e9));
}
function compareString(a: string | null | undefined, b: string | null | undefined, dir: 1 | -1) {
  return dir * String(b ?? "").localeCompare(String(a ?? ""));
}

// A fresh click sets dir = -1. VERIFIED: dir=-1 sorts ASCENDING (nulls first);
// a second click on the same key flips to dir = +1, which sorts DESCENDING
// (nulls last). The vanilla UI shows "▼" for dir<0 and "▲" for dir>=0 — i.e.
// the arrow glyph is inverted from the sort result. Port this exactly; do not
// "fix" the arrow without a PARITY-DEVIATIONS.md entry (D-04).
```

### Pattern 2: TanStack Query fetch failure needs status-code branching (Scoreboard only)

**What:** `fetchJson` currently throws `new Error(\`${path}: ${res.status}\`)` on any non-ok response — the status code is embedded in the message string but not structurally available.
**When to use:** Every page except Scoreboard can treat any `isError` as `ErrorState` (D-08). Scoreboard needs to distinguish "file doesn't exist yet" (→ empty state, verbatim vanilla copy) from "server/network failure" (→ `ErrorState`).
**Example:**
```typescript
// Source: web/assets/app.js loadJSON() + web/scoreboard.html's try{}catch{} (read directly)
// Vanilla's bare `catch {}` treats ANY failure — 404, 500, network — as "no data yet".
// This phase's D-08 wants only a missing-file (404) response to route to the empty
// state; a genuine 5xx/network failure should still surface ErrorState. This requires
// a query fn that distinguishes status codes, e.g.:
async function fetchScoreboard(): Promise<ScoreboardResponse | null> {
  const res = await fetch("/data/scoreboard.json");
  if (res.status === 404) return null;       // → empty state (verbatim vanilla copy)
  if (!res.ok) throw new Error(`/data/scoreboard.json: ${res.status}`); // → ErrorState
  return res.json();
}
```

### Anti-Patterns to Avoid
- **Re-deriving the sort comparator "from spec" without checking against real vanilla behavior:** the UI-SPEC's own prose description of the direction ("fresh key always starts descending") does not match what `web/assets/app.js`'s code actually does when executed. Trust the verified port in Pattern 1, not a paraphrase.
- **Relative `fetch("data/x.json")` paths:** vanilla pages are all served flat at the root, so a relative path always resolves correctly. React is client-side routed — `fetch("data/x.json")` from `/fixtures` resolves to `/fixtures/data/x.json` (404). Always use the root-relative `/data/x.json` form already established in `frontend/src/lib/api.ts` and `vite.config.ts`'s proxy comment.
- **Using `dangerouslySetInnerHTML` anywhere in the methodology renderer or any other page:** `react-markdown` avoids this by design; do not bypass it with a raw HTML injection shortcut even for "trusted" developer-authored content.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown → React elements | A regex-based mini markdown parser | `react-markdown` 10.1.0 | CommonMark edge cases (nested lists, emphasis inside links) are exactly the kind of "looks done, isn't" surface a hand-rolled parser gets wrong; `react-markdown` also structurally avoids `dangerouslySetInnerHTML` |
| Dark-mode CSS selector strategy | A second `data-theme` attribute mechanism alongside the existing `@media (prefers-color-scheme)` block | Tailwind v4's `@custom-variant dark (&:where(.dark, .dark *));` class-based variant (confirmed current pattern via web search, 2026-09-01) — migrate the *existing* token values into a `.dark { … }` selector block, do not restate them | Two competing dark-mode mechanisms (media-query + class) fighting over the same custom properties is a classic "why is this component wrong in dark mode but only sometimes" bug source |
| Font subsetting/hosting | Manually downloading Archivo/IBM Plex `.woff2` files and hand-writing `@font-face` | `@fontsource/archivo`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono` | Correct weights (400/700 only, matching the 2-weight contract), correct licensing metadata, zero manual `@font-face` bookkeeping |

**Key insight:** Every "don't hand-roll" in this phase is really "don't hand-roll a *second*, subtly different version of something vanilla already got right (or already got specifically wrong in a documented way)." The actual sort/filter/format logic *is* hand-rolled — by design, per D-01 — but it's a **port**, not a rebuild: the source of truth is `web/assets/app.js`'s executed behavior, not a re-derivation from a written description of it.

## Common Pitfalls

### Pitfall 1: Sort direction/arrow polarity is inverted from naive expectation (and from the UI-SPEC's own prose)
**What goes wrong:** An implementer reads `state.dir: -1` as "descending" (a common convention) and/or trusts the UI-SPEC Page Contract's claim "Fresh key always starts descending" and writes the React sort to match — producing a table that sorts the *opposite* direction from the real vanilla site on first click, silently failing D-05's parity intent while still "passing" a self-consistent test suite.
**Why it happens:** `makeSortable`'s comparator computes `state.dir * ((y ?? -1e9) - (x ?? -1e9))` where `x = a[key]` and `y = b[key]` — a `(y - x)` (not `(x - y)`) flip that inverts the naive reading of `dir`.
**How to avoid:** Use the verified polarity, confirmed by executing the exact comparator in Node (2026-09-01):
```
$ node -e '... (full script executed this session) ...'
dir=-1 (fresh click):        [{"v":1},{"v":2},{"v":3},{"v":5}]   // ASCENDING
dir=+1 (second click):       [{"v":5},{"v":3},{"v":2},{"v":1}]   // DESCENDING
dir=-1 null handling:        [{"v":null},{"v":3},{"v":5}]        // null → TOP on fresh click
dir=+1 null handling:        [{"v":5},{"v":3},{"v":null}]        // null → BOTTOM on second click
dir=-1 string:                [{"name":"Alpha"},{"name":"Bravo"},{"name":"Charlie"}]  // ASCENDING
```
And the arrow glyph, read directly from `web/assets/app.js:68-69`: `` h.querySelector(".dir").textContent = h === th ? (state.dir < 0 ? "▼" : "▲") : "" `` — so a fresh click (`dir=-1`, ascending) shows **▼**, and a second click (`dir=+1`, descending) shows **▲**. This is genuinely counter-intuitive (▼ usually implies "descending" in most UI conventions) but it is the real, live behavior of the production site today — port it exactly per D-01; do not "fix" it without a `PARITY-DEVIATIONS.md` entry.
**Warning signs:** A Vitest test that asserts "clicking a header once shows the largest value first" is testing the *wrong* behavior — write the test against the Node-verified output above.

### Pitfall 2: Scoreboard's empty-vs-error distinction is a special case, not the default D-08 behavior
**What goes wrong:** `fetchJson` (the shared Phase 1 utility) throws a generic `Error` on any non-ok HTTP response, with no structured status code — every other page correctly routes every failure to `ErrorState` (D-08). Scoreboard is the one page where a **missing file** (`scoreboard.json` genuinely does not exist pre-season — confirmed: `ls web/data/scoreboard.json` → "No such file or directory" as of this research session) must route to the verbatim vanilla empty-state copy instead, while a true 5xx/network failure must still route to `ErrorState`.
**Why it happens:** Vanilla's `try { board = await loadJSON("scoreboard.json"); } catch {}` swallows *every* failure uniformly into "empty" — it does not actually distinguish 404 from 500 from a network timeout. The UI-SPEC's stated intent (D-08 + this page's exception) asks React to be *more* discriminating than vanilla, which means the query function must branch on `res.status === 404` explicitly (see Pattern 2 above) — a level of structure `fetchJson` doesn't provide out of the box.
**How to avoid:** Write a dedicated fetch function for this one page (Pattern 2) rather than reusing bare `fetchJson<ScoreboardResponse>()`.
**Warning signs:** A scoreboard test that mocks a 500 response and expects the empty-state copy is testing vanilla's actual (cruder) behavior, not this phase's intended (D-08-compliant) behavior — confirm with the planner/discuss-phase record which one is wanted if this reads ambiguously; the UI-SPEC (E5 row) states the ErrorState-for-5xx behavior explicitly.

### Pitfall 3: `??`/`?.` fallback presence is inconsistent *between pages* for the identically-named `ownership` field — replicate exactly, don't unify
**What goes wrong:** `ownership` appears in four places across the JSON contract's consuming pages. Applying one fallback rule everywhere "for consistency" changes rendered output on pages where vanilla has no fallback:
- xP table (`web/index.html:107`): `r.ownership?.toFixed(1) ?? "–"` — has a `"–"` fallback.
- Captains sub-table (`web/index.html:128`): `r.ownership?.toFixed(1)` — **no fallback**; a null `ownership` renders the literal string `"undefined"`.
- Differentials (`web/differentials.html:72`): `r.ownership?.toFixed(1)` — **no fallback**, same as captains.
- Prices (`web/prices.html:93`): `r.ownership.toFixed(1)` — no optional chaining at all (assumes always present in `watchlist.json` rows).
**Why it happens:** The vanilla site was hand-written per-page without a shared formatting utility; each inline script drifted independently.
**How to avoid:** Port each page's exact fallback behavior — verified by reading each file directly this session, not inferred from the xP table's pattern. The UI-SPEC's own Page Contract tables already capture this correctly (xP table: "or – if null"; Differentials: plain ".toFixed(1)", no fallback note) — cross-verified against source, consistent.
**Warning signs:** A shared `formatOwnership()` utility used identically on all four pages is a sign this pitfall was missed — it should have (at minimum) a parameter for whether the caller wants the `"–"` fallback.

### Pitfall 4: `bandCell`'s width math uses a CSS `calc()` string, not a JS-computed number
**What goes wrong:** `web/assets/app.js:97-99` composes `style="left:${pct(lo)};width:calc(${pct(hi)} - ${pct(lo)})"` — the *width* is a CSS `calc()` expression subtracting two independently-clamped percentages (each individually passed through `Math.min(100, …)`), not a value computed in JS. An implementer who instead precomputes `widthPct = pct(hi) - pct(lo)` in JS will diverge whenever either bound is clamped at the 100% ceiling (i.e., when `p90` or `xp` exceeds `maxHi`, which can't happen by construction for `maxHi`'s own row, but can for other rows sharing the same `maxHi` denominator only in the non-clamped case — the clamp only matters if a per-row value could exceed the table's own max, which the current formula prevents by definition, but the calc()-vs-JS distinction still changes *which* value the browser subpixel-rounds and *when* — port the calc() string exactly for pixel-for-pixel intent, not a numeric equivalent).
**How to avoid:** Reproduce as an inline style `calc()` string (or Tailwind arbitrary value with `calc()`), not a pre-subtracted number.

### Pitfall 5: Root-relative vs relative fetch paths
**What goes wrong:** Vanilla's `loadJSON()` fetches `data/${name}` — relative to the current page URL, which works because every vanilla page is served flat at the site root (`/index.html`, `/fixtures.html`, …). React is client-side routed with real paths (`/fixtures`, `/prices`); a relative fetch from `/fixtures` would resolve to `/fixtures/data/x.json` (404).
**How to avoid:** Always fetch the root-relative form, `/data/x.json` — already the established convention in `frontend/src/lib/api.ts` (`fetchJson<MetaResponse>("/data/meta.json")`) and documented in `vite.config.ts`'s proxy comment. No page in this phase should introduce a relative fetch path.

### Pitfall 6: `xp_table.json`'s pre-sorted-by-pipeline assumption is silent and untested
**What goes wrong:** `web/index.html:88` does `const top = table.slice(0, 50);` with **no sort call** — it assumes `xp_table.json` arrives already sorted descending by `xp` from the Python export pipeline. This assumption was confirmed true for the current sample (`B.Fernandes` xp=3.63 first, descending through the file) but is not enforced anywhere in the JSON contract itself — a future pipeline change to `predict/export.py`'s ordering would silently break the "top 50 by xP" claim in the UI copy (D-02) without any test catching it, since the frontend doesn't re-sort.
**How to avoid:** Port the `.slice(0, 50)`-without-resort behavior exactly (per D-01/D-02), but add one Vitest assertion against the fixture data confirming the first 50 rows are `xp`-descending, so a future contract violation fails loudly on the frontend side rather than silently serving an unsorted "top 50."

## Code Examples

### Parity Rule Inventory (executable checklist — D-05's source of truth)

> Every `.sort()`, `.toFixed()`/`.toLocaleString()`, secondary sort key, and conditional class in `web/assets/app.js` and the seven page scripts, enumerated by reading each file directly this session (`[VERIFIED: web/assets/app.js]`, `[VERIFIED: web/index.html]`, etc. — see per-row citation). **No secondary sort key exists anywhere in vanilla** — closing out the phase description's research flag explicitly: `makeSortable` is single-active-key only, and only the xP table (`#xp`) calls it. Every other table (Fixtures, Prices ×2, League standings, Scoreboard history, Differentials) has no `data-key` headers and no `makeSortable` call.

| # | Rule | Verified detail | Source |
|---|------|------------------|--------|
| R1 | `makeSortable` fresh-click direction | `dir=-1` (fresh click) → **ascending**, nulls **top**, arrow **▼**. Second click `dir=+1` → **descending**, nulls **bottom**, arrow **▲**. See Pitfall 1 for the executed proof. | `web/assets/app.js:57-79` |
| R2 | Numeric compare | `dir * ((b ?? -1e9) - (a ?? -1e9))` | `web/assets/app.js:73` |
| R3 | String compare | `dir * String(b ?? "").localeCompare(String(a ?? ""))` | `web/assets/app.js:74` |
| R4 | `statusFlag` trigger | Renders only when `status !== "a"` | `web/assets/app.js:82` |
| R5 | `statusFlag` glyph/class | `status` in `["i","s","u","n"]` → `✕`, class `flag out`, `aria-label="unavailable"`; else → `▲`, class `flag`, `aria-label="doubtful"` | `web/assets/app.js:83-87` |
| R6 | `statusFlag` tooltip text | `r.news || label` (label = "unavailable"/"doubtful"), quotes escaped | `web/assets/app.js:86` |
| R7 | `bandCell` bounds | `lo = r.p10 ?? r.xp`, `hi = r.p90 ?? r.xp` | `web/assets/app.js:92` |
| R8 | `bandCell` pct fn | `Math.min(100, 100 * v / maxHi)` | `web/assets/app.js:93` |
| R9 | `bandCell` tooltip copy (verbatim, D-03) | `` xP {xp.toFixed(2)} — actual score lands between {lo.toFixed(1)} and {hi.toFixed(1)} in 8 gameweeks out of 10 `` | `web/assets/app.js:94` |
| R10 | xP table slice | `table.slice(0, 50)` — **no re-sort**, assumes pipeline pre-sorts descending by `xp` (Pitfall 6) | `web/index.html:88` |
| R11 | xP table `maxHi` | `Math.max(...top.map(r => r.p90 ?? r.xp))` — **no floor** | `web/index.html:89` |
| R12 | xP table row filter | `(posFilter === "ALL" || r.position === posFilter) && (!query || name/team/team_short.toLowerCase().includes(query))` — search matches `r.team` (full name, not displayed) as well as `r.team_short` | `web/index.html:95-100` |
| R13 | xP table search normalization | `e.target.value.trim().toLowerCase()` | `web/index.html:121` |
| R14 | xP table `£m` | `r.price_m.toFixed(1)` — no fallback (always present) | `web/index.html:106` |
| R15 | xP table `Own %` | `r.ownership?.toFixed(1) ?? "–"` | `web/index.html:107` |
| R16 | xP table `Captain xP` | `r.xp_capt?.toFixed(2) ?? "–"` | `web/index.html:109` |
| R17 | Captain picks sub-table | `capt.slice(0, 5)`, no sort/filter, columns use `r.team` (full name, not `team_short`) | `web/index.html:124-129` |
| R18 | Captains `Own %` | `r.ownership?.toFixed(1)` — **no `"–"` fallback** (Pitfall 3) | `web/index.html:128` |
| R19 | Captains `Captain xP` | `r.xp_capt.toFixed(2)` — no optional chaining (always present) | `web/index.html:129` |
| R20 | Fixtures: dynamic GW column count | `ticker[0].gws.length` (currently 6) | `web/fixtures.html:60` |
| R21 | Fixtures: blank-GW cell | `g.fixtures.length === 0` → `<span class="fdr fdr3" title="Blank gameweek">—</span>` (em dash, fdr3 = neutral) | `web/fixtures.html:70-71` |
| R22 | Fixtures: fixture cell | Per fixture: `{opp}{H\|A}` styled `fdr{f.fdr}`, `title="{Home\|Away} vs {opp}, difficulty {fdr}"` | `web/fixtures.html:72-75` |
| R23 | Fixtures: `xG next`/`xGC next` | `t.xg_next?.toFixed(2) ?? "–"`, `t.xgc_next?.toFixed(2) ?? "–"` | `web/fixtures.html:67-68` |
| R24 | Fixtures: `Ease` | `t.ease.toFixed(2)` — no fallback | `web/fixtures.html:77` |
| R25 | Prices: progress `raw`/`pct`/`bar` | `raw = r.prob ?? r.progress ?? 0`; `pct = Math.round(100*Math.abs(raw))`; `bar = Math.min(pct,100)` | `web/prices.html:83-85` |
| R26 | Prices: label, `official` mode | `` ${pct}%${proj_tonight != null ? ` → ${Math.round(100*Math.abs(proj_tonight))}% tonight` : ""} `` | `web/prices.html:86-88` |
| R27 | Prices: label, other modes | `r.prob != null ? \`${pct}%\` : \`${bar}% of threshold\`` | `web/prices.html:89` |
| R28 | Prices: `Net transfers` | `(r.net_transfers ?? 0).toLocaleString()` — **not** `.toFixed()` | `web/prices.html:94` |
| R29 | Prices: `£m`/`Own %` | `r.price_m.toFixed(1)`, `r.ownership.toFixed(1)` — **no optional chaining, no fallback** (watchlist rows assumed complete) | `web/prices.html:92-93` |
| R30 | Prices: mode-note copy, three exact variants | `official` / `heuristic` / else (trained, uses `w.trained_utc?.slice(0,10)` and `(100*w.val_moved_hit).toFixed(0)`) | `web/prices.html:61-79` |
| R31 | Prices: locked-players sentence | Appended to `official` mode note only if `w.locked_players` is truthy | `web/prices.html:66-67` |
| R32 | League: `#` | `index + 1` (array position, not a data field) | `web/league.html:59` |
| R33 | League: `GD` sign | `t.gd > 0 ? "+" + t.gd : t.gd` — no `+` prefix for zero or negative | `web/league.html:64` |
| R34 | Leaders boards | 5 fixed boards (`points`/`goals`/`assists`/`clean_sheets`/`cards`), `.slice(0, 8)`, fallback `"Nothing yet this season"` when the sliced array is empty | `web/league.html:68-79` |
| R35 | Scoreboard: empty-vs-error | `try{}catch{}` around `loadJSON("scoreboard.json")` — vanilla treats **any** failure as empty; this phase's D-08 wants only 404 → empty, other failures → `ErrorState` (Pitfall 2) | `web/scoreboard.html:64-65` |
| R36 | Scoreboard: empty tiles (verbatim, D-03) | `Backtest MAE: 0.87 vs FPL 1.07` / `Backtest rank corr: 0.74 vs FPL 0.30` / `Seasons validated: 6` | `web/scoreboard.html:81-85` |
| R37 | Scoreboard: populated tiles | `${s.mae_model} vs FPL ${s.mae_fpl ?? "–"}`, `${s.spearman_model} vs FPL ${s.spearman_fpl ?? "–"}`, `s.gameweeks`, `s.captain_avg_points` | `web/scoreboard.html:76-80` |
| R38 | Scoreboard: history row | `e.mae_fpl ?? "–"`, `e.spearman_fpl ?? "–"` per-row nullability | `web/scoreboard.html:87-93` |
| R39 | Differentials: filter | `(r.ownership ?? 100) <= cap && r.status === "a"`, `.slice(0, 30)` | `web/differentials.html:64-65` |
| R40 | Differentials: `maxHi` | `Math.max(1, ...rows.map(r => r.p90 ?? r.xp))` — **floor of 1**, differs from xP table's R11 (no floor); do not unify | `web/differentials.html:66` |
| R41 | Differentials: no fallback on `Own %` | `r.ownership?.toFixed(1)` — same as captains (R18), no `"–"` | `web/differentials.html:72` |

### Verified sort-direction test (paste-ready reference — see Pitfall 1)

```typescript
// Source: verified by executing the exact vanilla comparator in Node, 2026-09-01.
// Write this as the FIRST Vitest test for the ported sort utility — it locks in
// the counter-intuitive-but-correct polarity before any page code depends on it.
import { describe, expect, it } from "vitest";
import { sortRows } from "../lib/sortable"; // the ported utility

describe("sortRows (ported from web/assets/app.js makeSortable, verified 2026-09-01)", () => {
  it("fresh click (dir=-1) sorts numeric ascending, nulls first", () => {
    const rows = [{ v: 3 }, { v: 1 }, { v: 5 }, { v: 2 }];
    expect(sortRows(rows, "v", -1, true).map((r) => r.v)).toEqual([1, 2, 3, 5]);
  });
  it("second click (dir=+1) sorts numeric descending, nulls last", () => {
    const rows = [{ v: 3 }, { v: null }, { v: 5 }];
    expect(sortRows(rows, "v", 1, true).map((r) => r.v)).toEqual([5, 3, null]);
  });
  it("fresh click on a numeric key sorts nulls to the top, not the bottom", () => {
    const rows = [{ v: 3 }, { v: null }, { v: 5 }];
    expect(sortRows(rows, "v", -1, true).map((r) => r.v)).toEqual([null, 3, 5]);
  });
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Tailwind v3 `darkMode: 'class'` in `tailwind.config.js` | Tailwind v4 `@custom-variant dark (&:where(.dark, .dark *));` declared directly in the CSS entry file — no JS config file for this at all | Tailwind v4 (already the pinned version, 4.3.3) | `frontend/src/index.css` currently wraps its dark tokens in `@media (prefers-color-scheme: dark)` (Phase 1's placeholder strategy per its own comment: "Swappable for a `data-theme` attribute strategy when the Phase 2 dark-mode toggle needs explicit user override"). This phase migrates that block to a `.dark { … }` class selector fed by `@custom-variant dark`, keeping the same token *values* — additive, not a rewrite (per D-16/D-17 and confirmed via web search against the current documented pattern, 2026-09-01). `[CITED: schoen.world/n/tailwind-dark-mode-custom-variant, tailkits.com/blog/styling-dark-text-tailwind-v4]` |

**Deprecated/outdated:** none applicable to this phase's own history — the project has no prior React dark-mode implementation to deprecate; Phase 1 explicitly flagged its media-query-only approach as provisional.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | TanStack Query v5's out-of-the-box defaults (`staleTime: 0`, `refetchOnWindowFocus: true`, `retry: 3`) are acceptable "sensible defaults" for these mostly-static weekly-refreshed JSON files, per CONTEXT.md's discretion note | Claude's Discretion / TanStack Query caching policy | Low — CONTEXT.md explicitly delegates this choice; worst case is a few extra background refetches on window focus for data that only changes weekly. Recommend the planner set an explicit `staleTime` (e.g. 60_000ms) for `/data/*.json` queries to avoid refetch chatter, but this is a tuning choice, not a correctness one. |
| A2 | `window.matchMedia("(prefers-color-scheme: dark)")`'s `change` event listener is supported in all target browsers without a polyfill | Dark mode toggle / D-14 | Low — this is a long-standard API; not verified against a specific browser support matrix this session because the project has no documented minimum-browser-version target |
| A3 | `watchlist.json`'s `heuristic` and trained-model (`else`) mode shapes (fields present when `w.mode !== "official"`) match what the code paths in `web/prices.html` read (`w.trained_utc`, `w.val_moved_hit`) — only the `official`-mode shape was observed in the live sample this session (`web/data/watchlist.json` currently has `"mode": "official"`) | Prices page / R30 | Medium — if the planner writes fixture JSON for the `heuristic`/trained-model test cases without cross-checking `models/price.py`'s actual export shape, a field-name mismatch would only surface once the pipeline naturally transitions modes (day 14+ per the price-model unlock timeline in STATE.md's blockers). Recommend a quick grep of `models/price.py`'s watchlist-dict construction before writing those two fixtures. |

## Open Questions

1. **Should the per-second countdown tick (D-19's optional final-hour granularity) be implemented?**
   - What we know: UI-SPEC explicitly frames it as "Claude's discretion — include only if it falls out naturally," with an explicit fallback (per-minute tick) if not implemented.
   - What's unclear: Whether the added `setInterval` branching (switching cadence when entering the final hour) is worth the complexity for a countdown that's cosmetic once inside 60 minutes.
   - Recommendation: Implement it — the branching is a single `remaining < 3600_000 ? 1000 : 60000` conditional on the existing interval, not a structural change, and it directly satisfies UI-06's "live" framing more convincingly than a per-minute-only tick.

2. **`scoreboard.json`'s populated-state path is currently unexercisable against live data.**
   - What we know: The file does not exist on disk as of this research session (pre-season; confirmed via `ls`), so only the empty-state path (R35/R36) can be manually verified against the real dev server today.
   - What's unclear: Whether the planner should synthesize a fixture from `predict/scoreboard.py`'s `score_gw()`/`running_summary()` output shape (fully enumerated in this research from source) or wait for the first real scoreboard entry.
   - Recommendation: Synthesize a fixture now — the shape is fully known from `predict/scoreboard.py` (read directly this session): `{"entries": [{"gw", "n_players", "generated_utc", "mae_model", "spearman_model", "mae_fpl"?, "spearman_fpl"?, "captain": {"name","team","points"}, "top5": [...], "best_player": {"name","points"}}], "summary": {"gameweeks","mae_model","spearman_model","captain_avg_points","mae_fpl"?,"spearman_fpl"?}}`. Do not block D-06-adjacent test coverage on the first real gameweek finishing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Node.js | Vite dev server, Vitest, npm installs | ✓ | v24.20.0 | — |
| npm | Package installs | ✓ | 12.0.2 | — |
| Python (conda `python314`) | `uvicorn` dev server behind the Vite proxy (`/data`, `/api`) for manual verification | ✓ | 3.14.3 | — |
| uvicorn | Serves `web/data/*.json` + `api/main.py` for the proxy target | ✓ | 0.44.0 | — |
| Frontend packages (react, react-router, @tanstack/react-query, lucide-react, tailwindcss) | All page components | ✓ | pinned, see Standard Stack | — |
| `react-markdown`, `@fontsource/*` | Methodology page, self-hosted fonts | ✗ (not yet installed) | 10.1.0 / 5.3.0 (verified available on registry) | None needed — install is a normal `npm install --save-exact` step in this phase's plan, gated by the package-legitimacy audit above |

**Missing dependencies with no fallback:** none blocking — the four new packages are simply not yet installed; installing them is in-scope plan work, not a gap.
**Missing dependencies with fallback:** none applicable.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.11 + @testing-library/react 16.3.3 + @testing-library/jest-dom 7.0.1 |
| Config file | `frontend/vitest.config.ts` (jsdom environment, `src/test/setup.ts` registers `afterEach(cleanup)` + jest-dom matchers) |
| Quick run command | `cd frontend && npx vitest run src/lib/sortable.test.ts` (or any single new test file) |
| Full suite command | `cd frontend && npm test` (= `vitest run`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| UI-02 | Sort direction/polarity per Pitfall 1 / R1-R3 | unit | `npx vitest run src/lib/sortable.test.ts` | ❌ Wave 0 |
| UI-02 | xP table filter (position + search), R10-R16 | unit + component | `npx vitest run src/routes/XpTable.test.tsx` | ❌ Wave 0 |
| UI-02 | `bandCell` math + tooltip copy, R7-R9 | unit | `npx vitest run src/lib/bandCell.test.ts` | ❌ Wave 0 |
| UI-03 | FDR cell coloring + blank-GW dash, R20-R24 | component | `npx vitest run src/routes/Fixtures.test.tsx` | ❌ Wave 0 |
| UI-04 | Watchlist mode-note branches + progress bar, R25-R31 | unit + component | `npx vitest run src/routes/Prices.test.tsx` | ❌ Wave 0 |
| UI-05 | League GD sign + leaders slice, R32-R34 | component | `npx vitest run src/routes/League.test.tsx` | ❌ Wave 0 |
| UI-05 | Scoreboard empty-vs-error distinction, R35-R38 (Pitfall 2) | component | `npx vitest run src/routes/Scoreboard.test.tsx` | ❌ Wave 0 |
| UI-05 | Differentials filter + `maxHi` floor, R39-R41 | component | `npx vitest run src/routes/Differentials.test.tsx` | ❌ Wave 0 |
| UI-05 | Methodology renders bundled markdown, no fetch | component | `npx vitest run src/routes/Methodology.test.tsx` | ❌ Wave 0 |
| UI-06 | GW banner states (loading/populated/passed/failed), `{rel}`/`{freshness}` format tables | unit + component | `npx vitest run src/components/GwBanner.test.tsx` | ❌ Wave 0 |
| UIX-02 | Theme resolution (system/explicit), persistence, `matchMedia` live update | unit | `npx vitest run src/lib/theme.test.ts` | ❌ Wave 0 |
| D-09 | Status-flag tooltip (hover/focus/click-toggle, `aria-*`) | component | `npx vitest run src/lib/statusFlag.test.tsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the single new/changed test file's quick-run command above
- **Per wave merge:** `cd frontend && npm test` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/lib/sortable.ts` + `.test.ts` — the ported `makeSortable` comparator, R1-R3, first test written against the verified polarity (Pitfall 1)
- [ ] `frontend/src/lib/bandCell.ts` + `.test.ts` — R7-R9
- [ ] `frontend/src/lib/format.ts` — small `.toFixed`/`.toLocaleString` wrappers matching R14-R16, R23-R24, R28-R29 exactly per-page
- [ ] `frontend/src/lib/statusFlag.tsx` + `.test.tsx` — R4-R6, D-09's accessible-tooltip upgrade
- [ ] `frontend/src/lib/deadline.ts` + `.test.ts` — `{abs}` port (verbatim `fmtDeadline` format string) + D-19's `{rel}` graduated table + D-20's `{freshness}` table
- [ ] `frontend/src/lib/theme.ts` + `.test.ts` — `useTheme()` hook, localStorage read/write-failure degradation (D-16's private-browsing case), `matchMedia` change listener
- [ ] Fixture JSON: one file per `web/data/*.json` shape used this phase, small and hand-authored (2-5 rows) rather than copying the full 154KB `xp_table.json` — include a `scoreboard.json` populated-state fixture per Open Question 2 (currently absent from live data), and `heuristic`/trained-mode `watchlist.json` fixtures per Assumption A3
- [ ] Framework install: none — Vitest/Testing Library already installed and proven (existing `PageShell.test.tsx`, `ErrorState.test.tsx`, `routeIsolation.test.tsx`)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V2 Authentication | No | No login/auth surface on any of these 7 pages |
| V3 Session Management | No | No session state introduced this phase |
| V4 Access Control | No | All data is public (the same JSON contract vanilla already serves publicly) |
| V5 Input Validation | Yes | The xP table's search input and Differentials' ownership slider are client-side-only filters over already-fetched public JSON — no server round trip, so injection risk is minimal, but the output-encoding half of V5 still applies: React's JSX text interpolation auto-escapes all rendered values by default; the one place this discipline could be bypassed is the methodology renderer, where `react-markdown`'s explicit no-`dangerouslySetInnerHTML` design is the control (see Don't Hand-Roll) |
| V6 Cryptography | No | No cryptographic operations this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Reflected/stored XSS via markdown content | Tampering / Information Disclosure | `react-markdown` renders to real DOM nodes via `remark`/`rehype`, never `dangerouslySetInnerHTML` — verified as the package's core design property (33.7M weekly downloads, actively maintained); do not introduce a raw-HTML injection path even for developer-authored content |
| Search/filter input echoed unsafely | Tampering | Not applicable here — the search query string is used only for `.toLowerCase().includes()` comparison (never rendered back into the DOM as HTML, confirmed by reading `web/index.html`'s script); React's default JSX escaping covers any future case where a query string *is* echoed |
| `localStorage` tampering (theme value) | Tampering | Low severity — `localStorage["fpl-theme"]` only ever drives a `light`/`dark`/`system` class toggle; a tampered value simply falls through to `system` resolution rather than executing anything, per D-16's write-failure degradation path |

## Sources

### Primary (HIGH confidence — direct file reads and executed code, this session)
- `web/assets/app.js` — full file read; `makeSortable` comparator executed in Node to verify sort-direction polarity (Pitfall 1)
- `web/index.html`, `web/fixtures.html`, `web/prices.html`, `web/league.html`, `web/scoreboard.html`, `web/differentials.html`, `web/methodology.html` — all seven page scripts + markup read directly
- `web/assets/style.css` — full file read for the conditional-class/color-token inventory
- `web/data/meta.json`, `xp_table.json`, `captains.json`, `fixtures.json`, `watchlist.json`, `standings.json`, `leaders.json` — live sample data read directly; `web/data/scoreboard.json` confirmed absent via `ls`
- `predict/scoreboard.py` — read directly for `scoreboard.json`'s exact schema (entries/summary field names and optionality)
- `frontend/src/lib/api.ts`, `frontend/src/router.tsx`, `frontend/src/components/PageShell.tsx`, `frontend/src/index.css`, `frontend/src/routes/XpTable.tsx`, `frontend/src/components/{ErrorState,EmptyState,Spinner,PlaceholderPage}.tsx`, `frontend/vite.config.ts`, `frontend/vitest.config.ts`, `frontend/src/routes/routeIsolation.test.tsx`, `frontend/src/test/harness.test.tsx` — Phase 1 scaffold read directly to confirm established conventions this phase must extend, not replace
- `gsd-tools query package-legitimacy check --ecosystem npm react-markdown @fontsource/archivo @fontsource/ibm-plex-sans @fontsource/ibm-plex-mono` — all four `OK`
- `npm view <pkg> version` (react-markdown, @fontsource/archivo, @fontsource/ibm-plex-sans, @fontsource/ibm-plex-mono, lucide-react) — live registry check, 2026-09-01
- `npm view react-markdown scripts.postinstall` — empty (no postinstall script)

### Secondary (MEDIUM confidence)
- [Flexible Dark Mode with Tailwind CSS v4 Custom Variants](https://schoen.world/n/tailwind-dark-mode-custom-variant) — `@custom-variant dark (&:where(.dark, .dark *));` class-strategy syntax, cross-checked against the UI-SPEC's already-specified approach
- [Tailwind Dark Mode: class vs data-theme Strategy Comparison](https://eastondev.com/blog/en/posts/dev/20260328-tailwind-dark-mode-comparison/) — confirms Tailwind v4's config moved out of `tailwind.config.js` into CSS-first `@custom-variant`
- [react-markdown — npm](https://www.npmjs.com/package/react-markdown), [GitHub — remarkjs/react-markdown](https://github.com/remarkjs/react-markdown) — confirms `remark`/`rehype`-based rendering with no `dangerouslySetInnerHTML`, basic `<ReactMarkdown>{content}</ReactMarkdown>` usage pattern

### Tertiary (LOW confidence)
- None — every claim in this document is either a direct file read, an executed verification, or a cited official/near-official source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package already installed, or verified live against the npm registry with a clean package-legitimacy verdict
- Architecture: HIGH — the entire architecture is a port of already-read, already-running vanilla code; no novel architectural decisions this phase beyond D-01..D-22 (already locked in CONTEXT.md)
- Pitfalls: HIGH — the highest-value pitfall (sort-direction polarity) was verified by executing the real comparator, not by reading a description of it; every other pitfall traces to a specific file:line read this session

**Research date:** 2026-09-01
**Valid until:** Until `web/assets/app.js` or any of the 7 vanilla page scripts change (this research is a snapshot of their exact current behavior) — re-verify the Parity Rule Inventory if the vanilla site is touched before this phase's plans execute. Package versions valid ~30 days (stable, low-churn ecosystem for these packages).
