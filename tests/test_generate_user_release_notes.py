"""Tests for scripts/generate_user_release_notes.py."""

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_user_release_notes.py"


def load_generator_module() -> ModuleType:
    module_name = "tests.generate_user_release_notes_module"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_pull_request(generator: ModuleType, number: int, merged_at: str, title: str = "Example change"):
    return generator.GitHubPullRequest(
        number=number,
        title=title,
        merged_at=dt.datetime.fromisoformat(merged_at.replace("Z", "+00:00")),
        url=f"https://github.com/humlab-sead/sead_shape_shifter/pull/{number}",
    )


class TestPendingReleasePullRequests:
    def test_lists_staging_prs_merged_after_the_latest_main_merge(self, tmp_path: Path, monkeypatch):
        generator = load_generator_module()
        main_prs = [
            make_pull_request(generator, 10, "2026-10-27T17:00:00Z"),
            make_pull_request(generator, 9, "2026-10-25T10:00:00Z"),
        ]
        staging_prs = [
            make_pull_request(generator, 12, "2026-10-29T18:00:00Z"),
            make_pull_request(generator, 10, "2026-10-27T17:00:00Z"),
            make_pull_request(generator, 11, "2026-10-28T10:00:00Z"),
            make_pull_request(generator, 8, "2026-10-27T16:00:00Z"),
        ]

        def list_pull_requests(_repo_root, _github_repository, base_branch):
            return main_prs if base_branch == "main" else staging_prs

        monkeypatch.setattr(generator, "list_merged_pull_requests", list_pull_requests)

        pending = generator.get_pending_release_pull_requests(tmp_path, "humlab-sead/sead_shape_shifter")

        assert [pull_request.number for pull_request in pending] == [11, 12]

    def test_requires_a_merged_main_pr_to_find_the_pending_window(self, tmp_path: Path, monkeypatch):
        generator = load_generator_module()
        monkeypatch.setattr(generator, "list_merged_pull_requests", lambda *_args: [])

        with pytest.raises(RuntimeError, match="No merged pull requests into 'main'"):
            generator.get_pending_release_pull_requests(tmp_path, "humlab-sead/sead_shape_shifter")

    def test_lists_merged_prs_with_gh_and_parses_dates(self, tmp_path: Path, monkeypatch):
        generator = load_generator_module()
        commands: list[list[str]] = []

        def run(command, **_kwargs):
            commands.append(command)
            return SimpleNamespace(
                stdout=json.dumps(
                    [
                        {
                            "number": 42,
                            "title": "Improve validation",
                            "mergedAt": "2026-10-28T19:35:16Z",
                        }
                    ]
                ),
                stderr="",
            )

        monkeypatch.setattr(generator.subprocess, "run", run)

        pull_requests = generator.list_merged_pull_requests(
            tmp_path,
            "humlab-sead/sead_shape_shifter",
            "staging",
        )

        assert len(commands) == 1
        assert commands[0][0:3] == ["gh", "pr", "list"]
        assert commands[0][commands[0].index("--base") + 1] == "staging"
        assert pull_requests[0].number == 42
        assert pull_requests[0].merged_date == "2026-10-28"
        assert pull_requests[0].url.endswith("/pull/42")

    def test_reports_gh_errors(self, tmp_path: Path, monkeypatch):
        generator = load_generator_module()

        def fail(*args, **kwargs):
            raise subprocess.CalledProcessError(1, args[0], stderr="authentication required")

        monkeypatch.setattr(generator.subprocess, "run", fail)

        with pytest.raises(RuntimeError, match="authentication required"):
            generator.list_merged_pull_requests(
                tmp_path,
                "humlab-sead/sead_shape_shifter",
                "main",
            )


class TestPendingReleaseSection:
    def test_only_latest_changelog_version_gets_a_pending_snapshot(self, tmp_path: Path):
        generator = load_generator_module()
        changelog_path = tmp_path / "CHANGELOG.md"
        changelog_path.write_text(
            "# [2.5.0](https://example.test/2.5.0) (2026-10-27)\n\n" "# [2.4.0](https://example.test/2.4.0) (2026-10-26)\n",
            encoding="utf-8",
        )

        assert generator.is_latest_changelog_version(changelog_path, "2.5.0")
        assert not generator.is_latest_changelog_version(changelog_path, "2.4.0")

    def test_renders_pr_links_in_pending_section(self):
        generator = load_generator_module()
        pending_prs = [
            make_pull_request(
                generator,
                42,
                "2026-10-28T19:35:16Z",
                title="Improve **validation** <img src=x>",
            )
        ]

        content = generator.build_release_notes(
            version="2.5.0",
            release_date="2026-10-27",
            github_repository="humlab-sead/sead_shape_shifter",
            highlights=[],
            features=[],
            improvements=[],
            fixes=[],
            pending_release_prs=pending_prs,
        )

        assert "## Pending Release" in content
        assert "[PR #42](https://github.com/humlab-sead/sead_shape_shifter/pull/42)" in content
        assert r"\*\*validation\*\*" in content
        assert "&lt;img src=x&gt;" in content
        assert "merged 2026-10-28" in content

    def test_reports_when_no_prs_are_pending(self):
        generator = load_generator_module()

        content = generator.build_release_notes(
            version="2.5.0",
            release_date="2026-10-27",
            github_repository="humlab-sead/sead_shape_shifter",
            highlights=[],
            features=[],
            improvements=[],
            fixes=[],
            pending_release_prs=[],
        )

        assert "## Pending Release" in content
        assert "No PRs are currently pending release." in content

    def test_omits_pending_section_from_historical_notes(self):
        generator = load_generator_module()

        content = generator.build_release_notes(
            version="2.4.0",
            release_date="2026-10-26",
            github_repository="humlab-sead/sead_shape_shifter",
            highlights=[],
            features=[],
            improvements=[],
            fixes=[],
        )

        assert "## Pending Release" not in content

    def test_restores_generated_section_after_ai_draft(self):
        generator = load_generator_module()
        pending_prs = [make_pull_request(generator, 42, "2026-10-28T19:35:16Z")]
        generated_draft = generator.build_release_notes(
            version="2.5.0",
            release_date="2026-10-27",
            github_repository="humlab-sead/sead_shape_shifter",
            highlights=[],
            features=[],
            improvements=[],
            fixes=[],
            pending_release_prs=pending_prs,
        )
        ai_draft = "# What's New in v2.5.0\n\n## Upgrade Notes\n\n- None.\n\n## Learn More\n\n- Details\n"

        content = generator.preserve_pending_release_section(ai_draft, generated_draft)

        assert content.index("## Pending Release") < content.index("## Learn More")
        assert "[PR #42](https://github.com/humlab-sead/sead_shape_shifter/pull/42)" in content
