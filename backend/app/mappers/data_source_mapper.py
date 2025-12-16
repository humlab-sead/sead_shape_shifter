"""Data source configuration mapper between API and core models."""

import backend.app.models.data_source as api
import src.config_model as core
from src.loaders.driver_metadata import DriverSchemaRegistry


class DataSourceMapper:
    """Maps data source configurations between API and core models.
    
    Uses driver schemas to ensure correct field mapping based on
    the specific requirements of each driver.
    """

    @staticmethod
    def to_core_config(ds_config: api.DataSourceConfig) -> core.DataSourceConfig:
        """Map API DataSourceConfig to core DataSourceConfig.
        
        Uses the driver schema to determine which fields are valid
        and how they should be mapped.
        
        Args:
            ds_config: API data source configuration
            
        Returns:
            Core data source configuration
            
        Raises:
            ValueError: If driver schema not found or required fields missing
        """
        # Get schema for driver
        schema: DriverSchema | None = DriverSchemaRegistry.get(ds_config.driver)
        if not schema:
            raise ValueError(f"Unknown driver: {ds_config.driver}")
        
        # Build options dict based on schema
        options = {}
        
        # Map fields according to schema
        for field in schema.fields:
            # Try to get value from top-level API model field first
            value = getattr(ds_config, field.name, None)
            
            # If not found at top level, check options
            if value is None and ds_config.options:
                value = ds_config.options.get(field.name)
            
            # Handle password fields (extract secret value)
            if field.type == "password" and value is not None:
                if hasattr(value, "get_secret_value"):
                    value = value.get_secret_value()
            
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
