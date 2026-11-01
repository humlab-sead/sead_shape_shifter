from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from subprocess import CompletedProcess

import pytest

MODULE_SPEC = spec_from_file_location(
    "update_pr_descriptions",
    Path(__file__).resolve().parents[1] / "update_pr_descriptions.py",
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("Could not load update_pr_descriptions.py")
update_pr_descriptions = module_from_spec(MODULE_SPEC)
# The module defines dataclasses, which look the module up in sys.modules while building.
sys.modules["update_pr_descriptions"] = update_pr_descriptions
MODULE_SPEC.loader.exec_module(update_pr_descriptions)


VALID_BODY = """## Summary
Changed.

## User-facing release note
None.

## Upgrade notes
None - no user action required.

## Validation
Not verified: validation results unavailable."""


def make_draft(title: str = "Example PR title") -> dict[str, str]:
    return update_pr_descriptions.validate_draft({"title": title, "body": VALID_BODY})


def test_pr_specs_expand_inclusive_ranges_and_remove_duplicates() -> None:
    assert update_pr_descriptions.parse_pr_specs(["620-622", "622", "625"]) == [620, 621, 622, 625]


def test_parse_copilot_response_preserves_multiline_markdown_and_quotes() -> None:
    body = VALID_BODY.replace("Changed.", 'Changed "field" across\nmultiple lines.')
    response = f"Example PR title\n{update_pr_descriptions.COPILOT_BODY_SEPARATOR}\n{body}"

    assert update_pr_descriptions.parse_copilot_response(response) == {"title": "Example PR title", "body": body}


def test_parse_copilot_response_adds_markdown_to_ordered_bare_section_labels() -> None:
    body = VALID_BODY.replace("## ", "")
    response = f"Example PR title\n{update_pr_descriptions.COPILOT_BODY_SEPARATOR}\n{body}"

    assert update_pr_descriptions.parse_copilot_response(response) == make_draft()


@pytest.mark.parametrize("verbose", [False, True])
def test_generate_draft_logs_invalid_response_only_when_verbose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    verbose: bool,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(update_pr_descriptions, "render_context", lambda context: "context")
    monkeypatch.setattr(
        update_pr_descriptions,
        "configure_copilot_environment",
        lambda model: ("test-model", {"COPILOT_PROVIDER_API_KEY": "test-key"}),
    )
    monkeypatch.setattr(update_pr_descriptions, "run_command", lambda *args, **kwargs: "malformed test-key response")

    with pytest.raises(ValueError, match="after the title"):
        update_pr_descriptions.generate_draft({}, None, verbose=verbose)

    logged = capsys.readouterr().err
    if verbose:
        assert "Raw Copilot response:" in logged
        assert "malformed [REDACTED] response" in logged
        assert "test-key" not in logged
    else:
        assert logged == ""


def test_run_command_reports_empty_stdout_and_redacts_provider_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        update_pr_descriptions.subprocess,
        "run",
        lambda command, **kwargs: CompletedProcess(command, 0, stdout="", stderr="provider rejected test-key"),
    )

    with pytest.raises(update_pr_descriptions.CommandError) as error:
        update_pr_descriptions.run_command(
            ["copilot", "-p", "draft"],
            env={"COPILOT_PROVIDER_API_KEY": "test-key"},
            require_stdout=True,
        )

    assert "provider rejected [REDACTED]" in str(error.value)
    assert "test-key" not in str(error.value)


