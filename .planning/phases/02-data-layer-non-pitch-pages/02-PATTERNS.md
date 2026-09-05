# Phase 2: Data Layer & Non-Pitch Pages - Pattern Map

**Mapped:** 2026-09-01
**Files analyzed:** 24 (new/modified)
**Analogs found:** 24 / 24

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/lib/sortable.ts` | utility | transform | `web/assets/app.js` (`makeSortable`, lines 57-79) | exact (port) |
| `frontend/src/lib/bandCell.ts` | utility | transform | `web/assets/app.js` (`bandCell`, lines 91-102) | exact (port) |
| `frontend/src/lib/format.ts` | utility | transform | `web/index.html` / `web/prices.html` `.toFixed`/`.toLocaleString` call sites | exact (port) |
| `frontend/src/lib/statusFlag.tsx` | component | transform | `web/assets/app.js` (`statusFlag`, lines 81-88) | exact (port, upgraded to accessible tooltip per D-09) |
| `frontend/src/lib/deadline.ts` | utility | transform | `web/assets/app.js` (`fmtDeadline`, lines 30-42) | exact (port + D-19/D-20 extension) |
| `frontend/src/lib/theme.ts` | utility/hook | event-driven | none in vanilla — new capability (D-14..D-17) | no analog |
| `frontend/src/components/GwBanner.tsx` | component | request-response | `web/assets/app.js` (`initChrome`, lines 44-54) + `frontend/src/routes/XpTable.tsx` (useQuery pattern) | role-match |
| `frontend/src/components/ThemeToggle.tsx` | component | event-driven | none in vanilla — new capability | no analog |
| `frontend/src/components/FdrCell.tsx` | component | transform | `web/fixtures.html` (fixture cell markup, lines 69-77) | exact (port) |
| `frontend/src/components/BandCell.tsx` | component | transform | `web/assets/app.js` (`bandCell`) + `web/index.html`/`web/differentials.html` usage | exact (port) |
| `frontend/src/content/methodology.md` | content | file-I/O | `web/methodology.html` (prose, lines 30-77) | exact (verbatim port) |
| `frontend/src/routes/XpTable.tsx` | route/component | request-response | `web/index.html` (inline script, lines 83-131) | exact — flagship (D-06) |
| `frontend/src/routes/Fixtures.tsx` | route/component | request-response | `web/fixtures.html` (inline script, lines 55-78) | exact |
| `frontend/src/routes/Prices.tsx` | route/component | request-response | `web/prices.html` (inline script, lines 54-103) | exact |
| `frontend/src/routes/League.tsx` | route/component | request-response | `web/league.html` (inline script, lines 53-80) | exact |
| `frontend/src/routes/Scoreboard.tsx` | route/component | request-response | `web/scoreboard.html` (inline script, lines 60-94) | exact (special-cased error handling, Pitfall 2) |
| `frontend/src/routes/Differentials.tsx` | route/component | request-response | `web/differentials.html` (inline script, lines 54-77) | exact |
| `frontend/src/routes/Methodology.tsx` | route/component | file-I/O | `web/methodology.html` (static markup) + `react-markdown` | role-match |
| `frontend/src/lib/usePageMeta.ts` (or hook file) | hook | transform | `web/*.html` `<title>`/`<meta name="description">` per page | new capability, data source is verbatim per-page copy |
| `frontend/index.html` (inline theme script + font preloads) | config | event-driven | `web/index.html` head block (fonts/meta) — pattern differs (self-hosted vs CDN) | role-match |
| `frontend/src/index.css` (dark palette) | config | transform | `frontend/src/index.css` existing `@media (prefers-color-scheme: dark)` block (lines 75-108) | exact — migrate to `.dark` class selector |
| `frontend/src/components/PageShell.tsx` (modified: mount GwBanner + ThemeToggle) | component | request-response | itself (existing `ml-auto` slot, line 55) | exact |
| Fixture JSON files (`frontend/src/test/fixtures/*.json`) | test | file-I/O | `web/data/*.json` live samples | exact (hand-authored subsets) |
| `*.test.ts(x)` files (sortable, bandCell, GwBanner, theme, statusFlag, per-route) | test | transform | `frontend/src/components/PageShell.test.tsx`, `ErrorState.test.tsx`, `Spinner.test.tsx` (existing Vitest/RTL harness) | exact |

## Pattern Assignments

### `frontend/src/lib/sortable.ts` (utility, transform)

**Analog:** `web/assets/app.js` lines 57-79 (`makeSortable`)

**Core pattern — verified sort comparator** (lines 71-75):
```javascript
const sorted = [...rows()].sort((a, b) => {
  const [x, y] = [a[state.key], b[state.key]];
  if (numeric) return state.dir * ((y ?? -1e9) - (x ?? -1e9));
  return state.dir * String(y ?? "").localeCompare(String(x ?? ""));
});
```

**Direction/arrow polarity** (lines 65-69) — copy exactly, do not "fix" the inverted arrow (see RESEARCH.md Pitfall 1):
```javascript
btn.addEventListener("click", () => {
  state = { key: th.dataset.key,
            dir: state.key === th.dataset.key ? -state.dir : -1 };
  ths.forEach((h) => h.querySelector(".dir").textContent =
    h === th ? (state.dir < 0 ? "▼" : "▲") : "");
```
Verified truth table: fresh click `dir=-1` → ascending, nulls first, arrow ▼. Second click `dir=+1` → descending, nulls last, arrow ▲.

**Port target:** extract as a typed function `sortRows<T>(rows: T[], key: keyof T, dir: 1 | -1, numeric: boolean): T[]` per RESEARCH.md's Pattern 1 example — same file has the full TypeScript signature to copy.

---

### `frontend/src/lib/bandCell.ts` + `frontend/src/components/BandCell.tsx` (utility/component, transform)

**Analog:** `web/assets/app.js` lines 90-102 (`bandCell`)

```javascript
export function bandCell(r, maxHi) {
  const lo = r.p10 ?? r.xp, hi = r.p90 ?? r.xp;
  const pct = (v) => `${Math.min(100, 100 * v / maxHi)}%`;
  const title = `xP ${r.xp?.toFixed(2)} — actual score lands between ${lo?.toFixed(1)} and ${hi?.toFixed(1)} in 8 gameweeks out of 10`;
  return `<span class="band" title="${title}">
    <span class="val">${r.xp?.toFixed(2)}</span>
    <span class="track-wrap" aria-hidden="true">
      <span class="track" style="left:${pct(lo)};width:calc(${pct(hi)} - ${pct(lo)})"></span>
      <span class="pt" style="left:calc(${pct(r.xp)} - 4px)"></span>
    </span>
    <span class="range">${lo?.toFixed(1)}–${hi?.toFixed(1)}</span></span>`;
}
```

**Critical: width uses a CSS `calc()` string, not a pre-subtracted JS number** — see RESEARCH.md Pitfall 4. Reproduce `style={{ left: pct(lo), width: \`calc(${pct(hi)} - ${pct(lo)})\` }}` in JSX, not a computed `widthPct`.

**Tooltip copy is verbatim (D-03, Rule R9):** `xP {xp.toFixed(2)} — actual score lands between {lo.toFixed(1)} and {hi.toFixed(1)} in 8 gameweeks out of 10`. Port to the D-09 accessible-tooltip component (popover/click-toggle) instead of the `title` attribute.

**Two callers with different `maxHi` — do not unify:**
- xP table (`web/index.html:89`): `Math.max(...top.map(r => r.p90 ?? r.xp))` — no floor
- Differentials (`web/differentials.html:66`): `Math.max(1, ...rows.map(r => r.p90 ?? r.xp))` — floor of 1

---

### `frontend/src/lib/statusFlag.tsx` (component, transform)

**Analog:** `web/assets/app.js` lines 81-88 (`statusFlag`)

```javascript
export function statusFlag(r) {
  if (r.status === "a") return "";
  const out = ["i", "s", "u", "n"].includes(r.status);
  const label = out ? "unavailable" : "doubtful";
  const cls = out ? "flag out" : "flag";
  const news = (r.news || label).replace(/"/g, "&quot;");
  return ` <span class="${cls}" role="img" aria-label="${label}" title="${news}">${out ? "✕" : "▲"}</span>`;
}
```
Renders only when `status !== "a"`. Tooltip text = `r.news || label`. D-09 upgrade: replace the desktop-only `title` attribute with a tap/click-friendly popover or inline reveal, keeping the `role="img"` / `aria-label` semantics and the exact glyph/class mapping.

---

### `frontend/src/lib/deadline.ts` + `frontend/src/components/GwBanner.tsx` (utility+component, request-response)

**Analog:** `web/assets/app.js` lines 30-54 (`fmtDeadline`, `initChrome`)

**Verbatim `{abs}` format port** (lines 30-42):
```javascript
export function fmtDeadline(iso) {
  if (!iso) return "deadline TBC";
  const d = new Date(iso);
  const diff = d - Date.now();
  const rel = diff > 0
    ? `in ${Math.floor(diff / 864e5)}d ${Math.floor((diff % 864e5) / 36e5)}h`
    : "passed";
  const abs = d.toLocaleString(undefined, {
    weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
  return `${abs} · ${rel}`;
}
```
D-19/D-20 extend this: graduated `{rel}` granularity (per-minute default, per-second inside final hour) and a `{freshness}` line derived from `meta.json`'s `generated_utc`. D-21: when `diff <= 0`, render "GW{n} deadline passed" instead of `rel === "passed"`'s bare word.

**Chrome-mount fetch + graceful degradation pattern** (lines 44-54):
```javascript
export async function initChrome(page) {
  ...
  try {
    const meta = await loadJSON("meta.json");
    const el = document.querySelector(".deadline");
    if (el) el.textContent = `GW${meta.gw} deadline: ${fmtDeadline(meta.deadline_utc)}`;
    return meta;
  } catch { return null; }
}
```
D-22: on `meta.json` fetch failure, GwBanner shows quiet "deadline TBC" fallback, not `ErrorState` (D-08's rich-error rule applies to page data, not this banner). Port as a `useQuery(["meta"], () => fetchJson<MetaResponse>("/data/meta.json"))` call (already proven working in `frontend/src/routes/XpTable.tsx` lines 11-14) mounted in `PageShell.tsx`'s existing `ml-auto` slot (line 55).

---

### `frontend/src/routes/XpTable.tsx` (route, request-response) — FLAGSHIP (D-06)

**Analog:** `web/index.html` lines 83-131 (inline script)

**Imports pattern** (current scaffold, `frontend/src/routes/XpTable.tsx` lines 1-5):
```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchJson, type MetaResponse } from "../lib/api";
import { Spinner } from "../components/Spinner";
import { ErrorState } from "../components/ErrorState";
import { EmptyState } from "../components/EmptyState";
```

**Core pattern — slice/filter/sort pipeline** (`web/index.html` lines 86-113):
```javascript
const meta = await initChrome("index");
const table = await loadJSON("xp_table.json");
const top = table.slice(0, 50);                 // R10: NO re-sort — assumes pipeline pre-sorts desc by xp
const maxHi = Math.max(...top.map((r) => r.p90 ?? r.xp));  // R11: no floor

function rows() {
  return top.filter((r) =>
    (posFilter === "ALL" || r.position === posFilter) &&
    (!query || r.name.toLowerCase().includes(query) ||
     r.team.toLowerCase().includes(query) ||           // full team name, not displayed
     r.team_short.toLowerCase().includes(query)));
}
```
Search normalization (R13): `e.target.value.trim().toLowerCase()`.

**Format rules per column (R14-R16):**
```javascript
${r.price_m.toFixed(1)}                    // £m — no fallback
${r.ownership?.toFixed(1) ?? "–"}          // Own % — HAS "–" fallback
${r.xp_capt?.toFixed(2) ?? "–"}            // Captain xP — HAS "–" fallback
```

**Captain sub-table** (`web/index.html` lines 124-129) — different fallback rules (Pitfall 3):
```javascript
const capt = await loadJSON("captains.json");
document.querySelector("#capt tbody").innerHTML = capt.slice(0, 5).map((r) => `<tr>
  <td>${r.name}</td><td>${r.team}</td>
  <td class="n">${r.price_m.toFixed(1)}</td>
  <td class="n">${r.ownership?.toFixed(1)}</td>              <!-- NO "–" fallback (R18) -->
  <td class="n">${r.xp_capt.toFixed(2)}</td></tr>`).join("");  <!-- no optional chaining (R19) -->
```

**Copy (verbatim, D-03):** top-50 note — "Showing the top 50 by xP — the free preview. The full table, CSV download and your-team transfer planning are coming with the Pro tier." (`web/index.html` line 59-60). Reading-the-numbers explainer (lines 61-66). Header sub-copy (lines 30-34).

**Error/empty pattern** — reuse the already-proven `ErrorState`/`EmptyState`/`Spinner` from `frontend/src/routes/XpTable.tsx`'s current tracer implementation (lines 16-27):
```typescript
if (isPending) return <Spinner />;
if (isError) { console.error(error); return <ErrorState resource="the gameweek data" onRetry={() => refetch()} />; }
if (!data) return <EmptyState />;
```

---

### `frontend/src/routes/Fixtures.tsx` (route, request-response)

**Analog:** `web/fixtures.html` lines 55-78 (inline script) + `frontend/src/routes/Fixtures.tsx` (current placeholder to replace)

**Current placeholder to replace** (`frontend/src/routes/Fixtures.tsx`, whole file):
```typescript
import PlaceholderPage from "../components/PlaceholderPage";
export default function Fixtures() {
  return <PlaceholderPage title="Fixtures" />;
}
```

**Core pattern — dynamic GW columns + FDR cell** (`web/fixtures.html` lines 60-77):
```javascript
const gws = ticker[0].gws.map((g) => g.gw);     // R20: dynamic column count
...
${t.gws.map((g) => {
  if (!g.fixtures.length)                        // R21: blank-GW cell
    return `<td class="cellpad"><span class="fdr fdr3" title="Blank gameweek">—</span></td>`;
  return `<td class="cellpad">${g.fixtures.map((f) => `
    <span class="fdr fdr${f.fdr}" title="${f.home ? "Home" : "Away"} vs ${f.opp}, difficulty ${f.fdr}">
      ${f.opp}<small>${f.home ? "H" : "A"}</small>
    </span>`).join(" ")}</td>`;
}).join("")}
```
`xG next`/`xGC next` (R23): `t.xg_next?.toFixed(2) ?? "–"`. `Ease` (R24): `t.ease.toFixed(2)` — no fallback. Fdr color classes map through `--color-fdr{1..5}-bg/-ink` tokens already declared in `frontend/src/index.css`.

**Copy (verbatim):** sub-paragraph lines 31-36, legend lines 41-48.

---

### `frontend/src/routes/Prices.tsx` (route, request-response)

**Analog:** `web/prices.html` lines 54-103 (inline script)

**Core pattern — progress bar math** (lines 83-89):
```javascript
const raw = r.prob ?? r.progress ?? 0;
const pct = Math.round(100 * Math.abs(raw));
const bar = Math.min(pct, 100);
const label = w.mode === "official"
  ? `${pct}%${r.proj_tonight != null ? ` → ${Math.round(100 * Math.abs(r.proj_tonight))}% tonight` : ""}`
  : (r.prob != null ? `${pct}%` : `${bar}% of threshold`);
```

**Three mode-note copy variants (verbatim, D-03)** (lines 61-79) — `official` / `heuristic` / trained-model else-branch; `official` mode appends the locked-players sentence only if `w.locked_players` is truthy (R31).

**Format rules (R28-R29):**
```javascript
${r.price_m.toFixed(1)}                       // no optional chaining
${r.ownership.toFixed(1)}                     // no optional chaining, no fallback
${(r.net_transfers ?? 0).toLocaleString()}    // toLocaleString, NOT toFixed
```

**Watchlist shape caveat (Assumption A3, RESEARCH.md):** only `official` mode is exercisable against live `web/data/watchlist.json`; grep `models/price.py`'s watchlist-dict construction before authoring `heuristic`/trained-mode fixtures.

---

### `frontend/src/routes/League.tsx` (route, request-response)

**Analog:** `web/league.html` lines 53-80 (inline script)

```javascript
const standings = await loadJSON("standings.json");
// row index, not a data field (R32):
${i + 1}
// GD sign — no "+" for zero/negative (R33):
${t.gd > 0 ? "+" + t.gd : t.gd}

const leaders = await loadJSON("leaders.json");
const BOARDS = [
  ["points", "Most FPL points"], ["goals", "Most goals"],
  ["assists", "Most assists"], ["clean_sheets", "Clean sheets (GK/DEF)"],
  ["cards", "Most cards"],
];
// each board: .slice(0, 8), fallback when empty (R34):
${(leaders[key] || []).slice(0, 8).map(...).join("") || "<li><span class='pos'>Nothing yet this season</span></li>"}
```

---

### `frontend/src/routes/Scoreboard.tsx` (route, request-response — special-cased)

**Analog:** `web/scoreboard.html` lines 60-94 (inline script)

**Vanilla's uniform swallow (do NOT replicate as-is — see Pitfall 2):**
```javascript
let board = null;
try { board = await loadJSON("scoreboard.json"); } catch {}
const entries = board?.entries ?? [];
```
D-08 requires distinguishing 404 (→ empty, verbatim vanilla copy) from a real 5xx/network failure (→ `ErrorState`). Write a dedicated query fn per RESEARCH.md's Pattern 2:
```typescript
async function fetchScoreboard(): Promise<ScoreboardResponse | null> {
  const res = await fetch("/data/scoreboard.json");
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`/data/scoreboard.json: ${res.status}`);
  return res.json();
}
```

**Empty-state tiles (verbatim, R36):** "Backtest MAE: 0.87 vs FPL 1.07" / "Backtest rank corr: 0.74 vs FPL 0.30" / "Seasons validated: 6" (lines 82-84).

**Populated tiles (R37):** `${s.mae_model} vs FPL ${s.mae_fpl ?? "–"}`, `${s.spearman_model} vs FPL ${s.spearman_fpl ?? "–"}`, `s.gameweeks`, `s.captain_avg_points`.

**History row nullability (R38):** `e.mae_fpl ?? "–"`, `e.spearman_fpl ?? "–"`.

**Fixture note:** `scoreboard.json` doesn't exist on disk pre-season — synthesize a populated fixture from `predict/scoreboard.py`'s output shape (see RESEARCH.md Open Question 2 for the full field enumeration).

---

### `frontend/src/routes/Differentials.tsx` (route, request-response)

**Analog:** `web/differentials.html` lines 54-77 (inline script)

```javascript
const table = await loadJSON("xp_table.json");
const slider = document.querySelector("#own");
function render() {
  const cap = Number(slider.value);
  const rows = table
    .filter((r) => (r.ownership ?? 100) <= cap && r.status === "a")   // R39
    .slice(0, 30);
  const maxHi = Math.max(1, ...rows.map((r) => r.p90 ?? r.xp));       // R40: floor of 1, differs from xP table
  ...
  <td class="n">${r.ownership?.toFixed(1)}</td>   // R41: no "–" fallback, same as captains
}
slider.addEventListener("input", render);
render();
```
Own-cap slider: `min=1 max=25 value=10 step=1`, label updates to `${cap}%` on input (lines 34-37).

---

### `frontend/src/routes/Methodology.tsx` + `frontend/src/content/methodology.md` (route/content, file-I/O)

**Analog:** `web/methodology.html` lines 30-83 (static prose — port verbatim per D-03)

Sections to port 1:1 into markdown: "Prediction", "Uncertainty", "Selection", "The receipts" (4 tiles: Fixture MAE 0.87 vs FPL 1.07, Rank correlation 0.74 vs FPL 0.30, Season points ~2260, Edge over form-picking +102), "Honesty policy" (3 bullet list items). Render via `react-markdown` (no `dangerouslySetInnerHTML`), imported at build time — the one page this phase whose data source is a bundled file, not a runtime `/data/*.json` fetch (D-10's own carve-out, confirmed by RESEARCH.md's architecture map).

---

## Shared Patterns

### Data fetching (TanStack Query + relative-path discipline)
**Source:** `frontend/src/lib/api.ts` (whole file) + `frontend/src/routes/XpTable.tsx` lines 11-14
**Apply to:** All 7 route files
```typescript
async function fetchAndCheck<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return (await res.json()) as T;
}
export function fetchJson<T>(path: string): Promise<T> { return fetchAndCheck<T>(path); }
```
Always fetch the root-relative form (`/data/xp_table.json`), never `data/xp_table.json` — vanilla's relative form breaks under client-side routing (Pitfall 5). Every new JSON shape gets a TS interface added to this file (per the file's own header comment, line 1-8), mirroring the existing `MetaResponse` pattern (lines 29-36).

### Error/empty/loading states
**Source:** `frontend/src/components/ErrorState.tsx`, `EmptyState.tsx`, `Spinner.tsx`
**Apply to:** All 7 route files (D-08); Scoreboard uses a modified fetch fn (see Pattern above) but the same `ErrorState`/`EmptyState` components
```typescript
export function ErrorState({ resource, onRetry }: ErrorStateProps) {
  const handleRetry = onRetry ?? (() => window.location.reload());
  return ( /* centred block, "Couldn't load this page" heading, resource-named body, Retry button */ );
}
```
Per-page `resource` string should be specific ("the xP table", "fixture data", "price watch data", etc.) — pattern already established for the tracer route ("the gameweek data").

### PageShell mount points
**Source:** `frontend/src/components/PageShell.tsx` line 55
```tsx
{/* Meta-banner slot — Phase 2 UI-06 live deadline countdown lands here. */}
<div className="ml-auto" />
```
Replace this comment/div with `<GwBanner />` and add `<ThemeToggle />` alongside it in the same header row. Do not touch the nav/brand/footer structure (68rem containment already regression-tested per `PageShell.test.tsx`).

### Design tokens — dark mode migration
**Source:** `frontend/src/index.css` lines 12-108
```css
@theme { --color-bg: #fafbf7; /* ... */ }
@media (prefers-color-scheme: dark) {
  :root { --color-bg: #111815; /* same token names, dark values */ }
}
```
D-16/D-17: migrate the `@media` block to a `.dark { … }` class selector fed by Tailwind v4's `@custom-variant dark (&:where(.dark, .dark *));` (declared in the CSS entry file, no `tailwind.config.js`). Keep every token *name* and *dark value* as-is — additive migration, not a rewrite. The `--color-fdr*`, `--color-band*`, `--color-warn*` tokens already have dark variants declared (lines 91-106) — these were pre-declared in Phase 1 specifically for this phase to activate.

### Vanilla page chrome → PageShell equivalence table
Every vanilla page (`web/*.html`) shares this identical header/footer block (see any of the 7 files, lines ~14-28 and ~48-58) — already fully ported to `PageShell.tsx`. Per-page `<title>`/`<meta name="description">` values (verbatim, D-11) must be extracted per page for the new `usePageMeta` hook:

| Route | Title | Description |
|-------|-------|--------------|
| `/` | `FPL ML — expected points, honestly measured` | `Machine-learned FPL expected points with uncertainty bands, an optimal squad, and a public accuracy scoreboard.` |
| `/fixtures` | `Fixture ticker — FPL ML` | `Next six gameweeks of fixture difficulty for every Premier League club.` |
| `/prices` | `Price watch — FPL ML` | `Likely FPL price risers and fallers tonight.` |
| `/league` | `League table & leaders — FPL ML` | `Premier League standings and season player leaderboards: goals, assists, clean sheets, cards.` |
| `/scoreboard` | `Accuracy scoreboard — FPL ML` | `Every prediction this model makes, scored publicly against FPL's own expected points.` |
| `/differentials` | `Differentials — FPL ML` | `High expected points, low ownership: template-breaking FPL picks.` |
| `/methodology` | `How the model works — FPL ML` | `A two-stage ML model plus integer programming, validated over six seasons of walk-forward backtests.` |

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/lib/theme.ts` | utility/hook | event-driven | Vanilla site has no dark-mode toggle at all — pure new capability. Use RESEARCH.md's "State of the Art" section (Tailwind v4 `@custom-variant dark`) plus D-14..D-17 for the design; `matchMedia` + `localStorage` idiom has no in-repo precedent to copy from. |
| `frontend/src/components/ThemeToggle.tsx` | component | event-driven | Same — new capability, no vanilla analog. Follow D-15's three-state (Light/Dark/System) segmented-control shape; style with existing Tailwind tokens. |
| `frontend/index.html` inline theme script | config | event-driven | D-16's pre-mount flash-prevention script is new; no vanilla equivalent (vanilla has no theme at all). Standard inline `<script>` in `<head>` reading `localStorage` + `matchMedia` before React mounts — pattern is well-known, not project-local. |

## Metadata

**Analog search scope:** `web/` (7 HTML pages + `assets/app.js` + `assets/style.css`), `frontend/src/` (lib, components, routes)
**Files scanned:** 16 (all confirmed git-tracked via `git ls-files`)
**Pattern extraction date:** 2026-09-01
