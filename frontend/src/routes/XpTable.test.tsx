import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import XpTable from "./XpTable";
import fixtureRows from "../test/fixtures/xp_table.json";
import type { XpRow } from "../lib/api";

const rows = fixtureRows as XpRow[];

function mockFetchOnce(body: unknown, ok = true) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: () => Promise.resolve(body),
  }) as unknown as typeof fetch;
}

function renderXpTable() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <QueryClientProvider client={queryClient}>
        <XpTable />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function bodyRowNames() {
  return screen
    .getAllByRole("row")
    .slice(1) // drop the header row
    .map((row) => within(row).getAllByRole("cell")[1]?.textContent);
}

describe("XpTable (Task 1 — end-to-end slice)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders known-row cell text with vanilla number formats, including – fallbacks", async () => {
    mockFetchOnce(rows);
    renderXpTable();

    expect(await screen.findByText("Haaland")).toBeInTheDocument();
    const haalandRow = screen.getByText("Haaland").closest("tr")!;
    expect(within(haalandRow).getByText("15.5")).toBeInTheDocument();
    expect(within(haalandRow).getByText("69.5")).toBeInTheDocument();
    expect(within(haalandRow).getByText("12.30")).toBeInTheDocument();

    // Salah: ownership null -> en-dash fallback (R15)
    const salahRow = screen.getByText("Salah").closest("tr")!;
    expect(within(salahRow).getByText("–")).toBeInTheDocument();

    // B.Fernandes: xp_capt null -> en-dash fallback (R16)
    const fernandesRow = screen.getByText("B.Fernandes").closest("tr")!;
    expect(within(fernandesRow).getByText("–")).toBeInTheDocument();
  });

  it("renders the band tooltip text verbatim", async () => {
    mockFetchOnce(rows);
    renderXpTable();

    await screen.findByText("Haaland");
    expect(
      screen.getByTitle(
        "xP 8.20 — actual score lands between 5.1 and 14.2 in 8 gameweeks out of 10",
      ),
    ).toBeInTheDocument();
  });

  it("clicking the £m header once sorts ascending with ▼, clicking again sorts descending with ▲", async () => {
    mockFetchOnce(rows);
    renderXpTable();

    await screen.findByText("Haaland");
    const header = screen.getByRole("button", { name: /£m/ });

    fireEvent.click(header);
    expect(bodyRowNames()[0]).toBe("Gabriel"); // price_m 6.0, lowest
    expect(header).toHaveTextContent("▼");

    fireEvent.click(header);
    expect(bodyRowNames()[0]).toBe("Haaland"); // price_m 15.5, highest
    expect(header).toHaveTextContent("▲");
  });

  it("renders exactly 50 rows from a 51-row source, sliced not padded", async () => {
    const base = rows[0];
    const many: XpRow[] = Array.from({ length: 51 }, (_, i) => ({
      ...base,
      player_code: 200000 + i,
      player_id: 200000 + i,
      name: `Player ${i}`,
      xp: 51 - i,
    }));
    mockFetchOnce(many);
    renderXpTable();

    await screen.findByText("Player 0");
    expect(bodyRowNames()).toHaveLength(50);
    expect(screen.queryByText("Player 50")).not.toBeInTheDocument();
  });

  it("renders the fetched array in source order before any header is clicked (no re-sort before slicing)", async () => {
    const misordered: XpRow[] = [...rows].reverse();
    mockFetchOnce(misordered);
    renderXpTable();

    await screen.findByText(misordered[0].name);
    expect(bodyRowNames()).toEqual(misordered.map((r) => r.name));
  });

  it("renders the EmptyState heading for a zero-row source", async () => {
    mockFetchOnce([]);
    renderXpTable();

    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
  });
});

describe("XpTable (Task 2 — filters, verbatim copy, page meta)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("DEF chip filters to only DEF rows, carries aria-pressed, and ALL restores every sliced row", async () => {
    mockFetchOnce(rows);
    renderXpTable();
    await screen.findByText("Haaland");

    fireEvent.click(screen.getByRole("button", { name: "DEF" }));
    expect(bodyRowNames()).toEqual(["Gabriel"]);
    expect(screen.getByRole("button", { name: "DEF" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(screen.getByRole("button", { name: "All" }));
    expect(bodyRowNames()).toHaveLength(6);
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
  });

  it("composes the DEF chip and a trimmed search term with AND", async () => {
    mockFetchOnce(rows);
    renderXpTable();
    await screen.findByText("Haaland");

    fireEvent.click(screen.getByRole("button", { name: "DEF" }));
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "  gab  " } });
    expect(bodyRowNames()).toEqual(["Gabriel"]);

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "  mun  " } });
    expect(bodyRowNames()).toEqual([]);
  });

  it("search matches the full team name even though it is never rendered in any cell", async () => {
    mockFetchOnce(rows);
    renderXpTable();
    await screen.findByText("Haaland");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "villa" } });
    expect(bodyRowNames()).toEqual(["Watkins"]);
  });

  it("shows 'No players match' — not the generic empty state — for a zero-match filter", async () => {
    mockFetchOnce(rows);
    renderXpTable();
    await screen.findByText("Haaland");

    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "zzz-no-such-player" },
    });
    expect(screen.getByText("No players match")).toBeInTheDocument();
    expect(screen.queryByText("Nothing here yet")).not.toBeInTheDocument();
  });

  it("never lets a search reach past the top-50 slice, even from a 60-row source", async () => {
    const base = rows[0];
    const many: XpRow[] = Array.from({ length: 60 }, (_, i) => ({
      ...base,
      player_code: 300000 + i,
      player_id: 300000 + i,
      name: `Row${i}`,
      xp: 60 - i,
    }));
    mockFetchOnce(many);
    renderXpTable();
    await screen.findByText("Row0");

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "row59" } });
    expect(screen.getByText("No players match")).toBeInTheDocument();
  });

  it("sets document.title for the '/' route", async () => {
    mockFetchOnce(rows);
    renderXpTable();
    await screen.findByText("Haaland");
    expect(document.title).toBe("FPL ML — expected points, honestly measured");
  });

  it("renders the verbatim top-50 free-preview note", async () => {
    mockFetchOnce(rows);
    renderXpTable();
    expect(await screen.findByText(/Showing the top 50 by xP/)).toBeInTheDocument();
  });

  it("renders no vanilla .html href", async () => {
    mockFetchOnce(rows);
    renderXpTable();
    await screen.findByText("Haaland");
    const links = screen.getAllByRole("link");
    for (const link of links) {
      expect(link.getAttribute("href")).not.toMatch(/\.html$/);
    }
  });
});
