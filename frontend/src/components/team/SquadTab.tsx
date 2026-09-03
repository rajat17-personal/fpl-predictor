import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchApi,
  fetchJson,
  type MetaResponse,
  type SolveRequest,
  type SolveResult,
  type SolveTransfersResult,
  type SquadResponse,
  type SquadRow,
  type TeamPick,
  type TeamResponse,
  type XpRow,
} from "../../lib/api";
import { Spinner } from "../Spinner";
import { ErrorState } from "../ErrorState";
import { EmptyState } from "../EmptyState";
import { Pitch } from "../pitch/Pitch";
import type { PlayerMark } from "../pitch/PlayerCard";
import { SolveControls, type SolveControlValues } from "../SolveControls";
import { SolveResultsBar } from "../SolveResultsBar";
import { deriveFormation } from "../../lib/formation";
import { deriveViceCaptain, joinSquad } from "../../lib/squadJoin";

export interface SquadTabProps {
  entry: number | null;
  onLoadEntry: (entry: number) => void;
  onClearEntry: () => void;
}

/* Lock/exclude marks (D-13, D-17): keyed by player_code, values are the two
 * mutually-exclusive marks Pitch/PlayerCard already render (03-01's prop
 * surface) — clearing an entry removes the key entirely rather than storing
 * a null value, so the record only ever holds real marks and a plain key
 * filter turns it into a request array. Lives in this component's state
 * only: never the URL, never storage (D-13's "MARKS STAY EPHEMERAL" gate),
 * and never cleared by a solve (D-17) — only Task 3's Reset action clears
 * it. */
export type MarkRecord = Record<number, "locked" | "excluded">;

/* Derived request arrays (Pitfall 3): numeric player_code by construction, a
 * card's displayed name never enters them. Exported so this file's own solve
 * request builder (Task 2) and their direct unit tests share one
 * implementation instead of re-deriving the filter per call site. */
export function lockedCodes(marks: MarkRecord): number[] {
  return Object.entries(marks)
    .filter(([, mark]) => mark === "locked")
    .map(([code]) => Number(code));
}

export function excludedCodes(marks: MarkRecord): number[] {
  return Object.entries(marks)
    .filter(([, mark]) => mark === "excluded")
    .map(([code]) => Number(code));
}

/* Builds /api/solve's request body (D-15, Pitfall 3): locks/excludes always
 * come from the tested lockedCodes/excludedCodes derivations above — numeric
 * player_code, never a card's displayed name. max_transfers is omitted
 * entirely (not sent as null) when SolveControls' matching input was left
 * empty, so an unset control never becomes a round-trip validation quirk.
 * mode/budget are never included — D-14 limits the exposed surface to the
 * three knobs SolveControls collects. */
export function buildSolveRequest(
  entry: number,
  values: SolveControlValues,
  marks: MarkRecord,
): SolveRequest {
  const body: SolveRequest = {
    entry,
    free_transfers: values.freeTransfers,
    horizon: values.horizon,
    locks: lockedCodes(marks),
    excludes: excludedCodes(marks),
  };
  if (values.maxTransfers != null) {
    body.max_transfers = values.maxTransfers;
  }
  return body;
}

/* Custom fetch (not lib/api.ts's fetchApi) — same precedent as RateTab.tsx's
 * fetchRate and PlanTransfers.tsx's postPlan: fetchApi discards the response
 * body on a non-ok response, which cannot reproduce the exact "Couldn't
 * solve: {message}." copy (D-15) that needs the response's own `detail`
 * field when present, falling back to the status code otherwise. */
