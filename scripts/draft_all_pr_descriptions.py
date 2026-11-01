#!/usr/bin/env python3
"""Draft PR descriptions for every pull request in the repository.

This script drives `scripts/update_pr_descriptions.py` with `--draft
--include-orphaned` for a whole set of pull requests. It exists because the
target script accepts an explicit pull request list, and a range spec is capped
at 100 entries, so backfilling history needs enumeration and batching.

Existing drafts are left in place unless `--force` is given, so an interrupted
run resumes where it stopped. Generated drafts are never published; review them
and run the target script with `--publish` when ready.

Examples:
    uv run python scripts/draft_all_pr_descriptions.py --dry-run
    uv run python scripts/draft_all_pr_descriptions.py
    uv run python scripts/draft_all_pr_descriptions.py --limit 5 --newest-first
    uv run python scripts/draft_all_pr_descriptions.py --force --state all
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_SCRIPT = Path(__file__).resolve().parent / "update_pr_descriptions.py"
DRAFTS_DIR = REPO_ROOT / "docs" / "whats-new" / "PRs"
DEFAULT_BATCH_SIZE = 25
DEFAULT_PULL_REQUEST_LIMIT = 1000
FAILED_LINE_PATTERN = re.compile(r"^Failed PR #(?P<number>[0-9]+): ")
SKIPPED_LINE_PATTERN = re.compile(r"^Skipping PR #(?P<number>[0-9]+) since ")
WRITTEN_LINE_PATTERN = re.compile(r"^Wrote .*PR_(?P<number>[0-9]+)\.txt$")


@dataclass
class BatchOutcome:
    """Results collected from one target-script invocation."""

    drafted: list[int] = field(default_factory=list)
    failed: dict[int, str] = field(default_factory=dict)
    skipped: list[int] = field(default_factory=list)
    exit_code: int = 0

    def merge(self, other: BatchOutcome) -> None:
        """Fold another outcome into this one."""
        self.drafted.extend(other.drafted)
        self.failed.update(other.failed)
        self.skipped.extend(other.skipped)
        self.exit_code = self.exit_code or other.exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draft pull request descriptions for every pull request, using --include-orphaned.",
        epilog=(
            "Existing drafts are kept unless --force is given. Nothing is published; "
            "review docs/whats-new/PRs/ then run the target script with --publish."
        ),
    )
    parser.add_argument(
        "--state",
        default="merged",
        choices=("merged", "closed", "open", "all"),
        help="Pull request state to enumerate (default: merged)",
    )
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPO form; defaults to the current repository")
    parser.add_argument("--force", action="store_true", help="Redraft pull requests that already have a draft file")
    parser.add_argument("--newest-first", action="store_true", help="Process the highest pull request numbers first")
    parser.add_argument("--limit", type=int, help="Process at most this many pull requests")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Pull requests per target-script invocation (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument("--model", help="Copilot model identifier, passed through to the target script")
    parser.add_argument("--show-all-orphaned", action="store_true", help="List every detected commit instead of filtering housekeeping")
    parser.add_argument(
        "--no-preflight",
        action="store_true",
        help="Skip the Copilot configuration check; useful when every pull request is a promotion",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop after the first batch that reports a failure")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned pull requests without drafting")
    return parser.parse_args()


def run_command(command: list[str], *, require_stdout: bool = True) -> str:
    """Run a command and return its standard output."""
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    except FileNotFoundError as error:
        raise RuntimeError(f"Required command not found: {command[0]}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Command failed ({' '.join(command[:3])}): {detail}")
    if require_stdout and not result.stdout.strip():
        raise RuntimeError(f"Command produced no output ({' '.join(command[:3])})")
    return result.stdout


def list_pull_request_numbers(state: str, repo: str | None, limit: int) -> list[int]:
    """Return pull request numbers for the requested state."""
    command = ["gh", "pr", "list", "--state", state, "--limit", str(limit), "--json", "number"]
    if repo:
        command.extend(["--repo", repo])
    records = json.loads(run_command(command))
    if not isinstance(records, list):
        raise RuntimeError("GitHub CLI returned an invalid pull request list.")
    numbers: list[int] = []
    for record in records:
        number = record.get("number") if isinstance(record, dict) else None
        if isinstance(number, int) and not isinstance(number, bool):
            numbers.append(number)
    return sorted(set(numbers))


def draft_file_path(number: int) -> Path:
    """Return the draft path the target script writes for one pull request."""
    return DRAFTS_DIR / f"PR_{number}.txt"


def display_path(path: Path) -> str:
    """Return a repository-relative path when possible."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def select_pending(numbers: list[int], force: bool, limit: int | None, newest_first: bool) -> tuple[list[int], list[int]]:
    """Split pull request numbers into work to do and work skipped as already drafted."""
    ordered = sorted(numbers, reverse=newest_first)
    if force:
        already_drafted: list[int] = []
        pending = ordered
    else:
        already_drafted = [number for number in ordered if draft_file_path(number).is_file()]
        pending = [number for number in ordered if not draft_file_path(number).is_file()]
    if limit is not None:
        pending = pending[: max(limit, 0)]
    return pending, already_drafted


