import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { Pitch } from "./Pitch";
import { joinSquad } from "../../lib/squadJoin";
import squadFixture from "../../test/fixtures/squad.json";
import xpFixture from "../../test/fixtures/xp_table_squad.json";
import type { SquadResponse, XpRow } from "../../lib/api";
import type { PitchPlayer } from "../../lib/squadJoin";

const squad = (squadFixture as SquadResponse).squad;
const xp = xpFixture as XpRow[];
const players = joinSquad(squad, xp);
const captainCode = squad.find((r) => r.captain)!.player_code;

const VIRGIL = 97032;
const ODEGAARD = 184029;
const HAVERTZ = 219847;

const GHOST_PLAYER: PitchPlayer = {
  player_code: 999001,
  name: "Ghost Player",
  team: "Nowhere",
  position: "MID",
  price_m: 5.0,
  xp: 3.0,
  starting: false,
  captain: false,
  p10: 1.0,
  p90: 8.0,
  xp_capt: null,
  team_short: "ARS",
  status: "a",
  news: "",
  ownership: 5.0,
};

describe("Pitch — empty state", () => {
  it("renders EmptyState rather than a bare pitch when players is empty", () => {
    render(<Pitch players={[]} captainCode={null} viceCode={null} />);
    expect(screen.getByText("Nothing here yet")).toBeInTheDocument();
  });
});

describe("Pitch — marks (D-13)", () => {
  it("applies the locked badge to exactly the named player's card and no other", () => {
    render(
      <Pitch
        players={players}
        captainCode={captainCode}
        viceCode={null}
        marks={{ [VIRGIL]: "locked" }}
      />,
    );
    expect(screen.getAllByLabelText("Locked — always included in solve")).toHaveLength(1);
    expect(screen.queryAllByLabelText("Excluded from solve")).toHaveLength(0);
  });
});

describe("Pitch — diffs (D-16)", () => {
  it("applies the IN badge to exactly the named player's card", () => {
    render(
      <Pitch
        players={players}
        captainCode={captainCode}
        viceCode={null}
        diffs={{ [HAVERTZ]: "in" }}
      />,
    );
    expect(screen.getAllByLabelText("New signing this transfer")).toHaveLength(1);
  });
});

describe("Pitch — ghost card (D-16, D-18)", () => {
  it("renders one extra card immediately after the named player in the named row, announced as a suggested incoming player", () => {
    render(
      <Pitch
        players={players}
        captainCode={captainCode}
        viceCode={null}
        ghost={{ row: "MID", afterCode: ODEGAARD, player: GHOST_PLAYER }}
      />,
    );
    const ghostCards = screen.getAllByLabelText("Suggested incoming player");
    expect(ghostCards).toHaveLength(1);
    expect(within(ghostCards[0]).getByText("Ghost Player")).toBeInTheDocument();

    const midRow = screen.getByRole("group", { name: "Midfielders" });
    const cells = Array.from(midRow.children);
    const odegaardCellIdx = cells.findIndex((c) => within(c as HTMLElement).queryByText("Ødegaard"));
    const ghostCellIdx = cells.findIndex((c) =>
      within(c as HTMLElement).queryByText("Ghost Player"),
    );
    expect(ghostCellIdx).toBe(odegaardCellIdx + 1);
  });

  it("renders no extra card when ghost is null", () => {
    render(<Pitch players={players} captainCode={captainCode} viceCode={null} ghost={null} />);
    expect(screen.queryAllByLabelText("Suggested incoming player")).toHaveLength(0);
  });

  it("renders in the Bench group immediately after the named bench player when row is BENCH (04-08)", () => {
    const benchPlayer = squad.find((r) => !r.starting)!;
    render(
      <Pitch
        players={players}
        captainCode={captainCode}
        viceCode={null}
        ghost={{ row: "BENCH", afterCode: benchPlayer.player_code, player: GHOST_PLAYER }}
      />,
    );
    const ghostCards = screen.getAllByLabelText("Suggested incoming player");
    expect(ghostCards).toHaveLength(1);
    expect(within(ghostCards[0]).getByText("Ghost Player")).toBeInTheDocument();

    const benchGroup = screen.getByRole("group", { name: "Bench" });
    const cells = Array.from(benchGroup.children);
    const benchPlayerCellIdx = cells.findIndex((c) =>
      within(c as HTMLElement).queryByText(benchPlayer.name),
    );
    const ghostCellIdx = cells.findIndex((c) =>
      within(c as HTMLElement).queryByText("Ghost Player"),
    );
    expect(ghostCellIdx).toBe(benchPlayerCellIdx + 1);
  });
});

describe("Pitch — onMark threading", () => {
  it("threads onMark through to every card, making the popover interactive", () => {
    const onMark = vi.fn();
    render(
      <Pitch players={players} captainCode={captainCode} viceCode={null} onMark={onMark} />,
    );
    expect(screen.getByRole("button", { name: "Virgil actions" })).toBeInTheDocument();
  });
});

