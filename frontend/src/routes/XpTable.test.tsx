import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import XpTable from "./XpTable";
import fixtureRows from "../test/fixtures/xp_table.json";
import captainsFixture from "../test/fixtures/captains.json";
import type { CaptainRow, XpRow } from "../lib/api";

const rows = fixtureRows as XpRow[];
const captainsRows = captainsFixture as CaptainRow[];

/* The route fires two concurrent queries (xp_table.json, captains.json);
 * TanStack Query does not guarantee which fires first, so the mock must
 * route by URL rather than call order. `xpTableBody` covers the tests this
 * file is actually about; `captainsBody` defaults to an empty array so
 * tests that don't care about the Captain picks sub-table neither crash
 * (a null xp_capt in an xp_table row would break the captains-specific
 * un-guarded `.toFixed()`, R19, if the same body were reused for both
 * fetches) nor introduce player-name collisions with the main table. Tests
 * that DO exercise the sub-table pass the real captains fixture explicitly. */
function mockFetchOnce(xpTableBody: unknown, captainsBody: unknown = []) {
  globalThis.fetch = vi.fn((path: string) => {
    const body = path === "/data/captains.json" ? captainsBody : xpTableBody;
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body),
    });
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

/* Scoped to the main xP table (by its accessible name) so the Captain picks
 * sub-table's rows never leak into these assertions. Returns [] when the
 * main table isn't rendered at all (the "No players match" zero-match
 * state). */
function bodyRowNames() {
  const table = screen.queryByRole("table", { name: "xP table" });
  if (!table) {
    return [];
  }
  return within(table)
    .queryAllByRole("row")
    .slice(1) // drop the header row
    .map((row) => {
      const nameCell = within(row).getAllByRole("cell")[1];
      // The name cell's first child is the plain name text node; a second
      // child (the mounted StatusFlag) only appears for flagged rows, so
      // .textContent alone would append its glyph (e.g. "Saka✕").
      return nameCell?.childNodes[0]?.textContent ?? null;
    });
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

describe("XpTable (Task 3 — status flag + captain picks)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("mounts a StatusFlag for a flagged player and none for an available one", async () => {
    // Explicit captainsRows here — this test cares about name overlap
    // between the two tables, so both fetches carry real fixture data.
    mockFetchOnce(rows, captainsRows);
    renderXpTable();
    const table = await screen.findByRole("table", { name: "xP table" });

    // Saka: status "i" -> flag with accessible name "unavailable"
    const sakaRow = within(table).getByText("Saka").closest("tr")!;
    expect(within(sakaRow).getByRole("button", { name: "unavailable" })).toBeInTheDocument();

    // Haaland: status "a" -> no flag element at all
    const haalandRow = within(table).getByText("Haaland").closest("tr")!;
    expect(
      within(haalandRow).queryByRole("button", { name: /unavailable|doubtful/ }),
    ).not.toBeInTheDocument();
  });

  it("renders exactly 5 captain rows from a 7-row source, using the full team name", async () => {
    mockFetchOnce(rows, captainsRows);
    renderXpTable();
    await screen.findByRole("table", { name: "xP table" });

    const captainsTable = await screen.findByRole("table", { name: "Captain picks" });
    const captainRows = within(captainsTable).getAllByRole("row").slice(1);
    expect(captainRows).toHaveLength(5);

    // Full club name (not team_short) distinguishes this table from the main one.
    expect(within(captainsTable).getByText("Man City")).toBeInTheDocument();
    expect(within(captainsTable).queryByText("MCI")).not.toBeInTheDocument();

    // Palmer is the 7th fixture row — outside the slice(0, 5).
    expect(within(captainsTable).queryByText("Palmer")).not.toBeInTheDocument();
  });

  it("does not apply the main table's en-dash fallback to a captains row with null ownership", async () => {
    mockFetchOnce(rows, captainsRows);
    renderXpTable();
    await screen.findByRole("table", { name: "xP table" });

    const captainsTable = await screen.findByRole("table", { name: "Captain picks" });
    const salahRow = within(captainsTable).getByText("Salah").closest("tr")!;
    expect(within(salahRow).queryByText("–")).not.toBeInTheDocument();
  });
});
