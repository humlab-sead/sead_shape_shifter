"""Service for entity reconciliation against SEAD database."""

import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from backend.app.clients.reconciliation_client import (
    ReconciliationClient,
    ReconciliationQuery,
)
from backend.app.models.reconciliation import (
    AutoReconcileResult,
    EntityReconciliationSpec,
    ReconciliationCandidate,
    ReconciliationConfig,
    ReconciliationMapping,
    ReconciliationPreviewRow,
    ReconciliationSource,
)
from src.configuration.provider import ConfigStore
from src.entity_preview import EntityPreviewService
from src.loaders.sql_loader import SQLLoader
from src.configuration.provider import ConfigStore


class ReconciliationService:
    """Service for managing entity reconciliation."""

    def __init__(
        self,
        config_dir: Path,
        reconciliation_client: ReconciliationClient,
    ):
        """
        Initialize reconciliation service.

        Args:
            config_dir: Directory containing configuration files
            reconciliation_client: Client for OpenRefine reconciliation API
        """
        self.config_dir = Path(config_dir)
        self.recon_client = reconciliation_client

    def _get_reconciliation_file_path(self, config_name: str) -> Path:
        """Get path to reconciliation YAML file."""
        # FIXME: Should use value in configuration if specified!
        return self.config_dir / f"{config_name}-reconciliation.yml"

    def load_reconciliation_config(self, config_name: str) -> ReconciliationConfig:
        """
        Load reconciliation configuration from YAML file.

        Args:
            config_name: Configuration name

        Returns:
            Reconciliation configuration
        """
        recon_file = self._get_reconciliation_file_path(config_name)

        if not recon_file.exists():
            logger.info(
                f"No reconciliation config found for '{config_name}', creating empty config"
            )
            # Return empty config with default service URL
            return ReconciliationConfig(
                service_url="http://localhost:8000", entities={}
            )

        logger.debug(f"Loading reconciliation config from {recon_file}")
        with open(recon_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return ReconciliationConfig(**data)

    def save_reconciliation_config(
        self, config_name: str, recon_config: ReconciliationConfig
    ) -> None:
        """
        Save reconciliation configuration to YAML file.

        Args:
            config_name: Configuration name
            recon_config: Reconciliation configuration to save
        """
        recon_file = self._get_reconciliation_file_path(config_name)

        logger.info(f"Saving reconciliation config to {recon_file}")
        with open(recon_file, "w", encoding="utf-8") as f:
            yaml.dump(
                recon_config.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    def _get_service_type(self, entity_spec: EntityReconciliationSpec) -> str | None:
        """
        Get reconciliation service type from entity spec.

        Args:
            entity_spec: Entity reconciliation specification

        Returns:
            Reconciliation service type, or None if reconciliation disabled
        """
        return entity_spec.remote.service_type

    async def _resolve_source_data(
        self,
        entity_name: str,
        entity_spec: EntityReconciliationSpec,
        entity_preview_data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Resolve source data based on entity spec source configuration.

        Args:
            entity_name: Entity to reconcile
            entity_spec: Reconciliation specification
            entity_preview_data: Default entity preview data

        Returns:
            Data to use for reconciliation (may be from different source)
        """
        source: str | ReconciliationSource | None = entity_spec.source

        # Case 1: No source, empty, or same as entity name -> use entity preview
        if not source or (isinstance(source, str) and source == entity_name):
            logger.debug(f"Using preview data from entity '{entity_name}'")
            return entity_preview_data

        # Case 2: Source is another entity name
        if isinstance(source, str):
            logger.info(f"Fetching preview data from entity '{source}' for reconciliation of '{entity_name}'")
            # Import here to avoid circular dependency

            config = ConfigStore().get_config()
            if source not in config.entities:
                raise ValueError(f"Source entity '{source}' not found in configuration")

            preview_service = EntityPreviewService(config)
            source_data = await preview_service.get_entity_preview(source)
            logger.debug(f"Fetched {len(source_data)} rows from entity '{source}'")
            return source_data

        # Case 3: Source is a custom query dict
        if isinstance(source, ReconciliationSource):
            logger.info(f"Executing custom query for reconciliation of '{entity_name}'")
            # Import here to avoid circular dependency

            config = ConfigStore().get_config()
            
            # Get data source config
            if source.data_source not in config.data_sources:
                raise ValueError(f"Data source '{source.data_source}' not found in configuration")

            data_source_config = config.data_sources[source.data_source]
            
            # Execute query
            loader = SQLLoader(data_source_config)
            custom_data = await loader.load(source.query)
            logger.debug(f"Custom query returned {len(custom_data)} rows")
            return custom_data

        raise ValueError(f"Invalid source specification: {source}")

    def _extract_id_from_uri(self, uri: str) -> int:
        """
        Extract numeric ID from SEAD URI.

        Args:
            uri: Entity URI like 'https://w3id.org/sead/id/site/123'

        Returns:
            Numeric ID
        """
        # Extract last numeric segment
        match = re.search(r"/(\d+)/?$", uri)
        if match:
            return int(match.group(1))
        raise ValueError(f"Cannot extract numeric ID from URI: {uri}")

    async def auto_reconcile_entity(
        self,
        config_name: str,
        entity_name: str,
        entity_spec: EntityReconciliationSpec,
        entity_data: list[dict[str, Any]],
        max_candidates: int = 5,
    ) -> AutoReconcileResult:
        """
        Automatically reconcile entity instances using OpenRefine service.

        Args:
            config_name: Configuration name
            entity_name: Entity to reconcile
            entity_spec: Reconciliation specification
            entity_data: Default entity preview data (may be overridden by spec.source)
            max_candidates: Max candidates per query

        Returns:
            AutoReconcileResult with counts and candidates
        """
        logger.info(
            f"Auto-reconciling entity '{entity_name}'"
        )

        # Resolve source data based on entity_spec.source
        source_data = await self._resolve_source_data(entity_name, entity_spec, entity_data)
        logger.info(f"Using {len(source_data)} rows for reconciliation")

        # Check if reconciliation is enabled for this entity
        service_type = self._get_service_type(entity_spec)
        if not service_type:
            logger.info(
                f"Reconciliation disabled for entity '{entity_name}' (no service_type configured)"
            )
            return AutoReconcileResult(
                auto_accepted=0,
                needs_review=0,
                unmatched=0,
                total=0,
                candidates={},
            )

        # Build reconciliation queries
        queries: dict[str, ReconciliationQuery] = {}
        key_mapping: dict[str, tuple[Any, ...]] = {}  # query_id -> source_key_tuple

        for idx, row in enumerate(source_data):
            # Extract key values
            key_values = tuple(row.get(k) for k in entity_spec.keys)

            # Skip if all keys are None
            if all(v is None for v in key_values):
                continue

            # Build search query string from keys only
            query_parts = []
            for k in entity_spec.keys:
                value = row.get(k)
                if value is not None:
                    query_parts.append(str(value))

            query_string = " ".join(query_parts)

            if not query_string.strip():
                continue

            query_id = f"q{idx}"
            key_mapping[query_id] = key_values

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

        if not queries:
            logger.warning("No valid queries to reconcile")
            return AutoReconcileResult(
                auto_accepted=0,
                needs_review=0,
                unmatched=0,
                total=0,
                candidates={},
            )

        # Execute batch reconciliation
        logger.debug(f"Executing batch reconciliation for {len(queries)} queries")
        results = await self.recon_client.reconcile_batch(queries)

        # Map back to source keys
        candidate_map: dict[str, list[ReconciliationCandidate]] = {}
        for query_id, candidates in results.items():
            source_key = key_mapping[query_id]
            # Convert tuple to string key for JSON serialization
            key_str = "|".join(str(v) if v is not None else "" for v in source_key)
            candidate_map[key_str] = candidates

        # Load existing config
        recon_config = self.load_reconciliation_config(config_name)
        if entity_name not in recon_config.entities:
            recon_config.entities[entity_name] = entity_spec

        # Update entity spec reference
        entity_spec = recon_config.entities[entity_name]

        # Auto-accept high confidence matches
        auto_accepted = 0
        needs_review = 0
        unmatched = 0

        threshold = entity_spec.auto_accept_threshold
        review_threshold = entity_spec.review_threshold

        for key_str, candidates in candidate_map.items():
            source_key = tuple(
                v if v != "" else None for v in key_str.split("|")
            )  # Convert back

            if not candidates:
                unmatched += 1
                continue

            best_match = candidates[0]
            score_normalized = (
                best_match.score / 100.0 if best_match.score else 0.0
            )

            if score_normalized >= threshold:
                # Auto-accept
                try:
                    sead_id = self._extract_id_from_uri(best_match.id)

                    # Remove existing mapping for this key
                    entity_spec.mapping = [
                        m
                        for m in entity_spec.mapping
                        if tuple(m.source_values) != source_key
                    ]

                    # Add new mapping
                    mapping = ReconciliationMapping(
                        source_values=list(source_key),
                        sead_id=sead_id,
                        confidence=score_normalized,
                        notes=f"Auto-matched: {best_match.name}",
                        created_by="system",
                        created_at=None,
                    )
                    entity_spec.mapping.append(mapping)
                    auto_accepted += 1
                    logger.debug(
                        f"Auto-accepted: {source_key} -> {sead_id} ({best_match.name}, score={best_match.score:.1f})"
                    )
                except ValueError as e:
                    logger.warning(f"Cannot extract ID from {best_match.id}: {e}")
                    needs_review += 1
            elif score_normalized >= review_threshold:
                needs_review += 1
            else:
                unmatched += 1

        # Save updated config
        self.save_reconciliation_config(config_name, recon_config)

        logger.info(
            f"Auto-reconciliation complete: {auto_accepted} auto-accepted, "
            f"{needs_review} need review, {unmatched} unmatched"
        )

        return AutoReconcileResult(
            auto_accepted=auto_accepted,
            needs_review=needs_review,
            unmatched=unmatched,
            total=len(candidate_map),
            candidates=candidate_map,
        )

    def update_mapping(
        self,
        config_name: str,
        entity_name: str,
        source_values: list[Any],
        sead_id: int | None,
        notes: str | None = None,
    ) -> ReconciliationConfig:
        """
        Update or remove a single mapping entry.

        Args:
            config_name: Configuration name
            entity_name: Entity name
            source_values: Source key values
            sead_id: SEAD entity ID (None to remove mapping)
            notes: Optional notes

        Returns:
            Updated reconciliation configuration
        """
        recon_config = self.load_reconciliation_config(config_name)

        if entity_name not in recon_config.entities:
            raise ValueError(
                f"Entity '{entity_name}' not in reconciliation config"
            )

        entity_spec = recon_config.entities[entity_name]

        # Find existing mapping
        existing_idx = None
        for idx, mapping in enumerate(entity_spec.mapping):
            if mapping.source_values == source_values:
                existing_idx = idx
                break

        if sead_id is None:
            # Remove mapping
            if existing_idx is not None:
                entity_spec.mapping.pop(existing_idx)
                logger.info(f"Removed mapping for {source_values}")
        else:
            # Update or create mapping
            new_mapping = ReconciliationMapping(
                source_values=source_values,
                sead_id=sead_id,
                confidence=1.0,  # Manual mapping = 100% confidence
                notes=notes,
                created_by="user",
                created_at=None,
            )

            if existing_idx is not None:
                entity_spec.mapping[existing_idx] = new_mapping
                logger.info(
                    f"Updated mapping: {source_values} -> {sead_id}"
                )
            else:
                entity_spec.mapping.append(new_mapping)
                logger.info(f"Added new mapping: {source_values} -> {sead_id}")

        self.save_reconciliation_config(config_name, recon_config)
        return recon_config
