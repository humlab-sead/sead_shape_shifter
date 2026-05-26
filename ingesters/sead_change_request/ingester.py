"""SEAD change request ingester scaffold.

This module provides the initial registry-visible scaffold for the
`sead_change_request` ingester. Delivery 1 implementation work will add the
DataFrame-first ingestion contract and SQL generation workflow in follow-up
changes.
"""

import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.ingesters.protocol import IngesterConfig, IngesterMetadata, IngestionResult, ValidationResult
from backend.app.ingesters.registry import Ingesters
from ingesters.sead_change_request.collision_checks import CollisionCheckResult, check_materialized_collisions
from ingesters.sead_change_request.contracts import (
    APPROVED_DATATYPES,
    ChangeRequestPackage,
    ChangeRowState,
    DeployArtifact,
    IdentityAssignment,
    IdentityWorkPlan,
    PlannedTable,
    SourceTableBundle,
    SubmissionContext,
    is_valid_submission_identifier,
    normalize_submission_identifier,
    resolve_bundle_name,
)
from ingesters.sead_change_request.orchestration import SIMS_TARGET_ID_CAPABILITY_NOTE
from ingesters.sead_change_request.package_builder import build_change_request_package
from ingesters.sead_change_request.planning import plan_table
from ingesters.sead_change_request.preparation import (
    PlannedBundle,
    PreparationResult,
    ResolvedInputs,
    prepare_change_request,
)
from ingesters.sead_change_request.sql_builder import build_deploy_artifact, encode_bundle_file_content, resolve_deploy_artifact_strategy
from src.target_model.models import TargetModel
from src.utility import sanitize_columns


class SeadChangeRequestError(Exception):
    """Base error for SEAD change request ingestion."""


class InputResolutionError(SeadChangeRequestError):
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


