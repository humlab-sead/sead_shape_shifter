"""Artifact bundle emission helpers for the SEAD change request ingester."""

import json
import shutil
from pathlib import Path
from typing import Any

from ingesters.sead_change_request.contracts import SubmissionContext, resolve_bundle_name
from ingesters.sead_change_request.sql_builder import encode_bundle_file_content


def write_artifact_bundle(
    output_folder: Path | str,
    deploy_artifact: dict[str, Any],
    submission_context: SubmissionContext,
) -> Path:
    """Write the rendered deploy artifact bundle to disk."""
    output_root = Path(output_folder)
    bundle_name = resolve_bundle_name(submission_context)
    artifact_directory = output_root / bundle_name

    if artifact_directory.exists():
        shutil.rmtree(artifact_directory)
    artifact_directory.mkdir(parents=True, exist_ok=True)

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
        artifact_path = artifact_directory / str(relative_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(encode_bundle_file_content(str(relative_path), str(content)))

    return artifact_directory
