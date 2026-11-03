"""Profile normalization for a Shape Shifter project.

The report includes elapsed time for each entity and cProfile summaries for
the complete normalization run. The default project is copy_strucke_MS.

Usage:
    uv run python scripts/profile_normalization.py
    uv run python scripts/profile_normalization.py --out tmp/copy_strucke_MS.prof
    uv run python scripts/profile_normalization.py --project path/to/shapeshifter.yml
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import io
import os
import pstats
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import dotenv_values

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT: Path = Path("data/projects/copy_strucke_MS/shapeshifter.yml")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if TYPE_CHECKING:
    from src.extract import SubsetService
    from src.model import ShapeShiftProject
    from src.normalizer import ShapeShifter


@dataclass(frozen=True)
class EntityTiming:
    entity: str
    elapsed_seconds: float
    row_count: int | None
    column_count: int | None


def load_environment() -> None:
    """Load the repository's normalization environment files."""
    for env_file, override in (("data/test.env", False), ("data/.env", True)):
        for name, value in dotenv_values(REPO_ROOT / env_file).items():
            if value is not None and (override or name not in os.environ):
                os.environ[name] = value

    os.environ.setdefault("SHAPE_SHIFTER_APPLICATION_ROOT", str(REPO_ROOT))


def load_project(project_path: Path) -> ShapeShiftProject:
    """Load the project configuration after setting its environment."""
    load_environment()

    from src.model import ShapeShiftProject

    return ShapeShiftProject.from_file(str(project_path), env_file=str(REPO_ROOT / ".env"))


def create_profiled_normalizer(project: ShapeShiftProject, entity_timings: list[EntityTiming]) -> ShapeShifter:
    """Create a normalizer that records elapsed time and output size per entity."""
    from src.normalizer import ShapeShifter

    class ProfiledShapeShifter(ShapeShifter):
        def __init__(self, project: ShapeShiftProject) -> None:
            super().__init__(project)

        async def _process_entity(self, entity: str, subset_service: SubsetService) -> None:
            started = time.perf_counter()
            try:
                await super()._process_entity(entity, subset_service)
            finally:
                table = self.table_store.get(entity)
                entity_timings.append(
                    EntityTiming(
                        entity=entity,
                        elapsed_seconds=time.perf_counter() - started,
                        row_count=len(table) if table is not None else None,
                        column_count=len(table.columns) if table is not None else None,
                    )
                )

    return ProfiledShapeShifter(project)


def print_entity_timings(entity_timings: list[EntityTiming]) -> None:
    """Print per-entity elapsed time and normalized table sizes."""
    print("\n--- Entity wall time ---")
    for timing in sorted(entity_timings, key=lambda item: item.elapsed_seconds, reverse=True):
        size = (
            f"{timing.row_count} rows x {timing.column_count} columns"
            if timing.row_count is not None and timing.column_count is not None
            else "no output table"
        )
        print(f"{timing.elapsed_seconds:8.3f}s  {timing.entity:<32} {size}")


def print_profile(profiler: cProfile.Profile, limit: int) -> None:
    """Print cumulative-time and self-time reports for the normalization run."""
    print(
        "\nNote: cProfile cumulative times can include time spent awaiting async work. "
        "Use entity wall times for end-to-end comparisons."
    )
    for sort_key, title in (("cumulative", "cumulative time"), ("tottime", "self time")):
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.strip_dirs()
        stats.sort_stats(sort_key)
        stats.print_stats(limit)
        print(f"\n--- Top {limit} by {title} ---")
        print(stream.getvalue())


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile normalization for a Shape Shifter project.")
    parser.add_argument(
        "--project",
        type=Path,
        default=DEFAULT_PROJECT,
        help=f"Project YAML file (default: {DEFAULT_PROJECT})",
    )
    parser.add_argument("--out", type=Path, help="Save cProfile statistics to this .prof file.")
    parser.add_argument("--top", type=int, default=40, help="Number of functions in each cProfile report.")
    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top must be at least 1")

    project_path = args.project if args.project.is_absolute() else REPO_ROOT / args.project
    project_path = project_path.resolve()
    if not project_path.is_file():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    project = load_project(project_path)
    entity_timings: list[EntityTiming] = []
    normalizer = create_profiled_normalizer(project, entity_timings)
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    try:
        asyncio.run(normalizer.normalize())
    finally:
        profiler.disable()
        elapsed = time.perf_counter() - started
        print(f"Normalization elapsed: {elapsed:.3f}s")
        print_entity_timings(entity_timings)

        if args.out:
            profile_path = args.out if args.out.is_absolute() else REPO_ROOT / args.out
            profile_path = profile_path.resolve()
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profiler.dump_stats(str(profile_path))
            print(f"\nProfile saved to {profile_path}")
            print(f"View with: uv run snakeviz {profile_path}")

        print_profile(profiler, args.top)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
