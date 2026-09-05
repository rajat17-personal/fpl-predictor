# Phase 3: Pitch Renderer & Squad Views - Research

**Researched:** 2026-09-02
**Domain:** React pitch/squad UI over an existing FastAPI ILP solver; hand-built SVG kit rendering; no new runtime dependencies
**Confidence:** HIGH (grounded directly in read source: `api/main.py`, `optimize/squad_ilp.py`, `optimize/transfers.py`, `web/team.html`, `frontend/src/**`, and live `web/data/*.json`)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Kit & shirt sourcing (PITCH-01)**
- D-01: Shirts are **neutral generated kits** — self-made generic SVG shirts in club colors, no crests, no sponsor marks, fully self-hosted. Chosen **over** FPL CDN imagery. The roadmap's devtools-CDN-capture research flag is **moot** — no CDN URLs are needed. Reversibility: costly.
- D-02: Kit style is **colors + basic pattern** — one SVG shirt shape parameterized by a hand-maintained ~20-club map (primary/secondary color pair + pattern enum: plain / stripes / hoops / sleeves).
- D-03: The non-affiliation disclaimer lives in the **global footer on every page** (shared PageShell footer), not just the team page.
- D-04: The PITCH-01 "documented decision" deliverable (asset-sourcing rationale + trademark posture) is written during planning/execution as a committed doc — success criterion 1 requires it to exist.

**Pitch & player card design (PITCH-02, UIX-01, UI-07)**
- D-05: The pitch is **FPL-style green** — green gradient surface, white pitch markings (center circle, penalty box), formation rows on top, bench strip below. Requires dark-mode-safe green variants added to the Phase 2 dark token palette (extends D-17 of `02-CONTEXT.md`; do not restructure that palette).
- D-06: The p10/p90 interval renders as an **always-visible compact range line** (mono font, e.g. `2.4–9.1`) under the xP value on each card — no interaction required (UIX-01).
- D-07: At phone width, **cards shrink to fit** — the full formation (worst case 5-across plus the 4-slot bench) always fits the viewport width, like the official FPL app. Names truncate; price/xP stay; the interval line may fall back to tap-reveal (D-09 accessible popover pattern) at the smallest sizes.
- D-08: Vice-captain is **derived in the UI**: VC = the starter with the highest `xp_capt` (joined from `xp_table.json` by `player_code`) who isn't the captain. No data-contract or API change; logic lives in one tested utility. Reversibility: reversible — but `web/data/*.json` is consumed unchanged, so "add VC to the export" was explicitly rejected.

**Team page structure (PITCH-03, UIX-03)**
- D-09: One `/team` route with **three tabs: Squad (default) / Rate my team / Chips**. Squad hosts the pitch + solver; Rate hosts the visual diff + vanilla rate content; Chips hosts the timeline. Each tab lazy-fetches its own data. The locked 8-route structure is unchanged.
- D-10: **No auto-loading of any user's team.** The default Squad tab renders `squad.json` — the model's recommended squad of the week — clearly labeled (e.g. "Model squad · GW3"). 6980093 remains only a placeholder/example, not an auto-loaded default.
- D-11: URL state is **`?entry=` + `?tab=`** (e.g. `/team?entry=1234567&tab=rate`). An entry deep link loads that squad; a rate deep link auto-runs the rating. Everything else (locks, solve results) stays ephemeral per Phase 2's D-07.
- D-12: Nav label renames from vanilla's "Rate my team" to **"My team"**. Requires a one-line PARITY-DEVIATIONS ledger entry.

