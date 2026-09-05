---
status: diagnosed
trigger: "dark mode looks okay although the colour looks a bit green"
created: 2026-09-01T15:30:00Z
updated: 2026-09-01T15:52:00Z
---

## Current Focus

bug_class: Bohrbug — deterministic, reproduces on every dark-mode paint, no timing/concurrency component. Route: deterministic reproduction -> direct token inspection (search space is one CSS file, so SBFL/bisect are unnecessary).

hypothesis: The green cast comes from the dark-mode neutral tokens themselves (`--color-bg/-surface/-surface-2/-line` in `frontend/src/index.css` `.dark`), which carry OKLCH chroma 0.012-0.020 at a hue within 5-13 deg of the brand accent hue.
test: Compute OKLCH for every dark + light token; diff React values against vanilla `web/assets/style.css`; then rule out Tailwind-processing and opacity-blend alternatives.
expecting: If tokens are the cause, dark neutrals show measurable chroma near the accent hue AND the React values match vanilla verbatim (inherited, not port drift).
next_action: [investigation complete — diagnosis returned, no fix applied per goal: find_root_cause_only]

reasoning_checkpoint:
  hypothesis: "The dark theme reads green because the four tokens that paint nearly the entire viewport (--color-bg/-surface/-surface-2/-line in .dark) are green-family with OKLCH chroma 0.0121-0.0202 at hue 159.5-167.2deg, i.e. within 4.9-12.7deg of the brand accent hue — while their light-theme counterparts carry 1.2-2.3x less chroma and sit 19.5-35.5deg off the accent."
  confirming_evidence:
    - "Direct measurement: all six dark neutrals are green-family in HSL (hue 120-154, sat 8-17%); zero neutral grays exist in the dark palette"
    - "OKLCH differential: same-role neutrals drift +25.6 to +49.3deg in hue between themes while the accent holds at +1.1deg — the neutrals move, the brand colour does not"
    - "Built dist CSS emits the hex values verbatim (no Tailwind oklch conversion) and every .bg-bg/.bg-surface/.bg-surface-2 utility is a flat background-color with no alpha or color-mix"
  falsification_test: "Set the four dark neutral tokens to true achromatic greys of identical OKLCH lightness (C=0) and reload /fixtures in dark mode. If the green cast persists, the tokens are not the cause and something downstream (blend, filter, browser profile) is."
  fix_rationale: "N/A — diagnose-only mode. Fix belongs in the token values themselves, not in any React-layer code, because the values are inherited verbatim from vanilla."
  blind_spots:
    - "Not visually confirmed on the user's own display; a wide-gamut/uncalibrated monitor could amplify the cast beyond the measured values"
    - "The simultaneous-contrast amplification claim (neutral FDR-3 chip + light scrollbar next to tinted surfaces) is a perceptual inference from measured colour values, not an A/B test with the user"
  candidate_causes:
    - "code: green-family chroma baked into the .dark neutral token values (CONFIRMED — primary)"
    - "config: Tailwind v4 @theme processing converting or shifting hex values in the build (ELIMINATED)"
    - "code: alpha/color-mix blending of accent over surfaces compounding hue (ELIMINATED)"
    - "environment: missing color-scheme leaving UA chrome light-themed next to tinted surfaces (CONFIRMED — amplifier, and a parity regression in its own right)"
  and_gate: "YES. Token chroma alone is necessary and sufficient for the tint to EXIST. But its becoming salient enough to report required a true-neutral reference in the same frame — on /fixtures (the screenshotted page) the FDR-3 chip #383835 is near-achromatic (C=0.0051) at 3.7x less chroma than the adjacent --color-surface-2 at similar lightness, and the dropped color-scheme leaves light UA scrollbars against the tinted surfaces. Remove the neutral references and the same tokens read as merely 'dark'."

## Symptoms

expected: With OS in dark mode (or Dark chosen in the theme toggle), the app renders a dark palette whose background/surface colors read as neutral dark (or intentionally branded), not unexpectedly green.
actual: "dark mode looks okay although the colour looks a bit green" — user perceives the dark background/surfaces as having a green tint. A screenshot of /fixtures in dark mode confirms a subtle green cast on the page and header backgrounds.
errors: None reported
reproduction: Test 1 in UAT — load the app in dark mode (dev server, backend on port 8000) and observe overall background/surface hue.
started: Discovered during UAT of Phase 02 (data layer + non-pitch pages)

