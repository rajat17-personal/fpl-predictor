/* Deadline/freshness formatting (UI-06, D-18..D-22). Pure functions that take
 * an explicit `now` argument so tests are deterministic. Ports vanilla's
 * fmtDeadline (web/assets/app.js) for the {abs} format verbatim; {rel} and
 * {freshness} are new, graduated-precision formats per the UI-SPEC. */

const MINUTE_MS = 60_000;
const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

/** Vanilla's exact toLocaleString options object, or the deadline TBC fallback. */
export function fmtAbs(
  iso: string | null | undefined,
  fallback = "deadline TBC",
): string {
  if (!iso) return fallback;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export type RelResult = { passed: true } | { passed: false; text: string };

/**
 * Graduated-precision countdown (D-19): days+hours at or above a day,
 * hours+minutes below a day and at or above an hour, minutes+seconds below
 * an hour. Zero or negative remaining time signals the passed state rather
 * than a negative countdown (D-21 — the caller renders its own copy for it).
 */
export function fmtRel(deadlineIso: string, now: number): RelResult {
  const deadline = new Date(deadlineIso).getTime();
  const diff = deadline - now;

  if (diff <= 0) return { passed: true };

  if (diff >= DAY_MS) {
    const days = Math.floor(diff / DAY_MS);
    const hours = Math.floor((diff % DAY_MS) / HOUR_MS);
    return { passed: false, text: `in ${days}d ${hours}h` };
  }

  if (diff >= HOUR_MS) {
    const hours = Math.floor(diff / HOUR_MS);
    const minutes = Math.floor((diff % HOUR_MS) / MINUTE_MS);
    return { passed: false, text: `in ${hours}h ${minutes}m` };
  }

  const minutes = Math.floor(diff / MINUTE_MS);
  const seconds = Math.floor((diff % MINUTE_MS) / 1000);
  return { passed: false, text: `in ${minutes}m ${seconds}s` };
}

/**
 * Elapsed-time freshness line (D-20) — four buckets, each boundary landing
 * in the coarser bucket (59s stays "just now", 60s becomes "1m ago", etc.).
 */
export function fmtFreshness(generatedIso: string, now: number): string {
  const generated = new Date(generatedIso).getTime();
  const elapsed = now - generated;

  if (elapsed < MINUTE_MS) return "generated just now";
  if (elapsed < HOUR_MS) return `generated ${Math.floor(elapsed / MINUTE_MS)}m ago`;
  if (elapsed < DAY_MS) return `generated ${Math.floor(elapsed / HOUR_MS)}h ago`;
  return `generated ${Math.floor(elapsed / DAY_MS)}d ago`;
}
