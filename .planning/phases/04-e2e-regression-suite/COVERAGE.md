# Phase 4 — API Coverage Declaration

No external API integration: this phase adds a Playwright regression suite over the
existing stack and *removes* the last live dependency on `fantasy.premierleague.com`
by adding an on-disk fixture seam — it integrates no new external API, SDK, or service.

The only third-party surface touched is the FPL API this repo already consumes
(`data/ingest.py`, `api/main.py`), and this phase's change to it is subtractive:
in fixture mode those calls read frozen JSON from `e2e/fixtures/v1/` instead of the
network.
