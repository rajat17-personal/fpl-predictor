import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { PlanTransfers } from "./PlanTransfers";
import xpFixture from "../test/fixtures/xp_table_squad.json";
import planFixture from "../test/fixtures/plan_response.json";
import type { XpRow } from "../lib/api";

const xpTable = xpFixture as XpRow[];

function renderPlanTransfers(freeTransfersEstimate: number | null = 2) {
  return render(
    <PlanTransfers entryId={6980093} freeTransfersEstimate={freeTransfersEstimate} xpTable={xpTable} />,
  );
}

describe("PlanTransfers — controls (03-03 Task 2, D-19)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the horizon select with exactly 5 options, in vanilla's order and wording, 3 gameweeks selected by default", () => {
    renderPlanTransfers();
    const select = screen.getByLabelText("Plan over") as HTMLSelectElement;
    const options = within(select).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual([
      "next GW only",
      "2 gameweeks",
      "3 gameweeks",
      "4 gameweeks",
      "6 gameweeks",
    ]);
    expect(select).toHaveValue("3");
  });

  it("prefills the free-transfers input from the rating fixture's free_transfers, with min=1 max=5", () => {
    renderPlanTransfers(4);
    const input = screen.getByLabelText("Free transfers") as HTMLInputElement;
    expect(input).toHaveValue(4);
    expect(input).toHaveAttribute("min", "1");
    expect(input).toHaveAttribute("max", "5");
  });

  it("falls back to 1 when the rating's free_transfers is null", () => {
    renderPlanTransfers(null);
    const input = screen.getByLabelText("Free transfers") as HTMLInputElement;
    expect(input).toHaveValue(1);
  });

  it("renders the explanatory paragraph's full verbatim text", () => {
    renderPlanTransfers();
    expect(
      screen.getByText(
        "The solver plans your moves jointly over the horizon — when to move now, when to bank a free transfer, when a hit pays for itself. Free transfers are pre-filled with our estimate from your transfer history (FPL only shows the true figure to your own login) — correct it if the official site says otherwise.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/FPL only shows the true figure to your own login/)).toBeInTheDocument();
  });

  it("shows both the horizon-3 wait copy and the 10-60s warning while pending", async () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch;
    renderPlanTransfers();

    fireEvent.click(screen.getByRole("button", { name: "Plan my transfers" }));

    expect(await screen.findByText(/Planning 3 gameweeks jointly…/)).toBeInTheDocument();
    expect(
      screen.getByText(/a fresh horizon takes ~10-60s while future gameweeks are predicted/),
    ).toBeInTheDocument();
  });

  it("shows the horizon-1 wait copy with no 10-60s warning when 'next GW only' is selected", async () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch;
    renderPlanTransfers();

    fireEvent.change(screen.getByLabelText("Plan over"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Plan my transfers" }));

    expect(await screen.findByText("Planning 1 gameweek jointly…")).toBeInTheDocument();
    expect(screen.queryByText(/10-60s/)).not.toBeInTheDocument();
  });

  it("sends no free_transfers key when the input is emptied", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(planFixture) }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    renderPlanTransfers();

    fireEvent.change(screen.getByLabelText("Free transfers"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Plan my transfers" }));

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body).not.toHaveProperty("free_transfers");
    expect(body.entry).toBe(6980093);
  });

  it("sends free_transfers: 2 when the input holds 2", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(planFixture) }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    renderPlanTransfers();

    fireEvent.change(screen.getByLabelText("Free transfers"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Plan my transfers" }));

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(init.body as string);
    expect(body.free_transfers).toBe(2);
  });

  it("disables the button while the request is pending", () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch;
    renderPlanTransfers();

    const button = screen.getByRole("button", { name: "Plan my transfers" });
    fireEvent.click(button);
    expect(button).toBeDisabled();
  });

  it("renders text beginning 'Planning failed:' on a rejected plan request", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "solve timed out" }),
      }),
    ) as unknown as typeof fetch;
    renderPlanTransfers();

    fireEvent.click(screen.getByRole("button", { name: "Plan my transfers" }));

    expect(await screen.findByText(/^Planning failed:/)).toBeInTheDocument();
    expect(screen.getByText(/solve timed out/)).toBeInTheDocument();
  });

  it("does not error on a successful plan request", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(planFixture) }),
    ) as unknown as typeof fetch;
    renderPlanTransfers();

    fireEvent.click(screen.getByRole("button", { name: "Plan my transfers" }));

    expect(await screen.findByTestId("plan-output")).toBeInTheDocument();
    expect(screen.queryByText(/^Planning failed:/)).not.toBeInTheDocument();
  });
});