@pytest.mark.parametrize(
    ("requested_model", "expected_model"),
    [(None, "dotenv-model"), ("other-model", "other-model")],
)
def test_generate_draft_uses_configured_model_and_passes_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requested_model: str | None,
    expected_model: str,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(update_pr_descriptions, "render_context", lambda context: "context")
    (tmp_path / ".env").write_text(
        "PR_DESCRIPTION_DEFAULT_MODEL=dotenv-model\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE=openai\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL=http://localhost:9000/v1\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY=dotenv-secret\n",
        encoding="utf-8",
    )
    for key in (
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_MODEL_ID",
        "COPILOT_PROVIDER_WIRE_MODEL",
        "PR_DESCRIPTION_DEFAULT_MODEL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("COPILOT_PROVIDER_API_KEY", "configured-key")
    captured: dict[str, object] = {}

    def fake_run_command(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        require_stdout: bool = False,
    ) -> str:
        captured["command"] = command
        captured["environment"] = env
        captured["working_directory"] = cwd
        captured["require_stdout"] = require_stdout
        draft = make_draft()
        return f"{draft['title']}\n{update_pr_descriptions.COPILOT_BODY_SEPARATOR}\n{draft['body']}"

    monkeypatch.setattr(update_pr_descriptions, "run_command", fake_run_command)

    update_pr_descriptions.generate_draft({}, requested_model)

    command = captured["command"]
    environment = captured["environment"]
    working_directory = captured["working_directory"]
    assert isinstance(command, list)
    assert command[command.index("--model") + 1] == expected_model
    assert command[command.index("--stream") + 1] == "off"
    assert command[command.index("--secret-env-vars") + 1] == "COPILOT_PROVIDER_API_KEY"
    assert captured["require_stdout"] is True
    assert isinstance(environment, dict)
    assert isinstance(working_directory, Path)
    assert working_directory.parent == tmp_path / "tmp"
    assert working_directory.name.startswith("pr-description-")
    assert not working_directory.exists()
    assert environment["COPILOT_PROVIDER_TYPE"] == "openai"
    assert environment["COPILOT_PROVIDER_BASE_URL"] == "http://localhost:9000/v1"
    assert environment["COPILOT_PROVIDER_MODEL_ID"] == expected_model
    assert environment["COPILOT_PROVIDER_WIRE_MODEL"] == expected_model
    assert environment["COPILOT_PROVIDER_API_KEY"] == "configured-key"


def test_configure_copilot_environment_reads_project_dotenv_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "PR_DESCRIPTION_DEFAULT_MODEL=dotenv-model\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE=openai\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL=http://localhost:9000/v1\n"
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY=dotenv-secret\n",
        encoding="utf-8",
    )
    for key in (
        "COPILOT_PROVIDER_MODEL_ID",
        "COPILOT_PROVIDER_WIRE_MODEL",
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_API_KEY",
        "PR_DESCRIPTION_DEFAULT_MODEL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    model, environment = update_pr_descriptions.configure_copilot_environment(None)

    assert model == "dotenv-model"
    assert environment["COPILOT_PROVIDER_MODEL_ID"] == "dotenv-model"
    assert environment["COPILOT_PROVIDER_WIRE_MODEL"] == "dotenv-model"
    assert environment["COPILOT_PROVIDER_TYPE"] == "openai"
    assert environment["COPILOT_PROVIDER_BASE_URL"] == "http://localhost:9000/v1"
    assert environment["COPILOT_PROVIDER_API_KEY"] == "dotenv-secret"
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY" not in environment

    monkeypatch.setenv("PR_DESCRIPTION_DEFAULT_MODEL", "exported-model")
    monkeypatch.setenv("PR_DESCRIPTION_DEFAULT_PROVIDER_KEY", "exported-secret")
    exported_model, exported_environment = update_pr_descriptions.configure_copilot_environment(None)
    assert exported_model == "exported-model"
    assert exported_environment["COPILOT_PROVIDER_API_KEY"] == "exported-secret"


def test_configure_copilot_environment_fails_when_required_values_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "REPO_ROOT", tmp_path)
    for key in (
        "COPILOT_PROVIDER_MODEL_ID",
        "COPILOT_PROVIDER_TYPE",
        "COPILOT_PROVIDER_BASE_URL",
        "COPILOT_PROVIDER_API_KEY",
        "PR_DESCRIPTION_DEFAULT_MODEL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL",
        "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="Missing required Copilot configuration") as error:
        update_pr_descriptions.configure_copilot_environment(None)

    assert "PR_DESCRIPTION_DEFAULT_MODEL" in str(error.value)
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE" in str(error.value)
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL" in str(error.value)
    assert "PR_DESCRIPTION_DEFAULT_PROVIDER_KEY" in str(error.value)


def test_draft_file_format_round_trips_title_and_description() -> None:
    draft = make_draft("Title: with a colon")

    assert update_pr_descriptions.parse_draft_file(update_pr_descriptions.serialize_draft_file(draft)) == draft


def test_draft_mode_writes_files_without_publishing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    monkeypatch.setattr(update_pr_descriptions, "configure_copilot_environment", lambda model: ("test-model", {}))
    monkeypatch.setattr(update_pr_descriptions, "load_pr_context", lambda number, repo: {"metadata": {"number": number}})
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", lambda context, model, *, verbose=False: make_draft())
    monkeypatch.setattr(update_pr_descriptions, "publish_draft", lambda *args: pytest.fail("draft mode published a PR"))
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--draft"])

    assert update_pr_descriptions.main() == 0
    assert update_pr_descriptions.parse_draft_file((tmp_path / "PR_627.txt").read_text(encoding="utf-8")) == make_draft()


def test_existing_draft_is_skipped_before_configuration_or_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(
        update_pr_descriptions,
        "configure_copilot_environment",
        lambda model: pytest.fail("Copilot configuration was checked despite the existing draft"),
    )
    monkeypatch.setattr(update_pr_descriptions, "load_pr_context", lambda *args: pytest.fail("existing PR was queried"))
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", lambda *args: pytest.fail("existing draft was regenerated"))
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(make_draft()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--draft"])

    assert update_pr_descriptions.main() == 0
    assert "Skipping PR #627 since it exists" in capsys.readouterr().err


def test_draft_batch_writes_successes_skips_existing_and_continues_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    monkeypatch.setattr(update_pr_descriptions, "configure_copilot_environment", lambda model: ("test-model", {}))
    existing_draft = make_draft("Keep this existing draft")
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(existing_draft), encoding="utf-8")
    queried: list[int] = []
    verbose_values: list[bool] = []

    def fake_load_pr_context(number: int, _repo: str | None) -> dict[str, dict[str, int]]:
        queried.append(number)
        return {"metadata": {"number": number}}

    def fake_generate_draft(context: dict[str, dict[str, int]], _model: str | None, *, verbose: bool = False) -> dict[str, str]:
        verbose_values.append(verbose)
        number = context["metadata"]["number"]
        if number == 628:
            raise ValueError("invalid Copilot response")
        return make_draft(f"Draft for PR #{number}")

    monkeypatch.setattr(update_pr_descriptions, "load_pr_context", fake_load_pr_context)
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", fake_generate_draft)
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627-629", "--draft"])

    assert update_pr_descriptions.main() == 1

    assert queried == [628, 629]
    assert verbose_values == [False, False]
    assert update_pr_descriptions.parse_draft_file((tmp_path / "PR_627.txt").read_text(encoding="utf-8")) == existing_draft
    assert not (tmp_path / "PR_628.txt").exists()
    assert update_pr_descriptions.parse_draft_file((tmp_path / "PR_629.txt").read_text(encoding="utf-8")) == make_draft("Draft for PR #629")
    errors = capsys.readouterr().err
    assert "Skipping PR #627 since it exists" in errors
    assert "Failed PR #628: invalid Copilot response" in errors


def test_verbose_is_rejected_for_publish_mode(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--publish", "--verbose"])

    assert update_pr_descriptions.main() == 2
    assert "--verbose can only be used with --draft." in capsys.readouterr().err


def test_publish_reads_reviewed_files_without_generating(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    draft = make_draft("Reviewed title")
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(draft), encoding="utf-8")
    published: list[tuple[int, dict[str, str], str | None]] = []
    monkeypatch.setattr(update_pr_descriptions, "publish_draft", lambda number, body, repo: published.append((number, body, repo)))
    monkeypatch.setattr(
        update_pr_descriptions,
        "generate_draft",
        lambda *args: pytest.fail("publish mode regenerated a draft"),
    )
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--publish"])

    assert update_pr_descriptions.main() == 0
    assert published == [(627, draft, None)]


def test_publish_validates_every_file_before_updating_any_pr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    (tmp_path / "PR_627.txt").write_text(update_pr_descriptions.serialize_draft_file(make_draft()), encoding="utf-8")
    published: list[int] = []
    monkeypatch.setattr(update_pr_descriptions, "publish_draft", lambda number, draft, repo: published.append(number))
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627-628", "--publish"])

    assert update_pr_descriptions.main() == 1
    assert published == []


ORPHANED_BODY = (
    VALID_BODY
    + """

## Detected orphaned commits

Commits pushed directly to the base branch after the previous merged pull request. Each
commit below reached the base branch without a pull request of its own.

- `abc1234` fix: direct commit (2026-10-27)"""
)


def make_orphaned(sha: str, committed_at: str = "2026-10-27T10:00:00Z", subject: str = "fix: direct commit"):
    committed = update_pr_descriptions.parse_github_timestamp(committed_at)
    assert committed is not None
    return update_pr_descriptions.OrphanedCommit(sha=sha, committed_at=committed, subject=subject)


def moment(value: str) -> object:
    """Parse a test timestamp for the git-log stand-ins."""
    parsed = update_pr_descriptions.parse_github_timestamp(value)
    assert parsed is not None
    return parsed


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("chore(release): 2.4.0 [skip ci]", "release-version-bump"),
        ("feat(release): add v2.5.0 release notes and update dependencies", "release-note-commit"),
        ("chore: updated graphify graph", "generated-graph"),
        ("fix(frontend): clarify fixed-value column header styling", None),
        ("feat(validation): make results easier to scan", None),
        ("test: separate reconciliation client integration tests", None),
    ],
)
def test_housekeeping_reason_recognises_generated_subjects(subject: str, expected: str | None) -> None:
    assert update_pr_descriptions.housekeeping_reason(subject, ["frontend/src/App.vue"]) == expected


