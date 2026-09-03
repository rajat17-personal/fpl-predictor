import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Team from "./Team";
import squadFixture from "../test/fixtures/squad.json";
import xpFixture from "../test/fixtures/xp_table_squad.json";
import metaFixture from "../test/fixtures/meta.json";
import teamResponseFixture from "../test/fixtures/team_response.json";

const FIXTURES: Record<string, unknown> = {
  "/data/squad.json": squadFixture,
  "/data/xp_table.json": xpFixture,
  "/data/meta.json": metaFixture,
  "/api/team/6980093": teamResponseFixture,
};

function mockFetchByUrl(overrides: Record<string, unknown> = {}) {
  const body = { ...FIXTURES, ...overrides };
  const calls: string[] = [];
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    calls.push(url);
    const path = Object.keys(body).find((key) => url.endsWith(key));
    if (!path) {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(body[path]),
    });
  }) as unknown as typeof fetch;
  return calls;
}

function renderTeam(initialEntry = "/team") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <QueryClientProvider client={queryClient}>
        <Team />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Team (03-02 Task 1: three-tab shell + URL state + load flow)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders exactly three tabs with the expected accessible names, Squad selected by default", async () => {
    mockFetchByUrl();
    renderTeam();

    await screen.findByText("Virgil");
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(3);
    expect(tabs.map((t) => t.textContent)).toEqual(["Squad", "Rate my team", "Chips"]);
    expect(screen.getByRole("tab", { name: "Squad" })).toHaveAttribute("aria-selected", "true");
  });

  it("fires zero requests to any /api/ endpoint when arriving at /team with no query string", async () => {
    const calls = mockFetchByUrl();
    renderTeam();

    await screen.findByText("Virgil");
    expect(calls.some((url) => url.includes("/api/"))).toBe(false);
  });

  it("opens the Chips panel at /team?tab=chips, with Squad's tab aria-selected false", async () => {
    mockFetchByUrl();
    renderTeam("/team?tab=chips");

    const chipsTab = screen.getByRole("tab", { name: "Chips" });
    expect(chipsTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Squad" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tabpanel")).toHaveAttribute("id", "team-panel-chips");
  });

  it("fires exactly one /api/team/6980093 request with no user interaction at /team?entry=6980093", async () => {
    const calls = mockFetchByUrl();
    renderTeam("/team?entry=6980093");

    await screen.findByText("The Testers · GW3");
    const apiCalls = calls.filter((url) => url.includes("/api/"));
    expect(apiCalls).toHaveLength(1);
    expect(apiCalls[0]).toContain("/api/team/6980093");
  });

  it("clicking Load team with an empty input fires zero requests", async () => {
    const calls = mockFetchByUrl();
    renderTeam();

    await screen.findByText("Virgil");
    calls.length = 0;
    fireEvent.click(screen.getByRole("button", { name: "Load team" }));

    expect(calls).toHaveLength(0);
  });

  it("renders 'Couldn't load that team:' with 'Check the ID and try again.' on a rejected /api/team request", async () => {
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/team/")) {
        return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
      }
      const path = Object.keys(FIXTURES).find((key) => url.endsWith(key));
      if (!path) {
        return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(FIXTURES[path]) });
    }) as unknown as typeof fetch;
    renderTeam("/team?entry=6980093");

    expect(await screen.findByText(/Couldn't load that team:/)).toBeInTheDocument();
    expect(screen.getByText(/Check the ID and try again\./)).toBeInTheDocument();
  });

  it("renders the Model squad banner with no entry, and the loaded team's banner after a successful load", async () => {
    mockFetchByUrl();
    renderTeam();

    expect(await screen.findByText("Model squad · GW3")).toBeInTheDocument();

    renderTeam("/team?entry=6980093");
    expect(await screen.findByText("The Testers · GW3")).toBeInTheDocument();
  });

  it("normalises the loaded squad to exactly 11 starters, exactly 1 GK among them, and exactly 1 captain", async () => {
    mockFetchByUrl();
    renderTeam("/team?entry=6980093");

    await screen.findByText("The Testers · GW3");

    // Computed offline against team_response.json + xp_table_squad.json:
    // the max-xp legal split is DEF4/MID4/FWD2, leaving exactly these 4 on
    // the bench (1 GK + 1 DEF + 1 MID + 1 FWD) — 15 picks - 4 bench = 11
    // starters, and exactly one of the two GK picks starts.
    const bench = screen.getByTestId("bench");
    for (const name of ["Tzolakis", "Egan", "McBurnie", "Unmapped"]) {
      expect(within(bench).getByText(name)).toBeInTheDocument();
    }
    expect(within(bench).queryByText("Kelleher")).not.toBeInTheDocument();
    expect(teamResponseFixture.picks).toHaveLength(15);

    expect(screen.getAllByLabelText("Captain")).toHaveLength(1);
  });

  it("keeps a pick whose player_code is missing from the xp fixture on the bench, not among the starters", async () => {
    mockFetchByUrl();
    renderTeam("/team?entry=6980093");

    await screen.findByText("The Testers · GW3");
    const bench = screen.getByTestId("bench");
    expect(within(bench).getByText("Unmapped")).toBeInTheDocument();
  });

  // 03-01's original Task 1 assertions — must keep passing after the
  // extraction of this content into SquadTab.
  it("renders all 15 fixture player names, with exactly 4 inside the bench container", async () => {
    mockFetchByUrl();
    renderTeam();

    await screen.findByText("Virgil");

    const squadNames = (squadFixture as { squad: { name: string }[] }).squad.map((r) => r.name);
    for (const name of squadNames) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }

    const bench = screen.getByTestId("bench");
    const benchFixtureNames = (squadFixture as { squad: { name: string; starting: boolean }[] })
      .squad.filter((r) => !r.starting)
      .map((r) => r.name);
    expect(benchFixtureNames).toHaveLength(4);
    for (const name of benchFixtureNames) {
      expect(within(bench).getByText(name)).toBeInTheDocument();
    }
  });

  it("renders the formation label matching the fixture's own formation value", async () => {
    mockFetchByUrl();
    renderTeam();

    await screen.findByText("Virgil");
    const expected = (squadFixture as { formation: string }).formation;
    expect(screen.getByText(expected)).toBeInTheDocument();
    expect(expected).toBe("3-5-2");
  });

  it("sets document.title for the /team route", async () => {
    mockFetchByUrl();
    renderTeam();
    await screen.findByText("Virgil");
    expect(document.title).toBe("My team — FPL ML");
  });

  it("renders the EmptyState rather than throwing for a zero-row squad payload", async () => {
    mockFetchByUrl({
      "/data/squad.json": { ...(squadFixture as object), squad: [] },
    });
    renderTeam();

    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
  });

  it("renders ErrorState naming the team data on a failed fetch", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
    ) as unknown as typeof fetch;
    renderTeam();

    expect(await screen.findByText(/the team data/)).toBeInTheDocument();
  });
});
