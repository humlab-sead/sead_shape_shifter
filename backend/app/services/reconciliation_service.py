"""Service for entity reconciliation against SEAD database."""

import abc
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from loguru import logger

from backend.app.clients.reconciliation_client import (
    ReconciliationClient,
    ReconciliationQuery,
)
from backend.app.core.config import settings
from backend.app.core.operation_manager import OperationStatus, operation_manager
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models import (
    AutoReconcileResult,
    EntityReconciliationSpec,
    Project,
    ReconciliationCandidate,
    ReconciliationConfig,
    ReconciliationMapping,
    ReconciliationSource,
)
from backend.app.models.shapeshift import PreviewResult
from backend.app.services import ProjectService, ShapeShiftService
from backend.app.utils.exceptions import BadRequestError, NotFoundError
from backend.app.utils.reconciliation_migration import detect_format_version, migrate_config_v1_to_v2
from src.loaders import DataLoader, DataLoaders
from src.model import DataSourceConfig, ShapeShiftProject, TableConfig


class ReconciliationSourceResolver(abc.ABC):

    def __init__(self, project_name: str, project_service: ProjectService):

        self.project_name: str = project_name
        self.project_service: ProjectService = project_service
        self.preview_service: ShapeShiftService = ShapeShiftService(project_service)

        self.api_config: Project = self.project_service.load_project(project_name)
        self.config: ShapeShiftProject = ProjectMapper.to_core(self.api_config)

    @abc.abstractmethod
    async def resolve(self, entity_name: str, entity_spec: EntityReconciliationSpec) -> list[dict]:
        """Resolve source data based on entity spec source project."""

    @staticmethod
    def get_resolver_cls_for_source(entity_name: str, source: str | ReconciliationSource | None) -> "type[ReconciliationSourceResolver]":
        """Get appropriate resolver class for the given source specification."""
        if not source or (isinstance(source, str) and source == entity_name):
            return TargetEntityReconciliationSourceResolver

        if isinstance(source, str):
            return AnotherEntityReconciliationSourceResolver

        if isinstance(source, ReconciliationSource):
            return SqlQueryReconciliationSourceResolver

        raise BadRequestError(f"Invalid source specification: {source}")


class TargetEntityReconciliationSourceResolver(ReconciliationSourceResolver):
    """Case 1: No source, empty, or same as entity name -> use entity pource == entity_name)"""

    async def resolve(self, entity_name: str, entity_spec: EntityReconciliationSpec) -> list[dict]:
        logger.debug(f"Using preview data from entity '{entity_name}'")
        preview_result: PreviewResult = await self.preview_service.preview_entity(self.project_name, entity_name, limit=1000)
        return preview_result.rows


class AnotherEntityReconciliationSourceResolver(ReconciliationSourceResolver):
    """Case 2: Reconciliation source is the the result of another entity's data."""

    async def resolve(self, entity_name: str, entity_spec: EntityReconciliationSpec) -> list[dict]:

        assert isinstance(entity_spec.source, str)

        source: str = entity_spec.source

        logger.info(f"Fetching preview data from entity '{source}' for reconciliation of '{entity_name}'")

        if source not in self.config.tables:
            raise NotFoundError(f"Source entity '{source}' not found in project")

        preview_result: PreviewResult = await self.preview_service.preview_entity(self.project_name, source, limit=1000)
        source_data = preview_result.rows

        logger.debug(f"Fetched {len(source_data)} rows from entity '{source}'")
        return source_data


class SqlQueryReconciliationSourceResolver(ReconciliationSourceResolver):
    """Case 3: Reconciliation source is a custom SQL query."""

    async def resolve(self, entity_name: str, entity_spec: EntityReconciliationSpec) -> list[dict]:

        assert isinstance(entity_spec.source, ReconciliationSource)

        source: str | ReconciliationSource = entity_spec.source
        logger.info(f"Executing custom query for reconciliation of '{entity_name}'")

        # Get data source config from ShapeShiftProject
        if source.data_source not in self.config.data_sources:
            raise NotFoundError(f"Data source '{source.data_source}' not found in project")

        data_source_config: DataSourceConfig = self.config.get_data_source(source.data_source)

        loader: DataLoader = DataLoaders.get(data_source_config.driver)(data_source_config)
        sql_cfg_dict: dict[str, Any] = {
            "source": None,
            "type": source.type,
            "keys": [],
            "columns": [],
            "data_source": source.data_source,
            "query": source.query,
        }
        table_cfg: TableConfig = TableConfig(cfg=sql_cfg_dict, entity_name="recon_temp")
        custom_data: pd.DataFrame = await loader.load(entity_name=entity_name, table_cfg=table_cfg)
        logger.debug(f"Custom query returned {len(custom_data)} rows")
        return custom_data.to_dict(orient="records")


