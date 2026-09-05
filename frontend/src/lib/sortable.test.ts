// Source: verified by executing the exact vanilla comparator in Node, 2026-09-01
// (RESEARCH.md Pitfall 1). Locks in the counter-intuitive-but-correct polarity
// before any page code depends on it.
import { describe, expect, it } from "vitest";
import { sortRows } from "./sortable";

describe("sortRows (ported from web/assets/app.js makeSortable, verified 2026-09-01)", () => {
  it("fresh click (dir=-1) sorts numeric ascending", () => {
    const rows = [{ v: 3 }, { v: 1 }, { v: 5 }, { v: 2 }];
    expect(sortRows(rows, "v", -1, true).map((r) => r.v)).toEqual([1, 2, 3, 5]);
  });

  it("second click (dir=+1) sorts numeric descending", () => {
    const rows = [{ v: 3 }, { v: 1 }, { v: 5 }, { v: 2 }];
    expect(sortRows(rows, "v", 1, true).map((r) => r.v)).toEqual([5, 3, 2, 1]);
  });

  it("dir=-1 puts nulls at the TOP", () => {
    const rows: { v: number | null }[] = [{ v: 3 }, { v: null }, { v: 5 }];
    expect(sortRows(rows, "v", -1, true).map((r) => r.v)).toEqual([null, 3, 5]);
  });

  it("dir=+1 puts nulls at the BOTTOM", () => {
    const rows: { v: number | null }[] = [{ v: 3 }, { v: null }, { v: 5 }];
    expect(sortRows(rows, "v", 1, true).map((r) => r.v)).toEqual([5, 3, null]);
  });

  it("dir=-1 sorts strings ascending", () => {
    const rows = [{ name: "Charlie" }, { name: "Alpha" }, { name: "Bravo" }];
    expect(sortRows(rows, "name", -1, false).map((r) => r.name)).toEqual([
      "Alpha",
      "Bravo",
      "Charlie",
    ]);
  });

  it("preserves input order for equal keys (stable sort)", () => {
    const rows = [
      { v: 3, id: "a" },
      { v: 3, id: "b" },
      { v: 1, id: "c" },
    ];
    expect(sortRows(rows, "v", -1, true).map((r) => r.id)).toEqual(["c", "a", "b"]);
  });

  it("does not mutate the input array", () => {
    const rows = [{ v: 3 }, { v: 1 }];
    const original = rows.map((r) => ({ ...r }));
    sortRows(rows, "v", -1, true);
    expect(rows).toEqual(original);
  });
});
