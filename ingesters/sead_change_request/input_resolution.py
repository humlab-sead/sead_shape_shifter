"""Input and config resolution for the SEAD change request ingester."""

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from backend.app.ingesters.protocol import IngesterConfig
from ingesters.sead_change_request.contracts import (
    APPROVED_DATATYPES,
    CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE,
    ChangeRowState,
    IdentityAssignment,
    SourceTableBundle,
    SubmissionContext,
    TrustedProjectContext,
    is_valid_submission_identifier,
    normalize_submission_identifier,
)
from ingesters.sead_change_request.preparation import ResolvedInputs
from ingesters.sead_change_request.sql_builder import STAGING_TARGET_SCHEMA_KEY, resolve_deploy_artifact_strategy
from src.target_model.models import TargetModel

TRUSTED_PROJECT_CONTEXT_KEY = "trusted_project_context"
"""Config-extra key that carries the backend-owned project facts for one run."""

SIMS_SCOPE_OVERRIDE_KEY = "sims_scope_name"
"""Config-extra key a caller must not use to select the Change Request scope."""


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


class BusinessKeyValidationError(InputResolutionError):
    """Raised when the transformed delivery has no usable business keys."""

    scope = "business-keys"
    ingest_message = "Invalid business keys"


def resolve_inputs(config: IngesterConfig, source: object) -> ResolvedInputs:
    """Load and validate all expected inputs for the shared workflow.

    The source bundle is loaded first so its warnings can be preserved when
    later input resolution fails during validation.
    """
    bundle: SourceTableBundle = _resolve_source_bundle(config, source)

    try:
        target_model: TargetModel = _resolve_target_model(config)
        trusted_project_context: TrustedProjectContext | None = _resolve_trusted_project_context(config)
        submission_context: SubmissionContext = _resolve_submission_context(config, trusted_project_context)
        fallback_assignments: dict[str, dict[object, IdentityAssignment]] = _resolve_identity_assignments(config)
        mutable_fields_by_entity: dict[str, list[str]] = _resolve_mutable_fields_by_entity(config)
        existing_row_update_entities: set[str] | None = _resolve_existing_row_update_entities(config)
        staging_target_schema: str | None = _resolve_staging_target_schema(config)
        deploy_strategy: Any | None = _resolve_deploy_strategy(config, staging_target_schema)
    except InputResolutionError as exc:
        raise exc.with_warnings(bundle.warnings) from exc

    return ResolvedInputs(
        bundle=bundle,
        target_model=target_model,
        submission_context=submission_context,
        fallback_assignments=fallback_assignments,
        mutable_fields_by_entity=mutable_fields_by_entity,
        existing_row_update_entities=existing_row_update_entities,
        deploy_strategy=deploy_strategy,
        staging_target_schema=staging_target_schema,
        trusted_project_context=trusted_project_context,
    )


def _resolve_source_bundle(config: IngesterConfig, source: object) -> SourceTableBundle:
    """Resolve the internal bundle contract and reject the retired file input."""
    if isinstance(source, SourceTableBundle):
        return source

    if isinstance(source, (Path, str)):
        raise SourceBundleError(CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE)

    extras: dict[str, Any] = config.extra or {}

    source_bundle = extras.get("source_bundle")
    if isinstance(source_bundle, SourceTableBundle):
        return source_bundle

    table_mapping = source if isinstance(source, dict) else extras.get("tables")
    if isinstance(table_mapping, dict):
        return _build_source_bundle(table_mapping)

    raise SourceBundleError("Unsupported source type for sead_change_request ingestion")


def _build_source_bundle(tables: dict[object, object]) -> SourceTableBundle:
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

    return SourceTableBundle(tables=normalized_tables)


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


