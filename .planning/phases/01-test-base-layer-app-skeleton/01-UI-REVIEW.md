# Phase 1 — UI Review

**Audited:** 2026-09-01
**Baseline:** UI-SPEC.md (approved, 7/7 dimensions)
**Screenshots:** Not captured (no dev server detected on ports 3000, 5173, 8080)
**Method:** Code-only audit against UI-SPEC design contract and 6-pillar standards

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All UI-SPEC copy implemented verbatim; no generic labels; error details never leaked to DOM |
| 2. Visuals | 4/4 | App shell layout correct; visual hierarchy via typography roles; nav shows active state; WCAG 44px touch targets |
| 3. Color | 4/4 | All 24 tokens declared with light/dark values; no hardcoded hex; proper token usage throughout; dark mode ready |
| 4. Typography | 4/4 | Four roles (Label/Body/Heading/Display) with correct sizes/weights; two fonts (Archivo, IBM Plex Sans); Google Fonts linked |
| 5. Spacing | 2/4 | Several spacing values deviate from declared scale without justification; inconsistent use of gap/padding tokens |
| 6. Experience Design | 4/4 | Loading/error/empty/404 states complete; per-route error boundaries; all backstop behaviors tested; no leaked errors |

**Overall: 22/24**

---

## Top 3 Priority Fixes

1. **SPACING SCALE INCONSISTENCY** — Gap values `gap-0.5` (2px), `gap-2`, `gap-3` (12px) and padding `px-3` (12px) deviate from the declared scale (xs=4px, sm=8px, md=16px, lg=24px, xl=32px, 2xl=48px, 3xl=64px). — **User impact:** Spacing becomes harder to reason about and maintain as more pages are built; inconsistency with design token architecture. — **Fix:** Replace with scale-based equivalents: `gap-0.5`→`gap-0.25` or justify as exception; `gap-2`→`gap-1`; `gap-3`→`gap-4`; `px-3`→`px-2` or document exception.

2. **ARBITRARY SIZING VALUES UNDOCUMENTED** — Header gap `[18px]`, brand size `text-[1.25rem]`, state container height `min-h-[16rem]`, nav touch target `min-h-[44px]`, max-width `max-w-[68rem]` use arbitrary values outside Tailwind's default scale. — **User impact:** Non-obvious why exceptions were needed; future contributors may replace them with scale values, breaking WCAG compliance (44px) or design contracts (68rem). — **Fix:** Add inline JSDoc comments explaining each exception: `/* WCAG 2.5.5 touch target */` for 44px, `/* UI-SPEC max-width contract */` for 68rem, `/* 256px min-height prevents layout jump */` for 16rem.

3. **NO DEV SERVER SCREENSHOTS** — Audit cannot verify visual appearance, layout at 375px viewport, footer wrapping, nav active-state accent color, spinner animation, or interactive Retry button behavior. — **User impact:** Code review passes but real browser verification deferred; visual regressions could land undetected. — **Fix:** Capture screenshots at desktop (1440px), mobile (375px), and tablet (768px) viewports during next sprint; add visual regression tests to Phase 4's Playwright suite.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4) — PASS

All UI-SPEC copywriting requirements met with exact text matching.

**Verified implementations:**

- **Loading state:** `Spinner.tsx:15` renders `"Loading…"` (single ellipsis character per spec)
- **Error state heading:** `ErrorState.tsx:19` renders `"Couldn't load this page"`
- **Error state body:** `ErrorState.tsx:22` renders parameterized body with resource substitution (`"We couldn't reach {resource}…"`)
- **Retry CTA:** `ErrorState.tsx:29` button labeled `"Retry"` (exact text)
- **Empty state heading:** `EmptyState.tsx:7` renders `"Nothing here yet"`
- **Empty state body:** `EmptyState.tsx:8–10` renders exact UI-SPEC text
- **404 heading:** `NotFoundPage.tsx:9` renders `"Page not found"`
- **404 body:** `NotFoundPage.tsx:10–14` renders exact UI-SPEC text with link back to `/`
- **Footer disclaimer:** `PageShell.tsx:59–61` carries all three sentences verbatim: statistics-not-certainties, no-contests-no-stakes, not-affiliated-with-PL
- **Placeholder copy:** `PlaceholderPage.tsx:12–14` renders exact UI-SPEC text

