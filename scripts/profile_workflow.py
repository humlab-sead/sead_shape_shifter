"""Profiling script for the access-database CSV workflow.

Mirrors test_access_database_csv_workflow from tests/process/test_workflow.py.

Usage:
    uv run python scripts/profile_workflow.py              # text report to stdout
    uv run python scripts/profile_workflow.py --svg        # flamegraph via flameprof (pip install flameprof)
    uv run python scripts/profile_workflow.py --out my.prof  # save .prof for snakeviz / py-spy
"""

import asyncio
import cProfile
import io
import os
import pstats
import shutil
import sys
from pathlib import Path

import jpype

from src.loaders.sql_loaders import init_jvm_for_ucanaccess
from src.model import ShapeShiftProject
from src.workflow import workflow


CONFIG_FILE = "./tests/test_data/projects/arbodat/shapeshifter.yml"
OUTPUT_PATH = Path("tmp/arbodat-profile-run")


def setup() -> ShapeShiftProject:
    if not jpype.isJVMStarted():
        init_jvm_for_ucanaccess()
    if OUTPUT_PATH.exists():
        shutil.rmtree(OUTPUT_PATH)
    return ShapeShiftProject.from_file(CONFIG_FILE, env_prefix="SHAPE_SHIFTER", env_file=".env")


async def run_workflow(project: ShapeShiftProject) -> None:
    await workflow(
        project=project,
        target=str(OUTPUT_PATH),
        translate=False,
        target_type="csv",
        drop_foreign_keys=False,
    )


def main() -> None:
    save_path: str | None = None
    emit_svg = False

    args: list[str] = sys.argv[1:]
    if "--svg" in args:
        emit_svg = True
        args.remove("--svg")
    if "--out" in args:
        idx = args.index("--out")
        save_path = args[idx + 1]

    project: ShapeShiftProject = setup()

    profiler = cProfile.Profile()
    profiler.enable()
    asyncio.run(run_workflow(project))
    profiler.disable()

    if save_path:
        profiler.dump_stats(save_path)
        print(f"Profile saved to {save_path}")
        print(f"  View with:  snakeviz {save_path}")
        print(f"           or python -m pstats {save_path}")
        return

    if emit_svg:
        try:
            import flameprof  # type: ignore[import]

            buf = io.BytesIO()
            flameprof.render(profiler.getstats(), buf)
            svg_path = "tmp/profile_flame.svg"
            Path(svg_path).write_bytes(buf.getvalue())
            print(f"Flamegraph written to {svg_path}")
        except ImportError:
            print("flameprof not installed — run: pip install flameprof", file=sys.stderr)
        return

    # Default: cumulative text report
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(50)  # top 50 functions by cumulative time
    print(stream.getvalue())

    # Quick summary of top callers by total time
    print("\n--- Top 20 by total time ---")
    stream2 = io.StringIO()
    stats2 = pstats.Stats(profiler, stream=stream2)
    stats2.strip_dirs()
    stats2.sort_stats("tottime")
    stats2.print_stats(50)
    print(stream2.getvalue())

    assert os.path.exists(OUTPUT_PATH), "Workflow did not produce output — check for errors above"


if __name__ == "__main__":
    main()
