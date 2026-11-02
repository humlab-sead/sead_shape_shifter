"""Tests for scripts/generate_whats_new.py."""

import datetime as dt
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_whats_new.py"


def load_generator_module() -> ModuleType:
    module_name = "tests.generate_whats_new_module"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_pull_request(
    generator: ModuleType,
    number: int,
    merged_at: str,
    body: str = "",
    base_ref_name: str = "dev",
    head_ref_name: str = "issue-branch",
    merge_commit_oid: str = "",
):
    return generator.GitHubPullRequest(
        number=number,
        title=f"Change {number}",
        body=body,
        merged_at=dt.datetime.fromisoformat(merged_at.replace("Z", "+00:00")),
        url=f"https://github.com/humlab-sead/sead_shape_shifter/pull/{number}",
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        merge_commit_oid=merge_commit_oid or f"oid-{number}",
    )


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def create_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    run_git(repository, "init", "--quiet")
    run_git(repository, "config", "user.email", "tests@example.test")
    run_git(repository, "config", "user.name", "Tests")
    return repository


def commit(repository: Path, message: str) -> str:
    run_git(repository, "commit", "--quiet", "--allow-empty", "-m", message)
    return run_git(repository, "rev-parse", "HEAD")


def test_release_window_follows_commit_ancestry_not_merge_dates():
    generator = load_generator_module()
    released_earlier = make_pull_request(generator, 10, "2026-10-26T15:00:00Z")
    merged_into_dev_before_the_release = make_pull_request(generator, 11, "2026-10-20T16:00:00Z")
    not_promoted_yet = make_pull_request(generator, 12, "2026-10-27T17:00:00Z")

    selected = generator.get_release_pull_requests(
        [released_earlier, merged_into_dev_before_the_release, not_promoted_yet],
        current_commits={"oid-10", "oid-11"},
        previous_commits={"oid-10"},
    )

    assert [pull_request.number for pull_request in selected] == [11]


def test_release_window_without_a_previous_release_includes_every_reachable_pull_request():
    generator = load_generator_module()
    pull_requests = [
        make_pull_request(generator, 10, "2026-10-26T15:00:00Z"),
        make_pull_request(generator, 11, "2026-10-26T16:00:00Z"),
    ]

    selected = generator.get_release_pull_requests(
        pull_requests,
        current_commits={"oid-10", "oid-11"},
        previous_commits=set(),
    )

    assert [pull_request.number for pull_request in selected] == [10, 11]


def test_pending_release_lists_merged_pull_requests_outside_main_history():
    generator = load_generator_module()
    released = make_pull_request(generator, 10, "2026-10-26T15:00:00Z")
    pending = make_pull_request(generator, 11, "2026-10-27T16:00:00Z")

    selected = generator.get_pending_release_pull_requests(
        [released, pending],
        main_commits={"oid-10"},
        released_numbers={10},
    )

    assert [pull_request.number for pull_request in selected] == [11]


def test_promotion_pull_requests_contribute_no_release_notes():
    generator = load_generator_module()
    promotion = make_pull_request(
        generator,
        20,
        "2026-10-28T19:35:16Z",
        "<!-- promotion-pr -->\n## User-facing release note\n\nPromotes cached value previews.\n",
        base_ref_name="staging",
        head_ref_name="dev",
    )
    feature = make_pull_request(
        generator,
        21,
        "2026-10-28T17:00:00Z",
        "## User-facing release note\n\nUsers can preview cached columns.\n",
    )

    notes = generator.get_pull_request_notes([promotion, feature])

    assert [note.pull_request.number for note in notes] == [21]


def test_default_promotion_routes_are_detected_without_a_marker():
    generator = load_generator_module()
    staging_promotion = make_pull_request(generator, 30, "2026-10-28T19:35:16Z", base_ref_name="staging", head_ref_name="dev")
    release_promotion = make_pull_request(generator, 31, "2026-10-28T20:00:00Z", base_ref_name="main", head_ref_name="staging")
    feature = make_pull_request(generator, 32, "2026-10-28T21:00:00Z", base_ref_name="dev", head_ref_name="issue-12")

    assert staging_promotion.is_promotion
    assert release_promotion.is_promotion
    assert not feature.is_promotion


def test_promotion_pending_entry_lists_the_pull_requests_it_carries():
    generator = load_generator_module()
    promotion = make_pull_request(
        generator,
        40,
        "2026-10-28T19:35:16Z",
        "<!-- promotion-pr -->\n## Included PRs\n\n- #41\n- #42\n\n## User-facing release note\n\n" "None - no user-visible change.\n",
        base_ref_name="staging",
        head_ref_name="dev",
    )
    context = generator.ReleaseContext("2.5.0", dt.date(2026, 10, 27), "2.4.0")

    content = generator.build_heuristic_notes(context, "humlab-sead/sead_shape_shifter", [], [promotion])

    assert "## Pending Release" in content
    assert "- Promotes: #41, #42." in content


