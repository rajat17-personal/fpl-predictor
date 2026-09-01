---
phase: 02-data-layer-non-pitch-pages
reviewed: 2026-09-01T00:00:00Z
depth: standard
files_reviewed: 43
files_reviewed_list:
  - frontend/index.html
  - frontend/package.json
  - frontend/src/components/BandCell.tsx
  - frontend/src/components/ErrorState.test.tsx
  - frontend/src/components/FdrCell.test.tsx
  - frontend/src/components/FdrCell.tsx
  - frontend/src/components/GwBanner.test.tsx
  - frontend/src/components/GwBanner.tsx
  - frontend/src/components/PageShell.test.tsx
  - frontend/src/components/PageShell.tsx
  - frontend/src/components/Spinner.test.tsx
  - frontend/src/components/ThemeToggle.test.tsx
  - frontend/src/components/ThemeToggle.tsx
  - frontend/src/content/methodology.md
  - frontend/src/index.css
  - frontend/src/lib/api.ts
  - frontend/src/lib/bandCell.test.ts
  - frontend/src/lib/bandCell.ts
  - frontend/src/lib/deadline.test.ts
  - frontend/src/lib/deadline.ts
  - frontend/src/lib/format.test.ts
  - frontend/src/lib/format.ts
  - frontend/src/lib/sortable.test.ts
  - frontend/src/lib/sortable.ts
  - frontend/src/lib/statusFlag.test.tsx
  - frontend/src/lib/statusFlag.tsx
  - frontend/src/lib/theme.test.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/usePageMeta.test.tsx
  - frontend/src/lib/usePageMeta.ts
  - frontend/src/routes/Differentials.test.tsx
  - frontend/src/routes/Differentials.tsx
  - frontend/src/routes/Fixtures.test.tsx
  - frontend/src/routes/Fixtures.tsx
  - frontend/src/routes/League.test.tsx
  - frontend/src/routes/League.tsx
  - frontend/src/routes/Methodology.test.tsx
  - frontend/src/routes/Methodology.tsx
  - frontend/src/routes/Prices.test.tsx
  - frontend/src/routes/Prices.tsx
  - frontend/src/routes/Scoreboard.test.tsx
  - frontend/src/routes/Scoreboard.tsx
  - frontend/src/routes/XpTable.test.tsx
  - frontend/src/routes/XpTable.tsx
  - frontend/src/routes/routeIsolation.test.tsx
  - frontend/src/test/fixtures/captains.json
  - frontend/src/test/fixtures/fixtures.json
  - frontend/src/test/fixtures/leaders.json
  - frontend/src/test/fixtures/meta.json
  - frontend/src/test/fixtures/scoreboard.json
  - frontend/src/test/fixtures/standings.json
  - frontend/src/test/fixtures/watchlist_heuristic.json
  - frontend/src/test/fixtures/watchlist_model.json
  - frontend/src/test/fixtures/watchlist_official.json
  - frontend/src/test/fixtures/xp_table.json
  - frontend/src/test/harness.test.tsx
  - frontend/src/vite-env.d.ts
  - frontend/tsconfig.app.json
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-09-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 43 (source + spec/config files from the required-reading list; test files reviewed for coverage/reliability only, not flagged for style)
**Status:** issues_found

## Summary

