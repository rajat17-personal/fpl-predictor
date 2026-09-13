#!/usr/bin/env node
// e2e/parity/parity-diff.mjs -- machine-compares live pages across the
// vanilla and react-mode servers scripts/dual_site.sh boots (Phase 7,
// CUT-01, D-05/D-06/D-07). Walks the eight-page field map exported by
// e2e/parity/extract.mjs, routes every collected delta through
// e2e/parity/ledger.mjs's known-deviation filter, and classifies it as
// either `explained` (cites its PARITY-DEVIATIONS.md ledger number) or a
// `defect`. Imports `chromium` from the already human-approved
// @playwright/test@1.62.1 pin in e2e/node_modules (resolved by walking up
// from e2e/parity/) -- no new package install.
//
// Usage:
//   node e2e/parity/parity-diff.mjs --all
//     [--vanilla-origin http://127.0.0.1:8000]
//     [--react-origin http://127.0.0.1:8001]
//     [--stage pre-deadline --out .planning/phases/07-parity-validation-cutover/PARITY-REPORT.md]
//   node e2e/parity/parity-diff.mjs --page /fixtures
//
// --stage/--out (D-06): when --out is given, a markdown fragment (one H3
// stage heading + a Page/Verdict/Delta detail/Cron-green citation table
// row per page) is APPENDED to that path, ready to paste into
// PARITY-REPORT.md's matching stage table without editing.
//
// Before comparing anything, asserts both origins are serving the SAME live
// export: fetches /data/meta.json from each origin and from the on-disk
// web/data/meta.json, and aborts non-zero with an explicit message if the
// three are not byte-identical. That guard is what stops a fixture-mode or
// stale-build server from masquerading as a live one -- this script must
// never be pointed at anything but two live, same-instant processes.

import { chromium } from "@playwright/test";
import { appendFileSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { PAGES, extractPage } from "./extract.mjs";
import { isKnownDelta, loadLedger } from "./ledger.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..", "..");

