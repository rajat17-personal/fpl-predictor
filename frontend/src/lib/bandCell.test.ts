import { describe, expect, it } from "vitest";
import { bandGeometry, bandTooltip } from "./bandCell";

describe("bandGeometry", () => {
  it("computes lo/hi and percentage-of-maxHi geometry", () => {
    const g = bandGeometry({ xp: 5, p10: 2, p90: 8 }, 10);
    expect(g.lo).toBe(2);
    expect(g.hi).toBe(8);
    expect(g.leftPct).toBe("20%");
    expect(g.hiPct).toBe("80%");
    expect(g.xpPct).toBe("50%");
  });

  it("falls back p10/p90 to xp when null", () => {
    const g = bandGeometry({ xp: 5, p10: null, p90: null }, 10);
    expect(g.lo).toBe(5);
    expect(g.hi).toBe(5);
    expect(g.leftPct).toBe("50%");
    expect(g.hiPct).toBe("50%");
  });

  it("clamps every percentage at 100%", () => {
    const g = bandGeometry({ xp: 15, p10: 12, p90: 20 }, 10);
    expect(g.leftPct).toBe("100%");
    expect(g.hiPct).toBe("100%");
    expect(g.xpPct).toBe("100%");
  });
});

describe("bandTooltip", () => {
  it("returns the verbatim vanilla copy character-for-character", () => {
    expect(bandTooltip({ xp: 3.63, p10: 2.41, p90: 10.47 })).toBe(
      "xP 3.63 — actual score lands between 2.4 and 10.5 in 8 gameweeks out of 10",
    );
  });

  it("falls back p10/p90 to xp in the tooltip when null", () => {
    expect(bandTooltip({ xp: 3.63, p10: null, p90: null })).toBe(
      "xP 3.63 — actual score lands between 3.6 and 3.6 in 8 gameweeks out of 10",
    );
  });
});
