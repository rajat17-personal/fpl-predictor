import { test, expect } from "@playwright/test";
import { gotoReady } from "../../helpers/page";

/*
 * Under the blank set, `predict/export.py`'s build_table drops every player whose club
 * has no fixture that gameweek (no zero-xP placeholder row) -- e2e/scripts/synthesize-
 * variants.mjs mirrors that by dropping the six blank clubs' rows from xp_table.json.
 * Runs in the `chromium-blank` project (routed by this file's `blank-` prefix).
 */
const BLANK_CLUBS = ["ARS", "AVL", "BHA", "BOU", "BRE", "CHE"];

test.describe("blank set xP table (chromium-blank)", () => {
  test("no visible row belongs to a blanked club; the top-50 slice still applies", async ({
    page,
  }) => {
    await gotoReady(page, "/");

    const table = page.getByRole("table", { name: "xP table" });
    const rows = table.locator("tbody tr");
    const count = await rows.count();
    expect(count).toBeLessThanOrEqual(50);
    expect(count).toBeGreaterThan(0);

    const teamCells = rows.locator("td:nth-child(3)");
    const teams = await teamCells.allTextContents();
    for (const t of teams) {
      expect(BLANK_CLUBS).not.toContain(t);
    }

    // The blank set's own first row -- hand-derived from
    // e2e/fixtures/v1/blank/web-data/xp_table.json: B.Fernandes (MID, MUN) is unaffected
    // by the blank-club drop since Man Utd is not one of the six blanked clubs, so it
    // stays the top row exactly as it is in the normal set.
    const firstRow = rows.first();
    const cells = firstRow.locator("td");
    await expect(cells.nth(0)).toHaveText("MID");
    await expect(cells.nth(1)).toContainText("B.Fernandes");
    await expect(cells.nth(2)).toHaveText("MUN");
    await expect(cells.nth(3)).toHaveText("12.0");
    await expect(cells.nth(4)).toHaveText("48.6");
    await expect(cells.nth(6)).toHaveText("5.90");
  });
});
