// Derives the "blank" and "double-gameweek" E2E fixture variants from the immutable
// `normal` capture, by a single deterministic transform (D-06) -- so all three scenarios
// share the same real player names and prices and cannot silently drift apart the way
// three hand-authored sets would.
//
// Zero npm dependencies by design -- node:fs/node:path/node:url only, matching
// frontend/scripts/check-tokens.mjs's zero-dependency convention. Invoke directly:
//   node e2e/scripts/synthesize-variants.mjs
//
// NEVER writes into fixtures/v1/normal/ -- reads it only, writes only into
// fixtures/v1/{blank,dgw}/web-data/. Every selection is made by sorting on a stable
// string key (club `short` code), never by object/array iteration order and never by
// randomness -- re-running this script after it has already run reproduces the exact
// same output bytes (`git status --porcelain e2e/fixtures/v1` stays empty).
//
// See e2e/fixtures/v1/MANIFEST.md's "Synthesis rules" section for the selection rule,
// the two resulting club-code lists, and the full per-file transform/non-transform list.

import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES_ROOT = join(HERE, "..", "fixtures", "v1");
const NORMAL_API = join(FIXTURES_ROOT, "normal", "api");
const NORMAL_DATA = join(FIXTURES_ROOT, "normal", "web-data");
const BLANK_DATA = join(FIXTURES_ROOT, "blank", "web-data");
const DGW_DATA = join(FIXTURES_ROOT, "dgw", "web-data");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

// Line-diffable output (matches the normal capture's own json.dump(indent=1) style
// closely enough for code review); determinism -- not byte-parity with `normal`,
// which this script never touches -- is what the verify step actually checks.
function writeJson(path, data) {
  writeFileSync(path, JSON.stringify(data, null, 1) + "\n");
}

function copyVerbatim(filename, destDir) {
  copyFileSync(join(NORMAL_DATA, filename), join(destDir, filename));
}

const capture = readJson(join(NORMAL_API, "capture.json"));
const GW = capture.gw;

const fixtures = readJson(join(NORMAL_DATA, "fixtures.json"));

// Selection rule, stated once and reused: sort the ticker rows ascending by their
// `short` club code; the first six are the BLANK clubs, the first four are the DOUBLE
// clubs. `Array.prototype.sort()` on an array of plain uppercase 3-letter ASCII codes
// with no comparator is lexicographic ascending -- deterministic, no locale dependence.
const sortedShorts = fixtures.map((row) => row.short).slice().sort();
const BLANK_CLUBS = sortedShorts.slice(0, 6);
const DOUBLE_CLUBS = sortedShorts.slice(0, 4);

// ---------------------------------------------------------------------------------
// Blank set: copy every file verbatim, then transform four (fixtures, chips,
// xp_table, captains).
// ---------------------------------------------------------------------------------

mkdirSync(BLANK_DATA, { recursive: true });
for (const f of ["meta.json", "leaders.json", "squad.json", "standings.json", "watchlist.json"]) {
  copyVerbatim(f, BLANK_DATA);
}

// fixtures.json: each blank club's current-gameweek `fixtures` array becomes empty.
// `xg_next`/`xgc_next`/`ease` are deliberately left untouched -- a real blank week would
// change them, but no spec asserts those values on a blanked row (MANIFEST records this).
const blankFixtures = fixtures.map((row) => {
  if (!BLANK_CLUBS.includes(row.short)) {
    return row;
  }
  return {
    ...row,
    gws: row.gws.map((g) => (g.gw === GW ? { ...g, fixtures: [] } : g)),
  };
});
writeJson(join(BLANK_DATA, "fixtures.json"), blankFixtures);

// chips.json: current gameweek's bgw_clubs becomes the blank club count; dgw_clubs
// stays at its captured value; note becomes predict/live.py's `_chip_note` exact
// blank-week wording (gw + count substituted).
const chips = readJson(join(NORMAL_DATA, "chips.json"));
const blankChips = {
  note: `GW${GW} has ${BLANK_CLUBS.length} blank clubs — consider Free Hit.`,
  structure: chips.structure.map((row) =>
    row.gw === GW ? { ...row, bgw_clubs: BLANK_CLUBS.length } : row,
  ),
};
writeJson(join(BLANK_DATA, "chips.json"), blankChips);

// xp_table.json: drop every row whose team_short is a blank club -- mirrors what a real
// blank week produces (_gw_pool skips a club with no fixture entirely, never emits a
// zero-xP placeholder row for it).
const xpTable = readJson(join(NORMAL_DATA, "xp_table.json"));
writeJson(
  join(BLANK_DATA, "xp_table.json"),
  xpTable.filter((r) => !BLANK_CLUBS.includes(r.team_short)),
);

// captains.json: same drop rule, preserving the surviving rows' order.
const captains = readJson(join(NORMAL_DATA, "captains.json"));
writeJson(
  join(BLANK_DATA, "captains.json"),
  captains.filter((r) => !BLANK_CLUBS.includes(r.team_short)),
);

// ---------------------------------------------------------------------------------
// Double set: copy every file verbatim, then transform two (fixtures, chips).
// xp_table.json/captains.json stay untransformed -- a real double week would raise
// those players' xP, but the double-set specs assert only the ticker and the chip
// timeline, so no synthetic xP inflation is introduced.
// ---------------------------------------------------------------------------------

mkdirSync(DGW_DATA, { recursive: true });
for (const f of [
  "meta.json",
  "leaders.json",
  "squad.json",
  "standings.json",
  "watchlist.json",
  "xp_table.json",
  "captains.json",
]) {
  copyVerbatim(f, DGW_DATA);
}

// fixtures.json: each double club's current-gameweek `fixtures` array gains a second
// entry -- a copy of the existing entry with `home` inverted and `opp` set to the next
// club in the double list (the last wraps to the first), keeping the original `fdr`.
// Every doubled cell ends up with two chips of the same difficulty and opposite venue.
const doubleFixtures = fixtures.map((row) => {
  const idx = DOUBLE_CLUBS.indexOf(row.short);
  if (idx === -1) {
    return row;
  }
  const nextClub = DOUBLE_CLUBS[(idx + 1) % DOUBLE_CLUBS.length];
  return {
    ...row,
    gws: row.gws.map((g) => {
      if (g.gw !== GW) {
        return g;
      }
      const original = g.fixtures[0];
      const doubled = { opp: nextClub, home: !original.home, fdr: original.fdr };
      return { ...g, fixtures: [original, doubled] };
    }),
  };
});
writeJson(join(DGW_DATA, "fixtures.json"), doubleFixtures);

// chips.json: current gameweek's dgw_clubs becomes the double club count; note becomes
// `_chip_note`'s exact double-week wording (gw + count substituted).
const doubleChips = {
  note: `GW${GW} is a DOUBLE for ${DOUBLE_CLUBS.length} clubs — consider Bench Boost / Triple Captain.`,
  structure: chips.structure.map((row) =>
    row.gw === GW ? { ...row, dgw_clubs: DOUBLE_CLUBS.length } : row,
  ),
};
writeJson(join(DGW_DATA, "chips.json"), doubleChips);

console.log(
  `Synthesised variants for GW${GW}: blank clubs=[${BLANK_CLUBS.join(", ")}], ` +
    `double clubs=[${DOUBLE_CLUBS.join(", ")}]`,
);
