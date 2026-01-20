"""Tests for class-based driver schema system.

This test ensures that schemas defined in DataLoader classes are properly
registered and accessible through the DriverSchemaRegistry.
"""

import asyncio

from backend.app.api.v1.endpoints.data_sources import list_drivers
from src.loaders.driver_metadata import DriverSchema
from src.loaders.base_loader import DataLoaders
from src.loaders.driver_metadata import DriverSchemaRegistry


class TestClassBasedSchemas:
    """Test class-based schema system."""

    def test_all_registered_loaders_have_schemas(self):
        """All registered loaders should have schemas defined."""
        # Get all registered loaders
        registered_loaders = set(DataLoaders.items.keys())

        # Get all schemas
        schemas = DriverSchemaRegistry.all()
        schema_drivers = set(schemas.keys())

        # Map loader keys to expected driver names
        # Some loaders have multiple keys (e.g., xlsx, xls -> xlsx)
        loader_to_driver = {
            "postgresql": "postgresql",
            "postgres": "postgresql",  # Alias
            "sqlite": "sqlite",
            "access": "access",
            "ucanaccess": "ucanaccess",
            "csv": "csv",
            "tsv": "csv",  # TSV uses CSV loader
            "xlsx": "xlsx",
            "xls": "xlsx",  # XLS uses same schema as XLSX
            "openpyxl": "openpyxl",
            "fixed": None,  # Fixed loader doesn't have a schema
            "data": None,  # Data loader doesn't have a schema
        }

        # Check each registered loader
        for loader_key in registered_loaders:
            expected_driver = loader_to_driver.get(loader_key)
            if expected_driver is not None:
                assert expected_driver in schema_drivers, f"Loader '{loader_key}' should have schema '{expected_driver}'"

    def test_schemas_loaded_from_classes(self):
        """Schemas should be loaded from DataLoader classes."""
        schemas = DriverSchemaRegistry.all()

        # Check that we have schemas for all SQL loaders
        assert "postgresql" in schemas
        assert "sqlite" in schemas
        assert "ucanaccess" in schemas

        # Check that we have schemas for file loaders
        assert "csv" in schemas

        # Check that we have schemas for Excel loaders
        assert "xlsx" in schemas
        assert "openpyxl" in schemas

    def test_postgresql_schema_fields(self):
        """PostgreSQL schema should have correct fields."""
        schemas = DriverSchemaRegistry.all()
        pg_schema = schemas["postgresql"]

        field_names = {f.name for f in pg_schema.fields}
        assert "host" in field_names
        assert "port" in field_names
        assert "database" in field_names
        assert "username" in field_names
        assert "password" in field_names

    def test_sqlite_schema_fields(self):
        """SQLite schema should have correct fields."""
        schemas = DriverSchemaRegistry.all()
        sqlite_schema = schemas["sqlite"]

        field_names = {f.name for f in sqlite_schema.fields}
        assert "filename" in field_names

    def test_csv_schema_fields(self):
        """CSV schema should have correct fields."""
        schemas = DriverSchemaRegistry.all()
        csv_schema = schemas["csv"]

        field_names = {f.name for f in csv_schema.fields}
        assert "filename" in field_names
        assert "encoding" in field_names
        assert "delimiter" in field_names

    def test_excel_pandas_schema_fields(self):
        """Excel (pandas) schema should have correct fields."""
        schemas = DriverSchemaRegistry.all()
        xlsx_schema: DriverSchema = schemas["xlsx"]

        field_names = {f.name for f in xlsx_schema.fields}
        assert "filename" in field_names
        assert "sheet_name" in field_names

    def test_excel_openpyxl_schema_fields(self):
        """Excel (openpyxl) schema should have correct fields."""
        schemas = DriverSchemaRegistry.all()
        openpyxl_schema = schemas["openpyxl"]

        field_names = {f.name for f in openpyxl_schema.fields}
        assert "filename" in field_names
        assert "sheet_name" in field_names
        assert "range" in field_names

    def test_ucanaccess_schema_fields(self):
        """UCanAccess schema should have correct fields."""
        schemas = DriverSchemaRegistry.all()
        ucanaccess_schema = schemas["ucanaccess"]

        field_names = {f.name for f in ucanaccess_schema.fields}
        assert "filename" in field_names
        assert "ucanaccess_dir" in field_names

    def test_schema_metadata(self):
        """Schemas should have proper metadata."""
        schemas = DriverSchemaRegistry.all()

        # Known aliases - these map to a different base schema
        aliases = {
            "tsv": "csv",
            "xls": "xlsx",
            "postgres": "postgresql",
            "ucanaccess": "access",
        }

        for driver, schema in schemas.items():
            # For aliases, schema.driver points to the base schema
            if driver in aliases:
                assert schema.driver == aliases[driver], f"Alias '{driver}' should point to base schema '{aliases[driver]}'"
            else:
                assert schema.driver == driver
            assert schema.display_name
            assert schema.description
            assert schema.category in ["database", "file"]
            assert len(schema.fields) > 0

    def test_backend_endpoint_compatibility(self):
        """Schema format should be compatible with backend endpoint."""

        async def test():
            result = await list_drivers()
            assert len(result) > 0

            # Check that all schemas have required fields
            for driver, schema_response in result.items():
                assert schema_response.driver == driver
                assert schema_response.display_name
                assert schema_response.description
                assert schema_response.category
                assert len(schema_response.fields) > 0

        asyncio.run(test())
