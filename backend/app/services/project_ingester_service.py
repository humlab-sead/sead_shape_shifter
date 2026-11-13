"""Compose project validation and table-based ingester operations."""

from dataclasses import replace
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from backend.app.authorization.models import Action, AuthorizedResource, ResourceType
from backend.app.core.config import Settings, get_settings
from backend.app.exceptions import ConfigurationError
from backend.app.exceptions import ValidationError as DomainValidationError
from backend.app.ingesters.protocol import (
    ConfiguredTableIngester,
    IngesterConfig,
    IngestionResult,
    TableSourceIngester,
    ValidationResult,
)
from backend.app.ingesters.registry import get_ingester_registry
from backend.app.mappers.output_expectation_mapper import OutputExpectationMapper
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.execute import OutputExpectationResult
from backend.app.models.ingester import IngestResponse, ProjectIngesterRequest, ValidateResponse
from backend.app.models.project import Project
from backend.app.services.ingester_runtime import inject_ingester_database_dependencies, inject_ingester_runtime_dependencies
from backend.app.services.project_data_provider_service import ProjectDataProviderError, ProjectDataProviderService
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.services.reconciliation.mapping_manager import EntityMappingManager
from ingesters.sead_change_request.contracts import TrustedProjectContext
from ingesters.sead_change_request.input_resolution import TRUSTED_PROJECT_CONTEXT_KEY
from src.reconciliation.mapping_model import Link, LinkOwner, LinkSource, LocalOnlyApproval, MappingCatalog
from src.reconciliation.model import DecisionStatus
from src.specifications import CompositeProjectSpecification
from src.target_model.conformance import ConformanceIssue, ForeignKeyValueSourceConformanceValidator
from src.target_model.models import TargetModel
from src.workflow import normalize_project