async function postSolve(body: SolveRequest): Promise<SolveResult> {
  const res = await fetch("/api/solve", {
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
  return (await res.json()) as SolveResult;
}

export interface SolveState {
  status: "idle" | "pending" | "error" | "success";
  data?: SolveTransfersResult;
  error?: string;
}

/* Solve request lifecycle (D-15), extracted as its own hook so the
 * ordering-safety guard (T-03-16 — "a superseded solve response overwriting
 * the displayed squad") is directly unit-testable via renderHook, calling
 * solveNow() twice back-to-back without going through a real disabled-button
 * click. (D-15's button-disable is a separate, UI-level brake against
 * *starting* a second solve — T-03-15 — that this hook does not enforce
 * itself; SolveControls' own `disabled` prop is what stops a real user from
 * ever reaching this path through the rendered button. This hook's guard is
 * the independent safety net for whenever two solves land in flight anyway.)
 *
 * solveSeqRef captures the sequence number current when a solve starts, and
 * only applies that solve's result if the number is still current when the
 * response arrives — a later solve bumps the ref, so an earlier response
 * that arrives after is recognised as stale and dropped. Local useState, not
 * TanStack Query's useMutation — no existing precedent for useMutation in
 * this codebase (03-03-PLAN.md's SUMMARY records the same choice for
 * PlanTransfers.tsx). */
export function useSolveController(entry: number | null, marks: MarkRecord) {
  const [solve, setSolve] = useState<SolveState>({ status: "idle" });
  const solveSeqRef = useRef(0);

  async function solveNow(values: SolveControlValues) {
    if (entry == null) {
      return;
    }
    const seq = ++solveSeqRef.current;
    setSolve({ status: "pending" });
    const body = buildSolveRequest(entry, values, marks);
    try {
      const result = await postSolve(body);
      if (seq !== solveSeqRef.current) {
        return; // A newer solve has started — this response is stale.
      }
      if (result.kind === "transfers") {
        setSolve({ status: "success", data: result });
      }
    } catch (e) {
      if (seq !== solveSeqRef.current) {
        return;
      }
      const message = e instanceof Error ? e.message : String(e);
      setSolve({ status: "error", error: message });
    }
  }

  /* Reset to loaded squad (D-17): discards the current solve result and
   * invalidates any in-flight solve (bumping solveSeqRef so a response that
   * arrives afterward is treated as superseded). No network request. */
  function resetSolve() {
    solveSeqRef.current += 1;
    setSolve({ status: "idle" });
  }

  return { solve, solveNow, resetSolve };
}

/* DEF/MID/FWD starter-count bounds, mirrored from optimize/squad_ilp.py's
 * own formation constraints (verified in 03-RESEARCH.md Pattern 1: DEF 3-5,
 * MID 2-5, FWD 1-3, GK always exactly 1). Used only by selectLoadedSquad
 * below to reconstruct a legal eleven — squad.json/the ILP already supply
 * starting/captain directly, so this search never runs for the default
 * model-squad view. */
const POSITION_RANGE: Record<"DEF" | "MID" | "FWD", readonly [number, number]> = {
  DEF: [3, 5],
  MID: [2, 5],
  FWD: [1, 3],
};

/* D-13's "the real integration risk" (03-02-PLAN.md Task 1): /api/team/
 * {entry}'s picks carry no xp/starting/captain. Joins each pick to
 * xp_table.json by player_code (xp: 0 when unmatched — that pick is then
 * never selected as a starter, per the plan's action), then reconstructs a
 * legal starting eleven by choosing the DEF/MID/FWD split (summing to 10,
 * within the bounds above) that maximises total joined xp, exactly one GK
 * (the higher-xp of the two), and marks the highest-xp_capt starter as
 * captain — falling back to the highest-xp starter when every starter's
 * xp_capt is null. Exported (not just used internally) so plan 03-04 reuses
 * it after a solve, per the plan's explicit instruction. */
export function selectLoadedSquad(picks: TeamPick[], xpTable: XpRow[]): SquadRow[] {
  const xpByCode = new Map(xpTable.map((row) => [row.player_code, row]));
  const withXp = picks.map((pick) => ({
    ...pick,
    xp: xpByCode.get(pick.player_code)?.xp ?? 0,
    xpCapt: xpByCode.get(pick.player_code)?.xp_capt ?? null,
  }));

  const byPos = (position: string) =>
    withXp.filter((p) => p.position === position).sort((a, b) => b.xp - a.xp);
  const gk = byPos("GK");
  const def = byPos("DEF");
  const mid = byPos("MID");
  const fwd = byPos("FWD");

  const sumTop = (rows: typeof withXp, n: number) =>
    rows.slice(0, n).reduce((total, row) => total + row.xp, 0);

  let best: { d: number; m: number; f: number; sum: number } | null = null;
  for (let d = POSITION_RANGE.DEF[0]; d <= POSITION_RANGE.DEF[1]; d++) {
    for (let m = POSITION_RANGE.MID[0]; m <= POSITION_RANGE.MID[1]; m++) {
      for (let f = POSITION_RANGE.FWD[0]; f <= POSITION_RANGE.FWD[1]; f++) {
        if (d + m + f !== 10) continue;
        if (d > def.length || m > mid.length || f > fwd.length) continue;
        const sum = sumTop(def, d) + sumTop(mid, m) + sumTop(fwd, f);
        if (!best || sum > best.sum) {
          best = { d, m, f, sum };
        }
      }
    }
  }

  const startingCodes = new Set<number>();
  if (gk.length > 0) {
    startingCodes.add(gk[0].player_code);
  }
  if (best) {
    def.slice(0, best.d).forEach((p) => startingCodes.add(p.player_code));
    mid.slice(0, best.m).forEach((p) => startingCodes.add(p.player_code));
    fwd.slice(0, best.f).forEach((p) => startingCodes.add(p.player_code));
  }

  const starters = withXp.filter((p) => startingCodes.has(p.player_code));
  let captainCode: number | null = null;
  let bestCapt = -Infinity;
  for (const starter of starters) {
    if (starter.xpCapt != null && starter.xpCapt > bestCapt) {
      bestCapt = starter.xpCapt;
      captainCode = starter.player_code;
    }
  }
  if (captainCode == null) {
    let bestXp = -Infinity;
    for (const starter of starters) {
      if (starter.xp > bestXp) {
        bestXp = starter.xp;
        captainCode = starter.player_code;
      }
    }
  }

  return withXp.map((p) => ({
    player_code: p.player_code,
    name: p.name,
    team: p.team,
    position: p.position,
    price_m: p.price_m,
    xp: p.xp,
    starting: startingCodes.has(p.player_code),
    captain: p.player_code === captainCode,
  }));
}

/* Load-your-own-team control (D-10): a label, a numeric entry-ID input, the
 * vanilla-structured helper line, and the "Load team" CTA. An empty input is
 * a client-side no-op mirroring vanilla's `if (!id) return;` guard — no
 * request, no error. Non-numeric input is also rejected before firing,
 * mirroring the server's own `min="1"` bound so a bad value never becomes a
 * round-trip 422. 6980093 is placeholder/example text only — D-10 forbids
 * ever auto-submitting it on the user's behalf. */
function LoadTeamControl({ onLoadEntry }: { onLoadEntry: (entry: number) => void }) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    if (!/^\d+$/.test(trimmed)) {
      return;
    }
    const id = Number(trimmed);
    if (!Number.isFinite(id) || id < 1) {
      return;
    }
    onLoadEntry(id);
  }

  return (
    <div className="mt-6">
      <label htmlFor="team-entry-input" className="font-label text-label text-ink-2">
        Load your own team
      </label>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <input
          id="team-entry-input"
          type="number"
          min="1"
          aria-label="FPL team ID"
          placeholder="Team ID, e.g. 6980093"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              submit();
            }
          }}
          className="min-h-[44px] rounded border border-line bg-surface px-3 py-2 font-mono text-label tabular-nums text-ink"
        />
        <button
          type="button"
          onClick={submit}
          className="min-h-[44px] rounded bg-accent px-4 py-2 font-label text-label font-bold text-bg"
        >
          Load team
        </button>
      </div>
      <p className="mt-2 font-body text-body text-ink-2">
        Your ID is in the URL on the official site&apos;s Points page:{" "}
        fantasy.premierleague.com/entry/6980093/…
      </p>
    </div>
  );
}

