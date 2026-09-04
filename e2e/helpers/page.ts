import type { Page } from "@playwright/test";
import capture from "../fixtures/v1/normal/api/capture.json" with { type: "json" };

/* Single source of truth for the frozen instant and identifiers every spec pins to --
 * no spec restates frozen_now_utc, gw, entry or picks_event itself. Re-derive these from
 * e2e/fixtures/v1/normal/api/capture.json only, never hardcode a second copy of them. */
export const FROZEN_NOW = new Date(capture.frozen_now_utc);
export const GW = capture.gw;
export const ENTRY = capture.entry;
export const PICKS_EVENT = capture.picks_event;

export interface GotoReadyOptions {
  viewport?: { width: number; height: number };
}

/**
 * Navigates to `path` with the browser clock pinned to FROZEN_NOW and, once navigation
 * completes, waits for every requested web font to finish loading before returning.
 *
 * Ordering matters in both directions:
 * - The clock MUST be pinned BEFORE `page.goto` -- a clock installed after navigation
 *   does not retroactively affect timers/Date reads already scheduled during the initial
 *   render (e.g. GwBanner's own `useState(() => Date.now())` initializer), so a spec that
 *   pins the clock after navigating can read a real wall-clock value from that first
 *   render and assert against the wrong string.
 * - The font wait MUST happen AFTER navigation, inside the page itself
 *   (`document.fonts.ready`) -- the `@fontsource/*` families load asynchronously, and
 *   every bounding-box measurement this suite makes (shell-geometry.spec.ts) depends on
 *   the swapped-in font's real metrics. Measuring before the swap reads pre-swap numbers.
 *   There is no fixed-duration sleep anywhere in this helper -- `document.fonts.ready` is
 *   itself a promise that resolves exactly when loading is done, no polling required.
 */
export async function gotoReady(
  page: Page,
  path: string,
  opts: GotoReadyOptions = {},
): Promise<void> {
  if (opts.viewport) {
    await page.setViewportSize(opts.viewport);
  }
  await page.clock.setFixedTime(FROZEN_NOW);
  await page.goto(path);
  await page.evaluate(() => document.fonts.ready);
}

export interface OriginWatch {
  /** Every request URL observed so far whose origin is not the page's own test origin. */
  getForeignRequests(): string[];
}

/**
 * Attaches a request listener that records any request whose URL does not share the
 * suite's own test origin. Called BEFORE the first navigation (per the smoke spec's own
 * sequencing), so the test origin cannot be read off `page.url()` at call time -- it is
 * `about:blank` until the first navigation lands. Instead, the FIRST top-level
 * navigation request observed on the page's main frame establishes the origin baseline;
 * every request after that (including later same-page navigations, e.g. to `/team`) is
 * compared against it. Lets a spec assert the suite's own network isolation instead of
 * merely assuming it: no request made during a spec run may reach
 * `fantasy.premierleague.com` or any other host.
 */
export function watchOrigin(page: Page): OriginWatch {
  const foreign: string[] = [];
  let testOrigin: string | null = null;
  page.on("request", (request) => {
    const requestOrigin = new URL(request.url()).origin;
    if (testOrigin === null) {
      if (request.isNavigationRequest() && request.frame() === page.mainFrame()) {
        testOrigin = requestOrigin;
      }
      return; // can't judge foreign-ness before the test origin is established
    }
    if (requestOrigin !== testOrigin) {
      foreign.push(request.url());
    }
  });
  return {
    getForeignRequests: () => foreign,
  };
}