def _resolve_trusted_project_context(config: IngesterConfig) -> TrustedProjectContext | None:
    """Return the backend-owned project facts, or None when the caller supplied none.

    A caller-supplied ``sims_scope_name`` is rejected because the scope comes from the
    saved provider-schema pair, not from request configuration.
    """
    extras: dict[str, Any] = config.extra or {}
    if SIMS_SCOPE_OVERRIDE_KEY in extras:
        raise SubmissionContextError(
            f"'{SIMS_SCOPE_OVERRIDE_KEY}' cannot select the Change Request scope; " "the saved project provider-schema pair selects it"
        )

    raw_context = extras.get(TRUSTED_PROJECT_CONTEXT_KEY)
    if raw_context is None:
        return None
    if isinstance(raw_context, TrustedProjectContext):
        if not raw_context.scope_name.strip():
            raise SubmissionContextError("Trusted project context requires a non-empty scope name")
        return raw_context
    if not isinstance(raw_context, dict):
        raise SubmissionContextError(f"'{TRUSTED_PROJECT_CONTEXT_KEY}' must be a TrustedProjectContext")

    project_name = raw_context.get("project_name")
    provider_code = raw_context.get("provider_code")
    provider_schema = raw_context.get("provider_schema")
    scope_name = raw_context.get("scope_name")
    data_provider_id = raw_context.get("data_provider_id")
    raw_keys = raw_context.get("business_keys") or {}

    for label, value in (
        ("project_name", project_name),
        ("provider_code", provider_code),
        ("provider_schema", provider_schema),
        ("scope_name", scope_name),
    ):
        if not isinstance(value, str) or not value.strip():
            raise SubmissionContextError(f"Trusted project context requires a non-empty {label}")
    if not isinstance(data_provider_id, int) or isinstance(data_provider_id, bool) or data_provider_id <= 0:
        raise SubmissionContextError("Trusted project context requires a positive integer data_provider_id")
    if not isinstance(raw_keys, dict):
        raise SubmissionContextError("Trusted project context business_keys must map entity names to key lists")

    business_keys: dict[str, tuple[str, ...]] = {}
    for entity_name, key_columns in raw_keys.items():
        if not isinstance(entity_name, str) or not entity_name.strip():
            raise SubmissionContextError("Trusted project context business_keys requires non-empty entity names")
        if not isinstance(key_columns, (list, tuple)):
            raise SubmissionContextError(f"Trusted project context business_keys['{entity_name}'] must be a list of column names")
        business_keys[entity_name] = tuple(str(column) for column in key_columns)

    return TrustedProjectContext(
        project_name=project_name.strip(),
        provider_code=provider_code.strip(),
        provider_schema=provider_schema.strip(),
        scope_name=scope_name.strip(),
        data_provider_id=data_provider_id,
        business_keys=business_keys,
    )


def _resolve_submission_context(
    config: IngesterConfig,
    trusted_project_context: TrustedProjectContext | None = None,
) -> SubmissionContext:
    """Load submission-scoped metadata from the ingester config input."""
    extras: dict[str, Any] = config.extra or {}
    context_data = extras.get("submission_context")

    if isinstance(context_data, SubmissionContext):
        return _apply_trusted_context(
            context_data if context_data.run_id is not None else replace(context_data, run_id=str(uuid4())),
            trusted_project_context,
        )

    if not isinstance(context_data, dict):
        raise SubmissionContextError("Submission context is required; provide config.extra['submission_context']")

    _reject_conflicting_identity_inputs(context_data, trusted_project_context)

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
    run_id: str | None = _resolve_run_id(context_data)
    datatype: str | None = _optional_string(context_data, "datatype", SubmissionContextError)
    identifier: str | None = _optional_string(context_data, "identifier", SubmissionContextError)
    description: str | None = _optional_string(context_data, "description", SubmissionContextError)
    issue_identifier: str | None = _optional_string(context_data, "issue_identifier", SubmissionContextError)
    author: str | None = _optional_string(context_data, "author", SubmissionContextError)
    data_provider_code: str | None = _optional_string(context_data, "data_provider_code", SubmissionContextError)

    normalized_datatype: str = _normalize_datatype(datatype)
    normalized_identifier: str = _normalize_identifier(identifier)
    normalized_description: str | None = _normalize_description(description)

    return _apply_trusted_context(
        SubmissionContext(
            submission_name=submission_name.strip(),
            project_name=project_name.strip(),
            timestamp=parsed_timestamp,
            binding_set_uuid=binding_set_uuid,
            change_request_name=change_request_name,
            run_id=run_id,
            datatype=normalized_datatype,
            identifier=normalized_identifier,
            description=normalized_description,
            issue_identifier=issue_identifier.strip() if isinstance(issue_identifier, str) else None,
            author=author.strip() if isinstance(author, str) else None,
            data_provider_code=data_provider_code.strip() if isinstance(data_provider_code, str) else None,
        ),
        trusted_project_context,
    )


def _reject_conflicting_identity_inputs(
    context_data: dict[str, Any],
    trusted_project_context: TrustedProjectContext | None,
) -> None:
    """Reject caller identity values that disagree with the authorized saved project."""
    if trusted_project_context is None:
        return

    conflicts: list[str] = []
    provider_schema = context_data.get("provider_schema")
    if provider_schema is not None and (
        not isinstance(provider_schema, str) or provider_schema.strip() != trusted_project_context.provider_schema
    ):
        conflicts.append(f"provider_schema '{provider_schema}' does not match the saved provider schema")
    scope_name = context_data.get("scope_name")
    if scope_name is not None and (not isinstance(scope_name, str) or scope_name.strip() != trusted_project_context.scope_name):
        conflicts.append(f"scope_name '{scope_name}' does not match the saved provider-schema scope")

    if conflicts:
        raise SubmissionContextError("Submission context conflicts with the authorized project: " + "; ".join(conflicts))


