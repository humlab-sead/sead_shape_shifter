"""
Type Mapping Service

Suggests Shape Shifter entity field types from SQL data types.
Provides confidence scores and handles common type mappings.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel


class TypeMapping(BaseModel):
    """Suggested type mapping for a column."""

    sql_type: str
    suggested_type: str
    confidence: float  # 0.0 to 1.0
    reason: str
    alternatives: List[str] = []


class TypeMappingService:
    """Service for mapping SQL types to Shape Shifter entity field types."""

    # Shape Shifter common field types
    FIELD_TYPES = [
        "string",
        "integer",
        "float",
        "boolean",
        "date",
        "datetime",
        "text",
        "uuid",
        "json",
    ]

    # Mapping rules: SQL type pattern -> (Shape Shifter type, confidence, reason)
    TYPE_RULES = {
        # Integer types
        "smallint": ("integer", 1.0, "Standard small integer type"),
        "integer": ("integer", 1.0, "Standard integer type"),
        "int": ("integer", 1.0, "Standard integer type"),
        "bigint": ("integer", 1.0, "Standard big integer type"),
        "serial": ("integer", 1.0, "Auto-incrementing integer"),
        "bigserial": ("integer", 1.0, "Auto-incrementing big integer"),
        # Floating point types
        "real": ("float", 1.0, "Single precision floating point"),
        "double precision": ("float", 1.0, "Double precision floating point"),
        "numeric": ("float", 0.9, "Arbitrary precision number, usually used for decimal values"),
        "decimal": ("float", 0.9, "Fixed precision number"),
        "money": ("float", 0.8, "Currency type, typically mapped to float"),
        # String types
        "character varying": ("string", 1.0, "Variable length string"),
        "varchar": ("string", 1.0, "Variable length string"),
        "character": ("string", 1.0, "Fixed length string"),
        "char": ("string", 1.0, "Fixed length string"),
        "text": ("text", 1.0, "Unlimited length text"),
        # Boolean
        "boolean": ("boolean", 1.0, "Boolean true/false value"),
        "bool": ("boolean", 1.0, "Boolean true/false value"),
        # Date/Time types
        "date": ("date", 1.0, "Date without time"),
        "timestamp": ("datetime", 1.0, "Date and time with timezone"),
        "timestamp without time zone": ("datetime", 1.0, "Date and time without timezone"),
        "timestamp with time zone": ("datetime", 1.0, "Date and time with timezone"),
        "time": ("string", 0.7, "Time only, no direct Shape Shifter equivalent"),
        "time without time zone": ("string", 0.7, "Time only, no direct Shape Shifter equivalent"),
        "time with time zone": ("string", 0.7, "Time only, no direct Shape Shifter equivalent"),
        "interval": ("string", 0.6, "Time interval, no direct Shape Shifter equivalent"),
        # UUID
        "uuid": ("uuid", 1.0, "Universally unique identifier"),
        # JSON types
        "json": ("json", 1.0, "JSON data"),
        "jsonb": ("json", 1.0, "Binary JSON data"),
        # Binary types
        "bytea": ("string", 0.5, "Binary data, consider encoding as base64 string"),
        # Array types
        "array": ("json", 0.7, "Array type, best represented as JSON"),
        # Other common types
        "xml": ("text", 0.8, "XML data stored as text"),
        "inet": ("string", 0.9, "IP address as string"),
        "cidr": ("string", 0.9, "Network address as string"),
        "macaddr": ("string", 0.9, "MAC address as string"),
    }

    def get_type_mapping(
        self, sql_type: str, column_name: Optional[str] = None, is_primary_key: bool = False, max_length: Optional[int] = None
    ) -> TypeMapping:
        """
        Get suggested type mapping for a SQL column.

        Args:
            sql_type: SQL data type (e.g., 'integer', 'character varying')
            column_name: Optional column name for heuristic analysis
            is_primary_key: Whether this is a primary key column
            max_length: Maximum length for string types

        Returns:
            TypeMapping with suggestion and confidence score
        """
        # Normalize SQL type to lowercase
        sql_type_lower = sql_type.lower().strip()

        # Column name heuristics take precedence
        if column_name:
            heuristic_mapping = self._apply_heuristics(column_name, sql_type_lower)
            if heuristic_mapping:
                return heuristic_mapping

        # Check for exact match
        if sql_type_lower in self.TYPE_RULES:
            suggested_type, confidence, reason = self.TYPE_RULES[sql_type_lower]
            alternatives = self._get_alternatives(suggested_type)

            return TypeMapping(
                sql_type=sql_type,
                suggested_type=suggested_type,
                confidence=confidence,
                reason=reason,
                alternatives=alternatives,
            )

        # Check for partial matches (e.g., "character varying(255)")
        for pattern, (suggested_type, confidence, reason) in self.TYPE_RULES.items():
            if sql_type_lower.startswith(pattern):
                alternatives = self._get_alternatives(suggested_type)

                return TypeMapping(
                    sql_type=sql_type,
                    suggested_type=suggested_type,
                    confidence=confidence,
                    reason=reason,
                    alternatives=alternatives,
                )

        # Unknown type - default to string
        return TypeMapping(
            sql_type=sql_type,
            suggested_type="string",
            confidence=0.5,
            reason="Unknown type, defaulting to string for safety",
            alternatives=["text", "json"],
        )

    def _apply_heuristics(self, column_name: str, sql_type: str) -> Optional[TypeMapping]:
        """Apply heuristic rules based on column naming patterns."""
        name_lower = column_name.lower()

        # ID columns
        if name_lower.endswith("_id") or name_lower == "id":
            if "uuid" in sql_type or "guid" in sql_type:
                return TypeMapping(
                    sql_type=sql_type,
                    suggested_type="uuid",
                    confidence=0.95,
                    reason="ID column with UUID type",
                    alternatives=["string"],
                )
            return TypeMapping(
                sql_type=sql_type,
                suggested_type="integer",
                confidence=0.9,
                reason="ID column typically contains integer",
                alternatives=["string"],
            )

        # Date columns
        if any(pattern in name_lower for pattern in ["date", "timestamp", "created", "updated", "modified"]):
            return TypeMapping(
                sql_type=sql_type,
                suggested_type="datetime",
                confidence=0.85,
                reason="Column name suggests date/time value",
                alternatives=["date", "string"],
            )

        # Boolean columns
        if any(pattern in name_lower for pattern in ["is_", "has_", "enabled", "active", "deleted"]):
            return TypeMapping(
                sql_type=sql_type,
                suggested_type="boolean",
                confidence=0.85,
                reason="Column name suggests boolean flag",
                alternatives=["integer"],
            )

        # Email/URL columns
        if any(pattern in name_lower for pattern in ["email", "url", "uri", "link"]):
            return TypeMapping(
                sql_type=sql_type,
                suggested_type="string",
                confidence=0.9,
                reason="Column name suggests string value (email/URL)",
                alternatives=["text"],
            )

        # Count/number columns
        if any(pattern in name_lower for pattern in ["count", "total", "amount", "quantity", "number"]):
            if "decimal" in sql_type or "numeric" in sql_type or "float" in sql_type:
                return TypeMapping(
                    sql_type=sql_type,
                    suggested_type="float",
                    confidence=0.9,
                    reason="Count/amount column with decimal type",
                    alternatives=["integer"],
                )
            return TypeMapping(
                sql_type=sql_type,
                suggested_type="integer",
                confidence=0.9,
                reason="Count/amount column typically contains integer",
                alternatives=["float"],
            )

        return None

    def _get_alternatives(self, suggested_type: str) -> List[str]:
        """Get alternative type suggestions."""
        alternatives_map = {
            "integer": ["string", "float"],
            "float": ["string", "integer"],
            "string": ["text"],
            "text": ["string"],
            "boolean": ["integer", "string"],
            "date": ["datetime", "string"],
            "datetime": ["date", "string"],
            "uuid": ["string"],
            "json": ["text", "string"],
        }
        return alternatives_map.get(suggested_type, ["string"])

    def get_mappings_for_table(self, columns: List[Dict[str, any]]) -> Dict[str, TypeMapping]:
        """
        Get type mappings for all columns in a table.

        Args:
            columns: List of column dictionaries with keys: name, data_type, is_primary_key, max_length

        Returns:
            Dictionary mapping column names to TypeMapping objects
        """
        mappings = {}
        for column in columns:
            column_name = column.get("name")
            sql_type = column.get("data_type")
            is_pk = column.get("is_primary_key", False)
            max_length = column.get("max_length")

            mapping = self.get_type_mapping(sql_type=sql_type, column_name=column_name, is_primary_key=is_pk, max_length=max_length)
            mappings[column_name] = mapping

        return mappings
