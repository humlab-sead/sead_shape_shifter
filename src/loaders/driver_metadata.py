"""Driver metadata registry for data source configuration schemas.

This module defines the configuration schema for each data source driver,
enabling dynamic form generation and validation throughout the application.

Schemas are loaded from input/driver_schemas.yml at import time.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml


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
    """

    name: str
    type: Literal["string", "integer", "boolean", "password", "file_path"]
    required: bool = False
    default: Any = None
    description: str = ""
    min_value: int | None = None
    max_value: int | None = None
    placeholder: str = ""


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

    Schemas are automatically loaded from input/driver_schemas.yml at import time.
    """

    _schemas: dict[str, DriverSchema] = {}
    _loaded: bool = False

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
        cls._ensure_loaded()
        return cls._schemas.get(driver)

    @classmethod
    def all(cls) -> dict[str, DriverSchema]:
        """Get all registered driver schemas.

        Returns:
            Dictionary mapping driver names to schemas
        """
        cls._ensure_loaded()
        return cls._schemas.copy()

    @classmethod
    def list_drivers(cls) -> list[str]:
        """Get list of all registered driver names.

        Returns:
            List of driver identifiers
        """
        cls._ensure_loaded()
        return list(cls._schemas.keys())

    @classmethod
    def _ensure_loaded(cls) -> None:
        """Ensure schemas are loaded from YAML file."""
        if not cls._loaded:
            cls.load_from_yaml()

    @classmethod
    def load_from_yaml(cls, yaml_path: str | Path | None = None) -> None:
        """Load driver schemas from YAML file.

        Args:
            yaml_path: Path to YAML file. If None, uses default location.
        """
        if yaml_path is None:
            # Default to input/driver_schemas.yml relative to project root
            # Find project root by looking for pyproject.toml
            current = Path(__file__).resolve()
            for parent in [current] + list(current.parents):
                if (parent / "pyproject.toml").exists():
                    yaml_path = parent / "input" / "driver_schemas.yml"
                    break
            else:
                raise FileNotFoundError("Could not locate project root (pyproject.toml not found)")

        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Driver schemas file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty or invalid YAML file: {yaml_path}")

        # Clear existing schemas
        cls._schemas.clear()

        # Load each driver schema
        for driver_name, driver_data in data.items():
            schema = cls._parse_schema(driver_name, driver_data)
            cls.register(schema)

        cls._loaded = True

    @classmethod
    def _parse_schema(cls, driver_name: str, data: dict[str, Any]) -> DriverSchema:
        """Parse driver schema from YAML data.

        Args:
            driver_name: Driver identifier
            data: YAML data for driver

        Returns:
            Parsed driver schema
        """
        # Parse fields
        fields = []
        for field_data in data.get("fields", []):
            field = FieldMetadata(
                name=field_data["name"],
                type=field_data["type"],
                required=field_data.get("required", False),
                default=field_data.get("default"),
                description=field_data.get("description", ""),
                min_value=field_data.get("min_value"),
                max_value=field_data.get("max_value"),
                placeholder=field_data.get("placeholder", ""),
            )
            fields.append(field)

        return DriverSchema(
            driver=driver_name,
            display_name=data["display_name"],
            description=data["description"],
            fields=fields,
            category=data["category"],
        )


# Schemas are automatically loaded from input/driver_schemas.yml when the registry is first accessed
# To reload schemas manually, call: DriverSchemaRegistry.load_from_yaml()
# To load from a custom path, call: DriverSchemaRegistry.load_from_yaml("/path/to/schemas.yml")
