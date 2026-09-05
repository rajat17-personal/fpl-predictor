# Phase 3: Pitch Renderer & Squad Views - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the eighth and final page — the team page — around a new FPL-style pitch renderer. The pitch shows squads in formation-driven rows with a bench; player cards carry a neutral generated kit, name, price, xP with its p10/p90 interval, and C/VC badges. From one `/team` route users see the model's recommended squad by default, load any team by entry ID, lock/exclude players and request solves (transfers + XI update on the pitch), get a rate-my-team visual diff against the optimal squad, and see chip timing with a "why this GW" explanation. Both the pitch and the data tables stay usable at phone width (UI-07).

**Critical framing:** unlike Phase 2, this is mostly *new UI design*, not parity porting — vanilla has no pitch. Only the rate/plan flows (`web/team.html`) have vanilla behavior and copy to preserve. E2E coverage of these flows is Phase 4; this phase's verification is Vitest-level (per Phase 2 precedent D-05).

</domain>

<decisions>
## Implementation Decisions

### Kit & shirt sourcing (PITCH-01)
- **D-01:** Shirts are **neutral generated kits** — self-made generic SVG shirts in club colors, no crests, no sponsor marks, fully self-hosted. The user explicitly chose this **over** FPL CDN imagery: no dependency on FPL-served assets, and the legally cleanest posture for the paid product. The roadmap's devtools-CDN-capture research flag is thereby **moot** — no CDN URLs are needed. — **Reversibility:** costly — the PITCH-01 decision doc, the disclaimer posture, and every card component build on self-hosted SVGs; switching to CDN imagery later reopens the trademark review.
- **D-02:** Kit style is **colors + basic pattern** — one SVG shirt shape parameterized by a hand-maintained ~20-club map (primary/secondary color pair + pattern enum: plain / stripes / hoops / sleeves). Recognizable at a glance while staying crest-free.
- **D-03:** The non-affiliation disclaimer lives in the **global footer on every page** (shared PageShell footer), not just the team page. Strongest posture for the eventual payment-gateway review.
- **D-04:** The PITCH-01 "documented decision" deliverable (asset-sourcing rationale + trademark posture) is written during planning/execution as a committed doc — success criterion 1 requires it to exist.

### Pitch & player card design (PITCH-02, UIX-01, UI-07)
- **D-05:** The pitch is **FPL-style green** — green gradient surface, white pitch markings (center circle, penalty box), formation rows on top, bench strip below. Requires dark-mode-safe green variants added to the Phase 2 dark token palette (extends D-17 of `02-CONTEXT.md`; do not restructure that palette).
- **D-06:** The p10/p90 interval renders as an **always-visible compact range line** (mono font, e.g. `2.4–9.1`) under the xP value on each card — no interaction required to see it (UIX-01).
- **D-07:** At phone width, **cards shrink to fit** — the full formation (worst case 5-across plus the 4-slot bench) always fits the viewport width, like the official FPL app. Names truncate; price/xP stay; the interval line may fall back to tap-reveal (Phase 2's D-09 accessible popover pattern) at the smallest sizes.
- **D-08:** Vice-captain is **derived in the UI**: VC = the starter with the highest `xp_capt` (joined from `xp_table.json` by `player_code`) who isn't the captain. No data-contract or API change; logic lives in one tested utility. — **Reversibility:** reversible — but note the invariant: `web/data/*.json` is consumed unchanged, so "add VC to the export" was explicitly rejected.

### Team page structure (PITCH-03, UIX-03)
- **D-09:** One `/team` route with **three tabs: Squad (default) / Rate my team / Chips**. Squad hosts the pitch + solver; Rate hosts the visual diff + vanilla rate content; Chips hosts the timeline. Each tab lazy-fetches its own data. The locked 8-route structure is unchanged.
- **D-10:** **No auto-loading of any user's team.** The default Squad tab renders `squad.json` — the model's recommended squad of the week — clearly labeled (e.g. "Model squad · GW3"), with the entry input inviting "load your own team". The user explicitly rejected auto-loading entry 6980093 ("would not want a random team to show up"); 6980093 remains only a placeholder/example, not an auto-loaded default.
- **D-11:** URL state is **`?entry=` + `?tab=`** (e.g. `/team?entry=1234567&tab=rate`). An entry deep link loads that squad; a rate deep link auto-runs the rating — preserving vanilla's shareable `team.html?entry=` auto-rating behavior. Everything else (locks, solve results) stays ephemeral per Phase 2's D-07.
- **D-12:** Nav label renames from vanilla's "Rate my team" to **"My team"** — the page outgrew its vanilla name. Requires a one-line PARITY-DEVIATIONS ledger entry (Phase 2's D-04 discipline). — **Reversibility:** reversible — copy change plus ledger entry.

