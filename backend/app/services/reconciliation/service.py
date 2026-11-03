"""Service for entity reconciliation against SEAD database."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from backend.app.clients.reconciliation_client import (
    CandidateVerificationProtocolError,
    CandidateVerificationUnavailableError,
    ReconciliationClient,
    ReconciliationQuery,
)
from backend.app.core.operation_manager import OperationStatus, operation_manager
from backend.app.exceptions import (
    ConfigurationError,
    DependencyError,
    DomainException,
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
    ExportToMappingOutcome,
    ExportToMappingResult,
    ReconciliationRowError,
)
from backend.app.models.shapeshift import PreviewResult
from backend.app.services import ProjectService, ShapeShiftService
from backend.app.services.mapping_service import MappingService
from backend.app.services.reconciliation.mapping_manager import EntityMappingManager
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
        for index, row in enumerate(source_data.rows):
            key = row_keys.get(index)
            mapping = entity_mapping.get(key) if key else None
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
                "errors": errors.get(index, []),
            }
            enriched_data.append(enriched_row)

        logger.info(f"Retrieved {len(enriched_data)} preview rows for entity '{entity_name}'")
        return enriched_data

    async def get_resolved_source_data(
        self, project_name: str, entity_name: str, entity_mapping: core.EntityResolutionSet
    ) -> ResolvedSourceRows:
        """
        Resolve source data based on source in entity.

        Loads fresh ShapeShiftProject from disk (read-only for reconciliation).

        Args:
            project_name: Project name
            entity_name: Entity to reconcile
            entity_mapping: Entity mapping specification (domain model)

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
        target_rows = await target_resolver.resolve(entity_name, entity_mapping)
        if strategy == SourceStrategyType.TARGET_ENTITY:
            return ResolvedSourceRows(rows=target_rows, local_key=local_key)

        resolver_cls = ReconciliationSourceResolver.get_resolver_cls_for_strategy(strategy)
        search_rows = await resolver_cls(project_name, project, self.project_service).resolve(entity_name, entity_mapping)
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

    def _extract_id_from_uri(self, uri: str) -> int:
        """
        Extract integer ID at the end of the SEAD URI

        Args:
            uri: Entity URI like 'https://w3id.org/sead/id/site/123'

        Returns:
            SEAD numeric ID
        """
        # Extract integer at the end of the URI
        match: re.Match[str] | None = re.search(r"/(\d+)/?$", uri)
        if match:
            return int(match.group(1))
        raise BadRequestError(f"Cannot extract numeric ID from URI: {uri}")

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

        missing_candidate_keys = [key for key, decision in exportable.items() if not decision.candidate_id]
        if missing_candidate_keys:
            keys = ", ".join(repr(key) for key in missing_candidate_keys)
            raise ValidationError(
                f"Accepted decisions need to be re-accepted with their selected candidate before export. Business key(s): {keys}"
            )

        service_type = resolution_set.metadata.remote.service_type
        if exportable and not service_type:
            raise ConfigurationError(f"Entity '{entity_name}' has no reconciliation service type configured")
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
            if result.outcome == "exists" and result.aggregate_id != preflight.exportable[local_key_value].target_id:
                raise CandidateVerificationProtocolError(
                    f"The Authority Service resolved a different target ID for business key {local_key_value!r}"
                )

    async def export_to_mapping(self, project_name: str, entity_name: str, target_field: str) -> ExportToMappingResult:
        """Verify accepted candidates and update only the links owned by this specification."""
        with self.project_service._get_lock(project_name):
            preflight = self._prepare_export_to_mapping_locked(project_name, entity_name, target_field)
            if not preflight.verification_items:
                return self._export_to_mapping_locked(preflight, None, unavailable=False)

        verification_results: list[CandidateVerificationResult] | None = None
        unavailable = False
        try:
            verification_results = await self.reconciliation_client.verify_candidates(list(preflight.verification_items.values()))
        except CandidateVerificationUnavailableError:
            unavailable = True
        except CandidateVerificationProtocolError as exc:
            raise DependencyError(f"Candidate verification failed; no mapping links were changed: {exc}") from exc

        with self.project_service._get_lock(project_name):
            current = self._refresh_export_preflight_locked(preflight)
            if verification_results is not None:
                try:
                    self._validate_candidate_verification_results(current, verification_results)
                except CandidateVerificationProtocolError as exc:
                    raise DependencyError(f"Candidate verification failed; no mapping links were changed: {exc}") from exc
            return self._export_to_mapping_locked(current, verification_results, unavailable=unavailable)

    def _export_to_mapping_locked(
        self,
        preflight: ReconciliationExportPreflight,
        verification_results: list[CandidateVerificationResult] | None,
        *,
        unavailable: bool,
    ) -> ExportToMappingResult:
        """Apply verified outcomes to the captured sidecar and save with its version."""
        outcomes: dict[str, ExportToMappingOutcome] = {}
        if unavailable:
            for local_key_value in preflight.verification_items:
                outcomes[local_key_value] = ExportToMappingOutcome(
                    local_key_value=local_key_value,
                    outcome="unverified",
                    reason="The Authority Service is unavailable; this link was exported without verification. "
                    "Retry export when it is available.",
                )
        elif verification_results is not None:
            for (local_key_value, _), result in zip(preflight.verification_items.items(), verification_results, strict=True):
                if result.outcome == "exists":
                    outcomes[local_key_value] = ExportToMappingOutcome(local_key_value=local_key_value, outcome="verified")
                elif result.outcome == "not_found":
                    outcomes[local_key_value] = ExportToMappingOutcome(
                        local_key_value=local_key_value,
                        outcome="not_found",
                        reason="The candidate was not found in SEAD.",
                    )
                elif result.outcome == "invalid_candidate":
                    outcomes[local_key_value] = ExportToMappingOutcome(
                        local_key_value=local_key_value,
                        outcome="invalid_candidate",
                        reason="The selected candidate URI is invalid for this entity type.",
                    )

        sidecar: MappingCatalog = preflight.sidecar_snapshot.catalog
        entity_mapping = sidecar.entities.get(preflight.entity_name) or EntityMapping(
            local_key=preflight.expected_local_key,
            public_id=preflight.expected_public_id,
            entity_type=EntityType.PRIMARY,
        )
        failed_keys = {key for key, outcome in outcomes.items() if outcome.outcome in {"not_found", "invalid_candidate"}}
        removed = 0
        for local_key_value, link in list(entity_mapping.links.items()):
            if link.owner == preflight.owner and (local_key_value not in preflight.accepted or local_key_value in failed_keys):
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
            if outcome is None or outcome.outcome in {"not_found", "invalid_candidate"}:
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
                and (
                    (outcome.outcome == "verified" and existing_link.verified_at is not None)
                    or (outcome.outcome == "unverified" and existing_link.verified_at is None)
                )
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

    def replace_catalog(self, project_name: str, catalog: core.EntityResolutionCatalog) -> None:
        """Save a whole catalog and remove links owned by specifications it removes."""
        with self.project_service._get_lock(project_name):
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
        # Load existing config and ensure thresholds from caller are honored.
        registry: core.EntityResolutionCatalog = self.catalog_manager.load_catalog(project_name)

        thresholds_updated: bool = False

        # Get existing mapping using domain model method
        existing_mapping: core.EntityResolutionSet | None = registry.get(entity_name, target_field)
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

        service_type: str | None = entity_mapping.metadata.remote.service_type
        if not service_type:
            if thresholds_updated:
                self.catalog_manager.save_catalog(project_name, registry)
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
                if self._extract_id_from_uri(candidate_id) != target_id:
                    raise ValidationError("The selected candidate URI does not match the supplied target ID")
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
