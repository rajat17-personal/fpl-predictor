import { test, expect, type Page } from "@playwright/test";
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
 *
 * Every solve below is a genuine POST to /api/solve, run by the real PuLP/CBC ILP over
 * the frozen prediction pool (D-10) — no Playwright route-mock interception anywhere in this file.
 * Task 2's structural invariants (legal squad shape, budget, hit/hold agreement) hold for
 * ANY optimum the solver lands on; only the pinned golden further down pins one exact
 * result (D-11).
 */

/** The bounded knobs SolveControls.tsx mirrors from SolveRequest's own server-side
 * Field(ge=…, le=…) constraints (api/main.py:346-354, config.py's MAX_FREE_TRANSFERS). */
const MAX_FREE_TRANSFERS = 5;
const BUDGET = 100.0;
const POSITION_QUOTA = { GK: 2, DEF: 5, MID: 5, FWD: 3 };

async function openCardMenu(page: Page, name: string) {
  await page.getByRole("button", { name: `${name} actions` }).click();
  return page.getByRole("menu", { name: `${name} actions` });
}

async function cardActionsNames(page: Page): Promise<string[]> {
  return page
    .locator('[aria-label$=" actions"]')
    .evaluateAll((els) => els.map((el) => el.getAttribute("aria-label")!.replace(/ actions$/, "")));
}

