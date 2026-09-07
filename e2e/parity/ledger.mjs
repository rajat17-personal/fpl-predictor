// e2e/parity/ledger.mjs -- PARITY-DEVIATIONS.md table parser and known-delta
// filter (Phase 7, CUT-01, D-05). Dependency-free node:fs-only parsing,
// mirroring frontend/scripts/check-tokens.mjs's own style -- no markdown
// parser package.
//
// loadLedger() fails loudly on every malformed-input path (missing file,
// missing heading, zero parsed rows) by design: an empty allowlist would
// silently mark every delta "explained", which is the exact silent-pass
// this whole phase exists to prevent.

import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_LEDGER_PATH = path.resolve(
  __dirname,
  "..",
  "..",
  ".planning/phases/02-data-layer-non-pitch-pages/PARITY-DEVIATIONS.md",
);

/**
 * Reads and parses PARITY-DEVIATIONS.md's numbered deviation table. Locates
 * the "## Deviations" heading, stops before the next "## " heading (so the
 * later "Palette changes made in lockstep" section's own pipe table is
 * never mistaken for numbered rows), then keeps only rows whose first cell
 * is a bare integer -- the header row ("#", "Deviation", ...) and the
 * alignment row ("---", ...) are both skipped by that same rule.
 *
 * @param {string} [ledgerPath] defaults to the Phase 2 ledger's real path
 * @returns {{ number: number, deviation: string, reason: string, introducedBy: string }[]}
 */
export function loadLedger(ledgerPath = DEFAULT_LEDGER_PATH) {
  if (!existsSync(ledgerPath)) {
    throw new Error(
      `PARITY-DEVIATIONS.md ledger not found at ${ledgerPath} -- cannot ` +
        "classify any delta as explained without it",
    );
  }

  const content = readFileSync(ledgerPath, "utf-8");
  const headingIdx = content.indexOf("## Deviations");
  if (headingIdx === -1) {
    throw new Error(
      `No "## Deviations" heading found in ${ledgerPath} -- cannot locate ` +
        "the numbered deviation table",
    );
  }

  const afterHeading = content.slice(headingIdx);
  const nextHeadingIdx = afterHeading.indexOf("\n## ", 1);
  const section = nextHeadingIdx === -1 ? afterHeading : afterHeading.slice(0, nextHeadingIdx);

  const rows = [];
  for (const line of section.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed.startsWith("|")) {
      continue;
    }
    const cells = trimmed
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());
    if (cells.length < 4 || !/^\d+$/.test(cells[0])) {
      // Not a numbered row -- the header row, the "|---|---|" alignment
      // row, or a stray pipe-containing line, all skipped the same way.
      continue;
    }
    rows.push({
      number: Number(cells[0]),
      deviation: cells[1],
      reason: cells[2],
      introducedBy: cells[3],
    });
  }

  if (rows.length === 0) {
    throw new Error(
      `Zero numbered deviation rows parsed from ${ledgerPath} -- an empty ` +
        "allowlist would silently mark every delta explained, so this " +
        "loader refuses to return one",
    );
  }

  return rows;
}

/**
 * Classifies one delta record (as produced by parity-diff.mjs's
 * comparePage()) against the loaded ledger. The binding is field-level,
 * declared in extract.mjs's PAGES map (`field.knownDeviations`), never
 * inferred from the delta's own text -- so `delta.knownDeviations` is
 * expected to be present (an empty array when the field declares none).
 *
 * @returns {number | null} the cited ledger number when explained, else null
 */
export function isKnownDelta(delta, ledger) {
  const declared = delta.knownDeviations ?? [];
  if (declared.length === 0) {
    return null;
  }

  const ledgerNumbers = new Set(ledger.map((r) => r.number));
  for (const n of declared) {
    if (!ledgerNumbers.has(n)) {
      throw new Error(
        `Field "${delta.field}" on page "${delta.page}" declares ledger ` +
          `entry #${n}, which does not exist in the live PARITY-DEVIATIONS.md ` +
          "-- update extract.mjs's field map or the ledger",
      );
    }
  }

  return declared[0];
}
