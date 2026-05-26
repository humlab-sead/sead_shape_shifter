"""Main protocol adapter for the SEAD change request ingester.

This module resolves external inputs, runs the shared preparation flow, and
turns the result into validation or ingestion output.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.ingesters.protocol import IngesterConfig, IngesterMetadata, IngestionResult, ValidationResult
from backend.app.ingesters.registry import Ingesters
from ingesters.sead_change_request.artifact_writer import write_artifact_bundle
from ingesters.sead_change_request.collision_checks import CollisionCheckResult, check_projected_collisions
from ingesters.sead_change_request.contracts import ChangeRequestPackage, DeployArtifact
from ingesters.sead_change_request.input_resolution import InputResolutionError, resolve_inputs
from ingesters.sead_change_request.package_builder import build_change_request_package
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

    def _get_client(self, key: str) -> Any | None:
        """Get an optional injected client from config.extra."""
        extras = self.config.extra or {}
        return extras.get(key)

    async def _prepare_change_request(self, source: Path | str) -> PreparationResult:
        """Run the shared preparation workflow after inputs are resolved."""
        inputs: ResolvedInputs = resolve_inputs(self.config, source)
        planned = plan_bundle(inputs.bundle, inputs.target_model.entities)

        return await prepare_change_request(
            inputs,
            planned,
            sims_client=self._get_client("sims_client"),
            reconciliation_client=self._get_client("reconciliation_client"),
        )

    async def validate(self, excel_file: Path | str) -> ValidationResult:
        try:
            preparation: PreparationResult = await self._prepare_change_request(excel_file)
        except InputResolutionError as exc:
            return build_validation_input_failure(exc)

        logger.info(
            "Validated SEAD change request source bundle with {} table(s), {} row(s), and {} planned table(s)",
            len(preparation.inputs.bundle.tables),
            sum(len(frame.index) for frame in preparation.inputs.bundle.tables.values()),
            len(preparation.planned.tables),
        )
        return build_validation_result(preparation)

    async def ingest(self, excel_file: Path | str, validate_first: bool = True) -> IngestionResult:
        if validate_first:
            validation: ValidationResult = await self.validate(excel_file)
            if not validation.is_valid:
                return IngestionResult.create_failed_result(message="Validation failed", details=failure_details(validation.errors))

        try:
            preparation: PreparationResult = await self._prepare_change_request(excel_file)
        except InputResolutionError as exc:
            return build_ingestion_input_failure(exc)

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
            )
            if collision_result.has_conflicts:
                return IngestionResult.create_failed_result(
                    message="Target collision checks failed",
                    details=failure_details(collision_result.diagnostics),
                )

        change_package: ChangeRequestPackage = build_change_request_package(
            preparation.projection_result,
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
            self.config.output_folder,
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
        )
