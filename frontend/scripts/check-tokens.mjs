// Dependency-free OKLCH token-budget gate (UIX-02, UAT gap G-02-1).
//
// Zero npm dependencies by design — node:fs and node:url only, no network access, no
// child_process. Verifies that the dark-mode neutral tokens (--color-bg, --color-surface,
// --color-surface-2, --color-line) in frontend/src/index.css stay within a chroma budget
// derived from their light-theme counterparts, lock hue to the dark accent, and hold their
// pre-fix lightness — plus that dark UA chrome (color-scheme) and body paint are restored,
// and that the vanilla site (web/assets/style.css) stays in lockstep with the React palette.
//
// Why a plain Node script rather than a Vitest test: Vitest stubs CSS imports to an empty
// string by default (raw-query import would pass vacuously); enabling the css option pushes
// the tailwindcss import through a Vitest config with no Tailwind plugin. Reading the file
// with node:fs from inside src is closed off too — tsconfig.app.json declares types as
// vite/client only, no node types. A script under frontend/scripts sits in neither tsconfig
// project's include (tsconfig.app.json includes src, tsconfig.node.json includes only
// vite.config.ts), so the build-mode typecheck never sees it.

import { existsSync, readFileSync } from "node:fs";

// Resolve inputs relative to this script, not the process cwd.
const reactCssUrl = new URL("../src/index.css", import.meta.url);
const vanillaCssUrl = new URL("../../web/assets/style.css", import.meta.url);

// --- OKLCH conversion (Björn Ottosson's standard sRGB -> Oklab pipeline) ---

function srgbChannelToLinear(c) {
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function hexToOklch(hex) {
  const clean = hex.replace("#", "");
  let r, g, b;
  if (clean.length === 3) {
    r = parseInt(clean[0] + clean[0], 16);
    g = parseInt(clean[1] + clean[1], 16);
    b = parseInt(clean[2] + clean[2], 16);
  } else {
    r = parseInt(clean.slice(0, 2), 16);
    g = parseInt(clean.slice(2, 4), 16);
    b = parseInt(clean.slice(4, 6), 16);
  }

  const rl = srgbChannelToLinear(r / 255);
  const gl = srgbChannelToLinear(g / 255);
  const bl = srgbChannelToLinear(b / 255);

  // linear sRGB -> LMS
  const l = 0.4122214708 * rl + 0.5363325363 * gl + 0.0514459929 * bl;
  const m = 0.2119034982 * rl + 0.6806995451 * gl + 0.1073969566 * bl;
  const s = 0.0883024619 * rl + 0.2817188376 * gl + 0.6299787005 * bl;

  const lRoot = Math.cbrt(l);
  const mRoot = Math.cbrt(m);
  const sRoot = Math.cbrt(s);

  // LMS' -> Oklab
  const L = 0.2104542553 * lRoot + 0.7936177850 * mRoot - 0.0040720468 * sRoot;
  const a = 1.9779984951 * lRoot - 2.4285922050 * mRoot + 0.4505937099 * sRoot;
  const bComp = 0.0259040371 * lRoot + 0.7827717662 * mRoot - 0.8086757660 * sRoot;

  const C = Math.hypot(a, bComp);
  let H = (Math.atan2(bComp, a) * 180) / Math.PI;
  if (H < 0) H += 360;

  return { L: L * 100, C, H };
}

function hueDistance(h1, h2) {
  return Math.abs((((h1 - h2 + 180) % 360) + 360) % 360 - 180);
}

// --- CSS parsing ---

function extractBlock(css, blockRe, label) {
  const m = css.match(blockRe);
  if (!m) {
    throw new Error(`Could not find ${label} block`);
  }
  return m[1];
}

function readToken(blockText, name) {
  // Colon-anchored so --color-surface can never match --color-surface-2 (the "-2" that
  // follows "surface" in the longer name breaks the \s*: match at that position).
  const re = new RegExp(`${name}\\s*:\\s*(#[0-9a-fA-F]{3,8})`, "i");
  const m = blockText.match(re);
  if (!m) {
    throw new Error(`Token ${name} not found`);
  }
  return m[1];
}

const reactCss = readFileSync(reactCssUrl, "utf8");
const themeBody = extractBlock(reactCss, /@theme\s*{([^}]*)}/, "@theme");
const darkBody = extractBlock(reactCss, /\.dark\s*{([^}]*)}/, ".dark");

const ROLES = ["--color-bg", "--color-surface", "--color-surface-2", "--color-line"];
const ROLE_LABELS = {
  "--color-bg": "bg",
  "--color-surface": "surface",
  "--color-surface-2": "surface-2",
  "--color-line": "line",
};

const lightHex = {};
const darkHex = {};
for (const role of ROLES) {
  lightHex[role] = readToken(themeBody, role);
  darkHex[role] = readToken(darkBody, role);
}
const darkAccentHex = readToken(darkBody, "--color-accent");

const lightOklch = {};
const darkOklch = {};
for (const role of ROLES) {
  lightOklch[role] = hexToOklch(lightHex[role]);
  darkOklch[role] = hexToOklch(darkHex[role]);
}
const darkAccentOklch = hexToOklch(darkAccentHex);

// Chroma allowance: 8-bit sRGB quantization has a chroma floor near black. At L~20 and
// hue~154 no representable colour reaches some light-theme budgets exactly, so an
// exact-budget rule would fail for a reason unrelated to the defect this gate targets.
const CHROMA_ALLOWANCE = 0.001;
const HUE_LOCK_DEG = 8.0;
const LIGHTNESS_TOLERANCE = 0.6;

