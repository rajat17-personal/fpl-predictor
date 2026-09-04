import { defineConfig, devices } from "@playwright/test";
import type { PlaywrightTestConfig } from "@playwright/test";
import path from "node:path";

/*
 * This config owns the FULL server lifecycle for the E2E suite: build the React
 * frontend, boot fixture-mode uvicorn against a frozen fixture set, wait for it to
 * report healthy, then drive Chromium against it. Nothing here talks to a `vite dev`
 * server and there is no "E2E_DEV" escape hatch (D-03) -- local and CI runs boot the
 * exact same topology, so a spec that passes here passes in CI for the same reason.
 *
 * The build is chained AHEAD of uvicorn in the `command` string (`&&`) rather than run
 * as a separate step because `webServer.url`'s health check only starts polling once
 * the command has been spawned -- if uvicorn started before the build finished, the
 * fixture-mode server's `check_dir=False` static mount would happily boot and pass the
 * health check while `frontend/dist/` was still empty or stale, and every navigation to
 * `/` would 404 or serve last run's build. Chaining with `&&` guarantees `dist/` (and
 * `dist/404.html`, which is what makes the SPA client-route fallback work at all) exists
 * before uvicorn's first request can possibly be served.
 *
 * The fixture env vars (FPL_FIXTURE_DIR / FPL_FIXTURE_DATA_DIR) are set ONLY in this
 * file's `webServer.env` blocks, not in a shell script or .env file, so there is exactly
 * one place that decides which frozen data set backs a given run -- reading this file
 * top to bottom tells you the whole story.
 *
 * `locale: "en-GB"` and `timezoneId: "UTC"` (below, in `use`) are mandatory, not
 * cosmetic: frontend/src/lib/deadline.ts's `fmtAbs` calls `toLocaleString(undefined,
 * ...)`, which resolves against the *browser's* locale and timezone. An unpinned locale
 * or timezone makes the gameweek banner render a different string on a developer's own
 * machine than it does in CI -- the same "pass or fail on the calendar" defect class this
 * whole phase exists to eliminate, just for locale/timezone instead of the clock.
 *
 * Local runs MUST set E2E_PYTHON to the project's conda interpreter, e.g.:
 *   E2E_PYTHON=/home/sraja/miniconda3/envs/python314/bin/python npm run test
 * CI relies on `python` already being correctly on PATH (set up by the CI workflow,
 * Phase 5) and never needs E2E_PYTHON set explicitly.
 */

const ROOT = path.resolve(import.meta.dirname, "..");
const PYTHON = process.env.E2E_PYTHON ?? "python";

// Deliberately NOT 8000: a developer's own `uvicorn api.main:app --port 8000` (serving
// the vanilla site from live data) would otherwise be silently adopted by
// `reuseExistingServer` below, and every spec would fail against real, non-deterministic
// live data for a reason nobody would guess from the failure output alone.
const BASE = Number(process.env.E2E_PORT ?? 8100);
const NORMAL_PORT = BASE;
const BLANK_PORT = BASE + 1;
const DGW_PORT = BASE + 2;

const FIXTURE_NORMAL_DIR = path.join(ROOT, "e2e", "fixtures", "v1", "normal");
const FIXTURE_BLANK_DATA_DIR = path.join(ROOT, "e2e", "fixtures", "v1", "blank", "web-data");
const FIXTURE_DGW_DATA_DIR = path.join(ROOT, "e2e", "fixtures", "v1", "dgw", "web-data");

// Correctness over speed: the full, three-server suite is what `npm run test` means by
// default. Set E2E_VARIANTS=0 to skip the blank/dgw servers and projects entirely (one
// uvicorn instead of three) for a fast, focused local run against the normal fixture set.
const VARIANTS_ON = process.env.E2E_VARIANTS !== "0";

const webServer: NonNullable<ReturnType<typeof defineConfig>["webServer"]> = [
  {
    command:
      `npm --prefix frontend run build && ` +
      `${PYTHON} -m uvicorn api.main:app --port ${NORMAL_PORT}`,
    cwd: ROOT,
    url: `http://localhost:${NORMAL_PORT}/api/health`,
    timeout: 180_000, // the frontend build is the slow part, not uvicorn's own boot
    reuseExistingServer: !process.env.CI,
    env: { FPL_FIXTURE_DIR: FIXTURE_NORMAL_DIR },
  },
];

if (VARIANTS_ON) {
  // No `npm run build` chained here -- the normal entry above already owns the one build
  // this whole run needs, and `check_dir=False` on the fixture-mode static mounts (see
  // api/main.py) is exactly what lets these two servers boot before `dist/` exists.
  webServer.push(
    {
      command: `${PYTHON} -m uvicorn api.main:app --port ${BLANK_PORT}`,
      cwd: ROOT,
      url: `http://localhost:${BLANK_PORT}/api/health`,
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
      env: {
        FPL_FIXTURE_DIR: FIXTURE_NORMAL_DIR,
        FPL_FIXTURE_DATA_DIR: FIXTURE_BLANK_DATA_DIR,
      },
    },
    {
      command: `${PYTHON} -m uvicorn api.main:app --port ${DGW_PORT}`,
      cwd: ROOT,
      url: `http://localhost:${DGW_PORT}/api/health`,
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
      env: {
        FPL_FIXTURE_DIR: FIXTURE_NORMAL_DIR,
        FPL_FIXTURE_DATA_DIR: FIXTURE_DGW_DATA_DIR,
      },
    },
  );
}

const projects: NonNullable<PlaywrightTestConfig["projects"]> = [
  {
    name: "chromium",
    use: { ...devices["Desktop Chrome"], baseURL: `http://localhost:${NORMAL_PORT}` },
    testIgnore: "specs/variants/**",
  },
];

if (VARIANTS_ON) {
  projects.push(
    {
      name: "chromium-blank",
      use: { ...devices["Desktop Chrome"], baseURL: `http://localhost:${BLANK_PORT}` },
      testMatch: "specs/variants/blank-*.spec.ts",
    },
    {
      name: "chromium-dgw",
      use: { ...devices["Desktop Chrome"], baseURL: `http://localhost:${DGW_PORT}` },
      testMatch: "specs/variants/dgw-*.spec.ts",
    },
  );
}

export default defineConfig({
  testDir: "./specs",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [["line"], ["html", { outputFolder: "playwright-report" }]],
  use: {
    locale: "en-GB",
    timezoneId: "UTC",
  },
  // Chromium only (D-13) -- no other browser engine's project is ever added in this phase.
  projects,
  webServer,
});
