# Phase 5: Container Build & CI Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-04
**Phase:** 5-Container Build & CI Pipeline
**Areas discussed:** Lockfile tooling & layout, Docker image contents, Workflow shape & publish policy, GitHub repo setup & push

---

## Lockfile tooling & layout

| Option | Description | Selected |
|--------|-------------|----------|
| uv, pip-compatible output (Recommended) | uv compiles requirements.in → pinned requirements.txt with hashes; CI/Docker use plain pip | ✓ |
| uv with pyproject + uv.lock | Full uv-native project; converts repo away from requirements.txt | |
| pip-tools | Classic pip-compile; slower, adds a Python dev-dependency | |

**User's choice:** uv, pip-compatible output

| Option | Description | Selected |
|--------|-------------|----------|
| Runtime + dev split (Recommended) | requirements.in + requirements-dev.in; image installs runtime only | ✓ |
| Single lockfile | Everything pinned in one file; image carries test deps | |
| Three-way split | api-runtime / pipeline-extras / dev; leanest image, more maintenance | |

**User's choice:** Runtime + dev split

| Option | Description | Selected |
|--------|-------------|----------|
| Source-build in builder stage (Recommended) | Compilers in the Docker builder stage for any cp314 wheel gap; runtime stays 3.14-slim | ✓ |
| Drop image to 3.13 | Guaranteed wheels but version skew vs the 3.14 dev env | |
| Hard-block the phase | Wait for upstream wheels; hostage to release timing | |

**User's choice:** Source-build in builder stage (pre-authorized fallback)

| Option | Description | Selected |
|--------|-------------|----------|
| Hashes + require-hashes (Recommended) | --hash lines in locks; CI/Docker install with --require-hashes | ✓ |
| Exact pins only | == versions without hashes | |
| Pins + pip-audit job | CVE flagging on locked versions; doesn't stop tampering | |

**User's choice:** Hashes + require-hashes

---

## Docker image contents

| Option | Description | Selected |
|--------|-------------|----------|
| No model in image (Recommended) | Code + deps + static only; model supplied at deploy time; fixture mode for solve checks | ✓ |
| Commit model to git, bake it in | 7MB binary churn per retrain; self-contained image | |
| Model via CI artifact/release | GitHub Release download; out-of-band upload step per retrain | |

**User's choice:** No model in image

| Option | Description | Selected |
|--------|-------------|----------|
| Both web/ and frontend/dist (Recommended) | COPY vanilla site + CI-built dist; Phase 7 cutover becomes a config flip | ✓ |
| Vanilla web/ only | Mirrors today's posture; second image change needed at cutover | |
| API only, no static | Smallest image; diverges from single-process serving model | |

**User's choice:** Both web/ and frontend/dist

| Option | Description | Selected |
|--------|-------------|----------|
| Health + real fixture solve (Recommended) | Container in fixture mode; curl /health then real POST /api/solve through CBC | ✓ |
| Health + CBC presence check | pulp availability one-liner; doesn't exercise the API solve path | |
| Health only | Falls short of the stated success criterion | |

**User's choice:** Health + real fixture solve

---

## Workflow shape & publish policy

| Option | Description | Selected |
|--------|-------------|----------|
| One ci.yml, chained jobs (Recommended) | lint/typecheck → tests → E2E → docker build+smoke+scan → publish; shared dist artifact | ✓ |
| Split ci.yml + docker.yml | Separate verify and publish workflows; duplicated triggers | |
| Matrix-heavy minimal jobs | Fewer fatter jobs to save minutes; lumped failures | |

**User's choice:** One ci.yml, chained jobs

| Option | Description | Selected |
|--------|-------------|----------|
| Main only: sha + latest (Recommended) | Publish on main pushes only; SHA + moving latest tags | ✓ |
| Main + version tags | Adds semver release ceremony | |
| Every push publishes | Branch-tagged images; registry clutter with no deploys | |

**User's choice:** Main only: sha + latest

| Option | Description | Selected |
|--------|-------------|----------|
| Report-only + Security tab (Recommended) | SARIF to GitHub Security tab; never blocks | ✓ |
| Fail on CRITICAL only | Real gate but can freeze pipeline on unfixable base-image CVEs | |
| Fail on HIGH + CRITICAL | High friction for a pre-deploy project | |

**User's choice:** Report-only + Security tab

| Option | Description | Selected |
|--------|-------------|----------|
| Neutralize schedules now (Recommended) | Strip cron triggers; modernize in Phase 6 | |
| Modernize them in this phase | py3.14 + lockfile + fixed git identity now | ✓ |
| Delete them | Recreate from scratch in Phase 6 | |

**User's choice:** Modernize them in this phase (against the initial recommendation — follow-up below resolved the model tension)

| Option | Description | Selected |
|--------|-------------|----------|
| Modernize, schedules stay off (Recommended) | workflow_dispatch-only; local WSL cron stays production; model delivery settled next milestone | ✓ |
| Model from GitHub Release | Live schedule in Actions; manual upload per retrain | |
| Revisit: commit the model | Track the 7MB artifact for both weekly.yml and the image | |

**User's choice:** Modernize, schedules stay off

---

## GitHub repo setup & push

| Option | Description | Selected |
|--------|-------------|----------|
| Private (Recommended) | Protects predictions + model code; 2000 min/month, 500MB GHCR | |
| Public | Unlimited minutes/GHCR but publishes the product | |
| Private now, public later | Private today; revisit visibility at launch | ✓ |

**User's choice:** Private now, public later

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, push + verify green (Recommended) | Phase ends with repo on GitHub and a green run | |
| Push, but verify via act/local | Local simulation, first real run best-effort | |
| Defer the push | CI stays an unverifiable claim | |

**User's choice (free text):** "Git push actions will only be taken by me. rest can be completed. It can be kept as part of verify still but the push will be done manually by me."
**Notes:** All GitHub pushes (and repo creation) are user-executed. Plans model the push→green-CI verification as a blocking human checkpoint.

| Option | Description | Selected |
|--------|-------------|----------|
| PRs + required checks (Recommended) | Branch protection on main; ci.yml verify jobs required | ✓ |
| Direct pushes, CI advisory | No protection; red main can publish broken :latest | |
| Protection later | Defer the decision | |

**User's choice:** PRs + required checks

| Option | Description | Selected |
|--------|-------------|----------|
| Quick hygiene pass in-phase (Recommended) | Grep for emails/keys, swap workflow git identity to actions bot, confirm ignores; no history rewrite | ✓ |
| Push as-is | Accept current contents; relies on staying private | |
| Scrub .planning/ too | Keep planning state out of the pushed repo | |

**User's choice:** Quick hygiene pass in-phase

---

## Claude's Discretion

- CBC installation method (apt coinor-cbc vs PuLP bundled binary)
- Image COPY set and .dockerignore contents
- CI caching (pip/npm/Playwright browsers/docker layers), job names, concurrency, timeouts
- Exact uv invocation and lockfile naming; lock→Docker-layer mapping
- Python lint/typecheck tool choice (none configured today; via package-legitimacy gate)
- GHCR retention policy within the private free tier

## Deferred Ideas

- Arming daily/weekly Actions schedules + model delivery to CI (next milestone, with hosting)
- Trivy severity gating (next milestone, when deploys exist)
- Repo visibility revisit at launch (frontend-only open-sourcing)
- Semver/blessed-image release tagging (when deploys consume the registry)
- pip-audit dependency-CVE job (Phase 6 companion)
