"""Domain models for reconciliation system.

These models represent the business domain and are independent of API/persistence concerns.
They mirror the Pydantic DTO models but use dataclasses for flexibility and框架 independence.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReconciliationSourceDomain:
    """Custom data source for reconciliation (alternative to entity preview data)."""

    data_source: str
    type: str = "sql"
    query: str = ""


@dataclass
class ReconciliationRemoteDomain:
    """Remote SEAD entity specification for reconciliation."""

    service_type: str | None = None
    columns: list[str] = field(default_factory=list)


@dataclass
class ResolvedEntityPair:
    """Single reconciliation mapping entry linking source value to SEAD ID."""

    source_value: Any
    sead_id: int | None = None
    confidence: float | None = None
    notes: str | None = None
    will_not_match: bool = False
    created_at: str | None = None
    created_by: str | None = None
    last_modified: str | None = None


@dataclass
class EntityResolutionSet:
    """Mapping specification for a single target field.
    
    Business logic for entity mapping operations.
    Source is the data used for reconciliation (either entity preview or custom query).
    Property_mappings define how to map remote (OpenRefine) service properties to columns in source.
    Remote specifies the OpenRefine entity type and additional columns.
    Mapping contains the individual reconciled items.
    """

    remote: ReconciliationRemoteDomain
    source: str | ReconciliationSourceDomain | None = None
    property_mappings: dict[str, str] = field(default_factory=dict)
    auto_accept_threshold: float = 0.95
    review_threshold: float = 0.70
    mapping: list[ResolvedEntityPair] = field(default_factory=list)

    def add_mapping_item(self, item: ResolvedEntityPair) -> None:
        """Add or update a mapping item.
        
        If a mapping for the same source_value exists, it will be replaced.
        """
        # Remove existing mapping for this source value
        self.mapping = [m for m in self.mapping if m.source_value != item.source_value]
        # Add new mapping
        self.mapping.append(item)

    def remove_mapping_item(self, source_value: Any) -> bool:
        """Remove a mapping item by source value.
        
        Returns:
            True if item was found and removed, False otherwise
        """
        original_len = len(self.mapping)
        self.mapping = [m for m in self.mapping if m.source_value != source_value]
        return len(self.mapping) < original_len

    def get_mapping_item(self, source_value: Any) -> ResolvedEntityPair | None:
        """Get mapping item by source value."""
        for item in self.mapping:
            if item.source_value == source_value:
                return item
        return None

    def has_mappings(self) -> bool:
        """Check if this mapping has any mapping items."""
        return len(self.mapping) > 0

    def mapping_count(self) -> int:
        """Get count of mapping items."""
        return len(self.mapping)


@dataclass
class EntityResolutionCatalog:
    """Complete entity mapping registry for all entities.
    
    Top-level domain model for managing entity mappings across a project.
    """

    version: str
    service_url: str
    entities: dict[str, dict[str, EntityResolutionSet]] = field(default_factory=dict)

    def get_mapping(self, entity_name: str, target_field: str) -> EntityResolutionSet | None:
        """Get mapping for an entity and target field."""
        if entity_name not in self.entities:
            return None
        return self.entities[entity_name].get(target_field)

    def has_mapping(self, entity_name: str, target_field: str) -> bool:
        """Check if mapping exists for entity and target field."""
        return self.get_mapping(entity_name, target_field) is not None

    def add_mapping(
        self, entity_name: str, target_field: str, mapping: EntityResolutionSet
    ) -> None:
        """Add or update an entity mapping."""
        if entity_name not in self.entities:
            self.entities[entity_name] = {}
        self.entities[entity_name][target_field] = mapping

    def remove_mapping(self, entity_name: str, target_field: str) -> bool:
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

    def list_mappings(self) -> list[tuple[str, str, EntityResolutionSet]]:
        """List all mappings as (entity_name, target_field, mapping) tuples."""
        result = []
        for entity_name, fields in self.entities.items():
            for target_field, mapping in fields.items():
                result.append((entity_name, target_field, mapping))
        return result
