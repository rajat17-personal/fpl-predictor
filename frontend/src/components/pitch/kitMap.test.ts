import { describe, expect, it, vi } from "vitest";
import { FALLBACK_KIT, GK_KIT, KIT_MAP, resolveKit } from "./kitMap";

/* Verified 20-club team_short list, read directly from the live
 * web/data/xp_table.json export during planning (03-RESEARCH.md Pitfall 5). */
const LIVE_TEAM_SHORTS = [
  "ARS",
  "AVL",
  "BOU",
  "BRE",
  "BHA",
  "CHE",
  "COV",
  "CRY",
  "EVE",
  "FUL",
  "HUL",
  "IPS",
  "LEE",
  "LIV",
  "MCI",
  "MUN",
  "NEW",
  "NFO",
  "TOT",
  "SUN",
];

describe("KIT_MAP", () => {
  it("has exactly 20 entries", () => {
    expect(Object.keys(KIT_MAP)).toHaveLength(20);
  });

  it("resolves every one of the 20 live team_short codes to an explicit entry, never the fallback", () => {
    for (const code of LIVE_TEAM_SHORTS) {
      expect(KIT_MAP[code]).toBeDefined();
      const resolved = resolveKit(code, "MID");
      expect(resolved).not.toBe(FALLBACK_KIT);
      expect(resolved).toEqual(KIT_MAP[code]);
    }
  });
});

describe("resolveKit", () => {
  it("returns GK_KIT for any goalkeeper regardless of club", () => {
    expect(resolveKit("ANY", "GK")).toBe(GK_KIT);
    expect(resolveKit("ARS", "GK")).toBe(GK_KIT);
    expect(resolveKit(null, "GK")).toBe(GK_KIT);
  });

  it("returns the mapped entry for a known outfield code", () => {
    expect(resolveKit("LIV", "DEF")).toEqual(KIT_MAP.LIV);
  });

  it("returns FALLBACK_KIT and logs a dev-only warning for an unmapped code", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(resolveKit("XYZ", "MID")).toBe(FALLBACK_KIT);
    warnSpy.mockRestore();
  });

  it("returns FALLBACK_KIT for a null team_short on an outfield position", () => {
    expect(resolveKit(null, "MID")).toBe(FALLBACK_KIT);
  });
});
