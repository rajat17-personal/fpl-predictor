---
phase: 02-data-layer-non-pitch-pages
reviewed: 2026-09-01T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - frontend/package.json
  - frontend/scripts/check-tokens.mjs
  - frontend/src/components/FdrCell.test.tsx
  - frontend/src/components/FdrCell.tsx
  - frontend/src/index.css
  - frontend/src/routes/Fixtures.test.tsx
  - frontend/src/routes/Fixtures.tsx
  - web/assets/style.css
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-09-01T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the token-budget gate script (`check-tokens.mjs`), the dark-theme token
lockstep between `frontend/src/index.css` and `web/assets/style.css`, and the
`FdrCell`/`Fixtures` two-line fixture-chip port (UAT gap G-02-2). The OKLCH gate
script is sound: its chroma/hue/lightness math is correct, the colon-anchored
token regex correctly avoids `--color-surface` matching `--color-surface-2`, and
manual cross-checking confirms every dark-mode token in `index.css` (not just the
four gated neutral roles) is byte-for-byte identical to `web/assets/style.css`.

The chip stacking/accessibility fix in `FdrCell.tsx` is functionally correct and
well tested. However, two of the three literal geometry values it "ports from
vanilla" do not actually match `web/assets/style.css`'s `.fdr` rule: the chip uses
`min-w-[56px]` where vanilla specifies `min-width: 58px`, and `py-1` (4px) where
vanilla specifies `padding: 6px 8px` (6px vertical). Both wrong values are now
locked into the new "geometry contract" regression tests (`FdrCell.test.tsx`),
which means the suite will pass while silently shipping a pixel-narrower/-shorter
chip than the design source of truth — defeating the stated purpose of this
gap-closure (byte-exact parity with vanilla). No security issues or crash-level
bugs were found in the reviewed files.

## Warnings

### WR-01: FdrCell chip geometry diverges from vanilla's `.fdr` rule (min-width and vertical padding)

**File:** `frontend/src/components/FdrCell.tsx:57,70`
**Issue:** `web/assets/style.css:152-153` defines the ported rule as:
```css
.fdr { ... padding: 6px 8px; border-radius: 6px; min-width: 58px; }
```
`FdrCell.tsx` renders both the blank-gameweek chip (line 57) and the populated
chip (line 70) with `min-w-[56px]` and `px-2 py-1`. In this project's Tailwind
v4 config, the numeric spacing scale is unmodified (`--spacing: 0.25rem` default;
only named `--spacing-xs`..`--spacing-3xl` tokens are added), so `py-1` = 4px, not
the 6px vanilla specifies, and `min-w-[56px]` is 2px narrower than vanilla's
`min-width: 58px`. The module docstring (lines 3-17) explicitly frames this file
as a faithful geometry port validated against `web/assets/style.css`, and the new
`FdrCell.test.tsx` "geometry contract" tests (lines 90-98, 120-127, 130-144) now
assert the wrong `min-w-[56px]` value, which will keep this regression passing
indefinitely rather than catching it.
**Fix:**
```tsx
// FdrCell.tsx — both chip variants
className={`inline-flex min-w-[58px] flex-col items-center justify-center rounded px-2 py-1.5 font-mono text-label ${fdrClasses(3)}`}
```
and update the corresponding assertions in `FdrCell.test.tsx` (`min-w-[56px]` →
`min-w-[58px]`) once the value is corrected.

### WR-02: "next six gameweeks" copy is hard-coded while column count is explicitly data-derived

