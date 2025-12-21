"""
API Dependencies

Provides dependency injection functions for FastAPI endpoints.
"""

from typing import Generator

from fastapi import Depends

from backend.app import services
from backend.app.core.config import settings
from src.configuration.interface import ConfigLike
from src.configuration.provider import ConfigProvider, get_config_provider


def get_config(
    provider: ConfigProvider = Depends(get_config_provider),
) -> ConfigLike:
    """
    Get configuration from provider.

    Used as FastAPI dependency for endpoints needing config access.
    """
    return provider.get_config()


def get_data_source_service() -> Generator[services.DataSourceService, None, None]:
    """
    Get DataSourceService instance.

    Creates service for managing global data source files.
    Used as FastAPI dependency for data source endpoints.
    """
    service = services.DataSourceService(settings.CONFIGURATIONS_DIR)
    try:
        yield service
    finally:
        # Cleanup if needed (connection pool cleanup in future)
        pass


def get_schema_service(
    config: ConfigLike = Depends(get_config),  # pylint: disable=unused-argument
) -> Generator[services.SchemaIntrospectionService, None, None]:
    """
    Get SchemaIntrospectionService instance.

    Creates service with current configuration.
    Used as FastAPI dependency for schema introspection endpoints.
    """
    service = services.SchemaIntrospectionService(settings.CONFIGURATIONS_DIR)
    try:
        yield service
    finally:
        # Cleanup if needed (cache cleanup in future)
        pass
