#!/usr/bin/env python3
"""Copy projects from one local deployment to another without deleting projects."""

import argparse
import fcntl
import hashlib
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from _hashlib import HASH


class SyncError(Exception):
    """Report a project that cannot be copied safely."""


@dataclass(frozen=True)
class Deployment:
    """Paths and Unix identity for one local deployment."""

    user: str
    uid: int
    gid: int
    home: Path
    config_dir: Path
    data_dir: Path

    @property
    def projects_dir(self) -> Path:
        """Return the directory containing project folders."""
        return self.data_dir / "projects"

    @property
    def container_dir(self) -> Path:
        """Return the deployed scripts directory's parent."""
        return self.home / "container"


@dataclass(frozen=True)
class Project:
    """One source project and its named owner."""

    locator: str
    path: Path
    resource_id: str
    owner: str
    digest: str


@dataclass(frozen=True)
class Change:
    """One project copy that passed all preflight checks."""

    project: Project
    destination: Path
    target_resource_id: str | None
    enrollment: bool = False


class DeploymentCommands:
    """Run the installed deployment commands as their owning Unix user."""

    PATH = "/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin"

    def run(self, deployment: Deployment, script: str, *args: str) -> str:
        """Run a deployed script with the user's rootless Podman environment."""
        command = [
            "sudo",
            "-u",
            deployment.user,
            "-H",
            "env",
            "--",
            f"PATH={self.PATH}",
            f"XDG_RUNTIME_DIR=/run/user/{deployment.uid}",
            f"CONFIG_DIR={deployment.config_dir}",
            str(deployment.container_dir / "scripts" / script),
            *args,
        ]
        result: subprocess.CompletedProcess[str] = subprocess.run(
            command, cwd=deployment.container_dir, capture_output=True, text=True, check=False
        )
        if result.returncode:
            raise SyncError(f"{deployment.user}: {script} {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
        return result.stdout

    def grant_records(self, deployment: Deployment, command: str) -> list[dict[str, Any]]:
        """Read JSON resource or grant records from the authorization wrapper."""
        output = self.run(deployment, "authorization.sh", command, "--json")
        try:
            records = json.loads(output)
        except json.JSONDecodeError as exc:
            raise SyncError(f"{deployment.user}: invalid JSON from {command}") from exc
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise SyncError(f"{deployment.user}: invalid records from {command}")
        return records

    def adopt(self, deployment: Deployment, locator: str, owner: str) -> None:
        """Create a project resource with the source project's owner."""
        self.run(deployment, "project.sh", "adopt", "--project", locator, "--owner", owner)

    def restart(self, deployment: Deployment) -> None:
        """Restart the destination so its project caches reload from disk."""
        self.run(deployment, "container.sh", "restart")


def resolve_deployment(user: str, config_dir: Path | None = None) -> Deployment:
    """Resolve the data mount using the deployment's installed environment loader."""
    try:
        account = pwd.getpwnam(user)
    except KeyError as exc:
        raise SyncError(f"Unknown deployment user: {user}") from exc
    home = Path(account.pw_dir)
    loader = home / "container" / "scripts" / "_load-env.sh"
    if not loader.is_file():
        raise SyncError(f"Deployment loader is missing: {loader}")
    environment = ["env", "-i", f"HOME={home}", f"PATH={DeploymentCommands.PATH}"]
    if config_dir is not None:
        environment.append(f"CONFIG_DIR={config_dir}")
    command = [
        "sudo",
        "-u",
        user,
        "-H",
        *environment,
        "bash",
        "-c",
        '. "$HOME/container/scripts/_load-env.sh"; printf "%s\\n%s\\n" "$CONFIG_DIR" "$CONTAINER_DATA_DIR"',
    ]
    result = subprocess.run(command, cwd=home, capture_output=True, text=True, check=False)
    paths = result.stdout.splitlines()
    if result.returncode or len(paths) != 2 or any(not path for path in paths):
        raise SyncError(f"Cannot resolve the data directory for {user}: {result.stderr.strip()}")
    return Deployment(user, account.pw_uid, account.pw_gid, home, Path(paths[0]), Path(paths[1]))


def tree_digest(root: Path) -> str:
    """Hash file names and contents, rejecting links that could leave the project."""
    if not root.is_dir() or root.is_symlink():
        raise SyncError(f"Project folder is missing or is a symlink: {root}")
    digest: HASH = hashlib.sha256()
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in sorted(directories + files):
            path: Path = current_path / name
            if path.is_symlink():
                raise SyncError(f"Project contains a symlink: {path}")
            relative: bytes = path.relative_to(root).as_posix().encode()
            if path.is_dir():
                digest.update(b"D\0" + relative + b"\0")
            elif path.is_file():
                digest.update(b"F\0" + relative + b"\0")
                digest.update(path.stat().st_size.to_bytes(8, "big"))
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):  # pylint: disable=cell-var-from-loop
                        digest.update(chunk)
            else:
                raise SyncError(f"Project contains an unsupported file: {path}")
    return digest.hexdigest()


