import { useQuery } from "@tanstack/react-query";
import { fetchJson, type LeadersBoards, type StandingsRow } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { usePageMeta } from "../lib/usePageMeta";

/* Ported from web/league.html's inline script (lines 53-80), verified
 * 2026-09-01. Neither table on this page is sortable — no data-key headers
 * in vanilla; port that exactly. R32: the standings table's # column is the
 * row's array position (index + 1), never a data field. R33: GD renders a
 * leading "+" only when strictly positive — zero and negative render bare.
 * R34: the five leader boards are a fixed literal list, each sliced to 8,
 * with a verbatim per-board fallback line when the sliced array is empty
 * (or the board key is entirely absent from the source). */

const EYEBROW_TH =
  "px-3 py-2 font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2";

const BOARDS: readonly [key: keyof LeadersBoards, heading: string][] = [
  ["points", "Most FPL points"],
  ["goals", "Most goals"],
  ["assists", "Most assists"],
  ["clean_sheets", "Clean sheets (GK/DEF)"],
  ["cards", "Most cards"],
];

function gdText(gd: number): string {
  return gd > 0 ? `+${gd}` : String(gd);
}

interface LeaderBoardProps {
  heading: string;
  entries: LeadersBoards[keyof LeadersBoards];
}

function LeaderBoard({ heading, entries }: LeaderBoardProps) {
  const top = entries.slice(0, 8);
  return (
    <div className="rounded border border-line bg-surface p-4">
      <h3 className="font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2">
        {heading}
      </h3>
      {top.length === 0 ? (
        <p className="mt-2 font-body text-body text-ink-2">Nothing yet this season</p>
      ) : (
        <ul className="mt-2">
          {top.map((p) => (
            <li
              key={`${p.name}-${p.team}`}
              className="flex items-center justify-between gap-2 border-b border-line py-1 last:border-b-0"
            >
              <span className="font-label text-label text-ink">
                {p.name} <span className="text-ink-2">{p.team} · {p.position}</span>
              </span>
              <span className="font-label text-label tabular-nums text-ink">{p.value}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function League() {
  usePageMeta("/league");

  const standingsQuery = useQuery({
    queryKey: ["standings"],
    // Root-relative path — a bare "data/standings.json" resolves against the
    // current client-side route and 404s (RESEARCH.md Pitfall 5).
    queryFn: () => fetchJson<StandingsRow[]>("/data/standings.json"),
    staleTime: 60_000,
  });

  const leadersQuery = useQuery({
    queryKey: ["leaders"],
    queryFn: () => fetchJson<LeadersBoards>("/data/leaders.json"),
    staleTime: 60_000,
  });

  if (standingsQuery.isPending || leadersQuery.isPending) {
    return <Spinner />;
  }

  if (standingsQuery.isError || leadersQuery.isError) {
    console.error(standingsQuery.error ?? leadersQuery.error);
    return (
      <ErrorState
        resource="the league data"
        onRetry={() => {
          standingsQuery.refetch();
          leadersQuery.refetch();
        }}
      />
    );
  }

  const standings = standingsQuery.data;
  const leaders = leadersQuery.data;

  if (!standings || standings.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="py-8">
      <h1 className="font-display text-display font-bold text-ink">
        League table &amp; season leaders
      </h1>
      <p className="mt-2 font-body text-body text-ink-2">
        Standings computed from finished fixtures, and the players racking up the season's
        goals, assists, clean sheets and cards.
      </p>

      <h2 className="mt-8 font-heading text-heading font-bold text-ink">
        Premier League table
      </h2>
      <div className="mt-4 overflow-x-auto">
        <table aria-label="Premier League table" className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-line bg-surface">
              <th scope="col" className={EYEBROW_TH}>
                #
              </th>
              <th scope="col" className={EYEBROW_TH}>
                Team
              </th>
              <th scope="col" className={EYEBROW_TH}>
                P
              </th>
              <th scope="col" className={EYEBROW_TH}>
                W
              </th>
              <th scope="col" className={EYEBROW_TH}>
                D
              </th>
              <th scope="col" className={EYEBROW_TH}>
                L
              </th>
              <th scope="col" className={EYEBROW_TH}>
                GF
              </th>
              <th scope="col" className={EYEBROW_TH}>
                GA
              </th>
              <th scope="col" className={EYEBROW_TH}>
                GD
              </th>
              <th scope="col" className={EYEBROW_TH}>
                Pts
              </th>
            </tr>
          </thead>
          <tbody>
            {standings.map((t, i) => (
              <tr key={t.short} className="border-b border-line">
                <td className="px-3 py-2 font-label text-label tabular-nums">{i + 1}</td>
                <td className="px-3 py-2">
                  <strong>{t.short}</strong> <span className="text-ink-2">{t.team}</span>
                </td>
                <td className="px-3 py-2 font-label text-label tabular-nums">{t.played}</td>
                <td className="px-3 py-2 font-label text-label tabular-nums">{t.won}</td>
                <td className="px-3 py-2 font-label text-label tabular-nums">{t.drawn}</td>
                <td className="px-3 py-2 font-label text-label tabular-nums">{t.lost}</td>
                <td className="px-3 py-2 font-label text-label tabular-nums">{t.gf}</td>
                <td className="px-3 py-2 font-label text-label tabular-nums">{t.ga}</td>
                <td className="px-3 py-2 font-label text-label tabular-nums">{gdText(t.gd)}</td>
                <td className="px-3 py-2 font-label text-label tabular-nums">
                  <strong>{t.points}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8 grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
        {BOARDS.map(([key, heading]) => (
          <LeaderBoard key={key} heading={heading} entries={leaders?.[key] ?? []} />
        ))}
      </div>
    </div>
  );
}
