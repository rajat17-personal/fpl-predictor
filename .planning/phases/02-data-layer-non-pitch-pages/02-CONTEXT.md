# Phase 2: Data Layer & Non-Pitch Pages - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Rebuild seven of the eight pages (xP table/index, fixtures, prices, league, scoreboard, differentials, methodology) in the Phase 1 React app at **verified behavioral parity** with the vanilla site, consuming the same `web/data/*.json` contract fetched at runtime. Add the two cross-page features scoped here: a gameweek meta banner with a live deadline countdown (UI-06) and a persistent dark mode toggle (UIX-02). The team page and everything pitch-related is Phase 3. E2E/Playwright coverage is Phase 4 — this phase's verification is Vitest-level.

</domain>

<decisions>
## Implementation Decisions

### Parity model
- **D-01:** **Behavioral parity**, not visual cloning — same data, same sort/filter/format semantics verified against an enumerated inventory of the vanilla rules; markup and visuals are React-idiomatic using the Phase 1 design tokens. Phase 7 compares information + behavior, not pixels.
- **D-02:** The xP table keeps the vanilla **top-50 "free preview" cap** and the Pro-tier teaser copy. The full table stays behind the future paid tier.
- **D-03:** All page copy (headlines, explainers, footer disclaimer, Pro teaser) ports **verbatim**. Any rewrite is a ledger entry.
- **D-04:** Every intentional deviation from vanilla is logged as a one-line entry in a **deviation ledger**: `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md`. Phase 7's side-by-side comparison treats this ledger as the list of explained deltas. — **Reversibility:** costly — Phase 7 (CUT-01) depends on this ledger existing and being complete; skipping entries mid-phase can't be reconstructed later.
- **D-05:** Parity is verified by **unit tests per inventoried rule** — each `.sort()`, `.toFixed()`, secondary sort key, and conditional class from the vanilla inventory becomes a Vitest assertion against fixture JSON. The inventory survives as executable regression coverage that Phase 4 E2E builds on.
- **D-06:** The **xP table is the flagship** — it gets the deepest test coverage (sorting, filtering, band rendering).

### Interaction & degradation behavior
- **D-07:** Table sort/filter state is **ephemeral component state** — resets on reload/navigation exactly like vanilla. No URL params, no localStorage persistence.
- **D-08:** Data-load failures show **rich error states** using the Phase 1 ErrorState/EmptyState components with actionable per-page messages (deliberate improvement over vanilla's silent blanks; ledger entry).
- **D-09:** Status-flag injury news gets an **accessible tooltip** (tap/click-friendly, keyboard-accessible popover or inline reveal) instead of vanilla's desktop-only `title` attribute (ledger entry; also pre-work for Phase 3's mobile-usable tables).

