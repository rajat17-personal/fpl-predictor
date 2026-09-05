import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SolveResultsBar } from "./SolveResultsBar";
import solveFixture from "../test/fixtures/solve_transfers_response.json";
import type { SolveTransfersResult } from "../lib/api";

const fixture = solveFixture as SolveTransfersResult;

describe("SolveResultsBar (03-04 Task 3, D-16)", () => {
  it("renders one Moves line per sell-to-buy pair from the fixture", () => {
    render(<SolveResultsBar result={fixture} />);
    const list = screen.getByRole("list");
    expect(list.textContent).toContain("McBurnie");
    expect(list.textContent).toContain("Haaland");
    expect(list.textContent).toContain("Unmapped");
    expect(list.textContent).toContain("Palmer");
  });

  it("renders Hold for a mutated fixture with an empty buys array", () => {
    const holdFixture: SolveTransfersResult = { ...fixture, buys: [] };
    render(<SolveResultsBar result={holdFixture} />);
    expect(screen.getByText("Hold")).toBeInTheDocument();
  });

  it("renders −8 pts in hits for the two-hit fixture", () => {
    render(<SolveResultsBar result={fixture} />);
    expect(screen.getByText("−8 pts in hits")).toBeInTheDocument();
  });

  it("renders no 'pts in hits' text for a mutated zero-hit fixture", () => {
    const zeroHitFixture: SolveTransfersResult = { ...fixture, hits: 0 };
    render(<SolveResultsBar result={zeroHitFixture} />);
    expect(screen.queryByText(/pts in hits/)).not.toBeInTheDocument();
  });

  it("renders the bank to one decimal with a pound sign, the xi_xp value, and the captain name", () => {
    render(<SolveResultsBar result={fixture} />);
    expect(screen.getByText(`Bank £${fixture.bank_after.toFixed(1)}m`)).toBeInTheDocument();
    expect(screen.getByText(`XI xP ${fixture.xi_xp}`)).toBeInTheDocument();
    expect(screen.getByText(`Captain ${fixture.captain}`)).toBeInTheDocument();
  });

  it("renders no p10/p90 range text, and the fixture carries no interval fields", () => {
    render(<SolveResultsBar result={fixture} />);
    expect(screen.queryByText(/p10/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/–\d+\.\d in 8\/10/)).not.toBeInTheDocument();
    // The endpoint returns no interval fields (03-04-PLAN.md's
    // <planner_corrections>) — assert the fixture and the type it's cast to
    // both agree none exist, rather than assuming it.
    expect("xi_p10" in fixture).toBe(false);
    expect("xi_p90" in fixture).toBe(false);
  });

  it("renders a single sell-to-buy pair and several pairs through the same list, with no special single-pair markup", () => {
    const onePair: SolveTransfersResult = {
      ...fixture,
      hits: 0,
      buys: [fixture.buys[0]],
      sells: [fixture.sells[0]],
    };
    render(<SolveResultsBar result={onePair} />);
    const list = screen.getByRole("list");
    expect(list.querySelectorAll("li")).toHaveLength(1);
  });

  it("renders several pairs as a plain list with one <li> per pair", () => {
    render(<SolveResultsBar result={fixture} />);
    const list = screen.getByRole("list");
    expect(list.querySelectorAll("li")).toHaveLength(2);
  });
});
