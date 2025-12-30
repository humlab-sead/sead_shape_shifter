"""Driver metadata registry for data source configuration schemas.

This module defines the configuration schema for each data source driver,
enabling dynamic form generation and validation throughout the application.

Schemas are automatically loaded from registered DataLoader classes.
"""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class FieldMetadata:
    """Metadata for a configuration field.

    Attributes:
        name: Field identifier (e.g., 'host', 'port')
        type: Field data type
        required: Whether the field is mandatory
        default: Default value for the field
        description: Human-readable description
        min_value: Minimum value for integer fields
        max_value: Maximum value for integer fields
        placeholder: Example value to show in UI
        aliases: Alternative names for the field
    """

    name: str
    type: Literal["string", "integer", "boolean", "password", "file_path"]
    required: bool = False
    default: Any = None
    description: str = ""
    min_value: int | None = None
    max_value: int | None = None
    placeholder: str = ""
    aliases: list[str] | None = None


@dataclass
class DriverSchema:
    """Schema defining what fields a driver supports.

    Attributes:
        driver: Driver identifier (e.g., 'postgresql', 'ucanaccess')
        display_name: Human-readable driver name
        description: Driver description
        fields: List of supported configuration fields
        category: Driver category (database or file)
    """

    driver: str
    display_name: str
    description: str
    fields: list[FieldMetadata]
    category: Literal["database", "file"]


class DriverSchemaRegistry:
    """Registry for driver configuration schemas.

    This class maintains a registry of all available data source drivers
    and their configuration schemas, enabling dynamic form generation
    and validation.

    Schemas are automatically loaded from registered DataLoader classes
    on first access.
    """

    _schemas: dict[str, DriverSchema] = {}

    @classmethod
    def register(cls, schema: DriverSchema) -> None:
        """Register a driver schema.

        Args:
            schema: Driver schema to register
        """
        cls._schemas[schema.driver] = schema

    @classmethod
    def get(cls, driver: str) -> DriverSchema | None:
        """Get schema for a specific driver.

        Args:
            driver: Driver identifier

        Returns:
            Driver schema or None if not found
        """
        if not cls._schemas:
            cls._load_from_classes()
        return cls._schemas.get(driver)

    @classmethod
    def all(cls) -> dict[str, DriverSchema]:
        """Get all registered driver schemas.

        Returns:
            Dictionary mapping driver names to schemas
        """
        if not cls._schemas:
            cls._load_from_classes()
        return cls._schemas.copy()

    @classmethod
    def list_drivers(cls) -> list[str]:
        """Get list of all registered driver names.

        Returns:
            List of driver identifiers
        """
        if not cls._schemas:
            cls._load_from_classes()
        return list(cls._schemas.keys())

    @classmethod
    def _load_from_classes(cls) -> None:
        """Load schemas from registered DataLoader classes.

        This method introspects registered loader classes and adds
        their schemas to the registry.
        """
        # Import here to avoid circular dependency
        from src.loaders.base_loader import DataLoaders

        for key, loader_cls in DataLoaders.items.items():
            schema = loader_cls.get_schema()
            if schema is not None:
                # Register schema using the driver name from the schema itself
                cls._schemas[schema.driver] = schema

                # Also register under the loader key if different from schema driver
                # This handles aliases like ucanaccess/access
                if key != schema.driver:
                    cls._schemas[key] = schema