def project_locator(path: Path, projects_dir: Path) -> str:
    """Convert a project folder under projects/ to its API locator."""
    relative: Path = path.relative_to(projects_dir)
    if not relative.parts or any(part in {".", ".."} or ":" in part for part in relative.parts):
        raise SyncError(f"Invalid project folder name: {path}")
    return ":".join(relative.parts)


def reject_symlink_ancestors(path: Path, root: Path) -> None:
    """Reject a project path whose existing parent points outside its root."""
    relative: Path = path.relative_to(root)
    current: Path = root
    if current.is_symlink():
        raise SyncError(f"Project path contains a symlink: {current}")
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise SyncError(f"Project path contains a symlink: {current}")


def source_projects(source: Deployment, commands: DeploymentCommands) -> list[Project]:
    """Read source folders and their one named owner from authorization records."""
    resources: dict[Any, Any] = {
        item["locator"]: item["resource_id"]
        for item in commands.grant_records(source, "list-resources")
        if item.get("resource_type") == "project" and item.get("lifecycle_state") == "active"
    }
    owners: dict[str, list[str]] = {}
    for grant in commands.grant_records(source, "list-grants"):
        if grant.get("role") == "owner" and grant.get("subject_type") == "principal":
            owners.setdefault(grant["resource_id"], []).append(grant["subject_id"])

    projects: list[Project] = []
    for yaml_file in sorted(source.projects_dir.rglob("shapeshifter.yml")):
        folder: Path = yaml_file.parent
        reject_symlink_ancestors(folder, source.projects_dir)
        locator: str = project_locator(folder, source.projects_dir)
        resource_id: Any | None = resources.get(locator)
        if resource_id is None:
            raise SyncError(f"Source project has no active authorization resource: {locator}")
        project_owners: list[str] = sorted(set(owners.get(resource_id, [])))
        if len(project_owners) != 1:
            raise SyncError(f"Source project {locator} needs exactly one named owner; found {len(project_owners)}")
        projects.append(Project(locator, folder, resource_id, project_owners[0], tree_digest(folder)))

    paths: set[Path] = {project.path for project in projects}
    for project in projects:
        if any(parent in paths for parent in project.path.parents):
            raise SyncError(f"Nested project folders are not supported: {project.locator}")
    return projects


def state_path(source: Deployment, target: Deployment) -> Path:
    """Return the marker file for this source and destination pair."""
    return target.data_dir / "state" / "project-sync" / f"{source.user}.json"


def check_state_path(path: Path) -> None:
    """Reject links in the marker path before the root process opens it."""
    for candidate in (path.parent.parent, path.parent, path, path.with_suffix(".lock")):
        if candidate.is_symlink():
            raise SyncError(f"Project sync state path contains a symlink: {candidate}")


def read_state(path: Path, source: Deployment) -> dict[str, dict[str, str]]:
    """Read the prior successful copies and check their source identity."""
    check_state_path(path)
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"Cannot read sync state: {path}") from exc
    if not isinstance(state, dict):
        raise SyncError(f"Invalid project sync state: {path}")
    if state.get("version") != 1 or state.get("source_user") != source.user or state.get("source_data_dir") != str(source.data_dir):
        raise SyncError(f"Sync state belongs to another source or format: {path}")
    projects = state.get("projects")
    if not isinstance(projects, dict) or any(not isinstance(key, str) or not isinstance(value, dict) for key, value in projects.items()):
        raise SyncError(f"Invalid project sync state: {path}")
    return projects


def write_state(path: Path, source: Deployment, projects: dict[str, dict[str, str]]) -> None:
    """Atomically record completed copies for a later conflict check."""
    check_state_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    contents = {"version": 1, "source_user": source.user, "source_data_dir": str(source.data_dir), "projects": projects}
    temporary: Path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(contents, output, indent=2, sort_keys=True)
            output.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def sync_lock(path: Path) -> Iterator[None]:
    """Allow only one writer for a source and destination pair."""
    check_state_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SyncError("Another project sync is already running for this deployment pair") from exc
        yield
    finally:
        os.close(descriptor)


