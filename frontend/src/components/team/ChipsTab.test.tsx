import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, within, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ChipsTab } from "./ChipsTab";
import metaFixture from "../../test/fixtures/meta.json";
import chipsFixture from "../../test/fixtures/chips.json";
import chipsDgwFixture from "../../test/fixtures/chips_dgw.json";

const FIXTURES: Record<string, unknown> = {
  "/data/meta.json": metaFixture,
  "/data/chips.json": chipsFixture,
};

function mockFetchByUrl(overrides: Record<string, unknown> = {}) {
  const body = { ...FIXTURES, ...overrides };
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const path = Object.keys(body).find((key) => url.endsWith(key));
    if (!path) {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body[path]) });
  }) as unknown as typeof fetch;
}

function renderChipsTab() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ChipsTab />
    </QueryClientProvider>,
  );
}

describe("ChipsTab (03-02 Task 2)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the heading, sub, and Why GW{n} callout with the note verbatim", async () => {
    mockFetchByUrl();
    renderChipsTab();

    expect(await screen.findByText("Chip timing")).toBeInTheDocument();
    expect(screen.getByText("When to play your chips this season, and why.")).toBeInTheDocument();
    expect(screen.getByText("Why GW3")).toBeInTheDocument();
    expect(screen.getByText(chipsFixture.note)).toBeInTheDocument();
  });

  it("renders the timeline (all-zero live data) with no error/empty state", async () => {
    mockFetchByUrl();
    renderChipsTab();

    await screen.findByTestId("chip-timeline");
    expect(screen.queryByText("Nothing here yet")).not.toBeInTheDocument();
  });

  it("renders EmptyState and no timeline for an empty structure array", async () => {
    mockFetchByUrl({ "/data/chips.json": { note: "No chip data yet.", structure: [] } });
    renderChipsTab();

    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
    expect(screen.queryByTestId("chip-timeline")).not.toBeInTheDocument();
  });

  it("renders ErrorState with a working Retry on a rejected chips fetch", async () => {
    let chipsCallCount = 0;
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/data/meta.json")) {
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(metaFixture) });
      }
      chipsCallCount += 1;
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
    }) as unknown as typeof fetch;
    renderChipsTab();

    expect(await screen.findByText(/the chip timing data/)).toBeInTheDocument();
    const callsBeforeRetry = chipsCallCount;
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(chipsCallCount).toBeGreaterThan(callsBeforeRetry));
  });

  it("marks exactly the DGW/BGW gameweeks using a hand-built fixture with non-zero counts", async () => {
    mockFetchByUrl({ "/data/chips.json": chipsDgwFixture });
    renderChipsTab();

    await screen.findByTestId("chip-timeline");
    expect(within(screen.getByTestId("gw-marker-5")).getByText("DGW")).toBeInTheDocument();
    expect(within(screen.getByTestId("gw-marker-7")).getByText("BGW")).toBeInTheDocument();
  });
});
