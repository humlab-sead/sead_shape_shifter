"""SEAD change request ingester scaffold.

This module provides the initial registry-visible scaffold for the
`sead_change_request` ingester. Delivery 1 implementation work will add the
DataFrame-first ingestion contract and SQL generation workflow in follow-up
changes.
"""

import gzip
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
from ingesters.sead_change_request.collision_checks import check_materialized_collisions
from ingesters.sead_change_request.confirmation import build_pending_confirmation_report
from ingesters.sead_change_request.contracts import (
    APPROVED_DATATYPES,
    ChangeRowState,
    IdentityAssignment,
    IdentityWorkPlan,
    PlannedTable,
    SourceTableBundle,
    SubmissionContext,
    is_valid_submission_identifier,
    normalize_submission_identifier,
    resolve_bundle_name,
)
from ingesters.sead_change_request.identity_resolution import resolve_planned_tables
from ingesters.sead_change_request.identity_work import build_identity_work_plan
from ingesters.sead_change_request.materialization import materialize_resolved_tables
from ingesters.sead_change_request.orchestration import SIMS_TARGET_ID_CAPABILITY_NOTE, orchestrate_identity_assignments
from ingesters.sead_change_request.package_builder import build_change_request_package
from ingesters.sead_change_request.planning import plan_table
from ingesters.sead_change_request.sql_builder import build_deploy_artifact, encode_bundle_file_content, resolve_deploy_artifact_strategy
from src.target_model.models import TargetModel
from src.utility import sanitize_columns