## Eliminated

## Evidence

- timestamp: 2026-09-01T15:35:00Z
  checked: HSL of every dark-mode token in frontend/src/index.css `.dark` block
  found: EVERY neutral is in the green family, not neutral. bg #111815 = hue 154.3 / sat 17.1%; surface #18211c = 146.7 / 15.8%; surface-2 #1f2a24 = 147.3 / 15.1%; line #2c3831 = 145.0 / 12.0%; ink #e6ece6 = 120.0 / 13.6%; ink-2 #9caba0 = 136.0 / 8.2%. Accent #4cb878 = 144.4.
  implication: There is no neutral gray anywhere in the dark palette. Backgrounds, surfaces, borders AND text are all tinted toward the brand green.

- timestamp: 2026-09-01T15:36:00Z
  checked: OKLCH (perceptually uniform) chroma + hue distance from the accent, light vs dark
  found: LIGHT bg C=0.0054 @ 35.5deg from accent; surface C=0.0110 @ 29.9deg; surface-2 C=0.0143 @ 24.7deg; line C=0.0166 @ 19.5deg. DARK bg C=0.0121 @ 12.7deg; surface C=0.0161 @ 6.0deg; surface-2 C=0.0189 @ 6.5deg; line C=0.0202 @ 4.9deg.
  implication: Two compounding asymmetries. (1) Dark neutrals carry 1.2-2.2x the chroma of their light counterparts (bg 0.0121 vs 0.0054 = 2.2x). (2) Dark neutrals sit essentially ON the accent hue (4.9-12.7deg) while light neutrals sit 19.5-35.5deg off it. Same hue + more chroma = the frame reads as a green wash instead of a neutral dark surface with a green accent on it.

- timestamp: 2026-09-01T15:38:00Z
  checked: Diff of React `.dark` token values against vanilla web/assets/style.css `@media (prefers-color-scheme: dark)` block (lines 27-49)
  found: Byte-identical. #111815, #18211c, #1f2a24, #e6ece6, #9caba0, #2c3831, #4cb878, #6bcb90, #1a2e22 all match verbatim.
  implication: This is NOT hue drift introduced by the React rebuild. The tint is inherited from the vanilla design system, faithfully ported. The port is correct; the source palette is what the user is reacting to.

- timestamp: 2026-09-01T15:42:00Z
  checked: Built output frontend/dist/assets/index-vEJ1roPt.css — token emission + every surface utility
  found: `.dark{--color-bg:#111815;--color-surface:#18211c;...}` emitted as literal hex, no oklch/color-mix conversion. `.bg-bg`, `.bg-surface`, `.bg-surface-2` are flat `background-color:var(--color-X)` with no alpha channel. Grep for opacity utilities on surface tokens returned zero hits.
  implication: ELIMINATES the build/config category and the alpha-blend category. What ships is exactly what is authored — the tint is in the source values, nowhere else.

- timestamp: 2026-09-01T15:44:00Z
  checked: Differential OKLCH of the SAME token role across light vs dark
  found: bg 117.9->167.2 (+49.3deg), surface 123.5->160.6 (+37.1), surface-2 128.6->161.0 (+32.4), line 133.8->159.5 (+25.6). Chroma ratios dark/light: 2.26x, 1.46x, 1.32x, 1.21x. Accent moves only 153.4->154.5 (+1.1deg).
  implication: THE decisive finding. The brand accent hue is stable across themes; every neutral swings 26-49deg. In light the neutrals sit BELOW the accent hue (warm yellow-green, reads as off-white paper); in dark they sit ABOVE it (cool green/teal) AND carry more chroma. That asymmetry is precisely why the user sees green in dark mode but not in light — it is hue drift on the neutrals, not a uniformly-applied brand tint.

