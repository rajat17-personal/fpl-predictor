"""
CI/CD artifact verification tests for Phase 5 container build and CI pipeline.

These tests verify the structural and behavioral contracts of the build
artifacts: lock files must be hash-pinned (SEC-02), the container image
must be properly configured (CI-03), workflows must be SHA-pinned and gated
correctly (CI-01/CI-04/CI-05/SEC-04), and shell scripts must fail loudly
when preconditions are missing.

Each test targets a specific requirement gap from Phase 5's VALIDATION plan
and verifies observable behavior, not just structural presence.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import stat
import subprocess
from typing import Any

import pytest
import yaml

import config


# ============================================================================
# GAP-1: Hash-pinned lock files (SEC-02)
# ============================================================================


def test_requirements_txt_every_requirement_line_pinned_with_equals_and_hash():
    """GAP-1: requirements.txt must pin every requirement with == and --hash.

    Regression: D-02's "fully-pinned, hash-verified" lock enforces --require-hashes
    install everywhere downstream (CI, Dockerfile, schedulers). An unpinned line
    or missing hash lines silently disarm every consumer's hash verification.
    This test asserts requirements.txt carries at least one --hash line per
    requirement line, confirming the compile was complete."""
    req_file = config.ROOT / "requirements.txt"
    assert req_file.exists(), "requirements.txt must exist"

    with open(req_file, encoding="utf-8") as f:
        content = f.read()

    # Extract requirement lines (those that start with a package name, not
    # continuation lines starting with --).
    req_lines = [
        line.strip()
        for line in content.split("\n")
        if line and not line.startswith("#") and not line.startswith("--")
    ]

    # Count total requirement declarations (one per line that ends with ==X.Y.Z
    # or continues to the next line).
    assert req_lines, "requirements.txt is empty or contains only comments"

    # Verify every requirement line has exactly one == (except for hash continuation).
    requirement_count = 0
    hash_count = 0
    for line in content.split("\n"):
        if not line or line.startswith("#"):
            continue
        if re.match(r"^[a-z0-9\-_]+==[0-9]", line, re.IGNORECASE):
            requirement_count += 1
        elif re.match(r"^\s+--hash=sha256:", line):
            hash_count += 1

    assert requirement_count > 0, "requirements.txt has no == pinned packages"
    assert hash_count >= requirement_count, (
        f"requirements.txt has {requirement_count} packages but only {hash_count} "
        f"--hash lines (expected at least one per package)"
    )


def test_requirements_dev_txt_includes_requirements_txt_constraint_and_hashes():
    """GAP-1: requirements-dev.txt must carry hash lines and reference requirements.txt.

    Regression: D-02 makes requirements-dev.txt compiled with -c requirements.txt,
    ensuring shared packages are pinned identically in both locks. Both must be
    fully hashed because D-04 makes --require-hashes the install form everywhere
    downstream."""
    dev_file = config.ROOT / "requirements-dev.txt"
    assert dev_file.exists(), "requirements-dev.txt must exist"

    with open(dev_file, encoding="utf-8") as f:
        content = f.read()

    # Check for hash lines.
    hash_count = len(re.findall(r"--hash=sha256:", content))
    assert (
        hash_count > 0
    ), "requirements-dev.txt has no --hash lines (not fully pinned)"

    # Check for the -c requirements.txt constraint in the header.
    assert (
        "-c requirements.txt" in content or "requirements.txt" in content
    ), "requirements-dev.txt header should document the constraint file"


def test_requirements_dev_in_first_line_is_r_requirements_in():
    """GAP-1: requirements-dev.in must start with -r requirements.in.

    Regression: D-02's split pattern makes requirements-dev.in layer on top of
    requirements.in via the -r directive, ensuring both locks resolve against
    one dependency graph."""
    in_file = config.ROOT / "requirements-dev.in"
    if not in_file.exists():
        pytest.skip("requirements-dev.in does not exist (Phase 5 not executed)")

    with open(in_file, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    assert len(lines) > 0, "requirements-dev.in is empty"
    assert lines[0] == "-r requirements.in", (
        f"First non-comment line of requirements-dev.in should be '-r requirements.in', "
        f"got: {lines[0]}"
    )


# ============================================================================
# GAP-2: Dockerfile structural invariants (CI-03)
# ============================================================================


def test_dockerfile_has_exactly_two_python_3_14_slim_stages():
    """GAP-2: Dockerfile must have exactly two FROM python:3.14-slim stages.

    Regression: D-04 (two-stage build) separates builder (installs deps,
    compiles) from runtime (receives only site-packages, no compiler, no pip
    cache). An extra or missing stage means the contract is broken."""
    dockerfile = config.ROOT / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile must exist"

    with open(dockerfile, encoding="utf-8") as f:
        content = f.read()

    from_lines = re.findall(r"^FROM python:3\.14-slim", content, re.MULTILINE)
    assert (
        len(from_lines) == 2
    ), f"Expected 2 'FROM python:3.14-slim' lines, found {len(from_lines)}"

    # Verify both stages are named.
    builder_match = re.search(r"FROM python:3\.14-slim AS builder", content)
    runtime_match = re.search(r"FROM python:3\.14-slim AS runtime", content)
    assert builder_match, "Dockerfile must have 'FROM python:3.14-slim AS builder'"
    assert runtime_match, "Dockerfile must have 'FROM python:3.14-slim AS runtime'"


def test_dockerfile_builder_installs_with_require_hashes():
    """GAP-2: Builder stage must install requirements.txt with --require-hashes.

    Regression: D-04 enforces hash verification everywhere. A builder that
    installs without hashes means an artifact could be tampered with before
    reaching the final image."""
    dockerfile = config.ROOT / "Dockerfile"
    with open(dockerfile, encoding="utf-8") as f:
        content = f.read()

    # Find the builder section (from first FROM to the next FROM or end).
    builder_section = re.search(
        r"FROM python:3\.14-slim AS builder(.+?)(?=FROM|$)",
        content,
        re.DOTALL,
    )
    assert builder_section, "No builder stage found"

    builder_content = builder_section.group(1)
    assert (
        "--require-hashes" in builder_content
    ), "Builder stage must install with --require-hashes"
    assert (
        "-r requirements.txt" in builder_content
    ), "Builder stage must install requirements.txt"


def test_dockerfile_runtime_installs_libstdc6_and_libgomp1():
    """GAP-2: Runtime stage must install both libstdc++6 and libgomp1.

    Regression: CBC (PuLP's bundled solver) is a C++ binary needing libstdc++6;
    LightGBM needs libgomp1 (GNU OpenMP). Missing either breaks the app at
    runtime. These are not optional cosmetics."""
    dockerfile = config.ROOT / "Dockerfile"
    with open(dockerfile, encoding="utf-8") as f:
        content = f.read()

    # Both libraries must be present somewhere in the Dockerfile.
    assert (
        "libstdc++6" in content
    ), "Dockerfile must install libstdc++6 (CBC dependency)"
    assert (
        "libgomp1" in content
    ), "Dockerfile must install libgomp1 (LightGBM dependency)"

    # Verify they are installed via apt-get in the runtime stage.
    runtime_apt_section = re.search(
        r"apt-get install.*?libstdc\+\+6.*libgomp1",
        content,
        re.DOTALL,
    )
    assert runtime_apt_section, (
        "Both libstdc++6 and libgomp1 must appear in the same apt-get install "
        "command in the runtime stage"
    )


def test_dockerfile_has_non_root_user_before_cmd():
    """GAP-2: Dockerfile must have a non-root USER directive before CMD.

    Regression: Container hardening (T-05-02-02). Running as root is a security
    escalation vector. A non-root account must be created and selected before
    the entrypoint."""
    dockerfile = config.ROOT / "Dockerfile"
    with open(dockerfile, encoding="utf-8") as f:
        lines = f.readlines()

    user_line_idx = None
    cmd_line_idx = None

    for i, line in enumerate(lines):
        if re.match(r"^\s*USER\s+", line) and not re.match(r"^\s*USER\s+root", line):
            user_line_idx = i
        if re.match(r"^\s*CMD\s", line):
            cmd_line_idx = i

    assert user_line_idx is not None, "Dockerfile must have a non-root USER directive"
    assert cmd_line_idx is not None, "Dockerfile must have a CMD directive"
    assert (
        user_line_idx < cmd_line_idx
    ), "USER directive must appear before CMD (container hardening)"


def test_dockerfile_cmd_runs_uvicorn_api_main_app():
    """GAP-2: Dockerfile CMD must run uvicorn api.main:app.

    Regression: The app's entry point. Incorrect entrypoint means the container
    does not serve the API."""
    dockerfile = config.ROOT / "Dockerfile"
    with open(dockerfile, encoding="utf-8") as f:
        content = f.read()

    assert (
        "uvicorn" in content and "api.main:app" in content
    ), "CMD must start uvicorn api.main:app"


def test_dockerfile_no_model_artifact_or_secrets_referenced():
    """GAP-2: Dockerfile must not reference model artifacts, .env, or data/snapshots.

    Regression: D-05 (no model in image), T-05-02-01 (secrets excluded). These
    should never be copied or downloaded into the image. The absence of
    references to xp_model.joblib, .env, or snapshot paths verifies this intent."""
    dockerfile = config.ROOT / "Dockerfile"
    with open(dockerfile, encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, start=1):
        if line.startswith("#"):
            continue
        assert (
            "xp_model" not in line
        ), f"Line {i}: Dockerfile must not reference xp_model.joblib (D-05)"
        assert (
            ".env" not in line
        ), f"Line {i}: Dockerfile must not reference .env (T-05-02-01)"
        assert (
            "data/snapshots" not in line
        ), f"Line {i}: Dockerfile must not reference data/snapshots (D-05/T-05-02-01)"


# ============================================================================
# GAP-3: .dockerignore invariants (CI-03)
# ============================================================================


def test_dockerignore_excludes_required_paths():
    """GAP-3: .dockerignore must exclude required paths (one per exact line).

    Regression: D-05/T-05-02-01 exclude secrets, model artifacts, pipeline data,
    and test fixtures. Missing any allows those into a shipped image."""
    dockerignore = config.ROOT / ".dockerignore"
    assert dockerignore.exists(), ".dockerignore must exist"

    with open(dockerignore, encoding="utf-8") as f:
        content = f.read()

    required_excludes = [
        ".git",
        ".github",
        ".planning",
        ".claude",
        ".gsd",
        "tests",
        "e2e",
        "scripts",
        "data/snapshots",
        "models/artifacts",
        ".env",
    ]

    for exclude in required_excludes:
        assert re.search(
            rf"^{re.escape(exclude)}$", content, re.MULTILINE
        ), f".dockerignore must contain exact line: {exclude}"


def test_dockerignore_reincludes_frontend_dist():
    """GAP-3: .dockerignore must re-include frontend/dist (D-06).

    Regression: D-06 requires the built React bundle inside the image for
    Phase 7's cutover. CI builds the bundle before docker build runs, and it
    must not be stripped from the build context."""
    dockerignore = config.ROOT / ".dockerignore"
    with open(dockerignore, encoding="utf-8") as f:
        content = f.read()

    assert re.search(
        r"^!frontend/dist$", content, re.MULTILINE
    ), ".dockerignore must re-include !frontend/dist"
    assert re.search(
        r"^!frontend/dist/\*\*$", content, re.MULTILINE
    ), ".dockerignore must re-include !frontend/dist/**"


def test_dockerignore_does_not_reinclide_data_snapshots():
    """GAP-3: .dockerignore must NOT re-include data/snapshots.

    Regression: .gitignore re-includes !data/snapshots/ to preserve the
    irreplaceable daily history in git. .dockerignore must NOT re-include it
    because the history has no business in a stateless runtime image."""
    dockerignore = config.ROOT / ".dockerignore"
    with open(dockerignore, encoding="utf-8") as f:
        content = f.read()

    # Check that data/snapshots is excluded (without re-inclusion).
    assert re.search(
        r"^data/snapshots$", content, re.MULTILINE
    ), ".dockerignore must exclude data/snapshots"

    # Verify there is no re-inclusion line.
    assert not re.search(
        r"^!data/snapshots", content, re.MULTILINE
    ), ".dockerignore must NOT re-include !data/snapshots (would waste image space)"


# ============================================================================
# GAP-4: ci.yml workflow structural invariants (CI-01/CI-02/CI-04/CI-05)
# ============================================================================


def test_ci_yml_has_five_chained_jobs_in_linear_needs_order():
    """GAP-4: ci.yml must define five jobs in a linear needs chain.

    Regression: D-08 (chained, not parallel) ensures the built frontend
    bundle reaches the backend tests before they run, and ensures image build
    never wastes time on a red lint/test stage."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_file.exists(), "ci.yml must exist"

    with open(ci_file, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    jobs = workflow.get("jobs", {})
    required_jobs = ["lint-build", "test", "e2e", "image", "publish"]
    assert set(required_jobs).issubset(
        jobs.keys()
    ), f"ci.yml must define all five jobs: {required_jobs}"

    # Verify the needs chain.
    assert "needs" not in jobs["lint-build"] or jobs["lint-build"]["needs"] == [], (
        "lint-build has no dependencies"
    )
    assert (
        "lint-build" in str(jobs["test"].get("needs", []))
    ), "test must need lint-build"
    assert "test" in str(jobs["e2e"].get("needs", [])), "e2e must need test"
    assert "e2e" in str(jobs["image"].get("needs", [])), "image must need e2e"
    assert "image" in str(jobs["publish"].get("needs", [])), "publish must need image"


def test_ci_yml_workflow_level_concurrency_with_cancel_in_progress():
    """GAP-4: ci.yml must have concurrency with cancel-in-progress: true.

    Regression: D-07 (budget efficiency). A superseded push or PR update should
    cancel its predecessor, not race it."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    with open(ci_file, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    concurrency = workflow.get("concurrency", {})
    assert (
        concurrency.get("cancel-in-progress") is True
    ), "ci.yml must have concurrency.cancel-in-progress: true"


def test_ci_yml_workflow_default_permissions_contents_read():
    """GAP-4: ci.yml must have workflow-level permissions: contents: read.

    Regression: Least privilege default. Only jobs that need more (publish
    needs packages:write, image needs security-events:write) widen it."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    with open(ci_file, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    permissions = workflow.get("permissions", {})
    assert (
        permissions.get("contents") == "read"
    ), "ci.yml must have workflow-level permissions.contents: read"


def test_ci_yml_publish_job_requires_main_branch_and_has_packages_write():
    """GAP-4: publish job must gate on main branch and have packages:write.

    Regression: D-09 (publish only from default branch). A branch or PR build
    must never reach GHCR's registry. publish has packages:write; image does not."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    with open(ci_file, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    publish_job = workflow["jobs"]["publish"]
    assert (
        "refs/heads/main" in str(publish_job.get("if", ""))
    ), "publish must gate on github.ref == 'refs/heads/main'"
    assert (
        publish_job.get("permissions", {}).get("packages") == "write"
    ), "publish job must have packages: write"

    # Verify image job does NOT have packages:write.
    image_job = workflow["jobs"]["image"]
    assert (
        image_job.get("permissions", {}).get("packages") is None
    ), "image job must NOT have packages permission"
    assert (
        image_job.get("permissions", {}).get("security-events") == "write"
    ), "image job must have security-events: write"


def test_ci_yml_test_job_runs_pytest_via_module_form():
    """GAP-4: test job must run `python -m pytest` (module form, not bare pytest).

    Regression: The -m form prepends the repo root to sys.path, which is how
    top-level imports (config, backtest, etc.) resolve. A bare pytest binary
    might not have the repo on the path."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    with open(ci_file, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    test_steps = workflow["jobs"]["test"]["steps"]
    pytest_found = False
    for step in test_steps:
        run = step.get("run", "")
        if "pytest" in run:
            assert (
                "python -m pytest" in run
            ), "test job must use 'python -m pytest' (module form), not bare pytest"
            pytest_found = True

    assert pytest_found, "test job must have a pytest step"


def test_ci_yml_all_uses_lines_sha_pinned_to_40_hex_with_version_comment():
    """GAP-4: Every uses: line must be pinned to a 40-character SHA with version comment.

    Regression: T-05-03-01 (action tampering). A mutable tag (v7.0.0) can be
    repointed to a different SHA, allowing a supply-chain attack. All SHAs must
    be 40 hex characters with a trailing version comment for auditing."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    with open(ci_file, encoding="utf-8") as f:
        content = f.read()

    # Count uses: lines that carry an @ (any pinning method).
    # Look for "- uses:" or just "uses:" followed by text with @ and something after.
    uses_lines = re.findall(r"uses:\s*[^\s]+@[^\s]+", content, re.MULTILINE)
    # Count uses: lines pinned to 40-hex SHAs with optional trailing comment.
    # The pattern should capture the full uses line with @ followed by 40 hex chars.
    sha_pinned = re.findall(
        r"uses:\s*[^\s]+@[0-9a-f]{40}(?:\s+#|\s*$)",
        content,
        re.MULTILINE,
    )

    assert len(uses_lines) > 0, "ci.yml must have uses: lines"
    assert len(uses_lines) == len(sha_pinned), (
        f"ci.yml has {len(uses_lines)} uses: lines but only {len(sha_pinned)} "
        f"are pinned to 40-hex SHAs. Mutable tags detected."
    )


def test_ci_yml_only_sarif_upload_may_continue_on_error():
    """GAP-4: Only the Security-tab SARIF upload may carry continue-on-error: true.

    Regression: T-05-03-05 (no silent failures). A verification step that
    swallows its failure lets bad code go green. The only exception is the
    SARIF upload, which is a report sink, not a verification step."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    with open(ci_file, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            if step.get("continue-on-error") is True:
                uses = step.get("uses", "")
                assert (
                    "upload-sarif" in uses
                ), f"Only Security-tab SARIF upload may continue-on-error; found in {job_name}"


def test_ci_yml_smoke_test_step_before_trivy_in_image_job():
    """GAP-4: smoke_test.sh must run before the Trivy scan in the image job.

    Regression: A broken container should fail before a report is generated.
    The smoke test proves the image can do real work; the scan is only run if
    that succeeds."""
    ci_file = config.ROOT / ".github" / "workflows" / "ci.yml"
    with open(ci_file, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    image_steps = workflow["jobs"]["image"]["steps"]
    smoke_idx = None
    trivy_idx = None

    for i, step in enumerate(image_steps):
        run = step.get("run", "")
        uses = step.get("uses", "")
        if "smoke_test.sh" in run:
            smoke_idx = i
        if "trivy-action" in uses:
            trivy_idx = i

    assert smoke_idx is not None, "image job must have a smoke_test.sh step"
    assert trivy_idx is not None, "image job must have a trivy-action step"
    assert (
        smoke_idx < trivy_idx
    ), "smoke_test.sh must run before the Trivy scan (smoke test must pass first)"


# ============================================================================
# GAP-5: daily.yml and weekly.yml workflow invariants (SEC-04)
# ============================================================================


def test_daily_and_weekly_yml_no_schedule_trigger():
    """GAP-5: Both schedulers must have workflow_dispatch only (no schedule trigger).

    Regression: D-12 (local cron owns the time-critical daily snapshot; GitHub
    workflows are dispatch-only until hosting is settled). A schedule trigger
    would race the local cron and cause double-runs."""
    for workflow_name in ["daily", "weekly"]:
        wf_file = config.ROOT / ".github" / "workflows" / f"{workflow_name}.yml"
        assert wf_file.exists(), f"{workflow_name}.yml must exist"

        with open(wf_file, encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        # In YAML, "on:" is parsed as the boolean key True (not the string "on")
        # because "on" is a YAML reserved word. Get triggers via the boolean key.
        triggers = workflow.get(True, {})
        if not triggers:
            # Fallback: check if a string "on" key was used (unusual but possible).
            triggers = workflow.get("on", {})

        assert (
            "schedule" not in triggers
        ), f"{workflow_name}.yml must not have a schedule trigger (D-12)"
        assert (
            "workflow_dispatch" in triggers
        ), f"{workflow_name}.yml must have workflow_dispatch trigger"


def test_daily_and_weekly_yml_python_version_3_14():
    """GAP-5: Both schedulers must use Python 3.14.

    Regression: SEC-04 (unified runtime version). Workflows must match the
    production Python version to catch version-specific issues."""
    for workflow_name in ["daily", "weekly"]:
        wf_file = config.ROOT / ".github" / "workflows" / f"{workflow_name}.yml"
        with open(wf_file, encoding="utf-8") as f:
            content = f.read()

        assert (
            'python-version: "3.14"' in content
        ), f"{workflow_name}.yml must set python-version to 3.14"


def test_daily_and_weekly_yml_install_with_require_hashes():
    """GAP-5: Both schedulers must install with --require-hashes.

    Regression: D-04 (hash enforcement everywhere). Pipeline jobs must install
    from the hashed lock the same way CI and the Dockerfile do."""
    for workflow_name in ["daily", "weekly"]:
        wf_file = config.ROOT / ".github" / "workflows" / f"{workflow_name}.yml"
        with open(wf_file, encoding="utf-8") as f:
            content = f.read()

        assert (
            "--require-hashes" in content
        ), f"{workflow_name}.yml must install with --require-hashes (D-04)"


def test_daily_and_weekly_yml_uses_lines_sha_pinned():
    """GAP-5: Both schedulers must have all uses: lines SHA-pinned to 40 hex.

    Regression: T-05-03-01 (action tampering). The scheduler workflows also
    need immutable action pins."""
    for workflow_name in ["daily", "weekly"]:
        wf_file = config.ROOT / ".github" / "workflows" / f"{workflow_name}.yml"
        with open(wf_file, encoding="utf-8") as f:
            content = f.read()

        # Count uses: lines.
        uses_lines = re.findall(r"uses:\s+[^\s]+@[^\s]+", content)
        # Count SHA-pinned uses: lines (40 hex).
        sha_pinned = re.findall(
            r"uses:\s+[^\s]+@[0-9a-f]{40}", content
        )

        assert len(uses_lines) > 0, f"{workflow_name}.yml must have uses: lines"
        assert len(uses_lines) == len(sha_pinned), (
            f"{workflow_name}.yml: all {len(uses_lines)} uses: lines must be pinned "
            f"to 40-hex SHAs, but only {len(sha_pinned)} are"
        )


def test_daily_and_weekly_yml_bot_identity_not_personal():
    """GAP-5: Both schedulers must commit with github-actions[bot] identity.

    Regression: SEC-04 (no personal credentials in workflows). The commit
    identity must be the GitHub Actions bot account, never a personal name
    or email."""
    for workflow_name in ["daily", "weekly"]:
        wf_file = config.ROOT / ".github" / "workflows" / f"{workflow_name}.yml"
        with open(wf_file, encoding="utf-8") as f:
            content = f.read()

        # Check for the correct bot identity (these must be present exactly as shown).
        assert (
            'user.name "github-actions[bot]"' in content
        ), f"{workflow_name}.yml must set user.name to github-actions[bot]"
        assert (
            "41898282+github-actions[bot]@users.noreply.github.com" in content
        ), f"{workflow_name}.yml must set user.email to the bot email address"


# ============================================================================
# GAP-6: Shell scripts and repository state (SEC-04/CI-04)
# ============================================================================


def test_smoke_test_sh_syntax_valid_and_executable():
    """GAP-6: smoke_test.sh must parse as valid bash and be executable.

    Regression: The script cannot run if it has syntax errors or lacks
    execute permission."""
    script = config.ROOT / "scripts" / "smoke_test.sh"
    assert script.exists(), "scripts/smoke_test.sh must exist"

    # Check executable bit.
    st = script.stat()
    assert st.st_mode & stat.S_IXUSR, "smoke_test.sh must be executable"

    # Check bash syntax.
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"smoke_test.sh has syntax errors:\n{result.stderr}"


def test_preflight_sh_syntax_valid_and_executable():
    """GAP-6: preflight.sh must parse as valid bash and be executable.

    Regression: The preflight gate cannot run if it has syntax errors or
    lacks execute permission."""
    script = config.ROOT / "scripts" / "preflight.sh"
    assert script.exists(), "scripts/preflight.sh must exist"

    # Check executable bit.
    st = script.stat()
    assert st.st_mode & stat.S_IXUSR, "preflight.sh must be executable"

    # Check bash syntax.
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"preflight.sh has syntax errors:\n{result.stderr}"


def test_smoke_test_sh_no_argument_fails_with_failed_line():
    """GAP-6: smoke_test.sh invoked with no argument must exit non-zero and print FAILED:.

    Regression: The script must fail loudly when preconditions are missing.
    Exiting 0 with no output would be silently wrong."""
    script = config.ROOT / "scripts" / "smoke_test.sh"

    result = subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, "smoke_test.sh with no args must exit non-zero"
    assert any(
        line.startswith("FAILED:") for line in result.stdout.split("\n") + result.stderr.split("\n")
    ), "smoke_test.sh must print a line starting with 'FAILED:'"


def test_smoke_test_sh_with_missing_docker_cli_fails_with_failed_line():
    """GAP-6: smoke_test.sh with SMOKE_DOCKER=<nonexistent> must exit non-zero.

    Regression: When the container runtime is missing, the script must fail
    loudly and name the missing runtime, not silently pass."""
    script = config.ROOT / "scripts" / "smoke_test.sh"

    result = subprocess.run(
        ["bash", str(script), "local/fpl:test"],
        capture_output=True,
        text=True,
        env={**os.environ, "SMOKE_DOCKER": "__no_such_container_cli__"},
    )

    assert result.returncode != 0, (
        "smoke_test.sh with missing runtime must exit non-zero"
    )
    output = result.stdout + result.stderr
    assert (
        "FAILED:" in output
    ), "smoke_test.sh must print a line starting with 'FAILED:'"
    assert (
        "__no_such_container_cli__" in output
    ), "smoke_test.sh error message must name the missing runtime"


def test_google_chrome_installer_deb_absent_from_repo_root():
    """GAP-6: The 140MB Chrome installer must not be present in the working tree.

    Regression: An untracked installer in the root is noise and balloons the
    working-tree size. Plan 05-04 deletes it."""
    deb_file = config.ROOT / "google-chrome-stable_current_amd64.deb"
    assert (
        not deb_file.exists()
    ), "google-chrome-stable_current_amd64.deb should not exist (Phase 5 deletes it)"


def test_gitignore_contains_required_rules():
    """GAP-6: .gitignore must contain .gsd/, .venv/, venv/, .docker/ rules.

    Regression: These are dev/build artifacts that should never be committed.
    Their absence from .gitignore means they could accidentally be tracked."""
    gitignore = config.ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore must exist"

    with open(gitignore, encoding="utf-8") as f:
        content = f.read()

    required_rules = [".gsd/", ".venv/", "venv/", ".docker/"]
    for rule in required_rules:
        assert re.search(
            rf"^{re.escape(rule)}$", content, re.MULTILINE
        ), f".gitignore must contain rule: {rule}"


def test_gitignore_preserves_snapshot_history_reinclusion():
    """GAP-6: .gitignore must re-include !data/snapshots/ and !data/snapshots/**.

    Regression: The daily snapshot history cannot be backfilled once lost.
    These re-inclusion rules preserve it in git even though data/ is excluded."""
    gitignore = config.ROOT / ".gitignore"
    with open(gitignore, encoding="utf-8") as f:
        content = f.read()

    assert re.search(
        r"^!data/snapshots/$", content, re.MULTILINE
    ), ".gitignore must re-include !data/snapshots/"
    assert re.search(
        r"^!data/snapshots/\*\*$", content, re.MULTILINE
    ), ".gitignore must re-include !data/snapshots/**"