**File:** `frontend/src/routes/Fixtures.tsx:50-56`
**Issue:** The intro paragraph literally reads "The next six gameweeks for every
club..." while the column count (`gwNumbers`) is deliberately computed from
`data[0].gws.length` per the R20 requirement documented in the file's own
docstring ("the gameweek column count is derived from the data ... never
hard-coded to six"). The test fixture used in `Fixtures.test.tsx` intentionally
carries 4 gameweeks to prove the table doesn't hard-code 6 columns — but with
that same fixture the descriptive text above the table would read "next six"
while only 4 columns render, an inconsistency the tests never catch because
none of them assert on the paragraph copy. If the production export horizon
ever changes (a plausible future change per `optimize/multi_period.py`'s
horizon parameter), this copy silently becomes wrong.
**Fix:**
```tsx
const gwNumbers = data[0].gws.map((g) => g.gw);
// ...
<p className="mt-2 font-body text-body text-ink-2">
  The next {gwNumbers.length} gameweeks for every club, sorted by ease of run. ...
</p>
```

## Info

### IN-01: Unused default export on `FdrCell`

**File:** `frontend/src/components/FdrCell.tsx:80`
**Issue:** `FdrCell` is exported both as a named export (used by `Fixtures.tsx`
via `import { FdrCell } from "../components/FdrCell"`) and as a default export
(line 80), but nothing in the reviewed scope imports the default. Two export
paths for the same component invite accidental inconsistent imports elsewhere.
**Fix:** Drop `export default FdrCell;` unless another consumer specifically
needs the default import form.

### IN-02: Out-of-range FDR values leak into the accessible name verbatim

**File:** `frontend/src/components/FdrCell.tsx:69`
**Issue:** `fdrClasses()` correctly clamps an out-of-range `fdr` (e.g. `9`) to
the neutral difficulty-3 *styling*, but the `aria-label` still interpolates the
raw, unclamped value (`difficulty 9`) — confirmed by `FdrCell.test.tsx:58-65`,
which explicitly asserts the label says "difficulty 9". A screen-reader user
would hear a difficulty value (9) that has no meaning in FPL's 1-5 scale, while
sighted users see the neutral color — the two channels disagree on invalid
input instead of failing consistently.
**Fix:**
```tsx
const clampedFdr = FDR_CLASSES[f.fdr] ? f.fdr : 3;
aria-label={`${f.home ? "Home" : "Away"} vs ${f.opp}, difficulty ${clampedFdr}`}
```

### IN-03: Token-budget gate only checks 4 of the shared palette's tokens for lockstep

**File:** `frontend/scripts/check-tokens.mjs:212-217`
**Issue:** The "vanilla lockstep" section only compares `--bg/--surface/--surface-2/--line`
(via `VANILLA_TO_REACT`) between `web/assets/style.css` and `frontend/src/index.css`.
Manual comparison confirms `accent`, `accent-ink`, `accent-bg`, `bad`, `warn`,
`warn-bg`, `band`, `band-pt`, and all five `fdr*-bg`/`fdr*-ink` pairs also
currently match, but none of those are gated — a future edit to any of them in
only one file would ship a silent light/dark or React/vanilla palette drift
that this CI gate cannot catch, even though the script's own header comment
frames its job as keeping "the vanilla site ... in lockstep with the React
palette" (line 8), not just the four neutral roles.
**Fix:** Extend `VANILLA_TO_REACT` (and the light-side equivalent) to cover the
full shared token set, or explicitly scope the header comment to "neutral
tokens only" so the coverage gap is documented rather than implied-total.

### IN-04: `hexToOklch` mis-parses 4- and 5-character hex strings

**File:** `frontend/scripts/check-tokens.mjs:30-41`
**Issue:** `readToken`'s regex accepts hex captures of length 3-8
(`#[0-9a-fA-F]{3,8}`), but `hexToOklch` only special-cases length 3 (`#rgb`)
and otherwise assumes length ≥ 6 (`slice(0,2)/slice(2,4)/slice(4,6)`). A
4-length (`#rgba` shorthand) or 5-length hex would silently produce `NaN`
channels instead of throwing, since none of the current CSS tokens use those
forms this is currently inert, but it's a latent correctness gap in a script
whose entire job is precise numeric colour verification.
**Fix:**
```js
if (clean.length === 3 || clean.length === 4) {
  r = parseInt(clean[0] + clean[0], 16);
  g = parseInt(clean[1] + clean[1], 16);
  b = parseInt(clean[2] + clean[2], 16);
} else if (clean.length === 6 || clean.length === 8) {
  r = parseInt(clean.slice(0, 2), 16);
  g = parseInt(clean.slice(2, 4), 16);
  b = parseInt(clean.slice(4, 6), 16);
} else {
  throw new Error(`Unsupported hex length: #${hex}`);
}
```

---

_Reviewed: 2026-09-01T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