def test_release_window_reads_the_previous_release_from_the_changelog(tmp_path: Path):
    generator = load_generator_module()
    repository = create_repository(tmp_path)
    first = commit(repository, "first")
    run_git(repository, "tag", "v1.0.0")
    second = commit(repository, "second")
    run_git(repository, "tag", "v1.1.0")
    third = commit(repository, "third")
    context = generator.ReleaseContext("1.2.0", dt.date(2026, 11, 1), "1.1.0")

    window = generator.resolve_release_window(repository, context)

    assert window.current_ref == "HEAD"
    assert window.previous_ref == "v1.1.0"
    assert window.current_commits == {first, second, third}
    assert window.previous_commits == {first, second}


def test_release_window_prefers_the_existing_release_tag(tmp_path: Path):
    generator = load_generator_module()
    repository = create_repository(tmp_path)
    commit(repository, "first")
    run_git(repository, "tag", "v1.1.0")
    released = commit(repository, "released")
    run_git(repository, "tag", "v1.2.0")
    commit(repository, "unreleased")
    context = generator.ReleaseContext("1.2.0", dt.date(2026, 11, 1), "1.1.0")

    window = generator.resolve_release_window(repository, context)

    assert window.current_ref == "v1.2.0"
    assert released in window.current_commits


def test_release_window_rejects_an_unknown_explicit_ref(tmp_path: Path):
    generator = load_generator_module()
    repository = create_repository(tmp_path)
    commit(repository, "first")
    context = generator.ReleaseContext("1.2.0", dt.date(2026, 11, 1), None)

    with pytest.raises(RuntimeError):
        generator.resolve_release_window(repository, context, current_ref="v9.9.9")


def test_release_window_rejects_an_unknown_previous_tag_instead_of_widening(tmp_path: Path):
    generator = load_generator_module()
    repository = create_repository(tmp_path)
    commit(repository, "first")
    run_git(repository, "tag", "v1.0.0")
    commit(repository, "second")
    context = generator.ReleaseContext("1.2.0", dt.date(2026, 11, 1), "1.0.0")

    with pytest.raises(RuntimeError):
        generator.resolve_release_window(repository, context, previous_tag="v9.9.9")


def test_parse_branch_list_rejects_an_empty_selection():
    generator = load_generator_module()

    assert generator.parse_branch_list("dev, staging ,main") == ["dev", "staging", "main"]
    with pytest.raises(ValueError):
        generator.parse_branch_list(" , ")


def test_extracts_authored_sections_and_ignores_none():
    generator = load_generator_module()
    body = (
        "## Summary\n\nInternal details.\n\n"
        "## User-facing release note\n\nUsers can preview cached entity columns.\n\n"
        "## Upgrade notes\n\nNone - no user action required.\n\n"
        "## Validation\n\nTests passed.\n"
    )

    assert generator.extract_note_section(body, "User-facing release note") == "Users can preview cached entity columns."
    assert generator.extract_note_section(body, "Upgrade notes") == ""


def test_pending_release_keeps_titles_dates_and_authored_notes():
    generator = load_generator_module()
    pending_pr = make_pull_request(
        generator,
        42,
        "2026-10-28T19:35:16Z",
        "## User-facing release note\n\nUsers can preview cached columns.\n\n" "## Upgrade notes\n\nNone - no user action required.\n",
    )
    context = generator.ReleaseContext("2.5.0", dt.date(2026, 10, 27), "2.4.0")

    content = generator.build_heuristic_notes(
        context,
        "humlab-sead/sead_shape_shifter",
        [],
        [pending_pr],
    )

    assert "## Pending Release" in content
    assert "[PR #42](https://github.com/humlab-sead/sead_shape_shifter/pull/42)" in content
    assert "merged 2026-10-28" in content
    assert "Users can preview cached columns." in content
    assert "None - no user action required." not in content


def test_heuristic_release_content_uses_pr_notes_not_changelog_details():
    generator = load_generator_module()
    pull_request = make_pull_request(
        generator,
        7,
        "2026-10-27T16:00:00Z",
        "## User-facing release note\n\nUsers can preview cached entity columns.\n\n## Upgrade notes\n\nNone.\n",
    )
    notes = generator.get_pull_request_notes([pull_request])
    context = generator.ReleaseContext("2.5.0", dt.date(2026, 10, 27), "2.4.0")

    content = generator.build_heuristic_notes(context, "humlab-sead/sead_shape_shifter", notes, None)

    assert "Users can preview cached entity columns." in content
    assert "No upgrade actions were noted" in content
    assert "add abundance entity mapping" not in content


def test_latest_version_check_uses_version_when_release_dates_match(tmp_path: Path):
    generator = load_generator_module()
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        "# [2.5.1](https://example.test/2.5.1) (2026-10-27)\n\n# [2.5.0](https://example.test/2.5.0) (2026-10-27)\n",
        encoding="utf-8",
    )

    assert generator.is_latest_changelog_version(changelog_path, "2.5.1")
    assert not generator.is_latest_changelog_version(changelog_path, "2.5.0")
