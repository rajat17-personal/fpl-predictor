# Phase 2: Data Layer & Non-Pitch Pages - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-01
**Phase:** 2-Data Layer & Non-Pitch Pages
**Areas discussed:** Parity strictness, CSR vs prerender, Dark mode design, GW banner & countdown

---

## Parity strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Behavioral parity (Recommended) | Same data, same sort/filter/format semantics (verified against the enumerated inventory), React-idiomatic markup + Phase 1 tokens | ✓ |
| Strict visual clone | Reproduce vanilla layout/typography as closely as possible | |
| Improve freely | Treat vanilla as a data-requirements spec only | |

**User's choice:** Behavioral parity

| Option | Description | Selected |
|--------|-------------|----------|
| Keep top-50 cap (Recommended) | Same cap, same Pro-tier framing | ✓ |
| Show full table | Drop the cap — everything free pre-launch | |
| Full table + visual cutoff | Render all rows, mark rows past 50 as Pro preview | |

**User's choice:** Keep top-50 cap

| Option | Description | Selected |
|--------|-------------|----------|
| Deviation ledger doc (Recommended) | PARITY-DEVIATIONS.md in the phase dir, one-line entry per intentional difference | ✓ |
| Inline code comments | Mark deviations in the React source | |
| Rely on the parity checklist | Inventory doubles as the record | |

**User's choice:** Deviation ledger doc

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral state (Recommended) | Component state only, resets on reload/navigation like vanilla | ✓ |
| URL query params | Shareable/bookmarkable views | |
| Persist per-page | localStorage sort/filter memory | |

**User's choice:** Ephemeral state

| Option | Description | Selected |
|--------|-------------|----------|
| Rich error states (Recommended) | Phase 1 ErrorState/EmptyState with actionable messages; ledger deviation | ✓ |
| Mimic vanilla | Blank/partial render on failure | |

**User's choice:** Rich error states

| Option | Description | Selected |
|--------|-------------|----------|
| Unit tests per rule (Recommended) | Each inventoried rule becomes a Vitest assertion against fixture JSON | ✓ |
| Checklist sign-off | Manual side-by-side markdown checklist | |
| Hybrid | Tests for mechanics, checklist for visual judgments | |

**User's choice:** Unit tests per rule

| Option | Description | Selected |
|--------|-------------|----------|
| Accessible tooltip (Recommended) | Tap/click-friendly, keyboard-accessible reveal for injury news | ✓ |
| Keep title attribute | Desktop-hover only, exact vanilla | |
| You decide | Claude picks by effort | |

**User's choice:** Accessible tooltip

| Option | Description | Selected |
|--------|-------------|----------|
| No, defer (Recommended) | Freshness surfacing pairs with Phase 6 observability | |
| Yes, in the GW banner | "generated …" line in the new meta banner | ✓ |

**User's choice:** Yes, in the GW banner — user went against the recommendation; freshness is a cheap trust-builder

| Option | Description | Selected |
|--------|-------------|----------|
| Self-host (Recommended) | Bundle woff2, no third-party request, deterministic in CI | ✓ |
| Keep Google CDN | Exact vanilla behavior | |
| You decide | | |

**User's choice:** Self-host

| Option | Description | Selected |
|--------|-------------|----------|
| Verbatim (Recommended) | Word-for-word copy port; rewrites are ledger entries | ✓ |
| Light copyedit allowed | Claude may tighten copy while porting | |

**User's choice:** Verbatim

| Option | Description | Selected |
|--------|-------------|----------|
| You decide (Recommended) | Likely plain JSX unless markdown earns its keep | |
| Plain JSX | Port HTML straight into the route component | |
| Markdown-sourced | Content in .md rendered at build/runtime | ✓ |

**User's choice:** Markdown-sourced — user went against the recommendation; prefers editable content