This phase ports seven vanilla-JS pages (xP table, Fixtures, Prices, League, Scoreboard,
Differentials, Methodology) plus supporting chrome (PageShell, GwBanner, ThemeToggle) to
React/Vite, with an explicit behavioural-parity contract governed by
`PARITY-DEVIATIONS.md`. I traced every documented "load-bearing oddity" (the inverted sort
polarity in `sortable.ts`, the two distinct `maxHi` formulas for `BandCell`, the
un-guarded `ownership`/`xp_capt` fields on the Captains and Differentials/Prices tables,
the `diffOwnershipCell`'s literal `"undefined"` string) against its cited research note or
ledger entry and against its own test, and found each one correctly implemented and
correctly tested — none of these are flagged below.

Hooks-ordering, null/undefined handling on the fetched JSON contracts, the theme
resolution / pre-mount script agreement, the sort/filter/slice pipelines, and the
`?? "–"` vs. no-fallback conventions were all traced carefully and are correct. No
security issues (no `dangerouslySetInnerHTML`, no raw-HTML sink, no eval, no hardcoded
secrets, no un-sanitized markdown) were found; `Methodology.tsx`'s react-markdown usage is
correctly configured to escape rather than render raw HTML, and this is explicitly
regression-tested.

The issues below are two real (but non-crashing) inconsistencies and three lower-severity
robustness/consistency notes. There are no BLOCKER-level findings.

## Warnings

### WR-01: Model-mode price note silently renders "NaN%"/"undefined" if optional fields are absent

**File:** `frontend/src/routes/Prices.tsx:90-94`
**Issue:** `ModeNote`'s fallback branch (reached whenever `w.mode` is neither `"official"`
nor `"heuristic"` — i.e. the `"model"` case) builds its copy from two fields the
`Watchlist` interface itself declares optional (`api.ts:125-126`: `trained_utc?: string`,
`val_moved_hit?: number`):

```tsx
{`Model predictions (trained ${w.trained_utc?.slice(0, 10)}; hit-rate on actual movers ${(100 * w.val_moved_hit!).toFixed(0)}% in validation). Status reflects the model's probability.`}
```

`trained_utc` is accessed safely (`?.slice`), but `val_moved_hit` is forced with a
non-null assertion (`w.val_moved_hit!`) in the same expression. If a `"model"`-mode
payload ever omits `val_moved_hit` (which the type says is legal), `100 * undefined`
evaluates to `NaN`, and `NaN.toFixed(0)` silently prints the literal string `"NaN"` rather
than throwing — so the page renders "hit-rate on actual movers NaN% in validation"
instead of failing loudly or falling back gracefully. Likewise a missing `trained_utc`
renders "trained undefined" rather than a placeholder. This is inconsistent guard
discipline within one function — one field guarded, the sibling field force-unwrapped —
and there is no test fixture that exercises the model-mode note with either field absent
(only `watchlist_model.json`, which always supplies both).
**Fix:** Guard `val_moved_hit` the same way `trained_utc` is guarded, e.g.:
```tsx
{`Model predictions (trained ${w.trained_utc?.slice(0, 10) ?? "unknown date"}; hit-rate on actual movers ${w.val_moved_hit != null ? (100 * w.val_moved_hit).toFixed(0) + "%" : "–"} in validation). Status reflects the model's probability.`}
```
and add a test fixture/case for the model-mode note with `val_moved_hit`/`trained_utc`
absent, to lock in the fallback behaviour.

### WR-02: Internal markdown link bypasses client-side routing

**File:** `frontend/src/routes/Methodology.tsx:20-49`, `frontend/src/content/methodology.md:41`
**Issue:** The methodology markdown contains one internal link, `[scoreboard](/scoreboard)`.
`Methodology.tsx`'s `ReactMarkdown` component-override map supplies custom renderers for
`h1`, `h2`, `p`, `ul`, `li`, `a`, and `strong`, but the `a` override only adds a class —
it renders a plain `<a href="/scoreboard">`, not react-router's `<Link>`:
```tsx
a: (props) => <a className="text-accent underline" {...props} />,
```
Every other internal link built in this phase (`XpTable.tsx`'s "Track its accuracy live",
`Prices.tsx`'s "scoreboard" link in the heuristic-mode note) correctly uses react-router's
`<Link to="/scoreboard">`, which performs a client-side transition. Clicking the
methodology page's link instead triggers a full browser navigation/reload — it still
works, but it silently drops out of the SPA, is inconsistent with the rest of the app,
and undermines the whole point of `PageShell` owning a shared `meta.json` query cached
across route transitions (the reload re-fetches everything from scratch).
**Fix:** Have the `a` override detect an internal (root-relative) `href` and render a
react-router `<Link>` instead of a plain anchor, e.g.:
```tsx
a: ({ href, children, ...props }) =>
  href?.startsWith("/") ? (
    <Link to={href} className="text-accent underline">{children}</Link>
  ) : (
    <a href={href} className="text-accent underline" {...props}>{children}</a>
  ),
