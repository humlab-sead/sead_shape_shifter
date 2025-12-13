"""
Data Source API Endpoints

Provides REST API for managing data sources (PostgreSQL, Access, SQLite, CSV).
Supports CRUD operations, connection testing, and status checking.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.models.data_source import (
    DataSourceConfig,
    DataSourceTestResult,
    DataSourceStatus,
)
from app.services.data_source_service import DataSourceService
from app.api.dependencies import get_config, get_data_source_service


router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("", response_model=List[DataSourceConfig], summary="List all data sources")
async def list_data_sources(
    service: DataSourceService = Depends(get_data_source_service),
) -> List[DataSourceConfig]:
    """
    Retrieve all configured data sources.
    
    Returns data sources from the configuration, with environment variables resolved.
    Passwords are excluded from the response.
    
    **Response Fields**:
    - `name`: Unique identifier for the data source
    - `driver`: Database/file driver type (postgresql, access, sqlite, csv)
    - `host`, `port`, `database`: Database connection details (for database sources)
    - `filename`: File path (for file-based sources)
    - `options`: Driver-specific configuration
    """
    try:
        logger.info("Listing all data sources")
        data_sources = service.list_data_sources()
        logger.info(f"Found {len(data_sources)} data sources")
        return data_sources
    except Exception as e:
        logger.error(f"Error listing data sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list data sources: {str(e)}",
        )


@router.get("/{name}", response_model=DataSourceConfig, summary="Get data source by name")
async def get_data_source(
    name: str,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceConfig:
    """
    Retrieve a specific data source by name.
    
    **Path Parameters**:
    - `name`: Data source identifier (e.g., "sead", "arbodat_data")
    
    **Returns**: Complete data source configuration
    
    **Errors**:
    - 404: Data source not found
    """
    try:
        logger.info(f"Getting data source: {name}")
        data_source = service.get_data_source(name)
        
        if data_source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source '{name}' not found",
            )
        
        return data_source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data source '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data source: {str(e)}",
        )


@router.post("", response_model=DataSourceConfig, status_code=status.HTTP_201_CREATED, summary="Create data source")
async def create_data_source(
    config: DataSourceConfig,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceConfig:
    """
    Create a new data source.
    
    **Request Body**: DataSourceConfig with all required fields
    - Database sources require: `driver`, `host`, `port`, `database`, `username`
    - File sources require: `driver`, `filename`
    
    **Returns**: Created data source configuration
    
    **Errors**:
    - 400: Invalid configuration or data source already exists
    - 422: Validation error (invalid port, missing required fields, etc.)
    """
    try:
        logger.info(f"Creating data source: {config.name}")
        
        # Check if already exists
        existing = service.get_data_source(config.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data source '{config.name}' already exists",
            )
        
        service.create_data_source(config)
        logger.info(f"Created data source: {config.name}")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data source '{config.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create data source: {str(e)}",
        )


@router.put("/{name}", response_model=DataSourceConfig, summary="Update data source")
async def update_data_source(
    name: str,
    config: DataSourceConfig,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceConfig:
    """
    Update an existing data source.
    
    **Path Parameters**:
    - `name`: Current data source name
    
    **Request Body**: Complete DataSourceConfig (can include new name for renaming)
    
    **Returns**: Updated data source configuration
    
    **Errors**:
    - 404: Data source not found
    - 400: Invalid configuration or new name conflicts with existing data source
    """
    try:
        logger.info(f"Updating data source: {name}")
        
        # Check if exists
        existing = service.get_data_source(name)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source '{name}' not found",
            )
        
        # If renaming, check new name doesn't exist
        if config.name != name:
            existing_new = service.get_data_source(config.name)
            if existing_new is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Data source '{config.name}' already exists",
                )
        
        service.update_data_source(name, config)
        logger.info(f"Updated data source: {name}")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data source '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update data source: {str(e)}",
        )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete data source")
async def delete_data_source(
    name: str,
    service: DataSourceService = Depends(get_data_source_service),
):
    """
    Delete a data source.
    
    **Path Parameters**:
    - `name`: Data source identifier
    
    **Safety Check**: Prevents deletion if any entities reference this data source
    
    **Returns**: 204 No Content on success
    
    **Errors**:
    - 404: Data source not found
    - 400: Data source is in use by entities (cannot be deleted)
    """
    try:
        logger.info(f"Deleting data source: {name}")
        
        # Check if exists
        existing = service.get_data_source(name)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source '{name}' not found",
            )
        
        # Check if in use
        status_info = service.get_status(name)
        if status_info.in_use_by_entities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete data source '{name}': in use by entities {status_info.in_use_by_entities}",
            )
        
        service.delete_data_source(name)
        logger.info(f"Deleted data source: {name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting data source '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete data source: {str(e)}",
        )


@router.post("/{name}/test", response_model=DataSourceTestResult, summary="Test data source connection")
async def test_data_source_connection(
    name: str,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceTestResult:
    """
    Test connection to a data source.
    
    **Path Parameters**:
    - `name`: Data source identifier
    
    **Connection Tests**:
    - **Database**: Executes `SELECT 1 as test` to verify connectivity
    - **CSV File**: Checks file exists and reads first 5 rows
    
    **Timeout**: 10 seconds maximum
    
    **Returns**: 
    - `success`: Connection successful
    - `message`: Result description or error message
    - `connection_time_ms`: Time taken for connection test (milliseconds)
    - `metadata`: Additional info (table count, file size, etc.)
    
    **Errors**:
    - 404: Data source not found
    - 400: Connection test failed (invalid credentials, host unreachable, etc.)
    """
    try:
        logger.info(f"Testing connection to data source: {name}")
        
        # Get data source config
        config = service.get_data_source(name)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source '{name}' not found",
            )
        
        # Test connection
        result = await service.test_connection(config)
        
        if result.success:
            logger.info(f"Connection test successful for '{name}' in {result.connection_time_ms}ms")
        else:
            logger.warning(f"Connection test failed for '{name}': {result.message}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection to '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}",
        )


@router.get("/{name}/status", response_model=DataSourceStatus, summary="Get data source status")
async def get_data_source_status(
    name: str,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceStatus:
    """
    Get current status of a data source.
    
    **Path Parameters**:
    - `name`: Data source identifier
    
    **Returns**:
    - `name`: Data source name
    - `is_connected`: Whether last connection test succeeded
    - `last_test_result`: Most recent connection test result
    - `in_use_by_entities`: List of entity names using this data source
    
    **Errors**:
    - 404: Data source not found
    """
    try:
        logger.info(f"Getting status for data source: {name}")
        
        # Check if exists
        config = service.get_data_source(name)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source '{name}' not found",
            )
        
        status_info = service.get_status(name)
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data source status: {str(e)}",
        )
