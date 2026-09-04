import { test, expect, type Page } from "@playwright/test";
import { gotoReady, GW } from "../../helpers/page";
import blankFixtures from "../../fixtures/v1/blank/web-data/fixtures.json" with { type: "json" };

/*
 * FdrCell.tsx's R21 empty-fixtures branch is unreachable from the normal fixture set --
 * this spec is the only place in the suite that exercises it. Runs in the
 * `chromium-blank` project, routed here purely by this file's `blank-` filename prefix
 * (e2e/playwright.config.ts's testMatch) against the blank fixture set's own uvicorn
 * instance -- no absolute URL or port anywhere in this file, baseURL carries the routing
 * (D-05).
 *
 * The six blank club codes are the synthesis script's own selection rule output
 * (e2e/scripts/synthesize-variants.mjs), recorded verbatim in
 * e2e/fixtures/v1/MANIFEST.md's Synthesis rules section.
 */
const BLANK_CLUBS = ["ARS", "AVL", "BHA", "BOU", "BRE", "CHE"];

// Control club: not one of the six blanked clubs, so its GW3 fixture is untouched by the
// synthesis script -- away at Fulham, difficulty 3 (same value in normal/blank/dgw).
const CONTROL_CLUB = "CRY";
const CONTROL_LABEL = "Away vs FUL, difficulty 3";

// Current-gameweek column index within a ticker row's <td> list: Team(0), xG next(1),
// xGC next(2), then one column per pool gameweek starting at index 3. Derived from the
// committed fixture's own gws order rather than assumed to be index 0.
const CURRENT_GW_TD_INDEX = 3 + blankFixtures[0].gws.findIndex((g) => g.gw === GW);

function rowFor(page: Page, code: string) {
  return page.locator("tbody tr").filter({ has: page.locator(`strong:text-is("${code}")`) });
}

test.describe("blank fixtures ticker (chromium-blank)", () => {
  test("blanked clubs render the em-dash chip; a non-blank club still shows its fixture", async ({
    page,
  }) => {
    await gotoReady(page, "/fixtures");

    for (const code of BLANK_CLUBS) {
      const cell = rowFor(page, code).locator("td").nth(CURRENT_GW_TD_INDEX);
      const chip = cell.getByLabel("Blank gameweek");
      await expect(chip).toHaveCount(1);
      await expect(chip).toHaveText("—");
    }

    const controlCell = rowFor(page, CONTROL_CLUB).locator("td").nth(CURRENT_GW_TD_INDEX);
    await expect(controlCell.getByLabel(CONTROL_LABEL)).toHaveCount(1);
  });
});
