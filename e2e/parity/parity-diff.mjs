#!/usr/bin/env node
// e2e/parity/parity-diff.mjs -- machine-compares one live page across the
// vanilla and react-mode servers scripts/dual_site.sh boots (Phase 7,
// CUT-01, D-05). Imports `chromium` from the already human-approved
// @playwright/test@1.62.1 pin in e2e/node_modules (resolved by walking up
// from e2e/parity/) -- no new package install.
//
// Usage:
//   node e2e/parity/parity-diff.mjs --page /
//     [--vanilla-origin http://127.0.0.1:8000]
//     [--react-origin http://127.0.0.1:8001]
//
// Before comparing anything, asserts both origins are serving the SAME live
// export: fetches /data/meta.json from each origin and from the on-disk
// web/data/meta.json, and aborts non-zero with an explicit message if the
// three are not byte-identical. That guard is what stops a fixture-mode or
// stale-build server from masquerading as a live one -- this script must
// never be pointed at anything but two live, same-instant processes.

import { chromium } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..", "..");

function parseArgs(argv) {
  const args = {
    page: null,
    vanillaOrigin: "http://127.0.0.1:8000",
    reactOrigin: "http://127.0.0.1:8001",
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--page") {
      args.page = argv[++i];
    } else if (a === "--vanilla-origin") {
      args.vanillaOrigin = argv[++i];
    } else if (a === "--react-origin") {
      args.reactOrigin = argv[++i];
    }
  }
  return args;
}

async function fetchText(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`GET ${url} -> HTTP ${res.status}`);
  }
  return res.text();
}

// D-05's live-data guard: abort unless the vanilla origin, the react origin
// and the on-disk export are all reading the exact same live web/data
// snapshot at this instant.
async function assertSameLiveExport(vanillaOrigin, reactOrigin) {
  const onDiskPath = path.join(ROOT, "web", "data", "meta.json");
  const onDisk = readFileSync(onDiskPath, "utf-8");
  const [vanillaMeta, reactMeta] = await Promise.all([
    fetchText(`${vanillaOrigin}/data/meta.json`),
    fetchText(`${reactOrigin}/data/meta.json`),
  ]);
  if (vanillaMeta !== onDisk || reactMeta !== onDisk) {
    console.error(
      "FAILED: /data/meta.json is not byte-identical across the vanilla " +
        "origin, the react origin, and the on-disk web/data/meta.json. Both " +
        "servers must be reading the same live export at the same instant " +
        "-- a fixture-mode or stale-build server cannot masquerade as a " +
        "live one.",
    );
    console.error(`  on-disk       : ${onDisk}`);
    console.error(`  vanilla origin: ${vanillaMeta}`);
    console.error(`  react origin  : ${reactMeta}`);
    process.exit(1);
  }
}

// Strips every character outside letters/digits/space/period/apostrophe/
// hyphen -- removes vanilla's inline status-flag glyph (✕/▲) and React's
// status-flag button glyph symmetrically -- then collapses whitespace runs.
function normalizeName(raw) {
  return raw
    .replace(/[^\p{L}\p{N} .'-]/gu, "")
    .replace(/\s+/g, " ")
    .trim();
}

// Team/price cells: collapse whitespace and trim only, no character
// stripping.
function normalizePlain(raw) {
  return raw.replace(/\s+/g, " ").trim();
}

// Per row: cell 2 (player name), cell 3 (team short), cell 4 (price). The
// vanilla and react tables do not share a selector (the accessible name was
// only added on the React side), so the caller passes a per-origin row
// selector.
async function extractRows(page, rowSelector) {
  const rowLocator = page.locator(rowSelector);
  const count = await rowLocator.count();
  const rows = [];
  for (let i = 0; i < count; i++) {
    const cells = await rowLocator.nth(i).locator("td").allInnerTexts();
    rows.push({
      name: normalizeName(cells[1] ?? ""),
      team: normalizePlain(cells[2] ?? ""),
      price: normalizePlain(cells[3] ?? ""),
    });
  }
  return rows;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.page) {
    console.error("FAILED: --page <route> is required");
    process.exit(1);
  }
  if (args.page !== "/") {
    console.error(
      `FAILED: only --page / is supported by this build of parity-diff.mjs (got ${args.page})`,
    );
    process.exit(1);
  }

  await assertSameLiveExport(args.vanillaOrigin, args.reactOrigin);

  const browser = await chromium.launch();
  try {
    const vanillaPage = await browser.newPage();
    const reactPage = await browser.newPage();

    // Deliberately NOT pinning the clock (unlike e2e/helpers/page.ts's
    // gotoReady) -- the whole point of this comparison is two live
    // processes serving the same live data at the same real instant.
    await vanillaPage.goto(`${args.vanillaOrigin}/index.html`);
    await vanillaPage.evaluate(() => document.fonts.ready);

    await reactPage.goto(`${args.reactOrigin}/`);
    await reactPage.evaluate(() => document.fonts.ready);

    const vanillaRows = await extractRows(vanillaPage, "table#xp tbody tr");
    const reactRows = await extractRows(
      reactPage,
      'table[aria-label="xP table"] tbody tr',
    );

    const rowsCompared = Math.min(vanillaRows.length, reactRows.length);
    let mismatches = 0;
    for (let i = 0; i < rowsCompared; i++) {
      const v = vanillaRows[i];
      const r = reactRows[i];
      if (v.name !== r.name || v.team !== r.team || v.price !== r.price) {
        mismatches++;
        console.log(
          `row ${i}: vanilla=(${v.name} | ${v.team} | ${v.price}) ` +
            `react=(${r.name} | ${r.team} | ${r.price})`,
        );
      }
    }
    if (vanillaRows.length !== reactRows.length) {
      console.log(
        `row count mismatch: vanilla=${vanillaRows.length} react=${reactRows.length}`,
      );
    }

    console.log(`rows compared: ${rowsCompared}`);

    if (
      vanillaRows.length !== reactRows.length ||
      rowsCompared === 0 ||
      mismatches > 0
    ) {
      process.exitCode = 1;
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(`FAILED: ${err && err.stack ? err.stack : err}`);
  process.exit(1);
});
