import { Kit } from "./Kit";
import { resolveKit } from "./kitMap";
import type { PitchPlayer } from "../../lib/squadJoin";

export interface PlayerCardProps {
  player: PitchPlayer;
  captain: boolean;
  vice: boolean;
}

/* Tracer shape only (03-01-PLAN.md Task 1): kit + name + one price/xP line.
 * Badges, the always-visible range line, mark/diff badges and the action
 * popover are Task 2's full prop surface — deliberately not added here so
 * the end-to-end pitch proves out before the card's full richness lands. */
export function PlayerCard({ player, captain, vice }: PlayerCardProps) {
  const kit = resolveKit(player.team_short, player.position);

  return (
    <div className="flex w-full flex-col items-center gap-1 text-center">
      <div className="relative">
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
      </div>
      <span className="w-full truncate font-label text-label text-ink">{player.name}</span>
      <span className="font-mono text-label tabular-nums text-ink-2">
        £{player.price_m.toFixed(1)} · {player.xp.toFixed(1)}
      </span>
    </div>
  );
}

export default PlayerCard;