**Error detail protection:**

- `ErrorState.tsx:44–47` routes raw errors to `console.error()`, never to DOM
- `XpTable.tsx:21` logs query errors with `console.error()` before rendering ErrorState
- `ErrorState.test.tsx:51–57` explicitly asserts thrown error message and request path do not appear in rendered output

**No generic labels found:**

- Grep search for "Submit|Click Here|OK|Cancel|Save" across all `.tsx` files yields no results
- All CTA text is specific: "Retry" (refetch trigger), not generic action labels

**Routes correctly named per UI-SPEC:**

- All 8 page titles render via `PlaceholderPage.tsx`: "xP table" (XpTable), "Rate my team" (Team), "Fixtures", "Prices", "League", "Scoreboard", "Differentials", "Method" (Methodology)
- NAV_LINKS array in `PageShell.tsx:6–15` enumerates all 8 labels in UI-SPEC Routes-table order

**No deviations.** Score: **4/4**

---

### Pillar 2: Visuals (4/4) — PASS

App shell structure, visual hierarchy, and interactive affordances meet UI-SPEC contract.

**Layout frame verified:**

- `PageShell.tsx:26–64` — non-sticky `<header>`, centred `<main>` at `max-w-[68rem]`, persistent `<footer>`
- Header and footer use `px-4` (16px) horizontal padding matching design contract
- Content wrapper inherits the same max-width and padding (no inner breakpoints added)

**Visual hierarchy via typography:**

- Display role (28px/700 Archivo): `PlaceholderPage.tsx:11`, `ErrorState.tsx:18`
- Heading role (20px/700 Archivo): `NotFoundPage.tsx:9`, `EmptyState.tsx:7`
- Body role (16px/400 IBM Plex Sans): Error/empty/placeholder body text
- Label role (14px/400 IBM Plex Sans): Nav links, footer, spinner text

All roles applied via CSS classes, not inline styling.

**Nav link visual states:**

- `PageShell.tsx:32–47` — NavLink component renders with conditional className based on `isActive` state
- Active state: `bg-accent-bg` + `font-bold` + `text-accent-ink` (heading weight + accent text on secondary background)
- Inactive state: `text-ink-2` on transparent, `hover:bg-surface` + `hover:text-ink` on hover
- All 8 links present and ordered per UI-SPEC Routes table

**Touch target sizing:**

- Nav links: `min-h-[44px]` per `PageShell.tsx:38` (WCAG 2.5.5 compliance)
- Buttons: ErrorState Retry uses same min-height via flex centering (implicit 44px from outer container)

**Loading/error/empty visuals:**

- Spinner: `Spinner.tsx:11–14` — accent-colored border (`border-t-accent`) on a spinning ring (`animate-spin`), centered
- Error heading: Display role (28px/700) in destructive color (`text-bad`)
- Empty heading: Heading role (20px/700) in primary text color
- All state containers reserve `min-h-[16rem]` to prevent layout jump on resolve

**No wireframe or pixel-perfect visual verification possible without screenshots.** However, all structural requirements and hierarchy indicators are correctly implemented. Score: **4/4**

---

### Pillar 3: Color (4/4) — PASS

Complete token architecture with light/dark values; proper usage throughout.

**Token declaration (index.css:12–73):**

- `@theme` block declares 24 custom properties covering all UI-SPEC color roles
- **Backgrounds/surfaces:** `--color-bg`, `--color-surface`, `--color-surface-2` (60% dominant, 30% secondary)
- **Text:** `--color-ink`, `--color-ink-2`, `--color-line`
- **Accent:** `--color-accent`, `--color-accent-ink`, `--color-accent-bg` (10% reserved for interactive)
- **Destructive:** `--color-bad` (reserved for error heading/icon only)
- **Reserved future:** `--color-warn`, `--color-warn-bg`, `--color-band`, `--color-band-pt`, `--color-fdr1..5-bg/ink`

