import { test, expect } from "@playwright/test";
import { gotoReady, GW } from "../../helpers/page";

/*
 * Runs in the `chromium-dgw` project, routed here purely by this file's `dgw-` filename
 * prefix (e2e/playwright.config.ts's testMatch) against the double-gameweek fixture
 * set's own uvicorn instance -- no absolute URL or port anywhere in this file.
 *
 * The note wording is `predict/live.py`'s `_chip_note` double-week branch verbatim, with
 * gw=3 and the double club count (4) substituted -- e2e/fixtures/v1/dgw/web-data/
 * chips.json's own `note` field, hardcoded here per D-15 rather than re-read at test
 * time.
 */
const NOTE = "GW3 is a DOUBLE for 4 clubs — consider Bench Boost / Triple Captain.";
const AFFECTED_CLUBS_TOOLTIP = "4 clubs affected";

test.describe("double-gameweek chip timing (chromium-dgw)", () => {
  test("renders the double-week note and marks the current GW as a double on the timeline", async ({
    page,
  }) => {
    await gotoReady(page, "/team?tab=chips");

    await expect(page.getByRole("heading", { name: `Why GW${GW}` })).toBeVisible();
    await expect(page.getByText(NOTE, { exact: true })).toBeVisible();

    const marker = page.getByTestId(`gw-marker-${GW}`);
    const trigger = marker.getByRole("button");
    // classifyMarker's label construction: "GW{n} — current gameweek — double gameweek".
    await expect(trigger).toHaveAccessibleName(/double gameweek$/);
    await expect(marker.getByText("DGW", { exact: true })).toBeVisible();

    await trigger.click();
    await expect(marker.getByRole("tooltip")).toHaveText(AFFECTED_CLUBS_TOOLTIP);
  });
});