/* Squad tab (D-09, D-10, D-11): two modes over one pitch. With no `entry`,
 * this is 03-01's view-only model-squad behaviour verbatim, plus the load
 * control below the pitch. With an `entry`, it fetches /api/team/{entry},
 * normalises the response into a startable eleven (selectLoadedSquad above)
 * and renders the loaded squad with a Change-team affordance. Follows
 * Prices.tsx's isPending/isError/!data shell for every query. */
export function SquadTab({ entry, onLoadEntry, onClearEntry }: SquadTabProps) {
  /* Marks are supplied to <Pitch> only in loaded-team mode (below) — the
   * default model-squad pitch stays view-only (03-01's resolved
   * Claude's-Discretion item) by simply never receiving onMark, so
   * PlayerCard renders no popover trigger at all for it. */
  const [marks, setMarks] = useState<MarkRecord>({});

  function handleMark(code: number, mark: PlayerMark) {
    setMarks((prev) => {
      if (mark == null) {
        const next = { ...prev };
        delete next[code];
        return next;
      }
      return { ...prev, [code]: mark };
    });
  }

  const { solve, solveNow, resetSolve } = useSolveController(entry, marks);

  /* Reset to loaded squad (D-17, verbatim CTA copy): clears marks and
   * discards the current solve result via resetSolve(); performs no network
   * request — the solve was only ever a local preview. */
  function handleReset() {
    setMarks({});
    resetSolve();
  }

  const metaQuery = useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchJson<MetaResponse>("/data/meta.json"),
    staleTime: 60_000,
  });
  const xpQuery = useQuery({
    queryKey: ["xp_table"],
    queryFn: () => fetchJson<XpRow[]>("/data/xp_table.json"),
    staleTime: 60_000,
  });
  const squadQuery = useQuery({
    queryKey: ["squad"],
    queryFn: () => fetchJson<SquadResponse>("/data/squad.json"),
    staleTime: 60_000,
    enabled: entry == null,
  });
  const teamQuery = useQuery({
    queryKey: ["team", entry],
    queryFn: () => fetchApi<TeamResponse>(`/api/team/${entry}`),
    enabled: entry != null,
  });

  const baseIsPending = metaQuery.isPending || xpQuery.isPending;
  if (baseIsPending) {
    return <Spinner />;
  }

  const baseIsError = metaQuery.isError || xpQuery.isError;
  if (baseIsError) {
    console.error(metaQuery.error ?? xpQuery.error);
    const refetch = () => {
      void metaQuery.refetch();
      void xpQuery.refetch();
    };
    return <ErrorState resource="the team data" onRetry={refetch} />;
  }

  if (!metaQuery.data || !xpQuery.data) {
    return <EmptyState />;
  }

  const meta = metaQuery.data;
  const xpTable = xpQuery.data;

  if (entry != null) {
    if (teamQuery.isPending) {
      return (
        <div className="mt-6">
          <button
            type="button"
            disabled
            className="min-h-[44px] rounded bg-accent px-4 py-2 font-label text-label font-bold text-bg opacity-60"
          >
            Load team
          </button>
          <p role="status" className="mt-2 font-label text-label text-ink-2">
            Loading that team…
          </p>
        </div>
      );
    }

    if (teamQuery.isError) {
      const message =
        teamQuery.error instanceof Error ? teamQuery.error.message : String(teamQuery.error);
      return (
        <div className="mt-6">
          <p className="font-body text-body text-ink-2">
            Couldn't load that team: {message}. Check the ID and try again.
          </p>
          <button
            type="button"
            onClick={onClearEntry}
            className="mt-2 min-h-[44px] font-label text-label text-accent underline"
          >
            Change team
          </button>
        </div>
      );
    }

    if (!teamQuery.data) {
      return <EmptyState />;
    }

    /* The as-loaded squad — recomputed deterministically from teamQuery.data
     * (unchanged by a solve) every render, so it always reflects the team
     * exactly as it was loaded without needing separate state (D-17's
     * Reset target, and Task 3's IN-badge diff base). */
    const squadRows = selectLoadedSquad(teamQuery.data.picks, xpTable);
    /* D-16: a completed solve re-renders the same pitch in place with the
     * solve's own squad — never a second pitch. */
    const displayedRows =
      solve.status === "success" && solve.data ? solve.data.squad : squadRows;
    /* IN diff (D-16): computed against the codes of the squad as originally
     * loaded (squadRows, above) — never against a previous solve's result —
     * so a player who came in on an earlier solve and stayed keeps their IN
     * badge, and solving twice with an unchanged response leaves the badges
     * identical (idempotency). No "out" treatment on this pitch; outgoing
     * players simply disappear from the re-rendered squad. */
    const asLoadedCodes = new Set(squadRows.map((r) => r.player_code));
    const diffs: Record<number, "in"> = {};
    if (solve.status === "success" && solve.data) {
      for (const row of solve.data.squad) {
        if (!asLoadedCodes.has(row.player_code)) {
          diffs[row.player_code] = "in";
        }
      }
    }
    const players = joinSquad(displayedRows, xpTable);
    const formation = deriveFormation(displayedRows);
    const captainCode = displayedRows.find((r) => r.captain)?.player_code ?? null;
    const xpByCode = new Map(xpTable.map((row) => [row.player_code, row]));
    const viceCode = deriveViceCaptain(
      displayedRows
        .filter((r) => r.starting)
        .map((r) => ({ player_code: r.player_code, captain: r.captain })),
      xpByCode,
    );
    const teamName = teamQuery.data.manager?.team_name || `Team ${entry}`;

    return (
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="font-heading text-heading font-bold text-ink">
            {teamName} · GW{meta.gw}
          </h1>
          <button
            type="button"
            onClick={onClearEntry}
            className="min-h-[44px] font-label text-label text-accent underline"
          >
            Change team
          </button>
        </div>
        <p className="mt-1 font-mono text-label tabular-nums text-ink-2">{formation}</p>

        <div className="mt-4">
          <Pitch
            players={players}
            captainCode={captainCode}
            viceCode={viceCode}
            marks={marks}
            diffs={diffs}
            onMark={handleMark}
          />
        </div>

        {/* freeTransfersEstimate is null here: the only endpoint that returns
         * that estimate is /api/rate/{entry} (see api/main.py's _free_transfers),
         * and D-20 forbids the Squad tab firing a rate/plan-cost fetch just to
         * prefill this input. SolveControls falls back to 1 — /api/solve's own
         * server-side default and _free_transfers' own fallback when a
         * manager's transfer history is unavailable — so the field is still
         * never blank, and it stays editable per D-14. */}
        <SolveControls
          freeTransfersEstimate={null}
          pending={solve.status === "pending"}
          onSolve={(values) => void solveNow(values)}
        />

        <button
          type="button"
          onClick={handleReset}
          className="mt-2 min-h-[44px] font-label text-label text-ink-2 underline"
        >
          Reset to loaded squad
        </button>

        {solve.status === "error" && (
          <p className="mt-2 font-body text-body text-ink-2">
            Couldn't solve: {solve.error}. Check your inputs and try again.
          </p>
        )}

        {solve.status === "success" && solve.data && <SolveResultsBar result={solve.data} />}
      </div>
    );
  }

  if (squadQuery.isPending) {
    return <Spinner />;
  }

  if (squadQuery.isError) {
    console.error(squadQuery.error);
    return <ErrorState resource="the team data" onRetry={() => squadQuery.refetch()} />;
  }

  if (!squadQuery.data) {
    return <EmptyState />;
  }

  const { squad } = squadQuery.data;
  if (squad.length === 0) {
    return <EmptyState />;
  }

  const players = joinSquad(squad, xpTable);
  const formation = deriveFormation(squad);
  const captainCode = squad.find((r) => r.captain)?.player_code ?? null;
  const xpByCode = new Map(xpTable.map((row) => [row.player_code, row]));
  const viceCode = deriveViceCaptain(
    squad.filter((r) => r.starting).map((r) => ({ player_code: r.player_code, captain: r.captain })),
    xpByCode,
  );

  return (
    <div>
      <h1 className="font-heading text-heading font-bold text-ink">
        Model squad · GW{meta.gw}
      </h1>
      <p className="mt-1 font-mono text-label tabular-nums text-ink-2">{formation}</p>

      <div className="mt-4">
        <Pitch players={players} captainCode={captainCode} viceCode={viceCode} />
      </div>

      <LoadTeamControl onLoadEntry={onLoadEntry} />
    </div>
  );
}

export default SquadTab;