**Dark mode ready:**

- Light values on `:root` in `@theme` block (lines 14–49)
- Dark override via `@media (prefers-color-scheme: dark)` block (lines 75–107)
- Swappable for `data-theme` attribute per comment on line 7
- All 24 tokens re-declared with dark values

**No hardcoded hex colors in component files:**

- Grep search for `#[0-9a-fA-F]{6}` across all `.tsx` files yields zero results
- All colors go through token names: `bg-bg`, `text-ink`, `text-accent`, `bg-accent-bg`, `text-bad`, `border-line`, etc.

**Accent usage (10% reserved for interactive):**

- Active nav link: `bg-accent-bg` + `text-accent-ink` (headings count as 700 weight emphasis, permitted)
- Retry button: `bg-accent px-4 py-2` (interactive CTA)
- Loading spinner: `border-t-accent` (motion indicator)
- Links (via React Router): `text-accent underline` (NotFoundPage back link)
- Focus outlines: implicit (framework responsibility)

**Destructive color (--bad) usage:**

- ErrorState heading: `text-bad` only (no destructive *actions* in this phase)
- Not used elsewhere (correct — reserved for error/destruction only)

**60/30/10 ratio:** Cannot be pixel-counted without screenshots, but token allocation matches design intent (3 bg/surface tokens, 3 text tokens, 3 accent variants, 1 destructive).

**No deviations.** Score: **4/4**

---

### Pillar 4: Typography (4/4) — PASS

Four roles with exact sizes/weights; two font families; Google Fonts linked.

**Role definitions (index.css:60–72):**

| Role | Size | Weight | Font | Line Height |
|------|------|--------|------|-------------|
| Label | 14px | 400 | IBM Plex Sans | 1.4 |
| Body | 16px | 400 | IBM Plex Sans | 1.5 |
| Heading | 20px | 700 | Archivo | 1.2 |
| Display | 28px | 700 | Archivo | 1.15 |

All declared as `--font-*`, `--text-*`, `--text-*--line-height` custom properties.

**Component usage (all `.tsx` files):**

- `font-label` + `text-label`: Used 7 times (nav links, footer, spinner text, captions) — `PageShell.tsx:27,38,57`, `Spinner.tsx:15`, `EmptyState.tsx:6`, etc.
- `font-body` + `text-body`: Used 5 times (error body, empty body, placeholder body) — `ErrorState.tsx:21`, `EmptyState.tsx:8`, `PlaceholderPage.tsx:12`
- `font-heading` + `text-heading`: Used 4 times (404 heading, empty heading, brand wordmark alternative) — `NotFoundPage.tsx:9`, `EmptyState.tsx:7`
- `font-display` + `text-display`: Used 3 times (error heading, placeholder title) — `ErrorState.tsx:18`, `PlaceholderPage.tsx:11`

**Font loading (index.html):**

- Google Fonts `<link>` elements load Archivo (700), IBM Plex Sans (400), IBM Plex Mono (400)
- Same three families as vanilla site (parity)

**Size/weight consistency:**

- No more than 4 font sizes in use (Label, Body, Heading, Display)
- Exactly two weights: 400 and 700 (no 300, 500, 600, 800, etc.)
- Weight 700 always pairs with Archivo (headings); 400 with IBM Plex Sans (body/UI)

**No arbitrary font values in components.** Score: **4/4**

---

### Pillar 5: Spacing (2/4) — NEEDS WORK

Spacing is partially inconsistent with the declared UI-SPEC scale. Several values deviate without documented justification.

**Declared scale (index.css:51–58):**

```
xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 32px, 2xl: 48px, 3xl: 64px
```

**Actual usage in components:**