| Option | Description | Selected |
|--------|-------------|----------|
| No, all equal | Treat all seven uniformly | |
| xP table | Flagship page, deepest test coverage | ✓ |
| Prices page | Subtlest data handling outside xP | |
| Scoreboard | Public trust page | |

**User's choice:** xP table

---

## CSR vs prerender

| Option | Description | Selected |
|--------|-------------|----------|
| Pure CSR now (Recommended) | All pages client-rendered; prerendering addable later | ✓ |
| Prerender SEO trio | SSG methodology/scoreboard/differentials shells | |
| Prerender all shells | SSG every route with hydration | |

**User's choice:** Pure CSR now

| Option | Description | Selected |
|--------|-------------|----------|
| Small route helper (Recommended) | usePageMeta hook + per-route table, vanilla values verbatim | ✓ |
| Helmet-style library | react-helmet-async or similar | |
| Skip meta for now | Titles only | |

**User's choice:** Small route helper

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, defer it (Recommended) | Note prerender + sitemap/robots as pre-launch SEO backlog | ✓ |
| No, drop it | CSR fine indefinitely | |

**User's choice:** Yes, defer it

---

## Dark mode design

| Option | Description | Selected |
|--------|-------------|----------|
| System preference (Recommended) | Respect prefers-color-scheme; toggle overrides | ✓ |
| Light default | Everyone starts light like vanilla | |
| Dark default | Lead with dark | |

**User's choice:** System preference

| Option | Description | Selected |
|--------|-------------|----------|
| localStorage + head script (Recommended) | Inline script applies theme class before React mounts — no flash | ✓ |
| localStorage, React-applied | Effect-applied, accepts brief flash | |
| You decide | | |

**User's choice:** localStorage + head script

| Option | Description | Selected |
|--------|-------------|----------|
| Light/Dark/System (Recommended) | Three-state control with return-to-auto | ✓ |
| Binary light/dark | Two-state switch | |

**User's choice:** Light/Dark/System

| Option | Description | Selected |
|--------|-------------|----------|
| Full token palette (Recommended) | Complete dark set incl. dark-safe semantic colors (FDR, rise/fall, flags); Phase 3 inherits | ✓ |
| Pages-only palette | Dark-theme just these seven pages | |
| You decide | | |

**User's choice:** Full token palette

---

## GW banner & countdown

| Option | Description | Selected |
|--------|-------------|----------|
| Ticking per minute (Recommended) | 60s re-render; per-second inside final hour if cheap | ✓ |
| Compute per navigation | Refresh on route change only | |
| Ticking per second | Full HH:MM:SS always | |

**User's choice:** Ticking per minute

| Option | Description | Selected |
|--------|-------------|----------|
| Header chip, upgraded (Recommended) | Vanilla's chip location, now GW + countdown + freshness | ✓ |
| Dedicated banner bar | Slim full-width strip under the header | |
| You decide | | |

**User's choice:** Header chip, upgraded

| Option | Description | Selected |
|--------|-------------|----------|
| 'Passed' state (Recommended) | Flips to "GW{n} deadline passed"; no fake data | ✓ |
| Refetch meta on pass | Refetch hoping for next GW | |
| You decide | | |

**User's choice:** 'Passed' state

| Option | Description | Selected |
|--------|-------------|----------|
| Quiet fallback (Recommended) | "deadline TBC" chip, pages render normally | ✓ |
| Visible warning | Explicit unavailable state in the banner | |

**User's choice:** Quiet fallback

---

## Claude's Discretion

- Markdown renderer choice for methodology (package-legitimacy gate applies)
- Font delivery mechanism (Fontsource vs. static woff2)
- Tooltip implementation pattern for status flags
- TanStack Query caching/refetch policy (not discussed)
- Per-second ticking inside the final hour — only if it falls out naturally

## Deferred Ideas

- Pre-launch SEO pass: prerender methodology/scoreboard/differentials shells, sitemap.xml, robots.txt
