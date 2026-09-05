import { test, expect } from "@playwright/test";
import { gotoReady, watchOrigin } from "../helpers/page";

/*
 * The tracer (Task 2): ONE path through every layer the harness proves --
 * build -> fixture-mode uvicorn -> real API -> real ILP-backed pool join ->
 * Chromium rendering -> exact expected values. Every literal string/number
 * asserted below is hand-derived ONCE from the committed fixture set
 * (e2e/fixtures/v1/normal/{api,web-data}/*.json) and hardcoded here (D-15) --
 * never recomputed from the JSON at test time, which would re-implement the
 * formatting under test and let a shared bug pass silently.
 *
 * Frozen instant: capture.json's frozen_now_utc = 2026-09-03T16:02:38Z.
 * Deadline (web-data/meta.json): 2026-09-04T17:30:00Z.
 * Generated (web-data/meta.json): 2026-09-03T16:02:38+00:00 -- identical to
 * frozen_now_utc, so the freshness line is "generated just now" (elapsed 0).
 * Countdown (deadline - frozen_now = 1 day, 1 hour, 27 minutes, 22 seconds):
 * fmtRel's day-bucket keeps only whole days + whole hours -> "in 1d 1h".
 * fmtAbs (en-GB, UTC, weekday/day/month/hour/minute) of 2026-09-04T17:30:00Z
 * -> "Fri 4 Sept, 17:30" (verified against Node's own Intl this session).
 */
const BANNER_LINE_1 = "GW3 deadline: Fri 4 Sept, 17:30 · in 1d 1h";
const BANNER_LINE_2 = "generated just now";

test.describe("smoke: one path through the whole stack", () => {
  test("xP table renders the frozen top row and the deadline banner", async ({ page }) => {
    const origin = watchOrigin(page);
    await gotoReady(page, "/");

    await expect(page.getByText(BANNER_LINE_1, { exact: true })).toBeVisible();
    await expect(page.getByText(BANNER_LINE_2, { exact: true })).toBeVisible();

    // First body row of web-data/xp_table.json (already sorted desc by xp;
    // no re-sort applied by the page for the unsorted default view) --
    // B.Fernandes, MID, MUN, 12.0, 48.6% owned, 5.90 Captain xP.
    const table = page.getByRole("table", { name: "xP table" });
    const firstRow = table.locator("tbody tr").first();
    const cells = firstRow.locator("td");
    await expect(cells.nth(0)).toHaveText("MID");
    await expect(cells.nth(1)).toHaveText("B.Fernandes");
    await expect(cells.nth(2)).toHaveText("MUN");
    await expect(cells.nth(3)).toHaveText("12.0");
    await expect(cells.nth(4)).toHaveText("48.6");
    await expect(cells.nth(6)).toHaveText("5.90");

    expect(origin.getForeignRequests()).toEqual([]);
  });

  test("direct navigation to /team?entry=... proves the SPA fallback and the live team fixture", async ({
    page,
  }) => {
    const origin = watchOrigin(page);
    // Direct navigation (never a nav click) -- this is what exercises the
    // SPA dist/404.html fallback (Starlette's html=True mechanism) AND the
    // fixture-mode /api/team/{entry} branch at once.
    await gotoReady(page, "/team?entry=6980093");

    // entries/6980093/summary.json's `name` ("rajat") joined to meta.gw (3):
    // SquadTab.tsx renders `{teamName} · GW{meta.gw}`.
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("rajat · GW3");

    // Reconstructed starting XI (selectLoadedSquad's DEF/MID/FWD search over
    // picks_event2.json joined to xp_table.json by player_code): DEF 4 (top
    // by xp: O'Reilly, Calafiori, Shaw, Diop), MID 4 (B.Fernandes,
    // Szoboszlai, Mbeumo, Tzolis), FWD 2 (Haaland, Calvert-Lewin) maximise
    // joined xp at 21.47 total over every legal (d,m,f) split -- formation
    // "4-4-2" (deriveFormation's DEF-MID-FWD starter counts).
    await expect(page.getByText("4-4-2", { exact: true })).toBeVisible();

    // 11 starters (1 GK + 4 DEF + 4 MID + 2 FWD) + 4 bench (Kinsky, Davis,
    // Hughes, Mateta) = 15 total player cards across the five role="group"
    // rows. The loaded-team pitch always passes onMark (SquadTab.tsx), so
    // every rendered PlayerCard is an `{name} actions` button -- ghost cards
    // (which would NOT carry this aria-label suffix) never appear here since
    // no solve has run.
    await expect(page.locator('[aria-label$=" actions"]')).toHaveCount(15);
    await expect(page.getByRole("group", { name: "Goalkeeper" }).locator("> div")).toHaveCount(1);
    await expect(page.getByRole("group", { name: "Defenders" }).locator("> div")).toHaveCount(4);
    await expect(page.getByRole("group", { name: "Midfielders" }).locator("> div")).toHaveCount(4);
    await expect(page.getByRole("group", { name: "Forwards" }).locator("> div")).toHaveCount(2);
    await expect(page.getByRole("group", { name: "Bench" }).locator("> div")).toHaveCount(4);

    expect(origin.getForeignRequests()).toEqual([]);
  });
});
