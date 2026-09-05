import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Scoreboard from "./Scoreboard";
import scoreboardData from "../test/fixtures/scoreboard.json";
import type { ScoreboardResponse } from "../lib/api";

const board = scoreboardData as ScoreboardResponse;

function mockFetch(status: number, body: unknown) {
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    }),
  ) as unknown as typeof fetch;
}

function mockFetchReject() {
  globalThis.fetch = vi.fn(() =>
    Promise.reject(new Error("network failure")),
  ) as unknown as typeof fetch;
}

function renderScoreboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/scoreboard"]}>
      <QueryClientProvider client={queryClient}>
        <Scoreboard />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Scoreboard (ported from web/scoreboard.html, verified 2026-09-01)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stubs a 404 and renders the pre-season zero-state, not an error", async () => {
    mockFetch(404, {});
    renderScoreboard();

    expect(await screen.findByText("Seasons validated")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("stubs a 500 and renders the Retry control while the backtest tile text is absent", async () => {
    mockFetch(500, {});
    renderScoreboard();

    expect(await screen.findByRole("button", { name: /retry/i })).toBeInTheDocument();
    expect(screen.queryByText("Seasons validated")).not.toBeInTheDocument();
  });

  it("renders ErrorState on a rejected fetch (network failure)", async () => {
    mockFetchReject();
    renderScoreboard();

    expect(await screen.findByText(/the scoreboard data/)).toBeInTheDocument();
  });

  it("renders the zero-state and no history table for a 200 with an empty entries array", async () => {
    mockFetch(200, { entries: [], summary: {} });
    renderScoreboard();

    expect(await screen.findByText("Seasons validated")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("renders the rendered gameweek column values, in DOM order, equal to the source entries order", async () => {
    mockFetch(200, board);
    renderScoreboard();

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    const gwCells = rows.map((row) => within(row).getAllByRole("cell")[0].textContent);
    expect(gwCells).toEqual(board.entries.map((e) => String(e.gw)));
  });

  it("renders the en-dash for an entry's null mae_fpl while mae_model still shows a number", async () => {
    mockFetch(200, board);
    renderScoreboard();

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    const gw1Row = rows[0]; // entries[0].gw === 1, has mae_fpl: null
    const cells = within(gw1Row).getAllByRole("cell");
    expect(cells[1].textContent).toBe("0.81"); // MAE (us)
    expect(cells[2].textContent).toBe("–"); // MAE (FPL)
  });

  it("renders the en-dash for an entry's null spearman_fpl in that cell only", async () => {
    mockFetch(200, board);
    renderScoreboard();

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    const gw2Row = rows[1]; // entries[1].gw === 2, has spearman_fpl: null
    const cells = within(gw2Row).getAllByRole("cell");
    expect(cells[3].textContent).toBe("0.73"); // Rank corr (us)
    expect(cells[4].textContent).toBe("–"); // Rank corr (FPL)
  });

  it("renders the MAE tile en-dash for a null summary mae_fpl while still showing summary.mae_model", async () => {
    mockFetch(200, board);
    renderScoreboard();

    const maeTile = (await screen.findByText("MAE — points error")).closest("div")!;
    expect(within(maeTile).getByText(/0.79/)).toBeInTheDocument();
    expect(within(maeTile).getByText(/–/)).toBeInTheDocument();
  });

  it("renders four populated tiles: Gameweeks scored, MAE, Rank correlation, Captain average", async () => {
    mockFetch(200, board);
    renderScoreboard();

    expect(await screen.findByText("Gameweeks scored")).toBeInTheDocument();
    expect(screen.getByText("MAE — points error")).toBeInTheDocument();
    expect(screen.getByText("Rank correlation")).toBeInTheDocument();
    expect(screen.getByText("Captain average")).toBeInTheDocument();
  });

  it("sets document.title for the /scoreboard route", async () => {
    mockFetch(200, board);
    renderScoreboard();
    await screen.findByRole("table");
    expect(document.title).toBe("Accuracy scoreboard — FPL ML");
  });
});