def test_housekeeping_reason_filters_commits_inside_the_generated_graph() -> None:
    paths = ["graphify-out/graph.json", "graphify-out/GRAPH_REPORT.md"]

    assert update_pr_descriptions.housekeeping_reason("chore: refresh graph", paths) == "generated-graph"


def test_housekeeping_reason_filters_a_generated_subject_even_when_it_touches_a_test() -> None:
    # The graphify bot uses this subject consistently, so it stays housekeeping even when the
    # commit also regenerates a test file.
    paths = ["graphify-out/graph.json", "tests/test_generate_whats_new.py"]

    assert update_pr_descriptions.housekeeping_reason("chore: updated graphify graph", paths) == "generated-graph"


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["docs/whats-new/v2.5.0.md"], "docs-only"),
        (["docs/proposals/EXAMPLE/EXAMPLE.md", "docs/proposals/EXAMPLE/PLAN.md"], "docs-only"),
        ([".github/pull_request_template.md"], "contributor-config"),
        ([".vscode/settings.json", "sead_shape_shifter.code-workspace"], "contributor-config"),
        (["frontend/src/components/EntityForm.vue"], None),
        ([".github/workflows/release.yml", "frontend/src/App.vue"], None),
        ([], None),
    ],
)
def test_housekeeping_reason_classifies_by_changed_paths(paths: list[str], expected: str | None) -> None:
    assert update_pr_descriptions.housekeeping_reason("chore: adjust configuration", paths) == expected


