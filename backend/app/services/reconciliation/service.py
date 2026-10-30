"""Service for entity reconciliation against SEAD database."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.clients.reconciliation_client import ReconciliationClient, ReconciliationQuery
from backend.app.core.operation_manager import OperationStatus, operation_manager
from backend.app.exceptions import ResourceNotFoundError, ValidationError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.mappers.reconciliation_mapper import ReconciliationMapper
from backend.app.models import AutoReconcileResult, Project, ReconciliationCandidate
from backend.app.models.reconciliation import ReconciliationRowError
from backend.app.models.shapeshift import PreviewResult
from backend.app.services import ProjectService, ShapeShiftService
from backend.app.services.mapping_service import MappingService
from backend.app.services.reconciliation.mapping_manager import EntityMappingManager
from backend.app.services.reconciliation.resolvers import ReconciliationSourceResolver
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from src.model import ShapeShiftProject
from src.reconciliation import model as core
from src.reconciliation.mapping_model import encode_local_key
from src.reconciliation.source_strategy import ReconciliationSourceStrategy, SourceStrategyType
from src.types.fixed_entity_types import is_missing_fixed_entity_value


@dataclass
class ResolvedSourceRows:
    """Normalized target rows with optional search-source errors."""

    rows: list[dict[str, Any]]
    local_key: str | list[str]
    errors: list[ReconciliationRowError] = field(default_factory=list)


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

    def export_to_mapping(self, project_name: str, entity_name: str, target_field: str) -> tuple[int, int]:
        """Copy accepted reconciliation links into the mapping sidecar under the project lock."""
        with self.project_service._get_lock(project_name):
            return self._export_to_mapping_locked(project_name, entity_name, target_field)

    def _export_to_mapping_locked(self, project_name: str, entity_name: str, target_field: str) -> tuple[int, int]:
        """Refuse export until reviewed links have owned, verified export semantics."""
        reconciliation_catalog: core.EntityResolutionCatalog = self.catalog_manager.load_catalog(project_name)
        resolution_set: core.EntityResolutionSet | None = reconciliation_catalog.get(entity_name, target_field)
        if resolution_set is None:
            raise ResourceNotFoundError(
                f"No reconciliation registry for entity '{entity_name}' target '{target_field}'",
                resource_type="entity_mapping",
                resource_id=f"{entity_name}.{target_field}",
            )
        raise ValidationError("Reconciliation export is unavailable until owned, verified export is implemented")

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
            proposed_keys = {key for key in candidate_map if latest_mapping.get(key).status == core.DecisionStatus.PROPOSED}
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
            confidence = None
            if status == core.DecisionStatus.ACCEPTED and target_id is not None:
                for candidate in previous.candidates:
                    try:
                        candidate_id = self._extract_id_from_uri(candidate.id)
                    except BadRequestError:
                        continue
                    if candidate_id == target_id and candidate.score is not None:
                        confidence = candidate.score / 100
                        break
            decision = core.ResolvedEntityPair(
                local_key_value=local_key_value,
                source_value=previous.source_value,
                status=status,
                target_id=target_id,
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