@Ingesters.register(key="sead_change_request")
class SeadChangeRequestIngester:
    """Scaffold ingester for SEAD change request generation."""

    def __init__(self, config: IngesterConfig) -> None:
        self.config: IngesterConfig = config

    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="sead_change_request",
            name="SEAD Change Request",
            description="Generate SEAD change request artifacts from normalized data",
            version="0.1.0",
            supported_formats=["xlsx", "xls"],
            requires_config=True,
        )

    def _resolve_inputs(self, source: object) -> ResolvedInputs:
        """Load and validate all expected inputs for the shared workflow.

        The source bundle is loaded first so its warnings can be preserved when
        later input resolution fails during validation.
        """
        bundle: SourceTableBundle = self._resolve_source_bundle(source)

        try:
            target_model: TargetModel = self._resolve_target_model()
            submission_context: SubmissionContext = self._resolve_submission_context()
            fallback_assignments: dict[str, dict[object, IdentityAssignment]] = self._resolve_identity_assignments()
            deploy_strategy: Any | None = self._resolve_deploy_strategy()
        except InputResolutionError as exc:
            raise exc.with_warnings(bundle.warnings) from exc

        return ResolvedInputs(
            bundle=bundle,
            target_model=target_model,
            submission_context=submission_context,
            fallback_assignments=fallback_assignments,
            deploy_strategy=deploy_strategy,
        )

    def _resolve_source_bundle(self, source: object) -> SourceTableBundle:
        """Resolve the current protocol edge into the internal bundle contract."""
        extras = self.config.extra or {}

        if isinstance(source, SourceTableBundle):
            return source

        source_bundle = extras.get("source_bundle")
        if isinstance(source_bundle, SourceTableBundle):
            return source_bundle

        table_mapping = source if isinstance(source, dict) else extras.get("tables")
        if isinstance(table_mapping, dict):
            source_name = str(source) if isinstance(source, (Path, str)) else ""
            return self._build_source_bundle(table_mapping, source_name=source_name)

        if isinstance(source, (Path, str)):
            return self._load_source_bundle_from_path(Path(source))

        raise SourceBundleError("Unsupported source type for sead_change_request ingestion")

    def _load_source_bundle_from_path(self, source_path: Path) -> SourceTableBundle:
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

                frame = pd.read_excel(workbook, sheet_name=normalized_sheet_name)
                frame.columns = sanitize_columns(list(frame.columns))
                table_mapping[normalized_sheet_name] = frame

        if not table_mapping:
            raise SourceBundleError(f"No usable sheets were found in source file: {source_path}")

        return SourceTableBundle(tables=table_mapping, source_name=str(source_path), warnings=warnings)

    def _build_source_bundle(self, tables: dict[object, object], source_name: str = "") -> SourceTableBundle:
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

    def _resolve_target_model(self) -> TargetModel:
        """Load the target model from the ingester config input."""
        extras = self.config.extra or {}
        target_model_data = extras.get("target_model")

        if isinstance(target_model_data, TargetModel):
            return target_model_data
        if isinstance(target_model_data, dict):
            try:
                return TargetModel.model_validate(target_model_data)
            except ValueError as exc:
                raise TargetModelError(str(exc)) from exc

        raise TargetModelError("Target model is required; provide config.extra['target_model'] as a dict or TargetModel")

    def _resolve_submission_context(self) -> SubmissionContext:
        """Load submission-scoped metadata from the ingester config input."""
        extras = self.config.extra or {}
        context_data = extras.get("submission_context")

        if isinstance(context_data, SubmissionContext):
            return context_data

        if not isinstance(context_data, dict):
            raise SubmissionContextError("Submission context is required; provide config.extra['submission_context']")

        submission_name = context_data.get("submission_name") or self.config.submission_name
        project_name = context_data.get("project_name")
        timestamp = context_data.get("timestamp")

        if not isinstance(submission_name, str) or not submission_name.strip():
            raise SubmissionContextError("Submission context requires a non-empty submission_name")
        if not isinstance(project_name, str) or not project_name.strip():
            raise SubmissionContextError("Submission context requires a non-empty project_name")

        parsed_timestamp = self._parse_submission_timestamp(timestamp)

        binding_set_uuid = self._optional_string(context_data, "binding_set_uuid", SubmissionContextError)
        change_request_name = self._optional_string(context_data, "change_request_name", SubmissionContextError)
        datatype = self._optional_string(context_data, "datatype", SubmissionContextError)
        identifier = self._optional_string(context_data, "identifier", SubmissionContextError)
        description = self._optional_string(context_data, "description", SubmissionContextError)
        issue_number = self._optional_string(context_data, "issue_number", SubmissionContextError)
        author = self._optional_string(context_data, "author", SubmissionContextError)

        normalized_datatype = self._normalize_datatype(datatype)
        normalized_identifier = self._normalize_identifier(identifier)
        normalized_description = self._normalize_description(description)

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

    @staticmethod
    def _optional_string(
        data: dict[str, Any],
        field_name: str,
        error_type: type[InputResolutionError],
    ) -> str | None:
        """Return an optional string config value or raise an input error."""
        value = data.get(field_name)
        if value is not None and not isinstance(value, str):
            readable_field_name = field_name.replace("_", " ")
            raise error_type(f"Submission context {readable_field_name} must be a string when provided")
        return value

    @staticmethod
    def _normalize_datatype(datatype: str | None) -> str:
        if not isinstance(datatype, str) or not datatype.strip():
            raise SubmissionContextError("Submission context requires a non-empty datatype")

        normalized_datatype = datatype.strip().lower()
        if normalized_datatype not in APPROVED_DATATYPES:
            raise SubmissionContextError("Submission context datatype must be one of: " + ", ".join(sorted(APPROVED_DATATYPES)))
        return normalized_datatype

    @staticmethod
    def _normalize_identifier(identifier: str | None) -> str:
        if not isinstance(identifier, str) or not identifier.strip():
            raise SubmissionContextError("Submission context requires a non-empty identifier")

        normalized_identifier = normalize_submission_identifier(identifier)
        if not is_valid_submission_identifier(normalized_identifier):
            raise SubmissionContextError(
                "Submission context identifier must contain only A-Z, 0-9, and '_' characters and be shorter than 40 chars"
            )
        return normalized_identifier

    @staticmethod
    def _normalize_description(description: str | None) -> str | None:
        normalized_description = description.strip() if isinstance(description, str) else None
        if normalized_description == "":
            return None
        if normalized_description is None:
            return None
        if "\n" in normalized_description or "\r" in normalized_description:
            raise SubmissionContextError("Submission context description must be a single line")
        if len(normalized_description) >= 80:
            raise SubmissionContextError("Submission context description must be shorter than 80 characters")
        return normalized_description

    def _parse_submission_timestamp(self, value: object) -> datetime:
        """Parse submission timestamps accepted at the config input."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise SubmissionContextError("Submission context timestamp must be a valid ISO-8601 datetime string") from exc

        raise SubmissionContextError("Submission context requires a timestamp")

    def _plan_bundle(self, bundle: SourceTableBundle, target_model: TargetModel) -> PlannedBundle:
        """Plan all source tables against the target model and collect diagnostics."""
        planned_tables: list[PlannedTable] = []
        errors: list[str] = []
        warnings: list[str] = list(bundle.warnings)
        infos: list[str] = []

        for entity_name, frame in bundle.tables.items():
            entity_spec = target_model.entities.get(entity_name)
            if entity_spec is None:
                errors.append(f"Source table '{entity_name}' is not present in the target model")
                continue

            try:
                planned_table = plan_table(entity_name, frame, entity_spec)
            except ValueError as exc:
                errors.append(str(exc))
                continue

            planned_tables.append(planned_table)
            warnings.extend(planned_table.diagnostics)

            action_counts = planned_table.planned_actions.value_counts(sort=False)
            action_summary = ", ".join(f"{int(count)} {action}" for action, count in action_counts.items())
            infos.append(f"Planned '{entity_name}': {action_summary}")

        return PlannedBundle(tables=planned_tables, errors=errors, warnings=warnings, infos=infos)

    def _summarize_identity_work(self, work_plan: IdentityWorkPlan) -> list[str]:
        """Summarize partitioned identity work for validation reporting."""
        return [
            (
                "Identity work queues: "
                f"{work_plan.total_existing_rows} existing, "
                f"{work_plan.total_allocation_rows} allocation, "
                f"{work_plan.total_reconciliation_rows} reconciliation, "
                f"{work_plan.total_bridge_rows} bridge"
            )
        ]

    def _resolve_identity_assignments(self) -> dict[str, dict[object, IdentityAssignment]]:
        """Load optional identity assignments from the ingester config input."""
        extras = self.config.extra or {}
        raw_assignments = extras.get("identity_assignments")

        if raw_assignments is None:
            return {}
        if not isinstance(raw_assignments, dict):
            raise IdentityAssignmentError("Identity assignments must be a mapping of entity names to row assignments")

        assignments: dict[str, dict[object, IdentityAssignment]] = {}
        for entity_name, entity_assignments in raw_assignments.items():
            assignments[entity_name] = self._resolve_entity_identity_assignments(entity_name, entity_assignments)

        return assignments

    def _resolve_entity_identity_assignments(
        self,
        entity_name: object,
        entity_assignments: object,
    ) -> dict[object, IdentityAssignment]:
        """Normalize identity assignments for one entity."""
        if not isinstance(entity_name, str) or not entity_name.strip():
            raise IdentityAssignmentError("Identity assignment entity names must be non-empty strings")
        if not isinstance(entity_assignments, dict):
            raise IdentityAssignmentError(f"Identity assignments for '{entity_name}' must be a row-to-assignment mapping")

        return {
            row_index: self._resolve_identity_assignment(entity_name, row_index, assignment)
            for row_index, assignment in entity_assignments.items()
        }

    @staticmethod
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

    def _get_client(self, key: str) -> Any | None:
        """Get an optional injected client from config.extra."""
        extras = self.config.extra or {}
        return extras.get(key)

    def _resolve_deploy_strategy(self) -> Any | None:
        """Resolve the optional deploy-rendering strategy from the ingester input."""
        try:
            return resolve_deploy_artifact_strategy(self._get_client("deploy_strategy"))
        except ValueError as exc:
            raise DeployStrategyError(str(exc)) from exc

    async def _prepare_change_request(self, source: Path | str) -> PreparationResult:
        """Run the shared preparation workflow after inputs are resolved."""
        inputs: ResolvedInputs = self._resolve_inputs(source)
        planned: PlannedBundle = self._plan_bundle(inputs.bundle, inputs.target_model)

        return await prepare_change_request(
            inputs,
            planned,
            sims_client=self._get_client("sims_client"),
            reconciliation_client=self._get_client("reconciliation_client"),
        )

    def _emit_artifact_bundle(self, deploy_artifact: dict[str, Any], submission_context: SubmissionContext) -> Path:
        """Write the Delivery 1 artifact bundle to the configured output folder."""
        output_root = Path(self.config.output_folder)
        artifact_directory = output_root / self._artifact_directory_name(submission_context)
        if artifact_directory.exists():
            shutil.rmtree(artifact_directory)
        artifact_directory.mkdir(parents=True, exist_ok=True)

        deploy_directory = artifact_directory / "deploy"
        revert_directory = artifact_directory / "revert"
        verify_directory = artifact_directory / "verify"
        deploy_directory.mkdir(parents=True, exist_ok=True)
        revert_directory.mkdir(parents=True, exist_ok=True)
        verify_directory.mkdir(parents=True, exist_ok=True)

        bundle_name = self._artifact_directory_name(submission_context)
        (deploy_directory / f"{bundle_name}.sql").write_text(str(deploy_artifact["deploy_sql"]), encoding="utf-8")
        (revert_directory / f"{bundle_name}.sql").write_text(str(deploy_artifact["revert_placeholder_sql"]), encoding="utf-8")
        (verify_directory / f"{bundle_name}.sql").write_text(str(deploy_artifact["verify_placeholder_sql"]), encoding="utf-8")
        (artifact_directory / "manifest.json").write_text(
            json.dumps(deploy_artifact["metadata_artifact"], indent=2, sort_keys=True),
            encoding="utf-8",
        )
        for relative_path, content in deploy_artifact.get("bundle_files", {}).items():
            artifact_path = artifact_directory / relative_path
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_bytes(encode_bundle_file_content(str(relative_path), str(content)))
        return artifact_directory

    def _artifact_directory_name(self, submission_context: SubmissionContext) -> str:
        """Build a filesystem-safe directory name for emitted Delivery 1 artifacts."""
        return resolve_bundle_name(submission_context)

    @staticmethod
    def _is_sims_target_id_capability_gap(diagnostics: list[str]) -> bool:
        """Detect the current backend SIMS limitation for Delivery 1 target-ID materialization."""
        return bool(diagnostics) and all(SIMS_TARGET_ID_CAPABILITY_NOTE in diagnostic for diagnostic in diagnostics)

    @staticmethod
    def _failure_details(diagnostics: list[str]) -> str:
        """Render diagnostics into the string format expected by IngestionResult."""
        return "\n".join(diagnostics)

    def _validation_input_failure(self, exc: InputResolutionError) -> ValidationResult:
        logger.warning("SEAD change request validation failed while resolving {} input: {}", exc.scope, exc.user_message)
        return ValidationResult(is_valid=False, errors=[exc.user_message], warnings=list(exc.warnings), infos=[])

    def _ingestion_input_failure(self, exc: InputResolutionError) -> IngestionResult:
        logger.warning("SEAD change request ingest failed while resolving {} input: {}", exc.scope, exc.user_message)
        return self._failed_ingestion(message=exc.ingest_message, details=exc.user_message)

    @staticmethod
    def _failed_ingestion(
        *,
        message: str,
        details: str,
        deploy_artifact: dict[str, Any] | None = None,
        pending_confirmation_report: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Build a standard failed ingestion result."""
        return IngestionResult(
            success=False,
            message=message,
            submission_id=None,
            tables_processed=0,
            records_inserted=0,
            error_details=details,
            deploy_artifact=deploy_artifact,
            pending_confirmation_report=pending_confirmation_report,
        )

    @staticmethod
    def _successful_ingestion(
        *, message: str, tables_processed: int, records_inserted: int, deploy_artifact: dict[str, Any]
    ) -> IngestionResult:
        """Build a standard successful ingestion result."""
        return IngestionResult(
            success=True,
            message=message,
            submission_id=None,
            tables_processed=tables_processed,
            records_inserted=records_inserted,
            error_details=None,
            deploy_artifact=deploy_artifact,
            pending_confirmation_report=None,
        )

    def _identity_resolution_message(self, diagnostics: list[str], pending_confirmation_report: dict[str, Any] | None) -> str:
        if pending_confirmation_report is not None:
            return "Binding Set confirmation incomplete"
        if self._is_sims_target_id_capability_gap(diagnostics):
            return "SIMS target ID allocation capability incomplete"
        return "Identity resolution incomplete"

    async def validate(self, excel_file: Path | str) -> ValidationResult:
        try:
            preparation: PreparationResult = await self._prepare_change_request(excel_file)
        except InputResolutionError as exc:
            return self._validation_input_failure(exc)

        validation_errors: list[str] = preparation.planned.errors + preparation.materialization_result.diagnostics
        warnings: list[str] = list(preparation.planned.warnings)
        if preparation.resolution_result.blocked_rows:
            validation_errors.extend(preparation.resolution_result.diagnostics)
        else:
            warnings.extend(preparation.resolution_result.diagnostics)

        total_rows: int = sum(len(frame.index) for frame in preparation.inputs.bundle.tables.values())
        infos: list[str] = [
            f"Validated DataFrame-first handoff with {len(preparation.inputs.bundle.tables)} table(s)",
            f"Validated {total_rows} row(s) across the source bundle",
            f"Validated target model with {len(preparation.inputs.target_model.entities)} entity definition(s)",
            (
                f"Validated submission context for '{preparation.inputs.submission_context.submission_name}' "
                f"in project '{preparation.inputs.submission_context.project_name}'"
            ),
        ]
        if preparation.inputs.bundle.source_name:
            infos.append(f"Source bundle name: {preparation.inputs.bundle.source_name}")
        infos.append(f"Submission timestamp: {preparation.inputs.submission_context.timestamp.isoformat()}")
        if preparation.inputs.submission_context.binding_set_uuid:
            infos.append(f"Binding Set UUID: {preparation.inputs.submission_context.binding_set_uuid}")
        if preparation.inputs.submission_context.change_request_name:
            infos.append(f"Requested CR name: {preparation.inputs.submission_context.change_request_name}")
        infos.extend(preparation.planned.infos)
        infos.extend(self._summarize_identity_work(preparation.planned.work_plan))
        infos.append(f"Resolved identity tables: {len(preparation.resolution_result.tables)}")
        infos.append(f"Blocked rows after identity resolution: {preparation.resolution_result.blocked_rows}")
        infos.append(f"Materialized tables: {len(preparation.materialization_result.tables)}")

        logger.info(
            "Validated SEAD change request source bundle with {} table(s), {} row(s), and {} planned table(s)",
            len(preparation.inputs.bundle.tables),
            total_rows,
            len(preparation.planned.tables),
        )
        return ValidationResult(
            is_valid=len(validation_errors) == 0,
            errors=validation_errors,
            warnings=warnings,
            infos=infos,
            pending_confirmation_report=preparation.pending_confirmation_report,
        )

    async def ingest(self, excel_file: Path | str, validate_first: bool = True) -> IngestionResult:
        if validate_first:
            validation: ValidationResult = await self.validate(excel_file)
            if not validation.is_valid:
                return self._failed_ingestion(
                    message="Validation failed",
                    details=self._failure_details(validation.errors),
                )

        try:
            preparation: PreparationResult = await self._prepare_change_request(excel_file)
        except InputResolutionError as exc:
            return self._ingestion_input_failure(exc)

        if preparation.planned.errors:
            return self._failed_ingestion(message="Validation failed", details=self._failure_details(preparation.planned.errors))

        if preparation.resolution_result.blocked_rows:
            return self._failed_ingestion(
                message=self._identity_resolution_message(
                    preparation.resolution_result.diagnostics,
                    preparation.pending_confirmation_report,
                ),
                details=self._failure_details(preparation.resolution_result.diagnostics),
                pending_confirmation_report=preparation.pending_confirmation_report,
            )

        if preparation.materialization_result.diagnostics:
            return self._failed_ingestion(
                message="PK/FK materialization incomplete",
                details=self._failure_details(preparation.materialization_result.diagnostics),
            )

        collision_checker = self._get_client("collision_checker")
        if collision_checker is not None:
            collision_result: CollisionCheckResult = await check_materialized_collisions(
                preparation.materialization_result,
                preparation.resolution_result,
                preparation.inputs.target_model,
                collision_checker,
            )
            if collision_result.has_conflicts:
                return self._failed_ingestion(
                    message="Target collision checks failed",
                    details=self._failure_details(collision_result.diagnostics),
                )

        change_package: ChangeRequestPackage = build_change_request_package(
            preparation.materialization_result,
            preparation.resolution_result,
        )
        package_table_count: int = len(change_package.tables)
        insert_row_count: int = sum(len(table.frame.index) for table in change_package.tables.values())

        try:
            deploy_artifact: DeployArtifact = build_deploy_artifact(
                change_package,
                preparation.inputs.target_model,
                preparation.inputs.submission_context,
                strategy=preparation.inputs.deploy_strategy,
            )
        except NotImplementedError as exc:
            logger.warning("SEAD change request ingest failed at deploy-rendering boundary: {}", exc)
            return self._failed_ingestion(message="Deploy strategy not implemented", details=str(exc))

        sims_client: Any | None = self._get_client("sims_client")
        if (
            sims_client is not None
            and preparation.inputs.submission_context.binding_set_uuid
            and preparation.inputs.submission_context.change_request_name
        ):
            await sims_client.associate_change_request(
                preparation.inputs.submission_context.binding_set_uuid,
                preparation.inputs.submission_context.change_request_name,
            )
            deploy_artifact.metadata["change_request_associated"] = True

        deploy_artifact_payload: dict[str, Any] = asdict(deploy_artifact)
        artifact_directory: Path = self._emit_artifact_bundle(
            deploy_artifact_payload,
            preparation.inputs.submission_context,
        )
        logger.info(
            "Prepared SEAD change request ingestion scaffold for {} planned table(s)",
            len(preparation.planned.tables),
        )
        return self._successful_ingestion(
            message=f"Deploy artifact emitted to '{artifact_directory}'",
            tables_processed=package_table_count,
            records_inserted=insert_row_count,
            deploy_artifact=deploy_artifact_payload,
        )
