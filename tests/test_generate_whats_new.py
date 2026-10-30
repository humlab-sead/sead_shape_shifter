"""Tests for scripts/generate_whats_new.py."""

import datetime as dt
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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


def make_pull_request(generator: ModuleType, number: int, merged_at: str, body: str = ""):
    return generator.GitHubPullRequest(
        number=number,
        title=f"Change {number}",
        body=body,
        merged_at=dt.datetime.fromisoformat(merged_at.replace("Z", "+00:00")),
        url=f"https://github.com/humlab-sead/sead_shape_shifter/pull/{number}",
    )


def test_release_prs_include_staging_changes_until_the_main_promotion(tmp_path: Path):
    generator = load_generator_module()
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        "# [2.5.0](https://example.test/2.5.0) (2026-10-27)\n\n" "# [2.4.0](https://example.test/2.4.0) (2026-10-26)\n",
        encoding="utf-8",
    )
    context = generator.read_release_context(changelog_path, "2.5.0")
    main_prs = [
        make_pull_request(generator, 10, "2026-10-26T15:00:00Z"),
        make_pull_request(generator, 12, "2026-10-27T17:00:00Z"),
    ]
    staging_prs = [
        make_pull_request(generator, 11, "2026-10-27T16:00:00Z"),
        make_pull_request(generator, 13, "2026-10-27T18:00:00Z"),
    ]

    selected = generator.get_release_pull_requests(context, main_prs, staging_prs)

    assert [pull_request.number for pull_request in selected] == [11, 12]


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
    context = generator.ReleaseContext("2.5.0", dt.date(2026, 10, 27), dt.date(2026, 10, 26))

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
        "## User-facing release note\n\nUsers can preview cached entity columns.\n\n" "## Upgrade notes\n\nNone.\n",
    )
    notes = generator.get_pull_request_notes([pull_request])
    context = generator.ReleaseContext("2.5.0", dt.date(2026, 10, 27), dt.date(2026, 10, 26))

    content = generator.build_heuristic_notes(context, "humlab-sead/sead_shape_shifter", notes, None)

    assert "Users can preview cached entity columns." in content
    assert "No upgrade actions were noted" in content
    assert "add abundance entity mapping" not in content


def test_latest_version_check_uses_version_when_release_dates_match(tmp_path: Path):
    generator = load_generator_module()
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(
        "# [2.5.1](https://example.test/2.5.1) (2026-10-27)\n\n" "# [2.5.0](https://example.test/2.5.0) (2026-10-27)\n",
        encoding="utf-8",
    )

    assert generator.is_latest_changelog_version(changelog_path, "2.5.1")
    assert not generator.is_latest_changelog_version(changelog_path, "2.5.0")
