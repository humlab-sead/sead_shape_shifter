"""
Filter API Endpoints

Provides REST API for filter metadata and configuration schemas.
Enables dynamic form generation for filter types.
"""

from fastapi import APIRouter
from loguru import logger

from backend.app.models.filter_schema import FilterFieldMetadataResponse, FilterSchemaResponse
from backend.app.utils.error_handlers import handle_endpoint_errors
from src.transforms.filter_metadata import FilterSchemaRegistry

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("/types", response_model=dict[str, FilterSchemaResponse], summary="Get available filter types")
@handle_endpoint_errors
async def list_filter_types() -> dict[str, FilterSchemaResponse]:
    """
    Get metadata for all available filter types.

    Returns schema information for each filter including:
    - Required and optional fields
    - Field types and descriptions
    - Display names and placeholders

    **Use this endpoint to dynamically build filter-specific configuration forms.**

    **Supported Filters**:
    - `query`: Pandas query expression filter
    - `exists_in`: Keep rows where column exists in another entity

    **Response Structure**:
    ```json
    {
      "query": {
        "key": "query",
        "display_name": "Pandas Query",
        "description": "Filter rows using Pandas query syntax",
        "fields": [
          {
            "name": "query",
            "type": "string",
            "required": true,
            "description": "Pandas query expression",
            "placeholder": "column_name > 100"
          }
        ]
      },
      "exists_in": {
        "key": "exists_in",
        "display_name": "Exists In",
        "description": "Keep rows where column value exists in another entity",
        "fields": [
          {
            "name": "other_entity",
            "type": "entity",
            "required": true,
            "description": "Entity to check against",
            "placeholder": "Select entity",
            "options_source": "entities"
          },
          ...
        ]
      }
    }
    ```

    Returns:
        Dictionary mapping filter keys to their schemas
    """
    logger.debug("Fetching filter schemas")
    schemas = FilterSchemaRegistry.all()

    return {
        key: FilterSchemaResponse(
            key=schema.key,
            display_name=schema.display_name,
            description=schema.description,
            fields=[
                FilterFieldMetadataResponse(
                    name=field.name,
                    type=field.type,
                    required=field.required,
                    default=field.default,
                    description=field.description,
                    placeholder=field.placeholder,
                    options_source=field.options_source,
                )
                for field in schema.fields
            ],
        )
        for key, schema in schemas.items()
    }
