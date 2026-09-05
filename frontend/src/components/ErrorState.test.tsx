import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorState } from "./ErrorState";
import { routes } from "../router";

describe("ErrorState", () => {
  it("renders the heading, substitutes the resource into the body, and calls onRetry exactly once when Retry is clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorState resource="the gameweek data" onRetry={onRetry} />);

    expect(screen.getByText("Couldn't load this page")).toBeInTheDocument();
    expect(screen.getByText(/the gameweek data/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});

describe("ErrorState (UI-SPEC E2 error backstop)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders on a rejected route query, Retry re-triggers refetch, and no raw error detail reaches the DOM", async () => {
    // The "/" route now fires two concurrent queries (xp_table.json,
    // captains.json — Phase 2 Plan 01 Task 3). This test is about the
    // primary data source's error/retry contract, so it tracks calls to
    // that URL specifically rather than the raw mock's overall call count,
    // which also includes the (irrelevant here) captains fetch.
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn((path: string) => {
      if (path === "/data/xp_table.json") {
        return Promise.reject(new Error("/data/xp_table.json: 500"));
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
      });
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    const xpTableCallCount = () =>
      fetchMock.mock.calls.filter(([path]) => path === "/data/xp_table.json").length;

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const router = createMemoryRouter(routes, { initialEntries: ["/"] });

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Couldn't load this page")).toBeInTheDocument();
    const retryButton = screen.getByRole("button", { name: /retry/i });
    expect(retryButton).toBeInTheDocument();
    expect(xpTableCallCount()).toBe(1);

    fireEvent.click(retryButton);
    await waitFor(() => {
      expect(xpTableCallCount()).toBe(2);
    });

    expect(document.body.textContent).not.toContain("/data/xp_table.json");
    expect(document.body.textContent).not.toContain("500");

    globalThis.fetch = originalFetch;
  });
});