| Component | Class | Pixel Value | Scale Match | Status |
|-----------|-------|-------------|------------|--------|
| PageShell header | `gap-[18px]` | 18px | ✗ Not in scale | Arbitrary, no explanation |
| Brand text | `text-[1.25rem]` | 20px | — | Arbitrary, but matches heading size — arguably OK |
| Nav links | `gap-0.5` | 2px | ✗ Below min (xs=4px) | Non-standard, unexplained |
| Nav links | `px-3 py-2` | 12px / 8px | ✗ px-3 not in scale | Padding should be sm(8px) or md(16px) |
| State containers | `min-h-[16rem]` | 256px | — | Arbitrary, layout-specific (not in spacing scale) |
| State containers | `gap-3` | 12px | ✗ Not in scale | Should be gap-2 (8px) or gap-4 (16px) |
| Footer max-width | `max-w-[68rem]` | 68rem | — | Per UI-SPEC contract (intentional) ✓ |
| Nav touch targets | `min-h-[44px]` | 44px | — | WCAG 2.5.5 compliance (intentional) ✓ |

**Problematic spacing values (5 instances):**

1. **Header gap:** `gap-[18px]` — No explanation for 18px (between 16px and 24px). Suggestion: Use `gap-md` (16px) or `gap-lg` (24px).
2. **Nav interior gap:** `gap-0.5` — 2px is below the declared minimum (4px). This appears to be tightly packed link styling, but should be explicit: either increase to `gap-xs` (4px) or document the exception.
3. **Nav link padding:** `px-3 py-2` — Creates 12px horizontal (not in scale) and 8px vertical (sm, OK). Should be `px-2 py-1` or `px-4 py-2` for consistency.
4. **State container gap:** `gap-3` — 12px is between sm (8px) and md (16px), not in scale. Should be `gap-2` (8px) or `gap-4` (16px).
5. **State container gap:** `gap-2` (8px) in EmptyState — This is correct (sm), but inconsistency with Spinner using `gap-3`.

**Intentional deviations (justified):**

- `max-w-[68rem]` — Per UI-SPEC layout contract; must be exact
- `min-h-[44px]` on nav links — WCAG 2.5.5 touch target minimum; must be exact
- `min-h-[16rem]` on state containers — Prevents layout jump; could be commented but is reasonable
- `text-[1.25rem]` (brand) — Matches Display heading size; reasonable choice

**Impact:** Spacing becomes inconsistent as more pages are built; new contributors may replace arbitrary values incorrectly; the scale is declared but not uniformly followed.

**Recommendation:** Standardize all spacing to the declared scale or document exceptions with inline comments. See Top 3 Priority Fixes #1 and #2.

Score: **2/4** (Significant inconsistency between declared scale and implementation, even accounting for justified WCAG/contract exceptions)

---

### Pillar 6: Experience Design (4/4) — PASS

All runtime states (loading, error, empty, 404) are implemented, tested, and isolated correctly.

**Loading state (UI-SPEC E2 loading backstop):**

- `Spinner.tsx:5–18` renders centered loader with accent ring and `Loading…` label
- `min-h-[16rem]` reserves vertical space so content jump cannot occur on resolve
- `role="status"` announces to assistive tech
- `aria-hidden="true"` on the spinning ring (decorative)
- Tested in `Spinner.test.tsx:5–56` — asserts spinner is present during pending, absent after resolve

**Error state (UI-SPEC E2 error backstop):**

- `ErrorState.tsx:13–33` displays heading (`Couldn't load this page`), body with resource substitution, Retry button
- `onRetry` prop calls the query's `refetch()` if available; falls back to `window.location.reload()` for route-level errors
- `RouteErrorBoundary.tsx:43–49` wraps ErrorState for route `errorElement` slots, reads `useRouteError()` for logging only
- Tested in `ErrorState.test.tsx:9–64` — asserts heading/button render, Retry calls callback exactly once, no error message/URL appears in DOM

**Empty state (UI-SPEC E2 empty resolution):**

- `EmptyState.tsx:4–14` displays heading (`Nothing here yet`) and body copy
- Used in `XpTable.tsx:25–26` when query resolves with no data
- Shell-level fallback per spec (per-page singular/plural copy deferred to Phase 2)

