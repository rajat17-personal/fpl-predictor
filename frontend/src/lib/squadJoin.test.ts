import { describe, expect, it } from "vitest";
import { deriveViceCaptain, joinSquad } from "./squadJoin";
import squadFixture from "../test/fixtures/squad.json";
import xpFixture from "../test/fixtures/xp_table_squad.json";
import type { SquadResponse, XpRow } from "./api";

const squad = (squadFixture as SquadResponse).squad;
const xp = xpFixture as XpRow[];

describe("joinSquad", () => {
  it("joins every fixture squad row to its xp_table row by player_code", () => {
    const joined = joinSquad(squad, xp);
    expect(joined).toHaveLength(15);
    const fernandes = joined.find((r) => r.player_code === 141746)!;
    expect(fernandes.team_short).toBe("MUN");
    expect(fernandes.xp_capt).toBe(6.04);
    expect(fernandes.p10).toBe(2.41);
    expect(fernandes.p90).toBe(10.47);
  });

  it("matches only on player_code — a name collision with a different player_code yields null joined fields", () => {
    const rows = [
      {
        player_code: 999999,
        name: "Virgil",
        team: "Liverpool",
        position: "DEF",
        price_m: 6.5,
        xp: 2.68,
        starting: true,
        captain: false,
      },
    ];
    const decoy: XpRow = {
      player_code: 111111,
      player_id: 1,
      name: "Virgil",
      team: "Liverpool",
      team_short: "LIV",
      position: "DEF",
      price_m: 6.5,
      xp: 2.68,
      xp_capt: 9.99,
      p10: 5,
      p90: 9,
      ownership: 50,
      status: "a",
      news: "",
    };
    const joined = joinSquad(rows, [decoy]);
    expect(joined).toHaveLength(1);
    expect(joined[0].p10).toBeNull();
    expect(joined[0].p90).toBeNull();
    expect(joined[0].xp_capt).toBeNull();
    expect(joined[0].team_short).toBeNull();
    expect(joined[0].status).toBeNull();
    expect(joined[0].news).toBeNull();
    expect(joined[0].ownership).toBeNull();
  });

  it("keeps the squad row's own fields when no xp row matches at all", () => {
    const rows = [
      {
        player_code: 424242,
        name: "Unknown",
        team: "Nowhere",
        position: "MID",
        price_m: 4.5,
        xp: 1.1,
        starting: false,
        captain: false,
      },
    ];
    const joined = joinSquad(rows, []);
    expect(joined[0].name).toBe("Unknown");
    expect(joined[0].p10).toBeNull();
  });
});

describe("deriveViceCaptain (D-08)", () => {
  it("picks the highest xp_capt among starters, excluding the captain", () => {
    const xpByCode = new Map(xp.map((row) => [row.player_code, row]));
    const starters = squad
      .filter((r) => r.starting)
      .map((r) => ({ player_code: r.player_code, captain: r.captain }));
    const vc = deriveViceCaptain(starters, xpByCode);
    // Fernandes (141746) carries the highest starter xp_capt (6.04) and is
    // not the captain (Isak, 219168).
    expect(vc).toBe(141746);
  });

  it("skips the captain even when the captain holds the highest xp_capt", () => {
    const xpByCode = new Map<number, { xp_capt: number | null }>([
      [1, { xp_capt: 9.0 }],
      [2, { xp_capt: 5.0 }],
    ]);
    const starters = [
      { player_code: 1, captain: true },
      { player_code: 2, captain: false },
    ];
    expect(deriveViceCaptain(starters, xpByCode)).toBe(2);
  });

  it("returns null when every starter's xp_capt is null", () => {
    const xpByCode = new Map<number, { xp_capt: number | null }>([
      [1, { xp_capt: null }],
      [2, { xp_capt: null }],
    ]);
    const starters = [
      { player_code: 1, captain: false },
      { player_code: 2, captain: false },
    ];
    expect(deriveViceCaptain(starters, xpByCode)).toBeNull();
  });

  it("skips a starter whose xp_capt is null in favour of one that isn't", () => {
    const xpByCode = new Map<number, { xp_capt: number | null }>([
      [1, { xp_capt: null }],
      [2, { xp_capt: 3.5 }],
    ]);
    const starters = [
      { player_code: 1, captain: false },
      { player_code: 2, captain: false },
    ];
    expect(deriveViceCaptain(starters, xpByCode)).toBe(2);
  });

  it("returns null for an empty starters array", () => {
    expect(deriveViceCaptain([], new Map())).toBeNull();
  });
});
