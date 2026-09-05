import { describe, expect, it } from "vitest";
import { fmtAbs, fmtFreshness, fmtRel } from "./deadline";

const NOW = new Date("2026-09-01T12:00:00Z").getTime();

describe("fmtAbs", () => {
  it("formats a known ISO instant with weekday short, day numeric, month short, 2-digit hour/minute", () => {
    const expected = new Date("2026-09-04T17:30:00Z").toLocaleString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
    expect(fmtAbs("2026-09-04T17:30:00Z")).toBe(expected);
  });

  it("returns the deadline TBC fallback for null", () => {
    expect(fmtAbs(null)).toBe("deadline TBC");
  });

  it("returns the deadline TBC fallback for undefined", () => {
    expect(fmtAbs(undefined)).toBe("deadline TBC");
  });

  it("returns the deadline TBC fallback for an unparseable value, not an Invalid Date string", () => {
    expect(fmtAbs("not-a-date")).toBe("deadline TBC");
  });
});

describe("fmtRel", () => {
  it("returns exactly 'in 3d 2h' for a deadline 3 days 2 hours ahead", () => {
    const deadline = new Date(NOW + 3 * 86400000 + 2 * 3600000).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(false);
    if (!result.passed) expect(result.text).toBe("in 3d 2h");
  });

  it("stays in the days form at exactly 24 hours remaining", () => {
    const deadline = new Date(NOW + 86400000).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(false);
    if (!result.passed) expect(result.text).toMatch(/^in \d+d \d+h$/);
  });

  it("returns the hours-and-minutes form at 23h 59m remaining", () => {
    const deadline = new Date(NOW + 23 * 3600000 + 59 * 60000).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(false);
    if (!result.passed) expect(result.text).toBe("in 23h 59m");
  });

  it("returns exactly 'in 4h 12m' for a deadline 4 hours 12 minutes ahead", () => {
    const deadline = new Date(NOW + 4 * 3600000 + 12 * 60000).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(false);
    if (!result.passed) expect(result.text).toBe("in 4h 12m");
  });

  it("stays in the hours form at exactly 60 minutes remaining", () => {
    const deadline = new Date(NOW + 3600000).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(false);
    if (!result.passed) expect(result.text).toMatch(/^in \d+h \d+m$/);
  });

  it("returns the finest-granularity form at 59 minutes remaining", () => {
    const deadline = new Date(NOW + 59 * 60000).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(false);
    if (!result.passed) expect(result.text).toMatch(/^in \d+m \d+s$/);
  });

  it("signals the passed state rather than a negative countdown at zero remaining", () => {
    const deadline = new Date(NOW).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(true);
  });

  it("signals the passed state for a deadline already behind now", () => {
    const deadline = new Date(NOW - 3600000).toISOString();
    const result = fmtRel(deadline, NOW);
    expect(result.passed).toBe(true);
  });
});

describe("fmtFreshness", () => {
  it("returns 'generated just now' under 59 seconds elapsed", () => {
    expect(fmtFreshness(new Date(NOW - 59000).toISOString(), NOW)).toBe(
      "generated just now",
    );
  });

  it("returns 'generated 1m ago' at exactly 60 seconds elapsed", () => {
    expect(fmtFreshness(new Date(NOW - 60000).toISOString(), NOW)).toBe(
      "generated 1m ago",
    );
  });

  it("stays in minutes at 59 minutes elapsed", () => {
    expect(fmtFreshness(new Date(NOW - 59 * 60000).toISOString(), NOW)).toBe(
      "generated 59m ago",
    );
  });

  it("returns 'generated 1h ago' at exactly 60 minutes elapsed", () => {
    expect(fmtFreshness(new Date(NOW - 3600000).toISOString(), NOW)).toBe(
      "generated 1h ago",
    );
  });

  it("returns 'generated 1d ago' at exactly 24 hours elapsed", () => {
    expect(fmtFreshness(new Date(NOW - 86400000).toISOString(), NOW)).toBe(
      "generated 1d ago",
    );
  });
});
