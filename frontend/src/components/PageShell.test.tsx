import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PageShell from "./PageShell";
import metaFixture from "../test/fixtures/meta.json";

/* Regression test for UAT gap G-01-3: header content full-bleed on wide
 * viewports while main/footer content is capped at 68rem. jsdom has no
 * layout engine, so this asserts the *class tokens* that drive containment,
 * not measured pixel geometry — the real pixel-width assertion is handed
 * forward to Phase 4's Playwright suite (see deferred-items.md).
 *
 * PageShell now owns the shared `meta.json` query (Task 3) that feeds
 * GwBanner, so every render needs a QueryClientProvider — a fresh
 * QueryClient per test with retries disabled, and fetch mocked so the query
 * resolves deterministically without a real network call. */

const CONTAINMENT = ["mx-auto", "w-full", "max-w-[68rem]", "px-4"];

function mockFetchOnce() {
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(metaFixture),
    }),
  ) as unknown as typeof fetch;
}

function renderShell() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
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
}

function classSet(el: Element | null | undefined): Set<string> {
  if (!el) return new Set();
  return new Set((el.getAttribute("class") ?? "").split(/\s+/).filter(Boolean));
}

describe("PageShell chrome containment (G-01-3)", () => {
  beforeEach(() => {
    mockFetchOnce();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("header, main and footer content share one containment geometry", () => {
    const { container } = renderShell();

    const header = container.querySelector("header");
    const headerContentWrapper = header?.firstElementChild ?? null;
    const main = container.querySelector("main");
    const footerParagraph = container.querySelector("footer p");

    for (const el of [headerContentWrapper, main, footerParagraph]) {
      const tokens = classSet(el);
      for (const token of CONTAINMENT) {
        expect(tokens.has(token)).toBe(true);
      }
    }
  });

  it("chrome borders stay full-bleed while only content is capped", () => {
    const { container } = renderShell();

    const header = container.querySelector("header");
    const footer = container.querySelector("footer");

    const headerTokens = classSet(header);
    const footerTokens = classSet(footer);

    expect(headerTokens.has("border-b")).toBe(true);
    expect(footerTokens.has("border-t")).toBe(true);

    for (const tokens of [headerTokens, footerTokens]) {
      expect([...tokens].some((t) => t.startsWith("max-w-"))).toBe(false);
      expect([...tokens].some((t) => t.startsWith("px-"))).toBe(false);
    }

    const headerContentWrapper = header?.firstElementChild ?? null;
    expect(headerContentWrapper?.tagName).toBe("DIV");
    expect(headerContentWrapper?.parentElement).toBe(header);

    const nav = screen.getByRole("navigation", { name: "Site" });
    expect(headerContentWrapper?.contains(nav)).toBe(true);
    expect(headerContentWrapper?.textContent).toContain("FPL");
  });
});

describe("PageShell — GW banner and theme toggle wiring (Task 3)", () => {
  beforeEach(() => {
    mockFetchOnce();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders both the GW banner and the theme toggle in the header's trailing slot", async () => {
    renderShell();

    expect(await screen.findByText(/^GW3 deadline/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Light theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dark theme" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "System theme" })).toBeInTheDocument();
  });
});

describe("PageShell — PITCH-01 footer disclaimer and nav rename (03-01 Task 3)", () => {
  beforeEach(() => {
    mockFetchOnce();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the nav link for /team labeled 'My team', not the vanilla 'Rate my team'", () => {
    renderShell();
    expect(screen.getByRole("link", { name: "My team" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Rate my team" })).not.toBeInTheDocument();
  });

  it("renders the full four-sentence footer disclaimer, including the generic-kit-imagery sentence, on every route", () => {
    const { container } = renderShell();
    const footerParagraph = container.querySelector("footer p");
    expect(footerParagraph?.textContent).toContain(
      "Predictions are statistics, not certainties.",
    );
    expect(footerParagraph?.textContent).toContain(
      "This site hosts no contests and takes no stakes.",
    );
    expect(footerParagraph?.textContent).toContain(
      "Not affiliated with the Premier League or the official Fantasy Premier League game.",
    );
    expect(footerParagraph?.textContent).toContain(
      "Player kit colors shown are generic illustrations, not licensed team imagery.",
    );
  });
});
