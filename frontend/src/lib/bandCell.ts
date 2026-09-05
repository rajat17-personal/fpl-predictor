/* Ported from web/assets/app.js's bandCell (lines 91-102), verified
 * 2026-09-01. Two callers pass different `maxHi` computations (xP table:
 * `Math.max(...)`, no floor per R11; Differentials: `Math.max(1, ...)`, a
 * floor of 1) — this module takes `maxHi` as a parameter and never computes
 * it itself, so the two call sites cannot accidentally be unified. */

export interface BandRow {
  xp: number;
  p10?: number | null;
  p90?: number | null;
}

export interface BandGeometry {
  lo: number;
  hi: number;
  /** Percentage string (e.g. "42%") for the track's left edge — pct(lo). */
  leftPct: string;
  /** Percentage string for the track's right edge — pct(hi). Combine with
   * leftPct as a CSS calc() expression, never a pre-subtracted number
   * (RESEARCH.md Pitfall 4). */
  hiPct: string;
  /** Percentage string for the point marker — pct(xp). */
  xpPct: string;
}

function pct(v: number, maxHi: number): string {
  return `${Math.min(100, (100 * v) / maxHi)}%`;
}

/** R7-R8: p10/p90 bounds (falling back to xp) and their percentage-of-maxHi geometry. */
export function bandGeometry(row: BandRow, maxHi: number): BandGeometry {
  const lo = row.p10 ?? row.xp;
  const hi = row.p90 ?? row.xp;
  return {
    lo,
    hi,
    leftPct: pct(lo, maxHi),
    hiPct: pct(hi, maxHi),
    xpPct: pct(row.xp, maxHi),
  };
}

/** R9: verbatim tooltip copy (D-03). */
export function bandTooltip(row: BandRow): string {
  const lo = row.p10 ?? row.xp;
  const hi = row.p90 ?? row.xp;
  return `xP ${row.xp.toFixed(2)} — actual score lands between ${lo.toFixed(1)} and ${hi.toFixed(1)} in 8 gameweeks out of 10`;
}
