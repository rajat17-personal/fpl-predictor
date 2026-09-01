import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
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

  it("shows Loading… while the '/' route's xP table query is pending, and removes it once resolved", async () => {
    // PageShell now owns a second concurrent query (meta.json, Task 3) — the
    // mock must route by URL rather than share one Response instance across
    // both consumers (a shared instance's .json() can only be read once).
    // See ErrorState.test.tsx / 02-01-SUMMARY.md deviation 3 for the same fix.
    const originalFetch = globalThis.fetch;
    const { promise: xpTablePromise, resolve: resolveXpTable } =
      createDeferred<unknown[]>();
    globalThis.fetch = vi.fn((path: string) => {
      if (path === "/data/meta.json") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({}),
        });
      }
      if (path === "/data/captains.json") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve([]),
        });
      }
      return xpTablePromise.then((body) => ({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      }));
    }) as unknown as typeof fetch;

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const router = createMemoryRouter(routes, { initialEntries: ["/"] });

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Scoped to <main> — the header's GwBanner also shows a "loading…" pill
    // for its own concurrent meta.json query and would otherwise collide.
    const main = () => screen.getByRole("main");
    expect(within(main()).getByText(/Loading…/i)).toBeInTheDocument();

    resolveXpTable([
      {
        player_code: 1,
        player_id: 1,
        name: "B.Fernandes",
        team: "Man Utd",
        team_short: "MUN",
        position: "MID",
        price_m: 12.0,
        xp: 3.63,
        xp_capt: 6.04,
        p10: 2.41,
        p90: 10.47,
        ownership: 47.6,
        status: "a",
        news: "",
      },
    ]);

    await waitFor(() => {
      expect(within(main()).queryByText(/Loading…/i)).not.toBeInTheDocument();
    });
    expect(within(main()).getByText("B.Fernandes")).toBeInTheDocument();

    globalThis.fetch = originalFetch;
  });
});
