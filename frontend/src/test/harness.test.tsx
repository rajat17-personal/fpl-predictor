import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PageShell from "../components/PageShell";

/* Smoke test for the test harness itself, not for PageShell's design: proves
 * jsdom is present, JSX compiles under the TypeScript 6.0.3 pin, Testing
 * Library queries run, and the jest-dom matchers are registered. If this test
 * cannot be made to pass, the problem is the harness, not the component.
 *
 * PageShell owns a `meta.json` query (Task 3, UI-06) so it now needs a
 * QueryClientProvider to render at all; fetch is mocked so the query
 * resolves deterministically rather than hitting the network. */
describe("test harness", () => {
  it("renders PageShell and shows the footer disclaimer", () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      }),
    ) as unknown as typeof fetch;
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <MemoryRouter initialEntries={["/"]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route element={<PageShell />}>
              <Route index element={<div>content</div>} />
            </Route>
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    );

    expect(
      screen.getByText(/Not affiliated with the Premier League/i),
    ).toBeInTheDocument();
  });
});