def _apply_trusted_context(
    submission_context: SubmissionContext,
    trusted_project_context: TrustedProjectContext | None,
) -> SubmissionContext:
    """Replace caller identity values with the trusted project values.

    Caller values that agree with the saved project are accepted; values that disagree
    are rejected instead of silently replaced, so a tampered request cannot change which
    project, provider, or scope a run uses.
    """
    if trusted_project_context is None:
        return submission_context

    conflicts: list[str] = []
    if submission_context.project_name.strip() != trusted_project_context.project_name:
        conflicts.append(
            f"project_name '{submission_context.project_name}' does not match the authorized project "
            f"'{trusted_project_context.project_name}'"
        )
    if submission_context.data_provider_code and submission_context.data_provider_code.strip() != trusted_project_context.provider_code:
        conflicts.append(
            f"data_provider_code '{submission_context.data_provider_code}' does not match the saved provider "
            f"'{trusted_project_context.provider_code}'"
        )
    if submission_context.scope_name and submission_context.scope_name.strip() != trusted_project_context.scope_name:
        conflicts.append(f"scope_name '{submission_context.scope_name}' does not match the saved provider-schema scope")

    if conflicts:
        raise SubmissionContextError("Submission context conflicts with the authorized project: " + "; ".join(conflicts))

    return replace(
        submission_context,
        project_name=trusted_project_context.project_name,
        data_provider_code=trusted_project_context.provider_code,
        scope_name=trusted_project_context.scope_name,
    )


def _resolve_run_id(context_data: dict[str, Any]) -> str | None:
    """Return a persisted run ID, or mint a fresh one when absent.

    The persisted value is authoritative for retries; a missing value mints a
    new UUID so each intentional execution gets a distinct idempotency key.
    """
    persisted: str | None = _optional_string(context_data, "run_id", SubmissionContextError)
    return persisted if persisted else str(uuid4())


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


def _resolve_staging_target_schema(config: IngesterConfig) -> str | None:
    """Resolve the optional explicit schema used by the inline staging strategy."""
    extras: dict[str, Any] = config.extra or {}
    raw_schema = extras.get(STAGING_TARGET_SCHEMA_KEY)
    if raw_schema is None:
        return None
    if not isinstance(raw_schema, str):
        raise DeployStrategyError(f"'{STAGING_TARGET_SCHEMA_KEY}' must be a string when provided")
    return raw_schema


def _resolve_deploy_strategy(config: IngesterConfig, staging_target_schema: str | None = None) -> Any | None:
    """Resolve the optional deploy-rendering strategy from the ingester input."""
    extras: dict[str, Any] = config.extra or {}
    try:
        return resolve_deploy_artifact_strategy(extras.get("deploy_strategy"), staging_target_schema=staging_target_schema)
    except ValueError as exc:
        raise DeployStrategyError(str(exc)) from exc


def _resolve_mutable_fields_by_entity(config: IngesterConfig) -> dict[str, list[str]]:
    """Resolve optional mutable-field comparison scope per entity."""
    extras: dict[str, Any] = config.extra or {}
    raw = extras.get("mutable_fields_by_entity")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise InputResolutionError("mutable_fields_by_entity must be a mapping of entity names to field lists")

    resolved: dict[str, list[str]] = {}
    for entity_name, fields in raw.items():
        if not isinstance(entity_name, str) or not entity_name.strip():
            raise InputResolutionError("mutable_fields_by_entity keys must be non-empty strings")
        if not isinstance(fields, list):
            raise InputResolutionError(f"mutable_fields_by_entity['{entity_name}'] must be a list of field names")

        normalized_fields: list[str] = []
        for field_name in fields:
            if not isinstance(field_name, str) or not field_name.strip():
                raise InputResolutionError(f"mutable_fields_by_entity['{entity_name}'] entries must be non-empty strings")
            normalized_fields.append(field_name.strip())

        resolved[entity_name.strip()] = normalized_fields

    return resolved


def _resolve_existing_row_update_entities(config: IngesterConfig) -> set[str] | None:
    """Resolve the optional first-slice allowlist for existing-row updates."""
    extras: dict[str, Any] = config.extra or {}
    raw = extras.get("existing_row_update_entities")
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise InputResolutionError("existing_row_update_entities must be a list of entity names")

    resolved: set[str] = set()
    for entity_name in raw:
        if not isinstance(entity_name, str) or not entity_name.strip():
            raise InputResolutionError("existing_row_update_entities entries must be non-empty strings")
        resolved.add(entity_name.strip())
    return resolved
