import type { SquadRow, XpRow } from "./api";

/* Joins squad-shaped rows (squad.json, /api/solve, /api/rate's xi) to
 * xp_table.json rows by player_code only — the client always holds the
 * exact numeric code, so the server's fuzzy _resolve() behaviour has no
 * client-side counterpart (RESEARCH.md Pitfall/Anti-Pattern, 03-01-PLAN.md
 * Task 4). Pure functions, no module state, no fetch — same shape as
 * lib/bandCell.ts and lib/formation.ts. */

/** One squad row plus its joined xp_table.json fields (null when unmatched). */
export interface PitchPlayer extends SquadRow {
  p10: number | null;
  p90: number | null;
  xp_capt: number | null;
  team_short: string | null;
  status: string | null;
  news: string | null;
  ownership: number | null;
}

/** Joins each squad row to its xp_table row by numeric player_code. A squad
 * row with no matching xp row keeps its own fields and takes null for every
 * joined field — never dropped, never matched by name/team string. */
export function joinSquad(rows: SquadRow[], xp: XpRow[]): PitchPlayer[] {
  const xpByCode = new Map<number, XpRow>(xp.map((row) => [row.player_code, row]));
  return rows.map((row) => {
    const match = xpByCode.get(row.player_code);
    return {
      ...row,
      p10: match?.p10 ?? null,
      p90: match?.p90 ?? null,
      xp_capt: match?.xp_capt ?? null,
      team_short: match?.team_short ?? null,
      status: match?.status ?? null,
      news: match?.news ?? null,
      ownership: match?.ownership ?? null,
    };
  });
}

/** D-08: the starter with the highest xp_capt (joined from xp_table.json by
 * player_code) who isn't the captain. Skips starters whose xp_capt is null;
 * returns null when no starter qualifies (e.g. no xp_capt anywhere). */
export function deriveViceCaptain(
  starters: { player_code: number; captain: boolean }[],
  xpByCode: Map<number, { xp_capt: number | null }>,
): number | null {
  let best: { code: number; val: number } | null = null;
  for (const starter of starters) {
    if (starter.captain) continue;
    const xpCapt = xpByCode.get(starter.player_code)?.xp_capt;
    if (xpCapt == null) continue;
    if (!best || xpCapt > best.val) {
      best = { code: starter.player_code, val: xpCapt };
    }
  }
  return best?.code ?? null;
}
