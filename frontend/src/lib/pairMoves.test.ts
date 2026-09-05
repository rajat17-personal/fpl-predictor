import { describe, expect, it } from "vitest";
import { pairMoves } from "./pairMoves";

describe("pairMoves (03-02 Task 3: verbatim port of web/team.html's pairMoves)", () => {
  it("returns structured objects with sellName/buyName/position keys, never markup", () => {
    const pairs = pairMoves(
      [{ name: "Egan", position: "DEF" }],
      [{ name: "Gvardiol", position: "DEF" }],
    );
    expect(pairs).toEqual([{ sellName: "Egan", buyName: "Gvardiol", position: "DEF" }]);
    for (const pair of pairs) {
      expect(pair.sellName).not.toContain("<");
      expect(pair.buyName).not.toContain("<");
    }
  });

  it("pairs two sold midfielders with two bought midfielders by array order", () => {
    const pairs = pairMoves(
      [
        { name: "Schade", position: "MID" },
        { name: "Ødegaard", position: "MID" },
      ],
      [
        { name: "Saka", position: "MID" },
        { name: "Palmer", position: "MID" },
      ],
    );
    expect(pairs).toEqual([
      { sellName: "Schade", buyName: "Saka", position: "MID" },
      { sellName: "Ødegaard", buyName: "Palmer", position: "MID" },
    ]);
  });

  it("yields a question-mark buy name when a position has more sells than buys", () => {
    const pairs = pairMoves(
      [
        { name: "Schade", position: "MID" },
        { name: "Ødegaard", position: "MID" },
      ],
      [{ name: "Saka", position: "MID" }],
    );
    expect(pairs).toEqual([
      { sellName: "Schade", buyName: "Saka", position: "MID" },
      { sellName: "Ødegaard", buyName: "?", position: "MID" },
    ]);
  });

  it("returns an empty array for no sells", () => {
    expect(pairMoves([], [{ name: "Saka", position: "MID" }])).toEqual([]);
  });
});
