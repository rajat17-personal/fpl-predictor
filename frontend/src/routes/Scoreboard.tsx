import { useQuery } from "@tanstack/react-query";
import type { ScoreboardResponse } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { usePageMeta } from "../lib/usePageMeta";

/* Ported from web/scoreboard.html's inline script (lines 60-94), verified
 * 2026-09-01. This is the one page in the phase that deliberately does NOT
 * use the shared `fetchJson` helper (lib/api.ts): fetchJson collapses every
 * non-ok HTTP status into one untyped Error, but this page needs to tell a
 * genuinely-missing pre-season file (404 — scoreboard.json does not exist
 * until the first gameweek is scored) apart from a real server/network
 * failure (D-08, RESEARCH.md Pitfall 2). A future reader tempted to
 * "simplify" this back to fetchJson would silently break that distinction —
 * do not, unless the D-08 requirement changes. */
async function fetchScoreboard(): Promise<ScoreboardResponse | null> {
  const res = await fetch("/data/scoreboard.json");
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`/data/scoreboard.json: ${res.status}`);
  }
  return (await res.json()) as ScoreboardResponse;
}

const EYEBROW_TH =
  "px-3 py-2 font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2";

interface TileProps {
  label: string;
  value: string;
  detail: string;
}

function Tile({ label, value, detail }: TileProps) {
  return (
    <div className="rounded border border-line bg-surface p-4">
      <p className="font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2">
        {label}
      </p>
      {/* Ledger entry 8: tile values render at the 28px Display token, weight
       * 700 — the two-weight typography contract has no 500 (vanilla uses
       * 24px/500). */}
      <p className="mt-1 font-display text-display font-bold text-ink">{value}</p>
      <p className="mt-1 font-label text-label text-ink-2">{detail}</p>
    </div>
  );
}

function numOrDash(v: number | null | undefined): string {
  return v == null ? "–" : String(v);
}

export default function Scoreboard() {
  usePageMeta("/scoreboard");

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["scoreboard"],
    queryFn: fetchScoreboard,
    staleTime: 60_000,
    // A 500 should surface promptly rather than after the default retry
    // backoff — this page's error path is the assertion that it is more
    // discriminating than vanilla's blanket catch (D-08).
    retry: false,
  });

  if (isPending) {
    return <Spinner />;
  }

  if (isError) {
    console.error(error);
    return <ErrorState resource="the scoreboard data" onRetry={() => refetch()} />;
  }

  const entries = data?.entries ?? [];
  const summary = data?.summary;

  return (
    <div className="py-8">
      <h1 className="font-display text-display font-bold text-ink">The scoreboard</h1>
      <p className="mt-2 font-body text-body text-ink-2">
        Every gameweek's predictions are frozen before kickoff and scored after the whistle
        — against what happened, and against FPL's own expected points. No retro-fitting,
        no cherry-picking. Lower MAE and higher rank correlation are better.
      </p>

      {entries.length === 0 ? (
        <>
          {/* R36, verbatim under D-03 — these are six-season backtest
           * figures, not scored gameweeks; keeping the "Backtest"/"Seasons
           * validated" labelling here is the honesty claim this page rests
           * on. No history table renders in this state at all. */}
          <div className="mt-6 grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
            <Tile
              label="Backtest MAE"
              value="0.87 vs FPL 1.07"
              detail="held-out season, fixture level"
            />
            <Tile
              label="Backtest rank corr"
              value="0.74 vs FPL 0.30"
              detail="Spearman on the held-out season"
            />
            <Tile label="Seasons validated" value="6" detail="walk-forward, retrained each season" />
          </div>
          <p className="mt-6 font-body text-body text-ink-2">
            No gameweeks scored yet — the first entry appears automatically once the next
            gameweek finishes. In backtests over six seasons the model's fixture MAE was
            0.87 vs 1.07 for FPL's own expected points.
          </p>
        </>
      ) : (
        <>
          {/* R37: populated tiles. */}
          <div className="mt-6 grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
            <Tile
              label="Gameweeks scored"
              value={String(summary!.gameweeks)}
              detail="frozen pre-deadline, scored after"
            />
            <Tile
              label="MAE — points error"
              value={`${summary!.mae_model} vs FPL ${numOrDash(summary!.mae_fpl)}`}
              detail="mean abs error per player (lower is better)"
            />
            <Tile
              label="Rank correlation"
              value={`${summary!.spearman_model} vs FPL ${numOrDash(summary!.spearman_fpl)}`}
              detail="Spearman, predicted vs actual (higher is better)"
            />
            <Tile
              label="Captain average"
              value={String(summary!.captain_avg_points)}
              detail="points scored by our weekly captain pick"
            />
          </div>

          {/* R38: every entry the export emits, in export order — no
           * filtering, no re-ranking, no truncation. Per-row mae_fpl and
           * spearman_fpl fall back to the en-dash individually. Not
           * sortable. */}
          <div className="mt-6 overflow-x-auto">
            <table aria-label="Scoreboard history" className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-line bg-surface">
                  <th scope="col" className={EYEBROW_TH}>
                    GW
                  </th>
                  <th scope="col" className={EYEBROW_TH}>
                    MAE (us)
                  </th>
                  <th scope="col" className={EYEBROW_TH}>
                    MAE (FPL)
                  </th>
                  <th scope="col" className={EYEBROW_TH}>
                    Rank corr (us)
                  </th>
                  <th scope="col" className={EYEBROW_TH}>
                    Rank corr (FPL)
                  </th>
                  <th scope="col" className={EYEBROW_TH}>
                    Our captain
                  </th>
                  <th scope="col" className={EYEBROW_TH}>
                    Captain pts
                  </th>
                  <th scope="col" className={EYEBROW_TH}>
                    GW's best player
                  </th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.gw} className="border-b border-line">
                    <td className="px-3 py-2 font-label text-label tabular-nums">{e.gw}</td>
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {e.mae_model}
                    </td>
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {numOrDash(e.mae_fpl)}
                    </td>
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {e.spearman_model}
                    </td>
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {numOrDash(e.spearman_fpl)}
                    </td>
                    <td className="px-3 py-2">{e.captain.name}</td>
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {e.captain.points}
                    </td>
                    <td className="px-3 py-2">
                      {e.best_player.name}{" "}
                      <span className="font-label text-label tabular-nums text-ink-2">
                        ({e.best_player.points})
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
