import { describe, expect, it, afterEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { routes } from "./../router";

const NAV_LABELS = [
  "xP table",
  "Rate my team",
  "Fixtures",
  "Prices",
  "League",
  "Scoreboard",
  "Differentials",
  "Method",
];

describe("route isolation (UI-SPEC E2 partial backstop)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("keeps the nav and a sibling route interactive when one route's fetch fails", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi
      .fn()
      .mockRejectedValue(new Error("/data/meta.json: 500")) as unknown as typeof fetch;

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

    for (const label of NAV_LABELS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }

    fireEvent.click(screen.getByRole("link", { name: "Fixtures" }));
    expect(await screen.findByRole("heading", { name: "Fixtures" })).toBeInTheDocument();

    globalThis.fetch = originalFetch;
  });
});

/* Minimal local shape for Node's `process` event emitter — avoids depending on
 * @types/node in tsconfig.app.json's "types" list just for this one test. */
type MinimalNodeProcess = {
  on: (event: "unhandledRejection", listener: (reason: unknown) => void) => void;
  off: (event: "unhandledRejection", listener: (reason: unknown) => void) => void;
};
const nodeProcess = (globalThis as unknown as { process?: MinimalNodeProcess }).process;

describe("route isolation (UI-SPEC E2 concurrency backstop)", () => {
  function Fetcher({
    id,
    gate,
    shouldFail,
  }: {
    id: string;
    gate: Promise<void>;
    shouldFail: boolean;
  }) {
    useQuery({
      queryKey: [id],
      queryFn: async () => {
        await gate;
        if (shouldFail) {
          throw new Error(`${id} failed`);
        }
        return { id };
      },
      retry: false,
    });
    return <div>{id}</div>;
  }

  it("raises no unhandled promise rejection across concurrent queries when one is unmounted mid-flight", async () => {
    // jsdom does not reliably surface Node-level unhandled promise rejections on
    // `window`, so listen on both (per UI-SPEC backstop guidance).
    const rejectionHandler = vi.fn();
    window.addEventListener("unhandledrejection", rejectionHandler);
    nodeProcess?.on("unhandledRejection", rejectionHandler);

    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <Fetcher key="abandoned" id="abandoned" gate={gate} shouldFail={true} />
        <Fetcher key="sibling" id="sibling" gate={gate} shouldFail={false} />
      </QueryClientProvider>,
    );

    // "abandoned" is unmounted mid-flight (mirrors a route left by navigation)
    // while "sibling"'s concurrent query keeps running.
    rerender(
      <QueryClientProvider client={queryClient}>
        <Fetcher key="sibling" id="sibling" gate={gate} shouldFail={false} />
      </QueryClientProvider>,
    );

    release();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(rejectionHandler).not.toHaveBeenCalled();

    nodeProcess?.off("unhandledRejection", rejectionHandler);
    window.removeEventListener("unhandledrejection", rejectionHandler);
  });
});
