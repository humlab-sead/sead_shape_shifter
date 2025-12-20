"""
API Dependencies

Provides dependency injection functions for FastAPI endpoints.
"""

import sys
from pathlib import Path
from typing import Generator

from fastapi import Depends

from backend.app.services.data_source_service import DataSourceService
from backend.app.services.schema_service import SchemaIntrospectionService
from src.configuration.interface import ConfigLike
from src.configuration.provider import ConfigProvider, get_config_provider
from backend.app.core.config import settings


def get_config(
    provider: ConfigProvider = Depends(get_config_provider),
) -> ConfigLike:
    """
    Get configuration from provider.

    Used as FastAPI dependency for endpoints needing config access.
    """
    return provider.get_config()


def get_data_source_service() -> Generator[DataSourceService, None, None]:
    """
    Get DataSourceService instance.

    Creates service for managing global data source files.
    Used as FastAPI dependency for data source endpoints.
    """
    service = DataSourceService(settings.CONFIGURATIONS_DIR)
    try:
        yield service
    finally:
        # Cleanup if needed (connection pool cleanup in future)
        pass


def get_schema_service(
    config: ConfigLike = Depends(get_config),
) -> Generator[SchemaIntrospectionService, None, None]:
    """
    Get SchemaIntrospectionService instance.

    Creates service with current configuration.
    Used as FastAPI dependency for schema introspection endpoints.
    """
    service = SchemaIntrospectionService(config)
    try:
        yield service
    finally:
        # Cleanup if needed (cache cleanup in future)
        pass
