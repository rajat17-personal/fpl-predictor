import { TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { fetchJson, type Watchlist, type WatchlistRow } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { fixed1, localeInt } from "../lib/format";
import { usePageMeta } from "../lib/usePageMeta";

/* Ported from web/prices.html's inline script (lines 54-103), verified
 * 2026-09-01. R25-R31: progress math and the three mode-note copy variants
 * port verbatim. R29/Pitfall 3: price_m/ownership go through NO optional
 * chaining and NO en-dash fallback here — deliberately different from the
 * xP table's Own % column; do not unify with lib/format.ts's orDash. Not
 * sortable — no data-key headers in vanilla, port that exactly. Rise/fall
 * trend icons (ledger entry 5, PARITY-DEVIATIONS.md) are a deliberate
 * addition vanilla has no equivalent for. */

const EYEBROW_TH =
  "px-3 py-2 font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2";

const COLUMN_LABELS = [
  "Player",
  "Team",
  "Pos",
  "£m",
  "Own %",
  "Net transfers",
  "Progress",
  "Status",
];

interface ProgressResult {
  bar: number;
  label: string;
}

/* R25-R27: raw/pct/bar math and the per-mode label branch, verbatim. The
 * bar is clamped at 100% while the label is not — that asymmetry is
 * vanilla behaviour, not a bug. */
function computeProgress(row: WatchlistRow, mode: string): ProgressResult {
  const raw = row.prob ?? row.progress ?? 0;
  const pct = Math.round(100 * Math.abs(raw));
  const bar = Math.min(pct, 100);
  const label =
    mode === "official"
      ? `${pct}%${
          row.proj_tonight != null
            ? ` → ${Math.round(100 * Math.abs(row.proj_tonight))}% tonight`
            : ""
        }`
      : row.prob != null
        ? `${pct}%`
        : `${bar}% of threshold`;
  return { bar, label };
}

/* R30/R31: exactly one of three verbatim note variants, keyed on w.mode.
 * The official variant's price-locked-players sentence is appended only
 * when w.locked_players is truthy (0 counts as falsy, same as vanilla). */
function ModeNote({ w }: { w: Watchlist }) {
  if (w.mode === "official") {
    const lockedSentence = w.locked_players
      ? ` ${w.locked_players} price-locked players (new signings, recently unflagged) are excluded.`
      : "";
    return (
      <p className="mt-2 rounded border border-line bg-surface p-3 font-body text-body text-ink-2">
        <strong className="text-ink">Live from FPL's own price predictor.</strong>{" "}
        {`Progress is the official percentage toward the next change (100% = threshold reached — change due at the 00:00 UK update); status follows FPL's published likelihood.${lockedSentence}`}
      </p>
    );
  }

  if (w.mode === "heuristic") {
    return (
      <p className="mt-2 rounded border border-warn bg-warn-bg p-3 font-body text-body text-ink-2">
        <strong className="text-ink">Heuristic mode.</strong>{" "}
        These lists rank net event transfers per owner — the community-standard signal. A
        trained model takes over automatically once enough daily history is collected, and
        its hit-rate will be published on the{" "}
        <Link to="/scoreboard" className="text-accent underline">
          scoreboard
        </Link>
        .
      </p>
    );
  }

  return (
    <p className="mt-2 rounded border border-line bg-surface p-3 font-body text-body text-ink-2">
      {`Model predictions (trained ${w.trained_utc?.slice(0, 10)}; hit-rate on actual movers ${(100 * w.val_moved_hit!).toFixed(0)}% in validation). Status reflects the model's probability.`}
    </p>
  );
}

interface PriceTableProps {
  title: string;
  rows: WatchlistRow[];
  mode: string;
  trend: "up" | "down";
}

function PriceTable({ title, rows, mode, trend }: PriceTableProps) {
  return (
    <section className="mt-8">
      <h2 className="font-heading text-heading font-bold text-ink">{title}</h2>
      {rows.length === 0 ? (
        <div className="flex min-h-[16rem] flex-col items-center justify-center gap-2 py-12 text-center">
          <h3 className="font-heading text-heading font-bold text-ink">
            Nothing flagged right now
          </h3>
          <p className="font-body text-body text-ink-2">
            No players are currently trending toward a price change in this direction.
          </p>
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table aria-label={title} className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-line bg-surface">
                {COLUMN_LABELS.map((label) => (
                  <th key={label} scope="col" className={EYEBROW_TH}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const { bar, label } = computeProgress(r, mode);
                return (
                  <tr key={r.name} className="border-b border-line">
                    <td className="px-3 py-2">
                      {trend === "up" ? (
                        <TrendingUp
                          aria-hidden="true"
                          className="mr-1 inline-block h-4 w-4 text-accent"
                        />
                      ) : (
                        <TrendingDown
                          aria-hidden="true"
                          className="mr-1 inline-block h-4 w-4 text-bad"
                        />
                      )}
                      {r.name}
                    </td>
                    <td className="px-3 py-2">{r.team}</td>
                    <td className="px-3 py-2">{r.position}</td>
                    {/* R29: NO optional chaining, NO fallback — unlike the
                     * xP table's Own % column (Pitfall 3). */}
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {fixed1(r.price_m)}
                    </td>
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {fixed1(r.ownership)}
                    </td>
                    {/* R28: toLocaleString, NEVER a fixed-decimal format. */}
                    <td className="px-3 py-2 font-label text-label tabular-nums">
                      {localeInt(r.net_transfers ?? 0)}
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-flex flex-col gap-1">
                        <span
                          aria-hidden="true"
                          className="relative block h-1.5 w-24 rounded-full bg-surface-2"
                        >
                          <span
                            className="absolute top-0 left-0 h-1.5 rounded-full bg-band"
                            style={{ width: `${bar}%` }}
                          />
                        </span>
                        <span className="font-label text-label tabular-nums text-ink-2">
                          {label}
                        </span>
                      </span>
                    </td>
                    <td className="px-3 py-2">{r.status ?? ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function Prices() {
  usePageMeta("/prices");

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["watchlist"],
    // Root-relative path — a bare "data/watchlist.json" resolves against
    // the current client-side route and 404s (RESEARCH.md Pitfall 5).
    queryFn: () => fetchJson<Watchlist>("/data/watchlist.json"),
    staleTime: 60_000,
  });

  if (isPending) {
    return <Spinner />;
  }

  if (isError) {
    console.error(error);
    return <ErrorState resource="the price watch data" onRetry={() => refetch()} />;
  }

  if (!data) {
    return <EmptyState />;
  }

  return (
    <div className="py-8">
      <h1 className="font-display text-display font-bold text-ink">Price watch</h1>
      <p className="mt-2 font-body text-body text-ink-2">
        Players trending toward an overnight price change — data as of {data.date}.
      </p>

      <ModeNote w={data} />

      <PriceTable title="Likely risers" rows={data.risers} mode={data.mode} trend="up" />
      <PriceTable title="Likely fallers" rows={data.fallers} mode={data.mode} trend="down" />

      <p className="mt-4 font-body text-body text-ink-2">
        Low-ownership players rise and fall too — FPL's thresholds scale with how many
        managers own a player, so a 1%-owned player with a big inflow can move faster than a
        40%-owned one. Progress is our estimate of distance to the change threshold; it
        becomes a calibrated probability once the model has enough history to train.
      </p>
    </div>
  );
}
