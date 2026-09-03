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
