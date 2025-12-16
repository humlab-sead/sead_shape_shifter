"""Service for generating entity relationship suggestions."""

from typing import Any, Optional

from loguru import logger

from backend.app.models.data_source import TableMetadata, TableSchema
from backend.app.models.suggestion import (
    DependencySuggestion,
    EntitySuggestions,
    ForeignKeySuggestion,
)
from backend.app.services.schema_service import SchemaIntrospectionService


CONFIDENCE_MAP: dict[str, float] ={
    "exact": 0.5,
    "fk_pattern": 0.4,
    "entity_pattern": 0.3,
    "other": 0.2,
}

class SuggestionService:
    """Service for suggesting foreign keys and dependencies between entities."""

    def __init__(self, schema_service: SchemaIntrospectionService):
        """Initialize with schema service for database introspection."""
        self.schema_service = schema_service

    async def suggest_for_entity(
        self, entity: dict[str, Any], all_entities: list[dict[str, Any]], data_source_name: Optional[str] = None
    ) -> EntitySuggestions:
        """
        Generate complete suggestions for an entity.

        Args:
            entity: Entity configuration dict with 'name' and 'columns'
            all_entities: list of all entity configurations
            data_source_name: Optional data source for type checking

        Returns:
            EntitySuggestions with foreign key and dependency suggestions
        """
        entity_name: str = entity.get("name", "")
        logger.info(f"Generating suggestions for entity: {entity_name}")

        # Get table schemas if data source provided
        schemas: dict[str, TableSchema] = {}
        if data_source_name:
            try:
                schemas = await self._get_table_schemas(data_source_name, all_entities)
            except Exception as e:  # pylint: disable=broad-except
                logger.warning(f"Could not load schemas from {data_source_name}: {e}")

        # Generate foreign key suggestions
        fk_suggestions: list[ForeignKeySuggestion] = await self.suggest_foreign_keys(entity, all_entities, schemas)

        # Generate dependency suggestions from foreign keys
        dep_suggestions: list[DependencySuggestion] = self._infer_dependencies_from_foreign_keys(fk_suggestions)

        return EntitySuggestions(entity_name=entity_name, foreign_key_suggestions=fk_suggestions, dependency_suggestions=dep_suggestions)

    async def suggest_foreign_keys(
        self, entity: dict[str, Any], all_entities: list[dict[str, Any]], schemas: dict[str, TableSchema] | None = None
    ) -> list[ForeignKeySuggestion]:
        """
        Suggest foreign key relationships for an entity.

        Algorithm:
        1. Match column names between entities
        2. Check type compatibility if schemas available
        3. Score suggestions based on:
           - Exact name match: +0.5
           - Type compatibility: +0.3
           - Column name patterns (_id, id): +0.2

        Args:
            entity: Entity configuration
            all_entities: All other entities to check against
            schemas: Optional table schemas for type checking

        Returns:
            list of foreign key suggestions sorted by confidence
        """
        entity_name: str = entity.get("name", "")
        entity_columns: set[str] = set(entity.get("columns", []))
        suggestions: list[ForeignKeySuggestion] = []

        if schemas is None:
            schemas = {}

        # Check against each other entity
        for other_entity in all_entities:
            other_name: str = other_entity.get("name", "")

            # Skip self
            if other_name == entity_name:
                continue

            other_columns: set[str] = set(other_entity.get("columns", []))

            # Find matching columns
            matches: list[dict[str, Any]] = self._find_column_matches(entity_columns, other_columns, entity_name, other_name, schemas)

            for match in matches:
                confidence: float = self._calculate_fk_confidence(match, entity_name, other_name, schemas)

                if confidence >= 0.5:  # Threshold for suggestions
                    suggestion = ForeignKeySuggestion(
                        remote_entity=other_name,
                        local_keys=[match["local"]],
                        remote_keys=[match["remote"]],
                        confidence=confidence,
                        reason=match["reason"],
                        cardinality=match.get("cardinality", "many_to_one"),
                    )
                    suggestions.append(suggestion)

        # Sort by confidence descending
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        logger.info(f"Found {len(suggestions)} foreign key suggestions for {entity_name}")
        return suggestions

    def _find_column_matches(
        self,
        local_columns: set[str],
        remote_columns: set[str],
        local_entity: str,  # pylint: disable=unused-argument
        remote_entity: str,
        schemas: dict[str, TableSchema],  # pylint: disable=unused-argument
    ) -> list[dict[str, Any]]:
        """
        Find matching columns between two entities.

        Matching strategies:
        1. Exact match (e.g., user_id in both)
        2. Foreign key pattern (e.g., user_id matches id in users)
        3. Entity name pattern (e.g., user_id matches remote entity 'users')
        """
        matches = []

        for local_col in local_columns:
            local_lower = local_col.lower()

            # Strategy 1: Exact match
            if local_col in remote_columns:
                matches.append(
                    {"local": local_col, "remote": local_col, "reason": f"Exact column name match: '{local_col}'", "match_type": "exact"}
                )
                continue

            # Strategy 2: Foreign key pattern (local_id matches remote id)
            # e.g., user_id -> users.user_id or users.id
            if local_lower.endswith("_id"):
                prefix = local_lower[:-3]  # Remove _id

                # Check if local column matches remote entity name
                if prefix == remote_entity.lower().rstrip("s"):  # users -> user
                    # Look for id or entity_id in remote
                    for remote_col in remote_columns:
                        remote_lower = remote_col.lower()
                        if remote_lower in ["id", local_lower]:
                            matches.append(
                                {
                                    "local": local_col,
                                    "remote": remote_col,
                                    "reason": f"Foreign key pattern: '{local_col}' references '{remote_entity}.{remote_col}'",
                                    "match_type": "fk_pattern",
                                }
                            )
                            break

            # Strategy 3: Remote entity pattern
            # e.g., orders has user_id, remote entity is 'users'
            if local_lower.endswith("_id"):
                prefix = local_lower[:-3]
                if prefix in remote_entity.lower() or remote_entity.lower() in prefix:
                    # Look for matching column in remote
                    for remote_col in remote_columns:
                        remote_lower = remote_col.lower()
                        if remote_lower in [local_lower, f"{remote_entity.lower()}_id", "id"]:
                            matches.append(
                                {
                                    "local": local_col,
                                    "remote": remote_col,
                                    "reason": f"Entity name pattern: '{local_col}' likely references '{remote_entity}'",
                                    "match_type": "entity_pattern",
                                }
                            )
                            break

        return matches

    def _calculate_fk_confidence(
        self, match: dict[str, Any], local_entity: str, remote_entity: str, schemas: dict[str, TableSchema]
    ) -> float:
        """
        Calculate confidence score for a foreign key suggestion.

        Scoring:
        - Exact name match: 0.5 base
        - FK pattern match: 0.4 base
        - Entity pattern match: 0.3 base
        - Type compatibility: +0.3
        - Both integer types: +0.2
        """
        match_type = match.get("match_type", "")

        confidence: float = CONFIDENCE_MAP.get(match_type) or CONFIDENCE_MAP.get("other") or 0.2
        
        # Check type compatibility if schemas available
        local_schema: TableSchema | None = schemas.get(local_entity)
        remote_schema: TableSchema | None = schemas.get(remote_entity)

        if local_schema and remote_schema:
            local_col = match["local"]
            remote_col = match["remote"]

            local_type = self._get_column_type(local_schema, local_col)
            remote_type = self._get_column_type(remote_schema, remote_col)

            if local_type and remote_type:
                # Both are integer types
                if "int" in local_type.lower() and "int" in remote_type.lower():
                    confidence += 0.2
                    match["reason"] += f" (integer types: {local_type} → {remote_type})"
                # Types are compatible
                elif self._types_compatible(local_type, remote_type):
                    confidence += 0.15
                    match["reason"] += f" (compatible types: {local_type} → {remote_type})"

        # Check if remote column is a primary key
        if remote_schema:
            remote_col = match["remote"]
            if self._is_primary_key(remote_schema, remote_col):
                confidence += 0.15
                match["reason"] += " [references primary key]"

        return min(confidence, 1.0)  # Cap at 1.0

    def _get_column_type(self, schema: TableSchema, column_name: str) -> Optional[str]:
        """Get data type for a column."""
        for col in schema.columns:
            if col.name == column_name:
                return col.data_type
        return None

    def _is_primary_key(self, schema: TableSchema, column_name: str) -> bool:
        """Check if column is a primary key."""
        for col in schema.columns:
            if col.name == column_name:
                return col.is_primary_key
        return False

    def _types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two data types are compatible for foreign keys."""
        type1_lower = type1.lower()
        type2_lower = type2.lower()

        # Integer types
        int_types = ["int", "integer", "bigint", "smallint", "tinyint"]
        if any(t in type1_lower for t in int_types) and any(t in type2_lower for t in int_types):
            return True

        # String types
        str_types = ["char", "varchar", "text", "string"]
        if any(t in type1_lower for t in str_types) and any(t in type2_lower for t in str_types):
            return True

        # Same base type
        if type1_lower.split("(")[0] == type2_lower.split("(")[0]:
            return True

        return False

    def _infer_dependencies_from_foreign_keys(self, fk_suggestions: list[ForeignKeySuggestion]) -> list[DependencySuggestion]:
        """
        Infer processing dependencies from foreign key suggestions.

        Entities with foreign keys should depend on the referenced entities.
        """
        dependencies = []
        seen_entities = set()

        for fk in fk_suggestions:
            # Only suggest dependencies for high-confidence FKs
            if fk.confidence >= 0.7 and fk.remote_entity not in seen_entities:
                dependencies.append(
                    DependencySuggestion(
                        entity=fk.remote_entity,
                        reason=f"Foreign key relationship to {fk.remote_entity} ({', '.join(fk.local_keys)} → {', '.join(fk.remote_keys)})",
                        confidence=min(fk.confidence + 0.1, 1.0),  # Slightly higher than FK confidence
                    )
                )
                seen_entities.add(fk.remote_entity)

        return dependencies

    async def _get_table_schemas(self, data_source_name: str, entities: list[dict[str, Any]]) -> dict[str, TableSchema]:
        """Get table schemas for all entities from data source."""
        schemas = {}

        # Get table list
        try:
            tables: list[TableMetadata] = await self.schema_service.get_tables(data_source_name)
            table_names: set[str] = {t.name for t in tables}
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Could not list tables: {e}")
            return schemas

        # Load schemas for entities that match table names
        for entity in entities:
            entity_name = entity.get("name", "")

            # Try exact match or common variations
            table_name = None
            if entity_name in table_names:
                table_name = entity_name
            elif entity_name.lower() in {t.lower() for t in table_names}:
                # Case-insensitive match
                table_name = next(t for t in table_names if t.lower() == entity_name.lower())

            if table_name:
                try:
                    schema = await self.schema_service.get_table_schema(data_source_name, table_name)
                    schemas[entity_name] = schema
                except Exception as e:  # pylint: disable=broad-except
                    logger.warning(f"Could not load schema for {table_name}: {e}")

        return schemas


# Dependency injection helper
def get_suggestion_service(schema_service: SchemaIntrospectionService) -> SuggestionService:
    """Factory function for dependency injection."""
    return SuggestionService(schema_service)
