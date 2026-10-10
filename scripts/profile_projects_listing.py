"""Profile the backend path behind ``GET /projects`` (issue #508).

The Projects page is slow on its first visit. This script measures the backend
work that produces the project list so the slow part can be identified from
numbers instead of guesses:

    GET /projects
      -> ProjectService.list_authorized_projects()
           -> list_projects()          # rglob + parse every shapeshifter.yml
           -> authorization checks     # one lookup + decision per project

It runs the real service code against a project directory and reports:

* wall time for directory scanning, ``list_projects()``, and the authorization
  loop, repeated so the first (cold) and later (warm) runs can be compared;
* how ``YamlService.load_for_listing()`` spends its time inside
  ``list_projects()``: the raw YAML parse, plus the JSON round-trip that the full
  loader performs but the listing path skips;
* a per-file breakdown so the heaviest project files stand out.

This covers the backend only. If ``GET /projects`` is fast here but the page is
still slow, the remaining time is frontend bundle loading or row rendering.

Usage:
    uv run python scripts/profile_projects_listing.py
    uv run python scripts/profile_projects_listing.py --projects-dir /path/to/projects
    uv run python scripts/profile_projects_listing.py --runs 5
    uv run python scripts/profile_projects_listing.py --cprofile --out listing.prof
    uv run python scripts/profile_projects_listing.py --verify
    uv run python scripts/profile_projects_listing.py --json > listing-508.json

The default project directory is the deployment test data under
``sead-tools/test-shape-shifter.sead.se/container-data/projects``.
"""

from __future__ import annotations

import argparse
import atexit
import cProfile
import io
import json as json_lib
import os
import pstats
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
DEFAULT_PROJECTS_DIR: Path = REPO_ROOT / "sead-tools" / "test-shape-shifter.sead.se" / "container-data" / "projects"


# ---------------------------------------------------------------------------
# Backend import boundary
# ---------------------------------------------------------------------------


def import_backend() -> SimpleNamespace:
    """Import backend modules after the application root is fixed.

    Importing ``backend.app.core.config`` builds ``Settings`` and creates the
    configured directories, so the application root must point at the repository
    before the first backend import. Imports are local to this function so the
    environment is set first and no module-level import runs too early.
    """
    os.environ.setdefault("SHAPE_SHIFTER_APPLICATION_ROOT", str(REPO_ROOT))

    from backend.app.authorization.models import Action, Principal, ResourceType
    from backend.app.authorization.repository import SQLiteAuthorizationRepository
    from backend.app.authorization.service import AuthorizationService
    from backend.app.services import yaml_service as yaml_service_module
    from backend.app.services.project_service import ProjectService
    from backend.app.services.yaml_service import get_yaml_service

    return SimpleNamespace(
        Action=Action,
        Principal=Principal,
        ResourceType=ResourceType,
        SQLiteAuthorizationRepository=SQLiteAuthorizationRepository,
        AuthorizationService=AuthorizationService,
        yaml_service_module=yaml_service_module,
        ProjectService=ProjectService,
        get_yaml_service=get_yaml_service,
    )


def silence_logging() -> None:
    """Remove loguru sinks so the report stays readable.

    The measured ``len(str(data))`` call inside ``YamlService.load`` still runs;
    only log formatting and I/O are skipped.
    """
    from loguru import logger

    logger.remove()


# ---------------------------------------------------------------------------
# Instrumentation
# ---------------------------------------------------------------------------


@dataclass
class JsonTiming:
    """Accumulated time spent in the JSON round-trip inside ``YamlService.load``."""

    dumps: float = 0.0
    loads: float = 0.0


