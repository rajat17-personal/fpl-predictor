---
created: 2026-09-10T03:30:00.000Z
title: Availability flags into the P(play) hurdle stage — own snapshots first
area: models
severity: major
resolves_phase: 10
files:
  - data/snapshot.py
  - models/train.py
  - features/engineer.py
---

## Problem

The measured ranking gap to FPL's ep_next (Spearman 0.579 vs 0.383) is a minutes/availability problem, triple-confirmed by research (fplreview's edge is its xMins layer; the OpenFPL paper arXiv:2508.09992 closed most of that gap using only the FPL API's categorical chance_of_playing flags). Our P(play) classifier sees no availability signals.

## Solution

Own-data first: data/snapshot.py already captures `status`, `chance_of_playing_next_round`, `ep_this/ep_next` daily since 2026-08-31 — add `news`/`news_added`/`chance_of_playing_this_round` to _ELEMENT_COLS (small change) and build pre-deadline availability features (status one-hot, chance%, days-since-news) for the P(play) stage from the latest snapshot before each deadline, behind a default-off flag. Historical backfill (optional, user opt-in): vendor FPL-Core-Insights' per-GW playerstats.csv for 2025-26 GW1-38 as a one-time committed snapshot (theFPLkiwi pattern — no runtime dependency; leakage caveat: their GW folders freeze at GW end, so use GW N-1's snapshot for GW N). Evaluate: walk-forward on covered seasons + live Spearman-vs-ep_next tracking; expected gain concentrates in zeros/blanks prediction per OpenFPL. Mine OpenFPL's availability-feature encoding first.
