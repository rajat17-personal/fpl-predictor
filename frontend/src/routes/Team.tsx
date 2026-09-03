import { useQuery } from "@tanstack/react-query";
import { fetchJson, type MetaResponse, type SquadResponse, type XpRow } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
import { Pitch } from "../components/pitch/Pitch";
import { deriveFormation } from "../lib/formation";
import { deriveViceCaptain, joinSquad } from "../lib/squadJoin";
import { usePageMeta } from "../lib/usePageMeta";

/* Task 1's single end-to-end path (03-01-PLAN.md): fetch squad.json +
 * xp_table.json + meta.json at runtime, join by player_code, derive the
 * formation label and vice-captain, render the model's recommended squad on
 * <Pitch>. View-only — no entry-ID input, no solve controls (that's the
 * loaded-team flow, deferred per 03-RESEARCH.md's Open Question 1 recommendation).
 * Follows Prices.tsx's isPending/isError/!data shell exactly for each query. */
export default function Team() {
  usePageMeta("/team");

  const squadQuery = useQuery({
    queryKey: ["squad"],
    queryFn: () => fetchJson<SquadResponse>("/data/squad.json"),
    staleTime: 60_000,
  });
  const xpQuery = useQuery({
    queryKey: ["xp_table"],
    queryFn: () => fetchJson<XpRow[]>("/data/xp_table.json"),
    staleTime: 60_000,
  });
  const metaQuery = useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchJson<MetaResponse>("/data/meta.json"),
    staleTime: 60_000,
  });

  const isPending = squadQuery.isPending || xpQuery.isPending || metaQuery.isPending;
  if (isPending) {
    return <Spinner />;
  }

  const isError = squadQuery.isError || xpQuery.isError || metaQuery.isError;
  if (isError) {
    console.error(squadQuery.error ?? xpQuery.error ?? metaQuery.error);
    const refetch = () => {
      void squadQuery.refetch();
      void xpQuery.refetch();
      void metaQuery.refetch();
    };
    return <ErrorState resource="the team data" onRetry={refetch} />;
  }

  if (!squadQuery.data || !xpQuery.data || !metaQuery.data) {
    return <EmptyState />;
  }

  const { squad } = squadQuery.data;
  if (squad.length === 0) {
    return <EmptyState />;
  }

  const players = joinSquad(squad, xpQuery.data);
  const formation = deriveFormation(squad);
  const captainCode = squad.find((r) => r.captain)?.player_code ?? null;
  const xpByCode = new Map(xpQuery.data.map((row) => [row.player_code, row]));
  const viceCode = deriveViceCaptain(
    squad.filter((r) => r.starting).map((r) => ({ player_code: r.player_code, captain: r.captain })),
    xpByCode,
  );

  return (
    <div className="py-8">
      <h1 className="font-heading text-heading font-bold text-ink">
        Model squad · GW{metaQuery.data.gw}
      </h1>
      <p className="mt-1 font-mono text-label tabular-nums text-ink-2">{formation}</p>

      <div className="mt-4">
        <Pitch players={players} captainCode={captainCode} viceCode={viceCode} />
      </div>
    </div>
  );
}
