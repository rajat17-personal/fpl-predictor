/* Verbatim port of web/team.html:140-150's pairMoves() — only syntax
 * changes (var -> const/let, added TypeScript types), no logic changes
 * (03-CONTEXT.md D-19). Buckets both arrays by position, then pairs each
 * sell with the buy at the same index in that position's bucket — ties
 * resolve by array order, exactly as the original reduce()/forEach() does.
 * The one deliberate difference: returns structured objects rather than
 * vanilla's pre-built HTML string, so every consumer renders it as JSX
 * instead of injecting markup (03-02-PLAN.md Task 3, T-03-07). Both
 * wave-3 plans (03-03/03-04) import this module. */

export interface MovePair {
  sellName: string;
  buyName: string;
  position: string;
}

export interface NamedPositionRow {
  name: string;
  position: string;
}

export function pairMoves(sells: NamedPositionRow[], buys: NamedPositionRow[]): MovePair[] {
  const byPos = (rows: NamedPositionRow[]): Record<string, NamedPositionRow[]> =>
    rows.reduce<Record<string, NamedPositionRow[]>>((m, r) => {
      (m[r.position] ??= []).push(r);
      return m;
    }, {});

  const s = byPos(sells);
  const b = byPos(buys);
  const pairs: MovePair[] = [];
  for (const pos of Object.keys(s)) {
    s[pos].forEach((sell, i) => {
      pairs.push({ sellName: sell.name, buyName: b[pos]?.[i]?.name ?? "?", position: pos });
    });
  }
  return pairs;
}

export default pairMoves;