async function rowCount(
  page: Page,
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

test.describe("Squad tab: solve flow", () => {
  test("a real solve returns a legal squad and updates the same pitch in place", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    const solveButton = page.getByRole("button", { name: "Solve transfers" });
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("/api/solve") && r.request().method() === "POST",
    );
    await solveButton.click();
    await expect(page.getByRole("status")).toHaveText("Solving your transfers…");
    await expect(solveButton).toBeDisabled();

    const body = await (await responsePromise).json();

    // D-11's structural invariants: hold for whichever optimum CBC lands on.
    expect(body.squad).toHaveLength(15);
    expect(body.squad.filter((p: { starting: boolean }) => p.starting)).toHaveLength(11);
    expect(body.squad.filter((p: { captain: boolean }) => p.captain)).toHaveLength(1);
    const byPos: Record<string, number> = {};
    for (const p of body.squad as { position: string }[]) {
      byPos[p.position] = (byPos[p.position] ?? 0) + 1;
    }
    expect(byPos).toEqual(POSITION_QUOTA);
    const totalCost = (body.squad as { price_m: number }[]).reduce((s, p) => s + p.price_m, 0);
    expect(totalCost).toBeLessThanOrEqual(BUDGET);

    // Same pitch, updated in place (D-16) — never a second pitch: the rendered card set
    // equals the response's own name set, one-to-one.
    await expect(page.locator('[aria-label$=" actions"]')).toHaveCount(15);
    const cardNames = await cardActionsNames(page);
    const responseNames = (body.squad as { name: string }[]).map((p) => p.name);
    expect(new Set(cardNames)).toEqual(new Set(responseNames));
  });

  test("the results bar mirrors the solve response (moves, hits, bank, captain)", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    const responsePromise = page.waitForResponse((r) => r.url().includes("/api/solve"));
    await page.getByRole("button", { name: "Solve transfers" }).click();
    const body = await (await responsePromise).json();

    const bar = page.getByTestId("solve-results-bar");
    await expect(bar).toBeVisible();

    const sells = body.sells as { name: string; position: string }[];
    const buys = body.buys as { name: string; position: string }[];
    if (buys.length > 0) {
      const moveLines = bar.locator("ul > li");
      // pairMoves buckets sells/buys by position and zips within each bucket — #lines ==
      // #buys == #sells always (a transfer swaps one player for one player of the same
      // position, per config.POSITION_QUOTA being held exactly). Verified structurally
      // here (set membership + same-position pairing), never by re-deriving the exact
      // sell<->buy pairing algorithm under test.
      await expect(moveLines).toHaveCount(buys.length);
      const lineTexts = await moveLines.allTextContents();
      for (const text of lineTexts) {
        expect(text).toContain("→");
        const matchedSell = sells.find((s) => text.includes(s.name));
        const matchedBuy = buys.find((b) => text.includes(b.name));
        expect(matchedSell, `line ${JSON.stringify(text)} names a real sell`).toBeTruthy();
        expect(matchedBuy, `line ${JSON.stringify(text)} names a real buy`).toBeTruthy();
        expect(text).toContain(matchedSell!.position);
        expect(matchedSell!.position).toBe(matchedBuy!.position);
      }
      await expect(bar.getByText("Hold", { exact: true })).toHaveCount(0);
    } else {
      await expect(bar.getByText("Hold", { exact: true })).toBeVisible();
    }

    // The hit-cost line is omitted ENTIRELY at zero hits — never rendered as "0 pts".
    if (body.hits > 0) {
      await expect(bar.getByText(`−${4 * body.hits} pts in hits`)).toBeVisible();
    } else {
      await expect(bar.getByText(/pts in hits/)).toHaveCount(0);
    }

    await expect(bar.getByText(`Bank £${body.bank_after.toFixed(1)}m`, { exact: true })).toBeVisible();
    await expect(bar.getByText(`Captain ${body.captain}`, { exact: true })).toBeVisible();
  });

  test("the incoming badge diff is against the as-loaded squad and is idempotent on a repeat solve", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);
    const asLoadedNames = new Set(await cardActionsNames(page));

    async function badgeState(names: string[]): Promise<boolean[]> {
      const out: boolean[] = [];
      for (const name of names) {
        const count = await page
          .getByRole("button", { name: `${name} actions` })
          .getByLabel("New signing this transfer")
          .count();
        out.push(count > 0);
      }
      return out;
    }

    const solveButton = page.getByRole("button", { name: "Solve transfers" });
    let responsePromise = page.waitForResponse((r) => r.url().includes("/api/solve"));
    await solveButton.click();
    const body = await (await responsePromise).json();
    const squadNames = (body.squad as { name: string }[]).map((p) => p.name);

    const firstBadges = await badgeState(squadNames);
    squadNames.forEach((name, i) => {
      expect(firstBadges[i], `${name} IN-badge state`).toBe(!asLoadedNames.has(name));
    });

    // Solving again with the identical (unchanged) inputs must leave the badge set
    // unchanged — the diff is computed against the as-loaded squad, never the previous
    // solve result (D-16).
    responsePromise = page.waitForResponse((r) => r.url().includes("/api/solve"));
    await solveButton.click();
    await responsePromise;
    const secondBadges = await badgeState(squadNames);
    expect(secondBadges).toEqual(firstBadges);
  });

  test("locked players are present, an excluded player is absent, and marks survive the solve", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    async function mark(name: string, action: string) {
      const menu = await openCardMenu(page, name);
      await menu.getByRole("menuitem", { name: action }).click();
    }

    // Mateta (injured, xp=0) would otherwise be sold by the default solve (see the pinned
    // golden below) — locking it is a real test that the lock forces a keep. Diop is a
    // second, uncontested lock. Haaland (the default solve's own captain) is excluded to
    // force a genuinely different squad, not a no-op.
    await mark("Mateta", "Lock in squad");
    await mark("Diop", "Lock in squad");
    await mark("Haaland", "Exclude from squad");

    const responsePromise = page.waitForResponse((r) => r.url().includes("/api/solve"));
    await page.getByRole("button", { name: "Solve transfers" }).click();
    const body = await (await responsePromise).json();

    const names = (body.squad as { name: string }[]).map((p) => p.name);
    expect(names).toContain("Mateta");
    expect(names).toContain("Diop");
    expect(names).not.toContain("Haaland");

    // Marks are only cleared by Reset (D-17) — still displayed after this solve. Haaland's
    // own excluded badge cannot be checked visually (its card left the pitch along with the
    // player), but the two locks' badges are still on the pitch.
    await expect(page.getByLabel("Locked — always included in solve")).toHaveCount(2);
  });

  test("solve control bounds mirror the server's declared constraints", async ({ page }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    const freeTransfers = page.getByLabel("Free transfers");
    await expect(freeTransfers).toHaveAttribute("min", "0");
    await expect(freeTransfers).toHaveAttribute("max", String(MAX_FREE_TRANSFERS));

    const maxTransfers = page.getByLabel("Max transfers");
    await expect(maxTransfers).toHaveAttribute("min", "0");
    await expect(maxTransfers).toHaveAttribute("max", "15");

    const horizon = page.getByLabel("Plan horizon");
    const options = horizon.locator("option");
    await expect(options).toHaveCount(5);
    const values = await options.evaluateAll((els) => els.map((el) => el.getAttribute("value")));
    expect(values).toEqual(["1", "2", "3", "4", "6"]);
  });

  test("Reset to loaded squad restores the as-loaded fifteen with no network request", async ({
    page,
  }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);
    const asLoadedNames = new Set(await cardActionsNames(page));

    await (await openCardMenu(page, "Shaw")).getByRole("menuitem", { name: "Lock in squad" }).click();
    const responsePromise = page.waitForResponse((r) => r.url().includes("/api/solve"));
    await page.getByRole("button", { name: "Solve transfers" }).click();
    await responsePromise;
    await expect(page.getByTestId("solve-results-bar")).toBeVisible();

    let requested = false;
    page.on("request", (req) => {
      if (req.url().includes("/api/")) {
        requested = true;
      }
    });
    await page.getByRole("button", { name: "Reset to loaded squad" }).click();

    await expect(page.getByTestId("solve-results-bar")).toHaveCount(0);
    await expect(page.getByLabel("Locked — always included in solve")).toHaveCount(0);
    await expect(page.getByLabel("Excluded from solve")).toHaveCount(0);
    await expect(page.locator('[aria-label$=" actions"]')).toHaveCount(15);
    expect(new Set(await cardActionsNames(page))).toEqual(asLoadedNames);
    expect(requested).toBe(false);
  });

  test("a rejected solve surfaces the server's own detail text", async ({ page }) => {
    await gotoReady(page, `/team?entry=${ENTRY}`);

    // buildSolveRequest only ever sends numeric player_code locks/excludes (D-15's
    // "never free-text names" client invariant) — no UI control can submit a name string,
    // so the server's `_resolve()` player-not-found path (api/main.py:337) is unreachable
    // through ordinary interaction alone. To exercise this REAL server-side error path
    // (not a mocked response — the request still makes a genuine round trip to the real
    // /api/solve) without a Playwright route mock, this test wraps window.fetch to inject one
    // extra, non-existent string lock into the one outgoing /api/solve request's own body
    // just before it goes over the wire. Documented as a deviation in 04-05-SUMMARY.md.
    await page.evaluate(() => {
      const original = window.fetch.bind(window);
      window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
        const url = typeof input === "string" ? input : input.toString();
        if (url === "/api/solve" && init?.body) {
          const parsed = JSON.parse(init.body as string) as { locks?: (number | string)[] };
          parsed.locks = [...(parsed.locks ?? []), "ZzzzzNotARealPlayerXyz"];
          init = { ...init, body: JSON.stringify(parsed) };
        }
        return original(input, init);
      };
    });

    const responsePromise = page.waitForResponse((r) => r.url().includes("/api/solve"));
    await page.getByRole("button", { name: "Solve transfers" }).click();
    await responsePromise;

    await expect(
      page.getByText(
        "Couldn't solve: player not found in this gameweek: 'ZzzzzNotARealPlayerXyz'. Check your inputs and try again.",
      ),
    ).toBeVisible();
  });
});

