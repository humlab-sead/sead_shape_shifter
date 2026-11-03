from __future__ import annotations

import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

MODULE_SPEC = spec_from_file_location(
    "create_change_pr",
    Path(__file__).resolve().parents[1] / "create_change_pr.py",
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("Could not load create_change_pr.py")
create_change_pr = module_from_spec(MODULE_SPEC)
sys.modules["create_change_pr"] = create_change_pr
MODULE_SPEC.loader.exec_module(create_change_pr)


def test_commit_subject_line_with_scope() -> None:
    assert create_change_pr.commit_subject_line("chore", "deps", "upgrade dev tooling") == "chore(deps): upgrade dev tooling"


def test_commit_subject_line_without_scope() -> None:
    assert create_change_pr.commit_subject_line("docs", None, "document promotion guard") == "docs: document promotion guard"


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("", "empty"),
        ("Upgrade tooling", "lowercase"),
        ("upgrade tooling.", "period"),
    ],
)
def test_commit_subject_line_rejects_invalid_subjects(subject: str, expected: str) -> None:
    with pytest.raises(create_change_pr.WorkflowError, match=expected):
        create_change_pr.commit_subject_line("chore", None, subject)


def test_commit_subject_line_rejects_long_line() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="limit is 72"):
        create_change_pr.commit_subject_line("chore", "deps", "x" * 80)


def test_validate_subject_line_accepts_a_composed_line() -> None:
    assert create_change_pr.validate_subject_line("feat(workflow): add change pull request script") == (
        "feat(workflow): add change pull request script"
    )


def test_validate_subject_line_accepts_a_breaking_change_marker() -> None:
    assert create_change_pr.validate_subject_line("feat(api)!: change validation response format")


def test_validate_subject_line_rejects_an_unknown_type() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="Unknown commit type"):
        create_change_pr.validate_subject_line("update(workflow): adjust the script")


def test_validate_subject_line_rejects_a_missing_type_prefix() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="not `<type>"):
        create_change_pr.validate_subject_line("add change pull request script")


def test_validate_subject_line_rejects_multiple_lines() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="single line"):
        create_change_pr.validate_subject_line("chore: one\nchore: two")


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("chore(deps): upgrade dev tooling", "chore(deps): upgrade dev tooling"),
        ("Here is the subject:\n\n`chore(deps): upgrade dev tooling`", "chore(deps): upgrade dev tooling"),
        ('"fix(loaders): reject blank entity keys"', "fix(loaders): reject blank entity keys"),
    ],
)
def test_parse_generated_subject_picks_the_commit_line(response: str, expected: str) -> None:
    assert create_change_pr.parse_generated_subject(response) == expected


def test_parse_generated_subject_raises_without_a_commit_line() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="Could not find"):
        create_change_pr.parse_generated_subject("I could not summarise these changes.")


def test_truncate_keeps_short_text() -> None:
    assert create_change_pr.truncate("abc", 10) == "abc"


def test_truncate_marks_a_cut() -> None:
    assert create_change_pr.truncate("x" * 20, 5).endswith("... truncated at 5 characters")


class StubRunner:
    """Return fixed porcelain output so the pending-path helpers can be tested."""

    def __init__(self, output: str) -> None:
        self.output = output

    def read_raw(self, command: list[str]) -> str:  # pylint: disable=unused-argument
        return self.output


def make_plan(files: list[str], output: str) -> create_change_pr.Plan:
    """Return a plan whose pending-file listing is driven by the stub output."""
    return create_change_pr.Plan(
        runner=StubRunner(output),  # type: ignore[arg-type]
        base="dev",
        branch="chore/test",
        message="chore: test",
        subject="chore: test",
        files=files,
    )


def test_ensure_no_new_changes_accepts_an_identical_listing() -> None:
    plan = make_plan(["a.txt"], " M a.txt\0")
    create_change_pr.ensure_no_new_changes(plan)


def test_ensure_no_new_changes_rejects_an_appearing_file() -> None:
    plan = make_plan(["a.txt"], " M a.txt\0?? b.txt\0")
    with pytest.raises(create_change_pr.WorkflowError, match="appeared: b.txt"):
        create_change_pr.ensure_no_new_changes(plan)


def test_ensure_no_new_changes_rejects_a_vanished_file() -> None:
    plan = make_plan(["a.txt", "b.txt"], " M a.txt\0")
    with pytest.raises(create_change_pr.WorkflowError, match="vanished: b.txt"):
        create_change_pr.ensure_no_new_changes(plan)