@Ingesters.register(key="sead_change_request")
class SeadChangeRequestIngester:
    """Scaffold ingester for SEAD change request generation."""

    def __init__(self, config: IngesterConfig) -> None:
        self.config = config

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

    def _coerce_source_bundle(self, source: object) -> SourceTableBundle:
        """Coerce the current protocol edge into the internal bundle contract."""
        extras = self.config.extra or {}

        if isinstance(source, SourceTableBundle):
            return source

        source_bundle = extras.get("source_bundle")
        if isinstance(source_bundle, SourceTableBundle):
            return source_bundle

        table_mapping = source if isinstance(source, dict) else extras.get("tables")
        if isinstance(table_mapping, dict):
            return self._build_source_bundle(table_mapping, source_name=str(source) if isinstance(source, (Path, str)) else "")

        if isinstance(source, (Path, str)):
            return self._load_source_bundle_from_path(Path(source))

        raise ValueError("Unsupported source type for sead_change_request ingestion")

    def _load_source_bundle_from_path(self, source_path: Path) -> SourceTableBundle:
        """Load an Excel workbook into the internal source-bundle contract."""
        if not source_path.exists():
            raise ValueError(f"Source file does not exist: {source_path}")
        if source_path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError(f"Unsupported source file format '{source_path.suffix}'; expected .xlsx or .xls")

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
            raise ValueError(f"No usable sheets were found in source file: {source_path}")

        return SourceTableBundle(tables=table_mapping, source_name=str(source_path), warnings=warnings)

    def _build_source_bundle(self, tables: dict[object, object], source_name: str = "") -> SourceTableBundle:
        """Build a validated source bundle from a raw table mapping."""
        normalized_tables: dict[str, pd.DataFrame] = {}

        if not tables:
            raise ValueError("No source tables were provided")

        for table_name, frame in tables.items():
            if not isinstance(table_name, str) or not table_name.strip():
                raise ValueError("Source table names must be non-empty strings")
            if not isinstance(frame, pd.DataFrame):
                raise ValueError(f"Source table '{table_name}' must be a pandas DataFrame")

            normalized_tables[table_name] = frame

        return SourceTableBundle(tables=normalized_tables, source_name=source_name)

    def _coerce_target_model(self) -> TargetModel:
        """Load the target model from the ingester config boundary."""
        extras = self.config.extra or {}
        target_model_data = extras.get("target_model")

        if isinstance(target_model_data, TargetModel):
            return target_model_data
        if isinstance(target_model_data, dict):
            return TargetModel.model_validate(target_model_data)

        raise ValueError("Target model is required; provide config.extra['target_model'] as a dict or TargetModel")

    def _coerce_submission_context(self) -> SubmissionContext:
        """Load submission-scoped metadata from the ingester config boundary."""
        extras = self.config.extra or {}
        context_data = extras.get("submission_context")

        if isinstance(context_data, SubmissionContext):
            return context_data

        if not isinstance(context_data, dict):
            raise ValueError("Submission context is required; provide config.extra['submission_context']")

        submission_name = context_data.get("submission_name") or self.config.submission_name
        project_name = context_data.get("project_name")
        timestamp = context_data.get("timestamp")

        if not isinstance(submission_name, str) or not submission_name.strip():
            raise ValueError("Submission context requires a non-empty submission_name")
        if not isinstance(project_name, str) or not project_name.strip():
            raise ValueError("Submission context requires a non-empty project_name")

        parsed_timestamp = self._parse_submission_timestamp(timestamp)

        binding_set_uuid = context_data.get("binding_set_uuid")
        change_request_name = context_data.get("change_request_name")
        datatype = context_data.get("datatype")
        identifier = context_data.get("identifier")
        description = context_data.get("description")
        issue_number = context_data.get("issue_number")
        author = context_data.get("author")

        if binding_set_uuid is not None and not isinstance(binding_set_uuid, str):
            raise ValueError("Submission context binding_set_uuid must be a string when provided")
        if change_request_name is not None and not isinstance(change_request_name, str):
            raise ValueError("Submission context change_request_name must be a string when provided")
        if datatype is not None and not isinstance(datatype, str):
            raise ValueError("Submission context datatype must be a string when provided")
        if identifier is not None and not isinstance(identifier, str):
            raise ValueError("Submission context identifier must be a string when provided")
        if description is not None and not isinstance(description, str):
            raise ValueError("Submission context description must be a string when provided")
        if issue_number is not None and not isinstance(issue_number, str):
            raise ValueError("Submission context issue_number must be a string when provided")
        if author is not None and not isinstance(author, str):
            raise ValueError("Submission context author must be a string when provided")

        if not isinstance(datatype, str) or not datatype.strip():
            raise ValueError("Submission context requires a non-empty datatype")
        normalized_datatype = datatype.strip().lower()
        if normalized_datatype not in APPROVED_DATATYPES:
            raise ValueError(
                "Submission context datatype must be one of: " + ", ".join(sorted(APPROVED_DATATYPES))
            )

        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("Submission context requires a non-empty identifier")
        normalized_identifier = normalize_submission_identifier(identifier)
        if not is_valid_submission_identifier(normalized_identifier):
            raise ValueError(
                "Submission context identifier must contain only A-Z, 0-9, and '_' characters and be shorter than 40 chars"
            )

        normalized_description = description.strip() if isinstance(description, str) else None
        if normalized_description == "":
            normalized_description = None
        if normalized_description is not None:
            if "\n" in normalized_description or "\r" in normalized_description:
                raise ValueError("Submission context description must be a single line")
            if len(normalized_description) >= 80:
                raise ValueError("Submission context description must be shorter than 80 characters")

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

    def _parse_submission_timestamp(self, value: object) -> datetime:
        """Parse submission timestamps accepted at the config boundary."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Submission context timestamp must be a valid ISO-8601 datetime string") from exc

        raise ValueError("Submission context requires a timestamp")

    def _plan_bundle(
        self, bundle: SourceTableBundle, target_model: TargetModel
    ) -> tuple[list[PlannedTable], list[str], list[str], list[str]]:
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

        return planned_tables, errors, warnings, infos

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

    def _coerce_identity_assignments(self) -> dict[str, dict[object, IdentityAssignment]]:
        """Load optional identity assignments from the ingester config boundary."""
        extras = self.config.extra or {}
        raw_assignments = extras.get("identity_assignments")

        if raw_assignments is None:
            return {}
        if not isinstance(raw_assignments, dict):
            raise ValueError("Identity assignments must be a mapping of entity names to row assignments")

        assignments: dict[str, dict[object, IdentityAssignment]] = {}
        for entity_name, entity_assignments in raw_assignments.items():
            if not isinstance(entity_name, str) or not entity_name.strip():
                raise ValueError("Identity assignment entity names must be non-empty strings")
            if not isinstance(entity_assignments, dict):
                raise ValueError(f"Identity assignments for '{entity_name}' must be a row-to-assignment mapping")

            normalized_entity_assignments: dict[object, IdentityAssignment] = {}
            for row_index, assignment in entity_assignments.items():
                if isinstance(assignment, IdentityAssignment):
                    normalized_entity_assignments[row_index] = assignment
                    continue
                if not isinstance(assignment, dict):
                    raise ValueError(f"Identity assignment for '{entity_name}' row '{row_index}' must be a dict or IdentityAssignment")

                state = assignment.get("state")
                try:
                    normalized_state = ChangeRowState(state)
                except Exception as exc:  # pylint: disable=broad-except
                    raise ValueError(f"Identity assignment for '{entity_name}' row '{row_index}' has invalid state '{state}'") from exc

                target_id = assignment.get("target_id")
                if target_id is not None and not isinstance(target_id, int):
                    raise ValueError(f"Identity assignment for '{entity_name}' row '{row_index}' target_id must be an integer")

                note = assignment.get("note")
                if note is not None and not isinstance(note, str):
                    raise ValueError(f"Identity assignment for '{entity_name}' row '{row_index}' note must be a string")

                normalized_entity_assignments[row_index] = IdentityAssignment(
                    state=normalized_state,
                    target_id=target_id,
                    note=note,
                )

            assignments[entity_name] = normalized_entity_assignments

        return assignments

    def _get_client(self, key: str) -> Any | None:
        """Get an optional injected client from config.extra."""
        extras = self.config.extra or {}
        client = extras.get(key)
        return client

    def _coerce_deploy_strategy(self) -> Any | None:
        """Resolve the optional deploy-rendering strategy from the ingester boundary."""
        return resolve_deploy_artifact_strategy(self._get_client("deploy_strategy"))

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

    async def validate(self, excel_file: Path | str) -> ValidationResult:
        try:
            bundle = self._coerce_source_bundle(excel_file)
        except ValueError as exc:
            logger.warning(f"SEAD change request validation failed at input boundary: {exc}")
            return ValidationResult(is_valid=False, errors=[str(exc)], warnings=[], infos=[])

        try:
            target_model = self._coerce_target_model()
        except ValueError as exc:
            logger.warning(f"SEAD change request validation failed at target-model boundary: {exc}")
            return ValidationResult(is_valid=False, errors=[str(exc)], warnings=list(bundle.warnings), infos=[])

        try:
            submission_context = self._coerce_submission_context()
        except ValueError as exc:
            logger.warning(f"SEAD change request validation failed at submission-context boundary: {exc}")
            return ValidationResult(is_valid=False, errors=[str(exc)], warnings=list(bundle.warnings), infos=[])

        try:
            fallback_assignments = self._coerce_identity_assignments()
        except ValueError as exc:
            logger.warning(f"SEAD change request validation failed at identity-assignment boundary: {exc}")
            return ValidationResult(is_valid=False, errors=[str(exc)], warnings=list(bundle.warnings), infos=[])

        try:
            self._coerce_deploy_strategy()
        except ValueError as exc:
            logger.warning(f"SEAD change request validation failed at deploy-strategy boundary: {exc}")
            return ValidationResult(is_valid=False, errors=[str(exc)], warnings=list(bundle.warnings), infos=[])

        planned_tables, planning_errors, warnings, planning_infos = self._plan_bundle(bundle, target_model)
        work_plan = build_identity_work_plan(planned_tables)
        orchestration_result = await orchestrate_identity_assignments(
            planned_tables,
            submission_context,
            sims_client=self._get_client("sims_client"),
            reconciliation_client=self._get_client("reconciliation_client"),
            fallback_assignments=fallback_assignments,
        )
        if orchestration_result.binding_set_uuid and not submission_context.binding_set_uuid:
            submission_context.binding_set_uuid = orchestration_result.binding_set_uuid
        resolution_result = resolve_planned_tables(planned_tables, target_model, orchestration_result.assignments)
        materialization_result = materialize_resolved_tables(resolution_result, target_model)
        validation_errors = planning_errors + materialization_result.diagnostics
        if resolution_result.blocked_rows:
            validation_errors.extend(resolution_result.diagnostics)
        else:
            warnings.extend(resolution_result.diagnostics)
        pending_confirmation_report = None
        if (
            orchestration_result.binding_set_state
            and orchestration_result.binding_set_state != "confirmed"
            and resolution_result.blocked_rows
        ):
            pending_confirmation_report = asdict(
                build_pending_confirmation_report(
                    submission_context,
                    resolution_result,
                    binding_set_state=orchestration_result.binding_set_state,
                )
            )

        total_rows = sum(len(frame.index) for frame in bundle.tables.values())
        infos = [
            f"Validated DataFrame-first handoff with {len(bundle.tables)} table(s)",
            f"Validated {total_rows} row(s) across the source bundle",
            f"Validated target model with {len(target_model.entities)} entity definition(s)",
            (f"Validated submission context for '{submission_context.submission_name}' " f"in project '{submission_context.project_name}'"),
        ]
        if bundle.source_name:
            infos.append(f"Source bundle name: {bundle.source_name}")
        infos.append(f"Submission timestamp: {submission_context.timestamp.isoformat()}")
        if submission_context.binding_set_uuid:
            infos.append(f"Binding Set UUID: {submission_context.binding_set_uuid}")
        if submission_context.change_request_name:
            infos.append(f"Requested CR name: {submission_context.change_request_name}")
        infos.extend(planning_infos)
        infos.extend(self._summarize_identity_work(work_plan))
        infos.append(f"Resolved identity tables: {len(resolution_result.tables)}")
        infos.append(f"Blocked rows after identity resolution: {resolution_result.blocked_rows}")
        infos.append(f"Materialized tables: {len(materialization_result.tables)}")

        logger.info(
            f"Validated SEAD change request source bundle with {len(bundle.tables)} table(s), {total_rows} row(s), "
            f"and {len(planned_tables)} planned table(s)"
        )
        return ValidationResult(
            is_valid=len(validation_errors) == 0,
            errors=validation_errors,
            warnings=warnings,
            infos=infos,
            pending_confirmation_report=pending_confirmation_report,
        )

    async def ingest(self, excel_file: Path | str, validate_first: bool = True) -> IngestionResult:
        if validate_first:
            validation = await self.validate(excel_file)
            if not validation.is_valid:
                return IngestionResult(
                    success=False,
                    message="Validation failed",
                    submission_id=None,
                    tables_processed=0,
                    records_inserted=0,
                    error_details="\n".join(validation.errors),
                )

        try:
            bundle = self._coerce_source_bundle(excel_file)
        except ValueError as exc:
            logger.warning(f"SEAD change request ingest failed at input boundary: {exc}")
            return IngestionResult(
                success=False,
                message="Invalid source bundle",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=str(exc),
            )

        try:
            target_model = self._coerce_target_model()
        except ValueError as exc:
            logger.warning(f"SEAD change request ingest failed at target-model boundary: {exc}")
            return IngestionResult(
                success=False,
                message="Invalid target model",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=str(exc),
            )

        try:
            submission_context = self._coerce_submission_context()
        except ValueError as exc:
            logger.warning(f"SEAD change request ingest failed at submission-context boundary: {exc}")
            return IngestionResult(
                success=False,
                message="Invalid submission context",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=str(exc),
            )

        try:
            fallback_assignments = self._coerce_identity_assignments()
        except ValueError as exc:
            logger.warning(f"SEAD change request ingest failed at identity-assignment boundary: {exc}")
            return IngestionResult(
                success=False,
                message="Invalid identity assignments",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=str(exc),
            )

        try:
            deploy_strategy = self._coerce_deploy_strategy()
        except ValueError as exc:
            logger.warning(f"SEAD change request ingest failed at deploy-strategy boundary: {exc}")
            return IngestionResult(
                success=False,
                message="Invalid deploy strategy",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=str(exc),
            )

        planned_tables, planning_errors, _, _ = self._plan_bundle(bundle, target_model)
        if planning_errors:
            return IngestionResult(
                success=False,
                message="Validation failed",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details="\n".join(planning_errors),
            )

        orchestration_result = await orchestrate_identity_assignments(
            planned_tables,
            submission_context,
            sims_client=self._get_client("sims_client"),
            reconciliation_client=self._get_client("reconciliation_client"),
            fallback_assignments=fallback_assignments,
        )
        if orchestration_result.binding_set_uuid and not submission_context.binding_set_uuid:
            submission_context.binding_set_uuid = orchestration_result.binding_set_uuid
        resolution_result = resolve_planned_tables(planned_tables, target_model, orchestration_result.assignments)
        if resolution_result.blocked_rows:
            pending_confirmation_report = None
            if orchestration_result.binding_set_state and orchestration_result.binding_set_state != "confirmed":
                pending_confirmation_report = asdict(
                    build_pending_confirmation_report(
                        submission_context,
                        resolution_result,
                        binding_set_state=orchestration_result.binding_set_state,
                    )
                )
            return IngestionResult(
                success=False,
                message=(
                    "Binding Set confirmation incomplete"
                    if pending_confirmation_report is not None
                    else (
                        "SIMS target ID allocation capability incomplete"
                        if self._is_sims_target_id_capability_gap(resolution_result.diagnostics)
                        else "Identity resolution incomplete"
                    )
                ),
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details="\n".join(resolution_result.diagnostics),
                deploy_artifact=None,
                pending_confirmation_report=pending_confirmation_report,
            )

        materialization_result = materialize_resolved_tables(resolution_result, target_model)
        if materialization_result.diagnostics:
            return IngestionResult(
                success=False,
                message="PK/FK materialization incomplete",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details="\n".join(materialization_result.diagnostics),
            )

        collision_checker = self._get_client("collision_checker")
        if collision_checker is not None:
            collision_result = await check_materialized_collisions(
                materialization_result,
                resolution_result,
                target_model,
                collision_checker,
            )
            if collision_result.has_conflicts:
                return IngestionResult(
                    success=False,
                    message="Target collision checks failed",
                    submission_id=None,
                    tables_processed=0,
                    records_inserted=0,
                    error_details="\n".join(collision_result.diagnostics),
                )

        change_package = build_change_request_package(materialization_result, resolution_result)
        package_table_count = len(change_package.tables)
        insert_row_count = sum(len(table.frame.index) for table in change_package.tables.values())
        try:
            deploy_artifact = build_deploy_artifact(
                change_package,
                target_model,
                submission_context,
                strategy=deploy_strategy,
            )
        except NotImplementedError as exc:
            logger.warning(f"SEAD change request ingest failed at deploy-rendering boundary: {exc}")
            return IngestionResult(
                success=False,
                message="Deploy strategy not implemented",
                submission_id=None,
                tables_processed=0,
                records_inserted=0,
                error_details=str(exc),
            )

        sims_client = self._get_client("sims_client")
        if sims_client is not None and submission_context.binding_set_uuid and submission_context.change_request_name:
            await sims_client.associate_change_request(
                submission_context.binding_set_uuid,
                submission_context.change_request_name,
            )
            deploy_artifact.metadata["change_request_associated"] = True

        table_count = len(planned_tables)
        deploy_artifact_payload = asdict(deploy_artifact)
        artifact_directory = self._emit_artifact_bundle(deploy_artifact_payload, submission_context)
        logger.info(f"Prepared SEAD change request ingestion scaffold for {table_count} planned table(s)")
        return IngestionResult(
            success=True,
            message=f"Deploy artifact emitted to '{artifact_directory}'",
            submission_id=None,
            tables_processed=package_table_count,
            records_inserted=insert_row_count,
            error_details=None,
            deploy_artifact=deploy_artifact_payload,
            pending_confirmation_report=None,
        )
