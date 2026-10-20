"""Tests for the Change Request artifact writer run-folder helpers."""

from datetime import datetime

import pytest

from ingesters.sead_change_request.artifact_writer import (
    RunFolderCollisionError,
    build_run_folder_name,
    reserve_run_folder,
    write_artifact_bundle,
)
from ingesters.sead_change_request.contracts import SubmissionContext, resolve_bundle_name


def submission_context() -> SubmissionContext:
    """Build a minimal submission context for writer tests."""
    return SubmissionContext(
        submission_name="test-submission",
        project_name="test-project",
        timestamp=datetime(2026, 5, 23, 22, 0, 0),
        datatype="mal",
        identifier="TEST_SUBMISSION",
    )


def deploy_artifact() -> dict:
    """Build a minimal deploy artifact payload for writer tests."""
    return {
        "deploy_sql": "-- deploy",
        "revert_sql": "-- revert",
        "verify_sql": "-- verify",
        "metadata_artifact": {"scope_name": "provider://mal/test", "run_id": "run-1"},
        "bundle_files": {},
    }


def test_build_run_folder_name_digests_raw_run_id():
    """The run folder uses a fixed-length digest, never the raw run ID."""
    hostile = "../../etc/passwd"
    name = build_run_folder_name(hostile, started_at=datetime(2026, 5, 23, 22, 0, 0))
    assert name.startswith("20260523T220000Z_")
    assert hostile not in name
    assert "/" not in name
    assert ".." not in name
    assert len(name.split("_", 1)[1]) == 64  # SHA-256 hex digest length


def test_reserve_run_folder_is_exclusive(tmp_path):
    """Reserving the same run identity twice raises a collision."""
    run_id = "fixed-run-id"
    first = reserve_run_folder(tmp_path, run_id)
    assert first.is_dir()
    with pytest.raises(RunFolderCollisionError):
        reserve_run_folder(tmp_path, run_id)


def test_write_artifact_bundle_rejects_existing_bundle(tmp_path):
    """The writer must not replace an existing bundle directory."""
    run_folder = reserve_run_folder(tmp_path, "run-1")
    bundle_name = resolve_bundle_name(submission_context())
    (run_folder / bundle_name).mkdir(parents=True, exist_ok=False)
    with pytest.raises(FileExistsError):
        write_artifact_bundle(run_folder, deploy_artifact(), submission_context())


def test_write_artifact_bundle_rejects_escaping_payload_path(tmp_path):
    """A payload path that leaves the bundle must be rejected."""
    run_folder = reserve_run_folder(tmp_path, "run-1")
    artifact = deploy_artifact()
    artifact["bundle_files"] = {"../escape.gz": "payload"}
    with pytest.raises(ValueError, match="outside the managed root"):
        write_artifact_bundle(run_folder, artifact, submission_context())


def test_write_artifact_bundle_writes_into_reserved_folder(tmp_path):
    """The writer returns the bundle directory inside the reserved run folder."""
    run_folder = reserve_run_folder(tmp_path, "run-1")
    bundle_name = resolve_bundle_name(submission_context())
    directory = write_artifact_bundle(run_folder, deploy_artifact(), submission_context())
    assert directory == run_folder / bundle_name
    assert (directory / "deploy" / f"{bundle_name}.sql").exists()
    assert (directory / "manifest.json").exists()
