"""Tests for scripts/ci/check_instruction_references.py.

Each test builds a small Git repository, so the check runs against real files and real ignore rules.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.ci.check_instruction_references import find_broken_references, main


def make_repo(root: Path, files: dict[str, str]) -> Path:
    """Creates a Git repository with the given files and returns its root."""
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def broken(root: Path) -> list[tuple[str, int, str]]:
    return [(item.file, item.line, item.reference) for item in find_broken_references(root)]


def test_reports_backticked_path_that_does_not_exist_with_file_and_line(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"AGENTS.md": "# Guide\n\nTreat `docs/features/` as backlog.\n", "docs/README.md": "x"})

    assert broken(root) == [("AGENTS.md", 3, "docs/features/")]


@pytest.mark.parametrize("text", ["Read `src/model.py`.", "Look in `src/`.", "See `src/model.py:12`.", "Use `src/model.py::Project`."])
def test_accepts_existing_path_from_repository_root(tmp_path: Path, text: str) -> None:
    root = make_repo(tmp_path, {"backend/AGENTS.md": text, "src/model.py": "x"})

    assert not broken(root)


def test_accepts_path_relative_to_the_instruction_file(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {".github/AGENTS.md": "Read `instructions/python.md`.", ".github/instructions/python.md": "x"})

    assert not broken(root)


def test_accepts_shortened_path_that_matches_the_end_of_a_real_path(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {
            "AGENTS.md": "Routers are in `api/v1/endpoints/` and `v1/api.py`.",
            "backend/app/api/v1/endpoints/a.py": "x",
            "backend/app/api/v1/api.py": "x",
        },
    )

    assert not broken(root)


def test_does_not_shorten_a_path_that_starts_with_a_top_level_folder(tmp_path: Path) -> None:
    """`docs/features/` must not pass only because some other folder ends the same way."""
    root = make_repo(tmp_path, {"AGENTS.md": "See `docs/features/`.", "docs/a.md": "x", "frontend/docs/features/b.md": "x"})

    assert broken(root) == [("AGENTS.md", 1, "docs/features/")]


def test_checks_paths_inside_a_backticked_command(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"AGENTS.md": "Run `uv run python scripts/gone.py --check`.", "scripts/here.py": "x"})

    assert broken(root) == [("AGENTS.md", 1, "scripts/gone.py")]


@pytest.mark.parametrize(
    "text",
    [
        "`path/to/file.py::Symbol`",
        "`docs/<topic>/PLAN.md`",
        "`materialized/{entity}.csv`",
        "`docs/proposals/**/*.md`",
        "`/api/v1/projects/`",
        "`~/.cache/graphify-rebuild.log`",
        "`$HOME/.local/bin/tool.sh`",
        "`https://example.org/a/b.html`",
        "`text/plain` and `owner/repo`",
        "`docs/.../file.md`",
    ],
)
def test_ignores_text_that_is_not_a_concrete_repository_path(tmp_path: Path, text: str) -> None:
    root = make_repo(tmp_path, {"AGENTS.md": text, "docs/a.md": "x"})

    assert not broken(root)


def test_ignores_paths_that_git_ignores(tmp_path: Path) -> None:
    """Locally built files are missing in a fresh checkout, so the check must not require them."""
    root = make_repo(tmp_path, {".gitignore": "graphify-out/\n", "AGENTS.md": "See `graphify-out/wiki/index.md` and `graphify-out/`."})

    assert not broken(root)


def test_reports_a_tracked_file_that_was_deleted_from_disk(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"AGENTS.md": "See `docs/a.md`.", "docs/a.md": "x"})
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    (root / "docs/a.md").unlink()

    assert broken(root) == [("AGENTS.md", 1, "docs/a.md")]


def test_ignores_content_inside_fenced_code_blocks_and_keeps_line_numbers(tmp_path: Path) -> None:
    text = "```text\n`docs/example.md` [x](gone.md)\n```\nThen `docs/missing.md`.\n"
    root = make_repo(tmp_path, {"AGENTS.md": text, "docs/a.md": "x"})

    assert broken(root) == [("AGENTS.md", 4, "docs/missing.md")]


def test_reports_broken_markdown_link_relative_to_the_file(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {
            "src/AGENTS.md": "[ok](../AGENTS.md#part) [web](https://example.org/x) [here](#top) [bad](AUTHORIZATION.md)",
            "AGENTS.md": "x",
        },
    )

    assert broken(root) == [("src/AGENTS.md", 1, "AUTHORIZATION.md")]


def test_markdown_link_does_not_fall_back_to_the_repository_root(tmp_path: Path) -> None:
    """A link is followed from the file's own folder, so a root-relative target is broken."""
    root = make_repo(tmp_path, {"src/AGENTS.md": "[docs](docs/a.md)", "docs/a.md": "x"})

    assert broken(root) == [("src/AGENTS.md", 1, "docs/a.md")]


def test_checks_bare_instruction_file_names(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {"AGENTS.md": "Read `real.instructions.md` and `renamed.instructions.md`.", ".github/instructions/real.instructions.md": "x"},
    )

    assert broken(root) == [("AGENTS.md", 1, "renamed.instructions.md")]


@pytest.mark.parametrize(
    "name",
    [
        "AGENTS.md",
        "RTK.md",
        "backend/tests/AGENTS.md",
        ".github/copilot-instructions.md",
        ".github/pr-description-instructions.md",
        ".github/instructions/features/x.instructions.md",
        ".github/agents/x.agent.md",
        ".agents/skills/x/SKILL.md",
        ".clinerules/project.md",
    ],
)
def test_checks_every_kind_of_instruction_file(tmp_path: Path, name: str) -> None:
    root = make_repo(tmp_path, {name: "`nowhere/file.md`"})

    assert broken(root) == [(name, 1, "nowhere/file.md")]


@pytest.mark.parametrize("name", [".claude/rules/x.md", "docs/DESIGN.md", "README.md"])
def test_does_not_check_generated_rules_or_ordinary_documents(tmp_path: Path, name: str) -> None:
    root = make_repo(tmp_path, {name: "`nowhere/file.md`"})

    assert not broken(root)


def test_allows_listed_example_paths_only_in_the_listed_file(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"AGENTS.md": "`made/up.md`", "RTK.md": "`made/up.md`"})

    found = find_broken_references(root, examples={"AGENTS.md": {"made/up.md"}})

    assert [(item.file, item.reference) for item in found] == [("RTK.md", "made/up.md")]


def test_reports_an_example_entry_that_no_longer_matches_anything(tmp_path: Path) -> None:
    """Stops the exception list from keeping entries after the text is gone."""
    root = make_repo(tmp_path, {"AGENTS.md": "No paths here."})

    found = find_broken_references(root, examples={"AGENTS.md": {"made/up.md"}})

    assert [(item.file, item.line, item.reference) for item in found] == [("AGENTS.md", 0, "made/up.md")]


def test_main_exits_1_and_prints_each_broken_reference(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_repo(tmp_path, {"AGENTS.md": "`docs/missing.md`"})

    assert main(["--root", str(root)]) == 1
    assert "AGENTS.md:1: docs/missing.md" in capsys.readouterr().err


def test_main_exits_0_when_all_references_exist(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"AGENTS.md": "`docs/a.md`", "docs/a.md": "x"})

    assert main(["--root", str(root)]) == 0
