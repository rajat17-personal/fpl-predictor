import { useCallback, useState } from "react";

/** Ephemeral (D-07 — no URL params, no localStorage) sort state for one table. */
export type SortState<K extends string> = { key: K | null; dir: 1 | -1 };

/* Ported verbatim from web/assets/app.js's makeSortable comparator (lines
 * 71-75), verified via Node execution 2026-09-01 (RESEARCH.md Pitfall 1). The
 * polarity is counter-intuitive: dir=-1 (a fresh click) sorts ASCENDING with
 * nulls at the TOP; dir=+1 (a second click on the same key) sorts
 * DESCENDING with nulls at the BOTTOM. `x` is the FIRST argument's value
 * (a[key]), `y` the second (b[key]) — it is the `(y - x)` ordering, not
 * `(x - y)`, that produces the inversion from the naive reading of `dir`.
 * Do not "fix" this polarity without a PARITY-DEVIATIONS.md entry (D-04). */
export function sortRows<T, K extends keyof T>(
  rows: T[],
  key: K,
  dir: 1 | -1,
  numeric: boolean,
): T[] {
  return [...rows].sort((a, b) => {
    const x = a[key];
    const y = b[key];
    if (numeric) {
      const xn = (x as number | null | undefined) ?? -1e9;
      const yn = (y as number | null | undefined) ?? -1e9;
      return dir * (yn - xn);
    }
    const xs = String((x as string | null | undefined) ?? "");
    const ys = String((y as string | null | undefined) ?? "");
    return dir * ys.localeCompare(xs);
  });
}

/** The header direction glyph, derived from `dir` alone — never from the
 * resulting row order (web/assets/app.js:68-69). ▼ for a fresh click
 * (dir=-1, ascending); ▲ for a second click (dir=+1, descending). */
export function sortDirGlyph(dir: 1 | -1): "▼" | "▲" {
  return dir < 0 ? "▼" : "▲";
}

/** Ephemeral React sort-state hook mirroring makeSortable's click handler. A
 * fresh click on a new key sets dir=-1; clicking the already-active key
 * flips to -dir. */
export function useSortable<K extends string>(): {
  sortState: SortState<K>;
  onSort: (key: K) => void;
} {
  const [sortState, setSortState] = useState<SortState<K>>({ key: null, dir: -1 });

  const onSort = useCallback((key: K) => {
    setSortState((prev) => ({
      key,
      dir: prev.key === key ? ((-prev.dir) as 1 | -1) : -1,
    }));
  }, []);

  return { sortState, onSort };
}
