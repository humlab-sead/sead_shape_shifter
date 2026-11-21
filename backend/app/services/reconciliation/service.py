"""Service for entity reconciliation against SEAD database."""

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

import httpx
from loguru import logger
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import to_jsonable_python

from backend.app.clients.reconciliation_client import (
    CandidateVerificationProtocolError,
    CandidateVerificationUnavailableError,
    ReconciliationClient,
    ReconciliationQuery,
    RecordSelectionInvalidRequestError,
    RecordSelectionNotFoundError,
    RecordSelectionServiceError,
    RecordSelectionTooLargeError,
    RecordSelectionUnavailableError,
    RecordSelectionUnsupportedError,
)
from backend.app.core.operation_manager import OperationStatus, operation_manager
from backend.app.exceptions import (
    ConfigurationError,
    DependencyError,
    DomainException,
    ReconciliationManifestError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationError,
)
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.mappers.reconciliation_mapper import ReconciliationMapper
from backend.app.models import AutoReconcileResult, Project, ReconciliationCandidate
from backend.app.models.reconciliation import (
    CandidateVerificationRequestItem,
    CandidateVerificationResult,
    DecisionBatchCounts,
    DecisionBatchResult,
    DecisionDraft,
    ExportToMappingOutcome,
    ExportToMappingResult,
    ReconciliationIssue,
    ReconciliationRecord,
    ReconciliationRowError,
    RecordSelectionBrowseResult,
    RecordSelectionCapabilities,
    RecordSelectionSearchRequest,
    RecordSelectionSearchResult,
    SavedDecision,
    SpecificationDecisionCounts,
)
from backend.app.models.shapeshift import PreviewResult
from backend.app.services import ProjectService, ShapeShiftService
from backend.app.services.mapping_service import MappingService
from backend.app.services.reconciliation.mapping_manager import EntityMappingManager
from backend.app.services.reconciliation.reference_validation import (
    POSTGRES_INTEGER_MAX,
    accepted_reference_error,
    parse_record_uri,
)
from backend.app.services.reconciliation.resolvers import ReconciliationSourceResolver
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.model import ShapeShiftProject
from src.reconciliation import model as core
from src.reconciliation.mapping_manager import MappingManager, MappingSnapshot, MappingVersionConflictError
from src.reconciliation.mapping_model import (
    EntityMapping,
    EntityType,
    Link,
    LinkOwner,
    LinkSource,
    LocalOnlyApproval,
    MappingCatalog,
    encode_local_key,
)
from src.reconciliation.source_strategy import ReconciliationSourceStrategy, SourceStrategyType
from src.types.fixed_entity_types import is_missing_fixed_entity_value


@dataclass
class ResolvedSourceRows:
    """Normalized target rows with optional search-source errors."""

    rows: list[dict[str, Any]]
    local_key: str | list[str]
    errors: list[ReconciliationRowError] = field(default_factory=list)


# Operator text that starts with ``id:`` always means an exact target-ID lookup.
_EXACT_IDENTIFIER_PATTERN = re.compile(r"^id:\s*(.*)$", re.IGNORECASE | re.DOTALL)


def _canonical_value(value: Any) -> str:
    """Return a comparable representation used to detect changed source values.

    Preview rows reach the browser as JSON, so the value the operator saw is
    already JSON-safe while the freshly resolved row still holds native values
    such as ``datetime``. Both copies are converted with the same JSON
    conversion, so an unchanged date, time, or duration compares equal after
    that round trip.
    """
    item = getattr(value, "item", None)
    if callable(item) and not isinstance(value, (str, bytes, bytearray)):
        try:
            value = item()
        except (TypeError, ValueError):
            pass
    if value is None:
        return "null"
    if isinstance(value, float) and not math.isfinite(value):
        return "null"
    try:
        converted = to_jsonable_python(value)
    except (TypeError, ValueError):
        converted = str(value)
    return json.dumps(converted, sort_keys=True, default=str)


@dataclass
class ReconciliationExportPreflight:
    """Files and decisions captured before awaiting candidate verification."""

    project_name: str
    entity_name: str
    target_field: str
    project_path: str
    catalog_path: Path
    catalog_content: bytes | None
    project_file_path: Path
    project_content: bytes
    sidecar_path: Path
    sidecar_content: bytes | None
    sidecar_snapshot: MappingSnapshot
    expected_local_key: str | list[str]
    expected_public_id: str
    owner: LinkOwner
    accepted: dict[str, core.ResolvedEntityPair]
    local_only: dict[str, core.ResolvedEntityPair]
    exportable: dict[str, core.ResolvedEntityPair]
    verification_items: dict[str, CandidateVerificationRequestItem]
    skipped_manual: int


class ReconciliationQueryService:
    """Service for building reconciliation queries."""

    class QueryBuildResult:
        def __init__(
            self,
            queries: dict[str, ReconciliationQuery],
            key_mapping: dict[str, str],
            row_keys: dict[int, str],
            errors: list[ReconciliationRowError],
        ):
            self.queries: dict[str, ReconciliationQuery] = queries
            self.key_mapping: dict[str, str] = key_mapping
            self.row_keys: dict[int, str] = row_keys
            self.errors: list[ReconciliationRowError] = errors

    @staticmethod
    def index_rows(rows: list[dict[str, Any]], local_key: str | list[str]) -> tuple[dict[int, str], list[ReconciliationRowError]]:
        """Return unique encoded keys and errors for every invalid row."""
        columns = [local_key] if isinstance(local_key, str) else local_key
        if not columns or len(columns) != len(set(columns)):
            raise ValidationError("Reconciliation requires a nonempty ordered business key without repeated columns")
        indexed: dict[int, str] = {}
        occurrences: dict[str, list[int]] = {}
        errors: list[ReconciliationRowError] = []
        for index, row in enumerate(rows):
            missing = [column for column in columns if column not in row or is_missing_fixed_entity_value(row[column])]
            if missing:
                errors.append(ReconciliationRowError(row_index=index, message=f"Missing business key component(s): {missing}"))
                continue
            values = [row[column] for column in columns]
            key = encode_local_key(local_key, values[0] if isinstance(local_key, str) else values)
            indexed[index] = key
            occurrences.setdefault(key, []).append(index)
        for key, indices in occurrences.items():
            if len(indices) > 1:
                for index in indices:
                    indexed.pop(index)
                    errors.append(ReconciliationRowError(row_index=index, local_key_value=key, message="Duplicate business key"))
        return indexed, errors

    def create(
        self,
        target_field: str,
        entity_mapping: core.EntityResolutionSet,
        max_candidates: int,
        source_data: ResolvedSourceRows,
        service_type: str,
    ) -> QueryBuildResult:
        """Build reconciliation queries from source data based on entity spec.

        Args:
            target_field: Target field name for reconciliation
            entity_mapping: Entity mapping specification (domain model)
            max_candidates: Max candidates per query
            source_data: Source data rows
            service_type: Reconciliation service entity type

        Returns:
            dict of query_id -> ReconciliationQuery
            dict of query_id -> source_value_mapping
        """
        queries: dict[str, ReconciliationQuery] = {}
        key_mapping: dict[str, str] = {}
        row_keys, errors = self.index_rows(source_data.rows, source_data.local_key)
        errors.extend(source_data.errors)
        blocked = {error.row_index for error in source_data.errors}

        for idx, row in enumerate(source_data.rows):
            if idx not in row_keys or idx in blocked:
                continue
            existing = entity_mapping.get(row_keys[idx])
            if existing is not None and existing.status != core.DecisionStatus.PROPOSED:
                continue
            target_value = row.get(target_field)
            if is_missing_fixed_entity_value(target_value):
                errors.append(ReconciliationRowError(row_index=idx, local_key_value=row_keys[idx], message="Missing search label"))
                continue

            query_string: str = str(target_value)
            query_id: str = f"q{idx}"
            key_mapping[query_id] = row_keys[idx]

            # Build properties from property_mappings
            # Maps service property IDs to source column values
            properties: list[dict[str, str]] = []
            for property_id, source_column in entity_mapping.metadata.property_mappings.items():
                value = row.get(source_column)
                if value is not None:
                    properties.append({"pid": property_id, "v": str(value)})

            queries[query_id] = ReconciliationQuery(
                query=query_string,
                entity_type=service_type,
                limit=max_candidates,
                properties=properties if properties else None,
            )

        return ReconciliationQueryService.QueryBuildResult(queries=queries, key_mapping=key_mapping, row_keys=row_keys, errors=errors)


