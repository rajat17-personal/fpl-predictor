import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { RateDiff, resolveRateOverlay } from "./RateDiff";
import rateFixture from "../test/fixtures/rate_response.json";
import rateHoldFixture from "../test/fixtures/rate_response_hold.json";
import xpFixture from "../test/fixtures/xp_table_squad.json";
import type { RateBestMove, RateResponse, XpRow } from "../lib/api";

const fixture = rateFixture as RateResponse;
const holdFixture = rateHoldFixture as RateResponse;
const xpTable = xpFixture as XpRow[];

describe("resolveRateOverlay (backstop, PITCH-04)", () => {
  it("returns no diffs and no ghost when bestMove is null", () => {
    const result = resolveRateOverlay(fixture.xi, xpTable, null);
    expect(result.diffs).toEqual({});
    expect(result.ghost).toBeNull();
  });

  it("marks the sold player out and builds a ghost for the bought player when both resolve uniquely", () => {
    const result = resolveRateOverlay(fixture.xi, xpTable, fixture.best_move);
    const soldCode = fixture.xi.find((r) => r.name === "Havertz")!.player_code;
    expect(result.diffs).toEqual({ [soldCode]: "out" });
    expect(result.ghost).not.toBeNull();
    expect(result.ghost!.player.name).toBe("Haaland");
    expect(result.ghost!.afterCode).toBe(soldCode);
    expect(result.ghost!.row).toBe("FWD");
  });

  it("applies no out treatment when the sell name matches zero xi rows", () => {
    const move: RateBestMove = { sell: ["Nobody"], buy: ["Haaland"], xp_gain: 1 };
    const result = resolveRateOverlay(fixture.xi, xpTable, move);
    expect(result.diffs).toEqual({});
  });

  it("applies no out treatment when the sell name matches two xi rows", () => {
    const dupXi = fixture.xi.map((r, i) => (i === 3 ? { ...r, name: "Havertz" } : r));
    const result = resolveRateOverlay(dupXi, xpTable, fixture.best_move);
    expect(result.diffs).toEqual({});
  });

  it("passes no ghost when the buy name matches zero rows in the joined pool", () => {
    const move: RateBestMove = { sell: ["Havertz"], buy: ["Nobody"], xp_gain: 1 };
    const result = resolveRateOverlay(fixture.xi, xpTable, move);
    expect(result.ghost).toBeNull();
  });

  it("passes no ghost when the buy name matches two rows in the joined pool", () => {
    const dupXp = xpTable.map((r, i) => (i === 0 ? { ...r, name: "Haaland" } : r));
    const result = resolveRateOverlay(fixture.xi, dupXp, fixture.best_move);
    expect(result.ghost).toBeNull();
  });

  it("still resolves the out card even when the buy name fails to resolve", () => {
    const move: RateBestMove = { sell: ["Havertz"], buy: ["Nobody"], xp_gain: 1 };
    const result = resolveRateOverlay(fixture.xi, xpTable, move);
    const soldCode = fixture.xi.find((r) => r.name === "Havertz")!.player_code;
    expect(result.diffs).toEqual({ [soldCode]: "out" });
    expect(result.ghost).toBeNull();
  });
});

describe("RateDiff — one pitch (D-18)", () => {
  it("renders exactly one pitch (one bench container)", () => {
    render(
      <RateDiff xi={fixture.xi} bestMove={fixture.best_move} xpTable={xpTable} gw={fixture.gw} />,
    );
    expect(screen.getAllByTestId("bench")).toHaveLength(1);
  });

  it("marks the sold player with the accessible out label and renders exactly one ghost card", () => {
    render(
      <RateDiff xi={fixture.xi} bestMove={fixture.best_move} xpTable={xpTable} gw={fixture.gw} />,
    );
    expect(screen.getByText("Suggested transfer out")).toBeInTheDocument();
    expect(screen.getAllByLabelText("Suggested incoming player")).toHaveLength(1);
  });

  it("places the ghost card in the same formation row as the out card", () => {
    render(
      <RateDiff xi={fixture.xi} bestMove={fixture.best_move} xpTable={xpTable} gw={fixture.gw} />,
    );
    const fwdRow = screen.getByRole("group", { name: "Forwards" });
    expect(within(fwdRow).getByLabelText("Suggested incoming player")).toBeInTheDocument();
    expect(within(fwdRow).getByText("Suggested transfer out")).toBeInTheDocument();
  });

  it("renders no out treatment, no ghost card, and no swap line for the Hold fixture", () => {
    render(
      <RateDiff
        xi={holdFixture.xi}
        bestMove={holdFixture.best_move}
        xpTable={xpTable}
        gw={holdFixture.gw}
      />,
    );
    expect(screen.queryByText("Suggested transfer out")).not.toBeInTheDocument();
    expect(screen.queryAllByLabelText("Suggested incoming player")).toHaveLength(0);
    expect(screen.queryByTestId("swap-line")).not.toBeInTheDocument();
  });

  it("still renders the pitch and the textual swap line, with no out treatment, when the sell name matches no xi row", () => {
    const mutated: RateBestMove = { ...fixture.best_move!, sell: ["Nobody"] };
    render(<RateDiff xi={fixture.xi} bestMove={mutated} xpTable={xpTable} gw={fixture.gw} />);
    expect(screen.getAllByTestId("bench")).toHaveLength(1);
    expect(screen.getByTestId("swap-line")).toBeInTheDocument();
    expect(screen.queryByText("Suggested transfer out")).not.toBeInTheDocument();
  });

  it("applies no out treatment when the sell name matches two xi rows", () => {
    const dupXi = fixture.xi.map((r, i) => (i === 3 ? { ...r, name: "Havertz" } : r));
    render(
      <RateDiff xi={dupXi} bestMove={fixture.best_move} xpTable={xpTable} gw={fixture.gw} />,
    );
    expect(screen.queryByText("Suggested transfer out")).not.toBeInTheDocument();
  });

  it("renders the swap line with the sell name, the buy name, and +{xp_gain} xP", () => {
    render(
      <RateDiff xi={fixture.xi} bestMove={fixture.best_move} xpTable={xpTable} gw={fixture.gw} />,
    );
    const line = screen.getByTestId("swap-line");
    expect(line.textContent).toContain("Havertz");
    expect(line.textContent).toContain("Haaland");
    expect(line.textContent).toContain(`+${fixture.best_move!.xp_gain} xP`);
  });

  it("renders the verbatim best-XI heading and sub-copy", () => {
    render(
      <RateDiff xi={fixture.xi} bestMove={fixture.best_move} xpTable={xpTable} gw={fixture.gw} />,
    );
    expect(screen.getByText(`Your best XI for GW${fixture.gw}`)).toBeInTheDocument();
    expect(
      screen.getByText(
        "Keeping your current squad (no transfers), this is the lineup and captain the model would field.",
      ),
    ).toBeInTheDocument();
  });
});
