"""
Data Source API Endpoints

Provides REST API for managing data sources (PostgreSQL, Access, SQLite, CSV).
Supports CRUD operations, connection testing, and status checking.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from loguru import logger

from backend.app.api.dependencies import get_data_source_service
from backend.app.models.data_source import (
    DataSourceConfig,
    DataSourceStatus,
    DataSourceTestResult,
)
from backend.app.models.driver_schema import DriverSchemaResponse, FieldMetadataResponse
from backend.app.models.project import ExcelMetadataResponse, ProjectFileInfo
from backend.app.services.data_source_service import DataSourceService
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.utils.error_handlers import handle_endpoint_errors
from src.loaders.driver_metadata import DriverSchemaRegistry

router = APIRouter(prefix="/data-sources", tags=["data-sources"])

ALLOWED_FILE_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE_MB = 50


@router.get("/drivers", response_model=dict[str, DriverSchemaResponse], summary="Get available data source drivers")
async def list_drivers() -> dict[str, DriverSchemaResponse]:
    """
    Get metadata for all available data source drivers.

    Returns schema information for each driver including:
    - Required and optional fields
    - Field types, defaults, and validation rules
    - Display names and descriptions

    **Use this endpoint to dynamically build driver-specific configuration forms.**

    **Supported Drivers**:
    - `postgresql`: PostgreSQL database
    - `ucanaccess`: Microsoft Access database
    - `sqlite`: SQLite database file
    - `csv`: CSV file

    **Response Structure**:
    ```json
    {
      "postgresql": {
        "driver": "postgresql",
        "display_name": "PostgreSQL",
        "description": "PostgreSQL database connection",
        "category": "database",
        "fields": [
          {
            "name": "host",
            "type": "string",
            "required": true,
            "default": "localhost",
            "description": "Database server hostname",
            "placeholder": "localhost"
          },
          ...
        ]
      }
    }
    ```
    """
    try:

        logger.debug("Fetching driver schemas")
        schemas = DriverSchemaRegistry.all()

        return {
            driver: DriverSchemaResponse(
                driver=driver,  # Use the registry key as the driver name
                display_name=schema.display_name,
                description=schema.description,
                category=schema.category,
                fields=[
                    FieldMetadataResponse(
                        name=f.name,
                        type=f.type,
                        required=f.required,
                        default=f.default,
                        description=f.description,
                        min_value=f.min_value,
                        max_value=f.max_value,
                        placeholder=f.placeholder,
                        aliases=f.aliases or [],
                    )
                    for f in schema.fields
                ],
            )
            for driver, schema in schemas.items()
        }
    except Exception as e:
        logger.error(f"Error fetching driver schemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch driver schemas: {str(e)}",
        ) from e


@router.get("", response_model=list[DataSourceConfig], summary="List all global data sources")
async def list_data_sources(
    service: DataSourceService = Depends(get_data_source_service),
) -> list[DataSourceConfig]:
    """
    Retrieve all global data source files.

    Returns data sources from separate YAML files in projects/ directory.
    Environment variables remain as ${VAR_NAME} for editing.
    Passwords are excluded from the response.

    **Response Fields**:
    - `name`: Data source identifier (filename without extension)
    - `filename`: YAML filename (e.g., "sead-options.yml")
    - `driver`: Database/file driver type (postgresql, access, sqlite, csv)
    - `host`, `port`, `database`: Database connection details (for database sources)
    - `options`: Driver-specific configuration
    """
    try:
        logger.info("Listing all global data source files")
        data_sources: list[DataSourceConfig] = service.list_data_sources()
        logger.info(f"Found {len(data_sources)} data source files")
        return data_sources
    except Exception as e:
        logger.error(f"Error listing data sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list data sources: {str(e)}",
        ) from e


@router.get("/files", response_model=list[ProjectFileInfo], summary="List available data source files")
@handle_endpoint_errors
async def list_data_source_files(ext: list[str] | None = Query(default=None, description="Filter by extension")) -> list[ProjectFileInfo]:
    """List Excel/CSV files available for data source configuration."""

    project_service: ProjectService = get_project_service()
    return project_service.list_data_source_files(extensions=ext)


@router.get("/excel/metadata", response_model=ExcelMetadataResponse, summary="Get Excel sheets and columns")
@handle_endpoint_errors
async def get_excel_metadata(
    file: str = Query(..., description="Path to Excel file (absolute or relative to project root)"),
    sheet_name: str | None = Query(default=None, description="Optional sheet name to inspect for columns"),
) -> ExcelMetadataResponse:
    """Return available sheets and columns for a given Excel file."""

    project_service: ProjectService = get_project_service()
    sheets, columns = project_service.get_excel_metadata(file_path=file, sheet_name=sheet_name)
    return ExcelMetadataResponse(sheets=sheets, columns=columns)


@router.post(
    "/files",
    response_model=ProjectFileInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a data source file",
)
@handle_endpoint_errors
async def upload_data_source_file(file: UploadFile = File(...)) -> ProjectFileInfo:
    """Upload an Excel or CSV file for use in data source configurations."""

    project_service: ProjectService = get_project_service()
    return project_service.save_data_source_file(
        upload=file,
        allowed_extensions=ALLOWED_FILE_EXTENSIONS,
        max_size_mb=MAX_FILE_SIZE_MB,
    )


@router.get("/{filename}", response_model=DataSourceConfig, summary="Get data source by filename")
async def get_data_source(
    filename: str,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceConfig:
    """
    Retrieve a specific data source by filename.

    **Path Parameters**:
    - `filename`: Data source filename (e.g., "sead-options", "sead-options.yml")

    **Returns**: Complete data source configuration

    **Errors**:
    - 404: Data source file not found
    """
    try:
        logger.info(f"Getting data source: {filename}")
        data_source: DataSourceConfig | None = service.load_data_source(Path(filename))

        if data_source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source file '{filename}' not found",
            )

        return data_source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data source '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data source: {str(e)}",
        ) from e


@router.post("", response_model=DataSourceConfig, status_code=status.HTTP_201_CREATED, summary="Create global data source file")
async def create_data_source(
    config: DataSourceConfig,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceConfig:
    """
    Create a new global data source file.

    Creates a YAML file in projects/ directory (e.g., my-db-options.yml).
    The filename will be derived from the name field with "-options.yml" suffix.

    **Request Body**: DataSourceConfig with all required fields
    - Database sources require: `driver`, `host`, `port`, `database`, `username`
    - File sources require: `driver`, `filename`
    - `name`: Will be used to generate filename

    **Returns**: Created data source configuration with filename set

    **Errors**:
    - 400: Invalid configuration or file already exists
    - 422: Validation error (invalid port, missing required fields, etc.)
    """
    try:
        # Generate filename from name
        filename = f"{config.name}-options.yml"
        logger.info(f"Creating data source file: {filename}")

        # Check if already exists
        existing: DataSourceConfig | None = service.load_data_source(Path(filename))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Data source file '{filename}' already exists",
            )

        created: DataSourceConfig = service.create_data_source(Path(filename), config)
        logger.info(f"Created data source file: {filename}")
        return created
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data source '{config.name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create data source: {str(e)}",
        ) from e


@router.put("/{filename}", response_model=DataSourceConfig, summary="Update data source file")
async def update_data_source(
    filename: str,
    config: DataSourceConfig,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceConfig:
    """
    Update an existing data source file.

    Updates the content of the YAML file. Filename cannot be changed.

    **Path Parameters**:
    - `filename`: Data source filename (e.g., "sead-options.yml" or "sead-options")

    **Request Body**: Complete DataSourceConfig with updated fields

    **Returns**: Updated data source configuration

    **Errors**:
    - 404: Data source file not found
    - 400: Invalid configuration
    """
    try:
        logger.info(f"Updating data source file: {filename}")

        # Check if exists
        existing: DataSourceConfig | None = service.load_data_source(Path(filename))
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source file '{filename}' not found",
            )

        updated: DataSourceConfig = service.update_data_source(Path(filename), config)
        logger.info(f"Updated data source file: {filename}")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data source '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update data source: {str(e)}",
        ) from e


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete data source file")
async def delete_data_source(
    filename: str,
    service: DataSourceService = Depends(get_data_source_service),
):
    """
    Delete a data source file.

    **Path Parameters**:
    - `filename`: Data source filename (e.g., "sead-options.yml" or "sead-options")

    **Warning**: This permanently deletes the file. Configurations using
    @include references to this file will break.

    **Returns**: 204 No Content on success

    **Errors**:
    - 404: Data source file not found
    """
    try:
        logger.info(f"Deleting data source file: {filename}")

        # Check if exists
        existing: DataSourceConfig | None = service.load_data_source(Path(filename))
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source file '{filename}' not found",
            )

        service.delete_data_source(Path(filename))
        logger.info(f"Deleted data source: {filename}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting data source '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete data source: {str(e)}",
        ) from e


@router.post("/{filename}/test", response_model=DataSourceTestResult, summary="Test data source connection")
async def test_data_source_connection(
    filename: str,
    service: DataSourceService = Depends(get_data_source_service),
) -> DataSourceTestResult:
    """
    Test connection to a data source.

    **Path Parameters**:
    - `filename`: Data source filename (e.g., \"sead-options\" or \"sead-options.yml\")

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
    - 404: Data source file not found
    - 400: Connection test failed (invalid credentials, host unreachable, etc.)
    """
    try:
        logger.info(f"Testing connection to data source: {filename}")

        # Get data source config
        config: DataSourceConfig | None = service.load_data_source(Path(filename))
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source file '{filename}' not found",
            )

        # Test connection
        result: DataSourceTestResult = await service.test_connection(config=config)

        if result.success:
            logger.info(f"Connection test successful for '{filename}' in {result.connection_time_ms}ms")
        else:
            logger.warning(f"Connection test failed for '{filename}': {result.message}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection to '{filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}",
        ) from e


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
        config: DataSourceConfig | None = service.load_data_source(Path(name))
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source '{name}' not found",
            )

        status_info = service.get_status(Path(name))
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for '{name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data source status: {str(e)}",
        ) from e
