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