def plan(
    source: Deployment,
    target: Deployment,
    commands: DeploymentCommands,
    state: dict[str, dict[str, str]],
    enroll_existing: set[str],
) -> list[Change]:
    """Reject collisions and local changes before copying any project."""
    target_resources = {
        item["locator"]: item["resource_id"]
        for item in commands.grant_records(target, "list-resources")
        if item.get("resource_type") == "project" and item.get("lifecycle_state") == "active"
    }
    target_owners: dict[str, set[str]] = {}
    if enroll_existing:
        for grant in commands.grant_records(target, "list-grants"):
            if grant.get("role") == "owner" and grant.get("subject_type") == "principal":
                target_owners.setdefault(grant["resource_id"], set()).add(grant["subject_id"])
    changes = []
    enrolled: set[str] = set()
    for project in source_projects(source, commands):
        destination = target.projects_dir.joinpath(*project.locator.split(":"))
        reject_symlink_ancestors(destination, target.projects_dir)
        for ancestor in destination.parents:
            if ancestor == target.projects_dir:
                break
            if (ancestor / "shapeshifter.yml").exists():
                raise SyncError(f"Destination project is inside another project: {project.locator}")
        if destination.is_dir() and any(yaml_file.parent != destination for yaml_file in destination.rglob("shapeshifter.yml")):
            raise SyncError(f"Destination project contains another project: {project.locator}")
        previous = state.get(project.locator)
        resource_id = target_resources.get(project.locator)
        if previous is None:
            if destination.exists() or resource_id is not None:
                if project.locator not in enroll_existing:
                    raise SyncError(f"Destination project already exists and was not synced: {project.locator}")
                if not destination.is_dir() or resource_id is None or target_owners.get(resource_id) != {project.owner}:
                    raise SyncError(f"Existing destination project needs the same single owner before enrollment: {project.locator}")
                changes.append(Change(project, destination, resource_id, enrollment=True))
                enrolled.add(project.locator)
                continue
            if project.locator in enroll_existing:
                raise SyncError(f"Cannot enroll a project that is new on the destination: {project.locator}")
            changes.append(Change(project, destination, None))
            continue
        if project.locator in enroll_existing:
            raise SyncError(f"Project is already enrolled: {project.locator}")
        if previous.get("source_resource_id") != project.resource_id or previous.get("target_resource_id") != resource_id:
            raise SyncError(f"Authorization resource changed for synced project: {project.locator}")
        if not destination.is_dir() or destination.is_symlink():
            raise SyncError(f"Synced destination project is missing: {project.locator}")
        if tree_digest(destination) != previous.get("digest"):
            raise SyncError(f"Destination project was edited after the last sync: {project.locator}")
        if project.digest != previous.get("digest"):
            changes.append(Change(project, destination, resource_id))
    unknown = enroll_existing - enrolled
    if unknown:
        raise SyncError(f"Projects requested for enrollment were not found: {', '.join(sorted(unknown))}")
    return changes


def copy_to_stage(change: Change, target: Deployment) -> Path:
    """Copy one stable source project outside project discovery and set ownership."""
    parent = change.destination.parent
    reject_symlink_ancestors(parent, target.projects_dir)
    parent.mkdir(parents=True, exist_ok=True)
    current = parent
    while current != target.projects_dir.parent:
        os.chown(current, target.uid, target.gid)
        current = current.parent
    stage_root = target.data_dir / "tmp"
    if not stage_root.is_dir() or stage_root.is_symlink() or stage_root.stat().st_dev != parent.stat().st_dev:
        raise SyncError(f"Destination staging directory must be on the project filesystem: {stage_root}")
    stage = Path(tempfile.mkdtemp(prefix=f"project-sync-{change.destination.name}-", dir=stage_root))
    try:
        shutil.copytree(change.project.path, stage, dirs_exist_ok=True, symlinks=True)
        for current, directories, files in os.walk(stage):
            os.chown(current, target.uid, target.gid)
            for name in directories + files:
                os.chown(Path(current) / name, target.uid, target.gid)
        if tree_digest(change.project.path) != change.project.digest or tree_digest(stage) != change.project.digest:
            raise SyncError(f"Source project changed during copy: {change.project.locator}")
        return stage
    except Exception:
        shutil.rmtree(stage)
        raise


