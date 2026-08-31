# Pitfalls Research

**Domain:** Mid-season production hardening of a working FPL prediction product (React rewrite, FastAPI test suite, Playwright E2E, Docker/CI, security/reliability hardening)
**Researched:** 2026-08-31
**Confidence:** MEDIUM (domain patterns are well-established software engineering knowledge, cross-checked against current web sources; a few FPL-specific and Python-3.14-specific facts are LOW confidence and flagged as such — verify before locking in)

## Critical Pitfalls

### Pitfall 1: Big-bang React cutover silently breaks the weekly recommendation cycle

**What goes wrong:**
The team replaces all 8 vanilla pages with React in one branch, merges, and only then discovers a data-shape mismatch (e.g. a page that assumed `web/data/xp_table.json` rows are pre-sorted, or that null p10/p90 intervals render as blanks) during a live gameweek, right when users need the recommendation. Because the vanilla site and React site never ran side-by-side, there's no fallback and no easy diff to see what regressed.

**Why it happens:**
"Full rebuild" framing (explicitly chosen in this project) makes it tempting to treat the old site as throwaway and delete/ignore it mid-build, rather than keeping it live as a reference implementation until the React version has proven itself across a real gameweek cycle (deadline → live → finished).

**How to avoid:**
- Keep the vanilla site deployed/buildable and untouched until React reaches parity sign-off; do not delete `web/` static assets until after at least one full gameweek cycle has been verified on React.
- Build page-by-page, verifying each new React page against the same `web/data/*.json` snapshot the vanilla page renders, diffing rendered output (numbers, sort order, captain picks, differential ranks) rather than just "looks right."
- Treat the JSON export contract as a strict interface: write a contract test that asserts each page's expected fields exist and are non-null for a known-good snapshot, and run it against both old and new implementations during the transition.
- Because a full gameweek cycle (deadline, live scores, bonus points, price changes) only happens once a week, budget calendar time, not just engineering time, for parity verification — one bad merge before a deadline can cost a full week of trust.

**Warning signs:**
- No side-by-side old/new site running during development.
- React page renders without errors but numbers subtly differ (e.g. rounding, captain tie-breaks, autosub order) from the vanilla page on the same data.
- "It works" was only checked once, not across a blank gameweek, a postponed-fixture gameweek, or a double-gameweek edge case.

**Phase to address:**
React rebuild phase — should include an explicit parity-verification step (running old and new side by side against the same weekly export) before the vanilla site is retired, not just a "build the pages" step.

---

### Pitfall 2: Data-heavy tables (xP table, prices, fixtures) regress on sort/filter/format semantics that "look" identical

**What goes wrong:**
The xP table, prices page, and fixtures page all involve large sortable/filterable tables with subtle formatting rules (e.g. price shown to 1 decimal, ownership as %, p10/p90 shown as a range only when both present, differential highlighting based on ownership threshold). A React table component (even a good one like TanStack Table) defaults to generic sort/format behavior that doesn't match the hand-written vanilla JS, and these mismatches are easy to miss in casual QA because the table "looks like a table."

**Why it happens:**
Table components are a very common thing to "just use a library for" during a rewrite, but domain-specific formatting/sorting rules (numeric vs string sort on price strings, secondary sort keys like sort-by-xP-then-by-price, locked columns, sticky headers on long tables) get lost unless each rule is explicitly ported and tested.

**How to avoid:**
- Before writing the React table, enumerate every sort/filter/format rule from the vanilla JS (grep for `.sort(`, `toFixed(`, conditional class names) and write it down as an explicit checklist per page.
- Add unit tests (Vitest/RTL) for formatting functions (price, xP range, ownership %) independent of the table library, so the pitch/table rendering can be swapped without silently changing number formatting.
- Cover exactly these tables in the Playwright suite with real snapshot data and assert specific cell values, not just "table renders with N rows."

**Warning signs:**
- Table "renders" in dev but a user reports numbers or sort order look wrong only after a real gameweek with edge-case data (blank gameweek, postponed fixture, price change day).
- No unit tests for the formatting helpers, only visual review.

**Phase to address:**
React rebuild phase (xP table, prices, fixtures pages specifically) — pair with the Playwright E2E phase so these tables get explicit assertion coverage before old pages are retired.

---

### Pitfall 3: React CSR breaks or degrades SEO/discoverability that the vanilla static site had "for free"

**What goes wrong:**
The current site is static HTML — trivially crawlable, fast first paint, shareable links work immediately. A default Vite + React SPA renders an empty `<div id="root">` until JS executes, which can mean search engines and link-preview crawlers (used when users share squad/team links) see nothing, and pages the product will want indexed for organic acquisition (methodology, league, scoreboard) lose ranking after the switch.

**Why it happens:**
Vite's default template is a pure client-rendered SPA; teams focus on "does it work in the browser I'm testing in" and don't consider crawlers or link unfurling until traffic/acquisition metrics drop weeks later — by which point it's a monetization-relevant regression.

**How to avoid:**
- Since this is a freemium product that needs organic acquisition pre-launch, decide explicitly whether any pages need pre-rendering/SSG (e.g. methodology, landing/marketing pages) versus which are fine as CSR (team, solver — behind auth/personalized, not meant to be indexed).
- For pages that must be crawlable, use a static-generation approach (Vite SSG plugin, or prerendering step in the build) rather than assuming CSR is equivalent to the old static HTML.
- At minimum, set per-page `<title>`/meta tags via a router-aware head manager (e.g. react-helmet-async) — the vanilla site had per-page static `<title>` tags "for free," and losing that is easy to miss.

