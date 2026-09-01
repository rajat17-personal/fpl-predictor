import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Differentials, { diffOwnershipCell } from "./Differentials";
import type { XpRow } from "../lib/api";

/* Task 1 — Differentials page: ownership slider, R39 filter+slice, R40's
 * maxHi floor of 1, R41's un-guarded Own %. Rows are hand-built inline
 * (rather than extending the shared plan 02-01 xp_table.json fixture) so
 * each test can control the exact ownership/status combination it needs to
 * prove, per this task's own read_first note. */

function makeRow(overrides: Partial<XpRow> & { player_code: number; name: string }): XpRow {
  return {
    player_id: overrides.player_code,
    team: "Test Town",
    team_short: "TST",
    position: "MID",
    price_m: 5.0,
    xp: 3.0,
    xp_capt: 4.0,
    p10: 1.5,
    p90: 4.5,
    ownership: 5,
    status: "a",
    news: "",
    ...overrides,
  };
}

function mockFetchOnce(body: unknown) {
  const fetchMock = vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    }),
  );
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

function renderDifferentials() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/differentials"]}>
      <QueryClientProvider client={queryClient}>
        <Differentials />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function bodyRowCount(): number {
  const table = screen.queryByRole("table", { name: "Differentials" });
  if (!table) {
    return 0;
  }
  return within(table).queryAllByRole("row").length - 1; // drop header row
}

describe("diffOwnershipCell", () => {
  it("renders the literal 'undefined' text for a null ownership — no en-dash fallback (R41)", () => {
    expect(diffOwnershipCell(null)).toBe("undefined");
  });

  it("renders one decimal place for a real ownership value", () => {
    expect(diffOwnershipCell(12.34)).toBe("12.3");
  });
});

describe("Differentials", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the range input with min=1 max=25 step=1 and an initial value of 10", async () => {
    mockFetchOnce([makeRow({ player_code: 1, name: "Solo" })]);
    renderDifferentials();

    const slider = await screen.findByRole("slider", { name: /max ownership/i });
    expect(slider).toHaveAttribute("min", "1");
    expect(slider).toHaveAttribute("max", "25");
    expect(slider).toHaveAttribute("step", "1");
    expect((slider as HTMLInputElement).value).toBe("10");
  });

  it("at cap 10, includes an ownership-8 available player and excludes an ownership-12 player and an ownership-8 unavailable player", async () => {
    const rows = [
      makeRow({ player_code: 1, name: "Included", ownership: 8, status: "a" }),
      makeRow({ player_code: 2, name: "TooHighOwn", ownership: 12, status: "a" }),
      makeRow({ player_code: 3, name: "Unavailable", ownership: 8, status: "i" }),
    ];
    mockFetchOnce(rows);
    renderDifferentials();

    expect(await screen.findByText("Included")).toBeInTheDocument();
    expect(screen.queryByText("TooHighOwn")).not.toBeInTheDocument();
    expect(screen.queryByText("Unavailable")).not.toBeInTheDocument();
  });

  it("excludes a row with null ownership even at the maximum cap of 25 — the ?? 100 fallback treats it as fully owned", async () => {
    const rows = [
      makeRow({ player_code: 1, name: "NullOwned", ownership: null, status: "a" }),
      makeRow({ player_code: 2, name: "Visible", ownership: 25, status: "a" }),
    ];
    mockFetchOnce(rows);
    renderDifferentials();

    const slider = await screen.findByRole("slider", { name: /max ownership/i });
    fireEvent.change(slider, { target: { value: "25" } });

    expect(await screen.findByText("Visible")).toBeInTheDocument();
    expect(screen.queryByText("NullOwned")).not.toBeInTheDocument();
  });

  it("moving the slider from 10 to 25 widens the rendered set with no additional fetch", async () => {
    const rows = [8, 12, 16, 20, 24].map((own, i) =>
      makeRow({ player_code: i, name: `P${own}`, ownership: own, status: "a" }),
    );
    const fetchMock = mockFetchOnce(rows);
    renderDifferentials();

    await screen.findByText("P8");
    expect(bodyRowCount()).toBe(1); // only ownership 8 qualifies at cap 10

    const slider = screen.getByRole("slider", { name: /max ownership/i });
    fireEvent.change(slider, { target: { value: "25" } });

    await screen.findByText("P24");
    expect(bodyRowCount()).toBe(5); // all five qualify at cap 25

    const dataCalls = fetchMock.mock.calls.filter(([url]) => url === "/data/xp_table.json");
    expect(dataCalls).toHaveLength(1);
  });

  it("renders exactly 30 rows from a 40-row qualifying source (R39 slice)", async () => {
    const rows = Array.from({ length: 40 }, (_, i) =>
      makeRow({ player_code: i, name: `Q${i}`, ownership: 5, status: "a", xp: 1 + i }),
    );
    mockFetchOnce(rows);
    renderDifferentials();

    await screen.findByText("Q0");
    expect(bodyRowCount()).toBe(30);
  });

  it("scales the band point marker against a maxHi floor of 1 when every qualifying row's p90 is below 1 (R40)", async () => {
    const tinyRow = makeRow({
      player_code: 1,
      name: "Tiny",
      ownership: 5,
      status: "a",
      xp: 0.5,
      p10: 0.2,
      p90: 0.8,
    });
    mockFetchOnce([tinyRow]);
    const { container } = renderDifferentials();

    await screen.findByText("Tiny");
    const marker = container.querySelector(".bg-band-pt") as HTMLElement;
    // xp 0.5 / maxHi 1 (floored) = 50%. Without the floor, maxHi would be
    // 0.8 (the row's own p90), giving 62.5% instead.
    expect(marker.style.left).toBe("calc(50% - 4px)");
  });

  it("renders the page-specific zero-match heading and body when the cap matches nothing", async () => {
    mockFetchOnce([makeRow({ player_code: 1, name: "TooOwned", ownership: 10, status: "a" })]);
    renderDifferentials();

    const slider = await screen.findByRole("slider", { name: /max ownership/i });
    fireEvent.change(slider, { target: { value: "1" } });

    expect(
      await screen.findByText("No players under 1% ownership right now"),
    ).toBeInTheDocument();
    expect(screen.getByText("Try raising the slider.")).toBeInTheDocument();
  });

  it("has no interactive elements within the differentials table (not sortable)", async () => {
    mockFetchOnce([makeRow({ player_code: 1, name: "Solo", ownership: 5, status: "a" })]);
    renderDifferentials();

    const table = await screen.findByRole("table", { name: "Differentials" });
    expect(within(table).queryAllByRole("button")).toHaveLength(0);
  });

  it("renders the shared EmptyState for a zero-row source (distinct from the cap zero-match heading)", async () => {
    mockFetchOnce([]);
    renderDifferentials();

    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
  });

  it("renders ErrorState naming the differentials data on a fetch failure", async () => {
    globalThis.fetch = vi.fn(() => Promise.reject(new Error("network down"))) as unknown as typeof fetch;
    renderDifferentials();

    expect(await screen.findByText("Couldn't load this page")).toBeInTheDocument();
    expect(screen.getByText(/the differentials data/)).toBeInTheDocument();
  });

  it("sets document.title for the '/differentials' route", async () => {
    mockFetchOnce([makeRow({ player_code: 1, name: "Solo", ownership: 5, status: "a" })]);
    renderDifferentials();

    await screen.findByText("Solo");
    expect(document.title).toBe("Differentials — FPL ML");
  });
});
