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
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
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
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
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

});

describe("PlanTransfers — per-week output (03-03 Task 3, D-19/D-15)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  async function renderAndSubmit(response: unknown = planFixture) {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(response) }),
    ) as unknown as typeof fetch;
    const utils = renderPlanTransfers();
    fireEvent.click(screen.getByRole("button", { name: "Plan my transfers" }));
    await screen.findByText(/do this now/);
    return utils;
  }

  it("gives the first week's heading '— do this now' and the second week's '— planned'", async () => {
    await renderAndSubmit();
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings.some((t) => t?.includes("GW3") && t.includes("— do this now"))).toBe(true);
    expect(headings.some((t) => t?.includes("GW4") && t.includes("— planned"))).toBe(true);
  });

  it("shows the hit-cost clause for a week with hits and omits it for a week with zero hits", async () => {
    await renderAndSubmit();
    expect(screen.getByText(/, −8 pts in hits/)).toBeInTheDocument();

    const movesHeadings = screen.getAllByText("Moves");
    const week2Detail = movesHeadings[1].closest("div")!.textContent;
    expect(week2Detail).not.toMatch(/pts in hits/);
  });

  it("renders 'Hold' for a week with no buys", async () => {
    await renderAndSubmit();
    const movesHeadings = screen.getAllByText("Moves");
    const week2Tile = movesHeadings[1].closest("div") as HTMLElement;
    expect(within(week2Tile).getByText("Hold")).toBeInTheDocument();
  });

  it("renders 'captain' but no '8/10 GWs' in the Projected XI detail for a week with a null interval", async () => {
    await renderAndSubmit();
    const xiHeadings = screen.getAllByText("Projected XI");
    const week3Detail = xiHeadings[2].closest("div")!.textContent;
    expect(week3Detail).toMatch(/captain/);
    expect(week3Detail).not.toMatch(/8\/10 GWs/);
  });

  it("has exactly one disclosure open on first render, and it is week one's", async () => {
    await renderAndSubmit();
    const summaries = screen.getAllByText(/^Squad for GW/);
    const details = summaries.map((s) => s.closest("details") as HTMLDetailsElement);
    const openDetails = details.filter((d) => d.open);
    expect(openDetails).toHaveLength(1);
    expect(openDetails[0].textContent).toMatch(/Squad for GW3/);
  });

  it("renders each week's disclosure with a pitch showing that week's 15 squad rows", async () => {
    await renderAndSubmit();
    const benches = screen.getAllByTestId("bench");
    expect(benches).toHaveLength(3);
    expect(screen.getAllByText("Virgil")).toHaveLength(3);
  });

  it("renders the closing paragraph's verbatim text exactly once", async () => {
    await renderAndSubmit();
    expect(
      screen.getAllByText(
        "Week one is the decision to act on; later weeks are the current plan and will re-optimise as prices, injuries and form move.",
      ),
    ).toHaveLength(1);
  });

  it("renders a single-week plan as one block with '— do this now' and no '— planned' heading", async () => {
    const oneWeek = { ...planFixture, weeks: planFixture.weeks.slice(0, 1) };
    await renderAndSubmit(oneWeek);
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings.filter((t) => t?.startsWith("GW"))).toHaveLength(1);
    expect(headings.some((t) => t?.includes("— do this now"))).toBe(true);
    expect(headings.some((t) => t?.includes("— planned"))).toBe(false);
  });
});
