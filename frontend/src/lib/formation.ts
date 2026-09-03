import type { SquadRow } from "./api";

/* Formation derivation mirrors optimize/squad_ilp.py:126's own formula
 * verbatim:
 *   formation = "-".join(str((xi.position == p).sum()) for p in ["DEF", "MID", "FWD"])
 * GK is always exactly 1 (squad_ilp.py:92's own constraint) and is never
 * part of the string — it is implicit. Pure function, no module state, no
 * fetch — same shape as lib/bandCell.ts. */

interface FormationRow {
  position: string;
  starting: boolean;
}

/** Returns the DEF-MID-FWD starter counts joined by hyphens (e.g. "3-5-2"). */
export function deriveFormation(rows: FormationRow[]): string {
  const starters = rows.filter((r) => r.starting);
  const count = (position: string) =>
    starters.filter((r) => r.position === position).length;
  return `${count("DEF")}-${count("MID")}-${count("FWD")}`;
}

export interface PitchRows {
  gk: SquadRow[];
  def: SquadRow[];
  mid: SquadRow[];
  fwd: SquadRow[];
  bench: SquadRow[];
}

/* Bucket order (GK/DEF/MID/FWD) mirrors web/team.html:69's squadCards()
 * grouping. Bucketing is a stable filter, never a sort — source-array order
 * is preserved within each bucket (UIX-01 edge probe). */
export function splitPitchRows(rows: SquadRow[]): PitchRows {
  const starters = rows.filter((r) => r.starting);
  const bench = rows.filter((r) => !r.starting);
  const byPos = (position: string) => starters.filter((r) => r.position === position);
  return {
    gk: byPos("GK"),
    def: byPos("DEF"),
    mid: byPos("MID"),
    fwd: byPos("FWD"),
    bench,
  };
}
