import type { ReactNode } from "react";
import { useState } from "react";
import type { PlanResponse, PlanWeek, XpRow } from "../lib/api";
import { pairMoves } from "../lib/pairMoves";
import { deriveViceCaptain, joinSquad } from "../lib/squadJoin";
import { Pitch } from "./pitch/Pitch";

export interface PlanTransfersProps {
  entryId: number;
  /** The rating's own free_transfers estimate (or null) — prefills the
   * Free-transfers input, falling back to 1 (D-19). */
  freeTransfersEstimate: number | null;
  /** xp_table.json's full pool — needed by each planned week's squad pitch
   * (Task 3). Threaded through here so RateTab fetches it once. */
  xpTable: XpRow[];
}

interface PlanState {
  status: "idle" | "pending" | "error" | "success";
  horizon: number;
  data?: PlanResponse;
  error?: string;
}

/* POST /api/plan mirroring vanilla's plan() (web/team.html:152-165) exactly:
 * a conditional free_transfers spread (an emptied/invalid input falls back
 * to the server's own estimate rather than sending a bad value), and the
 * same {detail} extraction on failure as RateTab.tsx's fetchRate (fetchApi
 * discards the response body on a non-ok response, which cannot reproduce
 * vanilla's exact error copy — same precedent). */
async function postPlan(
  entry: number,
  horizon: number,
  freeTransfers: number | null,
): Promise<PlanResponse> {
  const body: { entry: number; horizon: number; free_transfers?: number } = { entry, horizon };
  if (freeTransfers != null) {
    body.free_transfers = freeTransfers;
  }
  const res = await fetch("/api/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const parsed = (await res.json()) as { detail?: string };
      detail = parsed?.detail;
    } catch {
      // Response body wasn't JSON — fall back to the status code below.
    }
    throw new Error(detail || String(res.status));
  }
  return (await res.json()) as PlanResponse;
}

/* Plan-transfers flow (D-19, D-15). Verbatim vanilla controls/copy/bounds:
 * Free transfers (min=1 max=5, prefilled from the rating's estimate), the
 * five-option horizon select (no five-gameweek option — matches vanilla
 * exactly), and the "Plan my transfers" CTA. The multi-gameweek wait warning
 * (D-15's stated user priority) appears only above a one-gameweek horizon.
 * Per-week output rendering lands in Task 3. */
export function PlanTransfers({ entryId, freeTransfersEstimate, xpTable }: PlanTransfersProps) {
  const [ft, setFt] = useState(String(freeTransfersEstimate ?? 1));
  const [horizon, setHorizon] = useState("3");
  const [state, setState] = useState<PlanState>({ status: "idle", horizon: 3 });

  async function submitPlan() {
    const hz = Number(horizon || 1);
    const ftNum = Number(ft);
    const ftToSend = Number.isFinite(ftNum) && ftNum >= 1 ? ftNum : null;
    setState({ status: "pending", horizon: hz });
    try {
      const data = await postPlan(entryId, hz, ftToSend);
      setState({ status: "success", horizon: hz, data });
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setState({ status: "error", horizon: hz, error: message });
    }
  }

  const pending = state.status === "pending";

  return (
    <div className="mt-8">
      <h2 className="font-heading text-heading font-bold text-ink">Plan transfers</h2>
      <p className="mt-1 font-body text-body text-ink-2">
        The solver plans your moves jointly over the horizon — when to move now, when to bank a
        free transfer, when a hit pays for itself. Free transfers are pre-filled with our estimate
        from your transfer history (FPL only shows the true figure to your own login) — correct it
        if the official site says otherwise.
      </p>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 font-label text-label text-ink-2">
          Free transfers
          <input
            type="number"
            min="1"
            max="5"
            value={ft}
            onChange={(e) => setFt(e.target.value)}
            className="min-h-[44px] w-[80px] rounded border border-line bg-surface px-3 py-2 font-mono text-label tabular-nums text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 font-label text-label text-ink-2">
          Plan over
          <select
            value={horizon}
            onChange={(e) => setHorizon(e.target.value)}
            className="min-h-[44px] rounded border border-line bg-surface px-3 py-2 font-label text-label text-ink"
          >
            <option value="1">next GW only</option>
            <option value="2">2 gameweeks</option>
            <option value="3">3 gameweeks</option>
            <option value="4">4 gameweeks</option>
            <option value="6">6 gameweeks</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => void submitPlan()}
          disabled={pending}
          className="min-h-[44px] rounded bg-accent px-4 py-2 font-label text-label font-bold text-bg disabled:opacity-60"
        >
          Plan my transfers
        </button>
      </div>

      {pending && (
        <p role="status" className="mt-4 font-body text-body text-ink-2">
          {`Planning ${state.horizon} gameweek${state.horizon > 1 ? "s" : ""} jointly…`}
          {state.horizon > 1
            ? " (a fresh horizon takes ~10-60s while future gameweeks are predicted)"
            : ""}
        </p>
      )}

      {state.status === "error" && (
        <p className="mt-4 font-body text-body text-ink-2">Planning failed: {state.error}</p>
      )}

      {state.status === "success" && state.data && (
        <div>
          {state.data.weeks.map((week, i) => (
            <PlanWeekBlock key={week.gw} week={week} index={i} xpTable={xpTable} />
          ))}
          <p className="mt-6 font-body text-body text-ink-2">
            Week one is the decision to act on; later weeks are the current plan and will
            re-optimise as prices, injuries and form move.
          </p>
        </div>
      )}
    </div>
  );
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

