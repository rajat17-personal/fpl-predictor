import { useEffect, useId, useRef, useState } from "react";
import { Lock, X } from "lucide-react";
import { Kit } from "./Kit";
import { resolveKit } from "./kitMap";
import { bandGeometry, bandTooltip, type BandGeometry } from "../../lib/bandCell";
import type { PitchPlayer } from "../../lib/squadJoin";

export type PlayerMark = "locked" | "excluded" | null;
export type PlayerDiff = "none" | "out" | "in";

export interface PlayerCardProps {
  player: PitchPlayer;
  captain: boolean;
  vice: boolean;
  mark?: PlayerMark;
  diff?: PlayerDiff;
  onMark?: (code: number, mark: PlayerMark) => void;
  /** True only for a real (non-ghost) card rendered directly on the green
   * pitch surface (GK/DEF/MID/FWD rows) -- never for Bench (bg-surface) or
   * a GhostCard (bg-accent-bg). Swaps the stat-line classes to the
   * pitch-stat tokens (07-03 contrast fix, UAT G-07-1): --color-ink-2 reads
   * as low-contrast grey against the green pitch-1/pitch-2 gradient in both
   * themes, so those two backgrounds get a dark semi-opaque backdrop plus
   * light text instead. */
  onPitch?: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  i: "unavailable",
  s: "unavailable",
  u: "unavailable",
  n: "unavailable",
  d: "doubtful",
};

function fmtOwnership(ownership: number | null): string {
  return ownership == null ? "–" : `${ownership.toFixed(1)}%`;
}

/* Below-400px tap-reveal (03-UI-SPEC.md Pitch Design → Mobile shrink
 * behavior) — the ONE documented exception to D-06's always-visible range
 * line rule, gated purely by viewport width via CSS (min-[400px]:hidden),
 * never JS media-query state. Reuses statusFlag.tsx's open/close shape at
 * a smaller scale (no outside-click/Escape — a single self-contained
 * trigger, not a persistent menu). */
function RangeReveal({
  geom,
  tooltip,
  onPitch,
}: {
  geom: BandGeometry;
  tooltip: string;
  onPitch?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();

  return (
    <span className="relative inline-block min-[400px]:hidden">
      <button
        type="button"
        aria-label="Show xP range"
        aria-expanded={open}
        aria-describedby={tooltipId}
        onClick={() => setOpen((v) => !v)}
        className={`min-h-[44px] min-w-[44px] rounded font-mono text-label tabular-nums underline decoration-dotted ${
          onPitch ? "bg-pitch-stat-bg px-1 text-pitch-stat-ink" : "text-ink-2"
        }`}
      >
        ±
      </button>
      {open && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute z-10 max-w-[240px] whitespace-normal rounded border border-line bg-surface p-2 font-label text-label text-ink shadow"
        >
          {geom.lo.toFixed(1)}–{geom.hi.toFixed(1)} — {tooltip}
        </span>
      )}
    </span>
  );
}

/* Full player card (03-01-PLAN.md Task 2): kit + C/VC badges + name +
 * price/xP + always-visible range line + lock/exclude/diff badges + the
 * tap-a-card action popover (D-13). `onMark` undefined keeps the card
 * non-interactive and renders no popover trigger — the default view-only
 * Squad tab (Task 1) stays view-only; the loaded-team flow (plan 03-04)
 * turns interaction on by passing the callback. */
