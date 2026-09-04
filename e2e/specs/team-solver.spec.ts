import { test, expect } from "@playwright/test";
import { gotoReady, ENTRY, GW, PICKS_EVENT } from "../helpers/page";

/*
 * Team page — Squad tab (E2E-02). Every navigation uses gotoReady (clock pinned before
 * nav, fonts settled after) per the suite-wide convention. `[aria-label$=" actions"]`
 * (PlayerCard.tsx's `{name} actions` trigger) is this file's card-count/name-set proxy for
 * an interactive (loaded/solved) pitch; the default model-squad pitch and the plan-flow
 * pitch (team-plan.spec.ts) render no such trigger at all (no `onMark` passed — 03-01's
 * view-only default and PlanTransfers.tsx's read-only per-week pitch), so counting the
 * five `role="group"` rows' direct children is this file's card-count proxy for those.
 *
 * Task 1's failure-path test drove a real Rule 1 fix in frontend/src/components/team/
 * SquadTab.tsx: teamQuery used lib/api.ts's fetchApi, which discards a non-ok response's
 * body (only the HTTP status code survives) — unlike this same file's own postSolve,
 * RateTab.tsx's fetchRate and PlanTransfers.tsx's postPlan, all three of which already
 * carry a custom fetch specifically BECAUSE fetchApi cannot reproduce a detail-bearing
 * error copy. teamQuery was the one fetch in this file that had NOT been given the same
 * treatment. See 04-05-SUMMARY.md's Deviations section.
 */

async function openCardMenu(page: import("@playwright/test").Page, name: string) {
  await page.getByRole("button", { name: `${name} actions` }).click();
  return page.getByRole("menu", { name: `${name} actions` });
}

async function cardActionsNames(page: import("@playwright/test").Page): Promise<string[]> {
  return page
    .locator('[aria-label$=" actions"]')
    .evaluateAll((els) => els.map((el) => el.getAttribute("aria-label")!.replace(/ actions$/, "")));
}

async function rowCount(
  page: import("@playwright/test").Page,
  label: "Goalkeeper" | "Defenders" | "Midfielders" | "Forwards" | "Bench",
): Promise<number> {
  return page.getByRole("group", { name: label }).locator("> div").count();
}