class TimedJson:
    """Stand-in for the ``json`` module that records time spent in dumps/loads.

    ``YamlService.load`` runs ``json.loads(json.dumps(data))`` through the module
    reference in ``backend.app.services.yaml_service``. Swapping that module
    attribute for this proxy times the round-trip without touching production code.
    """

    def __init__(self, real: Any, timing: JsonTiming) -> None:
        self._real = real
        self.timing = timing

    def dumps(self, *args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return self._real.dumps(*args, **kwargs)
        finally:
            self.timing.dumps += time.perf_counter() - start

    def loads(self, *args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return self._real.loads(*args, **kwargs)
        finally:
            self.timing.loads += time.perf_counter() - start


@dataclass
class LoadSample:
    """One ``YamlService.load`` call captured during ``list_projects``."""

    path: Path
    total: float
    raw_parse: float
    json_dumps: float
    json_loads: float
    size_bytes: int
    error: str | None = None


class LoadProfiler:
    """Record per-file time inside the YAML loaders on one service instance.

    Wraps both ``load`` and ``load_for_listing`` for per-file totals, and wraps the
    ruamel and C parser entry points for raw-parse time. A nested call, such as
    ``load_for_listing`` falling back to ``load``, is recorded once at the outermost
    call, and its duration covers both parses.
    """

    def __init__(self, yaml_service: Any, yaml_service_module: Any) -> None:
        self._yaml_service = yaml_service
        self._module = yaml_service_module
        self._real_json = yaml_service_module.json
        self.json_timing = JsonTiming()
        self.raw_parse_seconds = 0.0
        self.samples: list[LoadSample] = []
        self._patches: list[tuple[Any, str, bool, Any]] = []
        self._depth = 0

    def __enter__(self) -> LoadProfiler:
        self._patch(self._module, "json", TimedJson(self._real_json, self.json_timing))

        pyyaml_module = getattr(self._module, "_pyyaml", None)
        if pyyaml_module is not None and hasattr(pyyaml_module, "load"):
            self._patch(pyyaml_module, "load", self._timing_wrapper(pyyaml_module.load))

        self._patch(self._yaml_service.yaml, "load", self._timing_wrapper(self._yaml_service.yaml.load))

        for method_name in ("load", "load_for_listing"):
            original = getattr(self._yaml_service, method_name, None)
            if callable(original):
                self._patch(self._yaml_service, method_name, self._sample_wrapper(original))
        return self

    def __exit__(self, *_exc: object) -> bool:
        for holder, name, had_own, original in reversed(self._patches):
            if had_own:
                setattr(holder, name, original)
            else:
                try:
                    delattr(holder, name)
                except AttributeError:
                    pass
        self._patches.clear()
        return False

    def _patch(self, holder: Any, name: str, value: Any) -> None:
        attributes = getattr(holder, "__dict__", {})
        had_own = name in attributes
        self._patches.append((holder, name, had_own, attributes.get(name)))
        setattr(holder, name, value)

    def _timing_wrapper(self, original: Callable[..., Any]) -> Callable[..., Any]:
        profiler = self

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                profiler.raw_parse_seconds += time.perf_counter() - start

        return wrapper

    def _sample_wrapper(self, original: Callable[..., Any]) -> Callable[..., Any]:
        profiler = self

        def wrapper(filename: Any, *args: Any, **kwargs: Any) -> Any:
            if profiler._depth > 0:  # a nested loader call; the outer sample already covers it
                return original(filename, *args, **kwargs)

            before_dumps = profiler.json_timing.dumps
            before_loads = profiler.json_timing.loads
            before_raw = profiler.raw_parse_seconds

            profiler._depth += 1
            start = time.perf_counter()
            data: Any = None
            error: Exception | None = None
            try:
                data = original(filename, *args, **kwargs)
            except Exception as exc:  # pylint: disable=broad-except
                error = exc
            finally:
                profiler._depth -= 1
            total = time.perf_counter() - start

            path = Path(filename)
            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = 0

            profiler.samples.append(
                LoadSample(
                    path=path,
                    total=total,
                    raw_parse=profiler.raw_parse_seconds - before_raw,
                    json_dumps=profiler.json_timing.dumps - before_dumps,
                    json_loads=profiler.json_timing.loads - before_loads,
                    size_bytes=size_bytes,
                    error=str(error) if error is not None else None,
                )
            )

            if error is not None:
                raise error
            return data

        return wrapper


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Timings for one simulated ``GET /projects`` run."""

    index: int
    service_construct: float
    scan: float
    list_projects: float
    repo_open: float
    auth_loop: float
    authorized_count: int = 0
    samples: list[LoadSample] = field(default_factory=list)
    raw_parse: float = 0.0
    json_dumps: float = 0.0
    json_loads: float = 0.0

    @property
    def cold(self) -> bool:
        return self.index == 0


def measure_scan(projects_dir: Path) -> float:
    """Time a recursive discover of ``shapeshifter.yml`` plus one ``stat`` per file.

    ``list_projects`` finds files with ``rglob`` and calls ``stat`` twice per file
    for the modified/created timestamps. This is a lower-bound estimate of the
    discovery portion of ``list_projects``.
    """
    start = time.perf_counter()
    files = list(projects_dir.rglob("shapeshifter.yml"))
    for path in files:
        path.stat()
    return time.perf_counter() - start


def run_listing(args: argparse.Namespace, backend: SimpleNamespace) -> list[RunResult]:
    """Run the simulated request path ``args.runs`` times and collect timings."""
    projects_dir = Path(args.projects_dir).resolve()
    if not projects_dir.exists():
        raise SystemExit(f"Projects directory not found: {projects_dir}")

    db_dir = Path(tempfile.mkdtemp(prefix="profile-listing-"))
    atexit.register(shutil.rmtree, db_dir, ignore_errors=True)
    db_path = db_dir / "authorization.sqlite3"

    service: Any = None
    results: list[RunResult] = []

    for index in range(max(args.runs, 1)):
        construct = 0.0
        if service is None:
            start = time.perf_counter()
            service = backend.ProjectService(projects_dir=projects_dir)
            construct = time.perf_counter() - start

        scan = measure_scan(projects_dir)

        with LoadProfiler(service.yaml_service, backend.yaml_service_module) as profiler:
            start = time.perf_counter()
            metadata = service.list_projects()
            list_seconds = time.perf_counter() - start
            result = RunResult(
                index=index,
                service_construct=construct,
                scan=scan,
                list_projects=list_seconds,
                repo_open=0.0,
                auth_loop=0.0,
                samples=list(profiler.samples),
                raw_parse=profiler.raw_parse_seconds,
                json_dumps=profiler.json_timing.dumps,
                json_loads=profiler.json_timing.loads,
            )

        # The endpoint's ``get_authorization_repository`` dependency opens a fresh
        # SQLite connection (and runs the schema check) on every request.
        start = time.perf_counter()
        repository = backend.SQLiteAuthorizationRepository(db_path)
        result.repo_open = time.perf_counter() - start
        try:
            authorization_service = backend.AuthorizationService(repository)
            principal = backend.Principal(
                principal_id="profile-listing",
                authentication_provider="profiler",
                authenticated_at=datetime.now(UTC),
            )
            if index == 0:
                # Production has these resource rows already. Create one owner grant
                # per project so ``is_allowed`` takes the full grant-lookup path
                # instead of the administrator short-circuit.
                for item in metadata:
                    authorization_service.register_project(principal, item.name)

            # Mirror ProjectService.list_authorized_projects() over the metadata we
            # already parsed, so this timing isolates the authorization work.
            start = time.perf_counter()
            authorized = [
                item
                for item in metadata
                if (resource := repository.get_resource_by_locator(backend.ResourceType.PROJECT, item.name)) is not None
                and authorization_service.is_allowed(principal, backend.Action.READ, resource)
            ]
            result.auth_loop = time.perf_counter() - start
            result.authorized_count = len(authorized)
        finally:
            repository.close()

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def milliseconds(seconds: float) -> float:
    """Return ``seconds`` in milliseconds."""
    return seconds * 1000.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def render_report(results: list[RunResult], projects_dir: Path, top: int) -> str:
    """Build the human-readable profiling report."""
    cold = results[0]
    warm = results[1:]
    lines: list[str] = []

    lines.append("Shape Shifter — GET /projects listing profiler (issue #508)")
    lines.append("=" * 70)
    lines.append(f"Projects dir          : {projects_dir}")
    lines.append(f"shapeshifter.yml files: {len(cold.samples)}")
    lines.append(f"Total YAML bytes      : {sum(sample.size_bytes for sample in cold.samples):,}")
    lines.append(f"Python                : {sys.version.split()[0]}  platform={sys.platform}")
    lines.append(f"Runs                  : {len(results)} (run 1 cold, rest warm)")
    lines.append("")

    lines.append("Phase timings (ms)")
    lines.append(f"{'phase':<26}{'cold':>10}{'warm mean':>12}{'warm min':>10}{'warm max':>10}")
    lines.append("-" * 70)

    phases: list[tuple[str, Callable[[RunResult], float], bool]] = [
        ("service construct", lambda r: r.service_construct, False),
        ("scan (rglob + stat)", lambda r: r.scan, True),
        ("list_projects()", lambda r: r.list_projects, True),
        ("auth repo open", lambda r: r.repo_open, True),
        ("auth loop", lambda r: r.auth_loop, True),
    ]
    for label, getter, _ in phases:
        cold_ms = milliseconds(getter(cold))
        warm_values = [milliseconds(getter(r)) for r in warm]
        if warm_values:
            warm_mean = _mean(warm_values)
            warm_min = min(warm_values)
            warm_max = max(warm_values)
            lines.append(f"{label:<26}{cold_ms:>10.1f}{warm_mean:>12.1f}{warm_min:>10.1f}{warm_max:>10.1f}")
        else:
            lines.append(f"{label:<26}{cold_ms:>10.1f}{'-':>12}{'-':>10}{'-':>10}")
    lines.append("")

    # Attribution of list_projects() from the cold run.
    total = cold.list_projects
    scan = cold.scan
    residual = total - (scan + cold.raw_parse + cold.json_dumps + cold.json_loads)
    attribution = [
        ("scan (rglob + stat)", scan),
        ("yaml raw parse", cold.raw_parse),
        ("json.dumps (round-trip)", cold.json_dumps),
        ("json.loads (round-trip)", cold.json_loads),
        ("residual (read, metadata, log)", residual),
    ]
    lines.append("Attribution of list_projects() — cold run")
    lines.append(f"{'part':<34}{'ms':>10}{'%':>8}")
    lines.append("-" * 52)
    for label, value in attribution:
        share = (value / total * 100.0) if total else 0.0
        lines.append(f"{label:<34}{milliseconds(value):>10.1f}{share:>7.1f}%")
    lines.append(f"{'TOTAL list_projects()':<34}{milliseconds(total):>10.1f}{100.0:>7.1f}%")
    lines.append("")

    lines.append(f"Per-file load breakdown — cold run (top {min(top, len(cold.samples))})")
    header = f"{'total ms':>9}{'raw ms':>8}{'dumps ms':>9}{'loads ms':>9}{'KB':>8}  file"
    lines.append(header)
    lines.append("-" * len(header))
    for sample in sorted(cold.samples, key=lambda s: s.total, reverse=True)[:top]:
        try:
            label = str(sample.path.relative_to(projects_dir))
        except ValueError:
            label = str(sample.path)
        lines.append(
            f"{milliseconds(sample.total):>9.1f}"
            f"{milliseconds(sample.raw_parse):>8.1f}"
            f"{milliseconds(sample.json_dumps):>9.1f}"
            f"{milliseconds(sample.json_loads):>9.1f}"
            f"{sample.size_bytes / 1024.0:>8.1f}  {label}"
        )
    lines.append("")

    lines.append("Interpretation hints (issue #508)")
    lines.append("- list_projects() parses every shapeshifter.yml on every call. Most of the time is")
    lines.append("  the raw YAML parse; the JSON round-trip stays near zero on the listing path.")
    lines.append("- A large cold/warm gap means the operating system file cache explains part of the")
    lines.append("  first-visit delay (this script cannot drop the cache without root).")
    lines.append("- A small auth repo open + auth loop means authorization is not the bottleneck.")
    lines.append("- If every number here is small, the delay is on the frontend (bundle load/rendering).")
    return "\n".join(lines)


def profile_with_cprofile(args: argparse.Namespace, backend: SimpleNamespace) -> None:
    """Run ``list_authorized_projects`` under cProfile and print the top functions."""
    projects_dir = Path(args.projects_dir).resolve()
    db_dir = Path(tempfile.mkdtemp(prefix="profile-listing-cprof-"))
    atexit.register(shutil.rmtree, db_dir, ignore_errors=True)
    db_path = db_dir / "authorization.sqlite3"

    service = backend.ProjectService(projects_dir=projects_dir)
    repository = backend.SQLiteAuthorizationRepository(db_path)
    try:
        authorization_service = backend.AuthorizationService(repository)
        principal = backend.Principal(
            principal_id="profile-listing",
            authentication_provider="profiler",
            authenticated_at=datetime.now(UTC),
        )
        for item in service.list_projects():
            authorization_service.register_project(principal, item.name)

        profiler = cProfile.Profile()
        profiler.enable()
        service.list_authorized_projects(principal, authorization_service)
        profiler.disable()
    finally:
        repository.close()

    if args.out:
        profiler.dump_stats(args.out)
        print(f"Profile statistics written to {args.out}")
        print(f"  View with: snakeviz {args.out}")

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(40)
    print("\ncProfile — top 40 by cumulative time (list_authorized_projects)")
    print(stream.getvalue())


def summary_to_dict(results: list[RunResult], projects_dir: Path) -> dict[str, Any]:
    """Build a machine-readable summary of the measured runs."""
    cold = results[0]

    def run_dict(run: RunResult) -> dict[str, Any]:
        return {
            "index": run.index,
            "cold": run.cold,
            "service_construct_ms": milliseconds(run.service_construct),
            "scan_ms": milliseconds(run.scan),
            "list_projects_ms": milliseconds(run.list_projects),
            "auth_repo_open_ms": milliseconds(run.repo_open),
            "auth_loop_ms": milliseconds(run.auth_loop),
            "authorized_count": run.authorized_count,
            "yaml_raw_parse_ms": milliseconds(run.raw_parse),
            "json_dumps_ms": milliseconds(run.json_dumps),
            "json_loads_ms": milliseconds(run.json_loads),
        }

    return {
        "issue": 508,
        "projects_dir": str(projects_dir),
        "file_count": len(cold.samples),
        "total_yaml_bytes": sum(sample.size_bytes for sample in cold.samples),
        "runs": [run_dict(run) for run in results],
        "cold_attribution_ms": {
            "scan": milliseconds(cold.scan),
            "yaml_raw_parse": milliseconds(cold.raw_parse),
            "json_dumps": milliseconds(cold.json_dumps),
            "json_loads": milliseconds(cold.json_loads),
            "list_projects_total": milliseconds(cold.list_projects),
        },
        "per_file_cold": [
            {
                "file": str(sample.path),
                "total_ms": milliseconds(sample.total),
                "raw_parse_ms": milliseconds(sample.raw_parse),
                "json_dumps_ms": milliseconds(sample.json_dumps),
                "json_loads_ms": milliseconds(sample.json_loads),
                "size_bytes": sample.size_bytes,
            }
            for sample in sorted(cold.samples, key=lambda s: s.total, reverse=True)
        ],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Profile the backend path behind GET /projects (issue #508).")
    parser.add_argument(
        "--projects-dir",
        default=str(DEFAULT_PROJECTS_DIR),
        help="Directory containing project folders with shapeshifter.yml files.",
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of runs; run 1 is cold, the rest are warm (default: 3).")
    parser.add_argument("--top", type=int, default=20, help="Number of files to show in the per-file table (default: 20).")
    parser.add_argument("--cprofile", action="store_true", help="Also profile list_authorized_projects with cProfile.")
    parser.add_argument("--out", default=None, help="With --cprofile, write cProfile statistics to this .prof file.")
    parser.add_argument("--verify", action="store_true", help="Also time the real list_authorized_projects() and compare.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON summary instead of the text report.")
    parser.add_argument("--verbose", action="store_true", help="Keep application log output (silenced by default).")
    return parser.parse_args(argv)


def verify_authorized_listing(args: argparse.Namespace, backend: SimpleNamespace, projects_dir: Path) -> float:
    """Time the real ``list_authorized_projects()`` once and return its wall time."""
    service = backend.ProjectService(projects_dir=projects_dir)
    db_dir = Path(tempfile.mkdtemp(prefix="profile-listing-verify-"))
    atexit.register(shutil.rmtree, db_dir, ignore_errors=True)
    repository = backend.SQLiteAuthorizationRepository(db_dir / "authorization.sqlite3")
    try:
        authorization_service = backend.AuthorizationService(repository)
        principal = backend.Principal(
            principal_id="profile-listing",
            authentication_provider="profiler",
            authenticated_at=datetime.now(UTC),
        )
        for item in service.list_projects():
            authorization_service.register_project(principal, item.name)
        start = time.perf_counter()
        authorized = service.list_authorized_projects(principal, authorization_service)
        elapsed = time.perf_counter() - start
        print(f"[verify] real list_authorized_projects() -> {len(authorized)} projects in {milliseconds(elapsed):.1f} ms")
        return elapsed
    finally:
        repository.close()


def main(argv: list[str] | None = None) -> int:
    """Run the profiler and print the report."""
    args = parse_args(argv)
    if not args.verbose:
        silence_logging()

    backend = import_backend()
    projects_dir = Path(args.projects_dir).resolve()

    results = run_listing(args, backend)

    if args.verify:
        verify_authorized_listing(args, backend, projects_dir)

    if args.cprofile:
        profile_with_cprofile(args, backend)

    if args.json:
        print(json_lib.dumps(summary_to_dict(results, projects_dir), indent=2))
        return 0

    print(render_report(results, projects_dir, args.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