export function PlayerCard({
  player,
  captain,
  vice,
  mark = null,
  diff = "none",
  onMark,
  onPitch = false,
}: PlayerCardProps) {
  const kit = resolveKit(player.team_short, player.position);
  const geom = bandGeometry(player, player.p90 ?? player.xp);
  const tooltip = bandTooltip(player);

  const [open, setOpen] = useState(false);
  const menuId = useId();
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

  const statusLabel =
    player.status && player.status !== "a" ? (STATUS_LABELS[player.status] ?? player.status) : null;
  const newsBody = player.news || statusLabel;

  function chooseMark(next: PlayerMark) {
    onMark?.(player.player_code, next);
    setOpen(false);
  }

  const visual = (
    <>
      <Kit primary={kit.primary} secondary={kit.secondary} pattern={kit.pattern} />
      {captain && (
        <span
          aria-label="Captain"
          className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-accent font-label text-[10px] font-bold text-bg"
        >
          C
        </span>
      )}
      {!captain && vice && (
        <span
          aria-label="Vice-captain"
          className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full border border-accent bg-transparent font-label text-[10px] font-bold text-accent"
        >
          V
        </span>
      )}
      {mark === "locked" && (
        <Lock
          aria-label="Locked — always included in solve"
          className="absolute -bottom-1 -left-1 h-4 w-4 rounded-full bg-accent-bg p-0.5 text-accent-ink"
        />
      )}
      {mark === "excluded" && (
        <X
          aria-label="Excluded from solve"
          className="absolute -bottom-1 -left-1 h-4 w-4 rounded-full bg-bad/20 p-0.5 text-bad"
        />
      )}
      {diff === "in" && (
        <span
          aria-label="New signing this transfer"
          className="absolute -top-1 -left-1 rounded bg-accent px-1 font-label text-[9px] font-bold text-bg"
        >
          IN
        </span>
      )}
    </>
  );

  /* Outgoing-player marking (07-03 UAT G-07-2): the same dashed-outline idiom
   * GhostCard uses for the incoming player, mirrored in the "bad" (red)
   * token instead of "accent" (green) so a suggested swap reads as one
   * out/in pair at a glance. Applied on the same outer element GhostCard's
   * own wrapper occupies, replacing the previous bare opacity-50 (which
   * carried no visible marking of its own beyond the sr-only text). */
  const outClass =
    diff === "out" ? "rounded-lg border-2 border-dashed border-bad bg-bad/10 p-1 opacity-70" : "";

  return (
    <div
      ref={containerRef}
      className={`relative flex w-full flex-col items-center gap-1 text-center ${outClass}`}
    >
      {onMark ? (
        <button
          type="button"
          aria-label={`${player.name} actions`}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? menuId : undefined}
          onClick={() => setOpen((v) => !v)}
          className="relative flex min-h-[44px] min-w-[44px] flex-col items-center justify-center gap-1"
        >
          {visual}
        </button>
      ) : (
        <div className="relative flex flex-col items-center gap-1">{visual}</div>
      )}

      {diff === "out" && <span className="sr-only">Suggested transfer out</span>}

      <span className="w-full truncate font-label text-label text-ink">{player.name}</span>
      <span
        className={`font-mono text-label tabular-nums ${
          onPitch ? "rounded bg-pitch-stat-bg px-1 text-pitch-stat-ink" : "text-ink-2"
        }`}
      >
        £{player.price_m.toFixed(1)} · {player.xp.toFixed(1)}
      </span>

      <span
        className={`hidden rounded font-mono text-label tabular-nums min-[400px]:inline ${
          onPitch ? "bg-pitch-stat-bg px-1 text-pitch-stat-ink" : "text-ink-2"
        }`}
        title={tooltip}
      >
        {geom.lo.toFixed(1)}–{geom.hi.toFixed(1)}
      </span>
      <RangeReveal geom={geom} tooltip={tooltip} onPitch={onPitch} />

      {onMark && open && (
        <div
          id={menuId}
          role="menu"
          aria-label={`${player.name} actions`}
          className="absolute top-full z-10 mt-1 max-w-[240px] whitespace-normal rounded border border-line bg-surface p-2 text-left shadow"
        >
          <div className="mb-2 border-b border-line pb-2">
            <p className="font-label text-label font-bold text-ink">{player.name}</p>
            <p className="font-label text-label text-ink-2">{player.team}</p>
            {statusLabel && <p className="font-label text-label text-ink-2">{newsBody}</p>}
            <p className="font-label text-label text-ink-2">
              Ownership {fmtOwnership(player.ownership)}
            </p>
          </div>
          <button
            type="button"
            role="menuitem"
            className="block min-h-[44px] w-full text-left font-label text-label text-ink"
            onClick={() => chooseMark("locked")}
          >
            Lock in squad
          </button>
          <button
            type="button"
            role="menuitem"
            className="block min-h-[44px] w-full text-left font-label text-label text-ink"
            onClick={() => chooseMark("excluded")}
          >
            Exclude from squad
          </button>
          {mark && (
            <button
              type="button"
              role="menuitem"
              className="block min-h-[44px] w-full text-left font-label text-label text-ink"
              onClick={() => chooseMark(null)}
            >
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default PlayerCard;
