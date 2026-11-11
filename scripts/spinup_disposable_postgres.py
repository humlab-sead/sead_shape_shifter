#!/usr/bin/env python3
"""Start, stop, and inspect a loopback disposable PostgreSQL container for integration tests.

Several backend integration tests (for example
``backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py``) need a real
PostgreSQL server they can create and drop schemas in. Those tests read their connection
settings from ``SEAD_DISPOSABLE_POSTGRES_*`` environment variables and refuse any host that
is not loopback. This script starts a throwaway PostgreSQL container bound to the loopback
interface and prints the matching ``export`` lines, so the tests can run against a database
that holds no real data.

The container is disposable: ``down`` removes it together with all of its data. Never point
these tests at a real SEAD target or shared development database.

Usage:
    uv run python scripts/spinup_disposable_postgres.py up
    eval "$(uv run python scripts/spinup_disposable_postgres.py env)"
    uv run pytest backend/tests/ingesters/test_sead_change_request_direct_fk_postgres.py -q
    uv run python scripts/spinup_disposable_postgres.py down
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

DEFAULT_CONTAINER = "shifter-disposable-pg"
DEFAULT_IMAGE = "docker.io/library/postgres:16"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5432
DEFAULT_DB = "shifter_test"
DEFAULT_USER = "shifter_test"
DEFAULT_PASSWORD = "shifter_test"
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")
READY_TIMEOUT_SECONDS = 60
# podman's --publish needs an IP address, not a host name.
LOOPBACK_BIND_ADDRESSES = {"localhost": "127.0.0.1", "127.0.0.1": "127.0.0.1", "::1": "[::1]"}


class DisposablePostgresError(RuntimeError):
    """Raised when the disposable container cannot be started or reached."""


def run_command(args: list[str], *, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one podman command and return the completed process."""
    try:
        return subprocess.run(args, capture_output=capture, text=True, check=check)
    except FileNotFoundError as exc:
        raise DisposablePostgresError("podman is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise DisposablePostgresError(f"command failed: {' '.join(args)}\n{detail}") from exc


def container_exists(container: str) -> bool:
    """Return whether a container with this name exists."""
    result = run_command(["podman", "ps", "--all", "--filter", f"name=^/{container}$", "--format", "{{.Names}}"], check=False)
    return bool(result.stdout.strip())


def container_running(container: str) -> bool:
    """Return whether the named container is currently running."""
    result = run_command(["podman", "ps", "--filter", f"name=^/{container}$", "--format", "{{.Names}}"], check=False)
    return bool(result.stdout.strip())


def wait_until_ready(container: str, user: str, dbname: str, timeout: int = READY_TIMEOUT_SECONDS) -> None:
    """Wait until PostgreSQL inside the container accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = run_command(["podman", "exec", container, "pg_isready", "-U", user, "-d", dbname], check=False)
        if result.returncode == 0:
            return
        if not container_running(container):
            raise DisposablePostgresError(f"container '{container}' stopped while waiting for PostgreSQL to become ready")
        time.sleep(1)
    raise DisposablePostgresError(f"PostgreSQL was not ready within {timeout} seconds")


def start_container(args: argparse.Namespace) -> int:
    """Start the disposable PostgreSQL container and wait for it to accept connections."""
    if args.host not in LOOPBACK_HOSTS:
        raise DisposablePostgresError(f"--host must be one of {', '.join(LOOPBACK_HOSTS)}; the tests reject other hosts")

    if container_running(args.container):
        print(f"Container '{args.container}' is already running; reusing it.", file=sys.stderr)
    elif container_exists(args.container):
        run_command(["podman", "start", args.container])
        print(f"Started existing container '{args.container}'.", file=sys.stderr)
    else:
        run_command(
            [
                "podman",
                "run",
                "--detach",
                "--name",
                args.container,
                "--env",
                f"POSTGRES_DB={args.db}",
                "--env",
                f"POSTGRES_USER={args.user}",
                "--env",
                f"POSTGRES_PASSWORD={args.password}",
                "--publish",
                f"{LOOPBACK_BIND_ADDRESSES[args.host]}:{args.port}:5432",
                args.image,
            ]
        )
        print(f"Started disposable PostgreSQL container '{args.container}' on {args.host}:{args.port}.", file=sys.stderr)

    wait_until_ready(args.container, args.user, args.db)
    print("PostgreSQL is ready.", file=sys.stderr)
    print_exports(args)
    return 0


def stop_container(args: argparse.Namespace) -> int:
    """Remove the disposable container and all data it holds."""
    if not container_exists(args.container):
        print(f"No container named '{args.container}' exists.", file=sys.stderr)
        return 0
    run_command(["podman", "rm", "--force", args.container])
    print(f"Removed container '{args.container}' and its data.", file=sys.stderr)
    return 0


def show_status(args: argparse.Namespace) -> int:
    """Print whether the disposable container exists and is running."""
    if not container_exists(args.container):
        print(f"container '{args.container}': not created")
        return 0
    state = "running" if container_running(args.container) else "stopped"
    print(f"container '{args.container}': {state}")
    return 0


def print_exports(args: argparse.Namespace) -> None:
    """Print shell export lines for the disposable database connection."""
    print(f"export SEAD_DISPOSABLE_POSTGRES_HOST={args.host}")
    print(f"export SEAD_DISPOSABLE_POSTGRES_PORT={args.port}")
    print(f"export SEAD_DISPOSABLE_POSTGRES_DB={args.db}")
    print(f"export SEAD_DISPOSABLE_POSTGRES_USER={args.user}")
    print(f"export SEAD_DISPOSABLE_POSTGRES_PASSWORD={args.password}")


def build_parser() -> argparse.ArgumentParser:
    """Return the command-line parser with the up, down, status, and env commands."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--container", default=DEFAULT_CONTAINER, help=f"Container name (default: {DEFAULT_CONTAINER})")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help=f"PostgreSQL image (default: {DEFAULT_IMAGE})")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Loopback address to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Host port to publish (default: {DEFAULT_PORT})")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Disposable database name (default: {DEFAULT_DB})")
    parser.add_argument("--user", default=DEFAULT_USER, help=f"Disposable role name (default: {DEFAULT_USER})")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Password for the disposable role")

    subparsers = parser.add_subparsers(dest="command", required=True)
    up = subparsers.add_parser("up", help="Start the container, wait until ready, and print export lines")
    up.set_defaults(handler=start_container)

    down = subparsers.add_parser("down", help="Remove the container and its data")
    down.set_defaults(handler=stop_container)

    status = subparsers.add_parser("status", help="Report whether the container exists and is running")
    status.set_defaults(handler=show_status)

    env = subparsers.add_parser("env", help="Print export lines for an already running container")
    env.set_defaults(handler=print_exports)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested command and return its process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args) or 0)
    except DisposablePostgresError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
