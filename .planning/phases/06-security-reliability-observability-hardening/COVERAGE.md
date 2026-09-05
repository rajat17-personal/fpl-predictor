# API Coverage Decision — Phase 6

**Detector result at plan time:** `detected: false` against the ROADMAP phase section alone;
`detected: true` once the authored PLAN bodies are included in the scope (the signals are the phrase
"Wire the same validators into `api/main.py`" and a threat-model row reading "FPL API → pipeline").

**Verdict after re-reading the phase scope:** the signals are vocabulary, not integration.

No external API integration: this phase hardens *already-consumed* surfaces — it adds pydantic
validation, context-managed reads and structured logging around the FPL endpoints Phases 1 through 5
already call, and restricts CORS, bounds the solve cache and adds a readiness endpoint on this
project's own FastAPI service. No new third-party API, SDK, or service client is introduced, and the
plans explicitly forbid adding any new runtime dependency (see the `must_haves.prohibitions` block in
every plan, gated by `git diff --quiet -- requirements.txt requirements-dev.txt`).

## Why each detected signal is not an integration

| Signal | What it actually is |
|--------|---------------------|
| "Wire the same validators into `api/main.py::_load_live_fixture`" | Wiring an in-repo validator into an in-repo function. `api/main.py` is this project's own service, not a third party. |
| "FPL API → pipeline" (threat-model trust boundary) | A boundary *description* for an API this project has consumed since before this milestone. Phase 6 adds validation at that boundary; it does not add the boundary. |

## The one outbound call this phase does add

`ops/notify.py` issues a single optional `requests.post` to whatever URL the operator places in
`FPL_ALERT_WEBHOOK` (an ntfy.sh topic, a Discord channel webhook, or a Slack incoming webhook). This
is not an API integration with a capability surface to enumerate: there is no SDK, no authentication
flow, no resource model, and no second operation. The entire contract is "POST this JSON object to
this URL, ignore the response". A coverage matrix over it would have exactly one row and no
meaningful opt-out decision, which is why a matrix is not fabricated here.

Its failure behaviour is specified and gated in plan `06-03` (Task 1): the POST carries a 10-second
timeout, is wrapped in its own guard so a transport failure still leaves the on-disk alert record
written, and can never raise into the pipeline it observes.

---
*Declared at plan time for Phase 6 — Security, Reliability & Observability Hardening.*