- timestamp: 2026-09-01T15:46:00Z
  checked: `color-scheme` declaration and body background, React vs vanilla
  found: vanilla web/assets/style.css declares `color-scheme: light` (line 4) and `color-scheme: dark` (line 29), and paints `body { background: var(--bg) }` (line 55). The React port declares `color-scheme` NOWHERE (absent from index.html, index.css and all components — the only grep hits are `prefers-color-scheme` media queries in theme.ts). `<body>` is unpainted; `bg-bg` sits on PageShell.tsx:40's inner div instead.
  implication: A genuine vanilla-parity regression, independent of the hue question. Consequences: light UA scrollbars and light form controls in dark mode, plus a white canvas in the overscroll region. A light-neutral scrollbar hard against the tinted surfaces is a true-neutral reference in the same viewport, which materially amplifies how legible the cast is.

- timestamp: 2026-09-01T15:48:00Z
  checked: Why the tint was noticed on /fixtures specifically (the screenshotted page)
  found: The dark FDR-3 mid chip `--color-fdr3-bg: #383835` is near-achromatic (OKLCH C=0.0051, L=34.0) and sits directly against `--color-surface-2` #1f2a24 (C=0.0189, L=27.2) in the fixtures table header/cells — a 3.7x chroma gap at near-equal lightness.
  implication: /fixtures puts a true-neutral grey immediately adjacent to the tinted surface. This is the textbook simultaneous-contrast condition that turns a subtle cast into an obvious one, explaining why this page in particular triggered the report.

- timestamp: 2026-09-01T15:50:00Z
  checked: Whether the tint is documented anywhere as deliberate brand styling
  found: vanilla style.css header comment says only "single source of visual truth. Light palette on :root; dark redefines tokens only". 01-UI-SPEC.md Color table (lines 149-157) lists the hexes by role with no hue/chroma intent. 02-PARITY-DEVIATIONS.md does not mention the palette hue.
  implication: A green tint was clearly intended in the abstract (every neutral in BOTH themes is green-family — that cannot be accidental), but the degree and direction in dark mode are undocumented and internally inconsistent. No spec sanctions the dark neutrals sitting on the accent hue at 2.3x the light theme's chroma.

## Resolution

root_cause: |
  Two confirmed contributing causes (AND-gate fired).

  PRIMARY (code) — The four dark-mode tokens that paint essentially the whole viewport are
  green-family, not neutral, and are measurably MORE tinted than their light-mode counterparts
  while sitting almost exactly ON the brand accent hue. In frontend/src/index.css `.dark`
  (lines 87-93): --color-bg #111815 (OKLCH L=20.1 C=0.0121 H=167.2), --color-surface #18211c
  (L=23.7 C=0.0161 H=160.6), --color-surface-2 #1f2a24 (L=27.2 C=0.0189 H=161.0), --color-line
  #2c3831 (L=32.7 C=0.0202 H=159.5). Accent --color-accent #4cb878 is H=154.5, so the surfaces
  are only 4.9-12.7deg off the brand hue. The light-mode equivalents carry 1.2-2.3x LESS chroma
  and sit 19.5-35.5deg off the accent, which is why light mode reads as neutral paper and dark
  does not. Across the same token roles the neutrals drift +25.6 to +49.3deg in hue between
  themes while the accent holds at +1.1deg — the tint is therefore inconsistent hue drift on the
  neutrals, not a uniformly applied brand tint.

  SECONDARY (environment/parity) — `color-scheme` was dropped in the React port (vanilla declares
  it at style.css:4 and :29; React declares it nowhere) and `<body>` is left unpainted (vanilla
  paints it at style.css:55; React puts `bg-bg` on PageShell.tsx:40's inner div). This leaves
  light UA scrollbars/form controls and a white canvas against the tinted surfaces, supplying a
  true-neutral reference that makes the cast substantially more legible. On /fixtures the
  near-achromatic FDR-3 chip #383835 (C=0.0051) does the same at 3.7x less chroma than the
  adjacent surface-2.

  VERDICT — Partially intentional, but the user's complaint is a real defect. Brand-tinted
  neutrals were deliberate (every neutral in both themes is green-family). The dark theme's
  higher chroma, its collision with the accent hue, and its opposite hue direction versus light
  are undocumented and unintended. NOT a React port defect: the values are byte-identical to
  vanilla web/assets/style.css lines 30-35, Tailwind emits them verbatim, and no alpha/color-mix
  blend compounds them.

fix: "[not applied — goal: find_root_cause_only]"
verification: "[not applicable — diagnosis only]"
files_changed: []
