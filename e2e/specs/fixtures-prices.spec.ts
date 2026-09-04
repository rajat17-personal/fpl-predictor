import { test, expect } from "@playwright/test";
import { gotoReady } from "../helpers/page";
import fixturesFixture from "../fixtures/v1/normal/web-data/fixtures.json" with { type: "json" };
import watchlistFixture from "../fixtures/v1/normal/web-data/watchlist.json" with { type: "json" };

/*
 * Fixtures ticker + price watch list -- both pure `/data` renderers with no sorting and
 * no interactive cells (D-09). Every expected cell string below is a hardcoded literal
 * hand-derived once from the committed v1 normal fixture (D-15): `lib/format.ts`'s
 * fixed1/fixed2/orDash/localeInt are never imported or called here -- doing so would
 * re-implement the formatting under test, letting a shared bug pass silently.
 *
 * The one deliberate exception is the gameweek column count: it is a structural property
 * of the committed fixture (Fixtures.tsx's R20 comment is explicit that a hard-coded six
 * is the exact bug this guards against), so reading `fixturesFixture[0].gws.length` here
 * is required, not merely allowed.
 */

const GW_COUNT = fixturesFixture[0].gws.length;

test.describe("fixtures ticker", () => {
  test("renders the frozen first row, the data-derived gw column count, and a known chip", async ({
    page,
  }) => {
    await gotoReady(page, "/fixtures");

    await expect(page.getByRole("heading", { name: "Fixture ticker" })).toBeVisible();

    const table = page.locator("table");
    const headerCells = table.locator("thead th");
    // Team, xG next, xGC next, {GW_COUNT} gameweek columns, Ease.
    await expect(headerCells).toHaveCount(3 + GW_COUNT + 1);
    for (let i = 0; i < GW_COUNT; i++) {
      await expect(headerCells.nth(3 + i)).toHaveText(`GW${fixturesFixture[0].gws[i].gw}`);
    }

    // First ticker row (e2e/fixtures/v1/normal/web-data/fixtures.json's own row order,
    // never re-sorted by the page): Crystal Palace (CRY), xg_next 1.45, xgc_next 1.62,
    // ease 3.33.
    const firstRow = table.locator("tbody tr").first();
    const cells = firstRow.locator("td");
    await expect(cells.nth(0)).toContainText("CRY");
    await expect(cells.nth(0)).toContainText("Crystal Palace");
    await expect(cells.nth(1)).toHaveText("1.45");
    await expect(cells.nth(2)).toHaveText("1.62");
    await expect(cells.nth(3 + GW_COUNT)).toHaveText("3.33");

    // A known chip: Crystal Palace's current-gameweek (GW3, the first gw column, index
    // 3 after Team/xG next/xGC next) fixture is away at Fulham, difficulty 3 -- the full
    // FdrCell accessible-name wording. Scoped to that one cell -- the same club plays
    // Fulham again in a later gameweek column, so an unscoped page-wide query would be
    // ambiguous (multiple matches across gameweeks/rows).
    await expect(cells.nth(3).getByLabel("Away vs FUL, difficulty 3")).toBeVisible();

    await expect(page.getByText("Easy", { exact: true })).toBeVisible();
    await expect(page.getByText("Hard", { exact: true })).toBeVisible();

    // The fixtures table is non-sortable in vanilla and has no interactive cells at all
    // (FdrCell.tsx's own header comment) -- zero buttons anywhere inside it.
    await expect(table.getByRole("button")).toHaveCount(0);
  });
});

test.describe("price watch", () => {
  test("renders the single matching mode note and the frozen riser/faller rows", async ({
    page,
  }) => {
    await gotoReady(page, "/prices");

    await expect(page.getByRole("heading", { name: "Price watch" })).toBeVisible();
    await expect(page.getByText(`data as of ${watchlistFixture.date}`)).toBeVisible();

    // Frozen watchlist.json's mode is "official" with locked_players=48 (truthy) --
    // exactly one of the three mode notes renders, including the price-locked-players
    // sentence.
    await expect(page.getByText("Live from FPL's own price predictor.")).toBeVisible();
    await expect(page.getByText("Heuristic mode.")).toHaveCount(0);
    await expect(page.getByText(/^Model predictions \(trained/)).toHaveCount(0);
    await expect(
      page.getByText("48 price-locked players (new signings, recently unflagged) are excluded."),
    ).toBeVisible();

    // "Likely risers" first row: De Cuyper, BHA, DEF, £4.6m, 12.0% owned, 253,865 net
    // transfers, progress label "114% → 128% tonight" (official-mode: pct from
    // row.progress=1.14, tonight from row.proj_tonight=1.28), status "very likely tonight".
    const risersTable = page.getByRole("table", { name: "Likely risers" });
    const riserRow = risersTable.locator("tbody tr").first();
    const riserCells = riserRow.locator("td");
    await expect(riserCells.nth(0)).toContainText("De Cuyper");
    await expect(riserCells.nth(1)).toHaveText("BHA");
    await expect(riserCells.nth(2)).toHaveText("DEF");
    await expect(riserCells.nth(3)).toHaveText("4.6");
    await expect(riserCells.nth(4)).toHaveText("12.0");
    await expect(riserCells.nth(5)).toHaveText("253,865");
    await expect(riserCells.nth(6)).toContainText("114% → 128% tonight");
    await expect(riserCells.nth(7)).toHaveText("very likely tonight");
    await expect(risersTable.getByRole("button")).toHaveCount(0);

    // "Likely fallers" first row: Sánchez, CHE, GK, £5.0m, 1.9% owned, -26,368 net
    // transfers, progress label "111% → 120% tonight" (progress=-1.11, proj_tonight=-1.2).
    await expect(page.getByRole("heading", { name: "Likely fallers" })).toBeVisible();
    const fallersTable = page.getByRole("table", { name: "Likely fallers" });
    const fallerRow = fallersTable.locator("tbody tr").first();
    const fallerCells = fallerRow.locator("td");
    await expect(fallerCells.nth(0)).toContainText("Sánchez");
    await expect(fallerCells.nth(1)).toHaveText("CHE");
    await expect(fallerCells.nth(2)).toHaveText("GK");
    await expect(fallerCells.nth(3)).toHaveText("5.0");
    await expect(fallerCells.nth(4)).toHaveText("1.9");
    await expect(fallerCells.nth(5)).toHaveText("-26,368");
    await expect(fallerCells.nth(6)).toContainText("111% → 120% tonight");
    await expect(fallerCells.nth(7)).toHaveText("very likely tonight");
    await expect(fallersTable.getByRole("button")).toHaveCount(0);
  });
});
