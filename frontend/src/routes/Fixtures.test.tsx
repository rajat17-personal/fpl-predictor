import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Fixtures from "./Fixtures";
import fixtureData from "../test/fixtures/fixtures.json";
import type { FixtureTickerTeam } from "../lib/api";

const rows = fixtureData as FixtureTickerTeam[];

function mockFetchOnce(body: unknown) {
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    }),
  ) as unknown as typeof fetch;
}

function renderFixtures() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/fixtures"]}>
      <QueryClientProvider client={queryClient}>
        <Fixtures />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Fixtures (ported from web/fixtures.html, verified 2026-09-01)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders exactly four gameweek column headers, proving the count is data-derived (R20)", async () => {
    mockFetchOnce(rows);
    renderFixtures();

    const headers = await screen.findAllByRole("columnheader");
    const gwHeaders = headers.filter((h) => /^GW\d+$/.test(h.textContent ?? ""));
    expect(gwHeaders).toHaveLength(4);
  });

  it("renders the blank-gameweek cell as an em dash with accessible description 'Blank gameweek' (R21)", async () => {
    mockFetchOnce(rows);
    renderFixtures();
    await screen.findByText("Arsenal");

    const blankCell = screen.getByLabelText("Blank gameweek");
    expect(blankCell).toHaveTextContent("—");
  });

  it("renders the home and away fixture descriptions verbatim (R22)", async () => {
    mockFetchOnce(rows);
    renderFixtures();
    await screen.findByText("Arsenal");

    expect(screen.getByLabelText("Home vs MCI, difficulty 5")).toBeInTheDocument();
    expect(screen.getByLabelText("Away vs LIV, difficulty 4")).toBeInTheDocument();
  });

  it("renders both fixtures of a double gameweek in one cell", async () => {
    mockFetchOnce(rows);
    renderFixtures();
    await screen.findByText("Liverpool");

    expect(screen.getByLabelText("Home vs TOT, difficulty 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Away vs WOL, difficulty 2")).toBeInTheDocument();
  });

  it("collects a distinct background class at every difficulty 1 through 5", async () => {
    mockFetchOnce(rows);
    renderFixtures();
    await screen.findByText("Arsenal");

    const classes = [1, 2, 3, 4, 5].map((fdr) => {
      const el = document.querySelector(`[aria-label*="difficulty ${fdr}"]`);
      expect(el).not.toBeNull();
      return el!.className;
    });
    expect(new Set(classes).size).toBe(5);
  });

  it("renders a null xg_next as an en-dash while ease has no fallback (R23, R24)", async () => {
    mockFetchOnce(rows);
    renderFixtures();

    const cheRow = (await screen.findByText("Chelsea")).closest("tr")!;
    expect(within(cheRow).getByText("–")).toBeInTheDocument();
    expect(within(cheRow).getByText("2.00")).toBeInTheDocument();
  });

  it("has no interactive column headers — the table is not sortable", async () => {
    mockFetchOnce(rows);
    renderFixtures();

    const table = await screen.findByRole("table");
    expect(within(table).queryAllByRole("button")).toHaveLength(0);
  });

  it("renders the verbatim legend row", async () => {
    mockFetchOnce(rows);
    renderFixtures();
    await screen.findByText("Arsenal");

    expect(screen.getByText("Easy")).toBeInTheDocument();
    expect(screen.getByText("Hard")).toBeInTheDocument();
    expect(screen.getByText("— = blank gameweek")).toBeInTheDocument();
    for (const n of ["1", "2", "3", "4", "5"]) {
      expect(screen.getAllByText(n).length).toBeGreaterThan(0);
    }
  });

  it("renders the EmptyState for a zero-row response", async () => {
    mockFetchOnce([]);
    renderFixtures();

    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
  });

  it("renders ErrorState naming the fixture data on a failed fetch", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
    ) as unknown as typeof fetch;
    renderFixtures();

    expect(await screen.findByText(/the fixture data/)).toBeInTheDocument();
  });

  it("sets document.title for the /fixtures route", async () => {
    mockFetchOnce(rows);
    renderFixtures();
    await screen.findByText("Arsenal");
    expect(document.title).toBe("Fixture ticker — FPL ML");
  });

  // UAT gap G-02-2: the tight cell padding and the two-line stacked chip are
  // two halves of one vanilla design (web/assets/style.css:154 `.cellpad`)
  // — restoring the chip without the padding grows the table by roughly
  // 275px across twenty clubs.
  it("gives gameweek cells vanilla's tight fixture-specific padding", async () => {
    mockFetchOnce(rows);
    renderFixtures();
    await screen.findByText("Arsenal");

    const chip = screen.getByLabelText("Home vs MCI, difficulty 5");
    const cell = chip.closest("td")!;
    expect(cell.className).toContain("py-[3px]");
  });
});
