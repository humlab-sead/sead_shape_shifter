"""Main protocol adapter for the SEAD change request ingester.

This module resolves external inputs, runs the shared preparation flow, and
turns the result into validation or ingestion output.
"""

import shutil
from collections.abc import Mapping
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from loguru import logger

from backend.app.ingesters.protocol import IngesterConfig, IngesterMetadata, IngestionResult, ValidationResult
from backend.app.ingesters.registry import get_ingester_registry
from ingesters.sead_change_request.artifact_writer import RunFolderCollisionError, reserve_run_folder, write_artifact_bundle
from ingesters.sead_change_request.collision_checks import CollisionCheckResult, check_projected_collisions
from ingesters.sead_change_request.contracts import (
    CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE,
    FIXED_PROVIDER_TARGET_TABLE,
    ChangeRequestPackage,
    DeployArtifact,
    SourceTableBundle,
    TrustedProjectContext,
)
from ingesters.sead_change_request.input_resolution import (
    BusinessKeyValidationError,
    InputResolutionError,
    SubmissionContextError,
    TargetModelError,
    _build_source_bundle,
    resolve_inputs,
)
from ingesters.sead_change_request.package_builder import build_change_request_package, build_staging_package
from ingesters.sead_change_request.planning import plan_bundle
from ingesters.sead_change_request.preparation import PreparationResult, ResolvedInputs, prepare_change_request
from ingesters.sead_change_request.result_builders import (
    build_ingestion_input_failure,
    build_validation_input_failure,
    build_validation_result,
    check_ingestion_preconditions,
    failure_details,
)
from ingesters.sead_change_request.sql_builder import build_deploy_artifact
from ingesters.sead_change_request.submission_tables import DERIVED_SUBMISSION_TABLES, build_submission_source_bundle
from src.business_keys import business_key_errors
from src.target_model.effective_identity import resolve_effective_identity


