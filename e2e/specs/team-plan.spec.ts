import { test, expect } from "@playwright/test";
import { gotoReady, ENTRY, GW } from "../helpers/page";

/*
 * The multi-week plan flow (D-12, E2E-02) — a real /api/plan solve at horizon=2 against
 * the frozen pool, exercised in the browser: pending copy (including the multi-gameweek
 * wait clause), per-week rendering, and proof that the per-gameweek frozen pools are wired
 * through _gw_pools (api/main.py). No route mocking; the request is a genuine round trip.
 *
 * This test raises its OWN timeout (Pitfall 7 / T-04-19) rather than the global
 * playwright.config.ts timeout, so a genuinely hung test elsewhere in the suite is still
 * caught by the low global default.
 *
 * The frozen fixture's real horizon-2 plan happens to buy on both weeks (no week ever
 * holds) — the "Hold" branch of the Moves tile is consequently not exercised by this
 * specific real solve. Documented here rather than forced via a second, separate plan
 * request at a different horizon (out of this plan's D-12-bounded scope) or by mutating
 * the immutable v1 fixture (D-08). See 04-05-SUMMARY.md.
 */

interface PlanBuySell {
  name: string;
  position: string;
}

interface PlanWeek {
  gw: number;
  buys: PlanBuySell[];
  sells: PlanBuySell[];
  hits: number;
  captain: string;
  xi_xp: number;
  bank: number;
  free_transfers_after: number;
  squad: unknown[];
}

interface PlanResponse {
  gw: number;
  horizon: number;
  weeks: PlanWeek[];
}

function weekBlock(page: import("@playwright/test").Page, headingText: string) {
  // Scopes to the specific PlanWeekBlock <div className="mt-6"> that has this exact
  // heading as an immediate child — a Playwright CSS-extension selector, not XPath, and
  // no new data-testid is added to production code for this (the two week headings are
  // already unique strings).
  return page.locator(`div:has(> h2:text("${headingText}"))`);
}

test("a real two-gameweek plan solve renders the verbatim wait copy and both per-week blocks", async ({
  page,
}) => {
  test.setTimeout(90_000);

  await gotoReady(page, `/team?entry=${ENTRY}&tab=rate`);

  // D-20's deep-link exception: ?tab=rate auto-fetches the rating immediately.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("rajat");
  await expect(page.getByRole("heading", { name: "Plan transfers" })).toBeVisible();

  await page.getByLabel("Plan over").selectOption("2");

  const responsePromise = page.waitForResponse((r) => r.url().includes("/api/plan"));
  await page.getByRole("button", { name: "Plan my transfers" }).click();

  // Verbatim wait copy (D-15) — the multi-gameweek clause only appears above horizon 1.
  await expect(page.getByRole("status")).toHaveText(
    "Planning 2 gameweeks jointly… (a fresh horizon takes ~10-60s while future gameweeks are predicted)",
  );

  const body = (await (await responsePromise).json()) as PlanResponse;

  // Proves the per-gameweek frozen pools are wired through _gw_pools: two consecutive
  // gameweeks starting at the frozen current gameweek.
  expect(body.weeks).toHaveLength(2);
  expect(body.weeks[0].gw).toBe(GW);
  expect(body.weeks[1].gw).toBe(GW + 1);

  const headings = ["GW3 — do this now", "GW4 — planned"];
  expect(headings[0]).toBe(`GW${body.weeks[0].gw} — do this now`);
  expect(headings[1]).toBe(`GW${body.weeks[1].gw} — planned`);

  for (const [i, heading] of headings.entries()) {
    const week = body.weeks[i];
    const block = weekBlock(page, heading);
    await expect(block).toBeVisible();

    // Moves tile: paired lines or Hold, according to that week's own buys — hits clause
    // omitted entirely at zero hits, free-transfers-carried figure always present.
    if (week.buys.length > 0) {
      await expect(block.getByText("Hold", { exact: true })).toHaveCount(0);
      const moveText = await block.locator("p", { hasText: "→" }).allTextContents();
      for (const buy of week.buys) {
        expect(moveText.some((t) => t.includes(buy.name))).toBe(true);
      }
      for (const sell of week.sells) {
        expect(moveText.some((t) => t.includes(sell.name))).toBe(true);
      }
    } else {
      await expect(block.getByText("Hold", { exact: true })).toBeVisible();
    }
    const hitsClause = week.hits ? `, −${4 * week.hits} pts in hits` : "";
    await expect(
      block.getByText(
        `${week.buys.length} transfer(s)${hitsClause} · ${week.free_transfers_after} FT carried to next GW`,
        { exact: true },
      ),
    ).toBeVisible();

    // Projected XI tile: this week's xP, captain and bank.
    await expect(block.getByText(`${week.xi_xp}`)).toBeVisible();
    await expect(block.getByText(`captain ${week.captain}`, { exact: false })).toBeVisible();
    await expect(
      block.getByText(`bank £${week.bank.toFixed(1)}m`, { exact: false }),
    ).toBeVisible();

    // Squad section: open only for week one (index 0).
    const details = block.locator("details");
    if (i === 0) {
      await expect(details).toHaveAttribute("open", "");
    } else {
      await expect(details).not.toHaveAttribute("open", "");
    }
  }

  // Week one's pitch renders all 15 cards (view-only — PlanTransfers.tsx passes no
  // onMark, so this pitch carries no `{name} actions` triggers, unlike team-solver's).
  const week1Block = weekBlock(page, headings[0]);
  let week1Cards = 0;
  for (const label of ["Goalkeeper", "Defenders", "Midfielders", "Forwards", "Bench"] as const) {
    week1Cards += await week1Block.getByRole("group", { name: label }).locator("> div").count();
  }
  expect(week1Cards).toBe(15);

  await expect(
    page.getByText(
      "Week one is the decision to act on; later weeks are the current plan and will re-optimise as prices, injuries and form move.",
    ),
  ).toBeVisible();
});