def test_paths_within_requires_at_least_one_path_and_a_full_match() -> None:
    paths_within = update_pr_descriptions.paths_within

    assert paths_within([], ["docs/"]) is False
    assert paths_within(["docs/a.md"], ["docs/"]) is True
    assert paths_within(["docs/a.md", "src/a.py"], ["docs/"]) is False
    assert paths_within(["docs"], ["docs/"]) is False
    assert paths_within(["sead_shape_shifter.code-workspace"], ["sead_shape_shifter.code-workspace"]) is True


def test_split_housekeeping_counts_filtered_reasons(monkeypatch: pytest.MonkeyPatch) -> None:
    changed = {
        "keep": ["frontend/src/App.vue"],
        "graph": ["graphify-out/graph.json"],
        "docs": ["docs/whats-new/v2.5.0.md"],
    }
    monkeypatch.setattr(update_pr_descriptions, "commit_changed_paths", lambda sha: changed[sha])
    commits = [
        make_orphaned("keep", subject="fix(frontend): show preview button"),
        make_orphaned("graph", subject="chore: updated graphify graph"),
        make_orphaned("docs", subject="chore: move proposal to done"),
    ]

    listed, excluded = update_pr_descriptions.split_housekeeping(commits)

    assert [commit.sha for commit in listed] == ["keep"]
    assert excluded == {"generated-graph": 1, "docs-only": 1}


def test_render_orphaned_section_is_empty_when_every_commit_is_filtered() -> None:
    assert update_pr_descriptions.render_orphaned_section([], {"release-version-bump": 2}) == ""


def test_render_orphaned_section_summarises_filtered_commits() -> None:
    section = update_pr_descriptions.render_orphaned_section(
        [make_orphaned("abc1234")],
        {"generated-graph": 5, "docs-only": 2},
    )

    assert "`abc1234` fix: direct commit (2026-10-27)" in section
    assert "Filtered 7 housekeeping commit(s): docs-only 2, generated-graph 5." in section


