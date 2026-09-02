import { useQuery } from "@tanstack/react-query";
import { fetchJson, type FixtureTickerTeam } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { FdrCell } from "../components/FdrCell";
import { fixed2, orDash } from "../lib/format";
import { usePageMeta } from "../lib/usePageMeta";

/* Ported from web/fixtures.html's inline script (lines 55-78), verified
 * 2026-09-01. R20: the gameweek column count is derived from the data
 * (`ticker[0].gws.length`) — never hard-coded to six; this route's own test
 * fixture deliberately carries four gameweeks so a hard-coded six would
 * fail visibly. This table has no `data-key` headers in vanilla and is not
 * sortable; port that exactly (differs from the xP table). */

const EYEBROW_TH =
  "px-3 py-2 font-label text-label font-bold uppercase tracking-[0.08em] text-ink-2";

export default function Fixtures() {
  usePageMeta("/fixtures");

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["fixtures"],
    // Root-relative path — a bare "data/fixtures.json" resolves against the
    // current client-side route and 404s (RESEARCH.md Pitfall 5).
    queryFn: () => fetchJson<FixtureTickerTeam[]>("/data/fixtures.json"),
    staleTime: 60_000,
  });

  if (isPending) {
    return <Spinner />;
  }

  if (isError) {
    console.error(error);
    return <ErrorState resource="the fixture data" onRetry={() => refetch()} />;
  }

  if (!data || data.length === 0) {
    return <EmptyState />;
  }

  // R20: dynamic column count derived from the data, never hard-coded.
  const gwNumbers = data[0].gws.map((g) => g.gw);

  return (
    <div className="py-8">
      <h1 className="font-display text-display font-bold text-ink">Fixture ticker</h1>
      <p className="mt-2 font-body text-body text-ink-2">
        The next six gameweeks for every club, sorted by ease of run. Each cell shows the
        opponent and venue (H/A); color is FPL fixture difficulty from easy (blue) through
        neutral to hard (red). xG and xGC forecast the club's expected goals scored /
        conceded in its <strong>next fixture</strong> — season-to-date attack and defence
        rates adjusted for the opponent and venue (early season the samples are small; it
        sharpens weekly).
      </p>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-line bg-surface">
              <th scope="col" className={EYEBROW_TH}>
                Team
              </th>
              <th scope="col" className={EYEBROW_TH}>
                xG next
              </th>
              <th scope="col" className={EYEBROW_TH}>
                xGC next
              </th>
              {gwNumbers.map((gw) => (
                <th key={gw} scope="col" className={`min-w-[56px] ${EYEBROW_TH}`}>
                  GW{gw}
                </th>
              ))}
              <th scope="col" className={EYEBROW_TH}>
                Ease
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((t) => (
              <tr key={t.short} className="border-b border-line">
                <td className="px-3 py-2">
                  <strong>{t.short}</strong> <span className="text-ink-2">{t.team}</span>
                </td>
                <td className="px-3 py-2 font-label text-label tabular-nums">
                  {orDash(t.xg_next != null ? fixed2(t.xg_next) : undefined)}
                </td>
                <td className="px-3 py-2 font-label text-label tabular-nums">
                  {orDash(t.xgc_next != null ? fixed2(t.xgc_next) : undefined)}
                </td>
                {t.gws.map((g) => (
                  // Vanilla's fixture-specific tight cell padding
                  // (web/assets/style.css:154, `.cellpad`) — 4px horizontal,
                  // 3px vertical — absorbs the two-line stacked chip so the
                  // row grows by only a few px instead of the ~14px/row the
                  // generic 12px/8px table padding would cost. Scoped to the
                  // gameweek cells only; UAT gap G-02-2.
                  <td key={g.gw} className="px-1 py-[3px]">
                    <FdrCell gw={g} />
                  </td>
                ))}
                <td className="px-3 py-2 font-label text-label tabular-nums">
                  {fixed2(t.ease)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        aria-hidden="true"
        className="mt-4 flex flex-wrap items-center gap-2 font-label text-label text-ink-2"
      >
        <span>Easy</span>
        <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-fdr1-bg text-fdr1-ink">
          1
        </span>
        <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-fdr2-bg text-fdr2-ink">
          2
        </span>
        <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-fdr3-bg text-fdr3-ink">
          3
        </span>
        <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-fdr4-bg text-fdr4-ink">
          4
        </span>
        <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-fdr5-bg text-fdr5-ink">
          5
        </span>
        <span>Hard</span>
        <span className="ml-3">— = blank gameweek</span>
      </div>
    </div>
  );
}
