import { splitPitchRows } from "../../lib/formation";
import type { PitchPlayer } from "../../lib/squadJoin";
import { PlayerCard, type PlayerMark } from "./PlayerCard";
import { EmptyState } from "../EmptyState";

export interface PitchGhost {
  /** The OUTGOING player's row -- not the incoming player's position. "BENCH" covers a
   * sell target that isn't in the starting XI (04-08, WINDOWS.md id=2). */
  row: "GK" | "DEF" | "MID" | "FWD" | "BENCH";
  afterCode: number | null;
  player: PitchPlayer;
}

export interface PitchProps {
  players: PitchPlayer[];
  captainCode: number | null;
  viceCode: number | null;
  marks?: Record<number, "locked" | "excluded">;
  diffs?: Record<number, "in" | "out">;
  onMark?: (code: number, mark: PlayerMark) => void;
  ghost?: PitchGhost | null;
}

/* One shared card measure for every formation row (D-07's verified ceiling:
 * DEF max 5, MID max 5). Every card in a row shares one fixed flex basis
 * derived from `Math.max(5, cardCount)` parts — the part count never drops
 * below 5, so cards shrink and the row never reflows at any viewport width.
 * A row holding a ghost card may momentarily hold six cards — the part
 * count grows to 6 so every card in the row (including the ghost) shrinks
 * together instead of overflowing.
 *
 * Centering is continuous (flex `justify-content: center` against this fixed
 * basis), not integer-quantized. Two prior mechanisms were tried here and
 * are both defective: distributing free space across tracks that already
 * absorb all of it is a no-op, and placing a row at a single whole-number
 * start position cannot express the half-step an even-cardinality row needs
 * against an odd part count — that mechanism is exact only when row size and
 * part count share parity. Continuous centering has no parity condition, so
 * it is exact at every row size. See
 * .planning/debug/pitch-row-centering-drift.md for the algebra and measured
 * offsets (G-03-1). */
function rowParts(count: number): number {
  return Math.max(5, count);
}

function cardMeasure(parts: number): string {
  return `calc((100% - ${parts - 1} * var(--pitch-gap)) / ${parts})`;
}

/* Ghost/insert card (D-16, D-18): same kit/name/price/xP layout as a real
 * card, reduced opacity, dashed accent border — a suggested incoming
 * player, not yet part of the squad. No onMark, no captain/vice, no marks.
 * Placed via PitchGhost.row, which names the OUTGOING player's row (Bench
 * included) so the ghost always sits alongside the card it is replacing. */
function GhostCard({ player }: { player: PitchPlayer }) {
  return (
    <div
      aria-label="Suggested incoming player"
      className="rounded-lg border-2 border-dashed border-accent bg-accent-bg opacity-70"
    >
      <PlayerCard player={player} captain={false} vice={false} />
    </div>
  );
}

type RowSlot =
  | { kind: "player"; player: PitchPlayer }
  | { kind: "ghost"; player: PitchPlayer };

function buildRowSlots(
  players: PitchPlayer[],
  ghostPlayer: PitchPlayer | undefined,
  ghostAfterCode: number | null | undefined,
): RowSlot[] {
  const slots: RowSlot[] = players.map((player) => ({ kind: "player", player }));
  if (!ghostPlayer) {
    return slots;
  }
  if (ghostAfterCode == null) {
    slots.push({ kind: "ghost", player: ghostPlayer });
    return slots;
  }
  const idx = slots.findIndex((s) => s.player.player_code === ghostAfterCode);
  const insertAt = idx === -1 ? slots.length : idx + 1;
  slots.splice(insertAt, 0, { kind: "ghost", player: ghostPlayer });
  return slots;
}

interface PitchRowProps {
  players: PitchPlayer[];
  captainCode: number | null;
  viceCode: number | null;
  marks: Record<number, "locked" | "excluded">;
  diffs: Record<number, "in" | "out">;
  onMark?: (code: number, mark: PlayerMark) => void;
  ghostPlayer?: PitchPlayer;
  ghostAfterCode?: number | null;
  label: string;
  /** True for the GK/DEF/MID/FWD rows (green pitch surface exposed behind
   * the card), false/omitted for Bench (bg-surface). Forwarded only to the
   * real PlayerCard below, never to GhostCard's own internal card, which
   * always sits on its own bg-accent-bg regardless of row (07-03 contrast
   * fix, UAT G-07-1). */
  onPitch?: boolean;
}

