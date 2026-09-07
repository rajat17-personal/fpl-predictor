// e2e/parity/extract.mjs -- per-page, per-origin field map for the eight-page
// cross-origin parity comparison (Phase 7, CUT-01, D-05). Exports PAGES (one
// entry per React route in frontend/src/router.tsx) and extractPage(), which
// navigates a Playwright page to the right path for a given origin's flavour
// and returns a normalised, field-keyed snapshot of that page's content.
//
// Selector design: vanilla addresses tables by element id (table#xp) and
// React by accessible name (table[aria-label="xP table"]) -- the accessible
// name was only added on the React side, so the two sites never share a
// selector. Every field therefore carries an explicit `vanilla` selector and
// an explicit `react` selector.
//
// `knownDeviations` on a field is the ledger binding (Task 2, e2e/parity/
// ledger.mjs): a non-empty array names the PARITY-DEVIATIONS.md entry
// numbers that already explain any delta this field reports. The binding is
// declared here, in the field map, and reviewed here -- never inferred from
// prose text matching at diff time.

// Strips every character outside letters/digits/space/period/apostrophe/
// hyphen, then collapses whitespace runs and trims. Reused verbatim from the
// 07-01 tracer's normalizeName() and applied to every extracted value here
// -- row cells and text fields alike -- so sort-direction glyphs, the
// status-flag glyphs (vanilla's inline `title`-adjacent glyph, React's
// StatusFlag button glyph), and stray punctuation (%, ->, commas in
// toLocaleString figures) are removed symmetrically from both origins
// before comparison. Sort *order* is still compared as row sequence, never
// re-derived from an arrow glyph.
export function normalizeText(raw) {
  return (raw ?? "")
    .replace(/[^\p{L}\p{N} .'-]/gu, "")
    .replace(/\s+/g, " ")
    .trim();
}

const BANNER_FIELD = {
  name: "banner",
  kind: "text",
  vanilla: "span.deadline",
  // The GW banner pill (GwBanner.tsx's PILL_CLASS). Scoped to `header` and
  // matched on a substring unique to the pill (`px-3 py-1.5`) so it can
  // never resolve to ThemeToggle's sibling pill, which also carries
  // `rounded-full` but a different padding scale.
  react: 'header div[class*="px-3 py-1.5"]',
  // Ledger entries 3 (freshness line added) and 4 (deadline-passed wording
  // differs) -- any delta on this field is a known, already-explained one.
  knownDeviations: [3, 4],
};

export const PAGES = [
  {
    route: "/",
    vanillaPath: "/index.html",
    label: "xP table",
    fields: [
      { name: "heading", kind: "text", vanilla: "h1", react: "h1" },
      BANNER_FIELD,
      {
        name: "xpTable",
        kind: "rows",
        vanilla: "table#xp tbody tr",
        react: 'table[aria-label="xP table"] tbody tr',
      },
      {
        name: "captainsTable",
        kind: "rows",
        vanilla: "table#capt tbody tr",
        react: 'table[aria-label="Captain picks"] tbody tr',
      },
      {
        name: "notePara",
        kind: "text",
        vanilla: "text=Showing the top 50 by xP",
        react: "text=Showing the top 50 by xP",
      },
    ],
  },
  {
    route: "/team",
    vanillaPath: "/team.html",
    label: "Rate my team",
    fields: [
      // React's /team defaults to the Squad tab (h1 "Model squad GW{n}"),
      // not vanilla's rate-ID entry form (h1 "Rate my team") -- ledger #9
      // (Phase 3's 03-01 view-only default Squad tab decision).
      { name: "heading", kind: "text", vanilla: "h1", react: "h1", knownDeviations: [9] },
      BANNER_FIELD,
      // Vanilla's default view is the "Rate my team" ID-entry form; React's
      // default Squad tab renders the model squad first (Phase 3's pitch
      // redesign) and only shows this helper text once a team is loaded.
      // The two selectors intentionally point at each side's own
      // load/entry-form helper copy rather than assert byte-identical text
      // -- the structural divergence is recorded as PARITY-DEVIATIONS.md
      // ledger #9 (07-03).
      {
        name: "formHelper",
        kind: "text",
        vanilla: "text=Enter your FPL team ID",
        react: "text=Your ID is in the URL on the official site",
        knownDeviations: [9],
      },
    ],
  },
  {
    route: "/fixtures",
    vanillaPath: "/fixtures.html",
    label: "Fixture ticker",
    fields: [
      { name: "heading", kind: "text", vanilla: "h1", react: "h1" },
      BANNER_FIELD,
      {
        name: "tickerTable",
        kind: "rows",
        vanilla: "table#ticker tbody tr",
        // No id/aria-label on Fixtures.tsx's table -- it is the only table
        // on the page, so a bare `table` selector is unambiguous here.
        react: "table tbody tr",
      },
      {
        name: "notePara",
        kind: "text",
        vanilla: "text=The next six gameweeks for every club",
        react: "text=The next six gameweeks for every club",
      },
    ],
  },
  {
    route: "/prices",
    vanillaPath: "/prices.html",
    label: "Price watch",
    fields: [
      { name: "heading", kind: "text", vanilla: "h1", react: "h1" },
      BANNER_FIELD,
      {
        name: "subPara",
        kind: "text",
        vanilla: "text=Players trending toward an overnight price change",
        react: "text=Players trending toward an overnight price change",
      },
      {
        name: "risersTable",
        kind: "rows",
        vanilla: "table#risers tbody tr",
        react: 'table[aria-label="Likely risers"] tbody tr',
      },
      {
        name: "fallersTable",
        kind: "rows",
        vanilla: "table#fallers tbody tr",
        react: 'table[aria-label="Likely fallers"] tbody tr',
      },
    ],
  },
  {
    route: "/league",
    vanillaPath: "/league.html",
    label: "League table & leaders",
    fields: [
      { name: "heading", kind: "text", vanilla: "h1", react: "h1" },
      BANNER_FIELD,
      {
        name: "subPara",
        kind: "text",
        vanilla: "text=Standings computed from finished fixtures",
        react: "text=Standings computed from finished fixtures",
      },
      {
        name: "standingsTable",
        kind: "rows",
        vanilla: "table#standings tbody tr",
        react: 'table[aria-label="Premier League table"] tbody tr',
      },
    ],
  },
  {
    route: "/scoreboard",
    vanillaPath: "/scoreboard.html",
    label: "Scoreboard",
    fields: [
      { name: "heading", kind: "text", vanilla: "h1", react: "h1" },
      BANNER_FIELD,
      {
        name: "introPara",
        kind: "text",
        vanilla: "text=Every gameweek's predictions are frozen before kickoff",
        react: "text=Every gameweek's predictions are frozen before kickoff",
      },
      // The tiles row (a numeric-summary page, not a table -- extracted as
      // text per this plan's action text). Only one of the two mutually
      // exclusive tile grids (empty-state / populated) is ever in the DOM
      // at once, so the substring match is unambiguous.
      {
        name: "tiles",
        kind: "text",
        vanilla: "#tiles",
        react: 'div[class*="grid-cols-[repeat(auto-fit"]',
      },
      {
        name: "historyTable",
        kind: "rows",
        vanilla: "table#gws tbody tr",
        react: 'table[aria-label="Scoreboard history"] tbody tr',
      },
    ],
  },
  {
    route: "/differentials",
    vanillaPath: "/differentials.html",
    label: "Differentials",
    fields: [
      { name: "heading", kind: "text", vanilla: "h1", react: "h1" },
      BANNER_FIELD,
      {
        name: "introPara",
        kind: "text",
        vanilla: "text=Players the model rates that your mini-league rivals",
        react: "text=Players the model rates that your mini-league rivals",
      },
      {
        name: "diffTable",
        kind: "rows",
        vanilla: "table#diff tbody tr",
        react: 'table[aria-label="Differentials"] tbody tr',
      },
    ],
  },
  {
    route: "/methodology",
    vanillaPath: "/methodology.html",
    label: "Methodology",
    fields: [
      { name: "heading", kind: "text", vanilla: "h1", react: "h1" },
      BANNER_FIELD,
      {
        name: "predictionPara",
        kind: "text",
        vanilla: "text=A per-position two-stage model",
        react: "text=A per-position two-stage model",
      },
      // The data-source credit line (ledger entry 6: React moves this line
      // from the per-page footer into the page body). A plain substring
      // match finds it in either DOM location without asserting a location.
      // Ledger #10: the body paragraph ends after "...odds." and does not
      // repeat the "Not affiliated..." disclaimer sentence inline, since
      // PageShell's unified sitewide footer (also entry 6) already carries
      // it once for every page.
      {
        name: "creditLine",
        kind: "text",
        vanilla: "text=Data: official FPL API",
        react: "text=Data: official FPL API",
        knownDeviations: [10],
      },
    ],
  },
];

async function extractRows(page, selector) {
  const rowLocator = page.locator(selector);
  const count = await rowLocator.count();
  const rows = [];
  for (let i = 0; i < count; i++) {
    const cells = await rowLocator.nth(i).locator("td").allInnerTexts();
    rows.push(cells.map((c) => normalizeText(c)).join(" | "));
  }
  return rows;
}

async function extractFieldText(page, selector) {
  const locator = page.locator(selector).first();
  const count = await locator.count();
  if (count === 0) {
    return null;
  }
  const text = await locator.innerText();
  return normalizeText(text);
}

/**
 * Navigates `page` to the right path for `origin`'s flavour, waits for
 * fonts, and returns an object keyed by field name -- an array of
 * normalised row strings for a `rows` field, a normalised string (or null
 * if the element is absent) for a `text` field.
 *
 * @param {import("@playwright/test").Page} page
 * @param {typeof PAGES[number]} pageSpec
 * @param {{ base: string, flavour: "vanilla" | "react" }} origin
 */
export async function extractPage(page, pageSpec, origin) {
  const path = origin.flavour === "vanilla" ? pageSpec.vanillaPath : pageSpec.route;
  await page.goto(`${origin.base}${path}`);
  await page.evaluate(() => document.fonts.ready);

  const result = {};
  for (const field of pageSpec.fields) {
    const selector = origin.flavour === "vanilla" ? field.vanilla : field.react;
    if (field.kind === "rows") {
      result[field.name] = await extractRows(page, selector);
    } else {
      result[field.name] = await extractFieldText(page, selector);
    }
  }
  return result;
}
