import { bandGeometry, bandTooltip, type BandRow } from "../lib/bandCell";

interface BandCellProps {
  row: BandRow;
  maxHi: number;
}

/* Ported from web/assets/app.js's bandCell (lines 91-102) — used by the xP
 * table and (Phase 2 Plan 04) Differentials. See RESEARCH.md Pitfall 4: the
 * track's width is a CSS calc() expression subtracting two independently-
 * clamped percentages, not a pre-subtracted JS number. Colour goes through
 * the --color-band/--color-band-pt tokens only (no hex literal). The
 * tooltip stays a native `title` attribute, matching vanilla exactly — D-09's
 * accessible click-toggle upgrade is scoped to the status flag only. */
export function BandCell({ row, maxHi }: BandCellProps) {
  const { lo, hi, leftPct, hiPct, xpPct } = bandGeometry(row, maxHi);
  const tooltip = bandTooltip(row);

  return (
    <span className="inline-flex flex-col gap-1" title={tooltip}>
      <span className="font-label text-label tabular-nums text-ink">
        {row.xp.toFixed(2)}
      </span>
      <span aria-hidden="true" className="relative block h-1.5 w-24 rounded-full bg-surface-2">
        <span
          className="absolute top-0 h-1.5 rounded-full bg-band"
          style={{ left: leftPct, width: `calc(${hiPct} - ${leftPct})` }}
        />
        <span
          className="absolute top-0 h-1.5 w-1 rounded-full bg-band-pt"
          style={{ left: `calc(${xpPct} - 4px)` }}
        />
      </span>
      <span className="font-label text-label tabular-nums text-ink-2">
        {lo.toFixed(1)}–{hi.toFixed(1)}
      </span>
    </span>
  );
}

export default BandCell;