def sync(
    source: Deployment,
    target: Deployment,
    commands: DeploymentCommands,
    dry_run: bool = False,
    enroll_existing: set[str] | None = None,
) -> list[str]:
    """Copy changed projects and adopt new ones; keep absent source projects."""
    if source.user == target.user or source.projects_dir.resolve() == target.projects_dir.resolve():
        raise SyncError("Source and destination must be different deployments")
    if not source.projects_dir.is_dir() or not target.projects_dir.is_dir():
        raise SyncError("Both deployments need an existing projects directory")
    if source.projects_dir.is_symlink() or target.projects_dir.is_symlink():
        raise SyncError("The projects directory cannot be a symlink")
    marker: Path = state_path(source, target)
    state: dict[str, dict[str, str]] = read_state(marker, source)
    changes: list[Change] = plan(source, target, commands, state, enroll_existing or set())
    descriptions: list[str] = [
        f"{'enroll' if change.enrollment else 'adopt' if change.target_resource_id is None else 'update'} {change.project.locator}"
        for change in changes
    ]
    if dry_run or not changes:
        return descriptions

    stages: list[tuple[Change, Path]] = []
    changed = False
    try:
        for change in changes:
            stages.append((change, copy_to_stage(change, target)))
        for change, stage in stages:
            destination = change.destination
            backup_root = target.data_dir / "backups"
            if not backup_root.is_dir() or backup_root.is_symlink() or backup_root.stat().st_dev != destination.parent.stat().st_dev:
                raise SyncError(f"Destination backup directory must be on the project filesystem: {backup_root}")
            backup = backup_root / f"project-sync-{uuid4().hex}" if destination.exists() else None
            if backup is not None:
                os.replace(destination, backup)
            try:
                os.replace(stage, destination)
                changed = True
            except Exception:
                if backup is not None:
                    os.replace(backup, destination)
                raise
            try:
                if change.target_resource_id is None:
                    commands.adopt(target, change.project.locator, change.project.owner)
                    resources = commands.grant_records(target, "list-resources")
                    target_resource_id = next(
                        (
                            item["resource_id"]
                            for item in resources
                            if item.get("resource_type") == "project"
                            and item.get("lifecycle_state") == "active"
                            and item.get("locator") == change.project.locator
                        ),
                        None,
                    )
                    if target_resource_id is None:
                        raise SyncError(f"Adoption did not create a resource: {change.project.locator}")
                else:
                    target_resource_id = change.target_resource_id
                state[change.project.locator] = {
                    "source_resource_id": change.project.resource_id,
                    "target_resource_id": target_resource_id,
                    "digest": change.project.digest,
                }
                write_state(marker, source, state)
            except Exception:
                # Adoption can succeed before a later check fails. Keep the folder
                # so an authorization resource never points at a missing project.
                if change.target_resource_id is not None:
                    shutil.rmtree(destination)
                    if backup is not None:
                        os.replace(backup, destination)
                raise
            if backup is not None and change.enrollment:
                print(f"Kept prior destination project at {backup}")
            elif backup is not None:
                shutil.rmtree(backup)
    finally:
        for _, stage in stages:
            if stage.exists():
                shutil.rmtree(stage)
        if changed:
            commands.restart(target)
    return descriptions


def main() -> int:
    """Parse deployment names and run one local project sync."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-user", required=True, help="Unix user that owns the source deployment")
    parser.add_argument("--target-user", required=True, help="Unix user that owns the destination deployment")
    parser.add_argument("--source-config-dir", type=Path, help="Source CONFIG_DIR if it is not ~/config")
    parser.add_argument("--target-config-dir", type=Path, help="Destination CONFIG_DIR if it is not ~/config")
    parser.add_argument(
        "--enroll-existing",
        action="append",
        default=[],
        metavar="PROJECT",
        help="Allow one named existing destination project with the same owner to be replaced and tracked",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show copies without changing projects")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("run as root so both deployment users' files can be read and ownership can be set")
    try:
        source: Deployment = resolve_deployment(args.source_user, args.source_config_dir)
        target: Deployment = resolve_deployment(args.target_user, args.target_config_dir)
        if args.dry_run:
            descriptions: list[str] = sync(source, target, DeploymentCommands(), dry_run=True, enroll_existing=set(args.enroll_existing))
        else:
            with sync_lock(state_path(source, target)):
                descriptions = sync(source, target, DeploymentCommands(), enroll_existing=set(args.enroll_existing))
    except (OSError, SyncError) as exc:
        print(f"Project sync failed: {exc}", file=sys.stderr)
        return 1
    for description in descriptions:
        print(f"{'Would ' if args.dry_run else ''}{description}")
    print(f"{len(descriptions)} project(s) {'would change' if args.dry_run else 'changed'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
