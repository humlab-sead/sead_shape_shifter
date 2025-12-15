"""Models for entity relationship suggestions."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ForeignKeySuggestion(BaseModel):
    """Suggestion for a foreign key relationship between entities."""

    remote_entity: str = Field(..., description="Name of the entity to link to")
    local_keys: List[str] = Field(..., description="Local columns to use as foreign key")
    remote_keys: List[str] = Field(..., description="Remote columns to match")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    reason: str = Field(..., description="Explanation for the suggestion")
    cardinality: Optional[str] = Field(None, description="Suggested cardinality (many_to_one, one_to_one, etc.)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "remote_entity": "users",
                "local_keys": ["user_id"],
                "remote_keys": ["user_id"],
                "confidence": 0.9,
                "reason": "Exact column name match with integer type compatibility",
                "cardinality": "many_to_one",
            }
        }
    )


class DependencySuggestion(BaseModel):
    """Suggestion for processing dependency between entities."""

    entity: str = Field(..., description="Name of the entity this entity depends on")
    reason: str = Field(..., description="Explanation for the dependency")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")

    model_config = ConfigDict(
        json_schema_extra={"example": {"entity": "users", "reason": "Entity has foreign key to users table", "confidence": 0.95}}
    )


class EntitySuggestions(BaseModel):
    """Complete set of suggestions for an entity."""

    entity_name: str = Field(..., description="Name of the entity")
    foreign_key_suggestions: List[ForeignKeySuggestion] = Field(default_factory=list, description="Suggested foreign key relationships")
    dependency_suggestions: List[DependencySuggestion] = Field(default_factory=list, description="Suggested processing dependencies")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entity_name": "orders",
                "foreign_key_suggestions": [
                    {
                        "remote_entity": "users",
                        "local_keys": ["user_id"],
                        "remote_keys": ["user_id"],
                        "confidence": 0.9,
                        "reason": "Exact column name match",
                        "cardinality": "many_to_one",
                    }
                ],
                "dependency_suggestions": [{"entity": "users", "reason": "Foreign key relationship", "confidence": 0.95}],
            }
        }
    )


class SuggestionsRequest(BaseModel):
    """Request to get suggestions for entities."""

    entities: List[dict] = Field(..., description="List of entity configurations to analyze")
    data_source_name: Optional[str] = Field(None, description="Data source for database introspection")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "entities": [
                    {"name": "users", "columns": ["user_id", "username", "email"]},
                    {"name": "orders", "columns": ["order_id", "user_id", "total"]},
                ],
                "data_source_name": "test_sqlite",
            }
        }
    )