**Warning signs:**
- `view-source:` on a built React page shows only a script tag and empty div — no meaningful text.
- Social share preview (Slack/Twitter/WhatsApp unfurl) of a page link shows blank/generic card after the rewrite where it used to show real title/description.

**Phase to address:**
React rebuild phase — decide CSR vs SSG per page during initial React scaffolding, not after; retrofit is far more expensive once 8 pages exist.

---

### Pitfall 4: Playwright E2E tests are flaky because they hit the live, weekly-changing FPL data instead of fixed fixtures

**What goes wrong:**
The site's whole purpose is to consume weekly-changing JSON (`web/data/*.json`) and live FPL API data. If E2E tests run against whatever is currently in `web/data/` or call the live API, tests pass mid-week and fail on deadline day (blank gameweek, price change, injury flag change) — or vice versa — with no code change. This is the single most common way Playwright suites get disabled/ignored ("just flaky, ignore it") within a few weeks of introduction.

**Why it happens:**
It's tempting to point E2E tests at "the real running app with real data" because that's what's actually deployed, and it feels like a more faithful test. But FPL data changes daily (prices), weekly (gameweeks), and has genuine edge cases (blank/double gameweeks, postponed fixtures) that are exactly the states a test suite needs to be deterministic about, not exposed to at random.