**Solver UX (PITCH-03)**
- D-13: Lock/exclude is **tap-a-card → action popover** (Lock / Exclude / clear, plus player detail like news and ownership), reusing the D-09 accessible popover pattern. Locked/excluded cards get visible badge states.
- D-14: Solver knobs exposed: **essentials only** — free transfers (prefilled from the API's estimate, editable), max transfers, and plan horizon. Mode/budget use server defaults.
- D-15: Solve wait is **inline status + honest copy** — button disables, an inline status line appears, the pitch stays visible. Vanilla's wait copy carries over (including "a fresh horizon takes ~10-60s while future gameweeks are predicted" for plans).
- D-16: Solve results **update the pitch in place** — the post-solve squad re-renders with incoming players badged IN, plus a compact results bar (sells → buys pairs, hit cost, bank after, XI xP, captain). One pitch is the single source of truth.
- D-17: Users **iterate freely**: locks/excludes persist across re-solves; a "Reset to loaded squad" action restores the as-loaded team and clears marks. Solve results are a local preview — nothing is ever persisted.

**Rate-my-team & chip timing (PITCH-04, UIX-03)**
- D-18: The visual diff is **one pitch + swap overlays** — the user's squad on the pitch with diff markers: players the ideal squad drops get a red "out" treatment, suggested buys appear as ghost/insert cards, and a swap list (sell → buy, xP gain) sits beside it. Not side-by-side pitches.
- D-19: **All vanilla rate content carries over**: the four tiles (team score /100, season points/rank, captain, best move), the best-XI-for-this-GW view, and the multi-week "Plan transfers" flow — copy verbatim. The pitch diff is the new centerpiece; nothing users had disappears at cutover (CUT-01).
- D-20: Rate analysis fetches **on demand when the Rate tab opens** (then cached by TanStack Query) — no wasted triple-solve on every team load. Exception: a `?tab=rate` deep link auto-fetches (D-11).
- D-21: Chip timing renders as a **GW timeline strip** — a horizontal season timeline (current GW → 38) with DGW/BGW gameweeks highlighted as markers and callout badges, and `chips.json`'s `note` as the headline "why this GW" explanation. Derives entirely from the existing `note` + `structure` fields — no contract change.

### Claude's Discretion
- Whether the default model-squad pitch is view-only or supports lock/exclude + from-scratch wildcard solves (`/api/solve` with `entry: null`) — pick what keeps scope sane.
- GK kit differentiation, fallback colors for unmapped clubs, and exact kit SVG construction.
- Tab component implementation and how `?tab=` syncs with it.
- Exact IN-badge/out-treatment styling in solve results and the rate diff.
- How the transfers summary bar formats hits/bank (mirror vanilla's plan-flow copy where it exists).
- Where the PITCH-01 decision doc lives (e.g. `docs/` vs `.planning/`), as long as it's committed and findable.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (The pre-launch SEO pass deferred in Phase 2 remains deferred.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PITCH-01 | Shirt/kit asset sourcing decision documented, non-affiliation disclaimer | D-01 already resolves the sourcing choice (neutral SVG, no CDN) — this phase writes the decision doc; see Architecture Patterns → "Kit SVG system" and Common Pitfalls → "Trademark posture" |
| PITCH-02 | Pitch renderer — formation-driven rows, player cards with shirt/name/price/xP/C/VC | See Architecture Patterns → "Pitch layout", Code Examples → formation derivation from `squad.json`, verified 5-3-2 real-data example |
| PITCH-03 | Team page — load squad, render, lock/exclude, solve, see transfers/XI update | See `/api/solve` request/response shapes (verified from `api/main.py`), Architecture Patterns → "Tabs + URL state", "Solve request/response handling" |
| PITCH-04 | Rate-my-team — visual diff of user squad vs optimal with suggested swaps | See Common Pitfalls → "`/api/rate` only returns a single best move, not a full ideal squad" — this bounds what D-18's diff can show without an API change |
| UI-07 | Mobile-responsive pitch and tables | See Architecture Patterns → "Pitch layout" (CSS Grid, verified formation ceiling is 5-across), D-07 |
| UIX-01 | p10/p90 intervals on player/captain cards | Reuses `frontend/src/lib/bandCell.ts`'s `bandGeometry`/`bandTooltip` (verified read) as the geometry source; card range line is a sibling display, not the exact same component |
| UIX-03 | Chip-timing "why this GW" UI with DGW/BGW callouts | `chips.json` schema verified via Read — `note` (string) + `structure` (array of `{gw, dgw_clubs, bgw_clubs}`) |
</phase_requirements>

## Summary

This phase is almost entirely new UI construction on top of an already-complete backend: `api/main.py`'s `/api/solve`, `/api/plan`, `/api/rate`, `/api/team/{entry}` endpoints and the `web/data/{squad,xp_table,chips,meta}.json` exports were read directly this session and their response shapes are documented below with verbatim field lists. No new npm packages are anticipated — the pitch, kit SVGs, and diff overlays are hand-built with Tailwind v4 (CSS Grid) and inline SVG, reusing Phase 1/2 primitives (`StatusFlag`'s accessible popover pattern, `bandCell.ts`'s band-geometry math, `ErrorState`/`EmptyState`/`Spinner`, TanStack Query, React Router 7's `useSearchParams`).

The single most consequential research finding is **not** about kit sourcing (D-01 already mooted the CDN research flag) — it's that `/api/rate/{entry}` computes only a **single best transfer** (`optimize_gw(..., max_transfers=1)`), not a full "ideal 15-man squad" comparison. `ideal_xi_xp` is a scalar total; the actual ideal squad's player list is never returned to the client. D-18's "visual diff... with suggested swaps" must therefore be built from `best_move.sell[]`/`best_move.buy[]` (vanilla's existing one-swap suggestion, already rendered as text in `web/team.html`) rather than a full squad-vs-squad diff — this is consistent with vanilla behavior (D-19 verbatim-copy discipline), not a new gap, but a planner building toward "show what's different about every one of the 15 ideal-squad players" would be building something the API cannot support without a backend change, which is out of this phase's stated boundary.

**Primary recommendation:** Build one reusable `<Pitch>` component (CSS Grid formation rows + bench strip) driven by a plain `{position, starting, ...}[]` shape so it can render `squad.json` (default), `/api/solve` results (locked/excluded/incoming badges), and `/api/rate`'s `xi` field (diff overlays) without three separate renderers; derive VC, formation string, and per-player p10/p90 through one join utility keyed on `player_code` against `xp_table.json`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pitch rendering, kit SVGs, formation layout | Browser / Client | — | Pure presentational; all inputs already resolved server-side or joined client-side |
| Squad/xP data (default view) | CDN / Static (`web/data/*.json`) | Browser (join by `player_code`) | `squad.json`/`xp_table.json` are pre-built exports fetched at runtime, never bundled (UI-01 invariant) |
| Solve / rate / plan computation (ILP) | API / Backend (`api/main.py` + `optimize/*`) | — | CPU-bound MILP solves; must stay server-side, response cached by `(gw, params-hash)` |
| Lock/exclude, tab state, `?entry=`/`?tab=` | Browser / Client | — | Ephemeral UI state (Phase 2 D-07); URL params only for shareable deep links |
| Solve-result caching within a session | Browser / Client (TanStack Query) | API (`_solve_cache`, server-side) | Client caches by query key; server also caches by `(gw, entry, params-hash)` so repeat identical requests are free |
| VC / formation / band derivation | Browser / Client (one tested utility) | — | D-08 explicitly rejects adding these to the export contract |

## Standard Stack

### Core
No new runtime dependencies. This phase is built entirely on the stack already installed and verified in Phase 1/2 (`frontend/package.json`, read this session):

| Library | Installed Version | Purpose | Why Standard (already approved) |
|---------|-------|---------|--------------|
| react / react-dom | ^19.2.8 | UI runtime | Phase 1 install |
| react-router | 7.18.3 | `/team` route, `useSearchParams` for `?entry=`/`?tab=` (D-11) | Already routes all 8 pages |
| @tanstack/react-query | 5.102.8 | Fetch/cache for `squad.json`, `xp_table.json`, `chips.json`, and the three `/api/*` solve/rate/plan calls (D-20 on-demand + cache) | Already the fetch layer for every other route |
| tailwindcss | 4.3.3 | Pitch CSS Grid layout, dark-safe green tokens (D-05) | `@theme` block already reserves `--color-band*`/`--color-fdr*`; this phase adds pitch-green tokens the same way |
| lucide-react | 1.38.0 | Icons for lock/exclude badges, IN/OUT markers, if needed | Already installed (Phase 1 UI-SPEC) |
| vitest / @testing-library/react | 4.1.11 / 16.3.3 | Per-rule unit tests (VC derivation, formation derivation, kit color map, swap pairing, DGW/BGW timeline) | Established Phase 2 D-05 pattern |

