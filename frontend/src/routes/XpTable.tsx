import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { fetchJson, type CaptainRow, type XpRow } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { BandCell } from "../components/BandCell";
import { fixed1, fixed2, orDash } from "../lib/format";
import { sortDirGlyph, sortRows, useSortable } from "../lib/sortable";
import { usePageMeta } from "../lib/usePageMeta";
import { StatusFlag } from "../lib/statusFlag";

/* The flagship xP table (D-06) — ported from web/index.html's inline script
 * (lines 83-131). Task 1 wired ONE path end to end: JSON contract → typed
 * row → sortable header → band cell → rendered table. Task 2 added the
 * position-chip + search filters, the verbatim page copy, and the
 * per-route <title>/<meta> pair. Task 3 (this extension) mounts the
 * accessible status flag on flagged rows and adds the Captain picks
 * sub-table. */

type SortKey =
  | "position"
  | "name"
  | "team_short"
  | "price_m"
  | "ownership"
  | "xp"
  | "xp_capt";

const NUMERIC_KEYS = new Set<SortKey>(["price_m", "ownership", "xp", "xp_capt"]);

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "position", label: "Pos" },
  { key: "name", label: "Player" },
  { key: "team_short", label: "Team" },
  { key: "price_m", label: "£m" },
  { key: "ownership", label: "Own %" },
  { key: "xp", label: "xP (10–90% band)" },
  { key: "xp_capt", label: "Captain xP" },
];

const POSITIONS = ["ALL", "GK", "DEF", "MID", "FWD"] as const;
type PositionFilter = (typeof POSITIONS)[number];

function chipLabel(p: PositionFilter): string {
  return p === "ALL" ? "All" : p;
}