### Solver UX (PITCH-03)
- **D-13:** Lock/exclude is **tap-a-card → action popover** (Lock / Exclude / clear, plus player detail like news and ownership), reusing the D-09 accessible popover pattern. Locked/excluded cards get visible badge states.
- **D-14:** Solver knobs exposed: **essentials only** — free transfers (prefilled from the API's estimate, editable), max transfers, and plan horizon. Mode/budget use server defaults.
- **D-15:** Solve wait is **inline status + honest copy** — button disables, an inline status line appears, the pitch stays visible. Vanilla's wait copy carries over per D-03 verbatim-copy discipline (including "a fresh horizon takes ~10-60s while future gameweeks are predicted" for plans).
- **D-16:** Solve results **update the pitch in place** — the post-solve squad re-renders with incoming players badged IN, plus a compact results bar (sells → buys pairs, hit cost, bank after, XI xP, captain). One pitch is the single source of truth.
- **D-17:** Users **iterate freely**: locks/excludes persist across re-solves; a "Reset to loaded squad" action restores the as-loaded team and clears marks. Solve results are a local preview — nothing is ever persisted.

### Rate-my-team & chip timing (PITCH-04, UIX-03)
- **D-18:** The visual diff is **one pitch + swap overlays** — the user's squad on the pitch with diff markers: players the ideal squad drops get a red "out" treatment, suggested buys appear as ghost/insert cards, and a swap list (sell → buy, xP gain) sits beside it. Not side-by-side pitches.
- **D-19:** **All vanilla rate content carries over**: the four tiles (team score /100, season points/rank, captain, best move), the best-XI-for-this-GW view, and the multi-week "Plan transfers" flow — copy verbatim per D-03. The pitch diff is the new centerpiece; nothing users had disappears at cutover (CUT-01).
- **D-20:** Rate analysis fetches **on demand when the Rate tab opens** (then cached by TanStack Query) — no wasted triple-solve on every team load. Exception: a `?tab=rate` deep link auto-fetches (D-11).
- **D-21:** Chip timing renders as a **GW timeline strip** — a horizontal season timeline (current GW → 38) with DGW/BGW gameweeks highlighted as markers and callout badges, and `chips.json`'s `note` as the headline "why this GW" explanation. Derives entirely from the existing `note` + `structure` fields — no contract change; per-chip recommendation panels were explicitly rejected as requiring invented data.

### Claude's Discretion
- Whether the default model-squad pitch is view-only or supports lock/exclude + from-scratch wildcard solves (`/api/solve` with `entry: null`) — user declined to discuss; pick what keeps scope sane.
- GK kit differentiation, fallback colors for unmapped clubs, and exact kit SVG construction.
- Tab component implementation and how `?tab=` syncs with it.
- Exact IN-badge/out-treatment styling in solve results and the rate diff.
- How the transfers summary bar formats hits/bank (mirror vanilla's plan-flow copy where it exists).
- Where the PITCH-01 decision doc lives (e.g. `docs/` vs `.planning/`), as long as it's committed and findable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Parity source (the only vanilla behavior this phase preserves)
- `web/team.html` — vanilla rate-my-team + plan flows: copy (ports verbatim per Phase 2 D-03), tiles, `squadCards` grouping, FT prefill note, wait copy, `?entry=` deep-link behavior, `pairMoves` sell→buy pairing logic
- `web/assets/app.js` — shared helpers (`initChrome`, `detectApiBase`); `squadCards`/`pairMoves` live in team.html's inline script
- `web/assets/style.css` — `squadgrid`/`squadcard`/`tiles` styles (reference only; pitch is new design)

### Data contract (consumed unchanged, fetched at runtime)
- `web/data/squad.json` — recommended squad: 15 rows with `player_code`, `name`, `team`, `position`, `price_m`, `xp`, `starting`, `captain`. **No VC, no p10/p90, no formation field** — formation is derived from starters' positions; intervals and `xp_capt` join from `xp_table.json` by `player_code` (D-06, D-08)
- `web/data/xp_table.json` — per-player `p10`/`p90`/`xp_capt`/`team_short`/`status`/`news` keyed by `player_code` (the join source)
- `web/data/chips.json` — only `note` (string) + `structure` (per-GW `dgw_clubs`/`bgw_clubs`) — the entire data basis for the Chips tab (D-21)
- `web/data/meta.json` — `gw`, `deadline_utc`, `generated_utc` for the "Model squad · GW{n}" label

### API surface
- `api/main.py` — response shapes to type in `lib/api.ts`: `/api/team/{entry}` (picks, bank, value, manager), `/api/solve` (kind: squad vs transfers; locks/excludes; `_squad_rows` shape), `/api/plan` (weeks with `xi_p10`/`xi_p90`, 10–60s), `/api/rate/{entry}` (score, tiles data, best_move, xi rows). `/api/solve`, `/api/plan`, `/api/rate` sit behind the `require_key` stub (open mode when `FPL_API_KEYS` unset)

### Prior phase contracts
- `.planning/phases/02-data-layer-non-pitch-pages/02-CONTEXT.md` — carried-forward decisions: D-03 verbatim copy, D-04 deviation ledger, D-07 ephemeral state, D-08 rich error states, D-09 accessible popover, D-17 dark palette
- `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` — the ledger; this phase adds at least the "My team" nav rename (D-12)
- `.planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md` — design tokens, routes table, shell chrome, 68rem containment
- `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/STACK.md` — conventions, layout, stack

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/routes/Team.tsx` — the placeholder this phase replaces; router/nav entry already wired
- `frontend/src/lib/api.ts` — typed fetch layer (`fetchJson`/`fetchApi`); extend with squad/solve/plan/rate types
- `frontend/src/lib/bandCell.ts` + `BandCell.tsx` — existing interval rendering + exact tooltip copy (the card range line is a sibling, not a reuse — but keep copy consistent)
- `frontend/src/lib/statusFlag.tsx` — the accessible tap-reveal pattern (D-09) to reuse for the card popover
- `ErrorState` / `EmptyState` / `Spinner` — rich error states per Phase 2 D-08
- TanStack Query v5 — on-demand per-tab fetching + caching (D-20); React Router 7 — `useSearchParams` for `?entry=`/`?tab=` (D-11)
- Phase 2 dark token palette — the base D-05's pitch greens extend

### Established Patterns
- Package-legitimacy gate: any new npm package needs the blocking human approval gate with exact pins (`--save-exact`) — budget for zero or few new packages; the pitch/kits are hand-built SVG/CSS
- Per-rule Vitest coverage (Phase 2 D-05): VC derivation, formation derivation, kit color map, swap pairing, and timeline DGW/BGW detection are all unit-testable utilities
- Verbatim copy + deviation ledger discipline (D-03/D-04) applies to everything kept from `web/team.html`

### Integration Points
- `frontend/src/components/PageShell.tsx` — global footer disclaimer (D-03 of this phase) mounts here; nav label rename (D-12)
- `frontend/src/router.tsx` — Team route stays; no new routes (tabs are internal state + `?tab=`)
- `frontend/src/index.css` — dark-safe pitch green tokens extend the existing `@theme` block

</code_context>

<specifics>
## Specific Ideas

- Default pitch = the model's recommended squad, clearly labeled — "the pitch is never empty, it demos the product's core value"
- The user does *not* want any real user's team auto-loading on arrival ("would not want a random team to show up every time")
- Official-FPL-app familiarity is the design north star for the pitch (green pitch, 5-across shrinking cards on phones)
- Keep vanilla's honest solver-wait copy, including the 10–60s warning for fresh horizons

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (The pre-launch SEO pass deferred in Phase 2 remains deferred.)

</deferred>

---

*Phase: 3-Pitch Renderer & Squad Views*
*Context gathered: 2026-09-02*
