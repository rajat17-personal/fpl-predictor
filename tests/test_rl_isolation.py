"""RL lockfile production isolation tests (plan 09-06 D2).

The RL dependency stack (torch, gymnasium, stable-baselines3, sb3-contrib) is
dev-only and must never reach production environments (Dockerfile, CI, cron).
These tests prove that isolation by checking:
1. The literal string 'requirements-rl' appears nowhere in production files
2. Every pip install line only references requirements.txt or requirements-dev.txt
"""
from __future__ import annotations

import re

import pytest

import config


def test_requirements_rl_name_not_in_dockerfile():
    """D-09: requirements-rl string must not appear in Dockerfile."""
    dockerfile = config.ROOT / "Dockerfile"
    content = dockerfile.read_text()
    assert "requirements-rl" not in content, (
        "Dockerfile must not reference 'requirements-rl' even in a comment "
        "(defeat the grep guard per D-09)"
    )


def test_requirements_rl_name_not_in_github_workflows():
    """D-09: requirements-rl string must not appear in any .github/workflows/*.yml."""
    workflows_dir = config.ROOT / ".github" / "workflows"
    if not workflows_dir.exists():
        pytest.skip("No .github/workflows/ directory found")

    for yml_file in workflows_dir.glob("*.yml"):
        content = yml_file.read_text()
        assert "requirements-rl" not in content, (
            f"{yml_file.name}: must not reference 'requirements-rl' "
            "(defeat the grep guard per D-09)"
        )


def test_pip_install_lines_only_reference_main_or_dev_lockfiles():
    """D-09: Every pip install line in Dockerfile/.github/workflows/*.yml
    must reference only requirements.txt or requirements-dev.txt, never
    requirements-rl.txt or any other RL-specific lockfile."""
    files_to_check = []

    # Dockerfile
    dockerfile = config.ROOT / "Dockerfile"
    if dockerfile.exists():
        files_to_check.append(dockerfile)

    # .github/workflows/*.yml
    workflows_dir = config.ROOT / ".github" / "workflows"
    if workflows_dir.exists():
        files_to_check.extend(workflows_dir.glob("*.yml"))

    pip_install_pattern = re.compile(r"pip\s+install\s+.*?(-r\s+(\S+)|(\S+\.txt))", re.IGNORECASE)

    for file_path in files_to_check:
        content = file_path.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            if "pip install" in line.lower():
                # Extract the referenced file(s)
                match = pip_install_pattern.search(line)
                if match:
                    # Check if it references requirements-rl
                    if "requirements-rl" in line:
                        raise AssertionError(
                            f"{file_path.name}:{line_num}: pip install references "
                            "'requirements-rl', which must remain dev-only"
                        )
                    # Extract the lockfile name(s)
                    words = line.split()
                    for i, word in enumerate(words):
                        if word == "-r" and i + 1 < len(words):
                            lockfile = words[i + 1]
                            assert lockfile in ("requirements.txt", "requirements-dev.txt"), (
                                f"{file_path.name}:{line_num}: pip -r references '{lockfile}'; "
                                "only 'requirements.txt' or 'requirements-dev.txt' allowed"
                            )
                        elif word.endswith(".txt") and word not in ("requirements.txt", "requirements-dev.txt"):
                            # Single-file reference like pip install -r requirements-rl.txt
                            if "requirements-rl" in word:
                                raise AssertionError(
                                    f"{file_path.name}:{line_num}: pip install references "
                                    "'{word}', which must remain dev-only"
                                )