test.describe("Squad tab: pinned golden solve (D-11)", () => {
  test("REPIN POINT: the canonical zero-marks solve pins its exact XI, captain, moves, bank and XI xP", async ({
    page,
  }) => {
    // Hand-derived ONCE by running this exact request (entry 6980093, free_transfers=1,
    // horizon=1, no locks/excludes — SolveControls.tsx's own defaults) against the
    // committed e2e/fixtures/v1/normal fixture set during planning (see 04-05-SUMMARY.md
    // for the full response and the PuLP/CBC version observed at pin time). THIS IS THE
    // SINGLE RE-PIN POINT for the whole suite: if a future CBC/solver version bump ever
    // flips this particular optimal tie, only this one test needs re-deriving and
    // updating — every other solve assertion in this file is deliberately structural
    // (Task 2), not literal, and is unaffected by which optimum the solver happens to
    // land on.
    await gotoReady(page, `/team?entry=${ENTRY}`);

    const responsePromise = page.waitForResponse((r) => r.url().includes("/api/solve"));
    await page.getByRole("button", { name: "Solve transfers" }).click();
    await responsePromise;

    // Starting XI in rendered row order (GK, then DEF/MID/FWD each ascending by
    // player_code, per Pitch.tsx's splitPitchRows / PitchRow), then the bench in the
    // same ascending-player_code order.
    const XI_IN_ORDER = [
      "Roefs",
      "Shaw",
      "Calafiori",
      "O'Reilly",
      "B.Fernandes",
      "Szoboszlai",
      "Tzolis",
      "Mbeumo",
      "Calvert-Lewin",
      "Wissa",
      "Haaland",
    ];
    const BENCH_IN_ORDER = ["Hughes", "Diop", "Davis", "Kinsky"];
    const cardNames = await cardActionsNames(page);
    expect(cardNames).toEqual([...XI_IN_ORDER, ...BENCH_IN_ORDER]);

    const bar = page.getByTestId("solve-results-bar");
    await expect(bar.locator("ul > li")).toHaveText(["Mateta → Wissa FWD"]);
    await expect(bar.getByText("Hold", { exact: true })).toHaveCount(0);
    await expect(bar.getByText(/pts in hits/)).toHaveCount(0);
    await expect(bar.getByText("Bank £0.3m", { exact: true })).toBeVisible();
    await expect(bar.getByText("XI xP 27.79", { exact: true })).toBeVisible();
    await expect(bar.getByText("Captain Haaland", { exact: true })).toBeVisible();
  });
});
