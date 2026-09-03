import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchJson, type RateResponse, type XpRow } from "../../lib/api";
import { ErrorState } from "../ErrorState";
import { RateDiff } from "../RateDiff";
import { PlanTransfers } from "../PlanTransfers";

export interface RateTabProps {
  entry: number | null;
}

/* Custom fetch (not lib/api.ts's fetchApi) — mirrors web/team.html:84-85's
 * exact error extraction: `(await r.json()).detail || r.status`. fetchApi
 * discards the response body on failure (only the status code survives),
 * which cannot reproduce vanilla's `{message}` (D-19 requires the API's
 * own `detail` field when present). Same precedent as routes/Scoreboard.tsx
 * writing its own fetch when the shared helper's behaviour doesn't fit. */
async function fetchRate(entry: number): Promise<RateResponse> {
  const res = await fetch(`/api/rate/${entry}`);
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = (await res.json()) as { detail?: string };
      detail = body?.detail;
    } catch {
      // Response body wasn't JSON — fall back to the status code below.
    }
    throw new Error(detail || String(res.status));
  }
  return (await res.json()) as RateResponse;
}

/** Verbatim port of web/team.html:66's fmtRank. */
function fmtRank(n: number | null | undefined): string {
  return n == null ? "–" : n.toLocaleString();
}

interface TileProps {
  heading: string;
  value: ReactNode;
  detail: ReactNode;
}

function Tile({ heading, value, detail }: TileProps) {
  return (
    <div className="rounded border border-line bg-surface p-4">
      <p className="font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2">
        {heading}
      </p>
      <p className="mt-1 font-display text-display font-bold text-ink">{value}</p>
      <p className="mt-1 font-label text-label text-ink-2">{detail}</p>
    </div>
  );
}

/* Rate tab (D-19, D-20): fetches /api/rate/{entry} only once this tab
 * mounts — Team.tsx mounts only the active panel, so this never runs while
 * the Squad tab is active — then caches it by entry for the session. The
 * four tiles reproduce web/team.html:90-105's exact headings, value
 * formatting and fallback logic verbatim (03-02-PLAN.md Task 3's
 * read_first line ranges). */
export function RateTab({ entry }: RateTabProps) {
  const rateQuery = useQuery({
    queryKey: ["rate", entry],
    queryFn: () => fetchRate(entry as number),
    enabled: entry != null,
    retry: false,
  });
  /* The diff (D-18) resolves the suggested buy against the full player
   * pool, not just the 15-row squad — see RateDiff.tsx's resolveRateOverlay.
   * Gated on `entry != null` like rateQuery so this tab never fetches while
   * unmounted/inactive (D-20). */
  const xpQuery = useQuery({
    queryKey: ["xp_table"],
    queryFn: () => fetchJson<XpRow[]>("/data/xp_table.json"),
    enabled: entry != null,
    staleTime: 60_000,
  });

  if (entry == null) {
    return (
      <div className="py-4">
        <p className="font-body text-body text-ink-2">
          Load a team on the <span className="font-bold text-ink">Squad</span> tab to rate it
          against the model's optimum.
        </p>
      </div>
    );
  }

  if (rateQuery.isPending || xpQuery.isPending) {
    return (
      <p role="status" className="py-4 font-body text-body text-ink-2">
        Solving your squad…
      </p>
    );
  }

  if (rateQuery.isError) {
    const message =
      rateQuery.error instanceof Error ? rateQuery.error.message : String(rateQuery.error);
    return (
      <p className="py-4 font-body text-body text-ink-2">
        Couldn't rate that team: {message}. Check the ID and try again.
      </p>
    );
  }

  if (xpQuery.isError) {
    console.error(xpQuery.error);
    return <ErrorState resource="the player data" onRetry={() => xpQuery.refetch()} />;
  }

  if (!rateQuery.data || !xpQuery.data) {
    return null;
  }

  const d = rateQuery.data;
  const xpTable = xpQuery.data;
  const manager = d.manager;

  return (
    <div className="py-4">
      {manager?.team_name && (
        <h1 className="font-heading text-heading font-bold text-ink">
          {manager.team_name}
          {manager.manager ? (
            <span className="ml-2 font-label text-label text-ink-2">· {manager.manager}</span>
          ) : null}
        </h1>
      )}

      <div className="mt-4 grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
        <Tile
          heading="Team score"
          value={
            <>
              {d.score}
              <span className="font-label text-label">/100</span>
            </>
          }
          detail={
            <>
              best XI xP {d.xi_xp}
              {d.xi_p10 != null ? ` (${d.xi_p10}–${d.xi_p90} in 8/10 GWs)` : ""} vs ideal{" "}
              {d.ideal_xi_xp}
            </>
          }
        />
        <Tile
          heading="Season so far"
          value={
            <>
              {manager?.overall_points ?? "–"} <span className="font-label text-label">pts</span>
            </>
          }
          detail={`overall rank ${fmtRank(manager?.overall_rank)} · last GW ${
            manager?.gw_points ?? "–"
          } pts`}
        />
        <Tile heading="Captain" value={d.captain} detail="best armband in your current squad" />
        {d.best_move ? (
          <Tile
            heading="Best move"
            value={`${d.best_move.sell.join(", ")} → ${d.best_move.buy.join(", ")}`}
            detail={`+${d.best_move.xp_gain} xP this gameweek`}
          />
        ) : (
          <Tile heading="Best move" value="Hold" detail="no single transfer beats your current squad" />
        )}
      </div>

      <RateDiff xi={d.xi} bestMove={d.best_move} xpTable={xpTable} gw={d.gw} />

      <PlanTransfers entryId={entry} freeTransfersEstimate={d.free_transfers ?? null} xpTable={xpTable} />
    </div>
  );
}

export default RateTab;
