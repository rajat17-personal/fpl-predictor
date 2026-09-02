---
phase: "02"
slug: "data-layer-non-pitch-pages"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-02"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| pipeline → browser | `web/data/*.json` exports rendered as page text (names, teams, notes, fixtures, prices, standings) | Public FPL-derived strings and numbers |
| npm registry → build | Third-party packages (`react-markdown`, three `@fontsource` packages) enter the production bundle | Executable dependency code |
| localStorage → DOM class | User/extension-writable `fpl-theme` value drives a class on `<html>` | Two-state theme selector |
| authored content → DOM | Bundled `methodology.md` parsed and rendered as page structure via react-markdown | Developer-authored markdown |
| network → client | Failed or hostile `/data/*.json` responses reach `ErrorState`; HTTP status selects zero-state vs error | Error messages, status codes |
| developer/CI shell → repo scripts | `scripts/check-tokens.mjs` runs automatically on every `npm test` | Two repo CSS files, exit code |
| build-time class scanning → shipped CSS | Tailwind scanner decides which difficulty utility classes exist in the bundle | Class-name literals |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Tampering | XpTable/BandCell/statusFlag ported markup | high | mitigate | All vanilla template strings became JSX text children; `dangerouslySetInnerHTML` absent from `frontend/src` (verified by repo-wide grep) | closed |
| T-02-SC | Tampering | npm installs (react-markdown, @fontsource ×3) | high | mitigate | Package-legitimacy audit + human checkpoint; versions pinned exactly (`10.1.0`, `5.3.0`) in package.json/lockfile | closed |
| T-02-12 | Tampering | Markdown rendering on /methodology | high | mitigate | react-markdown renders React elements only; no `rehype-raw` plugin and no raw-HTML prop anywhere in `frontend/src` (grep gate); script-shaped markdown surfaces as visible text per rendering test | closed |
| T-02-02 | Information Disclosure | ErrorState on failed xp_table fetch | medium | mitigate | `ErrorState` accepts only a `resource` label (ErrorState.tsx:4,13); errors go to `console.error`, never the DOM | closed |
| T-02-04 | Repudiation | Undocumented parity deviations | medium | mitigate | PARITY-DEVIATIONS.md ledger exists in phase dir, recording each intentional difference with reason and originating plan | closed |
| T-02-06 | Information Disclosure | Third-party font CDN leaking visitor IP/referrer | medium | mitigate | No CDN font links in index.html; fonts self-hosted via pinned @fontsource packages | closed |
| T-02-07 | Tampering | GwBanner rendering meta.json fields | medium | mitigate | JSX auto-escaped text; malformed fetch routes to literal `deadline TBC` (GwBanner.tsx:41) | closed |
| T-02-08 | Tampering | FdrCell class selection from source fdr | medium | mitigate | Explicit literal 1–5 class map with `?? FDR_CLASSES[3]` clamp (FdrCell.tsx:36-45); no interpolated class names | closed |
| T-02-09 | Information Disclosure | Prices rendering unqualified heuristic probabilities | medium | mitigate | Mode note keyed on same `w.mode` field as label branch (Prices.tsx:59-92); per-mode tests assert exactly one note renders | closed |
| T-02-10 | Spoofing | Server failure presented as "no gameweeks scored yet" | medium | mitigate | `res.status === 404` branch isolates the genuine missing-file case (Scoreboard.tsx:18); all other non-ok statuses throw to ErrorState; 500 test asserts Retry appears | closed |
| T-02-07-01 | Tampering | check-tokens.mjs auto-run by npm test | medium | mitigate | Script imports only `node:fs` + `node:url`; zero npm dependencies, no network, no child_process, no writes | closed |
| T-02-07-03 | Tampering | web/assets/style.css lockstep edit | medium | mitigate | Edit confined to four hex literals in one media block; check-tokens.mjs asserts the four values match the React tokens on every test run | closed |
| T-02-08-01 | Tampering | FdrCell difficulty-to-class lookup vs Tailwind scanner | medium | mitigate | Literal class map preserved (no interpolation, so no silently-missing utility classes); out-of-range fallback to neutral difficulty 3 retained | closed |
| T-02-11 | Information Disclosure | ErrorState on failed scoreboard/league fetch | low | mitigate | Phase 1 ErrorState reused; error (embedding path + status) goes to console.error only | closed |
| T-02-13 | Information Disclosure | ErrorState on failed differentials fetch | low | mitigate | Same Phase 1 ErrorState reuse; message and body to console.error only | closed |
| T-02-07-02 | Denial of Service | Regex CSS parsing in check-tokens.mjs | low | mitigate | Inputs are two repo-controlled files of a few KB; captures use negated character classes, no nested quantifiers | closed |
| T-02-08-03 | Denial of Service | Two-line chips inflating table height | low | mitigate | Vanilla's tight gameweek-cell padding restored (commit 702ae4b); row count bounded at 20 clubs by data contract | closed |
| T-02-03 | Denial of Service | Oversized xp_table.json render cost | low | accept | `slice(0, 50)` bounds rendered rows by construction; same-origin static JSON already served publicly | closed |
| T-02-05 | Tampering | localStorage `fpl-theme` value | low | accept | Value only selects between two class states; head script and useTheme coerce anything outside light/dark to the OS default (index.html:17-19) | closed |
| T-02-07-04 | Information Disclosure | Rebalanced CSS shipped to browsers | low | accept | Colour token values carry no secrets, user data, or server topology | closed |
| T-02-08-02 | Information Disclosure | Chip text/aria-label from fixtures.json | low | accept | Club codes, home/away boolean, 1–5 integer — all already public; React escapes as text nodes | closed |
| T-02-07-05 | Tampering | Package installs (plan 02-07) | n/a | accept | Plan installs no packages; gate script is dependency-free by design | closed |
| T-02-08-04 | Tampering | Package installs (plan 02-08) | n/a | accept | Plan edits four existing source files and adds no dependency | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-03 | Render cost bounded by `slice(0, 50)`; data is same-origin public static JSON | plan 02-01 threat model | 2026-09-02 |
| AR-02-02 | T-02-05 | Theme value coerced to light/dark; tampering degrades to OS default, no injection path | plan 02-03 threat model | 2026-09-02 |
| AR-02-03 | T-02-07-04 | CSS colour tokens disclose nothing sensitive | plan 02-07 threat model | 2026-09-02 |
| AR-02-04 | T-02-08-02 | Rendered values already public on vanilla site; escaped as text nodes | plan 02-08 threat model | 2026-09-02 |
| AR-02-05 | T-02-07-05, T-02-08-04 | Plans install no packages; supply-chain protocol has nothing to audit | plan 02-07/02-08 threat models | 2026-09-02 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-02 | 23 | 23 | 0 | gsd-secure-phase (L1 grep-level, short-circuit — register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-02
