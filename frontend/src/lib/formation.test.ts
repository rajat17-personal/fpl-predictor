import { describe, expect, it } from "vitest";
import { deriveFormation, splitPitchRows } from "./formation";
import squadFixture from "../test/fixtures/squad.json";
import type { SquadResponse } from "./api";

const squad = (squadFixture as SquadResponse).squad;

describe("deriveFormation (mirrors optimize/squad_ilp.py:126)", () => {
  it("returns the live fixture's own formation string (3-5-2)", () => {
    expect(deriveFormation(squad)).toBe((squadFixture as SquadResponse).formation);
    expect(deriveFormation(squad)).toBe("3-5-2");
  });

  it("returns 5-3-2 for a hand-built 5-DEF starter set", () => {
    const rows = [
      { position: "GK", starting: true },
      { position: "DEF", starting: true },
      { position: "DEF", starting: true },
      { position: "DEF", starting: true },
      { position: "DEF", starting: true },
      { position: "DEF", starting: true },
      { position: "MID", starting: true },
      { position: "MID", starting: true },
      { position: "MID", starting: true },
      { position: "FWD", starting: true },
      { position: "FWD", starting: true },
      { position: "DEF", starting: false },
      { position: "MID", starting: false },
      { position: "FWD", starting: false },
      { position: "GK", starting: false },
    ];
    expect(deriveFormation(rows)).toBe("5-3-2");
  });

  it("ignores bench rows entirely", () => {
    const rows = [
      { position: "FWD", starting: true },
      { position: "FWD", starting: false },
      { position: "FWD", starting: false },
    ];
    expect(deriveFormation(rows)).toBe("0-0-1");
  });
});

describe("splitPitchRows", () => {
  it("buckets the live fixture into GK/DEF/MID/FWD starters plus a 4-card bench", () => {
    const split = splitPitchRows(squad);
    expect(split.gk).toHaveLength(1);
    expect(split.def).toHaveLength(3);
    expect(split.mid).toHaveLength(5);
    expect(split.fwd).toHaveLength(2);
    expect(split.bench).toHaveLength(4);
  });

  it("preserves source-array order within each bucket (stable filter, never a sort)", () => {
    const rows = [
      { player_code: 1, name: "A", team: "T", position: "MID", price_m: 5, xp: 1, starting: true, captain: false },
      { player_code: 2, name: "B", team: "T", position: "MID", price_m: 5, xp: 9, starting: true, captain: false },
      { player_code: 3, name: "C", team: "T", position: "MID", price_m: 5, xp: 3, starting: true, captain: false },
    ];
    const split = splitPitchRows(rows);
    expect(split.mid.map((r) => r.name)).toEqual(["A", "B", "C"]);
  });

  it("does not sort the bench either", () => {
    const rows = [
      { player_code: 1, name: "Z", team: "T", position: "DEF", price_m: 5, xp: 1, starting: false, captain: false },
      { player_code: 2, name: "A", team: "T", position: "DEF", price_m: 5, xp: 9, starting: false, captain: false },
    ];
    const split = splitPitchRows(rows);
    expect(split.bench.map((r) => r.name)).toEqual(["Z", "A"]);
  });
});
