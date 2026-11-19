"""Tests for scripts/ci/verify_promotion_provenance.sh range handling.

The release workflow pushes the release commit straight to ``main``, and ``main``
then merges back into ``dev``. A dev to staging promotion must not report those
commits as missing provenance, so the check accepts ``main`` as a second base.
"""

import os
import subprocess
from pathlib import Path

import pytest

VERIFIER = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "verify_promotion_provenance.sh"
PROTECTED_PATHS = "scripts/:src/:backend/:frontend/:ingesters/:tests/:.github/workflows/"
RELEASE_SUBJECT = "chore(release): 1.0.1 [skip ci]"


def _run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(repository: Path, message: str, relative_path: str) -> None:
    """Write one file and commit it with an identity that needs no global git config."""
    changed = repository / relative_path
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text(f"{message}\n", encoding="utf-8")
    _run_git(repository, "add", "--", relative_path)
    _run_git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--quiet",
        "-m",
        message,
    )


def _write_fake_gh(directory: Path) -> None:
    """Write a ``gh`` stub that reports no associated pull requests for any commit."""
    stub = directory / "gh"
    stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)


@pytest.fixture(name="repository")
def repository_fixture(tmp_path: Path) -> Path:
    """Build the branch shape left behind by a release.

    ``main`` carries the release commit, ``staging`` stops before it, and ``dev``
    carries the release commit plus one later documentation commit.
    """
    repository = tmp_path / "repository"
    repository.mkdir()
    _run_git(repository, "init", "--quiet", "--initial-branch", "main")

    _commit(repository, "docs: initial", "docs/README.md")
    _run_git(repository, "branch", "staging")
    _commit(repository, RELEASE_SUBJECT, "backend/app/__init__.py")
    _run_git(repository, "checkout", "--quiet", "-b", "dev")
    _commit(repository, "docs: add proposal", "docs/proposals/example.md")
    return repository


def _verify(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    gh_directory = repository.parent / "bin"
    gh_directory.mkdir(exist_ok=True)
    _write_fake_gh(gh_directory)

    environment = os.environ.copy()
    environment.pop("GITHUB_STEP_SUMMARY", None)
    environment["GITHUB_REPOSITORY"] = "humlab-sead/sead_shape_shifter"
    environment["PROTECTED_PATHS"] = PROTECTED_PATHS
    environment["PATH"] = f"{gh_directory}{os.pathsep}{environment['PATH']}"
    # A developer BASH_ENV file can rewrite PATH and hide the stub; the check must
    # resolve `gh` from the PATH assembled above.
    environment["BASH_ENV"] = ""

    return subprocess.run(
        ["bash", str(VERIFIER), *arguments],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_commit_reachable_from_main_is_outside_the_range(repository: Path) -> None:
    result = _verify(repository, "--base", "staging", "--base", "main", "--head", "dev")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Verified 0 commit(s) touching protected paths" in result.stdout


def test_release_commit_without_main_base_is_reported(repository: Path) -> None:
    result = _verify(repository, "--base", "staging", "--head", "dev")

    assert result.returncode == 1
    assert RELEASE_SUBJECT in result.stdout
    assert "backend/app/__init__.py" in result.stdout


def test_unknown_base_ref_is_a_usage_error(repository: Path) -> None:
    result = _verify(repository, "--base", "staging", "--base", "no-such-branch", "--head", "dev")

    assert result.returncode == 2
    assert "unknown base ref: no-such-branch" in result.stderr
