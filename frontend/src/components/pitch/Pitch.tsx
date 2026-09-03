import { splitPitchRows } from "../../lib/formation";
import type { PitchPlayer } from "../../lib/squadJoin";
import { PlayerCard } from "./PlayerCard";
import { EmptyState } from "../EmptyState";

export interface PitchProps {
  players: PitchPlayer[];
  captainCode: number | null;
  viceCode: number | null;
}

/* One shared 5-column grid definition for every formation row (D-07's
 * verified ceiling: DEF max 5, MID max 5). The column count never changes
 * with viewport width — cards shrink, the layout never reflows. A row with
 * fewer than 5 cards centres them within the row (GK's single card sits at
 * column 3, matching 03-UI-SPEC.md's Pitch Design section) rather than
 * changing grid-template-columns. */
function centeredStartColumn(count: number): number {
  return Math.max(1, Math.floor((5 - count) / 2) + 1);
}

interface PitchRowProps {
  players: PitchPlayer[];
  captainCode: number | null;
  viceCode: number | null;
  label: string;
}

function PitchRow({ players, captainCode, viceCode, label }: PitchRowProps) {
  const start = centeredStartColumn(players.length);
  return (
    <div className="grid grid-cols-5 gap-2" role="group" aria-label={label}>
      {players.map((player, i) => (
        <div key={player.player_code} style={{ gridColumn: start + i }}>
          <PlayerCard
            player={player}
            captain={player.player_code === captainCode}
            vice={player.player_code === viceCode}
          />
        </div>
      ))}
    </div>
  );
}

/* FPL-style pitch surface (D-05): green gradient, white decorative markings,
 * formation rows top to bottom (GK/DEF/MID/FWD), bench in a separate
 * non-green container below. All colour comes from the pitch-1/pitch-2/
 * pitch-line/surface tokens declared in index.css's @theme block — no hex
 * literal anywhere in this file. */
export function Pitch({ players, captainCode, viceCode }: PitchProps) {
  if (players.length === 0) {
    return <EmptyState />;
  }

  const { gk, def, mid, fwd, bench } = splitPitchRows(players);

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
          <PitchRow players={gk} captainCode={captainCode} viceCode={viceCode} label="Goalkeeper" />
          <PitchRow players={def} captainCode={captainCode} viceCode={viceCode} label="Defenders" />
          <PitchRow players={mid} captainCode={captainCode} viceCode={viceCode} label="Midfielders" />
          <PitchRow players={fwd} captainCode={captainCode} viceCode={viceCode} label="Forwards" />
        </div>
      </div>

      <div className="mt-4 rounded-lg bg-surface p-4" data-testid="bench">
        <h3 className="mb-2 font-label text-label font-bold text-ink-2">Bench</h3>
        <PitchRow players={bench} captainCode={captainCode} viceCode={viceCode} label="Bench" />
      </div>
    </div>
  );
}

export default Pitch;
