import { test, expect, type Page } from "@playwright/test";
import { gotoReady } from "../helpers/page";
import squadFixture from "../fixtures/v1/normal/web-data/squad.json" with { type: "json" };

/*
 * Browser-only geometry assertions a layout-less jsdom unit test cannot make (Group A is
 * the G-01-3 handoff from Phase 1's deferred-items.md; Group B is the G-03-1 regression
 * guard for the row-centring bug documented in .planning/debug/pitch-row-centering-drift.md;
 * Group C is Phase 3's D-07 phone-width promise). Every navigation goes through
 * `gotoReady` so the browser clock is pinned and web fonts have settled (Pitfall 6 --
 * @fontsource/* families load asynchronously, and every bounding-box measurement below
 * depends on the swapped-in font's real metrics) before any boundingBox() is read.
 *
 * Assertions are on measured boxes only -- no screenshot comparison anywhere (D-16).
 *
 * The three viewports below are exactly the ones D-14 mandates: 1280 wide as the
 * standard desktop for flow specs, 1720 wide for the Phase 1 header-containment
 * handoff, and 390 wide as the phone case for the team page.
 */

/* Row card counts are read from the committed fixture's `starting` flags -- structural
 * counts, never formatted display output, so deriving them here (rather than hardcoding
 * an assumed formation) keeps this spec honest if the frozen squad's shape ever changes
 * under a future fixture re-cut. Every string/number the app itself FORMATS for display
 * stays a hardcoded literal elsewhere in this suite (D-15) -- this is a raw structural
 * count, not formatted output. */
const starters = squadFixture.squad.filter((row) => row.starting);
const bench = squadFixture.squad.filter((row) => !row.starting);
const ROW_COUNTS: Record<string, number> = {
  Goalkeeper: starters.filter((r) => r.position === "GK").length,
  Defenders: starters.filter((r) => r.position === "DEF").length,
  Midfielders: starters.filter((r) => r.position === "MID").length,
  Forwards: starters.filter((r) => r.position === "FWD").length,
  Bench: bench.length,
};

/** Throws loudly instead of allowing a null bounding box to silently pass an
 * optional-chained comparison -- a locator that resolved to nothing is a spec bug, not a
 * "0" measurement. */
async function requireBox(locator: import("@playwright/test").Locator, label: string) {
  const box = await locator.boundingBox();
  if (!box) {
    throw new Error(`expected a bounding box for ${label}, got null`);
  }
  return box;
}

async function assertRowSymmetry(page: Page, label: string, expectedCount: number) {
  const row = page.getByRole("group", { name: label });
  const cards = row.locator("> div");
  await expect(cards).toHaveCount(expectedCount);

  const rowBox = await requireBox(row, `${label} row`);
  const firstBox = await requireBox(cards.first(), `${label} first card`);
  const lastBox = await requireBox(cards.last(), `${label} last card`);

  const leftGap = firstBox.x - rowBox.x;
  const rightGap = rowBox.x + rowBox.width - (lastBox.x + lastBox.width);
  expect(Math.abs(leftGap - rightGap)).toBeLessThan(1);
}

test.describe("shell geometry (browser-only, no screenshots)", () => {
  test("header inner wrapper stays contained at 1720px (G-01-3)", async ({ page }) => {
    await gotoReady(page, "/", { viewport: { width: 1720, height: 900 } });

    // PageShell.tsx: <header><div class="mx-auto w-full max-w-[68rem] ... px-4">
    const headerInner = page.locator("header > div").first();
    const main = page.locator("main");

    const headerBox = await requireBox(headerInner, "header inner wrapper");
    const mainBox = await requireBox(main, "main");

    expect(headerBox.width).toBeLessThanOrEqual(1088); // 68rem at the app's 16px root
    const viewportCenter = 1720 / 2;
    const headerCenter = headerBox.x + headerBox.width / 2;
    expect(Math.abs(headerCenter - viewportCenter)).toBeLessThan(1);
    expect(Math.abs(headerBox.x - mainBox.x)).toBeLessThan(1);
    expect(
      Math.abs(headerBox.x + headerBox.width - (mainBox.x + mainBox.width)),
    ).toBeLessThan(1);
  });

  for (const viewport of [
    { width: 1280, height: 720 },
    { width: 390, height: 844 },
  ]) {
    test(`pitch rows are centred symmetrically at ${viewport.width}px (G-03-1)`, async ({
      page,
    }) => {
      await gotoReady(page, "/team", { viewport });

      for (const [label, count] of Object.entries(ROW_COUNTS)) {
        await assertRowSymmetry(page, label, count);
      }
    });
  }

  test("team page has no horizontal overflow at 390px (D-07)", async ({ page }) => {
    await gotoReady(page, "/team", { viewport: { width: 390, height: 844 } });

    const { scrollWidth, clientWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);

    const cardBoxes = await page.locator('[role="group"] > div').evaluateAll((nodes) =>
      nodes.map((node) => {
        const rect = node.getBoundingClientRect();
        return { left: rect.left, right: rect.right };
      }),
    );
    expect(cardBoxes.length).toBeGreaterThan(0);
    for (const box of cardBoxes) {
      expect(box.left).toBeGreaterThanOrEqual(0);
      expect(box.right).toBeLessThanOrEqual(390);
    }
  });
});
