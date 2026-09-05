import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FdrCell } from "./FdrCell";
import type { TickerGw } from "../lib/api";

describe("FdrCell (ported from web/fixtures.html, R21-R22, verified 2026-09-01)", () => {
  it("renders an em dash with the accessible description 'Blank gameweek' when fixtures is empty", () => {
    const gw: TickerGw = { gw: 5, fixtures: [] };
    render(<FdrCell gw={gw} />);

    const cell = screen.getByLabelText("Blank gameweek");
    expect(cell).toHaveTextContent("—");
    expect(cell.className).toContain("bg-fdr3-bg");
  });

  it("renders the home-fixture description verbatim", () => {
    const gw: TickerGw = { gw: 5, fixtures: [{ opp: "ARS", home: true, fdr: 2 }] };
    render(<FdrCell gw={gw} />);

    expect(screen.getByLabelText("Home vs ARS, difficulty 2")).toBeInTheDocument();
    expect(screen.getByText("ARS")).toBeInTheDocument();
    expect(screen.getByText("H")).toBeInTheDocument();
  });

  it("renders the away-fixture description verbatim", () => {
    const gw: TickerGw = { gw: 5, fixtures: [{ opp: "MUN", home: false, fdr: 4 }] };
    render(<FdrCell gw={gw} />);

    expect(screen.getByLabelText("Away vs MUN, difficulty 4")).toBeInTheDocument();
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("renders both fixtures of a double gameweek in the same cell", () => {
    const gw: TickerGw = {
      gw: 12,
      fixtures: [
        { opp: "EVE", home: true, fdr: 1 },
        { opp: "BOU", home: false, fdr: 2 },
      ],
    };
    render(<FdrCell gw={gw} />);

    expect(screen.getByLabelText("Home vs EVE, difficulty 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Away vs BOU, difficulty 2")).toBeInTheDocument();
  });

  it("selects a distinct background class for every difficulty 1 through 5", () => {
    const classes = [1, 2, 3, 4, 5].map((fdr) => {
      const gw: TickerGw = { gw: 1, fixtures: [{ opp: "TST", home: true, fdr }] };
      const { unmount } = render(<FdrCell gw={gw} />);
      const cls = screen.getByLabelText(`Home vs TST, difficulty ${fdr}`).className;
      unmount();
      return cls;
    });
    expect(new Set(classes).size).toBe(5);
  });

  it("clamps an out-of-range fdr value to the neutral difficulty-3 styling", () => {
    const gw: TickerGw = { gw: 1, fixtures: [{ opp: "TST", home: true, fdr: 9 }] };
    render(<FdrCell gw={gw} />);

    const span = screen.getByLabelText("Home vs TST, difficulty 9");
    expect(span.className).toContain("bg-fdr3-bg");
    expect(span.className).toContain("text-fdr3-ink");
  });

  it("mounts no interactive elements — the fixture cell is not a control", () => {
    const gw: TickerGw = { gw: 1, fixtures: [{ opp: "TST", home: true, fdr: 1 }] };
    const { container } = render(<FdrCell gw={gw} />);
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });
});

/* UAT gap G-02-2: the seven tests above query text and accessible names only,
 * which pass identically whether the venue tag sits beside or beneath the
 * opponent code — nothing in the existing suite could have caught the
 * regression that shipped the venue letter inline. jsdom applies no
 * stylesheet, so these assertions pin the class contract (what Tailwind
 * compiles into layout) rather than computed style, and use substring
 * checks so incidental utility reordering doesn't break the suite. */
describe("FdrCell geometry contract (UAT gap G-02-2)", () => {
  it("stacks the populated chip in a column direction so the venue tag begins its own line", () => {
    const gw: TickerGw = { gw: 5, fixtures: [{ opp: "ARS", home: true, fdr: 2 }] };
    render(<FdrCell gw={gw} />);

    const chip = screen.getByLabelText("Home vs ARS, difficulty 2");
    expect(chip.className).toContain("flex-col");
  });

  it("carries the 56px minimum width on the populated chip itself, not on the wrapper", () => {
    const gw: TickerGw = { gw: 5, fixtures: [{ opp: "ARS", home: true, fdr: 2 }] };
    render(<FdrCell gw={gw} />);

    const chip = screen.getByLabelText("Home vs ARS, difficulty 2");
    const wrapper = chip.parentElement!;
    expect(chip.className).toContain("min-w-[56px]");
    expect(wrapper.className).not.toContain("min-w-[56px]");
  });

  it("keeps the venue letter as a small element whose parent is the chip carrying the accessible description", () => {
    const gw: TickerGw = { gw: 5, fixtures: [{ opp: "ARS", home: true, fdr: 2 }] };
    render(<FdrCell gw={gw} />);

    const chip = screen.getByLabelText("Home vs ARS, difficulty 2");
    const venueTag = screen.getByText("H");
    expect(venueTag.tagName).toBe("SMALL");
    expect(venueTag.parentElement).toBe(chip);
  });

  it("renders the chip in the monospace family and de-emphasises the venue tag at 75 percent opacity", () => {
    const gw: TickerGw = { gw: 5, fixtures: [{ opp: "ARS", home: true, fdr: 2 }] };
    render(<FdrCell gw={gw} />);

    const chip = screen.getByLabelText("Home vs ARS, difficulty 2");
    const venueTag = screen.getByText("H");
    expect(chip.className).toContain("font-mono");
    expect(venueTag.className).toContain("opacity-75");
  });

  it("stacks the blank-gameweek chip in the same column direction and keeps its 56px minimum width", () => {
    const gw: TickerGw = { gw: 5, fixtures: [] };
    render(<FdrCell gw={gw} />);

    const chip = screen.getByLabelText("Blank gameweek");
    expect(chip.className).toContain("flex-col");
    expect(chip.className).toContain("min-w-[56px]");
    expect(chip.className).toContain("font-mono");
  });

  it("gives both chips of a double gameweek their own 56px minimum width independently", () => {
    const gw: TickerGw = {
      gw: 12,
      fixtures: [
        { opp: "EVE", home: true, fdr: 1 },
        { opp: "BOU", home: false, fdr: 2 },
      ],
    };
    render(<FdrCell gw={gw} />);

    const chip1 = screen.getByLabelText("Home vs EVE, difficulty 1");
    const chip2 = screen.getByLabelText("Away vs BOU, difficulty 2");
    expect(chip1.className).toContain("min-w-[56px]");
    expect(chip2.className).toContain("min-w-[56px]");
  });
});
