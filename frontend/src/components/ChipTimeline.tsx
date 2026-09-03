import { useEffect, useId, useRef, useState } from "react";
import type { ChipsGwStructure } from "../lib/api";

export interface ChipTimelineProps {
  structure: ChipsGwStructure[];
  currentGw: number;
}

export type MarkerKind = "plain" | "dgw" | "bgw";

/* Pure classification (03-02-PLAN.md Task 2), unit-testable independent of
 * the DOM. A gameweek whose dgw_clubs count is above zero is DGW; one whose
 * bgw_clubs count is above zero (with no DGW) is BGW; a gameweek with
 * neither is a plain, unmarked tick — the normal case in the live export
 * today (see this plan's <planner_corrections> #2). DGW takes priority in
 * the (never-observed) case both counts are non-zero, so classification
 * stays total. Counts, never club-name arrays — <planner_corrections> #1 /
 * PARITY-DEVIATIONS.md row 13. */
export function classifyMarker(row: ChipsGwStructure): MarkerKind {
  if (row.dgw_clubs > 0) {
    return "dgw";
  }
  if (row.bgw_clubs > 0) {
    return "bgw";
  }
  return "plain";
}

function Marker({ row, isCurrent }: { row: ChipsGwStructure; isCurrent: boolean }) {
  const kind = classifyMarker(row);
  const [open, setOpen] = useState(false);
  const tooltipId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    function handleDocumentClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("click", handleDocumentClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("click", handleDocumentClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const isInteractive = kind !== "plain";
  const count = kind === "dgw" ? row.dgw_clubs : row.bgw_clubs;
  const kindWord = kind === "dgw" ? "double gameweek" : kind === "bgw" ? "blank gameweek" : "gameweek";
  // Distinguishes the current GW by accessible name/attribute, not colour
  // alone (UI-SPEC "assertable attribute or accessible name").
  const label = `GW${row.gw}${isCurrent ? " — current gameweek" : ""} — ${kindWord}`;

  const dotClasses = `h-3 w-3 shrink-0 rounded-full ${
    kind === "dgw" ? "bg-accent" : kind === "bgw" ? "bg-bad" : "bg-ink-2"
  } ${isCurrent ? "h-5 w-5 ring-2 ring-accent ring-offset-1 ring-offset-surface" : ""}`;

  return (
    <div
      ref={containerRef}
      className="relative flex min-w-[44px] flex-col items-center gap-1"
      data-testid={`gw-marker-${row.gw}`}
      data-current={isCurrent ? "true" : undefined}
    >
      {isInteractive ? (
        <button
          type="button"
          aria-label={label}
          aria-expanded={open}
          aria-describedby={tooltipId}
          onClick={() => setOpen((v) => !v)}
          className="flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-1"
        >
          <span aria-hidden="true" className={dotClasses} />
          <span className="font-label text-[10px] font-bold uppercase text-ink-2">
            {kind === "dgw" ? "DGW" : "BGW"}
          </span>
        </button>
      ) : (
        <div
          aria-label={label}
          className="flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-1"
        >
          <span aria-hidden="true" className={dotClasses} />
        </div>
      )}
      <span className="font-mono text-label tabular-nums text-ink-2">GW{row.gw}</span>
      {isInteractive && open && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute top-full z-10 mt-1 max-w-[240px] whitespace-normal rounded border border-line bg-surface p-2 font-label text-label text-ink shadow"
        >
          {count} club{count === 1 ? "" : "s"} affected
        </span>
      )}
    </div>
  );
}

/* Horizontal GW timeline strip (D-21): current GW through 38, current GW
 * emphasised, DGW/BGW markers derived from structure[]'s integer club
 * counts. Scrolls horizontally within its own container so 38 markers never
 * force page-level horizontal scroll (UI-SPEC E8). */
export function ChipTimeline({ structure, currentGw }: ChipTimelineProps) {
  const rows = structure
    .filter((row) => row.gw >= currentGw && row.gw <= 38)
    .sort((a, b) => a.gw - b.gw);

  return (
    <div
      data-testid="chip-timeline"
      className="mt-4 overflow-x-auto rounded-lg border border-line bg-surface p-4"
    >
      <div className="flex min-w-max items-end gap-4">
        {rows.map((row) => (
          <Marker key={row.gw} row={row} isCurrent={row.gw === currentGw} />
        ))}
      </div>
    </div>
  );
}

export default ChipTimeline;
