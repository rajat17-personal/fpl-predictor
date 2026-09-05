import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import League from "./League";
import standingsData from "../test/fixtures/standings.json";
import leadersData from "../test/fixtures/leaders.json";
import type { LeadersBoards, StandingsRow } from "../lib/api";

const standings = standingsData as StandingsRow[];
const leaders = leadersData as unknown as LeadersBoards;

function mockFetchByUrl(responses: Record<string, unknown>) {
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const body = responses[url];
    if (body === undefined) {
      return Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({}),
      }) as unknown as Promise<Response>;
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    }) as unknown as Promise<Response>;
  }) as unknown as typeof fetch;
}

function renderLeague() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/league"]}>
      <QueryClientProvider client={queryClient}>
        <League />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("League (ported from web/league.html, verified 2026-09-01)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders rank cells 1, 2, 3, 4 for a four-row fixture with no rank field (R32)", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();

    const table = await screen.findByRole("table");
    const rankCells = within(table)
      .getAllByRole("row")
      .slice(1) // skip header row
      .map((row) => within(row).getAllByRole("cell")[0].textContent);
    expect(rankCells).toEqual(["1", "2", "3", "4"]);
  });

  it("renders the goal-difference cells +7, +4, 0 and -3 for source values 7, 4, 0 and -3 (R33)", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();

    const table = await screen.findByRole("table");
    const gdCells = within(table)
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("cell")[8].textContent);
    expect(gdCells).toEqual(["+7", "+4", "0", "-3"]);
  });

  it("renders exactly five board headings, in order, with the exact documented strings (R34)", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();

    const headings = (
      await screen.findAllByRole("heading", { level: 3 })
    ).map((h) => h.textContent);
    expect(headings).toEqual([
      "Most FPL points",
      "Most goals",
      "Most assists",
      "Clean sheets (GK/DEF)",
      "Most cards",
    ]);
  });

  it("renders exactly eight list items for a board whose source array holds ten entries", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();

    const heading = await screen.findByRole("heading", { name: "Most FPL points" });
    const board = heading.closest("div")!;
    expect(within(board).getAllByRole("listitem")).toHaveLength(8);
  });

  it("renders 'Nothing yet this season' for an empty board array", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();

    const heading = await screen.findByRole("heading", { name: "Most goals" });
    const board = heading.closest("div")!;
    expect(within(board).getByText("Nothing yet this season")).toBeInTheDocument();
  });

  it("renders 'Nothing yet this season' for an entirely missing board key, without throwing", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();

    const heading = await screen.findByRole("heading", { name: "Most assists" });
    const board = heading.closest("div")!;
    expect(within(board).getByText("Nothing yet this season")).toBeInTheDocument();
  });

  it("has no interactive column headers in the standings table — not sortable", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();

    const table = await screen.findByRole("table");
    expect(within(table).queryAllByRole("button")).toHaveLength(0);
  });

  it("renders the shared EmptyState for a zero-row standings response", async () => {
    mockFetchByUrl({
      "/data/standings.json": [],
      "/data/leaders.json": leaders,
    });
    renderLeague();

    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
  });

  it("renders ErrorState naming the league data on a failed fetch", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
    ) as unknown as typeof fetch;
    renderLeague();

    expect(await screen.findByText(/the league data/)).toBeInTheDocument();
  });

  it("sets document.title for the /league route", async () => {
    mockFetchByUrl({
      "/data/standings.json": standings,
      "/data/leaders.json": leaders,
    });
    renderLeague();
    await screen.findByRole("table");
    expect(document.title).toBe("League table & leaders — FPL ML");
  });
});
