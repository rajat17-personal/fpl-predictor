#!/usr/bin/env bash
# Production build purity gate: proves no pipeline export (web/data/*.json) was
# copied or bundled into the frontend build output. Filename comparison rather
# than a content grep on purpose — it cannot be defeated by minification and
# does not depend on any particular field name surviving the bundler.
#
# Usage: bash scripts/verify_frontend_build.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d frontend/public/data ]; then
  echo "FAILED: frontend/public/data exists — pipeline data must never be copied into the build"
  exit 1
fi

echo "[verify_frontend_build] running npm --prefix frontend run build"
npm --prefix frontend run build

node -e "
const fs = require('fs');
const path = require('path');

const dataDir = path.join(process.cwd(), 'web', 'data');
const distDir = path.join(process.cwd(), 'frontend', 'dist');

const jsonNames = new Set(
  fs.readdirSync(dataDir).filter((f) => f.endsWith('.json'))
);

function walk(dir) {
  let out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out = out.concat(walk(full));
    else out.push(full);
  }
  return out;
}

const distFiles = walk(distDir);
const offenders = distFiles.filter((f) => jsonNames.has(path.basename(f)));

if (offenders.length > 0) {
  console.error('FAILED: pipeline JSON found in build output:');
  for (const f of offenders) console.error('  ' + path.relative(process.cwd(), f));
  process.exit(1);
}

console.log('BUILD PURITY OK');
"
