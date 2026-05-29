"""Input and config resolution for the SEAD change request ingester."""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.ingesters.protocol import IngesterConfig
from ingesters.sead_change_request.contracts import (
    APPROVED_DATATYPES,
    ChangeRowState,
    IdentityAssignment,
    SourceTableBundle,
    SubmissionContext,
    is_valid_submission_identifier,
    normalize_submission_identifier,
)
from ingesters.sead_change_request.preparation import ResolvedInputs
from ingesters.sead_change_request.sql_builder import resolve_deploy_artifact_strategy
from src.target_model.models import TargetModel
from src.utility import sanitize_columns


class InputResolutionError(Exception):
    """Expected user/configuration error while resolving ingester inputs.

    Input-resolution errors are safe to convert into ValidationResult or
    IngestionResult failures. Unexpected programming errors should not be
    wrapped in this type.
    """

    scope: str = "unknown"
    ingest_message: str = "Invalid ingester input"

    def __init__(self, user_message: str, *, warnings: list[str] | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.warnings = warnings or []

    def with_warnings(self, warnings: list[str]) -> "InputResolutionError":
        """Attach already discovered source-bundle warnings before re-raising."""
        self.warnings = list(warnings)
        return self


class SourceBundleError(InputResolutionError):
    scope = "input"
    ingest_message = "Invalid source bundle"


class TargetModelError(InputResolutionError):
    scope = "target-model"
    ingest_message = "Invalid target model"


class SubmissionContextError(InputResolutionError):
    scope = "submission-context"
    ingest_message = "Invalid submission context"


class IdentityAssignmentError(InputResolutionError):
    scope = "identity-assignment"
    ingest_message = "Invalid identity assignments"


class DeployStrategyError(InputResolutionError):
    scope = "deploy-strategy"
    ingest_message = "Invalid deploy strategy"


def resolve_inputs(config: IngesterConfig, source: object) -> ResolvedInputs:
    """Load and validate all expected inputs for the shared workflow.

    The source bundle is loaded first so its warnings can be preserved when
    later input resolution fails during validation.
    """
    bundle: SourceTableBundle = _resolve_source_bundle(config, source)

    try:
        target_model: TargetModel = _resolve_target_model(config)
        submission_context: SubmissionContext = _resolve_submission_context(config)
        fallback_assignments: dict[str, dict[object, IdentityAssignment]] = _resolve_identity_assignments(config)
        deploy_strategy: Any | None = _resolve_deploy_strategy(config)
    except InputResolutionError as exc:
        raise exc.with_warnings(bundle.warnings) from exc

    return ResolvedInputs(
        bundle=bundle,
        target_model=target_model,
        submission_context=submission_context,
        fallback_assignments=fallback_assignments,
        deploy_strategy=deploy_strategy,
    )


def _resolve_source_bundle(config: IngesterConfig, source: object) -> SourceTableBundle:
    """Resolve the current protocol edge into the internal bundle contract."""
    extras: dict[str, Any] = config.extra or {}

    if isinstance(source, SourceTableBundle):
        return source

    source_bundle = extras.get("source_bundle")
    if isinstance(source_bundle, SourceTableBundle):
        return source_bundle

    table_mapping = source if isinstance(source, dict) else extras.get("tables")
    if isinstance(table_mapping, dict):
        source_name = str(source) if isinstance(source, (Path, str)) else ""
        return _build_source_bundle(table_mapping, source_name=source_name)

    if isinstance(source, (Path, str)):
        return _load_source_bundle_from_path(Path(source))

    raise SourceBundleError("Unsupported source type for sead_change_request ingestion")


def _load_source_bundle_from_path(source_path: Path) -> SourceTableBundle:
    """Load an Excel workbook into the internal source-bundle contract."""
    if not source_path.exists():
        raise SourceBundleError(f"Source file does not exist: {source_path}")
    if source_path.suffix.lower() not in {".xlsx", ".xls"}:
        raise SourceBundleError(f"Unsupported source file format '{source_path.suffix}'; expected .xlsx or .xls")

    with pd.ExcelFile(source_path) as workbook:
        table_mapping: dict[str, pd.DataFrame] = {}
        warnings: list[str] = []

        for sheet_name in workbook.sheet_names:
            normalized_sheet_name = str(sheet_name)
            if normalized_sheet_name == "data_table_index":
                warnings.append("Ignored sheet 'data_table_index' from Excel source bundle")
                continue

            frame: pd.DataFrame = pd.read_excel(workbook, sheet_name=normalized_sheet_name)
            frame.columns = sanitize_columns(list(frame.columns))
            table_mapping[normalized_sheet_name] = frame

    if not table_mapping:
        raise SourceBundleError(f"No usable sheets were found in source file: {source_path}")

    return SourceTableBundle(tables=table_mapping, source_name=str(source_path), warnings=warnings)


def _build_source_bundle(tables: dict[object, object], source_name: str = "") -> SourceTableBundle:
    """Build a validated source bundle from a raw table mapping."""
    if not tables:
        raise SourceBundleError("No source tables were provided")

    normalized_tables: dict[str, pd.DataFrame] = {}
    for table_name, frame in tables.items():
        if not isinstance(table_name, str) or not table_name.strip():
            raise SourceBundleError("Source table names must be non-empty strings")
        if not isinstance(frame, pd.DataFrame):
            raise SourceBundleError(f"Source table '{table_name}' must be a pandas DataFrame")

        normalized_tables[table_name] = frame

    return SourceTableBundle(tables=normalized_tables, source_name=source_name)


def _resolve_target_model(config: IngesterConfig) -> TargetModel:
    """Load the target model from the ingester config input."""
    extras: dict[str, Any] = config.extra or {}
    target_model_data = extras.get("target_model")

    if isinstance(target_model_data, TargetModel):
        return target_model_data
    if isinstance(target_model_data, dict):
        try:
            return TargetModel.model_validate(target_model_data)
        except ValueError as exc:
            raise TargetModelError(str(exc)) from exc

    raise TargetModelError("Target model is required; provide config.extra['target_model'] as a dict or TargetModel")


def _resolve_submission_context(config: IngesterConfig) -> SubmissionContext:
    """Load submission-scoped metadata from the ingester config input."""
    extras: dict[str, Any] = config.extra or {}
    context_data = extras.get("submission_context")

    if isinstance(context_data, SubmissionContext):
        return context_data

    if not isinstance(context_data, dict):
        raise SubmissionContextError("Submission context is required; provide config.extra['submission_context']")

    submission_name = context_data.get("submission_name") or config.submission_name
    project_name = context_data.get("project_name")
    timestamp = context_data.get("timestamp")

    if not isinstance(submission_name, str) or not submission_name.strip():
        raise SubmissionContextError("Submission context requires a non-empty submission_name")
    if not isinstance(project_name, str) or not project_name.strip():
        raise SubmissionContextError("Submission context requires a non-empty project_name")

    parsed_timestamp = _parse_submission_timestamp(timestamp)

    binding_set_uuid: str | None = _optional_string(context_data, "binding_set_uuid", SubmissionContextError)
    change_request_name: str | None = _optional_string(context_data, "change_request_name", SubmissionContextError)
    datatype: str | None = _optional_string(context_data, "datatype", SubmissionContextError)
    identifier: str | None = _optional_string(context_data, "identifier", SubmissionContextError)
    description: str | None = _optional_string(context_data, "description", SubmissionContextError)
    issue_number: str | None = _optional_string(context_data, "issue_number", SubmissionContextError)
    author: str | None = _optional_string(context_data, "author", SubmissionContextError)

    normalized_datatype: str = _normalize_datatype(datatype)
    normalized_identifier: str = _normalize_identifier(identifier)
    normalized_description: str | None = _normalize_description(description)

    return SubmissionContext(
        submission_name=submission_name.strip(),
        project_name=project_name.strip(),
        timestamp=parsed_timestamp,
        binding_set_uuid=binding_set_uuid,
        change_request_name=change_request_name,
        datatype=normalized_datatype,
        identifier=normalized_identifier,
        description=normalized_description,
        issue_number=issue_number.strip() if isinstance(issue_number, str) else None,
        author=author.strip() if isinstance(author, str) else None,
    )


def _optional_string(data: dict[str, Any], field_name: str, error_type: type[InputResolutionError]) -> str | None:
    """Return an optional string config value or raise an input error."""
    value = data.get(field_name)
    if value is not None and not isinstance(value, str):
        readable_field_name = field_name.replace("_", " ")
        raise error_type(f"Submission context {readable_field_name} must be a string when provided")
    return value


def _normalize_datatype(datatype: str | None) -> str:
    if not isinstance(datatype, str) or not datatype.strip():
        raise SubmissionContextError("Submission context requires a non-empty datatype")

    normalized_datatype = datatype.strip().lower()
    if normalized_datatype not in APPROVED_DATATYPES:
        raise SubmissionContextError("Submission context datatype must be one of: " + ", ".join(sorted(APPROVED_DATATYPES)))
    return normalized_datatype


def _normalize_identifier(identifier: str | None) -> str:
    if not isinstance(identifier, str) or not identifier.strip():
        raise SubmissionContextError("Submission context requires a non-empty identifier")

    normalized_identifier: str = normalize_submission_identifier(identifier)
    if not is_valid_submission_identifier(normalized_identifier):
        raise SubmissionContextError(
            "Submission context identifier must contain only A-Z, 0-9, and '_' characters and be shorter than 40 chars"
        )
    return normalized_identifier


def _normalize_description(description: str | None) -> str | None:
    normalized_description: str | None = description.strip() if isinstance(description, str) else None
    if normalized_description == "":
        return None
    if normalized_description is None:
        return None
    if "\n" in normalized_description or "\r" in normalized_description:
        raise SubmissionContextError("Submission context description must be a single line")
    if len(normalized_description) >= 80:
        raise SubmissionContextError("Submission context description must be shorter than 80 characters")
    return normalized_description


def _parse_submission_timestamp(value: object) -> datetime:
    """Parse submission timestamps accepted at the config input."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise SubmissionContextError("Submission context timestamp must be a valid ISO-8601 datetime string") from exc

    raise SubmissionContextError("Submission context requires a timestamp")


def _resolve_identity_assignments(config: IngesterConfig) -> dict[str, dict[object, IdentityAssignment]]:
    """Load optional identity assignments from the ingester config input."""
    extras: dict[str, Any] = config.extra or {}
    raw_assignments = extras.get("identity_assignments")

    if raw_assignments is None:
        return {}
    if not isinstance(raw_assignments, dict):
        raise IdentityAssignmentError("Identity assignments must be a mapping of entity names to row assignments")

    assignments: dict[str, dict[object, IdentityAssignment]] = {}
    for entity_name, entity_assignments in raw_assignments.items():
        assignments[entity_name] = _resolve_entity_identity_assignments(entity_name, entity_assignments)

    return assignments


def _resolve_entity_identity_assignments(
    entity_name: object,
    entity_assignments: object,
) -> dict[object, IdentityAssignment]:
    """Normalize identity assignments for one entity."""
    if not isinstance(entity_name, str) or not entity_name.strip():
        raise IdentityAssignmentError("Identity assignment entity names must be non-empty strings")
    if not isinstance(entity_assignments, dict):
        raise IdentityAssignmentError(f"Identity assignments for '{entity_name}' must be a row-to-assignment mapping")

    return {
        row_index: _resolve_identity_assignment(entity_name, row_index, assignment) for row_index, assignment in entity_assignments.items()
    }


def _resolve_identity_assignment(entity_name: str, row_index: object, assignment: object) -> IdentityAssignment:
    """Normalize one row identity assignment."""
    if isinstance(assignment, IdentityAssignment):
        return assignment
    if not isinstance(assignment, dict):
        raise IdentityAssignmentError(f"Identity assignment for '{entity_name}' row '{row_index}' must be a dict or IdentityAssignment")

    state = assignment.get("state")
    try:
        normalized_state = ChangeRowState(state)
    except ValueError as exc:
        raise IdentityAssignmentError(f"Identity assignment for '{entity_name}' row '{row_index}' has invalid state '{state}'") from exc

    target_id = assignment.get("target_id")
    if target_id is not None and not isinstance(target_id, int):
        raise IdentityAssignmentError(f"Identity assignment for '{entity_name}' row '{row_index}' target_id must be an integer")

    note = assignment.get("note")
    if note is not None and not isinstance(note, str):
        raise IdentityAssignmentError(f"Identity assignment for '{entity_name}' row '{row_index}' note must be a string")

    return IdentityAssignment(state=normalized_state, target_id=target_id, note=note)


def _resolve_deploy_strategy(config: IngesterConfig) -> Any | None:
    """Resolve the optional deploy-rendering strategy from the ingester input."""
    extras: dict[str, Any] = config.extra or {}
    try:
        return resolve_deploy_artifact_strategy(extras.get("deploy_strategy"))
    except ValueError as exc:
        raise DeployStrategyError(str(exc)) from exc
