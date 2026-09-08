"""Data source configuration mapper between API and core models."""

from typing import Any

import backend.app.models.data_source as api
import src.model as core
from backend.app.services.data_source_policy import validate_server_managed_data_source
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
        validated = validate_server_managed_data_source(ds_config)
        schema: DriverSchema | None = validated.schema
        if not schema:
            raise ValueError(f"Unknown driver: {validated.config.driver}")

        options: dict[str, Any] = validated.options

        # Create core config
        core_config = core.DataSourceConfig(
            name=validated.config.name,
            cfg={
                "driver": validated.config.driver,
                "options": options,
            },
        )

        return core_config
