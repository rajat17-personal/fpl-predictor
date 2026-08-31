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
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockRejectedValue(new Error("/data/meta.json: 500"));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

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
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.click(retryButton);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    expect(document.body.textContent).not.toContain("/data/meta.json");
    expect(document.body.textContent).not.toContain("500");

    globalThis.fetch = originalFetch;
  });
});