### Supporting
None — no charting/diagramming/SVG-generation library is needed. Kit shirts are one parameterized inline SVG shape (D-02); the pitch is CSS Grid + absolutely-positioned pitch markings, not a canvas/WebGL library.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-built inline SVG shirt | An icon/asset package with pre-made jersey SVGs | Rejected — no vetted crest-free jersey icon package exists; hand-built keeps the ~20-club color/pattern map trivial to audit for D-01/D-02 compliance and avoids adding an unaudited npm dependency for a ~30-line SVG |
| CSS Grid pitch layout | A dedicated "football pitch" React component from npm | Rejected — public packages in this space are stale/unmaintained or overfit to a different design language; CONTEXT.md's own `code_context` states "budget for zero or few new packages; the pitch/kits are hand-built SVG/CSS" |

**Installation:** None required. If planning surfaces a genuine need for a new package (e.g. an animation helper for the "swap" transition), it must go through the same blocking package-legitimacy gate Phase 1/2 used (`npm view <pkg> version`, verify on the live registry, human approval) before install.

## Package Legitimacy Audit

**No new external packages are installed by this phase's plans as currently scoped.** All UI is built on the existing Phase 1/2 dependency set (verified above from `frontend/package.json`). If a plan later introduces a package not in that list, run the Package Legitimacy Gate (`gsd_run query package-legitimacy check`) before adding it to any plan, and route the human approval exactly as Phase 1's 13-package gate and Phase 2's 4-package gate did (see STATE.md decisions log).

**Packages removed due to [SLOP] verdict:** none (none proposed)
**Packages flagged as suspicious [SUS]:** none (none proposed)

## Architecture Patterns

### System Architecture Diagram

```
Browser (/team route)
  │
  ├─ Squad tab (default, no auth needed)
  │    fetch /data/squad.json ───┐
  │    fetch /data/xp_table.json─┤─→ join by player_code → derive VC, formation, p10/p90
  │    fetch /data/meta.json ────┘         │
  │                                        ▼
  │                                  <Pitch> component
  │                                  (formation rows + bench, CSS Grid)
  │                                        │
  │              user enters entry ID ─────┤
  │                        │                │
  │                        ▼                │
  │              GET /api/team/{entry} ─────┤ (picks + bank; renders as loaded squad)
  │                        │                │
  │         lock/exclude via tap-popover ───┤ (ephemeral client state)
  │                        │                │
  │              POST /api/solve ───────────┤ (kind: "squad" | "transfers")
  │                        │                │
  │                        ▼                ▼
  │              solve result ──────► <Pitch> re-renders in place (D-16)
  │                                   + results bar (sells/buys, hits, bank, XI xP, captain)
  │
  ├─ Rate tab (on-demand fetch, TanStack Query cache, D-20)
  │    GET /api/rate/{entry} ──→ hold squad (xi[], full 15) + best_move (single swap) + tiles
  │                          └─→ <Pitch> renders xi[] + best_move as ghost/out overlays (D-18)
  │    POST /api/plan ───────→ multi-week plan (10-60s), rendered as per-week squad cards
  │
  └─ Chips tab (on-demand fetch)
       fetch /data/chips.json ──→ GW timeline strip; note field = headline explanation (D-21)
```

### Recommended Project Structure
```
frontend/src/
├── routes/
│   └── Team.tsx                 # replaces placeholder; hosts the 3-tab shell, reads ?entry=/?tab=
├── components/
│   ├── pitch/
│   │   ├── Pitch.tsx             # formation rows + bench, CSS Grid, takes a plain row[] + formation
│   │   ├── PlayerCard.tsx        # shirt SVG + name/price/xP/interval/C-VC badges + tap popover
│   │   ├── Kit.tsx               # parameterized SVG shirt (club color/pattern map)
│   │   └── kitMap.ts             # ~20-club color/pattern lookup (hand-maintained, D-02)
│   ├── SolveControls.tsx         # free transfers / max transfers / horizon inputs (D-14)
│   ├── SolveResultsBar.tsx       # sells→buys pairs, hit cost, bank after, XI xP, captain (D-16)
│   ├── RateDiff.tsx              # pitch + swap overlay + swap list (D-18)
│   └── ChipTimeline.tsx          # GW timeline strip with DGW/BGW markers (D-21)
├── lib/
│   ├── squadJoin.ts              # join squad.json/api rows to xp_table.json by player_code;
│   │                              # derives VC (D-08), per-player p10/p90, xp_capt
│   ├── formation.ts              # derive "3-5-2"-style label from starting[] (mirrors
│   │                              # squad_ilp.py's "-".join(DEF,MID,FWD) — verified formula)
│   └── pairMoves.ts              # port of web/team.html's pairMoves() (sell↔buy pairing by position)
```

### Pattern 1: Formation derivation must match the ILP's exact rule set
**What:** `squad.json`'s rows carry `starting: boolean` per player but no formation field. The formation label ("3-5-2") is derived client-side by counting starters per position.
**When to use:** Any place a formation string or row grouping is needed (default pitch, solve result pitch, rate XI pitch).
**Verified formula** (from `optimize/squad_ilp.py:126`, read this session):
```python
formation = "-".join(str((xi.position == p).sum()) for p in ["DEF", "MID", "FWD"])
```
GK count is always exactly 1 (verified constraint at `squad_ilp.py:92`: `prob += pulp.lpSum(start[i] for i in idx if pos[i] == "GK") == 1`) and is never included in the formation string — it is implicit. DEF: 3-5, MID: 2-5, FWD: 1-3 (verified constraints, `squad_ilp.py:93-98`). Live `squad.json` data (read this session) confirms a real 3-5-2 example: 1 GK / 3 DEF / 5 MID / 2 FWD starters out of 5/5/3/2 squad totals.
```typescript
// src/lib/formation.ts
export function deriveFormation(rows: { position: string; starting: boolean }[]): string {
  const starters = rows.filter((r) => r.starting);
  const count = (p: string) => starters.filter((r) => r.position === p).length;
  return `${count("DEF")}-${count("MID")}-${count("FWD")}`;
}
```

