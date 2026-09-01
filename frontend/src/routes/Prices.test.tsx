import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Prices from "./Prices";
import officialFixture from "../test/fixtures/watchlist_official.json";
import heuristicFixture from "../test/fixtures/watchlist_heuristic.json";
import modelFixture from "../test/fixtures/watchlist_model.json";
import type { Watchlist } from "../lib/api";

const official = officialFixture as Watchlist;
const heuristic = heuristicFixture as Watchlist;
const trained = modelFixture as Watchlist;

function mockFetchOnce(body: unknown) {
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    }),
  ) as unknown as typeof fetch;
}

function renderPrices() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/prices"]}>
      <QueryClientProvider client={queryClient}>
        <Prices />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Prices (ported from web/prices.html, verified 2026-09-01)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows 114% with the progress bar clamped to 100% for a row whose progress is 1.14 (R25)", async () => {
    mockFetchOnce(official);
    renderPrices();

    const row = (await screen.findByText("De Cuyper")).closest("tr")!;
    expect(within(row).getByText("114%")).toBeInTheDocument();
    const bar = row.querySelector('[style*="width"]') as HTMLElement;
    expect(bar.style.width).toBe("100%");
  });

  it("appends the tonight clause only when proj_tonight is non-null (R26)", async () => {
    mockFetchOnce(official);
    renderPrices();

    const gakpoRow = (await screen.findByText("Gakpo")).closest("tr")!;
    expect(within(gakpoRow).getByText("88% → 87% tonight")).toBeInTheDocument();

    const deCuyperRow = screen.getByText("De Cuyper").closest("tr")!;
    expect(within(deCuyperRow).getByText("114%")).toBeInTheDocument();
    expect(within(deCuyperRow).queryByText(/→.*tonight/)).not.toBeInTheDocument();
  });

  it("shows the threshold label in non-official mode when prob is null (R27)", async () => {
    mockFetchOnce(heuristic);
    renderPrices();

    const row = (await screen.findByText("Semenyo")).closest("tr")!;
    expect(within(row).getByText("100% of threshold")).toBeInTheDocument();
  });

  it("renders the official note and none of the other two", async () => {
    mockFetchOnce(official);
    renderPrices();
    await screen.findByText("De Cuyper");

    expect(screen.getByText(/Live from FPL's own price predictor/)).toBeInTheDocument();
    expect(screen.queryByText(/Heuristic mode/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Model predictions \(trained/)).not.toBeInTheDocument();
  });

  it("renders the heuristic note and none of the other two", async () => {
    mockFetchOnce(heuristic);
    renderPrices();
    await screen.findByText("Semenyo");

    expect(screen.getByText(/Heuristic mode/)).toBeInTheDocument();
    expect(screen.queryByText(/Live from FPL's own price predictor/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Model predictions \(trained/)).not.toBeInTheDocument();
  });

  it("renders the trained-model note and none of the other two", async () => {
    mockFetchOnce(trained);
    renderPrices();
    await screen.findByText("Palmer");

    expect(screen.getByText(/Model predictions \(trained 2026-08-20/)).toBeInTheDocument();
    expect(
      screen.getByText(/hit-rate on actual movers 73% in validation/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Live from FPL's own price predictor/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Heuristic mode/)).not.toBeInTheDocument();
  });

  it("omits the price-locked-players sentence when locked_players is 0, keeping the rest of the note (R31)", async () => {
    mockFetchOnce({ ...official, locked_players: 0 });
    renderPrices();
    await screen.findByText("De Cuyper");

    expect(screen.getByText(/Live from FPL's own price predictor/)).toBeInTheDocument();
    expect(screen.queryByText(/price-locked players/)).not.toBeInTheDocument();
  });

  it("renders net_transfers with locale grouping and no decimal point (R28)", async () => {
    mockFetchOnce(official);
    renderPrices();

    const row = (await screen.findByText("De Cuyper")).closest("tr")!;
    expect(within(row).getByText("253,865")).toBeInTheDocument();
  });

  it("falls back net_transfers to zero when absent", async () => {
    const modified: Watchlist = {
      ...official,
      risers: [{ ...official.risers[0], net_transfers: null }],
    };
    mockFetchOnce(modified);
    renderPrices();

    const row = (await screen.findByText("De Cuyper")).closest("tr")!;
    expect(within(row).getByText("0")).toBeInTheDocument();
  });

  it("renders distinguishable riser and faller icons that never cross tables", async () => {
    mockFetchOnce(official);
    renderPrices();
    await screen.findByText("De Cuyper");

    const risersTable = screen.getByRole("table", { name: "Likely risers" });
    const fallersTable = screen.getByRole("table", { name: "Likely fallers" });

    expect(risersTable.querySelectorAll(".lucide-trending-up").length).toBeGreaterThan(0);
    expect(risersTable.querySelectorAll(".lucide-trending-down")).toHaveLength(0);
    expect(fallersTable.querySelectorAll(".lucide-trending-down").length).toBeGreaterThan(0);
    expect(fallersTable.querySelectorAll(".lucide-trending-up")).toHaveLength(0);
  });

  it("renders 'Nothing flagged right now' for an empty risers table while fallers still render", async () => {
    mockFetchOnce({ ...official, risers: [] });
    renderPrices();

    expect(await screen.findByText("Nothing flagged right now")).toBeInTheDocument();
    expect(screen.getByText("Wood")).toBeInTheDocument();
  });

  it("has no interactive column headers in either table — not sortable", async () => {
    mockFetchOnce(official);
    renderPrices();
    await screen.findByText("De Cuyper");

    const risersTable = screen.getByRole("table", { name: "Likely risers" });
    const fallersTable = screen.getByRole("table", { name: "Likely fallers" });
    expect(within(risersTable).queryAllByRole("button")).toHaveLength(0);
    expect(within(fallersTable).queryAllByRole("button")).toHaveLength(0);
  });

  it("sets document.title for the /prices route", async () => {
    mockFetchOnce(official);
    renderPrices();
    await screen.findByText("De Cuyper");
    expect(document.title).toBe("Price watch — FPL ML");
  });

  it("renders ErrorState naming the price watch data on a failed fetch", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
    ) as unknown as typeof fetch;
    renderPrices();

    expect(await screen.findByText(/the price watch data/)).toBeInTheDocument();
  });
});