function parseArgs(argv) {
  const args = {
    page: null,
    all: false,
    vanillaOrigin: "http://127.0.0.1:8000",
    reactOrigin: "http://127.0.0.1:8001",
    stage: null,
    out: null,
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
    } else if (a === "--stage") {
      args.stage = argv[++i];
    } else if (a === "--out") {
      args.out = argv[++i];
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
// regardless of whether it produced a delta. Raw deltas only -- ledger
// classification (explained vs defect) happens in classifyDeltas() below,
// once per page, against the loaded ledger.
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

// Routes every raw delta through the ledger filter. Mutates nothing --
// returns a new array where each delta carries an added `explainedBy`
// (the cited ledger number, or null for a real defect). Throws if a
// field's declared knownDeviations number no longer resolves against the
// live ledger (ledger.mjs's isKnownDelta()) -- a stale reference is a
// config error, not a delta to silently pass through.
function classifyDeltas(deltas, ledger) {
  return deltas.map((d) => ({ ...d, explainedBy: isKnownDelta(d, ledger) }));
}

// Builds the "Delta detail" cell for one page's markdown fragment row: the
// distinct ledger numbers cited by explained deltas, and -- when any
// defect remains -- an explicit unfilled marker naming what must replace
// it, so an unresolved defect can never be mistaken for finished work.
function deltaDetailCell(classifiedDeltas) {
  const explainedNumbers = new Set();
  let defectCount = 0;
  for (const d of classifiedDeltas) {
    if (d.explainedBy != null) {
      explainedNumbers.add(d.explainedBy);
    } else {
      defectCount++;
    }
  }

  const parts = [];
  if (explainedNumbers.size > 0) {
    const nums = [...explainedNumbers].sort((a, b) => a - b);
    parts.push(`ledger #${nums.join(", #")}`);
  }
  if (defectCount > 0) {
    parts.push(
      `UNRESOLVED — ${defectCount} defect(s), needs a fixing commit SHA or a new PARITY-DEVIATIONS.md row`,
    );
  }
  return parts.length > 0 ? parts.join("; ") : "no deltas";
}

// Appends one markdown fragment (an H3 stage heading, a run-header line,
// and a Page/Verdict/Delta detail/Cron-green citation table row per page)
// to `outPath` -- pastes directly into PARITY-REPORT.md's matching stage
// table (D-06).
function writeFragment(outPath, stage, commandLine, pageResults) {
  const metaRaw = readFileSync(path.join(ROOT, "web", "data", "meta.json"), "utf-8");
  const meta = JSON.parse(metaRaw);
  const timestamp = new Date().toISOString();

  const lines = [];
  lines.push(`### ${stage}`);
  lines.push("");
  lines.push(
    `**Run:** ${timestamp} | GW${meta.gw} | generated_utc: ${meta.generated_utc} | \`${commandLine}\``,
  );
  lines.push("");
  lines.push("| Page | Verdict | Delta detail | Cron-green citation |");
  lines.push("| --- | --- | --- | --- |");
  for (const r of pageResults) {
    const verdict = `${r.fieldsCompared} fields compared, ${r.explainedCount} explained, ${r.defectCount} defects`;
    lines.push(
      `| ${r.label} | ${verdict} | ${deltaDetailCell(r.classifiedDeltas)} | _(unfilled — cite cron log / alerts.jsonl absence / web/data git history)_ |`,
    );
  }
  lines.push("");

  appendFileSync(outPath, lines.join("\n") + "\n");
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

  // Loaded once, up front: a missing/malformed ledger fails the whole run
  // loudly rather than degrading into "nothing is explained" silently.
  const ledger = loadLedger();

  await assertSameLiveExport(args.vanillaOrigin, args.reactOrigin);

  const browser = await chromium.launch();
  let totalPages = 0;
  let totalFields = 0;
  let totalExplained = 0;
  let totalDefects = 0;
  let hadZeroFieldPage = false;
  const pageResults = [];

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
      const classifiedDeltas = classifyDeltas(deltas, ledger);
      const explainedCount = classifiedDeltas.filter((d) => d.explainedBy != null).length;
      const defectCount = classifiedDeltas.length - explainedCount;

      for (const d of classifiedDeltas) {
        const tag = d.explainedBy != null ? `explained (ledger #${d.explainedBy})` : "DEFECT";
        console.log(
          `  ${pageSpec.label} :: ${d.field}${d.row != null ? ` row ${d.row}` : ""} [${tag}]: ` +
            `vanilla=(${d.vanilla}) react=(${d.react})`,
        );
      }
      console.log(
        `${pageSpec.label}: ${fieldsCompared} fields compared, ${explainedCount} explained, ${defectCount} defects`,
      );

      totalPages++;
      totalFields += fieldsCompared;
      totalExplained += explainedCount;
      totalDefects += defectCount;
      if (fieldsCompared === 0) {
        hadZeroFieldPage = true;
      }
      pageResults.push({
        label: pageSpec.label,
        fieldsCompared,
        explainedCount,
        defectCount,
        classifiedDeltas,
      });
    }
  } finally {
    await browser.close();
  }

  console.log(
    `TOTAL: ${totalPages} pages, ${totalFields} fields compared, ${totalExplained} explained, ${totalDefects} defects`,
  );

  if (args.out) {
    const commandLine = `node e2e/parity/parity-diff.mjs ${args.all ? "--all" : `--page ${args.page}`}` +
      `${args.stage ? ` --stage ${args.stage}` : ""} --out ${args.out}`;
    writeFragment(args.out, args.stage ?? "unnamed stage", commandLine, pageResults);
  }

  if (hadZeroFieldPage || totalFields === 0 || totalDefects > 0) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(`FAILED: ${err && err.stack ? err.stack : err}`);
  process.exit(1);
});
