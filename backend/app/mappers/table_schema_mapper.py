import backend.app.models.data_source as api
from loaders.sql_loaders import CoreSchema


class TableSchemaMapper:
    @staticmethod
    def to_api_schema(core_schema: CoreSchema.TableSchema) -> api.TableSchema:
        # Convert CoreSchema.TableSchema to API TableSchema
        api_schema: api.TableSchema = api.TableSchema(
            table_name=core_schema.table_name,
            columns=[
                api.ColumnMetadata(
                    name=col.name,
                    data_type=col.data_type,
                    nullable=col.nullable,
                    default=col.default,
                    is_primary_key=col.is_primary_key,
                    max_length=col.max_length,
                )
                for col in core_schema.columns
            ],
            primary_keys=core_schema.primary_keys,
            foreign_keys=[
                api.ForeignKeyMetadata(
                    **{
                        "column_name": fk.column,
                        "foreign_table_name": fk.referenced_table,
                        "foreign_column_name": fk.referenced_column,
                    }
                )
                for fk in core_schema.foreign_keys
            ],
            indexes=core_schema.indexes,
            row_count=core_schema.row_count,
        )
        return api_schema