def test_render_orphaned_section_truncates_long_records(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update_pr_descriptions, "ORPHANED_COMMIT_LIMIT", 2)
    commits = [make_orphaned(f"abc{i:04d}") for i in range(5)]

    section = update_pr_descriptions.render_orphaned_section(commits)

    assert section.count("\n- ") == 3
    assert "3 further commit(s) are not listed." in section


def test_replace_orphaned_section_replaces_an_existing_record_instead_of_duplicating_it() -> None:
    replacement = "## Detected orphaned commits\n\n- `def5678` chore: newer commit (2026-10-28)"

    body = update_pr_descriptions.replace_orphaned_section(ORPHANED_BODY, replacement)

    assert body.count("## Detected orphaned commits") == 1
    assert "`def5678`" in body
    assert "`abc1234`" not in body
    assert body.startswith("## Summary")


def test_replace_orphaned_section_removes_the_record_when_none_is_supplied() -> None:
    assert update_pr_descriptions.replace_orphaned_section(ORPHANED_BODY, "") == VALID_BODY


def test_validate_draft_accepts_a_trailing_orphaned_commit_record() -> None:
    draft = update_pr_descriptions.validate_draft({"title": "Example PR title", "body": ORPHANED_BODY})

    assert draft["body"] == ORPHANED_BODY


def test_validate_draft_rejects_an_orphaned_record_before_the_required_sections() -> None:
    body = ORPHANED_BODY.replace(VALID_BODY, "").strip() + "\n\n" + VALID_BODY

    with pytest.raises(ValueError, match="supported heading sets"):
        update_pr_descriptions.validate_draft({"title": "Example PR title", "body": body})


def test_detect_orphaned_commits_windows_between_surrounding_pull_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        update_pr_descriptions,
        "list_merged_pull_requests_into",
        lambda base_ref, repo: [
            {"number": 10, "mergedAt": "2026-10-27T10:00:00Z", "mergeCommit": {"oid": "previous-merge"}},
            {"number": 12, "mergedAt": "2026-10-28T12:00:00Z", "mergeCommit": {"oid": "own-merge"}},
            {"number": 13, "mergedAt": "2026-10-28T09:00:00Z", "mergeCommit": {"oid": "squashed-merge"}},
        ],
    )
    monkeypatch.setattr(
        update_pr_descriptions,
        "list_first_parent_commits",
        lambda base_ref: [
            ("own-merge", moment("2026-10-28T12:00:00Z"), "Merge pull request #12 from x"),
            ("branch-merge-with-pr", moment("2026-10-28T11:30:00Z"), "Merge branch 'y' into dev"),
            ("pr-merge-subject", moment("2026-10-28T11:00:00Z"), "Merge pull request #13 from x"),
            ("direct-two", moment("2026-10-28T10:30:00Z"), "chore: second direct"),
            ("direct-one", moment("2026-10-28T10:00:00Z"), "fix: first direct"),
            ("squashed-merge", moment("2026-10-28T09:00:00Z"), "feat: squashed"),
            ("before-window", moment("2026-10-27T09:00:00Z"), "chore: older"),
        ],
    )
    monkeypatch.setattr(update_pr_descriptions, "resolve_repository_slug", lambda repo: "owner/repo")
    monkeypatch.setattr(
        update_pr_descriptions,
        "is_carried_by_merged_pull_request",
        lambda sha, repository: sha == "branch-merge-with-pr",
    )

    orphaned = update_pr_descriptions.detect_orphaned_commits({"number": 12, "baseRefName": "dev", "mergedAt": "2026-10-28T12:00:00Z"})

    assert [commit.sha for commit in orphaned] == ["direct-one", "direct-two"]