class RecordingRunner:
    """Record the change commands a plan would run."""

    def __init__(self, pending: str = "") -> None:
        self.pending = pending
        self.commands: list[list[str]] = []

    def read(self, command: list[str]) -> str:
        self.commands.append(["read", *command])
        return self.pending

    def change(self, command: list[str]) -> str:
        self.commands.append(list(command))
        return ""


def test_commit_description_draft_records_the_generated_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    draft = tmp_path / "docs" / "whats-new" / "PRs" / "PR_643.txt"
    draft.parent.mkdir(parents=True)
    draft.write_text("title: t\ndescription:\nbody\n", encoding="utf-8")
    monkeypatch.setattr(create_change_pr, "REPO_ROOT", tmp_path)

    module = types.SimpleNamespace(draft_file_path=lambda number: draft)
    monkeypatch.setattr(create_change_pr, "load_description_module", lambda: module)

    runner = RecordingRunner(pending="?? docs/whats-new/PRs/PR_643.txt")
    plan = create_change_pr.Plan(
        runner=runner,  # type: ignore[arg-type]
        base="dev",
        branch="feat/x",
        message="feat: x",
        subject="feat: x",
    )
    create_change_pr.commit_description_draft(643, plan=plan)

    changes = [command for command in runner.commands if command[0] != "read"]
    assert changes == [
        ["git", "add", "--", "docs/whats-new/PRs/PR_643.txt"],
        ["git", "commit", "-m", "docs(whats-new): record the description for pull request #643"],
        ["git", "push"],
    ]


def test_commit_description_draft_skips_an_unchanged_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    draft = tmp_path / "docs" / "whats-new" / "PRs" / "PR_643.txt"
    draft.parent.mkdir(parents=True)
    draft.write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(create_change_pr, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(create_change_pr, "load_description_module", lambda: types.SimpleNamespace(draft_file_path=lambda number: draft))

    runner = RecordingRunner(pending="")
    plan = create_change_pr.Plan(runner=runner, base="dev", branch="feat/x", message="feat: x", subject="feat: x")  # type: ignore[arg-type]
    create_change_pr.commit_description_draft(643, plan=plan)

    assert [command for command in runner.commands if command[0] != "read"] == []


def test_commit_description_draft_skips_a_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    draft = tmp_path / "docs" / "whats-new" / "PRs" / "PR_999.txt"
    monkeypatch.setattr(create_change_pr, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(create_change_pr, "load_description_module", lambda: types.SimpleNamespace(draft_file_path=lambda number: draft))

    runner = RecordingRunner()
    plan = create_change_pr.Plan(runner=runner, base="dev", branch="feat/x", message="feat: x", subject="feat: x")  # type: ignore[arg-type]
    create_change_pr.commit_description_draft(999, plan=plan)

    assert [command for command in runner.commands if command[0] != "read"] == []


def test_draft_commit_subject_stays_within_the_length_limit() -> None:
    line = create_change_pr.DRAFT_COMMIT_TEMPLATE.format(number=643)
    create_change_pr.validate_subject_line(line)


def test_shorten_subject_keeps_the_prefix_and_fits_the_limit() -> None:
    long_line = "feat(workflow): add script and skill for change pull requests with draft commit"
    shortened = create_change_pr.shorten_subject(long_line)
    assert len(shortened) <= create_change_pr.MAX_SUBJECT_LENGTH
    assert shortened.startswith("feat(workflow): ")
    create_change_pr.validate_subject_line(shortened)


def test_shorten_subject_drops_a_dangling_connector() -> None:
    shortened = create_change_pr.shorten_subject(
        "feat(workflow): add script and skill for change pull requests with draft commit"
    )
    assert not shortened.endswith(" with")


def test_shorten_subject_leaves_a_fitting_line_untouched() -> None:
    line = "chore: keep this line"
    assert create_change_pr.shorten_subject(line) == line


def test_shorten_subject_rejects_roomless_prefix() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="No room to shorten"):
        create_change_pr.shorten_subject("chore(" + "x" * 60 + "): describe the change")


def test_shorten_subject_rejects_a_non_conventional_line() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="not a Conventional Commit"):
        create_change_pr.shorten_subject("just some words that are too long to fit the limit here")


def test_branch_name_for_slugifies_subject() -> None:
    branch = create_change_pr.branch_name_for("chore", "Upgrade dev tooling & adapt formatting")
    assert branch == "chore/upgrade-dev-tooling-adapt-formatting"


