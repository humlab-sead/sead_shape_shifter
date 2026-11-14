import os
import subprocess
from pathlib import Path

import pytest

VERIFIER = Path(__file__).resolve().parents[1] / "scripts" / "verify_promotion_provenance.sh"
PROTECTED_PATHS = "scripts/:src/:backend/:frontend/:ingesters/:tests/:.github/workflows/"


def _run_git(repository: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True, text=True)


@pytest.mark.parametrize(
    ("branch", "staged_path", "blocked"),
    [
        ("dev", "src/example.py", True),
        ("staging", "backend/example.py", True),
        ("main", ".github/workflows/check.yml", True),
        ("dev", "docs/example.md", False),
        ("feature/example", "src/example.py", False),
    ],
)
def test_local_commit_guard_checks_protected_paths_on_protected_branches(
    tmp_path: Path, branch: str, staged_path: str, blocked: bool
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _run_git(repository, "init", "--quiet", "--initial-branch", branch)

    staged_file = repository / staged_path
    staged_file.parent.mkdir(parents=True, exist_ok=True)
    staged_file.write_text("pending change\n", encoding="utf-8")
    _run_git(repository, "add", "--", staged_path)

    environment = os.environ.copy()
    environment["PROTECTED_PATHS"] = PROTECTED_PATHS
    result = subprocess.run(
        ["bash", str(VERIFIER), "--check-local-commit"],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert (result.returncode != 0) is blocked
    if blocked:
        assert staged_path in result.stderr
