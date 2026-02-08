"""Domain models for reconciliation system.

These models represent the business domain and are independent of API/persistence concerns.
They mirror the Pydantic DTO models but use dataclasses for flexibility and框架 independence.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolutionSource:
    """Custom data source for reconciliation (alternative to entity preview data)."""

    data_source: str
    type: str = "sql"
    query: str = ""


@dataclass
class ResolutionTarget:
    """Entity resolution specification for reconciliation."""

    service_type: str | None = None
    columns: list[str] = field(default_factory=list)


@dataclass
class ResolvedEntityPair:
    """Single entity resolution mapping entry linking source value to Target ID."""

    source_value: Any
    target_id: int | None = None
    confidence: float | None = None
    notes: str | None = None
    will_not_match: bool = False
    created_at: str | None = None
    created_by: str | None = None
    last_modified: str | None = None


@dataclass
class EntityResolutionMetadata:
    """Metadata for a entity-field resolution set.

    - `source` is the data used for entity resolution (either entity preview or custom query).
    - `property_mappings` define how to map remote (OpenRefine) service properties to columns in source.
    - `remote` specifies the OpenRefine entity type and additional columns.
    - `mapping` contains the individual resolved items.
    """

    remote: ResolutionTarget
    source: str | ResolutionSource | None = None
    property_mappings: dict[str, str] = field(default_factory=dict)
    auto_accept_threshold: float = 0.95
    review_threshold: float = 0.70

    def update_thresholds(self, threshold: float, review_threshold: float | None = None) -> bool:
        """Update auto-accept and review thresholds."""
        updated = False
        if threshold != self.auto_accept_threshold:
            self.auto_accept_threshold = threshold
            updated = True
        if review_threshold is not None and review_threshold != self.review_threshold:
            self.review_threshold = review_threshold
            updated = True
        return updated

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise ValueError(f"Invalid metadata field: {key}")
            setattr(self, key, value)


@dataclass
class EntityResolutionSet:
    """Container for entity resolution data for an entity and field."""

    metadata: EntityResolutionMetadata
    links: list[ResolvedEntityPair] = field(default_factory=list)

    def add(self, item: ResolvedEntityPair) -> None:
        """Add or update a mapping item.

        If a mapping for the same source_value exists, it will be replaced.
        """
        self.links = [m for m in self.links if m.source_value != item.source_value]
        self.links.append(item)

    def remove(self, source_value: Any) -> bool:
        """Remove a mapping item by source value.

        Returns:
            True if item was found and removed, False otherwise
        """
        original_length: int = len(self.links)
        self.links = [m for m in self.links if m.source_value != source_value]
        return len(self.links) < original_length

    def get(self, source_value: Any) -> ResolvedEntityPair | None:
        """Get mapping item by source value."""
        for item in self.links:
            if item.source_value == source_value:
                return item
        return None

    def is_empty(self) -> bool:
        """Check if this mapping has any items."""
        return len(self.links) == 0

    def count(self) -> int:
        """Get count of mapping items."""
        return len(self.links)


@dataclass
class EntityResolutionCatalog:
    """Complete entity mapping registry for all entities.

    Top-level domain model for managing entity mappings across a project.
    """

    version: str
    service_url: str
    entities: dict[str, dict[str, EntityResolutionSet]] = field(default_factory=dict)

    def get(self, entity_name: str, target_field: str) -> EntityResolutionSet | None:
        """Get mapping for an entity and target field."""
        if entity_name not in self.entities:
            return None
        return self.entities[entity_name].get(target_field)

    def exists(self, entity_name: str, target_field: str) -> bool:
        """Check if mapping exists for entity and target field."""
        return self.get(entity_name, target_field) is not None

    def add(self, entity_name: str, target_field: str, mapping: EntityResolutionSet) -> None:
        """Add or update an entity mapping."""
        if entity_name not in self.entities:
            self.entities[entity_name] = {}
        self.entities[entity_name][target_field] = mapping

    def remove(self, entity_name: str, target_field: str) -> bool:
        """Remove an entity mapping.

        Returns:
            True if mapping was found and removed, False otherwise
        """
        if entity_name not in self.entities:
            return False
        if target_field not in self.entities[entity_name]:
            return False

        del self.entities[entity_name][target_field]

        # Clean up empty entity dict
        if not self.entities[entity_name]:
            del self.entities[entity_name]

        return True

    def list(self) -> list[tuple[str, str, EntityResolutionSet]]:
        """List all mappings as (entity_name, target_field, mapping) tuples."""
        result: list[tuple[str, str, EntityResolutionSet]] = []
        for entity_name, fields in self.entities.items():
            for target_field, mapping in fields.items():
                result.append((entity_name, target_field, mapping))
        return result

    def update_metadata(self, entity_name: str, target_field: str, metadata: EntityResolutionMetadata) -> bool:
        """Update metadata of an existing mapping.

        Returns:
            True if mapping was found and updated, False otherwise
        """
        mapping: EntityResolutionSet | None = self.get(entity_name, target_field)
        if not mapping:
            # raise KeyError(f"Entity mapping for entity '{entity_name}' and target field '{target_field}' not found")
            return False

        mapping.metadata = metadata

        return True
