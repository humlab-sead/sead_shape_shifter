"""Filter metadata registry for filter configuration schemas.

This module defines the configuration schema for each filter type,
enabling dynamic form generation and validation throughout the application.

Schemas are automatically loaded from registered Filter classes.
"""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class FilterFieldMetadata:
    """Metadata for a filter configuration field.

    Attributes:
        name: Field identifier (e.g., 'query', 'column', 'entity')
        type: Field data type
        required: Whether the field is mandatory
        default: Default value for the field
        description: Human-readable description
        placeholder: Example value to show in UI
        options_source: For autocomplete fields - 'entities' for available entities
    """

    name: str
    type: Literal["string", "boolean", "entity", "column"]
    required: bool = False
    default: Any = None
    description: str = ""
    placeholder: str = ""
    options_source: Literal["entities", "columns"] | None = None


@dataclass
class FilterSchema:
    """Schema defining what fields a filter supports.

    Attributes:
        key: Filter identifier (e.g., 'query', 'exists_in')
        display_name: Human-readable filter name
        description: Filter description
        fields: List of supported configuration fields
    """

    key: str
    display_name: str
    description: str
    fields: list[FilterFieldMetadata]


class FilterSchemaRegistry:
    """Registry for filter configuration schemas.

    This class maintains a registry of all available filter types
    and their configuration schemas, enabling dynamic form generation
    and validation.

    Schemas are automatically loaded from registered Filter classes
    on first access.
    """

    _schemas: dict[str, FilterSchema] = {}

    @classmethod
    def register(cls, schema: FilterSchema) -> None:
        """Register a filter schema.

        Args:
            schema: Filter schema to register
        """
        cls._schemas[schema.key] = schema

    @classmethod
    def get(cls, key: str) -> FilterSchema | None:
        """Get schema for a specific filter.

        Args:
            key: Filter identifier

        Returns:
            Filter schema or None if not found
        """
        if not cls._schemas:
            cls._load_from_classes()
        return cls._schemas.get(key)

    @classmethod
    def all(cls) -> dict[str, FilterSchema]:
        """Get all registered filter schemas.

        Returns:
            Dictionary mapping filter keys to schemas
        """
        if not cls._schemas:
            cls._load_from_classes()
        return cls._schemas

    @classmethod
    def _load_from_classes(cls) -> None:
        """Load schemas from registered filter classes.

        Introspects all registered filter classes in the Filters registry
        and extracts their schema ClassVar attributes.
        """
        from src.transforms.filter import Filters  # pylint: disable=import-outside-toplevel

        for key, filter_cls in Filters.items.items():
            if hasattr(filter_cls, "schema"):
                schema = filter_cls.schema
                cls._schemas[key] = schema

    @classmethod
    def clear(cls) -> None:
        """Clear all registered schemas.

        Primarily used for testing to reset registry state.
        """
        cls._schemas.clear()