describe("Pitch — row centering (G-03-1)", () => {
  // Row sizes present on the default 3-5-2 fixture, covering the two rows that drifted
  // left under the old integer-column scheme (Forwards at 2, Bench at 4) and the three
  // odd controls that must NOT move (Goalkeeper at 1, Defenders at 3, Midfielders at 5).
  const ROWS: { label: string; count: number }[] = [
    { label: "Goalkeeper", count: 1 },
    { label: "Defenders", count: 3 },
    { label: "Midfielders", count: 5 },
    { label: "Forwards", count: 2 },
    { label: "Bench", count: 4 },
  ];

  const VIEWPORTS = [
    { width: 600, gap: 8 }, // desktop
    { width: 311, gap: 4 }, // 375px
  ] as const;

  function parseBasis(cell: HTMLElement): { k: number; d: number } {
    const basis = cell.style.flexBasis;
    const match = basis.match(/^calc\(\(100% - (\d+) \* var\(--pitch-gap\)\) \/ (\d+)\)$/);
    expect(match, `unexpected flex-basis "${basis}"`).not.toBeNull();
    return { k: Number(match![1]), d: Number(match![2]) };
  }

  function assertRowIsExactlyCentered(row: HTMLElement, count: number) {
    const cells = Array.from(row.children) as HTMLElement[];
    expect(cells).toHaveLength(count);

    // Test 1 — continuous centering declared inline (invisible to jsdom via className)
    expect(row.style.display).toBe("flex");
    expect(row.style.justifyContent).toBe("center");

    // Test 2 — integer-quantized scheme is gone: no inline track list on the row,
    // no inline column placement on any cell.
    expect(row.style.gridTemplateColumns).toBe("");
    for (const cell of cells) {
      expect(cell.style.gridColumn).toBe("");
    }

    // Test 3 — every cell shares one basis; d === max(5, cellCount), k === d - 1.
    // Sizes 1-5 all resolve to the shared 5-part measure (D-07); size 6 (ghost) to 6.
    const bases = cells.map(parseBasis);
    const [first, ...rest] = bases;
    for (const b of rest) {
      expect(b).toEqual(first);
    }
    const expectedD = Math.max(5, count);
    expect(first.d).toBe(expectedD);
    expect(first.k).toBe(expectedD - 1);

    // Test 4 — zero grow and zero minimum inline size on every cell, so a long name
    // ellipsizes instead of forcing its cell wider than its measure.
    for (const cell of cells) {
      expect(cell.style.flexGrow).toBe("0");
      expect(cell.style.minWidth).toBe("0px");
    }

    // Test 5 — symmetry oracle at both UAT viewports, driven by the parsed part count.
    // jsdom has no layout engine, so this asserts the declared layout model produces
    // equal leading/trailing free space and never overflows its container.
    const d = first.d;
    for (const { width: W, gap: g } of VIEWPORTS) {
      const basis = (W - (d - 1) * g) / d;
      const rowWidth = count * basis + (count - 1) * g;
      const leading = (W - rowWidth) / 2;
      const trailing = W - rowWidth - leading;
      expect(leading).toBeCloseTo(trailing, 10);
      expect(rowWidth).toBeLessThanOrEqual(W + 1e-9);
    }
  }

  describe.each(ROWS)("row size $count ($label)", ({ label, count }) => {
    it(`centers the ${label} row (n=${count}) with equal leading/trailing space and no integer column placement`, () => {
      render(<Pitch players={players} captainCode={captainCode} viceCode={null} />);
      const row = screen.getByRole("group", { name: label });
      assertRowIsExactlyCentered(row, count);
    });
  });

  it("grows the ghost-holding Midfielders row to a 6-part measure and keeps it exactly centered", () => {
    render(
      <Pitch
        players={players}
        captainCode={captainCode}
        viceCode={null}
        ghost={{ row: "MID", afterCode: ODEGAARD, player: GHOST_PLAYER }}
      />,
    );
    const midRow = screen.getByRole("group", { name: "Midfielders" });
    assertRowIsExactlyCentered(midRow, 6);
  });

  it("keeps the ghost-holding Bench row (4 real + 1 ghost = 5) exactly centered (04-08)", () => {
    const benchPlayer = squad.find((r) => !r.starting)!;
    render(
      <Pitch
        players={players}
        captainCode={captainCode}
        viceCode={null}
        ghost={{ row: "BENCH", afterCode: benchPlayer.player_code, player: GHOST_PLAYER }}
      />,
    );
    const benchRow = screen.getByRole("group", { name: "Bench" });
    assertRowIsExactlyCentered(benchRow, 5);
  });
});
