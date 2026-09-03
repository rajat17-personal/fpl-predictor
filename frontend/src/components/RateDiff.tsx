import { Pitch, type PitchGhost } from "./pitch/Pitch";
import type { PitchPlayer } from "../lib/squadJoin";
import { deriveViceCaptain, joinSquad } from "../lib/squadJoin";
import { deriveFormation } from "../lib/formation";
import type { RateBestMove, SquadRow, XpRow } from "../lib/api";

/** Pitch's diffs/ghost props resolved from the rating's suggested move. */
export interface RateOverlay {
  diffs: Record<number, "out">;
  ghost: PitchGhost | null;
}

const VALID_PITCH_ROWS = new Set<string>(["GK", "DEF", "MID", "FWD"]);

/* Resolves best_move (0-or-1 sell, 0-or-1 buy by construction — see
 * <hard_bound> in 03-03-PLAN.md) into Pitch's diffs/ghost props. Exported as
 * a pure function so both the exact-match success path and the zero/
 * multiple-match degrade are directly unit-testable without rendering
 * (must_haves' "own unit test file" backstop). Matching is exact-string-
 * equal only, on names — never substring, never fuzzy (T-03-11): the client
 * always has the option of falling back to a text-only swap line, so it
 * never needs the server's own tie-break-ranked fuzzy resolver. */
export function resolveRateOverlay(
  xi: SquadRow[],
  xpTable: XpRow[],
  bestMove: RateBestMove | null,
): RateOverlay {
  if (!bestMove) {
    return { diffs: {}, ghost: null };
  }

  const diffs: Record<number, "out"> = {};
  let outCode: number | null = null;
  const sellName = bestMove.sell[0];
  if (sellName != null) {
    const matches = xi.filter((r) => r.name === sellName);
    if (matches.length === 1) {
      outCode = matches[0].player_code;
      diffs[outCode] = "out";
    }
  }

  let ghost: PitchGhost | null = null;
  const buyName = bestMove.buy[0];
  if (buyName != null) {
    const matches = xpTable.filter((r) => r.name === buyName);
    if (matches.length === 1) {
      const row = matches[0];
      const ghostPlayer: PitchPlayer = {
        player_code: row.player_code,
        name: row.name,
        team: row.team,
        position: row.position,
        price_m: row.price_m,
        xp: row.xp,
        starting: true,
        captain: false,
        p10: row.p10,
        p90: row.p90,
        xp_capt: row.xp_capt,
        team_short: row.team_short,
        status: row.status,
        news: row.news,
        ownership: row.ownership,
      };
      if (VALID_PITCH_ROWS.has(row.position)) {
        ghost = {
          row: row.position as PitchGhost["row"],
          afterCode: outCode,
          player: ghostPlayer,
        };
      } else if (import.meta.env.DEV) {
        console.warn(
          `resolveRateOverlay: unexpected position "${row.position}" for ghost buy`,
        );
      }
    }
  }

  return { diffs, ghost };
}

export interface RateDiffProps {
  /** The rating's own full 15-row squad — real data, never a hypothetical
   * "ideal" squad (the API has no such list to give, see <hard_bound>). */
  xi: SquadRow[];
  bestMove: RateBestMove | null;
  /** xp_table.json's full pool — the join source for card fields and the
   * only place a suggested buy (not currently owned) can be found. */
  xpTable: XpRow[];
  gw: number;
}

/* One pitch carries both D-18's diff overlay and D-19's best-XI section.
 * xi[] already IS the model's best-XI-for-this-GW (no transfers) — layering
 * the diff overlays onto that same pitch satisfies D-18's "not two
 * side-by-side pitches" rule and D-19's copy-preservation rule at once,
 * rather than mounting xi[] twice (03-03-PLAN.md's flagged_assumption; see
 * the plan's SUMMARY for this executor's chosen arrangement). */
export function RateDiff({ xi, bestMove, xpTable, gw }: RateDiffProps) {
  const players = joinSquad(xi, xpTable);
  const formation = deriveFormation(xi);
  const captainCode = xi.find((r) => r.captain)?.player_code ?? null;
  const xpByCode = new Map(xpTable.map((row) => [row.player_code, row]));
  const viceCode = deriveViceCaptain(
    xi.filter((r) => r.starting).map((r) => ({ player_code: r.player_code, captain: r.captain })),
    xpByCode,
  );
  const { diffs, ghost } = resolveRateOverlay(xi, xpTable, bestMove);

  return (
    <div className="mt-6">
      <h2 className="font-heading text-heading font-bold text-ink">Your best XI for GW{gw}</h2>
      <p className="mt-1 font-body text-body text-ink-2">
        Keeping your current squad (no transfers), this is the lineup and captain the model would
        field.
      </p>
      <p className="mt-1 font-mono text-label tabular-nums text-ink-2">{formation}</p>

      <div className="mt-4">
        <Pitch
          players={players}
          captainCode={captainCode}
          viceCode={viceCode}
          diffs={diffs}
          ghost={ghost}
        />
      </div>

      {bestMove && (
        <p data-testid="swap-line" className="mt-3 font-body text-body text-ink">
          {bestMove.sell[0]} → {bestMove.buy[0]}{" "}
          <span className="font-mono text-label tabular-nums text-ink-2">
            +{bestMove.xp_gain} xP
          </span>
        </p>
      )}
    </div>
  );
}

export default RateDiff;
