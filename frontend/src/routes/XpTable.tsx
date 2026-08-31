import { useQuery } from "@tanstack/react-query";
import { fetchJson, type MetaResponse } from "../lib/api";

/* Tracer route ("/"): proves the dev proxy reaches web/data/meta.json at runtime.
 * Plan 01-05 replaces the inline pending/error rendering below with the shared
 * <Spinner/> and <ErrorState/> components from the UI-SPEC contract. */
export default function XpTable() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["meta"],
    queryFn: () => fetchJson<MetaResponse>("/data/meta.json"),
  });

  if (isPending) {
    return <p>Loading…</p>;
  }

  if (isError) {
    return <p>{error instanceof Error ? error.message : "Failed to load meta.json"}</p>;
  }

  return (
    <p>
      Gameweek {data.gw} — {data.season}
    </p>
  );
}