def test_detect_orphaned_commits_identifies_itself_by_merge_commit_without_a_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        update_pr_descriptions,
        "list_merged_pull_requests_into",
        lambda base_ref, repo: [
            {"number": 10, "mergedAt": "2026-10-27T10:00:00Z", "mergeCommit": {"oid": "previous-merge"}},
            {"number": 12, "mergedAt": "2026-10-28T12:00:00Z", "mergeCommit": {"oid": "own-merge"}},
        ],
    )
    monkeypatch.setattr(
        update_pr_descriptions,
        "list_first_parent_commits",
        lambda base_ref: [
            ("own-merge", moment("2026-10-28T12:00:00Z"), "Merge pull request #12 from x"),
            ("direct-one", moment("2026-10-28T10:00:00Z"), "fix: first direct"),
        ],
    )
    monkeypatch.setattr(update_pr_descriptions, "resolve_repository_slug", lambda repo: "owner/repo")
    monkeypatch.setattr(update_pr_descriptions, "is_carried_by_merged_pull_request", lambda sha, repository: False)

    orphaned = update_pr_descriptions.detect_orphaned_commits(
        {"baseRefName": "dev", "mergedAt": "2026-10-28T12:00:00Z", "mergeCommit": {"oid": "own-merge"}}
    )

    assert [commit.sha for commit in orphaned] == ["direct-one"]


def test_detect_orphaned_commits_needs_an_earlier_pull_request_for_a_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        update_pr_descriptions,
        "list_merged_pull_requests_into",
        lambda base_ref, repo: [{"number": 12, "mergedAt": "2026-10-28T12:00:00Z", "mergeCommit": {"oid": "own-merge"}}],
    )
    monkeypatch.setattr(update_pr_descriptions, "list_first_parent_commits", lambda base_ref: pytest.fail("no window"))

    assert update_pr_descriptions.detect_orphaned_commits({"number": 12, "baseRefName": "dev"}) == []


def test_draft_include_orphaned_writes_the_filtered_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    monkeypatch.setattr(update_pr_descriptions, "configure_copilot_environment", lambda model: ("test-model", {}))
    monkeypatch.setattr(
        update_pr_descriptions,
        "load_pr_context",
        lambda number, repo: {"metadata": {"number": number, "baseRefName": "dev"}},
    )
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", lambda *args, **kwargs: make_draft())
    monkeypatch.setattr(
        update_pr_descriptions,
        "detect_orphaned_commits",
        lambda metadata, repo: [
            make_orphaned("keep001", subject="fix(frontend): show preview button"),
            make_orphaned("graph01", subject="chore: updated graphify graph"),
        ],
    )
    changed = {"keep001": ["frontend/src/App.vue"], "graph01": ["graphify-out/graph.json"]}
    monkeypatch.setattr(update_pr_descriptions, "commit_changed_paths", lambda sha: changed[sha])
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "634", "--draft", "--include-orphaned"])

    assert update_pr_descriptions.main() == 0
    written = (tmp_path / "PR_634.txt").read_text(encoding="utf-8")
    assert "`keep001`" in written
    assert "`graph01`" not in written
    assert "Filtered 1 housekeeping commit(s): generated-graph 1." in written
    assert "2 orphaned commit(s) for PR #634: 1 listed, 1 filtered (generated-graph 1)." in capsys.readouterr().err


