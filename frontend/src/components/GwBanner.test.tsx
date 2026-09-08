import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import GwBanner from "./GwBanner";
import metaFixture from "../test/fixtures/meta.json";
import type { MetaResponse } from "../lib/api";

const META = metaFixture as MetaResponse;

describe("GwBanner", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the verbatim loading… copy while the query is pending", () => {
    render(<GwBanner status="pending" data={undefined} />);
    expect(screen.getByText("loading…")).toBeInTheDocument();
  });

  it("shows both lines for a future deadline", () => {
    const now = new Date("2026-09-01T12:00:00Z").getTime();
    vi.useFakeTimers();
    vi.setSystemTime(now);

    const data: MetaResponse = { ...META, deadline_utc: "2026-09-04T17:30:00Z" };
    render(<GwBanner status="success" data={data} />);

    expect(screen.getByText(/^GW3 · /)).toBeInTheDocument();
    expect(screen.getByText(/generated /)).toBeInTheDocument();
  });

  it("shows the passed state for a past deadline, with the freshness line and no ·", () => {
    const now = new Date("2026-09-05T12:00:00Z").getTime();
    vi.useFakeTimers();
    vi.setSystemTime(now);

    const data: MetaResponse = { ...META, deadline_utc: "2026-09-04T17:30:00Z" };
    render(<GwBanner status="success" data={data} />);

    const line1 = screen.getByText(/deadline passed/);
    expect(line1.textContent).not.toContain("·");
    expect(screen.getByText(/^generated /)).toBeInTheDocument();
  });

  it("shows the quiet deadline TBC fallback with no freshness line and no Retry control on a failed query", () => {
    render(<GwBanner status="error" data={undefined} />);

    expect(screen.getByText("deadline TBC")).toBeInTheDocument();
    expect(screen.queryByText(/^generated /)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("flips to the passed state with no fetch call when fake timers advance past the deadline", () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy as unknown as typeof fetch;

    const now = new Date("2026-09-01T12:00:00Z").getTime();
    vi.useFakeTimers();
    vi.setSystemTime(now);

    const soon = new Date(now + 30000).toISOString();
    const data: MetaResponse = { ...META, deadline_utc: soon };
    render(<GwBanner status="success" data={data} />);

    expect(screen.queryByText(/deadline passed/)).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(60000);
    });

    expect(screen.getByText(/deadline passed/)).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
