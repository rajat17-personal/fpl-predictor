# syntax=docker/dockerfile:1
# Multi-stage image for the FPL solver API (CI-03). The builder stage installs
# the hash-locked runtime dependency set from requirements.txt with
# --require-hashes (D-04); the runtime stage is a fresh python:3.14-slim that
# receives only the installed site-packages tree plus application code, web/
# and frontend/dist -- no compiler, no pip cache, and no model artifact (D-05)
# ever lands in a shipped layer. Both static frontends are baked in (D-06) so
# Phase 7's cutover (CUT-01) is a mount-config flip in api/main.py, not an
# image rebuild. The model itself is supplied at deploy time next milestone --
# api/main.py's /api/health never calls _refresh(), and _refresh() only loads
# the joblib artifact when FPL_FIXTURE_DIR is unset, so this image boots and
# answers health/fixture-mode solves with no model present.

FROM python:3.14-slim AS builder
WORKDIR /app
# Copying the lock alone (before any other source file) keeps this layer
# cacheable across source-only changes -- only requirements.txt edits bust it.
# Plan 05-01's SUMMARY confirmed a clean-venv install with zero source
# compilation for every pin in the current lock, so no compiler is added here
# (D-03's from-source fallback stays available if a future lock regenerate
# needs it -- add build-essential to this stage only, never runtime).
COPY requirements.txt .
RUN pip install --require-hashes --prefix=/install -r requirements.txt

FROM python:3.14-slim AS runtime
# libstdc++6 is not optional and not cosmetic: PuLP's bundled CBC binary
# (pulp/solverdir/cbc/linux/i64/cbc, invoked via pulp.PULP_CBC_CMD by
# optimize/squad_ilp.py, optimize/transfers.py and optimize/multi_period.py)
# is a compiled C++ executable. python:3.14-slim's own build process purges
# every apt-managed library that CPython itself doesn't dynamically link, and
# CPython never links libstdc++ -- so it is absent by default and every ILP
# solve would fail at subprocess launch without this line. Do not "optimize"
# this away.
# libgomp1 is equally load-bearing: LightGBM's lib_lightgbm.so dlopens the
# GNU OpenMP runtime at import time, so `import lightgbm` (reached via
# api/main.py -> predict.live -> models.train) crashes the server at boot
# without it.
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
WORKDIR /app
# The build-context exclusion list in .dockerignore -- not a hand-maintained
# COPY list -- decides what lands in the image. No model artifact, .env file,
# pipeline data directory, or test fixture set is reachable from this layer.
COPY . .

# Non-root runtime user (container hardening; T-05-02-02).
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# No extra package needed -- urllib.request is stdlib, works whether or not
# curl is present in the image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