def test_show_all_orphaned_lists_filtered_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(update_pr_descriptions, "PR_DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(update_pr_descriptions.shutil, "which", lambda _: "/usr/bin/fake")
    monkeypatch.setattr(update_pr_descriptions, "configure_copilot_environment", lambda model: ("test-model", {}))
    monkeypatch.setattr(
        update_pr_descriptions,
        "load_pr_context",
        lambda number, repo: {"metadata": {"number": number, "baseRefName": "dev"}},
    )
    monkeypatch.setattr(update_pr_descriptions, "generate_draft", lambda *args, **kwargs: make_draft())
    monkeypatch.setattr(
        update_pr_descriptions,
        "detect_orphaned_commits",
        lambda metadata, repo: [make_orphaned("graph01", subject="chore: updated graphify graph")],
    )
    monkeypatch.setattr(update_pr_descriptions, "commit_changed_paths", lambda sha: ["graphify-out/graph.json"])
    monkeypatch.setattr(
        sys,
        "argv",
        ["update_pr_descriptions.py", "634", "--draft", "--include-orphaned", "--show-all-orphaned"],
    )

    assert update_pr_descriptions.main() == 0
    written = (tmp_path / "PR_634.txt").read_text(encoding="utf-8")
    assert "`graph01`" in written
    assert "Filtered" not in written


def test_include_orphaned_requires_draft_mode(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--publish", "--include-orphaned"])

    assert update_pr_descriptions.main() == 2
    assert "--include-orphaned can only be used with --draft." in capsys.readouterr().err


def test_show_all_orphaned_requires_include_orphaned(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--draft", "--show-all-orphaned"])

    assert update_pr_descriptions.main() == 2
    assert "--show-all-orphaned requires --include-orphaned." in capsys.readouterr().err


def test_included_pull_requests_use_the_promotions_own_base_not_the_current_branch_tip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later promotion must not hide pull requests carried by an earlier one."""
    merged_into_source = [
        {"number": 626, "title": "Carried by this promotion", "mergedAt": "2026-10-29T17:59:16Z", "mergeCommit": {"oid": "carried"}},
        {"number": 634, "title": "Merged after this promotion", "mergedAt": "2026-11-01T09:54:32Z", "mergeCommit": {"oid": "later"}},
        {"number": 604, "title": "Already in the target", "mergedAt": "2026-10-24T21:31:12Z", "mergeCommit": {"oid": "already"}},
    ]
    monkeypatch.setattr(update_pr_descriptions, "run_command", lambda *args, **kwargs: json.dumps(merged_into_source))
    commits = {
        # The promotion's own base commit already contained the older pull request.
        "base-oid": {"already"},
        # The promotion's merge commit contained only one of the two newer pull requests.
        "promotion-merge": {"already", "carried"},
        # The current target branch now contains everything, including the later pull request.
        "origin/staging": {"already", "carried", "later"},
    }
    monkeypatch.setattr(update_pr_descriptions, "local_commit_set", lambda ref: commits.get(ref))
    metadata = {
        "number": 627,
        "headRefName": "dev",
        "baseRefName": "staging",
        "baseRefOid": "base-oid",
        "mergedAt": "2026-10-29T18:04:35Z",
        "mergeCommit": {"oid": "promotion-merge"},
    }

    included = update_pr_descriptions.list_included_pull_requests(metadata, None)

    assert [record["number"] for record in included] == [626]


def test_promotion_draft_lists_included_pull_requests_and_issue_references() -> None:
    metadata = {"headRefName": "dev", "baseRefName": "staging", "url": "https://github.com/owner/repo/pull/627"}
    included = [
        {"number": 626, "title": "Enhance cached value reference UX", "closingIssuesReferences": [{"number": 612}]},
        {"number": 621, "title": "Simplify route inventory", "closingIssuesReferences": [{"number": 610}]},
    ]

    draft = update_pr_descriptions.build_promotion_draft(metadata, included)

    assert draft["title"] == "chore: promote dev into staging"
    assert draft["body"].startswith(update_pr_descriptions.PROMOTION_MARKER)
    assert "- [#626](https://github.com/owner/repo/pull/626) Enhance cached value reference UX" in draft["body"]
    assert "- [#621](https://github.com/owner/repo/pull/621) Simplify route inventory" in draft["body"]
    assert "Linked issues: #612, #610." in draft["body"]
    assert "## User-facing release note\n\nNone - no user-visible change." in draft["body"]


def test_build_draft_uses_branch_history_for_promotions_without_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        update_pr_descriptions,
        "generate_draft",
        lambda *args, **kwargs: pytest.fail("promotion draft consulted a model"),
    )
    monkeypatch.setattr(
        update_pr_descriptions,
        "list_included_pull_requests",
        lambda metadata, repo: [{"number": 626, "title": "Carried"}],
    )
    context = {"metadata": {"headRefName": "dev", "baseRefName": "staging", "url": "https://github.com/o/r/pull/9"}}

    draft = update_pr_descriptions.build_draft(context, None, repo=None)

    assert "#626" in draft["body"]


def test_included_prs_overrides_detection_for_a_promotion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        update_pr_descriptions,
        "list_included_pull_requests",
        lambda metadata, repo: pytest.fail("detection ran despite --included-prs"),
    )
    context = {"metadata": {"headRefName": "dev", "baseRefName": "staging", "url": "https://github.com/o/r/pull/9"}}

    draft = update_pr_descriptions.build_draft(context, None, included_prs=[621, 626])

    assert "#621" in draft["body"]
    assert "#626" in draft["body"]


def test_promotion_draft_accepts_a_trailing_orphaned_commit_record() -> None:
    metadata = {"headRefName": "dev", "baseRefName": "staging", "url": "https://github.com/owner/repo/pull/627"}
    draft = update_pr_descriptions.build_promotion_draft(metadata, [{"number": 626, "title": "Carried"}])

    with_orphaned = update_pr_descriptions.attach_detected_commits(
        draft,
        {"number": 627},
        None,
        True,
    )

    assert draft["body"] == update_pr_descriptions.replace_orphaned_section(with_orphaned["body"], "")


def test_included_prs_requires_draft_mode(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["update_pr_descriptions.py", "627", "--publish", "--included-prs", "621"])

    assert update_pr_descriptions.main() == 2
    assert "--included-prs can only be used with --draft." in capsys.readouterr().err


PREAMBLE_RESPONSE = (
    """I have reviewed the full diff, metadata, and template. This is a feature PR
(feature-branch -> dev), not a promotion PR, and no CI results are available.

Migrate projects to a folder-based layout
<<<PR_DESCRIPTION_BODY>>>
"""
    + VALID_BODY
)


def test_parse_copilot_response_takes_the_last_line_when_the_model_narrates_first() -> None:
    draft = update_pr_descriptions.parse_copilot_response(PREAMBLE_RESPONSE)

    assert draft["title"] == "Migrate projects to a folder-based layout"


@pytest.mark.parametrize(
    ("preamble", "expected"),
    [
        ("Add a validation check", "Add a validation check"),
        ("Title: Add a validation check", "Add a validation check"),
        ("**Title:** Add a validation check", "Add a validation check"),
        ("## Title: Add a validation check", "Add a validation check"),
        ('"Add a validation check"', "Add a validation check"),
        ("`Add a validation check`", "Add a validation check"),
        ("**Add a validation check**", "Add a validation check"),
        ("Title: **Add a validation check**", "Add a validation check"),
    ],
)
def test_parse_copilot_response_normalises_labels_and_wrapping(preamble: str, expected: str) -> None:
    response = f"{preamble}\n{update_pr_descriptions.COPILOT_BODY_SEPARATOR}\n{VALID_BODY}"

    assert update_pr_descriptions.parse_copilot_response(response)["title"] == expected


def test_parse_copilot_response_reports_a_missing_separator_with_the_length() -> None:
    with pytest.raises(ValueError, match="without the separator"):
        update_pr_descriptions.parse_copilot_response("Only a title and no separator")


def test_parse_copilot_response_keeps_a_title_at_the_length_limit() -> None:
    title = "a" * update_pr_descriptions.TITLE_LENGTH_LIMIT
    response = f"{title}\n{update_pr_descriptions.COPILOT_BODY_SEPARATOR}\n{VALID_BODY}"

    assert update_pr_descriptions.parse_copilot_response(response)["title"] == title


@pytest.mark.parametrize(
    ("case", "title", "expected"),
    [
        ("empty", "", "Generated title is empty."),
        ("multiline", "First line\nSecond line", "spans 2 line(s) instead of one"),
        ("long", "a" * 72, "is 72 characters; the limit is 71"),
        ("period", "Add a validation check.", "ends with a period"),
        ("ok", "Add a validation check", None),
    ],
)
def test_describe_title_problem_names_the_single_failing_condition(case: str, title: str, expected: str | None) -> None:
    problem = update_pr_descriptions.describe_title_problem(title)

    if expected is None:
        assert problem is None
    else:
        assert problem is not None
        assert expected in problem, case


def test_validate_draft_raises_only_the_matching_title_problem() -> None:
    with pytest.raises(ValueError, match="is 72 characters"):
        update_pr_descriptions.validate_draft({"title": "a" * 72, "body": VALID_BODY})

    with pytest.raises(ValueError, match="ends with a period"):
        update_pr_descriptions.validate_draft({"title": "Add a check.", "body": VALID_BODY})


def test_validate_draft_names_unexpected_headings() -> None:
    body = VALID_BODY.replace("## Validation", "## Extra")

    with pytest.raises(ValueError, match="Found: ## Summary, ## User-facing release note, ## Upgrade notes, ## Extra"):
        update_pr_descriptions.validate_draft({"title": "Example PR title", "body": body})


def test_validate_draft_names_headings_without_content() -> None:
    body = VALID_BODY.replace("None - no user action required.", "")

    with pytest.raises(ValueError, match="has no content under: ## Upgrade notes"):
        update_pr_descriptions.validate_draft({"title": "Example PR title", "body": body})
