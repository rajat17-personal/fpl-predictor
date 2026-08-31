import { useQuery } from "@tanstack/react-query";
import { fetchJson, type MetaResponse } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";

/* Tracer route ("/"): proves the dev proxy reaches web/data/meta.json at
 * runtime. Routes its pending/error/empty states through the shared shell
 * components from the UI-SPEC contract rather than inline text. */
export default function XpTable() {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchJson<MetaResponse>("/data/meta.json"),
  });

  if (isPending) {
    return <Spinner />;
  }

  if (isError) {
    console.error(error);
    return <ErrorState resource="the gameweek data" onRetry={() => refetch()} />;
  }

  if (!data) {
    return <EmptyState />;
  }

  return (
    <p>
      Gameweek {data.gw} — {data.season}
    </p>
  );
}
