import { useEffect, useState } from "react";
import type { MetaResponse } from "../lib/api";
import { fmtAbs, fmtFreshness, fmtRel } from "../lib/deadline";

/* Gameweek meta banner chip (UI-06, D-18..D-22). PageShell owns the single
 * `meta.json` query (TanStack Query) and passes its status/data down here —
 * this component never fetches. Pill styling family shared with
 * ThemeToggle: surface background, line border, rounded-full, Numeric
 * (IBM Plex Mono) Label-size text in ink-2. */
interface GwBannerProps {
  status: "pending" | "error" | "success";
  data: MetaResponse | undefined;
}

const PILL_CLASS =
  "rounded-full border border-line bg-surface px-3 py-1.5 font-mono text-label leading-tight text-ink-2";

export default function GwBanner({ status, data }: GwBannerProps) {
  const [now, setNow] = useState(() => Date.now());

  const deadlineMs = data ? new Date(data.deadline_utc).getTime() : null;
  const remaining = deadlineMs !== null ? deadlineMs - now : null;
  // D-19: 60s cadence outside the final hour, 1s inside it. The effect below
  // re-creates the interval whenever this crosses the boundary — a single
  // conditional on the existing interval, not a structural change.
  const intervalMs = remaining !== null && remaining < 3_600_000 ? 1000 : 60_000;

  useEffect(() => {
    if (deadlineMs === null) return;
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [deadlineMs, intervalMs]);

  if (status === "pending") {
    return <div className={PILL_CLASS}>loading…</div>;
  }

  // D-22: a failed fetch shows the quiet fallback alone — no ErrorState/Retry,
  // no freshness line, and every page's own content still renders underneath.
  if (status === "error" || !data) {
    return <div className={PILL_CLASS}>deadline TBC</div>;
  }

  const rel = fmtRel(data.deadline_utc, now);
  const freshness = fmtFreshness(data.generated_utc, now);
  // D-21: the passed state replaces the whole countdown segment, not
  // vanilla's "· passed" suffix.
  const line1 = rel.passed
    ? `GW${data.gw} deadline passed`
    : `GW${data.gw} deadline: ${fmtAbs(data.deadline_utc)} · ${rel.text}`;

  return (
    <div className={PILL_CLASS}>
      <div>{line1}</div>
      <div>{freshness}</div>
    </div>
  );
}
