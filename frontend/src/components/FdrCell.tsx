import type { TickerGw } from "../lib/api";

/* Ported from web/fixtures.html's inline fixture-cell markup (lines 69-77),
 * verified 2026-09-01. R21: an empty g.fixtures array renders a single
 * em-dash cell styled with the neutral difficulty-3 tokens. R22: each
 * fixture renders the opponent code plus an H/A venue tag, styled by its
 * OWN fdr value (not the cell's — a double gameweek can mix difficulties
 * within one cell).
 *
 * The difficulty -> token map is an explicit literal object, never a class
 * name built by interpolating the fdr value into a string — Tailwind's
 * build-time scanner cannot see a dynamically-interpolated class name and
 * would silently emit no styling for it at all. An out-of-range fdr value
 * (should never happen from real data, but the map protects against it)
 * falls through to the neutral difficulty-3 styling rather than rendering
 * unstyled.
 *
 * Accessibility (D-09's pattern, not a bare `title`): each chip carries its
 * description directly as an `aria-label`, which assistive technology
 * exposes unconditionally — no hover, focus, or click interaction needed to
 * reach it, unlike a native `title` attribute. This is deliberately NOT a
 * button: the fixtures table has no interactive cells at all (it is not
 * sortable, matching vanilla exactly) — StatusFlag's click-toggle popover
 * exists for ITS OWN discoverable trigger glyph, not for narrating a plain
 * data cell that's already fully visible as text/colour. */

const FDR_CLASSES: Record<number, string> = {
  1: "bg-fdr1-bg text-fdr1-ink",
  2: "bg-fdr2-bg text-fdr2-ink",
  3: "bg-fdr3-bg text-fdr3-ink",
  4: "bg-fdr4-bg text-fdr4-ink",
  5: "bg-fdr5-bg text-fdr5-ink",
};

function fdrClasses(fdr: number): string {
  return FDR_CLASSES[fdr] ?? FDR_CLASSES[3];
}

interface FdrCellProps {
  gw: TickerGw;
}

export function FdrCell({ gw }: FdrCellProps) {
  if (gw.fixtures.length === 0) {
    return (
      <span
        aria-label="Blank gameweek"
        className={`inline-flex min-w-[56px] items-center justify-center rounded px-2 py-1 font-label text-label ${fdrClasses(3)}`}
      >
        —
      </span>
    );
  }

  return (
    <span className="inline-flex min-w-[56px] flex-wrap items-center gap-1">
      {gw.fixtures.map((f, i) => (
        <span
          key={`${f.opp}-${i}`}
          aria-label={`${f.home ? "Home" : "Away"} vs ${f.opp}, difficulty ${f.fdr}`}
          className={`inline-flex items-center gap-0.5 rounded px-2 py-1 font-label text-label ${fdrClasses(f.fdr)}`}
        >
          {f.opp}
          <small className="text-[0.7em]">{f.home ? "H" : "A"}</small>
        </span>
      ))}
    </span>
  );
}

export default FdrCell;
