import { test, expect, type Page } from "@playwright/test";
import { gotoReady, GW } from "../../helpers/page";
import dgwFixtures from "../../fixtures/v1/dgw/web-data/fixtures.json" with { type: "json" };

/*
 * Runs in the `chromium-dgw` project, routed here purely by this file's `dgw-` filename
 * prefix (e2e/playwright.config.ts's testMatch) against the double-gameweek fixture
 * set's own uvicorn instance -- no absolute URL or port anywhere in this file, baseURL
 * carries the routing (D-05).
 *
 * The four double club codes are the synthesis script's own selection rule output
 * (e2e/scripts/synthesize-variants.mjs), recorded verbatim in
 * e2e/fixtures/v1/MANIFEST.md's Synthesis rules section.
 */
const DOUBLE_CLUBS = ["ARS", "AVL", "BHA", "BOU"];

// Control club: not one of the four doubled clubs, so its GW3 fixture is untouched by
// the synthesis script -- away at Fulham, difficulty 3 (same value in normal/blank/dgw).
const CONTROL_CLUB = "CRY";
const CONTROL_LABEL = "Away vs FUL, difficulty 3";

// Current-gameweek column index, derived the same way as blank-fixtures.spec.ts.
const CURRENT_GW_TD_INDEX = 3 + dgwFixtures[0].gws.findIndex((g) => g.gw === GW);

function rowFor(page: Page, code: string) {
  return page.locator("tbody tr").filter({ has: page.locator(`strong:text-is("${code}")`) });
}

test.describe("double-gameweek fixtures ticker (chromium-dgw)", () => {
  test("doubled clubs render two opposite-venue chips; a non-doubled club still shows one", async ({
    page,
  }) => {
    await gotoReady(page, "/fixtures");

    for (const code of DOUBLE_CLUBS) {
      const cell = rowFor(page, code).locator("td").nth(CURRENT_GW_TD_INDEX);
      const chips = cell.locator("span[aria-label]");
      await expect(chips).toHaveCount(2);

      const labels = await chips.evaluateAll((els) =>
        els.map((el) => el.getAttribute("aria-label") ?? ""),
      );
      const venues = new Set(labels.map((l) => (l.startsWith("Home") ? "Home" : "Away")));
      expect(venues.size).toBe(2); // one Home chip, one Away chip -- opposite venues
    }

    const controlCell = rowFor(page, CONTROL_CLUB).locator("td").nth(CURRENT_GW_TD_INDEX);
    const controlChips = controlCell.locator("span[aria-label]");
    await expect(controlChips).toHaveCount(1);
    await expect(controlCell.getByLabel(CONTROL_LABEL)).toHaveCount(1);
  });
});