/* One planned gameweek (Task 3, D-19/D-15): moves + projected-XI tiles,
 * a collapsible squad pitch (open only for week one), reproducing
 * web/team.html:166-181's exact structure and conditional copy — the hit-
 * cost clause is entirely omitted (not "0 pts") when a week takes no hits,
 * and the 8/10 GWs clause is entirely omitted when that week's interval is
 * null (Pitfall 2). The squad list substitution for the shared <Pitch>
 * component is PARITY-DEVIATIONS ledger row 11 — already authorised, no new
 * ledger row needed. */
function PlanWeekBlock({
  week,
  index,
  xpTable,
}: {
  week: PlanWeek;
  index: number;
  xpTable: XpRow[];
}) {
  const heading = `GW${week.gw} ${index === 0 ? "— do this now" : "— planned"}`;
  const pairs = pairMoves(week.sells, week.buys);
  const movesValue =
    week.buys.length > 0 ? (
      <>
        {pairs.map((pair, i) => (
          <span key={`${pair.sellName}-${pair.buyName}-${i}`} className="block">
            {pair.sellName} → {pair.buyName}{" "}
            <span className="font-label text-[11px] uppercase text-ink-2">{pair.position}</span>
          </span>
        ))}
      </>
    ) : (
      "Hold"
    );
  const movesDetail = `${week.buys.length} transfer(s)${
    week.hits ? `, −${4 * week.hits} pts in hits` : ""
  } · ${week.free_transfers_after} FT carried to next GW`;
  const xiDetail = `${
    week.xi_p10 != null ? `${week.xi_p10}–${week.xi_p90} in 8/10 GWs · ` : ""
  }captain ${week.captain} · bank £${week.bank.toFixed(1)}m`;

  const players = joinSquad(week.squad, xpTable);
  const captainCode = week.squad.find((r) => r.captain)?.player_code ?? null;
  const xpByCode = new Map(xpTable.map((row) => [row.player_code, row]));
  const viceCode = deriveViceCaptain(
    week.squad
      .filter((r) => r.starting)
      .map((r) => ({ player_code: r.player_code, captain: r.captain })),
    xpByCode,
  );

  return (
    <div className="mt-6">
      <h2 className="font-heading text-heading font-bold text-ink">{heading}</h2>
      <div className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
        <Tile heading="Moves" value={movesValue} detail={movesDetail} />
        <Tile
          heading="Projected XI"
          value={
            <>
              {week.xi_xp} <span className="font-label text-label">xP</span>
            </>
          }
          detail={xiDetail}
        />
      </div>
      <details open={index === 0} className="mt-3">
        <summary className="cursor-pointer font-label text-label font-bold text-ink-2">
          Squad for GW{week.gw}
        </summary>
        <div className="mt-2">
          <Pitch players={players} captainCode={captainCode} viceCode={viceCode} />
        </div>
      </details>
    </div>
  );
}

export default PlanTransfers;
