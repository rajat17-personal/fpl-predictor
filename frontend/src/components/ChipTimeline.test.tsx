import { describe, expect, it } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { ChipTimeline, classifyMarker } from "./ChipTimeline";
import chipsFixture from "../test/fixtures/chips.json";
import chipsDgwFixture from "../test/fixtures/chips_dgw.json";

describe("classifyMarker (03-02 Task 2: pure DGW/BGW classification)", () => {
  it("classifies a non-zero dgw_clubs count as dgw", () => {
    expect(classifyMarker({ gw: 5, dgw_clubs: 4, bgw_clubs: 0 })).toBe("dgw");
  });

  it("classifies a non-zero bgw_clubs count (with no dgw) as bgw", () => {
    expect(classifyMarker({ gw: 7, dgw_clubs: 0, bgw_clubs: 6 })).toBe("bgw");
  });

  it("classifies zero/zero as plain", () => {
    expect(classifyMarker({ gw: 3, dgw_clubs: 0, bgw_clubs: 0 })).toBe("plain");
  });
});

describe("ChipTimeline (03-02 Task 2)", () => {
  it("renders 36 markers with no DGW/BGW badges for the all-zero live fixture", () => {
    render(<ChipTimeline structure={chipsFixture.structure} currentGw={3} />);

    const timeline = screen.getByTestId("chip-timeline");
    expect(within(timeline).queryAllByText("DGW")).toHaveLength(0);
    expect(within(timeline).queryAllByText("BGW")).toHaveLength(0);
    // One marker container per gameweek, GW3 through GW38 inclusive.
    const markers = within(timeline)
      .getAllByText(/^GW\d+$/)
      .filter((el) => el.tagName === "SPAN");
    expect(markers).toHaveLength(36);
  });

  it("renders overflow-x-auto on the timeline container (source-level class check)", () => {
    render(<ChipTimeline structure={chipsFixture.structure} currentGw={3} />);
    expect(screen.getByTestId("chip-timeline").className).toContain("overflow-x-auto");
  });

  it("marks exactly the gameweeks with a non-zero dgw_clubs/bgw_clubs with DGW/BGW badges", () => {
    render(<ChipTimeline structure={chipsDgwFixture.structure} currentGw={3} />);

    expect(within(screen.getByTestId("gw-marker-5")).getByText("DGW")).toBeInTheDocument();
    expect(within(screen.getByTestId("gw-marker-7")).getByText("BGW")).toBeInTheDocument();
    for (const gw of [3, 4, 6, 8, 9, 10]) {
      const marker = screen.getByTestId(`gw-marker-${gw}`);
      expect(within(marker).queryByText("DGW")).not.toBeInTheDocument();
      expect(within(marker).queryByText("BGW")).not.toBeInTheDocument();
    }
  });

  it("distinguishes the current gameweek's marker by an accessible attribute, not colour alone", () => {
    render(<ChipTimeline structure={chipsDgwFixture.structure} currentGw={3} />);
    const current = screen.getByTestId("gw-marker-3");
    expect(current).toHaveAttribute("data-current", "true");
    const other = screen.getByTestId("gw-marker-4");
    expect(other).not.toHaveAttribute("data-current");
  });

  it("opens a DGW marker's popover showing the affected-club count, capped at 240px", () => {
    render(<ChipTimeline structure={chipsDgwFixture.structure} currentGw={3} />);
    const marker = screen.getByTestId("gw-marker-5");
    fireEvent.click(within(marker).getByRole("button"));

    const tooltip = within(marker).getByRole("tooltip");
    expect(tooltip.textContent).toContain("4 clubs affected");
    expect(tooltip.className).toContain("max-w-[240px]");
  });
});