### Rendering & assets
- **D-10:** **Pure CSR** for all pages this phase. No prerender/SSG machinery; data stays runtime-fetched so prerendering remains addable later without rework.
- **D-11:** Per-page titles and meta descriptions handled by a **small route helper** (e.g., a `usePageMeta` hook reading a per-route table), porting vanilla's values verbatim. No helmet-style dependency.
- **D-12:** Fonts (Archivo, IBM Plex Sans/Mono) are **self-hosted** (woff2 via Fontsource or static files) — no Google Fonts CDN request. — **Reversibility:** reversible, but note any new npm package must pass the package-legitimacy gate.
- **D-13:** The methodology page is **markdown-sourced** — content lives in a `.md` file rendered through a markdown pipeline (renderer choice is planner's; the package-legitimacy gate applies).

### Dark mode (UIX-02)
- **D-14:** Default theme is **system preference** (`prefers-color-scheme`); an explicit user choice overrides it.
- **D-15:** The toggle is **three-state: Light / Dark / System**.
- **D-16:** Persistence via **localStorage plus an inline head script** in `index.html` that applies the theme class before React mounts — no flash of wrong theme on reload.
- **D-17:** Build the **full dark token palette** this phase — surfaces, text, borders, plus dark-safe variants of the semantic colors (FDR 1–5 green→red scale, price rise/fall indicators, status flags, band cells). Phase 3's pitch UI inherits this palette rather than reworking it. — **Reversibility:** costly — Phase 3 components will be written against these tokens; a later palette restructure touches every themed component.

### GW meta banner (UI-06)
- **D-18:** Placement: the **upgraded header chip** — vanilla's deadline chip location in the shared header (PageShell), now showing GW number, countdown, and data freshness. Not a separate banner bar.
- **D-19:** Countdown **ticks per minute** (per-second inside the final hour if cheap). Genuinely live, satisfies UI-06's "live deadline countdown".
- **D-20:** The banner includes a **"generated …" freshness line** from `meta.json`'s `generated_utc` — a deliberate improvement (ledger entry).
- **D-21:** When the deadline passes mid-session, the chip flips to a clear **"GW{n} deadline passed"** state. No speculative refetching — the next GW appears when the weekly export refreshes `meta.json`.
- **D-22:** If `meta.json` fails to load, the chip shows a **quiet "deadline TBC" fallback** and pages render normally (matches vanilla's graceful degradation; the rich-error-state rule D-08 applies to page data, not the banner).

### Claude's Discretion
- Markdown renderer choice for the methodology page (D-13) — subject to the package-legitimacy approval gate.
- Font delivery mechanism (Fontsource packages vs. self-hosted static woff2 files) — same gate applies.
- Tooltip implementation for D-09 (popover vs. inline reveal) — pick the cheapest accessible pattern.
- TanStack Query caching/refetch policy for the JSON files — not discussed; standard sensible defaults.
- Per-second ticking inside the final hour (D-19) — include only if it falls out naturally.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Parity source of truth (the vanilla site)
- `web/assets/app.js` — shared helpers to replicate: `makeSortable` (sort semantics incl. null handling `?? -1e9`, direction toggling), `statusFlag`, `bandCell` (p10/p90 interval rendering + exact tooltip copy), `fmtDeadline`, `initChrome`
- `web/index.html` — xP table page: position chips + search filter logic, top-50 slice, column set, number formats, captains table; all page logic is in the inline `<script type="module">`
- `web/fixtures.html` — FDR ticker page (inline script)
- `web/prices.html` — watchlist rise/fall page (inline script)
- `web/league.html` — league page (inline script)
- `web/scoreboard.html` — accuracy scoreboard page (inline script)
- `web/differentials.html` — differentials page (inline script)
- `web/methodology.html` — methodology prose (source content for the markdown port)
- `web/assets/style.css` — vanilla styling; source for conditional-class inventory and semantic colors needing dark-safe variants

### Data contract
- `web/data/` — the JSON export contract (`xp_table.json`, `captains.json`, `fixtures.json`, `watchlist.json`, `standings.json`, `leaders.json`, `meta.json`, `chips.json`, `squad.json`); consumed unchanged, fetched at runtime, never bundled
- `frontend/src/lib/api.ts` — the typed fetch layer + `MetaResponse` interface mirroring `meta.json`

### Design & scaffold contract
- `.planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md` — Phase 1 design contract: tokens, routes table, shell chrome, containment geometry (68rem cap per gap G-01-3)
- `frontend/src/` — the Phase 1 scaffold: `router.tsx`, `routes/*.tsx` placeholders, `components/PageShell.tsx`, `ErrorState`/`EmptyState`/`Spinner`/`NotFoundPage`, Vitest harness

### Codebase maps
- `.planning/codebase/CONVENTIONS.md` — naming/style conventions
- `.planning/codebase/STRUCTURE.md` — repo layout
- `.planning/codebase/STACK.md` — stack and versions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PageShell` + header chrome (Phase 1): owns the header where the upgraded GW chip (D-18) lands; 68rem containment already regression-tested
- `ErrorState` / `EmptyState` / `Spinner` / `NotFoundPage`: the rich-error-state building blocks for D-08 (ErrorState is deliberately router-hook-free and unit-testable)
- `lib/api.ts` `fetchJson`/`fetchApi`: relative-path fetch discipline already ported from vanilla's `loadJSON`
- TanStack Query v5 + React Router 7 already wired; Vitest + Testing Library harness ready for the per-rule parity tests (D-05)
- Phase 1 design tokens (Tailwind 4.x): the base the dark palette (D-17) extends

### Established Patterns
- Vanilla page logic is small and fully enumerable: 102-line shared `app.js` + one inline module script per page — the parity inventory (roadmap research flag) is a bounded task
- All frontend installs are pinned `--save-exact` and gated by the human-approved package-legitimacy list — any new package (markdown renderer, Fontsource) needs that gate
- Vanilla nav order/labels and NAV_LINKS were settled in Phase 1 (UI-SPEC Routes-table order, vanilla label copy) — do not re-litigate
- `web/data/*.json` is fetched at runtime through the dev proxy (`/data` → uvicorn) — never bundled

### Integration Points
- `frontend/src/routes/*.tsx` — seven placeholder routes get real implementations (Team.tsx stays a placeholder for Phase 3)
- `frontend/src/components/PageShell.tsx` — GW banner chip + dark mode toggle both mount here
- `frontend/index.html` — inline theme script (D-16) and self-hosted font preloads (D-12)
- `frontend/src/index.css` / token layer — dark palette variables (D-17)

</code_context>

<specifics>
## Specific Ideas

- The xP table is the flagship page — when trading off effort, it wins (D-06)
- The freshness line (D-20) is a trust-builder for the paid product — "predictions generated 2h ago" phrasing from `meta.json.generated_utc`
- Keep vanilla's exact `bandCell` tooltip copy ("actual score lands between … in 8 gameweeks out of 10") — copy is verbatim per D-03

</specifics>

<deferred>
## Deferred Ideas

- **Pre-launch SEO pass** — prerender the shell of methodology/scoreboard/differentials, plus `sitemap.xml` and `robots.txt`. Deferred to a later milestone; CSR-with-runtime-data keeps it addable without rework.

</deferred>

---

*Phase: 2-Data Layer & Non-Pitch Pages*
*Context gathered: 2026-09-01*
