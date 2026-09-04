import { test, expect } from "@playwright/test";
import { gotoReady } from "../helpers/page";

/*
 * xP table (the flagship page, D-06) + Captain picks sub-table -- E2E-03. Every expected
 * cell string/row order below is a hardcoded literal hand-derived once from the committed
 * v1 normal fixture (D-15) by reading e2e/fixtures/v1/normal/web-data/{xp_table,captains}.json
 * directly and hand-running the exact sortRows/format logic on paper. frontend/src/lib/
 * {format,sortable}.ts are the code under test and are never imported here -- re-using them
 * to compute an expectation would let a shared bug pass silently (this plan's own prohibition).
 *
 * Fixture-derivation notes (recorded for Phase 7's parity pass and later plans to reuse):
 *  - xp_table.json's own row order is already descending by xp (the pipeline's own
 *    pre-sort) -- the page's top-50 slice takes rows 1-50 unchanged, no re-sort (R10).
 *  - Row 1: B.Fernandes, MID, MUN, GBP12.0m, 48.6% owned, band 2.5-10.6, xp 3.72, capt xP 5.90.
 *  - Row 2: Haaland, FWD, MCI, GBP15.5m, 71.1% owned, band 1.9-10.1, xp 3.14, capt xP 6.82.
 *  - Row 3: Cherki, MID, MCI, GBP7.7m, 26.5% owned, band 1.6-9.6, xp 2.77, capt xP 4.48.
 *  - Row 50 (last of the slice): Verbruggen, GK, BHA -- pins the top-50 boundary.
 *  - Searched the full 651-row frozen capture (not just the top 50): zero rows have a
 *    null ownership, null xp_capt or null price_m anywhere, and the top 50 contains no
 *    player with a non-"a" status (the closest non-"a" row is index 201, far outside the
 *    slice). Two assertions this plan's <action> text makes conditional on the frozen data
 *    ("if any... has a null ownership", "if the frozen capture contains a player with a
 *    non-available status") are therefore not exercisable against this immutable fixture:
 *      1. Captains.json's first 5 rendered rows (Haaland/Isak/B.Fernandes/Gonzalo/Foden)
 *         have no null ownership, so the R18 literal-"undefined" fallback cannot be proven
 *         here -- the code path (String(r.ownership?.toFixed(1))) is still ported and
 *         documented in PARITY-DEVIATIONS.md #n/a; only this spec's coverage of it is
 *         deferred to a future fixture cut (v2) that includes a null captain ownership row.
 *      2. No status-flag assertion is included -- skipped per the plan's own "if no such
 *         player exists in the capture, skip only that assertion" instruction.
 *    Both gaps are recorded in the plan SUMMARY, not silently dropped.
 */

