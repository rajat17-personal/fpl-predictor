---
status: testing
phase: 06-security-reliability-observability-hardening
source: [06-VERIFICATION.md]
started: 2026-09-06T10:45:00Z
updated: 2026-09-06T10:45:00Z
---

## Current Test

number: 1
name: Live-browser CORS check on the team page solve flow
expected: |
  The solve request succeeds under the FPL_CORS_ORIGINS-restricted CORS policy
  (default dev origins allow localhost:5173/8000 on both localhost and 127.0.0.1).
awaiting: user response

## Tests

### 1. Live-browser CORS check on the team page solve flow

expected: Open the React dev server (http://localhost:5173) with the API running and exercise the team page's solve button end to end. The solve request succeeds under the FPL_CORS_ORIGINS-restricted CORS policy (default dev origins allow localhost:5173/8000 on both localhost and 127.0.0.1).
result: [pending]

### 2. Cron install + alert-webhook confirmation

expected: Install the daily cron line (30 2 * * * .../scripts/daily.sh) and the weekly cron line (0 8 * * fri .../scripts/weekly.sh) on the pipeline host; `crontab -l` lists both jobs; a deliberately broken scripts/daily.sh run produces a same-day FPL_ALERT_WEBHOOK notification on a channel actually watched.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
