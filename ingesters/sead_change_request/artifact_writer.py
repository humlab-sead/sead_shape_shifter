"""Artifact bundle emission helpers for the SEAD change request ingester."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ingesters.sead_change_request.contracts import SubmissionContext, resolve_bundle_name
from ingesters.sead_change_request.sql_builder import encode_bundle_file_content
from src.path_resolution import resolve_contained_path


def utc_now() -> datetime:
    """Return the current UTC time; separated for deterministic tests."""
    return datetime.now(UTC)


def build_run_folder_name(run_id: str, started_at: datetime | None = None) -> str:
    """Build the exclusive run-folder name for one effective run ID."""
    started_at = started_at or utc_now()
    digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    return f"{started_at.strftime('%Y%m%dT%H%M%SZ')}_{digest}"


class RunFolderCollisionError(FileExistsError):
    """Raised when a run folder already exists for the same effective run ID."""


def reserve_run_folder(output_folder: Path | str, run_id: str) -> Path:
    """Reserve an exclusive run folder under the managed output root.

    Raises RunFolderCollisionError when the same run identity already has a
    folder, so the caller fails before any SIMS or file side effect.
    """
    output_root = Path(output_folder)
    run_folder = output_root / build_run_folder_name(run_id)
    try:
        run_folder.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise RunFolderCollisionError(f"Run folder already exists for run ID '{run_id}'") from exc
    return run_folder


def write_artifact_bundle(
    run_folder: Path | str,
    deploy_artifact: dict[str, Any],
    submission_context: SubmissionContext,
) -> Path:
    """Write the rendered deploy artifact bundle inside the reserved run folder.

    The bundle keeps its canonical name and internal layout. A pre-existing
    bundle directory is rejected instead of replaced, and payload paths are
    resolved inside the bundle so they cannot escape it.
    """
    bundle_name = resolve_bundle_name(submission_context)
    artifact_directory = Path(run_folder) / bundle_name
    artifact_directory.mkdir(parents=True, exist_ok=False)

    for deploy_target in ["deploy", "revert", "verify"]:
        sql_key = f"{deploy_target}_sql"
        if sql_key not in deploy_artifact:
            raise ValueError(f"Deploy artifact is missing required '{sql_key}' field")

        target_folder = artifact_directory / deploy_target
        target_folder.mkdir(parents=True, exist_ok=True)
        (target_folder / f"{bundle_name}.sql").write_text(str(deploy_artifact[sql_key]), encoding="utf-8")

    (artifact_directory / "manifest.json").write_text(
        json.dumps(deploy_artifact["metadata_artifact"], indent=2, sort_keys=True),
        encoding="utf-8",
    )

    for relative_path, content in deploy_artifact.get("bundle_files", {}).items():
        artifact_path = resolve_contained_path(relative_path, artifact_directory)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(encode_bundle_file_content(str(relative_path), str(content)))

    return artifact_directory
