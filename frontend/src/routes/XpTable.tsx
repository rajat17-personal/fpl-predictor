import { useQuery } from "@tanstack/react-query";
import { fetchJson, type XpRow } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { BandCell } from "../components/BandCell";
import { fixed1, fixed2, orDash } from "../lib/format";
import { sortDirGlyph, sortRows, useSortable } from "../lib/sortable";

/* The flagship xP table (D-06) — ported from web/index.html's inline script
 * (lines 83-131). This slice wires ONE path end to end: JSON contract →
 * typed row → sortable header → band cell → rendered table (Task 1). Filters
 * (position chips + search), verbatim page copy and per-route meta land in
 * Task 2; the accessible status flag and the Captain picks sub-table land in
 * Task 3. */

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

export default function XpTable() {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["xp_table"],
    // Root-relative path — a bare "data/xp_table.json" resolves against the
    // current client-side route and 404s (RESEARCH.md Pitfall 5).
    queryFn: () => fetchJson<XpRow[]>("/data/xp_table.json"),
    staleTime: 60_000,
  });

  const { sortState, onSort } = useSortable<SortKey>();

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

  const visible = sortState.key
    ? sortRows(top, sortState.key, sortState.dir, NUMERIC_KEYS.has(sortState.key))
    : top;

  return (
    <div className="py-8">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
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
                <td className="px-3 py-2">{r.name}</td>
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
    </div>
  );
}
