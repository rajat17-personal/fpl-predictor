---
created: 2026-09-10T03:30:00.000Z
title: Guardian/GDELT news sentiment for P(play) — only if flags/injury do not close the gap
area: data
severity: minor
resolves_phase: 10
files:
  - data/
  - models/train.py
---

## Problem

News sentiment is the last availability increment after structured flags and injury records. The IJCSS 2025 paper's regression gains were cherry-pick flavored, but its classification (will-play) gains were directionally consistent — and its method-2 sources are fully backfillable and timestamp-leakage-safe: The Guardian open-platform API (free key, historical archive) and GDELT DOC 2.0 (keyless, ~2017+, built-in tone scores).

## Solution

CONDITIONAL — build only if the availability-flags and Transfermarkt-injury experiments leave a measurable Spearman gap to ep_next. First pass: GDELT doc-count + mean tone for player-name mentions in the 7 days before each deadline (no sentiment model needed), Guardian as second source. Name-entity matching via the crosswalk with majority-vote over top articles. Leakage test: article timestamps < kickoff. Budget weeks of rate-limited backfill as a background killable fetcher. Related repo to mine: danielfrees/mlpremier (Frees et al. 2024, arXiv 2405.02412).
