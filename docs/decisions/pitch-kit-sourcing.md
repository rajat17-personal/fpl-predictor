# Decision: Pitch kit/shirt asset sourcing (PITCH-01)

**Status:** Decided
**Date:** 2026-09-03
**Phase:** 03-pitch-renderer-squad-views

## Decision

The pitch renderer's player kits are **neutral generated SVG shirts** — one hand-built, parameterized
inline SVG shape (`frontend/src/components/pitch/Kit.tsx`) coloured from a hand-maintained ~20-club
lookup table (`frontend/src/components/pitch/kitMap.ts`: primary/secondary colour pair + a
plain/stripes/hoops/sleeves pattern enum). The kits carry:

- **No club crests.**
- **No sponsor marks.**
- **No club-name text** anywhere on the SVG.
- **No image loaded from a remote host** — every kit is a self-hosted, generated shape drawn
  entirely with SVG primitives, produced in-process at render time.

This is chosen explicitly **over** using FPL's own shirt-image CDN (as the official app does).
FPL's CDN URL patterns were never captured or depended on — the roadmap's original research flag
("capture FPL CDN URLs from devtools before building the shirt component") is **closed as moot by
this decision**, not answered by doing that capture. The blocker `.planning/STATE.md` carries for
Phase 3 ("FPL shirt/kit CDN URL patterns are unverified community knowledge... trademark posture
must be documented, not deferred") is retired by this documented decision, not by any devtools
capture work.

## Reasoning

For a pre-revenue product moving toward paid launch (season-pass subscriptions, target July 2027),
the marginal recognisability gain of hotlinking or reproducing official club/league imagery is
small relative to the trademark and hotlinking exposure it would create. Fantasy-sports apps that
reuse official team logos or league-served imagery without a licensing relationship are a
recurring subject of trademark/passing-off concern in general commentary on the space [directional
framing only, see `03-RESEARCH.md` Pitfall 6 and its cited sources — non-official, non-legal-advice
discussion of the general risk category, not a legal opinion for this project]. Self-hosted,
crest-free, sponsor-free, neutral kits sidestep that exposure entirely: there is no club or league
mark anywhere in the asset, and no request ever leaves this app's own origin to fetch one.

This trades a small amount of visual fidelity (a Liverpool shirt reads as "red kit, teal trim,
plain pattern" rather than the exact retail jersey) for a materially safer posture ahead of the
eventual payment-gateway review — the review most likely to scrutinize trademark exposure before
approving a paid subscription product.

The ~20-club colour/pattern map's cosmetic accuracy is a low-risk, easily-corrected detail (see
`03-RESEARCH.md`'s Assumption A1) — a wrong hex is a one-line fix and carries no legal exposure,
since no crest or sponsor mark is ever used regardless of colour accuracy.

## Where the disclaimer lives

The non-affiliation and generic-kit-imagery disclaimer lives in the **shared `PageShell` footer**,
rendered on every page of the site (not a team-page-specific disclaimer) — the strongest posture
for the eventual payment-gateway review, per D-03. The footer's existing non-affiliation sentence
gains one additional sentence for this phase:

> "Player kit colors shown are generic illustrations, not licensed team imagery."

## Reversibility

**Costly.** This decision, the footer disclaimer posture, and every pitch/kit component
(`Kit.tsx`, `kitMap.ts`, `PlayerCard.tsx`, `Pitch.tsx`) are built entirely around self-hosted SVGs
with no crest/sponsor/CDN dependency. Switching to FPL CDN imagery later is not a component swap —
it reopens the trademark review this decision was written to close, requires re-litigating the
hotlinking/licensing question, and touches every place a kit is rendered.

## Related

- `.planning/phases/03-pitch-renderer-squad-views/03-CONTEXT.md` — D-01, D-02, D-03, D-04 (the
  locked decisions this doc documents)
- `.planning/phases/03-pitch-renderer-squad-views/03-RESEARCH.md` — Pitfall 6 (trademark posture
  framing), Assumption A1 (kit colour/pattern accuracy)
- `.planning/phases/03-pitch-renderer-squad-views/03-UI-SPEC.md` — Kit/Shirt System section (the
  full 20-club colour/pattern table)
- `.planning/phases/03-pitch-renderer-squad-views/PARITY-DEVIATIONS.md` — ledger entries 9-10
  (nav rename, footer disclaimer sentence)
