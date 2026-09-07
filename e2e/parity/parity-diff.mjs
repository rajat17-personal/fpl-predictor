#!/usr/bin/env node
// e2e/parity/parity-diff.mjs -- machine-compares live pages across the
// vanilla and react-mode servers scripts/dual_site.sh boots (Phase 7,
// CUT-01, D-05/D-06/D-07). Walks the eight-page field map exported by
// e2e/parity/extract.mjs and, once the ledger classifier lands (07-02 Task
// 2), routes every collected delta through e2e/parity/ledger.mjs before
// reporting it as a defect. Imports `chromium` from the already
// human-approved @playwright/test@1.62.1 pin in e2e/node_modules (resolved
// by walking up from e2e/parity/) -- no new package install.
//
// Usage:
//   node e2e/parity/parity-diff.mjs --all
//     [--vanilla-origin http://127.0.0.1:8000]
//     [--react-origin http://127.0.0.1:8001]
//   node e2e/parity/parity-diff.mjs --page /fixtures
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
import { PAGES, extractPage } from "./extract.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..", "..");

function parseArgs(argv) {
  const args = {
    page: null,
    all: false,
    vanillaOrigin: "http://127.0.0.1:8000",
    reactOrigin: "http://127.0.0.1:8001",
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--page") {
      args.page = argv[++i];
    } else if (a === "--all") {
      args.all = true;
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

// Compares one page's extracted vanilla/react snapshots field by field.
// `rows` fields compare index-for-index over the shorter of the two arrays
// and additionally flag a length mismatch as its own delta; `text` fields
// compare directly. Every field counts toward the compared-field total
// regardless of whether it produced a delta.
function comparePage(pageSpec, vanillaData, reactData) {
  const deltas = [];
  let fieldsCompared = 0;

  for (const field of pageSpec.fields) {
    const vVal = vanillaData[field.name];
    const rVal = reactData[field.name];
    fieldsCompared++;

    if (field.kind === "rows") {
      const n = Math.min(vVal.length, rVal.length);
      for (let i = 0; i < n; i++) {
        if (vVal[i] !== rVal[i]) {
          deltas.push({
            page: pageSpec.label,
            field: field.name,
            row: i,
            vanilla: vVal[i],
            react: rVal[i],
            knownDeviations: field.knownDeviations ?? [],
          });
        }
      }
      if (vVal.length !== rVal.length) {
        deltas.push({
          page: pageSpec.label,
          field: field.name,
          row: null,
          vanilla: `row count ${vVal.length}`,
          react: `row count ${rVal.length}`,
          knownDeviations: field.knownDeviations ?? [],
        });
      }
    } else if (vVal !== rVal) {
      deltas.push({
        page: pageSpec.label,
        field: field.name,
        row: null,
        vanilla: vVal,
        react: rVal,
        knownDeviations: field.knownDeviations ?? [],
      });
    }
  }

  return { fieldsCompared, deltas };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  let pagesToRun;
  if (args.all) {
    pagesToRun = PAGES;
  } else if (args.page) {
    const found = PAGES.find((p) => p.route === args.page);
    if (!found) {
      console.error(
        `FAILED: no page with route ${args.page} in extract.mjs's PAGES -- ` +
          `known routes: ${PAGES.map((p) => p.route).join(", ")}`,
      );
      process.exit(1);
      return;
    }
    pagesToRun = [found];
  } else {
    console.error("FAILED: --page <route> or --all is required");
    process.exit(1);
    return;
  }

  await assertSameLiveExport(args.vanillaOrigin, args.reactOrigin);

  const browser = await chromium.launch();
  let totalPages = 0;
  let totalFields = 0;
  let totalDeltas = 0;
  let hadZeroFieldPage = false;

  try {
    const vanillaPage = await browser.newPage();
    const reactPage = await browser.newPage();

    for (const pageSpec of pagesToRun) {
      const vanillaData = await extractPage(vanillaPage, pageSpec, {
        base: args.vanillaOrigin,
        flavour: "vanilla",
      });
      const reactData = await extractPage(reactPage, pageSpec, {
        base: args.reactOrigin,
        flavour: "react",
      });

      const { fieldsCompared, deltas } = comparePage(pageSpec, vanillaData, reactData);

      for (const d of deltas) {
        console.log(
          `  ${pageSpec.label} :: ${d.field}${d.row != null ? ` row ${d.row}` : ""}: ` +
            `vanilla=(${d.vanilla}) react=(${d.react})`,
        );
      }
      console.log(`${pageSpec.label}: ${fieldsCompared} fields compared, ${deltas.length} deltas`);

      totalPages++;
      totalFields += fieldsCompared;
      totalDeltas += deltas.length;
      if (fieldsCompared === 0) {
        hadZeroFieldPage = true;
      }
    }
  } finally {
    await browser.close();
  }

  console.log(`TOTAL: ${totalPages} pages, ${totalFields} fields compared, ${totalDeltas} deltas`);

  if (hadZeroFieldPage || totalFields === 0 || totalDeltas > 0) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(`FAILED: ${err && err.stack ? err.stack : err}`);
  process.exit(1);
});