@get_ingester_registry().register(key="sead_change_request")
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
            supported_formats=[],
            requires_config=True,
        )

    def _get_client(self, key: str) -> Any | None:
        """Get an optional injected client from config.extra."""
        extras = self.config.extra or {}
        return extras.get(key)

    async def _prepare_change_request(self, bundle: SourceTableBundle) -> PreparationResult:
        """Run the shared preparation workflow for an in-memory source bundle."""
        inputs: ResolvedInputs = await self._resolve_inputs(bundle)
        return await self._prepare_resolved_inputs(inputs)

    async def _resolve_inputs(self, bundle: SourceTableBundle) -> ResolvedInputs:
        """Resolve and verify inputs without SIMS identity work or output writes."""
        inputs: ResolvedInputs = resolve_inputs(self.config, bundle)
        inputs = self._add_submission_tables(inputs)
        self._validate_business_keys(inputs)
        await self._verify_provider_row(inputs)
        return inputs

    async def _prepare_resolved_inputs(self, inputs: ResolvedInputs) -> PreparationResult:
        """Plan and prepare already-resolved inputs through the shared workflow."""
        planned = plan_bundle(
            inputs.bundle,
            inputs.target_model.entities,
            mutable_fields_by_entity=inputs.mutable_fields_by_entity,
            existing_row_update_entities=inputs.existing_row_update_entities,
            staging=inputs.is_staging,
        )

        return await prepare_change_request(
            inputs,
            planned,
            sims_client=self._get_client("sims_client"),
            reconciliation_client=self._get_client("reconciliation_client"),
            collision_checker=self._get_client("collision_checker"),
        )

    def _add_submission_tables(self, inputs: ResolvedInputs) -> ResolvedInputs:
        """Add the submission rows required by the target contract, using the trusted provider row."""
        if "submission" not in inputs.target_model.entities:
            return inputs

        missing_entities = sorted(DERIVED_SUBMISSION_TABLES.difference(inputs.target_model.entities))
        if missing_entities:
            raise TargetModelError("Submission target contract is missing entity or entities: " + ", ".join(missing_entities))

        trusted_project_context: TrustedProjectContext | None = inputs.trusted_project_context
        if trusted_project_context is None:
            raise SubmissionContextError("Change Request ingestion requires an authorized saved project with a fixed data provider row")

        try:
            bundle = build_submission_source_bundle(
                inputs.bundle,
                inputs.submission_context,
                trusted_project_context.data_provider_id,
            )
        except ValueError as exc:
            raise SubmissionContextError(str(exc)) from exc
        return replace(inputs, bundle=bundle)

    def _validate_business_keys(self, inputs: ResolvedInputs) -> None:
        """Reject a delivery whose tracked or reconciled project entities lack usable business keys.

        Runs on the complete transformed bundle before any target-database check or SIMS
        request, so an invalid key contract has no external effect.
        """
        trusted_project_context: TrustedProjectContext | None = inputs.trusted_project_context
        if trusted_project_context is None:
            return

        errors: list[str] = []
        for entity_name, declared_keys in trusted_project_context.business_keys.items():
            frame = inputs.bundle.tables.get(entity_name)
            entity_spec = inputs.target_model.entities.get(entity_name)
            if frame is None or entity_spec is None:
                continue
            identity_tracking = resolve_effective_identity(entity_spec).identity_tracking
            if identity_tracking == "reconciled" and not declared_keys:
                continue
            if identity_tracking not in {"tracked", "reconciled"}:
                continue
            errors.extend(
                business_key_errors(
                    entity_name,
                    declared_keys,
                    frame,
                    public_id=entity_spec.public_id,
                    entity_label="Reconciled entity" if identity_tracking == "reconciled" else "Tracked entity",
                )
            )

        if errors:
            raise BusinessKeyValidationError("\n".join(errors))

    async def _verify_provider_row(self, inputs: ResolvedInputs) -> None:
        """Confirm the trusted provider ID and code identify one existing SEAD provider row."""
        if "submission" not in inputs.target_model.entities:
            return

        trusted_project_context: TrustedProjectContext | None = inputs.trusted_project_context
        if trusted_project_context is None:
            raise SubmissionContextError("Change Request ingestion requires an authorized saved project with a fixed data provider row")

        collision_checker = self._get_client("collision_checker")
        if collision_checker is None:
            raise SubmissionContextError(
                "Change Request ingestion requires a target database connection to confirm the fixed data provider row"
            )

        provider_id = trusted_project_context.data_provider_id
        provider_code = trusted_project_context.provider_code
        matched = await collision_checker.row_exists(
            FIXED_PROVIDER_TARGET_TABLE,
            {"data_provider_id": provider_id, "data_provider_code": provider_code},
        )
        if not matched:
            raise SubmissionContextError(
                f"No SEAD data provider row matches data_provider_id {provider_id} and data_provider_code '{provider_code}'"
            )

    async def _validate_bundle(self, bundle: SourceTableBundle) -> ValidationResult:
        """Validate an in-memory source bundle through the shared preparation flow."""
        try:
            preparation: PreparationResult = await self._prepare_change_request(bundle)
        except InputResolutionError as exc:
            return build_validation_input_failure(exc)

        self._log_validation(preparation)
        return build_validation_result(preparation)

    async def validate_tables(self, tables: Mapping[str, pd.DataFrame], *, source_name: str = "") -> ValidationResult:
        """Validate normalized tables through the shared preparation flow.

        The adapter copies and sanitizes the supplied frames before the existing
        bundle validation runs. ``source_name`` is diagnostic metadata only.
        """
        try:
            bundle: SourceTableBundle = _build_source_bundle(tables, source_name=source_name)
        except InputResolutionError as exc:
            return build_validation_input_failure(exc)
        return await self._validate_bundle(bundle)

    async def validate(self, source: Path | str) -> ValidationResult:  # pylint: disable=unused-argument
        """Reject the retired Change Request file input without opening the source."""
        logger.warning("SEAD change request validation rejected retired file input")
        return ValidationResult(is_valid=False, errors=[CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE], warnings=[], infos=[])

    @staticmethod
    def _build_change_package(preparation: PreparationResult) -> ChangeRequestPackage:
        """Build the staging or direct package for the selected strategy."""
        if preparation.change_package is not None:
            return preparation.change_package
        if preparation.inputs.is_staging:
            return build_staging_package(
                preparation.resolution_result,
                preparation.planned.tables,
                preparation.inputs.target_model,
                str(preparation.inputs.staging_target_schema),
            )
        return build_change_request_package(
            preparation.projection_result,
            preparation.resolution_result,
            preparation.planned.tables,
        )

    @staticmethod
    def _log_validation(preparation: PreparationResult) -> None:
        """Log the source bundle and target-model counts used during validation."""
        logger.info(
            "Validated SEAD change request source bundle with {} table(s), {} row(s), and {} planned table(s)",
            len(preparation.inputs.bundle.tables),
            sum(len(frame.index) for frame in preparation.inputs.bundle.tables.values()),
            len(preparation.planned.tables),
        )

    async def ingest(self, source: Path | str, validate_first: bool = True) -> IngestionResult:  # pylint: disable=unused-argument
        """Reject the retired Change Request file input without opening the source."""
        logger.warning("SEAD change request ingest rejected retired file input")
        return IngestionResult.create_failed_result(
            message="File input retired",
            details=CHANGE_REQUEST_FILE_INPUT_RETIRED_MESSAGE,
        )

    async def ingest_tables(
        self,
        tables: Mapping[str, pd.DataFrame],
        *,
        source_name: str = "",
        validate_first: bool = True,
    ) -> IngestionResult:
        """Ingest normalized tables through the shared preparation and artifact flow.

        The adapter copies and sanitizes the supplied frames before the existing
        bundle workflow runs. ``source_name`` is diagnostic metadata only and is
        never opened or resolved as a path.
        """
        try:
            bundle: SourceTableBundle = _build_source_bundle(tables, source_name=source_name)
        except InputResolutionError as exc:
            if validate_first:
                validation_failure = build_validation_input_failure(exc)
                return IngestionResult.create_failed_result(
                    message="Validation failed",
                    details=failure_details(validation_failure.errors),
                )
            return build_ingestion_input_failure(exc)
        return await self._ingest_bundle(bundle, validate_first=validate_first)

    async def _ingest_bundle(self, bundle: SourceTableBundle, validate_first: bool = True) -> IngestionResult:
        """Ingest an in-memory source bundle through the shared preparation flow."""
        try:
            inputs: ResolvedInputs = await self._resolve_inputs(bundle)
        except InputResolutionError as exc:
            if validate_first:
                validation_failure = build_validation_input_failure(exc)
                return IngestionResult.create_failed_result(
                    message="Validation failed",
                    details=failure_details(validation_failure.errors),
                )
            return build_ingestion_input_failure(exc)

        run_id: str = inputs.submission_context.run_id or str(uuid4())
        try:
            run_folder: Path = reserve_run_folder(self.config.output_folder, run_id)
        except RunFolderCollisionError as exc:
            return IngestionResult.create_failed_result(
                message="Output folder collision",
                details=str(exc),
                scope_name=inputs.submission_context.scope_name,
                run_id=run_id,
            )

        result: IngestionResult | None = None
        try:
            result = await self._ingest_resolved(inputs, run_folder, validate_first=validate_first)
            return result
        finally:
            if result is None or not result.success:
                shutil.rmtree(run_folder, ignore_errors=True)

    async def _ingest_resolved(
        self,
        inputs: ResolvedInputs,
        run_folder: Path,
        validate_first: bool,
    ) -> IngestionResult:
        """Run preparation through bundle emission inside the reserved run folder."""
        preparation: PreparationResult = await self._prepare_resolved_inputs(inputs)

        if validate_first:
            self._log_validation(preparation)
            validation: ValidationResult = build_validation_result(preparation)
            if not validation.is_valid:
                return IngestionResult.create_failed_result(
                    message="Validation failed",
                    details=failure_details(validation.errors),
                    scope_name=preparation.inputs.submission_context.scope_name,
                    run_id=preparation.inputs.submission_context.run_id,
                )

        precondition_failure = check_ingestion_preconditions(preparation)
        if precondition_failure is not None:
            return precondition_failure

        collision_checker = self._get_client("collision_checker")
        if collision_checker is not None:
            collision_result: CollisionCheckResult = await check_projected_collisions(
                preparation.projection_result,
                preparation.resolution_result,
                preparation.inputs.target_model,
                collision_checker,
                pending=preparation.pending_deployment if preparation.inputs.is_staging else None,
            )
            if collision_result.has_conflicts:
                return IngestionResult.create_failed_result(
                    message="Target collision checks failed",
                    details=failure_details(collision_result.diagnostics),
                    scope_name=preparation.inputs.submission_context.scope_name,
                    run_id=preparation.inputs.submission_context.run_id,
                )

        change_package: ChangeRequestPackage = self._build_change_package(preparation)
        package_table_count: int = len(change_package.tables)
        insert_row_count: int = sum(len(table.frame.index) for table in change_package.tables.values())

        try:
            deploy_artifact: DeployArtifact = build_deploy_artifact(
                change_package,
                preparation.inputs.target_model,
                preparation.inputs.submission_context,
                strategy=preparation.inputs.deploy_strategy,
            )
        except ValueError as exc:
            logger.warning("SEAD change request ingest rejected invalid deploy artifact input: {}", exc)
            return IngestionResult.create_failed_result(message="Invalid deploy artifact input", details=str(exc))
        except NotImplementedError as exc:
            logger.warning("SEAD change request ingest failed at deploy-rendering boundary: {}", exc)
            return IngestionResult.create_failed_result(message="Deploy strategy not implemented", details=str(exc))

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
        artifact_directory: Path = write_artifact_bundle(
            run_folder,
            deploy_artifact_payload,
            preparation.inputs.submission_context,
        )
        logger.info(
            "Prepared SEAD change request ingestion scaffold for {} planned table(s)",
            len(preparation.planned.tables),
        )
        return IngestionResult.create_success_result(
            message=f"Deploy artifact emitted to '{artifact_directory}'",
            tables_processed=package_table_count,
            records_inserted=insert_row_count,
            deploy_artifact=deploy_artifact_payload,
            scope_name=preparation.inputs.submission_context.scope_name,
            run_id=preparation.inputs.submission_context.run_id,
            output_path=str(artifact_directory),
        )