export default function XpTable() {
  usePageMeta("/");

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["xp_table"],
    // Root-relative path — a bare "data/xp_table.json" resolves against the
    // current client-side route and 404s (RESEARCH.md Pitfall 5).
    queryFn: () => fetchJson<XpRow[]>("/data/xp_table.json"),
    staleTime: 60_000,
  });

  // The captains fetch failing must not take the main xP table down — its
  // own isError branch renders a quiet inline message, never ErrorState.
  const { data: captainsData, isError: captainsIsError } = useQuery({
    queryKey: ["captains"],
    queryFn: () => fetchJson<CaptainRow[]>("/data/captains.json"),
    staleTime: 60_000,
  });

  const { sortState, onSort } = useSortable<SortKey>();
  const [posFilter, setPosFilter] = useState<PositionFilter>("ALL");
  const [query, setQuery] = useState("");

  if (isPending) {
    return <Spinner />;
  }

  if (isError) {
    console.error(error);
    return <ErrorState resource="the xP table" onRetry={() => refetch()} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState />;
  }

  // R10: slice(0, 50) with NO re-sort — the pipeline pre-sorts descending by
  // xp; porting this assumption unchanged is the parity requirement.
  const top = data.slice(0, 50);
  const maxHi = Math.max(...top.map((r) => r.p90 ?? r.xp)); // R11: no floor

  // R12/R13: filters run strictly on top of the already-sliced top 50, never
  // against the full fetched array; search matches r.team (the full club
  // name, never rendered in any cell) as well as r.team_short.
  const normalizedQuery = query.trim().toLowerCase();
  const filtered = top.filter(
    (r) =>
      (posFilter === "ALL" || r.position === posFilter) &&
      (!normalizedQuery ||
        r.name.toLowerCase().includes(normalizedQuery) ||
        r.team.toLowerCase().includes(normalizedQuery) ||
        r.team_short.toLowerCase().includes(normalizedQuery)),
  );

  const visible = sortState.key
    ? sortRows(filtered, sortState.key, sortState.dir, NUMERIC_KEYS.has(sortState.key))
    : filtered;

  return (
    <div className="py-8">
      <h1 className="font-display text-display font-bold text-ink">
        Projected points, with the uncertainty shown
      </h1>
      <p className="mt-2 font-body text-body text-ink-2">
        Every player's expected points for the next gameweek from a model that beats
        FPL's own projections. The band next to each xP is the range the player's
        actual score lands in 8 gameweeks out of 10.{" "}
        <Link to="/scoreboard" className="text-accent underline">
          Track its accuracy live
        </Link>
        .
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {POSITIONS.map((p) => (
          <button
            key={p}
            type="button"
            aria-pressed={posFilter === p}
            onClick={() => setPosFilter(p)}
            className={`flex min-h-[44px] items-center rounded-full border border-line px-4 font-label text-label ${
              posFilter === p
                ? "bg-accent-bg font-bold text-accent-ink"
                : "text-ink-2 hover:bg-surface"
            }`}
          >
            {chipLabel(p)}
          </button>
        ))}
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search player or team"
          aria-label="Search player or team"
          className="min-h-[44px] flex-1 rounded border border-line bg-bg px-3 font-label text-label text-ink"
        />
      </div>

      {visible.length === 0 ? (
        <div className="flex min-h-[16rem] flex-col items-center justify-center gap-2 py-12 text-center">
          <h2 className="font-heading text-heading font-bold text-ink">No players match</h2>
          <p className="font-body text-body text-ink-2">
            Try a different position filter or search term.
          </p>
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table aria-label="xP table" className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-line bg-surface">
                {COLUMNS.map(({ key, label }) => (
                  <th
                    key={key}
                    scope="col"
                    className="px-3 py-2 font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2"
                  >
                    <button
                      type="button"
                      onClick={() => onSort(key)}
                      className="inline-flex items-center gap-1"
                    >
                      <span>{label}</span>
                      <span className="text-accent">
                        {sortState.key === key ? sortDirGlyph(sortState.dir) : ""}
                      </span>
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => (
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
                    {orDash(r.ownership != null ? fixed1(r.ownership) : undefined)}
                  </td>
                  <td className="px-3 py-2">
                    <BandCell row={r} maxHi={maxHi} />
                  </td>
                  <td className="px-3 py-2 font-label text-label tabular-nums">
                    {orDash(r.xp_capt != null ? fixed2(r.xp_capt) : undefined)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 font-body text-body text-ink-2">
        Showing the top 50 by xP — the free preview. The full table, CSV download and
        your-team transfer planning are coming with the Pro tier.
      </p>
      <p className="mt-4 font-body text-body text-ink-2">
        <strong>Reading the numbers:</strong> xP is the <em>median</em> outcome — the
        metric that ranks players best for picking a team. Football scoring is skewy,
        so medians look modest; the band shows the haul potential.{" "}
        <strong>Captain xP</strong> is the <em>mean</em> outcome, used for the armband
        because doubling rewards ceiling. Early season both lean on price and fixture
        priors and sharpen from around GW4 as real form accumulates.
      </p>

      <h2 className="mt-8 font-heading text-heading font-bold text-ink">Captain picks</h2>
      {captainsIsError ? (
        <p className="mt-2 font-body text-body text-ink-2">
          Captain picks are unavailable right now.
        </p>
      ) : captainsData ? (
        <div className="mt-4 overflow-x-auto">
          {/* R17: top 5 of captains.json, no sort, no filter. */}
          <table aria-label="Captain picks" className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-line bg-surface">
                {["Player", "Team", "£m", "Own %", "Captain xP"].map((label) => (
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
              {captainsData.slice(0, 5).map((r) => (
                <tr key={r.name} className="border-b border-line">
                  {/* Team uses the FULL club name here — unlike the main
                   * table's team_short (R17). */}
                  <td className="px-3 py-2">{r.name}</td>
                  <td className="px-3 py-2">{r.team}</td>
                  <td className="px-3 py-2 font-label text-label tabular-nums">
                    {fixed1(r.price_m)}
                  </td>
                  {/* R18/Pitfall 3: NO "–" fallback here (unlike the main
                   * table) — this reproduces vanilla's un-guarded
                   * `r.ownership?.toFixed(1)`, which stringifies to the
                   * literal text "undefined" for a null value. Deliberate
                   * parity, not a bug we're introducing. */}
                  <td className="px-3 py-2 font-label text-label tabular-nums">
                    {String(r.ownership?.toFixed(1))}
                  </td>
                  {/* R19: no optional chaining — xp_capt always present. */}
                  <td className="px-3 py-2 font-label text-label tabular-nums">
                    {fixed2(r.xp_capt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
