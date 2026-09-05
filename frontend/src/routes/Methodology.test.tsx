import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import PageShell from "../components/PageShell";
import Methodology from "./Methodology";
import metaFixture from "../test/fixtures/meta.json";

/* Task 2 — Methodology page: build-time bundled markdown (D-13), no
 * runtime fetch of its own. Rendered inside <PageShell> (which owns the
 * meta.json query for the GW banner) so the shared-footer assertion can be
 * made against the real Phase 1 footer, mirroring PageShell.test.tsx's own
 * render pattern. */

function mockMetaFetch() {
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(metaFixture),
    }),
  ) as unknown as typeof fetch;
}

function renderMethodology() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter initialEntries={["/methodology"]}>
      <QueryClientProvider client={queryClient}>
        <Routes>
          <Route element={<PageShell />}>
            <Route path="/methodology" element={<Methodology />} />
          </Route>
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("Methodology", () => {
  beforeEach(() => {
    mockMetaFetch();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the five h2 sections in the documented order", () => {
    renderMethodology();

    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual([
      "Prediction",
      "Uncertainty",
      "Selection",
      "The receipts",
      "Honesty policy",
    ]);
  });

  it("renders the four receipt figures with their exact strings and source captions", () => {
    renderMethodology();

    expect(screen.getByText(/0\.87 vs FPL 1\.07/)).toBeInTheDocument();
    expect(screen.getByText(/held-out season, per fixture/)).toBeInTheDocument();

    expect(screen.getByText(/0\.74 vs FPL 0\.30/)).toBeInTheDocument();
    expect(screen.getByText(/Spearman, predicted vs actual/)).toBeInTheDocument();

    expect(screen.getByText(/~2260/)).toBeInTheDocument();
    expect(screen.getByText(/full system, 6-season walk-forward average/)).toBeInTheDocument();

    expect(screen.getByText(/\+102/)).toBeInTheDocument();
    expect(screen.getByText(/points\/season vs an ML-free baseline/)).toBeInTheDocument();
  });

  it("renders the honesty policy as exactly three list items", () => {
    renderMethodology();

    const heading = screen.getByRole("heading", { level: 2, name: "Honesty policy" });
    const list = heading.nextElementSibling as HTMLElement;
    expect(list.tagName).toBe("UL");
    expect(within(list).getAllByRole("listitem")).toHaveLength(3);
  });

  it("renders the data-source credit line as the final paragraph of the page body, leaving the PageShell footer unchanged", () => {
    const { container } = renderMethodology();

    expect(
      screen.getByText(
        /Data: official FPL API, historical per-gameweek archives, football-data\.co\.uk odds\./,
      ),
    ).toBeInTheDocument();

    const main = container.querySelector("main")!;
    const paragraphs = Array.from(main.querySelectorAll("p"));
    expect(paragraphs.at(-1)?.textContent).toContain("Data: official FPL API");

    const footerParagraph = container.querySelector("footer p");
    expect(footerParagraph?.textContent).toContain(
      "Predictions are statistics, not certainties.",
    );
  });

  it("navigates the internal scoreboard link client-side via react-router, not a full page reload (WR-02)", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <MemoryRouter initialEntries={["/methodology"]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route element={<PageShell />}>
              <Route path="/methodology" element={<Methodology />} />
              <Route path="/scoreboard" element={<div>SCOREBOARD STUB</div>} />
            </Route>
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    );

    const link = screen.getByRole("link", { name: "scoreboard" });
    expect(link).toHaveAttribute("href", "/scoreboard");

    // A plain <a href="/scoreboard"> would trigger jsdom's unimplemented
    // full-navigation path (and never swap the rendered route tree). A
    // react-router <Link> intercepts the click and transitions in place —
    // asserting the stub route's content appears proves client-side
    // routing occurred, not a full page reload.
    fireEvent.click(link);
    expect(screen.getByText("SCOREBOARD STUB")).toBeInTheDocument();
  });

  it("renders no spinner and no Retry control on this page under any condition", () => {
    renderMethodology();

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("sets document.title for the '/methodology' route", () => {
    renderMethodology();

    expect(document.title).toBe("How the model works — FPL ML");
  });

  it("renders script-shaped markdown text as escaped visible text, never as a live element", () => {
    render(
      <ReactMarkdown>{"before <script>window.__pwned = true</script> after"}</ReactMarkdown>,
    );

    expect(document.querySelector("script")).not.toBeInTheDocument();
    expect(screen.getByText(/window\.__pwned = true/)).toBeInTheDocument();
  });
});
