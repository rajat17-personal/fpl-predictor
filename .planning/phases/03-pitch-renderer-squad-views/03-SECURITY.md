---
phase: "03"
slug: "pitch-renderer-squad-views"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-03"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser → static export (`/data/*.json`) | Pipeline-authored data (player names, news, chip notes) crosses into the DOM | Public FPL data, low sensitivity |
| browser → self-hosted asset surface | Kit SVGs generated in-process; no third-party origin contacted | None (inline SVG only) |
| browser → `/api/team/{entry}`, `/api/rate/{entry}` | User-supplied entry ID crosses into a server request proxying the upstream FPL API | Numeric entry ID |
| browser → `/api/plan`, `/api/solve` | User-chosen horizon, locks, excludes and solver bounds cross into server-side integer programming | Numeric player codes, bounded solver params |
| URL → application state | `?entry=` and `?tab=` are attacker-controllable inputs on any shared link | Query-string values |
| API response → DOM | Player/manager names and suggested-move strings cross into rendered output | Public FPL strings |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | `PlayerCard`/`Pitch` rendering pipeline strings | medium | mitigate | JSX text nodes only; raw-HTML-injection grep gate (03-01 Task 2) — grep re-run clean 2026-09-03 (only read-only assertions in Kit.test.tsx) | closed |
| T-03-02 | Information Disclosure | `Kit.tsx`/`kitMap.ts` remote image host | low | mitigate | Inline SVG shapes, no `<image>`/external URL; remote-host grep gate — re-run clean | closed |
| T-03-03 | Spoofing | Trademark/passing-off from club imagery | medium | mitigate | Neutral generated kits (D-01), footer disclaimer in `PageShell.tsx`, committed `docs/decisions/pitch-kit-sourcing.md`; posture signed off in UAT test 3 | closed |
| T-03-04 | Information Disclosure | Pipeline exports bundled into prod build | low | mitigate | `scripts/verify_frontend_build.sh` gate present; root-relative runtime fetches only | closed |
| T-03-05 | Denial of Service | `/api/team`/`/api/rate` driven by entry ID | medium | mitigate | Numeric-only input mirroring server `min="1"`; in-flight button disable; TanStack Query per-entry cache; server pool/solve caches — verified by 03-02 tests | closed |
| T-03-06 | Tampering | `?tab=` accepting unrecognised value | low | mitigate | Unknown `?tab=` falls back to Squad default — verified by 03-02 tests | closed |
| T-03-07 | Tampering | `chips.json` `note` + names rendered to DOM | medium | mitigate | JSX text nodes; structured `pairMoves` (no HTML strings) — grep re-run clean | closed |
| T-03-08 | Information Disclosure | Squad/entry ID persisted to browser storage | low | mitigate | Storage grep gate — re-run clean 2026-09-03 (no localStorage/sessionStorage/indexedDB/cookie use); entry ID lives in URL only | closed |
| T-03-09 | Spoofing | API key embedded client-side (`/api/rate`, `/api/plan`) | high | mitigate | No key read/stored/sent in client — grep re-run clean; keying is a PAID-02 operator concern | closed |
| T-03-10 | Denial of Service | `/api/plan` multi-period solve CPU | medium | mitigate | Five fixed server-bounded horizon options; in-flight disable; server per-params solve cache — verified by 03-03 tests | closed |
| T-03-11 | Tampering | Suggested-move name strings selecting a card | low | mitigate | Exact-equality matching only with documented no-overlay degrade — verified by 03-03 tests | closed |
| T-03-12 | Tampering | Per-week move pairs from `pairMoves` | medium | mitigate | Structured objects + JSX position label; no HTML-string construction — grep re-run clean | closed |
| T-03-13 | Information Disclosure | Manager's own team name/rank from rating response | low | accept | Manager's own public data, requested by their own entry ID — see Accepted Risks Log | closed |
| T-03-14 | Tampering | Locks/excludes as free-text names via server substring matcher | medium | mitigate | Numeric `player_code` arrays by construction; 03-04 test asserts request body contains no display names | closed |
| T-03-15 | Denial of Service | Repeated queued solves on `/api/solve` | medium | mitigate | In-flight button disable; server solve cache; horizon/transfer inputs bounded to server limits — verified by 03-04 tests | closed |
| T-03-16 | Tampering | Superseded solve response overwriting squad | low | mitigate | Ordering-safety guard, `renderHook`-tested directly (03-04) | closed |
| T-03-17 | Spoofing | API key embedded client-side (`/api/solve`) | high | mitigate | No key read/stored/sent anywhere in client code — grep re-run clean | closed |
| T-03-18 | Repudiation | User believing a solve changed their real FPL team | medium | mitigate | Local preview only — no write path to any FPL account; explicit Reset; prohibition carried forward in plan frontmatter | closed |
| T-03-05-01 | Tampering | `Pitch.tsx` inline style values (03-05 fix) | low | accept | Basis/gap strings built from internal integer + design token only; CSSOM property setter, no markup interpolation — see Accepted Risks Log | closed |
| T-03-05-02 | Information Disclosure | Rendered player cards (03-05 fix) | low | accept | Layout-only change; same public fields, same DOM order — full-suite gate passed — see Accepted Risks Log | closed |
| T-03-SC | Tampering | npm/pip/cargo supply chain | high | mitigate | Zero packages installed across all five plans; 03-05 enforced `git diff --quiet` on package.json/lock as a task gate | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-03-01 | T-03-13 | Team name/rank is the manager's own public data from the official FPL API, requested via their own entry ID — same posture as vanilla site's footer disclaimer | plan 03-03 (plan-time disposition) | 2026-09-03 |
| R-03-02 | T-03-05-01 | Style values derived solely from internal slot count + design token; React CSSOM assignment leaves no CSS-injection sink. Accepted at ASVS L1 | plan 03-05 (plan-time disposition) | 2026-09-03 |
| R-03-03 | T-03-05-02 | Layout-only change renders the same already-public fields in the same DOM order; guarded by full-suite gate | plan 03-05 (plan-time disposition) | 2026-09-03 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-03 | 21 | 21 | 0 | gsd-secure-phase (L1 short-circuit: plan-time register, summary-verified mitigations, grep re-checks clean) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-03
