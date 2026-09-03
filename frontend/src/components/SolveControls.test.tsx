import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SolveControls } from "./SolveControls";

describe("SolveControls (03-04 Task 2)", () => {
  it("renders exactly three inputs with the accessible labels Free transfers/Max transfers/Plan horizon, and none for mode or budget", () => {
    render(<SolveControls freeTransfersEstimate={2} pending={false} onSolve={vi.fn()} />);

    expect(screen.getByLabelText("Free transfers")).toBeInTheDocument();
    expect(screen.getByLabelText("Max transfers")).toBeInTheDocument();
    expect(screen.getByLabelText("Plan horizon")).toBeInTheDocument();
    expect(screen.queryByLabelText(/mode/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/budget/i)).not.toBeInTheDocument();
  });

  it("mirrors the server bounds as min/max, and offers horizon values 1, 2, 3, 4, 6", () => {
    render(<SolveControls freeTransfersEstimate={2} pending={false} onSolve={vi.fn()} />);

    const ft = screen.getByLabelText("Free transfers");
    expect(ft).toHaveAttribute("min", "0");
    expect(ft).toHaveAttribute("max", "5");

    const maxT = screen.getByLabelText("Max transfers");
    expect(maxT).toHaveAttribute("min", "0");
    expect(maxT).toHaveAttribute("max", "15");

    const horizon = screen.getByLabelText("Plan horizon") as HTMLSelectElement;
    const values = Array.from(horizon.options).map((o) => o.value);
    expect(values).toEqual(["1", "2", "3", "4", "6"]);
  });

  it("prefills Free transfers from the supplied estimate and is never empty on first render", () => {
    render(<SolveControls freeTransfersEstimate={3} pending={false} onSolve={vi.fn()} />);
    expect((screen.getByLabelText("Free transfers") as HTMLInputElement).value).toBe("3");
  });

  it("falls back to 1 for Free transfers when no estimate is supplied", () => {
    render(<SolveControls freeTransfersEstimate={null} pending={false} onSolve={vi.fn()} />);
    expect((screen.getByLabelText("Free transfers") as HTMLInputElement).value).toBe("1");
  });

  it("omits maxTransfers entirely (null) when that input is left empty", () => {
    const onSolve = vi.fn();
    render(<SolveControls freeTransfersEstimate={1} pending={false} onSolve={onSolve} />);

    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    expect(onSolve).toHaveBeenCalledWith({ freeTransfers: 1, maxTransfers: null, horizon: 1 });
  });

  it("passes a numeric maxTransfers when the input carries a value", () => {
    const onSolve = vi.fn();
    render(<SolveControls freeTransfersEstimate={1} pending={false} onSolve={onSolve} />);

    fireEvent.change(screen.getByLabelText("Max transfers"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Solve transfers" }));

    expect(onSolve).toHaveBeenCalledWith({ freeTransfers: 1, maxTransfers: 4, horizon: 1 });
  });

  it("renders exactly 'Solving your transfers…' and disables the button while pending", () => {
    render(<SolveControls freeTransfersEstimate={1} pending={true} onSolve={vi.fn()} />);

    expect(screen.getByRole("status").textContent).toBe("Solving your transfers…");
    expect(screen.getByRole("button", { name: "Solve transfers" })).toBeDisabled();
  });

  it("renders no wait status and an enabled button when not pending", () => {
    render(<SolveControls freeTransfersEstimate={1} pending={false} onSolve={vi.fn()} />);

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Solve transfers" })).not.toBeDisabled();
  });
});
