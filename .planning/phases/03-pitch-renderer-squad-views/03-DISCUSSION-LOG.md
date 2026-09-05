# Phase 3: Pitch Renderer & Squad Views - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-02
**Phase:** 3-Pitch Renderer & Squad Views
**Areas discussed:** Pitch & player card design, Team page flow & solver UX, Rate-my-team diff & chip timing, Kit & shirt sourcing, Solve wait & result display, Tab structure & deep links

---

## Pitch & player card design

| Option | Description | Selected |
|--------|-------------|----------|
| FPL-style green pitch | Green gradient, white markings, formation rows, bench strip; needs dark-safe greens in D-17 palette | ✓ |
| Neutral surface, formation rows | Rows on existing tokens; reads as a grouped list, not a pitch | |
| Subtle hybrid | Muted green tint + faint halfway line | |

**User's choice:** FPL-style green pitch (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Range text on card | Always-visible mono 'p10–p90' line under xP | ✓ |
| Tap-to-reveal detail | Interval behind a D-09 popover | |
| Mini band bar | Tiny BandCell-style bar; likely unreadable at card width | |

**User's choice:** Range text on card (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Shrink cards to fit | Full formation always fits viewport width (official FPL app pattern) | ✓ |
| Fixed card size + pitch scroll | Horizontal pan on narrow screens | |
| Reflow to vertical list on phones | Collapse to position-grouped rows below a breakpoint | |

**User's choice:** Shrink cards to fit (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Derive VC in UI | VC = highest xp_capt starter (join xp_table.json) who isn't captain | ✓ |
| Show C badge only | Drop VC, ledger the deviation | |
| Add VC to the export/API | Contract change mid-milestone | |

**User's choice:** Derive in UI (recommended)

---

## Team page flow & solver UX

| Option | Description | Selected |
|--------|-------------|----------|
| Tabs/sections on one route | One /team route; pitch+solver primary, rate & chips as tabs/sections | ✓ |
| Single long scroll page | Everything stacked vertically | |
| Sub-routes under /team | /team/rate, /team/chips nested routes | |

**User's choice:** Tabs/sections on one route (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Tap card → action menu | Popover with Lock / Exclude / clear + player detail (D-09 pattern) | ✓ |
| Toggle mode + tap | Lock-mode/exclude-mode toolbar toggles | |
| Side list with checkboxes | Roster list beside the pitch | |

**User's choice:** Tap card → action menu (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Essentials only | Free transfers (prefilled, editable) + max transfers + horizon | ✓ |
| Full control panel | All knobs incl. mode and budget override | |
| Zero knobs | Just a Solve button | |

**User's choice:** Essentials only (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-load default entry | Load 6980093 immediately on arrival | |
| Prefill but wait for click | Input prefilled, pitch empty until Load | |
| Remember last entry | localStorage persistence | |
| *(follow-up)* Model's recommended squad | Default pitch renders squad.json, clearly labeled | ✓ |
| *(follow-up)* Blank pitch + empty state | Empty silhouette + EmptyState prompt | |

**User's choice:** Free-text: "keep blank or something better would not want a random team to show up every time. maybe a blank or sample team?" → follow-up question → Model's recommended squad (recommended)
**Notes:** User explicitly rejected auto-loading any user entry by default; 6980093 stays a placeholder/example only.

---

## Rate-my-team diff & chip timing

| Option | Description | Selected |
|--------|-------------|----------|
| One pitch + swap overlays | Red 'out' treatment, ghost buy cards, swap list beside | ✓ |
| Side-by-side pitches | Yours vs optimal; collapses badly on mobile | |
| Score tiles + paired swap list | No pitch involvement; barely visual | |

**User's choice:** One pitch + swap overlays (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep all of it | Tiles, best XI, multi-week plan flow, copy verbatim + new diff | ✓ |
| Tiles + diff only | Drop the plan flow this phase | |
| Diff-first redesign | Rebuild around the diff | |

**User's choice:** Keep all of it (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| GW timeline strip | Season timeline with DGW/BGW markers + note as headline | ✓ |
| Explanation card + upcoming list | Note headline + list of upcoming DGW/BGW weeks | |
| Per-chip recommendation panel | Needs data chips.json doesn't carry | |

**User's choice:** GW timeline strip (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| On demand per tab | /api/rate fetches when the Rate tab opens, cached | ✓ |
| Auto-run on team load | Triple-solve on every load | |

**User's choice:** On demand per tab (recommended)

---

## Kit & shirt sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| FPL CDN shirts | Official shirt images, URLs captured via devtools (was recommended) | |
| Neutral generated kits | Self-made generic SVG shirts in club colors, self-hosted | ✓ |
| CDN with neutral fallback | Both systems | |

**User's choice:** Neutral generated kits — chosen over the recommended CDN option
**Notes:** Legally cleanest for monetization; removes the devtools-CDN-capture research dependency.

| Option | Description | Selected |
|--------|-------------|----------|
| Colors + basic pattern | Club colors + pattern enum (plain/stripes/hoops/sleeves), ~20-club map | ✓ |
| Flat two-color shirts | Body + trim only | |
| No shirts — initials chip | Team-code chip in club colors | |

**User's choice:** Colors + basic pattern (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Global footer, every page | Non-affiliation line in shared PageShell footer | ✓ |
| Team page only | Scoped to where shirts render | |

**User's choice:** Global footer, every page (recommended)

---

## Solve wait & result display

| Option | Description | Selected |
|--------|-------------|----------|
| Inline status + honest copy | Button disables, inline status line, vanilla wait copy | ✓ |
| Pitch overlay shimmer | Dim + skeleton over the pitch | |
| Blocking progress modal | Modal until solve returns | |

**User's choice:** Inline status + honest copy (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Pitch updates in place + summary | Post-solve squad on the pitch, IN badges, compact results bar | ✓ |
| Results panel below, pitch untouched | Separate output panel | |
| Before/after toggle | Segmented current/after switch | |

**User's choice:** Pitch updates in place + summary (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Iterate freely + reset button | Locks persist across re-solves; 'Reset to loaded squad' action | ✓ |
| One-shot solves | Each solve clears marks and results | |

**User's choice:** Iterate freely + reset button (recommended)

---

## Tab structure & deep links

| Option | Description | Selected |
|--------|-------------|----------|
| 3 tabs: Squad / Rate / Chips | Each concern its own lazy-fetching tab, Squad default | ✓ |
| 2 tabs, chips inside Squad | Chips beneath the plan area | |
| No tabs — sticky section nav | One scrolling page | |

**User's choice:** 3 tabs (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| entry + tab in URL | /team?entry=…&tab=… ; rate deep link auto-runs | ✓ |
| entry only | Tabs pure component state | |
| No URL state | No deep links | |

**User's choice:** entry + tab in URL (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Rename to 'My team' | Page outgrew the vanilla name; one-line ledger entry | ✓ |
| Keep 'Rate my team' | Zero nav-copy deviation | |

**User's choice:** Rename to 'My team' (recommended)

---

## Claude's Discretion

- Model-squad pitch interactivity (view-only vs lock/exclude + entry-less wildcard solve) — offered as a gray area ("Model-squad interactions"), user chose not to discuss it
- GK kit differentiation, unmapped-club fallback colors, kit SVG construction details
- Tab component implementation and `?tab=` sync mechanics
- IN-badge / out-treatment styling specifics
- Transfers summary bar formatting (mirror vanilla plan-flow copy where it exists)
- Location of the committed PITCH-01 decision doc

## Deferred Ideas

None — discussion stayed within phase scope.