### Pattern 2: VC derivation joins two files by `player_code`
**What:** D-08 requires VC = highest `xp_capt` among starters, excluding the captain, joined from `xp_table.json`.
**Verified field:** `xp_table.json`'s rows carry `xp_capt: number | null` (already typed in `frontend/src/lib/api.ts:53`, confirmed present on the live export, e.g. `B.Fernandes`: `"xp_capt": 6.04`).
```typescript
// src/lib/squadJoin.ts
export function deriveViceCaptain(
  starters: { player_code: number; captain: boolean }[],
  xpByCode: Map<number, { xp_capt: number | null }>,
): number | null {
  let best: { code: number; val: number } | null = null;
  for (const s of starters) {
    if (s.captain) continue;
    const xpc = xpByCode.get(s.player_code)?.xp_capt;
    if (xpc == null) continue;
    if (!best || xpc > best.val) best = { code: s.player_code, val: xpc };
  }
  return best?.code ?? null;
}
```

### Pattern 3: `squad.json`'s top-level shape is `{ "squad": [...] }`, not a bare array
**What:** Live read of `web/data/squad.json` this session shows the top-level document is an object with one key, `squad`, whose value is the 15-row array — **not** a bare top-level array as `frontend/src/lib/api.ts`'s existing interfaces (e.g. `XpRow[]` for `xp_table.json`) might suggest by pattern-matching to sibling files.
```json
{ "squad": [ { "player_code": 97032, "name": "Virgil", "team": "Liverpool",
  "position": "DEF", "price_m": 6.5, "xp": 2.68, "starting": true, "captain": false }, ... ] }
```
**Why it matters:** a `fetchJson<SquadRow[]>("/data/squad.json")` typed call will compile but return the wrong shape at runtime (an object, not an array) — `.map()` on it throws. The new `SquadResponse` interface in `lib/api.ts` must be `{ squad: SquadRow[] }`.

### Pattern 4: Solve response shape branches on `kind`
**What:** `/api/solve`'s response (verified from `api/main.py:281-329`) has two disjoint shapes depending on whether `entry` was provided in the request:
- `entry: null` (from-scratch/wildcard) → `kind: "squad"`, fields: `gw, kind, squad[], captain, formation, cost, xi_xp` (no `buys`/`sells`/`bank_after`/`hits`).
- `entry: <id>` (transfers) → `kind: "transfers"`, fields: `gw, kind, entry, transfers (count), hits, buys[], sells[], captain, bank_after, xi_xp, squad[]` (`squad[]` here is the full 15-row post-solve squad via `_squad_rows`, shape matches `squad.json`'s rows plus nothing extra).
```typescript
export interface SolveSquadResult {
  gw: number; kind: "squad";
  squad: SquadRow[]; captain: string; formation: string;
  cost: number; xi_xp: number;
}
export interface SolveTransfersResult {
  gw: number; kind: "transfers"; entry: number;
  transfers: number; hits: number;
  buys: { name: string; position: string; price_m: number }[];
  sells: { name: string; position: string; price_m: number }[];
  captain: string; bank_after: number; xi_xp: number;
  squad: SquadRow[];
}
export type SolveResult = SolveSquadResult | SolveTransfersResult;
```
D-16's results bar (sells→buys pairs, hit cost, bank after, XI xP, captain) only has data to render for the `"transfers"` variant — the default Squad-tab "view-only" case (Claude's Discretion) most naturally maps to never sending `entry: null` solves at all unless that discretion item is exercised.

### Pattern 5: `/api/rate` returns one best move, not a full ideal squad — see Pitfall 1
See Common Pitfalls below — this fact directly shapes how D-18's diff must be built.

### Pattern 6: Reuse the accessible tap-popover for both StatusFlag and the card action menu
**What:** `frontend/src/lib/statusFlag.tsx` (read this session) implements a `useState(open)` + `useId()` tooltip pattern: opens on focus/hover/click, closes on outside-click or Escape, `min-h-[44px] min-w-[44px]` touch target. D-13 explicitly calls for reusing this pattern for the card's Lock/Exclude/detail popover.
**Difference for the card popover:** StatusFlag's popover is read-only (a tooltip, `role="tooltip"`); the card action popover needs actionable buttons (Lock/Exclude/clear), so it should use `role="menu"`/`role="menuitem"` semantics instead of `role="tooltip"`, keeping the open/close state machine and outside-click/Escape handling identical.