test.describe("xP table -- exact cell values and row order", () => {
  test("renders the frozen top 50 and the captain picks sub-table", async ({ page }) => {
    await gotoReady(page, "/");

    await expect(
      page.getByRole("heading", { name: "Projected points, with the uncertainty shown" }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Track its accuracy live" })).toHaveAttribute(
      "href",
      "/scoreboard",
    );

    // Scoped by aria-label so the Captain picks sub-table's overlapping player names
    // (Haaland, B.Fernandes, Foden all appear in both tables) can never satisfy these
    // assertions by accident.
    const table = page.getByRole("table", { name: "xP table" });
    const headerCells = table.locator("thead th");
    await expect(headerCells).toHaveCount(7);
    const expectedHeaders = [
      "Pos",
      "Player",
      "Team",
      "£m",
      "Own %",
      "xP (10–90% band)",
      "Captain xP",
    ];
    for (let i = 0; i < expectedHeaders.length; i++) {
      await expect(headerCells.nth(i)).toContainText(expectedHeaders[i]);
    }

    const rows = table.locator("tbody tr");
    await expect(rows).toHaveCount(50);

    // Row 1: B.Fernandes.
    let cells = rows.nth(0).locator("td");
    await expect(cells.nth(0)).toHaveText("MID");
    await expect(cells.nth(1)).toHaveText("B.Fernandes");
    await expect(cells.nth(2)).toHaveText("MUN");
    await expect(cells.nth(3)).toHaveText("12.0");
    await expect(cells.nth(4)).toHaveText("48.6");
    await expect(cells.nth(5)).toContainText("3.72");
    await expect(cells.nth(5)).toContainText("2.5–10.6");
    await expect(cells.nth(6)).toHaveText("5.90");

    // Row 2: Haaland.
    cells = rows.nth(1).locator("td");
    await expect(cells.nth(0)).toHaveText("FWD");
    await expect(cells.nth(1)).toHaveText("Haaland");
    await expect(cells.nth(2)).toHaveText("MCI");
    await expect(cells.nth(3)).toHaveText("15.5");
    await expect(cells.nth(4)).toHaveText("71.1");
    await expect(cells.nth(5)).toContainText("3.14");
    await expect(cells.nth(5)).toContainText("1.9–10.1");
    await expect(cells.nth(6)).toHaveText("6.82");

    // Row 3: Cherki.
    cells = rows.nth(2).locator("td");
    await expect(cells.nth(0)).toHaveText("MID");
    await expect(cells.nth(1)).toHaveText("Cherki");
    await expect(cells.nth(2)).toHaveText("MCI");
    await expect(cells.nth(3)).toHaveText("7.7");
    await expect(cells.nth(4)).toHaveText("26.5");
    await expect(cells.nth(5)).toContainText("2.77");
    await expect(cells.nth(5)).toContainText("1.6–9.6");
    await expect(cells.nth(6)).toHaveText("4.48");

    // Last body row (50th) pins the top-50 slice boundary -- a direct consequence of R10
    // (the pipeline pre-sorts descending by xp; the page applies no re-sort before slicing).
    await expect(rows.nth(49).locator("td").nth(1)).toHaveText("Verbruggen");

    await expect(page.getByText("Showing the top 50 by xP", { exact: false })).toBeVisible();
    await expect(page.getByText("Reading the numbers:", { exact: false })).toBeVisible();

    // Captain picks sub-table (R17-R19) -- exactly five rows, no sort/filter (D-15).
    const captainsTable = page.getByRole("table", { name: "Captain picks" });
    const captainRows = captainsTable.locator("tbody tr");
    await expect(captainRows).toHaveCount(5);

    const captainCells = captainRows.nth(0).locator("td");
    // Team uses the FULL club name here -- unlike the main table's team_short (R17).
    await expect(captainCells.nth(0)).toHaveText("Haaland");
    await expect(captainCells.nth(1)).toHaveText("Man City");
    await expect(captainCells.nth(2)).toHaveText("15.5");
    await expect(captainCells.nth(3)).toHaveText("71.1");
    await expect(captainCells.nth(4)).toHaveText("6.82");
  });
});

/*
 * Sort semantics (sortRows, web/assets/app.js's makeSortable ported verbatim). The
 * polarity is counter-intuitive and deliberate (frontend/src/lib/sortable.ts's own header
 * comment): a FRESH click sorts ASCENDING with nulls at the TOP (dir=-1, glyph "▼"); a
 * REPEAT click on the same header sorts DESCENDING with nulls at the BOTTOM (dir=1, glyph
 * "▲"). Every expected order below was hand-computed once from the frozen top 50 by
 * running sortRows' own comparator logic on paper against xp_table.json, never by
 * importing sortable.ts into this file.
 *
 * Tie coverage: price_m=4.5 is the minimum price in the frozen top 50, and its five-way
 * tie group (Dedic, Petrovic, Leno, Ajer, Verbruggen -- in that pre-sort relative order)
 * lands at the very front on the fresh (ascending) click and the very back on the repeat
 * (descending) click, in the SAME relative order both times -- exactly what a stable sort
 * guarantees for equal keys. ownership=0.6 (Ndoye, Janelt) is a second, independent tie
 * used for the same proof on a different numeric column.
 *
 * Null coverage: the full 651-row frozen capture (not just the top 50) has zero rows with
 * a null price_m, ownership or xp_capt -- confirmed by scripted inspection of the committed
 * v1 normal fixture. The plan's flagged-assumption fallback ("cover the tie/null cases
 * through a position filter that narrows to rows that do") presumes a null exists
 * SOMEWHERE reachable by filtering; since none exists anywhere in the committed JSON, no
 * filter can manufacture one without mutating the immutable v1 fixture (forbidden by D-08).
 * The null-key assertions are therefore not exercisable against this fixture and are
 * skipped here -- documented in the plan SUMMARY, not silently dropped. Everything else
 * this task's <action> text asks for (both directions, both glyphs, tie stability, a text
 * column) is fully covered below.
 */
test.describe("xP table -- sort semantics", () => {
  test("numeric column: fresh/repeat click glyphs, exact order, and a stable tie", async ({
    page,
  }) => {
    await gotoReady(page, "/");
    const table = page.getByRole("table", { name: "xP table" });
    const headerCells = table.locator("thead th");
    const priceHeader = headerCells.nth(3); // £m
    const names = () => table.locator("tbody tr td:nth-child(2)").allTextContents();

    // Fresh click: ascending, nulls-at-top polarity (none present here, so plain ascending).
    await priceHeader.locator("button").click();
    await expect(priceHeader).toContainText("▼");
    let visible = await names();
    expect(visible.slice(0, 5)).toEqual(["Dedić", "Petrović", "Leno", "Ajer", "Verbruggen"]);
    expect(visible).toHaveLength(50);

    // Repeat click on the SAME header: descending, nulls-at-bottom polarity.
    await priceHeader.locator("button").click();
    await expect(priceHeader).toContainText("▲");
    visible = await names();
    expect(visible.slice(0, 5)).toEqual(["Haaland", "B.Fernandes", "Palmer", "Saka", "Isak"]);
    // The same tie group, still in the SAME relative order (Dedić before Petrović),
    // now at the bottom instead of the top -- a stable sort neither merges nor swaps ties.
    expect(visible.slice(-5)).toEqual(["Dedić", "Petrović", "Leno", "Ajer", "Verbruggen"]);
    expect(visible).toHaveLength(50);
  });

  test("a second numeric tie (ownership=0.6) stays in relative order in both directions", async ({
    page,
  }) => {
    await gotoReady(page, "/");
    const table = page.getByRole("table", { name: "xP table" });
    const headerCells = table.locator("thead th");
    const ownershipHeader = headerCells.nth(4); // Own %
    const names = () => table.locator("tbody tr td:nth-child(2)").allTextContents();

    await ownershipHeader.locator("button").click();
    let visible = await names();
    // Ndoye and Janelt both have ownership=0.6, the minimum in the frozen top 50 -- fresh
    // click puts them first, in their original pre-sort relative order.
    expect(visible[0]).toBe("Ndoye");
    expect(visible[1]).toBe("Janelt");

    await ownershipHeader.locator("button").click();
    visible = await names();
    // Same pair, same relative order (Ndoye before Janelt), now at the bottom.
    expect(visible[48]).toBe("Ndoye");
    expect(visible[49]).toBe("Janelt");
  });

  test("text column (Player): fresh/repeat click glyphs and exact first/last names", async ({
    page,
  }) => {
    await gotoReady(page, "/");
    const table = page.getByRole("table", { name: "xP table" });
    const headerCells = table.locator("thead th");
    const playerHeader = headerCells.nth(1); // Player
    const names = () => table.locator("tbody tr td:nth-child(2)").allTextContents();

    await playerHeader.locator("button").click();
    await expect(playerHeader).toContainText("▼");
    let visible = await names();
    expect(visible[0]).toBe("A.Becker");
    expect(visible[visible.length - 1]).toBe("Wissa");

    await playerHeader.locator("button").click();
    await expect(playerHeader).toContainText("▲");
    visible = await names();
    expect(visible[0]).toBe("Wissa");
    expect(visible[visible.length - 1]).toBe("A.Becker");
  });

  test("clicking a different header resets to the fresh-click direction", async ({ page }) => {
    await gotoReady(page, "/");
    const table = page.getByRole("table", { name: "xP table" });
    const headerCells = table.locator("thead th");
    const priceHeader = headerCells.nth(3); // £m
    const ownershipHeader = headerCells.nth(4); // Own %

    await priceHeader.locator("button").click();
    await expect(priceHeader).toContainText("▼");

    await ownershipHeader.locator("button").click();
    await expect(ownershipHeader).toContainText("▼");
    // The previously-active header no longer shows a glyph at all.
    await expect(priceHeader).not.toContainText("▼");
    await expect(priceHeader).not.toContainText("▲");
  });
});

/*
 * Filters (position chips + search) and the empty-result state (R12/R13). Position
 * counts within the frozen top 50: GK=12, DEF=10, MID=22, FWD=6 (sums to 50, proving the
 * filter runs on top of the already-sliced 50, never the full fetched array). "Man City"
 * is the search term for the full-club-name test: 9 of the top 50 rows have team="Man
 * City"/team_short="MCI", and the full name is never rendered in any cell on this page --
 * so a passing search can only be exercising the r.team match (R13), not a rendered
 * substring.
 */
test.describe("xP table -- filters, empty state, and filter/sort interaction", () => {
  test("position chips render All/GK/DEF/MID/FWD with All pressed by default", async ({
    page,
  }) => {
    await gotoReady(page, "/");
    for (const label of ["All", "GK", "DEF", "MID", "FWD"]) {
      await expect(page.getByRole("button", { name: label, exact: true })).toBeVisible();
    }
    await expect(page.getByRole("button", { name: "All", exact: true, pressed: true })).toHaveCount(
      1,
    );
  });

  test("each position chip renders the exact frozen row count for the top 50", async ({
    page,
  }) => {
    await gotoReady(page, "/");
    const table = page.getByRole("table", { name: "xP table" });
    const counts: Record<string, number> = { GK: 12, DEF: 10, MID: 22, FWD: 6 };
    let sum = 0;
    for (const [label, count] of Object.entries(counts)) {
      await page.getByRole("button", { name: label, exact: true }).click();
      await expect(table.locator("tbody tr")).toHaveCount(count);
      sum += count;
    }
    expect(sum).toBe(50);
  });

  test("searching a club's full name matches on team, never a rendered cell", async ({
    page,
  }) => {
    await gotoReady(page, "/");
    const table = page.getByRole("table", { name: "xP table" });
    const searchBox = page.getByRole("searchbox", { name: "Search player or team" });
    await searchBox.fill("Man City");

    const rows = table.locator("tbody tr");
    await expect(rows).toHaveCount(9);
    const teamCells = table.locator("tbody tr td:nth-child(3)");
    const teamShorts = await teamCells.allTextContents();
    for (const short of teamShorts) {
      expect(short).toBe("MCI");
    }
  });

  test("an unmatched search shows the no-match block, distinct from the empty-data block", async ({
    page,
  }) => {
    await gotoReady(page, "/");
    const searchBox = page.getByRole("searchbox", { name: "Search player or team" });
    await searchBox.fill("zzz-no-such-player-or-club-zzz");

    await expect(page.getByRole("heading", { name: "No players match" })).toBeVisible();
    await expect(
      page.getByText("Try a different position filter or search term."),
    ).toBeVisible();
    await expect(page.getByRole("table", { name: "xP table" })).toHaveCount(0);
    // Distinct from the page-level EmptyState (an empty FETCH, not an empty FILTER) --
    // that heading must never appear here.
    await expect(page.getByRole("heading", { name: "Nothing here yet" })).toHaveCount(0);
    // The chips and search box stay present so the user can recover.
    await expect(page.getByRole("button", { name: "All", exact: true })).toBeVisible();
    await expect(searchBox).toBeVisible();

    await searchBox.fill("");
    await expect(page.getByRole("table", { name: "xP table" }).locator("tbody tr")).toHaveCount(
      50,
    );
  });

  test("sort runs over the filtered subset, not the unfiltered 50", async ({ page }) => {
    await gotoReady(page, "/");
    const table = page.getByRole("table", { name: "xP table" });
    await page.getByRole("button", { name: "GK", exact: true }).click();
    const rows = table.locator("tbody tr");
    await expect(rows).toHaveCount(12);

    const priceHeader = table.locator("thead th").nth(3); // £m
    await priceHeader.locator("button").click(); // fresh click: ascending

    const names = await table.locator("tbody tr td:nth-child(2)").allTextContents();
    // Hand-derived: all 12 GK rows in the frozen top 50, sorted ascending by price_m,
    // ties broken by the pre-sort (descending-xp) relative order -- proves the sort
    // operated over the 12-row GK subset, not the unfiltered 50 (which would include
    // non-GK names this list never mentions).
    expect(names).toEqual([
      "Petrović",
      "Leno",
      "Verbruggen",
      "Tzolakis",
      "Kelleher",
      "Trafford",
      "Horníček",
      "Sels",
      "Henderson",
      "Donnarumma",
      "A.Becker",
      "Pickford",
    ]);
  });
});
