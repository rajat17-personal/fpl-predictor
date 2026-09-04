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
