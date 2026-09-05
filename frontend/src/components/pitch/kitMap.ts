/* Hand-maintained club kit map (D-01, D-02). Keyed on the stable 3-letter
 * `team_short` code — never the full display `team` name, which has
 * punctuation/spacing variance ("Nott'm Forest") that a lookup key must not
 * depend on (03-RESEARCH.md Pitfall 5). Colors/pattern verbatim from
 * 03-UI-SPEC.md's Kit/Shirt System table (cosmetic accuracy is Assumption A1
 * there — low risk, since no crest or sponsor mark is ever used regardless).
 * No crest, no sponsor mark, no club-name text, no remote image host
 * anywhere in this module (D-01/D-02's exact constraint, T-03-02). */

export type KitPattern = "plain" | "stripes" | "hoops" | "sleeves";

export interface KitSpec {
  primary: string;
  secondary: string;
  pattern: KitPattern;
}

export const KIT_MAP: Readonly<Record<string, KitSpec>> = Object.freeze({
  ARS: { primary: "#EF0107", secondary: "#FFFFFF", pattern: "plain" },
  AVL: { primary: "#670E36", secondary: "#95BFE5", pattern: "sleeves" },
  BOU: { primary: "#DA291C", secondary: "#000000", pattern: "stripes" },
  BRE: { primary: "#E30613", secondary: "#FFFFFF", pattern: "stripes" },
  BHA: { primary: "#0057B8", secondary: "#FFFFFF", pattern: "stripes" },
  CHE: { primary: "#034694", secondary: "#FFFFFF", pattern: "plain" },
  COV: { primary: "#78D0F7", secondary: "#000000", pattern: "plain" },
  CRY: { primary: "#1B458F", secondary: "#C4122E", pattern: "stripes" },
  EVE: { primary: "#003399", secondary: "#FFFFFF", pattern: "plain" },
  FUL: { primary: "#FFFFFF", secondary: "#000000", pattern: "plain" },
  HUL: { primary: "#F18A01", secondary: "#000000", pattern: "stripes" },
  IPS: { primary: "#0044A9", secondary: "#FFFFFF", pattern: "plain" },
  LEE: { primary: "#FFFFFF", secondary: "#1D428A", pattern: "plain" },
  LIV: { primary: "#C8102E", secondary: "#00B2A9", pattern: "plain" },
  MCI: { primary: "#6CABDD", secondary: "#1C2C5B", pattern: "plain" },
  MUN: { primary: "#DA291C", secondary: "#FBE122", pattern: "plain" },
  NEW: { primary: "#241F20", secondary: "#FFFFFF", pattern: "stripes" },
  NFO: { primary: "#DD0000", secondary: "#FFFFFF", pattern: "plain" },
  TOT: { primary: "#FFFFFF", secondary: "#132257", pattern: "plain" },
  SUN: { primary: "#EB172B", secondary: "#FFFFFF", pattern: "stripes" },
});

/* GK differentiation (A3, Claude's Discretion, resolved in 03-UI-SPEC.md):
 * one fixed, club-independent kit scheme for every goalkeeper, regardless
 * of team. Standard football convention. */
export const GK_KIT: KitSpec = { primary: "#3A3A3A", secondary: "#EAB308", pattern: "plain" };

/* Unmapped-club fallback — a safety net for future data drift, not a
 * substitute for map completeness. Every club in the current 20-club list
 * must resolve to an explicit KIT_MAP entry (kitMap.test.ts asserts this). */
export const FALLBACK_KIT: KitSpec = {
  primary: "#9CA3AF",
  secondary: "#4B5563",
  pattern: "plain",
};

/** Returns GK_KIT for any goalkeeper regardless of club, the mapped entry
 * for a known team_short, or FALLBACK_KIT (plus a dev-only console warning
 * naming the unmapped code) otherwise. */
export function resolveKit(teamShort: string | null, position: string): KitSpec {
  if (position === "GK") {
    return GK_KIT;
  }
  if (teamShort && teamShort in KIT_MAP) {
    return KIT_MAP[teamShort];
  }
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.warn(`kitMap: unmapped team_short "${teamShort}", using fallback kit`);
  }
  return FALLBACK_KIT;
}
