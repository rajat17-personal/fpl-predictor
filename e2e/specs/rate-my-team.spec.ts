import { test, expect, type Page } from "@playwright/test";
import { gotoReady, FROZEN_NOW, ENTRY, PICKS_EVENT } from "../helpers/page";

/*
 * Rate-my-team flow (E2E-04) -- the four tiles, the single-pitch visual diff, and the
 * empty/pending/failure states around them, all against a real GET /api/rate/{entry} call
 * over the frozen GW3 pool (D-10). No Playwright route-interception mocking anywhere in
 * this file -- the rating always comes from the real fixture-fed API.
 *
 * Every expected literal below (tile values/details, the swap line, the pitch's per-row
 * counts) was hand-derived once by booting the fixture-mode server locally and reading its
 * real /api/rate/6980093 response directly, per D-15 -- never re-derived from the response
 * at test time inside a formatting/logic path this file is meant to be testing:
 *
 *   score=83, xi_xp=26.67, xi_p10=12.6, xi_p90=40.7, ideal_xi_xp=32.21, captain=Haaland,
 *   best_move={sell:[Mateta], buy:[Wissa], xp_gain:1.12}, manager={team_name:"rajat",
 *   manager:"", overall_points:133, overall_rank:4180581, gw_points:95}, free_transfers=2.
 *
 * manager.manager is "" (Task 1's checkpoint-approved scrub-names policy blanked both name
 * fields on entries/6980093/summary.json, 04-01-SUMMARY.md) -- RateTab.tsx's `manager.manager
 * ? <span>...` guard is therefore never rendered here, and the heading is the bare team name.
 *
 * Task 2 extends this file with the single-pitch visual diff (ghost card, outgoing label,
 * swap line) -- see the header note it adds there for a discovered rendering gap in how the
 * ghost/outgoing cards land when the sell target is a benched player, not a starter.
 */

const BAD_ENTRY = 9999999;

/** Scopes a locator to one Tile's own three <p> children (heading/value/detail, RateTab.tsx's
 * Tile component) via the heading text -- avoids matching a duplicate string rendered
 * elsewhere on the page (e.g. "Haaland" also appears as a pitch card name). */
function tileParas(page: Page, heading: string) {
  return page.locator(`div:has(> p:text-is("${heading}")) > p`);
}
function tileValue(page: Page, heading: string) {
  return tileParas(page, heading).nth(1);
}
function tileDetail(page: Page, heading: string) {
  return tileParas(page, heading).nth(2);
}

test.describe("Rate tab: empty state and fetch discipline", () => {
  test("no entry: the load-a-team prompt renders and fires no rate request", async ({ page }) => {
    let rateRequested = false;
    page.on("request", (req) => {
      if (req.url().includes("/api/rate/")) {
        rateRequested = true;
      }
    });

    await gotoReady(page, "/team?tab=rate");

    await expect(
      page.getByText("Load a team on the Squad tab to rate it against the model's optimum."),
    ).toBeVisible();
    expect(rateRequested).toBe(false);
  });

  test("only the mounted panel fetches: the Squad tab fires nothing, switching to Rate fires exactly one (D-20)", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    let rateRequestCount = 0;
    page.on("request", (req) => {
      if (req.url().includes(`/api/rate/${ENTRY}`)) {
        rateRequestCount++;
      }
    });

    // Squad tab is the active tab (default) -- Team.tsx mounts only the active panel, so
    // RateTab (and its fetch) does not exist in the tree at all yet.
    expect(rateRequestCount).toBe(0);

    const responsePromise = page.waitForResponse((r) => r.url().includes(`/api/rate/${ENTRY}`));
    await page.getByRole("tab", { name: "Rate my team" }).click();
    await responsePromise;

    expect(rateRequestCount).toBe(1);
  });
});