def test_branch_name_for_limits_word_count() -> None:
    assert create_change_pr.branch_name_for("fix", "one two three four five six seven") == "fix/one-two-three-four-five-six"


def test_branch_name_for_falls_back_when_subject_has_no_words() -> None:
    assert create_change_pr.branch_name_for("chore", "***") == "chore/change"


def test_render_body_keeps_required_headings_in_order() -> None:
    body = create_change_pr.render_body(
        summary="Upgraded the dev toolchain.",
        files=["uv.lock", "src/loaders/base_loader.py"],
        release_note="None - no user-visible change.",
        upgrade_notes="None - no user action required.",
        validation=["uv run pytest tests/specifications"],
    )
    headings = [line for line in body.splitlines() if line.startswith("## ")]
    assert headings == [
        "## Summary",
        "## User-facing release note",
        "## Upgrade notes",
        "## Validation",
    ]
    assert "- `uv.lock`" in body
    assert "- uv run pytest tests/specifications" in body


def test_render_body_uses_fallbacks_when_evidence_is_missing() -> None:
    body = create_change_pr.render_body(
        summary="Upgraded the dev toolchain.",
        files=[],
        release_note=create_change_pr.FALLBACK_RELEASE_NOTE,
        upgrade_notes=create_change_pr.FALLBACK_UPGRADE_NOTES,
        validation=[],
    )
    assert "- None recorded." in body
    assert f"- {create_change_pr.FALLBACK_VALIDATION}" in body


def test_ensure_specific_paths_rejects_empty_list() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="at least one --path"):
        create_change_pr.ensure_specific_paths([])
@pytest.mark.parametrize("path", [".", "./", "*", ":/"])
def test_ensure_specific_paths_rejects_blanket_paths(path: str) -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="blanket path"):
        create_change_pr.ensure_specific_paths([path])


def test_ensure_specific_paths_accepts_named_paths() -> None:
    create_change_pr.ensure_specific_paths(["uv.lock", "src/loaders"])


def test_resolve_paths_returns_named_paths() -> None:
    assert create_change_pr.resolve_paths(stage_all=False, paths=["uv.lock"]) == ["uv.lock"]


def test_resolve_paths_returns_empty_list_for_all() -> None:
    assert create_change_pr.resolve_paths(stage_all=True, paths=None) == []


def test_resolve_paths_rejects_all_with_a_named_path() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="either --path or --all"):
        create_change_pr.resolve_paths(stage_all=True, paths=["uv.lock"])


def test_resolve_paths_rejects_neither_mode() -> None:
    with pytest.raises(create_change_pr.WorkflowError, match="at least one --path"):
        create_change_pr.resolve_paths(stage_all=False, paths=None)


def test_compose_validation_uses_defaults_when_asked() -> None:
    lines = create_change_pr.compose_validation(defaults=True, custom=None)
    assert lines == [
        "uv run pylint -j 0 src tests backend ingesters: exit 0",
        "pytest: all passed",
    ]


def test_compose_validation_keeps_custom_lines_after_defaults() -> None:
    lines = create_change_pr.compose_validation(defaults=True, custom=["pytest tests/loaders: passed"])
    assert lines[:2] == list(create_change_pr.DEFAULT_VALIDATION_LINES)
    assert lines[2] == "pytest tests/loaders: passed"


def test_compose_validation_uses_only_custom_lines_without_the_flag() -> None:
    assert create_change_pr.compose_validation(defaults=False, custom=["pylint: exit 0"]) == ["pylint: exit 0"]


def test_compose_validation_falls_back_when_nothing_is_given() -> None:
    lines = create_change_pr.compose_validation(defaults=False, custom=None)
    assert lines == [create_change_pr.FALLBACK_VALIDATION]


def test_merge_followup_reports_gh_branch_switch() -> None:
    lines = create_change_pr.merge_followup(base="dev", branch="chore/deps", keep_branch=False)
    assert lines == ["gh switched to dev, pulled with --ff-only, and deleted chore/deps."]


def test_merge_followup_asks_for_switch_when_branch_is_kept() -> None:
    lines = create_change_pr.merge_followup(base="dev", branch="chore/deps", keep_branch=True)
    assert lines[0] == "Still on chore/deps; gh did not switch branches because --keep-branch was used."
    assert lines[1] == "Next: git switch dev && git pull --ff-only"
