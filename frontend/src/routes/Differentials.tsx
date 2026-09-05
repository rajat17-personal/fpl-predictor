import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchJson, type XpRow } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { BandCell } from "../components/BandCell";
import { fixed1 } from "../lib/format";
import { usePageMeta } from "../lib/usePageMeta";
import { StatusFlag } from "../lib/statusFlag";

/* Differentials — ported from web/differentials.html's inline script (lines
 * 54-77). Second consumer of <BandCell>/<StatusFlag> (plan 02-01). Shares
 * the xP table's TanStack Query cache entry via the identical query key
 * below, then re-filters client-side — no second export file, no second
 * fetch once both routes have been visited.
 *
 * Two divergences from the xP table are load-bearing, not omissions — see
 * RESEARCH.md R40/R41 and PARITY-DEVIATIONS.md's append rule:
 *   - maxHi floors at 1 here (R40); the xP table's own maxHi (R11) has no
 *     floor. Do not extract a shared computeMaxHi() — see bandCell.ts's
 *     module doc, which takes maxHi as a parameter for exactly this reason.
 *   - Own % has no "-" fallback here (R41), matching the Captains sub-table
 *     (R18/Pitfall 3) and diverging from the xP table's own Own % column. */

const DEFAULT_CAP = 10;

/** R41/Pitfall 3: no `?? "-"` fallback — ported verbatim from vanilla's
 * un-guarded `r.ownership?.toFixed(1)`, which stringifies to the literal
 * text "undefined" for a null value. Exported so the null-ownership case
 * (which R39's `?? 100 <= cap` predicate always filters out of the rendered
 * set) stays directly assertable, per this task's own acceptance criteria. */
export function diffOwnershipCell(ownership: number | null): string {
  return String(ownership?.toFixed(1));
}

export default function Differentials() {
  usePageMeta("/differentials");

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["xp_table"],
    // Root-relative path, identical query key to XpTable.tsx — same cache
    // entry, no duplicate request once both routes have been visited.
    queryFn: () => fetchJson<XpRow[]>("/data/xp_table.json"),
    staleTime: 60_000,
  });

  const [cap, setCap] = useState(DEFAULT_CAP);

  if (isPending) {
    return <Spinner />;
  }

  if (isError) {
    console.error(error);
    return <ErrorState resource="the differentials data" onRetry={() => refetch()} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState />;
  }

  // R39: filter + slice, re-run synchronously on every slider move — no
  // refetch, no loading/error state of its own (the slider cannot fail).
  const rows = data
    .filter((r) => (r.ownership ?? 100) <= cap && r.status === "a")
    .slice(0, 30);
  // R40: floor of 1 — the deliberate divergence from the xP table's R11.
  const maxHi = Math.max(1, ...rows.map((r) => r.p90 ?? r.xp));

  return (
    <div className="py-8">
      <h1 className="font-display text-display font-bold text-ink">Differentials</h1>
      <p className="mt-2 font-body text-body text-ink-2">
        Players the model rates that your mini-league rivals don't own — high xP,
        low ownership, currently available. Rank-climbing lives here.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <label htmlFor="own" className="font-label text-label text-ink-2">
          Max ownership{" "}
          <span className="font-label text-label tabular-nums text-ink">{cap}%</span>
        </label>
        <input
          id="own"
          type="range"
          min={1}
          max={25}
          step={1}
          value={cap}
          onChange={(e) => setCap(Number(e.target.value))}
          // 44px touch target (UI-SPEC Spacing Scale exception) on the
          // native thumb pseudo-elements; inert (and harmless) on engines
          // that don't support the arbitrary-variant selector.
          className="h-11 flex-1 accent-accent [&::-moz-range-thumb]:h-11 [&::-moz-range-thumb]:w-11 [&::-webkit-slider-thumb]:h-11 [&::-webkit-slider-thumb]:w-11"
        />
      </div>

      {rows.length === 0 ? (
        <div className="flex min-h-[16rem] flex-col items-center justify-center gap-2 py-12 text-center">
          <h2 className="font-heading text-heading font-bold text-ink">
            No players under {cap}% ownership right now
          </h2>
          <p className="font-body text-body text-ink-2">Try raising the slider.</p>
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          {/* Not sortable — no data-key/onClick headers, matching vanilla. */}
          <table aria-label="Differentials" className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-line bg-surface">
                {["Pos", "Player", "Team", "£m", "Own %", "xP (10–90% band)"].map((label) => (
                  <th
                    key={label}
                    scope="col"
                    className="px-3 py-2 font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2"
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.player_code} className="border-b border-line">
                  <td className="px-3 py-2">{r.position}</td>
                  <td className="px-3 py-2">
                    {r.name}
                    <StatusFlag status={r.status} news={r.news} />
                  </td>
                  <td className="px-3 py-2">{r.team_short}</td>
                  <td className="px-3 py-2 font-label text-label tabular-nums">
                    {fixed1(r.price_m)}
                  </td>
                  <td className="px-3 py-2 font-label text-label tabular-nums">
                    {diffOwnershipCell(r.ownership)}
                  </td>
                  <td className="px-3 py-2">
                    <BandCell row={r} maxHi={maxHi} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
