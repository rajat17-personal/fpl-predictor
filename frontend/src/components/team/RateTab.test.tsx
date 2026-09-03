import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RateTab } from "./RateTab";
import Team from "../../routes/Team";
import rateFixture from "../../test/fixtures/rate_response.json";
import squadFixture from "../../test/fixtures/squad.json";
import xpFixture from "../../test/fixtures/xp_table_squad.json";
import metaFixture from "../../test/fixtures/meta.json";
import teamResponseFixture from "../../test/fixtures/team_response.json";

function renderRateTab(entry: number | null) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <RateTab entry={entry} />
    </QueryClientProvider>,
  );
}

describe("RateTab (03-02 Task 3)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the four tile headings exactly", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(rateFixture) }),
    ) as unknown as typeof fetch;
    renderRateTab(6980093);

    expect(await screen.findByText("Team score")).toBeInTheDocument();
    expect(screen.getByText("Season so far")).toBeInTheDocument();
    expect(screen.getByText("Captain")).toBeInTheDocument();
    expect(screen.getByText("Best move")).toBeInTheDocument();
  });

  it("shows the 8/10 GWs range clause when xi_p10 is non-null", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(rateFixture) }),
    ) as unknown as typeof fetch;
    renderRateTab(6980093);

    await screen.findByText("Team score");
    expect(screen.getByText(/in 8\/10 GWs/)).toBeInTheDocument();
  });

  it("omits the range clause entirely when xi_p10 is null — no '8/10 GWs' and no '–' range", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ...rateFixture, xi_p10: null, xi_p90: null }),
      }),
    ) as unknown as typeof fetch;
    renderRateTab(6980093);

    await screen.findByText("Team score");
    const scoreTile = screen.getByText("Team score").closest("div") as HTMLElement;
    expect(within(scoreTile).queryByText(/8\/10 GWs/)).not.toBeInTheDocument();
    expect(scoreTile.textContent).not.toMatch(/\d+(\.\d+)?–\d+(\.\d+)?/);
  });

  it("renders Hold and the no-improving-transfer detail when best_move is null", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ...rateFixture, best_move: null }),
      }),
    ) as unknown as typeof fetch;
    renderRateTab(6980093);

    await screen.findByText("Team score");
    expect(screen.getByText("Hold")).toBeInTheDocument();
    expect(screen.getByText("no single transfer beats your current squad")).toBeInTheDocument();
  });

  it("renders an en dash for a null overall_rank rather than the string 'null'", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            ...rateFixture,
            manager: { ...rateFixture.manager, overall_rank: null },
          }),
      }),
    ) as unknown as typeof fetch;
    renderRateTab(6980093);

    await screen.findByText("Season so far");
    const detail = screen.getByText(/overall rank/);
    expect(detail.textContent).toContain("–");
    expect(detail.textContent).not.toContain("null");
  });

  it("renders exactly 'Solving your squad…' while the request is in flight", () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch;
    renderRateTab(6980093);

    expect(screen.getByText("Solving your squad…")).toBeInTheDocument();
  });

  it("renders the Couldn't-rate error copy on a rejected request", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "entry 6980093: no picks for GW2" }),
      }),
    ) as unknown as typeof fetch;
    renderRateTab(6980093);

    expect(await screen.findByText(/Couldn't rate that team:/)).toBeInTheDocument();
    expect(screen.getByText(/Check the ID and try again\./)).toBeInTheDocument();
  });

  it("does not fetch when no entry is loaded", () => {
    const fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    renderRateTab(null);

    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("RateTab lazy-fetch integration (03-02 Task 3: D-20 on-demand)", () => {
  const FIXTURES: Record<string, unknown> = {
    "/data/squad.json": squadFixture,
    "/data/xp_table.json": xpFixture,
    "/data/meta.json": metaFixture,
    "/api/team/6980093": teamResponseFixture,
    "/api/rate/6980093": rateFixture,
  };

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fires zero /api/rate/ requests on the Squad tab, exactly one after switching to Rate", async () => {
    const calls: string[] = [];
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      calls.push(url);
      const path = Object.keys(FIXTURES).find((key) => url.endsWith(key));
      if (!path) {
        return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(FIXTURES[path]) });
    }) as unknown as typeof fetch;

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter initialEntries={["/team?entry=6980093"]}>
        <QueryClientProvider client={queryClient}>
          <Team />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await screen.findByText("The Testers · GW3");
    expect(calls.some((url) => url.includes("/api/rate/"))).toBe(false);

    fireEvent.click(screen.getByRole("tab", { name: "Rate my team" }));
    await screen.findByText("Team score");

    const rateCalls = calls.filter((url) => url.includes("/api/rate/"));
    expect(rateCalls).toHaveLength(1);
  });
});