### Pattern 7: Pitch layout — CSS Grid formation rows, verified 5-across ceiling
**What:** Community CSS-Grid football-pitch implementations (e.g. `grid-template-rows: repeat(N, 1fr)` per formation row, `grid-template-columns: repeat(5, 1fr)` for the widest row) are the standard approach for a responsive formation display; no canvas/SVG-viewport library is needed [CITED: github.com/HugoGanoza/responsive-football-field-css-grid, codepen.io/opihana/pen/eedmQO — WebSearch, MEDIUM confidence, community pattern not an official spec].
**Verified ceiling (not assumed):** the max width of any single formation row is 5 cards (DEF max 5, MID max 5 per `squad_ilp.py`'s constraints), and bench is always exactly 4 cards (15 squad − 11 starting = 4). D-07's "worst case 5-across plus the 4-slot bench" is therefore an exact, code-verified bound, not a UI guess — plan the phone-width breakpoint against 5 columns, not a rounder number like 6.

### Anti-Patterns to Avoid
- **Building a full "ideal squad" diff UI:** the API cannot supply the ideal squad's player list (see Pitfall 1). Don't design a component that assumes it will receive 15 "ideal" rows to diff against — it will only ever receive `best_move.sell[]`/`best_move.buy[]` (0 or 1 pair) plus the existing squad's own `xi[]`.
- **Re-deriving the maxHi/band math from scratch for card intervals:** `bandCell.ts`'s `bandGeometry`/`bandTooltip` already encode the correct p10/p90-with-xp-fallback logic and the verbatim tooltip copy (D-03 discipline carries into Phase 3's card range line's underlying numbers, even though the card's visual treatment is new per D-06).
- **Assuming `xp_table.json` and `squad.json`/solve results share identical `name`/`team` casing or spelling** — join strictly by `player_code` (the numeric key both share), never by name string matching (the API's own `_resolve()` helper needs fuzzy name matching only because it accepts free-text locks from users — the client-side join has no such ambiguity and should never use string matching).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accessible show/hide popover (tooltip or menu) | A new focus-trap/outside-click implementation | Port `statusFlag.tsx`'s state machine (D-09 pattern) | Already accessibility-reviewed in Phase 2, has an established test pattern |
| p10/p90 percentage-of-track math | New band-geometry math for the card's range line | `bandCell.ts`'s `bandGeometry()` (parameterized by `maxHi`) | Prevents a repeat of Phase 2's Pitfall 4 (two call sites needing different `maxHi` floors) |
| Deep-link URL state (`?entry=`, `?tab=`) | A custom URL-param sync hook | React Router 7's native `useSearchParams()` | Already the established pattern in this codebase (React Router 7 is the routing library) |
| Sell→buy pairing for the transfers/plan summary | New pairing logic | Port `web/team.html`'s `pairMoves()` verbatim (position-keyed pairing, ties resolved by array order) | It's the exact vanilla algorithm D-19 requires be preserved copy-for-copy |
| Countdown/deadline formatting | New date math | `frontend/src/lib/deadline.ts` (already built, Phase 2) | Meta banner already solves gameweek deadline formatting; the "Model squad · GW{n}" label only needs `meta.json`'s `gw` field, no new date logic |

**Key insight:** almost nothing in this phase needs a new algorithm — the ILP, the transfer pairing, the accessible popover, and the band math all already exist and are verified working. The genuinely new work is presentational (SVG kits, CSS Grid pitch layout, the three-tab shell) and one small join utility (VC/formation/band-per-card derivation).

## Common Pitfalls

### Pitfall 1: `/api/rate/{entry}` returns a single best move, not the full ideal squad
**What goes wrong:** A plan or component built assuming it can diff the user's 15-man squad against the "ideal" 15-man squad player-by-player will find the API has no such data to give it.
**Why it happens:** `rate()` in `api/main.py:374-403` (read this session) computes `ideal = pick_squad(pool, budget=t["value"] + t["bank"])` purely to get `ideal["xp_xi"]` — a scalar total. The response body only ever includes `ideal_xi_xp: round(float(ideal["xp_xi"]), 2)`, never `ideal["squad"]`. The only per-player suggestion returned is `best_move` — computed separately via `optimize_gw(pool, squad, bank, 1, max_transfers=1, ...)`, i.e. **the single best one-transfer swap**, matching exactly what vanilla's `team.html` already renders (`d.best_move.sell.join(", ")} → ${d.best_move.buy.join(", ")`).
**How to avoid:** Design D-18's diff around `best_move.sell[]` (0 or 1 names) and `best_move.buy[]` (0 or 1 names) plus `xi[]` (the user's own full 15-row squad, returned in full via `_squad_rows`). "Suggested buys appear as ghost/insert cards" (D-18) means the 0-or-1 buy from `best_move`, not a full replacement squad. If a future phase wants a true full-squad diff, that requires adding `ideal["squad"]` (or equivalent) to `/api/rate`'s response — a backend change explicitly out of this phase's "consumed unchanged" contract discipline.
**Warning signs:** A component prop named something like `idealSquad: SquadRow[]` with no corresponding API field to populate it.

### Pitfall 2: `p10`/`p90` can be absent from a solve/rate/plan response
**What goes wrong:** UI code that always destructures `xi_p10`/`xi_p90` and formats them will crash or show `NaN–NaN` when the interval-band artifact isn't loaded.
**Why it happens:** `_xi_band()` in `api/main.py:114-134` returns `None` when `"p10" not in pool.columns` (i.e. `models.intervals.load_artifact()` returned nothing) — `/api/plan`'s per-week `xi_p10`/`xi_p90` and `/api/rate`'s top-level `xi_p10`/`xi_p90` are then both `null`. Vanilla already guards this (`d.xi_p10 != null ? ... : ""`), and per-card intervals from `xp_table.json`'s `p10`/`p90` fields are independently typed as `number | null` in `lib/api.ts` — both must be null-guarded.
**How to avoid:** Treat every `p10`/`p90`/`xi_p10`/`xi_p90` field as nullable everywhere, mirroring vanilla's existing null-guard pattern and the already-established `BandRow` interface (`p10?: number | null; p90?: number | null`).
**Warning signs:** A `.toFixed()` call on a `p10`/`p90` value without an `!= null` guard first.

### Pitfall 3: Locks/excludes accept player_code OR free-text name — client should always send `player_code`
**What goes wrong:** Sending a name string for a lock/exclude works (the server does fuzzy matching via `_resolve()`), but it's strictly worse than sending the numeric `player_code` the client already has from the loaded squad/pool data, and free-text matching has documented edge cases (`'Saka'` must not resolve to `'Wan-Bissaka'` — substring matching with rank tie-breaking, verified at `api/main.py:212-232`).
**Why it happens:** `SolveRequest.locks`/`excludes` are typed `list[int | str]` server-side to support vanilla's future potential text-entry use case; the pitch UI always has the exact `player_code` for the card being locked/excluded.
**How to avoid:** Always send `player_code` (int) in `locks`/`excludes` arrays from the pitch UI — never construct a name string from a card's displayed name.