**404 state (UI-SPEC E4):**

- `NotFoundPage.tsx:6–19` displays heading (`Page not found`), body, link back to `/`
- Rendered by catch-all route (`router.tsx:64`)
- Verified via automated path-assertion script (all 9 paths registered)

**Per-route error isolation (UI-SPEC E2 partial backstop):**

- `router.tsx:20–67` — Each of 8 concrete routes has its own `errorElement`, never a shared boundary on the layout route
- One route's failed fetch cannot unmount the header nav or any sibling route (T-05-01 mitigation)
- Tested in `routeIsolation.test.tsx:1–70` — asserts nav still renders all 8 links while one route's fetch fails; sibling route still renders its placeholder

**Concurrency handling (UI-SPEC E2 concurrency backstop):**

- `routeIsolation.test.tsx:57–69` — Two routes' queries run concurrently; one route unmounted mid-flight
- No unhandled promise rejection fires on `window` or Node `process` (listener registered on both per test)
- TanStack Query configured with retries disabled in all tests to prevent flakiness

**Accessibility:**

- Nav links have 44px min-height (WCAG 2.5.5)
- `<nav aria-label="Site">` labels navigation region
- Semantic HTML: `<header>`, `<main>`, `<footer>` (not `<div>` wrappers)
- Spinner uses `role="status"` for updates
- Footer text is plain (not inaccessible to screen readers)
- No aria-hidden applied incorrectly

**No runtime verification possible without dev server.** However, all backstop requirements are code-complete and tested at the unit/integration tier.

Score: **4/4**

---

## Files Audited

**Component files:**
- `frontend/src/components/PageShell.tsx` (app shell chrome, nav, footer)
- `frontend/src/components/Spinner.tsx` (loading indicator)
- `frontend/src/components/ErrorState.tsx` (error handling, retry affordance)
- `frontend/src/components/EmptyState.tsx` (zero-item fallback)
- `frontend/src/components/PlaceholderPage.tsx` (page template)
- `frontend/src/components/NotFoundPage.tsx` (404 state)

**Route files:**
- `frontend/src/router.tsx` (route tree with per-route error boundaries)
- `frontend/src/routes/XpTable.tsx` (tracer route with state wiring)
- `frontend/src/routes/Team.tsx` through `frontend/src/routes/Methodology.tsx` (7 placeholder routes)

**Support files:**
- `frontend/src/lib/api.ts` (fetch wrappers, error handling)
- `frontend/src/index.css` (design tokens, Tailwind imports)
- `frontend/src/main.tsx` (app entry, router setup)

**Test files:**
- `frontend/src/components/Spinner.test.tsx` (loading backstop)
- `frontend/src/components/ErrorState.test.tsx` (error backstop)
- `frontend/src/routes/routeIsolation.test.tsx` (isolation + concurrency backstop)
- `frontend/src/test/harness.test.tsx` (smoke test)

**Build/config:**
- `frontend/package.json` (pinned dependencies)
- `frontend/vite.config.ts` (dev proxy, React/Tailwind plugins)
- `frontend/vitest.config.ts` (test environment)
- `frontend/index.html` (Google Fonts, app root)

---

## Notes

- **Dev server not running:** Screenshots could not be captured. Audit relies on code review only. Visual verification (footer wrapping at 375px, nav active-state color, spinner animation, interactive Retry behavior) is deferred to Phase 4's Playwright suite or manual testing.
- **Arbitrary sizing justified:** `44px` (WCAG touch target), `68rem` (UI-SPEC max-width contract), `16rem` (layout jump prevention) are correctly arbitrary. `18px`, `px-3`, `gap-0.5` are not justified and should be standardized.
- **UI-SPEC approved:** All 7 dimensions passed the checker before Phase 1 execution. This audit verifies the implementation matches the approved contract.
- **Registry safety:** No component registry used (`Tool: none`, first-party components only). Not applicable.

