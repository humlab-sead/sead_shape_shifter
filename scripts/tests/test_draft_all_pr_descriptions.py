from __future__ import annotations

import argparse
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

MODULE_SPEC = spec_from_file_location(
    "draft_all_pr_descriptions",
    Path(__file__).resolve().parents[1] / "draft_all_pr_descriptions.py",
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("Could not load draft_all_pr_descriptions.py")
draft_all = module_from_spec(MODULE_SPEC)
sys.modules["draft_all_pr_descriptions"] = draft_all
MODULE_SPEC.loader.exec_module(draft_all)


def make_args(**overrides: object) -> argparse.Namespace:
    """Return the parsed-argument defaults with the supplied values replaced."""
    defaults: dict[str, object] = {
        "state": "merged",
        "repo": None,
        "force": False,
        "newest_first": False,
        "limit": None,
        "batch_size": 25,
        "model": None,
        "show_all_orphaned": False,
        "no_preflight": False,
        "fail_fast": False,
        "dry_run": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_select_pending_skips_existing_drafts_and_keeps_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    (tmp_path / "PR_2.txt").write_text("title: drafted\ndescription:\n", encoding="utf-8")

    pending, already = draft_all.select_pending([1, 2, 3], force=False, limit=None, newest_first=False)

    assert pending == [1, 3]
    assert already == [2]


def test_select_pending_reverses_order_for_newest_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)

    pending, _ = draft_all.select_pending([1, 2, 3], force=False, limit=None, newest_first=True)

    assert pending == [3, 2, 1]


def test_select_pending_applies_the_limit_after_skipping_existing_drafts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    (tmp_path / "PR_1.txt").write_text("title: drafted\ndescription:\n", encoding="utf-8")

    pending, already = draft_all.select_pending([1, 2, 3, 4], force=False, limit=2, newest_first=False)

    assert pending == [2, 3]
    assert already == [1]


def test_select_pending_force_ignores_existing_drafts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    (tmp_path / "PR_1.txt").write_text("title: drafted\ndescription:\n", encoding="utf-8")

    pending, already = draft_all.select_pending([1, 2], force=True, limit=None, newest_first=False)

    assert pending == [1, 2]
    assert already == []


def test_chunked_splits_into_batches_and_rejects_an_invalid_size() -> None:
    assert draft_all.chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert draft_all.chunked([], 5) == []
    with pytest.raises(ValueError, match="batch-size"):
        draft_all.chunked([1, 2], 0)


def test_build_child_command_always_requests_drafts_with_orphaned_commits() -> None:
    command = draft_all.build_child_command([10, 11], make_args())

    assert command[0] == sys.executable
    assert command[1] == str(draft_all.TARGET_SCRIPT)
    assert command[2:4] == ["10", "11"]
    assert "--draft" in command
    assert "--include-orphaned" in command
    assert "--force" not in command


def test_build_child_command_passes_optional_flags() -> None:
    args = make_args(force=True, show_all_orphaned=True, model="test-model", repo="owner/repo")

    command = draft_all.build_child_command([10], args)

    assert "--force" in command
    assert "--show-all-orphaned" in command
    assert command[command.index("--model") + 1] == "test-model"
    assert command[command.index("--repo") + 1] == "owner/repo"


def test_run_batch_collects_drafted_failed_and_skipped_pull_requests() -> None:
    lines = [
        "Generating draft for PR #10...",
        "Wrote docs/whats-new/PRs/PR_10.txt",
        "Generating draft for PR #11...",
        "Failed PR #11: Generated title is empty.",
        "Generating draft for PR #12...",
        "Skipping PR #12 since it exists: docs/whats-new/PRs/PR_12.txt",
    ]
    script = "".join(f"print({line!r})\n" for line in lines)

    outcome = draft_all.run_batch([sys.executable, "-c", script])

    assert outcome.drafted == [10]
    assert list(outcome.failed) == [11]
    assert "Generated title is empty." in outcome.failed[11]
    assert outcome.skipped == [12]
    assert outcome.exit_code == 0


def test_run_batch_reports_a_failing_child_exit_code() -> None:
    outcome = draft_all.run_batch([sys.executable, "-c", "raise SystemExit(3)"])

    assert outcome.exit_code == 3
    assert outcome.drafted == []


def test_main_dry_run_lists_the_planned_pull_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(draft_all, "list_pull_request_numbers", lambda state, repo, limit: [1, 2, 3])
    monkeypatch.setattr(draft_all, "preflight_configuration", lambda model: pytest.fail("dry run checked the model"))
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py", "--dry-run"])

    assert draft_all.main() == 0
    assert "Would draft: #1, #2, #3" in capsys.readouterr().out


def test_main_stops_when_every_pull_request_is_already_drafted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    (tmp_path / "PR_1.txt").write_text("title: drafted\ndescription:\n", encoding="utf-8")
    monkeypatch.setattr(draft_all, "list_pull_request_numbers", lambda state, repo, limit: [1])
    monkeypatch.setattr(draft_all, "run_batch", lambda command: pytest.fail("nothing should have been drafted"))
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py"])

    assert draft_all.main() == 0
    assert "Nothing to draft" in capsys.readouterr().err


def test_main_stops_when_the_copilot_configuration_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(draft_all, "list_pull_request_numbers", lambda state, repo, limit: [1, 2])

    def missing_configuration(model: str | None) -> str:
        raise ValueError("Missing required Copilot configuration: model")

    monkeypatch.setattr(draft_all, "preflight_configuration", missing_configuration)
    monkeypatch.setattr(draft_all, "run_batch", lambda command: pytest.fail("drafting started without configuration"))
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py"])

    assert draft_all.main() == 2
    logged = capsys.readouterr().err
    assert "Missing required Copilot configuration" in logged
    assert "--no-preflight" in logged


def test_main_runs_batches_and_summarises_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(draft_all, "list_pull_request_numbers", lambda state, repo, limit: [1, 2, 3])
    monkeypatch.setattr(draft_all, "preflight_configuration", lambda model: "test-model")
    batches: list[list[int]] = []

    def fake_run_batch(command: list[str]) -> object:
        numbers = [int(value) for value in command[2 : command.index("--draft")]]
        batches.append(numbers)
        return draft_all.BatchOutcome(drafted=numbers)

    monkeypatch.setattr(draft_all, "run_batch", fake_run_batch)
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py", "--batch-size", "2"])

    assert draft_all.main() == 0
    assert batches == [[1, 2], [3]]
    assert "Summary: 3 drafted, 0 failed, 0 skipped of 3 requested." in capsys.readouterr().err


def test_main_returns_nonzero_and_names_failed_pull_requests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(draft_all, "list_pull_request_numbers", lambda state, repo, limit: [1, 2])
    monkeypatch.setattr(draft_all, "preflight_configuration", lambda model: "test-model")
    monkeypatch.setattr(
        draft_all,
        "run_batch",
        lambda command: draft_all.BatchOutcome(drafted=[1], failed={2: "Failed PR #2: boom"}, exit_code=1),
    )
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py"])

    assert draft_all.main() == 1
    logged = capsys.readouterr().err
    assert "Summary: 1 drafted, 1 failed, 0 skipped of 2 requested." in logged
    assert "Failed pull requests: #2" in logged


def test_main_fail_fast_stops_after_the_first_failing_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(draft_all, "DRAFTS_DIR", tmp_path)
    monkeypatch.setattr(draft_all, "list_pull_request_numbers", lambda state, repo, limit: [1, 2, 3, 4])
    monkeypatch.setattr(draft_all, "preflight_configuration", lambda model: "test-model")
    batches: list[list[int]] = []

    def failing_batch(command: list[str]) -> object:
        numbers = [int(value) for value in command[2 : command.index("--draft")]]
        batches.append(numbers)
        return draft_all.BatchOutcome(failed={numbers[0]: "boom"}, exit_code=1)

    monkeypatch.setattr(draft_all, "run_batch", failing_batch)
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py", "--batch-size", "2", "--fail-fast"])

    assert draft_all.main() == 1
    assert batches == [[1, 2]]
    assert "Stopping after the first batch" in capsys.readouterr().err


def test_main_rejects_an_invalid_limit_or_batch_size(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py", "--limit", "0"])
    assert draft_all.main() == 2
    assert "--limit must be at least 1." in capsys.readouterr().err

    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py", "--batch-size", "0"])
    assert draft_all.main() == 2
    assert "--batch-size must be at least 1." in capsys.readouterr().err


def test_main_reports_an_empty_pull_request_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(draft_all, "list_pull_request_numbers", lambda state, repo, limit: [])
    monkeypatch.setattr(sys, "argv", ["draft_all_pr_descriptions.py"])

    assert draft_all.main() == 0
    assert "No merged pull requests were found." in capsys.readouterr().err