test.describe("Rate tab: deep link, pending copy, tiles and failure path", () => {
  test("deep link renders the pending copy, then the manager heading and all four tiles with exact values", async ({
    page,
  }) => {
    // Clock pinned before navigation (suite convention, helpers/page.ts's gotoReady) --
    // inlined here (not via gotoReady) because the response listener must be attached
    // BEFORE page.goto fires the request that a mount-triggered (not click-triggered)
    // fetch issues almost immediately once the SPA hydrates.
    await page.clock.setFixedTime(FROZEN_NOW);
    const rateResponsePromise = page.waitForResponse((r) => r.url().includes(`/api/rate/${ENTRY}`));
    await page.goto(`/team?entry=${ENTRY}&tab=rate`);

    await expect(page.getByRole("status")).toHaveText("Solving your squad…");
    const rateBody = await (await rateResponsePromise).json();
    await expect(page.getByRole("status")).toHaveCount(0);
    await page.evaluate(() => document.fonts.ready);

    // Heading: frozen team name, no manager-name segment (see this file's header comment).
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("rajat");

    // Boundary (edge coverage): the API clamps score at min(score, 100). This frozen rating
    // (score=83) never reaches the clamp itself -- a rating exactly at 100 cannot be
    // exercised without mutating the immutable v1 fixture (D-08) -- but the structural half
    // of the boundary (<=100, "/100" suffix, never empty/101) is asserted generically here
    // in addition to the exact literal.
    const scoreText = await tileValue(page, "Team score").textContent();
    const scoreMatch = scoreText?.match(/^(\d+)\/100$/);
    expect(scoreMatch, `score tile value "${scoreText}" must read as an integer over /100`).not.toBeNull();
    expect(Number(scoreMatch![1])).toBeLessThanOrEqual(100);
    expect(scoreText).toBe("83/100");
    expect(rateBody.score).toBe(83);

    // Precision (edge coverage): xi_p10/xi_p90 are non-null on this frozen rating, so the
    // interval clause is present, in exactly the decimal form the API returned -- the
    // wholly-absent branch (xi_p10 null) is not exercised by this real capture, matching
    // 04-04-SUMMARY.md's precedent of documenting an edge case the frozen data cannot reach
    // rather than mutating the immutable fixture to force it.
    expect(rateBody.xi_p10).not.toBeNull();
    await expect(tileDetail(page, "Team score")).toHaveText(
      "best XI xP 26.67 (12.6–40.7 in 8/10 GWs) vs ideal 32.21",
    );

    await expect(tileValue(page, "Season so far")).toHaveText("133 pts");
    await expect(tileDetail(page, "Season so far")).toHaveText(
      "overall rank 4,180,581 · last GW 95 pts",
    );

    await expect(tileValue(page, "Captain")).toHaveText("Haaland");
    await expect(tileDetail(page, "Captain")).toHaveText("best armband in your current squad");

    // Best-move tile, both branches (Task 1): this frozen rating produces a real
    // suggestion, not Hold -- the Hold branch is not exercised by this capture, documented
    // here rather than forced (D-08).
    expect(rateBody.best_move).not.toBeNull();
    await expect(tileValue(page, "Best move")).toHaveText("Mateta → Wissa");
    await expect(tileDetail(page, "Best move")).toHaveText("+1.12 xP this gameweek");
  });

  test("rate failure renders the couldn't-rate copy with the API's own detail text", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${BAD_ENTRY}&tab=rate`);

    // api/main.py's _fetch_entry_picks 404 detail, surfaced verbatim by fetchRate's
    // detail-extraction (mirrors SquadTab.tsx's fetchTeam, 04-05-SUMMARY.md's Rule 1 fix).
    const detail = `entry ${BAD_ENTRY}: no picks for GW${PICKS_EVENT} (bad id, or the season hasn't started)`;
    await expect(
      page.getByText(`Couldn't rate that team: ${detail}. Check the ID and try again.`),
    ).toBeVisible();
  });
});
