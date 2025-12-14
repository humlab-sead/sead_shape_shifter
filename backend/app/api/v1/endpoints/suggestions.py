"""API endpoints for entity relationship suggestions."""

from typing import List

from app.api.dependencies import get_schema_service
from app.models.suggestion import EntitySuggestions, SuggestionsRequest
from app.services.schema_service import SchemaIntrospectionService
from app.services.suggestion_service import SuggestionService, get_suggestion_service
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


def get_suggestion_service_dep(schema_service: SchemaIntrospectionService = Depends(get_schema_service)) -> SuggestionService:
    """Dependency injection for suggestion service."""
    return get_suggestion_service(schema_service)


@router.post("/analyze", summary="Analyze entities and generate suggestions")
async def analyze_entities(
    request: SuggestionsRequest,
    schema_service: SchemaIntrospectionService = Depends(get_schema_service),
) -> List[EntitySuggestions]:
    """
    Analyze a set of entities and generate relationship suggestions.

    **Request Body**:
    - `entities`: List of entity configurations (name, columns)
    - `data_source_name`: Optional data source for type checking

    **Returns**: List of suggestions for each entity

    **Features**:
    - Suggests foreign key relationships based on column names
    - Checks type compatibility if data source provided
    - Suggests processing dependencies
    - Confidence scores for all suggestions

    **Algorithm**:
    - Exact name match: High confidence (0.5 base)
    - Foreign key pattern (_id): Medium confidence (0.4 base)
    - Type compatibility: +0.3
    - Primary key reference: +0.15
    """
    try:
        logger.info(f"Analyzing {len(request.entities)} entities for suggestions")

        # Create service instance directly
        service = SuggestionService(schema_service)

        results = []
        for entity in request.entities:
            suggestions = await service.suggest_for_entity(
                entity=entity, all_entities=request.entities, data_source_name=request.data_source_name
            )
            results.append(suggestions)

        total_fks = sum(len(s.foreign_key_suggestions) for s in results)
        total_deps = sum(len(s.dependency_suggestions) for s in results)
        logger.info(f"Generated {total_fks} FK suggestions and {total_deps} dependency suggestions")

        return results

    except Exception as e:
        logger.error(f"Error analyzing entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze entities: {str(e)}",
        ) from e


@router.post("/entity", summary="Get suggestions for a single entity")
async def suggest_for_entity(
    entity: dict,
    all_entities: List[dict],
    data_source_name: str = None,
    schema_service: SchemaIntrospectionService = Depends(get_schema_service),
) -> EntitySuggestions:
    """
    Get relationship suggestions for a single entity.

    **Request Body**:
    - `entity`: Entity configuration to analyze
    - `all_entities`: All other entities in the configuration
    - `data_source_name`: Optional data source name

    **Returns**: Suggestions for the entity

    **Use Cases**:
    - Real-time suggestions while creating entity
    - Re-analyze entity after column changes
    - Get suggestions without analyzing all entities
    """
    try:
        logger.info(f"Getting suggestions for entity: {entity.get('name', 'unknown')}")

        # Create service instance directly
        service = SuggestionService(schema_service)

        suggestions = await service.suggest_for_entity(entity=entity, all_entities=all_entities, data_source_name=data_source_name)

        return suggestions

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}",
        ) from e
