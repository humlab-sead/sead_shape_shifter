"""Profile full data validation for the Arbodat test project.

The script follows the data-validation test: it normalizes the project, then
runs the data validators against the normalized table store.

Usage:
    uv run python scripts/profile_validation.py
    uv run python scripts/profile_validation.py --svg
    uv run python scripts/profile_validation.py --out validation.prof
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import io
import os
import pstats
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import dotenv_values

if TYPE_CHECKING:
    from backend.app.validators.data_validation_orchestrator import DataValidationOrchestrator
    from src.model import ShapeShiftProject
    from src.validators.data_validators import ValidationIssue


REPO_ROOT: Path = Path(__file__).resolve().parents[1]
CONFIG_FILE: Path = REPO_ROOT / "tests/test_data/projects/arbodat/shapeshifter.yml"
PROJECT_NAME: str = "arbodat"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def setup() -> ShapeShiftProject:
    """Load the Arbodat test environment and project configuration."""
    for env_file, override in (("data/test.env", False), ("data/.env", True)):
        for name, value in dotenv_values(REPO_ROOT / env_file).items():
            if value is not None and (override or name not in os.environ):
                os.environ[name] = value

    os.environ.setdefault("SHAPE_SHIFTER_APPLICATION_ROOT", str(REPO_ROOT))

    if not CONFIG_FILE.is_file():
        raise FileNotFoundError(f"Arbodat validation project not found: {CONFIG_FILE}")

    import jpype

    from src.loaders.sql_loaders import init_jvm_for_ucanaccess
    from src.model import ShapeShiftProject

    if not jpype.isJVMStarted():
        init_jvm_for_ucanaccess()

    return ShapeShiftProject.from_file(str(CONFIG_FILE))


async def run_validation(project: ShapeShiftProject) -> tuple[DataValidationOrchestrator, list[ValidationIssue]]:
    """Normalize the Arbodat project and validate its data."""
    from backend.app.validators.data_validation_orchestrator import DataValidationOrchestrator, TableStoreDataFetchStrategy
    from src.normalizer import ShapeShifter

    normalizer = ShapeShifter(project)
    await normalizer.normalize()

    orchestrator = DataValidationOrchestrator(fetch_strategy=TableStoreDataFetchStrategy(table_store=normalizer.table_store))
    issues = await orchestrator.validate_all_entities(core_project=project, project_name=PROJECT_NAME)
    return orchestrator, issues


def print_validation_summary(orchestrator: DataValidationOrchestrator, issues: list[ValidationIssue]) -> None:
    """Print validation status and issue counts without listing issue contents."""
    status = orchestrator.status.value
    issue_counts = Counter(issue.severity for issue in issues)
    is_valid = issue_counts["error"] == 0 and status == "completed"
    print(
        f"Validation: status={status}, valid={is_valid}, "
        f"errors={issue_counts['error']}, warnings={issue_counts['warning']}, info={issue_counts['info']}"
    )
    if orchestrator.status_reason:
        print(f"Status reason: {orchestrator.status_reason}")

    if orchestrator.entity_statuses:
        statuses = Counter(entity.status.value for entity in orchestrator.entity_statuses.values())
        counts = ", ".join(f"{name}={count}" for name, count in sorted(statuses.items()))
        print(f"Entities: {len(orchestrator.entity_statuses)} ({counts})")


def print_profile(profiler: cProfile.Profile) -> None:
    """Print cumulative-time and self-time reports for the profiled validation."""
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(50)
    print("\n--- Top 50 by cumulative time ---")
    print(stream.getvalue())

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats("tottime")
    stats.print_stats(50)
    print("\n--- Top 50 by total time ---")
    print(stream.getvalue())


def save_flamegraph(profiler: cProfile.Profile) -> int:
    """Write a flameprof SVG report and return a nonzero code if flameprof is missing."""
    try:
        import flameprof
    except ImportError:
        print("flameprof is not installed; install it with: uv pip install flameprof", file=sys.stderr)
        return 1

    output_path = REPO_ROOT / "tmp/profile_validation_flame.svg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    flameprof.render(profiler.getstats(), buffer)
    output_path.write_bytes(buffer.getvalue())
    print(f"Flamegraph written to {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile backend data validation for the Arbodat test project.")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--svg", action="store_true", help="Write an SVG flamegraph with flameprof.")
    output_group.add_argument("--out", type=Path, help="Save a .prof file for snakeviz or python -m pstats.")
    args = parser.parse_args()

    project = setup()
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        orchestrator, issues = asyncio.run(run_validation(project))
    finally:
        profiler.disable()

    print_validation_summary(orchestrator, issues)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(str(args.out))
        print(f"Profile saved to {args.out}")
        print(f"  View with: snakeviz {args.out}")
        print(f"         or: python -m pstats {args.out}")
        return 0

    if args.svg:
        return save_flamegraph(profiler)

    print_profile(profiler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
