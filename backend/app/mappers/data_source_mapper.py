"""Data source configuration mapper between API and core models."""

from typing import Any

import backend.app.models.data_source as api
import src.model as core
from src.loaders.driver_metadata import DriverSchema, DriverSchemaRegistry


class DataSourceMapper:
    """Maps data source configurations between API and core models.

    Uses driver schemas to ensure correct field mapping based on
    the specific requirements of each driver.
    """

    @staticmethod
    def to_core_config(ds_config: api.DataSourceConfig) -> core.DataSourceConfig:
        """Map API DataSourceConfig to Shape Shifter Core DataSourceConfig.

        Uses the driver schema to determine which fields are valid
        and how they should be mapped.

        IMPORTANT: This method resolves environment variables during the mapping.
        API entities remain "raw" with ${ENV_VAR} syntax, but core entities
        are always fully resolved and ready for use.

        Args:
            ds_config: API data source configuration (may contain ${ENV_VARS})

        Returns:
            Core data source configuration (fully resolved)

        Raises:
            ValueError: If driver schema not found or required fields missing
        """
        # Resolve environment variables at the boundary between API and Core layers
        ds_config = ds_config.resolve_config_env_vars()

        # Get schema for driver
        schema: DriverSchema | None = DriverSchemaRegistry.get(ds_config.driver)
        if not schema:
            raise ValueError(f"Unknown driver: {ds_config.driver}")

        # Build options dict based on schema
        options: dict[str, Any] = {}

        # Map fields according to schema
        for field in schema.fields:
            value = None

            # File paths should come from options (actual DB/CSV path), not the YAML filename metadata
            if field.type == "file_path" and ds_config.options:
                value = ds_config.options.get(field.name)

            # Try to get value from top-level API model field next
            if value is None:
                value = getattr(ds_config, field.name, None)

            # If still not found, check options and aliases
            if value is None and ds_config.options:
                value = ds_config.options.get(field.name)

                if value is None and field.aliases:
                    for alias in field.aliases:
                        value = ds_config.options.get(alias)
                        if value is not None:
                            break

            # if field.type == "password" and value is not None:
            #     if hasattr(value, "get_secret_value"):
            #         value = value.get_secret_value()

            # Skip None/empty values unless field has default
            if value is None or value == "":
                if field.default is not None:
                    value = field.default
                elif field.required:
                    raise ValueError(f"Required field missing: {field.name}")
                else:
                    continue

            options[field.name] = value

        # Add any additional options not in schema
        if ds_config.options:
            for key, value in ds_config.options.items():
                if key not in options and value is not None:
                    options[key] = value

        # Create core config
        core_config = core.DataSourceConfig(
            name=ds_config.name,
            cfg={
                "driver": ds_config.driver,
                "options": options,
            },
        )

        return core_config
