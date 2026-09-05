# Phase 1 — API Capability Coverage Declaration

**Decided:** 2026-08-31 (gsd-planner, standard planning)
**Detector:** `api-coverage` returned `detected: true` (signal: the word "API" in success
criteria 1–3, which describe testing `/solve`, `/rate`, `/team`, `/health`, `/meta` against a
*mocked* FPL API).

## Declaration

No external API integration: this phase adds pytest coverage for the project's **own** FastAPI
service (`api/main.py`, already built) while *mocking away* the pre-existing third-party FPL API,
and scaffolds a React app that consumes only that same first-party `/api` surface plus the
project's own `web/data/*.json` exports through a Vite dev proxy.

## Why the detector fired but no matrix is required

| Surface named in this phase | External? | What this phase does with it |
|---|---|---|
| `fantasy.premierleague.com/api` (FPL bootstrap/fixtures/entry) | Yes, but **pre-existing** — integrated in earlier milestones by `predict/live.py` and `api/main.py:_fetch_team`/`_free_transfers` | **Removes** live contact: `predict.live._load_live` is monkeypatched and the two direct `requests.get` call sites are intercepted by the `responses` library, which raises on any unregistered outbound URL. No new capability is integrated; existing capability is *isolated*. |
| `api/main.py` `/api/{health,meta,team,solve,rate}` | No — first-party, in-repo | Contract-tested in-process via `fastapi.testclient.TestClient`. |
| `web/data/*.json` | No — first-party pipeline output served by this repo's own `StaticFiles` mount | Fetched at runtime by the React app through the Vite dev proxy. |

No new vendor, SDK, OAuth flow, webhook, or billing surface is introduced. The capability matrix
(`| capability | decision | reason |`, INTEGRATE-by-default) exists to stop a phase from wiring
1 of 12 available endpoints and calling it done; there is no such menu here, because the phase
adds zero new external endpoints.

## Boundaries this declaration does NOT cover

- Widening FPL API usage (new endpoints, leagues, live-event polling) — out of scope for v1
  (`REQUIREMENTS.md` → Out of Scope: "Real-time in-match live tracking").
- Payment / merchant-of-record integration — v2 (`PAID-03`), blocked on a pending user decision.
- Restricting `CORSMiddleware(allow_origins=["*"])` — Phase 6 (`SEC-01`). Explicitly untouched
  here (`01-RESEARCH.md` Pitfall 5).
