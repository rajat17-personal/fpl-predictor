import type { SolveTransfersResult } from "../lib/api";
import { pairMoves } from "../lib/pairMoves";

export interface SolveResultsBarProps {
  result: SolveTransfersResult;
}

/* Solve results bar (D-16): sells→buys pairs (or Hold), the hit-cost clause
 * omitted entirely at zero hits — not rendered as "0 pts" — bank after, XI
 * xP alone (the endpoint carries no interval fields, see 03-04-PLAN.md's
 * <planner_corrections>: do not add xi_p10/xi_p90 to SolveTransfersResult),
 * and the captain name. One pair and several pairs render through the same
 * list — no special single-pair layout — and every line wraps normally
 * within the container rather than forcing overflow. */
export function SolveResultsBar({ result }: SolveResultsBarProps) {
  const pairs = pairMoves(result.sells, result.buys);

  return (
    <div
      data-testid="solve-results-bar"
      className="mt-4 rounded-lg bg-surface p-4 font-label text-label text-ink"
    >
      <p className="font-bold text-ink-2">Moves</p>
      {/* Hold is defined by "the solve returns no buys" (result.buys.length),
       * not by pairMoves' own output count — pairMoves buckets by the
       * sells side, so a response with sells but zero buys would still
       * produce pairs (with a "?" buyName) if this checked pairs.length
       * instead. Matches PlanTransfers.tsx's identical `week.buys.length >
       * 0` condition (Don't Hand-Roll: same vanilla-derived rule). */}
      {result.buys.length > 0 ? (
        <ul className="mt-1">
          {pairs.map((pair, i) => (
            <li key={`${pair.sellName}-${pair.buyName}-${i}`} className="whitespace-normal">
              {pair.sellName} → {pair.buyName}{" "}
              <span className="font-label text-[11px] uppercase text-ink-2">{pair.position}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1">Hold</p>
      )}

      {result.hits > 0 && (
        <p className="mt-2 font-mono tabular-nums text-ink-2">
          −{4 * result.hits} pts in hits
        </p>
      )}

      <p className="mt-2 font-mono tabular-nums text-ink-2">
        Bank £{result.bank_after.toFixed(1)}m
      </p>
      <p className="mt-1 font-mono tabular-nums text-ink-2">XI xP {result.xi_xp}</p>
      <p className="mt-1">Captain {result.captain}</p>
    </div>
  );
}

export default SolveResultsBar;
