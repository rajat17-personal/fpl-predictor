import { describe, expect, it } from "vitest";
import { fixed1, fixed2, localeInt, orDash } from "./format";

describe("fixed1", () => {
  it("formats to exactly one decimal place", () => {
    expect(fixed1(12)).toBe("12.0");
    expect(fixed1(3.63)).toBe("3.6");
    expect(fixed1(47.649)).toBe("47.6");
  });
});

describe("fixed2", () => {
  it("formats to exactly two decimal places", () => {
    expect(fixed2(6)).toBe("6.00");
    expect(fixed2(6.041)).toBe("6.04");
    expect(fixed2(3.634)).toBe("3.63");
  });
});

describe("orDash", () => {
  it("returns the en-dash for null", () => {
    expect(orDash(null)).toBe("–");
  });

  it("returns the en-dash for undefined", () => {
    expect(orDash(undefined)).toBe("–");
  });

  it("returns the value unchanged for a real (including empty) string", () => {
    expect(orDash("47.6")).toBe("47.6");
    expect(orDash("")).toBe("");
  });
});

describe("localeInt", () => {
  it("formats with thousands separators via toLocaleString", () => {
    expect(localeInt(1234)).toBe((1234).toLocaleString());
    expect(localeInt(0)).toBe((0).toLocaleString());
  });
});