// Pinned pre-fix lightness values — the measured lightness of the palette shipped by plan
// 02-03, recorded in .planning/debug/dark-theme-green-tint.md. Pinning these stops a future
// "just make it darker" edit from satisfying the chroma budget by moving the contrast ladder
// instead of removing the excess chroma.
const PINNED_LIGHTNESS = {
  "--color-bg": 20.1,
  "--color-surface": 23.7,
  "--color-surface-2": 27.2,
  "--color-line": 32.7,
};

const results = [];
function record(name, passed, detail) {
  results.push({ name, passed });
  console.log(`[${passed ? "PASS" : "FAIL"}] ${name} — ${detail}`);
}

for (const role of ROLES) {
  const label = ROLE_LABELS[role];
  const light = lightOklch[role];
  const dark = darkOklch[role];

  // 1. Chroma budget
  const chromaBudget = light.C + CHROMA_ALLOWANCE;
  record(
    `${label} chroma budget`,
    dark.C <= chromaBudget,
    `dark C=${dark.C.toFixed(4)} vs budget ${chromaBudget.toFixed(4)} (light C=${light.C.toFixed(4)}) L=${dark.L.toFixed(1)} H=${dark.H.toFixed(1)}`,
  );

  // 2. Hue lock
  const dist = hueDistance(dark.H, darkAccentOklch.H);
  record(
    `${label} hue lock`,
    dist <= HUE_LOCK_DEG,
    `dark H=${dark.H.toFixed(1)} vs accent H=${darkAccentOklch.H.toFixed(1)}, distance=${dist.toFixed(1)}deg (budget ${HUE_LOCK_DEG}deg)`,
  );

  // 3. Lightness lock
  const pinned = PINNED_LIGHTNESS[role];
  const lDelta = Math.abs(dark.L - pinned);
  record(
    `${label} lightness lock`,
    lDelta <= LIGHTNESS_TOLERANCE,
    `dark L=${dark.L.toFixed(1)} vs pinned ${pinned} (delta ${lDelta.toFixed(2)}, budget ${LIGHTNESS_TOLERANCE})`,
  );
}

// --- Structure assertions on frontend/src/index.css ---

const rootBlocks = [...reactCss.matchAll(/:root\s*{([^}]*)}/g)].map((m) => m[1]);
const rootHasColorSchemeLight = rootBlocks.some((b) => /color-scheme\s*:\s*light/i.test(b));
record(
  ":root color-scheme light",
  rootHasColorSchemeLight,
  rootHasColorSchemeLight ? ":root declares color-scheme: light" : ":root does not declare color-scheme: light",
);

const darkHasColorSchemeDark = /color-scheme\s*:\s*dark/i.test(darkBody);
record(
  ".dark color-scheme dark",
  darkHasColorSchemeDark,
  darkHasColorSchemeDark ? ".dark declares color-scheme: dark" : ".dark does not declare color-scheme: dark",
);

const bodyMatch = reactCss.match(/\bbody\s*{([^}]*)}/);
const bodyPass = !!bodyMatch && /background(-color)?\s*:\s*var\(\s*--color-bg\s*\)/i.test(bodyMatch[1]);
record(
  "body background paint",
  bodyPass,
  bodyMatch ? `body rule found — background-from-var check ${bodyPass ? "passed" : "failed"}` : "no body rule found in index.css",
);

// --- Lockstep invariant against web/assets/style.css ---

if (!existsSync(vanillaCssUrl)) {
  console.log("[SKIP] vanilla lockstep — web/assets/style.css not found (frontend-only context)");
} else {
  const vanillaCss = readFileSync(vanillaCssUrl, "utf8");
  const mediaIdx = vanillaCss.search(/@media\s*\(prefers-color-scheme:\s*dark\)/i);
  if (mediaIdx === -1) {
    record("vanilla lockstep", false, "prefers-color-scheme dark media query not found in web/assets/style.css");
  } else {
    const afterMedia = vanillaCss.slice(mediaIdx);
    const VANILLA_TO_REACT = {
      "--bg": "--color-bg",
      "--surface": "--color-surface",
      "--surface-2": "--color-surface-2",
      "--line": "--color-line",
    };
    for (const [vanillaName, reactRole] of Object.entries(VANILLA_TO_REACT)) {
      const label = ROLE_LABELS[reactRole];
      let vanillaValue;
      try {
        vanillaValue = readToken(afterMedia, vanillaName);
      } catch {
        record(`vanilla lockstep ${label}`, false, `token ${vanillaName} not found after dark media query`);
        continue;
      }
      const reactValue = darkHex[reactRole];
      record(
        `vanilla lockstep ${label}`,
        vanillaValue.toLowerCase() === reactValue.toLowerCase(),
        `vanilla ${vanillaName}=${vanillaValue} vs react ${reactRole}=${reactValue}`,
      );
    }
  }
}

// --- Verdict ---

const failed = results.filter((r) => !r.passed);
console.log("");
if (failed.length > 0) {
  console.log(`${failed.length} assertion(s) failed: ${failed.map((f) => f.name).join(", ")}`);
  process.exit(1);
} else {
  console.log("All token-budget assertions passed.");
  process.exit(0);
}