def load_target_module() -> ModuleType:
    """Load the target script as a module so its configuration check is reused."""
    module_name = "_update_pr_descriptions_for_batch"
    spec = spec_from_file_location(module_name, TARGET_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {TARGET_SCRIPT}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def preflight_configuration(model: str | None) -> str:
    """Return the model the target script will use, or raise with its own message."""
    module = load_target_module()
    selected_model, _ = module.configure_copilot_environment(model)
    return selected_model


def build_child_command(batch: list[int], args: argparse.Namespace) -> list[str]:
    """Build the target-script invocation for one batch."""
    command = [
        sys.executable,
        str(TARGET_SCRIPT),
        *[str(number) for number in batch],
        "--draft",
        "--include-orphaned",
    ]
    if args.force:
        command.append("--force")
    if args.show_all_orphaned:
        command.append("--show-all-orphaned")
    if args.model:
        command.extend(["--model", args.model])
    if args.repo:
        command.extend(["--repo", args.repo])
    return command


def run_batch(command: list[str]) -> BatchOutcome:
    """Run one batch, relaying its output live and collecting per-pull-request results."""
    outcome = BatchOutcome()
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")
        print(line, flush=True)
        failed = FAILED_LINE_PATTERN.match(line)
        if failed:
            outcome.failed[int(failed.group("number"))] = line
            continue
        skipped = SKIPPED_LINE_PATTERN.match(line)
        if skipped:
            outcome.skipped.append(int(skipped.group("number")))
            continue
        written = WRITTEN_LINE_PATTERN.match(line)
        if written:
            outcome.drafted.append(int(written.group("number")))
    process.wait()
    outcome.exit_code = process.returncode
    return outcome


def chunked(numbers: list[int], size: int) -> list[list[int]]:
    """Split numbers into batches of at most `size` entries."""
    if size < 1:
        raise ValueError("--batch-size must be at least 1.")
    return [numbers[index : index + size] for index in range(0, len(numbers), size)]


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        print("--limit must be at least 1.", file=sys.stderr)
        return 2
    if args.batch_size < 1:
        print("--batch-size must be at least 1.", file=sys.stderr)
        return 2

    try:
        numbers = list_pull_request_numbers(args.state, args.repo, DEFAULT_PULL_REQUEST_LIMIT)
    except (RuntimeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    if not numbers:
        print(f"No {args.state} pull requests were found.", file=sys.stderr)
        return 0

    pending, already_drafted = select_pending(numbers, args.force, args.limit, args.newest_first)
    print(
        f"Found {len(numbers)} {args.state} pull request(s): " f"{len(pending)} to draft, {len(already_drafted)} already drafted.",
        file=sys.stderr,
    )
    if not pending:
        print("Nothing to draft. Pass --force to redraft existing files.", file=sys.stderr)
        return 0
    if already_drafted:
        preview = ", ".join(f"#{number}" for number in already_drafted[:10])
        print(f"Keeping existing drafts for {preview}{' ...' if len(already_drafted) > 10 else ''}.", file=sys.stderr)

    if args.dry_run:
        for batch in chunked(pending, args.batch_size):
            print("Would draft: " + ", ".join(f"#{number}" for number in batch))
        print(f"Dry run: {len(pending)} pull request(s) would be drafted.", file=sys.stderr)
        return 0

    if not args.no_preflight:
        try:
            selected_model = preflight_configuration(args.model)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            print("Pass --no-preflight to draft promotions without a model.", file=sys.stderr)
            return 2
        print(f"Drafting with model {selected_model}.", file=sys.stderr)

    batches = chunked(pending, args.batch_size)
    outcome = BatchOutcome()
    for index, batch in enumerate(batches, start=1):
        print(
            f"--- batch {index}/{len(batches)}: {len(batch)} pull request(s), " f"#{batch[0]}..#{batch[-1]} ---",
            file=sys.stderr,
        )
        outcome.merge(run_batch(build_child_command(batch, args)))
        if args.fail_fast and outcome.failed:
            print("Stopping after the first batch that reported a failure.", file=sys.stderr)
            break

    print(
        f"Summary: {len(outcome.drafted)} drafted, {len(outcome.failed)} failed, "
        f"{len(outcome.skipped)} skipped of {len(pending)} requested.",
        file=sys.stderr,
    )
    if outcome.failed:
        print("Failed pull requests: " + ", ".join(f"#{number}" for number in sorted(outcome.failed)), file=sys.stderr)
        print("Re-run without --force to retry only the missing drafts.", file=sys.stderr)
        return 1
    print(f"Review {display_path(DRAFTS_DIR)} then publish with --publish.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