function PitchRow({
  players,
  captainCode,
  viceCode,
  marks,
  diffs,
  onMark,
  ghostPlayer,
  ghostAfterCode,
  label,
  onPitch,
}: PitchRowProps) {
  const slots = buildRowSlots(players, ghostPlayer, ghostAfterCode);
  const parts = rowParts(slots.length);
  const basis = cardMeasure(parts);
  return (
    <div
      style={{ display: "flex", justifyContent: "center", gap: "var(--pitch-gap)" }}
      role="group"
      aria-label={label}
    >
      {slots.map((slot) => (
        <div
          key={`${slot.kind}-${slot.player.player_code}`}
          style={{ flexGrow: 0, flexShrink: 1, flexBasis: basis, minWidth: "0px" }}
        >
          {slot.kind === "ghost" ? (
            <GhostCard player={slot.player} />
          ) : (
            <PlayerCard
              player={slot.player}
              captain={slot.player.player_code === captainCode}
              vice={slot.player.player_code === viceCode}
              mark={marks[slot.player.player_code] ?? null}
              diff={diffs[slot.player.player_code] ?? "none"}
              onMark={onMark}
              onPitch={onPitch}
            />
          )}
        </div>
      ))}
    </div>
  );
}

/* FPL-style pitch surface (D-05): green gradient, white decorative markings,
 * formation rows top to bottom (GK/DEF/MID/FWD), bench in a separate
 * non-green container below. All colour comes from the pitch-1/pitch-2/
 * pitch-line/surface tokens declared in index.css's @theme block — no hex
 * literal anywhere in this file. `marks`/`diffs`/`onMark`/`ghost` are the
 * full wave-3 prop surface (03-01-PLAN.md Task 2) declared once here so
 * plans 03-03/03-04, which run in parallel, never re-edit this file. */
export function Pitch({
  players,
  captainCode,
  viceCode,
  marks = {},
  diffs = {},
  onMark,
  ghost = null,
}: PitchProps) {
  if (players.length === 0) {
    return <EmptyState />;
  }

  const { gk, def, mid, fwd, bench } = splitPitchRows(players);

  const rowGhost = (row: PitchGhost["row"]) =>
    ghost && ghost.row === row
      ? { ghostPlayer: ghost.player, ghostAfterCode: ghost.afterCode }
      : { ghostPlayer: undefined, ghostAfterCode: undefined };

  return (
    <div>
      <div
        className="relative overflow-hidden rounded-lg p-4"
        style={{
          backgroundImage:
            "linear-gradient(180deg, var(--color-pitch-1), var(--color-pitch-2))",
        }}
      >
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <line
            x1="0"
            y1="50"
            x2="100"
            y2="50"
            stroke="var(--color-pitch-line)"
            strokeWidth="0.3"
          />
          <circle
            cx="50"
            cy="50"
            r="10"
            fill="none"
            stroke="var(--color-pitch-line)"
            strokeWidth="0.3"
          />
          <rect
            x="25"
            y="0"
            width="50"
            height="14"
            fill="none"
            stroke="var(--color-pitch-line)"
            strokeWidth="0.3"
          />
          <rect
            x="25"
            y="86"
            width="50"
            height="14"
            fill="none"
            stroke="var(--color-pitch-line)"
            strokeWidth="0.3"
          />
        </svg>
        <div className="relative flex flex-col gap-4">
          <PitchRow
            players={gk}
            captainCode={captainCode}
            viceCode={viceCode}
            marks={marks}
            diffs={diffs}
            onMark={onMark}
            label="Goalkeeper"
            onPitch
            {...rowGhost("GK")}
          />
          <PitchRow
            players={def}
            captainCode={captainCode}
            viceCode={viceCode}
            marks={marks}
            diffs={diffs}
            onMark={onMark}
            label="Defenders"
            onPitch
            {...rowGhost("DEF")}
          />
          <PitchRow
            players={mid}
            captainCode={captainCode}
            viceCode={viceCode}
            marks={marks}
            diffs={diffs}
            onMark={onMark}
            label="Midfielders"
            onPitch
            {...rowGhost("MID")}
          />
          <PitchRow
            players={fwd}
            captainCode={captainCode}
            viceCode={viceCode}
            marks={marks}
            diffs={diffs}
            onMark={onMark}
            label="Forwards"
            onPitch
            {...rowGhost("FWD")}
          />
        </div>
      </div>

      <div className="mt-4 rounded-lg bg-surface p-4" data-testid="bench">
        <h3 className="mb-2 font-label text-label font-bold text-ink-2">Bench</h3>
        <PitchRow
          players={bench}
          captainCode={captainCode}
          viceCode={viceCode}
          marks={marks}
          diffs={diffs}
          onMark={onMark}
          label="Bench"
          {...rowGhost("BENCH")}
        />
      </div>
    </div>
  );
}

export default Pitch;