class ReconciliationQueryService:
    """Service for building reconciliation queries."""

    class QueryBuildResult:
        def __init__(self, queries: dict[str, ReconciliationQuery], key_mapping: dict[str, tuple[Any, ...]]):
            self.queries: dict[str, ReconciliationQuery] = queries
            self.key_mapping: dict[str, tuple[Any, ...]] = key_mapping

    def create(self, target_field: str, entity_spec: EntityReconciliationSpec, max_candidates: int, source_data: list[dict[str, Any]], service_type: str):
        """Build reconciliation queries from source data based on entity spec.

        Args:
            target_field: Target field name for reconciliation
            entity_spec: Reconciliation specification
            max_candidates: Max candidates per query
            source_data: Source data rows
            service_type: Reconciliation service entity type
            Returns:
            dict of query_id -> ReconciliationQuery
            dict of query_id -> source_value_mapping
        """
        queries: dict[str, ReconciliationQuery] = {}
        key_mapping: dict[str, Any] = {}  # query_id -> source_value

        for idx, row in enumerate(source_data):
            # Extract target field value
            target_value = row.get(target_field)

            # Skip if target value is None
            if target_value is None:
                continue

            # Build search query string from target field
            query_string: str = str(target_value)

            if not query_string.strip():
                continue

            query_id: str = f"q{idx}"
            key_mapping[query_id] = target_value

            # Build properties from property_mappings
            # Maps service property IDs to source column values
            properties = []
            for property_id, source_column in entity_spec.property_mappings.items():
                value = row.get(source_column)
                if value is not None:
                    properties.append({"pid": property_id, "v": str(value)})

            queries[query_id] = ReconciliationQuery(
                query=query_string,
                entity_type=service_type,
                limit=max_candidates,
                properties=properties if properties else None,
            )

        return ReconciliationQueryService.QueryBuildResult(queries=queries, key_mapping=key_mapping)


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
        self.recon_client: ReconciliationClient = reconciliation_client
        self.project_service: ProjectService = ProjectService()
        self.query_builder: ReconciliationQueryService = ReconciliationQueryService()

    def _get_default_recon_config_filename(self, project_name: str) -> Path:
        """Get path to reconciliation YAML file."""
        return self.config_dir / f"{project_name}-reconciliation.yml"

    def load_reconciliation_config(self, project_name: str, recon_config_filename: Path | None = None) -> ReconciliationConfig:
        """
        Load reconciliation from YAML file with automatic v1 to v2 migration.

        Args:
            project_name: Project name

        Returns:
            Reconciliation configuration (v2 format)
        """
        recon_config_filename = recon_config_filename or self._get_default_recon_config_filename(project_name)

        if not recon_config_filename.exists():
            logger.info(f"No reconciliation config found for '{project_name}', creating empty config")
            return ReconciliationConfig(service_url=settings.reconciliation_service_url, entities={})

        logger.debug(f"Loading reconciliation config from {recon_config_filename}")
        with open(recon_config_filename, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Detect format version and auto-migrate if needed
        version = detect_format_version(data)
        if version == "1.0":
            logger.warning(f"Detected v1 format for '{project_name}', auto-migrating to v2")
            data = migrate_config_v1_to_v2(data)
            
            # Save migrated version
            logger.info(f"Saving auto-migrated v2 config for '{project_name}'")
            config = ReconciliationConfig(**data)
            self.save_reconciliation_config(project_name, config, recon_config_filename)
            return config

        return ReconciliationConfig(**data)

    def save_reconciliation_config(
        self, project_name: str, recon_config: ReconciliationConfig, recon_config_filename: Path | None = None
    ) -> None:
        """
        Save reconciliation configuration to YAML file.

        Args:
            project_name: Project name
            recon_config: Reconciliation configuration to save
        """
        recon_config_filename = recon_config_filename or self._get_default_recon_config_filename(project_name)

        logger.info(f"Saving reconciliation config to {recon_config_filename}")
        with open(recon_config_filename, "w", encoding="utf-8") as f:
            yaml.dump(
                recon_config.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    async def get_reconciliation_preview(self, project_name: str, entity_name: str, target_field: str) -> list[dict]:
        """
        Get preview data for entity with reconciliation mappings applied.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field for reconciliation

        Returns:
            List of rows with source data + reconciliation status (sead_id, confidence, etc.)
        """
        # Load reconciliation config
        recon_config: ReconciliationConfig = self.load_reconciliation_config(project_name)

        if entity_name not in recon_config.entities:
            raise NotFoundError(f"No reconciliation spec for entity '{entity_name}'")
        
        if target_field not in recon_config.entities[entity_name]:
            raise NotFoundError(f"No reconciliation spec for entity '{entity_name}' with target field '{target_field}'")

        entity_spec: EntityReconciliationSpec = recon_config.entities[entity_name][target_field]

        # Get source data
        source_data: list[dict] = await self.get_resolved_source_data(project_name, entity_name, entity_spec)

        # Enrich with reconciliation mappings
        enriched_data: list[dict] = []
        for row in source_data:
            # Extract target field value from row
            target_value = row.get(target_field)

            # Find matching mapping
            mapping: ReconciliationMapping | None = None
            for m in entity_spec.mapping:
                if m.source_value == target_value:
                    mapping = m
                    break

            # Enrich row with mapping data
            enriched_row = {
                **row,
                "sead_id": mapping.sead_id if mapping else None,
                "confidence": mapping.confidence if mapping else None,
                "notes": mapping.notes if mapping else "",
                "will_not_match": mapping.will_not_match if mapping and hasattr(mapping, "will_not_match") else False,
            }
            enriched_data.append(enriched_row)

        logger.info(f"Retrieved {len(enriched_data)} preview rows for entity '{entity_name}'")
        return enriched_data

    async def get_resolved_source_data(self, project_name: str, entity_name: str, entity_spec: EntityReconciliationSpec) -> list[dict]:
        """
        Resolve source data based on source in entity.

        Loads fresh ShapeShiftProject from disk (read-only for reconciliation).

        Args:
            project_name: Project name
            entity_name: Entity to reconcile
            entity_spec: Reconciliation specification

        Returns:
            Data to use for reconciliation (may be from different source)
        """
        resolver_cls: type[ReconciliationSourceResolver] = ReconciliationSourceResolver.get_resolver_cls_for_source(
            entity_name, entity_spec.source
        )
        resolver: ReconciliationSourceResolver = resolver_cls(project_name, self.project_service)
        data = await resolver.resolve(entity_name, entity_spec)
        return data

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

    async def auto_reconcile_entity(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        entity_spec: EntityReconciliationSpec,
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
            entity_spec: Reconciliation specification
            max_candidates: Max candidates per query
            operation_id: Optional operation ID for progress tracking

        Returns:
            AutoReconcileResult with counts and candidates

        Raises:
            ValueError: If project has unsaved changes
        """
        # Load existing config and ensure thresholds from caller are honored.
        recon_config: ReconciliationConfig = self.load_reconciliation_config(project_name)

        thresholds_updated: bool = False
        if entity_name not in recon_config.entities:
            recon_config.entities[entity_name] = {}
        
        existing_spec: EntityReconciliationSpec | None = recon_config.entities[entity_name].get(target_field)
        if existing_spec is None:
            recon_config.entities[entity_name][target_field] = entity_spec
            existing_spec = entity_spec
            thresholds_updated = True
        else:
            if existing_spec.auto_accept_threshold != entity_spec.auto_accept_threshold:
                existing_spec.auto_accept_threshold = entity_spec.auto_accept_threshold
                thresholds_updated = True
            if existing_spec.review_threshold != entity_spec.review_threshold:
                existing_spec.review_threshold = entity_spec.review_threshold
                thresholds_updated = True

        entity_spec = existing_spec

        service_type: str | None = entity_spec.remote.service_type
        if not service_type:
            if thresholds_updated:
                self.save_reconciliation_config(project_name, recon_config)
            logger.info(f"Reconciliation disabled for entity '{entity_name}' (no service_type configured)")
            return AutoReconcileResult(auto_accepted=0, needs_review=0, unmatched=0, total=0, candidates={})

        logger.info(f"Auto-reconciling entity '{entity_name}'")

        # Update progress: Starting
        if operation_id:
            operation_manager.update_progress(
                operation_id, status=OperationStatus.RUNNING, message=f"Loading source data for {entity_name}..."
            )

        source_data: list[dict] = await self.get_resolved_source_data(project_name, entity_name, entity_spec)
        logger.info(f"Using {len(source_data)} rows for reconciliation")

        # Update progress: Building queries
        if operation_id:
            operation_manager.update_progress(operation_id, message=f"Building {len(source_data)} reconciliation queries...")

        query_data: ReconciliationQueryService.QueryBuildResult = self.query_builder.create(
            target_field, entity_spec, max_candidates, source_data, service_type
        )

        if not query_data.queries:
            if thresholds_updated:
                self.save_reconciliation_config(project_name, recon_config)
            logger.warning("No valid queries to reconcile")
            if operation_id:
                operation_manager.complete_operation(operation_id, "No valid queries to reconcile")
            return AutoReconcileResult(auto_accepted=0, needs_review=0, unmatched=0, total=0, candidates={})

        # Update progress: Total queries
        if operation_id:
            operation_manager.update_progress(
                operation_id,
                total=len(query_data.queries),
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
                return AutoReconcileResult(auto_accepted=0, needs_review=0, unmatched=0, total=0, candidates={})

            # Create batch dict
            batch_items = queries_items[i : i + batch_size]
            batch_dict = dict(batch_items)

            batch_results = await self.recon_client.reconcile_batch(batch_dict)
            all_results.update(batch_results)

            # Update progress
            if operation_id:
                processed = min(i + batch_size, total_queries)
                operation_manager.update_progress(
                    operation_id, current=processed, message=f"Processed {processed}/{total_queries} queries..."
                )

        results = all_results

        # Update progress: Processing results
        if operation_id:
            operation_manager.update_progress(operation_id, message="Processing reconciliation results...")

        # Map back to source values
        candidate_map: dict[str, list[ReconciliationCandidate]] = {}
        for query_id, candidates in results.items():
            source_value = query_data.key_mapping[query_id]
            # Convert to string key for JSON serialization
            key_str = str(source_value) if source_value is not None else ""
            candidate_map[key_str] = candidates

        # Auto-accept high confidence matches
        auto_accepted, needs_review, unmatched = self.auto_accept_candidates(entity_spec, candidate_map)

        # Save updated config (mappings and/or updated thresholds)
        self.save_reconciliation_config(project_name, recon_config)

        logger.info(f"Auto-reconciliation complete: {auto_accepted} auto-accepted, " f"{needs_review} need review, {unmatched} unmatched")

        # Complete operation
        if operation_id:
            operation_manager.complete_operation(
                operation_id, f"Complete: {auto_accepted} auto-accepted, {needs_review} need review, {unmatched} unmatched"
            )

        return AutoReconcileResult(
            auto_accepted=auto_accepted,
            needs_review=needs_review,
            unmatched=unmatched,
            total=len(candidate_map),
            candidates=candidate_map,
        )

    def auto_accept_candidates(
        self, entity_spec: EntityReconciliationSpec, candidate_map: dict[str, list[ReconciliationCandidate]]
    ) -> tuple[int, int, int]:
        auto_accepted: int = 0
        needs_review: int = 0
        unmatched: int = 0

        threshold = entity_spec.auto_accept_threshold
        review_threshold: float = entity_spec.review_threshold

        for key_str, candidates in candidate_map.items():
            # Convert back from string
            source_value = key_str if key_str != "" else None

            if not candidates:
                unmatched += 1
                continue

            best_match: ReconciliationCandidate = candidates[0]
            score_normalized: float = best_match.score / 100.0 if best_match.score else 0.0

            if score_normalized >= threshold:
                # Auto-accept
                try:
                    sead_id: int = self._extract_id_from_uri(best_match.id)

                    # Remove existing mapping for this value
                    entity_spec.mapping = [m for m in entity_spec.mapping if m.source_value != source_value]

                    # Add new mapping
                    mapping = ReconciliationMapping(
                        source_value=source_value,
                        sead_id=sead_id,
                        confidence=score_normalized,
                        notes=f"Auto-matched: {best_match.name}",
                        created_by="system",
                        created_at=None,
                    )
                    entity_spec.mapping.append(mapping)
                    auto_accepted += 1
                    logger.debug(f"Auto-accepted: {source_value} -> {sead_id} ({best_match.name}, score={best_match.score:.1f})")
                except ValueError as e:
                    logger.warning(f"Cannot extract ID from {best_match.id}: {e}")
                    needs_review += 1
            elif score_normalized >= review_threshold:
                needs_review += 1
            else:
                unmatched += 1
        return auto_accepted, needs_review, unmatched

    def update_mapping(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        source_value: Any,
        sead_id: int | None,
        notes: str | None = None,
    ) -> ReconciliationConfig:
        """
        Update or remove a single mapping entry.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field for reconciliation
            source_value: Source field value
            sead_id: SEAD entity ID (None to remove mapping)
            notes: Optional notes

        Returns:
            Updated reconciliation configuration
        """
        recon_config: ReconciliationConfig = self.load_reconciliation_config(project_name)

        if entity_name not in recon_config.entities:
            raise NotFoundError(f"Entity '{entity_name}' not in reconciliation config")
        
        if target_field not in recon_config.entities[entity_name]:
            raise NotFoundError(f"Target field '{target_field}' not in reconciliation config for entity '{entity_name}'")

        entity_spec = recon_config.entities[entity_name][target_field]

        # Find existing mapping
        existing_idx = None
        for idx, mapping in enumerate(entity_spec.mapping):
            if mapping.source_value == source_value:
                existing_idx = idx
                break

        if sead_id is None:
            # Remove mapping
            if existing_idx is not None:
                entity_spec.mapping.pop(existing_idx)
                logger.info(f"Removed mapping for {source_value}")
        else:
            # Update or create mapping
            new_mapping = ReconciliationMapping(
                source_value=source_value,
                sead_id=sead_id,
                confidence=1.0,  # Manual mapping = 100% confidence
                notes=notes,
                created_by="user",
                created_at=None,
            )

            if existing_idx is not None:
                entity_spec.mapping[existing_idx] = new_mapping
                logger.info(f"Updated mapping: {source_value} -> {sead_id}")
            else:
                entity_spec.mapping.append(new_mapping)
                logger.info(f"Added new mapping: {source_value} -> {sead_id}")

        self.save_reconciliation_config(project_name, recon_config)
        return recon_config

    def mark_as_unmatched(
        self,
        project_name: str,
        entity_name: str,
        target_field: str,
        source_value: Any,
        notes: str | None = None,
    ) -> ReconciliationConfig:
        """
        Mark an entity as "will not match" - local-only with no SEAD mapping.

        Args:
            project_name: Project name
            entity_name: Entity name
            target_field: Target field for reconciliation
            source_value: Source field value
            notes: Optional reason for marking as unmatched

        Returns:
            Updated reconciliation configuration
        """
        from datetime import datetime, timezone

        recon_config: ReconciliationConfig = self.load_reconciliation_config(project_name)

        if entity_name not in recon_config.entities:
            raise NotFoundError(f"Entity '{entity_name}' not in reconciliation config")
        
        if target_field not in recon_config.entities[entity_name]:
            raise NotFoundError(f"Target field '{target_field}' not in reconciliation config for entity '{entity_name}'")

        entity_spec = recon_config.entities[entity_name][target_field]

        # Find existing mapping
        existing_idx = None
        for idx, mapping in enumerate(entity_spec.mapping):
            if mapping.source_value == source_value:
                existing_idx = idx
                break

        # Create unmatched mapping
        new_mapping = ReconciliationMapping(
            source_value=source_value,
            sead_id=None,  # No SEAD match
            will_not_match=True,  # Mark as local-only
            confidence=None,  # Not applicable
            notes=notes or "Marked as local-only (will not match)",
            created_by="user",
            created_at=None,
            last_modified=datetime.now(timezone.utc).isoformat(),
        )

        if existing_idx is not None:
            entity_spec.mapping[existing_idx] = new_mapping
            logger.info(f"Updated mapping to unmatched: {source_value}")
        else:
            entity_spec.mapping.append(new_mapping)
            logger.info(f"Marked as unmatched: {source_value}")

        self.save_reconciliation_config(project_name, recon_config)
        return recon_config
