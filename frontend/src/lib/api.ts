/* Thin fetch wrappers over same-origin relative paths.
 *
 * Never build an absolute URL and never read a base-URL env var: relative paths are
 * what make dev (proxied by Vite to localhost:8000) and production (served by
 * FastAPI's own StaticFiles mount) behave identically. Ports the discipline from
 * web/assets/app.js's loadJSON(), which throws on a non-ok response rather than
 * returning a broken value.
 */

async function fetchAndCheck<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`${path}: ${res.status}`);
  }
  return (await res.json()) as T;
}

/** Fetch a JSON file served under the /data prefix (web/data/*.json via the proxy/mount). */
export function fetchJson<T>(path: string): Promise<T> {
  return fetchAndCheck<T>(path);
}

/** Fetch a JSON response from an /api/* FastAPI route. */
export function fetchApi<T>(path: string): Promise<T> {
  return fetchAndCheck<T>(path);
}

/** Mirrors web/data/meta.json's fields (see api/main.py's export contract). */
export interface MetaResponse {
  gw: number;
  horizon: number;
  deadline_utc: string;
  generated_utc: string;
  model_mtime_utc: string;
  season: string;
}

/* The remaining interfaces below mirror the rest of the web/data/*.json export
 * contract, declared here in full now (Phase 2 Plan 01) so no later plan in
 * this phase has to re-edit this file — plans 02-04, 02-05, 02-06 run in
 * parallel and would otherwise collide on this one shared file. */

/** One row of web/data/xp_table.json. */
export interface XpRow {
  player_code: number;
  player_id: number;
  name: string;
  team: string;
  team_short: string;
  position: string;
  price_m: number;
  xp: number;
  xp_capt: number | null;
  p10: number | null;
  p90: number | null;
  ownership: number | null;
  status: string;
  news: string;
}

/** One row of web/data/captains.json. */
export interface CaptainRow {
  name: string;
  team: string;
  team_short: string;
  position: string;
  price_m: number;
  xp: number;
  xp_capt: number;
  ownership: number | null;
}

/** One fixture within a TickerGw's `fixtures` array (web/data/fixtures.json). */
export interface TickerFixture {
  opp: string;
  home: boolean;
  fdr: number;
}

/** One gameweek slot within a FixtureTickerTeam's `gws` array. */
export interface TickerGw {
  gw: number;
  fixtures: TickerFixture[];
}

/** One row of web/data/fixtures.json. */
export interface FixtureTickerTeam {
  team: string;
  short: string;
  gws: TickerGw[];
  ease: number;
  xg_next: number | null;
  xgc_next: number | null;
}

/** One row of a watchlist's `risers`/`fallers` array (web/data/watchlist.json).
 *
 * `prob` and `proj_tonight` are genuinely absent keys (not just null) on some
 * modes, not merely nullable — confirmed by reading models/price.py directly
 * (2026-09-01, plan 02-04): `_emit_official`'s official-mode rows never carry
 * a `prob` key at all, and `_entry`'s heuristic/model-mode rows only add a
 * `prob` key when a real probability exists (never for heuristic) and never
 * add `proj_tonight` at all (that key is official-mode only). */
export interface WatchlistRow {
  name: string;
  team: string;
  position: string;
  price_m: number;
  ownership: number;
  net_transfers: number | null;
  progress: number | null;
  prob?: number | null;
  proj_tonight?: number | null;
  status: string | null;
}

/** web/data/watchlist.json's top-level shape. */
export interface Watchlist {
  mode: string;
  date: string;
  risers: WatchlistRow[];
  fallers: WatchlistRow[];
  locked_players?: number;
  note?: string;
  trained_utc?: string;
  val_moved_hit?: number;
}

/** One row of web/data/standings.json. */
export interface StandingsRow {
  team: string;
  short: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
}

/** One row within a LeadersBoards board (web/data/leaders.json). */
export interface LeaderEntry {
  name: string;
  team: string;
  position: string;
  value: number;
}

/** web/data/leaders.json's top-level shape — five fixed boards. */
export interface LeadersBoards {
  points: LeaderEntry[];
  goals: LeaderEntry[];
  assists: LeaderEntry[];
  clean_sheets: LeaderEntry[];
  cards: LeaderEntry[];
}

/** One row of web/data/scoreboard.json's `entries` array (see predict/scoreboard.py's score_gw()). */
export interface ScoreboardEntry {
  gw: number;
  n_players: number;
  generated_utc: string;
  mae_model: number;
  spearman_model: number;
  mae_fpl?: number | null;
  spearman_fpl?: number | null;
  captain: { name: string; team: string; points: number };
  top5: { name: string; xp: number; points: number }[];
  best_player: { name: string; points: number };
}

/** web/data/scoreboard.json's `summary` field (see predict/scoreboard.py's running_summary()). */
export interface ScoreboardSummary {
  gameweeks: number;
  mae_model: number;
  spearman_model: number;
  captain_avg_points: number;
  mae_fpl?: number | null;
  spearman_fpl?: number | null;
}

/** web/data/scoreboard.json's top-level shape. */
export interface ScoreboardResponse {
  entries: ScoreboardEntry[];
  summary: ScoreboardSummary;
}

