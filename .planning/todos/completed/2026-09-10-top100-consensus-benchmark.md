---
created: 2026-09-10T03:30:00.000Z
title: Top-100-manager consensus column in the scoreboard (diagnostic)
area: predict
severity: minor
resolves_phase: 10
files:
  - predict/scoreboard.py
---

## Problem

Elite-manager effective ownership is a crowd-wisdom signal that bakes in pre-deadline news (like ep_next). We have no benchmark measuring how our xP ranking compares to it.

## Solution

Scoreboard-only diagnostic (never a model feature): fetch top-100 overall managers' picks per GW from the FPL API standings/entry endpoints, compute a consensus ownership ranking, and add a Spearman column vs our xP and vs actual points in predict/scoreboard.py's post-GW report. Near-zero cost; product surface unchanged (scoreboard is an internal report).