**How to avoid:**
- Freeze fixed, versioned fixture snapshots of `web/data/*.json` (checked into the repo or an artifact) representing known states: a normal gameweek, a blank gameweek, a double gameweek, a post-deadline "live" gameweek, and the user's own team (id 6980093) at a known state. Point the E2E test server at these fixtures, never at live data or the current day's real export.
- For the FastAPI-backed flows (rate-my-team, solver), mock or stub the outbound FPL API calls (route interception via Playwright's `page.route()` for browser-side calls, and dependency overrides / recorded HTTP fixtures for FastAPI-side calls) so a live FPL API hiccup never fails a CI run.
- Treat fixture staleness like a schema migration: when the export contract changes shape, update fixtures deliberately and re-verify all E2E assertions, rather than letting fixtures silently drift from what production actually emits.
- Never assert on values that depend on "now" (e.g. "next deadline in X days") without controlling the clock (Playwright's clock API / fixed system time in the test env).

**Warning signs:**
- E2E suite has different pass/fail results on different days without any code change.
- Tests reference `data/latest` or call `fantasy.premierleague.com` directly instead of a pinned fixture directory.
- Nobody can say which gameweek/season a given E2E fixture represents.

**Phase to address:**
Playwright E2E phase — fixture strategy (frozen snapshots + FPL API mocking) must be designed before the first test is written, not bolted on after flakiness appears.

---

### Pitfall 5: Playwright browser binaries and caches are re-downloaded on every CI run, or worse, silently mismatch between local dev and CI

**What goes wrong:**
Playwright ships its own browser binaries (Chromium/Firefox/WebKit) separate from npm packages. Without explicit CI caching, every workflow run re-downloads ~300MB+ of browsers, slowing CI and burning free-tier GitHub Actions minutes. Conversely, over-aggressive or incorrect caching (caching by a key that doesn't include the Playwright version) can leave CI running a stale browser binary against a newer `@playwright/test`, causing cryptic protocol-mismatch failures that don't reproduce locally.

**Why it happens:**
Teams new to Playwright treat it like a normal npm dependency and either forget to cache `~/.cache/ms-playwright` at all, or cache it with a key that doesn't bump when the Playwright version changes in `package.json`/lockfile.

**How to avoid:**
- Cache the Playwright browser directory keyed on the lockfile hash *and* the installed `@playwright/test` version (e.g. `actions/cache` key including `hashFiles('package-lock.json')` plus `npx playwright --version`), and run `npx playwright install --with-deps` only on cache miss.
- Pin the Playwright version explicitly (not a floating range) so cache keys are stable and local/CI environments can't silently drift onto different browser builds.
- Since this project already disables the Python `pytest-playwright` plugin (`pytest.ini` disables `-p no:playwright`) in favor of (implied) the Node Playwright runner, make that decision explicit and documented — don't let both a Python Playwright plugin and a Node Playwright runner exist half-configured, which is a common source of "which Playwright is even running" confusion.

**Warning signs:**
- CI job time for the E2E step balloons every run because caching isn't hit.
- A test fails in CI referencing a browser protocol error that never reproduces on a developer machine running a different (newer) Playwright/browser pairing.

**Phase to address:**
CI/CD hardening phase, in coordination with the Playwright E2E phase — set up caching and version pinning at the same time the workflow is authored, not as a later optimization pass.

---

### Pitfall 6: Retrofitting tests onto `api/main.py`'s module-level global state and `threading.Lock` produces tests that pass in isolation but hide real races

**What goes wrong:**
`api/main.py` loads the model/pool into a module-level `_state` dict and `_solve_cache` at import time, guarded by a `threading.Lock`. The first test suite for this file is very likely to instantiate a single `TestClient` per test (or per module) and call endpoints sequentially — which never exercises the lock, never triggers the cache-invalidation race already flagged in `CONCERNS.md` (cache cleared inside `_lock` but read outside it), and gives 100% "passing tests" while the underlying concurrency bug remains live in production.

**Why it happens:**
`TestClient` requests are synchronous by default and a naive first test suite (understandably, since none exists yet) will test "does /solve return 200 with expected shape," not "what happens under concurrent /solve + a pool refresh." Concurrency bugs are inherently invisible to sequential test design, and nobody adds concurrency tests to a *first* suite without deliberately deciding to.
Additionally, because `_state` is populated at import time (module-level side effect), importing `api.main` in a test at all triggers artifact loading — meaning every test file that imports the app pays the model-load cost and, worse, all tests share the same mutated global state unless explicitly reset between tests, causing order-dependent test pollution (test A's solve-cache entries leak into test B's assertions).

**How to avoid:**
- Explicitly write at least one concurrency test that spawns multiple threads/async tasks calling `/solve` while a `_refresh()` (or equivalent pool/model reload) happens concurrently, and assert no exception and no stale-cache read — this directly targets the already-known cache-invalidation race in `CONCERNS.md`.
- Isolate global state between tests: add a pytest fixture (autouse) that resets `_state` and `_solve_cache` before/after each test, or refactor `_state`/cache into an object that can be constructed fresh per `TestClient` instance (a natural side effect of adding tests — this refactor is worth doing now rather than fighting global state forever).
- Because artifact loading (7MB model, 16MB parquet) happens at import time, use a `scope="session"` fixture for the `TestClient` app import to avoid reloading the model per test, but pair it with the state-reset fixture above so session-scoped speed doesn't reintroduce cross-test pollution.
- Mock/stub the outbound FPL API calls in `_fetch_team()` and pool-refresh paths so tests don't depend on live FPL API availability or rate limits — this is the same fixture-freezing discipline needed for Playwright (Pitfall 4), applied at the API layer.
- Test the `require_key()` auth stub explicitly for both the "no key" and "wrong key" paths now, since it's the single swap point for real auth later — a test suite that doesn't pin its current (stub) behavior will not catch a regression when Supabase JWT replaces it.

**Warning signs:**
- All tests pass, but they always run in the same order and no test explicitly asserts anything about concurrent access to `_solve_cache` or `_lock`.
- Tests are flaky only when run in parallel (`pytest -n auto`) or in a different order — a symptom of shared global state leaking between tests.
- No test imports `api.main` more than once per session, or the model reload cost is "surprisingly" high per test run (indicates state isn't isolated, or model is reloaded per test unnecessarily).

**Phase to address:**
FastAPI test suite phase — this is the phase where the global-state design gets its first real pressure test; treat "add tests" and "add a state-reset/DI seam for tests" as one deliverable, not two.

---

### Pitfall 7: Baking a fat, slow-to-build Docker image because LightGBM/pandas/pyarrow/scikit-learn pull in full build toolchains

**What goes wrong:**
A naive `FROM python:3.14 / pip install -r requirements.txt` Dockerfile for this stack routinely produces images in the 1.5–2.5GB+ range and slow, cache-busting builds, because LightGBM's Python wheel can fall back to compiling from source (pulling in gcc/cmake/libgomp), pandas/pyarrow bring large compiled extensions, and a full (non-slim) base image plus `apt-get` build tools left in the final layer bloat everything further.

**Why it happens:**
Teams new to Dockerizing an ML/data-science stack default to the "just works" full base image and single-stage `pip install`, because getting LightGBM to import correctly is already a minor fight (native OpenMP dependency, `libgomp1`) and adding multi-stage build discipline on top feels like premature optimization — until CI minutes and GHCR storage/pull time make it a real cost on a free-tier budget.

**How to avoid:**
- Use a multi-stage build: a `builder` stage (with build tools, `libgomp1`-dev if needed) that installs wheels into a virtualenv or `--target` directory, and a slim runtime stage (`python:3.14-slim`) that copies only the installed site-packages plus `libgomp1` runtime lib (not `-dev`) — LightGBM's prebuilt wheel needs `libgomp.so.1` at runtime but not a compiler.
- Prefer prebuilt wheels over source builds: pin versions known to ship manylinux wheels for the target Python (verify against PyPI before pinning — see Pitfall 11) so `pip install` doesn't silently trigger a from-source LightGBM/pyarrow build inside the image.
- Add a `.dockerignore` covering `data/`, `.git/`, notebooks, and (per the existing concerns audit) never let the 134MB Chrome `.deb` or any large binary end up in the Docker build context — a bloated build context slows every build even before layers are considered.
- Measure and gate image size in CI (e.g. `docker image inspect` size check or `dive` in a lint step) so growth is visible before it becomes normal.

**Warning signs:**
- `docker build` takes several minutes even with warm layer cache, or CI logs show `gcc`/`cmake` compiling LightGBM from source.
- Final image size creeps past ~1GB and nobody can explain which layer is responsible.
- GHCR push/pull times become a noticeable fraction of the CI job.

**Phase to address:**
Docker/CI phase — get the multi-stage pattern right in the first Dockerfile; retrofitting multi-stage onto a working single-stage image later is easy technically but easy to deprioritize once "it works."

---

### Pitfall 8: PuLP's CBC solver binary is missing or unreachable inside the container, and `/solve` fails only in Docker

**What goes wrong:**
PuLP does not reliably bundle a working CBC executable across all install paths — a "No executable found" / `PulpSolverError` at solve time is a well-known failure mode, and it's exactly the kind of thing that works on a developer's conda environment (which may have CBC available via conda-forge or a previous manual install) but fails the moment the app is Dockerized from a clean base image, because nothing in `requirements.txt` alone guarantees a CBC binary is present. *(LOW confidence — verify current PuLP/CBC packaging behavior directly against the PuLP docs and by running `pulp.listSolvers(onlyAvailable=True)` inside the built image before shipping.)*

**Why it happens:**
`pip install pulp` installs the Python API; whether a usable `cbc` executable comes with it depends on the PuLP version and the extras used. Conda environments often have CBC available as a system-level binary from a previous setup step that never got written down as a Dockerfile instruction, so the dependency is invisible until the app is rebuilt from scratch in a container.

**How to avoid:**
- Explicitly install CBC in the Docker image rather than relying on it coming "for free" with PuLP: either `pip install "pulp[cbc]"` (if available for the pinned PuLP version) or `apt-get install -y coinor-cbc` in the builder/runtime stage, and record whichever path is chosen in the Dockerfile as a comment so it survives future edits.
- Add a solver health check at API startup (already flagged as a recommendation in `CONCERNS.md`'s "Dependencies at Risk" section) that calls `pulp.listSolvers(onlyAvailable=True)` and fails fast/loud if CBC isn't found, rather than only failing on the first real `/solve` request from a user.
- Add this exact check to the FastAPI test suite and to a Docker-image smoke test in CI (build image → run container → hit `/health` or run `pulp.listSolvers` inside it) so a missing solver binary is caught in CI, not in production after the image is published.

**Warning signs:**
- `/solve` works in every developer's local environment but fails immediately once tested against a container built from a clean Dockerfile.
- No test or CI step ever actually invokes the ILP solver inside the built Docker image — only outside it (host Python).

**Phase to address:**
Docker/CI phase — must be verified as part of the Dockerfile authoring step and again as an image smoke test in CI, not assumed from "it worked on conda."

---

### Pitfall 9: Baking the model artifact into the Docker image creates a stale-model trap; mounting it externally creates a missing-file trap

**What goes wrong:**
Two failure modes, opposite directions:
- **Bake the model in**: every time the model is retrained (which, per this project's own cadence, could be weekly or whenever price-model data accrues), the Docker image must be rebuilt and republished to pick up the new artifact — if the team forgets this coupling, the deployed image silently serves an increasingly stale model with no error, no warning, and no CI check catching it, because the image still builds and boots fine with an old (but valid) `xp_model.joblib`.
- **Mount the model externally** (volume/bind-mount, or fetch-on-boot): the image is decoupled from retraining, but now a missing/misconfigured mount means the container starts, `_state` loading fails or loads a wrong/absent artifact, and (per the existing joblib/pickle fragility already noted in `CONCERNS.md`) a LightGBM/scikit-learn version mismatch between the image's Python env and the artifact's training env causes a deserialization crash at import time — which, because `api/main.py` loads artifacts at module import, crashes the whole process on startup rather than failing one request.

**Why it happens:**
This milestone explicitly stops short of live deployment (CI ends at a published image, no deploy step), so the bake-vs-mount decision doesn't have to be made under real production pressure yet — but if it's left undecided, whoever eventually deploys the image will guess, and the guess is unlikely to account for the retraining cadence or the joblib version-pinning fragility already flagged as a project risk.

**How to avoid:**
- Decide explicitly (even if deployment itself is out of scope this milestone): bake the artifact at build time via a build ARG/stage that copies a specific artifact version, and tag the image with the model version (e.g. image tag includes a model hash or training date) so "which model is in which image" is always answerable from the tag alone.
- If artifacts will ever be mounted/fetched externally in a future milestone, add a startup health check now that validates the loaded model's expected schema/feature columns against `config.py` before serving traffic, so a version mismatch fails loudly at boot instead of producing silently wrong predictions.
- Pin the training environment's LightGBM/scikit-learn/joblib versions to match the serving image's versions exactly (this ties directly into Pitfall 11 — dependency pinning) — this is the single highest-leverage fix for the joblib/pickle fragility already identified in `CONCERNS.md`.

**Warning signs:**
- No documented answer to "if I retrain the model today, what has to happen for a deployed image to serve it?"
- Model artifact version and Docker image tag carry no relationship to each other.
- `xp_model.joblib` load happens at import time with no schema/version assertion — a bad deserialize either crashes hard (bake) or is caught nowhere (mount).

**Phase to address:**
Docker/CI phase — the decision and its guardrail (version tagging + startup schema check) should ship even though live deployment is out of scope; it's cheap now and expensive to retrofit once a deploy pipeline exists.

---

### Pitfall 10: CI secrets and unpinned third-party Actions turn a "just publish a Docker image" pipeline into a supply-chain exposure

**What goes wrong:**
Referencing third-party GitHub Actions by a mutable tag (e.g. `uses: some/action@v3`) means the pipeline's behavior — including anything with access to `GITHUB_TOKEN`, GHCR publish credentials, or any secrets the workflow exposes — can change without a corresponding commit in this repo, if that action's tag is ever repointed (maliciously or via compromised maintainer account). This already happened at scale in the wild: the March 2025 tj-actions/changed-files incident, where a widely-used action's tags were rewritten to a malicious commit and exfiltrated CI secrets from every workflow that ran during the compromised window across roughly 23,000 repositories. Separately, workflows triggered on `pull_request_target` or that check out and execute untrusted PR code with secrets in scope create a classic "pwn request" vector — dangerous specifically because this repo may eventually accept external contributions or run CI on forks.

**Why it happens:**
Copy-pasting example GitHub Actions YAML from docs/blog posts almost always uses `@v3`/`@main`-style tags because they're more readable, and nobody thinks about action-tag mutability as a threat model until an incident like tj-actions makes it visible — pinning by full commit SHA feels like unnecessary friction on a solo/small project.

**How to avoid:**
- Pin every third-party action (not just risky ones) to a full 40-character commit SHA, with a version comment for readability (e.g. `uses: actions/checkout@<sha> # v4.2.2`); first-party `actions/*` are lower risk than random third-party actions but pin them too since even `actions/checkout` has had incidents in the ecosystem historically.
- Use Dependabot (or Renovate) to keep pinned SHAs current — pinning without an update mechanism just trades "vulnerable to tag rewrites" for "silently falls behind on security patches," so pair the pin with automated PRs that bump the SHA.
- Scope secrets tightly: use repository/environment-level secrets with the minimum permissions (`permissions:` block set explicitly per workflow, not defaulted to read/write-all), and never pass secrets to a job that also checks out/builds from a `pull_request_target` trigger without review gating.
- For the GHCR publish step specifically, use the automatically-scoped `GITHUB_TOKEN` (with `packages: write` permission explicitly granted) rather than a long-lived personal access token stored as a secret, minimizing blast radius if a workflow is ever compromised.
- Add a CI lint step (e.g. `zizmor` or a simple grep) that fails the build if any `uses:` line references a mutable tag instead of a SHA, so this becomes a structural guarantee rather than a one-time review.

**Warning signs:**
- Any `uses: owner/action@vN` or `@main`/`@master` in `.github/workflows/*.yml`.
- Workflow `permissions:` block absent (defaults to broad token permissions) rather than explicitly minimal.
- No Dependabot config for `github-actions` ecosystem, meaning pinned SHAs (once added) will silently rot.

**Phase to address:**
CI/CD hardening phase — should be a checklist item at the same time workflows are first authored (this project's `.github/workflows/` are currently untracked/dormant per `PROJECT.md`, i.e. this is a rare opportunity to get it right from the very first commit rather than retrofitting).

---

### Pitfall 11: First-time dependency pinning on a working conda/pip hybrid environment breaks reproducibility instead of fixing it — especially with Python 3.14's immature wheel ecosystem

**What goes wrong:**
`requirements.txt` today uses `>=` constraints and "works" only because the specific conda env (`python314`) happens to have a compatible transitive dependency graph resolved once, a while ago. The first attempt to pin everything to `==` (the fix `CONCERNS.md` itself recommends) commonly does one of two things wrong: (a) `pip freeze` inside the conda env captures conda-installed packages pip doesn't actually manage (e.g. things installed via `conda install`, or platform-specific build strings), producing a lockfile that fails to install cleanly in Docker/CI on a plain pip/venv setup; or (b) pinning to exact versions that don't have prebuilt wheels for Python 3.14 yet, forcing slow/fragile from-source builds in CI and Docker (LightGBM, scikit-learn, and PyArrow have all had partial/late 3.14 wheel coverage — as of late 2025, scikit-learn had not yet shipped 3.14 wheels and PyArrow's 3.14-ready release was still catching up to Python 3.14's own release). *(LOW confidence on exact current wheel status for LightGBM/PuLP specifically for 3.14 — verify directly against PyPI's file listing for each pinned version before finalizing the lockfile, since this changes month to month.)*

**Why it happens:**
"Pin the versions" sounds like a mechanical `pip freeze > requirements.lock` task, but a conda-managed environment mixes conda and pip package sources in ways `pip freeze` doesn't fully understand, and Python 3.14 is new enough (this project adopted it ahead of most of the ecosystem) that "the version I have locally" is not guaranteed to have a wheel available for a clean install elsewhere (Docker's `python:3.14-slim` base, GitHub Actions' hosted Python 3.14).

**How to avoid:**
- Before pinning, explicitly separate "what pip actually installed" from "what conda provided" — run the pin/lock step from a clean pip-only virtualenv built against `requirements.txt` (not `pip freeze` inside the conda env) to get a lockfile that's portable to Docker/CI, then verify the conda env still resolves compatibly for local dev.
- For each pinned version, check PyPI's file list for that release to confirm a `cp314`-tagged wheel exists for the target platform (linux x86_64, matching the Docker base image) before locking it — don't assume "latest version" implies "has a 3.14 wheel."
This directly matters for LightGBM (native extension, has historically had slower wheel turnaround for new Python versions), scikit-learn (confirmed no 3.14 wheels as of Oct 2025 per current search), and PyArrow (3.14 support tracked and in progress but timing-sensitive).
- If a needed package has no 3.14 wheel yet, treat that as a real go/no-go input to the Docker/CI phase — either accept a slower from-source build (with the base image build toolchain that implies, conflicting with the image-size goal in Pitfall 7) or pin that one package to whatever last-working version does have a 3.14 wheel, documenting the constraint.
- Re-run the full pytest suite (once it exists) against the newly-pinned, from-clean-install environment — not just against the existing conda env — before declaring the pin done; pinning that "still passes in the same conda env it was extracted from" proves nothing about portability.

**Warning signs:**
- `pip install -r requirements.lock` fails or behaves differently in a fresh venv/Docker build than in the existing conda env.
- CI logs show compilation happening (gcc invoked) for a package that's supposed to be pure-wheel-installed.
- Nobody has checked PyPI directly for `cp314` wheel tags on the pinned versions — the pin was chosen purely from "what's currently installed."

**Phase to address:**
Security/config hardening phase (dependency pinning task) — do this pin-and-verify cycle as its own testable step, gated on a clean-environment install + full test pass, before folding it into the Docker phase (which will inherit whatever wheel-availability problems the pin didn't catch).

---

### Pitfall 12: Using Premier League club crests/kit imagery without a clear rights basis creates legal exposure right as the product moves toward monetization

**What goes wrong:**
Club crests and kit designs are trademarked/copyrighted by the Premier League and individual clubs. A product that's free/fan-hobby-scale generally flies under the radar, but this project is explicitly heading toward paid subscriptions (₹499/$19 season pass) — the moment real money changes hands, "fan project" goodwill is a weaker legal shield, and a cease-and-desist (or a payment processor / app-store compliance review flagging trademark use) becomes a real, not hypothetical, risk for the pitch renderer specifically, since it's the most visually crest/kit-heavy surface in the product.

**Why it happens:**
Building the "obviously correct" FPL-style pitch UI naturally pulls toward recreating what the official app and most fan tools visually look like — actual club crests and kits — because that's what makes it feel legitimate and readable at a glance, without pausing to check what rights basis (if any) backs that imagery.

**How to avoid:**
- Default to using FPL's own officially-served image assets (the FPL API and site already serve shirt/kit images and team badges from their own CDN as part of the public bootstrap data) rather than sourcing, redistributing, or re-hosting club crest/kit artwork from another source — hot-linking or referencing official-source URLs for elements FPL itself displays publicly is a materially different (and more defensible) posture than downloading and re-hosting logo files.
This specific technical detail (which URLs/fields the current FPL bootstrap payload exposes for shirts/badges) should be re-verified against the live API response next to this decision, since API-shape assumptions elsewhere in this codebase are already flagged as fragile (`CONCERNS.md` — "Live predictions depend on consistent FPL API schema").
- Where officially-served imagery isn't available or reliable enough for the pitch UI's needs, use neutral/generic kit graphics (color-by-team, no crest) rather than recreating trademarked crest artwork independently — many fan tools use exactly this pattern (colored jersey silhouettes, team-color coding, initials) instead of true crests.
- Carry an explicit "not affiliated with / endorsed by the Premier League or its clubs" disclaimer on the site (a near-universal pattern among independent FPL fan tools), since even fair, non-infringing use benefits from an unambiguous non-affiliation statement, especially once payments are involved.
- Treat this as a decision to make and document once (during the pitch-renderer UI design step, as `PROJECT.md` already flags), not something to leave ambiguous — a payment gateway or app-store review (Razorpay/merchant-of-record) may itself ask about trademark/brand usage as part of onboarding compliance.

**Warning signs:**
- Crest/kit image files checked into the repo as static assets (`web/assets/crests/*.png` or similar) rather than referenced from a live official source or generated programmatically.
- No disclaimer/non-affiliation text anywhere on the site.
- The decision is left as a TODO past the pitch-renderer UI design phase and resurfaces only when a payment integration or legal review asks about it.

**Phase to address:**
React rebuild / pitch renderer phase — `PROJECT.md` already marks this "resolve during UI design," so it should be a concrete decision-with-rationale artifact from that phase, not deferred again.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Skip parallel-run verification, cut over React in one merge | Faster perceived progress | Silent regression discovered live during a gameweek, with no fallback | Never for this milestone — core value is "must not disrupt the weekly cycle" |
| Point first Playwright tests at live `web/data/` and live FPL API | Fast to write, "realistic" | Flaky suite gets disabled/ignored within weeks | Never — acceptable only for a one-off manual smoke check, not the CI suite |
| Write FastAPI tests without touching the global-state/lock design | Tests ship faster | Tests pass while masking real concurrency bugs already flagged in `CONCERNS.md` | Acceptable only as an interim first pass, with an explicit follow-up ticket for concurrency tests + state-reset fixture |
| Single-stage Docker build (`pip install -r requirements.txt` on full base image) | Simple, works immediately | 1.5–2.5GB+ images, slow CI, high GHCR costs at scale | Acceptable for a first "does it boot" spike, never for the published/tagged image |
| Pin dependencies via `pip freeze` inside the existing conda env | Quick, one command | Lockfile may not reproduce in Docker/CI (mixed conda/pip sources, missing 3.14 wheel checks) | Never as the final lockfile — fine as a starting draft to hand-verify against a clean venv |
| Bake model artifact into image with no version tag relating image↔model | Simplifies first Dockerfile | Untraceable stale-model deployments once retraining resumes | Acceptable only until the phase explicitly addresses model/image version tagging |
| Leave GitHub Actions on tag-pinned (`@v3`) third-party actions | Standard, readable YAML | Supply-chain exposure (tj-actions-style secret exfiltration) | Never once secrets (GHCR publish creds) are in the workflow |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| FPL public API (bootstrap/fixtures/entry) in Playwright/API tests | Calling the live API in test runs | Freeze versioned fixture JSON snapshots; mock outbound calls in both Playwright (`page.route()`) and FastAPI tests (dependency override / recorded responses) |
| PuLP + CBC solver | Assuming `pip install pulp` guarantees a working CBC binary everywhere | Explicitly install CBC (`pulp[cbc]` extra or `apt-get install coinor-cbc`) in the Docker image; verify with `pulp.listSolvers(onlyAvailable=True)` at startup and in CI |
| GHCR (GitHub Container Registry) publish | Using a long-lived PAT secret for `docker push` | Use scoped `GITHUB_TOKEN` with explicit `packages: write` permission |
| Third-party GitHub Actions | Referencing `@v3`/`@main` tags | Pin to full commit SHA + Dependabot for updates |
| FPL image CDN (shirts/badges) for pitch renderer | Downloading and re-hosting crest/kit artwork as static repo assets | Reference FPL's own officially-served image URLs, or use neutral/generic kit graphics |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Unbounded `_solve_cache` dict (already flagged in `CONCERNS.md`) | Memory grows over weeks of uptime with no restart | Add TTL/LRU eviction (`cachetools.TTLCache`) as part of the reliability-fixes work, verified by a new API test | Multi-week uptime without a redeploy |
| Model/parquet reloaded per-CLI-invocation instead of cached | CLI predict runs feel slow, repeated I/O | Cache-once pattern already used in API `_state`; extend to CLI entrypoints or a shared loader | Noticeable at every manual `predict.live` run, worse under load |
| Playwright browser binaries re-downloaded every CI run (no cache, or wrong cache key) | CI job time balloons; free-tier Action minutes burn faster than expected | Cache `~/.cache/ms-playwright` keyed on Playwright version + lockfile hash | Every single CI run until fixed — immediate, not a scale threshold |
| Docker image rebuilt from scratch every CI run (no layer cache reuse, or dependency layer invalidated by unrelated code changes) | Every CI run recompiles/reinstalls all Python deps | Order Dockerfile layers so `requirements.txt`/lockfile copy + install happens before application code copy; use BuildKit cache mounts | Every CI run — compounds as the repo/dep list grows |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Wide-open CORS (`["*"]`) left in place while adding a public-facing React frontend | Any site can call `/solve`/`/rate`, enabling scraping/abuse once the API is more discoverable via a polished frontend | Restrict `allow_origins` to the deployed frontend domain(s) as part of this milestone's security hardening, not deferred to the deploy milestone |
| Third-party GitHub Actions pinned to mutable tags | Supply-chain secret exfiltration (real-world precedent: tj-actions/changed-files, March 2025, ~23K repos affected) | Pin to full commit SHA; add Dependabot for `github-actions` ecosystem; lint for unpinned `uses:` |
| API keys (`FPL_API_KEYS`) risk of appearing in cron logs or CI logs | Credential leakage via log files/artifacts | Never echo/print env vars containing keys in scripts or workflow steps; use GitHub Actions `secrets.*` (auto-masked in logs), restrict `.env` file permissions |
| No explicit least-privilege `permissions:` block in GitHub Actions workflows | Compromised action/dependency gets broad token permissions by default | Set `permissions:` explicitly and minimally per workflow/job |
| Docker image published to GHCR without a vulnerability/dependency scan step | Known-CVE base image or Python package ships in the published, potentially-public image | Add a scan step (e.g. `docker scout` or Trivy) to the CI publish job before/alongside the push |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| React rewrite changes URL structure/routing without redirects | Bookmarked/shared links (team, league, scoreboard views) break | Preserve existing URL paths in the React Router config, or add explicit redirects for any that must change |
| Pitch renderer uses generic/incorrect team colors or missing shirt art for a team mid-transfer-window (kit/crest changes) | Squad looks visually wrong or confusing right when a user is deciding transfers | Source imagery from FPL's live bootstrap data (already updated by FPL when kits change) rather than a hardcoded/static local mapping |
| E2E and manual QA only test "happy path" gameweek states | Real breakage surfaces only on blank/double gameweeks or post-postponement — exactly when users most need reliable output | Include blank-gameweek and double-gameweek fixtures explicitly in both Playwright and API test suites (this codebase's existing pytest suite already has a precedent: `test_blank_gw_holding_needs_metadata`) |

## "Looks Done But Isn't" Checklist

- [ ] **React parity**: Verify not just that a page renders, but that sort order, number formatting (price, xP ranges, ownership %), and captain/differential logic produce identical output to the vanilla page on the same JSON snapshot.
- [ ] **Playwright E2E "passing"**: Verify tests run against frozen fixtures (not live `web/data/` or live FPL API) and include at least one blank-gameweek / edge-case fixture, not only a normal-week happy path.
- [ ] **FastAPI test suite "covers main.py"**: Verify it includes at least one concurrency test (parallel `/solve` + refresh) and an explicit state-reset fixture — not just sequential happy-path endpoint tests.
- [ ] **Docker image "builds and runs"**: Verify the built image actually resolves a CBC solver (`pulp.listSolvers(onlyAvailable=True)` inside the container) and serves a real `/solve` request, not just that `docker build` exits 0 and `/health` returns 200.
- [ ] **CI "green checkmark"**: Verify third-party Actions are SHA-pinned and workflow `permissions:` are minimal — a green CI run says nothing about supply-chain exposure.
- [ ] **Dependencies "pinned"**: Verify the lockfile installs cleanly in a fresh venv/Docker build (not just inside the existing conda env) and that pinned versions have confirmed `cp314` wheels for the target platform.
- [ ] **Crest/kit imagery "looks right"**: Verify the rights basis (officially-served asset reference vs. re-hosted trademarked artwork) is a documented decision, not an unexamined default.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|------------------|
| Big-bang React cutover broke the live weekly cycle | HIGH | Roll back to the still-deployable vanilla site (if kept per Pitfall 1's prevention) while diagnosing; without that fallback, recovery means an emergency hotfix under time pressure before the next deadline |
| Playwright suite is flaky and got disabled | MEDIUM | Re-derive fixed fixture snapshots from a known-good export, rewrite tests against them, re-enable incrementally per page rather than all at once |
| FastAPI concurrency bug (stale cache read) shipped to production | MEDIUM | Add the TTL/LRU cache fix and concurrency regression test from `CONCERNS.md`'s recommendation; redeploy; the bug is a known, already-diagnosed one, not a mystery |
| Docker image published with missing CBC binary | LOW | Fix Dockerfile (add `coinor-cbc` or `pulp[cbc]`), rebuild, republish — no data loss, just a bad image tag to supersede |
| CI secret exfiltrated via a compromised unpinned action | HIGH | Rotate all secrets immediately (GHCR token, any API keys used in CI), audit workflow run history for the compromised window, pin all actions to SHA before re-enabling CI |
| Dependency pin breaks the Docker/CI build (no 3.14 wheel) | LOW-MEDIUM | Unpin just the offending package to the last version with a working wheel, document the constraint, revisit when upstream ships 3.14 support |
| Crest/kit trademark concern raised post-launch (e.g. by payment gateway compliance review) | MEDIUM | Swap to officially-served FPL imagery or neutral kit graphics, add/strengthen non-affiliation disclaimer — a design change, not a data-loss event |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Big-bang React cutover breaks weekly cycle | React rebuild phase | Vanilla site stays live/buildable until React passes a full real-gameweek parity check |
| Data-heavy table regressions (xP/prices/fixtures) | React rebuild phase | Unit tests for formatting helpers + Playwright assertions on specific cell values |
| CSR SEO/discoverability regression | React rebuild phase | Per-page CSR-vs-SSG decision documented; `view-source` shows meaningful content for pages intended to be indexed |
| Flaky Playwright tests from live data | Playwright E2E phase | CI runs consistently pass/fail regardless of the calendar date; fixtures are versioned and reviewed like code |
| Playwright browser cache/versioning issues | CI/CD hardening phase (with Playwright phase) | CI job time for E2E step is stable across runs; cache key includes Playwright version |
| FastAPI tests hide global-state/lock races | FastAPI test suite phase | At least one concurrency test targets `_solve_cache`/`_lock`; state-reset fixture exists and is autoused |
| Docker image bloat | Docker/CI phase | Image size tracked/gated in CI; multi-stage build confirmed in Dockerfile |
| Missing CBC solver in container | Docker/CI phase | CI smoke test runs `pulp.listSolvers(onlyAvailable=True)` inside the built image |
| Bake-vs-mount model artifact ambiguity | Docker/CI phase | Image tag encodes model version; startup schema check validates loaded artifact |
| CI secrets/unpinned actions | CI/CD hardening phase | Lint step fails build on any non-SHA-pinned third-party action; `permissions:` explicit per workflow |
| First-time dependency pinning breaks reproducibility | Security/config hardening phase | Lockfile installs cleanly in a fresh venv/Docker build; full test suite passes against it |
| Trademarked crest/kit usage risk | React rebuild / pitch renderer phase | Documented decision (officially-served asset references or neutral graphics) + non-affiliation disclaimer present on site |

## Sources

- [Python 3.14 Wheels Readiness — status.fedoralovespython.org](https://status.fedoralovespython.org/wheels_py314/) — LOW confidence, general tracker, spot-check per package before pinning
- [pandas-dev/pandas Issue #63649 — 3.14t Windows wheel clarification](https://github.com/pandas-dev/pandas/issues/63649) — LOW confidence
- [apache/arrow Issue #47438 — Python 3.14 wheel support](https://github.com/apache/arrow/issues/47438) — LOW confidence
- [PuLP discussion #384 — PulpSolverError / CBC executable not found](https://github.com/coin-or/pulp/discussions/384) — LOW confidence, verify against current PuLP release notes
- [PuLP official docs — includeme / solver installation](https://coin-or.github.io/pulp/main/includeme.html) — LOW confidence (fetched via search summary, not direct read)
- [GitHub Changelog — GitHub Actions policy now supports blocking and SHA pinning actions (Aug 2025)](https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/) — MEDIUM confidence, cross-checked across multiple sources describing the same March 2025 tj-actions/changed-files incident
- [emmer.dev — Pin Your GitHub Actions to Protect Against Supply Chain Attacks](https://emmer.dev/blog/pin-your-github-actions-to-protect-against-mutability/) — MEDIUM confidence
- [pydevtools — How to pin GitHub Actions by SHA for Python projects](https://pydevtools.com/handbook/how-to/how-to-pin-github-actions-by-sha-for-python-projects/) — MEDIUM confidence
- [Independent FPL fan tools (Fantasy Football Scout, LiveFPL, Fantasy Football Hub) — general non-affiliation/disclaimer pattern](https://www.fantasyfootballscout.co.uk/) — LOW confidence; specific crest/kit image-sourcing mechanics not directly confirmed, recommend spot-checking live FPL API image fields before implementation
- Domain/software-engineering pattern knowledge (React SPA migration practice, Playwright fixture/mocking discipline, FastAPI global-state testing, Docker multi-stage builds) — general engineering knowledge, cross-referenced with the project's own `CONCERNS.md` audit for FPL-specific specifics
- `/home/sraja/fpl/.planning/PROJECT.md` and `/home/sraja/fpl/.planning/codebase/CONCERNS.md` — primary project-specific grounding (HIGH confidence, first-party source)

---
*Pitfalls research for: FPL prediction product — mid-season production hardening (React/Playwright/FastAPI tests/Docker/CI)*
*Researched: 2026-08-31*