```

## Info

### IN-01: No runtime validation of fetched JSON — a malformed backend response can crash a route

**File:** `frontend/src/lib/api.ts:10-16`, `frontend/src/routes/Scoreboard.tsx:117-138`
**Issue:** `fetchJson`/`fetchAndCheck` cast the parsed body to the declared TypeScript
type (`return (await res.json()) as T;`) with no runtime shape check. This is consistent
across every route, but `Scoreboard.tsx` is the one place that then dereferences the
result with non-null assertions inside the populated branch (`summary!.gameweeks`,
`summary!.mae_model`, `summary!.spearman_model`, `summary!.captain_avg_points` at
lines 120-135), guarded only by the TS-level guarantee that `ScoreboardResponse.summary`
is non-optional. If the backend ever emits `entries: [...]` with a missing or malformed
`summary` object (e.g. a partial write, a schema drift between `predict/scoreboard.py`
and this contract), this throws inside render with no `ErrorBoundary` anywhere in the
tree (none of the reviewed files define one), blanking the whole page rather than
degrading to the ErrorState/EmptyState pattern used everywhere else for fetch failures.
**Fix:** Either add a minimal runtime guard (`if (!data?.summary) return <ErrorState .../>`
before the populated branch) or wrap the router in a top-level React error boundary as a
backstop, consistent with the "no unhandled render crash" intent already tested for async
rejections in `routeIsolation.test.tsx`.

### IN-02: `PriceTable` rows keyed on `name`, which has no uniqueness guarantee

**File:** `frontend/src/routes/Prices.tsx:133`
**Issue:** `rows.map((r) => ... <tr key={r.name} ...>)` uses the player's display name as
the React key. Unlike `XpRow`/row-level identifiers elsewhere in this phase (`XpTable`/
`Differentials` key by `player_code`, `Scoreboard` keys by `gw`), `WatchlistRow`
(`api.ts:104-115`) carries no numeric/stable id field at all, so two players sharing a
display name within the same risers/fallers table would collide as React keys (silent
mis-render/reconciliation bug, not a crash). This is a backend-contract limitation more
than a frontend defect, but is worth flagging since it's the one table in this phase not
keyed on a stable identifier.
**Fix:** If/when the watchlist export gains a stable id (`player_code`, matching the
other exports), switch the key to it. Until then, no action is strictly required, but
this is a latent footgun worth noting for whoever revisits `predict/scoreboard.py`'s /
`models/price.py`'s export contract.

### IN-03: Empty (but present) captains array renders an empty table shell, not an explicit fallback

**File:** `frontend/src/routes/XpTable.tsx:227-271`
**Issue:** `captainsData ? (<table>...</table>) : null` treats an empty array (`[]`,
which is truthy in JS) the same as a populated one — an empty `captains.json` response
would render the "Captain picks" `<h2>` plus an empty `<table>` with a header row and zero
body rows, rather than a "no data" message (contrast with every other table on this page
and elsewhere in the phase, which render an explicit empty-state message or hide the
section entirely). No test in `XpTable.test.tsx` exercises `captainsData = []`
specifically (the default mock captains body used by tests that don't care about the
sub-table is `[]`, but none of those tests assert on the Captain picks table's presence
or absence). Low practical risk since `captains.json` should always contain the top
picks in production, but the gap is untested and inconsistent with the rest of the page's
empty-state discipline.
**Fix:** Either add `captainsData.length > 0` to the render guard (rendering nothing, or a
one-line fallback, for an empty array) and add a regression test for it, or explicitly
document why an empty captains export should still show table chrome.

---

_Reviewed: 2026-09-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
