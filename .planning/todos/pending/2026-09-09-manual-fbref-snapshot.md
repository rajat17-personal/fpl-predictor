---
created: 2026-09-09T05:14:14.086Z
title: Manual FBref CSV snapshot committed like the kiwi data, joined via crosswalk
area: data
severity: minor
resolves_phase: 10
files:
  - data/external/kiwi/
  - data/id_crosswalk.py
  - features/engineer.py
---

## Problem

Automated FBref access is confirmed dead (Phase 9: Cloudflare "Just a moment..." challenge survives real-Chrome UC-mode; 3 attempts logged in IMPROVEMENTS.md § fbref_v2). The hosted proxy fbrapi.com (dkjorling/FbrefAPI) was probed 2026-09-09 and is currently half-down: TLS chain fails verification AND no HTTP response even ignoring TLS — not dependable for a pipeline. But FBref's per-season tables are downloadable manually in a normal browser (Share & Export → Get table as CSV; a human passes the Cloudflare challenge interactively).

## Solution

Follow the theFPLkiwi snapshot pattern from plan 09-02: user manually downloads the per-season defensive-stats tables (tackles, interceptions, pressures etc.), drops them under data/external/fbref/, commits them as a versioned snapshot with a README recording retrieval date/URL. Then a small plan joins them through data/id_crosswalk.py and rolls them via ROLL_STATS behind a default-off fbref_v2 flag, judged on the standard harness. Acquisition stays manual — respects Phase 9's no-new-scraping-infrastructure rule (D-04). Optionally re-probe fbrapi.com first; if it comes back up it automates the same acquisition.
