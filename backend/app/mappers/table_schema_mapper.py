import math
from typing import Any

import backend.app.models.data_source as api
from src.loaders.sql_loaders import CoreSchema


def safe_str_or_none(value: Any) -> str | None:
    """Convert value to string or None, handling pandas NaN.

    Args:
        value: Value to convert (may be str, None, float NaN, etc.)

    Returns:
        String value or None
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return str(value) if value else None


def safe_int_or_none(value: Any) -> int | None:
    """Convert value to int or None, handling pandas NaN.

    Args:
        value: Value to convert (may be int, None, float NaN, etc.)

    Returns:
        Integer value or None
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return int(value) if value is not None else None
    except (ValueError, TypeError):
        return None


class TableSchemaMapper:
    @staticmethod
    def to_api_schema(core_schema: CoreSchema.TableSchema) -> api.TableSchema:
        # Convert CoreSchema.TableSchema to API TableSchema
        api_schema: api.TableSchema = api.TableSchema(
            table_name=core_schema.table_name,
            schema_name=core_schema.schema_name,
            columns=[
                api.ColumnMetadata(
                    name=col.name,
                    data_type=col.data_type,
                    nullable=col.nullable,
                    default=safe_str_or_none(col.default),
                    is_primary_key=col.is_primary_key,
                    max_length=safe_int_or_none(col.max_length),
                )
                for col in core_schema.columns
            ],
            primary_keys=core_schema.primary_keys,
            foreign_keys=[
                api.ForeignKeyMetadata(
                    column=fk.column,
                    referenced_table=fk.referenced_table,
                    referenced_column=fk.referenced_column,
                    constraint_name=safe_str_or_none(fk.constraint_name),
                )
                for fk in core_schema.foreign_keys
            ],
            indexes=core_schema.indexes,
            row_count=core_schema.row_count,
        )
        return api_schema