class ReconciliationService:
    """
    Service for managing entity reconciliation.

    Uses read-only ShapeShiftProject from disk for reconciliation workflow.
    Prevents reconciliation if project has unsaved changes.
    """

    def __init__(self, config_dir: Path, reconciliation_client: ReconciliationClient):
        """
        Initialize reconciliation service.

        Args:
            config_dir: Directory containing project files
            reconciliation_client: Client for OpenRefine reconciliation API
        """
        self.config_dir = Path(config_dir)
        self.reconciliation_client: ReconciliationClient = reconciliation_client
        self.project_service: ProjectService = ProjectService()
        self.mapping_service: MappingService = MappingService(self.project_service)
        self.query_builder: ReconciliationQueryService = ReconciliationQueryService()
        self.shapeshift_service: ShapeShiftService | None = None
        # Lazy-load mapping manager to avoid circular imports
        self._mapping_manager: "EntityMappingManager | None" = None

    async def ensure_reconciliation_eligibility(self, service_type: str, property_mappings: dict[str, str]) -> None:
        """Check that the service manifest supports a type and all saved property IDs."""
        try:
            manifest = await self.reconciliation_client.get_service_manifest()
        except (httpx.HTTPError, ValueError) as exc:
            raise ReconciliationManifestError(
                "The reconciliation service manifest is unavailable or invalid; candidate matching was not started."
            ) from exc

        if not isinstance(manifest, dict):
            raise ReconciliationManifestError(
                "The reconciliation service returned a malformed manifest; candidate matching was not started."
            )

        default_types = manifest.get("defaultTypes")
        if not isinstance(default_types, list):
            raise ReconciliationManifestError("The reconciliation service manifest is missing a valid defaultTypes list.")

        default_type_ids: set[str] = set()
        for item in default_types:
            if (
                not isinstance(item, dict)  # pylint: disable=too-many-boolean-expressions
                or not isinstance(item.get("id"), str)
                or not item["id"].strip()
                or ("name" in item and not isinstance(item["name"], str))
                or item["id"] in default_type_ids
            ):
                raise ReconciliationManifestError("The reconciliation service manifest contains an invalid or duplicate default type.")
            default_type_ids.add(item["id"])

        reconciliation = manifest.get("reconciliation")
        supported_types = reconciliation.get("supportedTypes") if isinstance(reconciliation, dict) else None
        if not isinstance(supported_types, list):
            raise ReconciliationManifestError("The reconciliation service manifest is missing a valid reconciliation.supportedTypes list.")

        supported_type_ids: set[str] = set()
        for item in supported_types:
            if not isinstance(item, str) or not item.strip() or item in supported_type_ids or item not in default_type_ids:
                raise ReconciliationManifestError("The reconciliation service manifest contains an invalid or unresolved supported type.")
            supported_type_ids.add(item)

        extend = manifest.get("extend")
        property_settings = extend.get("property_settings") if isinstance(extend, dict) else None
        if not isinstance(property_settings, list):
            raise ReconciliationManifestError("The reconciliation service manifest is missing a valid extend.property_settings list.")

        served_properties: set[str] = set()
        for item in property_settings:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("name"), str)
                or not item["name"].strip()
                or not isinstance(item.get("entity_types"), list)
                or any(not isinstance(entity_type, str) or not entity_type.strip() for entity_type in item["entity_types"])
            ):
                raise ReconciliationManifestError("The reconciliation service manifest contains an invalid property setting.")
            if service_type in item["entity_types"]:
                served_properties.add(item["name"])

        if service_type not in supported_type_ids:
            raise ValidationError(f"Remote type '{service_type}' is not supported for reconciliation.")

        if not isinstance(property_mappings, dict) or any(not isinstance(property_id, str) for property_id in property_mappings):
            raise ValidationError("Saved reconciliation property mappings must use property IDs as string keys.")

        unsupported_properties = sorted(set(property_mappings) - served_properties)
        if unsupported_properties:
            names = ", ".join(f"'{property_id}'" for property_id in unsupported_properties)
            raise ValidationError(f"Property mapping(s) {names} are not declared for remote type '{service_type}'.")

    @property
    def catalog_manager(self) -> "EntityMappingManager":
        """Get entity mapping manager (lazy-loaded)."""
        if self._mapping_manager is None:

            self._mapping_manager = EntityMappingManager(
                project_service=self.project_service,
                config_dir=self.config_dir,
            )
        return self._mapping_manager

    async def get_reconciliation_preview(self, project_name: str, entity_name: str, target_field: str) -> list[dict]:
        """
        Get preview data for entity with reconciliation mappings applied.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field for reconciliation

        Returns:
            List of rows with source data + reconciliation status (target_id, confidence, etc.)
        """
        # Load entity mapping registry (now returns domain model)
        registry: core.EntityResolutionCatalog = self.catalog_manager.load_catalog(project_name)

        # Use domain model method
        entity_mapping: core.EntityResolutionSet | None = registry.get(entity_name, target_field)
        if entity_mapping is None:
            raise NotFoundError(f"No reconciliation spec for entity '{entity_name}' with target field '{target_field}'")

        source_data = await self.get_resolved_source_data(project_name, entity_name, entity_mapping)
        row_keys, key_errors = self.query_builder.index_rows(source_data.rows, source_data.local_key)
        errors: dict[int, list[str]] = {}
        for error in key_errors + source_data.errors:
            errors.setdefault(error.row_index, []).append(error.message)

        enriched_data: list[dict] = []
        service_type = entity_mapping.metadata.remote.service_type
        for index, row in enumerate(source_data.rows):
            key = row_keys.get(index)
            mapping = entity_mapping.get(key) if key else None
            row_errors = list(errors.get(index, []))
            if mapping is not None and mapping.status == core.DecisionStatus.ACCEPTED:
                reference_error = accepted_reference_error(mapping.candidate_id, mapping.target_id, service_type)
                if reference_error is not None:
                    row_errors.append(reference_error)
            enriched_row = {
                **row,
                "local_key_value": key,
                "status": mapping.status.value if mapping else None,
                "target_id": mapping.target_id if mapping else None,
                "candidate_id": mapping.candidate_id if mapping else None,
                "confidence": mapping.confidence if mapping else None,
                "notes": mapping.notes if mapping else "",
                "candidates": (
                    [ReconciliationMapper.candidate_to_dto(candidate).model_dump() for candidate in mapping.candidates] if mapping else []
                ),
                "errors": row_errors,
            }
            enriched_data.append(enriched_row)

        logger.info(f"Retrieved {len(enriched_data)} preview rows for entity '{entity_name}'")
        return enriched_data

    async def get_resolved_source_data(
        self, project_name: str, entity_name: str, entity_mapping: core.EntityResolutionSet, *, fresh: bool = False
    ) -> ResolvedSourceRows:
        """
        Resolve source data based on source in entity.

        Loads fresh ShapeShiftProject from disk (read-only for reconciliation).

        Args:
            project_name: Project name
            entity_name: Entity to reconcile
            entity_mapping: Entity mapping specification (domain model)
            fresh: When true, preview-based sources bypass warm and cached rows so
                current external source data is validated.

        Returns:
            Normalized target rows, optionally enriched with keyed search data.
        """
        # Load project once and pass to resolver (eliminates redundant loading)
        api_config: Project = self.project_service.load_project(project_name)
        project: ShapeShiftProject = ProjectMapper.to_core(api_config)

        strategy: SourceStrategyType = ReconciliationSourceStrategy.determine_strategy(entity_name, entity_mapping.metadata.source)
        mapping_service = MappingService(self.project_service)
        sidecar_entity = mapping_service.get_entity_mapping(project_name, entity_name)
        local_key = sidecar_entity.local_key
        target_resolver = ReconciliationSourceResolver.get_resolver_cls_for_strategy(SourceStrategyType.TARGET_ENTITY)(
            project_name, project, self.project_service
        )
        target_rows = await target_resolver.resolve(entity_name, entity_mapping, fresh=fresh)
        if strategy == SourceStrategyType.TARGET_ENTITY:
            return ResolvedSourceRows(rows=target_rows, local_key=local_key)

        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_strategy(strategy)
        search_rows = await resolver_cls(project_name, project, self.project_service).resolve(entity_name, entity_mapping, fresh=fresh)
        search_keys, search_errors = self.query_builder.index_rows(search_rows, local_key)
        if search_errors:
            indices = [error.row_index for error in search_errors]
            raise ValidationError(f"Search source has missing or duplicate business keys at rows {indices}")

        target_keys, _ = self.query_builder.index_rows(target_rows, local_key)
        by_key = {key: search_rows[index] for index, key in search_keys.items()}
        key_columns = [local_key] if isinstance(local_key, str) else local_key
        rows: list[dict[str, Any]] = []
        errors: list[ReconciliationRowError] = []
        for index, target in enumerate(target_rows):
            key = target_keys.get(index)
            search = by_key.get(key) if key is not None else None
            if key is not None and search is None:
                errors.append(ReconciliationRowError(row_index=index, local_key_value=key, message="No matching search-source row"))
            rows.append(
                {
                    **target,
                    **{
                        column: value
                        for column, value in (search or {}).items()
                        if column not in key_columns and column not in {"system_id", sidecar_entity.public_id}
                    },
                }
            )
        return ResolvedSourceRows(rows=rows, local_key=local_key, errors=errors)

    @staticmethod
    def _reference_issue(
        decision: core.ResolvedEntityPair, entity_type: str | None, row_index: int | None = None
    ) -> ReconciliationIssue | None:
        """Return a row-specific issue when an accepted reference is invalid."""
        error = accepted_reference_error(decision.candidate_id, decision.target_id, entity_type)
        if error is None:
            return None
        return ReconciliationIssue(
            row_index=row_index,
            local_key_value=decision.local_key_value,
            field="candidate_id",
            code="invalid_reference",
            message=error,
        )

    @staticmethod
    def _catalog_reference_issues(catalog: core.EntityResolutionCatalog) -> list[ReconciliationIssue]:
        """Return one issue for every decision that cannot be saved as written."""
        issues: list[ReconciliationIssue] = []
        for target_mappings in catalog.entities.values():
            for resolution_set in target_mappings.values():
                entity_type = resolution_set.metadata.remote.service_type
                for decision in resolution_set.links:
                    if decision.status == core.DecisionStatus.ACCEPTED:
                        issue = ReconciliationService._reference_issue(decision, entity_type)
                        if issue is not None:
                            issues.append(issue)
                        continue
                    if decision.target_id is not None:
                        issues.append(
                            ReconciliationIssue(
                                local_key_value=decision.local_key_value,
                                field="target_id",
                                code="invalid_decision",
                                message="Only an accepted decision may have a target ID",
                            )
                        )
                    if decision.candidate_id is not None:
                        issues.append(
                            ReconciliationIssue(
                                local_key_value=decision.local_key_value,
                                field="candidate_id",
                                code="invalid_decision",
                                message="Only an accepted decision may have a candidate URI",
                            )
                        )
        return issues

    @staticmethod
    def _read_optional_file(path: Path) -> bytes | None:
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    def _prepare_export_to_mapping_locked(self, project_name: str, entity_name: str, target_field: str) -> ReconciliationExportPreflight:
        """Validate one export and capture the files it depends on."""
        catalog_path = self.catalog_manager._get_default_catalog_filename(project_name)
        catalog_content = self._read_optional_file(catalog_path)
        reconciliation_catalog = self.catalog_manager.load_catalog(project_name)
        resolution_set = reconciliation_catalog.get(entity_name, target_field)
        if resolution_set is None:
            raise ResourceNotFoundError(
                f"No reconciliation registry for entity '{entity_name}' target '{target_field}'",
                resource_type="entity_mapping",
                resource_id=f"{entity_name}.{target_field}",
            )

        project = self.project_service.load_project(project_name)
        project_path = MappingService._project_path(project, project_name)
        project_file_path = Path(project.filename) if project.filename else Path(project_path)
        project_content = self._read_optional_file(project_file_path)
        if project_content is None:
            raise ResourceNotFoundError(
                f"Project configuration was not found for '{project_name}'",
                resource_type="project",
                resource_id=project_name,
            )

        try:
            core_project: ShapeShiftProject = ProjectMapper.to_core(project)
        except ConfigurationError as exc:
            if exc.context.get("specification") != "MappingSidecarSpecification":
                raise
            raise ResourceConflictError(
                f"Mapping metadata for entity '{entity_name}' does not match the project business key and public_id",
                resource_type="mapping-entity",
                resource_id=entity_name,
            ) from exc
        try:
            table = core_project.get_table(entity_name)
        except KeyError as exc:
            raise ResourceNotFoundError(
                f"Entity '{entity_name}' not found",
                resource_type="entity",
                resource_id=entity_name,
            ) from exc

        expected_local_key = self.mapping_service._default_local_key(table)
        expected_public_id = table.public_id
        if not expected_public_id:
            raise ValidationError(f"Entity '{entity_name}' has no public_id configured for reconciliation export")

        mapping_manager: MappingManager = self.mapping_service.manager
        sidecar_path: Path = mapping_manager._sidecar_path(project_path)
        sidecar_snapshot: MappingSnapshot = mapping_manager.load_snapshot(project_path)
        sidecar_content: bytes | None = self._read_optional_file(sidecar_path)
        sidecar: MappingCatalog = sidecar_snapshot.catalog
        existing_entity_mapping: EntityMapping | None = sidecar.entities.get(entity_name)  # pylint: disable=no-member
        if existing_entity_mapping is not None and (
            existing_entity_mapping.local_key != expected_local_key or existing_entity_mapping.public_id != expected_public_id
        ):
            raise ResourceConflictError(
                f"Mapping metadata for entity '{entity_name}' does not match the project business key and public_id",
                resource_type="mapping-entity",
                resource_id=entity_name,
            )

        owner = LinkOwner(entity_name=entity_name, target_field=target_field)
        accepted: dict[str, core.ResolvedEntityPair] = {
            decision.local_key_value: decision for decision in resolution_set.links if decision.status == core.DecisionStatus.ACCEPTED
        }
        local_only: dict[str, core.ResolvedEntityPair] = {
            decision.local_key_value: decision for decision in resolution_set.links if decision.status == core.DecisionStatus.LOCAL_ONLY
        }
        exportable: dict[str, core.ResolvedEntityPair] = {}
        skipped_manual = 0

        for local_key_value in dict.fromkeys((*accepted, *local_only)):
            existing_link = existing_entity_mapping.links.get(local_key_value) if existing_entity_mapping else None
            existing_approval = existing_entity_mapping.local_only_approvals.get(local_key_value) if existing_entity_mapping else None
            if existing_link is not None and existing_link.owner is not None and existing_link.owner != owner:
                raise ResourceConflictError(
                    f"Mapping key {local_key_value!r} is owned by {existing_link.owner.entity_name}.{existing_link.owner.target_field}",
                    resource_type="mapping-link",
                    resource_id=f"{entity_name}:{local_key_value}",
                )
            if existing_approval is not None and existing_approval.owner != owner:
                raise ResourceConflictError(
                    f"Mapping key {local_key_value!r} has a local-only approval owned by "
                    f"{existing_approval.owner.entity_name}.{existing_approval.owner.target_field}",
                    resource_type="mapping-local-only-approval",
                    resource_id=f"{entity_name}:{local_key_value}",
                )
            if (
                local_key_value in local_only
                and existing_link is not None
                and (existing_link.source != LinkSource.RECONCILIATION or existing_link.owner is None)
            ):
                raise ResourceConflictError(
                    f"Mapping key {local_key_value!r} has a protected link and cannot receive a local-only approval",
                    resource_type="mapping-local-only-approval",
                    resource_id=f"{entity_name}:{local_key_value}",
                )
            for other_entity, target_mappings in reconciliation_catalog.entities.items():
                if other_entity != entity_name:
                    continue
                for other_field, other_spec in target_mappings.items():
                    if (other_entity, other_field) == (entity_name, target_field):
                        continue
                    if any(
                        decision.local_key_value == local_key_value
                        and decision.status in {core.DecisionStatus.ACCEPTED, core.DecisionStatus.LOCAL_ONLY}
                        for decision in other_spec.links
                    ):
                        raise ResourceConflictError(
                            f"Another reconciliation specification has a claim for key {local_key_value!r}",
                            resource_type="mapping-link",
                            resource_id=f"{entity_name}:{local_key_value}",
                        )

            if local_key_value in accepted and existing_link is not None and existing_link.owner is None:
                skipped_manual += 1
            elif local_key_value in accepted:
                exportable[local_key_value] = accepted[local_key_value]

        service_type = resolution_set.metadata.remote.service_type
        if exportable and not service_type:
            raise ConfigurationError(f"Entity '{entity_name}' has no reconciliation service type configured")

        missing_candidate_keys = [key for key, decision in exportable.items() if not decision.candidate_id]
        if missing_candidate_keys:
            keys = ", ".join(repr(key) for key in missing_candidate_keys)
            raise ValidationError(
                f"Accepted decisions need to be re-accepted with their selected candidate before export. Business key(s): {keys}"
            )

        reference_issues = [
            issue for decision in exportable.values() if (issue := self._reference_issue(decision, service_type)) is not None
        ]
        if reference_issues:
            raise ValidationError(
                "Accepted decisions contain invalid target references. No mapping links were changed.",
                issues=[issue.model_dump() for issue in reference_issues],
            )

        verification_items = {
            key: CandidateVerificationRequestItem(type=service_type.lower(), id=decision.candidate_id)
            for key, decision in exportable.items()
            if decision.candidate_id is not None and service_type is not None
        }

        return ReconciliationExportPreflight(
            project_name=project_name,
            entity_name=entity_name,
            target_field=target_field,
            project_path=project_path,
            catalog_path=catalog_path,
            catalog_content=catalog_content,
            project_file_path=project_file_path,
            project_content=project_content,
            sidecar_path=sidecar_path,
            sidecar_content=sidecar_content,
            sidecar_snapshot=sidecar_snapshot,
            expected_local_key=expected_local_key,
            expected_public_id=expected_public_id,
            owner=owner,
            accepted=accepted,
            local_only=local_only,
            exportable=exportable,
            verification_items=verification_items,
            skipped_manual=skipped_manual,
        )

    def _export_inputs_unchanged(self, preflight: ReconciliationExportPreflight) -> bool:
        return (
            self._read_optional_file(preflight.catalog_path) == preflight.catalog_content
            and self._read_optional_file(preflight.project_file_path) == preflight.project_content
            and self._read_optional_file(preflight.sidecar_path) == preflight.sidecar_content
        )

    def _raise_export_changed_conflict(self, project_name: str) -> None:
        raise ResourceConflictError(
            "The reconciliation catalog, project configuration, or mapping sidecar "
            "changed during candidate verification. Reload and retry.",
            resource_type="reconciliation-export",
            resource_id=project_name,
        )

    def _refresh_export_preflight_locked(self, preflight: ReconciliationExportPreflight) -> ReconciliationExportPreflight:
        """Reload export inputs and reject any change made during candidate verification."""
        if not self._export_inputs_unchanged(preflight):
            self._raise_export_changed_conflict(preflight.project_name)

        try:
            current = self._prepare_export_to_mapping_locked(preflight.project_name, preflight.entity_name, preflight.target_field)
        except (DomainException, PydanticValidationError, BadRequestError, NotFoundError) as exc:
            if not self._export_inputs_unchanged(preflight):
                self._raise_export_changed_conflict(preflight.project_name)
            raise exc

        if (
            current.catalog_content != preflight.catalog_content
            or current.project_content != preflight.project_content
            or current.sidecar_content != preflight.sidecar_content
            or current.sidecar_snapshot.content_version != preflight.sidecar_snapshot.content_version
        ):
            self._raise_export_changed_conflict(preflight.project_name)
        return current

    @staticmethod
    def _validate_candidate_verification_results(
        preflight: ReconciliationExportPreflight, results: list[CandidateVerificationResult]
    ) -> None:
        expected_items = list(preflight.verification_items.items())
        if len(results) != len(expected_items):
            raise CandidateVerificationProtocolError("The Authority Service returned a different number of candidate results")

        for (local_key_value, request_item), result in zip(expected_items, results, strict=True):
            if result.type != request_item.type or result.id != request_item.id:
                raise CandidateVerificationProtocolError("The Authority Service returned candidate results in a different order")
            if result.outcome == "unsupported_type":
                raise CandidateVerificationProtocolError(f"The Authority Service does not support candidate type {result.type!r}")
            if result.outcome != "exists":
                raise DependencyError(
                    f"The Authority Service could not verify candidate {result.id!r} for business key "
                    f"{local_key_value!r}; no mapping links were changed."
                )
            if result.aggregate_id != preflight.exportable[local_key_value].target_id:
                raise CandidateVerificationProtocolError(
                    f"The Authority Service resolved a different target ID for business key {local_key_value!r}"
                )

    async def export_to_mapping(self, project_name: str, entity_name: str, target_field: str) -> ExportToMappingResult:
        """Verify accepted candidates and update only the links owned by this specification."""
        with self.project_service._get_lock(project_name):
            preflight = self._prepare_export_to_mapping_locked(project_name, entity_name, target_field)
            if not preflight.verification_items:
                return self._export_to_mapping_locked(preflight, None)

        try:
            verification_results = await self.reconciliation_client.verify_candidates(list(preflight.verification_items.values()))
        except CandidateVerificationUnavailableError as exc:
            raise DependencyError(
                "The Authority Service is unavailable; no mapping links were changed. Retry export when it is available."
            ) from exc
        except CandidateVerificationProtocolError as exc:
            raise DependencyError(f"Candidate verification failed; no mapping links were changed: {exc}") from exc

        with self.project_service._get_lock(project_name):
            current = self._refresh_export_preflight_locked(preflight)
            try:
                self._validate_candidate_verification_results(current, verification_results)
            except CandidateVerificationProtocolError as exc:
                raise DependencyError(f"Candidate verification failed; no mapping links were changed: {exc}") from exc
            return self._export_to_mapping_locked(current, verification_results)

    def _export_to_mapping_locked(
        self,
        preflight: ReconciliationExportPreflight,
        verification_results: list[CandidateVerificationResult] | None,
    ) -> ExportToMappingResult:
        """Apply verified outcomes to the captured sidecar and save with its version."""
        outcomes: dict[str, ExportToMappingOutcome] = {}
        if verification_results is not None:
            for local_key_value, _ in preflight.verification_items.items():
                outcomes[local_key_value] = ExportToMappingOutcome(local_key_value=local_key_value, outcome="verified")

        sidecar: MappingCatalog = preflight.sidecar_snapshot.catalog
        entity_mapping = sidecar.entities.get(preflight.entity_name) or EntityMapping(
            local_key=preflight.expected_local_key,
            public_id=preflight.expected_public_id,
            entity_type=EntityType.PRIMARY,
        )
        removed = 0
        for local_key_value, link in list(entity_mapping.links.items()):
            if link.owner == preflight.owner and local_key_value not in preflight.accepted:
                del entity_mapping.links[local_key_value]
                removed += 1

        removed_local_only_approvals = 0
        for local_key_value, approval in list(entity_mapping.local_only_approvals.items()):
            if approval.owner == preflight.owner and local_key_value not in preflight.local_only:
                del entity_mapping.local_only_approvals[local_key_value]
                removed_local_only_approvals += 1

        exported = 0
        exported_local_only_approvals = 0
        committed_at = datetime.now(timezone.utc)
        for local_key_value, decision in preflight.exportable.items():
            outcome = outcomes.get(local_key_value)
            if outcome is None:
                continue

            verified_at = committed_at if outcome.outcome == "verified" else None
            existing_link = entity_mapping.links.get(local_key_value)
            same_link = (
                existing_link is not None
                and existing_link.source == LinkSource.RECONCILIATION
                and existing_link.owner == preflight.owner
                and existing_link.target_id == decision.target_id
                and existing_link.confidence == decision.confidence
                and existing_link.notes == decision.notes
                and existing_link.committed_at is not None
                and existing_link.verified_at is not None
            )
            if same_link:
                continue

            entity_mapping.links[local_key_value] = Link(
                target_id=decision.target_id,
                source=LinkSource.RECONCILIATION,
                confidence=decision.confidence,
                committed_at=committed_at,
                owner=preflight.owner,
                verified_at=verified_at,
                notes=decision.notes,
                created_by="reconciliation",
            )
            exported += 1

        for local_key_value in preflight.local_only:
            existing_approval = entity_mapping.local_only_approvals.get(local_key_value)
            if existing_approval is not None and existing_approval.owner == preflight.owner and existing_approval.committed_at is not None:
                continue
            entity_mapping.local_only_approvals[local_key_value] = LocalOnlyApproval(
                owner=preflight.owner,
                committed_at=committed_at,
            )
            exported_local_only_approvals += 1

        if exported or removed or exported_local_only_approvals or removed_local_only_approvals:
            sidecar.entities[preflight.entity_name] = entity_mapping
            try:
                self.mapping_service.manager.save(
                    sidecar,
                    preflight.project_path,
                    expected_version=preflight.sidecar_snapshot.content_version,
                )
            except MappingVersionConflictError as exc:
                raise ResourceConflictError(
                    "The mapping sidecar changed during reconciliation export. Reload it and retry.",
                    resource_type="mapping-sidecar",
                    resource_id=preflight.project_name,
                ) from exc

        return ExportToMappingResult(
            exported=exported,
            removed=removed,
            exported_local_only_approvals=exported_local_only_approvals,
            removed_local_only_approvals=removed_local_only_approvals,
            skipped_manual=preflight.skipped_manual,
            entity=preflight.entity_name,
            field=preflight.target_field,
            outcomes=list(outcomes.values()),
        )

    def create_specification(
        self, project_name: str, entity_name: str, target_field: str, entity_mapping: core.EntityResolutionSet
    ) -> core.EntityResolutionCatalog:
        """Create a specification with its catalog read-modify-write under the project lock."""
        with self.project_service._get_lock(project_name):
            return self.catalog_manager.create_entity_mapping(project_name, entity_name, target_field, entity_mapping)

    def update_specification(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        source: "str | core.ResolutionSource | None",
        property_mappings: dict[str, str],
        remote: core.ResolutionTarget,
        auto_accept_threshold: float,
        review_threshold: float,
    ) -> core.EntityResolutionCatalog:
        """Update specification metadata with its catalog read-modify-write under the project lock."""
        with self.project_service._get_lock(project_name):
            return self.catalog_manager.update_entity_mapping(
                project_name,
                entity_name,
                target_field,
                source,
                property_mappings,
                remote,
                auto_accept_threshold,
                review_threshold,
            )

    def replace_catalog(self, project_name: str, catalog: core.EntityResolutionCatalog) -> None:
        """Save a whole catalog and remove links owned by specifications it removes."""
        with self.project_service._get_lock(project_name):
            self.catalog_manager.validate_catalog_business_keys(project_name, catalog)
            issues = self._catalog_reference_issues(catalog)
            if issues:
                raise ValidationError(
                    "The reconciliation catalog contains invalid accepted references. No catalog or mapping change was saved.",
                    issues=[issue.model_dump() for issue in issues],
                )
            previous = self.catalog_manager.load_catalog(project_name)
            removed_owners = {
                (entity_name, target_field)
                for entity_name, target_mappings in previous.entities.items()
                for target_field in target_mappings
                if not catalog.exists(entity_name, target_field)
            }
            removed_links, removed_approvals = self._remove_owned_mapping_links_locked(project_name, removed_owners)
            try:
                self.catalog_manager.save_catalog(project_name, catalog)
            except OSError as exc:
                if removed_links or removed_approvals:
                    raise DomainException(
                        "The reconciliation catalog was not saved. The removed specifications are still present, but "
                        f"{removed_links} owned mapping link(s) and {removed_approvals} local-only approval(s) were already "
                        "removed. Retry saving the catalog.",
                        context={
                            "removed_owned_links": removed_links,
                            "removed_owned_approvals": removed_approvals,
                        },
                    ) from exc
                raise

    def delete_specification(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        force: bool = False,
    ) -> tuple[core.EntityResolutionCatalog, int, int]:
        """Delete a specification after removing only its owned sidecar entries."""
        with self.project_service._get_lock(project_name):
            catalog = self.catalog_manager.load_catalog(project_name)
            self.catalog_manager.remove_specification(catalog, entity_name, target_field, force)
            removed_links, removed_approvals = self._remove_owned_mapping_links_locked(project_name, {(entity_name, target_field)})
            try:
                self.catalog_manager.save_catalog(project_name, catalog)
            except OSError as exc:
                if removed_links or removed_approvals:
                    raise DomainException(
                        f"Specification '{entity_name}.{target_field}' is still present, but {removed_links} owned "
                        f"mapping link(s) and {removed_approvals} local-only approval(s) were already removed. Retry the deletion.",
                        context={
                            "entity_name": entity_name,
                            "target_field": target_field,
                            "removed_owned_links": removed_links,
                            "removed_owned_approvals": removed_approvals,
                        },
                    ) from exc
                raise
            return catalog, removed_links, removed_approvals

    def _remove_owned_mapping_links_locked(self, project_name: str, owners: set[tuple[str, str]]) -> tuple[int, int]:
        """Remove specified owners' links and approvals from a fresh sidecar snapshot under the project lock."""
        if not owners:
            return 0, 0

        project = self.project_service.load_project(project_name)
        project_path = MappingService._project_path(project, project_name)
        mapping_manager = self.mapping_service.manager
        snapshot = mapping_manager.load_snapshot(project_path)
        removed = 0
        removed_approvals = 0
        for entity_mapping in snapshot.catalog.entities.values():  # pylint: disable=no-member
            stale_keys = [
                local_key_value
                for local_key_value, link in entity_mapping.links.items()
                if link.owner is not None and (link.owner.entity_name, link.owner.target_field) in owners
            ]
            for local_key_value in stale_keys:
                del entity_mapping.links[local_key_value]
                removed += 1
            stale_approval_keys = [
                local_key_value
                for local_key_value, approval in entity_mapping.local_only_approvals.items()
                if (approval.owner.entity_name, approval.owner.target_field) in owners
            ]
            for local_key_value in stale_approval_keys:
                del entity_mapping.local_only_approvals[local_key_value]
                removed_approvals += 1

        if removed or removed_approvals:
            try:
                mapping_manager.save(snapshot.catalog, project_path, expected_version=snapshot.content_version)
            except MappingVersionConflictError as exc:
                raise ResourceConflictError(
                    "The mapping sidecar changed during specification removal. Reload it and retry.",
                    resource_type="mapping-sidecar",
                    resource_id=project_name,
                ) from exc
        return removed, removed_approvals

    async def auto_reconcile_entity(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        entity_mapping: core.EntityResolutionSet,
        max_candidates: int = 3,
        operation_id: str | None = None,
    ) -> AutoReconcileResult:
        """
        Perform automatic reconciliation for an entity.

        Prevents reconciliation if project has unsaved changes.

        Args:
            project_name: Project name
            entity_name: Entity to reconcile
            target_field: Target field for reconciliation
            entity_mapping: Entity mapping specification (domain model)
            max_candidates: Max candidates per query
            operation_id: Optional operation ID for progress tracking

        Returns:
            AutoReconcileResult with counts and candidates

        Raises:
            ValueError: If project has unsaved changes
        """
        # Check the saved type and properties before changing or saving the catalog.
        registry: core.EntityResolutionCatalog = self.catalog_manager.load_catalog(project_name)
        existing_mapping: core.EntityResolutionSet | None = registry.get(entity_name, target_field)
        mapping_to_check = existing_mapping or entity_mapping
        service_type: str | None = mapping_to_check.metadata.remote.service_type
        if service_type:
            await self.ensure_reconciliation_eligibility(service_type, mapping_to_check.metadata.property_mappings)

        thresholds_updated: bool = False

        if existing_mapping is None:
            # Add new mapping using domain model method
            registry.add(entity_name, target_field, entity_mapping)
            existing_mapping = entity_mapping
            thresholds_updated = True
        else:
            thresholds_updated = existing_mapping.metadata.update_thresholds(
                entity_mapping.metadata.auto_accept_threshold, entity_mapping.metadata.review_threshold
            )
            entity_mapping = existing_mapping

        if not service_type:
            if thresholds_updated:
                with self.project_service._get_lock(project_name):
                    latest_catalog = self.catalog_manager.load_catalog(project_name)
                    latest_mapping = latest_catalog.get(entity_name, target_field)
                    if latest_mapping is None:
                        latest_catalog.add(entity_name, target_field, entity_mapping)
                    else:
                        latest_mapping.metadata.update_thresholds(
                            entity_mapping.metadata.auto_accept_threshold,
                            entity_mapping.metadata.review_threshold,
                        )
                    self.catalog_manager.save_catalog(project_name, latest_catalog)
            logger.info(f"Reconciliation disabled for entity '{entity_name}' (no service_type configured)")
            return AutoReconcileResult(proposed=0, unmatched=0, total=0, candidates={}, errors=[])

        logger.info(f"Finding reconciliation candidates for entity '{entity_name}'")

        # Update progress: Starting
        if operation_id:
            operation_manager.update_progress(
                operation_id, status=OperationStatus.RUNNING, message=f"Loading source data for {entity_name}..."
            )

        source_data = await self.get_resolved_source_data(project_name, entity_name, entity_mapping)
        logger.info(f"Considering {len(source_data.rows)} normalized rows for reconciliation")

        # Update progress: Building queries
        if operation_id:
            operation_manager.update_progress(operation_id, message=f"Checking {len(source_data.rows)} normalized rows...")

        query_data: ReconciliationQueryService.QueryBuildResult = self.query_builder.create(
            target_field, entity_mapping, max_candidates, source_data, service_type
        )

        if operation_id:
            operation_manager.update_progress(
                operation_id,
                total=len(source_data.rows),
                current=0,
                message=f"Reconciling {len(query_data.queries)} queries...",
            )

        # Execute batch reconciliation with progress tracking
        logger.debug(f"Executing batch reconciliation for {len(query_data.queries)} queries")

        # For progress tracking, we'll process in smaller batches
        batch_size = 50
        all_results: dict[str, list[ReconciliationCandidate]] = {}

        # Convert dict to list of items for batching
        queries_items = list(query_data.queries.items())
        total_queries = len(queries_items)

        for i in range(0, total_queries, batch_size):
            # Check for cancellation
            if operation_id and operation_manager.is_cancelled(operation_id):
                logger.warning(f"Reconciliation cancelled for {entity_name}")
                raise BadRequestError(f"Reconciliation cancelled for {entity_name}")

            # Create batch dict
            batch_items = queries_items[i : i + batch_size]
            batch_dict = dict(batch_items)

            batch_results = await self.reconciliation_client.reconcile_batch(batch_dict)
            all_results.update(batch_results)

            # Update progress
            if operation_id:
                processed = min(i + batch_size, total_queries)
                operation_manager.update_progress(
                    operation_id, current=processed, message=f"Processed {processed}/{total_queries} queries..."
                )

        if operation_id:
            operation_manager.update_progress(operation_id, message="Processing reconciliation results...")

        errors = query_data.errors.copy()
        blocked = {error.row_index for error in source_data.errors}
        candidate_map: dict[str, list[ReconciliationCandidate]] = {}
        for index, key in query_data.row_keys.items():
            if index in blocked:
                continue
            existing = entity_mapping.get(key)
            if existing is not None and existing.status != core.DecisionStatus.PROPOSED:
                candidate_map[key] = [ReconciliationMapper.candidate_to_dto(candidate) for candidate in existing.candidates]
                continue
            query_id = f"q{index}"
            if query_id in query_data.queries and query_id not in all_results:
                errors.append(ReconciliationRowError(row_index=index, local_key_value=key, message="Matching service omitted query result"))
                continue
            candidates = all_results.get(query_id, [])
            candidate_map[key] = candidates
            previous = entity_mapping.get(key)
            entity_mapping.add(
                core.ResolvedEntityPair(
                    local_key_value=key,
                    source_value=source_data.rows[index].get(target_field),
                    status=core.DecisionStatus.PROPOSED,
                    candidates=[ReconciliationMapper.candidate_to_domain(candidate) for candidate in candidates],
                    notes=previous.notes if previous else None,
                )
            )

        with self.project_service._get_lock(project_name):
            latest_catalog = self.catalog_manager.load_catalog(project_name)
            latest_mapping = latest_catalog.get(entity_name, target_field)
            if latest_mapping is None:
                latest_catalog.add(entity_name, target_field, entity_mapping)
                latest_mapping = entity_mapping
            else:
                latest_mapping.metadata.update_thresholds(
                    entity_mapping.metadata.auto_accept_threshold, entity_mapping.metadata.review_threshold
                )
                for decision in entity_mapping.links:
                    saved = latest_mapping.get(decision.local_key_value)
                    if saved is not None and saved.status != core.DecisionStatus.PROPOSED:
                        candidate_map[decision.local_key_value] = [
                            ReconciliationMapper.candidate_to_dto(candidate) for candidate in saved.candidates
                        ]
                        continue
                    latest_mapping.add(decision)
            proposed_keys = {
                key
                for key in candidate_map
                if (entry := latest_mapping.get(key)) is not None and entry.status == core.DecisionStatus.PROPOSED
            }
            proposed = len(proposed_keys)
            unmatched = sum(not candidate_map[key] for key in proposed_keys)
            self.catalog_manager.save_catalog(project_name, latest_catalog)

        logger.info(f"Candidate search complete: {proposed} proposed, {unmatched} without candidates, {len(errors)} row errors")

        # Complete operation
        if operation_id:
            operation_manager.update_progress(operation_id, current=len(source_data.rows), message="Candidate search complete")
            operation_manager.complete_operation(
                operation_id, f"Complete: {proposed} proposed, {len(errors)} row errors of {len(source_data.rows)} rows"
            )

        return AutoReconcileResult(
            proposed=proposed,
            unmatched=unmatched,
            total=len(source_data.rows),
            candidates=candidate_map,
            errors=errors,
        )

    def update_mapping(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        local_key_value: str,
        status: core.DecisionStatus,
        target_id: int | None,
        notes: str | None = None,
        candidate_id: str | None = None,
    ) -> core.EntityResolutionCatalog:
        """Save an explicit operator decision for an existing business key."""
        with self.project_service._get_lock(project_name):
            recon_config: core.EntityResolutionCatalog = self.catalog_manager.load_catalog(project_name)
            entity_mapping: core.EntityResolutionSet | None = recon_config.get(entity_name, target_field)
            if entity_mapping is None:
                raise NotFoundError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' not found")
            previous = entity_mapping.get(local_key_value)
            if previous is None:
                raise BadRequestError(f"No reconciliation row with business key {local_key_value!r}; run matching first")

            if status == core.DecisionStatus.ACCEPTED:
                if target_id is None or candidate_id is None or not candidate_id.strip():
                    raise ValidationError("Accepting a candidate requires its URI and numeric target ID")
                reference_error = accepted_reference_error(candidate_id, target_id, entity_mapping.metadata.remote.service_type)
                if reference_error is not None:
                    raise ValidationError(reference_error)
            elif candidate_id is not None:
                raise ValidationError("Only accepted decisions may include a candidate URI")

            confidence = None
            if status == core.DecisionStatus.ACCEPTED and candidate_id is not None:
                for candidate in previous.candidates:
                    if candidate.id == candidate_id and candidate.score is not None:
                        confidence = candidate.score / 100
                        break
            decision = core.ResolvedEntityPair(
                local_key_value=local_key_value,
                source_value=previous.source_value,
                status=status,
                target_id=target_id,
                candidate_id=candidate_id,
                confidence=confidence,
                notes=notes if notes is not None else previous.notes,
                candidates=previous.candidates,
                created_by="user",
                created_at=previous.created_at,
                last_modified=datetime.now(timezone.utc).isoformat(),
            )
            entity_mapping.add(decision)
            self.catalog_manager.save_catalog(project_name, recon_config)
            return recon_config

    async def save_decision_batch(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        drafts: list[DecisionDraft],
    ) -> DecisionBatchResult:
        """Save first-time accepted and local-only decisions in one catalog write.

        Source rows are resolved once, before the project lock is taken. Every draft
        is validated against the current source rows, so a changed, missing, or
        repeated row rejects the whole batch without touching the catalog.
        """
        catalog = self.catalog_manager.load_catalog(project_name)
        resolution_set = catalog.get(entity_name, target_field)
        if resolution_set is None:
            raise ResourceNotFoundError(
                f"No reconciliation registry for entity '{entity_name}' target '{target_field}'",
                resource_type="entity_mapping",
                resource_id=f"{entity_name}.{target_field}",
            )

        # Steps 1-2: resolve current source rows once, before the project lock.
        try:
            source_data = await self.get_resolved_source_data(project_name, entity_name, resolution_set, fresh=True)
        except ValidationError as exc:
            raise ValidationError(
                "The source rows could not be resolved; no decisions were saved.",
                issues=[
                    ReconciliationIssue(code="source_resolution_failed", message=str(exc.message)).model_dump(),
                ],
            ) from exc
        row_keys, key_errors = self.query_builder.index_rows(source_data.rows, source_data.local_key)
        resolution_errors = list(key_errors) + list(source_data.errors)
        if resolution_errors:
            raise ValidationError(
                "The source rows contain missing or duplicate business keys; no decisions were saved.",
                issues=[
                    ReconciliationIssue(
                        row_index=error.row_index,
                        local_key_value=error.local_key_value,
                        code="source_resolution_failed",
                        message=error.message,
                    ).model_dump()
                    for error in resolution_errors
                ],
            )

        key_to_index = {key: index for index, key in row_keys.items()}
        service_type = resolution_set.metadata.remote.service_type
        issues: list[ReconciliationIssue] = []
        valid: list[tuple[DecisionDraft, int]] = []

        # Step 3: reject malformed, repeated, or absent drafts.
        if not drafts:
            issues.append(ReconciliationIssue(code="invalid_draft", message="At least one decision draft is required."))
        seen_keys: set[str] = set()
        for draft in drafts:
            if not draft.local_key_value or not draft.local_key_value.strip():
                issues.append(ReconciliationIssue(code="invalid_draft", message="Each draft requires an encoded business key."))
                continue
            if draft.local_key_value in seen_keys:
                issues.append(
                    ReconciliationIssue(
                        local_key_value=draft.local_key_value,
                        code="duplicate_draft",
                        message="The batch contains more than one draft for this business key.",
                    )
                )
                continue
            seen_keys.add(draft.local_key_value)
            row_index = key_to_index.get(draft.local_key_value)
            if row_index is None:
                issues.append(
                    ReconciliationIssue(
                        local_key_value=draft.local_key_value,
                        code="row_not_found",
                        message="The business key is not present in the resolved source rows.",
                    )
                )
                continue
            valid.append((draft, row_index))

        # Step 4: compare every displayed column with the resolved row.
        for draft, row_index in valid:
            resolved_row = source_data.rows[row_index]
            for column, displayed in draft.displayed_values.items():
                if column not in resolved_row:
                    issues.append(
                        ReconciliationIssue(
                            row_index=row_index,
                            local_key_value=draft.local_key_value,
                            field=column,
                            code="row_changed",
                            message=f"Column '{column}' is not present in the current source row.",
                        )
                    )
                    continue
                if _canonical_value(displayed) != _canonical_value(resolved_row[column]):
                    issues.append(
                        ReconciliationIssue(
                            row_index=row_index,
                            local_key_value=draft.local_key_value,
                            field=column,
                            code="row_changed",
                            message=f"Column '{column}' changed since it was displayed.",
                        )
                    )

        # Step 5: validate the accepted references introduced by this batch.
        for draft, row_index in valid:
            if draft.status == "accepted":
                error = accepted_reference_error(draft.candidate_id, draft.target_id, service_type)
                if error is not None:
                    issues.append(
                        ReconciliationIssue(
                            row_index=row_index,
                            local_key_value=draft.local_key_value,
                            field="candidate_id",
                            code="invalid_reference",
                            message=error,
                        )
                    )
            elif draft.target_id is not None or draft.candidate_id is not None:
                issues.append(
                    ReconciliationIssue(
                        row_index=row_index,
                        local_key_value=draft.local_key_value,
                        field="candidate_id" if draft.candidate_id is not None else "target_id",
                        code="invalid_draft",
                        message="A local-only decision must not include a target ID or candidate URI.",
                    )
                )

        if issues:
            raise ValidationError(
                "The decision batch was rejected; no catalog change was saved.",
                issues=[issue.model_dump() for issue in issues],
            )

        # Steps 6-8: apply every decision to the catalog loaded under the project lock.
        with self.project_service._get_lock(project_name):
            latest_catalog = self.catalog_manager.load_catalog(project_name)
            latest_set = latest_catalog.get(entity_name, target_field)
            if latest_set is None:
                raise ResourceNotFoundError(
                    f"No reconciliation registry for entity '{entity_name}' target '{target_field}'",
                    resource_type="entity_mapping",
                    resource_id=f"{entity_name}.{target_field}",
                )

            owner = LinkOwner(entity_name=entity_name, target_field=target_field)
            if any(draft.status == "local-only" for draft, _ in valid):
                sidecar_entity = self.mapping_service.get_entity_mapping(project_name, entity_name)
                for draft, row_index in valid:
                    if draft.status != "local-only":
                        continue
                    existing_link = sidecar_entity.links.get(draft.local_key_value)
                    if existing_link is not None and (
                        existing_link.source != LinkSource.RECONCILIATION or existing_link.owner is None or existing_link.owner != owner
                    ):
                        issues.append(
                            ReconciliationIssue(
                                row_index=row_index,
                                local_key_value=draft.local_key_value,
                                code="protected_link",
                                message="A manual or other-owner mapping link already claims this business key.",
                            )
                        )
                if issues:
                    raise ValidationError(
                        "The decision batch was rejected; no catalog change was saved.",
                        issues=[issue.model_dump() for issue in issues],
                    )

            last_modified = datetime.now(timezone.utc).isoformat()
            saved: list[SavedDecision] = []
            batch_accepted = 0
            batch_local_only = 0
            for draft, row_index in valid:
                previous = latest_set.get(draft.local_key_value)
                source_value = source_data.rows[row_index].get(target_field)
                status = core.DecisionStatus.ACCEPTED if draft.status == "accepted" else core.DecisionStatus.LOCAL_ONLY
                confidence = None
                if status == core.DecisionStatus.ACCEPTED and previous is not None and draft.candidate_id is not None:
                    for candidate in previous.candidates:
                        if candidate.id == draft.candidate_id and candidate.score is not None:
                            confidence = candidate.score / 100
                            break
                decision = core.ResolvedEntityPair(
                    local_key_value=draft.local_key_value,
                    source_value=source_value,
                    status=status,
                    target_id=draft.target_id,
                    candidate_id=draft.candidate_id,
                    confidence=confidence,
                    notes=draft.notes if draft.notes is not None else (previous.notes if previous else None),
                    candidates=previous.candidates if previous else [],
                    created_at=previous.created_at if previous else last_modified,
                    created_by=previous.created_by if previous else "user",
                    last_modified=last_modified,
                )
                latest_set.add(decision)
                if status == core.DecisionStatus.ACCEPTED:
                    batch_accepted += 1
                else:
                    batch_local_only += 1
                saved.append(
                    SavedDecision(
                        local_key_value=draft.local_key_value,
                        status=draft.status,
                        target_id=draft.target_id,
                        candidate_id=draft.candidate_id,
                        notes=decision.notes,
                        last_modified=last_modified,
                    )
                )

            # save_catalog writes through a temporary file and os.replace, so a failed
            # write leaves the previous catalog intact and every draft unsaved.
            self.catalog_manager.save_catalog(project_name, latest_catalog)

            specification_counts = {"accepted": 0, "local_only": 0, "proposed": 0, "rejected": 0}
            for link in latest_set.links:
                if link.status == core.DecisionStatus.ACCEPTED:
                    specification_counts["accepted"] += 1
                elif link.status == core.DecisionStatus.LOCAL_ONLY:
                    specification_counts["local_only"] += 1
                elif link.status == core.DecisionStatus.PROPOSED:
                    specification_counts["proposed"] += 1
                elif link.status == core.DecisionStatus.REJECTED:
                    specification_counts["rejected"] += 1
            specification_total = len(latest_set.links)

        logger.info(f"Saved {len(saved)} reconciliation decision(s) for {entity_name}.{target_field}")
        return DecisionBatchResult(
            saved=saved,
            counts=DecisionBatchCounts(
                saved=len(saved),
                accepted=batch_accepted,
                local_only=batch_local_only,
                specification=SpecificationDecisionCounts(total=specification_total, **specification_counts),
            ),
        )

    def delete_decision(self, project_name: str, entity_name: str, target_field: str, local_key_value: str) -> core.EntityResolutionCatalog:
        """Delete a decision by encoded business key."""
        with self.project_service._get_lock(project_name):
            catalog = self.catalog_manager.load_catalog(project_name)
            resolution_set = catalog.get(entity_name, target_field)
            if resolution_set is None:
                raise NotFoundError(f"No reconciliation spec for {entity_name}.{target_field}")
            if not resolution_set.remove(local_key_value):
                raise NotFoundError(f"No reconciliation decision for business key {local_key_value!r}")
            self.catalog_manager.save_catalog(project_name, catalog)
            return catalog

    def mark_as_unmatched(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        local_key_value: str,
        notes: str | None = None,
    ) -> core.EntityResolutionCatalog:
        """Mark an existing keyed row as local-only."""
        return self.update_mapping(project_name, entity_name, target_field, local_key_value, core.DecisionStatus.LOCAL_ONLY, None, notes)

    def _selection_resolution_set(self, project_name: str, entity_name: str, target_field: str) -> tuple[core.EntityResolutionSet, str]:
        """Return the specification and its fixed record type for selection calls."""
        catalog = self.catalog_manager.load_catalog(project_name)
        resolution_set = catalog.get(entity_name, target_field)
        if resolution_set is None:
            raise ResourceNotFoundError(
                f"No reconciliation registry for entity '{entity_name}' target '{target_field}'",
                resource_type="entity_mapping",
                resource_id=f"{entity_name}.{target_field}",
            )
        service_type = resolution_set.metadata.remote.service_type
        if not service_type or not service_type.strip():
            raise ValidationError(
                f"Entity '{entity_name}' has no remote service type configured, so record selection is unavailable.",
                error_code="RECORD_SELECTION_UNSUPPORTED",
            )
        return resolution_set, service_type.strip().lower()

    @staticmethod
    def _raise_selection_failure(exc: RecordSelectionServiceError) -> NoReturn:
        """Translate an Authority Service selection failure into a domain exception."""
        if isinstance(exc, RecordSelectionUnsupportedError):
            raise ValidationError(str(exc), error_code="RECORD_SELECTION_UNSUPPORTED") from exc
        if isinstance(exc, RecordSelectionInvalidRequestError):
            raise ValidationError(str(exc), error_code="RECORD_SELECTION_INVALID_INPUT") from exc
        if isinstance(exc, RecordSelectionTooLargeError):
            raise ResourceConflictError(
                str(exc) or "The complete record list is too large to browse.",
                error_code="RECORD_SELECTION_TOO_LARGE",
            ) from exc
        if isinstance(exc, RecordSelectionUnavailableError):
            raise ReconciliationManifestError(
                f"The reconciliation service cannot be reached, so record selection was not completed: {exc}",
                error_code="RECORD_SELECTION_UNAVAILABLE",
            ) from exc
        raise DependencyError(
            f"The reconciliation service returned an invalid record-selection response: {exc}",
            error_code="RECORD_SELECTION_INVALID_RESPONSE",
        ) from exc

    async def get_selection_capabilities(
        self, project_name: str, entity_name: str, target_field: str, *, fresh: bool = True
    ) -> RecordSelectionCapabilities:
        """Return the versioned selection capabilities advertised for the specification's type."""
        _, service_type = self._selection_resolution_set(project_name, entity_name, target_field)
        try:
            version, descriptors = await self.reconciliation_client.get_record_selection_capabilities(fresh=fresh)
        except RecordSelectionServiceError as exc:
            self._raise_selection_failure(exc)

        for descriptor in descriptors:
            if descriptor.type == service_type:
                return RecordSelectionCapabilities(version=version, type=descriptor)

        raise ValidationError(
            f"Record selection is not available for remote type '{service_type}'.",
            error_code="RECORD_SELECTION_UNSUPPORTED",
        )

    @staticmethod
    def _selection_record(record: ReconciliationRecord, service_type: str) -> ReconciliationRecord:
        """Validate that a service-supplied record belongs to the fixed type and ID space."""
        if record.type != service_type:
            raise DependencyError(
                f"The reconciliation service returned a '{record.type}' record for type '{service_type}'.",
                error_code="RECORD_SELECTION_INVALID_RESPONSE",
            )
        if record.target_id is None:
            raise DependencyError(
                "The reconciliation service returned a record without a numeric target ID.",
                error_code="RECORD_SELECTION_INVALID_RESPONSE",
            )
        if parse_record_uri(record.id, service_type) != record.target_id:
            raise DependencyError(
                f"The reconciliation service returned a record URI that does not match "
                f"type '{service_type}' and target ID {record.target_id}.",
                error_code="RECORD_SELECTION_INVALID_RESPONSE",
            )
        return record

    @staticmethod
    def _exact_identifier(text: str) -> int | None:
        """Return the positive ID of an ``id:`` query, or ``None`` when the text is not one.

        Text that starts with ``id:`` is always treated as an exact-identifier query,
        so malformed values are rejected instead of falling back to ranked search.
        """
        match = _EXACT_IDENTIFIER_PATTERN.match(text)
        if match is None:
            return None
        digits = match.group(1).strip()
        if not digits.isascii() or not digits.isdecimal():
            raise ValidationError(
                "Enter 'id:' followed by a positive whole-number target ID, for example 'id: 42'.",
                error_code="RECORD_SELECTION_INVALID_INPUT",
            )
        identifier = int(digits)
        if identifier <= 0 or identifier > POSTGRES_INTEGER_MAX:
            raise ValidationError(
                "The target ID after 'id:' must be a positive whole number within the supported integer range.",
                error_code="RECORD_SELECTION_INVALID_INPUT",
            )
        return identifier

    async def search_selection(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        request: RecordSelectionSearchRequest,
    ) -> RecordSelectionSearchResult:
        """Run a bounded ranked search, or an exact type-scoped lookup for ``id:`` text."""
        _, service_type = self._selection_resolution_set(project_name, entity_name, target_field)
        capabilities = await self.get_selection_capabilities(project_name, entity_name, target_field)

        text = request.query.strip()
        if not text:
            raise ValidationError(
                "Enter search text or 'id: <positive integer>' before searching.",
                error_code="RECORD_SELECTION_INVALID_INPUT",
            )

        identifier = self._exact_identifier(text)
        if identifier is not None:
            if not capabilities.type.identifier_search_supported:
                raise ValidationError(
                    f"Exact identifier lookup is not enabled for remote type '{service_type}'.",
                    error_code="RECORD_SELECTION_UNSUPPORTED",
                )
            try:
                record = await self.reconciliation_client.get_record_details(service_type, identifier)
            except RecordSelectionServiceError as exc:
                if isinstance(exc, RecordSelectionNotFoundError):
                    logger.info(f"Record selection found no {service_type} record for target ID {identifier}")
                    return RecordSelectionSearchResult(mode="exact", items=[])
                self._raise_selection_failure(exc)
            return RecordSelectionSearchResult(mode="exact", items=[self._selection_record(record, service_type)])

        if not capabilities.type.search_supported:
            raise ValidationError(
                f"Interactive search is not enabled for remote type '{service_type}'.",
                error_code="RECORD_SELECTION_UNSUPPORTED",
            )

        cap = capabilities.type.interactive_search_max_results
        if cap is None:
            raise ValidationError(
                f"Remote type '{service_type}' does not advertise an interactive search limit.",
                error_code="RECORD_SELECTION_UNSUPPORTED",
            )
        if request.limit is not None and request.limit <= 0:
            raise ValidationError(
                "The requested search limit must be a positive whole number.",
                error_code="RECORD_SELECTION_INVALID_INPUT",
            )
        limit = min(request.limit or cap, cap)

        # Declared property IDs are ranking hints only; they never restrict results.
        if request.context:
            await self.ensure_reconciliation_eligibility(service_type, request.context)

        try:
            candidates = await self.reconciliation_client.search_records(service_type, text, limit, request.context or None)
        except RecordSelectionServiceError as exc:
            self._raise_selection_failure(exc)

        items: list[ReconciliationRecord] = []
        for candidate in candidates:
            target_id = parse_record_uri(candidate.id, service_type)
            if target_id is None:
                logger.warning(f"Dropping search candidate whose URI does not match '{service_type}': {candidate.id}")
                continue
            items.append(
                ReconciliationRecord(
                    id=candidate.id,
                    target_id=target_id,
                    type=service_type,
                    name=candidate.name,
                    description=candidate.description,
                    fields={},
                    score=candidate.score,
                )
            )
        return RecordSelectionSearchResult(mode="ranked", items=items)

    async def browse_selection(self, project_name: str, entity_name: str, target_field: str) -> RecordSelectionBrowseResult:
        """Return the complete record list for the specification's type, or a too-large error."""
        _, service_type = self._selection_resolution_set(project_name, entity_name, target_field)
        capabilities = await self.get_selection_capabilities(project_name, entity_name, target_field)
        if not capabilities.type.browse_supported:
            raise ValidationError(
                f"Browse is not enabled for remote type '{service_type}'.",
                error_code="RECORD_SELECTION_UNSUPPORTED",
            )

        try:
            records, completeness = await self.reconciliation_client.list_records(service_type)
        except RecordSelectionServiceError as exc:
            self._raise_selection_failure(exc)

        if completeness != "complete":
            raise DependencyError(
                "The reconciliation service returned a record list that it did not mark complete.",
                error_code="RECORD_SELECTION_INVALID_RESPONSE",
            )
        return RecordSelectionBrowseResult(
            items=[self._selection_record(record, service_type) for record in records],
            completeness="complete",
        )

    async def get_available_target_fields(self, project_name: str, entity_name: str) -> list[str]:
        """
        Get available target fields for an entity (from preview schema).

        Args:
            project_name: Project name
            entity_name: Entity name

        Returns:
            List of column names from entity preview

        Raises:
            NotFoundError: If entity doesn't exist
        """
        # Lazy-load ShapeShiftService if needed
        if self.shapeshift_service is None:
            from backend.app.services.shapeshift_service import (  # pylint: disable=import-outside-toplevel
                get_shapeshift_service,
            )

            # Use shared singleton cache (not a new instance)
            self.shapeshift_service = get_shapeshift_service()

        try:
            preview_result: PreviewResult = await self.shapeshift_service.preview_entity(project_name, entity_name, limit=1)
            if isinstance(preview_result.rows, list) and preview_result.rows:
                return list(preview_result.rows[0].keys())

            if preview_result.columns:
                fields: list[str] = []
                for col in preview_result.columns:
                    column_name = getattr(col, "name", None)
                    if not isinstance(column_name, str):
                        column_name = getattr(col, "_mock_name", None)
                    if isinstance(column_name, str):
                        fields.append(column_name)
                return fields

            return []

        except Exception as e:
            logger.error(f"Failed to get fields for entity '{entity_name}': {e}")
            raise NotFoundError(f"Entity '{entity_name}' not found or failed to load") from e

    def get_mapping_count(self, project_name: str, entity_name: str, target_field: str) -> int:
        """
        Get the number of mappings for an entity mapping specification.

        Uses domain model method for querying.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field name

        Returns:
            Number of mappings

        Raises:
            NotFoundError: If mapping specification doesn't exist
        """
        recon_config: core.EntityResolutionCatalog = self.catalog_manager.load_catalog(project_name)

        # Use domain model method
        entity_mapping: core.EntityResolutionSet | None = recon_config.get(entity_name, target_field)
        if entity_mapping is None:
            raise NotFoundError(f"Specification for entity '{entity_name}' and target field '{target_field}' not found")

        return entity_mapping.count()