### Pitfall 4: `squad.json` and API squad rows share a shape but not a wrapper
**What goes wrong:** `squad.json`'s top-level document is `{ squad: SquadRow[] }`; `/api/solve`'s response has the array directly at `.squad` (no extra wrapper needed since it's already inside the JSON response object) but a **different set of sibling fields** depending on `kind` (see Pattern 4). Code that treats all three squad-row sources (`squad.json`, solve response, rate response's `xi`) as interchangeable without checking the wrapper/sibling-field differences will misread bank/formation/cost fields that only exist on some of them.
**How to avoid:** Normalize all three sources into one internal `SquadRow[]` + a separate "context" object (formation/cost/captain-name/bank) at the point of fetch, rather than passing the raw API response shape deep into `<Pitch>`.

### Pitfall 5: Club identity in the data uses full names, not codes — need `xp_table.json`'s `team_short` for the kit map key
**What goes wrong:** `squad.json` rows only carry `team: "Man Utd"` (full display name); a kit-color lookup keyed on `team_short` (`"MUN"`) will fail to match unless the row is first joined to `xp_table.json` by `player_code` to pick up `team_short`.
**Verified 20-club list** (read from live `xp_table.json` this session — full name / `team_short`): Arsenal/ARS, Aston Villa/AVL, Bournemouth/BOU, Brentford/BRE, Brighton/BHA, Chelsea/CHE, Coventry City/COV, Crystal Palace/CRY, Everton/EVE, Fulham/FUL, Hull City/HUL, Ipswich Town/IPS, Leeds/LEE, Liverpool/LIV, Man City/MCI, Man Utd/MUN, Newcastle/NEW, Nott'm Forest/NFO, Spurs/TOT, Sunderland/SUN.
**How to avoid:** Key `kitMap.ts` on `team_short` (stable 3-letter codes) and perform the `player_code` join (Pattern 2/3's utility) before any kit lookup — never key the map on the full display name, which has punctuation/spacing variance (`"Nott'm Forest"`).

### Pitfall 6: Trademark posture is now about the disclaimer, not the CDN — don't re-litigate D-01
**What goes wrong:** A plan that spends effort verifying FPL CDN URL patterns (per the original roadmap research flag) is solving an already-closed question — D-01 explicitly declared that flag "moot."
**Why it happens:** The phase description's "Research flags" text predates the CONTEXT.md discussion; CONTEXT.md is the authoritative, later artifact.
**How to avoid:** The only PITCH-01 work remaining is (1) building the neutral SVG kit system (D-02) and (2) writing the decision doc (D-04) that documents *why* neutral kits were chosen over CDN imagery — trademark/licensing risk of hotlinking official league/team imagery for a paid product is a real, well-documented concern for fantasy-sports apps generally [CITED: avvo.com legal-answers threads on fantasy sports and team logo/trademark use — WebSearch, MEDIUM confidence, non-official legal-advice source; treat as directional rationale for the decision doc, not as a legal opinion] — cite this class of concern in the decision doc as the *reason* D-01 chose the safer path, not as new research to redo.

## Code Examples

### Formation + bench split from a flat squad-row array
```typescript
// Source: derived from optimize/squad_ilp.py (verified formula) + squad.json's shape
export function splitPitchRows(rows: SquadRow[]) {
  const starters = rows.filter((r) => r.starting);
  const bench = rows.filter((r) => !r.starting);
  const byPos = (pos: string) => starters.filter((r) => r.position === pos);
  return {
    gk: byPos("GK"), def: byPos("DEF"), mid: byPos("MID"), fwd: byPos("FWD"),
    bench, // always length 4 (15 - 11), verified against config.SQUAD_SIZE/POSITION_QUOTA
  };
}
```

### Solve request — sending locks/excludes as player_codes
```typescript
// Source: api/main.py's SolveRequest model (verified fields + constraints)
interface SolveRequest {
  entry: number | null;
  free_transfers: number;   // 0..config.MAX_FREE_TRANSFERS (5), prefilled from /api/rate's free_transfers
  horizon: number;          // 1..6
  mode?: "normal" | "tc" | "bb"; // server default "normal" — D-14 doesn't expose this
  max_transfers?: number | null; // 0..15
  locks: number[];          // player_code, never free-text from this UI (Pitfall 3)
  excludes: number[];
}
```

### Band-line rendering reusing bandCell.ts's math
```typescript
// Source: frontend/src/lib/bandCell.ts (read verbatim this session)
import { bandGeometry, bandTooltip } from "../lib/bandCell";

// Card range line (D-06): always-visible, no interaction.
// `maxHi` for a single-card context is just this player's own p90 (or xp if absent) —
// there is no "column" of players to compute a shared scale against, unlike the table view.
const geom = bandGeometry({ xp: player.xp, p10: player.p10, p90: player.p90 }, player.p90 ?? player.xp);
const rangeLabel = `${(player.p10 ?? player.xp).toFixed(1)}–${(player.p90 ?? player.xp).toFixed(1)}`;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Vanilla `squadgrid`/`squadcard` (4-column list grouped by position, no pitch) | React `<Pitch>` (CSS Grid formation rows + bench strip, FPL-app-style) | This phase | New visual design, not a port — CONTEXT.md's "Critical framing" note (vanilla has no pitch) |
| Vanilla desktop-only `title` tooltip | Accessible tap/click/keyboard popover (`StatusFlag` pattern, D-09) | Phase 2, extended to card actions this phase (D-13) | Mobile-usable, keyboard-accessible |

**Deprecated/outdated:** none specific to this phase's domain — the backend endpoints and data contract are stable and unchanged.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact per-club primary/secondary kit colors and pattern classification (plain/stripes/hoops/sleeves) for the 20 clubs in the current data | Architecture Patterns → Pattern 7 / Don't Hand-Roll table (kitMap.ts) | Low — explicitly Claude's Discretion in CONTEXT.md; wrong colors are a cosmetic fix, no functional/legal risk since no crests or sponsor marks are used regardless (D-02's constraint is about *shape*, not color accuracy) |
| A2 | CSS Grid (rather than Flexbox or absolute positioning) is the best-practice approach for the pitch's formation rows | Architecture Patterns → Pattern 7 | Low — [CITED] community pattern, not an official spec; Flexbox with `flex-basis` percentages would work equally well and is a trivial swap if CSS Grid proves awkward for the bench strip |
| A3 | GK kit differentiation approach (distinct color/pattern for goalkeepers vs outfield players) | Claude's Discretion (CONTEXT.md) | Low — cosmetic; standard convention (GK shirt visually distinct from outfield) is well-known and uncontroversial |
| A4 | Trademark/licensing risk framing for the PITCH-01 decision doc | Common Pitfalls → Pitfall 6 | Low — D-01 already made the decision; this only affects how persuasively the decision doc explains *why*, not the doc's required existence (success criterion 1) |

## Open Questions

1. **Does the default Squad tab support solving (lock/exclude → `/api/solve` with `entry: null`), or is it view-only?**
   - What we know: `/api/solve` fully supports `entry: null` for a from-scratch/wildcard squad build (verified in `api/main.py:291-304`); this is technically available today.
   - What's unclear: CONTEXT.md leaves this to Claude's Discretion explicitly ("pick what keeps scope sane").
   - Recommendation: Ship view-only for the default Squad tab in this phase (renders `squad.json` + derived VC/formation, no solve controls) — the loaded-team flow (D-13 through D-17) already fully covers the solve/lock/exclude interaction surface once a real entry ID is loaded. Revisit "wildcard from empty" as a fast-follow if user feedback wants it; this keeps Phase 3's scope aligned with its stated success criteria (all four of which describe either a *loaded* squad flow, the *default recommended* squad display, rate-my-team, or chip timing — none require solving from the empty default state).

2. **Should the Rate tab's diff visually distinguish "0 suggested transfers" (hold) from "1 suggested transfer"?**
   - What we know: `best_move` is `null` in the API response when `optimize_gw`'s ILP finds no transfer improves the XI (`if one["transfers"]: move = {...}` else stays `None`, verified at `api/main.py:387-392`). Vanilla renders "Hold" / "no single transfer beats your current squad" in this case.
   - What's unclear: whether the pitch diff view (D-18) needs its own explicit "no changes suggested" pitch state, or whether omitting overlays entirely (plain pitch, no red/ghost cards) is self-explanatory alongside the existing tile copy.
   - Recommendation: Reuse vanilla's tile copy verbatim (D-19) for the textual "Hold" state; the pitch itself needs no special-case rendering beyond "no overlays present" when `best_move` is `null` — plan a `PlayerCard` variant prop (`none | out | in`) that defaults to `none`.

## Environment Availability

No new external tools, services, or runtimes are introduced by this phase — it is a frontend-only build on the existing Vite/React/Vitest toolchain (already verified present and working through Phase 2) and the existing FastAPI backend (`api/main.py`, unchanged). `scripts/verify_frontend_build.sh` (read this session) already gates that no `web/data/*.json` file is copied into the frontend build output — this invariant is unaffected by this phase's runtime-fetch pattern for `squad.json`/`xp_table.json`/`chips.json`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.11 + @testing-library/react 16.3.3 (jsdom environment) |
| Config file | `frontend/vitest.config.ts` (verified, separate from `vite.config.ts` on purpose) |
| Quick run command | `npm --prefix frontend run test -- <pattern>` (or `npx vitest run <file>` from `frontend/`) |
| Full suite command | `npm --prefix frontend run test` (runs `node scripts/check-tokens.mjs && vitest run`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PITCH-01 | Kit color/pattern map resolves every club in `xp_table.json`'s team list to a defined entry (no fallback-color silently masking a missing club) | unit | `vitest run src/components/pitch/kitMap.test.ts` | ❌ Wave 0 |
| PITCH-02 | Formation derivation matches `squad_ilp.py`'s formula for known starter sets (incl. the verified live 3-5-2 example) | unit | `vitest run src/lib/formation.test.ts` | ❌ Wave 0 |
| PITCH-02 | VC derivation excludes the captain and picks the highest `xp_capt` among starters, null-safe when `xp_capt` is absent | unit | `vitest run src/lib/squadJoin.test.ts` | ❌ Wave 0 |
| PITCH-03 | Solve request sends `player_code` (not name) for locks/excludes; solve result branches correctly on `kind` | unit | `vitest run src/routes/Team.test.tsx` (or a dedicated solve-handling unit file) | ❌ Wave 0 |
| PITCH-03 | `?entry=`/`?tab=` deep links load the right tab/team and auto-rate on `?tab=rate` (D-11) | unit | `vitest run src/routes/Team.test.tsx` | ❌ Wave 0 |
| PITCH-04 | Rate diff renders `best_move`'s 0-or-1 sell/buy correctly, including the null (`Hold`) case | unit | `vitest run src/components/RateDiff.test.tsx` | ❌ Wave 0 |
| UI-07 | Pitch renders all formation rows + 4-slot bench without horizontal overflow at a phone-width viewport (worst-case 5-across DEF/MID row) | unit (jsdom layout assertion) or documented manual check | `vitest run src/components/pitch/Pitch.test.tsx` | ❌ Wave 0 |
| UIX-01 | Card interval line renders `p10–p90`, falls back to `xp` when both null, matches `bandTooltip`'s copy semantics | unit | `vitest run src/components/pitch/PlayerCard.test.tsx` | ❌ Wave 0 |
| UIX-03 | Chip timeline correctly flags DGW/BGW gameweeks from `structure[]`'s `dgw_clubs`/`bgw_clubs` | unit | `vitest run src/components/ChipTimeline.test.tsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `npx vitest run <changed-file-pattern>` from `frontend/`
- **Per wave merge:** `npm --prefix frontend run test` (full suite + token check) and `npm --prefix frontend run typecheck`
- **Phase gate:** Full suite green + `bash scripts/verify_frontend_build.sh` before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/test/fixtures/squad.json`, `xp_table_sample.json`, `chips.json`, `rate_response.json`, `solve_transfers_response.json`, `solve_squad_response.json` — realistic fixtures mirroring the verified shapes in this document (the existing `frontend/src/test/fixtures/` directory already holds watchlist fixtures per Phase 2's pattern; this phase adds squad/solve/rate fixtures the same way)
- [ ] `src/lib/formation.ts`, `src/lib/squadJoin.ts`, `src/lib/pairMoves.ts` — new utilities, no existing file to extend
- [ ] No new test framework or config needed — existing Vitest setup covers this phase's testing needs

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Partial | `/api/solve`, `/api/plan`, `/api/rate` sit behind `require_key` (stub: open when `FPL_API_KEYS` unset, `X-API-Key` header required when set, verified at `api/main.py:167-171`). This phase's frontend must never hardcode or embed an API key client-side — the key, if configured, is an operator/paid-tier concern (PAID-02, out of scope) not this phase's |
| V3 Session Management | No | No session/cookie mechanism exists or is introduced; `?entry=` is public data (any FPL team ID), not a credential |
| V4 Access Control | No | No role/permission model in this phase; `entry` IDs are public FPL data per vanilla's own disclaimer ("Team IDs are public data from the official API; nothing is stored") |
| V5 Input Validation | Yes | Entry ID input: numeric only, matches `/api/team/{entry}` and `/api/rate/{entry}`'s `int` path param — client-side should reject non-numeric input before firing a request, mirroring vanilla's `<input type="number" min="1">`. Free-transfer/horizon inputs already have server-side bounds (`SolveRequest`'s `Field(ge=..., le=...)`, verified) — client should mirror these as `min`/`max` on the inputs to avoid a round-trip 422 |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Reflected/stored XSS via a manager team name or player name rendered into the DOM | Tampering / Information Disclosure | React's default JSX text-node escaping (no `dangerouslySetInnerHTML` anywhere in this phase's components) — the existing `react-markdown` usage on the Methodology page is the only place raw HTML rendering is used in this codebase, and this phase introduces no new markdown/HTML rendering |
| Arbitrary numeric `entry` ID enumeration hitting the FPL upstream API through this app as a proxy | Denial of Service (upstream) | Already mitigated server-side by the 1-hour pool cache (`POOL_TTL_S`) and per-`(gw, entry, params)` solve cache; this phase's frontend should debounce/disable the "Rate it"/"Solve" buttons while a request is in flight (D-15 already requires this for UX reasons, which doubles as a basic client-side rate-limit) |
| Client trusting `/api/solve`'s `kind` field without validating it matches the request sent | Tampering (client-side logic error, not a real security boundary) | TypeScript discriminated union (`SolveResult = SolveSquadResult | SolveTransfersResult` keyed on `kind`) forces exhaustive handling at compile time |

## Sources

### Primary (HIGH confidence — read directly this session)
- `api/main.py` — full file read; all endpoint request/response shapes, `require_key`, `_xi_band`, `_resolve`, `_squad_rows`, `SolveRequest`/`PlanRequest` models
- `optimize/squad_ilp.py` — full file read; formation constraints, formation-string formula, captain/formation output shape
- `optimize/transfers.py` — `optimize_gw`'s return dict fields (partial read, targeted at the return statement)
- `web/team.html` — full file read; vanilla rate/plan flow copy, `squadCards`, `pairMoves`, deep-link behavior
- `web/data/squad.json`, `xp_table.json`, `chips.json`, `meta.json` — live data read via Python one-liner this session; verified top-level shapes, field lists, and one real 3-5-2 formation example
- `frontend/src/lib/api.ts`, `bandCell.ts`, `statusFlag.tsx` — full files read; existing typed interfaces, band-geometry math, accessible popover pattern
- `frontend/src/components/PageShell.tsx`, `frontend/src/index.css` — full files read; footer/disclaimer mount point, dark-token `@theme` block structure
- `frontend/src/routes/routeIsolation.test.tsx`, `Prices.test.tsx`, `frontend/src/router.tsx`, `frontend/src/test/setup.ts` — full/partial reads; established test conventions (MemoryRouter + QueryClientProvider wrapper, fetch mocking, fixture imports)
- `config.py` — full file read; FPL rules constants (`SQUAD_SIZE`, `POSITION_QUOTA`, `FORMATION_MIN`, `MAX_FREE_TRANSFERS`)
- `frontend/package.json` — full file read; confirmed installed dependency versions, no gaps for this phase
- `.planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md` — full file read; ledger format and discipline this phase must extend
- `.planning/phases/01-test-base-layer-app-skeleton/01-UI-SPEC.md` — partial read (first 150 lines); design token/typography/spacing contract this phase must not violate

### Secondary (MEDIUM confidence)
- CSS Grid football-pitch layout pattern — [CITED: github.com/HugoGanoza/responsive-football-field-css-grid, codepen.io/opihana/pen/eedmQO] — WebSearch, community pattern, not an official spec
- Trademark/hotlinking risk framing for sports team imagery in fantasy apps — [CITED: avvo.com legal-answers threads] — WebSearch, non-official legal-advice sources; used only as directional rationale for the already-made D-01 decision, not as a legal opinion for the decision doc to cite as authoritative

### Tertiary (LOW confidence)
None used as a basis for any recommendation in this document.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified directly against `frontend/package.json`; zero new dependencies
- Architecture (API contracts): HIGH — every field/shape claim traced to a specific read line range in `api/main.py`, `optimize/*.py`, or a live `web/data/*.json` file
- Architecture (pitch CSS layout): MEDIUM — the CSS Grid approach is community-sourced, not verified against an official spec (no "official" spec exists for this UI pattern)
- Pitfalls: HIGH for API-shape pitfalls (all read from source); MEDIUM for the trademark-framing pitfall (non-authoritative legal sources)
- Kit color/pattern map (Assumption A1): LOW — explicitly deferred to Claude's Discretion in CONTEXT.md, no verification attempted

**Research date:** 2026-09-02
**Valid until:** Backend API/data-contract facts (the HIGH-confidence majority of this document) are stable until `api/main.py` or the `predict/export.py` JSON schema changes — no natural expiry, but re-verify field lists directly from source before executing if either file has been touched since this research date. CSS/UI pattern research (MEDIUM confidence) valid ~90 days (slow-moving, not framework-version-dependent).
