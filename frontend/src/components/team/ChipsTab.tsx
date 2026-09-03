import { useQuery } from "@tanstack/react-query";
import { fetchJson, type ChipsResponse, type MetaResponse } from "../../lib/api";
import { Spinner } from "../Spinner";
import { ErrorState } from "../ErrorState";
import { EmptyState } from "../EmptyState";
import { ChipTimeline } from "../ChipTimeline";

/* Chips tab (D-21, UIX-03): the season's GW timeline plus the verbatim
 * "why this GW" callout. Follows Prices.tsx's isPending/isError/!data shell.
 * An empty structure[] also renders EmptyState rather than a zero-length
 * timeline (UI-SPEC E8). No per-chip recommendation panels — the export
 * carries no per-chip data to base them on (03-CONTEXT.md D-21). */
export function ChipsTab() {
  const metaQuery = useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchJson<MetaResponse>("/data/meta.json"),
    staleTime: 60_000,
  });
  const chipsQuery = useQuery({
    queryKey: ["chips"],
    queryFn: () => fetchJson<ChipsResponse>("/data/chips.json"),
    staleTime: 60_000,
  });

  const isPending = metaQuery.isPending || chipsQuery.isPending;
  if (isPending) {
    return <Spinner />;
  }

  const isError = metaQuery.isError || chipsQuery.isError;
  if (isError) {
    console.error(metaQuery.error ?? chipsQuery.error);
    const refetch = () => {
      void metaQuery.refetch();
      void chipsQuery.refetch();
    };
    return <ErrorState resource="the chip timing data" onRetry={refetch} />;
  }

  if (!metaQuery.data || !chipsQuery.data) {
    return <EmptyState />;
  }

  const chips = chipsQuery.data;
  if (chips.structure.length === 0) {
    return <EmptyState />;
  }

  const gw = metaQuery.data.gw;

  return (
    <div>
      <h1 className="font-heading text-heading font-bold text-ink">Chip timing</h1>
      <p className="mt-2 font-body text-body text-ink-2">
        When to play your chips this season, and why.
      </p>

      <div className="mt-4 rounded-lg border border-line bg-surface p-4">
        <h2 className="font-heading text-heading font-bold text-ink">Why GW{gw}</h2>
        <p className="mt-2 whitespace-pre-wrap font-body text-body text-ink-2">{chips.note}</p>
      </div>

      <ChipTimeline structure={chips.structure} currentGw={gw} />
    </div>
  );
}

export default ChipsTab;
