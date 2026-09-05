import { useState } from "react";

/** The three knobs D-14 exposes — mode and budget deliberately absent, the
 * server's own defaults cover the rest. */
export interface SolveControlValues {
  freeTransfers: number;
  maxTransfers: number | null;
  horizon: number;
}

export interface SolveControlsProps {
  /** The API's own free-transfers estimate, or null when unavailable — the
   * input is prefilled from this and is never rendered blank (falls back to
   * 1, `/api/solve`'s own server-side default). */
  freeTransfersEstimate: number | null;
  /** True while a solve is in flight — disables the button and renders the
   * inline wait status (D-15). The pitch itself stays mounted elsewhere;
   * this component never replaces it with a spinner. */
  pending: boolean;
  onSolve: (values: SolveControlValues) => void;
}

const HORIZON_OPTIONS = [1, 2, 3, 4, 6];

/* Solve controls (D-14, D-15, Pitfall 3): a compact row of three bounded
 * inputs plus the "Solve transfers" CTA. Every bound mirrors SolveRequest's
 * own server-side Field(ge=…, le=…) constraint (api/main.py:235-243) as the
 * input's own min/max, so an out-of-range value can never be submitted from
 * the UI. This component knows nothing about locks/excludes/player_code —
 * it only collects the three knobs and hands them to onSolve; the caller
 * (SquadTab) owns marks and builds the actual /api/solve request body. */
export function SolveControls({ freeTransfersEstimate, pending, onSolve }: SolveControlsProps) {
  const [freeTransfers, setFreeTransfers] = useState(String(freeTransfersEstimate ?? 1));
  const [maxTransfers, setMaxTransfers] = useState("");
  const [horizon, setHorizon] = useState("1");

  function submit() {
    const ftNum = Number(freeTransfers);
    const ftToSend = Number.isFinite(ftNum) ? ftNum : 1;

    const trimmedMax = maxTransfers.trim();
    let maxToSend: number | null = null;
    if (trimmedMax !== "") {
      const maxNum = Number(trimmedMax);
      maxToSend = Number.isFinite(maxNum) ? maxNum : null;
    }

    const horizonNum = Number(horizon || 1);

    onSolve({ freeTransfers: ftToSend, maxTransfers: maxToSend, horizon: horizonNum });
  }

  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 font-label text-label text-ink-2">
          Free transfers
          <input
            type="number"
            min="0"
            max="5"
            aria-label="Free transfers"
            value={freeTransfers}
            onChange={(e) => setFreeTransfers(e.target.value)}
            className="min-h-[44px] w-[80px] rounded border border-line bg-surface px-3 py-2 font-mono text-label tabular-nums text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 font-label text-label text-ink-2">
          Max transfers
          <input
            type="number"
            min="0"
            max="15"
            aria-label="Max transfers"
            placeholder="No cap"
            value={maxTransfers}
            onChange={(e) => setMaxTransfers(e.target.value)}
            className="min-h-[44px] w-[80px] rounded border border-line bg-surface px-3 py-2 font-mono text-label tabular-nums text-ink"
          />
        </label>
        <label className="flex flex-col gap-1 font-label text-label text-ink-2">
          Plan horizon
          <select
            aria-label="Plan horizon"
            value={horizon}
            onChange={(e) => setHorizon(e.target.value)}
            className="min-h-[44px] rounded border border-line bg-surface px-3 py-2 font-label text-label text-ink"
          >
            {HORIZON_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n} gameweek{n > 1 ? "s" : ""}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={submit}
          disabled={pending}
          className="min-h-[44px] rounded bg-accent px-4 py-2 font-label text-label font-bold text-bg disabled:opacity-60"
        >
          Solve transfers
        </button>
      </div>

      {pending && (
        <p role="status" className="mt-2 font-body text-body text-ink-2">
          Solving your transfers…
        </p>
      )}
    </div>
  );
}

export default SolveControls;