test.describe("Squad tab: default view (no entry)", () => {
  test("renders the model squad view-only, with no team auto-submitted", async ({ page }) => {
    await gotoReady(page, "/team");

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Model squad · GW${GW}`);
    // web-data/squad.json's own formation/count (04-05-SUMMARY.md): 3-5-2, 15 total.
    await expect(page.getByText("3-5-2", { exact: true })).toBeVisible();
    expect(await rowCount(page, "Goalkeeper")).toBe(1);
    expect(await rowCount(page, "Defenders")).toBe(3);
    expect(await rowCount(page, "Midfielders")).toBe(5);
    expect(await rowCount(page, "Forwards")).toBe(2);
    expect(await rowCount(page, "Bench")).toBe(4);

    // View-only (03-01's resolved Claude's-Discretion item): no card exposes an
    // action-menu trigger at all on the default pitch.
    await expect(page.locator('[aria-label$=" actions"]')).toHaveCount(0);

    // D-10: 6980093 is placeholder/example text only, never auto-submitted.
    const input = page.getByLabel("FPL team ID");
    await expect(input).toHaveValue("");
    await expect(input).toHaveAttribute("placeholder", /6980093/);
    expect(page.url()).not.toContain("entry=");
  });
});

test.describe("Squad tab: loading a team by entry id", () => {
  test("Load team switches to the loaded squad on the pitch", async ({ page }) => {
    await gotoReady(page, "/team");

    await page.getByLabel("FPL team ID").fill(String(ENTRY));
    await page.getByRole("button", { name: "Load team" }).click();

    await expect(page).toHaveURL(new RegExp(`entry=${ENTRY}`));
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`rajat · GW${GW}`);
    // selectLoadedSquad's DEF/MID/FWD search (smoke.spec.ts's own derivation, reused here):
    // formation 4-4-2, 11 starters + 4 bench = 15 total.
    await expect(page.getByText("4-4-2", { exact: true })).toBeVisible();
    await expect(page.locator('[aria-label$=" actions"]')).toHaveCount(15);
    expect(await rowCount(page, "Goalkeeper")).toBe(1);
    expect(await rowCount(page, "Defenders")).toBe(4);
    expect(await rowCount(page, "Midfielders")).toBe(4);
    expect(await rowCount(page, "Forwards")).toBe(2);
    expect(await rowCount(page, "Bench")).toBe(4);
  });

  test("a direct ?entry= deep link auto-loads without any interaction (D-11)", async ({ page }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`rajat · GW${GW}`);
    await expect(page.locator('[aria-label$=" actions"]')).toHaveCount(15);
  });

  test("an empty or non-numeric entry id fires no request and leaves the URL unchanged", async ({
    page,
  }) => {
    await gotoReady(page, "/team");
    let teamRequested = false;
    page.on("request", (req) => {
      if (req.url().includes("/api/team/")) {
        teamRequested = true;
      }
    });

    const input = page.getByLabel("FPL team ID");
    const button = page.getByRole("button", { name: "Load team" });

    await input.fill("");
    await button.click();
    await expect(page).toHaveURL(/\/team$/);

    // Syntactically valid for a <input type="number"> (no `step` restriction), but fails
    // the client-side `/^\d+$/` integer guard — the "non-numeric" case, distinct from
    // "empty", since an actually non-numeric string (e.g. "abc") is sanitised to "" by the
    // browser's own number-input value setter before it ever reaches React state.
    await input.fill("1.5");
    await button.click();
    await expect(page).toHaveURL(/\/team$/);

    expect(teamRequested).toBe(false);
  });

  test("an entry with no frozen picks renders the load error, then Change team recovers", async ({
    page,
  }) => {
    const badEntry = 9999999;
    await gotoReady(page, `/team?entry=${badEntry}`);

    // api/main.py's _fetch_entry_picks 404 detail, surfaced verbatim by the fix documented
    // in this file's header comment (SquadTab.tsx's fetchTeam, not the discarding fetchApi).
    const detail = `entry ${badEntry}: no picks for GW${PICKS_EVENT} (bad id, or the season hasn't started)`;
    await expect(
      page.getByText(`Couldn't load that team: ${detail}. Check the ID and try again.`),
    ).toBeVisible();

    await page.getByRole("button", { name: "Change team" }).click();
    await expect(page).toHaveURL(/\/team$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Model squad · GW${GW}`);
  });

  test("lock/exclude marks badge the card and are cleared by a reload (ephemeral, D-13/D-17)", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    const shawMenu = await openCardMenu(page, "Shaw");
    await expect(shawMenu.getByText("Shaw", { exact: true })).toBeVisible();
    await expect(shawMenu.getByText("MUN", { exact: true })).toBeVisible();
    await expect(shawMenu.getByText("Ownership 16.6%", { exact: true })).toBeVisible();
    await shawMenu.getByRole("menuitem", { name: "Lock in squad" }).click();

    const diopMenu = await openCardMenu(page, "Diop");
    await expect(diopMenu.getByText("Diop", { exact: true })).toBeVisible();
    await expect(diopMenu.getByText("IPS", { exact: true })).toBeVisible();
    await expect(diopMenu.getByText("Ownership 15.8%", { exact: true })).toBeVisible();
    await diopMenu.getByRole("menuitem", { name: "Exclude from squad" }).click();

    await expect(page.getByLabel("Locked — always included in solve")).toHaveCount(1);
    await expect(page.getByLabel("Excluded from solve")).toHaveCount(1);

    // Marks live only in component state (D-13) — a reload clears both badges while the
    // squad itself still loads straight from the URL.
    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`rajat · GW${GW}`);
    await expect(page.getByLabel("Locked — always included in solve")).toHaveCount(0);
    await expect(page.getByLabel("Excluded from solve")).toHaveCount(0);
  });
});
