import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Team from "./Team";
import squadFixture from "../test/fixtures/squad.json";
import xpFixture from "../test/fixtures/xp_table_squad.json";
import metaFixture from "../test/fixtures/meta.json";

const FIXTURES: Record<string, unknown> = {
  "/data/squad.json": squadFixture,
  "/data/xp_table.json": xpFixture,
  "/data/meta.json": metaFixture,
};

function mockFetchByUrl(overrides: Record<string, unknown> = {}) {
  const body = { ...FIXTURES, ...overrides };
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
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
}

function renderTeam() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/team"]}>
      <QueryClientProvider client={queryClient}>
        <Team />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Team (03-01 Task 1: end-to-end model squad pitch)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

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

  it("renders the Model squad banner with the meta GW number", async () => {
    mockFetchByUrl();
    renderTeam();

    expect(await screen.findByText("Model squad · GW3")).toBeInTheDocument();
  });

  it("sets document.title for the /team route", async () => {
    mockFetchByUrl();
    renderTeam();
    await screen.findByText("Virgil");
    expect(document.title).toBe("Rate my team — FPL ML");
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
