import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Spinner } from "./Spinner";
import { routes } from "../router";

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("Spinner", () => {
  it("renders the Loading… label", () => {
    render(<Spinner />);
    expect(screen.getByText(/Loading…/i)).toBeInTheDocument();
  });
});

describe("Spinner (UI-SPEC E2 loading backstop)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows Loading… while the tracer route's query is pending, and removes it once resolved", async () => {
    const originalFetch = globalThis.fetch;
    const { promise, resolve } = createDeferred<Response>();
    globalThis.fetch = vi.fn().mockReturnValue(promise) as unknown as typeof fetch;

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const router = createMemoryRouter(routes, { initialEntries: ["/"] });

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(screen.getByText(/Loading…/i)).toBeInTheDocument();

    resolve(
      new Response(JSON.stringify({ gw: 5, season: "2026-27" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await waitFor(() => {
      expect(screen.queryByText(/Loading…/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText(/Gameweek 5/)).toBeInTheDocument();

    globalThis.fetch = originalFetch;
  });
});
