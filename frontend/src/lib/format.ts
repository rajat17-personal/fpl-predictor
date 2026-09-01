/* Primitive number/format helpers ported from the vanilla site's per-call-site
 * `.toFixed()`/`.toLocaleString()` idioms (web/index.html, web/prices.html,
 * web/fixtures.html, ...).
 *
 * These are PRIMITIVES ONLY — deliberately not a per-field formatter (e.g. a
 * single `formatOwnership()`). RESEARCH.md Pitfall 3 documents that the
 * vanilla pages deliberately disagree about which fields get a "–" fallback
 * for the identically-named `ownership` field (xP table has one, the
 * Captains sub-table and Differentials do not). A unified per-field
 * formatter would erase that distinction. Each call site composes these
 * primitives the way its own vanilla source did.
 */

const EN_DASH = "–";

/** `.toFixed(1)` — one decimal place (£m, ownership %, ease, ...). */
export function fixed1(v: number): string {
  return v.toFixed(1);
}

/** `.toFixed(2)` — two decimal places (xP, Captain xP, xG, ...). */
export function fixed2(v: number): string {
  return v.toFixed(2);
}

/** En-dash fallback for an already-formatted value that may be null/undefined
 * (mirrors vanilla's `?? "–"` chains). Returns `s` unchanged when it is a
 * real string — including an empty string, which is not a null/undefined
 * absence. */
export function orDash(s: string | null | undefined): string {
  return s === null || s === undefined ? EN_DASH : s;
}

/** `.toLocaleString()` — thousands separators (net transfers, ...). */
export function localeInt(v: number): string {
  return v.toLocaleString();
}
