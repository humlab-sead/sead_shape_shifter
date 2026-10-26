"""Tests for copying projects between local deployments."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy"))

from sync_projects import Deployment, SyncError, sync  # noqa: E402


class FakeCommands:
    """Keep authorization resources in memory while the files use temporary folders."""

    def __init__(self) -> None:
        self.resources: dict[str, list[dict[str, str]]] = {"source": [], "target": []}
        self.grants: dict[str, list[dict[str, str]]] = {"source": [], "target": []}
        self.adoptions: list[tuple[str, str]] = []
        self.restarts = 0

    def records(self, deployment: Deployment, command: str) -> list[dict[str, str]]:
        """Return fake JSON records for one deployment."""
        if command == "list-resources":
            return self.resources[deployment.user]
        if command == "list-grants":
            return self.grants[deployment.user]
        raise AssertionError(command)

    def adopt(self, deployment: Deployment, locator: str, owner: str) -> None:
        """Record a new resource with one owner grant."""
        self.adoptions.append((locator, owner))
        resource_id = f"target-{len(self.adoptions)}"
        self.resources[deployment.user].append(
            {"resource_type": "project", "locator": locator, "lifecycle_state": "active", "resource_id": resource_id}
        )
        self.grants[deployment.user].append({"resource_id": resource_id, "subject_type": "principal", "subject_id": owner, "role": "owner"})

    def restart(self, deployment: Deployment) -> None:
        """Count cache-clearing destination restarts."""
        assert deployment.user == "target"
        self.restarts += 1


class SyncProjectsTest(unittest.TestCase):
    """Check adoption, updates, conflicts, and retention of destination projects."""

    def setUp(self) -> None:
        """Create two fake deployments under a temporary directory."""
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        uid, gid = os.getuid(), os.getgid()
        self.source = Deployment("source", uid, gid, root / "source", root / "source/config", root / "source/data")
        self.target = Deployment("target", uid, gid, root / "target", root / "target/config", root / "target/data")
        self.source.projects_dir.mkdir(parents=True)
        self.target.projects_dir.mkdir(parents=True)
        (self.target.data_dir / "tmp").mkdir()
        (self.target.data_dir / "backups").mkdir()
        self.commands = FakeCommands()
        self.chown = patch("sync_projects.os.chown")
        self.chown.start()

    def tearDown(self) -> None:
        """Remove temporary deployments and restore the ownership function."""
        self.chown.stop()
        self.temporary.cleanup()

    def add_source_project(self, locator: str = "group:P", owner: str = "alice") -> Path:
        """Add a project folder and its source owner grant."""
        folder = self.source.projects_dir.joinpath(*locator.split(":"))
        folder.mkdir(parents=True)
        (folder / "shapeshifter.yml").write_text("entities: {}\n", encoding="utf-8")
        resource_id = f"source-{len(self.commands.resources['source']) + 1}"
        self.commands.resources["source"].append(
            {"resource_type": "project", "locator": locator, "lifecycle_state": "active", "resource_id": resource_id}
        )
        self.commands.grants["source"].append(
            {"resource_id": resource_id, "subject_type": "principal", "subject_id": owner, "role": "owner"}
        )
        return folder

    def test_adopts_new_project_and_keeps_destination_only_project(self) -> None:
        """Copy a new project and its owner without removing another project."""
        source_folder = self.add_source_project()
        (source_folder / "input.xlsx").write_bytes(b"data")
        destination_only = self.target.projects_dir / "local"
        destination_only.mkdir()
        (destination_only / "shapeshifter.yml").write_text("local", encoding="utf-8")

        self.assertEqual(sync(self.source, self.target, self.commands), ["adopt group:P"])

        self.assertEqual((self.target.projects_dir / "group/P/input.xlsx").read_bytes(), b"data")
        self.assertEqual(self.commands.adoptions, [("group:P", "alice")])
        self.assertEqual(self.commands.restarts, 1)
        self.assertTrue(destination_only.is_dir())
        marker = self.target.data_dir / "state/project-sync/source.json"
        self.assertEqual(json.loads(marker.read_text(encoding="utf-8"))["projects"]["group:P"]["target_resource_id"], "target-1")

    def test_updates_content_and_keeps_existing_grants(self) -> None:
        """Replace obsolete files within a synced project and retain its resource."""
        source_folder = self.add_source_project()
        (source_folder / "old.csv").write_text("old", encoding="utf-8")
        sync(self.source, self.target, self.commands)
        (source_folder / "old.csv").unlink()
        (source_folder / "new.csv").write_text("new", encoding="utf-8")
        target_grants = list(self.commands.grants["target"])

        self.assertEqual(sync(self.source, self.target, self.commands), ["update group:P"])

        destination = self.target.projects_dir / "group/P"
        self.assertFalse((destination / "old.csv").exists())
        self.assertEqual((destination / "new.csv").read_text(encoding="utf-8"), "new")
        self.assertEqual(self.commands.grants["target"], target_grants)
        self.assertEqual(self.commands.adoptions, [("group:P", "alice")])
        self.assertEqual(self.commands.restarts, 2)

    def test_target_edit_is_a_conflict(self) -> None:
        """Leave target edits in place rather than silently overwriting them."""
        self.add_source_project()
        sync(self.source, self.target, self.commands)
        target_yaml = self.target.projects_dir / "group/P/shapeshifter.yml"
        target_yaml.write_text("edited locally\n", encoding="utf-8")

        with self.assertRaisesRegex(SyncError, "edited after the last sync"):
            sync(self.source, self.target, self.commands)

        self.assertEqual(target_yaml.read_text(encoding="utf-8"), "edited locally\n")
        self.assertEqual(self.commands.restarts, 1)

    def test_source_deletion_does_not_delete_destination(self) -> None:
        """Keep a synced target project when its source project disappears."""
        source_folder = self.add_source_project()
        sync(self.source, self.target, self.commands)
        (source_folder / "shapeshifter.yml").unlink()
        source_folder.rmdir()

        self.assertEqual(sync(self.source, self.target, self.commands), [])
        self.assertTrue((self.target.projects_dir / "group/P/shapeshifter.yml").is_file())
        self.assertEqual(self.commands.restarts, 1)

    def test_untracked_destination_name_is_a_conflict(self) -> None:
        """Require explicit enrollment before overwriting a same-named target project."""
        self.add_source_project()
        destination = self.target.projects_dir / "group/P"
        destination.mkdir(parents=True)
        (destination / "shapeshifter.yml").write_text("destination", encoding="utf-8")

        with self.assertRaisesRegex(SyncError, "was not synced"):
            sync(self.source, self.target, self.commands)

        self.assertEqual((destination / "shapeshifter.yml").read_text(encoding="utf-8"), "destination")
        self.assertEqual(self.commands.adoptions, [])

    def test_explicit_enrollment_updates_existing_project_with_same_owner(self) -> None:
        """Enroll a named prior project and retain its replaced folder as a backup."""
        self.add_source_project()
        destination = self.target.projects_dir / "group/P"
        destination.mkdir(parents=True)
        (destination / "shapeshifter.yml").write_text("old destination", encoding="utf-8")
        self.commands.resources["target"].append(
            {"resource_type": "project", "locator": "group:P", "lifecycle_state": "active", "resource_id": "existing"}
        )
        self.commands.grants["target"].append(
            {"resource_id": "existing", "subject_type": "principal", "subject_id": "alice", "role": "owner"}
        )

        self.assertEqual(sync(self.source, self.target, self.commands, enroll_existing={"group:P"}), ["enroll group:P"])

        self.assertEqual((destination / "shapeshifter.yml").read_text(encoding="utf-8"), "entities: {}\n")
        backups = list((self.target.data_dir / "backups").glob("project-sync-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "shapeshifter.yml").read_text(encoding="utf-8"), "old destination")
        self.assertEqual(self.commands.adoptions, [])
        self.assertEqual(self.commands.restarts, 1)

    def test_enrollment_requires_same_owner(self) -> None:
        """Avoid taking over an existing project owned by someone else."""
        self.add_source_project()
        destination = self.target.projects_dir / "group/P"
        destination.mkdir(parents=True)
        (destination / "shapeshifter.yml").write_text("destination", encoding="utf-8")
        self.commands.resources["target"].append(
            {"resource_type": "project", "locator": "group:P", "lifecycle_state": "active", "resource_id": "existing"}
        )
        self.commands.grants["target"].append(
            {"resource_id": "existing", "subject_type": "principal", "subject_id": "bob", "role": "owner"}
        )

        with self.assertRaisesRegex(SyncError, "same single owner"):
            sync(self.source, self.target, self.commands, enroll_existing={"group:P"})

        self.assertEqual((destination / "shapeshifter.yml").read_text(encoding="utf-8"), "destination")

    def test_dry_run_changes_nothing(self) -> None:
        """Report adoption without writing files or authorization records."""
        self.add_source_project()

        self.assertEqual(sync(self.source, self.target, self.commands, dry_run=True), ["adopt group:P"])

        self.assertFalse((self.target.projects_dir / "group/P").exists())
        self.assertEqual(self.commands.adoptions, [])
        self.assertEqual(self.commands.restarts, 0)

    def test_multiple_source_owners_need_review(self) -> None:
        """Avoid choosing an arbitrary owner when the source has two."""
        self.add_source_project()
        self.commands.grants["source"].append(
            {"resource_id": "source-1", "subject_type": "principal", "subject_id": "bob", "role": "owner"}
        )

        with self.assertRaisesRegex(SyncError, "exactly one named owner"):
            sync(self.source, self.target, self.commands)

        self.assertFalse((self.target.projects_dir / "group/P").exists())

    def test_symlinked_project_file_is_rejected(self) -> None:
        """Do not copy files through a project symlink."""
        folder = self.add_source_project()
        outside = self.source.home / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        (folder / "linked.txt").symlink_to(outside)

        with self.assertRaisesRegex(SyncError, "contains a symlink"):
            sync(self.source, self.target, self.commands)

        self.assertFalse((self.target.projects_dir / "group/P").exists())

    def test_destination_nested_project_is_preserved(self) -> None:
        """Refuse an update that would remove a destination-only child project."""
        source_folder = self.add_source_project(locator="P")
        sync(self.source, self.target, self.commands)
        child = self.target.projects_dir / "P/local"
        child.mkdir()
        (child / "shapeshifter.yml").write_text("local", encoding="utf-8")
        (source_folder / "shapeshifter.yml").write_text("changed", encoding="utf-8")

        with self.assertRaisesRegex(SyncError, "contains another project"):
            sync(self.source, self.target, self.commands)

        self.assertEqual((child / "shapeshifter.yml").read_text(encoding="utf-8"), "local")


if __name__ == "__main__":
    unittest.main()