class ProjectIngesterService:
    """Validate a saved project and pass its normalized tables to a table-capable ingester."""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        project_data_provider_service: ProjectDataProviderService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.project_service = project_service or get_project_service()
        self.project_data_provider_service = project_data_provider_service or ProjectDataProviderService()
        self.settings = settings or get_settings()
        self.reconciliation_catalog_manager = EntityMappingManager(
            project_service=self.project_service,
            config_dir=Path(self.settings.PROJECTS_DIR),
        )

    async def validate_project_tables(
        self,
        key: str,
        authorized_project: AuthorizedResource,
        request: ProjectIngesterRequest,
    ) -> ValidateResponse:
        """Validate normalized tables from the authorized saved project."""
        project_name = self._guard_project_call(authorized_project, request)
        project, core_project, project_warnings, project_error = self._load_validated_project(project_name)
        if project_error:
            return ValidateResponse(is_valid=False, errors=project_error, warnings=project_warnings)

        ingester_class = self._get_table_ingester(key)
        if isinstance(ingester_class, ValidateResponse):
            return ingester_class

        try:
            config = self._create_trusted_config(key, project, core_project, request)
        except (ConfigurationError, ProjectDataProviderError, PydanticValidationError, ProjectIngesterConfigurationError) as exc:
            return ValidateResponse(is_valid=False, errors=[str(exc)], warnings=project_warnings)

        shapeshifter = await normalize_project(
            core_project,
            translate=request.translate,
            drop_foreign_keys=request.drop_foreign_keys,
            default_entity=request.default_entity,
            env_file=None,
        )
        try:
            config = self._attach_local_only_approvals(key, project_name, config, shapeshifter.mapping_catalog)
        except ProjectIngesterConfigurationError as exc:
            return ValidateResponse(is_valid=False, errors=[str(exc)], warnings=project_warnings)
        tables = shapeshifter.table_store
        self._log_table_counts(project_name, tables)
        ingester: TableSourceIngester = ingester_class(config=config)
        result: ValidationResult = await ingester.validate_tables(tables, source_name=f"project:{project_name}")

        return ValidateResponse(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=project_warnings + result.warnings,
            infos=result.infos,
            pending_confirmation_report=result.pending_confirmation_report,
        )

    async def ingest_project_tables(
        self,
        key: str,
        authorized_project: AuthorizedResource,
        request: ProjectIngesterRequest,
    ) -> IngestResponse:
        """Normalize and ingest tables from the authorized saved project."""
        project_name = self._guard_project_call(authorized_project, request)
        project, core_project, project_warnings, project_error = self._load_validated_project(project_name)
        if project_error:
            return self._ingestion_failure("Project validation failed", project_error)

        ingester_class = self._get_table_ingester(key)
        if isinstance(ingester_class, ValidateResponse):
            return self._ingestion_failure("File input required", ingester_class.errors)

        try:
            config = self._create_trusted_config(key, project, core_project, request)
        except (ConfigurationError, ProjectDataProviderError, PydanticValidationError, ProjectIngesterConfigurationError) as exc:
            return self._ingestion_failure("Ingestion configuration failed", [str(exc)])

        shapeshifter = await normalize_project(
            core_project,
            translate=request.translate,
            drop_foreign_keys=request.drop_foreign_keys,
            default_entity=request.default_entity,
            env_file=None,
            check_output_expectations=True,
        )
        evaluation = shapeshifter.output_expectation_evaluation
        expectation_results = OutputExpectationMapper.to_api_results(evaluation)
        if evaluation is not None and not evaluation.passed:
            failed_reasons = [result.failure_reason for result in expectation_results if result.failure_reason]
            logger.error(
                "Project '{}' failed output expectation checks: {} of {} checks",
                project_name,
                len(failed_reasons),
                len(expectation_results),
            )
            return self._ingestion_failure(
                "Output expectation checks failed; no tables were ingested.",
                failed_reasons or ["One or more output expectations did not match the measured output."],
                expectation_results,
            )

        if shapeshifter.incomplete_entities:
            logger.error("Project '{}' produced incomplete output: {}", project_name, shapeshifter.incomplete_entities)
            return self._ingestion_failure(
                "Full-run output is incomplete; no tables were ingested.",
                [self._incomplete_output_detail(shapeshifter.incomplete_entities)],
                expectation_results,
            )

        try:
            config = self._attach_local_only_approvals(key, project_name, config, shapeshifter.mapping_catalog)
        except ProjectIngesterConfigurationError as exc:
            return self._ingestion_failure("Ingestion configuration failed", [str(exc)], expectation_results)
        tables = shapeshifter.table_store
        self._log_table_counts(project_name, tables)
        ingester: TableSourceIngester = ingester_class(config=config)
        result: IngestionResult = await ingester.ingest_tables(
            tables,
            source_name=f"project:{project_name}",
            validate_first=True,
        )
        if project_warnings:
            logger.warning("Project '{}' passed specification checks with warnings: {}", project_name, project_warnings)

        return IngestResponse(
            success=result.success,
            records_processed=result.records_inserted,
            message=result.message,
            submission_id=result.submission_id,
            output_path=result.output_path,
            error_details=result.error_details,
            scope_name=result.scope_name,
            run_id=result.run_id,
            deploy_artifact=result.deploy_artifact,
            pending_confirmation_report=result.pending_confirmation_report,
            output_expectation_results=expectation_results,
        )

    def _guard_project_call(self, authorized_project: AuthorizedResource, request: ProjectIngesterRequest) -> str:
        """Reject invalid project authorization before loading project data or settings."""
        if not isinstance(authorized_project, AuthorizedResource):
            raise PermissionError("Project is not authorized for ingester execution")

        resource = authorized_project.resource
        locator = resource.locator
        if (
            authorized_project.action != Action.EXECUTE
            or resource.resource_type != ResourceType.PROJECT
            or resource.lifecycle_state != "active"
            or not isinstance(locator, str)
            or not locator.strip()
        ):
            raise PermissionError("Project is not authorized for ingester execution")

        if not isinstance(request, ProjectIngesterRequest):
            raise TypeError("Project ingester calls require a validated ProjectIngesterRequest")
        if request.project_name != locator:
            raise PermissionError("Requested project does not match the authorized project")

        return locator

    def _load_validated_project(
        self,
        project_name: str,
    ) -> tuple[Project, Any, list[str], list[str]]:
        """Load and validate one saved project before normalization or ingester work."""
        project = self.project_service.load_project(project_name)
        try:
            core_project = ProjectMapper.to_core(project)
            specification = CompositeProjectSpecification(core_project.cfg)
            is_valid = specification.is_satisfied_by()
            errors = [str(error) for error in specification.errors]
            warnings = [str(warning) for warning in specification.warnings]
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Project validation failed for '{}'", project_name)
            return project, None, [], [f"Project configuration validation failed: {exc}"]

        if not is_valid or errors:
            return project, core_project, warnings, errors or ["Project configuration validation failed"]
        return project, core_project, warnings, []

    @staticmethod
    def _get_table_ingester(key: str) -> type[ConfiguredTableIngester] | ValidateResponse:
        """Return the registered table ingester or a clear file-input-required error."""
        ingester_class = get_ingester_registry().get(key)
        if ingester_class is None:
            raise ValueError(f"Ingester '{key}' not found")
        if not issubclass(ingester_class, TableSourceIngester):
            message = f"Ingester '{key}' requires file input and does not support normalized tables"
            return ValidateResponse(is_valid=False, errors=[message])
        if not issubclass(ingester_class, ConfiguredTableIngester):
            message = f"Ingester '{key}' does not implement the configured table-ingester lifecycle"
            return ValidateResponse(is_valid=False, errors=[message])
        return ingester_class

    def _create_trusted_config(
        self,
        key: str,
        project: Project,
        core_project: Any,
        request: ProjectIngesterRequest,
    ) -> IngesterConfig:
        """Build the ingester config from backend settings and named request values."""
        required_connection_values = {
            "INGEST_TARGET_HOST": self.settings.INGEST_TARGET_HOST,
            "INGEST_TARGET_DBNAME": self.settings.INGEST_TARGET_DBNAME,
            "INGEST_TARGET_USER": self.settings.INGEST_TARGET_USER,
        }
        missing = [name for name, value in required_connection_values.items() if not isinstance(value, str) or not value.strip()]
        if missing:
            raise ProjectIngesterConfigurationError("Project ingester settings are missing: " + ", ".join(missing))
        if self.settings.INGEST_OUTPUT_DIR is None:
            raise ProjectIngesterConfigurationError("Project ingester setting INGEST_OUTPUT_DIR is required")

        target_model_data = core_project.cfg.get("metadata", {}).get("target_model")
        if target_model_data is None:
            raise ProjectIngesterConfigurationError("The saved project requires metadata.target_model")
        target_model = TargetModel.model_validate(target_model_data)

        foreign_key_value_sources: dict[str, dict[str, str]] = {}
        for entity_name in core_project.entities:
            entity_config = core_project.get_table(entity_name)
            if entity_config.foreign_key_value_sources:
                foreign_key_value_sources[entity_name] = dict(entity_config.foreign_key_value_sources)
        if key == "sead_change_request" and any(
            value_source == "public_id" for entity_sources in foreign_key_value_sources.values() for value_source in entity_sources.values()
        ):
            direct_issues = ForeignKeyValueSourceConformanceValidator().validate(target_model, core_project)
            if direct_issues:
                raise ProjectIngesterConfigurationError(self._format_direct_fk_issues(direct_issues))

        trusted_context = self.project_data_provider_service.build_trusted_context(project)

        submission_context = request.submission_context.model_dump(mode="python", exclude_none=True)
        submission_context["project_name"] = trusted_context.project_name
        extra: dict[str, Any] = {
            "target_model": target_model,
            TRUSTED_PROJECT_CONTEXT_KEY: trusted_context,
            "submission_context": submission_context,
        }
        if key == "sead_change_request" and foreign_key_value_sources:
            extra["foreign_key_value_sources"] = foreign_key_value_sources
        if request.deploy_strategy is not None:
            extra["deploy_strategy"] = request.deploy_strategy

        extra = inject_ingester_runtime_dependencies(key, extra, self.settings)
        host = self.settings.INGEST_TARGET_HOST
        port = self.settings.INGEST_TARGET_PORT
        dbname = self.settings.INGEST_TARGET_DBNAME
        user = self.settings.INGEST_TARGET_USER
        if host is None or dbname is None or user is None:
            raise ProjectIngesterConfigurationError("Missing required ingester database configuration")
        extra = inject_ingester_database_dependencies(
            key,
            extra,
            {
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
            },
        )

        return IngesterConfig(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            submission_name=request.submission_context.submission_name,
            data_types=request.submission_context.datatype,
            output_folder=str(self.settings.INGEST_OUTPUT_DIR),
            extra=extra,
        )

    def _attach_local_only_approvals(
        self,
        key: str,
        project_name: str,
        config: IngesterConfig,
        mapping_catalog: MappingCatalog | None,
    ) -> IngesterConfig:
        """Verify and attach committed reconciliation links and local-only approvals."""
        if key != "sead_change_request" or mapping_catalog is None:
            return config
        if mapping_catalog.metadata.project != project_name:
            raise ProjectIngesterConfigurationError(
                f"Mapping sidecar project '{mapping_catalog.metadata.project}' does not match authorized project '{project_name}'"
            )

        extra: dict[str, Any] = config.extra or {}
        trusted_context = extra.get(TRUSTED_PROJECT_CONTEXT_KEY)
        if not isinstance(trusted_context, TrustedProjectContext):
            raise ProjectIngesterConfigurationError("Change Request approvals require backend-owned trusted project context")

        local_key_columns_by_entity: dict[str, tuple[str, ...]] = {}
        local_only_approvals: dict[str, dict[str, LocalOnlyApproval]] = {}
        candidate_reconciliation_links: dict[str, dict[str, Link]] = {}
        for entity_name, entity_mapping in mapping_catalog.entities.items():
            committed_links = mapping_catalog.committed_links_by_entity(entity_name)
            committed_approvals = mapping_catalog.committed_local_only_approvals_by_entity(entity_name)
            if not committed_links and not committed_approvals:
                continue
            local_key_columns_by_entity[entity_name] = (
                (entity_mapping.local_key,) if isinstance(entity_mapping.local_key, str) else tuple(entity_mapping.local_key)
            )
            if committed_approvals:
                local_only_approvals[entity_name] = committed_approvals
            eligible_links = {
                encoded_key: link
                for encoded_key, link in committed_links.items()
                if link.source == LinkSource.RECONCILIATION
                and link.owner is not None
                and link.verified_at is not None
                and link.target_id is not None
                and link.target_id > 0
            }
            if eligible_links:
                candidate_reconciliation_links[entity_name] = eligible_links

        verified_local_only_approval_owners: dict[str, dict[str, LinkOwner]] = {}
        verified_reconciliation_links: dict[str, dict[str, int]] = {}
        if local_only_approvals or candidate_reconciliation_links:
            try:
                reconciliation_catalog = self.reconciliation_catalog_manager.load_catalog(project_name)
            except DomainValidationError as exc:
                raise ProjectIngesterConfigurationError(
                    f"Reconciliation catalog for project '{project_name}' could not be validated: {exc}"
                ) from exc

            for entity_name, approvals in local_only_approvals.items():
                for encoded_key, approval in approvals.items():
                    owner = approval.owner
                    if owner.entity_name != entity_name:
                        raise ProjectIngesterConfigurationError(
                            f"Local-only approval for '{entity_name}' key '{encoded_key}' has an invalid owner entity"
                        )
                    resolution_set = reconciliation_catalog.get(owner.entity_name, owner.target_field)
                    if resolution_set is None:
                        raise ProjectIngesterConfigurationError(
                            f"Local-only approval for '{entity_name}' key '{encoded_key}' references missing "
                            f"reconciliation specification '{owner.entity_name}.{owner.target_field}'"
                        )
                    decision = resolution_set.get(encoded_key)
                    if decision is None or decision.status != DecisionStatus.LOCAL_ONLY:
                        raise ProjectIngesterConfigurationError(
                            f"Local-only approval for '{entity_name}' key '{encoded_key}' has no matching local-only "
                            f"decision in reconciliation specification '{owner.entity_name}.{owner.target_field}'"
                        )
                    verified_local_only_approval_owners.setdefault(entity_name, {})[encoded_key] = owner

            for entity_name, links in candidate_reconciliation_links.items():
                for encoded_key, link in links.items():
                    owner = link.owner
                    if owner is None or owner.entity_name != entity_name:
                        continue
                    resolution_set = reconciliation_catalog.get(owner.entity_name, owner.target_field)
                    if resolution_set is None:
                        continue
                    decision = resolution_set.get(encoded_key)
                    if (
                        decision is None
                        or link.target_id is None
                        or decision.status != DecisionStatus.ACCEPTED
                        or decision.target_id != link.target_id
                    ):
                        continue
                    verified_reconciliation_links.setdefault(entity_name, {})[encoded_key] = link.target_id

        updated_context = replace(
            trusted_context,
            mapping_project_name=mapping_catalog.metadata.project,
            local_key_columns_by_entity=local_key_columns_by_entity,
            local_only_approvals=local_only_approvals,
            verified_local_only_approval_owners=verified_local_only_approval_owners,
            verified_reconciliation_links=verified_reconciliation_links,
        )
        config.extra = {**extra, TRUSTED_PROJECT_CONTEXT_KEY: updated_context}
        return config

    @staticmethod
    def _format_direct_fk_issues(issues: list[ConformanceIssue]) -> str:
        """Format direct foreign-key declaration errors for existing service responses."""
        formatted_issues: list[str] = []
        for issue in issues:
            context = [
                f"entity '{issue.entity}'" if issue.entity else None,
                f"field '{issue.field}'" if issue.field else None,
                f"column '{issue.column}'" if issue.column else None,
            ]
            issue_context = ", ".join(item for item in context if item)
            formatted_issues.append(f"{issue.code}: {issue.message}" + (f" ({issue_context})" if issue_context else ""))
        return "Invalid direct foreign-key declaration: " + "; ".join(formatted_issues)

    @staticmethod
    def _log_table_counts(project_name: str, tables: dict[str, Any]) -> None:
        """Log the entity and row counts passed to the ingester."""
        counts = {entity_name: len(table.index) for entity_name, table in tables.items()}
        logger.info(
            "Project '{}' produced {} table(s) and {} row(s) for ingester: {}",
            project_name,
            len(tables),
            sum(counts.values()),
            counts,
        )

    @staticmethod
    def _incomplete_output_detail(incomplete_entities: dict[str, str]) -> str:
        """Describe incomplete entities that block a full project-table write."""
        details = "; ".join(f"entity '{entity}': {reason}" for entity, reason in incomplete_entities.items())
        return f"Full-run output is incomplete and was not ingested: {details}"

    @staticmethod
    def _ingestion_failure(
        message: str,
        errors: list[str],
        output_expectation_results: list[OutputExpectationResult] | None = None,
    ) -> IngestResponse:
        """Build a failed response without a bundle or output path."""
        return IngestResponse(
            success=False,
            records_processed=0,
            message=message,
            output_path=None,
            error_details="\n".join(errors),
            output_expectation_results=output_expectation_results or [],
        )


class ProjectIngesterConfigurationError(ValueError):
    """Raised when required backend-owned project-ingester settings or data are missing."""