/* Phase 3 type surface (plan 03-01), declared here in full now so plans
 * 03-02/03-03/03-04 — which run in parallel — never re-edit this file (same
 * discipline as the Phase 2 comment above). Field lists are copied from
 * 03-PATTERNS.md's "New interfaces to add" block verbatim, with the two
 * corrections recorded in 03-01-PLAN.md's <planner_corrections>: SquadResponse
 * carries five top-level keys (not a one-key wrapper), and
 * ChipsGwStructure.dgw_clubs/.bgw_clubs are integer counts (not string[]). */

/** One row of web/data/squad.json's `squad` array, and of every squad-shaped
 * API response (`/api/solve`, `/api/team`, `/api/rate`'s `xi`). */
export interface SquadRow {
  player_code: number;
  name: string;
  team: string;
  position: string;
  price_m: number;
  xp: number;
  starting: boolean;
  captain: boolean;
}

/** web/data/squad.json's top-level shape — five keys, verified by reading the
 * live export during planning (not a bare `SquadRow[]` and not a `{ squad }`
 * one-key wrapper — see <planner_corrections> in 03-01-PLAN.md). */
export interface SquadResponse {
  squad: SquadRow[];
  captain: string;
  formation: string;
  cost: number;
  xi_xp: number;
}

/** `/api/solve`'s request body. `locks`/`excludes` are always numeric
 * `player_code`, never free-text names, from this client (Pitfall 3). */
export interface SolveRequest {
  entry: number | null;
  free_transfers: number;
  horizon: number;
  mode?: "normal" | "tc" | "bb";
  max_transfers?: number | null;
  locks: number[];
  excludes: number[];
}

/** `/api/solve`'s response when `entry` is null (from-scratch/wildcard build). */
export interface SolveSquadResult {
  gw: number;
  kind: "squad";
  squad: SquadRow[];
  captain: string;
  formation: string;
  cost: number;
  xi_xp: number;
}

/** `/api/solve`'s response when `entry` is provided (transfers). */
export interface SolveTransfersResult {
  gw: number;
  kind: "transfers";
  entry: number;
  transfers: number;
  hits: number;
  buys: { name: string; position: string; price_m: number }[];
  sells: { name: string; position: string; price_m: number }[];
  captain: string;
  bank_after: number;
  xi_xp: number;
  squad: SquadRow[];
}

/** Discriminated on `kind` — TypeScript forces exhaustive handling at the
 * consuming component rather than an `any`-typed branch. */
export type SolveResult = SolveSquadResult | SolveTransfersResult;

/** `/api/rate/{entry}`'s single best-transfer suggestion. `null` at the
 * top level when no improving one-transfer swap exists (the "Hold" case). */
export interface RateBestMove {
  sell: string[];
  buy: string[];
  xp_gain: number;
}

/** `/api/rate/{entry}`'s response. */
export interface RateResponse {
  manager?: {
    team_name?: string;
    manager?: string;
    overall_points?: number;
    overall_rank?: number | null;
    gw_points?: number;
  };
  score: number;
  xi_xp: number;
  xi_p10: number | null;
  xi_p90: number | null;
  ideal_xi_xp: number;
  captain: string;
  best_move: RateBestMove | null;
  gw: number;
  xi: SquadRow[];
  free_transfers?: number;
}

/** One week of `/api/plan`'s multi-week horizon response. */
export interface PlanWeek {
  gw: number;
  buys: { name: string; position: string; price_m: number }[];
  sells: { name: string; position: string; price_m: number }[];
  hits: number;
  free_transfers_after: number;
  xi_xp: number;
  xi_p10: number | null;
  xi_p90: number | null;
  captain: string;
  bank: number;
  squad: SquadRow[];
}

/** `/api/plan`'s top-level response shape. */
export interface PlanResponse {
  weeks: PlanWeek[];
}

/** One pick within `/api/team/{entry}`'s response. Deliberately narrower
 * than `SquadRow` — verified from `api/main.py`'s `_fetch_team` (the picks
 * comprehension at lines 199-205): the real payload carries only these five
 * fields, never `xp`/`starting`/`captain` (03-02-PLAN.md Task 1's "real
 * integration risk"). A caller that needs a full `SquadRow` must derive
 * `xp`/`starting`/`captain` itself — see
 * `components/team/SquadTab.tsx`'s `selectLoadedSquad`. */
export interface TeamPick {
  player_code: number;
  name: string;
  team: string;
  position: string;
  price_m: number;
}

/** `/api/team/{entry}`'s response (verified from `api/main.py`'s
 * `_fetch_team`, lines 174-209 — corrects `picks`'s prior `SquadRow[]`
 * typing, which claimed fields the endpoint never returns). */
export interface TeamResponse {
  entry: number;
  picks: TeamPick[];
  bank: number;
  value: number;
  manager?: {
    team_name?: string;
    manager?: string;
    overall_points?: number;
    overall_rank?: number | null;
    gw_points?: number;
  };
}

/** One gameweek's DGW/BGW structure within `web/data/chips.json`'s
 * `structure` array. `dgw_clubs`/`bgw_clubs` are integer counts, not arrays
 * of club names — verified against `predict/export.py:197-198`'s
 * `sum(1 for v in counts.values() if v > 1)` / `len(all_teams) - len(counts)`
 * (see <planner_corrections> in 03-01-PLAN.md). */
export interface ChipsGwStructure {
  gw: number;
  dgw_clubs: number;
  bgw_clubs: number;
}

/** web/data/chips.json's top-level shape. */
export interface ChipsResponse {
  note: string;
  structure: ChipsGwStructure[];
}
